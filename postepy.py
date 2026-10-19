"""Strona Postępy: rekordy, tygodniowa objętość i trendy w wybranym ćwiczeniu.

Nie zakłada żadnej dyscypliny. Liczymy wszystko, co da się policzyć z zapisanych serii
(ciężar, serie, powtórzenia, czas, dystans), a wyniki w kg pokazujemy tylko tam, gdzie
ciężar w ogóle występuje. Dane bierzemy z trzech źródeł naraz: z prowadzonych treningów,
z ręcznego formularza i ze starych wpisów (tabela treningi).
"""
from __future__ import annotations

import html
import sqlite3
from contextlib import closing
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import baza
from karty import (
    KOLOR_KARTY, KOLOR_OBRAMOWANIA, KOLOR_PRZYGASZONY, KOLOR_TEKSTU, KOLOR_TLA_PIERSCIENIA,
    NIEBIESKI, POMARANCZOWY, ZIELONY, _naglowek_karty, _tlo_karty, siatka_kart,
)
from motywy import v as _kolor_motywu
from regeneracja import karta_wykresu, siatka_wykresow, wykres_liniowy_svg
from sesja_treningowa import JEDNOSTKI_POWTORZEN, format_kg, jednostka_powtorzen, lista_partii, opis_serii, pytajnik

ZAKRESY = {"30 dni": 30, "90 dni": 90, "Rok": 365, "Wszystko": None}
KOLOR_SLUPKA = _kolor_motywu("slupek")
KOLOR_SLUPKA_BIEZACY = _kolor_motywu("slupek_biezacy")


# ---------------------------------------------------------------
# Dane
# ---------------------------------------------------------------
def wczytaj_wpisy() -> pd.DataFrame:
    """Jeden wiersz = jedno ćwiczenie w jednym treningu. Kolumny: Data, Cwiczenie, Ciezar, Serie, Powt, Jednostka."""
    kolumny = ["Data", "Cwiczenie", "Ciezar", "Serie", "Powt", "Jednostka", "Sesja"]
    with closing(sqlite3.connect(baza.SCIEZKA_BAZY)) as db:
        czesci = []
        try:
            ma_jednostke = "Jednostka" in {w[1] for w in db.execute("PRAGMA table_info(wpisy_cwiczen)")}
            jednostka = "COALESCE(w.Jednostka, 'powt.')" if ma_jednostke else "'powt.'"
            czesci.append(pd.read_sql_query(
                f"SELECT s.Data, w.Cwiczenie, w.Ciezar, w.Serie, w.Powtorzenia AS Powt, {jednostka} AS Jednostka, w.Sesja_id AS Sesja "
                "FROM wpisy_cwiczen w JOIN sesje s ON s.id = w.Sesja_id", db))
        except (sqlite3.OperationalError, pd.errors.DatabaseError):
            pass
        try:
            czesci.append(pd.read_sql_query(
                "SELECT Data, Nazwa_cwiczenia AS Cwiczenie, Ciezar, Serie, Powtorzenia AS Powt, 'powt.' AS Jednostka, -id AS Sesja "
                "FROM treningi WHERE Nazwa_cwiczenia IS NOT NULL AND Nazwa_cwiczenia != ''", db))
        except (sqlite3.OperationalError, pd.errors.DatabaseError):
            pass
    czesci = [c for c in czesci if not c.empty]
    if not czesci:
        return pd.DataFrame(columns=kolumny)
    wpisy = pd.concat(czesci, ignore_index=True)
    wpisy["Data"] = pd.to_datetime(wpisy["Data"], errors="coerce").dt.normalize()
    wpisy = wpisy.dropna(subset=["Data"])
    wpisy["Ciezar"] = pd.to_numeric(wpisy["Ciezar"], errors="coerce").fillna(0.0)
    wpisy["Serie"] = pd.to_numeric(wpisy["Serie"], errors="coerce").fillna(1).astype(int)
    wpisy["Powt"] = pd.to_numeric(wpisy["Powt"], errors="coerce").fillna(0).astype(int)
    wpisy["Jednostka"] = wpisy["Jednostka"].fillna("powt.")
    return dodaj_wyliczenia(wpisy[wpisy["Powt"] > 0].reset_index(drop=True))


def szacowane_1rm(ciezar: float, powt: int) -> float | None:
    """Wzór Epleya: ciężar × (1 + powtórzenia / 30). Wiarygodny do ok. 12 powtórzeń."""
    if ciezar <= 0 or powt < 1 or powt > 12:
        return None
    return float(ciezar) if powt == 1 else float(ciezar) * (1 + powt / 30)


