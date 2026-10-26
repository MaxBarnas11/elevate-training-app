"""Styl strony: tło i menu boczne w kolorach motywu (jasny beżowy lub ciemny neonowy)."""
from __future__ import annotations

import streamlit as st

from motywy import zastosuj_motyw

# Tło strony: ciemniejszy beż u góry i u dołu okna (poświata) na jasnym beżowym tle.
# background-attachment: fixed sprawia, że poświata zostaje w oknie przy przewijaniu.
CSS_TLA = """
<style>
.stApp {
    background:
        radial-gradient(ellipse 80% 55% at 50% 0%, var(--e-tlo_g1) 0%, transparent 70%),
        radial-gradient(ellipse 90% 60% at 50% 110%, var(--e-tlo_g2) 0%, transparent 70%),
        linear-gradient(180deg, var(--e-tlo_l1) 0%, var(--e-tlo_l2) 100%);
    background-attachment: fixed;
}
[data-testid="stSidebar"] {
    background:
        radial-gradient(ellipse at 50% 0%, var(--e-bok_g) 0%, transparent 60%),
        var(--e-bok) !important;
}
</style>
"""


def zastosuj_styl() -> None:
    """Wstrzykuje zmienne kolorów motywu oraz tło strony."""
    zastosuj_motyw()
    st.markdown(CSS_TLA, unsafe_allow_html=True)


def naglowek(tekst: str) -> None:
    """Prosty nagłówek (zostawiony dla zgodności ze starym kodem)."""
    st.markdown(f"## {tekst}")