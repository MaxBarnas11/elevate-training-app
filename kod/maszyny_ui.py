"""Okno „Maszyny na mojej siłowni” (Profil → Moja siłownia): szukanie i zaznaczanie konkretnych maszyn dużymi przyciskami szkła.

Każde stuknięcie zapisuje się od razu, więc zamknięcie okna krzyżykiem niczego nie gubi.
"""
from __future__ import annotations

import html

import streamlit as st

import maszyny
import profil

CSS = (
    "<style>"
    "[class*='st-key-msz_rzad'] [data-testid='stHorizontalBlock']{flex-wrap:nowrap !important;gap:8px !important;}"
    "[class*='st-key-msz_rzad'] [data-testid='stColumn'],[class*='st-key-msz_rzad'] [data-testid='column']"
    "{min-width:0 !important;flex:1 1 0 !important;width:auto !important;}"
    "[class*='st-key-msz_rzad'] button{min-height:3.1rem;height:100%;padding:0.35rem 0.5rem !important;}"
    "[class*='st-key-msz_rzad'] button p{font-size:0.9rem !important;font-weight:700;line-height:1.2;white-space:normal !important;}"
    ".msz-grupa{font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;opacity:.65;margin:14px 2px 6px;}"
    ".msz-licznik{opacity:.75;font-size:.85rem;margin:2px 2px 8px;}"
    "</style>"
)


def _przelacz(mid: str) -> None:
    wybrane = profil.maszyny_wybrane()
    profil.zapisz_maszyny([x for x in wybrane if x != mid] if mid in wybrane else [*wybrane, mid])


def _typowe() -> None:
    profil.zapisz_maszyny(sorted(set(profil.maszyny_wybrane()) | set(maszyny.typowe())))


def _wyczysc() -> None:
    profil.zapisz_maszyny([])


def _zamknij() -> None:
    st.session_state["msz_zamknij"] = True


def _rzad(klucz: str, przyciski: list[tuple[str, str, bool, object, tuple]], kolumn: int = 2) -> None:
    """Rząd przycisków: (klucz, etykieta, zaznaczony, callback, argumenty)."""
    for start in range(0, len(przyciski), kolumn):
        paczka = przyciski[start:start + kolumn]
        with st.container(key=f"msz_rzad_{klucz}_{start}"):
            kol = st.columns(kolumn)
            for j, (k, et, tak, cb, args) in enumerate(paczka):
                kol[j].button(et, key=k, type="primary" if tak else "secondary", use_container_width=True, on_click=cb, args=args)


@st.dialog("Maszyny na mojej siłowni")
def okno_maszyn() -> None:
    s = st.session_state
    if s.pop("msz_zamknij", False):
        st.rerun()
    st.markdown(CSS, unsafe_allow_html=True)
    wybrane = set(profil.maszyny_wybrane())
    st.caption("Zaznacz maszyny i stanowiska, które masz. Listy ćwiczeń, zamiana na podobne i „Trening na dziś” pokażą wtedy tylko "
               "ćwiczenia na tych maszynach. Dopóki nic nie zaznaczysz, nic nie jest ukrywane.")
    _rzad("gora", [("msz_typowe", "Typowa siłownia", False, _typowe, ()), ("msz_czysc", "Wyczyść", False, _wyczysc, ())])
    st.text_input("Szukaj maszyny", key="msz_szukaj", placeholder="np. hack, suwnica, butterfly, wyciąg",
                  label_visibility="collapsed")
    znalezione = maszyny.szukaj(s.get("msz_szukaj") or "")
    st.markdown(f"<div class='msz-licznik'>Zaznaczone: <b>{len(wybrane)}</b> z {len(maszyny.KATALOG)}</div>",
                unsafe_allow_html=True)
    if not znalezione:
        st.caption("Nic nie pasuje. Spróbuj innego słowa (szukam też po angielsku, np. „leg press”).")
    for nr, grupa in enumerate(maszyny.GRUPY):
        w_grupie = [m for m in znalezione if m.grupa == grupa]
        if not w_grupie:
            continue
        st.markdown(f"<div class='msz-grupa'>{html.escape(grupa)}</div>", unsafe_allow_html=True)
        _rzad(f"g{nr}", [(f"msz_{m.id}", ("✓ " if m.id in wybrane else "") + m.nazwa, m.id in wybrane, _przelacz, (m.id,))
                         for m in w_grupie])
    st.button("Gotowe", type="primary", use_container_width=True, key="msz_gotowe", on_click=_zamknij)


def sekcja_w_profilu() -> None:
    """Wiersz w karcie „Moja siłownia”: ile maszyn zaznaczono i przycisk otwierający okno."""
    st.markdown(CSS, unsafe_allow_html=True)
    ile = len(profil.maszyny_wybrane())
    opis = (f"Maszyny i stanowiska: <b>{ile}</b> zaznaczonych" if ile
            else "Maszyny i stanowiska: <b>nie zaznaczono</b> (pokazujemy ćwiczenia na wszystkich)")
    st.markdown(f"<div class='msz-licznik'>{opis}</div>", unsafe_allow_html=True)
    if st.button("Wybierz maszyny", use_container_width=True, key="pr_maszyny",
                 help="Konkretne maszyny, np. suwnica, hack przysiad, butterfly, wyciąg górny. Dzięki temu aplikacja nie proponuje "
                      "ćwiczeń na maszynach, których nie masz."):
        okno_maszyn()