def dodaj_wyliczenia(wpisy: pd.DataFrame) -> pd.DataFrame:
    wpisy = wpisy.copy()
    na_powt = wpisy["Jednostka"].isin(JEDNOSTKI_POWTORZEN)
    wpisy["E1RM"] = [szacowane_1rm(c, p) if r else None for c, p, r in zip(wpisy["Ciezar"], wpisy["Powt"], na_powt)]
    wpisy["E1RM"] = pd.to_numeric(wpisy["E1RM"], errors="coerce")
    wpisy["Objetosc"] = (wpisy["Ciezar"] * wpisy["Serie"] * wpisy["Powt"]).where(na_powt, 0.0)
    wpisy["Powt_lacznie"] = wpisy["Serie"] * wpisy["Powt"]
    return wpisy


# ---------------------------------------------------------------
# Liczenie
# ---------------------------------------------------------------
def rekordy(wpisy: pd.DataFrame) -> pd.DataFrame:
    """Dni, w których pobito rekord szacowanego 1RM w danym ćwiczeniu (pierwszy pomiar to punkt wyjścia, nie rekord)."""
    wyniki = []
    for nazwa, grupa in wpisy.dropna(subset=["E1RM"]).groupby("Cwiczenie"):
        najlepszy = None
        for data, wartosc in grupa.groupby("Data")["E1RM"].max().sort_index().items():
            if najlepszy is not None and wartosc > najlepszy + 0.05:
                wyniki.append({"Cwiczenie": nazwa, "Data": data, "E1RM": float(wartosc), "Poprzedni": float(najlepszy)})
            najlepszy = wartosc if najlepszy is None else max(najlepszy, wartosc)
    kolumny = ["Cwiczenie", "Data", "E1RM", "Poprzedni"]
    if not wyniki:
        return pd.DataFrame(columns=kolumny)
    return pd.DataFrame(wyniki, columns=kolumny).sort_values("Data", ascending=False).reset_index(drop=True)


def poczatek_tygodnia(d: date) -> date:
    return d - timedelta(days=d.weekday())


def tygodnie(wpisy: pd.DataFrame, metryka: str, dzis: date, ile: int = 12) -> list[tuple[date, float]]:
    """Wartość metryki ('Objetosc' albo 'Serie') w kolejnych tygodniach, najstarszy pierwszy; puste tygodnie = 0."""
    start = poczatek_tygodnia(dzis) - timedelta(weeks=ile - 1)
    tydzien = wpisy["Data"].dt.date.map(poczatek_tygodnia)
    sumy = wpisy.groupby(tydzien)[metryka].sum() if not wpisy.empty else {}
    return [(start + timedelta(weeks=i), float(sumy.get(start + timedelta(weeks=i), 0.0))) for i in range(ile)]


def seria_tygodni(wpisy: pd.DataFrame, dzis: date) -> int:
    """Ile tygodni z rzędu miało choć jeden trening. Bieżący tydzień bez treningu nie przerywa serii (jeszcze trwa)."""
    if wpisy.empty:
        return 0
    zajete = {poczatek_tygodnia(d) for d in wpisy["Data"].dt.date}
    tydzien = poczatek_tygodnia(dzis)
    if tydzien not in zajete:
        tydzien -= timedelta(weeks=1)
    licznik = 0
    while tydzien in zajete:
        licznik += 1
        tydzien -= timedelta(weeks=1)
    return licznik


def partie_cwiczen() -> dict[str, str]:
    """Nazwa ćwiczenia -> partia mięśniowa z bazy ćwiczeń (puste i brakujące to „Inne”)."""
    with closing(sqlite3.connect(baza.SCIEZKA_BAZY)) as db:
        try:
            return {n: (p or "Inne") for n, p in db.execute("SELECT Nazwa, Partia FROM cwiczenia")}
        except sqlite3.OperationalError:
            return {}


def przypisz_partie(nazwa: str, partia: str) -> None:
    """Zmienia partię ćwiczenia w bazie (dodaje je, jeśli go tam jeszcze nie ma)."""
    with closing(sqlite3.connect(baza.SCIEZKA_BAZY)) as db:
        db.execute("INSERT OR IGNORE INTO cwiczenia (Nazwa, Partia) VALUES (?, ?)", (nazwa, partia))
        db.execute("UPDATE cwiczenia SET Partia = ? WHERE Nazwa = ?", (partia, nazwa))
        db.commit()


