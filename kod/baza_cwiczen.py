"""Duża baza ćwiczeń: import polskiej listy (dane_cwiczen.json), aliasy do wyszukiwania i wybór ćwiczenia z filtrami.

Dane pochodzą z free-exercise-db (domena publiczna, The Unlicense), nazwy przetłumaczone na polski, braki (końcówki wyciągów,
typy maszyn, skrzynie plyo, cardio, boks) dopisane ręcznie. Import jest bezpieczny dla historii: ćwiczenia, które już masz, zostają
pod swoimi nazwami (tylko uzupełniamy im sprzęt, partie dodatkowe i typ), a przed pierwszym importem powstaje kopia bazy.
"""
from __future__ import annotations

import json
import sqlite3
import unicodedata
from contextlib import closing
from datetime import datetime
from pathlib import Path

PLIK_DANYCH = Path(__file__).parent / "dane_cwiczen.json"
FLAGA = "baza_cwiczen_v1"
KOLUMNY = {"Partia_dod": "TEXT", "Sprzet": "TEXT", "Rodzaj": "TEXT", "Poziom": "TEXT", "Jednostka_dom": "TEXT",
           "Ukryte": "INTEGER", "Zrodlo": "TEXT"}
WSZYSTKIE = "Wszystkie"
# Kategorie ruchu do szybkiego zawężania listy (wg partii głównej ćwiczenia)
KATEGORIE = {
    "Pchanie": ("Klatka", "Barki przód", "Barki bok", "Triceps"),
    "Ciągnięcie": ("Plecy szerokie", "Plecy górne", "Plecy dolne", "Barki tył", "Biceps", "Przedramiona", "Szyja"),
    "Nogi": ("Czworogłowe", "Dwugłowe uda", "Pośladki", "Łydki", "Przywodziciele"),
    "Brzuch": ("Brzuch",),
    "Cardio i skoki": ("Cardio", "Plyometria", "Cały"),
}


def _kopia(db: sqlite3.Connection, sciezka: Path | None) -> None:
    """Kopia bazy przed pierwszym importem (folder kopie obok bazy)."""
    if not sciezka or not Path(sciezka).exists():
        return
    folder = Path(sciezka).parent / "kopie"
    folder.mkdir(exist_ok=True)
    cel = folder / f"treningi_przed_baza_cwiczen_{datetime.now():%Y%m%d_%H%M%S}.db"
    db.commit()
    with closing(sqlite3.connect(cel)) as cel_db:
        db.backup(cel_db)


