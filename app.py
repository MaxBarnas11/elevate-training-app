"""Interfejs aplikacji Training Buddy (zakładki, formularz)."""
from __future__ import annotations

from datetime import date

import streamlit as st
from dotenv import load_dotenv
from garminconnect import (
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

from baza import (
    przygotuj_baze,
    wczytaj_dane_garmin_do_wykresow,
    wczytaj_historie,
    wczytaj_wage_do_wykresu,
    zapisz_trening,
)
from garmin import formatuj_czas, synchronizuj_garmin
from wykresy import MIN_DNI_DLA_PASMA, SEN_PASMO, pasmo_osobiste, rysuj_wykres

# Wczytuje zmienne z pliku .env (email i hasło do Garmina)
load_dotenv()

NAZWA_APLIKACJI = "Training Buddy"
st.set_page_config(page_title=NAZWA_APLIKACJI, page_icon="🏐", layout="centered")

# Lista rodzajów treningu do rozwijanej listy
RODZAJE_TRENINGU = ["Dół 1", "Dół 2", "Góra 1", "Góra 2", "Siatkówka/Padel"]

# Początkowa baza ćwiczeń (na razie zwykła lista, później ją rozwiniemy)
BAZA_CWICZEN = [
    "Przysiad ze sztangą",
    "RDL",
    "Przysiad bułgarski",
    "Wyciskanie sztangi",
    "Podciąganie",
]

# Od ilu dni z wpisaną wagą pokazujemy wykres wagi
MIN_DNI_WAGI = 3

# Przygotowanie bazy; zwraca komunikat tylko, gdy plik musiał zostać odtworzony
komunikat_bazy = przygotuj_baze()

# ---------------------------------------------------------------
# NAGŁÓWEK
# ---------------------------------------------------------------
st.title(f"🏐 {NAZWA_APLIKACJI}")
dzisiaj = date.today().isoformat()  # format RRRR-MM-DD
st.caption(f"Dziś: {date.today().strftime('%d.%m.%Y')}")

# Synchronizację z Garminem robimy RAZ, przed zakładkami, bo dane
# są potrzebne zarówno na Pulpicie, jak i w formularzu treningu
dane_garmin: dict | None = None
blad_garmin: tuple[str, str] | None = None  # (rodzaj komunikatu, tekst)

try:
    dane_garmin = synchronizuj_garmin(dzisiaj)
except ValueError as blad:
    blad_garmin = ("error", f"Błąd konfiguracji: {blad}")
except GarminConnectAuthenticationError:
    blad_garmin = ("error", "Błąd logowania: sprawdź email i hasło w pliku .env.")
except GarminConnectTooManyRequestsError:
    blad_garmin = ("warning", "Garmin ogranicza liczbę zapytań. Odczekaj kilka minut i kliknij Odśwież.")
except GarminConnectConnectionError as blad:
    blad_garmin = ("error", f"Błąd połączenia z Garmin Connect: {blad}")
except Exception as blad:
    blad_garmin = ("error", f"Nieoczekiwany błąd: {blad}")

# ---------------------------------------------------------------
# NAWIGACJA: poziomy pasek zakładek na górze strony
# ---------------------------------------------------------------
zakladka_start, zakladka_regeneracja, zakladka_trening, zakladka_historia = st.tabs(
    ["Start (Pulpit)", "Regeneracja", "Trening", "Historia i Kalendarz"]
)

# ---------------------------------------------------------------
# ZAKŁADKA 1: START (PULPIT)
# ---------------------------------------------------------------
with zakladka_start:
    st.subheader("Jak się dziś masz?")

    # Informacja, jeśli baza musiała zostać odtworzona
    if komunikat_bazy:
        st.warning(komunikat_bazy)

    # Błędy Garmina pokazujemy tutaj
    if blad_garmin is not None:
        if blad_garmin[0] == "warning":
            st.warning(blad_garmin[1])
        else:
            st.error(blad_garmin[1])

    # Cztery kafelki z samymi liczbami
    if dane_garmin is not None:
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

    # on_click czyści cache jeszcze przed ponownym uruchomieniem skryptu,
    # więc synchronizacja na górze pliku pobierze świeże dane
    st.button("🔄 Odśwież dane z Garmina", on_click=st.cache_data.clear)

# ---------------------------------------------------------------
# ZAKŁADKA 2: REGENERACJA (wszystkie wykresy)
# ---------------------------------------------------------------
with zakladka_regeneracja:
    st.subheader("Regeneracja (dane z Garmina)")
    dane_garmin_wykresy = wczytaj_dane_garmin_do_wykresow()

    if len(dane_garmin_wykresy) < 2:
        st.info("Wykresy regeneracji pojawią się, gdy w bazie będą dane z co najmniej dwóch dni.")
    else:
        st.caption("Wynik snu (zielone pole: dobry i doskonały sen)")
        rysuj_wykres(dane_garmin_wykresy, "Wynik_snu", "Wynik snu", "punkty", pasmo=SEN_PASMO)

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
        rysuj_wykres(dane_wagi, "Waga", "Waga", "kg")

# ---------------------------------------------------------------
# ZAKŁADKA 3: TRENING (formularz z bazą ćwiczeń)
# ---------------------------------------------------------------
with zakladka_trening:
    st.subheader("Dodaj trening")

    # st.form zbiera pola i wysyła je dopiero po kliknięciu przycisku
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

        st.markdown("**Główne ćwiczenie**")
        cwiczenie = st.selectbox("Ćwiczenie", BAZA_CWICZEN)

        kol_ciezar, kol_serie, kol_powt = st.columns(3)
        ciezar = kol_ciezar.number_input(
            "Ciężar (kg)", min_value=0.0, max_value=500.0, value=60.0, step=2.5, format="%.1f"
        )
        serie = kol_serie.number_input("Serie", min_value=1, max_value=20, value=4, step=1)
        powtorzenia = kol_powt.number_input("Powtórzenia", min_value=1, max_value=100, value=5, step=1)

        komentarz = st.text_area(
            "Komentarz / samopoczucie / RPE",
            placeholder="Jak się czułeś? Ocena trudności (RPE 1-10)?",
            height=120,
        )

        zapisz = st.form_submit_button("💾 Zapisz Trening")

    # Ten blok wykona się po kliknięciu "Zapisz Trening"
    if zapisz:
        zapisz_trening(
            dzisiaj, dane_garmin, waga, rodzaj,
            cwiczenie, ciezar, int(serie), int(powtorzenia), komentarz,
        )
        st.success(
            f"**Trening zapisany w bazie!**\n\n"
            f"- **Data:** {date.today().strftime('%d.%m.%Y')}\n"
            f"- **Waga:** {waga:.1f} kg\n"
            f"- **Rodzaj treningu:** {rodzaj}\n"
            f"- **Ćwiczenie:** {cwiczenie}: {ciezar:g} kg x {int(powtorzenia)} powt. w {int(serie)} seriach\n"
            f"- **Komentarz / RPE:** {komentarz or '—'}"
        )
        if dane_garmin is None:
            st.warning("Dane z Garmina nie były dostępne, więc kolumny snu i RHR zostały puste.")

# ---------------------------------------------------------------
# ZAKŁADKA 4: HISTORIA I KALENDARZ
# ---------------------------------------------------------------
with zakladka_historia:
    st.subheader("Historia Treningów")

    historia = wczytaj_historie()

    if historia.empty:
        st.info("Brak zapisanych treningów. Dodaj pierwszy w zakładce Trening.")
    else:
        st.dataframe(historia, use_container_width=True, hide_index=True)