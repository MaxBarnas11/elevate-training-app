"""Interfejs aplikacji Training Buddy (zakładki, formularz)."""
from __future__ import annotations

from datetime import date, timedelta
import html
import json
from pathlib import Path
import sys

_KOD = str(Path(__file__).resolve().parent / "kod")   # moduły aplikacji leżą w folderze kod/
if _KOD not in sys.path:
    sys.path.insert(0, _KOD)

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from garminconnect import (
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

import baza
import logowanie
import uzytkownik
from garmin import formatuj_czas, ostatnie_zapisane_dane, synchronizuj_garmin
from rekomendacje import rekomendacje_na_dzis, trening_dzis_zapisany
from motywy import PALETA, kolor_typu
from szklo import css_szklo
from styl import naglowek, zastosuj_styl
from wykresy import MIN_DNI_DLA_PASMA, SEN_PASMO, pasmo_osobiste, rysuj_wykres
from karty import (
    karta_pierscien, karta_wartosc, kolor_snu, status_snu,
    kolor_czasu_snu, status_czasu_snu, naglowek_strony, format_czasu, ocena_wzgledem_pasma, oblicz_gotowosc, karta_tekst, siatka_kart,
    ZIELONY, ZOLTY, POMARANCZOWY, NIEBIESKI, KOLOR_PRZYGASZONY,
)
from karty_start import karta_kroki, karta_kalorie, karta_stres, karta_sen_fazy, karta_tydzien
import dziennik
import regeneracja
import sesja_treningowa
import postepy
import profil
import uwagi
from karty_presety import widok_presetu_html
from presety import (wczytaj_presety_startowe, lista_presetow, wczytaj_cwiczenia_presetu,
                     zapisz_cwiczenia_presetu, JEDNOSTKI, ROLE, MAKS_GLOWNYCH)
from datetime import datetime
from plan import (wczytaj_plan, zapisz_plan, podsumowanie_tygodnia, plan_na_dzien, trening_zapisany,
                  NAZWY_DNI, SKROTY_DNI, nazwa_krotka)

# Wczytuje zmienne z pliku .env (email i hasło do Garmina)
load_dotenv()

NAZWA_APLIKACJI = "OVRLD"
_IKONA = Path(__file__).parent / "static" / "ikona-180.png"
st.set_page_config(
    page_title=NAZWA_APLIKACJI, page_icon=str(_IKONA) if _IKONA.exists() else "🏋️", layout="wide",
    initial_sidebar_state="expanded",
)
logowanie.wymagaj_logowania()   # przy wymaganym logowaniu: ekran logowania i stop; zanim ruszy cokolwiek z bazą
# Dodatkowy CSS: czcionka bezszeryfowa, zaokrąglone rogi i subtelne cienie
CSS_DODATKOWY = """
<style>
/* Czcionka systemowa bezszeryfowa; ikon Streamlita (Material) nie ruszamy */
.stApp, .stApp p, .stApp label, .stApp input, .stApp textarea,
.stApp button, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stSidebar"] * {
    font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
[data-testid="stIconMaterial"], .material-symbols-rounded {
    font-family: "Material Symbols Rounded" !important;
}

/* Nagłówek systemowy przezroczysty, treść przy samej górze */
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewBlockContainer"],
.stMain .block-container,
.block-container { padding-top: 0 !important; }

/* Telefon: nagłówek z logo ma tło, a treść zaczyna się pod nim (inaczej logo nachodzi na pierwszy element) */
@media (max-width: 768px) {
    [data-testid="stHeader"] {
        background: var(--e-naglowek) !important;
        -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px);
    }
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"],
    .stMain .block-container,
    .block-container { padding-top: 6.9rem !important; }   /* tyle, ile zajmuje nagłówek z logo (z paskiem stanu iPhone'a) */
    /* iPhone przybliża stronę po stuknięciu w pole z czcionką mniejszą niż 16 px */
    input, textarea, select { font-size: 16px !important; }
}

/* Bloki ze samym CSS-em i puste miejsca (st.empty) nie mają wysokości, ale każdy dokładał 1 rem odstępu na górze strony
   (razem ok. 100 px pustki nad nagłówkiem). Chowamy je całkiem; style działają dalej. */
[data-testid="stMainBlockContainer"] [data-testid="stElementContainer"]:has([data-testid="stMarkdownContainer"] > style:only-child),
[data-testid="stMainBlockContainer"] [data-testid="stElementContainer"]:has(> [data-testid="stEmpty"]) { display: none !important; }

/* Bez przybliżania podwójnym stuknięciem (zwykłe stuknięcia i przewijanie działają jak zawsze) */
html, body, .stApp { touch-action: manipulation; }

/* Logo w menu bocznym */
[data-testid="stLogo"],
[data-testid="stSidebarLogo"] { height: 2.2rem !important; max-width: 100% !important; }
[data-testid="stSidebarHeader"] { height: 5rem !important; }

/* Menu boczne */
[data-testid="stSidebar"] { border-right: 1px solid var(--e-obram); }
/* Mniejsze odstępy pod listą stron, żeby „Ustawienia” były bliżej (mniej przewijania na telefonie) */
[data-testid="stSidebarNav"], [data-testid="stSidebarNavItems"] { padding-bottom: 0 !important; margin-bottom: 0 !important; }
[data-testid="stSidebarNavSeparator"] { margin: 0.2rem 0 !important; }
[data-testid="stSidebarUserContent"] { padding-top: 0.4rem !important; }
[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
[data-testid="stSidebar"] hr { margin: 0.3rem 0 !important; }

/* Strona Treningi: kafelki-przyciski (cały kafelek jest przyciskiem) z napisem i strzałką; każdy w swoim kolorze.
   Kolor kafelka to zmienna --kafel; przycisk powrotu po wybraniu ma kolor wybranego trybu. */
.st-key-btn_start, .st-key-tryby_powrot_start { --kafel: var(--e-przerwa); --mocnosc: 26%; }
.st-key-btn_wlasny, .st-key-tryby_powrot_wlasny { --kafel: var(--e-serie); --mocnosc: 14%; }
.st-key-btn_presety, .st-key-tryby_powrot_presety { --kafel: var(--e-typ_plyo); --mocnosc: 14%; }
.st-key-btn_asystent, .st-key-tryby_powrot_asystent { --kafel: var(--e-zielony); --mocnosc: 14%; }
.st-key-tryby_wiersz button, [class*="st-key-tryby_powrot_"] button {
    position: relative; justify-content: flex-start !important; min-height: 4.2rem; width: 100% !important;
    padding: 0 68px 0 20px !important; border-radius: 16px !important; white-space: nowrap;
    background: linear-gradient(100deg, color-mix(in srgb, var(--kafel) var(--mocnosc), var(--e-karta)) 0%, var(--e-karta) 75%) !important;
    border: 2px solid color-mix(in srgb, var(--kafel) 50%, var(--e-obram2)) !important;
    box-shadow: 0 4px 14px var(--e-cien_s); color: var(--e-tekst) !important;
}
.st-key-tryby_wiersz button p, [class*="st-key-tryby_powrot_"] button p {
    font-size: 1.1rem !important; font-weight: 700 !important; text-align: left; margin: 0; white-space: nowrap;
}
/* Pigułka ze strzałką (strzałka to maska SVG, więc leży dokładnie na środku pigułki) */
.st-key-tryby_wiersz button::after, [class*="st-key-tryby_powrot_"] button::after {
    content: ""; position: absolute; right: 14px; top: 50%; width: 38px; height: 38px; margin-top: -19px;
    border-radius: 11px; background: var(--kafel);
}
.st-key-tryby_wiersz button::before, [class*="st-key-tryby_powrot_"] button::before {
    content: ""; position: absolute; right: 14px; top: 50%; width: 38px; height: 38px; margin-top: -19px; z-index: 1;
    background: var(--e-przycisk_tekst);
    -webkit-mask: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M6 6l6 6-6 6M12 6l6 6-6 6' fill='none' stroke='black' stroke-width='2.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / 22px 22px no-repeat; mask: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M6 6l6 6-6 6M12 6l6 6-6 6' fill='none' stroke='black' stroke-width='2.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / 22px 22px no-repeat;
}
/* Przycisk powrotu: niższy, pigułka ze strzałką w lewo po lewej stronie */
[class*="st-key-tryby_powrot_"] button { min-height: 3.2rem; padding: 0 20px 0 64px !important; }
[class*="st-key-tryby_powrot_"] button::after, [class*="st-key-tryby_powrot_"] button::before {
    right: auto; left: 12px; width: 34px; height: 34px; margin-top: -17px;
}
[class*="st-key-tryby_powrot_"] button::before {
    -webkit-mask: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M15 6l-6 6 6 6' fill='none' stroke='black' stroke-width='2.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / 22px 22px no-repeat; mask: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M15 6l-6 6 6 6' fill='none' stroke='black' stroke-width='2.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / 22px 22px no-repeat;
}

/* Kafelki metryk i formularze */
[data-testid="stMetric"], [data-testid="stForm"] {
    background: var(--e-karta);
    border: 2px solid var(--e-obram2);
    border-radius: 16px;
    box-shadow: 0 4px 14px var(--e-cien_s);
}
[data-testid="stMetric"] { padding: 16px 18px; }
[data-testid="stExpander"] {
    border: 2px solid var(--e-obram2) !important;
    border-radius: 14px !important;
    overflow: hidden;
    background: var(--e-karta);
}
[data-testid="stAlert"] { border-radius: 12px; }
/* Przycisk „Zmień plan tygodnia”: szkło (półprzezroczyste tło, gradientowa ramka w kolorach motywu, połysk u góry) */
.st-key-plan_edycja [data-testid="stExpander"] {
    border: 1.5px solid transparent !important;
    border-radius: 18px !important;
    background:
        linear-gradient(135deg, color-mix(in srgb, var(--e-tytul_glow2) 55%, transparent) 0%, transparent 45%, color-mix(in srgb, var(--e-tytul_glow3) 55%, transparent) 100%) padding-box,
        linear-gradient(var(--e-kafelek), var(--e-kafelek)) padding-box,
        linear-gradient(100deg, var(--e-g1), var(--e-g2) 55%, var(--e-g3)) border-box !important;
    box-shadow: inset 0 1px 0 color-mix(in srgb, white 22%, transparent), inset 0 -14px 24px color-mix(in srgb, var(--e-tytul_glow1) 35%, transparent),
                0 10px 30px color-mix(in srgb, var(--e-tytul_glow1) 70%, transparent) !important;
    transition: box-shadow .25s ease, transform .15s ease, filter .25s ease;
}
.st-key-plan_edycja [data-testid="stExpander"]:hover { filter: brightness(1.12) saturate(1.1); }
.st-key-plan_edycja [data-testid="stExpander"] summary {
    display: flex !important; align-items: center; justify-content: space-between;
    padding: 1.05rem 1.3rem !important; cursor: pointer;
}
.st-key-plan_edycja [data-testid="stExpander"] summary:active { transform: scale(0.99); }
.st-key-plan_edycja [data-testid="stExpander"] summary > span { display: flex; align-items: center; gap: 0.75rem; }
.st-key-plan_edycja [data-testid="stExpander"] summary p {
    font-family: 'Archivo', 'Helvetica Neue', Arial, sans-serif;
    font-weight: 800; font-stretch: 115%; font-size: 0.92rem; letter-spacing: 0.09em; text-transform: uppercase;
    margin: 0;
}
.st-key-plan_edycja [data-testid="stExpanderIcon"] {
    font-size: 1.5rem;
    background: linear-gradient(135deg, var(--e-g1), var(--e-g2), var(--e-g3));
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; color: transparent;
}
.st-key-plan_edycja [data-testid="stExpander"] summary::after {
    content: ""; width: 0.6rem; height: 0.6rem; margin-right: 0.3rem;
    border-right: 2.5px solid var(--e-g2); border-bottom: 2.5px solid var(--e-g2);
    transform: rotate(45deg) translateY(-2px); transition: transform .25s ease;
}
.st-key-plan_edycja [data-testid="stExpander"] details[open] > summary::after { transform: rotate(-135deg) translateY(-2px); }
.st-key-plan_edycja [data-testid="stExpanderDetails"] { padding: 0.4rem 0.9rem 1rem 0.9rem; }
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid var(--e-obram);
}
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 16px; }

/* Pola tekstowe */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div,
.stTextInput input, .stNumberInput input, .stTextArea textarea {
    border-radius: 12px !important;
    background: var(--e-pill) !important;
}

/* Przyciski */
.stButton > button, [data-testid="stFormSubmitButton"] > button {
    border-radius: 12px;
    border: 2px solid var(--e-obram2);
    transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease;
}
/* Przycisk główny (ciemny) ma ciemną ramkę, żeby nie było jasnego obrysu */
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"] {
    border-color: var(--e-przycisk);
    background-color: var(--e-przycisk);
    background-image: var(--e-przycisk-grad);
    color: var(--e-przycisk_tekst);
}
.stButton > button[kind="primary"] p, .stButton > button[data-testid="stBaseButton-primary"] p,
[data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"] p { color: var(--e-przycisk_tekst); }
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
    border-color: var(--e-obram_hover);
    transform: translateY(-1px);
    box-shadow: 0 6px 16px var(--e-cien_h);
}

/* Znak „?” z objaśnieniami: większy i z większym polem dotyku (kciuk na telefonie) */
[data-testid="stTooltipIcon"] svg { width: 1.45rem !important; height: 1.45rem !important; }
[data-testid="stTooltipIcon"] { color: var(--e-przyg) !important; }
[data-testid="stTooltipHoverTarget"] { padding: 10px !important; margin: -10px !important; }
/* Bez zaznaczania tekstu przy dłuższym dotknięciu (iPhone zaznaczał słowo obok znaku „?”); pola do wpisywania działają normalnie */
.stApp, .stApp * { -webkit-user-select: none; user-select: none; -webkit-touch-callout: none; }
.stApp input, .stApp textarea, .stApp [contenteditable="true"] { -webkit-user-select: text !important; user-select: text !important; }
/* Ikonka linku przy nagłówkach jest niepotrzebna */
[data-testid="stHeaderActionElements"] { display: none !important; }

/* Okienko z objaśnieniem nie może być szersze niż ekran telefonu (inaczej prawa część tekstu ucina się za krawędzią) */
[data-baseweb="popover"], [data-baseweb="popover"] > div, [data-testid="stTooltipContent"] {
    max-width: min(22rem, calc(100vw - 24px)) !important;
    box-sizing: border-box !important;
}
[data-testid="stTooltipContent"] { white-space: normal !important; overflow-wrap: anywhere !important; }

/* Dziennik ręczny: pola obok siebie także na telefonie; usuwanie uwag na czerwono */
.st-key-dz_wiersz [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 8px !important; }
.st-key-dz_wiersz [data-testid="stColumn"], .st-key-dz_wiersz [data-testid="column"] { min-width: 0 !important; flex: 1 1 0 !important; width: auto !important; }
[class*="st-key-uwaga_u_"] button { color: var(--e-kasuj); border-color: var(--e-kasuj_ramka); }

/* Poświata na kafelkach (kontenery z ramką), formularzach i panelach */
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stForm"],
[data-testid="stExpander"] {
    background: radial-gradient(ellipse at 50% 0%, var(--e-kafelek_glow) 0%, transparent 72%), var(--e-kafelek);
    box-shadow: 0 6px 18px var(--e-cien_m);
    border: 2px solid var(--e-obram2) !important;
}
/* Kafelki i bloki ćwiczeń wskazane po kluczu (najpewniejszy sposób w nowych wersjach Streamlita) */
[class*="st-key-kafelek_"], [class*="st-key-blok_cwiczenia_"] {
    background: radial-gradient(ellipse at 50% 0%, var(--e-kafelek_glow) 0%, transparent 72%), var(--e-kafelek) !important;
    border: 2px solid var(--e-obram2) !important;
    border-radius: 16px !important;
    box-shadow: 0 6px 18px var(--e-cien_m) !important;
}
/* Kontener w kontenerze nie ma własnej poświaty (żeby nie dublować) */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] {
    background: none !important;
    box-shadow: none !important;
    border: none !important;
}
</style>
"""
CSS_DZISIEJSZY_TRENING = """
<style>
@keyframes dzis-puls {
    0%   { box-shadow: 0 0 0 0 var(--e-puls); }
    70%  { box-shadow: 0 0 0 9px var(--e-puls0); }
    100% { box-shadow: 0 0 0 0 var(--e-puls0); }
}
a[data-testid="stSidebarNavLink"][href$="/dzis"],
[data-testid="stSidebarNav"] a[href$="/dzis"] {
    background-color: var(--e-przycisk) !important;
    background-image: var(--e-przycisk-grad) !important;
    border-radius: 12px !important;
    animation: dzis-puls 2.4s ease-out infinite;
}
a[data-testid="stSidebarNavLink"][href$="/dzis"] *,
[data-testid="stSidebarNav"] a[href$="/dzis"] * {
    color: var(--e-dzis_tekst) !important;
    font-weight: 600 !important;
}
@media (prefers-reduced-motion: reduce) {
    a[data-testid="stSidebarNavLink"][href$="/dzis"] { animation: none; }
}
</style>
"""

# Pozycja „Jutro” w menu: ten sam styl co „Na dziś”, ale w chłodnych kolorach (cyjan, niebieski, mięta), bez pulsowania
CSS_JUTRO = (CSS_DZISIEJSZY_TRENING.replace('"/dzis"', '"/jutro"').replace("animation: dzis-puls 2.4s ease-out infinite;", "")
             .replace("var(--e-przycisk-grad)", "linear-gradient(90deg, var(--e-jutro1), var(--e-jutro2) 55%, var(--e-jutro3))")
             .replace("var(--e-przycisk)", "var(--e-jutro2)").replace("var(--e-dzis_tekst)", "var(--e-jutro_tekst)"))

# Pozycja „Na dziś” w menu: ten sam neonowy kolor co „Dziś: …”, ale bez pulsowania
CSS_NA_DZIS = CSS_DZISIEJSZY_TRENING.replace('"/dzis"', '"/na-dzis"').replace("animation: dzis-puls 2.4s ease-out infinite;", "")


def rekomendacja_dnia():
    """Rekomendacje „na dziś” (rekomendacje.py) albo None, gdy wszystko w normie, brak danych albo dziś już był trening.
    Wynik: {'rek': ..., 'tytul': tekst do menu}. Start zostaje czysty: podpowiedź jest tylko pozycją w menu bocznym."""
    try:
        if trening_dzis_zapisany(date.today()):
            return None
        lista = lista_presetow()
        dzis_plan = plan_na_dzien()
        nazwa = sesja_treningowa.domyslny_preset(lista, dzis_plan["Typ"] if dzis_plan["Aktywny"] else "") if not lista.empty else None
        rek = rekomendacje_na_dzis(date.today(), nazwa)
    except Exception:
        return None
    if not rek["regeneracja"] and not rek["partie"]:
        return None
    tytul = "Rekomendacja na dziś"   # krótko, żeby mieściło się w pasku bocznym; szczegóły są na stronie
    return {"rek": rek, "tytul": tytul}


_rek_dnia = rekomendacja_dnia()

_plan_jutro = plan_na_dzien(date.today() + timedelta(days=1))

# Pozycja "Dziś: ..." w menu pulsuje tylko w dzień treningowy, dopóki trening nie jest zapisany
_pulsuj_dzis = plan_na_dzien()["Aktywny"] and not trening_zapisany()
st.markdown(CSS_DODATKOWY + css_szklo() + profil.CSS_PROFIL + (CSS_JUTRO if _plan_jutro["Aktywny"] else "") + (CSS_DZISIEJSZY_TRENING if _pulsuj_dzis else "") + (CSS_NA_DZIS if _rek_dnia else ""), unsafe_allow_html=True)

zastosuj_styl()
# Logo nad menu bocznym (plik logo.svg leży obok app.py)
st.logo(str(Path(__file__).parent / "logo.svg"), size="large")


def css_logo() -> str:
    """Plik logo.svg jest ciemny; w ciemnym motywie Streamlita odwracamy go na jasny.
    Motyw podaje st.context.theme.type (wybór w aplikacji lub menu ⋮); gdy go brak, decyduje ustawienie systemu."""
    cel = 'img[data-testid*="Logo" i], img[class*="Logo" i]'
    odwroc = f"{cel}{{filter:invert(1) brightness(1.08);}}"
    try:
        motyw = st.context.theme.type
    except Exception:
        motyw = None
    if motyw == "dark":
        return f"<style>{odwroc}</style>"
    if motyw == "light":
        return ""
    return f"<style>@media (prefers-color-scheme: dark){{{odwroc}}}</style>"


_css_logo = css_logo()
if _css_logo:
    st.markdown(_css_logo, unsafe_allow_html=True)


def css_pol() -> str:
    """Pola do wpisywania (także w oknach dialogowych i w stanie „aktywne”) w kolorach aktywnego motywu.
    Na telefonie aktywne pole w oknie dialogowym zostawało jasne w ciemnym motywie, więc kolory podajemy tu wprost
    (według st.context.theme.type), zamiast polegać na light-dark(). Gdy motywu nie znamy, zostaje zwykły mechanizm."""
    try:
        motyw = st.context.theme.type
    except Exception:
        motyw = None
    if motyw not in ("light", "dark"):
        return ""
    i = 1 if motyw == "dark" else 0
    tlo, tekst = PALETA["pill"][i], PALETA["tekst"][i]
    pola = ('[data-baseweb="input"]', '[data-baseweb="base-input"]', '[data-baseweb="textarea"]',
            '[data-baseweb="select"] > div', '.stTextInput input', '.stNumberInput input', '.stTextArea textarea',
            '.stDateInput input', '.stTimeInput input', '[role="dialog"] input', '[role="dialog"] textarea')
    stany = ('', ':hover', ':focus', ':focus-within', ':active')
    selektor = ",".join(f"{p}{s}" for p in pola for s in stany)
    return (f"<style>{selektor}{{background:{tlo} !important;background-color:{tlo} !important;color:{tekst} !important;"
            f"-webkit-text-fill-color:{tekst} !important;caret-color:{tekst};}}"
            f"input:-webkit-autofill,textarea:-webkit-autofill{{-webkit-box-shadow:0 0 0 1000px {tlo} inset !important;"
            f"-webkit-text-fill-color:{tekst} !important;}}</style>")


_css_pol = css_pol()
if _css_pol:
    st.markdown(_css_pol, unsafe_allow_html=True)

# Blokada przybliżania szczypaniem (iPhone ignoruje user-scalable=no, więc blokujemy gesty skryptem).
# Skrypt działa w ukrytej ramce i zakłada zmiany na stronie nadrzędnej. Wyłączenie przybliżania utrudnia obsługę
# osobom słabowidzącym; jeśli aplikacja trafi do innych użytkowników, warto to usunąć albo zostawić do wyboru.
with st.sidebar:
    components.html(
        """<script>
        const d = window.parent.document;
        if (!d.__bezZoomu) {
            d.__bezZoomu = true;
        // Ikona na ekranie początkowym iPhone'a (plik leży w folderze static, serwowanym przez Streamlit)
        d.querySelectorAll('link[rel~="apple-touch-icon"]').forEach(function (l) { l.remove(); });
        const ik = d.createElement('link');
        ik.rel = 'apple-touch-icon'; ik.sizes = '180x180'; ik.href = '/app/static/ikona-180.png';
        d.head.appendChild(ik);
        if (!d.querySelector('meta[name="apple-mobile-web-app-title"]')) {
            const t = d.createElement('meta'); t.name = 'apple-mobile-web-app-title'; t.content = 'OVRLD'; d.head.appendChild(t);
        }
            ['gesturestart', 'gesturechange', 'gestureend'].forEach(function (e) {
                d.addEventListener(e, function (ev) { ev.preventDefault(); }, {passive: false});
            });
            d.addEventListener('touchmove', function (ev) {
                if (ev.touches.length > 1) { ev.preventDefault(); }
            }, {passive: false});
            const m = d.querySelector('meta[name=viewport]');
            if (m) { m.setAttribute('content', 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no'); }
        }
        // Listy wyboru: gdy jest już coś wybrane, tylko klikamy (bez pisania i bez klawiatury na telefonie);
        // pisanie (szukanie) działa tylko w pustym polu. Stan sprawdzamy przy wejściu w pole.
        if (!d.__listyBezPisania) {
            d.__listyBezPisania = true;
            const st = d.createElement('style');
            st.textContent = '[data-testid="stSelectbox"] input[data-wybrane="1"] {caret-color: transparent; cursor: pointer;}';
            d.head.appendChild(st);
            const sel = '[data-testid="stSelectbox"] input[role="combobox"]';
            const ocen = function (ev) {
                const i = ev.target;
                if (!i || !i.matches || !i.matches(sel)) { return; }
                const wybrane = i.value !== '';
                if (wybrane) { i.setAttribute('data-wybrane', '1'); i.setAttribute('inputmode', 'none'); }
                else { i.removeAttribute('data-wybrane'); i.setAttribute('inputmode', 'text'); }
            };
            d.addEventListener('focusin', ocen, true);
            d.addEventListener('pointerdown', ocen, true);
            d.addEventListener('beforeinput', function (ev) {
                const i = ev.target;
                if (i && i.matches && i.matches(sel) && i.getAttribute('data-wybrane') === '1') { ev.preventDefault(); }
            }, true);
        }
        </script>""",
        height=0,
    )

# Motyw aplikacji. Streamlit zapamiętuje wybór motywu (System / Light / Dark) w przeglądarce pod kluczem
# "stActiveTheme-<ścieżka strony>-v2". Przełącznik w Ustawieniach zapisuje wybór tam i odświeża stronę, więc zmienia
# wygląd całej aplikacji (także pól, list i okien Streamlita), tak samo jak menu ⋮ → Settings.
MOTYWY_ZAPIS = {"Jasny": "Light", "Ciemny": "Dark", "Auto": "System"}   # kolejność = układ przycisków: Jasny i Ciemny obok siebie, duże Auto niżej


def wczytaj_motyw() -> str:
    try:
        w = sesja_treningowa.wczytaj_ustawienie("motyw", "Auto")
    except Exception:
        return "Auto"
    return w if w in MOTYWY_ZAPIS else "Auto"


def _zmien_motyw() -> None:
    wybor = st.session_state.get("motyw_wybor")
    if wybor not in MOTYWY_ZAPIS:      # ponowne stuknięcie w wybraną opcję zdejmuje zaznaczenie, więc je przywracamy
        st.session_state["motyw_wybor"] = wczytaj_motyw()
        return
    sesja_treningowa.zapisz_ustawienie("motyw", wybor)
    st.session_state["motyw_zastosuj"] = wybor


def skrypt_motywu(wybor: str) -> str:
    """Skrypt (w ukrytej ramce): zapisuje wybór motywu dla wszystkich stron aplikacji i odświeża stronę."""
    wartosc = json.dumps(MOTYWY_ZAPIS[wybor])
    return f"""<script>
    (function () {{
        try {{
            const w = window.parent;
            const wartosc = JSON.stringify({wartosc});
            const sciezki = new Set([w.location.pathname, '/']);
            w.document.querySelectorAll('a[href]').forEach(function (a) {{
                try {{
                    const u = new URL(a.href, w.location.href);
                    if (u.origin === w.location.origin) {{ sciezki.add(u.pathname); }}
                }} catch (e) {{}}
            }});
            sciezki.forEach(function (p) {{ w.localStorage.setItem('stActiveTheme-' + p + '-v2', wartosc); }});
            w.location.reload();
        }} catch (e) {{}}
    }})();
    </script>"""


# Tryb bez zegarka: przełącznik w Ustawieniach. Wyłączony Garmin = brak synchronizacji, a na Starcie ręczny wpis snu, wagi i energii.
def garmin_wlaczony() -> bool:
    try:
        if baza.TRYB_GOSCIA or not uzytkownik.czy_wlasciciel():   # inni niż właściciel: ręczny wpis dnia, bez jego Garmina
            return False
        return sesja_treningowa.wczytaj_ustawienie("garmin", "1") != "0"
    except Exception:
        return True


def _zapisz_garmin() -> None:
    sesja_treningowa.zapisz_ustawienie("garmin", "1" if st.session_state.get("garmin_wl") else "0")


def _zapisz_dziennik() -> None:
    s = st.session_state
    dziennik.zapisz(date.today(), s.get("dz_sen"), s.get("dz_waga"), s.get("dz_energia"))
    st.toast("Zapisane.")


def _status_energii(e: int | None) -> tuple[str, str]:
    if e is None:
        return KOLOR_PRZYGASZONY, "Wpisz energię"
    return (ZIELONY if e >= 4 else ZOLTY if e == 3 else POMARANCZOWY), dziennik.ENERGIA[e]


def kafelki_reczne() -> list[str]:
    """Kafelki dnia z ręcznego dziennika: sen, waga, energia."""
    dz = dziennik.dzien()
    hist = dziennik.wczytaj()
    sen = dz.get("Sen_godz")
    sen_min = sen * 60 if sen is not None else None
    wagi = hist["Waga"].dropna() if not hist.empty else None
    waga = dz.get("Waga")
    podpis_wagi = ""
    if wagi is not None and len(wagi):
        if waga is None:
            waga = float(wagi.iloc[-1])
            podpis_wagi = f"ostatni wpis: {wagi.index[-1]:%d.%m}"
        elif len(wagi) >= 2:
            roznica = float(wagi.iloc[-1] - wagi.iloc[-2])
            podpis_wagi = f"{roznica:+.1f} kg od poprzedniego".replace(".", ",")
    seria_wagi = wagi.tail(14).tolist() if wagi is not None else []
    energia = dz.get("Energia")
    kolor_en, status_en = _status_energii(energia)
    return [
        karta_pierscien("Sen", sen_min, 480, kolor_czasu_snu(sen_min), status_czasu_snu(sen_min), "cel: 8h",
                        tekst_srodka=format_czasu(sen_min) if sen_min is not None else None),
        karta_wartosc("Waga", waga, "kg", NIEBIESKI, podpis_wagi, seria_wagi if len(seria_wagi) >= 2 else None, miejsca=1),
        karta_pierscien("Energia", energia, 5, kolor_en, status_en, "", tekst_srodka=f"{energia}/5" if energia is not None else None),
    ]


def formularz_dzienny() -> None:
    """Ręczny wpis dnia (sen, waga, energia) dla osób bez zegarka; pola wypełnione dzisiejszymi wartościami."""
    dz = dziennik.dzien()
    with st.form("form_dziennik"):
        with st.container(key="dz_wiersz"):
            k1, k2 = st.columns(2)
            k1.number_input("Sen (godz.)", min_value=0.0, max_value=16.0, value=dz.get("Sen_godz"), step=0.5, format="%.1f", key="dz_sen")
            k2.number_input("Waga (kg)", min_value=30.0, max_value=300.0, value=dz.get("Waga"), step=0.1, format="%.1f", key="dz_waga")
        sesja_treningowa.rzad_w_jednej_linii("dz_energia")
        st.segmented_control("Energia", [1, 2, 3, 4, 5], default=dz.get("Energia"), key="dz_energia",
                             help="1 = bardzo niska, 5 = świetna.")
        st.form_submit_button("Zapisz", on_click=_zapisz_dziennik, use_container_width=True)


# Uwagi do aplikacji (przycisk w pasku bocznym): zapis w bazie i powiadomienie na telefon
def _wyslij_uwage() -> None:
    tekst = (st.session_state.get("uwaga_tekst") or "").strip()
    if not tekst:
        st.toast("Najpierw wpisz uwagę.")
        return
    _, wyslano = uwagi.zapisz(tekst, st.session_state.get("strona_tytul", ""))
    st.session_state["uwaga_tekst"] = ""
    st.toast("Uwaga zapisana i wysłana na telefon." if wyslano else "Uwaga zapisana (powiadomienie nie poszło).")


# Od ilu dni z wpisaną wagą pokazujemy wykres wagi
MIN_DNI_WAGI = 3

# Przygotowanie bazy; zwraca komunikat tylko, gdy plik musiał zostać odtworzony
komunikat_bazy = baza.przygotuj_baze()
sesja_treningowa.kopia_dzienna()   # raz dziennie kopia bazy w folderze kopie/ (przy pierwszym uruchomieniu danego dnia)
# Ćwiczenia czytamy z bazy, a nie z listy w kodzie. Rodzaj treningu to po prostu nazwa presetu.
BAZA_CWICZEN = baza.lista_cwiczen()

# ---------------------------------------------------------------
# FORMULARZ TRENINGU: dodawanie ćwiczeń i zapis
# ---------------------------------------------------------------
# Każde pole ćwiczenia ma klucz z przedrostkiem i numerem, np. cw_0, ci_0, se_0...
PREFIKSY_POL = ("cw_", "jd_", "ci_", "se_", "po_", "ko_")

# Na starcie pokazujemy jeden blok ćwiczenia
st.session_state.setdefault("liczba_cwiczen", 1)


def dodaj_cwiczenie() -> None:
    """Przycisk ➕: dokłada jeszcze jeden blok ćwiczenia."""
    st.session_state["liczba_cwiczen"] += 1


def usun_ostatnie_cwiczenie() -> None:
    """Przycisk ➖: usuwa ostatni blok (zawsze zostaje co najmniej jeden)."""
    ile = st.session_state["liczba_cwiczen"]
    if ile > 1:
        nr = ile - 1
        for klucz in list(st.session_state.keys()):
            if any(klucz == f"{p}{nr}" or klucz.startswith(f"{p}{nr}_") for p in PREFIKSY_POL):
                del st.session_state[klucz]
        st.session_state["liczba_cwiczen"] = ile - 1


def jednostka_bloku(i: int) -> str:
    """Jednostka ćwiczenia w bloku i: wybrana ręcznie albo automatyczna (rower stacjonarny: minuty, plank: sekundy)."""
    s = st.session_state
    return sesja_treningowa.jednostka_formularza(s.get(f"cw_{i}"), s.get(f"jd_{i}"))


def zapisz_z_formularza() -> None:
    """Przycisk Zapisz: zbiera wpisane dane, zapisuje trening i czyści ćwiczenia."""
    s = st.session_state
    cwiczenia = []
    for i in range(s["liczba_cwiczen"]):
        if s.get(f"cw_{i}") is None:
            s["blad_zapisu"] = f"Wybierz ćwiczenie w bloku numer {i + 1} (albo usuń ten blok przyciskiem ➖)."
            return  # nic nie zapisujemy
        u = jednostka_bloku(i)
        cwiczenia.append(
            {
                "cwiczenie": s[f"cw_{i}"],
                "ciezar": float(s.get(f"ci_{i}_{u}") or 0.0),   # dla minut pola kg nie ma
                "serie": int(s[f"se_{i}_{u}"]),
                "powtorzenia": int(s[f"po_{i}_{u}"]),
                "jednostka": u,
                "komentarz": s.get(f"ko_{i}", ""),
            }
        )

    sesja_treningowa.przygotuj_tabele()   # dokłada kolumnę z jednostką, gdyby jej jeszcze nie było
    baza.zapisz_sesje(
        s["data_treningu"].isoformat(),
        "" if s["typ_treningu"] == sesja_treningowa.BRAK_RODZAJU else s["typ_treningu"],
        s["waga_ciala"],
        s.get("komentarz_treningu", ""),
        cwiczenia,
    )

    # Po zapisie czyścimy ćwiczenia i komentarz; data, rodzaj i waga zostają
    for klucz in list(s.keys()):
        if klucz.startswith(PREFIKSY_POL):
            del s[klucz]
    s["liczba_cwiczen"] = 1
    s["komentarz_treningu"] = ""
    s["komunikat_zapisu"] = f"Trening zapisany! Liczba ćwiczeń: {len(cwiczenia)}."

# ---------------------------------------------------------------
# NAGŁÓWEK
# ---------------------------------------------------------------

dzisiaj = date.today().isoformat()  # format RRRR-MM-DD

# Synchronizację z Garminem robimy RAZ, przed zakładkami, bo dane
# są potrzebne zarówno na Pulpicie, jak i w formularzu treningu
def pobierz_dane_garmin() -> tuple[dict | None, tuple[str, str] | None]:
    """Zwraca (dane, błąd). Wywoływana tylko na stronie Start, więc reszta aplikacji nie czeka."""
    try:
        return synchronizuj_garmin(dzisiaj), None
    except ValueError as blad:
        return None, ("error", f"Błąd konfiguracji: {blad}")
    except GarminConnectAuthenticationError:
        return None, ("error", "Błąd logowania: sprawdź email i hasło w pliku .env.")
    except GarminConnectTooManyRequestsError:
        return None, ("warning", "Garmin ogranicza liczbę zapytań. Odczekaj kilka minut i kliknij Odśwież.")
    except GarminConnectConnectionError as blad:
        return None, ("error", f"Błąd połączenia z Garmin Connect: {blad}")
    except Exception as blad:
        return None, ("error", f"Nieoczekiwany błąd: {blad}")

# ---------------------------------------------------------------
# NAWIGACJA: poziomy pasek zakładek na górze strony
# ---------------------------------------------------------------

# ---------------------------------------------------------------
# ZAKŁADKA 1: START (PULPIT)
# ---------------------------------------------------------------
def _kiedy(data_iso: str) -> str:
    """„z dzisiaj”, „z wczoraj” albo „z 17.10” (do komunikatu o danych zapasowych)."""
    d = date.fromisoformat(data_iso)
    roznica = (date.today() - d).days
    return "z dzisiaj" if roznica == 0 else "z wczoraj" if roznica == 1 else f"z {d.strftime('%d.%m')}"


def strona_start():
    st.markdown(
        naglowek_strony("Start", f"Dziś: {date.today().strftime('%d.%m.%Y')}"),
        unsafe_allow_html=True,
    )
    # Zwykły napis zamiast czarnego spinnera; znika, gdy dane są gotowe
    reczny = not garmin_wlaczony()
    zapasowe = None   # ostatnie dane z bazy, gdy Garmin chwilowo nie odpowiada (interfejs zostaje cały)
    if reczny:
        dane_garmin, blad_garmin = None, None
    else:
        info = st.empty()
        info.caption("⏳ Synchronizacja z Garminem…")
        dane_garmin, blad_garmin = pobierz_dane_garmin()
        info.empty()
        if blad_garmin is not None:
            zapasowe = ostatnie_zapisane_dane()
            if zapasowe:
                dane_garmin = zapasowe["dane"]
    try:
        powitanie = profil.powitanie()      # „Dzień dobry, <imię>” z Profilu; bez imienia zostaje samo pytanie
    except Exception:   # noqa: BLE001 (powitanie nie może zablokować Startu)
        powitanie = None
    st.subheader(powitanie or "Jak się dziś masz?")

        # Pole na odpis o samopoczuciu; Enter wysyła formularz
    with st.form("form_samopoczucie", clear_on_submit=True):
        kol_pole, kol_przycisk = st.columns([5, 1])
        wpis = kol_pole.text_input(
            "Samopoczucie",
            placeholder="Jak się dziś masz?" if powitanie else "Jak się czujesz…",
            label_visibility="collapsed",
        )
        wyslano = kol_przycisk.form_submit_button("Zapisz", use_container_width=True)

    if wyslano:
        if wpis.strip():
            baza.zapisz_samopoczucie(wpis.strip())
            st.success("Zapisane.")
        else:
            st.warning("Najpierw wpisz kilka słów.")

    # Informacja, jeśli baza musiała zostać odtworzona
    if komunikat_bazy:
        st.warning(komunikat_bazy)

    if reczny:
        st.subheader("Dziś w liczbach")
        formularz_dzienny()
        st.markdown(siatka_kart(kafelki_reczne() + [karta_tydzien(podsumowanie_tygodnia())]), unsafe_allow_html=True)

    # Błędy Garmina pokazujemy tutaj
    if blad_garmin is not None and zapasowe:
        st.warning(f"Garmin chwilowo niedostępny. Pokazuję ostatnie zapisane dane ({_kiedy(zapasowe['data'])}).")
        with st.expander("Szczegóły błędu"):
            st.write(blad_garmin[1])
    elif blad_garmin is not None:
        if blad_garmin[0] == "warning":
            st.warning(blad_garmin[1])
        else:
            st.error(blad_garmin[1])

    # Cztery karty z pierścieniami i wartościami: wynik snu, czas snu, RHR i HRV
    if dane_garmin is not None:
        wynik_snu = dane_garmin["wynik_snu"]
        czas_sekundy = dane_garmin["czas_snu"]
        czas_snu_min = czas_sekundy / 60 if czas_sekundy is not None else None
        rhr = dane_garmin["rhr"]
        hrv = dane_garmin["hrv"]

        # Historia z bazy: normę liczymy z całej historii, na wykresie pokazujemy 14 ostatnich dni
        historia = baza.wczytaj_dane_garmin_do_wykresow()
        pasmo_rhr = pasmo_osobiste(historia["RHR"])
        pasmo_hrv = pasmo_osobiste(historia["HRV"])
        seria_rhr = historia["RHR"].dropna().tail(14).tolist()
        seria_hrv = historia["HRV"].dropna().tail(14).tolist()
        kolor_rhr, status_rhr = ocena_wzgledem_pasma(rhr, pasmo_rhr, wyzsze_lepiej=False)
        kolor_hrv, status_hrv = ocena_wzgledem_pasma(hrv, pasmo_hrv, wyzsze_lepiej=True)

        # Gotowość do treningu: średnia RHR z bazy (bez dzisiejszego dnia)
        rhr_hist = historia["RHR"].dropna()
        rhr_hist = rhr_hist[rhr_hist.index.date != date.today()]
        srednia_rhr = float(rhr_hist.mean()) if len(rhr_hist) >= 3 else None
        gotowosc = oblicz_gotowosc(czas_snu_min, rhr, srednia_rhr)
        procent = gotowosc["procent"]

        # Dodatkowe dane z Garmina: kroki, kalorie, stres (z .get, bo stary cache mógł ich nie mieć)
        kroki = dane_garmin.get("kroki")
        rozszerzone = baza.wczytaj_garmin_rozszerzone(14)

        # Karty w jednej siatce: jednakowe odstępy w poziomie i w pionie
        st.markdown(
            siatka_kart([
                # rząd 1
                karta_pierscien("Wynik snu", wynik_snu, 100, kolor_snu(wynik_snu), status_snu(wynik_snu)),
                karta_pierscien(
                    "Czas snu", czas_snu_min, 480,
                    kolor_czasu_snu(czas_snu_min), status_czasu_snu(czas_snu_min), "cel: 8h",
                    tekst_srodka=format_czasu(czas_snu_min) if czas_snu_min is not None else None,
                ),
                karta_wartosc("Tętno spoczynkowe", rhr, "bpm", kolor_rhr, status_rhr, seria_rhr, pasmo_rhr),
                karta_wartosc("HRV", hrv, "ms", kolor_hrv, status_hrv, seria_hrv, pasmo_hrv),
                # rząd 2
                karta_pierscien(
                    "Gotowość do treningu", procent, 100, gotowosc["kolor"],
                    gotowosc["status"], gotowosc["podpis"],
                    tekst_srodka=f"{procent}%" if procent is not None else None,
                ),
                karta_kroki(kroki, dane_garmin.get("cel_krokow")),
                karta_kalorie(dane_garmin.get("kcal_aktywne"), dane_garmin.get("kcal_spoczynkowe")),
                karta_stres(dane_garmin.get("stres"), rozszerzone["Stres"], date.today()),                # rząd 3: dwie szerokie karty
                karta_sen_fazy(rozszerzone, date.today()),
                karta_tydzien(podsumowanie_tygodnia()),
            ]),
            unsafe_allow_html=True,
        )
# ---------------------------------------------------------------
# ZAKŁADKA 2: REGENERACJA (wszystkie wykresy)
# ---------------------------------------------------------------

def _naglowek_z_pytajnikiem(tytul: str, opis: str) -> None:
    """Nagłówek strony; objaśnienie jest pod znakiem „?” zamiast stale widocznego szarego tekstu."""
    st.markdown(naglowek_strony(tytul), unsafe_allow_html=True)
    sesja_treningowa.pytajnik(opis, w_prawo=False)


def strona_regeneracja():
    _naglowek_z_pytajnikiem("Regeneracja", "Trendy snu, tętna, HRV i wagi.")
    regeneracja.widok_regeneracji(reczny=not garmin_wlaczony())

# ---------------------------------------------------------------
# WIDOK: WŁASNY TRENING (formularz z bazą ćwiczeń)
# ---------------------------------------------------------------
def widok_wlasny_trening():
    # Prowadzony trening od zera (bez presetu): ćwiczenia dodajesz w trakcie, nazwę możesz nadać na końcu
    st.button("Zacznij pusty trening (bez presetu)", type="primary", use_container_width=True, key="start_pusty_btn",
              on_click=sesja_treningowa.rozpocznij_pusty,
              help="Prowadzony trening bez rozpiski: ćwiczenia dodajesz w trakcie, a nazwę (preset) możesz nadać na końcu.")
    st.subheader("Dodaj trening po fakcie")

    # Komunikaty po kliknięciu przycisku Zapisz
    if "komunikat_zapisu" in st.session_state:
        st.success(st.session_state.pop("komunikat_zapisu"))
    if "blad_zapisu" in st.session_state:
        st.error(st.session_state.pop("blad_zapisu"))

    # Preset (zarazem nazwa treningu), pod nim data i waga ciała
    wczytaj_presety_startowe()
    opcje_presetow = [sesja_treningowa.BRAK_RODZAJU] + lista_presetow()["Nazwa"].tolist()
    st.selectbox("Preset", opcje_presetow, key="typ_treningu",
                 help="Którą rozpiskę trenowałeś. Bez presetu trening zapisze się bez nazwy.")
    kol_data, kol_waga = st.columns(2)
    kol_data.date_input("Data treningu", value=date.today(), key="data_treningu", format="DD.MM.YYYY")
    kol_waga.number_input(
        "Waga ciała (kg)", min_value=30.0, max_value=200.0, value=88.0,
        step=0.1, format="%.1f", key="waga_ciala",
    )

    # Pola ćwiczenia (obciążenie, serie, wartość) w jednym rzędzie także na telefonie
    st.markdown(
        "<style>[class*='st-key-blok_cwiczenia_'] [data-testid='stHorizontalBlock']{flex-wrap:nowrap !important;gap:8px !important;}"
        "[class*='st-key-blok_cwiczenia_'] [data-testid='stColumn'],[class*='st-key-blok_cwiczenia_'] [data-testid='column']"
        "{min-width:0 !important;flex:1 1 0 !important;width:auto !important;}</style>",
        unsafe_allow_html=True,
    )
    # Jeden blok na każde ćwiczenie; liczba bloków rośnie po kliknięciu ➕
    for i in range(st.session_state["liczba_cwiczen"]):
        with st.container(border=True, key=f"blok_cwiczenia_{i}"):
            st.markdown(f"**Ćwiczenie {i + 1}**")
            # index=None: lista startuje pusta, żeby przypadkiem nie zapisać pierwszego z listy
            st.selectbox(
                "Ćwiczenie", BAZA_CWICZEN, index=None,
                placeholder="Wybierz lub zacznij pisać nazwę...", key=f"cw_{i}",
            )
            st.selectbox(
                "Jednostka (w czym liczysz)", list(sesja_treningowa.JEDNOSTKI_WYBOR), key=f"jd_{i}",
                help="Automatycznie: jak ostatnio zapisywałeś to ćwiczenie (rower i bieganie: minuty, plank: sekundy), "
                     "a gdy robisz je pierwszy raz: powtórzenia.",
            )
            u = jednostka_bloku(i)
            ciezar0, serie0, wartosc0 = sesja_treningowa.domyslne_formularza(u)
            # Klucze pól zawierają jednostkę, więc po zmianie jednostki pola dostają wartości startowe dla niej
            if u == "min":    # cardio w minutach: bez obciążenia
                kol_serie, kol_powt = st.columns(2)
            else:
                kol_ciezar, kol_serie, kol_powt = st.columns(3)
                kol_ciezar.number_input(
                    "Ciężar (kg)" if sesja_treningowa.jednostka_powtorzen(u) else "Ciężar (kg, opcj.)",
                    min_value=0.0, max_value=500.0, value=ciezar0, step=2.5, format="%.1f", key=f"ci_{i}_{u}",
                )
            kol_serie.number_input("Serie", min_value=1, max_value=20, value=serie0, step=1, key=f"se_{i}_{u}")
            kol_powt.number_input(
                sesja_treningowa._etykieta_wartosci(u), min_value=1, max_value=10000, value=wartosc0, step=1, key=f"po_{i}_{u}",
            )
            st.text_input(
                "Komentarz do ćwiczenia",
                placeholder="np. RPE 8, ostatnia seria ciężko",
                key=f"ko_{i}",
            )

    # Przyciski pod ćwiczeniami: dodaj / usuń ostatnie
    kol_plus, kol_minus = st.columns(2)
    kol_plus.button("➕ Dodaj ćwiczenie", on_click=dodaj_cwiczenie, use_container_width=True)
    kol_minus.button(
        "➖ Usuń ostatnie ćwiczenie", on_click=usun_ostatnie_cwiczenie,
        use_container_width=True, disabled=st.session_state["liczba_cwiczen"] <= 1,
    )

    # Komentarz do całego treningu i zapis
    st.text_area(
        "Komentarz do całego treningu",
        placeholder="Samopoczucie, ogólny RPE, uwagi...",
        height=100, key="komentarz_treningu",
    )
    st.button("Zapisz trening", type="primary", on_click=zapisz_z_formularza, use_container_width=True)

# ---------------------------------------------------------------
# ZAKŁADKA: HISTORIA
# ---------------------------------------------------------------

def strona_historia():
    st.markdown(naglowek_strony("Historia"), unsafe_allow_html=True)
    sesja_treningowa.widok_historii()

    wpisy = baza.wczytaj_ostatnie_samopoczucie(30)
    with st.expander(f"Samopoczucie: zapisane wpisy ({len(wpisy)})"):
        if wpisy.empty:
            st.caption("Brak wpisów.")
        else:
            for _, wiersz in wpisy.iterrows():
                st.markdown(f"**{wiersz['Zapisano'][:16]}**: {wiersz['Tekst']}")
                if wiersz["Odpowiedz"]:
                    st.caption(f"Odpowiedź: {wiersz['Odpowiedz']}")
            if st.button("Usuń wszystkie wpisy", key="hist_sam_usun", use_container_width=True):
                sesja_treningowa.okno_usuniecia_samopoczucia(sesja_treningowa.liczba_wpisow_samopoczucia())


@st.dialog("Edytuj preset", width="large")
def okno_edycji_presetu(preset_id: int, nazwa: str):
    """Okno z edytorem ćwiczeń presetu (otwiera się po kliknięciu 'Edytuj preset')."""
    st.markdown(f"**{nazwa}**", help="Zmieniaj ćwiczenia, serie i powtórzenia, dodawaj lub usuwaj wiersze.")
    dane = wczytaj_cwiczenia_presetu(preset_id)
    edytowane = st.data_editor(
        dane,
        num_rows="dynamic",          # pozwala dodawać i usuwać wiersze
        use_container_width=True,
        hide_index=True,
        key=f"edytor_{preset_id}",
        column_config={
            "Cwiczenie": st.column_config.TextColumn("Ćwiczenie", required=True),
            "Rola": st.column_config.SelectboxColumn("Rola", options=ROLE, default="Główne"),
            "Serie": st.column_config.NumberColumn("Serie", min_value=1, step=1),
            "Powt_od": st.column_config.NumberColumn("Powt. od", min_value=1, step=1),
            "Powt_do": st.column_config.NumberColumn("Powt. do", min_value=1, step=1),
            "Jednostka": st.column_config.SelectboxColumn("Jednostka", options=JEDNOSTKI, default="powt."),
            "Alternatywa": st.column_config.TextColumn("Zamiennik"),
            "Wskazowka": st.column_config.TextColumn("Wskazówka"),
        },
    )
    glownych = int((edytowane["Rola"] == "Główne").sum())
    if glownych > MAKS_GLOWNYCH:
        st.warning(f"Masz {glownych} ćwiczeń głównych, zalecane maksimum to {MAKS_GLOWNYCH}. "
                   f"Resztę ustaw jako „Dodatek”.")
    if st.button("Zapisz zmiany", type="primary", use_container_width=True):
        zapisz_cwiczenia_presetu(preset_id, edytowane)
        st.rerun()   # zamyka okno i odświeża karty


def widok_presetow():
    wczytaj_presety_startowe()   # wczytuje rozpiskę tylko za pierwszym razem
    lista = lista_presetow()

    # Kategoria to lista rozwijana (pigułki zawijały się na telefonie); presety startują bez wyboru
    kategorie = ["Wszystkie"] + lista["Kategoria"].dropna().unique().tolist()
    kategoria = st.selectbox("Kategoria", kategorie, key="presety_kategoria")
    if kategoria and kategoria != "Wszystkie":
        lista = lista[lista["Kategoria"] == kategoria]
    nazwy = lista["Nazwa"].tolist()
    if st.session_state.get("presety_wybor") not in nazwy:
        st.session_state.pop("presety_wybor", None)   # po zmianie kategorii poprzedni wybór znika

    opis = ""   # opis rozpiski jest pod znakiem „?” przy wybranym presecie (bez szarego tekstu na ekranie)
    if st.session_state.get("presety_wybor") in nazwy:
        opis = str(lista[lista["Nazwa"] == st.session_state["presety_wybor"]].iloc[0]["Cel"] or "")
    wybrana_nazwa = st.selectbox("Preset", nazwy, index=None, placeholder="Wybierz preset...", key="presety_wybor",
                                 help=opis or None)
    if not wybrana_nazwa:
        return   # dopóki nic nie wybrano, nie pokazujemy ćwiczeń
    wiersz = lista[lista["Nazwa"] == wybrana_nazwa].iloc[0]
    preset_id = int(wiersz["id"])

    dane = wczytaj_cwiczenia_presetu(preset_id)
    st.markdown(
        widok_presetu_html(wiersz["Nazwa"], wiersz["Kategoria"], wiersz["Typ"], wiersz["Cel"] or "", dane),
        unsafe_allow_html=True,
    )
    if st.button("Edytuj preset", use_container_width=True):
        okno_edycji_presetu(preset_id, wiersz["Nazwa"])
    st.button("Rozpocznij ten trening", type="primary", use_container_width=True, key="presety_start",
              on_click=sesja_treningowa.rozpocznij_z_presetu, args=(preset_id,))


def widok_asystenta():
    st.info("Trening od asystenta pojawi się tutaj. W przyszłości będzie dobierany do Twoich "
            "danych o śnie i regeneracji, a Ty zawsze zatwierdzasz propozycję.")


TRYBY_TRENINGU = {
    "start": ("Rozpocznij trening", "Prowadzony trening seria po serii z licznikiem przerw.", sesja_treningowa.widok_startu),
    "wlasny": ("Własny trening", "Zapisz trening od zera: ćwiczenia, ciężary, serie.", widok_wlasny_trening),
    "presety": ("Presety", "Gotowe rozpiski, które możesz edytować.", widok_presetow),
    "asystent": ("Trening od asystenta", "Propozycja dopasowana do Ciebie. Wkrótce.", widok_asystenta),
}


def przelacz_tryb_treningu(klucz: str) -> None:
    """Klik w kafelek: otwiera go, a ponowny klik w ten sam zamyka (nic nie jest wybrane)."""
    if st.session_state.get("tryb_treningu") == klucz:
        st.session_state["tryb_treningu"] = None
    else:
        st.session_state["tryb_treningu"] = klucz


def strona_treningi():
    st.markdown(naglowek_strony("Treningi"), unsafe_allow_html=True)
    if sesja_treningowa.widok_jesli_aktywna():
        return
    st.session_state.setdefault("tryb_treningu", None)   # na starcie nic nie jest wybrane
    aktywny = st.session_state["tryb_treningu"]

    # Menu: cztery kafelki-przyciski. Po wybraniu menu znika, a w jego miejscu pojawia się wybrany ekran z przyciskiem powrotu.
    if aktywny is None:
        with st.container(key="tryby_wiersz"):
            for klucz, (tytul, opis, _) in TRYBY_TRENINGU.items():
                st.button(tytul, key=f"btn_{klucz}", on_click=przelacz_tryb_treningu, args=(klucz,),
                          use_container_width=True, help=opis)
    else:
        with st.container(key=f"tryby_powrot_{aktywny}"):
            st.button(TRYBY_TRENINGU[aktywny][0], key="btn_wroc", on_click=przelacz_tryb_treningu, args=(aktywny,),
                      use_container_width=True, help="Wróć do wyboru rodzaju treningu.")
        TRYBY_TRENINGU[aktywny][2]()


# Pierwsza pozycja listy presetów w planie: dzień treningowy bez narzuconego presetu
BRAK_TYPU = "— dowolny —"


def _pasek_tygodnia_html(plan) -> str:
    """Siedem kwadratów Pn-Nd: ciemny = trening, jasny = odpoczynek."""
    elementy = []
    for _, d in plan.iterrows():
        akt = bool(d["Aktywny"])
        k_typu = kolor_typu(d["Typ"]) if akt else None
        if k_typu:          # dzień treningowy w kolorze rodzaju treningu (Dół, Góra, Plyo, Cardio)
            tlo = f"background:color-mix(in srgb, {k_typu} 16%, var(--e-karta));border-color:{k_typu} !important;"
            tekst = "var(--e-tekst)"
        elif akt:
            tlo = "background-color:var(--e-przycisk);background-image:var(--e-przycisk-grad);"
            tekst = "var(--e-dzis_tekst)"
        else:
            tlo = "background:var(--e-karta);"
            tekst = "var(--e-przyg)"
        podpis = html.escape(nazwa_krotka(d["Typ"]) or "trening") if akt else "wolne"   # nazwa presetu wpisana przez użytkownika
        elementy.append(
            f'<div style="flex:1;min-width:0;text-align:center;padding:12px 4px;border-radius:14px;'
            f'border:2px solid var(--e-obram2);{tlo}color:{tekst};">'
            f'<div style="font-weight:700;">{SKROTY_DNI[int(d["Dzien"])]}</div>'
            f'<div style="font-size:0.72rem;opacity:0.85;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{podpis}</div>'
            f'</div>'
        )
    return f'<div style="display:flex;gap:8px;margin:4px 0 18px 0;">{"".join(elementy)}</div>'


def strona_plan():
    _naglowek_z_pytajnikiem("Mój plan", "Twój typowy tydzień treningowy.")
    plan = wczytaj_plan()
    st.markdown(_pasek_tygodnia_html(plan), unsafe_allow_html=True)
    wczytaj_presety_startowe()
    lista_p = lista_presetow()

    with st.container(key="plan_edycja"), st.expander("Zmień plan tygodnia", icon=":material/edit_calendar:"):
        with st.form("formularz_planu"):
            wyniki = []
            for _, d in plan.iterrows():
                i = int(d["Dzien"])
                with st.container(border=True, key=f"plan_dzien_{i}"):
                    k_dzien, k_trening, k_typ, k_godz, k_notatka = st.columns([1.3, 1, 2, 1.2, 2.5], vertical_alignment="center")
                    k_dzien.markdown(f"**{NAZWY_DNI[i]}**")
                    aktywny = k_trening.toggle("Trening", value=bool(d["Aktywny"]), key=f"plan_akt_{i}")
                    opcje = [BRAK_TYPU] + lista_p["Nazwa"].tolist()
                    # stary wpis planu (rodzaj, np. "Góra Push") pokazujemy jako pasujący preset
                    obecny = sesja_treningowa.preset_z_etykiety(lista_p, d["Typ"]) or d["Typ"]
                    if obecny and obecny not in opcje:
                        opcje.append(obecny)            # preset usunięty z listy nie ginie po cichu
                    typ = k_typ.selectbox(
                        "Preset", opcje, key=f"plan_typ_{i}", label_visibility="collapsed",
                        index=opcje.index(obecny) if obecny in opcje else 0,
                    )
                    godz_start = datetime.strptime(d["Godzina"], "%H:%M").time() if d["Godzina"] else None
                    godz = k_godz.time_input(
                        "Godzina", value=godz_start, key=f"plan_godz_{i}", label_visibility="collapsed", step=900,
                    )
                    notatka = k_notatka.text_input(
                        "Notatka", value=d["Notatka"], key=f"plan_not_{i}", label_visibility="collapsed",
                        placeholder="Notatka (np. siłownia, z kolegą)",
                    )
                    wyniki.append({
                        "Dzien": i, "Aktywny": aktywny, "Typ": "" if typ == BRAK_TYPU else typ,
                        "Godzina": godz.strftime("%H:%M") if godz else "", "Notatka": notatka,
                    })
            zapisano = st.form_submit_button("Zapisz plan", type="primary")

    if zapisano:
        zapisz_plan(wyniki)
        st.toast("Plan zapisany.")
        st.rerun()


# ---------------------------------------------------------------
# STRONA: DZISIEJSZY TRENING (pojawia się w menu tylko w dni treningowe z planu)
# ---------------------------------------------------------------
def strona_dzisiejszy_trening():
    plan_dzis = plan_na_dzien()
    podtytul = plan_dzis["Typ"] or "Trening dowolny"
    if plan_dzis["Godzina"]:
        podtytul += f" · {plan_dzis['Godzina']}"
    st.markdown(naglowek_strony("Trening na dziś", html.escape(podtytul)), unsafe_allow_html=True)
    if sesja_treningowa.widok_jesli_aktywna():
        return
    if plan_dzis["Notatka"]:
        st.caption(f"Notatka z planu: {plan_dzis['Notatka']}")
    if trening_zapisany():
        st.success("Dzisiejszy trening jest już zapisany. Możesz dodać kolejny.")
    sesja_treningowa.widok_startu(plan_dzis["Typ"])
    plan_preset = sesja_treningowa.preset_z_etykiety(lista_presetow(), plan_dzis["Typ"])
    if plan_preset and "typ_treningu" not in st.session_state:
        st.session_state["typ_treningu"] = plan_preset
    with st.expander("Wolisz wpisać trening ręcznie, po fakcie?"):
        widok_wlasny_trening()


def strona_na_dzis():
    """Szczegóły rekomendacji „na dziś” (pozycja w menu bocznym) i przyciski, które przenoszą do wyboru treningu."""
    _naglowek_z_pytajnikiem("Rekomendacja na dziś", "Podpowiedź ze snu, regeneracji i wczorajszego treningu.")
    if not _rek_dnia:
        st.write("Dziś nic do zmiany: trenuj według planu.")
        return
    rek = _rek_dnia["rek"]
    if rek["regeneracja"]:
        sesja_treningowa.karta_rekomendacji(rek["regeneracja"]["karta"])
        if rek["regeneracja"]["poziom"] == "lzejszy" and st.button("Włącz lżejszy trening", type="primary", use_container_width=True,
                                                                  key="na_dzis_lzejszy"):
            st.session_state["lzejszy_zalecany"] = True
            st.switch_page(strona_treningi_pg)
    if rek["partie"]:
        sesja_treningowa.karta_rekomendacji(rek["partie"]["karta"])
        if rek["partie"]["propozycja"] and st.button(f"Wybierz: {rek['partie']['propozycja']}", type="primary", use_container_width=True,
                                                    key="na_dzis_preset"):
            st.session_state["preset_zalecany"] = rek["partie"]["propozycja"]
            st.switch_page(strona_treningi_pg)


def strona_jutro():
    """Plan na jutro (pozycja w menu bocznym pod Startem)."""
    p = _plan_jutro
    podtytul = p["Typ"] or "Trening dowolny"
    if p["Godzina"]:
        podtytul += f" · {p['Godzina']}"
    st.markdown(naglowek_strony("Jutro w planie", html.escape(podtytul)), unsafe_allow_html=True)
    if p["Notatka"]:
        st.caption(f"Notatka z planu: {p['Notatka']}")
    try:   # podgląd presetu, który jest w planie na jutro
        lista = lista_presetow()
        nazwa = sesja_treningowa.preset_z_etykiety(lista, p["Typ"])
        if nazwa:
            wiersz = lista[lista["Nazwa"] == nazwa].iloc[0]
            st.markdown(widok_presetu_html(wiersz["Nazwa"], wiersz["Kategoria"], wiersz["Typ"], wiersz["Cel"] or "",
                                           wczytaj_cwiczenia_presetu(int(wiersz["id"]))), unsafe_allow_html=True)
        else:
            st.caption("Do tego wpisu w planie nie pasuje żaden preset. Wybierz preset w „Mój plan”.")
    except Exception:   # noqa: BLE001 (podgląd nie może zablokować strony)
        pass
    if st.button("Zmień plan", key="jutro_plan", use_container_width=True):
        st.switch_page(strona_plan_pg)


def strona_postepy():
    _naglowek_z_pytajnikiem("Postępy", "Rekordy, objętość i trendy w ćwiczeniach.")
    postepy.widok_postepow()


def strona_profil():
    _naglowek_z_pytajnikiem("Profil", "Twoje dane, siłownia, ulubione ćwiczenia oraz eksport, kopia i usuwanie danych.")
    profil.widok_profilu()

# MENU BOCZNE
# ---------------------------------------------------------------
# Lista stron: funkcja, nazwa w menu i ikona (Material Symbols)
plan_dzis = plan_na_dzien()
strona_treningi_pg = st.Page(strona_treningi, title="Treningi", icon=":material/fitness_center:")
strona_plan_pg = st.Page(strona_plan, title="Mój plan", icon=":material/event_note:")
strony = [st.Page(strona_start, title="Start", icon=":material/home:", default=True)]
if _plan_jutro["Aktywny"]:
    strony.append(st.Page(strona_jutro, title=f"Jutro: {nazwa_krotka(_plan_jutro['Typ']) or 'trening'}", icon=":material/event:", url_path="jutro"))
if _rek_dnia:
    strony.append(st.Page(strona_na_dzis, title=_rek_dnia["tytul"], icon=":material/auto_awesome:", url_path="na-dzis"))
if plan_dzis["Aktywny"]:
    zrobiony_dzis = trening_zapisany()
    strony.append(st.Page(
        strona_dzisiejszy_trening,
        title=f"Dziś: {nazwa_krotka(plan_dzis['Typ']) or 'trening'}" + (" ✓" if zrobiony_dzis else ""),
        icon=":material/check_circle:" if zrobiony_dzis else ":material/play_circle:",
        url_path="dzis",
    ))
strony += [
    st.Page(strona_regeneracja, title="Regeneracja", icon=":material/bedtime:"),
    strona_treningi_pg,
    st.Page(strona_postepy, title="Postępy", icon=":material/trending_up:"),
    st.Page(strona_historia, title="Historia", icon=":material/history:"),
    strona_plan_pg,
]
strona_profil_pg = st.Page(strona_profil, title="Profil", icon=":material/account_circle:", url_path="profil")
strony.append(strona_profil_pg)
wybrana = st.navigation(strony)
st.session_state["strona_tytul"] = wybrana.title

# Dół menu: połączenie z Garminem i ustawienia (pojawia się pod listą stron)
with st.sidebar:
    try:
        with st.container(key="profil_kafelek"):     # avatar i imię; dotknięcie otwiera Profil (CSS w profil.py)
            st.markdown(profil.kafelek_boczny_html(), unsafe_allow_html=True)
            st.page_link(strona_profil_pg, label="Profil")
        st.markdown("<div class='pr-linia'></div>", unsafe_allow_html=True)     # kreska oddzielająca profil od Ustawień (jak nad profilem)
    except Exception:   # noqa: BLE001 (kafelek nie może zablokować menu)
        pass
    if sesja_treningowa.aktywna():
        st.markdown('<div style="padding-bottom:12px;"><div style="padding:10px 14px;border:2px solid var(--e-zielony);border-radius:12px;background:var(--e-karta);font-weight:700;color:var(--e-tekst);">Trening w toku<div style="font-weight:400;font-size:0.8rem;color:var(--e-przyg);">wróć do zakładki Treningi</div></div></div>', unsafe_allow_html=True)
    with st.expander("⚙️ Ustawienia i połączenie"):
        sesja_treningowa.rzad_w_jednej_linii("motyw_wybor")
        st.segmented_control("Motyw", list(MOTYWY_ZAPIS), default=wczytaj_motyw(), key="motyw_wybor",
                             on_change=_zmien_motyw,
                             help="Auto idzie za ustawieniem telefonu lub komputera (jasny albo ciemny). Po zmianie strona odświeży się sama.")
        if uzytkownik.czy_wlasciciel() and not baza.TRYB_GOSCIA:
            st.toggle("Mam zegarek Garmin", value=garmin_wlaczony(), key="garmin_wl", on_change=_zapisz_garmin,
                      help="Wyłącz, jeśli nie masz zegarka. Wtedy zamiast danych z Garmina wpisujesz sen, wagę i energię ręcznie na stronie Start.")
        if garmin_wlaczony():
            st.button("🔄 Odśwież dane z Garmina", on_click=st.cache_data.clear, use_container_width=True,
                      help="Status połączenia widać na stronie Start. Dane logowania do Garmina są w pliku .env na tym komputerze.")
    with st.expander("💬 Zgłoś uwagę"):
        st.text_area("Uwaga", key="uwaga_tekst", height=110, placeholder="Co poprawić, co przeszkadza, jaki pomysł...",
                     label_visibility="collapsed")
        st.button("Wyślij", key="uwaga_wyslij", on_click=_wyslij_uwage, use_container_width=True, type="primary",
                  help="Uwaga zapisuje się w aplikacji i przychodzi jako powiadomienie na telefon (ntfy).")
    _zapisane_uwagi = uwagi.lista(10)
    if _zapisane_uwagi:
        with st.expander(f"📝 Zapisane uwagi ({uwagi.ile()})"):
            for _u in _zapisane_uwagi:
                _opis = html.escape(f"{_u['zapisano'][5:]} · {_u['strona']}" if _u["strona"] else _u["zapisano"][5:])
                _tresc = html.escape(_u["tresc"]).replace("\n", "<br>")
                st.markdown(f"**{_opis}**<br>{_tresc}", unsafe_allow_html=True)
                st.button("Usuń", key=f"uwaga_u_{_u['id']}", on_click=uwagi.usun, args=(_u["id"],))
    _wybrany_motyw = st.session_state.pop("motyw_zastosuj", None)
    if _wybrany_motyw in MOTYWY_ZAPIS:
        components.html(skrypt_motywu(_wybrany_motyw), height=0)

# Uruchamia wybraną stronę. Musi być na końcu, po definicjach wszystkich funkcji.
wybrana.run()