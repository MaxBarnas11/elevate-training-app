"""Wszystkie funkcje do pracy z bazą SQLite (treningi.db)."""
from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pandas as pd

import uzytkownik

# Plik bazy leży obok tego pliku, niezależnie od tego, skąd uruchomisz aplikację.
# Zmienna OVRLD_BAZA (pełna ścieżka do pliku .db) uruchamia osobną instancję z własnymi, pustymi danymi (konto gościa, GOSC.bat).
TRYB_GOSCIA = bool(os.environ.get("OVRLD_BAZA"))


class _SciezkaBazy(os.PathLike):
    """Ścieżka do bazy bieżącego użytkownika. Wygląda jak Path (sqlite3.connect, .parent, .exists() itd.), ale przy każdym użyciu
    pyta moduł uzytkownik, czyja to sesja, więc wiele osób naraz nigdy nie dzieli jednego pliku."""

    def _p(self) -> Path:
        return uzytkownik.sciezka_bazy()

    def __fspath__(self) -> str:
        return str(self._p())

    __str__ = __fspath__

    def __repr__(self) -> str:
        return f"SciezkaBazy({self.__fspath__()!r})"

    def __getattr__(self, nazwa: str):
        return getattr(self._p(), nazwa)

    def __truediv__(self, inny):
        return self._p() / inny

    def __eq__(self, inny) -> bool:
        try:
            return self._p() == Path(inny)
        except TypeError:
            return False

    def __hash__(self) -> int:
        return hash(self._p())


if TRYB_GOSCIA:
    SCIEZKA_BAZY = Path(os.environ["OVRLD_BAZA"])
    SCIEZKA_BAZY.parent.mkdir(parents=True, exist_ok=True)
else:
    SCIEZKA_BAZY = _SciezkaBazy()

# Nowe kolumny w tabeli treningi (nazwa -> typ w SQLite)
NOWE_KOLUMNY = {
    "Nazwa_cwiczenia": "TEXT",
    "Ciezar": "REAL",
    "Serie": "INTEGER",
    "Powtorzenia": "INTEGER",
}

# Dodatkowe dane dzienne z Garmina (nazwa kolumny -> typ w SQLite); sen w minutach
NOWE_KOLUMNY_GARMIN = {
    "Kroki": "INTEGER",
    "Cel_krokow": "INTEGER",
    "Kcal_aktywne": "INTEGER",
    "Kcal_spoczynkowe": "INTEGER",
    "Stres": "INTEGER",
    "Sen_gleboki": "INTEGER",
    "Sen_rem": "INTEGER",
    "Sen_lekki": "INTEGER",
    "Sen_czuwanie": "INTEGER",
}

# NOWE: rodzaje treningu siłowego (lista startowa, później dojdą kolejne w bazie)
TYPY_TRENINGU = ["Dół Siła", "Góra Full", "Góra 50/50", "Dół Asymetria"]

