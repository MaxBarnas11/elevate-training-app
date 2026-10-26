"""Dokładniejsze partie nóg i typ ćwiczenia (wielostawowe albo izolowane).

Partia mówi, CO zostało obciążone. Typ mówi, JAK MOCNO ćwiczenie męczy cały organizm: wielostawowe (przysiad, martwy ciąg,
wyciskanie) to więcej zmęczenia niż izolowane (prostowanie nóg, uginanie ramion). Typ używają rekomendacje (rekomendacje.py).
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata

WIELOSTAWOWE = "Wielostawowe"
IZOLOWANE = "Izolowane"

# Dawna partia „Nogi” rozbita na cztery (plus przywodziciele); None w typie = rozpoznaj po nazwie
NOGI = {
    "Przysiad ze sztangą": "Czworogłowe", "Przysiad przedni": "Czworogłowe", "Przysiad kielichowy (goblet)": "Czworogłowe",
    "Przysiad bułgarski": "Czworogłowe", "Przysiad na jednej nodze na skrzynię": "Czworogłowe",
    "Wypychanie na suwnicy (obunóż)": "Czworogłowe", "Wyciskanie na suwnicy na jedną nogę": "Czworogłowe",
    "Wykroki chodzone": "Czworogłowe", "Wykroki w miejscu": "Czworogłowe", "Wykroki w tył": "Pośladki",
    "Wejścia na podwyższenie (step-up)": "Czworogłowe", "Prostowanie nóg na maszynie": "Czworogłowe",
    "RDL (rumuński martwy ciąg)": "Dwugłowe uda", "Martwy ciąg jednonóż z hantlą (single-leg RDL)": "Dwugłowe uda",
    "Martwy ciąg na prostych nogach": "Dwugłowe uda", "Martwy ciąg": "Dwugłowe uda", "Good morning": "Dwugłowe uda",
    "Uginanie nóg leżąc": "Dwugłowe uda", "Uginanie nóg na maszynie": "Dwugłowe uda",
    "Hip thrust": "Pośladki", "Hip thrust na jednej nodze": "Pośladki", "Odwodziciele na maszynie": "Pośladki",
    "Przywodziciele na maszynie": "Przywodziciele",
    "Wspięcia na palce stojąc": "Łydki", "Wspięcia na palce siedząc": "Łydki",
    "Spacer farmera jednorącz": "Cały",
}
# Poprawki ćwiczeń, które wylądowały w „Inne”
Z_INNE = {"Ściąganie drążka do klatki piersiowej": "Plecy", "Chód na bieżni": "Cardio"}

# Partie, w których typ ćwiczenia nie ma sensu (czas, dystans, skoki)
BEZ_TYPU = {"Cardio", "Plyometria", "Cały", "Inne", "Brzuch"}
# Fragmenty nazw ćwiczeń izolowanych (małe, jednostawowe)
IZOLOWANE_FRAZY = (
    "rozpiętki", "uginanie ramion", "prostowanie ramion", "wznosy", "face pulls", "szrugsy", "prostowanie nóg", "uginanie nóg",
    "wspięcia", "przywodziciele", "odwodziciele", "ściąganie warkocza", "ściąganie drążka na wyciągu", "francuskie",
    "na prostych ramionach", "maszyna do spięć", "allahy", "bayesian",
)


def typ_cwiczenia(nazwa: str, partia: str | None) -> str | None:
    """Wielostawowe albo izolowane (po partii i nazwie); None dla cardio, plyometrii, ćwiczeń na czas i nieznanych partii."""
    if not partia or partia in BEZ_TYPU - {"Brzuch"}:
        return None
    n = nazwa.lower()
    if any(fraza in n for fraza in IZOLOWANE_FRAZY):
        return IZOLOWANE
    return None if partia == "Brzuch" else WIELOSTAWOWE


def migruj(db: sqlite3.Connection) -> None:
    """Przypisuje dokładniejsze partie nóg i typy ćwiczeniom z bazy. Bezpieczne do wielokrotnego uruchamiania:
    rusza tylko ćwiczenia, które nadal mają dawną partię „Nogi” (albo „Inne” z listy poprawek) i puste typy."""
    kolumny = {w[1] for w in db.execute("PRAGMA table_info(cwiczenia)")}
    if not kolumny or "Typ" not in kolumny:
        return
    for nazwa, nowa in NOGI.items():
        db.execute("UPDATE cwiczenia SET Partia = ? WHERE Nazwa = ? AND Partia = 'Nogi'", (nowa, nazwa))
    for nazwa, nowa in Z_INNE.items():
        db.execute("UPDATE cwiczenia SET Partia = ? WHERE Nazwa = ? AND Partia = 'Inne'", (nowa, nazwa))
    # ćwiczenia z dawną partią „Nogi”, których nie znamy (własne): do „Inne”, żeby przypisać je w Postępach
    db.execute("UPDATE cwiczenia SET Partia = 'Inne' WHERE Partia = 'Nogi'")
    for nazwa, partia in db.execute("SELECT Nazwa, Partia FROM cwiczenia WHERE Typ IS NULL").fetchall():
        typ = typ_cwiczenia(nazwa, partia)
        if typ:
            db.execute("UPDATE cwiczenia SET Typ = ? WHERE Nazwa = ?", (typ, nazwa))


# --- Plecy i Barki rozbite na części, waga partii dodatkowych ----------------------------------------------------------
# Serie liczą się do partii głównej za 1, a do każdej partii dodatkowej za 0,5 (np. wyciskanie leżąc: klatka 1,
# triceps i barki przód po 0,5). Plecy i barki to kilka różnych mięśni, więc mają własne części.
WAGA_DODATKOWEJ = 0.5
PLECY = ("Plecy szerokie", "Plecy górne", "Plecy dolne")
BARKI = ("Barki przód", "Barki bok", "Barki tył")
FLAGA_PODZIALU = "partie_podzial_v1"


def rodzina(partia: str) -> str:
    """„Plecy szerokie” → „Plecy”, „Barki bok” → „Barki”; pozostałe partie bez zmian (do rekomendacji, które nie rozróżniają części)."""
    p = partia or ""
    return "Plecy" if p.startswith("Plecy") else "Barki" if p.startswith("Barki") else p


def _n(tekst: str) -> str:
    t = (tekst or "").lower().replace("ł", "l")
    return "".join(z for z in unicodedata.normalize("NFKD", t) if not unicodedata.combining(z))


def _ma(t: str, *frazy: str) -> bool:
    return any(f in t for f in frazy)


_WIERSZ = re.compile(r"\brows?\b")


def plecy_czesc(tekst: str) -> str:
    """Która część pleców pracuje w ćwiczeniu (po nazwie polskiej i angielskim aliasie): dolne, szerokie albo górne (domyślnie)."""
    t = _n(tekst)
    if _ma(t, "deadlift", "martwy ciag", "hyperextension", "back extension", "prostowanie tulowia", "good morning", "superman",
           "reverse hyper", "rack pull"):
        return "Plecy dolne"
    if _WIERSZ.search(t) or "wioslow" in t or "srodek plecow" in t:
        return "Plecy górne"
    if _ma(t, "pulldown", "pull-up", "pullup", "pull up", "chin-up", "chinup", "chin up", "lat pull", "pullover", "podciag",
           "sciaganie", "wiszenie", "muscle-up", "muscle up", "rope climb", "straight-arm", "na prostych ramionach", " lats"):
        return "Plecy szerokie"
    return "Plecy górne"


def _dopelnienie_plecow(tekst: str, czesc: str) -> str | None:
    """Druga część pleców, która pracuje obok głównej (wiosłowanie: szerokie, ściąganie: górne, martwy ciąg: górne)."""
    t = _n(tekst)
    if _ma(t, "shrug", "szrugs", "wiszenie", "hang", "upright", "wzdluz tulowia"):
        return None
    return {"Plecy górne": "Plecy szerokie", "Plecy szerokie": "Plecy górne", "Plecy dolne": "Plecy górne"}.get(czesc)


def barki_czesc(tekst: str) -> str:
    """Która część barków pracuje: tył (odwrócone, face pull), bok (wznosy bokiem, upright row) albo przód (wyciskanie, wznosy przodem)."""
    t = _n(tekst)
    if _ma(t, "rear", "reverse", "bent over", "bent-over", "face pull", "pull apart", "external rotation", "row to neck", "back fly",
           "back flye", "odwrocone", "tylne", "w opadzie", "tyl barku", "na brzuchu", "straight raises"):
        return "Barki tył"
    if _ma(t, "lateral", "side raise", "upright row", "bokiem", "high pull", "scaption", "crucifix", "krucyfiks"):
        return "Barki bok"
    return "Barki przód"


def przelicz_partie(tekst: str, partia: str, dod: str) -> tuple[str, str]:
    """Ćwiczenie z ogólną partią „Plecy”/„Barki” (jako główną albo dodatkową) -> nowa partia główna i dodatkowe z częściami.
    `tekst` to nazwa polska i angielskie aliasy. Partie już rozbite i inne zostają bez zmian."""
    nowa = plecy_czesc(tekst) if partia == "Plecy" else barki_czesc(tekst) if partia == "Barki" else partia
    wynik: list[str] = []

    def dodaj(p: str | None) -> None:
        if p and p != nowa and p not in wynik:
            wynik.append(p)

    for d in [x.strip() for x in (dod or "").split(",") if x.strip()]:
        if d == "Plecy":
            dodaj(plecy_czesc(tekst))
        elif d == "Barki":     # barki przy ćwiczeniach na plecy i ciągnięcie to tył, przy wyciskaniu przód, przy podciąganiu wzdłuż tułowia bok
            if _ma(_n(tekst), "upright row", "high pull", "wzdluz tulowia"):
                dodaj("Barki bok")
            else:
                dodaj("Barki tył" if rodzina(nowa) in ("Plecy", "Biceps", "Przedramiona", "Szyja") else "Barki przód")
        else:
            dodaj(d)
    if partia == "Plecy":
        dodaj(_dopelnienie_plecow(tekst, nowa))
    return nowa, ",".join(wynik)


def _jest_ogolna(partia: str | None, dod: str | None) -> bool:
    return partia in ("Plecy", "Barki") or any(x.strip() in ("Plecy", "Barki") for x in (dod or "").split(","))


def zmiany_podzialu(db: sqlite3.Connection) -> list[tuple[str, str, str]]:
    """Ćwiczenia z ogólnymi partiami „Plecy”/„Barki”, z nowymi wartościami: [(nazwa, partia, partie dodatkowe)]. Nic nie zapisuje."""
    kolumny = {w[1] for w in db.execute("PRAGMA table_info(cwiczenia)")}
    if "Partia" not in kolumny:
        return []
    kol_dod = "Partia_dod" if "Partia_dod" in kolumny else "NULL"
    wiersze = db.execute(f"SELECT Nazwa, Partia, {kol_dod} FROM cwiczenia").fetchall()
    wiersze = [w for w in wiersze if _jest_ogolna(w[1], w[2])]
    if not wiersze:
        return []
    aliasy: dict[str, list[str]] = {}
    try:
        for a, n in db.execute("SELECT Alias, Nazwa FROM cwiczenia_aliasy"):
            aliasy.setdefault(n, []).append(a)
    except sqlite3.OperationalError:
        pass
    wynik = []
    for nazwa, partia, dod in wiersze:
        nowa, nowe_dod = przelicz_partie(" ".join([nazwa, *aliasy.get(nazwa, [])]), partia, dod or "")
        wynik.append((nazwa, nowa, nowe_dod))
    return wynik


def zastosuj_podzial(db: sqlite3.Connection, zmiany: list[tuple[str, str, str]]) -> None:
    kolumny = {w[1] for w in db.execute("PRAGMA table_info(cwiczenia)")}
    for nazwa, partia, dod in zmiany:
        if "Partia_dod" in kolumny:
            db.execute("UPDATE cwiczenia SET Partia = ?, Partia_dod = ? WHERE Nazwa = ?", (partia, dod, nazwa))
        else:
            db.execute("UPDATE cwiczenia SET Partia = ? WHERE Nazwa = ?", (partia, nazwa))


def wagi_partii(partia: str | None, dod: str | None) -> dict[str, float]:
    """{partia: waga serii}: główna 1, każda dodatkowa 0,5. Ogólne „Plecy”/„Barki” (stare dane) liczymy jak górne plecy i przód barków."""
    ogolne = {"Plecy": "Plecy górne", "Barki": "Barki przód"}
    wynik: dict[str, float] = {}
    if partia:
        wynik[ogolne.get(partia, partia)] = 1.0
    for d in (dod or "").split(","):
        d = ogolne.get(d.strip(), d.strip())
        if d and d not in wynik:
            wynik[d] = WAGA_DODATKOWEJ
    return wynik


def wagi_cwiczen(db: sqlite3.Connection) -> dict[str, dict[str, float]]:
    """Nazwa ćwiczenia -> {partia: waga} z bazy (puste i brakujące partie to „Inne” z wagą 1)."""
    kolumny = {w[1] for w in db.execute("PRAGMA table_info(cwiczenia)")}
    if "Partia" not in kolumny:
        return {}
    kol_dod = "Partia_dod" if "Partia_dod" in kolumny else "NULL"
    return {n: wagi_partii(p or "Inne", d) for n, p, d in db.execute(f"SELECT Nazwa, Partia, {kol_dod} FROM cwiczenia")}
