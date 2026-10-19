"""Prowadzony trening: seria po serii, licznik przerwy i zapis do bazy.

Moduł nie zakłada żadnej dyscypliny: ćwiczenia, jednostki (powtórzenia, sekundy, metry)
i długości przerw pochodzą z presetu albo z Twojej bazy ćwiczeń.

Stan trwającego treningu jest na bieżąco zapisywany w tabeli trening_w_toku,
więc odświeżenie strony albo zamknięcie karty niczego nie gubi.
Część "logika" (na górze) nie używa Streamlita i da się ją testować osobno.
"""
from __future__ import annotations

import html
import json
import math
import sqlite3
from contextlib import closing
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

import baza
import powiadomienia
from karty import (
    KOLOR_KARTY, KOLOR_OBRAMOWANIA, KOLOR_PRZYGASZONY, KOLOR_TEKSTU, KOLOR_TLA_PIERSCIENIA,
    CZERWONY, NIEBIESKI, POMARANCZOWY, ZIELONY,
    _naglowek_karty, _tlo_karty,
)
from motywy import v as _kolor_motywu

KOLOR_PRZERWY = _kolor_motywu("przerwa")     # odliczanie przerwy
KOLOR_SERII = _kolor_motywu("serie")         # licznik serii

# ---------------------------------------------------------------
# Ustawienia
# ---------------------------------------------------------------
KROK_CIEZARU = 2.5                       # o ile proponujemy podnieść ciężar
PRZERWA_GLOWNE = 120                     # sekundy przerwy po ćwiczeniu głównym
PRZERWA_DODATEK = 60                     # sekundy przerwy po dodatku i ćwiczeniach na czas/dystans
PRZERWA_ROZGRZEWKA = 60                  # sekundy przerwy po serii rozgrzewkowej
SCHEMAT_ROZGRZEWKI = ((0.5, 5), (0.7, 3), (0.85, 1))   # (część ciężaru roboczego, powtórzenia)
OPCJE_PRZERWY = {"Auto": None, "60 s": 60, "90 s": 90, "2 min": 120, "3 min": 180, "Wył.": 0}
OPCJE_RPE = list(range(1, 11))


def rzad_w_jednej_linii(klucz: str) -> None:
    """Rząd przycisków (segmenty, pigułki) o danym kluczu w jednej linii: małe wcięcia, napisy nigdy nie są ucinane
    (przyciski mają szerokość napisu i rozciągają się na wolne miejsce), a gdy rząd jest za szeroki, przewija się w bok."""
    st.markdown(
        f"<style>.st-key-{klucz} [data-testid='stButtonGroup']{{flex-wrap:nowrap !important;gap:4px !important;"
        f"overflow-x:auto;scrollbar-width:none;}}"
        f".st-key-{klucz} [data-testid='stButtonGroup']::-webkit-scrollbar{{display:none;}}"
        f".st-key-{klucz} button{{padding:0.3rem 0.45rem !important;min-height:0 !important;white-space:nowrap;"
        f"flex:1 0 auto !important;overflow:visible !important;}}"
        f".st-key-{klucz} button p{{font-size:0.85rem !important;white-space:nowrap !important;overflow:visible !important;"
        f"text-overflow:clip !important;}}</style>",
        unsafe_allow_html=True,
    )
JEDNOSTKI_POWTORZEN = ("powt.", "powt./nogę", "powt./stronę")
# Wybór jednostki przy dodawaniu i zamianie ćwiczenia (None = ustal automatycznie z historii, a bez historii: powtórzenia)
JEDNOSTKI_WYBOR = {
    "Automatycznie": None, "Powtórzenia": "powt.", "Powtórzenia na nogę": "powt./nogę",
    "Powtórzenia na stronę": "powt./stronę", "Czas (sekundy)": "s", "Czas (minuty)": "min", "Dystans (metry)": "m",
}
BRAK_RODZAJU = "— bez presetu —"
# Jednostka dla ćwiczeń, które nie mają jeszcze historii (poza tym: partia „Cardio” = minuty, reszta = powtórzenia)
JEDNOSTKI_DOMYSLNE = {
    "Deska (plank)": "s", "Plank boczny": "s", "Wiszenie na drążku": "s",
    "Pływanie": "m", "Spacer farmera (obie ręce)": "m", "Spacer farmera jednorącz": "m",
}


# ===============================================================
# CZĘŚĆ 1: LOGIKA (bez Streamlita)
# ===============================================================
def _polacz() -> sqlite3.Connection:
    return sqlite3.connect(baza.SCIEZKA_BAZY)


_przygotowane: set[str] = set()


def przygotuj_tabele() -> None:
    """Tworzy tabele pomocnicze i dokłada brakujące kolumny (stare dane zostają)."""
    sciezka = str(baza.SCIEZKA_BAZY)
    if sciezka in _przygotowane:
        return
    with closing(_polacz()) as db:
        db.execute("CREATE TABLE IF NOT EXISTS trening_w_toku (id INTEGER PRIMARY KEY CHECK (id = 1), Dane TEXT NOT NULL)")
        db.execute(
            "CREATE TABLE IF NOT EXISTS serie_wykonane ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "Sesja_id INTEGER NOT NULL, Kolejnosc INTEGER, Cwiczenie TEXT NOT NULL, "
            "Nr_serii INTEGER, Ciezar REAL, Powtorzenia INTEGER, RPE INTEGER, Jednostka TEXT)"
        )
        db.execute("CREATE TABLE IF NOT EXISTS ustawienia (Klucz TEXT PRIMARY KEY, Wartosc TEXT)")
        for tabela, nowe in (("sesje", {"Czas_min": "INTEGER", "Preset": "TEXT"}),
                             ("wpisy_cwiczen", {"Jednostka": "TEXT"}),
                             ("serie_wykonane", {"Rozgrzewka": "INTEGER"}),
                             ("cwiczenia", {"Notatka": "TEXT"})):
            istniejace = {w[1] for w in db.execute(f"PRAGMA table_info({tabela})")}
            if not istniejace:
                continue   # tabela powstanie w baza.przygotuj_baze()
            for nazwa, typ in nowe.items():
                if nazwa not in istniejace:
                    db.execute(f"ALTER TABLE {tabela} ADD COLUMN {nazwa} {typ}")
        # Jednorazowo (15.10): bieganie z 12.10 zapisane jako „powt.” to minuty; ćwiczenie trafia do partii Cardio
        if not db.execute("SELECT 1 FROM ustawienia WHERE Klucz = 'migracja_bieganie_min'").fetchone():
            for tabela in ("wpisy_cwiczen", "serie_wykonane"):
                if {w[1] for w in db.execute(f"PRAGMA table_info({tabela})")} >= {"Cwiczenie", "Jednostka"}:
                    db.execute(f"UPDATE {tabela} SET Jednostka = 'min' WHERE Cwiczenie = 'Bieganie na bieżni' AND Jednostka = 'powt.'")
            if db.execute("SELECT 1 FROM sqlite_master WHERE name = 'cwiczenia'").fetchone():
                db.execute("UPDATE cwiczenia SET Partia = 'Cardio' WHERE Nazwa = 'Bieganie na bieżni' AND Partia = 'Inne'")
            db.execute("INSERT OR REPLACE INTO ustawienia (Klucz, Wartosc) VALUES ('migracja_bieganie_min', '1')")
        db.commit()
    _przygotowane.add(sciezka)


def wczytaj_stan() -> dict | None:
    """Trwający trening z bazy (albo None, gdy żaden nie trwa)."""
    przygotuj_tabele()
    with closing(_polacz()) as db:
        wiersz = db.execute("SELECT Dane FROM trening_w_toku WHERE id = 1").fetchone()
    if not wiersz:
        return None
    try:
        return json.loads(wiersz[0])
    except ValueError:
        return None


def zapisz_stan(stan: dict | None) -> None:
    """Zapisuje trwający trening w bazie (None kasuje)."""
    przygotuj_tabele()
    with closing(_polacz()) as db:
        if stan is None:
            db.execute("DELETE FROM trening_w_toku WHERE id = 1")
        else:
            db.execute("INSERT OR REPLACE INTO trening_w_toku (id, Dane) VALUES (1, ?)", (json.dumps(stan, ensure_ascii=False),))
        db.commit()
    # budzik „koniec przerwy” (push); każda zmiana przerwy (seria, +30 s, Pomiń, wyłączenie) przechodzi przez zapis stanu
    powiadomienia.synchronizuj_przerwe(stan.get("przerwa_do") if stan else None, powiadomienia_przerwy_wlaczone())


def wczytaj_ustawienie(klucz: str, domyslna: str = "") -> str:
    """Zapamiętane ustawienie użytkownika (np. długość przerwy) albo wartość domyślna."""
    przygotuj_tabele()
    with closing(_polacz()) as db:
        w = db.execute("SELECT Wartosc FROM ustawienia WHERE Klucz = ?", (klucz,)).fetchone()
    return w[0] if w and w[0] is not None else domyslna


def powiadomienia_przerwy_wlaczone() -> bool:
    """Czy wysyłać push o końcu przerwy (domyślnie tak, o ile powiadomienia są skonfigurowane)."""
    try:
        return wczytaj_ustawienie("push_przerwa", "1") != "0"
    except Exception:
        return True


def zapisz_ustawienie(klucz: str, wartosc: str) -> None:
    przygotuj_tabele()
    with closing(_polacz()) as db:
        db.execute("INSERT INTO ustawienia (Klucz, Wartosc) VALUES (?, ?) "
                   "ON CONFLICT(Klucz) DO UPDATE SET Wartosc = excluded.Wartosc", (klucz, wartosc))
        db.commit()


def _iso(t: datetime) -> str:
    return t.isoformat(timespec="seconds")


def _tekst(v) -> str:
    return "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v).strip()


def _liczba_lub_none(v) -> int | None:
    try:
        return None if v is None or pd.isna(v) else int(v)
    except (TypeError, ValueError):
        return None


def nowe_cwiczenie(nazwa: str, rola: str = "Główne", serie_plan: int | None = 3, powt_od: int | None = None,
                   powt_do: int | None = None, jednostka: str = "powt.", wskazowka: str = "",
                   alternatywa: str = "") -> dict:
    return {
        "nazwa": nazwa, "rola": rola or "Główne", "serie_plan": int(serie_plan or 3),
        "powt_od": powt_od, "powt_do": powt_do, "jednostka": jednostka or "powt.",
        "wskazowka": wskazowka or "", "alternatywa": alternatywa or "", "serie": [],
    }


def cwiczenia_z_presetu(dane: pd.DataFrame) -> list[dict]:
    """Zamienia tabelę ćwiczeń presetu na listę ćwiczeń treningu."""
    wynik = []
    for _, w in dane.iterrows():
        wynik.append(nowe_cwiczenie(
            _tekst(w["Cwiczenie"]), _tekst(w.get("Rola")) or "Główne", _liczba_lub_none(w.get("Serie")),
            _liczba_lub_none(w.get("Powt_od")), _liczba_lub_none(w.get("Powt_do")),
            _tekst(w.get("Jednostka")) or "powt.", _tekst(w.get("Wskazowka")), _tekst(w.get("Alternatywa")),
        ))
    return [c for c in wynik if c["nazwa"]]


def nowy_stan(nazwa: str, typ: str, cwiczenia: list[dict], preset_id: int | None = None,
              teraz: datetime | None = None, przerwa: str = "Auto") -> dict:
    teraz = teraz or datetime.now()
    return {
        "start": _iso(teraz), "data": teraz.date().isoformat(), "nazwa": nazwa, "typ": typ or "",
        "preset_id": preset_id, "cwiczenia": list(cwiczenia), "biezace": 0,
        "przerwa_do": None, "przerwa_dl": 0, "przerwa": przerwa if przerwa in OPCJE_PRZERWY else "Auto",
    }


def jednostka_powtorzen(jednostka: str) -> bool:
    return (jednostka or "powt.") in JEDNOSTKI_POWTORZEN


def dlugosc_przerwy(cwiczenie: dict, ustawienie: int | None = None) -> int:
    """Sekundy przerwy po serii: ustawienie użytkownika albo automat (główne dłużej, dodatki krócej)."""
    if ustawienie is not None:
        return int(ustawienie)
    if jednostka_powtorzen(cwiczenie.get("jednostka")) and cwiczenie.get("rola") != "Dodatek":
        return PRZERWA_GLOWNE
    return PRZERWA_DODATEK


def serie_robocze(c: dict) -> list[dict]:
    """Serie bez rozgrzewkowych: tylko one liczą się do planu, objętości, rekordów i historii."""
    return [s for s in c["serie"] if not s.get("rozgrz")]


def propozycja_rozgrzewki(ciezar_roboczy: float | None, minimum: float = 40.0) -> list[tuple[float, int]]:
    """Rozgrzewka z ciężaru roboczego, np. 80 kg: 40 × 5, 55 × 3, 67,5 × 1. Poniżej `minimum` kg nie proponujemy."""
    if not ciezar_roboczy or ciezar_roboczy < minimum:
        return []
    kroki: list[tuple[float, int]] = []
    for udzial, powt in SCHEMAT_ROZGRZEWKI:
        kg = round(ciezar_roboczy * udzial / KROK_CIEZARU) * KROK_CIEZARU
        if 10 <= kg < ciezar_roboczy and (not kroki or kg > kroki[-1][0]):
            kroki.append((float(kg), powt))
    return kroki


def dodaj_serie(stan: dict, nr: int, ciezar: float, powt: int, rpe: int | None = None,
                przerwa: int | None = None, teraz: datetime | None = None, rozgrzewka: bool = False) -> None:
    """Dopisuje serię do ćwiczenia nr i uruchamia licznik przerwy (poza ostatnią serią całego treningu).
    Seria rozgrzewkowa nie liczy się do planu i ma krótką przerwę (albo żadną, gdy przerwy są wyłączone)."""
    teraz = teraz or datetime.now()
    c = stan["cwiczenia"][nr]
    seria = {"ciezar": float(ciezar or 0), "powt": int(powt), "rpe": rpe}
    if rozgrzewka:
        seria["rozgrz"] = True
        seria["rpe"] = None
    c["serie"].append(seria)
    ostatnia_seria_treningu = (not rozgrzewka and nr == len(stan["cwiczenia"]) - 1
                               and len(serie_robocze(c)) >= c["serie_plan"])
    if rozgrzewka:
        sekundy = 0 if przerwa == 0 else min(przerwa or PRZERWA_ROZGRZEWKA, PRZERWA_ROZGRZEWKA)
    else:
        sekundy = 0 if ostatnia_seria_treningu else dlugosc_przerwy(c, przerwa)
    if sekundy > 0:
        stan["przerwa_do"] = _iso(teraz + timedelta(seconds=sekundy))
        stan["przerwa_dl"] = sekundy
    else:
        stan["przerwa_do"], stan["przerwa_dl"] = None, 0


def cofnij_serie(stan: dict, nr: int) -> bool:
    c = stan["cwiczenia"][nr]
    if not c["serie"]:
        return False
    c["serie"].pop()
    stan["przerwa_do"], stan["przerwa_dl"] = None, 0
    return True


def przerwa_pozostalo(stan: dict, teraz: datetime | None = None) -> int | None:
    """Ile sekund przerwy zostało (0 = skończona). None = żadna przerwa nie trwa."""
    if not stan.get("przerwa_do"):
        return None
    teraz = teraz or datetime.now()
    zostalo = (datetime.fromisoformat(stan["przerwa_do"]) - teraz).total_seconds()
    return max(0, math.ceil(zostalo))


def przedluz_przerwe(stan: dict, sekundy: int, teraz: datetime | None = None) -> None:
    teraz = teraz or datetime.now()
    zostalo = przerwa_pozostalo(stan, teraz)
    if zostalo:
        stan["przerwa_do"] = _iso(datetime.fromisoformat(stan["przerwa_do"]) + timedelta(seconds=sekundy))
        stan["przerwa_dl"] = int(stan.get("przerwa_dl") or 0) + sekundy
    else:
        stan["przerwa_do"] = _iso(teraz + timedelta(seconds=sekundy))
        stan["przerwa_dl"] = sekundy


def pomin_przerwe(stan: dict) -> None:
    stan["przerwa_do"], stan["przerwa_dl"] = None, 0


def ustawienie_przerwy(stan: dict) -> int | None:
    """Wybrana długość przerwy w sekundach (None = automat, 0 = przerwy wyłączone)."""
    return OPCJE_PRZERWY.get(stan.get("przerwa") or "Auto")


def przerwy_wylaczone(stan: dict) -> bool:
    return stan.get("przerwa") == "Wył."


def ustaw_przerwe(stan: dict, opcja: str | None) -> None:
    """Zmienia długość przerwy w trwającym treningu. Wyłączenie przerywa też odliczanie, które właśnie trwa."""
    opcja = opcja if opcja in OPCJE_PRZERWY else "Auto"
    if opcja != "Wył." and stan.get("przerwa") not in (None, "Wył."):
        stan["przerwa_poprz"] = stan["przerwa"]
    stan["przerwa"] = opcja
    if opcja == "Wył.":
        pomin_przerwe(stan)