# NOWE: startowa baza ćwiczeń: (nazwa, partia). Ćwiczenia na górę dopiszemy później.
CWICZENIA_STARTOWE = [
    # Twoje ćwiczenia na dół
    ("Przysiad ze sztangą", "Nogi"),
    ("RDL (rumuński martwy ciąg)", "Nogi"),
    ("Wyciskanie na suwnicy na jedną nogę", "Nogi"),
    ("Wspięcia na palce stojąc", "Nogi"),
    ("Przysiad bułgarski", "Nogi"),
    ("Uginanie nóg na maszynie", "Nogi"),
    ("Spacer farmera jednorącz", "Nogi"),
    # Dodatkowe ćwiczenia na dół, żeby było z czego wybierać
    ("Przysiad przedni", "Nogi"),
    ("Przysiad kielichowy (goblet)", "Nogi"),
    ("Wypychanie na suwnicy (obunóż)", "Nogi"),
    ("Martwy ciąg", "Nogi"),
    ("Martwy ciąg na prostych nogach", "Nogi"),
    ("Hip thrust", "Nogi"),
    ("Hip thrust na jednej nodze", "Nogi"),
    ("Wykroki chodzone", "Nogi"),
    ("Wykroki w miejscu", "Nogi"),
    ("Wykroki w tył", "Nogi"),
    ("Wejścia na podwyższenie (step-up)", "Nogi"),
    ("Prostowanie nóg na maszynie", "Nogi"),
    ("Uginanie nóg leżąc", "Nogi"),
    ("Wspięcia na palce siedząc", "Nogi"),
    ("Przysiad na jednej nodze na skrzynię", "Nogi"),
    ("Good morning", "Nogi"),
    ("Przywodziciele na maszynie", "Nogi"),
    ("Odwodziciele na maszynie", "Nogi"),
    # Klasyczne ćwiczenia (dopisane 15.10): górna część ciała, brzuch, cardio
    ("Wyciskanie hantli na ławce płaskiej", "Klatka"),
    ("Wyciskanie sztangi na ławce skośnej dodatniej", "Klatka"),
    ("Wyciskanie na maszynie (klatka)", "Klatka"),
    ("Rozpiętki z hantlami", "Klatka"),
    ("Pompki", "Klatka"),
    ("Podciąganie podchwytem", "Plecy"),
    ("Wiosłowanie na maszynie", "Plecy"),
    ("Wiszenie na drążku", "Plecy"),
    ("Wyciskanie na maszynie (barki)", "Barki"),
    ("Wznosy ramion w opadzie z hantlami", "Barki"),
    ("Uginanie ramion ze sztangą stojąc", "Biceps"),
    ("Uginanie ramion z hantlami", "Biceps"),
    ("Wyciskanie sztangi wąskim chwytem", "Triceps"),
    ("Prostowanie ramion z hantlą zza głowy", "Triceps"),
    ("Dipy na poręczach", "Triceps"),
    ("Plank boczny", "Brzuch"),
    ("Unoszenie nóg w zwisie", "Brzuch"),
    ("Martwy robak (dead bug)", "Brzuch"),
    ("Skręty rosyjskie (russian twist)", "Brzuch"),
    ("Kettlebell swing", "Cały"),
    ("Bieganie na bieżni", "Cardio"),
    ("Bieg na zewnątrz", "Cardio"),
    ("Marsz pod górę na bieżni", "Cardio"),
    ("Rower stacjonarny", "Cardio"),
    ("Orbitrek", "Cardio"),
    ("Skakanka", "Cardio"),
    ("Pływanie", "Cardio"),
]

def utworz_tabele(db: sqlite3.Connection) -> None:
    """Tworzy tabele (jeśli nie istnieją) w aktualnej strukturze."""
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS treningi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Data TEXT NOT NULL,
            Wynik_snu INTEGER,
            Czas_snu INTEGER,          -- w minutach
            RHR INTEGER,
            Waga REAL,
            Rodzaj_treningu TEXT,
            Nazwa_cwiczenia TEXT,
            Ciezar REAL,
            Serie INTEGER,
            Powtorzenia INTEGER,
            Komentarz TEXT
        )
        """
    )
    # Osobna tabela na dane z Garmina, jeden wiersz na dzień
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS garmin_dziennie (
            Data TEXT PRIMARY KEY,
            Wynik_snu INTEGER,
            Czas_snu INTEGER,          -- w minutach
            RHR INTEGER,
            HRV INTEGER
        )
        """
    )
        # Dokładamy nowe kolumny do istniejącej tabeli (stare dane zostają)
    istniejace = {w[1] for w in db.execute("PRAGMA table_info(garmin_dziennie)")}
    for nazwa, typ in NOWE_KOLUMNY_GARMIN.items():
        if nazwa not in istniejace:
            db.execute(f"ALTER TABLE garmin_dziennie ADD COLUMN {nazwa} {typ}")
    db.commit()


def migruj_tabele(db: sqlite3.Connection) -> None:
    """Dodaje brakujące kolumny do starej tabeli, nie ruszając istniejących danych."""
    istniejace = {wiersz[1] for wiersz in db.execute("PRAGMA table_info(treningi)")}
    for nazwa, typ in NOWE_KOLUMNY.items():
        if nazwa not in istniejace:
            db.execute(f"ALTER TABLE treningi ADD COLUMN {nazwa} {typ}")
    db.commit()

