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
.cw-tytul { font-size:1.4rem; font-weight:700; color:var(--e-tekst); }
.cw-tagi span { display:inline-block; background:var(--e-pill); border:1px solid var(--e-obram); border-radius:999px;
                padding:4px 12px; font-size:0.8rem; color:var(--e-przyg); margin-left:6px; }
.cw-cel { color:var(--e-przyg); font-size:0.9rem; margin:2px 0 6px 0; }
.cw-sekcja { font-size:0.8rem; letter-spacing:0.12em; text-transform:uppercase; color:var(--e-przyg); margin:18px 0 10px 0; }
.cw-karta { display:flex; align-items:center; gap:16px; padding:14px 18px; margin-bottom:10px;
            border:1px solid var(--e-obram); border-radius:16px; box-shadow:0 4px 14px var(--e-cien_s);
            background:radial-gradient(ellipse at 0% 50%, var(--e-glow_presetu) 0%, transparent 60%), var(--e-karta);
            animation:cw-wjazd 0.45s ease both; transition:transform 0.15s ease, box-shadow 0.15s ease; }
.cw-karta:hover { transform:translateY(-2px); box-shadow:0 8px 20px var(--e-cien_h); }
.cw-dodatek { background:var(--e-dodatek); opacity:0.9; }
.cw-num { width:34px; height:34px; border-radius:50%; flex:none; display:flex; align-items:center; justify-content:center;
          font-weight:700; color:var(--e-dzis_tekst); background-color:var(--e-przycisk); background-image:var(--e-przycisk-grad); }
.cw-dodatek .cw-num { background:var(--e-tlo_pier); background-image:none; color:var(--e-przyg); }
.cw-tresc { flex:1; min-width:0; }
.cw-nazwa { font-weight:600; font-size:1.02rem; color:var(--e-tekst); }
.cw-sub { color:var(--e-przyg); font-size:0.82rem; margin-top:3px; }
.cw-wsk { color:var(--e-wsk); }
.cw-ikona { margin-right:6px; color:var(--e-akcent); }
.cw-plakietka { background:var(--e-plakietka); border:1px solid var(--e-obram); border-radius:12px; padding:8px 14px;
                font-weight:700; font-size:1.05rem; white-space:nowrap; color:var(--e-tekst); }
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

    # Bez dodatkowych pigułek z kategorią i typem (to już jest w nazwie) i bez szarego opisu: zostaje tylko liczba ćwiczeń
    tagi = f'<span>{len(glowne)} głównych' + (f' + {len(dodatki)} dod.' if len(dodatki) else '') + '</span>'
    czesci = [
        KARTY_CWICZEN_CSS,
        f'<div class="cw-top"><div class="cw-tytul">{e(nazwa)}</div><div class="cw-tagi">{tagi}</div></div>',
    ]

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