def przelacz_przerwy(stan: dict) -> None:
    """Jedno stuknięcie: wyłącza przerwy albo wraca do poprzedniej długości (domyślnie Auto)."""
    if przerwy_wylaczone(stan):
        ustaw_przerwe(stan, stan.get("przerwa_poprz") or "Auto")
    else:
        stan["przerwa_poprz"] = stan.get("przerwa") or "Auto"
        ustaw_przerwe(stan, "Wył.")


def usun_cwiczenie(stan: dict, nr: int, z_seriami: bool = False) -> bool:
    """Usuwa ćwiczenie. Bez z_seriami=True odmawia, gdy ćwiczenie ma już zapisane serie."""
    if stan["cwiczenia"][nr]["serie"] and not z_seriami:
        return False
    del stan["cwiczenia"][nr]
    b = stan["biezace"] - 1 if nr < stan["biezace"] else stan["biezace"]
    stan["biezace"] = max(0, min(b, len(stan["cwiczenia"]) - 1))
    return True


def przesun_na_koniec(stan: dict, nr: int) -> bool:
    """„Zrób później”: przenosi ćwiczenie na koniec treningu (np. gdy sprzęt jest zajęty). Ekran zostaje przy tym samym
    ćwiczeniu, a gdy przenosisz bieżące, wskakuje następne."""
    if nr >= len(stan["cwiczenia"]) - 1:
        return False
    stan["cwiczenia"].append(stan["cwiczenia"].pop(nr))
    if stan["biezace"] > nr:
        stan["biezace"] -= 1
    return True


def dolacz_cwiczenie(stan: dict, cwiczenie: dict) -> None:
    stan["cwiczenia"].append(cwiczenie)
    stan["biezace"] = len(stan["cwiczenia"]) - 1


def jednostka_z_historii(nazwa: str) -> str | None:
    """Jednostka, w jakiej ostatnio zapisywałeś to ćwiczenie (None, gdy go jeszcze nie robiłeś)."""
    try:
        with closing(_polacz()) as db:
            w = db.execute(
                "SELECT w.Jednostka FROM wpisy_cwiczen w JOIN sesje s ON s.id = w.Sesja_id "
                "WHERE w.Cwiczenie = ? AND COALESCE(w.Jednostka, '') <> '' ORDER BY s.Data DESC, s.id DESC LIMIT 1",
                (nazwa,),
            ).fetchone()
    except sqlite3.OperationalError:
        return None
    return w[0] if w else None


# Wartość startowa pola przy ćwiczeniu bez celu i bez historii (powtórzenia: 8)
WARTOSC_STARTOWA = {"s": 30, "min": 20, "m": 100}


# Wartości startowe formularza „Dodaj trening” po fakcie: (obciążenie kg, serie, wartość na serię)
FORMULARZ_DOMYSLNE = {"powt.": (60.0, 4, 5), "s": (0.0, 3, 30), "min": (0.0, 1, 20), "m": (0.0, 3, 100)}


def jednostka_formularza(nazwa: str | None, wybor: str | None = "Automatycznie") -> str:
    """Jednostka bloku ćwiczenia w formularzu: wybrana ręcznie albo automatyczna (historia, lista znanych, partia Cardio)."""
    reczna = JEDNOSTKI_WYBOR.get(wybor or "Automatycznie")
    if reczna:
        return reczna
    return jednostka_domyslna(nazwa) if nazwa else "powt."


def domyslne_formularza(jednostka: str) -> tuple[float, int, int]:
    return FORMULARZ_DOMYSLNE["powt." if jednostka_powtorzen(jednostka) else jednostka] if (jednostka_powtorzen(jednostka) or jednostka in FORMULARZ_DOMYSLNE) else FORMULARZ_DOMYSLNE["powt."]


def ustaw_cel(c: dict, serie: int | None = None, od: int | None = None, do: int | None = None) -> None:
    """Cel ćwiczenia po dodaniu lub zamianie. Puste pole = automat: liczba serii zostaje (dla minut: 1 seria),
    a zakres powtórzeń, czasu lub dystansu zostaje taki, jaki był. „do” bez „od” oznacza jedną wartość celu."""
    if serie:
        c["serie_plan"] = max(1, int(serie))
    elif c.get("jednostka") == "min":
        c["serie_plan"] = 1
    if do and not od:
        od, do = do, None
    if od:
        c["powt_od"] = int(od)
        c["powt_do"] = int(do) if do and int(do) > int(od) else int(od)


def jednostka_domyslna(nazwa: str) -> str:
    """Jednostka nowego ćwiczenia: ostatnio zapisana, potem znana z listy, potem minuty dla cardio, a na końcu powtórzenia."""
    z_historii = jednostka_z_historii(nazwa)
    if z_historii:
        return z_historii
    if nazwa in JEDNOSTKI_DOMYSLNE:
        return JEDNOSTKI_DOMYSLNE[nazwa]
    try:
        with closing(_polacz()) as db:
            w = db.execute("SELECT Partia FROM cwiczenia WHERE Nazwa = ?", (nazwa,)).fetchone()
    except sqlite3.OperationalError:
        w = None
    return "min" if w and w[0] == "Cardio" else "powt."


def pokaz_ciezar(c: dict, wymus: bool = False) -> bool:
    """Czy przy ćwiczeniu pokazywać pole obciążenia. Powtórzenia: tak. Minuty (cardio): nie.
    Sekundy i metry (plank, spacer farmera): tylko gdy ćwiczenie miało już obciążenie albo użytkownik włączył je ręcznie."""
    jednostka = c.get("jednostka") or "powt."
    if jednostka_powtorzen(jednostka):
        return True
    if jednostka == "min":
        return False
    if wymus or any(x.get("ciezar") for x in c.get("serie", [])):
        return True
    return bool((c.get("propozycja") or {}).get("ciezar"))


def zamien_cwiczenie(stan: dict, nr: int, nazwa: str, jednostka: str | None = None) -> None:
    """Podmienia ćwiczenie nr na inne. Zostaje liczba serii i rola. Zakres powtórzeń zostaje tylko wtedy,
    gdy jednostka się nie zmienia. Wskazówka i zamiennik dotyczyły starego ćwiczenia, więc znikają.
    Zapisane już serie zostają przy ćwiczeniu (przydaje się, gdy wpisałeś serie pod złą nazwą)."""
    c = stan["cwiczenia"][nr]
    nowa_jednostka = jednostka or c["jednostka"]
    if nowa_jednostka != c["jednostka"]:
        c["powt_od"], c["powt_do"] = None, None
    c["nazwa"], c["jednostka"] = nazwa, nowa_jednostka
    c["wskazowka"], c["alternatywa"] = "", ""
    c.pop("propozycja", None)


def postep(stan: dict) -> tuple[int, int]:
    """(zrobione serie, zaplanowane serie); nadprogramowe serie podnoszą plan, żeby pasek nie przekraczał 100%."""
    zrobione = sum(len(serie_robocze(c)) for c in stan["cwiczenia"])
    plan = sum(max(c["serie_plan"], len(serie_robocze(c))) for c in stan["cwiczenia"])
    return zrobione, plan


def czas_trwania(stan: dict, teraz: datetime | None = None) -> timedelta:
    return (teraz or datetime.now()) - datetime.fromisoformat(stan["start"])


def objetosc(stan: dict) -> float:
    """Suma ciężar × powtórzenia (tylko ćwiczenia liczone w powtórzeniach)."""
    return sum(s["ciezar"] * s["powt"] for c in stan["cwiczenia"] if jednostka_powtorzen(c["jednostka"]) for s in serie_robocze(c))


def zgrupuj_serie(serie: list[dict]) -> list[dict]:
    """Kolejne identyczne serie (ten sam ciężar i powtórzenia) łączy w jeden wiersz."""
    grupy: list[dict] = []
    for s in serie:
        if grupy and grupy[-1]["ciezar"] == s["ciezar"] and grupy[-1]["powt"] == s["powt"]:
            grupy[-1]["serie"] += 1
        else:
            grupy.append({"ciezar": s["ciezar"], "powt": s["powt"], "serie": 1})
    return grupy


# --- formatowanie tekstów --------------------------------------------------
def format_kg(x: float | None) -> str:
    if x is None:
        return ""
    return f"{x:.1f}".rstrip("0").rstrip(".").replace(".", ",") if x else "0"


def format_powt(powt: int, jednostka: str) -> str:
    return str(powt) if jednostka_powtorzen(jednostka) else f"{powt} {jednostka}"


def opis_serii(grupy: list[dict], jednostka: str = "powt.") -> str:
    """Np. '3 × 5 @ 60 kg, 1 × 4 @ 60 kg'."""
    czesci = []
    for g in grupy:
        tekst = f"{g['serie']} × {format_powt(g['powt'], jednostka)}"
        if g["ciezar"]:
            tekst += f" @ {format_kg(g['ciezar'])} kg"
        czesci.append(tekst)
    return ", ".join(czesci)


def format_czasu(sekundy: float) -> str:
    sekundy = max(0, int(sekundy))
    g, reszta = divmod(sekundy, 3600)
    m, s = divmod(reszta, 60)
    return f"{g}:{m:02d}:{s:02d}" if g else f"{m:02d}:{s:02d}"


def tekst_planu(c: dict) -> str:
    od, do = c.get("powt_od"), c.get("powt_do")
    if od and do and od != do:
        zakres = f"{od}–{do}"
    else:
        zakres = str(od or do or "")
    if not zakres:
        n = c["serie_plan"]
        return f"{n} " + ("seria" if n == 1 else "serie" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else "serii")
    jednostka = c["jednostka"]
    return f"{c['serie_plan']} × {zakres} {jednostka}"


# --- historia i propozycja ciężaru ----------------------------------------
def ostatnie_serie(cwiczenie: str) -> dict | None:
    """Wiersze z ostatniego zapisanego treningu z tym ćwiczeniem (z wpisy_cwiczen)."""
    try:
        with closing(_polacz()) as db:
            sesja = db.execute(
                "SELECT s.id, s.Data FROM wpisy_cwiczen w JOIN sesje s ON s.id = w.Sesja_id "
                "WHERE w.Cwiczenie = ? ORDER BY s.Data DESC, s.id DESC LIMIT 1", (cwiczenie,),
            ).fetchone()
            if not sesja:
                return None
            wiersze = db.execute(
                "SELECT Ciezar, Serie, Powtorzenia FROM wpisy_cwiczen WHERE Sesja_id = ? AND Cwiczenie = ? ORDER BY Kolejnosc, id",
                (sesja[0], cwiczenie),
            ).fetchall()
    except sqlite3.OperationalError:
        return None
    return {"data": sesja[1], "wiersze": wiersze}


def oblicz_propozycje(wiersze: list[tuple], data: str, powt_od: int | None, powt_do: int | None,
                      serie_plan: int | None, jednostka: str = "powt.") -> dict | None:
    """Prosta reguła progresji: gdy wszystkie serie na najcięższym ciężarze doszły do górnej granicy
    zakresu powtórzeń, proponujemy +2,5 kg. W przeciwnym razie zostajemy przy tym samym ciężarze."""
    serie = []
    for ciezar, ile, powt in wiersze:
        serie += [(float(ciezar or 0), int(powt or 0))] * int(ile or 1)
    if not serie:
        return None
    szczyt = max(c for c, _ in serie)
    na_szczycie = [p for c, p in serie if c == szczyt]
    podniesc = bool(
        szczyt > 0 and jednostka_powtorzen(jednostka) and powt_do
        and min(na_szczycie) >= powt_do and len(na_szczycie) >= (serie_plan or 1)
    )
    grupy = zgrupuj_serie([{"ciezar": c, "powt": p} for c, p in serie])
    return {
        "data": data,
        "ostatnio": opis_serii(grupy, jednostka),
        "ciezar": szczyt + KROK_CIEZARU if podniesc else szczyt,
        "powt": (powt_od or na_szczycie[-1]) if podniesc else na_szczycie[-1],
        "podniesc": podniesc,
        "bazowy_ciezar": szczyt,
    }


def zaproponuj(c: dict) -> dict | None:
    ostatnie = ostatnie_serie(c["nazwa"])
    if not ostatnie:
        return None
    return oblicz_propozycje(ostatnie["wiersze"], ostatnie["data"], c.get("powt_od"), c.get("powt_do"),
                             c.get("serie_plan"), c.get("jednostka") or "powt.")


def dopelnij_propozycje(stan: dict) -> None:
    for c in stan["cwiczenia"]:
        if "propozycja" not in c:
            c["propozycja"] = zaproponuj(c)


def ostatni_trening_rodzaju(typ: str, zapas: str = "") -> dict | None:
    """Ćwiczenia z ostatniego zapisanego treningu o tej nazwie (z planem: serie i zakres powtórzeń).
    Nazwa to nazwa presetu. Gdy takiego treningu nie ma, szukamy pod starym rodzajem (`zapas`, np. 'Góra Push'),
    bo treningi sprzed zmiany mają zapisany rodzaj, a nie nazwę presetu."""
    if not typ:
        return None
    przygotuj_tabele()
    try:
        with closing(_polacz()) as db:
            sesja = None
            for etykieta in (typ, zapas):
                if not etykieta:
                    continue
                sesja = db.execute(
                    "SELECT id, Data FROM sesje WHERE Typ_treningu = ? "
                    "AND EXISTS (SELECT 1 FROM wpisy_cwiczen w WHERE w.Sesja_id = sesje.id) "
                    "ORDER BY Data DESC, id DESC LIMIT 1", (etykieta,),
                ).fetchone()
                if sesja:
                    break
            if not sesja:
                return None
            wiersze = db.execute(
                "SELECT Cwiczenie, Serie, Powtorzenia, COALESCE(Jednostka, 'powt.') FROM wpisy_cwiczen "
                "WHERE Sesja_id = ? ORDER BY Kolejnosc, id", (sesja[0],),
            ).fetchall()
    except sqlite3.OperationalError:
        return None
    zebrane: dict[str, dict] = {}
    for nazwa, serie, powt, jednostka in wiersze:
        z = zebrane.setdefault(nazwa, {"serie": 0, "powt": [], "jednostka": jednostka})
        z["serie"] += int(serie or 1)
        if powt:
            z["powt"].append(int(powt))
    cwiczenia = [
        nowe_cwiczenie(nazwa, "Główne", z["serie"], min(z["powt"]) if z["powt"] else None,
                       max(z["powt"]) if z["powt"] else None, z["jednostka"])
        for nazwa, z in zebrane.items()
    ]
    return {"data": sesja[1], "cwiczenia": cwiczenia}


def pasujace_presety(lista: pd.DataFrame, typ: str) -> tuple[pd.DataFrame, str]:
    """Presety do rodzaju treningu: dokładne dopasowanie, a gdy go brak, ta sama kategoria (pierwsze słowo, np. 'Góra')."""
    if not typ or lista.empty:
        return lista.iloc[0:0], "brak"
    dokladne = lista[lista["Typ"] == typ]
    if not dokladne.empty:
        return dokladne, "dokladne"
    kategoria = typ.split()[0].lower()
    podobne = lista[lista["Kategoria"].fillna("").str.lower() == kategoria]
    return (podobne, "kategoria") if not podobne.empty else (lista.iloc[0:0], "brak")


def preset_z_etykiety(lista: pd.DataFrame, etykieta: str | None) -> str | None:
    """Nazwa presetu odpowiadająca etykiecie z planu albo z historii: dokładna nazwa presetu, a dla starych wpisów
    (zapisanych jako rodzaj, np. 'Góra Push') pierwszy preset o takim rodzaju."""
    if not etykieta or lista.empty:
        return None
    if etykieta in set(lista["Nazwa"]):
        return etykieta
    po_rodzaju = lista[lista["Typ"] == etykieta]
    return str(po_rodzaju.iloc[0]["Nazwa"]) if not po_rodzaju.empty else None


