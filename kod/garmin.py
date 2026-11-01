"""Logowanie do Garmin Connect i pobieranie danych."""
from __future__ import annotations

import os
import time
from datetime import date, datetime, timedelta

import streamlit as st
from garminconnect import Garmin

import baza
import uzytkownik
from baza import zapisane_dni_garmin, zapisz_dzien_garmin
from garminconnect import GarminConnectConnectionError

# Zapamiętane tokeny logowania: po pierwszym udanym logowaniu hasło nie jest już wysyłane, tylko odświeżany token.
# Ciągłe logowanie hasłem (każde odświeżenie, każdy restart) kończy się blokadą Cloudflare po stronie Garmina.
SCIEZKA_TOKENOW = baza.SCIEZKA_BAZY.parent / ".garmin_tokeny" if baza.TRYB_GOSCIA else uzytkownik.FOLDER_APLIKACJI / ".garmin_tokeny"
# Po nieudanym logowaniu przez tyle minut nie próbujemy ponownie (kolejne próby tylko przedłużają blokadę)
PRZERWA_PO_BLEDZIE_MIN = 60
PLIK_BLOKADY = baza.SCIEZKA_BAZY.parent / ".garmin_blokada" if baza.TRYB_GOSCIA else uzytkownik.FOLDER_APLIKACJI / ".garmin_blokada"


def _sprawdz_blokade() -> None:
    """Zgłasza czytelny błąd, gdy ostatnie logowanie się nie udało i przerwa jeszcze trwa."""
    try:
        do = float(PLIK_BLOKADY.read_text().strip())
    except (OSError, ValueError):
        return
    if time.time() < do:
        godzina = datetime.fromtimestamp(do).strftime("%H:%M")
        raise GarminConnectConnectionError(
            f"logowanie jest wstrzymane do {godzina}, bo ostatnia próba została zablokowana (zabezpieczenie Cloudflare). "
            f"Kolejne próby tylko przedłużają blokadę. Dane z poprzednich dni są w bazie. "
            f"Żeby spróbować od razu, usuń plik .garmin_blokada w folderze aplikacji."
        )


def _ustaw_blokade() -> None:
    try:
        PLIK_BLOKADY.write_text(str(time.time() + PRZERWA_PO_BLEDZIE_MIN * 60))
    except OSError:
        pass


def _zdejmij_blokade() -> None:
    try:
        PLIK_BLOKADY.unlink()
    except OSError:
        pass

# Ile dni wstecz uzupełniać z Garmina (gdy jeszcze ich nie mamy w bazie)
LICZBA_DNI_WSTECZ = 14

# Ile brakujących dni dociągamy przy jednym odświeżeniu (żeby nie zasypać Garmina zapytaniami)
MAKS_DOCIAGNIEC_NA_RAZ = 5


def ostatnie_zapisane_dane() -> dict | None:
    """Ostatni dzień z danymi zapisany w bazie (gdy Garmin chwilowo nie odpowiada): {'data': 'RRRR-MM-DD', 'dane': {...}}.
    Klucze w 'dane' jak z pobierz_jeden_dzien, żeby interfejs mógł je pokazać bez zmian."""
    from contextlib import closing
    import sqlite3
    try:
        with closing(sqlite3.connect(baza.SCIEZKA_BAZY)) as db:
            w = db.execute(
                "SELECT Data, Wynik_snu, Czas_snu, RHR, HRV, Kroki, Cel_krokow, Kcal_aktywne, Kcal_spoczynkowe, Stres "
                "FROM garmin_dziennie WHERE Wynik_snu IS NOT NULL OR RHR IS NOT NULL ORDER BY Data DESC LIMIT 1"
            ).fetchone()
    except sqlite3.OperationalError:
        return None
    if not w:
        return None
    return {"data": w[0], "dane": {
        "wynik_snu": w[1], "czas_snu": w[2] * 60 if w[2] is not None else None, "rhr": w[3], "hrv": w[4],
        "kroki": w[5], "cel_krokow": w[6], "kcal_aktywne": w[7], "kcal_spoczynkowe": w[8], "stres": w[9],
    }}


