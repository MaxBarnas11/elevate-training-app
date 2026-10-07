"""Logowanie do Garmin Connect i pobieranie danych."""
from __future__ import annotations

import os
from datetime import date, timedelta

import streamlit as st
from garminconnect import Garmin

from baza import zapisane_dni_garmin, zapisz_dzien_garmin

# Ile dni wstecz uzupełniać z Garmina (gdy jeszcze ich nie mamy w bazie)
LICZBA_DNI_WSTECZ = 6


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
@st.cache_data(ttl=900, show_spinner=False)
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