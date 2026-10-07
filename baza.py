"""Wszystkie funkcje do pracy z bazą SQLite (treningi.db)."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pandas as pd

# Plik bazy leży obok tego pliku, niezależnie od tego, skąd uruchomisz aplikację
SCIEZKA_BAZY = Path(__file__).parent / "treningi.db"

# Nowe kolumny w tabeli treningi (nazwa -> typ w SQLite)
NOWE_KOLUMNY = {
    "Nazwa_cwiczenia": "TEXT",
    "Ciezar": "REAL",
    "Serie": "INTEGER",
    "Powtorzenia": "INTEGER",
}


def utworz_tabele(db: sqlite3.Connection) -> None:
    """Tworzy tabele (jeśli nie istnieją) w aktualnej strukturze."""
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS treningi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Data TEXT NOT NULL,
            Wynik_snu INTEGER,
            Czas_snu INTEGER,          -- w minutach
            RHR INTEGER,
            Waga REAL,
            Rodzaj_treningu TEXT,
            Nazwa_cwiczenia TEXT,
            Ciezar REAL,
            Serie INTEGER,
            Powtorzenia INTEGER,
            Komentarz TEXT
        )
        """
    )
    # Osobna tabela na dane z Garmina, jeden wiersz na dzień
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS garmin_dziennie (
            Data TEXT PRIMARY KEY,
            Wynik_snu INTEGER,
            Czas_snu INTEGER,          -- w minutach
            RHR INTEGER,
            HRV INTEGER
        )
        """
    )
    db.commit()


def migruj_tabele(db: sqlite3.Connection) -> None:
    """Dodaje brakujące kolumny do starej tabeli, nie ruszając istniejących danych."""
    istniejace = {wiersz[1] for wiersz in db.execute("PRAGMA table_info(treningi)")}
    for nazwa, typ in NOWE_KOLUMNY.items():
        if nazwa not in istniejace:
            db.execute(f"ALTER TABLE treningi ADD COLUMN {nazwa} {typ}")
    db.commit()


def przygotuj_baze() -> str | None:
    """Przygotowuje bazę. Zwraca tekst komunikatu, jeśli trzeba było odtworzyć plik."""
    try:
        with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
            utworz_tabele(db)
            migruj_tabele(db)
        return None
    except sqlite3.Error:
        # W razie błędu zachowujemy stary plik jako kopię (nie kasujemy go!)
        znacznik = datetime.now().strftime("%Y%m%d_%H%M%S")
        kopia = SCIEZKA_BAZY.with_name(f"treningi_kopia_{znacznik}.db")
        SCIEZKA_BAZY.replace(kopia)
        with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
            utworz_tabele(db)
        return f"Nie udało się odczytać bazy, więc stworzyłem nową. Stary plik zapisałem jako {kopia.name}."


def zapisz_trening(
    dzien: str,
    dane_garmin: dict | None,
    waga: float,
    rodzaj: str,
    cwiczenie: str,
    ciezar: float,
    serie: int,
    powtorzenia: int,
    komentarz: str,
) -> None:
    """Dodaje jeden nowy wiersz do tabeli treningi."""
    garmin = dane_garmin or {}
    czas_snu_s = garmin.get("czas_snu")
    czas_snu_min = round(czas_snu_s / 60) if czas_snu_s is not None else None

    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        db.execute(
            """
            INSERT INTO treningi
                (Data, Wynik_snu, Czas_snu, RHR, Waga, Rodzaj_treningu,
                 Nazwa_cwiczenia, Ciezar, Serie, Powtorzenia, Komentarz)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dzien,
                garmin.get("wynik_snu"),
                czas_snu_min,
                garmin.get("rhr"),
                waga,
                rodzaj,
                cwiczenie,
                ciezar,
                serie,
                powtorzenia,
                komentarz,
            ),
        )
        db.commit()


def wczytaj_historie() -> pd.DataFrame:
    """Czyta wszystkie treningi z bazy (najnowsze na górze) jako tabelę pandas."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        dane = pd.read_sql_query(
            "SELECT * FROM treningi ORDER BY Data DESC, id DESC", db
        )

    # Kolumny w ładnej kolejności; bierzemy tylko te, które istnieją
    kolejnosc = [
        "Data", "Rodzaj_treningu", "Nazwa_cwiczenia", "Ciezar", "Serie",
        "Powtorzenia", "Waga", "Wynik_snu", "Czas_snu", "RHR", "Komentarz",
    ]
    # Stara kolumna z wynikiem tekstowym: pokazujemy ją tylko, jeśli są w niej stare wpisy
    if "Wynik_cwiczenia" in dane.columns and dane["Wynik_cwiczenia"].notna().any():
        kolejnosc.append("Wynik_cwiczenia")
    return dane[[k for k in kolejnosc if k in dane.columns]]


def zapisz_dzien_garmin(dzien: str, dane: dict) -> None:
    """Zapisuje (lub aktualizuje) jeden dzień w tabeli garmin_dziennie."""
    czas_s = dane.get("czas_snu")
    czas_min = round(czas_s / 60) if czas_s is not None else None

    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        # COALESCE: jeśli nowa wartość jest pusta, zostaje stara (nie kasujemy danych)
        db.execute(
            """
            INSERT INTO garmin_dziennie (Data, Wynik_snu, Czas_snu, RHR, HRV)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(Data) DO UPDATE SET
                Wynik_snu = COALESCE(excluded.Wynik_snu, Wynik_snu),
                Czas_snu  = COALESCE(excluded.Czas_snu, Czas_snu),
                RHR       = COALESCE(excluded.RHR, RHR),
                HRV       = COALESCE(excluded.HRV, HRV)
            """,
            (dzien, dane.get("wynik_snu"), czas_min, dane.get("rhr"), dane.get("hrv")),
        )
        db.commit()


def zapisane_dni_garmin() -> set[str]:
    """Zwraca zbiór dat, które mamy już zapisane z Garmina."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        wiersze = db.execute("SELECT Data FROM garmin_dziennie").fetchall()
    return {w[0] for w in wiersze}


def wczytaj_dane_garmin_do_wykresow() -> pd.DataFrame:
    """Dane do wykresów z Garmina (sen, RHR, HRV)."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        dane = pd.read_sql_query(
            "SELECT Data, Wynik_snu, RHR, HRV FROM garmin_dziennie ORDER BY Data",
            db,
        )
    dane["Data"] = pd.to_datetime(dane["Data"])
    return dane.set_index("Data")


def wczytaj_wage_do_wykresu() -> pd.DataFrame:
    """Dane do wykresu wagi: tylko z ręcznych wpisów w formularzu."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        dane = pd.read_sql_query(
            "SELECT Data, Waga FROM treningi WHERE Waga IS NOT NULL",
            db,
        )
    if dane.empty:
        return dane
    dane["Data"] = pd.to_datetime(dane["Data"])
    # Kilka wpisów jednego dnia = średnia, żeby był jeden punkt na dzień
    return dane.groupby("Data").mean(numeric_only=True).sort_index()