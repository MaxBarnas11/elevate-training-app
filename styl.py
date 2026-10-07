"""Wygląd aplikacji: motyw czarno-biało-granatowy, logo, większe zakładki."""
import streamlit as st


def zastosuj_styl() -> None:
    """Dokłada do strony własny CSS (tło, zakładki, kafelki, przyciski)."""
    st.markdown(
        """
<style>
/* Kolory w jednym miejscu: łatwo je później zmienić */
:root {
  --akcent: #2563EB;
  --akcent-jasny: #3B82F6;
  --granat: #0B1F4B;
  --ramka: rgba(59, 130, 246, 0.28);
}

/* Tło: czerń z granatową poświatą w rogu, przechodząca w ciemny granat */
.stApp {
  background:
    radial-gradient(1100px 600px at 8% -10%, rgba(37, 99, 235, 0.20), transparent 60%),
    linear-gradient(180deg, #05070D 0%, #0A1330 100%);
  background-attachment: fixed;
}
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.5rem; padding-left: 3rem; padding-right: 3rem; }

/* Nagłówek z logo */
.tb-naglowek { display: flex; align-items: center; gap: 18px; margin-bottom: 1.4rem; }
.tb-logo {
  display: flex; padding: 12px; border-radius: 18px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.35), rgba(11, 31, 75, 0.7));
  border: 1px solid var(--ramka);
}
.tb-nazwa { font-size: 2.8rem; font-weight: 800; letter-spacing: -0.02em; line-height: 1.1; color: #FFFFFF; }
.tb-data { font-size: 1rem; color: #94A3B8; margin-top: 2px; }

/* Pasek zakładek: duży, z wyraźnie zaznaczoną aktywną zakładką */


/* ===== MENU BOCZNE ===== */
/* Tło menu w ciemnym granacie i cienka niebieska linia po prawej */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #070C1C 0%, #0B1530 100%);
  border-right: 1px solid rgba(59, 130, 246, 0.28);
}
/* Pozycje menu: wyższe, z odstępami i zaokrąglone */
[data-testid="stSidebarNav"] a,
[data-testid="stSidebarNavLink"] {
  padding: 0.9rem 1rem !important;
  border-radius: 12px !important;
  margin-bottom: 6px !important;
}
/* Napis i ikona w pozycji menu: większe (ikona też jest elementem span) */
[data-testid="stSidebarNav"] a span,
[data-testid="stSidebarNavLink"] span {
  font-size: 1.3rem !important;
  font-weight: 600 !important;
}
/* Aktualnie otwarta strona: wyróżnione granatowo-niebieskie tło */
[data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: linear-gradient(135deg, #1D4ED8, #0B1F4B) !important;
}
/* Tytuły stron: większe */
h1 { font-size: 2.6rem !important; font-weight: 800 !important; }

</style>
        """,
        unsafe_allow_html=True,
    )


def naglowek(nazwa: str, podpis: str) -> None:
    """Rysuje nagłówek z logo (sztanga) zamiast zwykłego tytułu."""
    # Logo to prosta sztanga narysowana w SVG, więc nie potrzebuje żadnego pliku
    st.markdown(
        f"""
<div class="tb-naglowek">
<div class="tb-logo">
<svg width="46" height="46" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="2" y="17" width="5" height="14" rx="1.5" fill="#3B82F6"/>
<rect x="8" y="11" width="6" height="26" rx="2" fill="#2563EB"/>
<rect x="14" y="22" width="20" height="4" rx="2" fill="#E5E7EB"/>
<rect x="34" y="11" width="6" height="26" rx="2" fill="#2563EB"/>
<rect x="41" y="17" width="5" height="14" rx="1.5" fill="#3B82F6"/>
</svg>
</div>
<div>
<div class="tb-nazwa">{nazwa}</div>
<div class="tb-data">{podpis}</div>
</div>
</div>
        """,
        unsafe_allow_html=True,
    )