def ostatnia_etykieta_treningu() -> str | None:
    """Nazwa (albo stary rodzaj) ostatnio zapisanego treningu, który coś nazwano."""
    try:
        with closing(_polacz()) as db:
            w = db.execute("SELECT Typ_treningu FROM sesje WHERE COALESCE(Typ_treningu, '') <> '' "
                           "ORDER BY Data DESC, id DESC LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return None
    return w[0] if w else None


def domyslny_preset(lista: pd.DataFrame, typ_planu: str | None = None) -> str | None:
    """Który preset ma być zaznaczony na starcie: z dzisiejszego planu, a gdy plan go nie wskazuje, ten ostatnio robiony."""
    return preset_z_etykiety(lista, typ_planu) or preset_z_etykiety(lista, ostatnia_etykieta_treningu())


# --- zapis gotowego treningu ----------------------------------------------
def zapisz_trening(stan: dict, komentarz: str = "", waga: float | None = None, teraz: datetime | None = None) -> int:
    """Zapisuje trening do sesje + wpisy_cwiczen (zbiorczo, jak ręczny formularz) i serie_wykonane (szczegółowo)."""
    teraz = teraz or datetime.now()
    wykonane = [c for c in stan["cwiczenia"] if c["serie"]]
    if not any(serie_robocze(c) for c in wykonane):
        raise ValueError("Nie zapisano jeszcze żadnej serii roboczej (same rozgrzewki to za mało).")
    przygotuj_tabele()
    czas_min = max(1, round(czas_trwania(stan, teraz).total_seconds() / 60))
    with closing(_polacz()) as db:
        kursor = db.execute(
            "INSERT INTO sesje (Data, Typ_treningu, Waga, Komentarz, Czas_min, Preset) VALUES (?, ?, ?, ?, ?, ?)",
            (stan["data"], stan.get("typ") or "", waga, komentarz or "", czas_min, stan.get("nazwa") or ""),
        )
        sesja_id = kursor.lastrowid
        kolejnosc = 0
        for nr, c in enumerate(wykonane, start=1):
            for g in zgrupuj_serie(serie_robocze(c)):   # rozgrzewki tylko w serie_wykonane, nie psują objętości i rekordów
                kolejnosc += 1
                db.execute(
                    "INSERT INTO wpisy_cwiczen (Sesja_id, Kolejnosc, Cwiczenie, Ciezar, Serie, Powtorzenia, Komentarz, Jednostka) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (sesja_id, kolejnosc, c["nazwa"], g["ciezar"], g["serie"], g["powt"], "", c["jednostka"]),
                )
            for i, s in enumerate(c["serie"], start=1):
                db.execute(
                    "INSERT INTO serie_wykonane (Sesja_id, Kolejnosc, Cwiczenie, Nr_serii, Ciezar, Powtorzenia, RPE, Jednostka, Rozgrzewka) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (sesja_id, nr, c["nazwa"], i, s["ciezar"], s["powt"], s.get("rpe"), c["jednostka"], 1 if s.get("rozgrz") else 0),
                )
        db.execute("DELETE FROM trening_w_toku WHERE id = 1")
        db.commit()
    powiadomienia.anuluj("przerwa")
    return sesja_id


# --- notatki do ćwiczeń ----------------------------------------------------
def wczytaj_notatke(nazwa: str) -> str:
    """Notatka przypięta do ćwiczenia (np. ustawienie maszyny). Pusta, gdy jej nie ma."""
    try:
        with closing(_polacz()) as db:
            w = db.execute("SELECT Notatka FROM cwiczenia WHERE Nazwa = ?", (nazwa,)).fetchone()
    except sqlite3.OperationalError:
        return ""
    return (w[0] or "") if w else ""


def zapisz_notatke(nazwa: str, tekst: str) -> None:
    """Zapisuje notatkę do ćwiczenia (pusty tekst ją usuwa). Ćwiczenia spoza bazy trafiają do niej z partią „Inne”."""
    przygotuj_tabele()
    tekst = (tekst or "").strip()
    with closing(_polacz()) as db:
        zmienione = db.execute("UPDATE cwiczenia SET Notatka = ? WHERE Nazwa = ?", (tekst or None, nazwa)).rowcount
        if not zmienione:
            db.execute("INSERT INTO cwiczenia (Nazwa, Partia, Notatka) VALUES (?, 'Inne', ?)", (nazwa, tekst or None))
        db.commit()


# --- zapis treningu jako preset ---------------------------------------------
def cwiczenia_stanu_do_presetu(stan: dict) -> list[dict]:
    """Ćwiczenia trwającego treningu jako wiersze presetu: liczba serii roboczych i zakres powtórzeń z tego, co zrobiłeś."""
    wynik = []
    for c in stan["cwiczenia"]:
        rob = serie_robocze(c)
        if not rob:
            continue
        powt = [s["powt"] for s in rob]
        wynik.append({"nazwa": c["nazwa"], "rola": c.get("rola") or "Główne", "serie": len(rob), "powt_od": min(powt),
                      "powt_do": max(powt), "jednostka": c["jednostka"], "wskazowka": c.get("wskazowka", ""),
                      "alternatywa": c.get("alternatywa", "")})
    return wynik


def cwiczenia_sesji_do_presetu(sesja_id: int) -> list[dict]:
    """To samo dla zapisanego już treningu (z wierszy ćwiczeń). Pięć pierwszych ćwiczeń to „Główne”, reszta „Dodatek”."""
    t = wczytaj_sesje(sesja_id)
    if t is None:
        return []
    zebrane: dict[str, dict] = {}
    for w in t["wpisy"]:
        z = zebrane.setdefault(w["Cwiczenie"], {"serie": 0, "powt": [], "jednostka": w["Jednostka"] or "powt."})
        z["serie"] += int(w["Serie"] or 1)
        if w["Powtorzenia"]:
            z["powt"].append(int(w["Powtorzenia"]))
    return [{"nazwa": n, "rola": "Główne" if i < 5 else "Dodatek", "serie": z["serie"],
             "powt_od": min(z["powt"]) if z["powt"] else None, "powt_do": max(z["powt"]) if z["powt"] else None,
             "jednostka": z["jednostka"], "wskazowka": "", "alternatywa": ""} for i, (n, z) in enumerate(zebrane.items())]


def utworz_preset(nazwa: str, cwiczenia: list[dict], kategoria: str = "Własne") -> int:
    """Dopisuje nowy preset (na końcu listy). Nazwa presetu jest też rodzajem treningu, więc musi być unikalna.
    Najwyżej pięć ćwiczeń może być „Główne”, kolejne dostają rolę „Dodatek” (tak samo jak w edytorze presetów)."""
    import presety
    nazwa = (nazwa or "").strip()
    if not nazwa:
        raise ValueError("Podaj nazwę presetu.")
    if not cwiczenia:
        raise ValueError("W tym treningu nie ma ćwiczeń z zapisanymi seriami.")
    with closing(_polacz()) as db:
        presety._utworz_tabele(db)
        if db.execute("SELECT 1 FROM presety WHERE Nazwa = ? COLLATE NOCASE", (nazwa,)).fetchone():
            raise ValueError("Preset o takiej nazwie już istnieje. Wpisz inną nazwę.")
        numer = db.execute("SELECT COALESCE(MAX(Kolejnosc), 0) FROM presety").fetchone()[0] + 1
        preset_id = db.execute("INSERT INTO presety (Nazwa, Typ, Kategoria, Cel, Kolejnosc) VALUES (?, ?, ?, ?, ?)",
                               (nazwa, nazwa, kategoria, "", numer)).lastrowid
        glowne = 0
        for kolejnosc, c in enumerate(cwiczenia, start=1):
            rola = c.get("rola") if c.get("rola") in presety.ROLE else "Główne"
            if rola == "Główne":
                glowne += 1
                if glowne > presety.MAKS_GLOWNYCH:
                    rola = "Dodatek"
            db.execute(
                "INSERT INTO presety_cwiczenia (Preset_id, Kolejnosc, Cwiczenie, Serie, Powt_od, Powt_do, Jednostka, "
                "Alternatywa, Wskazowka, Rola) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (preset_id, kolejnosc, c["nazwa"], c.get("serie"), c.get("powt_od"), c.get("powt_do"),
                 c.get("jednostka") or "powt.", c.get("alternatywa", ""), c.get("wskazowka", ""), rola))
            presety._dodaj_cwiczenie_jesli_brak(db, c["nazwa"], "Inne")
        db.commit()
    return preset_id


# --- rekordy i porównanie po treningu ---------------------------------------
def poprzedni_trening(typ: str, zapas: str = "") -> dict | None:
    """Ostatni zapisany trening o tej nazwie (preset): data, objętość i liczba serii. Do porównania po treningu."""
    if not typ:
        return None
    try:
        with closing(_polacz()) as db:
            sesja = None
            for etykieta in (typ, zapas):
                if not etykieta:
                    continue
                sesja = db.execute(
                    "SELECT id, Data FROM sesje WHERE Typ_treningu = ? "
                    "AND EXISTS (SELECT 1 FROM wpisy_cwiczen w WHERE w.Sesja_id = sesje.id) "
                    "ORDER BY Data DESC, id DESC LIMIT 1", (etykieta,)).fetchone()
                if sesja:
                    break
            if not sesja:
                return None
            wiersze = db.execute("SELECT Ciezar, Serie, Powtorzenia, COALESCE(Jednostka, 'powt.') FROM wpisy_cwiczen "
                                 "WHERE Sesja_id = ?", (sesja[0],)).fetchall()
    except sqlite3.OperationalError:
        return None
    objetosc_poprz = sum(float(c or 0) * int(s or 1) * int(p or 0) for c, s, p, j in wiersze if jednostka_powtorzen(j))
    return {"data": sesja[1], "objetosc": objetosc_poprz, "serie": sum(int(s or 1) for _, s, _, _ in wiersze)}


def rekordy_treningu(stan: dict) -> dict:
    """Rekordy osobiste i porównanie z poprzednim takim treningiem. Wołać PRZED zapisem treningu, bo porównuje z historią.
    Rekord: najcięższa seria (gdy ciężar wzrósł), szacowane 1RM (jak na stronie Postępy), a dla ćwiczeń bez ciężaru
    najwięcej powtórzeń albo najdłuższy czas. Pierwszy zapis ćwiczenia to punkt wyjścia, nie rekord."""
    from postepy import szacowane_1rm, wczytaj_wpisy
    historia = wczytaj_wpisy()
    rekordy: list[dict] = []
    for c in stan["cwiczenia"]:
        rob = serie_robocze(c)
        h = historia[(historia["Cwiczenie"] == c["nazwa"]) & (historia["Jednostka"] == c["jednostka"])] if not historia.empty else historia
        if not rob or h.empty:
            continue
        j = c["jednostka"]
        tekst = None
        if jednostka_powtorzen(j):
            kg = max(s["ciezar"] for s in rob)
            if kg > 0:
                poprz_kg = float(h["Ciezar"].max())
                najlepsza = max((s for s in rob if s["ciezar"] == kg), key=lambda s: s["powt"])
                e1rm = [x for x in (szacowane_1rm(s["ciezar"], s["powt"]) for s in rob) if x]
                poprz_e1rm = h["E1RM"].max()
                if poprz_kg > 0 and kg > poprz_kg + 0.001:
                    tekst = f"najcięższa seria {format_kg(kg)} kg × {najlepsza['powt']} (poprzednio {format_kg(poprz_kg)} kg)"
                elif e1rm and pd.notna(poprz_e1rm) and max(e1rm) > poprz_e1rm + 0.05:
                    tekst = (f"szacowane 1RM {format_kg(round(max(e1rm), 1))} kg "
                             f"(poprzednio {format_kg(round(float(poprz_e1rm), 1))} kg)")
            else:
                najwiecej = max(s["powt"] for s in rob)
                bez_ciezaru = h[h["Ciezar"] == 0]["Powt"]
                if not bez_ciezaru.empty and najwiecej > int(bez_ciezaru.max()):
                    tekst = f"najwięcej powtórzeń w serii: {najwiecej} (poprzednio {int(bez_ciezaru.max())})"
        else:
            najlepszy = max(s["powt"] for s in rob)
            if najlepszy > int(h["Powt"].max()):
                tekst = f"najdłuższy wynik {format_powt(najlepszy, j)} (poprzednio {format_powt(int(h['Powt'].max()), j)})"
        if tekst:
            rekordy.append({"cwiczenie": c["nazwa"], "tekst": tekst})

    porownanie = None
    zapas = ""
    typ = stan.get("typ") or ""
    if typ:
        try:
            from presety import lista_presetow
            lp = lista_presetow()
            zapas = str(lp[lp["Nazwa"] == typ].iloc[0]["Typ"]) if typ in set(lp["Nazwa"]) else ""
        except (ImportError, sqlite3.Error, IndexError, KeyError):
            zapas = ""
    poprz = poprzedni_trening(typ, zapas)
    if poprz:
        teraz_obj, teraz_serie = objetosc(stan), postep(stan)[0]
        proc = 100 * (teraz_obj - poprz["objetosc"]) / poprz["objetosc"] if poprz["objetosc"] and teraz_obj else None
        porownanie = {"data": poprz["data"], "objetosc": teraz_obj, "objetosc_poprz": poprz["objetosc"],
                      "proc": proc, "serie": teraz_serie, "serie_poprz": poprz["serie"]}
    return {"rekordy": rekordy, "porownanie": porownanie}


# --- partie mięśniowe ćwiczeń ------------------------------------------------
def lista_partii() -> list[str]:
    """Partie z bazy ćwiczeń (w kolejności pierwszego wystąpienia); „Inne” zawsze na końcu."""
    try:
        with closing(_polacz()) as db:
            wiersze = db.execute("SELECT Partia FROM cwiczenia WHERE COALESCE(Partia, '') <> '' ORDER BY rowid").fetchall()
    except sqlite3.OperationalError:
        wiersze = []
    wynik: list[str] = []
    for (partia,) in wiersze:
        if partia != "Inne" and partia not in wynik:
            wynik.append(partia)
    return wynik + ["Inne"]


def dopisz_cwiczenie_do_bazy(nazwa: str, partia: str | None = None) -> None:
    """Nowe ćwiczenie trafia do bazy ćwiczeń z wybraną partią (domyślnie „Inne”). Istniejącego nie zmienia."""
    with closing(_polacz()) as db:
        db.execute("INSERT OR IGNORE INTO cwiczenia (Nazwa, Partia) VALUES (?, ?)", (nazwa, partia or "Inne"))
        db.commit()


# --- ujednolicenie nazw starych treningów -------------------------------------
def plan_przemianowania() -> list[dict]:
    """Treningi, których nazwa nie jest nazwą presetu, a da się ją jednoznacznie przypisać: po zapisanej nazwie presetu
    albo po dawnym rodzaju, gdy pasuje do dokładnie jednego presetu (np. „Góra Siła”). Niejednoznaczne (np. samo „Cardio”) pomijamy."""
    from presety import lista_presetow
    lp = lista_presetow()
    nazwy = set(lp["Nazwa"])
    po_rodzaju: dict[str, list[str]] = {}
    for _, w in lp.iterrows():
        po_rodzaju.setdefault(str(w["Typ"] or ""), []).append(str(w["Nazwa"]))
    przygotuj_tabele()
    with closing(_polacz()) as db:
        wiersze = db.execute("SELECT id, Data, COALESCE(Typ_treningu, ''), COALESCE(Preset, '') FROM sesje ORDER BY Data, id").fetchall()
    wynik = []
    for sesja_id, data, typ, preset in wiersze:
        if typ in nazwy:
            continue
        nowa = preset.removesuffix(" (jak ostatnio)")
        if nowa not in nazwy:
            kandydaci = po_rodzaju.get(typ, []) if typ else []
            nowa = kandydaci[0] if len(kandydaci) == 1 else None
        if nowa:
            wynik.append({"id": sesja_id, "data": data, "stare": typ, "nowe": nowa})
    return wynik


def przemianuj_stare_treningi() -> int:
    """Zmienia nazwy treningów z `plan_przemianowania`. Przed zmianą robi kopię bazy (nie jest sprzątana automatycznie)."""
    plan = plan_przemianowania()
    if not plan:
        return 0
    kopia_bazy("przed_przemianowaniem")
    with closing(_polacz()) as db:
        db.executemany("UPDATE sesje SET Typ_treningu = ? WHERE id = ?", [(w["nowe"], w["id"]) for w in plan])
        db.commit()
    return len(plan)


# --- kopie zapasowe, usuwanie i edycja zapisanych treningów ------------------
POWODY_KOPII_AUTO = ("dzienna", "przed_edycja", "przed_usunieciem")   # tylko takie kopie sprzątamy automatycznie


def folder_kopii() -> Path:
    folder = Path(baza.SCIEZKA_BAZY).parent / "kopie"
    folder.mkdir(exist_ok=True)
    return folder


def kopia_bazy(powod: str = "reczna", zachowaj: int = 30) -> Path:
    """Spójna kopia bazy w folderze kopie/ (działa też przy włączonej aplikacji). Automatycznych kopii zostaje `zachowaj`
    najnowszych na rodzaj, a kopie ręczne i z narzedzia_bazy.py nigdy nie są kasowane."""
    cel = folder_kopii() / f"treningi_{datetime.now():%Y%m%d_%H%M%S}_{powod}.db"
    with closing(sqlite3.connect(baza.SCIEZKA_BAZY)) as zrodlo, closing(sqlite3.connect(cel)) as kopia:
        zrodlo.backup(kopia)
    if powod in POWODY_KOPII_AUTO:
        stare = sorted(folder_kopii().glob(f"treningi_*_{powod}.db"))
        for plik in stare[:-zachowaj]:
            plik.unlink(missing_ok=True)
    return cel


def kopia_dzienna() -> Path | None:
    """Raz dziennie robi kopię bazy (przy pierwszym uruchomieniu aplikacji danego dnia)."""
    try:
        if not Path(baza.SCIEZKA_BAZY).exists():
            return None
        if any(folder_kopii().glob(f"treningi_{datetime.now():%Y%m%d}_*_dzienna.db")):
            return None
        return kopia_bazy("dzienna")
    except (OSError, sqlite3.Error):
        return None


def lista_kopii() -> list[Path]:
    return sorted(folder_kopii().glob("treningi_*.db"), reverse=True)


def usun_sesje(sesja_id: int) -> bool:
    """Usuwa trening razem z ćwiczeniami i seriami. Przed usunięciem robi kopię bazy, więc pomyłkę da się cofnąć."""
    przygotuj_tabele()
    kopia_bazy("przed_usunieciem")
    with closing(_polacz()) as db:
        db.execute("DELETE FROM serie_wykonane WHERE Sesja_id = ?", (sesja_id,))
        db.execute("DELETE FROM wpisy_cwiczen WHERE Sesja_id = ?", (sesja_id,))
        usuniete = db.execute("DELETE FROM sesje WHERE id = ?", (sesja_id,)).rowcount
        db.commit()
    return usuniete > 0


