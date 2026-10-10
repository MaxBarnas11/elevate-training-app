"""Karty ćwiczeń w presetach (HTML z animacją) dla strony Treningi."""
from __future__ import annotations


import html as _html

import pandas as pd

KARTY_CWICZEN_CSS = """
<style>
@keyframes cw-wjazd {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}
.cw-top { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; margin-bottom:4px; }
.cw-tytul { font-size:1.4rem; font-weight:700; color:#1B1B1A; }
.cw-tagi span { display:inline-block; background:#F4ECDC; border:1px solid #CFC2A6; border-radius:999px;
                padding:4px 12px; font-size:0.8rem; color:#6B6355; margin-left:6px; }
.cw-cel { color:#6B6355; font-size:0.9rem; margin:2px 0 6px 0; }
.cw-sekcja { font-size:0.8rem; letter-spacing:0.12em; text-transform:uppercase; color:#6B6355; margin:18px 0 10px 0; }
.cw-karta { display:flex; align-items:center; gap:16px; padding:14px 18px; margin-bottom:10px;
            border:1px solid #CFC2A6; border-radius:16px; box-shadow:0 4px 14px rgba(60,45,20,0.12);
            background:radial-gradient(ellipse at 0% 50%, #8A6D3B1F 0%, transparent 60%), #F4ECDC;
            animation:cw-wjazd 0.45s ease both; transition:transform 0.15s ease, box-shadow 0.15s ease; }
.cw-karta:hover { transform:translateY(-2px); box-shadow:0 8px 20px rgba(60,45,20,0.22); }
.cw-dodatek { background:#EDE3CF; opacity:0.9; }
.cw-num { width:34px; height:34px; border-radius:50%; flex:none; display:flex; align-items:center; justify-content:center;
          font-weight:700; color:#F4ECDC; background:#1B1B1A; }
.cw-dodatek .cw-num { background:#DCD0B8; color:#6B6355; }
.cw-tresc { flex:1; min-width:0; }
.cw-nazwa { font-weight:600; font-size:1.02rem; color:#1B1B1A; }
.cw-sub { color:#6B6355; font-size:0.82rem; margin-top:3px; }
.cw-wsk { color:#7A5F2E; }
.cw-ikona { margin-right:6px; color:#7A6A4F; }
.cw-plakietka { background:#EFE3C9; border:1px solid #CFC2A6; border-radius:12px; padding:8px 14px;
                font-weight:700; font-size:1.05rem; white-space:nowrap; color:#1B1B1A; }
@media (max-width:640px) { .cw-karta { flex-wrap:wrap; } }
@media (prefers-reduced-motion: reduce) { .cw-karta { animation:none; transition:none; } }
</style>
"""

_ETYKIETY_JEDNOSTEK = {"powt.": "", "powt./nogę": " /nogę", "powt./stronę": " /stronę",
                       "s": " s", "m": " m", "min": " min"}


def _int_lub_none(wartosc):
    return None if wartosc is None or pd.isna(wartosc) else int(wartosc)


def format_serii(serie, od, do, jednostka) -> str:
    """Zamienia dane ćwiczenia na zapis typu '4 × 6–10', '45–60 s' albo '500 m'."""
    serie, od, do = _int_lub_none(serie), _int_lub_none(od), _int_lub_none(do)
    jednostka = jednostka if isinstance(jednostka, str) else "powt."
    koncowka = _ETYKIETY_JEDNOSTEK.get(jednostka, "")
    if od is None:
        return f"{serie} serie" if serie else ""
    zakres = f"{od}–{do}" if do is not None and do != od else f"{od}"
    # jedna "seria" czasu lub dystansu (np. 30-45 min, 500 m) zapisujemy bez mnożnika
    if jednostka in ("s", "m", "min") and serie in (None, 1):
        return f"{zakres}{koncowka}"
    return f"{serie or 1} × {zakres}{koncowka}"


def karta_cwiczenia(numer: int, nazwa: str, serie_tekst: str, zamiennik: str = "",
                    wskazowka: str = "", dodatek: bool = False, opoznienie_ms: int = 0) -> str:
    """Jedna karta ćwiczenia: numer, nazwa, serie i powtórzenia oraz zamiennik i wskazówka pod spodem."""
    e = _html.escape
    podpisy = ""
    if zamiennik:
        podpisy += f'<div class="cw-sub"><span class="cw-ikona">⇄</span>Zamiennik: {e(zamiennik)}</div>'
    if wskazowka:
        podpisy += f'<div class="cw-sub cw-wsk">{e(wskazowka)}</div>'
    klasa = "cw-karta cw-dodatek" if dodatek else "cw-karta"
    return (
        f'<div class="{klasa}" style="animation-delay:{opoznienie_ms}ms;">'
        f'<div class="cw-num">{"+" if dodatek else numer}</div>'
        f'<div class="cw-tresc"><div class="cw-nazwa">{e(nazwa)}</div>{podpisy}</div>'
        f'<div class="cw-plakietka">{e(serie_tekst)}</div>'
        f'</div>'
    )


def widok_presetu_html(nazwa: str, kategoria: str, typ: str, cel: str, cwiczenia: pd.DataFrame) -> str:
    """Cały preset jako nagłówek i dwie sekcje kart: ćwiczenia główne oraz dodatki."""
    e = _html.escape
    glowne = cwiczenia[cwiczenia["Rola"] != "Dodatek"]
    dodatki = cwiczenia[cwiczenia["Rola"] == "Dodatek"]

    tagi = f'<span>{e(str(kategoria))}</span>'
    if str(typ) != str(kategoria):          # żeby nie powtarzać np. "Cardio" dwa razy
        tagi += f'<span>{e(str(typ))}</span>'
    tagi += f'<span>{len(glowne)} głównych' + (f' + {len(dodatki)} dod.' if len(dodatki) else '') + '</span>'
    czesci = [
        KARTY_CWICZEN_CSS,
        f'<div class="cw-top"><div class="cw-tytul">{e(nazwa)}</div><div class="cw-tagi">{tagi}</div></div>',
    ]
    if cel:
        czesci.append(f'<div class="cw-cel">{e(cel)}</div>')

    licznik = 0

    def sekcja(tytul: str, tabela: pd.DataFrame, dodatek: bool) -> None:
        nonlocal licznik
        if tabela.empty:
            return
        czesci.append(f'<div class="cw-sekcja">{tytul}</div>')
        for numer, (_, w) in enumerate(tabela.iterrows(), start=1):
            czesci.append(karta_cwiczenia(
                numer, str(w["Cwiczenie"]),
                format_serii(w["Serie"], w["Powt_od"], w["Powt_do"], w["Jednostka"]),
                str(w["Alternatywa"] or ""), str(w["Wskazowka"] or ""),
                dodatek=dodatek, opoznienie_ms=licznik * 60,
            ))
            licznik += 1

    sekcja("Główne ćwiczenia", glowne, dodatek=False)
    sekcja("Dodatki (opcjonalnie)", dodatki, dodatek=True)
    return "".join(czesci)