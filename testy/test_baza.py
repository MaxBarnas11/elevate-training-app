"""Baza danych: przygotowanie jest bezpieczne do powtarzania, a uszkodzony plik nie ginie."""
from __future__ import annotations

import sqlite3
from contextlib import closing

import baza


def test_przygotowanie_mozna_powtarzac(baza_testowa):
    with closing(sqlite3.connect(baza_testowa)) as db:
        przed = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        cwiczen_przed = db.execute("SELECT COUNT(*) FROM cwiczenia").fetchone()[0]
    assert baza.przygotuj_baze() is None
    with closing(sqlite3.connect(baza_testowa)) as db:
        po = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        cwiczen_po = db.execute("SELECT COUNT(*) FROM cwiczenia").fetchone()[0]
    assert przed == po
    assert cwiczen_przed == cwiczen_po, "drugie uruchomienie nie może drugi raz importować ćwiczeń"


def test_baza_ma_cwiczenia_i_flagi_migracji(baza_testowa):
    with closing(sqlite3.connect(baza_testowa)) as db:
        assert db.execute("SELECT COUNT(*) FROM cwiczenia").fetchone()[0] > 700
        assert db.execute("SELECT COUNT(*) FROM ustawienia").fetchone()[0] >= 1


def test_uszkodzony_plik_zostaje_jako_kopia(tmp_path, monkeypatch):
    zepsuty = tmp_path / "treningi.db"
    zepsuty.write_bytes(b"to nie jest baza SQLite" * 100)
    monkeypatch.setattr(baza, "SCIEZKA_BAZY", zepsuty)
    komunikat = baza.przygotuj_baze()
    assert komunikat and "kopi" in komunikat.lower()
    kopie = list(tmp_path.glob("treningi_kopia_*.db"))
    assert len(kopie) == 1 and kopie[0].read_bytes().startswith(b"to nie jest")
    with closing(sqlite3.connect(zepsuty)) as db:
        db.execute("SELECT 1 FROM sqlite_master").fetchall()
