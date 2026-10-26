"""Presety treningów: tabele w bazie, wczytanie danych startowych i edycja.

Dane startowe leżą w presety_dane.py, a ten plik zajmuje się bazą SQLite.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing

import pandas as pd

from baza import SCIEZKA_BAZY

# Jednostki do wyboru w edytorze (powtórzenia, czas, dystans)
JEDNOSTKI = ["powt.", "powt./nogę", "powt./stronę", "s", "m", "min"]
# Rola ćwiczenia w treningu: główne (max 5) albo dodatek do dołożenia
ROLE = ["Główne", "Dodatek"]
MAKS_GLOWNYCH = 5


def _utworz_tabele(db: sqlite3.Connection) -> None:
    """Tworzy tabele presetów, jeśli ich jeszcze nie ma."""
    # Migracja z pierwszej wersji (bez kolumny Rola): usuwamy stare tabele, dane wczytają się od nowa
    kolumny = [w[1] for w in db.execute("PRAGMA table_info(presety_cwiczenia)").fetchall()]
    if kolumny and "Rola" not in kolumny:
        db.execute("DROP TABLE presety_cwiczenia")
        db.execute("DROP TABLE IF EXISTS presety")
    db.execute(
        "CREATE TABLE IF NOT EXISTS presety ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "Nazwa TEXT NOT NULL UNIQUE, "
        "Typ TEXT, "
        "Kategoria TEXT, "
        "Cel TEXT, "
        "Kolejnosc INTEGER NOT NULL DEFAULT 0)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS presety_cwiczenia ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "Preset_id INTEGER NOT NULL, "
        "Kolejnosc INTEGER NOT NULL, "
        "Cwiczenie TEXT NOT NULL, "
        "Serie INTEGER, Powt_od INTEGER, Powt_do INTEGER, "
        "Jednostka TEXT NOT NULL DEFAULT 'powt.', "
        "Alternatywa TEXT, Wskazowka TEXT, "
        "Rola TEXT NOT NULL DEFAULT 'Główne')"
    )


def _dodaj_typ_jesli_brak(db: sqlite3.Connection, nazwa: str) -> None:
    """Dopisuje rodzaj treningu do listy rodzajów, jeśli go tam jeszcze nie ma."""
    db.execute(
        "INSERT INTO typy_treningu (Nazwa, Kolejnosc) "
        "SELECT ?, COALESCE((SELECT MAX(Kolejnosc) FROM typy_treningu), 0) + 1 "
        "WHERE NOT EXISTS (SELECT 1 FROM typy_treningu WHERE Nazwa = ?)",
        (nazwa, nazwa),
    )


def _dodaj_cwiczenie_jesli_brak(db: sqlite3.Connection, nazwa: str, partia: str) -> None:
    """Dopisuje ćwiczenie do bazy ćwiczeń, jeśli go tam jeszcze nie ma."""
    db.execute(
        "INSERT INTO cwiczenia (Nazwa, Partia) SELECT ?, ? "
        "WHERE NOT EXISTS (SELECT 1 FROM cwiczenia WHERE Nazwa = ?)",
        (nazwa, partia, nazwa),
    )


def _wstaw_preset(db: sqlite3.Connection, preset: dict, kolejnosc: int) -> None:
    """Wstawia jeden preset z ćwiczeniami (rodzaj treningu i brakujące ćwiczenia dopisuje do bazy)."""
    kursor = db.execute(
        "INSERT INTO presety (Nazwa, Typ, Kategoria, Cel, Kolejnosc) VALUES (?, ?, ?, ?, ?)",
        (preset["Nazwa"], preset["Typ"], preset["Kategoria"], preset["Cel"], kolejnosc),
    )
    preset_id = kursor.lastrowid
    _dodaj_typ_jesli_brak(db, preset["Typ"])
    for numer, c in enumerate(preset["Cwiczenia"], start=1):
        db.execute(
            "INSERT INTO presety_cwiczenia "
            "(Preset_id, Kolejnosc, Cwiczenie, Serie, Powt_od, Powt_do, Jednostka, Alternatywa, Wskazowka, Rola) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (preset_id, numer, c["Cwiczenie"], c["Serie"], c["Powt_od"], c["Powt_do"],
             c["Jednostka"], c["Alternatywa"], c["Wskazowka"], c["Rola"]),
        )
        _dodaj_cwiczenie_jesli_brak(db, c["Cwiczenie"], c["Partia"])


def _wczytaj_pakiety(db: sqlite3.Connection) -> None:
    """Dokłada pakiety presetów (krótkie treningi, sporty) RAZ na pakiet. Presetów, które już masz
    (także o tej samej nazwie), nie rusza, a usunięte pakiety nie wracają."""
    from presety_dane import PAKIETY

    db.execute("CREATE TABLE IF NOT EXISTS ustawienia (Klucz TEXT PRIMARY KEY, Wartosc TEXT)")
    for flaga, pakiet in PAKIETY.items():
        if db.execute("SELECT 1 FROM ustawienia WHERE Klucz = ?", (flaga,)).fetchone():
            continue
        istniejace = {w[0] for w in db.execute("SELECT Nazwa FROM presety")}
        numer = db.execute("SELECT COALESCE(MAX(Kolejnosc), 0) FROM presety").fetchone()[0]
        for preset in pakiet:
            if preset["Nazwa"] in istniejace:
                continue
            numer += 1
            _wstaw_preset(db, preset, numer)
        db.execute("INSERT OR REPLACE INTO ustawienia (Klucz, Wartosc) VALUES (?, '1')", (flaga,))
    db.commit()


def _zamien_w_json(wartosc, stara: str, nowa: str):
    """Zamienia w strukturze JSON (listy, słowniki) każdy tekst równy starej nazwie."""
    if isinstance(wartosc, str):
        return nowa if wartosc == stara else wartosc
    if isinstance(wartosc, list):
        return [_zamien_w_json(x, stara, nowa) for x in wartosc]
    if isinstance(wartosc, dict):
        return {k: _zamien_w_json(v, stara, nowa) for k, v in wartosc.items()}
    return wartosc


def _przemianuj_presety(db: sqlite3.Connection) -> None:
    """Jednorazowo zamienia dawne nazwy presetów (np. „Góra 1: Push (klatka i barki)”) na zrozumiałe
    („Góra push: klatka i barki”) w presetach, historii treningów, planie i trwającym treningu.
    Przed zmianą robi kopię bazy. Preset o nowej nazwie, który już istnieje, zostaje nietknięty."""
    import json
    from datetime import datetime
    from pathlib import Path

    from presety_dane import PRZEMIANOWANIA

    flaga = "presety_nazwy_v2"
    db.execute("CREATE TABLE IF NOT EXISTS ustawienia (Klucz TEXT PRIMARY KEY, Wartosc TEXT)")
    if db.execute("SELECT 1 FROM ustawienia WHERE Klucz = ?", (flaga,)).fetchone():
        return
    istnieje = {w[0] for w in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    obecne = {w[0] for w in db.execute("SELECT Nazwa FROM presety")}
    do_zmiany = {s: n for s, n in PRZEMIANOWANIA.items() if s in obecne and n not in obecne}
    if do_zmiany and Path(SCIEZKA_BAZY).exists():
        folder = Path(SCIEZKA_BAZY).parent / "kopie"
        folder.mkdir(exist_ok=True)
        db.commit()
        with closing(sqlite3.connect(folder / f"treningi_przed_nazwami_presetow_{datetime.now():%Y%m%d_%H%M%S}.db")) as kopia:
            db.backup(kopia)
    for stara, nowa in do_zmiany.items():
        db.execute("UPDATE presety SET Nazwa = ? WHERE Nazwa = ?", (nowa, stara))
        if "sesje" in istnieje:
            db.execute("UPDATE sesje SET Typ_treningu = ? WHERE Typ_treningu = ?", (nowa, stara))
            kolumny = [w[1] for w in db.execute("PRAGMA table_info(sesje)")]
            if "Preset" in kolumny:
                db.execute("UPDATE sesje SET Preset = ? WHERE Preset = ?", (nowa, stara))
        if "plan_tygodniowy" in istnieje:
            db.execute("UPDATE plan_tygodniowy SET Typ = ? WHERE Typ = ?", (nowa, stara))
        if "trening_w_toku" in istnieje:
            for id_, dane in db.execute("SELECT id, Dane FROM trening_w_toku").fetchall():
                try:
                    zmienione = json.dumps(_zamien_w_json(json.loads(dane), stara, nowa), ensure_ascii=False)
                except ValueError:
                    continue
                if zmienione != dane:
                    db.execute("UPDATE trening_w_toku SET Dane = ? WHERE id = ?", (zmienione, id_))
    db.execute("INSERT OR REPLACE INTO ustawienia (Klucz, Wartosc) VALUES (?, '1')", (flaga,))
    db.commit()


def _kategorie_sportowe(db: sqlite3.Connection) -> None:
    """Jednorazowo: presety sportowe ze wspólną kategorią „Sport” dostają kategorię swojej dyscypliny (z rodzaju, np. „Sport Tenis”)."""
    from presety_dane import SPORTY

    flaga = "presety_kategorie_sport_v1"
    db.execute("CREATE TABLE IF NOT EXISTS ustawienia (Klucz TEXT PRIMARY KEY, Wartosc TEXT)")
    if db.execute("SELECT 1 FROM ustawienia WHERE Klucz = ?", (flaga,)).fetchone():
        return
    for dyscyplina in SPORTY:
        db.execute("UPDATE presety SET Kategoria = ? WHERE Kategoria = 'Sport' AND Typ = ?", (dyscyplina, f"Sport {dyscyplina}"))
    db.execute("INSERT OR REPLACE INTO ustawienia (Klucz, Wartosc) VALUES (?, '1')", (flaga,))
    db.commit()


def wczytaj_presety_startowe() -> None:
    """Wczytuje presety z presety_dane.py: podstawowe tylko gdy tabela presetów jest pusta, pakiety dodatkowe raz.
    Dzięki temu Twoje zmiany nigdy nie są nadpisywane przy kolejnym uruchomieniu."""
    from presety_dane import PRESETY

    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        _utworz_tabele(db)
        if db.execute("SELECT COUNT(*) FROM presety").fetchone()[0] == 0:
            for numer, preset in enumerate(PRESETY, start=1):
                _wstaw_preset(db, preset, numer)
            db.commit()
        _przemianuj_presety(db)
        _wczytaj_pakiety(db)
        _kategorie_sportowe(db)


def lista_presetow() -> pd.DataFrame:
    """Lista presetów w kolejności z rozpiski."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        _utworz_tabele(db)
        return pd.read_sql_query(
            "SELECT id, Nazwa, Typ, Kategoria, Cel FROM presety ORDER BY Kolejnosc, id", db
        )


