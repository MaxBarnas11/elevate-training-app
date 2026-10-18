"""Tygodniowy plan treningowy: tabela w bazie i proste funkcje do zapisu i odczytu.

Plan to szablon Pon-Niedz: dla każdego dnia czy jest trening, jaki rodzaj,
opcjonalnie godzina i notatka. Plik jest samodzielny (jak presety.py).
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import date, timedelta

import pandas as pd

from baza import SCIEZKA_BAZY

NAZWY_DNI = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
SKROTY_DNI = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]


def nazwa_krotka(nazwa: str | None) -> str:
    """Krótka nazwa do małych kafelków: 'Góra 1: Push (klatka i barki)' -> 'Góra 1'."""
    return (nazwa or "").split(":")[0].strip()


def _utworz_tabele(db: sqlite3.Connection) -> None:
    db.execute(
        "CREATE TABLE IF NOT EXISTS plan_tygodniowy ("
        "Dzien INTEGER PRIMARY KEY, "          # 0 = poniedziałek ... 6 = niedziela
        "Aktywny INTEGER NOT NULL DEFAULT 0, "  # 1 = trening, 0 = odpoczynek
        "Typ TEXT, Godzina TEXT, Notatka TEXT)"
    )
    for dzien in range(7):
        db.execute("INSERT OR IGNORE INTO plan_tygodniowy (Dzien, Aktywny) VALUES (?, 0)", (dzien,))


def wczytaj_plan() -> pd.DataFrame:
    """Zawsze 7 wierszy (Pn-Nd). Kolumny: Dzien, Aktywny (bool), Typ, Godzina, Notatka."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        _utworz_tabele(db)
        db.commit()
        plan = pd.read_sql_query(
            "SELECT Dzien, Aktywny, Typ, Godzina, Notatka FROM plan_tygodniowy ORDER BY Dzien", db
        )
    plan["Aktywny"] = plan["Aktywny"].astype(bool)
    for kolumna in ("Typ", "Godzina", "Notatka"):
        plan[kolumna] = plan[kolumna].fillna("")
    return plan


def zapisz_plan(dni: list[dict]) -> None:
    """Zapisuje cały plan. Każdy element: {Dzien, Aktywny, Typ, Godzina, Notatka}.
    Dla dnia odpoczynku Typ i Godzina są czyszczone, żeby nie zostawały śmieci."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        _utworz_tabele(db)
        for d in dni:
            aktywny = bool(d.get("Aktywny"))
            db.execute(
                "UPDATE plan_tygodniowy SET Aktywny = ?, Typ = ?, Godzina = ?, Notatka = ? WHERE Dzien = ?",
                (
                    1 if aktywny else 0,
                    (d.get("Typ") or "") if aktywny else "",
                    (d.get("Godzina") or "") if aktywny else "",
                    (d.get("Notatka") or "").strip(),
                    int(d["Dzien"]),
                ),
            )
        db.commit()


def plan_na_dzien(dzien: date | None = None) -> dict:
    """Plan na podany dzień (domyślnie dziś) jako słownik. Aktywny=False oznacza odpoczynek."""
    dzien = dzien or date.today()
    wiersz = wczytaj_plan().iloc[dzien.weekday()]
    return {
        "Dzien": int(wiersz["Dzien"]),
        "Nazwa": NAZWY_DNI[int(wiersz["Dzien"])],
        "Aktywny": bool(wiersz["Aktywny"]),
        "Typ": wiersz["Typ"],
        "Godzina": wiersz["Godzina"],
        "Notatka": wiersz["Notatka"],
    }


def liczba_dni_treningowych() -> int:
    return int(wczytaj_plan()["Aktywny"].sum())

def podsumowanie_tygodnia(dzis: date | None = None) -> dict:
    """Bieżący tydzień (Pn-Nd): plan kontra zapisane treningi. Dane do kafelka na stronie Start."""
    dzis = dzis or date.today()
    poniedzialek = dzis - timedelta(days=dzis.weekday())
    niedziela = poniedzialek + timedelta(days=6)
    plan = wczytaj_plan()

    treningi: dict[str, dict] = {}   # data ISO -> {"typ": ..., "objetosc": ...}
    ostatni = None
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        try:
            # Objętość liczymy tylko z ćwiczeń na powtórzenia (spacer farmera w metrach czy bieganie w minutach nie mają sensu jako kg × powt.)
            kolumny_wpisow = {w[1] for w in db.execute("PRAGMA table_info(wpisy_cwiczen)")}
            warunek = ("CASE WHEN COALESCE(w.Jednostka, 'powt.') LIKE 'powt%' THEN w.Ciezar * w.Serie * w.Powtorzenia ELSE 0 END"
                       if "Jednostka" in kolumny_wpisow else "w.Ciezar * w.Serie * w.Powtorzenia")
            wiersze = db.execute(
                f"SELECT s.Data, s.Typ_treningu, COALESCE(SUM({warunek}), 0) "
                "FROM sesje s LEFT JOIN wpisy_cwiczen w ON w.Sesja_id = s.id "
                "WHERE s.Data BETWEEN ? AND ? GROUP BY s.id",
                (poniedzialek.isoformat(), niedziela.isoformat()),
            ).fetchall()
            ostatni = db.execute("SELECT MAX(Data) FROM sesje WHERE Data <= ?", (dzis.isoformat(),)).fetchone()[0]
        except sqlite3.OperationalError:
            wiersze = []   # tabele jeszcze nie istnieją
    for data, typ, objetosc in wiersze:
        wpis = treningi.setdefault(data, {"typ": typ, "objetosc": 0.0})
        wpis["objetosc"] += float(objetosc or 0)

    dni = []
    for i in range(7):
        dzien = poniedzialek + timedelta(days=i)
        wiersz = plan.iloc[i]
        dni.append({
            "skrot": SKROTY_DNI[i],
            "data": dzien,
            "planowany": bool(wiersz["Aktywny"]),
            "typ": nazwa_krotka(treningi.get(dzien.isoformat(), {}).get("typ") or wiersz["Typ"]),
            "zrobiony": dzien.isoformat() in treningi,
            "dzis": dzien == dzis,
            "przeszlosc": dzien < dzis,
        })

    zaplanowane = sum(d["planowany"] for d in dni)
    # zaległe: zaplanowane dni sprzed dzisiaj bez zapisanego treningu
    zalegle = sum(d["planowany"] and d["przeszlosc"] and not d["zrobiony"] for d in dni)
    return {
        "dni": dni,
        "wykonane": len(treningi),
        "zaplanowane": zaplanowane,
        "zalegle": zalegle,
        "dni_od_ostatniego": (dzis - date.fromisoformat(ostatni)).days if ostatni else None,
        "objetosc_kg": sum(t["objetosc"] for t in treningi.values()),
    }


def trening_zapisany(dzien: date | None = None) -> bool:
    """Czy na podany dzień (domyślnie dziś) jest już zapisany jakikolwiek trening."""
    dzien = dzien or date.today()
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        try:
            return db.execute("SELECT 1 FROM sesje WHERE Data = ? LIMIT 1", (dzien.isoformat(),)).fetchone() is not None
        except sqlite3.OperationalError:
            return False   # tabela jeszcze nie istnieje