def wczytaj_sesje(sesja_id: int) -> dict | None:
    """Jeden trening do edycji: dane ogólne i wiersze ćwiczeń (jeden wiersz = ćwiczenie z ciężarem, seriami i powtórzeniami)."""
    przygotuj_tabele()
    with closing(_polacz()) as db:
        db.row_factory = sqlite3.Row
        w = db.execute("SELECT id, Data, Typ_treningu, Waga, Komentarz, Czas_min FROM sesje WHERE id = ?", (sesja_id,)).fetchone()
        if w is None:
            return None
        wpisy = [dict(x) for x in db.execute(
            "SELECT Cwiczenie, Ciezar, Serie, Powtorzenia, Jednostka FROM wpisy_cwiczen WHERE Sesja_id = ? ORDER BY Kolejnosc, id",
            (sesja_id,))]
    for x in wpisy:
        x["Jednostka"] = x["Jednostka"] or "powt."
    return {**dict(w), "wpisy": wpisy}


def _liczba(v, domyslna=0):
    """Liczba z komórki tabeli: puste pole i NaN dają wartość domyślną."""
    try:
        return domyslna if v is None or pd.isna(v) else v
    except (TypeError, ValueError):
        return domyslna


def _tekst_komorki(v) -> str:
    return "" if _liczba(v, "") == "" else str(v).strip()


def _wiersz_wpisu(x: dict) -> tuple:
    return (_tekst_komorki(x.get("Cwiczenie")), float(_liczba(x.get("Ciezar"), 0)), int(_liczba(x.get("Serie"), 1)),
            int(_liczba(x.get("Powtorzenia"), 0)), _tekst_komorki(x.get("Jednostka")) or "powt.")


