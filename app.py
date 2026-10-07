"""Interfejs aplikacji Training Buddy (zakładki, formularz)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from garminconnect import (
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

from baza import (
    lista_cwiczen,
    lista_typow_treningu,
    przygotuj_baze,
    wczytaj_dane_garmin_do_wykresow,
    wczytaj_historie,
    wczytaj_historie_sesji,
    wczytaj_wage_do_wykresu,
    zapisz_sesje,
)
from garmin import formatuj_czas, synchronizuj_garmin
from styl import naglowek, zastosuj_styl
from wykresy import MIN_DNI_DLA_PASMA, SEN_PASMO, pasmo_osobiste, rysuj_wykres

# Wczytuje zmienne z pliku .env (email i hasło do Garmina)
load_dotenv()

NAZWA_APLIKACJI = "NextLvl Training"
st.set_page_config(
    page_title=NAZWA_APLIKACJI, page_icon="🏋️", layout="wide",
    initial_sidebar_state="expanded",
)
zastosuj_styl()
# Logo nad menu bocznym (plik logo.svg leży obok app.py)
st.logo(str(Path(__file__).parent / "logo.svg"), size="large")

# Od ilu dni z wpisaną wagą pokazujemy wykres wagi
MIN_DNI_WAGI = 3

# Przygotowanie bazy; zwraca komunikat tylko, gdy plik musiał zostać odtworzony
komunikat_bazy = przygotuj_baze()
# NOWE: rodzaje treningu i ćwiczenia czytamy z bazy, a nie z listy w kodzie
RODZAJE_TRENINGU = lista_typow_treningu()

BAZA_CWICZEN = lista_cwiczen()

# ---------------------------------------------------------------
# FORMULARZ TRENINGU: dodawanie ćwiczeń i zapis
# ---------------------------------------------------------------
# Każde pole ćwiczenia ma klucz z przedrostkiem i numerem, np. cw_0, ci_0, se_0...
PREFIKSY_POL = ("cw_", "ci_", "se_", "po_", "ko_")

# Na starcie pokazujemy jeden blok ćwiczenia
st.session_state.setdefault("liczba_cwiczen", 1)


def dodaj_cwiczenie() -> None:
    """Przycisk ➕: dokłada jeszcze jeden blok ćwiczenia."""
    st.session_state["liczba_cwiczen"] += 1


def usun_ostatnie_cwiczenie() -> None:
    """Przycisk ➖: usuwa ostatni blok (zawsze zostaje co najmniej jeden)."""
    ile = st.session_state["liczba_cwiczen"]
    if ile > 1:
        for przedrostek in PREFIKSY_POL:
            st.session_state.pop(f"{przedrostek}{ile - 1}", None)
        st.session_state["liczba_cwiczen"] = ile - 1


def zapisz_z_formularza() -> None:
    """Przycisk Zapisz: zbiera wpisane dane, zapisuje trening i czyści ćwiczenia."""
    s = st.session_state
    cwiczenia = []
    for i in range(s["liczba_cwiczen"]):
        if s.get(f"cw_{i}") is None:
            s["blad_zapisu"] = f"Wybierz ćwiczenie w bloku numer {i + 1} (albo usuń ten blok przyciskiem ➖)."
            return  # nic nie zapisujemy
        cwiczenia.append(
            {
                "cwiczenie": s[f"cw_{i}"],
                "ciezar": s[f"ci_{i}"],
                "serie": int(s[f"se_{i}"]),
                "powtorzenia": int(s[f"po_{i}"]),
                "komentarz": s.get(f"ko_{i}", ""),
            }
        )

    zapisz_sesje(
        s["data_treningu"].isoformat(),
        s["typ_treningu"],
        s["waga_ciala"],
        s.get("komentarz_treningu", ""),
        cwiczenia,
    )

    # Po zapisie czyścimy ćwiczenia i komentarz; data, rodzaj i waga zostają
    for klucz in list(s.keys()):
        if klucz.startswith(PREFIKSY_POL):
            del s[klucz]
    s["liczba_cwiczen"] = 1
    s["komentarz_treningu"] = ""
    s["komunikat_zapisu"] = f"Trening zapisany! Liczba ćwiczeń: {len(cwiczenia)}."

# ---------------------------------------------------------------
# NAGŁÓWEK
# ---------------------------------------------------------------

dzisiaj = date.today().isoformat()  # format RRRR-MM-DD

# Synchronizację z Garminem robimy RAZ, przed zakładkami, bo dane
# są potrzebne zarówno na Pulpicie, jak i w formularzu treningu
def pobierz_dane_garmin() -> tuple[dict | None, tuple[str, str] | None]:
    """Zwraca (dane, błąd). Wywoływana tylko na stronie Start, więc reszta aplikacji nie czeka."""
    try:
        return synchronizuj_garmin(dzisiaj), None
    except ValueError as blad:
        return None, ("error", f"Błąd konfiguracji: {blad}")
    except GarminConnectAuthenticationError:
        return None, ("error", "Błąd logowania: sprawdź email i hasło w pliku .env.")
    except GarminConnectTooManyRequestsError:
        return None, ("warning", "Garmin ogranicza liczbę zapytań. Odczekaj kilka minut i kliknij Odśwież.")
    except GarminConnectConnectionError as blad:
        return None, ("error", f"Błąd połączenia z Garmin Connect: {blad}")
    except Exception as blad:
        return None, ("error", f"Nieoczekiwany błąd: {blad}")

# ---------------------------------------------------------------
# NAWIGACJA: poziomy pasek zakładek na górze strony
# ---------------------------------------------------------------

# ---------------------------------------------------------------
# ZAKŁADKA 1: START (PULPIT)
# ---------------------------------------------------------------
def strona_start():
    st.title("Start")
    st.caption(f"Dziś: {date.today().strftime('%d.%m.%Y')}")
        # Zwykły napis zamiast czarnego spinnera; znika, gdy dane są gotowe
    info = st.empty()
    info.caption("⏳ Synchronizuję dane z Garmina... (przy limicie 429 może to potrwać do minuty)")
    dane_garmin, blad_garmin = pobierz_dane_garmin()
    info.empty()
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

# ---------------------------------------------------------------
# ZAKŁADKA 2: REGENERACJA (wszystkie wykresy)
# ---------------------------------------------------------------
def strona_regeneracja():
    st.title("Regeneracja")
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
def strona_trening():
    st.title("Trening")
    st.subheader("Dodaj trening")

    # Komunikaty po kliknięciu przycisku Zapisz
    if "komunikat_zapisu" in st.session_state:
        st.success(st.session_state.pop("komunikat_zapisu"))
    if "blad_zapisu" in st.session_state:
        st.error(st.session_state.pop("blad_zapisu"))

    # Górny rząd: data, rodzaj treningu i waga ciała
    kol_data, kol_typ, kol_waga = st.columns(3)
    kol_data.date_input("Data treningu", value=date.today(), key="data_treningu", format="DD.MM.YYYY")
    kol_typ.selectbox("Rodzaj treningu", RODZAJE_TRENINGU, key="typ_treningu")
    kol_waga.number_input(
        "Waga ciała (kg)", min_value=30.0, max_value=200.0, value=88.0,
        step=0.1, format="%.1f", key="waga_ciala",
    )

    # Jeden blok na każde ćwiczenie; liczba bloków rośnie po kliknięciu ➕
    for i in range(st.session_state["liczba_cwiczen"]):
        with st.container(border=True):
            st.markdown(f"**Ćwiczenie {i + 1}**")
            # index=None: lista startuje pusta, żeby przypadkiem nie zapisać pierwszego z listy
            st.selectbox(
                "Ćwiczenie", BAZA_CWICZEN, index=None,
                placeholder="Wybierz lub zacznij pisać nazwę...", key=f"cw_{i}",
            )
            kol_ciezar, kol_serie, kol_powt = st.columns(3)
            kol_ciezar.number_input(
                "Ciężar (kg)", min_value=0.0, max_value=500.0, value=60.0,
                step=2.5, format="%.1f", key=f"ci_{i}",
            )
            kol_serie.number_input("Serie", min_value=1, max_value=20, value=4, step=1, key=f"se_{i}")
            kol_powt.number_input("Powtórzenia", min_value=1, max_value=100, value=5, step=1, key=f"po_{i}")
            st.text_input(
                "Komentarz do ćwiczenia",
                placeholder="np. RPE 8, ostatnia seria ciężko",
                key=f"ko_{i}",
            )

    # Przyciski pod ćwiczeniami: dodaj / usuń ostatnie
    kol_plus, kol_minus = st.columns(2)
    kol_plus.button("➕ Dodaj ćwiczenie", on_click=dodaj_cwiczenie, use_container_width=True)
    kol_minus.button(
        "➖ Usuń ostatnie ćwiczenie", on_click=usun_ostatnie_cwiczenie,
        use_container_width=True, disabled=st.session_state["liczba_cwiczen"] <= 1,
    )

    # Komentarz do całego treningu i zapis
    st.text_area(
        "Komentarz do całego treningu",
        placeholder="Samopoczucie, ogólny RPE, uwagi...",
        height=100, key="komentarz_treningu",
    )
    st.button("💾 Zapisz trening", type="primary", on_click=zapisz_z_formularza, use_container_width=True)

# ---------------------------------------------------------------
# ZAKŁADKA 4: HISTORIA I KALENDARZ

def strona_historia():
    st.title("Historia i Kalendarz")
    st.subheader("Historia Treningów")

    historia_sesji = wczytaj_historie_sesji()

    if historia_sesji.empty:
        st.info("Brak zapisanych treningów. Dodaj pierwszy w zakładce Trening.")
    else:
        st.dataframe(historia_sesji, use_container_width=True, hide_index=True)

    # Stare wpisy z wersji z jednym ćwiczeniem zostają w archiwum
    stare_wpisy = wczytaj_historie()
    if not stare_wpisy.empty:
        with st.expander("Archiwum: stare wpisy z poprzedniej wersji"):
            st.dataframe(stare_wpisy, use_container_width=True, hide_index=True)

            # ---------------------------------------------------------------
# MENU BOCZNE
# ---------------------------------------------------------------
# Lista stron: funkcja, nazwa w menu i ikona (Material Symbols)
strony = [
    st.Page(strona_start, title="Start", icon=":material/home:", default=True),
    st.Page(strona_regeneracja, title="Regeneracja", icon=":material/bedtime:"),
    st.Page(strona_trening, title="Trening", icon=":material/fitness_center:"),
    st.Page(strona_historia, title="Historia i Kalendarz", icon=":material/calendar_month:"),
]
wybrana = st.navigation(strony)

# Dół menu: połączenie z Garminem i ustawienia (pojawia się pod listą stron)
with st.sidebar:
    st.divider()
    with st.expander("⚙️ Ustawienia i połączenie"):
        st.caption("Status połączenia widać na stronie Start.")
        st.button("🔄 Odśwież dane z Garmina", on_click=st.cache_data.clear, use_container_width=True)
        st.caption("Dane logowania do Garmina są w pliku .env na tym komputerze.")

# Uruchamia wybraną stronę. Musi być na końcu, po definicjach wszystkich funkcji.
wybrana.run()