def _przypisz_z_formularza() -> None:
    s = st.session_state
    if s.get("post_partia_cwiczenie") and s.get("post_partia_wybor"):
        przypisz_partie(s["post_partia_cwiczenie"], s["post_partia_wybor"])
        s["post_partia_info"] = f"Zapisano: {s['post_partia_cwiczenie']} → {s['post_partia_wybor']}."
        s["post_partia_cwiczenie"] = None


def serie_na_partie(wpisy: pd.DataFrame, partie: dict[str, str], dzis: date, ile_tygodni: int = 5) -> pd.DataFrame:
    """Serie na partię mięśniową w kolejnych tygodniach (kolumny: poniedziałki, najstarszy pierwszy, ostatni to bieżący tydzień).
    Liczą się tylko ćwiczenia w powtórzeniach; rozgrzewki nie wchodzą, bo nie trafiają do wpisów ćwiczeń."""
    start = poczatek_tygodnia(dzis) - timedelta(weeks=ile_tygodni - 1)
    kolumny = [start + timedelta(weeks=i) for i in range(ile_tygodni)]
    if wpisy.empty:
        return pd.DataFrame(columns=kolumny)
    w = wpisy[wpisy["Jednostka"].isin(JEDNOSTKI_POWTORZEN)].copy()
    w["Tydzien"] = w["Data"].dt.date.map(poczatek_tygodnia)
    w = w[w["Tydzien"] >= start]
    if w.empty:
        return pd.DataFrame(columns=kolumny)
    w["Partia"] = w["Cwiczenie"].map(lambda n: partie.get(n, "Inne"))
    tabela = w.pivot_table(index="Partia", columns="Tydzien", values="Serie", aggfunc="sum", fill_value=0)
    return tabela.reindex(columns=kolumny, fill_value=0)


def dni_treningowe(wpisy: pd.DataFrame, od: date, do: date) -> int:
    daty = wpisy["Data"].dt.date
    return int(daty[(daty >= od) & (daty <= do)].nunique())


def suma_w_oknie(wpisy: pd.DataFrame, kolumna: str, od: date, do: date) -> float:
    daty = wpisy["Data"].dt.date
    return float(wpisy.loc[(daty >= od) & (daty <= do), kolumna].sum())


def dzienne_dla_cwiczenia(wpisy: pd.DataFrame, cwiczenie: str) -> pd.DataFrame:
    """Jeden wiersz na dzień: najlepsze 1RM, maksymalny ciężar, łączne powtórzenia i objętość."""
    w = wpisy[wpisy["Cwiczenie"] == cwiczenie]
    if w.empty:
        return pd.DataFrame(columns=["E1RM", "Maks_ciezar", "Powt_lacznie", "Objetosc"])
    return w.groupby("Data").agg(
        E1RM=("E1RM", "max"), Maks_ciezar=("Ciezar", "max"),
        Powt_lacznie=("Powt_lacznie", "sum"), Objetosc=("Objetosc", "sum"),
    ).sort_index()


def zgrupuj_wiersze(wiersze: pd.DataFrame) -> list[dict]:
    """Takie same serie (ciężar i powtórzenia) sumujemy w jedną pozycję, w kolejności pierwszego wystąpienia."""
    grupy: dict[tuple, dict] = {}
    for r in wiersze.itertuples():
        g = grupy.setdefault((float(r.Ciezar), int(r.Powt)), {"ciezar": float(r.Ciezar), "powt": int(r.Powt), "serie": 0})
        g["serie"] += int(r.Serie)
    return list(grupy.values())


def skroc_opis(tekst: str, maks_czesci: int = 3) -> str:
    czesci = tekst.split(", ")
    return ", ".join(czesci[:maks_czesci]) + (" …" if len(czesci) > maks_czesci else "")


def jednostka_cwiczenia(wpisy: pd.DataFrame, cwiczenie: str) -> str:
    jednostki = wpisy.loc[wpisy["Cwiczenie"] == cwiczenie, "Jednostka"]
    return jednostki.mode().iloc[0] if not jednostki.empty else "powt."


# ---------------------------------------------------------------
# Wygląd
# ---------------------------------------------------------------
def siatka_postepow(karty: list[str], kolumny: int = 2) -> str:
    """Siatka wykresów z własnym odstępem u góry i u dołu (nie zależymy od odstępów Streamlita) i progiem 700 px."""
    return (
        f'<style>.siatka-postepow{{display:grid;grid-template-columns:repeat({kolumny},minmax(0,1fr));gap:16px;margin:16px 0;}}'
        '@media (max-width:700px){.siatka-postepow{grid-template-columns:minmax(0,1fr);}}</style>'
        '<div class="siatka-postepow">' + "".join(karty) + '</div>'
    )