def formatuj_czas(sekundy: int | None) -> str:
    """Zamienia sekundy na tekst typu '7 h 24 min'."""
    if sekundy is None:
        return "brak danych"
    godziny, reszta = divmod(sekundy, 3600)
    return f"{godziny} h {reszta // 60} min"


def _liczba(wartosc) -> int | None:
    return round(wartosc) if wartosc is not None else None


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

    stres = statystyki.get("averageStressLevel")
    if stres is not None and stres < 0:
        stres = None  # Garmin daje -1, gdy nie zmierzył stresu

    return {
        "wynik_snu": wynik_snu,
        "czas_snu": sen.get("sleepTimeSeconds"),
        "rhr": statystyki.get("restingHeartRate"),
        "hrv": round(hrv) if hrv is not None else None,
        "kroki": statystyki.get("totalSteps"),
        "cel_krokow": statystyki.get("dailyStepGoal"),
        "kcal_aktywne": _liczba(statystyki.get("activeKilocalories")),
        "kcal_spoczynkowe": _liczba(statystyki.get("bmrKilocalories")),
        "stres": round(stres) if stres is not None else None,
        # fazy snu w sekundach (do bazy trafiają w minutach)
        "sen_gleboki": sen.get("deepSleepSeconds"),
        "sen_rem": sen.get("remSleepSeconds"),
        "sen_lekki": sen.get("lightSleepSeconds"),
        "sen_czuwanie": sen.get("awakeSleepSeconds"),
    }


def synchronizuj_garmin(dzisiaj: str) -> dict:
    """Zwraca dzisiejsze dane z Garmina i uzupełnia bazę o brakujące dni (tylko dla właściciela).
    Sprawdzenie właściciela stoi POZA cache: trafienie w cache nie uruchamia ciała funkcji, więc kontrola w środku
    nie ochroniłaby danych właściciela przed innym zalogowanym."""
    if baza.TRYB_GOSCIA or not uzytkownik.czy_wlasciciel():   # dane logowania do Garmina z .env należą tylko do właściciela
        raise ValueError("Garmin jest dostępny tylko na koncie właściciela")
    return _synchronizuj_garmin_cache(dzisiaj)


# Cache na 15 min, więc kliknięcia w aplikacji nie męczą Garmina
@st.cache_data(ttl=900, show_spinner=False)
def _synchronizuj_garmin_cache(dzisiaj: str) -> dict:
    if baza.TRYB_GOSCIA or not uzytkownik.czy_wlasciciel():   # druga kontrola (pierwsza jest w synchronizuj_garmin)
        raise ValueError("Garmin jest dostępny tylko na koncie właściciela")
    email = os.getenv("GARMIN_EMAIL")
    haslo = os.getenv("GARMIN_PASSWORD")
    if not email or not haslo:
        raise ValueError("Brak GARMIN_EMAIL lub GARMIN_PASSWORD w pliku .env")

    _sprawdz_blokade()
    garmin = Garmin(email, haslo)
    try:
        garmin.login(str(SCIEZKA_TOKENOW))   # z zapamiętanych tokenów, a hasło tylko gdy ich nie ma
    except Exception:
        _ustaw_blokade()
        raise
    _zdejmij_blokade()

    # Dzisiejszy dzień: błąd tutaj trafia do komunikatów w aplikacji
    dane_dzis = pobierz_jeden_dzien(garmin, dzisiaj)
    zapisz_dzien_garmin(dzisiaj, dane_dzis)

    # Brakujące dni z ostatnich LICZBA_DNI_WSTECZ dni (tylko te, których nie ma w bazie)
    dzis = date.fromisoformat(dzisiaj)

    mamy = zapisane_dni_garmin()
    dociagniete = 0
    for i in range(1, LICZBA_DNI_WSTECZ):
        dzien = (dzis - timedelta(days=i)).isoformat()
        if dzien in mamy:
            continue
        if dociagniete >= MAKS_DOCIAGNIEC_NA_RAZ:
            break  # resztę uzupełnimy przy następnym odświeżeniu
        dociagniete += 1
        try:
            zapisz_dzien_garmin(dzien, pobierz_jeden_dzien(garmin, dzien))
        except Exception:
            continue

    return dane_dzis
