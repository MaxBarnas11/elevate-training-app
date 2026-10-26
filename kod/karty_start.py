"""Nowe kafelki na stronie Start: kroki, kalorie, stres, fazy snu i tydzień treningowy."""
from __future__ import annotations

import html

from motywy import kolor_typu
from karty import (
    KOLOR_OBRAMOWANIA, KOLOR_TLA_PIERSCIENIA, KOLOR_TEKSTU, KOLOR_PRZYGASZONY, KOLOR_KARTY,
    ZIELONY, ZOLTY, POMARANCZOWY, CZERWONY, NIEBIESKI,
    karta_pierscien, karta_wartosc, format_czasu, _tlo_karty, _naglowek_karty,
)

# ---------------------------------------------------------------
# NOWE KAFELKI NA STRONIE START: kroki, kalorie, stres, fazy snu, tydzień treningowy
# ---------------------------------------------------------------
KOLOR_FAZ = {                 # kolory faz snu takie jak w Garmin Connect
    "gleboki": "#0679D1",     # głęboki: ciemny niebieski
    "lekki": "#3A9BF5",       # lekki: jasny niebieski
    "rem": "#CC3AC1",         # REM: fiolet/magenta
    "czuwanie": "#E265CF",    # czuwanie: różowy
}


def _spacje(liczba: float) -> str:
    """12345 -> '12 345' (twarda spacja, żeby liczba nie łamała się w połowie)."""
    return f"{int(round(liczba)):,}".replace(",", " ")


def karta_kroki(kroki: int | None, cel: int | None = None) -> str:
    """Pierścień kroków względem celu dziennego (domyślnie 10 000)."""
    cel = cel or 10000
    podpis = f"cel: {_spacje(cel)}"
    if kroki is None:
        return karta_pierscien("Kroki", None, cel, KOLOR_PRZYGASZONY, "Brak danych", podpis)
    udzial = kroki / cel
    if udzial >= 1:
        kolor, status = ZIELONY, "Cel osiągnięty"
    elif udzial >= 0.6:
        kolor, status = ZOLTY, "Dobry ruch"
    else:
        kolor, status = NIEBIESKI, "Dzień w toku"   # rano mało kroków to nie "zły" wynik
    return karta_pierscien("Kroki", kroki, cel, kolor, status, podpis, tekst_srodka=_spacje(kroki))


def karta_kalorie(aktywne: int | None, spoczynkowe: int | None) -> str:
    """Spalone kcal: suma, a pod spodem pasek podziału na aktywne i spoczynkowe."""
    if aktywne is None and spoczynkowe is None:
        suma_tekst, pasek = "-", ""
    else:
        a, s = aktywne or 0, spoczynkowe or 0
        suma_tekst = _spacje(a + s)
        udzial = a / (a + s) * 100 if (a + s) else 0
        pasek = (
            f'<div style="margin-top:auto;">'
            f'<div style="display:flex;height:10px;border-radius:999px;overflow:hidden;background:{KOLOR_TLA_PIERSCIENIA};">'
            f'<div style="width:{udzial:.0f}%;background:{POMARANCZOWY};"></div></div>'
            f'<div style="display:flex;justify-content:space-between;font-size:0.78rem;color:{KOLOR_PRZYGASZONY};margin-top:8px;">'
            f'<span>aktywne <b style="color:{KOLOR_TEKSTU};">{_spacje(a)}</b></span>'
            f'<span>spoczynkowe <b style="color:{KOLOR_TEKSTU};">{_spacje(s)}</b></span></div></div>'
        )
    return (
        f'<div style="{_tlo_karty(NIEBIESKI)}border:1px solid {KOLOR_OBRAMOWANIA};border-radius:16px;'
        f'padding:16px 18px;height:230px;box-sizing:border-box;display:flex;flex-direction:column;">'
        f'{_naglowek_karty("Spalone kcal", NIEBIESKI)}'
        f'<div style="text-align:center;margin-top:10px;">'
        f'<span style="font-size:2.4rem;font-weight:700;color:{KOLOR_TEKSTU};">{suma_tekst}</span>'
        f'<span style="font-size:1rem;color:{KOLOR_PRZYGASZONY};margin-left:6px;">kcal</span></div>'
        f'<div style="text-align:center;font-size:0.85rem;font-weight:600;color:{NIEBIESKI};margin-top:2px;">dziś łącznie</div>'
        f'{pasek}</div>'
    )


