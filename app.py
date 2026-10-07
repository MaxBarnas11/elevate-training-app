from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

# Wczytuje zmienne z pliku .env (email i hasło do Garmina)
load_dotenv()

# Ustawienia strony: tytuł karty w przeglądarce i układ
st.set_page_config(page_title="Mój Dziennik Treningowy", page_icon="🏐", layout="centered")

# Plik bazy leży obok app.py, niezależnie od tego, skąd uruchomisz aplikację
SCIEZKA_BAZY = Path(__file__).parent / "treningi.db"

# Lista rodzajów treningu do rozwijanej listy
RODZAJE_TRENINGU = ["Dół 1", "Dół 2", "Góra 1", "Góra 2", "Siatkówka/Padel"]


# ---------------------------------------------------------------
# BAZA DANYCH
# ---------------------------------------------------------------
def przygotuj_baze() -> None:
    """Tworzy plik treningi.db i tabelę, jeśli jeszcze nie istnieją."""
    # connect() samo utworzy plik, jeśli go nie ma
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
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
                Wynik_cwiczenia TEXT,
                Komentarz TEXT
            )
            """
        )
        db.commit()


def zapisz_trening(
    dzien: str,
    dane_garmin: dict | None,
    waga: float,
    rodzaj: str,
    wynik: str,
    komentarz: str,
) -> None:
    """Dodaje jeden nowy wiersz do tabeli treningi."""
    # Jeśli Garmin się nie połączył, w kolumnach z Garmina zapiszemy puste wartości (NULL)
    garmin = dane_garmin or {}
    czas_snu_s = garmin.get("czas_snu")
    czas_snu_min = round(czas_snu_s / 60) if czas_snu_s is not None else None

    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        # Znaki zapytania to bezpieczne "miejsca" na wartości (chronią przed błędami w tekście)
        db.execute(
            """
            INSERT INTO treningi
                (Data, Wynik_snu, Czas_snu, RHR, Waga, Rodzaj_treningu, Wynik_cwiczenia, Komentarz)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dzien,
                garmin.get("wynik_snu"),
                czas_snu_min,
                garmin.get("rhr"),
                waga,
                rodzaj,
                wynik,
                komentarz,
            ),
        )
        db.commit()