def ogranicz_wysokosc(svg: str, px: int = 230) -> str:
    """Wykres nie rośnie ponad px (na szerokim ekranie byłby ogromny); proporcje zostają, więc nic się nie rozciąga."""
    return svg.replace('style="display:block;overflow:visible;', f'style="display:block;overflow:visible;max-height:{px}px;', 1)


def karta_liczby(tytul: str, wartosc: str, jednostka: str, opis: str, kolor: str, podpis: str = "") -> str:
    return (
        f'<div style="{_tlo_karty(kolor)}border:1px solid {KOLOR_OBRAMOWANIA};border-radius:16px;'
        f'padding:16px 18px;min-height:{170 if podpis else 140}px;box-sizing:border-box;display:flex;flex-direction:column;">'
        f'{_naglowek_karty(html.escape(tytul), kolor)}'
        f'<div style="text-align:center;margin-top:10px;">'
        f'<span style="font-size:2.2rem;font-weight:700;color:{KOLOR_TEKSTU};">{html.escape(wartosc)}</span>'
        f'<span style="font-size:1rem;color:{KOLOR_PRZYGASZONY};margin-left:6px;">{html.escape(jednostka)}</span></div>'
        f'<div style="text-align:center;font-size:0.8rem;font-weight:600;color:{kolor};margin-top:2px;">{html.escape(opis)}</div>'
        f'<div style="margin-top:auto;text-align:center;font-size:0.7rem;color:{KOLOR_PRZYGASZONY};">{html.escape(podpis)}</div>'
        f'</div>'
    )


def _roznica(teraz: float, wczesniej: float) -> tuple[str, str]:
    """(opis, kolor) dla porównania dwóch okresów; neutralny kolor, bo więcej nie zawsze znaczy lepiej."""
    if not wczesniej:
        return ("pierwszy okres z danymi" if teraz else "brak danych do porównania"), NIEBIESKI
    proc = 100 * (teraz - wczesniej) / wczesniej
    if abs(proc) < 1:
        return "bez zmian względem poprzednich dni", NIEBIESKI
    return f"{'▲' if proc > 0 else '▼'} {abs(proc):.0f}% względem poprzednich dni".replace(".", ","), NIEBIESKI


def slupki_svg(etykiety: list[str], wartosci: list[float], jednostka: str = "") -> str:
    """Wykres słupkowy w kolorach aplikacji; ostatni słupek (bieżący tydzień) jest ciemniejszy."""
    if not wartosci or max(wartosci) <= 0:
        return ""
    szer, wys = 600, 190
    l, p, g, d = 12, 12, 24, 26
    maks = max(wartosci)
    n = len(wartosci)
    miejsce = (szer - l - p) / n
    szer_slupka = miejsce * 0.62
    czesci = [f'<svg viewBox="0 0 {szer} {wys}" width="100%" style="display:block;overflow:visible;" font-family="Segoe UI, Arial, sans-serif">']
    for i, (et, w) in enumerate(zip(etykiety, wartosci)):
        x = l + i * miejsce + (miejsce - szer_slupka) / 2
        h = (wys - g - d) * w / maks
        y = wys - d - h
        kolor = KOLOR_SLUPKA_BIEZACY if i == n - 1 else KOLOR_SLUPKA
        opis = f"{w / 1000:.1f} t".replace(".", ",") if w >= 10000 else f"{w:.0f}"
        if w > 0:
            czesci.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{szer_slupka:.1f}" height="{h:.1f}" rx="4" style="fill:{kolor}">'
                          f'<title>tydzień od {et}: {w:.0f} {html.escape(jednostka)}</title></rect>')
            czesci.append(f'<text x="{x + szer_slupka / 2:.1f}" y="{y - 5:.1f}" text-anchor="middle" font-size="10" style="fill:{KOLOR_PRZYGASZONY}">{opis}</text>')
        else:
            czesci.append(f'<rect x="{x:.1f}" y="{wys - d - 2}" width="{szer_slupka:.1f}" height="2" rx="1" style="fill:{KOLOR_OBRAMOWANIA}"/>')
        if n <= 8 or i % 2 == (n - 1) % 2:
            czesci.append(f'<text x="{x + szer_slupka / 2:.1f}" y="{wys - 8}" text-anchor="middle" font-size="10" style="fill:{KOLOR_PRZYGASZONY}">{et}</text>')
    czesci.append("</svg>")
    return ogranicz_wysokosc("".join(czesci), 220)