def zapisz_edycje_sesji(sesja_id: int, data: str, typ: str, waga: float | None, komentarz: str,
                        czas_min: int | None, wpisy: list[dict]) -> None:
    """Zapisuje zmiany w treningu. Wiersze ćwiczeń zastępują stare. Gdy ćwiczenia się zmieniły, szczegóły serii (RPE)
    tego treningu są usuwane, bo przestałyby pasować do nowych wartości."""
    datetime.fromisoformat(data)   # zła data zatrzyma zapis (ValueError)
    czyste = [w for w in wpisy if _tekst_komorki(w.get("Cwiczenie"))]
    if not czyste:
        raise ValueError("Trening musi mieć co najmniej jedno ćwiczenie. Jeśli ma zniknąć, użyj „Usuń trening”.")
    for w in czyste:   # nowy wiersz bez jednostki: jak w treningu na żywo (historia, znane ćwiczenia, partia Cardio)
        if not _tekst_komorki(w.get("Jednostka")):
            w["Jednostka"] = jednostka_domyslna(_tekst_komorki(w.get("Cwiczenie")))
    nowe = [_wiersz_wpisu(w) for w in czyste]
    if any(w[2] < 1 or w[3] < 1 for w in nowe):
        raise ValueError("Serie i powtórzenia (czas, dystans) muszą być większe od zera.")
    stary = wczytaj_sesje(sesja_id)
    if stary is None:
        raise ValueError("Nie znaleziono tego treningu.")
    kopia_bazy("przed_edycja")
    zmiana_cwiczen = [_wiersz_wpisu(x) for x in stary["wpisy"]] != nowe
    with closing(_polacz()) as db:
        db.execute("UPDATE sesje SET Data = ?, Typ_treningu = ?, Waga = ?, Komentarz = ?, Czas_min = ? WHERE id = ?",
                   (data, typ or "", waga, komentarz or "", czas_min, sesja_id))
        if zmiana_cwiczen:
            db.execute("DELETE FROM wpisy_cwiczen WHERE Sesja_id = ?", (sesja_id,))
            db.execute("DELETE FROM serie_wykonane WHERE Sesja_id = ?", (sesja_id,))
            for numer, (nazwa, ciezar, serie, powt, jednostka) in enumerate(nowe, start=1):
                db.execute("INSERT OR IGNORE INTO cwiczenia (Nazwa, Partia) VALUES (?, 'Inne')", (nazwa,))
                db.execute(
                    "INSERT INTO wpisy_cwiczen (Sesja_id, Kolejnosc, Cwiczenie, Ciezar, Serie, Powtorzenia, Komentarz, Jednostka) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (sesja_id, numer, nazwa, ciezar, serie, powt, "", jednostka))
        db.commit()


def eksport_csv() -> bytes:
    """Wszystkie treningi jako CSV (separator ;, przecinek dziesiętny, kodowanie z BOM: otwiera się poprawnie w Excelu)."""
    przygotuj_tabele()
    with closing(_polacz()) as db:
        df = pd.read_sql_query(
            "SELECT s.Data, s.Typ_treningu AS Trening, s.Czas_min, s.Waga, w.Kolejnosc, w.Cwiczenie, w.Ciezar, w.Serie, "
            "w.Powtorzenia, COALESCE(w.Jednostka, 'powt.') AS Jednostka, s.Komentarz AS Komentarz_treningu "
            "FROM sesje s LEFT JOIN wpisy_cwiczen w ON w.Sesja_id = s.id ORDER BY s.Data DESC, s.id DESC, w.Kolejnosc", db)
    return df.to_csv(sep=";", decimal=",", index=False).encode("utf-8-sig")


def plik_bazy() -> bytes:
    """Spójna kopia całej bazy do pobrania (np. na telefon)."""
    with closing(sqlite3.connect(baza.SCIEZKA_BAZY)) as zrodlo, closing(sqlite3.connect(":memory:")) as pamiec:
        zrodlo.backup(pamiec)
        return pamiec.serialize()


def historia_treningow(limit: int = 30) -> list[dict]:
    """Ostatnie treningi do listy w Historii: data, rodzaj, czas, waga, komentarz i ćwiczenia z opisem serii."""
    przygotuj_tabele()
    with closing(_polacz()) as db:
        db.row_factory = sqlite3.Row
        sesje = [dict(w) for w in db.execute(
            "SELECT id, Data, Typ_treningu, Waga, Komentarz, Czas_min FROM sesje ORDER BY Data DESC, id DESC LIMIT ?", (limit,))]
        if not sesje:
            return []
        znaki = ",".join("?" * len(sesje))
        wpisy = db.execute(
            f"SELECT Sesja_id, Cwiczenie, Ciezar, Serie, Powtorzenia, Jednostka FROM wpisy_cwiczen "
            f"WHERE Sesja_id IN ({znaki}) ORDER BY Sesja_id, Kolejnosc, id", [x["id"] for x in sesje]).fetchall()
    for x in sesje:
        x["cwiczenia"] = []
    po_id = {x["id"]: x for x in sesje}
    for w in wpisy:
        lista = po_id[w["Sesja_id"]]["cwiczenia"]
        jednostka = w["Jednostka"] or "powt."
        grupa = {"ciezar": w["Ciezar"] or 0.0, "powt": w["Powtorzenia"] or 0, "serie": w["Serie"] or 1}
        if lista and lista[-1]["nazwa"] == w["Cwiczenie"] and lista[-1]["jednostka"] == jednostka:
            lista[-1]["grupy"].append(grupa)
        else:
            lista.append({"nazwa": w["Cwiczenie"], "jednostka": jednostka, "grupy": [grupa]})
    for x in sesje:
        for c in x["cwiczenia"]:
            c["opis"] = opis_serii(c["grupy"], c["jednostka"])
    return sesje


# ===============================================================
# CZĘŚĆ 2: WYGLĄD (kafelki HTML)
# ===============================================================
def _pasek(proc: float, kolor: str, wysokosc: int = 8) -> str:
    proc = max(0.0, min(100.0, proc))
    return (f'<div style="height:{wysokosc}px;border-radius:{wysokosc}px;background:{KOLOR_TLA_PIERSCIENIA};overflow:hidden;">'
            f'<div style="width:{proc:.1f}%;height:100%;background:{kolor};border-radius:{wysokosc}px;"></div></div>')


def _ramka(kolor: str, tresc: str, wypelnienie: str = "16px 18px") -> str:
    return (f'<div style="{_tlo_karty(kolor)}border:1px solid {KOLOR_OBRAMOWANIA};border-radius:16px;'
            f'padding:{wypelnienie};box-sizing:border-box;">{tresc}</div>')


def naglowek_sesji_html(stan: dict) -> str:
    zrobione, plan = postep(stan)
    start = datetime.fromisoformat(stan["start"]).strftime("%H:%M")
    typ = stan.get("typ") or ""
    if typ and stan["nazwa"].startswith(typ):   # nazwa już mówi to samo (preset albo „jak ostatnio”)
        typ = ""
    podpis = " · ".join(x for x in (html.escape(typ), f"start {start}") if x)
    return _ramka(ZIELONY, (
        f'<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">'
        f'{_naglowek_karty("Trening w toku", ZIELONY)}'
        f'<span style="font-size:0.85rem;color:{KOLOR_PRZYGASZONY};">serie {zrobione} / {plan}</span></div>'
        f'<div style="font-size:1.5rem;font-weight:700;color:{KOLOR_TEKSTU};margin-top:6px;">{html.escape(stan["nazwa"])}</div>'
        f'<div style="font-size:0.85rem;color:{KOLOR_PRZYGASZONY};margin:2px 0 10px 0;">{podpis}</div>'
        f'{_pasek(100 * zrobione / plan if plan else 0, ZIELONY)}'
    ))


def pasek_sesji_html(stan: dict, teraz: datetime) -> str:
    """Cienki pasek przypięty do góry ekranu: czas treningu, przerwa i postęp serii."""
    zrobione, plan = postep(stan)
    zostalo = przerwa_pozostalo(stan, teraz)
    if przerwy_wylaczone(stan):
        kolor, glowny, opis = KOLOR_PRZYGASZONY, "wyłączona", "Przerwa"
        pasek = _pasek(100 * zrobione / plan if plan else 0, ZIELONY, 6)
    elif zostalo is None:
        kolor, glowny, opis = NIEBIESKI, "–", "Przerwa"
        pasek = _pasek(100 * zrobione / plan if plan else 0, ZIELONY, 6)
    elif zostalo > 0:
        dl = max(int(stan.get("przerwa_dl") or 0), zostalo)
        kolor = CZERWONY if zostalo <= 10 else KOLOR_PRZERWY
        glowny, opis = format_czasu(zostalo), "Przerwa"
        pasek = _pasek(100 * zostalo / dl, kolor, 6)
    else:
        kolor, glowny, opis = ZIELONY, "Gotowe", "Przerwa"
        pasek = _pasek(100, ZIELONY, 6)

    def kolumna(podpis: str, wartosc: str, kol: str, flex: str, rozmiar: str = "1.35rem") -> str:
        # Stała wysokość wiersza z wartością, żeby podpisy nad liczbami były na tej samej wysokości mimo różnych rozmiarów liczb
        return (f'<div style="flex:{flex};min-width:0;text-align:center;line-height:1.15;">'
                f'<div style="font-size:0.7rem;color:{KOLOR_PRZYGASZONY};">{podpis}</div>'
                f'<div style="display:flex;align-items:center;justify-content:center;height:1.9rem;font-size:{rozmiar};'
                f'font-weight:700;color:{kol};white-space:nowrap;">{wartosc}</div></div>')

    czas = format_czasu(czas_trwania(stan, teraz).total_seconds())
    return '<div style="margin-bottom:10px;">' + _ramka(kolor, (
        '<div style="display:flex;align-items:flex-start;gap:8px;">'
        + kolumna("Czas treningu", czas, KOLOR_TEKSTU, "1")
        + kolumna(opis, glowny, kolor, "1.3", "1.6rem" if glowny != "wyłączona" else "1rem")
        + kolumna("Serie", f"{zrobione}/{plan}", KOLOR_SERII, "1")
        + f'</div><div style="margin-top:6px;">{pasek}</div>'
    ), "8px 12px") + '</div>'


def licznik_html(stan: dict, teraz: datetime) -> str:
    """Czas treningu po lewej, odliczanie przerwy po prawej."""
    zostalo = przerwa_pozostalo(stan, teraz)
    if zostalo is None:
        kolor, glowny, opis, proc = NIEBIESKI, "–", "po zapisaniu serii ruszy odliczanie", 0
    elif zostalo > 0:
        dl = max(int(stan.get("przerwa_dl") or 0), zostalo)
        kolor = CZERWONY if zostalo <= 10 else KOLOR_PRZERWY
        glowny, opis, proc = format_czasu(zostalo), "do kolejnej serii", 100 * zostalo / dl
    else:
        kolor, glowny, opis, proc = ZIELONY, "Gotowe", "możesz robić kolejną serię", 100
    return _ramka(kolor, (
        f'<div style="display:flex;align-items:stretch;gap:16px;">'
        f'<div style="flex:1;min-width:0;text-align:center;">'
        f'<div style="font-size:0.8rem;color:{KOLOR_PRZYGASZONY};">Czas treningu</div>'
        f'<div style="font-size:1.9rem;font-weight:700;color:{KOLOR_TEKSTU};">{format_czasu(czas_trwania(stan, teraz).total_seconds())}</div></div>'
        f'<div style="width:1px;background:{KOLOR_OBRAMOWANIA};"></div>'
        f'<div style="flex:1.4;min-width:0;text-align:center;">'
        f'<div style="font-size:0.8rem;color:{KOLOR_PRZYGASZONY};">Przerwa</div>'
        f'<div style="font-size:1.9rem;font-weight:700;color:{kolor};">{glowny}</div>'
        f'<div style="font-size:0.75rem;color:{KOLOR_PRZYGASZONY};margin:0 0 6px 0;">{opis}</div>'
        f'{_pasek(proc, kolor, 6)}</div></div>'
    ), "12px 18px")


def _chip(tekst: str) -> str:
    return (f'<span style="display:inline-block;margin:3px 6px 0 0;padding:3px 10px;border-radius:999px;'
            f'background:{KOLOR_TLA_PIERSCIENIA};font-size:0.8rem;color:{KOLOR_TEKSTU};">{html.escape(tekst)}</span>')


def karta_cwiczenia_html(c: dict, nr: int, ile: int, notatka: str = "") -> str:
    """Nagłówek bieżącego ćwiczenia: nazwa, plan, notatka, wskazówka, ostatni wynik i zapisane już serie."""
    rola = html.escape(c.get("rola") or "")
    czesci = [
        f'<div style="display:flex;justify-content:space-between;align-items:center;font-size:0.8rem;color:{KOLOR_PRZYGASZONY};">'
        f'<span>Ćwiczenie {nr + 1} z {ile}</span><span>{rola}</span></div>',
        f'<div style="font-size:1.45rem;font-weight:700;color:{KOLOR_TEKSTU};margin-top:2px;">{html.escape(c["nazwa"])}</div>',
        f'<div style="font-size:0.95rem;color:{KOLOR_TEKSTU};margin-top:2px;">Plan: <b>{html.escape(tekst_planu(c))}</b></div>',
    ]
    if notatka:
        czesci.append(f'<div style="font-size:0.88rem;color:{KOLOR_TEKSTU};margin-top:6px;padding-left:8px;'
                      f'border-left:3px solid {NIEBIESKI};">Notatka: {html.escape(notatka)}</div>')
    if c.get("wskazowka"):
        czesci.append(f'<div style="font-size:0.85rem;font-style:italic;color:{KOLOR_PRZYGASZONY};margin-top:4px;">{html.escape(c["wskazowka"])}</div>')
    if c.get("alternatywa"):
        czesci.append(f'<div style="font-size:0.8rem;color:{KOLOR_PRZYGASZONY};margin-top:2px;">Zamiennik: {html.escape(c["alternatywa"])}</div>')
    prop = c.get("propozycja")
    if prop:
        data = datetime.fromisoformat(prop["data"]).strftime("%d.%m")
        czesci.append(f'<div style="font-size:0.85rem;color:{KOLOR_PRZYGASZONY};margin-top:6px;">Ostatnio ({data}): {html.escape(prop["ostatnio"])}</div>')
        if prop["podniesc"]:
            czesci.append(f'<div style="font-size:0.85rem;font-weight:600;color:{ZIELONY};">Propozycja: {format_kg(prop["ciezar"])} kg. Górny zakres był osiągnięty.</div>')
        elif prop["bazowy_ciezar"]:
            czesci.append(f'<div style="font-size:0.85rem;font-weight:600;color:{NIEBIESKI};">Propozycja: zostań przy {format_kg(prop["ciezar"])} kg i dobij do górnej granicy.</div>')
        kroki = propozycja_rozgrzewki(prop.get("ciezar")) if jednostka_powtorzen(c["jednostka"]) and not serie_robocze(c) else []
        if kroki:
            opis_rozgrzewki = ", ".join(f"{format_kg(kg)} kg × {p}" for kg, p in kroki)
            czesci.append(f'<div style="font-size:0.8rem;color:{KOLOR_PRZYGASZONY};margin-top:2px;">Rozgrzewka (propozycja): {opis_rozgrzewki}</div>')
    if c["serie"]:
        chipy = []
        numer_roboczej = numer_rozgrzewki = 0
        for s in c["serie"]:
            if s.get("rozgrz"):
                numer_rozgrzewki += 1
                etykieta = f"R{numer_rozgrzewki}"
            else:
                numer_roboczej += 1
                etykieta = str(numer_roboczej)
            tekst = f"{etykieta}: {format_powt(s['powt'], c['jednostka'])}"
            if s["ciezar"]:
                tekst += f" @ {format_kg(s['ciezar'])} kg"
            if s.get("rpe"):
                tekst += f" · RPE {s['rpe']}"
            chipy.append(_chip(tekst))
        czesci.append(f'<div style="margin-top:8px;">{"".join(chipy)}</div>')
    return "".join(czesci)


def podsumowanie_html(stan: dict, teraz: datetime) -> str:
    zrobione, _ = postep(stan)
    ile_cw = sum(1 for c in stan["cwiczenia"] if serie_robocze(c))
    kafelki = [
        ("Czas", f"{max(1, round(czas_trwania(stan, teraz).total_seconds() / 60))} min"),
        ("Ćwiczenia", str(ile_cw)),
        ("Serie", str(zrobione)),
        ("Objętość", f"{objetosc(stan):,.0f} kg".replace(",", " ")),
    ]
    elementy = "".join(
        f'<div style="flex:1;min-width:0;text-align:center;">'
        f'<div style="font-size:0.8rem;color:{KOLOR_PRZYGASZONY};">{n}</div>'
        f'<div style="font-size:1.5rem;font-weight:700;color:{KOLOR_TEKSTU};">{w}</div></div>'
        for n, w in kafelki
    )
    return _ramka(ZIELONY, f'{_naglowek_karty("Podsumowanie treningu", ZIELONY)}'
                           f'<div style="display:flex;gap:12px;margin-top:10px;">{elementy}</div>')


def wynik_html(wynik: dict | None) -> str:
    """Karta po zapisie treningu: nowe rekordy i porównanie z poprzednim takim treningiem (pusta, gdy nie ma czego pokazać)."""
    if not wynik:
        return ""
    wiersze = []
    for r in wynik.get("rekordy", []):
        wiersze.append(
            f'<div style="padding:6px 0;border-bottom:1px solid {KOLOR_OBRAMOWANIA};">'
            f'<div style="font-weight:600;color:{KOLOR_TEKSTU};">{html.escape(r["cwiczenie"])}</div>'
            f'<div style="font-size:0.85rem;font-weight:600;color:{ZIELONY};">Nowy rekord: {html.escape(r["tekst"])}</div></div>')
    por = wynik.get("porownanie")
    if por:
        data = datetime.fromisoformat(por["data"]).strftime("%d.%m")
        if por["proc"] is not None:
            znak = "+" if por["proc"] >= 0 else "−"
            zmiana = f"{znak}{abs(por['proc']):.0f}%".replace(".", ",")
            tekst = (f"Objętość {por['objetosc']:,.0f} kg ({zmiana} względem treningu z {data}, było {por['objetosc_poprz']:,.0f} kg). "
                     f"Serie: {por['serie']} (było {por['serie_poprz']}).").replace(",", " ")
        else:
            tekst = f"Serie: {por['serie']} (w treningu z {data} było {por['serie_poprz']})."
        wiersze.append(f'<div style="padding:8px 0 0 0;font-size:0.88rem;color:{KOLOR_TEKSTU};">{html.escape(tekst)}</div>')
    if not wiersze:
        return ""
    return _ramka(ZIELONY, f'{_naglowek_karty("Rekordy i porównanie", ZIELONY)}<div style="margin-top:6px;">{"".join(wiersze)}</div>')


# ===============================================================
# CZĘŚĆ 3: INTERFEJS STREAMLIT
# ===============================================================
def _stan() -> dict | None:
    if "sesja_stan" not in st.session_state:
        st.session_state["sesja_stan"] = wczytaj_stan()
    return st.session_state["sesja_stan"]


def aktywna() -> bool:
    return _stan() is not None


def _wyczysc_pola() -> None:
    s = st.session_state
    for klucz in list(s.keys()):
        if klucz.startswith(("sesja_ci_", "sesja_po_", "sesja_rpe_", "sesja_zob_", "sesja_rozgrz_", "sesja_nota_")):
            del s[klucz]


def _uruchom(stan: dict) -> None:
    # długość przerwy: wybór z ekranu startowego, a gdy go nie ma (start z innej strony): ostatnio zapamiętany
    wybor = st.session_state.get("start_przerwa") or wczytaj_ustawienie("przerwa", "Auto")
    stan["przerwa"] = wybor if wybor in OPCJE_PRZERWY else "Auto"
    if stan["przerwa"] != "Wył.":
        stan.pop("przerwa_poprz", None)
    zapisz_ustawienie("przerwa", stan["przerwa"])
    dopelnij_propozycje(stan)
    _wyczysc_pola()
    st.session_state["sesja_stan"] = stan
    st.session_state["sesja_konczenie"] = False
    zapisz_stan(stan)


def rozpocznij_z_presetu(preset_id: int) -> None:
    """Przycisk 'Rozpocznij': ładuje ćwiczenia presetu i uruchamia prowadzony trening."""
    from presety import lista_presetow, wczytaj_cwiczenia_presetu
    lista = lista_presetow()
    wiersz = lista[lista["id"] == preset_id].iloc[0]
    cwiczenia = cwiczenia_z_presetu(wczytaj_cwiczenia_presetu(preset_id))
    # rodzaj treningu to po prostu nazwa presetu: jedna rzecz do wyboru
    _uruchom(nowy_stan(str(wiersz["Nazwa"]), str(wiersz["Nazwa"]), cwiczenia, preset_id))


def rozpocznij_z_ostatniego(typ: str, zapas: str = "") -> None:
    """Start na podstawie ostatniego treningu z tego presetu (te same ćwiczenia, serie i zakresy)."""
    ostatni = ostatni_trening_rodzaju(typ, zapas)
    _uruchom(nowy_stan(f"{typ} (jak ostatnio)", typ, ostatni["cwiczenia"] if ostatni else []))


def rozpocznij_pusty(typ: str = "") -> None:
    """Przycisk 'Zacznij pusty trening': ćwiczenia dodajesz w trakcie, nazwę (preset) możesz nadać na końcu."""
    _uruchom(nowy_stan(typ or "Trening", typ, []))


# --- callbacki przycisków --------------------------------------------------
def _blad(tekst: str) -> None:
    st.session_state["sesja_blad"] = tekst


def _zapisz_serie(nr: int) -> None:
    s, stan = st.session_state, _stan()
    if stan is None:
        return
    powt = int(s.get(f"sesja_po_{nr}") or 0)
    if powt < 1:
        _blad("Wpisz liczbę powtórzeń (albo czas / dystans) większą od zera.")
        return
    c = stan["cwiczenia"][nr]
    ciezar = float(s.get(f"sesja_ci_{nr}") or 0.0) if pokaz_ciezar(c, bool(s.get(f"sesja_zob_{nr}"))) else 0.0
    rozgrzewka = bool(s.get(f"sesja_rozgrz_{nr}"))
    dodaj_serie(stan, nr, ciezar, powt, None if rozgrzewka else s.get(f"sesja_rpe_{nr}"), ustawienie_przerwy(stan),
                rozgrzewka=rozgrzewka)
    if rozgrzewka:   # pola od razu na kolejny krok rozgrzewki
        s[f"sesja_ci_{nr}"], s[f"sesja_po_{nr}"] = _domyslne_pola(c, True)
    else:
        s[f"sesja_rpe_{nr}"] = None
    zapisz_stan(stan)


def opis_serii_krotko(s: dict, jednostka: str) -> str:
    """Jedna seria w skrócie, np. „80 kg × 5 · RPE 8”, „20 min”."""
    tekst = format_powt(s["powt"], jednostka)
    if s["ciezar"]:
        tekst = f"{format_kg(s['ciezar'])} kg × {tekst}"
    if s.get("rpe"):
        tekst += f" · RPE {s['rpe']}"
    return tekst


def _powtorz_serie(nr: int) -> None:
    """Zapisuje serię identyczną z ostatnią roboczą (z jej RPE). Pola zostają na tych wartościach, RPE się czyści."""
    s, stan = st.session_state, _stan()
    if stan is None:
        return
    rob = serie_robocze(stan["cwiczenia"][nr])
    if not rob:
        return
    ostatnia = rob[-1]
    dodaj_serie(stan, nr, ostatnia["ciezar"], ostatnia["powt"], ostatnia.get("rpe"), ustawienie_przerwy(stan))
    s[f"sesja_ci_{nr}"], s[f"sesja_po_{nr}"] = float(ostatnia["ciezar"]), int(ostatnia["powt"])
    s[f"sesja_rpe_{nr}"] = None
    zapisz_stan(stan)


def _domyslne_pola(c: dict, rozgrzewka: bool = False) -> tuple[float, int]:
    """Wartości w polach: ostatnia seria robocza albo propozycja z historii; dla rozgrzewki kolejny krok schematu."""
    rob = serie_robocze(c)
    prop = c.get("propozycja") or {}
    if rozgrzewka:
        kroki = propozycja_rozgrzewki(prop.get("ciezar") or (rob[-1]["ciezar"] if rob else 0))
        zrobione = len(c["serie"]) - len(rob)
        if kroki:
            kg, powt = kroki[min(zrobione, len(kroki) - 1)]
            return float(kg), powt
    ostatnia = rob[-1] if rob else None
    ciezar = ostatnia["ciezar"] if ostatnia else (prop.get("ciezar") or 0.0)
    powt = ostatnia["powt"] if ostatnia else (prop.get("powt") or c.get("powt_od") or WARTOSC_STARTOWA.get(c.get("jednostka"), 8))
    return float(ciezar), max(1, int(powt))


def _przelacz_rozgrzewke(nr: int) -> None:
    """Po przełączeniu „Seria rozgrzewkowa” pola dostają wartości pasujące do rozgrzewki albo do serii roboczej."""
    s, stan = st.session_state, _stan()
    if stan is None:
        return
    s[f"sesja_ci_{nr}"], s[f"sesja_po_{nr}"] = _domyslne_pola(stan["cwiczenia"][nr], bool(s.get(f"sesja_rozgrz_{nr}")))


def _zapisz_notatke(nr: int) -> None:
    s, stan = st.session_state, _stan()
    if stan is None:
        return
    zapisz_notatke(stan["cwiczenia"][nr]["nazwa"], s.get(f"sesja_nota_{nr}") or "")


def _cofnij(nr: int) -> None:
    stan = _stan()
    if stan and cofnij_serie(stan, nr):
        zapisz_stan(stan)


def _przejdz(delta: int) -> None:
    stan = _stan()
    if stan:
        stan["biezace"] = max(0, min(len(stan["cwiczenia"]) - 1, stan["biezace"] + delta))
        zapisz_stan(stan)


def _skocz() -> None:
    stan, nowy = _stan(), st.session_state.get("sesja_skok")
    if stan and nowy is not None and 0 <= nowy < len(stan["cwiczenia"]):
        stan["biezace"] = nowy
        zapisz_stan(stan)


def _ustaw_rpe(nr: int, wartosc: int) -> None:
    """RPE jednym stuknięciem; ponowne stuknięcie w zaznaczoną wartość czyści wybór (RPE jest opcjonalne)."""
    s = st.session_state
    s[f"sesja_rpe_{nr}"] = None if s.get(f"sesja_rpe_{nr}") == wartosc else wartosc


def _otworz(nr: int) -> None:
    stan = _stan()
    if stan and 0 <= nr < len(stan["cwiczenia"]):
        stan["biezace"] = nr
        zapisz_stan(stan)


def _pozniej(nr: int) -> None:
    stan = _stan()
    if stan and przesun_na_koniec(stan, nr):
        _wyczysc_pola()
        st.session_state.pop("sesja_usun_potw", None)
        zapisz_stan(stan)


def _usun_z_listy(nr: int) -> None:
    """Usuwa od razu ćwiczenie bez serii. Gdy ma serie, najpierw prosi o potwierdzenie w liście."""
    s, stan = st.session_state, _stan()
    if stan is None:
        return
    if stan["cwiczenia"][nr]["serie"]:
        s["sesja_usun_potw"] = nr
        return
    usun_cwiczenie(stan, nr)
    _wyczysc_pola()
    zapisz_stan(stan)


def _usun_potwierdzone() -> None:
    s, stan = st.session_state, _stan()
    nr = s.pop("sesja_usun_potw", None)
    if stan is not None and nr is not None and 0 <= nr < len(stan["cwiczenia"]):
        usun_cwiczenie(stan, nr, z_seriami=True)
        _wyczysc_pola()
        zapisz_stan(stan)


def _anuluj_usuwanie() -> None:
    st.session_state.pop("sesja_usun_potw", None)


def _odczytaj_cel(prefiks: str) -> tuple[int | None, int | None, int | None]:
    s = st.session_state
    wartosci = []
    for pole in ("serie", "od", "do"):
        v = s.get(f"{prefiks}_{pole}")
        wartosci.append(int(v) if v else None)
    return tuple(wartosci)


def _wyczysc_cel(prefiks: str) -> None:
    for pole in ("serie", "od", "do"):
        st.session_state[f"{prefiks}_{pole}"] = None


def _pola_celu(prefiks: str) -> None:
    """Cel nowego ćwiczenia: liczba serii i zakres na serię (powtórzenia, sekundy, minuty lub metry zależnie od jednostki)."""
    st.markdown("**Cel (opcjonalnie)**")
    st.number_input("Liczba serii", min_value=1, max_value=20, step=1, value=None, placeholder="Auto", key=f"{prefiks}_serie",
                    help="Puste: zostaje liczba serii z planu (dla minut: 1 seria).")
    k1, k2 = st.columns(2)
    k1.number_input("Cel na serię: od", min_value=1, max_value=10000, step=1, value=None, placeholder="bez celu", key=f"{prefiks}_od",
                    help="W wybranej jednostce: powtórzenia, sekundy, minuty albo metry. Np. 30 min albo 8 powtórzeń.")
    k2.number_input("do (zakres)", min_value=1, max_value=10000, step=1, value=None, placeholder="opcjonalnie", key=f"{prefiks}_do",
                    help="Tylko gdy cel to zakres, np. 8–12 powtórzeń.")


def _dodaj_cwiczenie() -> None:
    s, stan = st.session_state, _stan()
    if stan is None:
        return
    nazwa = (s.get("sesja_dodaj_nowe") or "").strip() or (s.get("sesja_dodaj_wybor") or "")
    if not nazwa:
        _blad("Wybierz ćwiczenie z listy albo wpisz własną nazwę.")
        return
    dopisz_cwiczenie_do_bazy(nazwa, s.get("sesja_dodaj_partia"))
    jednostka = JEDNOSTKI_WYBOR.get(s.get("sesja_dodaj_jednostka") or "Automatycznie") or jednostka_domyslna(nazwa)
    c = nowe_cwiczenie(nazwa, jednostka=jednostka)
    ustaw_cel(c, *_odczytaj_cel("sesja_dodaj"))
    c["propozycja"] = zaproponuj(c)
    dolacz_cwiczenie(stan, c)
    _wyczysc_pola()
    s["sesja_dodaj_wybor"], s["sesja_dodaj_nowe"], s["sesja_dodaj_jednostka"] = None, "", "Automatycznie"
    s["sesja_dodaj_partia"] = "Inne"
    _wyczysc_cel("sesja_dodaj")
    zapisz_stan(stan)


def _zamien_cwiczenie() -> None:
    s, stan = st.session_state, _stan()
    if stan is None or not stan["cwiczenia"]:
        return
    nr = stan["biezace"]
    nazwa = (s.get("sesja_zam_nowe") or "").strip() or (s.get("sesja_zam_wybor") or "")
    if not nazwa:
        s["sesja_zam_blad"] = "Wybierz ćwiczenie z listy albo wpisz własną nazwę."
        return
    dopisz_cwiczenie_do_bazy(nazwa, s.get("sesja_zam_partia"))
    jednostka = JEDNOSTKI_WYBOR.get(s.get("sesja_zam_jednostka") or "Automatycznie") or jednostka_domyslna(nazwa)
    zamien_cwiczenie(stan, nr, nazwa, jednostka)
    ustaw_cel(stan["cwiczenia"][nr], *_odczytaj_cel("sesja_zam"))
    stan["cwiczenia"][nr]["propozycja"] = zaproponuj(stan["cwiczenia"][nr])
    _wyczysc_pola()
    s["sesja_zam_wybor"], s["sesja_zam_nowe"], s["sesja_zam_jednostka"] = None, "", "Automatycznie"
    s["sesja_zam_partia"] = "Inne"
    _wyczysc_cel("sesja_zam")
    s["sesja_zam_zamknij"] = True   # okno zamknie się przy następnym przebiegu (patrz _okno_zamiany)
    zapisz_stan(stan)


def _zapisz_push_przerwy() -> None:
    zapisz_ustawienie("push_przerwa", "1" if st.session_state.get("start_push_przerwa") else "0")


def _ustaw_przerwe() -> None:
    """Zmiana długości przerwy w panelu na dole (dotyczy tylko trwającego treningu)."""
    stan = _stan()
    if stan:
        ustaw_przerwe(stan, st.session_state.get("sesja_przerwa"))
        zapisz_stan(stan)


def _przelacz_przerwy() -> None:
    """Przycisk w przypiętym pasku: przerwy wł./wył."""
    stan = _stan()
    if stan:
        przelacz_przerwy(stan)
        st.session_state["sesja_przerwa"] = stan["przerwa"]
        zapisz_stan(stan)


def _dodaj_przerwe(sekundy: int) -> None:
    stan = _stan()
    if stan:
        przedluz_przerwe(stan, sekundy)
        zapisz_stan(stan)


def _pomin_przerwe() -> None:
    stan = _stan()
    if stan:
        pomin_przerwe(stan)
        zapisz_stan(stan)


def _rozpocznij_konczenie() -> None:
    st.session_state["sesja_konczenie"] = True


def _wroc_do_treningu() -> None:
    st.session_state["sesja_konczenie"] = False


def _zapisz_preset_ze_stanu() -> None:
    s, stan = st.session_state, _stan()
    if stan is None:
        return
    nazwa = (s.get("sesja_preset_nazwa") or "").strip()
    try:
        utworz_preset(nazwa, cwiczenia_stanu_do_presetu(stan))
    except ValueError as blad:
        s["sesja_preset_blad"] = str(blad)
        return
    info = f"Zapisano preset „{nazwa}”."
    if not stan.get("typ"):   # trening od zera dostaje nazwę nowego presetu
        stan["typ"] = nazwa
        zapisz_stan(stan)
        info += " Ten trening zapisze się pod tą nazwą."
    s["sesja_preset_info"] = info


def _porzuc() -> None:
    s = st.session_state
    s["sesja_stan"], s["sesja_konczenie"] = None, False
    _wyczysc_pola()
    for klucz in ("sesja_typ_konca", "sesja_preset_nazwa", "sesja_preset_info", "sesja_preset_blad"):
        s.pop(klucz, None)
    zapisz_stan(None)
    s["sesja_ukonczona"] = "Trening porzucony bez zapisu."


def _zakoncz_i_zapisz() -> None:
    s, stan = st.session_state, _stan()
    if stan is None:
        return
    typ = s.get("sesja_typ_konca")   # to pole jest tylko dla treningu od zera; w innych wiadomo, jaki to preset
    if typ not in (None, BRAK_RODZAJU) and not stan.get("typ"):
        stan["typ"] = typ
    try:
        podsumowanie = (len([c for c in stan["cwiczenia"] if serie_robocze(c)]), postep(stan)[0], objetosc(stan))
        try:
            wynik = rekordy_treningu(stan)   # przed zapisem, żeby trening nie porównywał się sam ze sobą
        except Exception:   # dodatek do zapisu: jego błąd nie może zablokować zapisania treningu
            wynik = None
        zapisz_trening(stan, (s.get("sesja_komentarz") or "").strip(), s.get("sesja_waga"))
    except ValueError as blad:
        _blad(str(blad))
        return
    s["sesja_stan"], s["sesja_konczenie"] = None, False
    _wyczysc_pola()
    for klucz in ("sesja_komentarz", "sesja_waga", "sesja_typ_konca", "sesja_preset_nazwa", "sesja_preset_info", "sesja_preset_blad"):
        s.pop(klucz, None)
    s["sesja_wynik"] = wynik
    obj = f"{podsumowanie[2]:,.0f}".replace(",", " ")
    s["sesja_ukonczona"] = f"Trening zapisany. Ćwiczeń: {podsumowanie[0]}, serii: {podsumowanie[1]}, objętość: {obj} kg."


# --- widoki ----------------------------------------------------------------
@st.fragment(run_every=1)
def _licznik() -> None:
    """Pasek z czasem i przerwą. Odświeża się co sekundę tylko ten fragment, reszta strony stoi w miejscu."""
    stan = st.session_state.get("sesja_stan")
    if not stan:
        return
    teraz = datetime.now()
    st.markdown(pasek_sesji_html(stan, teraz), unsafe_allow_html=True)
    zostalo = przerwa_pozostalo(stan, teraz)
    k1, k2, k3 = st.columns(3)
    k1.button("+30 s", key="sesja_p30", on_click=_dodaj_przerwe, args=(30,), use_container_width=True, disabled=not zostalo)
    k2.button("Pomiń", key="sesja_pomin", on_click=_pomin_przerwe, use_container_width=True, disabled=not zostalo)
    wylaczone = przerwy_wylaczone(stan)
    k3.button("Przerwy wył." if wylaczone else "Przerwy wł.", key="sesja_przerwy_przel", on_click=_przelacz_przerwy,
              use_container_width=True, type="primary" if wylaczone else "secondary",
              help="Jedno stuknięcie wyłącza lub włącza odliczanie przerw w tym treningu.")
    if zostalo == 0 and st.session_state.get("sesja_toast") != stan["przerwa_do"]:
        st.session_state["sesja_toast"] = stan["przerwa_do"]
        st.toast("Koniec przerwy. Czas na kolejną serię.")


# Pasek z czasem i przerwą przypięty do góry ekranu. Nagłówek Streamlita (z logo) na telefonie dostaje tło, żeby nie
# prześwitywała treść. Zakładamy, że kontener z kluczem bywa opakowany w stLayoutWrapper (nowsze wersje Streamlita).
CSS_PASEK = (
    "<style>"
    "[data-testid='stMainBlockContainer'],[data-testid='stAppViewBlockContainer'],.stMain .block-container,.block-container"
    "{padding-top:4rem !important;}"
    ".st-key-sesja_pasek,[data-testid='stLayoutWrapper']:has(> .st-key-sesja_pasek){position:sticky;top:3.75rem;z-index:100;}"
    ".st-key-sesja_pasek{background:var(--e-pasek);padding:6px 4px 8px 4px;border-radius:0 0 16px 16px;"
    "gap:0.4rem !important;margin-bottom:0.6rem;box-shadow:0 8px 10px -8px var(--e-cien_pasek);}"
    ".st-key-sesja_pasek [data-testid='stHorizontalBlock']{flex-wrap:nowrap !important;gap:8px !important;}"
    ".st-key-sesja_pasek [data-testid='stColumn'],.st-key-sesja_pasek [data-testid='column']"
    "{min-width:0 !important;flex:1 1 0 !important;width:auto !important;}"
    ".st-key-sesja_pasek button{min-height:2.4rem;padding:0 0.3rem;font-size:0.9rem;}"
    "@media (max-width:768px){[data-testid='stHeader']{background:var(--e-naglowek) !important;"
    "-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px);}}"
    "</style>"
)


def _etykieta_wartosci(jednostka: str) -> str:
    return {"s": "Czas (s)", "m": "Dystans (m)", "min": "Czas (min)"}.get(jednostka, "Powtórzenia")


def _nazwa_pigulki(stan: dict, i: int) -> str:
    """Sam numer (✓ przy wykonanym), żeby wszystkie ćwiczenia mieściły się w jednym rzędzie."""
    c = stan["cwiczenia"][i]
    return f"{'✓' if len(serie_robocze(c)) >= c['serie_plan'] else ''}{i + 1}"


CSS_LISTA = (
    "<style>"
    ".st-key-sesja_lista [data-testid='stHorizontalBlock']{flex-wrap:nowrap !important;gap:8px !important;}"
    ".st-key-sesja_lista [data-testid='stColumn'],.st-key-sesja_lista [data-testid='column']"
    "{min-width:0 !important;flex:1 1 0 !important;width:auto !important;}"
    ".st-key-sesja_lista button{min-height:2.3rem;padding:0 0.3rem;font-size:0.9rem;}"
    ".st-key-sesja_lista [class*='st-key-sesja_lu_'] button,.st-key-sesja_lista [class*='st-key-sesja_lt_'] button"
    "{color:var(--e-kasuj);border-color:var(--e-kasuj_ramka);}"
    "</style>"
)


def _lista_cwiczen(stan: dict) -> None:
    """Pełna lista ćwiczeń: otwórz, zrób później (na koniec), usuń (z potwierdzeniem, gdy są już serie)."""
    ile = len(stan["cwiczenia"])
    with st.expander(f"Lista ćwiczeń ({ile}): kolejność i usuwanie"):
        with st.container(key="sesja_lista"):
            st.markdown(CSS_LISTA, unsafe_allow_html=True)
            potw = st.session_state.get("sesja_usun_potw")
            if potw is not None and potw >= ile:
                potw = None
            for i, c in enumerate(stan["cwiczenia"]):
                zrobione = len(serie_robocze(c))
                aktualne = " · teraz" if i == stan["biezace"] else ""
                st.markdown(f"**{i + 1}. {html.escape(c['nazwa'])}**  \n"
                            f"<span style='font-size:0.85rem;color:{KOLOR_PRZYGASZONY};'>serie {zrobione}/{c['serie_plan']}{aktualne}</span>",
                            unsafe_allow_html=True)
                if potw == i:
                    st.warning(f"Usunąć to ćwiczenie razem z {zrobione} zapisanymi seriami?")
                    k1, k2 = st.columns(2)
                    k1.button("Tak, usuń", key=f"sesja_lt_{i}", on_click=_usun_potwierdzone, use_container_width=True)
                    k2.button("Anuluj", key=f"sesja_la_{i}", on_click=_anuluj_usuwanie, use_container_width=True)
                else:
                    k1, k2, k3 = st.columns(3)
                    k1.button("Otwórz", key=f"sesja_lo_{i}", on_click=_otworz, args=(i,), use_container_width=True,
                              disabled=i == stan["biezace"])
                    k2.button("Później", key=f"sesja_lp_{i}", on_click=_pozniej, args=(i,), use_container_width=True,
                              disabled=i == ile - 1, help="Przenosi na koniec treningu")
                    k3.button("Usuń", key=f"sesja_lu_{i}", on_click=_usun_z_listy, args=(i,), use_container_width=True)


def _przygotuj_pola(c: dict, nr: int) -> None:
    """Ustawia wartości początkowe pól: ostatnia seria, a gdy jej nie ma, propozycja z historii."""
    s = st.session_state
    ciezar, powt = _domyslne_pola(c)
    if f"sesja_ci_{nr}" not in s:
        s[f"sesja_ci_{nr}"] = ciezar
    if f"sesja_po_{nr}" not in s:
        s[f"sesja_po_{nr}"] = powt
    s.setdefault(f"sesja_rpe_{nr}", None)
    if f"sesja_nota_{nr}" not in s:
        s[f"sesja_nota_{nr}"] = wczytaj_notatke(c["nazwa"])


@st.dialog("Zamień to ćwiczenie")
def _okno_zamiany() -> None:
    """Okienko zamiany ćwiczenia. Po zamianie zamyka się samo (st.rerun odświeża całą stronę)."""
    s = st.session_state
    if s.pop("sesja_zam_zamknij", False):
        st.rerun()
    if "sesja_zam_blad" in s:
        st.error(s.pop("sesja_zam_blad"))
    st.selectbox("Ćwiczenie z bazy", baza.lista_cwiczen(), index=None, placeholder="Wybierz lub zacznij pisać...", key="sesja_zam_wybor")
    st.text_input("...albo wpisz własne ćwiczenie", placeholder="np. Przysiad bułgarski", key="sesja_zam_nowe")
    st.selectbox("Partia (tylko dla nowego, własnego ćwiczenia)", lista_partii(), index=len(lista_partii()) - 1, key="sesja_zam_partia",
                 help="Do której partii mięśniowej zaliczyć nowe ćwiczenie. Dzięki temu liczy się w „Serie na partię” w Postępach. "
                      "Dla ćwiczenia wybranego z bazy ta wartość jest pomijana.")
    st.selectbox("Jednostka (w czym liczysz)", list(JEDNOSTKI_WYBOR), key="sesja_zam_jednostka",
                 help="Automatycznie: jak ostatnio zapisywałeś to ćwiczenie, a gdy robisz je pierwszy raz: powtórzenia.")
    _pola_celu("sesja_zam")
    st.button("Zamień", type="primary", use_container_width=True, on_click=_zamien_cwiczenie, key="sesja_zam_btn",
              help="Zapisane już serie zostają przy tym ćwiczeniu.")


# Trzy małe przyciski w jednym rzędzie także na telefonie (Streamlit domyślnie układa kolumny jedna pod drugą).
CSS_PRZYCISKI_NAV = (
    "<style>"
    ".st-key-sesja_nav [data-testid='stHorizontalBlock']{flex-wrap:nowrap !important;gap:10px !important;}"
    ".st-key-sesja_nav [data-testid='stColumn'],.st-key-sesja_nav [data-testid='column']{min-width:0 !important;flex:1 1 0 !important;width:auto !important;}"
    ".st-key-sesja_nav button{min-height:3rem;font-size:1.4rem;font-weight:700;}"
    ".st-key-sesja_cofnij button:not(:disabled){color:var(--e-kasuj);border-color:var(--e-kasuj_ramka);}"
    ".st-key-kafelek_sesja_cw [data-testid='stHorizontalBlock']{flex-wrap:nowrap !important;gap:10px !important;}"
    ".st-key-kafelek_sesja_cw [data-testid='stColumn'],.st-key-kafelek_sesja_cw [data-testid='column']{min-width:0 !important;flex:1 1 0 !important;width:auto !important;}"
    "</style>"
)


# RPE w jednym rzędzie: dziesięć małych przycisków, kolor od zielonego (lekko) przez żółty do czerwonego (maksimum).
# Kolory skali RPE i napisów na nich są w motywy.py (zmienne --e-rpe_N i --e-rpe_t_N, osobne dla motywu jasnego i ciemnego).


def _css_rpe() -> str:
    reguly = [
        ".st-key-sesja_rpe_rzad [data-testid='stHorizontalBlock']{flex-wrap:nowrap !important;gap:3px !important;}",
        ".st-key-sesja_rpe_rzad [data-testid='stColumn'],.st-key-sesja_rpe_rzad [data-testid='column']"
        "{min-width:0 !important;flex:1 1 0 !important;width:auto !important;}",
        ".st-key-sesja_rpe_rzad button{min-height:2.3rem;padding:0 !important;font-size:0.9rem;font-weight:600;"
        "border-width:2px;background:var(--e-karta);color:var(--e-tekst);}",
    ]
    for i in range(1, 11):
        kolor, tekst = f"var(--e-rpe_{i - 1})", f"var(--e-rpe_t_{i - 1})"
        reguly.append(f".st-key-sesja_rpe_rzad [class*='st-key-sesja_rpb_{i}_'] button{{border-color:{kolor};}}")
        reguly.append(f".st-key-sesja_rpe_rzad [class*='st-key-sesja_rpb_{i}_'][class*='_zaznaczone'] button"
                      f"{{background:{kolor};color:{tekst};border-color:{kolor};}}")
    return "<style>" + "".join(reguly) + "</style>"


CSS_RPE = _css_rpe()


def _pole_rpe(nr: int) -> None:
    aktualne = st.session_state.get(f"sesja_rpe_{nr}")
    st.markdown("<span style='font-size:0.9rem;'>Jak ciężko? RPE (opcjonalnie): 1 lekko, 10 maksimum</span>", unsafe_allow_html=True)
    with st.container(key="sesja_rpe_rzad"):
        st.markdown(CSS_RPE, unsafe_allow_html=True)
        for kol, i in zip(st.columns(len(OPCJE_RPE)), OPCJE_RPE):
            klucz = f"sesja_rpb_{i}_{nr}" + ("_zaznaczone" if aktualne == i else "")
            kol.button(str(i), key=klucz, on_click=_ustaw_rpe, args=(nr, i), use_container_width=True)


def _widok_cwiczenia(stan: dict) -> None:
    nr = stan["biezace"]
    c = stan["cwiczenia"][nr]
    ile = len(stan["cwiczenia"])
    _przygotuj_pola(c, nr)
    with st.container(border=True, key="kafelek_sesja_cw"):
        st.markdown(karta_cwiczenia_html(c, nr, ile, wczytaj_notatke(c["nazwa"])), unsafe_allow_html=True)
        zob = False
        if c["jednostka"] in ("s", "m") and not pokaz_ciezar(c):
            zob = st.toggle("Z obciążeniem (kg)", key=f"sesja_zob_{nr}", help="Włącz, gdy robisz to ćwiczenie z dodatkowym ciężarem.")
        if pokaz_ciezar(c, zob):
            k1, k2 = st.columns(2)
            k1.number_input("Obciążenie (kg)", min_value=0.0, max_value=1000.0, step=KROK_CIEZARU, format="%.1f", key=f"sesja_ci_{nr}")
            k2.number_input(_etykieta_wartosci(c["jednostka"]), min_value=1, max_value=1000, step=1, key=f"sesja_po_{nr}")
        else:
            st.number_input(_etykieta_wartosci(c["jednostka"]), min_value=1, max_value=1000, step=1, key=f"sesja_po_{nr}")
        rozgrzewka = st.toggle("Seria rozgrzewkowa", key=f"sesja_rozgrz_{nr}", on_change=_przelacz_rozgrzewke, args=(nr,),
                               help="Rozgrzewka nie liczy się do planu, objętości ani rekordów i ma krótszą przerwę.")
        if not rozgrzewka:
            _pole_rpe(nr)
        st.button("Zapisz serię rozgrzewkową" if rozgrzewka else f"Zapisz serię {len(serie_robocze(c)) + 1}",
                  type="secondary" if rozgrzewka else "primary", use_container_width=True,
                  key=f"sesja_zapisz_{nr}", on_click=_zapisz_serie, args=(nr,))
        if not rozgrzewka and serie_robocze(c):
            st.button(f"Powtórz poprzednią: {opis_serii_krotko(serie_robocze(c)[-1], c['jednostka'])}", use_container_width=True,
                      key=f"sesja_powtorz_{nr}", on_click=_powtorz_serie, args=(nr,),
                      help="Zapisuje od razu serię identyczną z poprzednią (ciężar, powtórzenia i RPE) i włącza przerwę.")

    zrobione = len(serie_robocze(c)) >= c["serie_plan"]
    with st.container(key="sesja_nav"):
        st.markdown(CSS_PRZYCISKI_NAV, unsafe_allow_html=True)
        k_wstecz, k_dalej, k_cofnij = st.columns(3)
        k_wstecz.button("←", use_container_width=True, disabled=nr == 0, on_click=_przejdz, args=(-1,),
                        key="sesja_wstecz", help="Poprzednie ćwiczenie")
        k_dalej.button("→", use_container_width=True, disabled=nr >= ile - 1,
                       type="primary" if zrobione else "secondary", on_click=_przejdz, args=(1,),
                       key="sesja_dalej", help="Następne ćwiczenie")
        k_cofnij.button("↶", use_container_width=True, disabled=not c["serie"], on_click=_cofnij, args=(nr,),
                        key="sesja_cofnij", help="Cofnij ostatnią serię")
    if zrobione and nr < ile - 1:
        st.caption("To ćwiczenie jest wykonane. Przejdź do następnego albo dołóż serię.")
    if st.button("Zamień to ćwiczenie na inne", use_container_width=True, key="sesja_zam_otworz"):
        _okno_zamiany()
    with st.expander("Notatka do ćwiczenia" + (" (jest)" if wczytaj_notatke(c["nazwa"]) else "")):
        st.text_area("Notatka do ćwiczenia", key=f"sesja_nota_{nr}", height=80, label_visibility="collapsed",
                     placeholder="np. siedzisko 4, uchwyt wąski, hantle z lewej strony")
        st.button("Zapisz notatkę", use_container_width=True, key=f"sesja_nota_zapisz_{nr}", on_click=_zapisz_notatke, args=(nr,),
                  help="Notatka jest przypięta do ćwiczenia i pokaże się przy nim w każdym kolejnym treningu.")


def _panel_dodawania(stan: dict) -> None:
    pusty = not stan["cwiczenia"]
    with st.expander("Dodaj ćwiczenie albo zmień przerwy", expanded=pusty):
        st.selectbox("Ćwiczenie z bazy", baza.lista_cwiczen(), index=None, placeholder="Wybierz lub zacznij pisać...", key="sesja_dodaj_wybor")
        st.text_input("...albo wpisz własne ćwiczenie", placeholder="np. Trójskok, Plank, Podciąganie", key="sesja_dodaj_nowe")
        st.selectbox("Partia (tylko dla nowego, własnego ćwiczenia)", lista_partii(), index=len(lista_partii()) - 1, key="sesja_dodaj_partia",
                     help="Do której partii mięśniowej zaliczyć nowe ćwiczenie. Dzięki temu liczy się w „Serie na partię” w Postępach. "
                          "Dla ćwiczenia wybranego z bazy ta wartość jest pomijana.")
        st.selectbox("Jednostka (w czym liczysz)", list(JEDNOSTKI_WYBOR), key="sesja_dodaj_jednostka",
                     help="Automatycznie: jak ostatnio zapisywałeś to ćwiczenie, a gdy robisz je pierwszy raz: powtórzenia.")
        _pola_celu("sesja_dodaj")
        st.button("Dodaj do treningu", use_container_width=True, on_click=_dodaj_cwiczenie, key="sesja_dodaj_btn")
        if "sesja_przerwa" not in st.session_state:
            st.session_state["sesja_przerwa"] = stan.get("przerwa") or "Auto"
        rzad_w_jednej_linii("sesja_przerwa")
        st.segmented_control("Długość przerwy", list(OPCJE_PRZERWY), key="sesja_przerwa", on_change=_ustaw_przerwe,
                             help="Auto: 2 min po ćwiczeniach głównych, 1 min po dodatkach. Dotyczy tego treningu.")


def _widok_konca(stan: dict) -> None:
    st.markdown(podsumowanie_html(stan, datetime.now()), unsafe_allow_html=True)
    if not stan.get("typ"):
        # trening od zera: można mu nadać nazwę presetu (np. żeby pojawił się w planie tygodnia), ale nie trzeba
        from presety import lista_presetow
        opcje = [BRAK_RODZAJU] + lista_presetow()["Nazwa"].tolist()
        st.selectbox("Preset (opcjonalnie)", opcje, index=0, key="sesja_typ_konca",
                     help="Trening zaczęty od zera nie ma nazwy. Jeśli był to jeden z Twoich presetów, wybierz go.")
    st.number_input("Waga ciała (kg, opcjonalnie)", min_value=30.0, max_value=300.0, value=None, step=0.1, format="%.1f", key="sesja_waga")
    st.text_area("Komentarz do treningu", placeholder="Samopoczucie, uwagi, co poszło dobrze...", height=100, key="sesja_komentarz")
    if postep(stan)[0] == 0:
        st.warning("Nie zapisano żadnej serii. Wróć do treningu albo go porzuć.")
    k1, k2 = st.columns(2)
    k1.button("← Wróć do treningu", use_container_width=True, on_click=_wroc_do_treningu, key="sesja_wroc")
    k2.button("Zapisz trening", type="primary", use_container_width=True, disabled=postep(stan)[0] == 0,
              on_click=_zakoncz_i_zapisz, key="sesja_zapisz_trening")
    with st.expander("Zapisz ten trening jako preset"):
        if "sesja_preset_nazwa" not in st.session_state:
            st.session_state["sesja_preset_nazwa"] = (f"{stan['nazwa']} (moja wersja)" if stan.get("typ") else "Mój trening")
        if "sesja_preset_blad" in st.session_state:
            st.error(st.session_state.pop("sesja_preset_blad"))
        if "sesja_preset_info" in st.session_state:
            st.success(st.session_state.pop("sesja_preset_info"))
        st.text_input("Nazwa presetu", key="sesja_preset_nazwa")
        st.button("Zapisz preset", use_container_width=True, on_click=_zapisz_preset_ze_stanu, key="sesja_preset_btn",
                  help="Z ćwiczeń, liczby serii i zakresu powtórzeń tego treningu powstanie nowy preset na liście przy starcie "
                       "treningu. Sam trening zapisujesz osobnym przyciskiem.")
    with st.expander("Porzuć trening bez zapisu"):
        st.caption("Wszystkie serie z tego treningu przepadną.")
        st.button("Tak, porzuć trening", on_click=_porzuc, key="sesja_porzuc")


def widok_sesji() -> None:
    """Główny ekran trwającego treningu."""
    stan = _stan()
    if stan is None:
        return
    if "sesja_blad" in st.session_state:
        st.error(st.session_state.pop("sesja_blad"))
    if st.session_state.get("sesja_konczenie"):
        _widok_konca(stan)
        return

    st.markdown(CSS_PASEK, unsafe_allow_html=True)
    with st.container(key="sesja_pasek"):
        _licznik()
    if stan["cwiczenia"]:
        st.session_state["sesja_skok"] = stan["biezace"]
        st.pills("Ćwiczenia", list(range(len(stan["cwiczenia"]))), format_func=lambda i: _nazwa_pigulki(stan, i),
                 key="sesja_skok", on_change=_skocz, label_visibility="collapsed")
        _widok_cwiczenia(stan)
        _lista_cwiczen(stan)
    else:
        st.info("Ten trening nie ma jeszcze ćwiczeń. Dodaj pierwsze poniżej.")
    _panel_dodawania(stan)
    st.button("Zakończ trening", type="primary", use_container_width=True, on_click=_rozpocznij_konczenie, key="sesja_koniec")


def widok_jesli_aktywna() -> bool:
    """Wstaw na początku strony: gdy trening trwa, pokazuje go i zwraca True (strona ma wtedy zakończyć rysowanie)."""
    if aktywna():
        widok_sesji()
        return True
    komunikat = st.session_state.pop("sesja_ukonczona", None)
    if komunikat:
        st.success(komunikat)
    karta = wynik_html(st.session_state.pop("sesja_wynik", None))
    if karta:
        st.markdown(karta, unsafe_allow_html=True)
    return False


def widok_startu(typ_planu: str | None = None) -> None:
    """Start prowadzonego treningu w dowolny dzień. Jedyny wybór to preset (on jest też rodzajem treningu).
    Domyślnie zaznaczony jest preset z dzisiejszego planu, a gdy plan go nie wskazuje, ten robiony ostatnio."""
    from karty_presety import widok_presetu_html
    from plan import plan_na_dzien
    from presety import lista_presetow, wczytaj_cwiczenia_presetu, wczytaj_presety_startowe

    if widok_jesli_aktywna():
        return
    if typ_planu is None:
        dzis = plan_na_dzien()
        typ_planu = dzis["Typ"] if dzis["Aktywny"] else ""
    st.subheader("Rozpocznij trening", help="Prowadzimy Cię seria po serii: wpisujesz wynik, odliczamy przerwę, "
                                            "a na końcu wszystko zapisuje się samo.")

    wczytaj_presety_startowe()
    lista = lista_presetow()
    wiersz = None
    if not lista.empty:
        nazwy = lista["Nazwa"].tolist()
        domyslny = domyslny_preset(lista, typ_planu)
        nazwa = st.selectbox("Preset", nazwy, index=nazwy.index(domyslny) if domyslny in nazwy else 0, key="start_preset",
                             help="Gotowa rozpiska ćwiczeń. Zarazem nazwa treningu w historii i w planie tygodnia. "
                                  "Domyślnie ten z dzisiejszego planu albo ostatnio robiony.")
        wiersz = lista[lista["Nazwa"] == nazwa].iloc[0]
    zapamietana = wczytaj_ustawienie("przerwa", "Auto")
    rzad_w_jednej_linii("start_przerwa")
    st.segmented_control("Przerwy między seriami", list(OPCJE_PRZERWY), default=zapamietana if zapamietana in OPCJE_PRZERWY else "Auto",
                         key="start_przerwa",
                         help="Zapamiętuje się na kolejne treningi. W trakcie treningu możesz je zmienić, a jednym przyciskiem wyłączyć.")
    if powiadomienia.dostepne():
        st.toggle("Powiadomienie o końcu przerwy", value=powiadomienia_przerwy_wlaczone(), key="start_push_przerwa",
                  on_change=_zapisz_push_przerwy,
                  help="Gdy przerwa się skończy, telefon dostanie powiadomienie (aplikacja ntfy), także przy zablokowanym ekranie. "
                       "Pomiń, +30 s i wyłączenie przerw zmieniają je na bieżąco.")

    if wiersz is not None:
        preset_id = int(wiersz["id"])
        ostatni = ostatni_trening_rodzaju(nazwa, _tekst(wiersz["Typ"]))
        # 1) ten sam trening co ostatnio
        if ostatni:
            st.button(f"Rozpocznij: {nazwa} (jak ostatnio)", type="primary", use_container_width=True, key="start_ostatni_btn",
                      on_click=rozpocznij_z_ostatniego, args=(nazwa, _tekst(wiersz["Typ"])))
        # 2) preset w wersji z rozpiski
        st.button(f"Rozpocznij: {nazwa}" + (" (wg rozpiski)" if ostatni else ""), type="secondary" if ostatni else "primary",
                  use_container_width=True, key="start_preset_btn", on_click=rozpocznij_z_presetu, args=(preset_id,))
        # 3) lista ćwiczeń schowana w jednym panelu (nic nie zajmuje miejsca, dopóki jej nie otworzysz)
        podglad = widok_presetu_html(wiersz["Nazwa"], wiersz["Kategoria"], wiersz["Typ"], wiersz["Cel"] or "",
                                     wczytaj_cwiczenia_presetu(preset_id))
        with st.expander("Zobacz ćwiczenia"):
            if ostatni:
                data = datetime.fromisoformat(ostatni["data"]).strftime("%d.%m")
                zakladka_ostatnio, zakladka_rozpiska = st.tabs([f"Jak ostatnio ({data})", "Wg rozpiski"])
                with zakladka_ostatnio:
                    st.markdown("\n".join(f"- {c['nazwa']}" for c in ostatni["cwiczenia"]))
                with zakladka_rozpiska:
                    st.markdown(podglad, unsafe_allow_html=True)
            else:
                st.markdown(podglad, unsafe_allow_html=True)



JEDNOSTKI_KODY = ["powt.", "powt./nogę", "powt./stronę", "s", "min", "m"]


def _klucz_edycji(sesja_id: int) -> str:
    return f"hed_{sesja_id}"


def _wyczysc_edycje(sesja_id: int) -> None:
    """Czyści pola okna edycji tego treningu (żeby po X albo po zapisie nie wracały stare, niezapisane wartości)."""
    s = st.session_state
    for klucz in list(s.keys()):
        if str(klucz).startswith(_klucz_edycji(sesja_id) + "_"):
            del s[klucz]


def _zapisz_edycje(sesja_id: int) -> None:
    s = st.session_state
    k = _klucz_edycji(sesja_id)
    try:
        wpisy = s[f"{k}_df"].to_dict("records")
        typ = s.get(f"{k}_typ")
        czas = s.get(f"{k}_czas")
        zapisz_edycje_sesji(sesja_id, s[f"{k}_data"].isoformat(), "" if typ in (None, BRAK_RODZAJU) else typ,
                            s.get(f"{k}_waga"), s.get(f"{k}_kom") or "", int(czas) if czas else None, wpisy)
    except (ValueError, KeyError) as e:
        s["hist_blad"] = str(e)
        return
    _wyczysc_edycje(sesja_id)
    s["hist_info"] = "Zapisano zmiany w treningu. Kopia poprzedniej wersji jest w folderze kopie."
    s["hist_zamknij"] = True


def _usun_trening(sesja_id: int) -> None:
    st.session_state["hist_info"] = ("Trening usunięty. Kopia bazy sprzed usunięcia jest w folderze kopie."
                                     if usun_sesje(sesja_id) else "Nie znaleziono tego treningu.")
    st.session_state["hist_zamknij"] = True


def _zamknij_okno() -> None:
    st.session_state["hist_zamknij"] = True


def liczba_wpisow_samopoczucia() -> int:
    with closing(_polacz()) as db:
        try:
            return db.execute("SELECT COUNT(*) FROM samopoczucie").fetchone()[0]
        except sqlite3.OperationalError:
            return 0


def usun_wpisy_samopoczucia() -> int:
    """Kasuje wszystkie zapisane wpisy o samopoczuciu (po kopii bazy). Zwraca liczbę usuniętych."""
    ile = liczba_wpisow_samopoczucia()
    if not ile:
        return 0
    kopia_bazy("przed_usunieciem")
    with closing(_polacz()) as db:
        db.execute("DELETE FROM samopoczucie")
        db.commit()
    return ile


def _usun_samopoczucie() -> None:
    ile = usun_wpisy_samopoczucia()
    st.session_state["hist_info"] = (f"Usunięto wpisy o samopoczuciu ({ile}). Kopia bazy sprzed usunięcia jest w folderze kopie."
                                     if ile else "Nie było wpisów do usunięcia.")
    st.session_state["hist_zamknij"] = True


@st.dialog("Usunąć wszystkie wpisy o samopoczuciu?")
def okno_usuniecia_samopoczucia(ile: int) -> None:
    if st.session_state.pop("hist_zamknij", False):
        st.rerun()
    st.warning(f"Zniknie {ile} zapisanych wpisów. Pole „Jak się dziś masz?” na stronie Start zostaje. "
               "Przed usunięciem robię kopię bazy w folderze kopie.")
    k1, k2 = st.columns(2)
    k1.button("Tak, usuń", key="hist_sam_tak", on_click=_usun_samopoczucie, use_container_width=True)
    k2.button("Anuluj", key="hist_sam_nie", on_click=_zamknij_okno, use_container_width=True)


def _przemianuj() -> None:
    ile = przemianuj_stare_treningi()
    st.session_state["hist_info"] = (f"Zmieniono nazwy {ile} treningów. Kopia bazy sprzed zmiany jest w folderze kopie."
                                     if ile else "Nie było nic do zmiany.")


def _kopia_reczna() -> None:
    st.session_state["hist_info"] = f"Zrobiono kopię: {kopia_bazy('reczna').name}"


def _zapisz_preset_z_sesji(sesja_id: int) -> None:
    s = st.session_state
    nazwa = (s.get(f"hp_nazwa_{sesja_id}") or "").strip()
    try:
        utworz_preset(nazwa, cwiczenia_sesji_do_presetu(sesja_id))
    except ValueError as blad:
        s["hist_blad"] = str(blad)
        return
    s["hist_info"] = f"Zapisano preset „{nazwa}”. Znajdziesz go na liście presetów przy starcie treningu."
    s["hist_zamknij"] = True


@st.dialog("Zapisz jako preset")
def _okno_presetu(sesja_id: int, domyslna: str) -> None:
    s = st.session_state
    if s.pop("hist_zamknij", False):
        st.rerun()
    if "hist_blad" in s:
        st.error(s.pop("hist_blad"))
    st.text_input("Nazwa presetu", value=domyslna, key=f"hp_nazwa_{sesja_id}")
    k1, k2 = st.columns(2)
    k1.button("Zapisz preset", type="primary", use_container_width=True, on_click=_zapisz_preset_z_sesji, args=(sesja_id,),
              key=f"hp_zapisz_{sesja_id}",
              help="Powstanie nowy preset z ćwiczeń tego treningu (liczba serii i zakres powtórzeń z tego, co zapisałeś).")
    k2.button("Anuluj", use_container_width=True, on_click=_zamknij_okno, key=f"hp_anuluj_{sesja_id}")


@st.dialog("Edytuj trening")
def _okno_edycji(sesja_id: int) -> None:
    s = st.session_state
    if s.pop("hist_zamknij", False):
        st.rerun()
    t = wczytaj_sesje(sesja_id)
    if t is None:
        st.error("Nie znaleziono tego treningu.")
        return
    if "hist_blad" in s:
        st.error(s.pop("hist_blad"))
    k = _klucz_edycji(sesja_id)
    try:
        data = datetime.fromisoformat(t["Data"]).date()
    except (TypeError, ValueError):
        data = datetime.now().date()
    from presety import lista_presetow
    typy = [BRAK_RODZAJU] + lista_presetow()["Nazwa"].tolist()
    obecny = t["Typ_treningu"] or BRAK_RODZAJU
    if obecny not in typy:
        typy.append(obecny)   # stary rodzaj (sprzed presetów) nie ginie po cichu
    st.date_input("Data", value=data, key=f"{k}_data", format="DD.MM.YYYY")
    st.selectbox("Preset", typy, index=typy.index(obecny), key=f"{k}_typ")
    k1, k2 = st.columns(2)
    k1.number_input("Waga ciała (kg)", min_value=30.0, max_value=200.0, step=0.1, format="%.1f",
                    value=float(t["Waga"]) if t["Waga"] else None, placeholder="brak", key=f"{k}_waga")
    k2.number_input("Czas (min)", min_value=1, max_value=600, step=1, value=int(t["Czas_min"]) if t["Czas_min"] else None,
                    placeholder="brak", key=f"{k}_czas")
    st.text_area("Komentarz do treningu", value=t["Komentarz"] or "", key=f"{k}_kom", height=80)
    st.markdown("**Ćwiczenia** (klik w komórkę, żeby zmienić; kosz po zaznaczeniu wiersza usuwa, pusty wiersz na dole dodaje)")
    if f"{k}_orig" not in s:
        s[f"{k}_orig"] = pd.DataFrame(t["wpisy"], columns=["Cwiczenie", "Ciezar", "Serie", "Powtorzenia", "Jednostka"])
    nazwy = list(dict.fromkeys(list(s[f"{k}_orig"]["Cwiczenie"]) + list(baza.lista_cwiczen())))
    s[f"{k}_df"] = st.data_editor(
        s[f"{k}_orig"], key=f"{k}_tabela", num_rows="dynamic", hide_index=True, use_container_width=True,
        column_config={
            "Cwiczenie": st.column_config.SelectboxColumn("Ćwiczenie", options=nazwy, required=True),
            "Ciezar": st.column_config.NumberColumn("kg", min_value=0.0, step=0.5, format="%.1f"),
            "Serie": st.column_config.NumberColumn("Serie", min_value=1, step=1, format="%d"),
            "Powtorzenia": st.column_config.NumberColumn("Powt. / czas / dystans", min_value=1, step=1, format="%d"),
            "Jednostka": st.column_config.SelectboxColumn("Jednostka", options=JEDNOSTKI_KODY),
        },
    )
    st.caption("Zmiana ćwiczeń usuwa szczegóły RPE tego treningu.")
    st.button("Zapisz zmiany", type="primary", use_container_width=True, on_click=_zapisz_edycje, args=(sesja_id,),
              key=f"{k}_zapisz", help="Przed zapisem aplikacja robi kopię bazy w folderze kopie.")


@st.dialog("Usunąć ten trening?")
def _okno_usuniecia(sesja_id: int, opis: str) -> None:
    if st.session_state.pop("hist_zamknij", False):
        st.rerun()
    st.warning(f"{opis}: trening zniknie z historii i z Postępów. Przed usunięciem robię kopię bazy w folderze kopie.")
    k1, k2 = st.columns(2)
    k1.button("Tak, usuń", key="hist_usun_tak", on_click=_usun_trening, args=(sesja_id,), use_container_width=True)
    k2.button("Anuluj", key="hist_usun_nie", on_click=_zamknij_okno, use_container_width=True)


CSS_HISTORIA = (
    "<style>"
    ".st-key-hist_lista [data-testid='stHorizontalBlock']{flex-wrap:nowrap !important;gap:8px !important;}"
    ".st-key-hist_lista [data-testid='stColumn'],.st-key-hist_lista [data-testid='column']"
    "{min-width:0 !important;flex:1 1 0 !important;width:auto !important;}"
    "[class*='st-key-hist_u_'] button,.st-key-hist_usun_tak button,.st-key-hist_sam_usun button,.st-key-hist_sam_tak button"
    "{color:var(--e-kasuj);border-color:var(--e-kasuj_ramka);}"
    "</style>"
)


DNI_TYGODNIA = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]
MIESIACE = ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec", "sierpień", "wrzesień", "październik",
            "listopad", "grudzień"]
