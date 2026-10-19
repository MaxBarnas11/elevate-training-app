"""Karty z kolorowymi pierścieniami (HTML/SVG) dla strony Start."""
from __future__ import annotations

import math
from datetime import date

from motywy import CZCIONKA_TYTULOW, poswiata, v

# Kolory to zmienne CSS motywu (jasny/ciemny), patrz motywy.py
KOLOR_KARTY = v("karta")
KOLOR_OBRAMOWANIA = v("obram")
KOLOR_TLA_PIERSCIENIA = v("tlo_pier")
KOLOR_TEKSTU = v("tekst")
KOLOR_PRZYGASZONY = v("przyg")

ZIELONY = v("zielony")
ZOLTY = v("zolty")
POMARANCZOWY = v("pomaranczowy")
CZERWONY = v("czerwony")
NIEBIESKI = v("akcent")   # kolor neutralny (nazwa historyczna)


def tlo_przezr(kolor: str, procent: int) -> str:
    """Kolor z przezroczystością (zamiast doklejania cyfr szesnastkowych)."""
    return f"color-mix(in srgb, {kolor} {procent}%, transparent)"


def kolor_snu(wynik: float | None) -> str:
    """Zielony od 80, żółty 50-79, czerwony poniżej 50."""
    if wynik is None:
        return KOLOR_PRZYGASZONY
    if wynik >= 80:
        return ZIELONY
    if wynik >= 50:
        return ZOLTY
    return CZERWONY


def status_snu(wynik: float | None) -> str:
    if wynik is None:
        return "Brak danych"
    if wynik >= 90:
        return "Doskonały"
    if wynik >= 80:
        return "Dobry"
    if wynik >= 50:
        return "Średni"
    return "Słaby"


def _tlo_karty(kolor: str) -> str:
    """Tło karty z miękką poświatą w kolorze statusu (w ciemnym motywie słabszą)."""
    return f"background:{poswiata(kolor, 33)}, {KOLOR_KARTY};"


def _naglowek_karty(tytul: str, kolor: str) -> str:
    """Tytuł karty z małą świecącą kropką w kolorze statusu."""
    return (
        f'<div style="display:flex;align-items:center;gap:8px;font-size:0.85rem;color:{KOLOR_PRZYGASZONY};">'
        f'<span style="width:8px;height:8px;border-radius:50%;background:{kolor};box-shadow:0 0 8px {kolor};"></span>'
        f'{tytul}</div>'
    )


def karta_pierscien(tytul: str, wartosc: float | None, maks: float,
                    kolor: str, status: str = "", podpis: str = "",
                    tekst_srodka: str | None = None) -> str:
    """Karta z wyśrodkowanym pierścieniem. tekst_srodka nadpisuje liczbę w środku (np. '8h 19m')."""
    promien = 44
    obwod = 2 * math.pi * promien
    if wartosc is None:
        udzial, napis = 0.0, "–"
    else:
        udzial = max(0.0, min(wartosc / maks, 1.0))
        napis = tekst_srodka if tekst_srodka else f"{wartosc:.0f}"
    dlugosc = obwod * udzial
    rozmiar = 26 if len(napis) <= 3 else 17

    return (
        f'<div style="{_tlo_karty(kolor)}border:1px solid {KOLOR_OBRAMOWANIA};border-radius:16px;'
        f'padding:16px 18px;height:230px;box-sizing:border-box;display:flex;flex-direction:column;">'
        f'{_naglowek_karty(tytul, kolor)}'
        f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;'
        f'justify-content:center;text-align:center;">'
        f'<svg width="104" height="104" viewBox="0 0 110 110">'
        f'<circle cx="55" cy="55" r="{promien}" fill="none" style="stroke:{KOLOR_TLA_PIERSCIENIA}" stroke-width="10"/>'
        f'<circle cx="55" cy="55" r="{promien}" fill="none" style="stroke:{kolor}" stroke-width="10" '
        f'stroke-linecap="round" stroke-dasharray="{dlugosc:.1f} {obwod:.1f}" transform="rotate(-90 55 55)"/>'
        f'<text x="55" y="{55 + rozmiar * 0.35:.0f}" text-anchor="middle" font-size="{rozmiar}" '
        f'font-weight="700" style="fill:{KOLOR_TEKSTU}">{napis}</text>'
        f'</svg>'
        f'<div style="font-size:1.25rem;font-weight:700;line-height:1.2;color:{kolor};margin-top:6px;">{status}</div>'
        f'<div style="font-size:0.8rem;color:{KOLOR_PRZYGASZONY};min-height:1em;">{podpis}</div>'
        f'</div></div>'
    )


