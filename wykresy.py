"""Funkcje rysujące wykresy (statyczne, bez zoomu)."""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

# Zielone pole na wykresie snu (dobry i doskonały sen wg skali Garmina)
SEN_PASMO = (80, 100)

# Od ilu dni danych liczymy Twój własny zakres dla HRV i RHR
MIN_DNI_DLA_PASMA = 5


def pasmo_osobiste(serie: pd.Series) -> tuple[float, float] | None:
    """Zwraca Twój własny zakres (średnia ± odchylenie standardowe) albo None, gdy za mało danych."""
    wartosci = serie.dropna()
    if len(wartosci) < MIN_DNI_DLA_PASMA:
        return None
    srednia = wartosci.mean()
    odchylenie = wartosci.std()
    return float(srednia - odchylenie), float(srednia + odchylenie)


def rysuj_wykres(
    dane: pd.DataFrame,
    kolumna: str,
    nazwa: str,
    jednostka: str,
    pasmo: tuple[float, float] | None = None,
) -> None:
    """Rysuje niewielki wykres liniowy z opcjonalnym zielonym polem (pasmo)."""
    # reset_index zamienia datę z indeksu na zwykłą kolumnę "Data"
    df = dane[[kolumna]].dropna().reset_index()

    # Linia z punktami. Brak .interactive(), więc scroll nie przybliża wykresu.
    linia = (
        alt.Chart(df)
        .mark_line(point=True, color="#4C9BE8")
        .encode(
            x=alt.X("Data:T", title=None, axis=alt.Axis(format="%d.%m", tickCount="day")),
            y=alt.Y(f"{kolumna}:Q", title=jednostka, scale=alt.Scale(zero=False)),
            tooltip=[
                alt.Tooltip("Data:T", title="Data", format="%d.%m.%Y"),
                alt.Tooltip(f"{kolumna}:Q", title=nazwa),
            ],
        )
    )

    warstwy = []
    if pasmo is not None:
        # Zielony prostokąt na całą szerokość wykresu, od dolnej do górnej granicy
        df_pasmo = pd.DataFrame({"dol": [pasmo[0]], "gora": [pasmo[1]]})
        zielone = (
            alt.Chart(df_pasmo)
            .mark_rect(color="#2ECC71", opacity=0.20)
            .encode(y=alt.Y("dol:Q", title=jednostka), y2="gora:Q")
        )
        warstwy.append(zielone)
    warstwy.append(linia)

    st.altair_chart(alt.layer(*warstwy).properties(height=220), use_container_width=True)