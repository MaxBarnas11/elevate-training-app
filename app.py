from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

import altair as alt  # NOWE: biblioteka do wykresów (jest razem ze Streamlitem)
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

NAZWA_APLIKACJI = "Training Buddy"
st.set_page_config(page_title=NAZWA_APLIKACJI, page_icon="🏐", layout="centered")

# Plik bazy leży obok app.py, niezależnie od tego, skąd uruchomisz aplikację
SCIEZKA_BAZY = Path(__file__).parent / "treningi.db"

# Lista rodzajów treningu do rozwijanej listy
RODZAJE_TRENINGU = ["Dół 1", "Dół 2", "Góra 1", "Góra 2", "Siatkówka/Padel"]

# Ile dni wstecz uzupełniać z Garmina (gdy jeszcze ich nie mamy w bazie)
LICZBA_DNI_WSTECZ = 6

# Od ilu dni z wpisaną wagą pokazujemy wykres wagi
MIN_DNI_WAGI = 3

# NOWE: zielone pole na wykresie snu (dobry i doskonały sen wg skali Garmina)
SEN_PASMO = (80, 100)

# NOWE: od ilu dni danych liczymy Twój własny zakres dla HRV i RHR
MIN_DNI_DLA_PASMA = 5


# ---------------------------------------------------------------
# BAZA DANYCH
# ---------------------------------------------------------------
def przygotuj_baze() -> None:
    """Tworzy plik treningi.db i tabele, jeśli jeszcze nie istnieją."""
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
    garmin = dane_garmin or {}
    czas_snu_s = garmin.get("czas_snu")
    czas_snu_min = round(czas_snu_s / 60) if czas_snu_s is not None else None

    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
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


def zapisz_dzien_garmin(dzien: str, dane: dict) -> None:
    """Zapisuje (lub aktualizuje) jeden dzień w tabeli garmin_dziennie."""
    czas_s = dane.get("czas_snu")
    czas_min = round(czas_s / 60) if czas_s is not None else None

    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        # COALESCE: jeśli nowa wartość jest pusta, zostaje stara (nie kasujemy danych)
        db.execute(
            """
            INSERT INTO garmin_dziennie (Data, Wynik_snu, Czas_snu, RHR, HRV)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(Data) DO UPDATE SET
                Wynik_snu = COALESCE(excluded.Wynik_snu, Wynik_snu),
                Czas_snu  = COALESCE(excluded.Czas_snu, Czas_snu),
                RHR       = COALESCE(excluded.RHR, RHR),
                HRV       = COALESCE(excluded.HRV, HRV)
            """,
            (dzien, dane.get("wynik_snu"), czas_min, dane.get("rhr"), dane.get("hrv")),
        )
        db.commit()


def zapisane_dni_garmin() -> set[str]:
    """Zwraca zbiór dat, które mamy już zapisane z Garmina."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        wiersze = db.execute("SELECT Data FROM garmin_dziennie").fetchall()
    return {w[0] for w in wiersze}


def wczytaj_dane_garmin_do_wykresow() -> pd.DataFrame:
    """Dane do wykresów z Garmina (sen, RHR, HRV), bez udziału formularza."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        dane = pd.read_sql_query(
            "SELECT Data, Wynik_snu, RHR, HRV FROM garmin_dziennie ORDER BY Data",
            db,
        )
    dane["Data"] = pd.to_datetime(dane["Data"])
    return dane.set_index("Data")


def wczytaj_wage_do_wykresu() -> pd.DataFrame:
    """Dane do wykresu wagi: tylko z ręcznych wpisów w formularzu."""
    with closing(sqlite3.connect(SCIEZKA_BAZY)) as db:
        dane = pd.read_sql_query(
            "SELECT Data, Waga FROM treningi WHERE Waga IS NOT NULL",
            db,
        )
    if dane.empty:
        return dane
    dane["Data"] = pd.to_datetime(dane["Data"])
    # Kilka wpisów jednego dnia = średnia, żeby był jeden punkt na dzień
    return dane.groupby("Data").mean(numeric_only=True).sort_index()


# Uruchamiamy przy każdym starcie skryptu; jeśli baza już jest, nic się nie dzieje
przygotuj_baze()


# ---------------------------------------------------------------
# NOWE: WYKRESY (statyczne, bez zoomu)
# ---------------------------------------------------------------
def pasmo_osobiste(serie: pd.Series) -> tuple[float, float] | None:
    """Zwraca Twój własny zakres (średnia ± odchylenie standardowe) albo None, gdy za mało danych."""
    wartosci = serie.dropna()
    if len(wartosci) < MIN_DNI_DLA_PASMA:
        return None
    srednia = wartosci.mean()
    odchylenie = wartosci.std()
    return float(srednia - odchylenie), float(srednia + odchylenie)


