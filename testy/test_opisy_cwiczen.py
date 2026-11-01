"""Podpowiedzi „Jak wykonać”: reguły mają się kompilować, trafiać we właściwe ćwiczenia i nie zgadywać przy niepewnych."""
from __future__ import annotations

import re

import pytest

import opisy_cwiczen as O


def test_kazda_regula_jest_kompletna_i_poprawna():
    for wzorzec, ustawienie, ruch, uwaga in O.REGULY:
        re.compile(wzorzec)
        assert ustawienie and ruch and uwaga, wzorzec


@pytest.mark.parametrize("nazwa", [
    "Hip thrust",
    "Wyciskanie sztangi na ławce płaskiej",
    "Przysiad ze sztangą",
    "Martwy ciąg",
    "Wiosłowanie sztangą w opadzie",
    "Podciąganie na drążku",
    "Pompki",
])
def test_popularne_cwiczenia_maja_opis(nazwa):
    d = O.opis(nazwa)
    assert d is not None
    assert set(d) >= {"ustawienie", "ruch", "uwaga"}


@pytest.mark.parametrize("nazwa", ["Turkish get-up", "Rwanie", "Coś zupełnie nieznanego"])
def test_niepewne_cwiczenia_bez_opisu(nazwa):
    assert O.opis(nazwa) is None


def test_rower_nie_dostaje_opisu_wioslowania():
    """Dawny błąd: wzorzec „row” łapał „rower”."""
    d = O.opis("Rower stacjonarny")
    wioslowanie = O.opis("Wiosłowanie sztangą w opadzie")
    assert d is None or d["ruch"] != wioslowanie["ruch"]


def test_wspiecia_to_lydki_a_nie_podciaganie():
    """Dawny błąd: wzorzec „spiecia” łapał „wspięcia”."""
    d = O.opis("Wspięcia na palce stojąc")
    assert d is not None
    assert "pięt" in d["ruch"].lower() or "łyd" in d["ruch"].lower()


def test_wielkosc_liter_i_ogonki_nie_maja_znaczenia():
    assert O.opis("HIP THRUST") == O.opis("hip thrust")