def karta_wartosc(tytul: str, wartosc: float | None, jednostka: str,
                  kolor: str = NIEBIESKI, podpis: str = "",
                  seria: list[float] | None = None,
                  pasmo: tuple[float, float] | None = None,
                  plakietka: str = "", miejsca: int = 0) -> str:
    """Karta z wyśrodkowaną liczbą, statusem i małym wykresem ostatnich dni."""
    napis = "-" if wartosc is None else f"{wartosc:.{miejsca}f}".replace(".", ",")
    wykres = sparkline_svg(seria, pasmo, kolor) if seria else ""
    return (
        f'<div style="{_tlo_karty(kolor)}border:1px solid {KOLOR_OBRAMOWANIA};border-radius:16px;'
        f'padding:16px 18px;height:230px;box-sizing:border-box;display:flex;flex-direction:column;">'
        f'{_naglowek_karty(tytul, kolor)}'
        f'<div style="text-align:center;margin-top:10px;">'
        f'<span style="font-size:2.4rem;font-weight:700;color:{KOLOR_TEKSTU};">{napis}</span>'
        f'<span style="font-size:1rem;color:{KOLOR_PRZYGASZONY};margin-left:6px;">{jednostka}</span></div>'
        f'<div style="text-align:center;font-size:0.85rem;font-weight:600;color:{kolor};margin-top:2px;">{podpis}</div>'
        f'{plakietka}'
        f'<div style="margin-top:auto;">{wykres}</div>'
        f'</div>'
    )


def format_czasu(minuty: float) -> str:
    """Zamienia minuty na zapis '8h 19m'."""
    godziny, reszta = divmod(int(round(minuty)), 60)
    return f"{godziny}h {reszta}m"


def kolor_czasu_snu(minuty: float | None) -> str:
    if minuty is None:
        return KOLOR_PRZYGASZONY
    if minuty >= 420:      # 7 h i więcej
        return ZIELONY
    if minuty >= 360:      # 6-7 h
        return ZOLTY
    return CZERWONY


def status_czasu_snu(minuty: float | None) -> str:
    if minuty is None:
        return "Brak danych"
    if minuty >= 420:
        return "Dobry"
    if minuty >= 360:
        return "Krótki"
    return "Bardzo krótki"


def sparkline_svg(wartosci: list[float], pasmo: tuple[float, float] | None = None,
                  kolor: str = NIEBIESKI) -> str:
    """Mały wykres liniowy (SVG) z opcjonalnym zielonym pasmem normy."""
    if len(wartosci) < 2:
        return ""
    szer, wys = 200, 44
    dolny, gorny = min(wartosci), max(wartosci)
    if pasmo:
        dolny, gorny = min(dolny, pasmo[0]), max(gorny, pasmo[1])
    zakres = (gorny - dolny) or 1.0

    def y(v: float) -> float:
        return wys - 4 - (v - dolny) / zakres * (wys - 8)

    krok = szer / (len(wartosci) - 1)
    punkty = " ".join(f"{i * krok:.1f},{y(v):.1f}" for i, v in enumerate(wartosci))
    pasmo_svg = ""
    if pasmo:
        g, d = y(pasmo[1]), y(pasmo[0])
        pasmo_svg = (f'<rect x="0" y="{g:.1f}" width="{szer}" height="{d - g:.1f}" '
                     f'style="fill:{ZIELONY}" fill-opacity="0.18"/>')
    return (
        f'<svg viewBox="0 0 {szer} {wys}" width="100%" height="{wys}" '
        f'preserveAspectRatio="none" style="display:block;">'
        f'{pasmo_svg}'
        f'<polyline points="{punkty}" fill="none" style="stroke:{kolor}" stroke-width="2" '
        f'stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>'
        f'</svg>'
    )


