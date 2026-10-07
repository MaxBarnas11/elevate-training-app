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
.stTabs [data-baseweb="tab-list"] { gap: 12px; border-bottom: 1px solid var(--ramka); padding-bottom: 8px; }
.stTabs button[data-baseweb="tab"] {
  height: 4rem; padding: 0 1.8rem; border-radius: 14px;
  background: rgba(255, 255, 255, 0.04); border: 1px solid transparent;
}
.stTabs button[data-baseweb="tab"] p { font-size: 1.35rem !important; font-weight: 600; }
.stTabs button[data-baseweb="tab"]:hover { background: rgba(37, 99, 235, 0.20); }
.stTabs button[aria-selected="true"] {
  background: linear-gradient(135deg, #1D4ED8, #0B1F4B);
  border: 1px solid var(--akcent-jasny);
}
.stTabs button[aria-selected="true"] p { color: #FFFFFF; }
/* Ukrywamy domyślne czerwone podkreślenie zakładki */
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

/* Kafelki z liczbami (metric) jako karty */
[data-testid="stMetric"] {
  background: linear-gradient(145deg, rgba(37, 99, 235, 0.16), rgba(255, 255, 255, 0.03));
  border: 1px solid var(--ramka); border-radius: 16px; padding: 1.1rem 1.3rem;
}
[data-testid="stMetricLabel"] p {
  font-size: 1rem; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.06em;
}
[data-testid="stMetricValue"] { font-size: 2.6rem; font-weight: 700; }

/* Przyciski: wyższe, zaokrąglone; główny w kolorze granatowo-niebieskim */
.stButton button {
  min-height: 3.2rem; font-size: 1.1rem; border-radius: 12px;
  border: 1px solid var(--ramka); background: rgba(255, 255, 255, 0.04);
}
.stButton button:hover { border-color: var(--akcent-jasny); }
.stButton button[kind="primary"],
.stButton button[data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, #2563EB, #1D4ED8); border: none; color: #FFFFFF;
}
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