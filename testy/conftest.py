"""Wspólne ustawienia testów.

Testy sprawdzają logikę bez interfejsu (bez uruchamiania Streamlita w przeglądarce). Każde uruchomienie dostaje własny,
tymczasowy plik bazy: zmienna STRUO_BAZA jest ustawiana, zanim zostanie zaimportowany jakikolwiek moduł aplikacji,
więc testy nigdy nie dotykają prawdziwego treningi.db.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

import pytest

KOD = Path(__file__).resolve().parent.parent / "kod"
sys.path.insert(0, str(KOD))

_TMP = Path(tempfile.mkdtemp(prefix="struo_testy_"))
os.environ["STRUO_BAZA"] = str(_TMP / "treningi.db")
os.environ.pop("OVRLD_BAZA", None)


@pytest.fixture(scope="session")
def baza_testowa() -> Path:
    """Świeża baza z pełną listą ćwiczeń i presetami startowymi (tworzona raz na całe uruchomienie testów)."""
    import baza
    import presety
    import sesja_treningowa

    assert str(baza.SCIEZKA_BAZY).startswith(str(_TMP)), "testy muszą pracować na bazie tymczasowej"
    assert baza.przygotuj_baze() is None
    sesja_treningowa.przygotuj_tabele()
    presety.wczytaj_presety_startowe()
    return Path(baza.SCIEZKA_BAZY)


@pytest.fixture(scope="session")
def cwiczenia(baza_testowa) -> list[dict]:
    """Lista ćwiczeń tak, jak widzi ją aplikacja."""
    import baza_cwiczen

    with closing(sqlite3.connect(baza_testowa)) as db:
        return baza_cwiczen.wszystkie(db)
