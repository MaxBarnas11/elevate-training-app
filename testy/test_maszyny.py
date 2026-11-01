"""Filtr sprzętu i maszyn: co da się zrobić na mojej siłowni."""
from __future__ import annotations

import maszyny as M


def test_bez_filtra_wszystko_dostepne():
    assert M.dostepne({"sprzet": "Sztanga"}, None) is True


def test_filtr_po_rodzaju_sprzetu():
    dozwolony = {"Hantle", "Masa ciała"}
    assert M.dostepne({"sprzet": "Hantle"}, dozwolony)
    assert not M.dostepne({"sprzet": "Sztanga"}, dozwolony)


def test_bez_wybranych_maszyn_zbior_sie_nie_zmienia():
    assert M.zbior_dozwolony({"Hantle"}, []) == {"Hantle"}
    assert M.zbior_dozwolony(None, []) is None


def test_cwiczenie_na_maszynie_wymaga_tej_maszyny():
    pierwsza, druga = M.KATALOG[0], next(m for m in M.KATALOG[1:] if m.sprzet == M.KATALOG[0].sprzet and m.id != M.KATALOG[0].id)
    dozwolony = M.zbior_dozwolony({pierwsza.sprzet}, [pierwsza.id])
    na_pierwszej = {"sprzet": pierwsza.sprzet, "maszyny": (pierwsza.id,)}
    na_drugiej = {"sprzet": druga.sprzet, "maszyny": (druga.id,)}
    bez_maszyny = {"sprzet": pierwsza.sprzet}
    assert M.dostepne(na_pierwszej, dozwolony)
    assert not M.dostepne(na_drugiej, dozwolony)
    assert M.dostepne(bez_maszyny, dozwolony), "ćwiczenie bez przypisanej maszyny zależy tylko od sprzętu"


def test_nieznane_id_maszyny_jest_pomijane():
    assert M.zbior_dozwolony({"Hantle"}, ["nie-ma-takiej"]) == {"Hantle"}
