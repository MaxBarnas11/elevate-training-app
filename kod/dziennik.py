"""Ręczny dziennik dnia dla osób bez zegarka: sen (godziny), waga i energia (1-5). Jeden wiersz na dzień."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import date

import pandas as pd

import baza

ENERGIA = {1: "Bardzo niska", 2: "Niska", 3: "Średnia", 4: "Dobra", 5: "Świetna"}


def _polacz() -> sqlite3.Connection:
    db = sqlite3.connect(baza.SCIEZKA_BAZY)
    db.execute(
        "CREATE TABLE IF NOT EXISTS dziennik_reczny ("
        "Data TEXT PRIMARY KEY, Sen_godz REAL, Waga REAL, Energia INTEGER)"
    )
    return db


def zapisz(data: date, sen_godz: float | None = None, waga: float | None = None, energia: int | None = None) -> None:
    """Zapisuje wpis dnia. Puste pola nie kasują wcześniejszych wartości tego dnia."""
    if sen_godz is None and waga is None and energia is None:
        return
    with closing(_polacz()) as db:
        db.execute(
            "INSERT INTO dziennik_reczny (Data, Sen_godz, Waga, Energia) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(Data) DO UPDATE SET "
            "Sen_godz = COALESCE(excluded.Sen_godz, Sen_godz), "
            "Waga = COALESCE(excluded.Waga, Waga), "
            "Energia = COALESCE(excluded.Energia, Energia)",
            (data.isoformat(), sen_godz, waga, energia),
        )
        db.commit()


def dzien(data: date | None = None) -> dict:
    """Wpis z danego dnia (domyślnie dzisiaj) albo pusty słownik."""
    data = data or date.today()
    with closing(_polacz()) as db:
        w = db.execute("SELECT Sen_godz, Waga, Energia FROM dziennik_reczny WHERE Data = ?", (data.isoformat(),)).fetchone()
    if not w:
        return {}
    return {"Sen_godz": w[0], "Waga": w[1], "Energia": w[2]}


def wczytaj() -> pd.DataFrame:
    """Wszystkie wpisy; indeks: data (Timestamp), kolumny Sen_godz, Waga, Energia."""
    with closing(_polacz()) as db:
        dane = pd.read_sql_query("SELECT Data, Sen_godz, Waga, Energia FROM dziennik_reczny ORDER BY Data", db)
    dane["Data"] = pd.to_datetime(dane["Data"])
    return dane.set_index("Data")


def waga_do_wykresu() -> pd.Series:
    """Waga z dziennika jako seria (do połączenia z wagą z treningów)."""
    d = wczytaj()
    return d["Waga"].dropna() if not d.empty else pd.Series(dtype=float)