def _kolor_stresu(stres: float | None) -> tuple[str, str]:
    """Strefy stresu wg Garmina: do 25 odpoczynek, do 50 niski, do 75 średni, powyżej wysoki."""
    if stres is None:
        return KOLOR_PRZYGASZONY, "Brak danych"
    if stres <= 25:
        return ZIELONY, "Odpoczynek"
    if stres <= 50:
        return ZIELONY, "Niski stres"
    if stres <= 75:
        return ZOLTY, "Średni stres"
    return CZERWONY, "Wysoki stres"


def karta_stres(stres: float | None, seria=None, do_dnia=None, liczba_dni: int = 7) -> str:
    """Stres dziś (0-100) i słupki z ostatnich 7 dni (stała skala 0-100, kolor = strefa stresu Garmina).
    seria: kolumna Stres z tabeli pandas z indeksem dat; do_dnia: ostatni dzień wykresu (dziś)."""
    from datetime import date, timedelta

    skroty = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]
    do_dnia = do_dnia or date.today()
    kolor, status = _kolor_stresu(stres)
    wartosci = {}
    if seria is not None:
        wartosci = {d.date(): float(v) for d, v in seria.items() if v == v}

    mala = f"font-size:0.62rem;line-height:1;color:{KOLOR_PRZYGASZONY};"
    wysokosc = 40   # px słupka przy wartości 100
    kolumny = []
    for i in range(liczba_dni - 1, -1, -1):
        dzien = do_dnia - timedelta(days=i)
        dzis = dzien == do_dnia
        v = wartosci.get(dzien)
        if v is None:
            liczba = f'<div style="{mala}">-</div>'
            slupek = f'<div style="width:100%;height:3px;border-radius:2px;background:{KOLOR_TLA_PIERSCIENIA};"></div>'
            opis = f"{dzien:%d.%m}: brak danych"
        else:
            k, _ = _kolor_stresu(v)
            liczba = f'<div style="{mala}{"color:" + KOLOR_TEKSTU + ";font-weight:700;" if dzis else ""}">{v:.0f}</div>'
            slupek = (f'<div style="width:100%;height:{max(v / 100 * wysokosc, 3):.0f}px;border-radius:4px 4px 2px 2px;'
                      f'background:{k};opacity:{1 if dzis else 0.75};"></div>')
            opis = f"{dzien:%d.%m}: {v:.0f} / 100"
        kolumny.append(
            f'<div title="{opis}" style="flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;gap:3px;">'
            f'<div style="height:{wysokosc + 14}px;width:60%;display:flex;flex-direction:column;justify-content:flex-end;'
            f'align-items:center;gap:3px;">{liczba}{slupek}</div>'
            f'<div style="{mala}{"color:" + KOLOR_TEKSTU + ";font-weight:700;" if dzis else ""}">{skroty[dzien.weekday()]}</div></div>'
        )

    def punkt(kol: str, opis: str) -> str:
        return (f'<span style="display:inline-flex;align-items:center;gap:4px;margin:0 6px;">'
                f'<span style="width:6px;height:6px;border-radius:50%;background:{kol};opacity:0.8;"></span>{opis}</span>')

    legenda = (
        f'<div style="text-align:center;margin-top:6px;{mala}opacity:0.85;">'
        f'{punkt(ZIELONY, "do 50")}{punkt(ZOLTY, "51–75")}{punkt(CZERWONY, "76+")}</div>'
    )
    napis = "-" if stres is None else f"{stres:.0f}"
    return (
        f'<div style="{_tlo_karty(kolor)}border:1px solid {KOLOR_OBRAMOWANIA};border-radius:16px;'
        f'padding:16px 18px;height:230px;box-sizing:border-box;display:flex;flex-direction:column;">'
        f'{_naglowek_karty("Stres", kolor)}'
        f'<div style="text-align:center;margin-top:6px;">'
        f'<span style="font-size:2.4rem;font-weight:700;color:{KOLOR_TEKSTU};">{napis}</span>'
        f'<span style="font-size:1rem;color:{KOLOR_PRZYGASZONY};margin-left:6px;">/ 100</span></div>'
        f'<div style="text-align:center;font-size:0.85rem;font-weight:600;color:{kolor};margin-top:2px;">{status}</div>'
        f'<div style="margin-top:auto;"><div style="display:flex;gap:4px;">{"".join(kolumny)}</div>{legenda}</div></div>'
    )


