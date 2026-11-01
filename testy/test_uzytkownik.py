"""Ustawienia logowania: nowe nazwy STRUO_* i [struo], stare OVRLD_* i [ovrld] jako zapas."""
from __future__ import annotations

import types

import pytest

import uzytkownik


class _Sekrety(dict):
    """Udaje st.secrets: brak sekcji = KeyError (jak w Streamlicie)."""


@pytest.fixture
def st(monkeypatch):
    """Podmienia Streamlita w module na prosty obiekt, żeby testy nie zależały od działającej sesji."""
    falszywy = types.SimpleNamespace(secrets=_Sekrety(), session_state={}, logout=lambda: None)
    monkeypatch.setattr(uzytkownik, "st", falszywy)
    for nazwa in ("LOGOWANIE", "WLASCICIEL", "DOZWOLONE", "BAZA"):
        monkeypatch.delenv(f"STRUO_{nazwa}", raising=False)
        monkeypatch.delenv(f"OVRLD_{nazwa}", raising=False)
    monkeypatch.setattr(uzytkownik, "secrets_uszkodzone", lambda: False)
    return falszywy


def test_env_nowa_nazwa_ma_pierwszenstwo(st, monkeypatch):
    assert uzytkownik.env("LOGOWANIE") is None
    monkeypatch.setenv("OVRLD_LOGOWANIE", "0")
    assert uzytkownik.logowanie_wymagane() is False
    monkeypatch.setenv("STRUO_LOGOWANIE", "1")
    assert uzytkownik.logowanie_wymagane() is True


def test_logowanie_wymagane_gdy_jest_sekcja_auth(st):
    assert uzytkownik.logowanie_wymagane() is False
    st.secrets["auth"] = {"client_id": "x"}
    assert uzytkownik.logowanie_wymagane() is True


def test_adresy_z_sekcji_struo_i_zapas_ovrld(st):
    st.secrets["ovrld"] = {"wlasciciel": "Ja@Example.com", "dozwolone": "a@example.com; b@example.com"}
    assert uzytkownik.dozwolone() == {"ja@example.com", "a@example.com", "b@example.com"}
    st.secrets["struo"] = {"wlasciciel": "nowy@example.com"}
    assert uzytkownik.adresy("WLASCICIEL", "wlasciciel") == {"nowy@example.com"}
    # klucza „dozwolone” nie ma w [struo], więc działa zapas z [ovrld]
    assert uzytkownik.adresy("DOZWOLONE", "dozwolone") == {"a@example.com", "b@example.com"}


def test_zmienna_srodowiskowa_wygrywa_z_plikiem(st, monkeypatch):
    st.secrets["struo"] = {"dozwolone": "plik@example.com"}
    monkeypatch.setenv("STRUO_DOZWOLONE", "env@example.com")
    assert uzytkownik.adresy("DOZWOLONE", "dozwolone") == {"env@example.com"}


def test_zaloguj_rozpoznaje_wlasciciela(st):
    st.secrets["struo"] = {"wlasciciel": "ja@example.com"}
    stan = uzytkownik.zaloguj("  JA@example.com ")
    assert stan["wlasciciel"] is True
    assert stan["email"] == "ja@example.com"
    assert uzytkownik.zalogowany() and uzytkownik.czy_wlasciciel()
    uzytkownik.wyloguj_sesje()
    assert not uzytkownik.zalogowany()


def test_id_folderu_nie_ujawnia_adresu(st):
    ident = uzytkownik.id_z_adresu("Ja@Example.com")
    assert ident == uzytkownik.id_z_adresu("ja@example.com")
    assert "@" not in ident and "example" not in ident
    assert len(ident) == 25 and ident.startswith("u")


@pytest.mark.parametrize("nazwa", ["STRUO_BAZA", "OVRLD_BAZA"])
def test_konto_goscia_nie_jest_wlascicielem(st, monkeypatch, nazwa):
    monkeypatch.setenv(nazwa, "/tmp/gosc.db")
    assert uzytkownik.czy_wlasciciel() is False
