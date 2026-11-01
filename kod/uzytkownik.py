"""Użytkownik aplikacji: kto korzysta i gdzie leżą jego dane.

Bez logowania (praca lokalna, jak dotąd) dane leżą w treningi.db obok aplikacji. Po zalogowaniu każda osoba ma własny folder
dane/<id>/ z własną bazą, a konto właściciela (adres z ustawień) używa dotychczasowego treningi.db, więc jego dane nie wymagają
żadnych przenosin. Gdy logowanie jest wymagane (STRUO_LOGOWANIE=1 albo sekcja [auth] w secrets.toml), a nikt nie jest
zalogowany, dane nie są nigdy zwracane: zamiast ścieżki leci wyjątek BrakUzytkownika.

Ustawienia: zmienne środowiskowe STRUO_* i sekcja [struo] w secrets.toml. Dawne nazwy (OVRLD_* i [ovrld]) działają dalej
jako zapas, więc stara konfiguracja nie przestaje działać po zmianie nazwy projektu.
"""
from __future__ import annotations

import hashlib
import os
import tomllib
from pathlib import Path

import streamlit as st

# Główny folder aplikacji (tam leżą treningi.db, dane/, kopie/, .env, ntfy_temat.txt); ten plik leży w kod/, więc o jeden poziom wyżej.
FOLDER_APLIKACJI = Path(__file__).resolve().parent.parent
KLUCZ_SESJI = "struo_uzytkownik"


class BrakUzytkownika(RuntimeError):
    """Logowanie jest wymagane, ale nikt nie jest zalogowany."""


def _stan() -> dict | None:
    try:
        return st.session_state.get(KLUCZ_SESJI)
    except Exception:   # noqa: BLE001 (poza sesją Streamlita, np. w skryptach i testach)
        return None


def _sekret(sekcja: str, klucz: str) -> str:
    try:
        return str(st.secrets[sekcja][klucz])
    except Exception:   # noqa: BLE001 (brak pliku secrets.toml albo klucza)
        return ""


def env(nazwa: str) -> str | None:
    """Zmienna środowiskowa STRUO_<nazwa>; gdy jej nie ma, dawna OVRLD_<nazwa> (zgodność ze starą konfiguracją)."""
    return os.environ.get(f"STRUO_{nazwa}") or os.environ.get(f"OVRLD_{nazwa}")


def sekret_aplikacji(klucz: str) -> str:
    """Klucz z sekcji [struo] w secrets.toml; gdy go nie ma, z dawnej sekcji [ovrld]."""
    return _sekret("struo", klucz) or _sekret("ovrld", klucz)


def normalizuj_adres(email: str | None) -> str:
    return (email or "").strip().lower()


def adresy(nazwa_env: str, klucz_sekretu: str) -> set[str]:
    """Lista adresów e-mail ze zmiennej STRUO_<nazwa_env> albo z secrets.toml (rozdzielone przecinkami lub średnikami)."""
    surowe = env(nazwa_env) or sekret_aplikacji(klucz_sekretu)
    return {a for a in (normalizuj_adres(x) for x in surowe.replace(";", ",").split(",")) if a}


def logowanie_wymagane() -> bool:
    """Czy dostęp wymaga zalogowania. STRUO_LOGOWANIE=1 wymusza (tak ustawiamy serwer), =0 wyłącza (praca lokalna),
    a bez zmiennej logowanie jest wymagane, gdy w secrets.toml jest sekcja [auth] albo gdy ten plik jest uszkodzony."""
    tryb = env("LOGOWANIE")
    if tryb == "1":
        return True
    if tryb == "0":
        return False
    # Uszkodzony secrets.toml nie może po cichu wyłączać logowania: wtedy aplikacja nikogo nie wpuszcza (fail closed).
    return auth_skonfigurowane() or secrets_uszkodzone()


def auth_skonfigurowane() -> bool:
    try:
        return "auth" in st.secrets
    except Exception:   # noqa: BLE001 (brak pliku secrets.toml)
        return False


def secrets_uszkodzone() -> bool:
    """True, gdy plik .streamlit/secrets.toml istnieje, ale nie da się go odczytać (błąd składni TOML)."""
    plik = FOLDER_APLIKACJI / ".streamlit" / "secrets.toml"
    if not plik.is_file():
        return False
    try:
        tomllib.loads(plik.read_text(encoding="utf-8-sig"))
        return False
    except Exception:   # noqa: BLE001
        return True


def dozwolone() -> set[str]:
    """Adresy, które mogą się zalogować: właściciel oraz zaproszeni (STRUO_DOZWOLONE albo [struo] dozwolone w secrets.toml)."""
    return adresy("WLASCICIEL", "wlasciciel") | adresy("DOZWOLONE", "dozwolone")


def id_z_adresu(email: str) -> str:
    """Stały, nieodwracalny identyfikator folderu z adresu e-mail (nie ujawnia adresu w nazwie folderu)."""
    return "u" + hashlib.sha256(normalizuj_adres(email).encode("utf-8")).hexdigest()[:24]


def zaloguj(email: str) -> dict:
    """Zapamiętuje w sesji, kto jest zalogowany (wywołuje się po udanym logowaniu przez dostawcę)."""
    adres = normalizuj_adres(email)
    stan = {"email": adres, "id": id_z_adresu(adres), "wlasciciel": adres in adresy("WLASCICIEL", "wlasciciel")}
    st.session_state[KLUCZ_SESJI] = stan
    return stan


def wyloguj_sesje() -> None:
    """Zapomina użytkownika w tej sesji (bez wylogowania u dostawcy)."""
    try:
        st.session_state.pop(KLUCZ_SESJI, None)
    except Exception:   # noqa: BLE001
        pass


def wyloguj() -> None:
    """Czyści sesję i wylogowuje u dostawcy (st.logout)."""
    wyloguj_sesje()
    try:
        st.logout()
    except Exception:   # noqa: BLE001 (np. praca lokalna bez logowania)
        pass


def zalogowany() -> bool:
    return _stan() is not None


def email() -> str:
    return (_stan() or {}).get("email", "")


def czy_wlasciciel() -> bool:
    """Czy bieżący użytkownik ma dostęp do rzeczy właściciela (Garmin, powiadomienia na jego telefon).
    Bez logowania (praca lokalna) tak; konto gościa z osobną instancją (STRUO_BAZA) nie."""
    if env("BAZA"):
        return False
    stan = _stan()
    if stan is not None:
        return bool(stan.get("wlasciciel"))
    return not logowanie_wymagane()


def katalog_danych() -> Path:
    """Folder z danymi bieżącego użytkownika (baza, kopie)."""
    stan = _stan()
    if stan is None:
        if logowanie_wymagane():
            raise BrakUzytkownika("Najpierw zaloguj się.")
        return FOLDER_APLIKACJI
    if stan.get("wlasciciel"):
        return FOLDER_APLIKACJI
    folder = FOLDER_APLIKACJI / "dane" / stan["id"]
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def sciezka_bazy() -> Path:
    return katalog_danych() / "treningi.db"