def utworz_nowe_tabele(db: sqlite3.Connection) -> None:
    """NOWE: tworzy tabele na treningi z wieloma ćwiczeniami i wypełnia listy startowe."""
    # Rodzaje treningu (Kolejnosc ustala kolejność na liście rozwijanej)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS typy_treningu (
            Nazwa TEXT PRIMARY KEY,
            Kolejnosc INTEGER
        )
        """
    )
    # Baza ćwiczeń: nazwa jest unikalna, więc nie da się dodać dwa razy tego samego
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS cwiczenia (
            Nazwa TEXT PRIMARY KEY,
            Partia TEXT
        )
        """
    )
    # Jeden trening (sesja): data, rodzaj, waga ciała i komentarz do całości
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS sesje (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Data TEXT NOT NULL,
            Typ_treningu TEXT,
            Waga REAL,
            Komentarz TEXT
        )
        """
    )
    # Ćwiczenia wykonane w treningu; Sesja_id wskazuje, do którego treningu należą
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS wpisy_cwiczen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Sesja_id INTEGER NOT NULL REFERENCES sesje(id),
            Kolejnosc INTEGER,
            Cwiczenie TEXT NOT NULL,
            Ciezar REAL,
            Serie INTEGER,
            Powtorzenia INTEGER,
            Komentarz TEXT
        )
        """
    )

    # INSERT OR IGNORE: wstawia tylko to, czego jeszcze nie ma, więc Twoje własne
    # dopiski zostają, a ponowne uruchomienie niczego nie dubluje
    for numer, nazwa in enumerate(TYPY_TRENINGU):
        db.execute(
            "INSERT OR IGNORE INTO typy_treningu (Nazwa, Kolejnosc) VALUES (?, ?)",
            (nazwa, numer),
        )
    for nazwa, partia in CWICZENIA_STARTOWE:
        db.execute(
            "INSERT OR IGNORE INTO cwiczenia (Nazwa, Partia) VALUES (?, ?)",
            (nazwa, partia),
        )
    db.commit()

def przygotuj_baze() -> str | None:
    """Przygotowuje bazę. Zwraca tekst komunikatu, jeśli trzeba było odtworzyć plik."""
    try:
        with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
            utworz_tabele(db)
            migruj_tabele(db)
            utworz_nowe_tabele(db)  # NOWE
        return None
    except sqlite3.Error:
        # W razie błędu zachowujemy stary plik jako kopię (nie kasujemy go!)
        znacznik = datetime.now().strftime("%Y%m%d_%H%M%S")
        kopia = SCIEZKA_BAZY.with_name(f"treningi_kopia_{znacznik}.db")
        SCIEZKA_BAZY.replace(kopia)
        with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
            utworz_tabele(db)
            utworz_nowe_tabele(db)  # NOWE
        return f"Nie udało się odczytać bazy, więc stworzyłem nową. Stary plik zapisałem jako {kopia.name}."


def zapisz_trening(
    dzien: str,
    dane_garmin: dict | None,
    waga: float,
    rodzaj: str,
    cwiczenie: str,
    ciezar: float,
    serie: int,
    powtorzenia: int,
    komentarz: str,
) -> None:
    """Dodaje jeden nowy wiersz do tabeli treningi."""
    garmin = dane_garmin or {}
    czas_snu_s = garmin.get("czas_snu")
    czas_snu_min = round(czas_snu_s / 60) if czas_snu_s is not None else None

    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        db.execute(
            """
            INSERT INTO treningi
                (Data, Wynik_snu, Czas_snu, RHR, Waga, Rodzaj_treningu,
                 Nazwa_cwiczenia, Ciezar, Serie, Powtorzenia, Komentarz)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dzien,
                garmin.get("wynik_snu"),
                czas_snu_min,
                garmin.get("rhr"),
                waga,
                rodzaj,
                cwiczenie,
                ciezar,
                serie,
                powtorzenia,
                komentarz,
            ),
        )
        db.commit()


def wczytaj_historie() -> pd.DataFrame:
    """Czyta wszystkie treningi z bazy (najnowsze na górze) jako tabelę pandas."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        dane = pd.read_sql_query(
            "SELECT * FROM treningi ORDER BY Data DESC, id DESC", db
        )

    # Kolumny w ładnej kolejności; bierzemy tylko te, które istnieją
    kolejnosc = [
        "Data", "Rodzaj_treningu", "Nazwa_cwiczenia", "Ciezar", "Serie",
        "Powtorzenia", "Waga", "Wynik_snu", "Czas_snu", "RHR", "Komentarz",
    ]
    # Stara kolumna z wynikiem tekstowym: pokazujemy ją tylko, jeśli są w niej stare wpisy
    if "Wynik_cwiczenia" in dane.columns and dane["Wynik_cwiczenia"].notna().any():
        kolejnosc.append("Wynik_cwiczenia")
    return dane[[k for k in kolejnosc if k in dane.columns]]


