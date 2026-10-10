"""Styl strony: jasny, beżowy motyw z delikatnymi, ciemniejszymi poświatami."""
from __future__ import annotations

import streamlit as st

# Tło strony: ciemniejszy beż u góry i u dołu okna (poświata) na jasnym beżowym tle.
# background-attachment: fixed sprawia, że poświata zostaje w oknie przy przewijaniu.
CSS_TLA = """
<style>
.stApp {
    background:
        radial-gradient(ellipse 80% 55% at 50% 0%, #D6C49D 0%, transparent 70%),
        radial-gradient(ellipse 90% 60% at 50% 110%, #D0BC92 0%, transparent 70%),
        linear-gradient(180deg, #EFE6D2 0%, #E9DFCB 100%);
    background-attachment: fixed;
}
[data-testid="stSidebar"] {
    background:
        radial-gradient(ellipse at 50% 0%, #CDBB92 0%, transparent 60%),
        #DDD0B6 !important;
}
</style>
"""


def zastosuj_styl() -> None:
    """Wstrzykuje beżowe tło z poświatą."""
    st.markdown(CSS_TLA, unsafe_allow_html=True)


def naglowek(tekst: str) -> None:
    """Prosty nagłówek (zostawiony dla zgodności ze starym kodem)."""
    st.markdown(f"## {tekst}")