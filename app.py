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
    zapisz_samopoczucie,
    wczytaj_ostatnie_samopoczucie,
    wczytaj_historie,
    wczytaj_historie_sesji,
    wczytaj_wage_do_wykresu,
    zapisz_sesje,
)
from garmin import formatuj_czas, synchronizuj_garmin
from styl import naglowek, zastosuj_styl
from wykresy import MIN_DNI_DLA_PASMA, SEN_PASMO, pasmo_osobiste, rysuj_wykres
from karty import (
    karta_pierscien, karta_wartosc, kolor_snu, status_snu,
    kolor_czasu_snu, status_czasu_snu, naglowek_strony, format_czasu, ocena_wzgledem_pasma, oblicz_gotowosc, karta_tekst, siatka_kart
)
from karty_presety import widok_presetu_html
from presety import (wczytaj_presety_startowe, lista_presetow, wczytaj_cwiczenia_presetu,
                     zapisz_cwiczenia_presetu, JEDNOSTKI, ROLE, MAKS_GLOWNYCH)

# Wczytuje zmienne z pliku .env (email i hasło do Garmina)
load_dotenv()

NAZWA_APLIKACJI = "NextLvl Training"
st.set_page_config(
    page_title=NAZWA_APLIKACJI, page_icon="🏋️", layout="wide",
    initial_sidebar_state="expanded",
)
# Dodatkowy CSS: czcionka bezszeryfowa, zaokrąglone rogi i subtelne cienie
CSS_DODATKOWY = """
<style>
/* Czcionka systemowa bezszeryfowa; ikon Streamlita (Material) nie ruszamy */
.stApp, .stApp p, .stApp label, .stApp input, .stApp textarea,
.stApp button, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stSidebar"] * {
    font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
[data-testid="stIconMaterial"], .material-symbols-rounded {
    font-family: "Material Symbols Rounded" !important;
}

/* Nagłówek systemowy przezroczysty, treść przy samej górze */
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewBlockContainer"],
.stMain .block-container,
.block-container { padding-top: 0 !important; }

/* Logo w menu bocznym */
[data-testid="stLogo"],
[data-testid="stSidebarLogo"] { height: 2.2rem !important; max-width: 100% !important; }
[data-testid="stSidebarHeader"] { height: 5rem !important; }

/* Menu boczne */
[data-testid="stSidebar"] { border-right: 1px solid #CFC2A6; }

/* Kafelki metryk i formularze */
[data-testid="stMetric"], [data-testid="stForm"] {
    background: #F4ECDC;
    border: 2px solid #BFAE86;
    border-radius: 16px;
    box-shadow: 0 4px 14px rgba(60, 45, 20, 0.10);
}
[data-testid="stMetric"] { padding: 16px 18px; }
[data-testid="stExpander"] {
    border: 2px solid #BFAE86 !important;
    border-radius: 14px !important;
    overflow: hidden;
    background: #F4ECDC;
}
[data-testid="stAlert"] { border-radius: 12px; }
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #CFC2A6;
}
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 16px; }

/* Pola tekstowe */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div,
.stTextInput input, .stNumberInput input, .stTextArea textarea {
    border-radius: 12px !important;
    background: #F4ECDC !important;
}

/* Przyciski */
.stButton > button, [data-testid="stFormSubmitButton"] > button {
    border-radius: 12px;
    border: 2px solid #BFAE86;
    transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease;
}
/* Przycisk główny (ciemny) ma ciemną ramkę, żeby nie było jasnego obrysu */
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"] {
    border-color: #1B1B1A;
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
    border-color: #9C8A5E;
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(60, 45, 20, 0.18);
}

/* Poświata na kafelkach (kontenery z ramką), formularzach i panelach */
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stForm"],
[data-testid="stExpander"] {
    background: radial-gradient(ellipse at 50% 0%, #9A7B4A44 0%, transparent 72%), #F1E7D2;
    box-shadow: 0 6px 18px rgba(90, 65, 25, 0.14);
    border: 2px solid #BFAE86 !important;
}
/* Kafelki i bloki ćwiczeń wskazane po kluczu (najpewniejszy sposób w nowych wersjach Streamlita) */
[class*="st-key-kafelek_"], [class*="st-key-blok_cwiczenia_"] {
    background: radial-gradient(ellipse at 50% 0%, #9A7B4A44 0%, transparent 72%), #F1E7D2 !important;
    border: 2px solid #BFAE86 !important;
    border-radius: 16px !important;
    box-shadow: 0 6px 18px rgba(90, 65, 25, 0.14) !important;
}
/* Kontener w kontenerze nie ma własnej poświaty (żeby nie dublować) */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] {
    background: none !important;
    box-shadow: none !important;
    border: none !important;
}
</style>
"""
st.markdown(CSS_DODATKOWY, unsafe_allow_html=True)

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
    st.markdown(
        naglowek_strony("Start", f"Dziś: {date.today().strftime('%d.%m.%Y')}"),
        unsafe_allow_html=True,
    )
    # Zwykły napis zamiast czarnego spinnera; znika, gdy dane są gotowe
    info = st.empty()
    info.caption("⏳ Synchronizuję dane z Garmina... (przy limicie 429 może to potrwać do minuty)")
    dane_garmin, blad_garmin = pobierz_dane_garmin()
    info.empty()
    st.subheader("Jak się dziś masz?")

        # Pole na odpis o samopoczuciu; Enter wysyła formularz
    with st.form("form_samopoczucie", clear_on_submit=True):
        kol_pole, kol_przycisk = st.columns([5, 1])
        wpis = kol_pole.text_input(
            "Samopoczucie",
            placeholder="Napisz, jak się czujesz (np. bolą plecy, mało snu, dużo energii)...",
            label_visibility="collapsed",
        )
        wyslano = kol_przycisk.form_submit_button("Zapisz", use_container_width=True)

    if wyslano:
        if wpis.strip():
            zapisz_samopoczucie(wpis.strip())
            st.success("Zapisane.")
        else:
            st.warning("Najpierw wpisz kilka słów.")

    # Informacja, jeśli baza musiała zostać odtworzona
    if komunikat_bazy:
        st.warning(komunikat_bazy)

    # Błędy Garmina pokazujemy tutaj
    if blad_garmin is not None:
        if blad_garmin[0] == "warning":
            st.warning(blad_garmin[1])
        else:
            st.error(blad_garmin[1])

    # Cztery karty z pierścieniami i wartościami: wynik snu, czas snu, RHR i HRV
    if dane_garmin is not None:
        wynik_snu = dane_garmin["wynik_snu"]
        czas_sekundy = dane_garmin["czas_snu"]
        czas_snu_min = czas_sekundy / 60 if czas_sekundy is not None else None
        rhr = dane_garmin["rhr"]
        hrv = dane_garmin["hrv"]

        # Historia z bazy: normę liczymy z całej historii, na wykresie pokazujemy 14 ostatnich dni
        historia = wczytaj_dane_garmin_do_wykresow()
        pasmo_rhr = pasmo_osobiste(historia["RHR"])
        pasmo_hrv = pasmo_osobiste(historia["HRV"])
        seria_rhr = historia["RHR"].dropna().tail(14).tolist()
        seria_hrv = historia["HRV"].dropna().tail(14).tolist()
        kolor_rhr, status_rhr = ocena_wzgledem_pasma(rhr, pasmo_rhr, wyzsze_lepiej=False)
        kolor_hrv, status_hrv = ocena_wzgledem_pasma(hrv, pasmo_hrv, wyzsze_lepiej=True)

        # Gotowość do treningu: średnia RHR z bazy (bez dzisiejszego dnia)
        rhr_hist = historia["RHR"].dropna()
        rhr_hist = rhr_hist[rhr_hist.index.date != date.today()]
        srednia_rhr = float(rhr_hist.mean()) if len(rhr_hist) >= 3 else None
        gotowosc = oblicz_gotowosc(czas_snu_min, rhr, srednia_rhr)
        procent = gotowosc["procent"]

                # Karty w jednej siatce: jednakowe odstępy w poziomie i w pionie
        st.markdown(
            siatka_kart([
                karta_pierscien("Wynik snu", wynik_snu, 100, kolor_snu(wynik_snu), status_snu(wynik_snu)),
                karta_pierscien(
                    "Czas snu", czas_snu_min, 480,
                    kolor_czasu_snu(czas_snu_min), status_czasu_snu(czas_snu_min), "cel: 8h",
                    tekst_srodka=format_czasu(czas_snu_min) if czas_snu_min is not None else None,
                ),
                karta_wartosc("Tętno spoczynkowe", rhr, "bpm", kolor_rhr, status_rhr, seria_rhr, pasmo_rhr),
                karta_wartosc("HRV", hrv, "ms", kolor_hrv, status_hrv, seria_hrv, pasmo_hrv),
                karta_pierscien(
                    "Gotowość do treningu", procent, 100, gotowosc["kolor"],
                    gotowosc["status"], gotowosc["podpis"],
                    tekst_srodka=f"{procent}%" if procent is not None else None,
                ),
            ]),
            unsafe_allow_html=True,
        )