def _dane() -> list[dict]:
    try:
        return json.loads(PLIK_DANYCH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def importuj(db: sqlite3.Connection) -> int:
    """Dodaje ćwiczenia z pliku danych. Zwraca liczbę nowych ćwiczeń. Istniejących nie zmienia poza uzupełnieniem pustych pól
    i partii „Inne”, więc historia i presety zostają nietknięte."""
    from cwiczenia_meta import typ_cwiczenia
    nowe = 0
    for r in _dane():
        w = db.execute("SELECT Partia, Typ FROM cwiczenia WHERE Nazwa = ?", (r["nazwa"],)).fetchone()
        if w is None:
            typ = r["typ"] or typ_cwiczenia(r["nazwa"], r["partia"])
            db.execute("INSERT INTO cwiczenia (Nazwa, Partia, Typ, Partia_dod, Sprzet, Rodzaj, Poziom, Jednostka_dom, Ukryte, Zrodlo) "
                       "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'baza')",
                       (r["nazwa"], r["partia"], typ, r["dod"], r["sprzet"], r["rodzaj"], r["poziom"], r["jednostka"], r["ukryte"]))
            nowe += 1
        else:
            partia, typ_obecny = w
            db.execute(
                "UPDATE cwiczenia SET Partia_dod = COALESCE(NULLIF(Partia_dod, ''), ?), Sprzet = COALESCE(NULLIF(Sprzet, ''), ?), "
                "Rodzaj = COALESCE(NULLIF(Rodzaj, ''), ?), Poziom = COALESCE(NULLIF(Poziom, ''), ?), "
                "Jednostka_dom = COALESCE(NULLIF(Jednostka_dom, ''), ?), Ukryte = 0 WHERE Nazwa = ?",
                (r["dod"], r["sprzet"], r["rodzaj"], r["poziom"], r["jednostka"], r["nazwa"]))
            if partia in (None, "", "Inne") and r["partia"] != "Inne":
                db.execute("UPDATE cwiczenia SET Partia = ? WHERE Nazwa = ?", (r["partia"], r["nazwa"]))
                partia = r["partia"]
            if not typ_obecny:
                typ = r["typ"] or typ_cwiczenia(r["nazwa"], partia)
                if typ:
                    db.execute("UPDATE cwiczenia SET Typ = ? WHERE Nazwa = ?", (typ, r["nazwa"]))
        for alias in {_norma(r["en"]), _norma(r["nazwa"])} - {""}:
            db.execute("INSERT OR IGNORE INTO cwiczenia_aliasy (Alias, Nazwa) VALUES (?, ?)", (alias, r["nazwa"]))
    return nowe


def _odkryj_uzywane(db: sqlite3.Connection) -> None:
    """Ćwiczenia, które były już robione albo są w presetach, nigdy nie są ukryte."""
    tabele = {w[0] for w in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "wpisy_cwiczen" in tabele:
        db.execute("UPDATE cwiczenia SET Ukryte = 0 WHERE Ukryte = 1 AND Nazwa IN (SELECT Cwiczenie FROM wpisy_cwiczen)")
    if "presety_cwiczenia" in tabele:
        db.execute("UPDATE cwiczenia SET Ukryte = 0 WHERE Ukryte = 1 AND Nazwa IN (SELECT Cwiczenie FROM presety_cwiczenia)")


def przygotuj(db: sqlite3.Connection, sciezka_bazy: Path | None = None) -> None:
    """Kolumny, tabela aliasów i jednorazowy import. Bezpieczne do wielokrotnego uruchamiania."""
    istniejace = {w[1] for w in db.execute("PRAGMA table_info(cwiczenia)")}
    if not istniejace:
        return
    for nazwa, typ in KOLUMNY.items():
        if nazwa not in istniejace:
            db.execute(f"ALTER TABLE cwiczenia ADD COLUMN {nazwa} {typ}")
    db.execute("CREATE TABLE IF NOT EXISTS cwiczenia_aliasy (Alias TEXT, Nazwa TEXT, PRIMARY KEY (Alias, Nazwa))")
    db.execute("CREATE TABLE IF NOT EXISTS ustawienia (Klucz TEXT PRIMARY KEY, Wartosc TEXT)")
    if not db.execute("SELECT 1 FROM ustawienia WHERE Klucz = ?", (FLAGA,)).fetchone() and _dane():
        _kopia(db, sciezka_bazy)
        importuj(db)
        db.execute("INSERT OR REPLACE INTO ustawienia (Klucz, Wartosc) VALUES (?, '1')", (FLAGA,))
    _odkryj_uzywane(db)
    _podziel_plecy_i_barki(db, sciezka_bazy)
    import korekty_cwiczen
    if korekty_cwiczen.zastosuj(db, sciezka_bazy):
        _odkryj_uzywane(db)          # ukrycie dziwnych ćwiczeń nie dotyczy tych, które już robisz


def _podziel_plecy_i_barki(db: sqlite3.Connection, sciezka_bazy: Path | None) -> None:
    """Ogólne „Plecy” i „Barki” (partia główna i dodatkowe) zamieniamy na ich części (szerokie/górne/dolne, przód/bok/tył).
    Idempotentne: rusza tylko ćwiczenia, które jeszcze mają ogólną nazwę; przed pierwszą zmianą powstaje kopia bazy."""
    from cwiczenia_meta import FLAGA_PODZIALU, zastosuj_podzial, zmiany_podzialu
    zmiany = zmiany_podzialu(db)
    if not zmiany:
        return
    if not db.execute("SELECT 1 FROM ustawienia WHERE Klucz = ?", (FLAGA_PODZIALU,)).fetchone():
        _kopia(db, sciezka_bazy)
        db.execute("INSERT OR REPLACE INTO ustawienia (Klucz, Wartosc) VALUES (?, '1')", (FLAGA_PODZIALU,))
    zastosuj_podzial(db, zmiany)


# --- wyszukiwanie ------------------------------------------------------------
def _norma(tekst: str) -> str:
    """Małe litery bez polskich znaków (żeby „sciaganie” znalazło „ściąganie”)."""
    t = (tekst or "").lower().replace("ł", "l")
    return "".join(z for z in unicodedata.normalize("NFKD", t) if not unicodedata.combining(z)).strip()


def _kat(kategoria) -> str | None:
    """Kategoria jako tekst lub None (przyciski Streamlita bywają zwracane jako lista z jednym elementem)."""
    if isinstance(kategoria, (list, tuple, set)):
        kategoria = next(iter(kategoria), None)
    return kategoria if isinstance(kategoria, str) and kategoria in KATEGORIE else None


def _rdzen(slowo: str) -> str:
    """Obcina końcówkę fleksyjną, żeby „wiosłowanie” znalazło też „wiosłowania”, a „przysiady” – „przysiad”."""
    return slowo[:-2] if len(slowo) >= 7 else slowo[:-1] if len(slowo) >= 5 else slowo


def wszystkie(db: sqlite3.Connection) -> list[dict]:
    """Wszystkie ćwiczenia z bazy jako słowniki (nazwa, partia, dodatkowe, sprzęt, typ, ukryte, tekst do szukania, maszyny).
    `maszyny`: konkretne maszyny, na których zrobisz ćwiczenie (moduł maszyny); `opis_sprzetu`: nazwa maszyny albo rodzaj sprzętu."""
    import maszyny
    kolumny = {w[1] for w in db.execute("PRAGMA table_info(cwiczenia)")}
    if "Sprzet" not in kolumny:
        return [{"nazwa": n, "partia": p or "Inne", "dod": "", "sprzet": "", "rodzaj": "", "typ": "", "ukryte": 0,
                 "szukaj": _norma(n), "uzycia": 0, "maszyny": (), "opis_sprzetu": ""}
                for (n, p) in db.execute("SELECT Nazwa, Partia FROM cwiczenia ORDER BY rowid")]
    aliasy: dict[str, list[str]] = {}
    try:
        for a, n in db.execute("SELECT Alias, Nazwa FROM cwiczenia_aliasy"):
            aliasy.setdefault(n, []).append(a)
    except sqlite3.OperationalError:
        pass
    uzycia: dict[str, int] = {}
    try:
        for n, k in db.execute("SELECT Cwiczenie, COUNT(*) FROM wpisy_cwiczen GROUP BY Cwiczenie"):
            uzycia[n] = k
    except sqlite3.OperationalError:
        pass
    wynik = []
    for n, p, dod, sp, rodz, typ, uk in db.execute(
            "SELECT Nazwa, Partia, Partia_dod, Sprzet, Rodzaj, Typ, Ukryte FROM cwiczenia ORDER BY rowid"):
        ids = maszyny.maszyny_cwiczenia(n, sp or "", " ".join(aliasy.get(n, [])))
        tekst = " ".join([_norma(n), *aliasy.get(n, []), _norma(sp or ""), _norma(p or ""), maszyny.tekst_do_szukania(ids)])
        opis = maszyny.PO_ID[ids[0]].nazwa if len(ids) == 1 else (sp or "")
        wynik.append({"nazwa": n, "partia": p or "Inne", "dod": dod or "", "sprzet": sp or "", "rodzaj": rodz or "",
                      "typ": typ or "", "ukryte": int(uk or 0), "szukaj": tekst, "uzycia": uzycia.get(n, 0),
                      "maszyny": ids, "opis_sprzetu": opis})
    return wynik


def filtruj(lista: list[dict], szukaj: str = "", partia: str = WSZYSTKIE, sprzet: str = WSZYSTKIE,
            zaawansowane: bool = False, zachowaj: str | None = None, kategoria: str | None = None,
            dozwolony_sprzet: set[str] | None = None, ulubione: set[str] | None = None) -> list[dict]:
    """Ćwiczenia pasujące do filtrów. Kolejność: ulubione, potem najczęściej robione, potem alfabetycznie. Wybrane wcześniej
    (zachowaj) zostaje. dozwolony_sprzet: tylko ćwiczenia ze sprzętem (i maszynami) z tego zbioru (profil „Moja siłownia”, zob.
    maszyny.dostepne); None = bez ograniczenia."""
    from maszyny import dostepne
    slowa = [_rdzen(w) for w in _norma(szukaj).split()]
    kategoria = _kat(kategoria)
    wynik = []
    for c in lista:
        if c["nazwa"] == zachowaj:
            wynik.append(c)
            continue
        if c["ukryte"] and not zaawansowane:
            continue
        if kategoria and c["partia"] not in KATEGORIE[kategoria]:
            continue
        if partia != WSZYSTKIE and partia != c["partia"] and partia not in c["dod"].split(","):
            continue
        if sprzet != WSZYSTKIE and sprzet != c["sprzet"]:
            continue
        if not dostepne(c, dozwolony_sprzet):
            continue
        if slowa and not all(s in c["szukaj"] for s in slowa):
            continue
        wynik.append(c)
    ulubione = ulubione or set()
    wynik.sort(key=lambda c: (c["nazwa"] not in ulubione, -min(c["uzycia"], 1), -c["uzycia"], _norma(c["nazwa"])))
    return wynik


def podobne(lista: list[dict], nazwa: str, dozwolony_sprzet: set[str] | None = None, ulubione: set[str] | None = None,
            ile: int = 8) -> list[dict]:
    """Ćwiczenia zastępujące dane: ta sama partia główna i ten sam rodzaj (np. siłowe), tylko sprzęt, który masz.
    Wyżej: ten sam typ ruchu (wielostawowe/izolowane), inny sprzęt niż w oryginale (zajęta sztanga → hantle lub maszyna),
    wspólne partie dodatkowe, ulubione i te, które już robiłeś."""
    from maszyny import dostepne
    obecne = next((c for c in lista if c["nazwa"] == nazwa), None)
    if obecne is None:
        return []
    ulubione = ulubione or set()
    dod = set(filter(None, obecne["dod"].split(",")))
    wynik = []
    for c in lista:
        if c["nazwa"] == nazwa or c["ukryte"] or c["partia"] != obecne["partia"]:
            continue
        if obecne["rodzaj"] and c["rodzaj"] and c["rodzaj"] != obecne["rodzaj"]:
            continue
        if not dostepne(c, dozwolony_sprzet):
            continue
        punkty = 0
        if obecne["typ"] and c["typ"] == obecne["typ"]:
            punkty += 4
        if c["sprzet"] != obecne["sprzet"]:
            punkty += 2
        punkty += len(dod & set(filter(None, c["dod"].split(","))))
        punkty += 3 if _norma(c["nazwa"]).split()[:1] == _norma(nazwa).split()[:1] else 0     # ten sam ruch (np. „Wyciskanie …”)
        punkty += 3 if c["nazwa"] in ulubione else 0
        punkty += 2 if c["uzycia"] else 0
        wynik.append((punkty, c))
    wynik.sort(key=lambda x: (-x[0], -x[1]["uzycia"], _norma(x[1]["nazwa"])))
    # Różnorodność: najwyżej dwa ćwiczenia na rodzaj sprzętu (inaczej lista to same wariacje hantli), resztę dopełniamy po kolei
    kolejne = [c for _, c in wynik]
    wybrane, na_sprzet = [], {}
    for c in kolejne:
        if na_sprzet.get(c["sprzet"], 0) < 2:
            wybrane.append(c)
            na_sprzet[c["sprzet"]] = na_sprzet.get(c["sprzet"], 0) + 1
    wybrane += [c for c in kolejne if c not in wybrane]
    return wybrane[:ile]


def nazwy_widoczne(db: sqlite3.Connection) -> list[str]:
    """Do prostych list wyboru: ćwiczenia nieukryte (najpierw Twoje, w kolejności dodawania)."""
    return [c["nazwa"] for c in wszystkie(db) if not c["ukryte"]]


def partie_i_sprzet(lista: list[dict], kategoria: str | None = None) -> tuple[list[str], list[str]]:
    """Partie i sprzęt do filtrów; z kategorią tylko te, które w niej występują."""
    kategoria = _kat(kategoria)
    lista = [c for c in lista if not kategoria or c["partia"] in KATEGORIE[kategoria]]
    partie = sorted({c["partia"] for c in lista if not c["ukryte"]} - {"Inne"})
    sprzet = sorted({c["sprzet"] for c in lista if c["sprzet"] and not c["ukryte"]})
    return partie + (["Inne"] if any(c["partia"] == "Inne" for c in lista) else []), sprzet
