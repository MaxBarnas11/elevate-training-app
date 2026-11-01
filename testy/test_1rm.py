"""Szacowany ciężar maksymalny (1RM) wzorem Epleya."""
from __future__ import annotations

import pytest

from postepy import szacowane_1rm


def test_jedno_powtorzenie_to_sam_ciezar():
    assert szacowane_1rm(100, 1) == 100


def test_wzor_epleya():
    assert szacowane_1rm(80, 8) == pytest.approx(80 * (1 + 8 / 30))
    assert szacowane_1rm(100, 10) == pytest.approx(133.33, abs=0.01)


def test_wiecej_powtorzen_to_wyzszy_szacunek():
    assert szacowane_1rm(60, 12) > szacowane_1rm(60, 6) > szacowane_1rm(60, 1)


@pytest.mark.parametrize("ciezar, powt", [(0, 5), (60, 0), (60, 13)])
def test_poza_wiarygodnym_zakresem_brak_szacunku(ciezar, powt):
    """Powyżej 12 powtórzeń wzór przestaje być wiarygodny, więc aplikacja nic nie szacuje."""
    assert szacowane_1rm(ciezar, powt) is None