def wczytaj_historie() -> pd.DataFrame:
    """Czyta wszystkie treningi z bazy (najnowsze na górze) jako tabelę pandas."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        return pd.read_sql_query(
            "SELECT Data, Wynik_snu, Czas_snu, RHR, Waga, Rodzaj_treningu, "
            "Wynik_cwiczenia, Komentarz FROM treningi ORDER BY Data DESC, id DESC",
            db,
        )


# Uruchamiamy przy każdym starcie skryptu; jeśli baza już jest, nic się nie dzieje
przygotuj_baze()


# ---------------------------------------------------------------
# GARMIN
# ---------------------------------------------------------------
def formatuj_czas(sekundy: int | None) -> str:
    """Zamienia sekundy na tekst typu '7 h 24 min'."""
    if sekundy is None:
        return "brak danych"
    godziny, reszta = divmod(sekundy, 3600)
    return f"{godziny} h {reszta // 60} min"


# Cache: wynik jest zapamiętany na 15 minut, żeby nie logować się do Garmina przy każdym kliknięciu
@st.cache_data(ttl=900, show_spinner="Pobieram dane z Garmina...")
def pobierz_dane_garmin(dzien: str) -> dict:
    """Loguje się do Garmina i zwraca sen, czas snu oraz RHR dla danego dnia."""
    email = os.getenv("GARMIN_EMAIL")
    haslo = os.getenv("GARMIN_PASSWORD")
    if not email or not haslo:
        raise ValueError("Brak GARMIN_EMAIL lub GARMIN_PASSWORD w pliku .env")

    garmin = Garmin(email, haslo)
    garmin.login()

    dane_snu = garmin.get_sleep_data(dzien)
    sen = dane_snu.get("dailySleepDTO") or {}
    wynik_snu = ((sen.get("sleepScores") or {}).get("overall") or {}).get("value")
    statystyki = garmin.get_stats(dzien)

    return {
        "wynik_snu": wynik_snu,
        "czas_snu": sen.get("sleepTimeSeconds"),
        "rhr": statystyki.get("restingHeartRate"),
    }


# ---------------------------------------------------------------
# NAGŁÓWEK
# ---------------------------------------------------------------
st.title("🏐 Mój Dziennik Treningowy")
dzisiaj = date.today().isoformat()  # format RRRR-MM-DD
st.caption(f"Dziś: {date.today().strftime('%d.%m.%Y')}")

# ---------------------------------------------------------------
# SEKCJA 1: STATYSTYKI Z GARMINA
# ---------------------------------------------------------------
st.subheader("Dane z Garmina")

if st.button("🔄 Odśwież dane z Garmina"):
    st.cache_data.clear()

# Domyślnie brak danych; jeśli pobieranie się uda, podmienimy to na słownik z wynikami
dane_garmin: dict | None = None

try:
    dane_garmin = pobierz_dane_garmin(dzisiaj)

    kol_sen, kol_czas, kol_rhr = st.columns(3)
    kol_sen.metric(
        "Wynik snu",
        dane_garmin["wynik_snu"] if dane_garmin["wynik_snu"] is not None else "brak",
    )
    kol_czas.metric("Czas snu", formatuj_czas(dane_garmin["czas_snu"]))
    kol_rhr.metric(
        "Tętno spoczynkowe",
        f"{dane_garmin['rhr']} bpm" if dane_garmin["rhr"] is not None else "brak",
    )

except ValueError as blad:
    st.error(f"Błąd konfiguracji: {blad}")
except GarminConnectAuthenticationError:
    st.error("Błąd logowania: sprawdź email i hasło w pliku .env.")
except GarminConnectTooManyRequestsError:
    st.warning("Garmin ogranicza liczbę zapytań. Odczekaj kilka minut i kliknij Odśwież.")
except GarminConnectConnectionError as blad:
    st.error(f"Błąd połączenia z Garmin Connect: {blad}")
except Exception as blad:
    st.error(f"Nieoczekiwany błąd: {blad}")

st.divider()

# ---------------------------------------------------------------
# SEKCJA 2: FORMULARZ TRENINGOWY
# ---------------------------------------------------------------
st.subheader("Dodaj trening")

with st.form("formularz_treningu"):
    waga = st.number_input(
        "Dzisiejsza waga ciała (kg)",
        min_value=30.0,
        max_value=200.0,
        value=80.0,
        step=0.1,
        format="%.1f",
    )
    rodzaj = st.selectbox("Rodzaj treningu", RODZAJE_TRENINGU)
    wynik = st.text_input(
        "Wynik w głównym ćwiczeniu",
        placeholder="np. Przysiad 80 kg x 5 w 4 seriach",
    )
    komentarz = st.text_area(
        "Komentarz / samopoczucie / RPE",
        placeholder="Jak się czułeś? Ocena trudności (RPE 1-10)?",
        height=120,
    )

    zapisz = st.form_submit_button("💾 Zapisz Trening")

# Ten blok wykona się po kliknięciu "Zapisz Trening"
if zapisz:
    zapisz_trening(dzisiaj, dane_garmin, waga, rodzaj, wynik, komentarz)
    st.success(
        f"**Trening zapisany w bazie!**\n\n"
        f"- **Data:** {date.today().strftime('%d.%m.%Y')}\n"
        f"- **Waga:** {waga:.1f} kg\n"
        f"- **Rodzaj treningu:** {rodzaj}\n"
        f"- **Główne ćwiczenie:** {wynik or '—'}\n"
        f"- **Komentarz / RPE:** {komentarz or '—'}"
    )
    # Uwaga, jeśli zapis poszedł bez danych z Garmina
    if dane_garmin is None:
        st.warning("Dane z Garmina nie były dostępne, więc kolumny snu i RHR zostały puste.")

st.divider()

# ---------------------------------------------------------------
# SEKCJA 3: HISTORIA TRENINGÓW
# ---------------------------------------------------------------
st.header("Historia Treningów")

historia = wczytaj_historie()

if historia.empty:
    st.info("Brak zapisanych treningów. Dodaj pierwszy w formularzu powyżej.")
else:
    # Przewijalna tabela; hide_index ukrywa numerki wierszy
    st.dataframe(historia, use_container_width=True, hide_index=True)