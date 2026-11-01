"""Tryb demo: przykładowe dane są sensowne i powstają tylko w bazie, którą wskazano."""
from __future__ import annotations

import importlib.util
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

import pytest

import baza
import plan
import presety

_PLIK = Path(__file__).resolve().parent.parent / "narzedzia" / "demo.py"
_spec = importlib.util.spec_from_file_location("demo", _PLIK)
demo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(demo)


@pytest.fixture(scope="module")
def baza_demo(tmp_path_factory):
    """Osobna baza na demo (moduły, które zapamiętały ścieżkę przy imporcie, dostają ją na czas testu)."""
    sciezka = tmp_path_factory.mktemp("demo") / "treningi.db"
    stare = baza.SCIEZKA_BAZY, presety.SCIEZKA_BAZY, plan.SCIEZKA_BAZY
    baza.SCIEZKA_BAZY = presety.SCIEZKA_BAZY = plan.SCIEZKA_BAZY = sciezka
    try:
        demo.wypelnij(dzis=date(2026, 11, 1))
        yield sciezka
    finally:
        baza.SCIEZKA_BAZY, presety.SCIEZKA_BAZY, plan.SCIEZKA_BAZY = stare


def test_srodowisko_demo_bez_logowania_i_z_osobna_baza():
    env = demo.srodowisko()
    assert env["STRUO_BAZA"].endswith("treningi.db") and "demo" in env["STRUO_BAZA"]
    assert env["STRUO_LOGOWANIE"] == "0" and env["STRUO_DEMO"] == "1"
    assert "OVRLD_BAZA" not in env


def test_treningi_z_ostatnich_tygodni(baza_demo):
    with closing(sqlite3.connect(baza_demo)) as db:
        ile, od, do = db.execute("SELECT COUNT(*), MIN(Data), MAX(Data) FROM sesje").fetchone()
        serie = db.execute("SELECT COUNT(*) FROM serie_wykonane").fetchone()[0]
    assert 15 <= ile <= demo.TYGODNIE * len(demo.PLAN)
    assert od >= "2026-09-06" and do < "2026-11-01"
    assert serie > ile * 10


def test_ciezar_rosnie_z_tygodniami(baza_demo):
    with closing(sqlite3.connect(baza_demo)) as db:
        wiersze = db.execute(
            "SELECT s.Data, MAX(w.Ciezar) FROM serie_wykonane w JOIN sesje s ON s.id = w.Sesja_id "
            "WHERE w.Cwiczenie = 'Wyciskanie sztangi na ławce płaskiej' GROUP BY s.Data ORDER BY s.Data").fetchall()
    assert len(wiersze) >= 4
    assert wiersze[-1][1] > wiersze[0][1]


def test_profil_i_plan(baza_demo):
    with closing(sqlite3.connect(baza_demo)) as db:
        profil = dict(db.execute("SELECT Klucz, Wartosc FROM profil"))
        aktywne = db.execute("SELECT COUNT(*) FROM plan_tygodniowy WHERE Aktywny = 1").fetchone()[0]
        dni_dziennika = db.execute("SELECT COUNT(*) FROM dziennik_reczny").fetchone()[0]
    assert profil["imie"] == "Demo"
    assert aktywne == len(demo.PLAN)
    assert dni_dziennika == demo.TYGODNIE * 7
