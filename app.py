from __future__ import annotations

import os
from datetime import date

from dotenv import load_dotenv
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

# Wczytuje zmienne z pliku .env do pamięci programu
load_dotenv()


def pobierz_dane_logowania() -> tuple[str, str]:
    """Czyta email i hasło ze zmiennych środowiskowych (z pliku .env)."""
    email = os.getenv("GARMIN_EMAIL")
    haslo = os.getenv("GARMIN_PASSWORD")

    # Jeśli czegoś brakuje, przerywamy z czytelnym komunikatem
    if not email or not haslo:
        raise ValueError(
            "Brak GARMIN_EMAIL lub GARMIN_PASSWORD w pliku .env"
        )
    return email, haslo


def formatuj_czas(sekundy: int | None) -> str:
    """Zamienia sekundy na tekst typu '7 h 24 min'."""
    if sekundy is None:
        return "brak danych"
    godziny, reszta = divmod(sekundy, 3600)
    minuty = reszta // 60
    return f"{godziny} h {minuty} min"


def main() -> None:
    dzisiaj = date.today().isoformat()  # format RRRR-MM-DD, którego chce Garmin

    try:
        # --- Logowanie ---
        email, haslo = pobierz_dane_logowania()
        garmin = Garmin(email, haslo)
        garmin.login()
        print("Zalogowano do Garmin Connect.\n")

        # --- Dane snu ---
        dane_snu = garmin.get_sleep_data(dzisiaj)
        # Dane są zagnieżdżone, więc używamy .get(), żeby brak klucza nie wywalił programu
        sen = dane_snu.get("dailySleepDTO") or {}
        czas_snu = sen.get("sleepTimeSeconds")
        wynik_snu = ((sen.get("sleepScores") or {}).get("overall") or {}).get("value")

        # --- Tętno spoczynkowe ---
        statystyki = garmin.get_stats(dzisiaj)
        rhr = statystyki.get("restingHeartRate")

        # --- Wypisanie wyników ---
        print(f"Dane z dnia: {dzisiaj}")
        print(f"Wynik snu (sleep score): {wynik_snu if wynik_snu is not None else 'brak danych'}")
        print(f"Czas snu: {formatuj_czas(czas_snu)}")
        print(f"Tętno spoczynkowe (RHR): {f'{rhr} bpm' if rhr is not None else 'brak danych'}")

    except ValueError as blad:
        # Problem z plikiem .env
        print(f"Błąd konfiguracji: {blad}")
    except GarminConnectAuthenticationError:
        # Zły email lub hasło
        print("Błąd logowania: sprawdź email i hasło w pliku .env.")
    except GarminConnectTooManyRequestsError:
        # Garmin chwilowo blokuje zbyt częste próby
        print("Garmin ogranicza liczbę zapytań. Odczekaj kilka minut i spróbuj ponownie.")
    except GarminConnectConnectionError as blad:
        # Brak internetu albo problem po stronie Garmina
        print(f"Błąd połączenia z Garmin Connect: {blad}")
    except Exception as blad:
        # Cokolwiek nieprzewidzianego
        print(f"Nieoczekiwany błąd: {blad}")


if __name__ == "__main__":
    main()