# ---------------------------------------------------------------
# ZAKŁADKA 2: REGENERACJA (wszystkie wykresy)
# ---------------------------------------------------------------

def strona_regeneracja():
    st.markdown(naglowek_strony("Regeneracja"), unsafe_allow_html=True)
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
# WIDOK: WŁASNY TRENING (formularz z bazą ćwiczeń)
# ---------------------------------------------------------------
def widok_wlasny_trening():
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
        with st.container(border=True, key=f"blok_cwiczenia_{i}"):
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
    st.button("Zapisz trening", type="primary", on_click=zapisz_z_formularza, use_container_width=True)

# ---------------------------------------------------------------
# ZAKŁADKA: HISTORIA I KALENDARZ
# ---------------------------------------------------------------

def strona_historia():
    st.markdown(naglowek_strony("Historia i Kalendarz"), unsafe_allow_html=True)
    st.subheader("Historia Treningów")

    historia_sesji = wczytaj_historie_sesji()

    if historia_sesji.empty:
        st.info("Brak zapisanych treningów. Dodaj pierwszy w zakładce Treningi.")
    else:
        st.dataframe(historia_sesji, use_container_width=True, hide_index=True)

    # Stare wpisy z wersji z jednym ćwiczeniem zostają w archiwum
    stare_wpisy = wczytaj_historie()
    if not stare_wpisy.empty:
        with st.expander("Archiwum: stare wpisy z poprzedniej wersji"):
            st.dataframe(stare_wpisy, use_container_width=True, hide_index=True)

    wpisy = wczytaj_ostatnie_samopoczucie(30)
    with st.expander(f"Samopoczucie: zapisane wpisy ({len(wpisy)})"):
        if wpisy.empty:
            st.caption("Brak wpisów. Dodasz je na stronie Start.")
        else:
            for _, wiersz in wpisy.iterrows():
                st.markdown(f"**{wiersz['Zapisano'][:16]}**: {wiersz['Tekst']}")
                if wiersz["Odpowiedz"]:
                    st.caption(f"Odpowiedź: {wiersz['Odpowiedz']}")