def karta_rekordow(rek: pd.DataFrame, ile: int = 6) -> str:
    if rek.empty:
        tresc = (f'<div style="min-height:120px;display:flex;align-items:center;justify-content:center;text-align:center;'
                 f'font-size:0.85rem;color:{KOLOR_PRZYGASZONY};">Rekordy pojawią się, gdy to samo ćwiczenie<br>zapiszesz z ciężarem w co najmniej dwóch treningach.</div>')
    else:
        wiersze = []
        for _, r in rek.head(ile).iterrows():
            skok = r["E1RM"] - r["Poprzedni"]
            wiersze.append(
                f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;padding:8px 0;'
                f'border-bottom:1px solid {KOLOR_OBRAMOWANIA};">'
                f'<div style="min-width:0;"><div style="font-weight:600;color:{KOLOR_TEKSTU};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{html.escape(r["Cwiczenie"])}</div>'
                f'<div style="font-size:0.75rem;color:{KOLOR_PRZYGASZONY};">{r["Data"]:%d.%m.%Y}</div></div>'
                f'<div style="text-align:right;white-space:nowrap;"><span style="font-weight:700;color:{KOLOR_TEKSTU};">{format_kg(round(r["E1RM"], 1))} kg</span>'
                f'<span style="font-size:0.78rem;font-weight:600;color:{ZIELONY};margin-left:8px;">▲ {format_kg(round(skok, 1))}</span></div></div>'
            )
        tresc = "".join(wiersze)
    return (
        f'<div style="{_tlo_karty(ZIELONY)}border:1px solid {KOLOR_OBRAMOWANIA};border-radius:16px;padding:16px 18px;box-sizing:border-box;min-width:0;">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;">{_naglowek_karty("Ostatnie rekordy", ZIELONY)}'
        f'<span style="font-size:0.72rem;color:{KOLOR_PRZYGASZONY};">szacowane 1RM</span></div>'
        f'<div style="margin-top:8px;">{tresc}</div></div>'
    )


KOLOR_POPRZEDNI_TYDZIEN = _kolor_motywu("poprzedni")


def karta_partii(tabela: pd.DataFrame, znacznik: int = 10) -> str:
    """Poziome słupki serii na partię: szary to poprzedni tydzień, zielony bieżący. Kreska to punkt odniesienia. Legenda pod spodem."""
    tytul = _naglowek_karty("Serie na partię", NIEBIESKI)
    if tabela.shape[1] < 2 or float(tabela.iloc[:, -2:].to_numpy().sum()) == 0:
        tresc = (f'<div style="min-height:80px;display:flex;align-items:center;justify-content:center;text-align:center;'
                 f'font-size:0.85rem;color:{KOLOR_PRZYGASZONY};">Pojawi się, gdy zapiszesz treningi z ćwiczeniami na powtórzenia.</div>')
        legenda = ""
    else:
        dane = pd.DataFrame({"Teraz": tabela.iloc[:, -1], "Poprzedni": tabela.iloc[:, -2]})
        dane = dane[(dane["Teraz"] > 0) | (dane["Poprzedni"] > 0)].sort_values(["Teraz", "Poprzedni"], ascending=False)
        maks = max(20.0, float(dane["Teraz"].max()), float(dane["Poprzedni"].max()))

        def slupek(wartosc: float, kolor: str, wysokosc: int) -> str:
            return (f'<div style="height:{wysokosc}px;border-radius:{wysokosc}px;background:{KOLOR_TLA_PIERSCIENIA};overflow:hidden;">'
                    f'<div style="width:{100 * wartosc / maks:.1f}%;height:100%;border-radius:{wysokosc}px;background:{kolor};"></div></div>')

        wiersze = []
        for partia, r in dane.iterrows():
            teraz, poprzedni = int(r["Teraz"]), int(r["Poprzedni"])
            wiersze.append(
                f'<div style="padding:8px 0;border-bottom:1px solid {KOLOR_OBRAMOWANIA};">'
                f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;">'
                f'<span style="font-weight:600;color:{KOLOR_TEKSTU};">{html.escape(str(partia))}</span>'
                f'<span style="font-weight:700;color:{KOLOR_TEKSTU};">{teraz}</span></div>'
                f'<div style="position:relative;margin-top:6px;">'
                f'{slupek(poprzedni, KOLOR_POPRZEDNI_TYDZIEN, 6)}<div style="height:3px;"></div>{slupek(teraz, ZIELONY, 8)}'
                f'<div style="position:absolute;left:{100 * znacznik / maks:.1f}%;top:-3px;bottom:-3px;width:2px;background:{KOLOR_TEKSTU};opacity:0.5;"></div>'
                f'</div></div>'
            )
        tresc = "".join(wiersze)

        def kwadracik(kolor: str) -> str:
            return f'<span style="display:inline-block;width:10px;height:10px;border-radius:3px;background:{kolor};margin-right:5px;"></span>'

        legenda = (f'<div style="display:flex;flex-wrap:wrap;gap:6px 16px;margin-top:10px;font-size:0.75rem;color:{KOLOR_PRZYGASZONY};">'
                   f'<span>{kwadracik(KOLOR_POPRZEDNI_TYDZIEN)}poprzedni tydzień</span>'
                   f'<span>{kwadracik(ZIELONY)}ten tydzień</span>'
                   f'<span><span style="display:inline-block;width:2px;height:10px;background:{KOLOR_TEKSTU};opacity:0.5;margin-right:6px;'
                   f'vertical-align:-1px;"></span>{znacznik} serii</span></div>')
    return (
        f'<div style="{_tlo_karty(NIEBIESKI)}border:1px solid {KOLOR_OBRAMOWANIA};border-radius:16px;padding:16px 18px;box-sizing:border-box;min-width:0;">'
        f'{tytul}<div style="margin-top:8px;">{tresc}</div>{legenda}</div>'
    )


