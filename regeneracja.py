"""Strona Regeneracja: wybór zakresu dni, kafelki trendu i wykresy w kolorach aplikacji (HTML/SVG)."""
from __future__ import annotations

import html
import math
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import baza
from karty import (
    KOLOR_KARTY, KOLOR_OBRAMOWANIA, KOLOR_PRZYGASZONY, KOLOR_TEKSTU, KOLOR_TLA_PIERSCIENIA,
    NIEBIESKI, POMARANCZOWY, ZIELONY,
    _naglowek_karty, _tlo_karty, siatka_kart,
)
from wykresy import SEN_PASMO, pasmo_osobiste

KOLOR_LINII = "#2B2A27"
ZAKRESY = {"7 dni": 7, "30 dni": 30, "90 dni": 90}


# ---------------------------------------------------------------
# Liczenie trendu: ostatnie 7 dni kontra poprzednie 7 dni
# ---------------------------------------------------------------
def srednie_tygodniowe(seria: pd.Series, dzis: date | None = None) -> tuple[float | None, float | None]:
    """(średnia z ostatnich 7 dni, średnia z 7 dni przed nimi). None, gdy mniej niż 2 pomiary w okresie."""
    dzis = dzis or date.today()
    seria = seria.dropna()
    dni = pd.Series(seria.index.date, index=seria.index)
    teraz = seria[(dni > dzis - timedelta(days=7)) & (dni <= dzis)]
    wczesniej = seria[(dni > dzis - timedelta(days=14)) & (dni <= dzis - timedelta(days=7))]
    return (
        float(teraz.mean()) if len(teraz) >= 2 else None,
        float(wczesniej.mean()) if len(wczesniej) >= 2 else None,
    )


def karta_trendu(tytul: str, srednia: float | None, poprzednia: float | None, jednostka: str,
                 wyzsze_lepiej: bool | None, prog: float = 0.5, miejsca: int = 0) -> str:
    """Kafelek: średnia z 7 dni i różnica względem poprzednich 7 dni (kolor mówi, czy zmiana jest dobra)."""
    if srednia is None:
        kolor, napis, opis = KOLOR_PRZYGASZONY, "-", "za mało danych z ostatnich 7 dni"
    else:
        napis = f"{srednia:.{miejsca}f}".replace(".", ",")
        if poprzednia is None:
            kolor, opis = NIEBIESKI, "brak danych do porównania z poprzednim tygodniem"
        else:
            roznica = srednia - poprzednia
            if abs(roznica) < prog:
                kolor, opis = NIEBIESKI, "bez zmian względem poprzednich 7 dni"
            else:
                if wyzsze_lepiej is None:
                    kolor = NIEBIESKI
                else:
                    kolor = ZIELONY if (roznica > 0) == wyzsze_lepiej else POMARANCZOWY
                strzalka = "▲" if roznica > 0 else "▼"
                wartosc = f"{abs(roznica):.{miejsca}f}".replace(".", ",")
                opis = f"{strzalka} {wartosc} {jednostka} vs poprzednie 7 dni".replace("  ", " ")
    return (
        f'<div style="{_tlo_karty(kolor)}border:1px solid {KOLOR_OBRAMOWANIA};border-radius:16px;'
        f'padding:16px 18px;height:170px;box-sizing:border-box;display:flex;flex-direction:column;">'
        f'{_naglowek_karty(html.escape(tytul), kolor)}'
        f'<div style="text-align:center;margin-top:10px;">'
        f'<span style="font-size:2.2rem;font-weight:700;color:{KOLOR_TEKSTU};">{napis}</span>'
        f'<span style="font-size:1rem;color:{KOLOR_PRZYGASZONY};margin-left:6px;">{jednostka}</span></div>'
        f'<div style="text-align:center;font-size:0.8rem;font-weight:600;color:{kolor};margin-top:2px;">{opis}</div>'
        f'<div style="margin-top:auto;text-align:center;font-size:0.7rem;color:{KOLOR_PRZYGASZONY};">średnia z ostatnich 7 dni</div>'
        f'</div>'
    )


# ---------------------------------------------------------------
# Wykres liniowy jako SVG (kolory spójne z kafelkami)
# ---------------------------------------------------------------
def _ladne_ticki(dol: float, gora: float, ile: int = 4) -> list[float]:
    """Okrągłe wartości na osi Y obejmujące zakres [dol, gora]."""
    rozpietosc = (gora - dol) or 1.0
    surowy = rozpietosc / (ile - 1)
    rzad = 10 ** math.floor(math.log10(surowy))
    krok = rzad * 10
    for m in (1, 2, 2.5, 5, 10):
        if m * rzad >= surowy:
            krok = m * rzad
            break
    t = math.floor(dol / krok) * krok
    ticki = []
    while t < gora + krok * 0.999:
        ticki.append(round(t, 6))
        t += krok
        if len(ticki) > 12:
            break
    if len(ticki) < 2:
        ticki.append(ticki[0] + krok)
    return ticki