def _legenda_faz(srednie: dict) -> str:
    nazwy = [("gleboki", "Głęboki"), ("lekki", "Lekki"), ("rem", "REM"), ("czuwanie", "Czuwanie")]
    elementy = []
    for klucz, nazwa in nazwy:
        wartosc = srednie.get(klucz)
        tekst = format_czasu(wartosc) if wartosc is not None else "-"
        elementy.append(
            f'<span style="display:inline-flex;align-items:center;gap:6px;margin-right:14px;white-space:nowrap;">'
            f'<span style="width:10px;height:10px;border-radius:3px;background:{KOLOR_FAZ[klucz]};"></span>'
            f'{nazwa} <b style="color:{KOLOR_TEKSTU};">{tekst}</b></span>'
        )
    return (
        f'<div style="font-size:0.78rem;color:{KOLOR_PRZYGASZONY};margin-top:10px;line-height:1.7;">'
        f'<span style="margin-right:12px;opacity:0.8;">Średnio na noc:</span>{"".join(elementy)}</div>'
    )


def karta_sen_fazy(dane, do_dnia, liczba_dni: int = 14) -> str:
    """Szeroka karta: słupki faz snu (głęboki, REM, lekki, czuwanie) z ostatnich dni.
    dane: tabela pandas z indeksem dat i kolumnami Sen_gleboki, Sen_rem, Sen_lekki, Sen_czuwanie (minuty)."""
    from datetime import timedelta

    skroty = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]
    kolumny = [("czuwanie", "Sen_czuwanie"), ("rem", "Sen_rem"), ("lekki", "Sen_lekki"), ("gleboki", "Sen_gleboki")]
    nazwy = {"gleboki": "głęboki", "rem": "REM", "lekki": "lekki", "czuwanie": "czuwanie"}

    wiersze = {data.date(): wiersz for data, wiersz in dane.iterrows()}
    dni = []
    for i in range(liczba_dni - 1, -1, -1):
        dzien = do_dnia - timedelta(days=i)
        wiersz = wiersze.get(dzien)
        minuty = {}
        for faza, kol in kolumny:
            w = wiersz[kol] if wiersz is not None else None
            minuty[faza] = None if w is None or w != w else float(w)   # w != w to NaN
        dni.append((dzien, minuty))

    sumy = [sum(v or 0 for v in m.values()) for _, m in dni]
    skala = max(480.0, max(sumy)) if sumy else 480.0   # słupek 8 h = prawie pełna wysokość
    srednie = {}
    for faza, _ in kolumny:
        wartosci = [m[faza] for _, m in dni if m[faza] is not None]
        srednie[faza] = sum(wartosci) / len(wartosci) if wartosci else None

    slupki = []
    for (dzien, m), suma in zip(dni, sumy):
        if suma <= 0:
            wnetrze = f'<div style="height:3px;background:{KOLOR_TLA_PIERSCIENIA};"></div>'
            opis = f"{dzien:%d.%m}: brak danych"
        else:
            segmenty = "".join(
                f'<div style="height:{(m[f] or 0) / skala * 100:.1f}%;background:{KOLOR_FAZ[f]};"></div>'
                for f, _ in kolumny if m[f]
            )
            wnetrze = segmenty
            opis = f"{dzien:%d.%m}: " + ", ".join(
                f"{nazwy[f]} {format_czasu(m[f])}" for f, _ in reversed(kolumny) if m[f]
            ) + f" (razem {format_czasu(suma)})"
        dzis = dzien == do_dnia
        slupki.append(
            f'<div style="flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;gap:4px;">'
            f'<div title="{opis}" style="height:120px;width:100%;display:flex;flex-direction:column;'
            f'justify-content:flex-end;border-radius:6px 6px 2px 2px;overflow:hidden;">{wnetrze}</div>'
            f'<div style="font-size:0.62rem;line-height:1.15;text-align:center;color:{KOLOR_TEKSTU if dzis else KOLOR_PRZYGASZONY};'
            f'font-weight:{700 if dzis else 400};">{skroty[dzien.weekday()]}<br>{dzien.day}</div></div>'
        )

    return (
        f'<div style="grid-column:span 2;{_tlo_karty(NIEBIESKI)}border:1px solid {KOLOR_OBRAMOWANIA};border-radius:16px;'
        f'padding:16px 18px;min-height:260px;box-sizing:border-box;display:flex;flex-direction:column;">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;">'
        f'{_naglowek_karty("Sen: fazy z ostatnich 14 dni", NIEBIESKI)}'
        f'<span style="font-size:0.75rem;color:{KOLOR_PRZYGASZONY};">dane z Garmina</span></div>'
        f'<div style="display:flex;gap:6px;align-items:flex-end;margin-top:14px;">{"".join(slupki)}</div>'
        f'{_legenda_faz(srednie)}</div>'
    )


def _dni_slownie(dni: int | None) -> str:
    if dni is None:
        return "brak"
    if dni == 0:
        return "dziś"
    return "1 dzień" if dni == 1 else f"{dni} dni"


