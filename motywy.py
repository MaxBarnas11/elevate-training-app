"""Motywy kolorystyczne: jasny („Piasek + kolory”) i ciemny („Neon”).

Wszystkie kolory w aplikacji są zmiennymi CSS `--e-...`. Zmienne mają postać `light-dark(jasny, ciemny)`,
a Streamlit ustawia na `.stApp` właściwość `color-scheme` zgodnie z aktywnym motywem, więc przeglądarka sama
wybiera właściwą wartość (bez skryptów i bez znajomości motywu po stronie Pythona).
Starsze przeglądarki (bez light-dark) dostają wersję jasną, a ciemną przy ustawieniu systemu na ciemny.
"""
from __future__ import annotations

import streamlit as st

# nazwa: (jasny, ciemny)
PALETA: dict[str, tuple[str, str]] = {
    # tło strony i menu
    "tlo": ("#E9DFCB", "#050506"),
    "tlo_g1": ("#D6C49D", "#050506"),
    "tlo_g2": ("#D0BC92", "#050506"),
    "tlo_l1": ("#EFE6D2", "#050506"),
    "tlo_l2": ("#E9DFCB", "#050506"),
    "bok_g": ("#CDBB92", "#0A0A0D"),
    "bok": ("#DDD0B6", "#0A0A0D"),
    # karty i kafelki
    "karta": ("#F4ECDC", "#0F0F12"),
    "kafelek": ("#F1E7D2", "#0F0F12"),
    "kafelek_glow": ("#9A7B4A44", "transparent"),
    "glow_presetu": ("#8A6D3B1F", "transparent"),
    "dodatek": ("#EDE3CF", "#15141A"),
    "plakietka": ("#EFE3C9", "#18171D"),
    "pill": ("#F4ECDC", "#18171D"),
    "obram": ("#CFC2A6", "#27252E"),
    "obram2": ("#BFAE86", "#2E2C38"),
    "obram_hover": ("#9C8A5E", "#4A4757"),
    "tlo_pier": ("#DCD0B8", "#24222B"),
    # tekst
    "tekst": ("#1B1B1A", "#F5F3FA"),
    "przyg": ("#6B6355", "#9A97A6"),
    "wsk": ("#7A5F2E", "#FFB03A"),
    "linia": ("#2B2A27", "#F5F3FA"),
    # statusy
    "zielony": ("#3F9A5A", "#2EE6A6"),
    "zolty": ("#E0AC00", "#FFD23F"),
    "pomaranczowy": ("#E8751A", "#FF8A3D"),
    "czerwony": ("#D5392F", "#FF5C5C"),
    "akcent": ("#7A6A4F", "#9A97A6"),
    "kasuj": ("#C0392B", "#FF5C5C"),
    "kasuj_ramka": ("#E2B4AE", "#5A2833"),
    # kolory funkcji
    "przerwa": ("#E8751A", "#FF5CAA"),
    "serie": ("#3A6FD8", "#6C8CFF"),
    "typ_dol": ("#E07A2A", "#FF8A3D"),
    "typ_gora": ("#3A6FD8", "#5C86FF"),
    "typ_plyo": ("#8A5CC8", "#C45CFF"),
    "typ_cardio": ("#3F9A5A", "#2EE6A6"),
    # wykresy słupkowe
    "slupek": ("#7A6A4F", "#4A4757"),
    "slupek_biezacy": ("#2B2A27", "#FF8A3D"),
    "poprzedni": ("#A8A196", "#3A3845"),
    # główny przycisk (w ciemnym neonowy gradient)
    "przycisk": ("#1B1B1A", "#FF3D9A"),
    "g1": ("#1B1B1A", "#FF8A3D"),
    "g2": ("#1B1B1A", "#FF3D9A"),
    "g3": ("#1B1B1A", "#8B5CFF"),
    "przycisk_tekst": ("#FFFFFF", "#0A0610"),
    "dzis_tekst": ("#F4ECDC", "#0A0610"),
    # tytuł strony: trójkolorowa poświata (w jasnym motywie w jaśniejszych, bardziej przezroczystych odcieniach)
    "tytul_glow1": ("rgba(224,60,130,0.34)", "rgba(255,61,154,0.30)"),     # różowa, pod napisem
    "tytul_glow2": ("rgba(232,117,26,0.45)", "rgba(255,138,61,0.40)"),     # pomarańczowa, z lewej
    "tytul_glow3": ("rgba(138,92,200,0.42)", "rgba(139,92,255,0.40)"),     # fioletowa, z prawej
    # cienie, paski, animacje
    "cien_s": ("rgba(60,45,20,0.10)", "rgba(0,0,0,0.45)"),
    "cien_m": ("rgba(90,65,25,0.14)", "rgba(0,0,0,0.50)"),
    "cien_h": ("rgba(60,45,20,0.18)", "rgba(0,0,0,0.55)"),
    "cien_pasek": ("rgba(60,45,20,0.45)", "rgba(0,0,0,0.70)"),
    "pasek": ("rgba(233,223,203,0.97)", "rgba(5,5,6,0.97)"),
    "naglowek": ("rgba(233,223,203,0.92)", "rgba(5,5,6,0.92)"),
    "puls": ("rgba(232,117,26,0.55)", "rgba(255,61,154,0.55)"),
    "puls0": ("rgba(232,117,26,0)", "rgba(255,61,154,0)"),
    # warstwa przyciemniająca poświatę kart (w ciemnym motywie poświata jest słabsza)
    "przyciemnienie": ("transparent", "rgba(15,15,18,0.72)"),
    "przyciemnienie_tlo": ("transparent", "rgba(5,5,6,0.72)"),      # to samo dla poświaty na tle strony
}