def wykres_liniowy_svg(seria: pd.Series, jednostka: str = "", pasmo: tuple[float, float] | None = None,
                       srednia_ruchoma: pd.Series | None = None, miejsca: int = 0, wysokosc: int = 210,
                       limit_gorny: float | None = None) -> str:
    """Wykres liniowy z opcjonalnym zielonym pasmem i linią średniej. Najechanie na punkt pokazuje datę i wartość."""
    seria = seria.dropna()
    if len(seria) < 2:
        return ""
    szer, wys = 600, wysokosc
    l, p, g, d = 40, 14, 12, 26                      # marginesy: lewy, prawy, górny, dolny
    wartosci = list(seria.values)
    dol, gora = min(wartosci), max(wartosci)
    if pasmo:
        dol, gora = min(dol, pasmo[0]), max(gora, pasmo[1])
    margines = (gora - dol) * 0.08 or 1.0
    gora_osi = gora + margines if limit_gorny is None else min(gora + margines, limit_gorny)
    ticki = _ladne_ticki(dol - margines, gora_osi)
    if limit_gorny is not None and ticki[-1] > limit_gorny:
        ticki = [t for t in ticki if t <= limit_gorny] or ticki[:1]
    y0, y1 = ticki[0], ticki[-1]

    dni = [ts.date() for ts in seria.index]
    pierwszy, ostatni = dni[0], dni[-1]
    rozpietosc_dni = max((ostatni - pierwszy).days, 1)

    def x(dzien: date) -> float:
        return l + (dzien - pierwszy).days / rozpietosc_dni * (szer - l - p)

    def y(v: float) -> float:
        return g + (y1 - v) / (y1 - y0) * (wys - g - d)

    czesci = [f'<svg viewBox="0 0 {szer} {wys}" width="100%" style="display:block;overflow:visible;" '
              f'font-family="Segoe UI, Arial, sans-serif">']
    # siatka i opisy osi Y
    for t in ticki:
        czesci.append(f'<line x1="{l}" x2="{szer - p}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="{KOLOR_TLA_PIERSCIENIA}" stroke-width="1"/>')
        etykieta = f"{t:.0f}" if abs(t - round(t)) < 1e-6 else f"{t:.1f}"
        czesci.append(f'<text x="{l - 8}" y="{y(t) + 4:.1f}" text-anchor="end" font-size="11" fill="{KOLOR_PRZYGASZONY}">{etykieta}</text>')
    # pasmo
    if pasmo:
        gp, dp = max(pasmo[1], y0), min(pasmo[0], y1)
        if gp > dp:
            czesci.append(f'<rect x="{l}" y="{y(gp):.1f}" width="{szer - l - p}" height="{y(dp) - y(gp):.1f}" fill="{ZIELONY}" fill-opacity="0.16"/>')
    # opisy osi X
    krok = 1 if rozpietosc_dni <= 7 else math.ceil(rozpietosc_dni / 5)
    dzien = pierwszy
    while dzien <= ostatni:
        czesci.append(f'<text x="{x(dzien):.1f}" y="{wys - 6}" text-anchor="middle" font-size="11" fill="{KOLOR_PRZYGASZONY}">{dzien:%d.%m}</text>')
        dzien += timedelta(days=krok)
    # linia główna (przy średniej ruchomej jest delikatna, a średnia mocna)
    punkty = " ".join(f"{x(dz):.1f},{y(v):.1f}" for dz, v in zip(dni, wartosci))
    gruba = srednia_ruchoma is None
    czesci.append(f'<polyline points="{punkty}" fill="none" stroke="{KOLOR_LINII if gruba else KOLOR_PRZYGASZONY}" '
                  f'stroke-width="{2.4 if gruba else 1.2}" stroke-opacity="{1 if gruba else 0.6}" stroke-linejoin="round" stroke-linecap="round"/>')
    if srednia_ruchoma is not None and len(srednia_ruchoma.dropna()) >= 2:
        sr = srednia_ruchoma.dropna()
        pts = " ".join(f"{x(ts.date()):.1f},{y(v):.1f}" for ts, v in sr.items())
        czesci.append(f'<polyline points="{pts}" fill="none" stroke="{KOLOR_LINII}" stroke-width="2.6" '
                      f'stroke-linejoin="round" stroke-linecap="round"/>')
    # punkty z podpowiedziami
    for i, (dz, v) in enumerate(zip(dni, wartosci)):
        ost = i == len(dni) - 1
        wart = f"{v:.{miejsca}f}".replace(".", ",")
        czesci.append(
            f'<circle cx="{x(dz):.1f}" cy="{y(v):.1f}" r="{5 if ost else 3.2}" '
            f'fill="{KOLOR_LINII if ost else KOLOR_KARTY}" stroke="{KOLOR_LINII if gruba else KOLOR_PRZYGASZONY}" stroke-width="1.8">'
            f'<title>{dz:%d.%m.%Y}: {wart} {html.escape(jednostka)}</title></circle>'
        )
    czesci.append("</svg>")
    return "".join(czesci)