def _mini_statystyka(etykieta: str, wartosc: str) -> str:
    return (
        f'<div style="flex:1;text-align:center;">'
        f'<div style="font-size:1.35rem;font-weight:700;color:{KOLOR_TEKSTU};">{wartosc}</div>'
        f'<div style="font-size:0.75rem;color:{KOLOR_PRZYGASZONY};">{etykieta}</div></div>'
    )


def karta_tydzien(podsumowanie: dict) -> str:
    """Szeroka karta 'Twój tydzień treningowy': kropki Pn-Nd i trzy liczby pod spodem.
    podsumowanie: wynik plan.podsumowanie_tygodnia()."""
    if podsumowanie["zaplanowane"] == 0:
        kolor = NIEBIESKI
    elif podsumowanie["zalegle"] == 0:
        kolor = ZIELONY
    elif podsumowanie["zalegle"] == 1:
        kolor = ZOLTY
    else:
        kolor = POMARANCZOWY

    kolumny = []
    for d in podsumowanie["dni"]:
        kolor_dnia = kolor_typu(d["typ"]) or KOLOR_TEKSTU      # rodzaj treningu ma swój kolor
        if d["zrobiony"]:
            kropka = (
                f'<div style="width:34px;height:34px;border-radius:50%;background:{kolor_dnia};display:flex;'
                f'align-items:center;justify-content:center;">'
                f'<svg width="16" height="16" viewBox="0 0 16 16"><polyline points="3,8.5 6.5,12 13,4.5" fill="none" '
                f'style="stroke:var(--e-przycisk_tekst)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg></div>'
            )
        elif d["planowany"] and d["przeszlosc"]:      # zaległy: pomarańczowy pierścień
            kropka = f'<div style="width:30px;height:30px;border-radius:50%;border:2px solid {POMARANCZOWY};"></div>'
        elif d["planowany"]:                          # dziś lub w przyszłości: ciemny pierścień
            kropka = f'<div style="width:30px;height:30px;border-radius:50%;border:2px solid {kolor_dnia};"></div>'
        else:                                         # dzień wolny: mała kropka
            kropka = f'<div style="width:8px;height:8px;border-radius:50%;background:{KOLOR_TLA_PIERSCIENIA};"></div>'
        podpis = html.escape(d["typ"] or "trening") if (d["planowany"] or d["zrobiony"]) else "wolne"   # nazwa presetu wpisana przez użytkownika
        kolumny.append(
            f'<div style="flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;gap:6px;">'
            f'<div style="font-size:0.8rem;font-weight:{700 if d["dzis"] else 400};'
            f'color:{KOLOR_TEKSTU if d["dzis"] else KOLOR_PRZYGASZONY};">{d["skrot"]}</div>'
            f'<div style="height:34px;display:flex;align-items:center;justify-content:center;">{kropka}</div>'
            f'<div style="font-size:0.66rem;color:{KOLOR_PRZYGASZONY};max-width:100%;white-space:nowrap;'
            f'overflow:hidden;text-overflow:ellipsis;">{podpis}</div>'
            f'<div style="height:3px;width:16px;border-radius:2px;background:{KOLOR_TEKSTU if d["dzis"] else "transparent"};"></div>'
            f'</div>'
        )

    wykonane = podsumowanie["wykonane"]
    treningi = f'{wykonane} / {podsumowanie["zaplanowane"]}' if podsumowanie["zaplanowane"] else str(wykonane)
    kg = podsumowanie["objetosc_kg"]
    objetosc = f"{kg / 1000:.1f}".replace(".", ",") + " t" if kg >= 1000 else f"{_spacje(kg)} kg"

    return (
        f'<div style="grid-column:span 2;{_tlo_karty(kolor)}border:1px solid {KOLOR_OBRAMOWANIA};border-radius:16px;'
        f'padding:16px 18px;min-height:260px;box-sizing:border-box;display:flex;flex-direction:column;">'
        f'{_naglowek_karty("Twój tydzień treningowy", kolor)}'
        f'<div style="display:flex;gap:4px;margin-top:16px;">{"".join(kolumny)}</div>'
        f'<div style="display:flex;gap:8px;margin-top:auto;padding-top:14px;border-top:1px solid {KOLOR_OBRAMOWANIA};">'
        f'{_mini_statystyka("treningi w tym tygodniu", treningi)}'
        f'{_mini_statystyka("od ostatniego treningu", _dni_slownie(podsumowanie["dni_od_ostatniego"]))}'
        f'{_mini_statystyka("objętość tygodnia", objetosc)}</div></div>'
    )