@st.dialog("Edytuj preset", width="large")
def okno_edycji_presetu(preset_id: int, nazwa: str):
    """Okno z edytorem ćwiczeń presetu (otwiera się po kliknięciu 'Edytuj preset')."""
    st.caption(f"{nazwa}: zmieniaj ćwiczenia, serie i powtórzenia, dodawaj lub usuwaj wiersze.")
    dane = wczytaj_cwiczenia_presetu(preset_id)
    edytowane = st.data_editor(
        dane,
        num_rows="dynamic",          # pozwala dodawać i usuwać wiersze
        use_container_width=True,
        hide_index=True,
        key=f"edytor_{preset_id}",
        column_config={
            "Cwiczenie": st.column_config.TextColumn("Ćwiczenie", required=True),
            "Rola": st.column_config.SelectboxColumn("Rola", options=ROLE, default="Główne"),
            "Serie": st.column_config.NumberColumn("Serie", min_value=1, step=1),
            "Powt_od": st.column_config.NumberColumn("Powt. od", min_value=1, step=1),
            "Powt_do": st.column_config.NumberColumn("Powt. do", min_value=1, step=1),
            "Jednostka": st.column_config.SelectboxColumn("Jednostka", options=JEDNOSTKI, default="powt."),
            "Alternatywa": st.column_config.TextColumn("Zamiennik"),
            "Wskazowka": st.column_config.TextColumn("Wskazówka"),
        },
    )
    glownych = int((edytowane["Rola"] == "Główne").sum())
    if glownych > MAKS_GLOWNYCH:
        st.warning(f"Masz {glownych} ćwiczeń głównych, zalecane maksimum to {MAKS_GLOWNYCH}. "
                   f"Resztę ustaw jako „Dodatek”.")
    if st.button("Zapisz zmiany", type="primary", use_container_width=True):
        zapisz_cwiczenia_presetu(preset_id, edytowane)
        st.rerun()   # zamyka okno i odświeża karty


