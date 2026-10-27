"""Wspólna warstwa „szkła” (liquid glass) dla całej aplikacji: wybór kategorii, przyciski, pola, listy, karty.

Kolory idą ze zmiennych motywu (--e-…), więc działa w obu motywach. Stałe elementy (ramka w gradiencie,
połysk u góry, delikatna mgiełka w kolorach motywu) są zdefiniowane raz jako zmienne --sz-… i używane wszędzie,
żeby wszystkie elementy trzymały ten sam poziom wykonania. Selektory są oparte na strukturze Streamlita 1.65
(react-aria: role="group", data-selected, data-focus-within, stSelectboxVirtualDropdown).
"""
from __future__ import annotations

CSS_SZKLO = """
<style>
:root, .stApp {
    --sz-mgla: linear-gradient(135deg, color-mix(in srgb, var(--e-tytul_glow2) 38%, transparent) 0%, transparent 42%, color-mix(in srgb, var(--e-tytul_glow3) 38%, transparent) 100%);
    --sz-mgla-lekka: linear-gradient(135deg, color-mix(in srgb, var(--e-tytul_glow2) 14%, transparent) 0%, transparent 45%, color-mix(in srgb, var(--e-tytul_glow3) 14%, transparent) 100%);
    --sz-baza: color-mix(in srgb, var(--e-kafelek) 84%, transparent);
    --sz-ramka: linear-gradient(100deg, var(--e-g1), var(--e-g2) 55%, var(--e-g3));
    --sz-polysk: inset 0 1px 0 color-mix(in srgb, white 18%, transparent);
    --sz-cien: 0 6px 16px -4px color-mix(in srgb, var(--e-tytul_glow1) 55%, transparent);
    /* Szkło na całej powierzchni przycisku: jaśniejsza górna połowa z miękką krawędzią w połowie wysokości,
       lekko ciemniejszy dół i równy, delikatny odcień motywu od lewej do prawej (wcześniej mgiełka była tylko w rogach). */
    --sz-blask: linear-gradient(180deg, light-dark(rgba(255,255,255,.55), rgba(255,255,255,.075)) 0%,
                light-dark(rgba(255,255,255,.22), rgba(255,255,255,.03)) 46%, transparent 54%,
                light-dark(rgba(90,65,25,.06), rgba(0,0,0,.18)) 100%);
    --sz-odcien: linear-gradient(110deg, color-mix(in srgb, var(--e-tytul_glow2) 16%, transparent), color-mix(in srgb, var(--e-tytul_glow3) 16%, transparent));
    --sz-krawedz: inset 0 1px 0 light-dark(rgba(255,255,255,.7), rgba(255,255,255,.14)), inset 0 -1px 0 light-dark(rgba(90,65,25,.08), rgba(0,0,0,.35));
    --sz-ruch: transform .16s cubic-bezier(.2,.8,.2,1), box-shadow .2s ease, border-color .2s ease, filter .2s ease, background-color .2s ease;
}

/* ---------- Wybór kategorii, długości przerw itp. (segmenty i pigułki): osobne szklane pigułki ---------- */
[data-testid="stButtonGroup"] :has(> [data-variant]) {
    gap: 8px !important; border: none !important; background: transparent !important; box-shadow: none !important;
    padding: 2px !important; border-radius: 0 !important;
}
[data-testid="stButtonGroup"] [data-variant] {
    border-radius: 999px !important; min-height: 2.6rem !important; padding: 0 1rem !important;
    border: 1.5px solid var(--e-obram2) !important;
    background: var(--sz-blask), var(--sz-odcien), var(--sz-baza) !important;
    box-shadow: var(--sz-krawedz) !important; color: var(--e-tekst) !important;
    transition: var(--sz-ruch);
}
[data-testid="stButtonGroup"] [data-variant] p { font-weight: 600 !important; color: inherit !important; }
[data-testid="stButtonGroup"] [data-variant]:hover { border-color: var(--e-obram_hover) !important; filter: brightness(1.12); }
[data-testid="stButtonGroup"] [data-variant]:active { transform: scale(0.97); }
[data-testid="stButtonGroup"] [data-variant][data-selected] {
    border-color: transparent !important;
    background: var(--sz-blask) padding-box, var(--sz-mgla) padding-box, linear-gradient(var(--e-kafelek), var(--e-kafelek)) padding-box, var(--sz-ramka) border-box !important;
    box-shadow: var(--sz-krawedz), var(--sz-cien) !important;
}
[data-testid="stButtonGroup"] [data-variant][data-selected] p { font-weight: 800 !important; }

/* ---------- Znaczek „?” pod blokiem: przy prawej krawędzi, tuż pod kartą (nie luźno z lewej) ---------- */
[class*="st-key-pytajnik_"] {
    flex-direction: row !important; justify-content: flex-end !important; align-items: center !important;
    margin-top: -0.9rem !important; margin-bottom: -0.3rem !important;
}
[class*="st-key-pytajnik_"] > * { width: auto !important; flex: 0 0 auto !important; }

/* ---------- Pola (lista wyboru, tekst, liczba, godzina): szklane pole z gradientową ramką po wejściu ---------- */
[role="group"][data-rac] {
    border-radius: 14px !important; min-height: 3rem;
    border: 1.5px solid var(--e-obram2) !important;
    background: var(--sz-blask), var(--sz-odcien), var(--sz-baza) !important;
    box-shadow: var(--sz-krawedz) !important;
    transition: border-color .2s ease, box-shadow .2s ease, background .2s ease;
}
[role="group"][data-rac][data-hovered] { border-color: var(--e-obram_hover) !important; }
/* Aktywne pole: tylko jaśniejsza ramka (bez kolorowej poświaty wokół), tak jak przyciski */
[role="group"][data-rac][data-focus-within] { border-color: var(--e-obram_hover) !important; }
[role="group"][data-rac] input, [role="group"][data-rac] textarea { background: transparent !important; font-weight: 600; }
[role="group"][data-rac] button { background: transparent !important; }
/* Jedna warstwa: tło i poświatę ma tylko zewnętrzne szklane pole. Wnętrze (samo pole tekstowe, także w stanie aktywnym)
   jest przezroczyste; „html body” podnosi ważność reguły ponad kolory pól ustawiane w app.py (css_pol). */
html body [role="group"][data-rac] *:not(svg):not(path):not(input:-webkit-autofill) {
    background: transparent !important; background-color: transparent !important; box-shadow: none !important;
}

/* ---------- Otwarta lista wyboru: szklany panel, wygodne pozycje ---------- */
[data-testid="stSelectboxVirtualDropdown"] {
    border-radius: 18px !important; overflow: hidden; margin-top: 6px !important;
    border: 1.5px solid var(--e-obram2) !important;
    background: var(--sz-mgla-lekka), color-mix(in srgb, var(--e-kafelek) 90%, transparent) !important;
    -webkit-backdrop-filter: blur(18px) saturate(150%); backdrop-filter: blur(18px) saturate(150%);
    box-shadow: var(--sz-polysk), 0 18px 40px var(--e-cien_m) !important;
}
[data-testid="stSelectboxVirtualDropdown"] > *, [data-testid="stSelectboxVirtualDropdown"] [role="listbox"] { background: transparent !important; }
[data-testid="stSelectboxVirtualDropdown"] [role="option"] {
    border-radius: 12px !important; margin: 2px 6px !important; padding: 0.7rem 0.9rem !important;
    font-weight: 600; color: var(--e-tekst) !important; background: transparent !important; transition: background .15s ease;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"][data-focused], [data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover {
    background: var(--sz-mgla) !important;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"], [data-testid="stSelectboxVirtualDropdown"] [role="option"][data-selected] {
    background: var(--sz-mgla) !important; box-shadow: inset 3px 0 0 var(--e-g2); font-weight: 800;
}

/* ---------- Duże przyciski-kafelki (Treningi): szkło w kolorze kafelka ---------- */
.st-key-tryby_wiersz button, [class*="st-key-tryby_powrot_"] button {
    background:
        radial-gradient(130% 150% at 0% 0%, color-mix(in srgb, var(--kafel) calc(var(--mocnosc) * 1.5), transparent) 0%, transparent 62%),
        linear-gradient(100deg, color-mix(in srgb, var(--kafel) var(--mocnosc), var(--e-karta)) 0%, var(--e-karta) 78%) !important;
    border: 1.5px solid color-mix(in srgb, var(--kafel) 55%, var(--e-obram2)) !important;
    box-shadow: inset 0 1px 0 color-mix(in srgb, white 20%, transparent),
                inset 0 -14px 24px color-mix(in srgb, var(--kafel) 12%, transparent),
                0 10px 26px color-mix(in srgb, var(--kafel) 20%, transparent) !important;
}
.st-key-tryby_wiersz button::after, [class*="st-key-tryby_powrot_"] button::after {
    background: linear-gradient(160deg, color-mix(in srgb, var(--kafel) 62%, white) 0%, var(--kafel) 70%);
    box-shadow: inset 0 1px 0 color-mix(in srgb, white 40%, transparent), 0 4px 12px color-mix(in srgb, var(--kafel) 40%, transparent);
}

/* ---------- Przyciski zwykłe i główne ---------- */
.stButton > button[data-testid="stBaseButton-secondary"], [data-testid="stFormSubmitButton"] > button[kind="secondaryFormSubmit"],
.stDownloadButton > button {
    border: 1.5px solid var(--e-obram2) !important; border-radius: 14px !important;
    background: var(--sz-blask), var(--sz-odcien), var(--sz-baza) !important;
    box-shadow: var(--sz-krawedz) !important; transition: var(--sz-ruch) !important;
}
.stButton > button:active, [data-testid="stFormSubmitButton"] > button:active, .stDownloadButton > button:active,
[data-testid="stButtonGroup"] [data-variant]:active {
    transform: scale(0.97) !important; filter: brightness(1.08);
}
.stButton > button[data-testid="stBaseButton-secondary"]:hover, .stDownloadButton > button:hover {
    border-color: var(--e-obram_hover) !important; filter: brightness(1.12);
}
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"] {
    border-radius: 14px !important; border: 1.5px solid color-mix(in srgb, white 22%, var(--e-przycisk)) !important;
    background-image: linear-gradient(180deg, rgba(255,255,255,.20) 0%, rgba(255,255,255,.06) 46%, transparent 54%, rgba(0,0,0,.10) 100%),
                      var(--e-przycisk-grad) !important;
    box-shadow: inset 0 1px 0 color-mix(in srgb, white 45%, transparent), inset 0 -1px 0 rgba(0, 0, 0, 0.18),
                0 8px 18px -6px color-mix(in srgb, var(--e-przycisk) 55%, transparent) !important;
    transition: var(--sz-ruch) !important;
}

/* ---------- Karty, formularze, panele, okna ---------- */
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stForm"], [data-testid="stExpander"],
[class*="st-key-kafelek_"], [class*="st-key-blok_cwiczenia_"] {
    border-width: 1.5px !important; border-radius: 18px !important;
    box-shadow: var(--sz-polysk), 0 8px 22px var(--e-cien_m) !important;
}
/* Rozwijane panele: bez ucinania zawartości (ucinanie robiło prostokątne krawędzie poświaty przycisków w środku) */
[data-testid="stExpander"] { overflow: visible !important; }
[data-testid="stExpander"] details { border-radius: inherit !important; }
[data-testid="stExpander"] summary { border-radius: 12px !important; }

/* Płynne pojawianie się: treść okna po zmianie kroku i nowe elementy w oknach */
@keyframes sz-wejscie { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
[data-testid="stDialog"] [data-testid="stElementContainer"], [data-testid="stDialog"] [data-testid="stLayoutWrapper"],
[role="dialog"] [data-testid="stElementContainer"] {
    animation: sz-wejscie .22s cubic-bezier(.2,.8,.2,1) both;
}
@media (prefers-reduced-motion: reduce) {
    [data-testid="stDialog"] [data-testid="stElementContainer"], [role="dialog"] [data-testid="stElementContainer"] { animation: none; }
    .stButton > button, [data-testid="stButtonGroup"] [data-variant] { transition: none !important; }
}
[data-testid="stDialog"] [role="dialog"] {
    border-radius: 22px !important; border: 1.5px solid var(--e-obram2) !important;
    box-shadow: var(--sz-polysk), 0 24px 60px var(--e-cien_m) !important;
}
</style>
"""


def css_szklo() -> str:
    """CSS szkła + kolory dla okienek, które Streamlit rysuje poza aplikacją (lista wyboru i okna dialogowe).
    Okienko nie leży w `.stApp`, więc nie dziedziczyło ciemnego motywu i wychodziło jasne (kolory --e-* to light-dark(),
    a ten wybiera wariant według color-scheme elementu). Podajemy mu motyw wprost."""
    import streamlit as st
    try:
        motyw = st.context.theme.type
    except Exception:
        motyw = None
    schemat = motyw if motyw in ("light", "dark") else "light dark"
    return CSS_SZKLO + (
        "<style>[data-baseweb=\"popover\"], [data-baseweb=\"popover\"] *, [data-testid=\"stSelectboxVirtualDropdown\"], "
        "[data-testid=\"stSelectboxVirtualDropdown\"] *, [data-testid=\"stDialog\"], [data-testid=\"stDialog\"] *, "
        "[role=\"dialog\"], [role=\"dialog\"] *, [data-baseweb=\"modal\"], [data-baseweb=\"modal\"] * "
        f"{{ color-scheme: {schemat}; }}</style>"
    )