def karta_wykresu(tytul: str, podpis: str, svg: str, komunikat_pusty: str = "Za mało danych w tym zakresie.") -> str:
    tresc = svg or (f'<div style="height:150px;display:flex;align-items:center;justify-content:center;'
                    f'font-size:0.85rem;color:{KOLOR_PRZYGASZONY};">{komunikat_pusty}</div>')
    return (
        f'<div style="{_tlo_karty(NIEBIESKI)}border:1px solid {KOLOR_OBRAMOWANIA};border-radius:16px;'
        f'padding:16px 18px;box-sizing:border-box;min-width:0;">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;">'
        f'{_naglowek_karty(html.escape(tytul), NIEBIESKI)}'
        f'<span style="font-size:0.72rem;color:{KOLOR_PRZYGASZONY};text-align:right;">{podpis}</span></div>'
        f'<div style="margin-top:12px;">{tresc}</div></div>'
    )


def siatka_wykresow(karty: list[str]) -> str:
    """Dwie kolumny wykresów (jedna na wąskim ekranie)."""
    return (
        '<style>.siatka-wykresow{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:16px;}'
        '@media (max-width:900px){.siatka-wykresow{grid-template-columns:minmax(0,1fr);}}</style>'
        '<div class="siatka-wykresow">' + "".join(karty) + '</div>'
    )


# ---------------------------------------------------------------
# Widok strony
# ---------------------------------------------------------------
def widok_regeneracji() -> None:
    # Wyśrodkowanie przełącznika zakresu (klasa st-key-reg_zakres pochodzi od klucza widżetu)
    st.markdown(
        "<style>"
        ".st-key-reg_zakres{align-self:center !important;margin-left:auto !important;margin-right:auto !important;}"
        "</style>",
        unsafe_allow_html=True,
    )
    _, srodek, _ = st.columns([1, 2, 1])
    with srodek:
        wybor = st.segmented_control("Zakres", list(ZAKRESY), default="30 dni", key="reg_zakres",
                                     label_visibility="collapsed")
    dni = ZAKRESY.get(wybor or "30 dni", 30)
    od = pd.Timestamp(date.today() - timedelta(days=dni - 1))

    historia = baza.wczytaj_dane_garmin_do_wykresow()
    wagi = baza.wczytaj_wage_do_wykresu()
    waga = wagi["Waga"] if (not wagi.empty and "Waga" in wagi.columns) else pd.Series(dtype=float)

    if len(historia.dropna(how="all")) < 2 and len(waga) < 2:
        st.info("Wykresy pojawią się, gdy w bazie będą dane z co najmniej dwóch dni.")
        return

    # Kafelki trendu (zawsze ostatnie 7 dni vs poprzednie 7, niezależnie od zakresu wykresów)
    sen_now, sen_prev = srednie_tygodniowe(historia["Wynik_snu"])
    rhr_now, rhr_prev = srednie_tygodniowe(historia["RHR"])
    hrv_now, hrv_prev = srednie_tygodniowe(historia["HRV"])
    waga_now, waga_prev = srednie_tygodniowe(waga)
    st.markdown(siatka_kart([
        karta_trendu("Wynik snu", sen_now, sen_prev, "pkt", True, prog=1),
        karta_trendu("Tętno spoczynkowe", rhr_now, rhr_prev, "bpm", False, prog=0.5),
        karta_trendu("HRV", hrv_now, hrv_prev, "ms", True, prog=1),
        karta_trendu("Waga", waga_now, waga_prev, "kg", None, prog=0.2, miejsca=1),
    ]), unsafe_allow_html=True)

    # Wykresy w wybranym zakresie; zielone pasmo liczymy z całej historii
    w_zakresie = historia[historia.index >= od]
    karty = [
        karta_wykresu("Wynik snu", "zielone pole: dobry i doskonały sen",
                      wykres_liniowy_svg(w_zakresie["Wynik_snu"], "pkt", pasmo=SEN_PASMO, limit_gorny=100)),
        karta_wykresu("Tętno spoczynkowe", "zielone pole: Twój zwykły zakres, niżej = lepiej",
                      wykres_liniowy_svg(w_zakresie["RHR"], "bpm", pasmo=pasmo_osobiste(historia["RHR"]))),
    ]
    if historia["HRV"].notna().any():
        karty.append(karta_wykresu("HRV", "zielone pole: Twój zwykły zakres",
                                   wykres_liniowy_svg(w_zakresie["HRV"], "ms", pasmo=pasmo_osobiste(historia["HRV"]))))
    waga_zakres = waga[waga.index >= od] if len(waga) else waga
    sr = waga.rolling("7D").mean()[waga.index >= od] if len(waga) else None
    karty.append(karta_wykresu("Waga ciała", "cienka linia: pomiary, gruba: średnia z 7 dni",
                               wykres_liniowy_svg(waga_zakres, "kg", srednia_ruchoma=sr, miejsca=1),
                               komunikat_pusty="Wpisz wagę w co najmniej 2 dniach tego zakresu."))
    st.markdown(siatka_wykresow(karty), unsafe_allow_html=True)
    st.caption("Pasmo RHR i HRV to Twoja średnia ± odchylenie standardowe (pojawia się od kilku dni danych).")