# Skala RPE 1-10: (kolor jasny, kolor ciemny, tekst jasny, tekst ciemny)
_RPE_JASNY = ["#5BA05E", "#6FAA55", "#86B04C", "#A3B340", "#C4B238", "#D9A82F", "#E0912B", "#E07A2A", "#D95F2B", "#C8402F"]
_RPE_CIEMNY = ["#2EE6A6", "#5BEA8A", "#8BEE6E", "#BBEF55", "#E4EA46", "#FFD23F", "#FFB03A", "#FF8A3D", "#FF5C5C", "#FF3D6E"]
_RPE_TEKST_CIEMNY_W_JASNYM = {3, 4, 5}      # indeksy, w których w jasnym motywie tekst jest ciemny (jak dotąd)

for _i in range(10):
    PALETA[f"rpe_{_i}"] = (_RPE_JASNY[_i], _RPE_CIEMNY[_i])
    PALETA[f"rpe_t_{_i}"] = (("#1B1B1A" if _i in _RPE_TEKST_CIEMNY_W_JASNYM else "#FFFFFF"), "#0A0610")


def v(nazwa: str) -> str:
    """Zapis zmiennej CSS, np. v('karta') -> 'var(--e-karta)'."""
    if nazwa not in PALETA:
        raise KeyError(f"Nieznany kolor motywu: {nazwa}")
    return f"var(--e-{nazwa})"


_TYPY = (("dół", "typ_dol"), ("dol", "typ_dol"), ("góra", "typ_gora"), ("gora", "typ_gora"),
         ("plyo", "typ_plyo"), ("cardio", "typ_cardio"))


def kolor_typu(nazwa: str | None) -> str | None:
    """Kolor rodzaju treningu po początku nazwy (Dół, Góra, Plyo, Cardio); inne nazwy: None."""
    n = (nazwa or "").strip().lower()
    for poczatek, klucz in _TYPY:
        if n.startswith(poczatek):
            return v(klucz)
    return None


def css_zmiennych() -> str:
    """Blok <style> z definicjami zmiennych dla obu motywów."""
    jasny = "".join(f"--e-{k}:{j};" for k, (j, _c) in PALETA.items())
    ciemny = "".join(f"--e-{k}:{c};" for k, (_j, c) in PALETA.items())
    ld = "".join(f"--e-{k}:light-dark({j},{c});" for k, (j, c) in PALETA.items())
    gradient = "--e-przycisk-grad:linear-gradient(90deg,var(--e-g1),var(--e-g2),var(--e-g3));"
    return (
        "<style>"
        f":root,.stApp{{{jasny}{gradient}}}"
        f"@media (prefers-color-scheme: dark){{:root,.stApp{{{ciemny}}}}}"
        f"@supports (color: light-dark(#000,#fff)){{:root,.stApp{{{ld}}}}}"
        "</style>"
    )


# Czcionka nagłówków: szeroka grotesk przemysłowa (Archivo, szerokość 125). Ładowana z Google Fonts; gdy sieci brak, działa czcionka zapasowa.
CZCIONKA_TYTULOW = "'Archivo', 'Helvetica Neue', Arial, sans-serif"
CSS_CZCIONKI = ("<style>@import url('https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@125,800&display=swap');</style>")


def zastosuj_motyw() -> None:
    """Wstrzykuje czcionkę nagłówków i zmienne kolorów; wywoływane raz w app.py."""
    st.markdown(CSS_CZCIONKI, unsafe_allow_html=True)
    st.markdown(css_zmiennych(), unsafe_allow_html=True)


def poswiata(kolor: str, procent: int, pozycja: str = "50% 0%", zasieg: int = 70, na_tle_strony: bool = False) -> str:
    """Warstwy tła: miękka poświata w kolorze statusu (w ciemnym motywie przyciemniona). Po tym trzeba dodać kolor tła."""
    warstwa = v("przyciemnienie_tlo" if na_tle_strony else "przyciemnienie")
    return (f"linear-gradient({warstwa},{warstwa}),"
            f"radial-gradient(ellipse at {pozycja}, color-mix(in srgb, {kolor} {procent}%, transparent) 0%, transparent {zasieg}%)")