# ---------------------------------------------------------------
# Widok strony
# ---------------------------------------------------------------
def widok_postepow() -> None:
    wpisy = wczytaj_wpisy()
    if wpisy.empty:
        st.info("Postępy pojawią się po pierwszym zapisanym treningu. Najwygodniej zacząć od zakładki Treningi → Rozpocznij trening.")
        return
    dzis = date.today()
    ma_ciezar = bool((wpisy["Objetosc"] > 0).any())

    # --- kafelki ---
    tren_30 = dni_treningowe(wpisy, dzis - timedelta(days=29), dzis)
    tren_30_wczesniej = dni_treningowe(wpisy, dzis - timedelta(days=59), dzis - timedelta(days=30))
    serie_7 = suma_w_oknie(wpisy, "Serie", dzis - timedelta(days=6), dzis)
    serie_7_wczesniej = suma_w_oknie(wpisy, "Serie", dzis - timedelta(days=13), dzis - timedelta(days=7))
    opis_serie, kolor_serie = _roznica(serie_7, serie_7_wczesniej)
    streak = seria_tygodni(wpisy, dzis)
    rek = rekordy(wpisy)
    nowe_rekordy = int((rek["Data"] >= pd.Timestamp(dzis - timedelta(days=29))).sum()) if not rek.empty else 0
    st.markdown(siatka_kart([
        karta_liczby("Treningi", str(tren_30), "w 30 dni", f"poprzednie 30 dni: {tren_30_wczesniej}", NIEBIESKI),
        karta_liczby("Serie", f"{serie_7:.0f}", "w 7 dni", opis_serie, kolor_serie),
        karta_liczby("Regularność", str(streak), "tyg. z rzędu" if streak != 1 else "tydzień", "min. 1 trening w tygodniu" if streak else "zacznij nową serię", ZIELONY if streak >= 2 else NIEBIESKI),
        karta_liczby("Rekordy", str(nowe_rekordy), "w 30 dni", "nowe rekordy szacowanego 1RM" if nowe_rekordy else "jeszcze bez nowych rekordów", ZIELONY if nowe_rekordy else NIEBIESKI),
    ]), unsafe_allow_html=True)
    pytajnik("Treningi: dni z zapisanym treningiem. Serie: ostatnie 7 dni. Regularność: kolejne tygodnie z co najmniej jednym treningiem "
             "(bieżący tydzień nie przerywa serii). Rekordy: liczone z ćwiczeń z ciężarem.")

    # --- tygodniowa objętość + rekordy ---
    metryki = ["Objętość (kg)", "Serie"] if ma_ciezar else ["Serie"]
    wybor_metryki = st.segmented_control("Metryka tygodnia", metryki, default=metryki[0], key="post_metryka", label_visibility="collapsed")
    kolumna = "Objetosc" if (wybor_metryki or metryki[0]) == "Objętość (kg)" else "Serie"
    tyg = tygodnie(wpisy, kolumna, dzis, 12)
    jednostka = "kg" if kolumna == "Objetosc" else "serii"
    wykres = karta_wykresu(
        "Tydzień po tygodniu", "ostatnie 12 tygodni, ciemny słupek: bieżący tydzień",
        slupki_svg([f"{t:%d.%m}" for t, _ in tyg], [w for _, w in tyg], jednostka),
        komunikat_pusty="Brak treningów w ostatnich 12 tygodniach.",
    )
    st.markdown(siatka_postepow([wykres, karta_rekordow(rek)]), unsafe_allow_html=True)
    pytajnik("Tydzień po tygodniu: ostatnie 12 tygodni, ciemny słupek to bieżący tydzień.")

    # --- serie na partię mięśniową ---
    st.markdown(siatka_postepow([karta_partii(serie_na_partie(wpisy, partie_cwiczen(), dzis))], kolumny=1), unsafe_allow_html=True)
    pytajnik("Serie na partię: tylko serie robocze w ćwiczeniach liczonych w powtórzeniach (rozgrzewki i cardio nie wchodzą), "
             "a ćwiczenie liczy się do jednej, przypisanej partii. Zwykle podaje się 10–20 serii tygodniowo na partię jako punkt "
             "odniesienia dla przyrostu mięśni. To orientacja, nie norma.")
    partie = partie_cwiczen()
    bez_partii = sorted(n for n in wpisy["Cwiczenie"].unique() if partie.get(n, "Inne") == "Inne"
                        and jednostka_powtorzen(wpisy.loc[wpisy["Cwiczenie"] == n, "Jednostka"].iloc[0]))
    if bez_partii:
        with st.expander(f"Ćwiczenia bez partii ({len(bez_partii)})"):
            if "post_partia_info" in st.session_state:
                st.success(st.session_state.pop("post_partia_info"))
            st.selectbox("Ćwiczenie", bez_partii, index=None, placeholder="Wybierz ćwiczenie...", key="post_partia_cwiczenie")
            st.selectbox("Partia", [p for p in lista_partii() if p != "Inne"], index=None, placeholder="Wybierz partię...", key="post_partia_wybor")
            st.button("Zapisz partię", use_container_width=True, on_click=_przypisz_z_formularza, key="post_partia_btn")

    # --- wybrane ćwiczenie ---
    st.subheader("Wybrane ćwiczenie")
    ostatnie = wpisy.groupby("Cwiczenie")["Data"].max().sort_values(ascending=False)
    cwiczenie = st.selectbox("Ćwiczenie", ostatnie.index.tolist(), key="post_cwiczenie", label_visibility="collapsed")
    if not cwiczenie:
        return
    jednostka_cw = jednostka_cwiczenia(wpisy, cwiczenie)
    dzienne = dzienne_dla_cwiczenia(wpisy, cwiczenie)
    ma_e1rm = dzienne["E1RM"].notna().any()
    nazwy_metryk: dict[str, tuple[str, str, int]] = {}   # nazwa -> (kolumna, jednostka, miejsca po przecinku)
    if ma_e1rm:
        nazwy_metryk["Szac. 1RM"] = ("E1RM", "kg", 1)
        nazwy_metryk["Maks. ciężar"] = ("Maks_ciezar", "kg", 1)
    elif (dzienne["Maks_ciezar"] > 0).any():
        nazwy_metryk["Maks. ciężar"] = ("Maks_ciezar", "kg", 1)
    nazwy_metryk[f"Łącznie ({'powt.' if jednostka_powtorzen(jednostka_cw) else jednostka_cw})"] = ("Powt_lacznie", "" if jednostka_powtorzen(jednostka_cw) else jednostka_cw, 0)

    k1, k2 = st.columns(2)
    with k1:
        wybrana_metryka = st.segmented_control("Co pokazać", list(nazwy_metryk), default=list(nazwy_metryk)[0], key="post_metryka_cw", label_visibility="collapsed")
    with k2:
        wybrany_zakres = st.segmented_control("Zakres", list(ZAKRESY), default="90 dni", key="post_zakres", label_visibility="collapsed")
    kol, jedn, miejsca = nazwy_metryk.get(wybrana_metryka or list(nazwy_metryk)[0])
    dni_zakresu = ZAKRESY.get(wybrany_zakres or "90 dni")
    w_zakresie = dzienne if dni_zakresu is None else dzienne[dzienne.index >= pd.Timestamp(dzis - timedelta(days=dni_zakresu - 1))]
    seria = w_zakresie[kol].where(w_zakresie[kol] > 0).dropna()

    najlepszy = dzienne[kol].max()
    dzien_najlepszego = dzienne[kol].idxmax() if pd.notna(najlepszy) else None
    ostatni_wpis = dzienne.iloc[-1]
    if len(seria) >= 2:
        zmiana = seria.iloc[-1] - seria.iloc[0]
        opis_zmiany = f"{'▲' if zmiana > 0 else '▼' if zmiana < 0 else '='} {abs(zmiana):.{miejsca}f} {jedn}".replace(".", ",").strip()
        kolor_zmiany = ZIELONY if zmiana > 0 else POMARANCZOWY if zmiana < 0 else NIEBIESKI
        zmiana_txt = f"{seria.iloc[0]:.{miejsca}f} → {seria.iloc[-1]:.{miejsca}f}".replace(".", ",")
    else:
        opis_zmiany, kolor_zmiany, zmiana_txt = "za mało danych w zakresie", NIEBIESKI, "-"
    ostatnie_wiersze = wpisy[(wpisy["Cwiczenie"] == cwiczenie) & (wpisy["Data"] == dzienne.index[-1])]
    ostatnie_wiersze = ostatnie_wiersze[ostatnie_wiersze["Sesja"] == ostatnie_wiersze["Sesja"].max()]   # tylko ostatni trening z tego dnia
    opis_ostatniego = skroc_opis(opis_serii(zgrupuj_wiersze(ostatnie_wiersze), jednostka_cw))
    st.markdown(siatka_kart([
        karta_liczby("Najlepszy wynik", f"{najlepszy:.{miejsca}f}".replace(".", ",") if pd.notna(najlepszy) else "-", jedn,
                     f"{dzien_najlepszego:%d.%m.%Y}" if dzien_najlepszego is not None else "", ZIELONY),
        karta_liczby("Ostatni trening", f"{dzienne.index[-1]:%d.%m}", f"{(dzis - dzienne.index[-1].date()).days} dni temu",
                     opis_ostatniego, NIEBIESKI),
        karta_liczby("Zmiana w zakresie", zmiana_txt, jedn if len(seria) >= 2 else "", opis_zmiany, kolor_zmiany),
        karta_liczby("Treningi", str(len(dzienne)), "raz" if len(dzienne) == 1 else "razy", "z tym ćwiczeniem w historii", NIEBIESKI),
    ]), unsafe_allow_html=True)
    pytajnik("Najlepszy wynik: w całej historii tego ćwiczenia. Zmiana w zakresie: od pierwszego do ostatniego pomiaru w wybranym "
             "zakresie dni. Na wykresie każdy punkt to jeden dzień.")
    st.markdown(siatka_postepow([karta_wykresu(
        f"{cwiczenie}: {wybrana_metryka or list(nazwy_metryk)[0]}", "każdy punkt to jeden dzień",
        ogranicz_wysokosc(wykres_liniowy_svg(seria, jedn, miejsca=miejsca, wysokosc=190), 240),
        komunikat_pusty="Potrzebne są co najmniej 2 treningi z tym ćwiczeniem w wybranym zakresie.",
    )], kolumny=1), unsafe_allow_html=True)

    # --- tabela z historią ćwiczenia ---
    wiersze = []
    for data, grupa in wpisy[wpisy["Cwiczenie"] == cwiczenie].groupby("Data"):
        grupy = zgrupuj_wiersze(grupa)
        wiersze.append({
            "Data": data.strftime("%d.%m.%Y"), "Serie": opis_serii(grupy, jednostka_cw),
            "Szac. 1RM (kg)": round(grupa["E1RM"].max(), 1) if grupa["E1RM"].notna().any() else None,
            "Objętość (kg)": round(grupa["Objetosc"].sum()) if grupa["Objetosc"].sum() else None,
            "_d": data,
        })
    tabela = pd.DataFrame(wiersze).sort_values("_d", ascending=False).drop(columns="_d")
    with st.expander(f"Historia ćwiczenia ({len(tabela)})"):
        st.dataframe(tabela, use_container_width=True, hide_index=True)
    pytajnik("Szacowane 1RM to wzór Epleya (ciężar × (1 + powtórzenia / 30)), liczony do 12 powtórzeń. To przybliżenie, nie test siłowy.")

