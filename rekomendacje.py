"""Rekomendacje na dziś: stałe, jawne reguły (bez zgadywania). Aplikacja tylko proponuje, decyzję podejmuje użytkownik.

Reguły:
1. Słaby dzień = wynik snu poniżej 50 ORAZ gotowość do treningu poniżej 50% (z Garmina), a bez zegarka:
   energia 1-2 ORAZ sen poniżej 6 godzin (z dziennika). Brak danych to brak rekomendacji.
2. Pierwszy słaby dzień: lżejszy trening (o ok. 20% mniej serii, np. 4 → 3). Drugi i kolejny z rzędu: dzień odpoczynku.
3. Partie, które wczoraj mocno pracowały (4 i więcej serii ćwiczeń wielostawowych, 8 i więcej serii w sumie albo
   3 i więcej serii przy średnim RPE 9+), nie powinny być dziś w treningu. Wielostawowe męczą bardziej niż izolowane. Gdy wybrany preset je mocno obciąża, proponujemy preset z innymi partiami.

Wszystkie progi są w jednym miejscu (słownik PROGI), żeby łatwo je zmieniać po testach.
"""
from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from datetime import date, timedelta

import pandas as pd

import baza
from cwiczenia_meta import rodzina, wagi_cwiczen
from presety_dane import SPORTY

PROGI = {
    "wynik_snu": 50,          # poniżej tego sen uznajemy za słaby (skala Garmina 0-100)
    "gotowosc": 50,           # poniżej tego (w %) gotowość uznajemy za niską
    "sen_godz_reczny": 6.0,   # bez zegarka: poniżej tylu godzin snu
    "energia_reczna": 2,      # bez zegarka: energia równa tej wartości albo niższa (skala 1-5)
    "ciecie_serii": 0.2,     # o ile mniej serii w lżejszym treningu
    "serie_wielostawowe": 4,  # tyle serii ćwiczeń wielostawowych w jednej partii w jeden dzień to mocna praca
    "serie_partii": 8,        # tyle serii roboczych w sumie (także izolowanych) w jednej partii to mocna praca
    "serie_partii_rpe": 3,    # przy takiej liczbie serii wystarczy wysokie RPE...
    "rpe_partii": 9.0,        # ...czyli średnie RPE co najmniej tyle
    "kolizja_presetu": 0.4,   # preset koliduje, gdy tyle jego serii (udział) wypada na obciążone partie
    "wolny_preset": 0.1,      # preset „z innymi partiami” może mieć najwyżej tyle serii na obciążonych partiach
}

# Partie, które nie mają sensu jako „obciążone” (nie ograniczają wyboru treningu)
IZOLOWANE = "Izolowane"
PARTIE_NEUTRALNE = {"Inne", "Cardio", "Cały", "Brzuch"}
JEDNOSTKI_POWT = ("powt.", "powt./nogę", "powt./stronę")


# --- ocena pojedynczego dnia -------------------------------------------------
def ocena_dnia_garmin(wynik_snu, gotowosc_proc) -> bool | None:
    """True = słaby dzień, False = w porządku, None = brak danych."""
    if wynik_snu is None or gotowosc_proc is None or pd.isna(wynik_snu) or pd.isna(gotowosc_proc):
        return None
    return bool(wynik_snu < PROGI["wynik_snu"] and gotowosc_proc < PROGI["gotowosc"])


def ocena_dnia_reczna(sen_godz, energia) -> bool | None:
    if sen_godz is None or energia is None or pd.isna(sen_godz) or pd.isna(energia):
        return None
    return bool(sen_godz < PROGI["sen_godz_reczny"] and energia <= PROGI["energia_reczna"])


def ile_slabych_dni_z_rzedu(oceny: dict[date, bool | None], dzis: date) -> int:
    """Ile kolejnych słabych dni kończy się dzisiaj (dzień bez danych albo dobry przerywa serię)."""
    licznik, dzien = 0, dzis
    while oceny.get(dzien) is True:
        licznik += 1
        dzien -= timedelta(days=1)
    return licznik


def poziom_regeneracji(oceny: dict[date, bool | None], dzis: date) -> str | None:
    """'lzejszy' po pierwszym słabym dniu, 'odpoczynek' od drugiego z rzędu, inaczej None."""
    n = ile_slabych_dni_z_rzedu(oceny, dzis)
    return None if n == 0 else ("lzejszy" if n == 1 else "odpoczynek")


