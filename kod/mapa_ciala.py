"""Mapa ciała: sylwetka z przodu i z tyłu, w której partie mięśniowe są pokolorowane wg liczby serii (Postępy).

Rysunek jest własny (proste kształty SVG), kolory to zmienne motywu `--e-mapa_*`, więc działa w jasnym i ciemnym motywie.
Skala to stopnie od „brak” do „ponad zakres”; progi są w jednym miejscu (STOPNIE), żeby łatwo je zmieniać.
"""
from __future__ import annotations

import html

from motywy import v as _kolor

# (od ilu serii, nazwa, opis zakresu). Stopień 0 to brak serii.
STOPNIE = [
    (0, "brak", "0"),
    (1, "mało", "1–4"),
    (5, "ok", "5–9"),
    (10, "idealnie", "10–16"),
    (17, "dużo", "17–20"),
    (21, "bardzo dużo", "21–25"),
    (26, "ponad zakres", "26+"),
]

# Partia -> obszary rysunku. Obszary: przód (p_...), tył (t_...). Brak partii w słowniku = nie pokazujemy na sylwetce.
OBSZARY = {
    "Klatka": ["p_klatka"],
    "Barki przód": ["p_barki_przod"],
    "Barki bok": ["p_barki_bok", "t_barki_bok"],
    "Barki tył": ["t_barki_tyl"],
    "Biceps": ["p_biceps"],
    "Triceps": ["t_triceps"],
    "Plecy szerokie": ["t_plecy_szerokie"],
    "Plecy górne": ["t_plecy_gorne"],
    "Plecy dolne": ["t_dol_plecow"],
    "Brzuch": ["p_brzuch"],
    "Czworogłowe": ["p_czworoglowe"],
    "Przywodziciele": ["p_przywodziciele"],
    "Dwugłowe uda": ["t_dwuglowe"],
    "Pośladki": ["t_posladki"],
    "Łydki": ["p_lydki", "t_lydki"],
}


def stopien(serie: float) -> int:
    """Numer stopnia skali (0-6) dla liczby serii."""
    if serie <= 0:
        return 0
    wynik = 1                       # każda dodatnia liczba serii to co najmniej „mało” (też ułamki, np. pół serii)
    for i, (od, _, _) in enumerate(STOPNIE):
        if i > 0 and serie >= od:
            wynik = i
    return wynik


# Kształty lewej strony ciała (patrzymy na sylwetkę: lewa połowa rysunku). Prawą dostajemy odbiciem względem x = 80.
# Układ współrzędnych: 160 × 340, środek ciała x = 80.
_LEWA = {
    # --- przód ---
    "p_klatka": "M79 50 C69 47 57 50 53 60 C51 74 62 86 79 84 Z",
    "p_barki_przod": "M53 52 C50 50.5 46 49.5 43 49.5 L41.5 80.3 C43 80 44.5 79.7 46 79 C51 75 54 64 56 56 Z",
    "p_barki_bok": "M43 49.5 C37 50 33 55 32 67 C32 76 37 80.5 41.5 80.3 Z",
    "p_biceps": "M33 80 C27 88 26 100 28 110 C32 115 41 115 45 110 C48 100 47 88 44 80 C41 77 36 77 33 80 Z",
    "p_brzuch": "M80 88 L67 88 C64 102 64 126 67 142 C71 148 76 148 80 148 Z",
    "p_czworoglowe": "M60 152 C51 176 50 210 56 238 C61 244 72 244 76 238 C79 210 78 178 76 152 C70 148 64 148 60 152 Z",
    "p_przywodziciele": "M76 158 C79 180 79 212 76 238 L80 238 L80 158 Z",
    "p_lydki": "M58 250 C53 270 55 296 62 312 C66 316 72 316 74 312 C78 296 78 270 74 250 C69 246 62 246 58 250 Z",
    # --- tył ---
    "t_plecy_gorne": "M79 48 C67 48 55 54 52 66 C60 82 70 92 79 100 Z",
    "t_plecy_szerokie": "M52 66 C50 88 58 106 69 116 C73 118 76 118 79 118 L79 100 C70 92 60 82 52 66 Z",
    "t_dol_plecow": "M79 120 L67 120 C65 130 66 140 69 146 L79 146 Z",
    "t_barki_tyl": "M53 52 C50 50.5 46 49.5 43 49.5 L41.5 80.3 C43 80 44.5 79.7 46 79 C51 75 54 64 56 56 Z",
    "t_barki_bok": "M43 49.5 C37 50 33 55 32 67 C32 76 37 80.5 41.5 80.3 Z",
    "t_triceps": "M33 80 C27 88 26 100 28 110 C32 115 41 115 45 110 C48 100 47 88 44 80 C41 77 36 77 33 80 Z",
    "t_posladki": "M79 150 C68 146 57 150 56 163 C56 176 65 182 79 181 Z",
    "t_dwuglowe": "M58 186 C51 206 51 224 57 240 C62 245 72 245 76 240 C79 224 79 206 77 186 C71 182 63 182 58 186 Z",
    "t_lydki": "M58 252 C53 270 55 296 62 312 C66 316 72 316 74 312 C79 296 79 270 75 252 C69 248 62 248 58 252 Z",
}