def _w_minutach(sekundy) -> int | None:
    return round(sekundy / 60) if sekundy is not None else None


def zapisz_dzien_garmin(dzien: str, dane: dict) -> None:
    """Zapisuje (lub aktualizuje) jeden dzień w tabeli garmin_dziennie."""
    wartosci = {
        "Wynik_snu": dane.get("wynik_snu"),
        "Czas_snu": _w_minutach(dane.get("czas_snu")),
        "RHR": dane.get("rhr"),
        "HRV": dane.get("hrv"),
        "Kroki": dane.get("kroki"),
        "Cel_krokow": dane.get("cel_krokow"),
        "Kcal_aktywne": dane.get("kcal_aktywne"),
        "Kcal_spoczynkowe": dane.get("kcal_spoczynkowe"),
        "Stres": dane.get("stres"),
        "Sen_gleboki": _w_minutach(dane.get("sen_gleboki")),
        "Sen_rem": _w_minutach(dane.get("sen_rem")),
        "Sen_lekki": _w_minutach(dane.get("sen_lekki")),
        "Sen_czuwanie": _w_minutach(dane.get("sen_czuwanie")),
    }
    kolumny = ", ".join(wartosci)
    znaki = ", ".join("?" for _ in wartosci)
    # COALESCE: jeśli nowa wartość jest pusta, zostaje stara (nie kasujemy danych)
    aktualizacja = ", ".join(f"{k} = COALESCE(excluded.{k}, {k})" for k in wartosci)

    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        db.execute(
            f"INSERT INTO garmin_dziennie (Data, {kolumny}) VALUES (?, {znaki}) "
            f"ON CONFLICT(Data) DO UPDATE SET {aktualizacja}",
            (dzien, *wartosci.values()),
        )
        db.commit()


def zapisane_dni_garmin() -> set[str]:
    """Zwraca zbiór dat, które mamy już zapisane z Garmina."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        wiersze = db.execute("SELECT Data FROM garmin_dziennie WHERE Kroki IS NOT NULL").fetchall()
    return {w[0] for w in wiersze}


def wczytaj_dane_garmin_do_wykresow() -> pd.DataFrame:
    """Dane do wykresów z Garmina (sen, RHR, HRV)."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        dane = pd.read_sql_query(
            "SELECT Data, Wynik_snu, RHR, HRV FROM garmin_dziennie ORDER BY Data",
            db,
        )
    dane["Data"] = pd.to_datetime(dane["Data"])
    return dane.set_index("Data")


def wczytaj_garmin_rozszerzone(dni: int = 14) -> pd.DataFrame:
    """Ostatnie dni z fazami snu i stresem (do kafelków na Start). Indeks: data."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        dane = pd.read_sql_query(
            "SELECT Data, Stres, Sen_gleboki, Sen_rem, Sen_lekki, Sen_czuwanie "
            "FROM garmin_dziennie ORDER BY Data DESC LIMIT ?",
            db,
            params=(dni,),
        )
    dane["Data"] = pd.to_datetime(dane["Data"])
    return dane.set_index("Data").sort_index()


def wczytaj_garmin_rozszerzone(dni: int = 14) -> pd.DataFrame:
    """Ostatnie dni z fazami snu i stresem (do kafelków na Start). Indeks: data."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        dane = pd.read_sql_query(
            "SELECT Data, Stres, Sen_gleboki, Sen_rem, Sen_lekki, Sen_czuwanie "
            "FROM garmin_dziennie ORDER BY Data DESC LIMIT ?",
            db,
            params=(dni,),
        )
    dane["Data"] = pd.to_datetime(dane["Data"])
    return dane.set_index("Data").sort_index()


