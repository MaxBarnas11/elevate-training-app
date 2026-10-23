"""Uwagi do aplikacji (przycisk „Zgłoś uwagę”): zapis w bazie i powiadomienie ntfy na telefon właściciela.

Uwaga zapisuje się w bazie zawsze (nie przepada, gdy brak sieci); powiadomienie jest dodatkiem i jego błąd nie blokuje zapisu.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime

import baza
import powiadomienia
import uzytkownik

MAKS_DLUGOSC = 2000


def _polacz() -> sqlite3.Connection:
    db = sqlite3.connect(baza.SCIEZKA_BAZY)
    db.execute(
        "CREATE TABLE IF NOT EXISTS uwagi ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, Zapisano TEXT NOT NULL, Strona TEXT, Tresc TEXT NOT NULL, "
        "Wyslano INTEGER NOT NULL DEFAULT 0)"
    )
    return db


def zapisz(tresc: str, strona: str = "", teraz: datetime | None = None) -> tuple[int | None, bool]:
    """Zapisuje uwagę i wysyła powiadomienie. Zwraca (id, czy powiadomienie dotarło); (None, False) przy pustej treści."""
    tresc = (tresc or "").strip()[:MAKS_DLUGOSC]
    if not tresc:
        return None, False
    teraz = teraz or datetime.now()
    with closing(_polacz()) as db:
        cur = db.execute("INSERT INTO uwagi (Zapisano, Strona, Tresc) VALUES (?, ?, ?)",
                         (teraz.strftime("%Y-%m-%d %H:%M"), strona or "", tresc))
        db.commit()
        nr = cur.lastrowid
    try:
        tytul = f"Uwaga: {strona}" if strona else "Uwaga do aplikacji"
        if not uzytkownik.czy_wlasciciel():   # uwaga od znajomego: właściciel widzi, kto ją wysłał
            tytul += f" ({uzytkownik.email() or 'gość'})"
        wyslano = bool(powiadomienia.wyslij(tytul, tresc, priorytet=3, tag="memo"))
    except Exception:
        wyslano = False
    if wyslano:
        with closing(_polacz()) as db:
            db.execute("UPDATE uwagi SET Wyslano = 1 WHERE id = ?", (nr,))
            db.commit()
    return nr, wyslano


def lista(ile: int = 10) -> list[dict]:
    """Ostatnie uwagi, najnowsza pierwsza."""
    with closing(_polacz()) as db:
        wiersze = db.execute("SELECT id, Zapisano, Strona, Tresc, Wyslano FROM uwagi ORDER BY id DESC LIMIT ?", (ile,)).fetchall()
    return [{"id": w[0], "zapisano": w[1], "strona": w[2] or "", "tresc": w[3], "wyslano": bool(w[4])} for w in wiersze]


def ile() -> int:
    with closing(_polacz()) as db:
        return db.execute("SELECT COUNT(*) FROM uwagi").fetchone()[0]


def usun(nr: int) -> None:
    with closing(_polacz()) as db:
        db.execute("DELETE FROM uwagi WHERE id = ?", (nr,))
        db.commit()