KOLORY_TRENINGOW = (("dół", "orange"), ("dol", "orange"), ("góra", "blue"), ("gora", "blue"), ("plyo", "violet"), ("cardio", "green"))
KROK_LISTY_TRENINGOW = 15


def kolor_treningu(nazwa: str | None) -> str:
    """Kolor nazwy treningu w liście (po początku nazwy: Dół, Góra, Plyo, Cardio; inne szare). Dzięki temu rodzaje widać bez czytania."""
    n = (nazwa or "").strip().lower()
    for poczatek, kolor in KOLORY_TRENINGOW:
        if n.startswith(poczatek):
            return kolor
    return "gray"


def _data_treningu(iso) -> tuple[str, "datetime | None"]:
    try:
        d = datetime.fromisoformat(str(iso))
        return d.strftime("%d.%m.%Y"), d
    except (TypeError, ValueError):
        return str(iso), None


def pytajnik(tekst: str) -> None:
    """Sam znaczek „?” z podpowiedzią po dotknięciu, zamiast stale widocznego szarego opisu."""
    st.markdown("&nbsp;", help=tekst)


def etykieta_treningu(t: dict) -> str:
    """Opis do nagłówka rozwijanej pozycji (Markdown): dzień tygodnia i data pogrubione, nazwa w kolorze rodzaju, czas."""
    napis, d = _data_treningu(t["Data"])
    dzien = f"**{DNI_TYGODNIA[d.weekday()][:3]}. {d.strftime('%d.%m')}**" if d else f"**{napis}**"
    nazwa = (t["Typ_treningu"] or "bez presetu").replace("[", "(").replace("]", ")")
    czesci = [dzien, f":{kolor_treningu(t['Typ_treningu'])}[**{nazwa}**]"]
    if t["Czas_min"]:
        czesci.append(f"{t['Czas_min']} min")
    return " · ".join(czesci)