def wczytaj_cwiczenia_presetu(preset_id: int) -> pd.DataFrame:
    """Ćwiczenia jednego presetu w ustalonej kolejności."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        _utworz_tabele(db)
        return pd.read_sql_query(
            "SELECT Cwiczenie, Rola, Serie, Powt_od, Powt_do, Jednostka, Alternatywa, Wskazowka "
            "FROM presety_cwiczenia WHERE Preset_id = ? ORDER BY Kolejnosc, id",
            db,
            params=(preset_id,),
        )


def _liczba(wartosc) -> int | None:
    return None if pd.isna(wartosc) else int(wartosc)


def _tekst(wartosc) -> str:
    return "" if pd.isna(wartosc) else str(wartosc).strip()


def zapisz_cwiczenia_presetu(preset_id: int, dane: pd.DataFrame) -> None:
    """Zastępuje ćwiczenia presetu zawartością edytora. Kolejność wierszy = kolejność ćwiczeń.
    Nowe nazwy ćwiczeń trafiają też do bazy ćwiczeń (partia 'Inne')."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        _utworz_tabele(db)
        db.execute("DELETE FROM presety_cwiczenia WHERE Preset_id = ?", (preset_id,))
        kolejnosc = 0
        # główne na górze, dodatki pod nimi (kolejność w obrębie grup zostaje)
        dane = dane.copy()
        dane["_dodatek"] = dane["Rola"].map(lambda r: _tekst(r) == "Dodatek")
        dane = dane.sort_values("_dodatek", kind="stable")
        for _, wiersz in dane.iterrows():
            nazwa = _tekst(wiersz["Cwiczenie"])
            if not nazwa:
                continue  # pusty wiersz z edytora pomijamy
            kolejnosc += 1
            jednostka = _tekst(wiersz["Jednostka"]) or "powt."
            rola = _tekst(wiersz["Rola"])
            rola = rola if rola in ROLE else "Główne"
            db.execute(
                "INSERT INTO presety_cwiczenia "
                "(Preset_id, Kolejnosc, Cwiczenie, Serie, Powt_od, Powt_do, Jednostka, Alternatywa, Wskazowka, Rola) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (preset_id, kolejnosc, nazwa, _liczba(wiersz["Serie"]), _liczba(wiersz["Powt_od"]),
                 _liczba(wiersz["Powt_do"]), jednostka, _tekst(wiersz["Alternatywa"]),
                 _tekst(wiersz["Wskazowka"]), rola),
            )
            _dodaj_cwiczenie_jesli_brak(db, nazwa, "Inne")
        db.commit()
        