def widok_presetow():
    wczytaj_presety_startowe()   # wczytuje rozpiskę tylko za pierwszym razem
    lista = lista_presetow()

    # Filtr kategorii (przyciski-pigułki); gdy nic nie zaznaczone, pokazujemy wszystko
    kategorie = ["Wszystkie"] + lista["Kategoria"].dropna().unique().tolist()
    kategoria = st.pills("Kategoria", kategorie, default="Wszystkie", label_visibility="collapsed")
    if kategoria and kategoria != "Wszystkie":
        lista = lista[lista["Kategoria"] == kategoria]

    wybrana_nazwa = st.selectbox("Preset", lista["Nazwa"].tolist())
    wiersz = lista[lista["Nazwa"] == wybrana_nazwa].iloc[0]
    preset_id = int(wiersz["id"])

    dane = wczytaj_cwiczenia_presetu(preset_id)
    st.markdown(
        widok_presetu_html(wiersz["Nazwa"], wiersz["Kategoria"], wiersz["Typ"], wiersz["Cel"] or "", dane),
        unsafe_allow_html=True,
    )
    if st.button("Edytuj preset", use_container_width=True):
        okno_edycji_presetu(preset_id, wiersz["Nazwa"])


def widok_asystenta():
    st.info("Trening od asystenta pojawi się tutaj. W przyszłości będzie dobierany do Twoich "
            "danych o śnie i regeneracji, a Ty zawsze zatwierdzasz propozycję.")


TRYBY_TRENINGU = {
    "wlasny": ("Własny trening", "Zapisz trening od zera: ćwiczenia, ciężary, serie.", widok_wlasny_trening),
    "presety": ("Presety", "Gotowe rozpiski, które możesz edytować.", widok_presetow),
    "asystent": ("Trening od asystenta", "Propozycja dopasowana do Ciebie. Wkrótce.", widok_asystenta),
}


def przelacz_tryb_treningu(klucz: str) -> None:
    """Klik w kafelek: otwiera go, a ponowny klik w ten sam zamyka (nic nie jest wybrane)."""
    if st.session_state.get("tryb_treningu") == klucz:
        st.session_state["tryb_treningu"] = None
    else:
        st.session_state["tryb_treningu"] = klucz


def strona_treningi():
    st.markdown(naglowek_strony("Treningi"), unsafe_allow_html=True)    
    st.session_state.setdefault("tryb_treningu", None)   # na starcie nic nie jest wybrane
    aktywny = st.session_state["tryb_treningu"]

    kolumny = st.columns(len(TRYBY_TRENINGU))
    for kol, (klucz, (tytul, opis, _)) in zip(kolumny, TRYBY_TRENINGU.items()):
        with kol.container(border=True, height=280, key=f"kafelek_{klucz}"):
            # tekst w osobnym pojemniku o stałej wysokości, dzięki temu przyciski są na jednej linii
            with st.container(border=False, height=160):
                st.subheader(tytul)
                st.caption(opis)

            # przycisk jest w kafelku (to samo wcięcie co "with st.container" wyżej)
            wybrany = aktywny == klucz
            st.button(
                "Zamknij" if wybrany else "Otwórz",
                key=f"btn_{klucz}",
                type="primary" if wybrany else "secondary",
                on_click=przelacz_tryb_treningu, args=(klucz,),
                use_container_width=True,
            )

    if aktywny is None:
        st.caption("Wybierz jedną z opcji powyżej.")
    else:
        st.divider()
        TRYBY_TRENINGU[aktywny][2]()


# MENU BOCZNE
# ---------------------------------------------------------------
# Lista stron: funkcja, nazwa w menu i ikona (Material Symbols)
strony = [
    st.Page(strona_start, title="Start", icon=":material/home:", default=True),
    st.Page(strona_regeneracja, title="Regeneracja", icon=":material/bedtime:"),
    st.Page(strona_treningi, title="Treningi", icon=":material/fitness_center:"),
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