def _slowo_treningow(n: int) -> str:
    if n == 1:
        return "trening"
    return "treningi" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "treningów"


def podsumowanie_historii() -> dict:
    """Liczba zapisanych treningów, ostatni trening i liczba treningów z ostatnich 30 dni (do kafelka w Historii)."""
    przygotuj_tabele()
    prog = (datetime.now() - timedelta(days=29)).date().isoformat()
    with closing(_polacz()) as db:
        ile = db.execute("SELECT COUNT(*) FROM sesje").fetchone()[0]
        ostatni = db.execute("SELECT Data, Typ_treningu, Czas_min FROM sesje ORDER BY Data DESC, id DESC LIMIT 1").fetchone()
        ile30 = db.execute("SELECT COUNT(*) FROM sesje WHERE Data >= ?", (prog,)).fetchone()[0]
    return {"ile": ile, "ile30": ile30, "ostatni": ({"Data": ostatni[0], "Typ_treningu": ostatni[1], "Czas_min": ostatni[2]}
                                                    if ostatni else None)}


def kafelek_historii_html(dane: dict) -> str:
    glowny = f"{dane['ile']} {_slowo_treningow(dane['ile'])}"
    podpis = ""
    if dane["ostatni"]:
        o = dane["ostatni"]
        napis, d = _data_treningu(o["Data"])
        dzien = f"{DNI_TYGODNIA[d.weekday()]} {d.strftime('%d.%m')}" if d else napis
        czas = f" · {o['Czas_min']} min" if o["Czas_min"] else ""
        podpis = (f'<div style="font-size:0.9rem;color:{KOLOR_PRZYGASZONY};margin-top:6px;">Ostatni: {html.escape(dzien)} · '
                  f'{html.escape(o["Typ_treningu"] or "bez presetu")}{czas}</div>'
                  f'<div style="font-size:0.9rem;color:{KOLOR_PRZYGASZONY};">W ostatnich 30 dniach: {dane["ile30"]}</div>')
    return '<div style="margin-bottom:14px;">' + _ramka(NIEBIESKI, (
        f'{_naglowek_karty("Zapisane treningi", NIEBIESKI)}'
        f'<div style="font-size:1.6rem;font-weight:700;color:{KOLOR_TEKSTU};margin-top:6px;">{glowny}</div>{podpis}')) + '</div>'