def wczytaj_wage_do_wykresu() -> pd.DataFrame:
    """Dane do wykresu wagi: tylko z ręcznych wpisów w formularzu."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        dane = pd.read_sql_query(
            "SELECT Data, Waga FROM treningi WHERE Waga IS NOT NULL "
            "UNION ALL SELECT Data, Waga FROM sesje WHERE Waga IS NOT NULL",
            db,
        )
        if dane.empty:
            return dane

    dane["Data"] = pd.to_datetime(dane["Data"])
    # Kilka wpisów jednego dnia = średnia, żeby był jeden punkt na dzień
    return dane.groupby("Data").mean(numeric_only=True).sort_index()

def lista_typow_treningu() -> list[str]:
    """NOWE: zwraca rodzaje treningu z bazy, w ustalonej kolejności."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        wiersze = db.execute("SELECT Nazwa FROM typy_treningu ORDER BY Kolejnosc").fetchall()
    return [w[0] for w in wiersze]


def lista_cwiczen() -> list[str]:
    """NOWE: zwraca ćwiczenia z bazy (w kolejności dodawania, Twoje na górze)."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        wiersze = db.execute("SELECT Nazwa FROM cwiczenia ORDER BY rowid").fetchall()
    return [w[0] for w in wiersze]

def zapisz_sesje(
    dzien: str,
    typ: str,
    waga: float,
    komentarz: str,
    cwiczenia: list[dict],
) -> None:
    """NOWE: zapisuje jeden trening i wszystkie jego ćwiczenia naraz (w jednej transakcji)."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        kursor = db.execute(
            "INSERT INTO sesje (Data, Typ_treningu, Waga, Komentarz) VALUES (?, ?, ?, ?)",
            (dzien, typ, waga, komentarz),
        )
        sesja_id = kursor.lastrowid  # numer właśnie dodanego treningu

        for numer, c in enumerate(cwiczenia, start=1):
            db.execute(
                """
                INSERT INTO wpisy_cwiczen
                    (Sesja_id, Kolejnosc, Cwiczenie, Ciezar, Serie, Powtorzenia, Komentarz, Jednostka)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (sesja_id, numer, c["cwiczenie"], c["ciezar"], c["serie"], c["powtorzenia"], c["komentarz"],
                 c.get("jednostka") or "powt."),
            )
        db.commit()  # jeśli coś pójdzie źle wcześniej, nie zapisze się nic


def wczytaj_historie_sesji() -> pd.DataFrame:
    """NOWE: treningi z ćwiczeniami: jeden wiersz = jedno ćwiczenie (najnowsze na górze)."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        return pd.read_sql_query(
            """
            SELECT s.Data, s.Typ_treningu AS Trening, s.Waga,
                   w.Cwiczenie, w.Ciezar, w.Serie, w.Powtorzenia,
                   w.Komentarz AS Komentarz_cwiczenia,
                   s.Komentarz AS Komentarz_treningu
            FROM sesje s
            LEFT JOIN wpisy_cwiczen w ON w.Sesja_id = s.id
            ORDER BY s.Data DESC, s.id DESC, w.Kolejnosc
            """,
            db,
        )

def _utworz_tabele_samopoczucia(db: sqlite3.Connection) -> None:
    """Tworzy tabelę z wpisami o samopoczuciu, jeśli jeszcze jej nie ma."""
    db.execute(
        "CREATE TABLE IF NOT EXISTS samopoczucie ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "Zapisano TEXT NOT NULL, "
        "Tekst TEXT NOT NULL, "
        "Odpowiedz TEXT)"  # miejsce na przyszłą odpowiedź modelu AI
    )


def zapisz_samopoczucie(tekst: str) -> None:
    """Zapisuje wpis użytkownika razem z datą i godziną (czas lokalny)."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        _utworz_tabele_samopoczucia(db)
        db.execute(
            "INSERT INTO samopoczucie (Zapisano, Tekst) VALUES (datetime('now', 'localtime'), ?)",
            (tekst,),
        )
        db.commit()


def wczytaj_ostatnie_samopoczucie(ile: int = 5) -> pd.DataFrame:
    """Zwraca ostatnie wpisy (najnowszy pierwszy)."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        _utworz_tabele_samopoczucia(db)
        return pd.read_sql_query(
            "SELECT Zapisano, Tekst, Odpowiedz FROM samopoczucie ORDER BY id DESC LIMIT ?",
            db,
            params=(ile,),
        )