def lzejsze_serie(serie: int | None) -> int | None:
    """O ok. 20% mniej serii (4 → 3, 5 → 4, 6 → 5), minimum 2. Jedna i dwie serie (np. cardio) zostają."""
    if serie is None or serie < 3:
        return serie
    return max(2, round(serie * (1 - PROGI["ciecie_serii"])))


# --- dane z bazy -------------------------------------------------------------
def _polacz() -> sqlite3.Connection:
    return sqlite3.connect(baza.SCIEZKA_BAZY)


def oceny_dni(dzis: date, ile_dni: int = 5) -> tuple[dict[date, bool | None], dict]:
    """Oceny ostatnich dni (od `dzis` wstecz) i szczegóły dzisiejszego dnia (do tekstu rekomendacji).
    Dzień bierzemy z Garmina, a gdy go tam nie ma, z ręcznego dziennika."""
    from karty import oblicz_gotowosc   # lokalnie, żeby moduł nie ciągnął całego interfejsu przy imporcie

    oceny: dict[date, bool | None] = {}
    szczegoly: dict = {}
    with closing(_polacz()) as db:
        try:
            garmin = pd.read_sql_query("SELECT Data, Wynik_snu, Czas_snu, RHR FROM garmin_dziennie ORDER BY Data", db)
        except (sqlite3.OperationalError, pd.errors.DatabaseError):
            garmin = pd.DataFrame(columns=["Data", "Wynik_snu", "Czas_snu", "RHR"])
        try:
            reczny = pd.read_sql_query("SELECT Data, Sen_godz, Energia FROM dziennik_reczny", db)
        except (sqlite3.OperationalError, pd.errors.DatabaseError):
            reczny = pd.DataFrame(columns=["Data", "Sen_godz", "Energia"])
    garmin = garmin.set_index("Data") if not garmin.empty else garmin
    reczny = reczny.set_index("Data") if not reczny.empty else reczny
    rhr_wszystkie = garmin["RHR"].dropna() if not garmin.empty else pd.Series(dtype=float)

    for i in range(ile_dni):
        dzien = dzis - timedelta(days=i)
        klucz = dzien.isoformat()
        ocena, info = None, {}
        if not garmin.empty and klucz in garmin.index:
            w = garmin.loc[klucz]
            inne = rhr_wszystkie[rhr_wszystkie.index != klucz]
            srednia = float(inne.mean()) if len(inne) >= 3 else None
            czas = w["Czas_snu"]
            g = oblicz_gotowosc(None if pd.isna(czas) else float(czas), None if pd.isna(w["RHR"]) else float(w["RHR"]), srednia)
            ocena = ocena_dnia_garmin(w["Wynik_snu"], g["procent"])
            info = {"zrodlo": "garmin", "wynik_snu": w["Wynik_snu"], "gotowosc": g["procent"]}
        if ocena is None and not reczny.empty and klucz in reczny.index:
            r = reczny.loc[klucz]
            ocena = ocena_dnia_reczna(r["Sen_godz"], r["Energia"])
            info = {"zrodlo": "reczny", "sen_godz": r["Sen_godz"], "energia": r["Energia"]}
        oceny[dzien] = ocena
        if i == 0:
            szczegoly = info
    return oceny, szczegoly


def opis_regeneracji(poziom: str, dni: int, info: dict) -> str:
    """Jedno zdanie z powodem rekomendacji."""
    if info.get("zrodlo") == "garmin":
        dane = f"wynik snu {int(info['wynik_snu'])}/100, gotowość {int(info['gotowosc'])}%"
    else:
        dane = f"sen {info['sen_godz']:g} h, energia {int(info['energia'])}/5"
    if poziom == "odpoczynek":
        return (f"{dni}. dzień z rzędu słabej regeneracji ({dane}). Proponuję dzień odpoczynku "
                f"albo lekki spacer czy spokojne cardio.")
    return (f"Słaba regeneracja dziś ({dane}). Proponuję lżejszy trening: około 20% mniej serii "
            f"(np. 4 → 3), ciężary bez zmian.")


def _typy_cwiczen(db: sqlite3.Connection) -> dict[str, str | None]:
    """Nazwa ćwiczenia -> typ (wielostawowe/izolowane); gdy w bazie brak, rozpoznajemy po nazwie i partii."""
    from cwiczenia_meta import typ_cwiczenia
    try:
        wiersze = db.execute("SELECT Nazwa, Partia, Typ FROM cwiczenia").fetchall()
    except sqlite3.OperationalError:
        wiersze = [(n, p, None) for n, p in db.execute("SELECT Nazwa, Partia FROM cwiczenia").fetchall()]
    return {n: (t or typ_cwiczenia(n, p)) for n, p, t in wiersze}


