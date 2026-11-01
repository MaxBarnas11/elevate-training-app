"""Każdy moduł aplikacji da się zaimportować (łapie literówki i brakujące importy po porządkach w kodzie)."""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

MODULY = sorted(p.stem for p in (Path(__file__).resolve().parent.parent / "kod").glob("*.py"))


@pytest.mark.parametrize("nazwa", MODULY)
def test_modul_sie_importuje(nazwa):
    importlib.import_module(nazwa)
