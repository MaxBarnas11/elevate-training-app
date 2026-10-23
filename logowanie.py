"""Bramka logowania przez Google (st.login, OIDC) z listą zaproszonych adresów.

Wywołanie `wymagaj_logowania()` stoi w app.py zaraz po set_page_config, przed pierwszym dostępem do bazy. Gdy logowanie nie jest
wymagane (praca lokalna), nic nie robi. W przeciwnym razie pokazuje ekran logowania albo odmowy i zatrzymuje skrypt, a po udanym
logowaniu zapamiętuje użytkownika w sesji (uzytkownik.zaloguj), od czego zależy, której bazy używa aplikacja.
"""
from __future__ import annotations

import html

import streamlit as st

import uzytkownik

CSS_BEZ_MENU = """
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stSidebarNav"] { display: none !important; }
.stApp [data-testid="stMainBlockContainer"] { max-width: 34rem; margin: 0 auto; padding-top: 12vh; }
</style>
"""


def _ekran(tytul: str, podtytul: str = "") -> None:
    """Wspólny wygląd ekranów przed logowaniem (bez bazy danych: motyw według ustawienia przeglądarki)."""
    try:
        from karty import naglowek_strony
        from styl import zastosuj_styl
        zastosuj_styl()
        st.markdown(CSS_BEZ_MENU, unsafe_allow_html=True)
        st.markdown(naglowek_strony(tytul, html.escape(podtytul)), unsafe_allow_html=True)
    except Exception:   # noqa: BLE001 (ekran logowania musi się pokazać nawet bez stylu)
        st.title(tytul)
        if podtytul:
            st.caption(podtytul)


def ekran_logowania() -> None:
    _ekran("OVRLD", "Zaloguj się, żeby zacząć")
    st.button("Zaloguj się przez Google", type="primary", use_container_width=True, key="logowanie_google", on_click=st.login)
    st.caption("Dostęp tylko dla zaproszonych osób. Logujesz się kontem Google, a aplikacja nie zna Twojego hasła.")


def _ekran_odmowy(tytul: str, tresc_html: str) -> None:
    _ekran(tytul)
    st.markdown(f"<div>{tresc_html}</div>", unsafe_allow_html=True)
    st.button("Wyloguj", use_container_width=True, key="logowanie_wyloguj", on_click=uzytkownik.wyloguj)


def wymagaj_logowania() -> None:
    if not uzytkownik.logowanie_wymagane():
        return
    if not uzytkownik.auth_skonfigurowane():
        _ekran("OVRLD", "Logowanie nie jest skonfigurowane")
        st.error("Brakuje sekcji [auth] w pliku .streamlit/secrets.toml. Dopóki jej nie ma, aplikacja nikogo nie wpuszcza.")
        st.stop()
    u = st.user
    if not getattr(u, "is_logged_in", False):
        uzytkownik.wyloguj_sesje()
        ekran_logowania()
        st.stop()
    adres = uzytkownik.normalizuj_adres(getattr(u, "email", ""))
    if not adres or getattr(u, "email_verified", True) is False:
        uzytkownik.wyloguj_sesje()
        _ekran_odmowy("Nie udało się zalogować", "Konto Google nie ma potwierdzonego adresu e-mail.")
        st.stop()
    if adres not in uzytkownik.dozwolone():
        uzytkownik.wyloguj_sesje()
        _ekran_odmowy("Brak dostępu", f"Adres <b>{html.escape(adres)}</b> nie jest na liście zaproszonych osób. "
                                      "Poproś właściciela aplikacji o zaproszenie albo zaloguj się innym kontem.")
        st.stop()
    uzytkownik.zaloguj(adres)