def obciazenie_partii(dzien: date) -> dict[str, dict]:
    """Partie, które w podanym dniu mocno pracowały: {partia: {'serie': n, 'rpe': średnie lub None}}."""
    klucz = dzien.isoformat()
    seria_sql = ",".join("?" * len(JEDNOSTKI_POWT))
    with closing(_polacz()) as db:
        try:
            serie = db.execute(
                f"SELECT w.Cwiczenie, SUM(COALESCE(w.Serie, 1)) FROM wpisy_cwiczen w JOIN sesje s ON s.id = w.Sesja_id "
                f"WHERE substr(s.Data, 1, 10) = ? AND COALESCE(w.Jednostka, 'powt.') IN ({seria_sql}) GROUP BY w.Cwiczenie",
                (klucz, *JEDNOSTKI_POWT),
            ).fetchall()
            wagi = wagi_cwiczen(db)
            typy = _typy_cwiczen(db)
        except sqlite3.OperationalError:
            return {}
        try:
            rpe = db.execute(
                f"SELECT x.Cwiczenie, x.RPE FROM serie_wykonane x JOIN sesje s ON s.id = x.Sesja_id "
                f"WHERE substr(s.Data, 1, 10) = ? AND x.RPE IS NOT NULL AND COALESCE(x.Rozgrzewka, 0) = 0 "
                f"AND COALESCE(x.Jednostka, 'powt.') IN ({seria_sql})",
                (klucz, *JEDNOSTKI_POWT),
            ).fetchall()
        except sqlite3.OperationalError:
            rpe = []
    # Seria liczy się za 1 do partii głównej i za 0,5 do każdej dodatkowej. Części pleców i barków zostają osobno
    # (np. po przysiadach i RDL zmęczone są plecy dolne, a dzień „pull” obciąża plecy szerokie i górne)
    suma: dict[str, float] = {}
    wielostawowe: dict[str, float] = {}
    for cw, n in serie:
        for p, waga in (wagi.get(cw) or {"Inne": 1.0}).items():
            suma[p] = suma.get(p, 0) + int(n or 0) * waga
            if typy.get(cw) != IZOLOWANE:      # ćwiczenie bez znanego typu liczymy ostrożnie jak wielostawowe
                wielostawowe[p] = wielostawowe.get(p, 0) + int(n or 0) * waga
    rpe_partii: dict[str, list[int]] = {}
    for cw, r in rpe:
        glowna = next(iter(wagi.get(cw) or {"Inne": 1.0}))     # RPE dotyczy partii głównej ćwiczenia
        rpe_partii.setdefault(glowna, []).append(int(r))
    wynik = {}
    for p, n in suma.items():
        if p in PARTIE_NEUTRALNE:
            continue
        srednie = sum(rpe_partii[p]) / len(rpe_partii[p]) if rpe_partii.get(p) else None
        mocno = (wielostawowe.get(p, 0) >= PROGI["serie_wielostawowe"] or n >= PROGI["serie_partii"]
                 or (n >= PROGI["serie_partii_rpe"] and srednie is not None and srednie >= PROGI["rpe_partii"]))
        if mocno:
            wynik[p] = {"serie": n, "rpe": srednie}
    return dict(sorted(wynik.items(), key=lambda x: -x[1]["serie"]))   # od najmocniej obciążonej


def partie_presetu(preset_id: int) -> dict[str, float]:
    """Serie robocze presetu rozłożone na partie z wagami 1 i 0,5 (bez dodatków i partii neutralnych)."""
    from presety import wczytaj_cwiczenia_presetu
    dane = wczytaj_cwiczenia_presetu(preset_id)
    with closing(_polacz()) as db:
        wagi = wagi_cwiczen(db)
    wynik: dict[str, float] = {}
    for _, w in dane.iterrows():
        if w["Rola"] == "Dodatek":
            continue
        if w["Jednostka"] not in JEDNOSTKI_POWT:
            continue
        for p, waga in (wagi.get(w["Cwiczenie"]) or {"Inne": 1.0}).items():
            if p not in PARTIE_NEUTRALNE:
                wynik[p] = wynik.get(p, 0) + int(w["Serie"] or 1) * waga
    return wynik


