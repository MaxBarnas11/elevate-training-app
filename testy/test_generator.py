"""Generator „Trening na dziś”: reguły, nie losowanie. Te same dane wejściowe dają ten sam trening."""
from __future__ import annotations

import pytest

import generator as G


@pytest.fixture(scope="module")
def dane(cwiczenia):
    return cwiczenia, G.poziomy_cwiczen(), {c["nazwa"]: c for c in cwiczenia}


def _nazwy(trening: dict) -> list[str]:
    return [p.nazwa for p in trening["pozycje"]]


@pytest.mark.parametrize("czas", G.CZASY)
@pytest.mark.parametrize("grupy", [["Klatka"], ["Klatka", "Barki", "Triceps"], ["Plecy", "Biceps"], ["Nogi", "Pośladki", "Łydki", "Brzuch"]])
def test_podstawowe_zasady(dane, czas, grupy):
    lista, poziomy, _ = dane
    warianty = G.trzy_warianty(lista, poziomy, G.Ustawienia(cel=G.CEL_MASA, czas=czas), grupy)
    assert 1 <= len(warianty) <= 3
    partie = {p for g in grupy for p in G.GRUPY[g]}
    for t in warianty:
        nazwy = _nazwy(t)
        assert nazwy, "trening nie może być pusty"
        assert len(nazwy) == len(set(nazwy)), "bez powtórzonych ćwiczeń"
        assert len(nazwy) <= G.MAX_CWICZEN[czas], "limit ćwiczeń dla czasu"
        assert all(p.partia in partie for p in t["pozycje"]), "tylko wybrane partie"


def test_trzy_rozne_propozycje(dane):
    lista, poziomy, _ = dane
    warianty = G.trzy_warianty(lista, poziomy, G.Ustawienia(cel=G.CEL_MASA, czas=75), ["Klatka", "Barki", "Triceps"])
    assert len(warianty) == 3
    assert len({frozenset(_nazwy(t)) for t in warianty}) == 3


def test_ten_sam_wynik_przy_tych_samych_danych(dane):
    lista, poziomy, _ = dane
    u = G.Ustawienia(cel=G.CEL_SILA, czas=60)
    pierwszy = [_nazwy(t) for t in G.trzy_warianty(lista, poziomy, u, ["Plecy", "Biceps"])]
    drugi = [_nazwy(t) for t in G.trzy_warianty(lista, poziomy, u, ["Plecy", "Biceps"])]
    assert pierwszy == drugi


def test_uloz_inne_daje_inne_zestawy(dane):
    lista, poziomy, _ = dane
    u = G.Ustawienia(cel=G.CEL_MASA, czas=75)
    raz = {frozenset(_nazwy(t)) for t in G.trzy_warianty(lista, poziomy, u, ["Klatka", "Barki", "Triceps"])}
    dwa = {frozenset(_nazwy(t)) for t in G.trzy_warianty(lista, poziomy, u, ["Klatka", "Barki", "Triceps"], 1)}
    assert not raz & dwa


def test_tylko_dostepny_sprzet(dane):
    lista, poziomy, po_nazwie = dane
    dozwolony = frozenset({"Hantle", "Maszyna", "Masa ciała", ""})
    u = G.Ustawienia(cel=G.CEL_MASA, czas=60, dozwolony=dozwolony)
    for t in G.trzy_warianty(lista, poziomy, u, ["Klatka", "Plecy"]):
        for nazwa in _nazwy(t):
            assert po_nazwie[nazwa]["sprzet"] in dozwolony, nazwa


def test_brak_sprzetu_daje_uwage_a_nie_blad(dane):
    lista, poziomy, _ = dane
    t = G.uloz_dzis(lista, poziomy, G.Ustawienia(dozwolony=frozenset({"Piłka lekarska"})), ["Klatka"])
    assert t["uwagi"]


def test_krotszy_czas_to_mniej_cwiczen(dane):
    lista, poziomy, _ = dane
    krotki = G.uloz_dzis(lista, poziomy, G.Ustawienia(czas=45), ["Klatka", "Plecy", "Nogi"])
    dlugi = G.uloz_dzis(lista, poziomy, G.Ustawienia(czas=90), ["Klatka", "Plecy", "Nogi"])
    assert len(krotki["pozycje"]) < len(dlugi["pozycje"])


def test_najwyzej_dwa_ulubione(dane):
    lista, poziomy, _ = dane
    klatka = [c["nazwa"] for c in lista if c["partia"] == "Klatka" and not c["ukryte"] and c["rodzaj"] == "Siłowe"][:8]
    t = G.uloz_dzis(lista, poziomy, G.Ustawienia(cel=G.CEL_MASA, ulubione=frozenset(klatka), czas=30), ["Klatka"])
    assert sum(p.etykieta == "ulubione" for p in t["pozycje"]) == G.LIMIT_ULUBIONYCH