def ocena_wzgledem_pasma(wartosc: float | None, pasmo: tuple[float, float] | None,
                         wyzsze_lepiej: bool) -> tuple[str, str]:
    """Zwraca (kolor, status) na podstawie tego, gdzie wartość leży względem Twojej normy.
    RHR: wyższe = gorzej (wyzsze_lepiej=False). HRV: wyższe = lepiej (wyzsze_lepiej=True)."""
    if wartosc is None:
        return KOLOR_PRZYGASZONY, "Brak danych"
    if pasmo is None:
        return NIEBIESKI, "Zbieram dane do normy"
    dolna, gorna = pasmo
    if dolna <= wartosc <= gorna:
        return ZIELONY, "W Twojej normie"
    if wartosc > gorna:
        return (ZIELONY, "Powyżej normy") if wyzsze_lepiej else (POMARANCZOWY, "Podwyższone")
    return (POMARANCZOWY, "Poniżej normy") if wyzsze_lepiej else (ZIELONY, "Niskie")


def plakietka_zmiany(wartosc: float | None, srednia: float | None,
                     wyzsze_lepiej: bool, jednostka: str = "") -> str:
    """Mała plakietka: o ile dzisiejsza wartość różni się od średniej z 7 dni."""
    if wartosc is None or srednia is None:
        return ""
    roznica = wartosc - srednia
    if abs(roznica) < 0.5:
        kolor, tekst = KOLOR_PRZYGASZONY, "≈ jak średnia z 7 dni"
    else:
        dobrze = (roznica > 0) == wyzsze_lepiej
        kolor = ZIELONY if dobrze else POMARANCZOWY
        strzalka = "▲" if roznica > 0 else "▼"
        tekst = f"{strzalka} {roznica:+.0f} {jednostka} vs śr. 7 dni".replace("  ", " ")
    return (
        f'<div style="margin-top:6px;text-align:center;">'
        f'<span style="display:inline-block;background:{tlo_przezr(kolor, 15)};color:{kolor};border-radius:999px;'
        f'padding:2px 10px;font-size:0.75rem;font-weight:600;">{tekst}</span></div>'
    )

def oblicz_gotowosc(czas_snu_min: float | None, rhr: float | None,
                    srednia_rhr: float | None) -> dict:
    """Prosty wynik gotowości (0-100%) ze snu i tętna spoczynkowego."""
    punkty, maks, linie = 0.0, 0, []

    if czas_snu_min is not None:
        p = 50 * max(0.0, min((czas_snu_min - 300) / 180, 1.0))
        punkty += p
        maks += 50
        linie.append(f"Sen {format_czasu(czas_snu_min)}: {p:.0f}/50 pkt (8h i więcej = komplet)")
    else:
        linie.append("Sen: brak danych")

    if rhr is not None and srednia_rhr is not None:
        roznica = rhr - srednia_rhr
        p = 50 * max(0.0, min(0.6 - roznica * 0.08, 1.0))
        punkty += p
        maks += 50
        linie.append(f"RHR {rhr:.0f} bpm przy Twojej średniej {srednia_rhr:.0f}: {p:.0f}/50 pkt "
                     f"(poniżej średniej = więcej punktów)")
    elif rhr is not None:
        linie.append("RHR: za mało dni w bazie, żeby policzyć średnią")
    else:
        linie.append("RHR: brak danych")

    if maks == 0:
        return {"procent": None, "kolor": KOLOR_PRZYGASZONY, "status": "Brak danych",
                "podpis": "", "linie": linie}

    procent = round(punkty / maks * 100)
    if procent >= 80:
        kolor, status = ZIELONY, "Świetna forma"
    elif procent >= 60:
        kolor, status = ZOLTY, "Dobra forma"
    elif procent >= 40:
        kolor, status = POMARANCZOWY, "Umiarkowana"
    else:
        kolor, status = CZERWONY, "Słaba regeneracja"
    return {"procent": procent, "kolor": kolor, "status": status,
            "podpis": f"{punkty:.0f}/{maks} pkt", "linie": linie}