def udzial_kolizji(partie: dict[str, float], obciazone) -> float:
    """Jaka część serii presetu wypada na partie, które wczoraj mocno pracowały (0-1)."""
    razem = sum(partie.values())
    return sum(n for p, n in partie.items() if p in obciazone) / razem if razem else 0.0


def kiedy_ostatnio(nazwa_presetu: str) -> str | None:
    with closing(_polacz()) as db:
        try:
            w = db.execute("SELECT MAX(substr(Data, 1, 10)) FROM sesje WHERE Typ_treningu = ?", (nazwa_presetu,)).fetchone()
        except sqlite3.OperationalError:
            return None
    return w[0] if w and w[0] else None


KATEGORIE_POZA_PROPOZYCJA = {"Sport", "Całe ciało", *SPORTY}


def _poza_propozycja(nazwa: str, kategoria: str | None) -> bool:
    """Skróty (np. „30 min”), treningi sportowe i całe ciało nie są podpowiadane w zastępstwie zwykłego treningu partii."""
    return (kategoria or "") in KATEGORIE_POZA_PROPOZYCJA or bool(re.search(r"\b\d+ min\b", nazwa or ""))


def propozycja_partii(dzis: date, wybrany_preset: str | None) -> dict | None:
    """Gdy wybrany preset mocno obciąża partie z wczoraj, zwraca {'obciazone', 'preset_koliduje', 'propozycja', 'partie_propozycji'}.
    Gdy nie koliduje (albo wczoraj nic mocno nie pracowało), None."""
    from presety import lista_presetow

    obciazone = obciazenie_partii(dzis - timedelta(days=1))
    if not obciazone or not wybrany_preset:
        return None
    lista = lista_presetow()
    wiersz = lista[lista["Nazwa"] == wybrany_preset]
    if wiersz.empty:
        return None
    if udzial_kolizji(partie_presetu(int(wiersz.iloc[0]["id"])), obciazone) < PROGI["kolizja_presetu"]:
        return None
    kandydaci = []
    for _, p in lista.iterrows():
        if p["Nazwa"] == wybrany_preset:
            continue
        if _poza_propozycja(p["Nazwa"], p["Kategoria"]):
            continue
        partie = partie_presetu(int(p["id"]))
        if not partie:                     # sam cardio i dodatki: nie proponujemy w zastępstwie treningu siłowego
            continue
        if udzial_kolizji(partie, obciazone) <= PROGI["wolny_preset"]:
            kandydaci.append((kiedy_ostatnio(p["Nazwa"]) or "", p["Nazwa"], partie))
    kandydaci.sort(key=lambda k: (k[0], k[1]))   # najdawniej robiony (albo nigdy) pierwszy
    wynik = {"obciazone": obciazone, "preset_koliduje": True, "propozycja": None, "partie_propozycji": [], "ostatnio": None}
    if kandydaci:
        data, nazwa, partie = kandydaci[0]
        wynik.update(propozycja=nazwa, partie_propozycji=sorted(partie, key=partie.get, reverse=True), ostatnio=data or None)
    return wynik


def serie_pl(n: float) -> str:
    """„1 seria”, „3 serie”, „10 serii” (polska odmiana)."""
    n = int(n + 0.5)      # 4,5 serii to „5 serii” (zaokrąglamy połówki w górę)
    if n == 1:
        return "1 seria"
    return f"{n} serie" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else f"{n} serii"


def karta_regeneracji(poziom: str, dni: int, info: dict, na_starcie: bool = False) -> dict:
    """Rekomendacja regeneracji do pokazania w karcie: {'tytul', 'linie'} (krótko i po ludzku)."""
    if info.get("zrodlo") == "garmin":
        dane = f"wynik snu {int(info['wynik_snu'])}/100, gotowość {int(info['gotowosc'])}%"
    else:
        dane = f"sen {info['sen_godz']:g} h, energia {int(info['energia'])}/5"
    if poziom == "odpoczynek":
        return {"tytul": "Dziś odpoczynek",
                "linie": [f"{dni}. dzień z rzędu słabej regeneracji ({dane}).", "Zrób wolne albo lekki spacer czy spokojne cardio."]}
    linie = [f"Słaba regeneracja ({dane}).", "Zrób około 20% mniej serii (np. 4 → 3), ciężary bez zmian."]
    if na_starcie:
        linie.append("Włączysz to w Treningi → Rozpocznij trening.")
    return {"tytul": "Dziś lżejszy trening", "linie": linie}


