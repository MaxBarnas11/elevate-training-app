"""Proste narzędzia do bazy treningów: kopia zapasowa, lista treningów i usuwanie testowych.

Uruchamiasz w terminalu (w folderze aplikacji, z włączonym venv):
    python narzedzia_bazy.py kopia          zapisuje kopię bazy w folderze kopie/
    python narzedzia_bazy.py lista          pokazuje zapisane treningi (numer, data, rodzaj, ile ćwiczeń)
    python narzedzia_bazy.py usun 3 4 5     usuwa treningi o podanych numerach (po potwierdzeniu)
Przed usunięciem zawsze robi się kopia, więc pomyłkę da się cofnąć.
"""
from __future__ import annotations

import sqlite3
import sys
from contextlib import closing
from datetime import datetime
from pathlib import Path

FOLDER = Path(__file__).parent
SCIEZKA = FOLDER / "treningi.db"


def _tabela_istnieje(db: sqlite3.Connection, nazwa: str) -> bool:
    return db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (nazwa,)).fetchone() is not None


def kopia(sciezka: Path = SCIEZKA) -> Path:
    """Spójna kopia bazy (używa mechanizmu SQLite, więc działa też, gdy aplikacja jest włączona)."""
    cel_folder = sciezka.parent / "kopie"
    cel_folder.mkdir(exist_ok=True)
    cel = cel_folder / f"treningi_{datetime.now():%Y%m%d_%H%M%S}.db"
    with closing(sqlite3.connect(sciezka)) as zrodlo, closing(sqlite3.connect(cel)) as cel_db:
        zrodlo.backup(cel_db)
    return cel


def lista(sciezka: Path = SCIEZKA) -> list[tuple]:
    with closing(sqlite3.connect(sciezka)) as db:
        if not _tabela_istnieje(db, "sesje"):
            return []
        kolumny = {w[1] for w in db.execute("PRAGMA table_info(sesje)")}
        czas = "s.Czas_min" if "Czas_min" in kolumny else "NULL"
        return db.execute(
            f"SELECT s.id, s.Data, COALESCE(s.Typ_treningu, ''), COUNT(w.id), {czas} "
            "FROM sesje s LEFT JOIN wpisy_cwiczen w ON w.Sesja_id = s.id GROUP BY s.id ORDER BY s.Data DESC, s.id DESC"
        ).fetchall()


def usun(numery: list[int], sciezka: Path = SCIEZKA) -> int:
    """Usuwa treningi (sesje) razem z ich ćwiczeniami i seriami. Zwraca liczbę usuniętych treningów."""
    with closing(sqlite3.connect(sciezka)) as db:
        usuniete = 0
        for numer in numery:
            if _tabela_istnieje(db, "serie_wykonane"):
                db.execute("DELETE FROM serie_wykonane WHERE Sesja_id = ?", (numer,))
            db.execute("DELETE FROM wpisy_cwiczen WHERE Sesja_id = ?", (numer,))
            usuniete += db.execute("DELETE FROM sesje WHERE id = ?", (numer,)).rowcount
        db.commit()
    return usuniete


def _wypisz(wiersze: list[tuple]) -> None:
    if not wiersze:
        print("Brak zapisanych treningów.")
        return
    print(f"{'nr':>4}  {'data':<11} {'rodzaj':<20} {'wpisów':>6}  czas")
    for numer, data, typ, ile, czas in wiersze:
        print(f"{numer:>4}  {data:<11} {typ[:20]:<20} {ile:>6}  {'' if czas is None else f'{czas} min'}")


def main(argumenty: list[str]) -> None:
    if not SCIEZKA.exists():
        print(f"Nie znaleziono bazy: {SCIEZKA}")
        return
    polecenie = argumenty[0] if argumenty else ""
    if polecenie == "kopia":
        print(f"Kopia zapisana: {kopia()}")
    elif polecenie == "lista":
        _wypisz(lista())
    elif polecenie == "usun":
        try:
            numery = [int(a) for a in argumenty[1:]]
        except ValueError:
            print("Podaj numery treningów jako liczby, np.: python narzedzia_bazy.py usun 3 4 5")
            return
        if not numery:
            print("Podaj numery treningów do usunięcia (zobacz: python narzedzia_bazy.py lista).")
            return
        _wypisz([w for w in lista() if w[0] in numery])
        if input(f"Usunąć {len(numery)} trening(ów)? Wpisz tak, aby potwierdzić: ").strip().lower() != "tak":
            print("Anulowano, nic nie usunięto.")
            return
        print(f"Kopia przed usunięciem: {kopia()}")
        print(f"Usunięto treningów: {usun(numery)}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