# Elementy bez partii (stałe tło): szyja, przedramiona, dłonie, boki tułowia, miednica, kolana, stopy
_TLO_LEWA = [
    "M79 44 L70 44 L67 52 C62 52 56 53 52 56 C60 62 70 54 79 52 Z",                   # kark / szyja
    "M29 114 C24 128 21 144 22 158 C26 163 34 163 37 158 C39 144 43 128 46 114 Z",    # przedramię
    "M22 160 C19 168 20 177 25 180 C30 178 34 169 36 160 Z",                          # dłoń
    "M54 90 C52 110 53 130 57 148 C60 150 63 150 66 148 C64 128 64 108 66 90 Z",      # bok tułowia
    "M56 144 C54 156 55 164 60 170 L79 170 L79 144 Z",                                # miednica
    "M58 238 L76 238 L74 252 L58 252 Z",                                              # kolano
    "M59 314 C56 324 56 332 61 336 L77 336 C77 328 75 320 72 314 Z",                  # stopa
]


def _kontur() -> str:
    return f'stroke="{_kolor("mapa_kontur")}" stroke-width="1" stroke-linejoin="round"'


def _obie_strony(sciezka: str, wypelnienie: str, dodatek: str = "") -> str:
    lewa = f'<path d="{sciezka}" fill="{wypelnienie}" {_kontur()} {dodatek}/>'
    prawa = f'<g transform="translate(160,0) scale(-1,1)"><path d="{sciezka}" fill="{wypelnienie}" {_kontur()} {dodatek}/></g>'
    return lewa + prawa


def _sylwetka(widok: str, kolory: dict[str, str]) -> str:
    """Jedna sylwetka (widok 'p' = przód, 't' = tył). `kolory`: obszar -> zmienna koloru."""
    tlo = _kolor("mapa_tlo")
    elementy = [
        f'<ellipse cx="80" cy="22" rx="13" ry="16" fill="{tlo}" {_kontur()}/>',     # głowa
        f'<rect x="73" y="36" width="14" height="13" fill="{tlo}"/>',                 # szyja
        f'<path d="M56 52 C50 58 48 84 54 112 C56 130 58 144 60 150 L100 150 C102 144 104 130 106 112 C112 84 110 58 104 52 Z" fill="{tlo}"/>',  # tułów
    ]
    for kształt in _TLO_LEWA:
        elementy.append(_obie_strony(kształt, tlo))
    for obszar, sciezka in _LEWA.items():
        if not obszar.startswith(widok + "_"):
            continue
        elementy.append(_obie_strony(sciezka, kolory.get(obszar, _kolor("mapa_0"))))
    if widok == "p":      # linie brzucha
        elementy.append(f'<g stroke="{_kolor("mapa_kontur")}" stroke-width="1" opacity="0.7">'
                        '<path d="M80 86 L80 146"/><path d="M68 100 L92 100"/><path d="M67 114 L93 114"/><path d="M68 128 L92 128"/></g>')
    nazwa = "przód" if widok == "p" else "tył"
    return f'<svg viewBox="0 0 160 340" role="img" aria-label="Sylwetka, {nazwa}" style="width:100%;height:auto;display:block;">{"".join(elementy)}</svg>'


def kolory_obszarow(serie: dict[str, float]) -> dict[str, str]:
    """Obszar rysunku -> kolor wg liczby serii partii (partie bez rysunku pomijamy)."""
    wynik: dict[str, str] = {}
    for partia, obszary in OBSZARY.items():
        kolor = _kolor(f"mapa_{stopien(float(serie.get(partia, 0) or 0))}")
        for o in obszary:
            wynik[o] = kolor
    return wynik


def mapa_ciala_html(serie: dict[str, float], kolor_tekstu: str, kolor_przygaszony: str, kolor_obramowania: str) -> str:
    """Dwie sylwetki obok siebie (przód i tył), legenda stopni i lista partii z liczbą serii."""
    kolory = kolory_obszarow(serie)
    sylwetki = (
        '<div style="display:flex;gap:4px;justify-content:center;align-items:flex-start;">'
        f'<div style="flex:1 1 0;min-width:0;max-width:210px;">{_sylwetka("p", kolory)}</div>'
        f'<div style="flex:1 1 0;min-width:0;max-width:210px;">{_sylwetka("t", kolory)}</div></div>'
    )
    legenda = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:5px;white-space:nowrap;">'
        f'<span style="width:11px;height:11px;border-radius:3px;background:{_kolor(f"mapa_{i}")};flex:none;"></span>'
        f'{html.escape(nazwa)} {html.escape(zakres)}</span>'
        for i, (_, nazwa, zakres) in enumerate(STOPNIE)
    )
    legenda = (f'<div style="display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:10px;font-size:0.75rem;color:{kolor_przygaszony};">'
               f'{legenda}</div>')
    wiersze = []
    for partia, n in sorted(((p, float(serie.get(p, 0) or 0)) for p in OBSZARY), key=lambda x: -x[1]):
        if n <= 0:
            continue
        wiersze.append(
            f'<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid {kolor_obramowania};">'
            f'<span style="width:10px;height:10px;border-radius:50%;background:{_kolor(f"mapa_{stopien(n)}")};flex:none;"></span>'
            f'<span style="font-weight:600;color:{kolor_tekstu};flex:1;">{html.escape(partia)}</span>'
            f'<span style="color:{kolor_przygaszony};">{html.escape(STOPNIE[stopien(n)][1])}</span>'
            f'<span style="font-weight:700;color:{kolor_tekstu};min-width:2ch;text-align:right;">{f"{n:g}".replace(".", ",")}</span></div>')
    lista = f'<div style="margin-top:8px;">{"".join(wiersze)}</div>' if wiersze else ""
    return sylwetki + legenda + lista