def rysuj_wykres(
    dane: pd.DataFrame,
    kolumna: str,
    nazwa: str,
    jednostka: str,
    pasmo: tuple[float, float] | None = None,
) -> None:
    """Rysuje niewielki wykres liniowy z opcjonalnym zielonym polem (pasmo)."""
    # reset_index zamienia datę z indeksu na zwykłą kolumnę "Data"
    df = dane[[kolumna]].dropna().reset_index()

    # Linia z punktami. Brak .interactive(), więc scroll nie przybliża wykresu.
    linia = (
        alt.Chart(df)
        .mark_line(point=True, color="#4C9BE8")
        .encode(
            x=alt.X("Data:T", title=None, axis=alt.Axis(format="%d.%m", tickCount="day")),
            y=alt.Y(f"{kolumna}:Q", title=jednostka, scale=alt.Scale(zero=False)),
            tooltip=[
                alt.Tooltip("Data:T", title="Data", format="%d.%m.%Y"),
                alt.Tooltip(f"{kolumna}:Q", title=nazwa),
            ],
        )
    )

    warstwy = []
    if pasmo is not None:
        # Zielony prostokąt na całą szerokość wykresu, od dolnej do górnej granicy
        df_pasmo = pd.DataFrame({"dol": [pasmo[0]], "gora": [pasmo[1]]})
        zielone = (
            alt.Chart(df_pasmo)
            .mark_rect(color="#2ECC71", opacity=0.20)
            .encode(y=alt.Y("dol:Q", title=jednostka), y2="gora:Q")
        )
        warstwy.append(zielone)
    warstwy.append(linia)

    st.altair_chart(alt.layer(*warstwy).properties(height=220), use_container_width=True)


# ---------------------------------------------------------------
# GARMIN
# ---------------------------------------------------------------
def formatuj_czas(sekundy: int | None) -> str:
    """Zamienia sekundy na tekst typu '7 h 24 min'."""
    if sekundy is None:
        return "brak danych"
    godziny, reszta = divmod(sekundy, 3600)
    return f"{godziny} h {reszta // 60} min"


def pobierz_jeden_dzien(garmin: Garmin, dzien: str) -> dict:
    """Zwraca sen, czas snu, RHR i HRV dla jednego dnia."""
    dane_snu = garmin.get_sleep_data(dzien)
    sen = dane_snu.get("dailySleepDTO") or {}
    wynik_snu = ((sen.get("sleepScores") or {}).get("overall") or {}).get("value")
    statystyki = garmin.get_stats(dzien)

    # HRV: najpierw próbujemy z danych snu, a jeśli ich brak, z osobnego zapytania
    hrv = dane_snu.get("avgOvernightHrv")
    if hrv is None:
        try:
            dane_hrv = garmin.get_hrv_data(dzien) or {}
            hrv = (dane_hrv.get("hrvSummary") or {}).get("lastNightAvg")
        except Exception:
            hrv = None  # brak HRV nie może psuć reszty

    return {
        "wynik_snu": wynik_snu,
        "czas_snu": sen.get("sleepTimeSeconds"),
        "rhr": statystyki.get("restingHeartRate"),
        "hrv": round(hrv) if hrv is not None else None,
    }


# Cache na 15 min, więc kliknięcia w aplikacji nie męczą Garmina
@st.cache_data(ttl=900, show_spinner="Synchronizuję dane z Garmina...")
def synchronizuj_garmin(dzisiaj: str) -> dict:
    """Zwraca dzisiejsze dane z Garmina i uzupełnia bazę o brakujące dni."""
    email = os.getenv("GARMIN_EMAIL")
    haslo = os.getenv("GARMIN_PASSWORD")
    if not email or not haslo:
        raise ValueError("Brak GARMIN_EMAIL lub GARMIN_PASSWORD w pliku .env")

    garmin = Garmin(email, haslo)
    garmin.login()

    # Dzisiejszy dzień: błąd tutaj trafia do komunikatów w aplikacji
    dane_dzis = pobierz_jeden_dzien(garmin, dzisiaj)
    zapisz_dzien_garmin(dzisiaj, dane_dzis)

    # Brakujące dni z ostatnich LICZBA_DNI_WSTECZ dni (tylko te, których nie ma w bazie)
    dzis = date.fromisoformat(dzisiaj)
    mamy = zapisane_dni_garmin()
    for i in range(1, LICZBA_DNI_WSTECZ):
        dzien = (dzis - timedelta(days=i)).isoformat()
        if dzien in mamy:
            continue
        try:
            zapisz_dzien_garmin(dzien, pobierz_jeden_dzien(garmin, dzien))
        except Exception:
            continue  # jeden zły dzień nie psuje reszty; spróbujemy następnym razem

    return dane_dzis