def _otworz_liste_treningow() -> None:
    st.session_state["hist_lista_otwarta"] = True
    st.session_state["hist_limit"] = KROK_LISTY_TRENINGOW


def _zamknij_liste_treningow() -> None:
    st.session_state["hist_lista_otwarta"] = False


def _pokaz_wiecej_treningow() -> None:
    st.session_state["hist_limit"] = st.session_state.get("hist_limit", KROK_LISTY_TRENINGOW) + KROK_LISTY_TRENINGOW


def _pasuje_do_szukania(t: dict, fraza: str, dzien) -> bool:
    napis, _ = _data_treningu(t["Data"])
    if dzien is not None and str(t["Data"])[:10] != dzien.isoformat():
        return False
    if not fraza:
        return True
    tekst = " ".join([napis, t["Typ_treningu"] or "", t["Komentarz"] or "", *[c["nazwa"] for c in t["cwiczenia"]]]).lower()
    return all(slowo in tekst for slowo in fraza.lower().split())


def _widok_listy_treningow() -> None:
    """Osobny ekran: wszystkie zapisane treningi ze szukaniem (nazwa, ćwiczenie, data) i wyborem dnia, od najnowszych."""
    s = st.session_state
    st.button("← Wróć do Historii", on_click=_zamknij_liste_treningow, key="hist_wroc")
    if "hist_info" in s:
        st.success(s.pop("hist_info"))
    st.text_input("Szukaj", placeholder="Nazwa treningu, ćwiczenie albo data (np. 15.10)", key="hist_szukaj",
                  label_visibility="collapsed")
    st.date_input("Albo wybierz dzień", value=None, format="DD.MM.YYYY", key="hist_dzien")
    wszystkie = historia_treningow(5000)
    if not wszystkie:
        st.info("Brak zapisanych treningów. Zacznij pierwszy na stronie Start.")
        return
    fraza = (s.get("hist_szukaj") or "").strip()
    dzien = s.get("hist_dzien")
    wyniki = [t for t in wszystkie if _pasuje_do_szukania(t, fraza, dzien)]
    if fraza or dzien:
        st.caption(f"Znaleziono: {len(wyniki)} z {len(wszystkie)}")
        if not wyniki:
            st.info("Nic nie pasuje. Spróbuj krótszej frazy albo wyczyść wybór dnia.")
    limit = s.get("hist_limit", KROK_LISTY_TRENINGOW)
    with st.container(key="hist_lista"):
        miesiac = None
        for t in wyniki[:limit]:
            napis, d = _data_treningu(t["Data"])
            if d and (d.year, d.month) != miesiac:
                miesiac = (d.year, d.month)
                st.markdown(f"##### {MIESIACE[d.month - 1].capitalize()} {d.year}")
            czesci = [napis, t["Typ_treningu"] or "bez presetu"] + ([f"{t['Czas_min']} min"] if t["Czas_min"] else [])
            opis = " · ".join(czesci)
            with st.expander(etykieta_treningu(t)):
                if t["Waga"]:
                    st.caption(f"Waga: {format_kg(t['Waga'])} kg")
                if t["Komentarz"]:
                    st.caption(f"Komentarz: {t['Komentarz']}")
                if not t["cwiczenia"]:
                    st.caption("Brak zapisanych ćwiczeń.")
                for c in t["cwiczenia"]:
                    st.markdown(f"**{c['nazwa']}**: {c['opis']}")
                if st.button("Zapisz jako preset", key=f"hist_p_{t['id']}", use_container_width=True) and t["cwiczenia"]:
                    _okno_presetu(t["id"], f"{t['Typ_treningu']} (moja wersja)" if t["Typ_treningu"] else f"Mój trening z {napis}")
                k1, k2 = st.columns(2)
                if k1.button("Edytuj", key=f"hist_e_{t['id']}", use_container_width=True,
                             on_click=_wyczysc_edycje, args=(t["id"],)):
                    _okno_edycji(t["id"])
                if k2.button("Usuń trening", key=f"hist_u_{t['id']}", use_container_width=True):
                    _okno_usuniecia(t["id"], opis)
    if len(wyniki) > limit:
        st.button(f"Pokaż starsze (jeszcze {len(wyniki) - limit})", use_container_width=True,
                  on_click=_pokaz_wiecej_treningow, key="hist_wiecej")


def widok_historii() -> None:
    """Strona Historia: jeden kafelek „Zapisane treningi” otwierający osobny ekran z listą, a pod nim jedno zwijane menu
    z narzędziami (ujednolicenie nazw, eksport, kopie zapasowe, pełna tabela)."""
    s = st.session_state
    st.markdown(CSS_HISTORIA, unsafe_allow_html=True)
    if s.get("hist_lista_otwarta"):
        _widok_listy_treningow()
        return
    if "hist_info" in s:
        st.success(s.pop("hist_info"))
    dane = podsumowanie_historii()
    if not dane["ile"]:
        st.info("Brak zapisanych treningów. Zacznij pierwszy na stronie Start.")
    else:
        st.markdown(kafelek_historii_html(dane), unsafe_allow_html=True)
        st.button("Otwórz zapisane treningi", type="primary", use_container_width=True, on_click=_otworz_liste_treningow,
                  key="hist_otworz", help="Lista od najnowszych, ze szukaniem po nazwie, ćwiczeniu i dacie.")
    do_zmiany = plan_przemianowania()
    with st.expander("Narzędzia: nazwy, eksport, kopie zapasowe" + (f" ({len(do_zmiany)} do ujednolicenia)" if do_zmiany else "")):
        if do_zmiany:
            st.markdown("**Ujednolicenie nazw starych treningów**",
                        help="Starsze treningi mają zapisany dawny rodzaj (np. „Góra Siła”), a nowe nazwę presetu. Poniżej zmiany, "
                             "które da się zrobić jednoznacznie. Przed zmianą aplikacja robi kopię bazy. Treningów, których nie da się "
                             "przypisać jednoznacznie (np. samo „Cardio” przy trzech presetach), nie ruszamy.")
            for w in do_zmiany:
                dzien, _ = _data_treningu(w["data"])
                st.markdown(f"{dzien}: **{w['stare'] or 'bez nazwy'}** → **{w['nowe']}**")
            st.button("Zmień nazwy (z kopią bazy)", use_container_width=True, on_click=_przemianuj, key="hist_przemianuj")
            st.divider()
        st.markdown("**Kopie zapasowe i eksport**",
                    help="Aplikacja robi kopię raz dziennie oraz przed każdą edycją i usunięciem treningu.")
        kopie = lista_kopii()
        ostatnia = datetime.fromtimestamp(kopie[0].stat().st_mtime).strftime("%d.%m.%Y %H:%M") if kopie else "brak"
        st.caption(f"Kopie: {len(kopie)}, ostatnia: {ostatnia}")
        dzis = datetime.now().strftime("%Y%m%d")
        st.download_button("Pobierz treningi (CSV, do Excela)", data=eksport_csv(), file_name=f"treningi_{dzis}.csv",
                           mime="text/csv", use_container_width=True, key="hist_csv")
        st.download_button("Pobierz całą bazę (plik .db)", data=plik_bazy(), file_name=f"treningi_{dzis}.db",
                           mime="application/octet-stream", use_container_width=True, key="hist_db")
        st.button("Zrób kopię teraz", use_container_width=True, on_click=_kopia_reczna, key="hist_kopia")
        if dane["ile"]:
            st.divider()
            if st.toggle("Pokaż pełną tabelę (surowe dane)", key="hist_tabela"):
                st.dataframe(baza.wczytaj_historie_sesji(), use_container_width=True, hide_index=True)