def _nazwy_w_tytule(partie: list[str]) -> list[str]:
    """Do tytułu karty: gdy obciążone są co najmniej dwie części plecy albo barków, piszemy po prostu „Plecy”/„Barki”."""
    wynik: list[str] = []
    for p in partie:
        nazwa = rodzina(p) if sum(1 for q in partie if rodzina(q) == rodzina(p)) > 1 else p
        if nazwa not in wynik:
            wynik.append(nazwa)
    return wynik


def karta_partii(wynik: dict, wybrany: str, na_starcie: bool = False) -> dict:
    """Rekomendacja partii do pokazania w karcie: {'tytul', 'linie'}."""
    czesci = []
    for p, d in wynik["obciazone"].items():
        opis = f"{p}: {serie_pl(d['serie'])}"
        if d["rpe"] is not None and d["rpe"] >= PROGI["rpe_partii"]:
            opis += f", na granicy sił (RPE {d['rpe']:.0f})" if d["rpe"] >= 9.5 else f", bardzo ciężko (RPE {d['rpe']:.0f})"
        czesci.append(opis)
    linie = ["Wczoraj mocno pracowały: " + "; ".join(czesci) + "."]
    if wynik["propozycja"]:
        linie.append(f"Lepszy wybór: **{wynik['propozycja']}** ({', '.join(wynik['partie_propozycji'])}).")
        if na_starcie:
            linie.append("Wybierzesz go w Treningi → Rozpocznij trening.")
    else:
        linie.append("Dziś lepiej wybrać trening bez tych partii.")
    return {"tytul": "Daj odpocząć: " + ", ".join(_nazwy_w_tytule(list(wynik["obciazone"]))), "linie": linie}


def trening_dzis_zapisany(dzis: date) -> bool:
    """Czy dziś jest już zapisany trening (wtedy rekomendacje „na dziś” na Starcie nie mają sensu)."""
    try:
        with closing(_polacz()) as db:
            return db.execute("SELECT 1 FROM sesje WHERE Data = ? LIMIT 1", (dzis.isoformat(),)).fetchone() is not None
    except sqlite3.Error:
        return False


def opis_partii(wynik: dict, wybrany: str) -> str:
    wczoraj = ", ".join(f"{p} ({d['serie']} serii" + (f", RPE {d['rpe']:.0f}" if d["rpe"] is not None and d["rpe"] >= PROGI["rpe_partii"] else "") + ")"
                        for p, d in wynik["obciazone"].items())
    tekst = f"Wczoraj mocno pracowały: {wczoraj}."
    if wynik["propozycja"]:
        tekst += f" Proponuję trening z innymi partiami: {wynik['propozycja']} ({', '.join(wynik['partie_propozycji'])})."
    else:
        tekst += " Dziś lepiej wybrać trening bez tych partii."
    return tekst


def rekomendacje_na_dzis(dzis: date, wybrany_preset: str | None) -> dict:
    """Wszystko dla ekranu startu: {'regeneracja': {...} | None, 'partie': {...} | None, 'status': 'ok' | 'slaba' | 'brak_danych'}.
    Status mówi, czy mamy dzisiejsze dane o regeneracji (żeby cisza nie znaczyła „coś nie działa”). Błędy nie blokują ekranu."""
    wynik = {"regeneracja": None, "partie": None, "status": "brak_danych"}
    try:
        oceny, info = oceny_dni(dzis)
        if oceny.get(dzis) is not None:
            wynik["status"] = "slaba" if oceny[dzis] else "ok"
        poziom = poziom_regeneracji(oceny, dzis)
        if poziom:
            dni = ile_slabych_dni_z_rzedu(oceny, dzis)
            wynik["regeneracja"] = {"poziom": poziom, "dni": dni, "opis": opis_regeneracji(poziom, dni, info),
                                    "karta": karta_regeneracji(poziom, dni, info), "karta_start": karta_regeneracji(poziom, dni, info, True)}
    except Exception:
        pass
    try:
        if not wynik["regeneracja"] or wynik["regeneracja"]["poziom"] != "odpoczynek":
            p = propozycja_partii(dzis, wybrany_preset)
            if p:
                p["opis"] = opis_partii(p, wybrany_preset)
                p["karta"], p["karta_start"] = karta_partii(p, wybrany_preset), karta_partii(p, wybrany_preset, True)
                wynik["partie"] = p
    except Exception:
        pass
    return wynik