# ---------------------------------------------------------------
# NAGŁÓWEK
# ---------------------------------------------------------------
st.title(f"🏐 {NAZWA_APLIKACJI}")
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
    dane_garmin = synchronizuj_garmin(dzisiaj)

    kol_sen, kol_czas, kol_rhr, kol_hrv = st.columns(4)
    kol_sen.metric(
        "Wynik snu",
        dane_garmin["wynik_snu"] if dane_garmin["wynik_snu"] is not None else "brak",
    )
    kol_czas.metric("Czas snu", formatuj_czas(dane_garmin["czas_snu"]))
    kol_rhr.metric(
        "RHR",
        f"{dane_garmin['rhr']} bpm" if dane_garmin["rhr"] is not None else "brak",
    )
    kol_hrv.metric(
        "HRV",
        f"{dane_garmin['hrv']} ms" if dane_garmin["hrv"] is not None else "brak",
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
    if dane_garmin is None:
        st.warning("Dane z Garmina nie były dostępne, więc kolumny snu i RHR zostały puste.")

st.divider()

# ---------------------------------------------------------------
# SEKCJA 3: MOJE POSTĘPY (WYKRESY)
# ---------------------------------------------------------------
st.header("Moje Postępy")

st.subheader("Regeneracja (dane z Garmina)")
dane_garmin_wykresy = wczytaj_dane_garmin_do_wykresow()

if len(dane_garmin_wykresy) < 2:
    st.info("Wykresy regeneracji pojawią się, gdy w bazie będą dane z co najmniej dwóch dni.")
else:
    # NOWE: wykres snu ze stałym zielonym polem
    st.caption("Wynik snu (zielone pole: dobry i doskonały sen)")
    rysuj_wykres(dane_garmin_wykresy, "Wynik_snu", "Wynik snu", "punkty", pasmo=SEN_PASMO)

    # NOWE: RHR z Twoim własnym zakresem
    st.caption("Tętno spoczynkowe, RHR (zielone pole: Twój zwykły zakres)")
    rysuj_wykres(
        dane_garmin_wykresy, "RHR", "RHR", "bpm",
        pasmo=pasmo_osobiste(dane_garmin_wykresy["RHR"]),
    )

    # HRV rysujemy tylko, jeśli Garmin w ogóle zwrócił jakiekolwiek wartości
    if dane_garmin_wykresy["HRV"].notna().any():
        st.caption("HRV (zielone pole: Twój zwykły zakres)")
        rysuj_wykres(
            dane_garmin_wykresy, "HRV", "HRV", "ms",
            pasmo=pasmo_osobiste(dane_garmin_wykresy["HRV"]),
        )
    else:
        st.info("Brak danych HRV z Garmina, więc wykres HRV się nie pokazuje.")

    # NOWE: wyjaśnienie, skąd bierze się zielone pole
    st.caption(
        f"Zielone pole dla RHR i HRV to Twoja średnia ± odchylenie standardowe "
        f"(pojawia się od {MIN_DNI_DLA_PASMA} dni danych). Dla RHR niżej zwykle znaczy lepiej."
    )

# Wykres wagi zależy od ręcznych wpisów
st.subheader("Waga ciała (kg)")
dane_wagi = wczytaj_wage_do_wykresu()

if len(dane_wagi) < MIN_DNI_WAGI:
    st.info(
        f"Wykres wagi pojawi się, gdy wpiszesz wagę w co najmniej {MIN_DNI_WAGI} różnych "
        f"dniach (na razie: {len(dane_wagi)})."
    )
else:
    # NOWE: statyczny wykres wagi (bez zielonego pola)
    rysuj_wykres(dane_wagi, "Waga", "Waga", "kg")

st.divider()

# ---------------------------------------------------------------
# SEKCJA 4: HISTORIA TRENINGÓW
# ---------------------------------------------------------------
st.header("Historia Treningów")

historia = wczytaj_historie()

if historia.empty:
    st.info("Brak zapisanych treningów. Dodaj pierwszy w formularzu powyżej.")
else:
    st.dataframe(historia, use_container_width=True, hide_index=True)