def karta_tekst(tytul: str, linie: list[str]) -> str:
    """Karta z kilkoma liniami tekstu (wyjaśnienie wyniku)."""
    tresc = "".join(
        f'<div style="font-size:0.9rem;color:{KOLOR_TEKSTU};margin-bottom:8px;">{l}</div>' for l in linie
    )
    return (
        f'<div style="background:{KOLOR_KARTY};border:1px solid {KOLOR_OBRAMOWANIA};'
        f'border-radius:16px;padding:16px 18px;min-height:200px;box-sizing:border-box;">'
        f'<div style="font-size:0.85rem;color:{KOLOR_PRZYGASZONY};margin-bottom:10px;">{tytul}</div>'
        f'{tresc}</div>'
    )

def siatka_kart(karty: list[str]) -> str:
    """Układa karty w siatce 4 kolumn z jednakowym odstępem w poziomie i w pionie."""
    return (
        '<style>'
        '.siatka-kart{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;}'
        '@media (max-width:1000px){.siatka-kart{grid-template-columns:repeat(2,minmax(0,1fr));}}'
        '</style>'
        '<div class="siatka-kart">' + "".join(karty) + '</div>'
    )


def naglowek_strony(tytul: str, podtytul: str = "", kolor: str = NIEBIESKI) -> str:
    """Nagłówek strony w stylu plansz technicznych: drobna linia opisu, duży napis z szerokiej czcionki.
    Napis ma trójkolorową poświatę (pomarańcz, fiolet, róż); w jasnym motywie jaśniejszą.
    Parametr `kolor` zostaje dla zgodności ze starym kodem."""
    dzis = date.today()
    najdluzsze_slowo = max((len(s) for s in str(tytul).split()), default=5)
    rozmiar = f"min(3.2rem, calc((100vw - 3rem) / {max(najdluzsze_slowo, 5) * 0.92:.2f}))"   # najdłuższe słowo mieści się w jednej linii
    napis_daty = f"{dzis:%d.%m.%Y}"
    podpis = (
        f'<div style="font-size:0.9rem;color:{KOLOR_PRZYGASZONY};margin-top:12px;letter-spacing:0.01em;">{podtytul}</div>'
        if podtytul else ""
    )
    meta = (f"font-size:0.68rem;letter-spacing:0.2em;text-transform:uppercase;color:{KOLOR_PRZYGASZONY};"
            "display:flex;justify-content:space-between;align-items:center;")
    return (
        f'<div style="padding:30px 4px 18px 4px;margin:0 0 14px 0;">'
        f'<div style="{meta}"><span>● ELEVATE</span><span>{napis_daty} ✦</span></div>'
        f'<div style="height:1px;background:{v("obram2")};margin:10px 0 14px 0;"></div>'
        f'<div style="font-family:{CZCIONKA_TYTULOW};font-weight:800;font-stretch:125%;text-transform:uppercase;'
        f'font-size:{rozmiar};line-height:1.02;letter-spacing:0.01em;color:{KOLOR_TEKSTU};'
        f'overflow-wrap:anywhere;'
        f'text-shadow:-9px 0 9px {v("tytul_glow2")},9px 0 9px {v("tytul_glow3")},0 8px 14px {v("tytul_glow1")};">{tytul}</div>'
        f'{podpis}</div>'
    )
