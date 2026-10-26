"""Pierwsze logowanie nowej osoby: kilka krótkich kroków (wiek, zgody, sprzęt, cel) i proponowany plan tygodnia.

Wywołanie `wymagaj_onboardingu()` stoi w app.py po przygotowaniu bazy, przed nawigacją. Dla właściciela, dla pracy lokalnej bez
logowania i dla osób, które onboarding już przeszły, nic nie robi. Dla nowej osoby pokazuje kolejne kroki zamiast zwykłej aplikacji i
zatrzymuje skrypt, aż skończy (albo ją wyloguje). Osoby poniżej 16 lat nie wchodzą: nic o nich nie zapisujemy.

Logika (wiek, dobór planu) jest oddzielona od interfejsu, żeby dało się ją sprawdzać testami bez uruchamiania Streamlita.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import date

import baza
import plan as plan_tygodnia
import presety
import profil
import uzytkownik

WIEK_MINIMALNY = 16
ILE_KROKOW = 5
CEL_REDUKCJA = profil.CEL_REDUKCJA
CELE = profil.CELE
DNI_DO_WYBORU = (2, 3, 4, 5)
ODPOCZYNEK = "Odpoczynek"

# Które dni tygodnia (0 = poniedziałek) zajmuje trening przy danej liczbie dni: z przerwami na regenerację
UKLAD_DNI = {2: (1, 4), 3: (0, 2, 4), 4: (0, 1, 3, 4), 5: (0, 1, 3, 4, 5)}

# Kolejne treningi tygodnia dla celu (rodzaj presetu = pole Typ). Przy mniejszej liczbie dni bierzemy początek listy.
SZABLONY = {
    "Siła": ("Dół Siła", "Góra Siła", "Góra Pull", "Dół Asymetria", "Cardio"),
    "Masa mięśniowa": ("Góra Push", "Dół Siła", "Góra Pull", "Góra Hipertrofia", "Dół Asymetria"),
    CEL_REDUKCJA: ("Całe ciało", "Cardio", "Całe ciało", "Cardio", "Góra Hipertrofia"),
    "Kondycja i zdrowie": ("Całe ciało", "Cardio", "Całe ciało", "Cardio", "Plyo"),
}
DWA_DNI = {"Siła": ("Dół Siła", "Góra Siła")}      # reszta celów przy dwóch dniach: całe ciało dwa razy
PROG_SPRZETU = 0.7                                 # tyle ćwiczeń głównych musi pasować do Twojego sprzętu


# ---------------------------------------------------------------- logika

def wiek_wystarczajacy(data_ur: date | None, dzis: date | None = None) -> bool:
    w = profil.wiek(data_ur, dzis)
    return w is not None and w >= WIEK_MINIMALNY


def cele_dla(data_ur: date | None, dzis: date | None = None) -> list[str]:
    """Cele do wyboru: osobom poniżej 18 lat nie proponujemy redukcji tkanki tłuszczowej."""
    w = profil.wiek(data_ur, dzis)
    dorosly = w is not None and w >= profil.WIEK_DOROSLOSCI
    return [c for c in CELE if dorosly or c != CEL_REDUKCJA]


def wymagany() -> bool:
    """Czy bieżąca osoba musi najpierw przejść onboarding."""
    if not uzytkownik.logowanie_wymagane() or not uzytkownik.zalogowany() or uzytkownik.czy_wlasciciel():
        return False
    return not profil.wczytaj().get("onboarding")


def pasowanie_presetow(dozwolony: set[str] | None) -> list[dict]:
    """Presety z oceną, jaka część ćwiczeń głównych pasuje do sprzętu (1.0 = wszystko, gdy sprzęt nie ogranicza)."""
    with closing(sqlite3.connect(baza.SCIEZKA_BAZY)) as db:
        presety._utworz_tabele(db)
        wiersze = db.execute(
            "SELECT p.Nazwa, p.Typ, p.Kategoria, p.Kolejnosc, COALESCE(c.Sprzet, ''), pc.Rola "
            "FROM presety p LEFT JOIN presety_cwiczenia pc ON pc.Preset_id = p.id "
            "LEFT JOIN cwiczenia c ON c.Nazwa = pc.Cwiczenie ORDER BY p.Kolejnosc, p.id").fetchall()
    zebrane: dict[str, dict] = {}
    for nazwa, typ, kategoria, kolejnosc, sprzet, rola in wiersze:
        p = zebrane.setdefault(nazwa, {"nazwa": nazwa, "typ": typ or "", "kategoria": kategoria or "", "kolejnosc": kolejnosc,
                                       "ile": 0, "pasuje": 0})
        if rola is None or rola != "Główne":
            continue
        p["ile"] += 1
        if dozwolony is None or sprzet in dozwolony:
            p["pasuje"] += 1
    for p in zebrane.values():
        p["ocena"] = p["pasuje"] / p["ile"] if p["ile"] else 0.0
        if p["kategoria"] == "Cardio" and dozwolony is not None and "Maszyna cardio" not in dozwolony:
            p["ocena"] = 0.0     # cardio z presetów to rower, wioślarz i schody: bez maszyn cardio ich nie zrobisz
    return list(zebrane.values())


def _kandydaci(slot: str, lista: list[dict], uzyte: set[str]) -> list[dict]:
    if slot == "Całe ciało":
        zgodne = [p for p in lista if p["kategoria"] == "Całe ciało"]
    else:
        zgodne = [p for p in lista if p["typ"] == slot]
    return [p for p in zgodne if p["nazwa"] not in uzyte and "awaryjna" not in p["nazwa"]]


def _najlepszy(kandydaci: list[dict]) -> dict | None:
    dobre = [p for p in kandydaci if p["ocena"] >= PROG_SPRZETU]
    return max(dobre, key=lambda p: (p["ocena"], -p["kolejnosc"])) if dobre else None


def zaproponuj_plan(cel: str, dni: int, lista: list[dict]) -> list[dict]:
    """Plan na 7 dni (format zapisz_plan). Dla każdego treningu bierze preset pasujący do sprzętu; gdy żaden nie pasuje, całe ciało
    (albo cokolwiek, co najlepiej pasuje, poza presetami sportowymi). Dni bez treningu to odpoczynek."""
    dni = dni if dni in UKLAD_DNI else 3
    sloty = DWA_DNI.get(cel, ("Całe ciało", "Całe ciało")) if dni == 2 else SZABLONY.get(cel, SZABLONY["Kondycja i zdrowie"])[:dni]
    bez_sportu = [p for p in lista if p["kategoria"] not in presety_sportowe()]
    uzyte: set[str] = set()
    wybrane: list[str] = []
    for slot in sloty:
        p = _najlepszy(_kandydaci(slot, bez_sportu, uzyte)) or _najlepszy(_kandydaci("Całe ciało", bez_sportu, uzyte))
        if p is None:   # nic nie pasuje do sprzętu: bierzemy najlepiej dopasowany, który jeszcze nie jest w planie
            reszta = [x for x in bez_sportu if x["nazwa"] not in uzyte and x["ile"]]
            p = max(reszta, key=lambda x: (x["ocena"], -x["kolejnosc"])) if reszta else None
        if p is not None:
            uzyte.add(p["nazwa"])
            wybrane.append(p["nazwa"])
        else:
            wybrane.append("")
    dni_treningowe = dict(zip(UKLAD_DNI[dni], wybrane))
    return [{"Dzien": i, "Aktywny": bool(dni_treningowe.get(i)), "Typ": dni_treningowe.get(i, ""), "Godzina": "", "Notatka": ""}
            for i in range(7)]


def presety_sportowe() -> tuple[str, ...]:
    from presety_dane import SPORTY
    return tuple(SPORTY) + ("Sport",)


def zakoncz(cel: str | None, dni: int | None, plan: list[dict] | None) -> None:
    """Zapisuje wynik onboardingu. Plan zapisujemy tylko, gdy jest (pusty plan = nic nie nadpisujemy)."""
    if plan:
        plan_tygodnia.zapisz_plan(plan)
    profil.zapisz(cel=cel if cel in CELE else None, dni_w_tygodniu=dni if dni in DNI_DO_WYBORU else None,
                  onboarding=date.today().isoformat())


# ---------------------------------------------------------------- interfejs

def _naglowek(tytul: str, podtytul: str = "") -> None:
    import html
    import streamlit as st
    import logowanie
    try:
        from karty import naglowek_strony
        from styl import zastosuj_styl
        zastosuj_styl()
        st.markdown(logowanie.CSS_BEZ_MENU + "<style>.stApp [data-testid='stMainBlockContainer'] { padding-top: 3vh; }</style>",
                    unsafe_allow_html=True)
        st.markdown(naglowek_strony(html.escape(tytul), html.escape(podtytul)), unsafe_allow_html=True)
    except Exception:   # noqa: BLE001 (onboarding musi się pokazać nawet bez stylu)
        st.title(tytul)
        if podtytul:
            st.caption(podtytul)


def _idz(krok: int) -> None:
    import streamlit as st
    st.session_state["ob_krok"] = krok


def _pasek(krok: int) -> None:
    import streamlit as st
    st.progress(krok / ILE_KROKOW, text=f"Krok {krok} z {ILE_KROKOW}")


def _krok_dane() -> None:
    import streamlit as st
    s = st.session_state
    zapisane = profil.wczytaj()
    st.text_input("Imię", value=zapisane["imie"], max_chars=profil.MAKS_IMIE, key="ob_imie",
                  placeholder="Jak mamy się do Ciebie zwracać?")
    data_ur = profil.pole_daty("Data urodzenia", "ob_data_ur", zapisane["data_ur"],
                               help=f"Aplikacja jest dla osób od {WIEK_MINIMALNY} lat. Datę zapisujemy tylko po to, żeby dopasować aplikację do wieku.")
    imie = (s.get("ob_imie") or "").strip()
    if s.get("ob_za_mlody"):
        st.error(f"Ta aplikacja jest dla osób od {WIEK_MINIMALNY} lat, więc nie możemy Cię jeszcze wpuścić. Nic o Tobie nie zapisaliśmy. "
                 "Jeśli data jest błędna, popraw ją i kliknij Dalej.")
        st.button("Wyloguj", use_container_width=True, key="ob_wyloguj", on_click=uzytkownik.wyloguj)

    def dalej() -> None:
        d = profil.data_z_pol("ob_data_ur")
        if not wiek_wystarczajacy(d):
            st.session_state["ob_za_mlody"] = True
            return
        st.session_state["ob_za_mlody"] = False
        profil.zapisz(imie=st.session_state.get("ob_imie"), data_ur=d)
        _idz(2)

    st.button("Dalej", type="primary", use_container_width=True, key="ob_dalej_1", on_click=dalej,
              disabled=not imie or not isinstance(data_ur, date))


def _krok_zgody() -> None:
    import streamlit as st
    st.markdown("Zanim zaczniesz, dwie ważne rzeczy:")
    st.markdown("- Twoje treningi, waga, sen i notatki są tylko Twoje: widzisz je tylko Ty i administrator aplikacji.\n"
                "- W każdej chwili możesz pobrać swoje dane albo je usunąć (strona Profil, sekcja Dane i prywatność).")
    with st.expander("Informacja o prywatności"):
        st.markdown(profil.informacja_o_prywatnosci())
    with st.expander("Zasady korzystania"):
        st.markdown(profil.zasady_korzystania())
    byla_zgoda = bool(profil.wczytaj()["zgoda_zdrowie"])
    zdrowie = st.checkbox("Zgadzam się na zapisywanie moich danych o zdrowiu i treningach w tej aplikacji", value=byla_zgoda,
                          key="ob_zgoda_zdrowie",
                          help="Waga, sen, tętno i samopoczucie to dane o zdrowiu. Zgodę możesz cofnąć w każdej chwili w Profilu.")
    zasady = st.checkbox("Przeczytałem(-am) informację o prywatności i zasady korzystania", value=byla_zgoda, key="ob_zgoda_zasady")

    def dalej() -> None:
        profil.zapisz_zgode("zgoda_zdrowie", True)
        _idz(3)

    a, b = st.columns(2)
    a.button("Wstecz", use_container_width=True, key="ob_wstecz_2", on_click=_idz, args=(1,))
    b.button("Dalej", type="primary", use_container_width=True, key="ob_dalej_2", on_click=dalej, disabled=not (zdrowie and zasady))


def _ustaw_sprzet(lista: list[str]) -> None:
    import streamlit as st
    st.session_state["ob_sprzet"] = lista


def _krok_sprzet() -> None:
    import streamlit as st
    s = st.session_state
    opcje = profil.dostepny_sprzet()
    if "ob_sprzet" not in s:
        s["ob_sprzet"] = [x for x in profil.sprzet_wybrany() if x in opcje]
    else:
        s["ob_sprzet"] = [x for x in s["ob_sprzet"] if x in opcje]
    st.markdown("Z czego możesz korzystać na treningu? Dzięki temu proponujemy tylko ćwiczenia, które zrobisz.")
    st.multiselect("Sprzęt, który masz", opcje, key="ob_sprzet", placeholder="Wybierz rodzaje sprzętu...",
                   help="Nic nie zaznaczone znaczy: pokazuj wszystko. Masa ciała jest zawsze dostępna.")
    typowy = [x for x in profil.SPRZET_TYPOWY if x in opcje]
    tylko_cialo = [x for x in profil.SPRZET_ZAWSZE if x in opcje]
    a, b, c = st.columns(3)
    a.button("Typowa siłownia", use_container_width=True, key="ob_typowy", on_click=_ustaw_sprzet, args=(typowy,))
    b.button("Tylko ciało", use_container_width=True, key="ob_cialo", on_click=_ustaw_sprzet, args=(tylko_cialo,),
             help="Trening w domu, bez sprzętu.")
    c.button("Wyczyść", use_container_width=True, key="ob_czysc", on_click=_ustaw_sprzet, args=([],))

    def dalej() -> None:
        profil.zapisz_sprzet(list(st.session_state.get("ob_sprzet") or []))
        _idz(4)

    x, y = st.columns(2)
    x.button("Wstecz", use_container_width=True, key="ob_wstecz_3", on_click=_idz, args=(2,))
    y.button("Dalej", type="primary", use_container_width=True, key="ob_dalej_3", on_click=dalej)


def _krok_cel() -> None:
    import streamlit as st
    s = st.session_state
    cele = cele_dla(profil.wczytaj()["data_ur"])
    stan = s.get("ob_stan") or {}     # wybór zapamiętany poza widgetami: Streamlit kasuje stan widgetów, których nie ma na ekranie
    if s.get("ob_cel") not in cele:
        s["ob_cel"] = stan.get("cel") if stan.get("cel") in cele else cele[0]
    if s.get("ob_dni") not in DNI_DO_WYBORU:
        s["ob_dni"] = stan.get("dni") if stan.get("dni") in DNI_DO_WYBORU else 3
    st.radio("Jaki jest Twój główny cel?", cele, key="ob_cel")
    st.segmented_control("Ile dni w tygodniu chcesz trenować?", list(DNI_DO_WYBORU), key="ob_dni",
                         help="Zacznij od tylu dni, ile realnie dasz radę. Później zmienisz to w planie.")

    def dalej() -> None:
        dni = st.session_state.get("ob_dni") or 3
        st.session_state["ob_stan"] = {"cel": st.session_state.get("ob_cel"), "dni": dni}
        lista = pasowanie_presetow(profil.dozwolony_sprzet(profil.sprzet_wybrany()))
        propozycja = zaproponuj_plan(st.session_state["ob_stan"]["cel"], dni, lista)
        for d in propozycja:
            st.session_state[f"ob_plan_{d['Dzien']}"] = d["Typ"] or ODPOCZYNEK
        _idz(5)

    x, y = st.columns(2)
    x.button("Wstecz", use_container_width=True, key="ob_wstecz_4", on_click=_idz, args=(3,))
    y.button("Zaproponuj plan", type="primary", use_container_width=True, key="ob_dalej_4", on_click=dalej)


def _krok_plan() -> None:
    import streamlit as st
    s = st.session_state
    lista = presety.lista_presetow()
    opcje = [ODPOCZYNEK] + lista["Nazwa"].tolist()
    st.markdown("Tak mógłby wyglądać Twój tydzień. Zmień, co chcesz: zawsze możesz to poprawić później w zakładce Mój plan.")
    for i, nazwa in enumerate(plan_tygodnia.NAZWY_DNI):
        if s.get(f"ob_plan_{i}") not in opcje:
            s[f"ob_plan_{i}"] = ODPOCZYNEK
        st.selectbox(nazwa, opcje, key=f"ob_plan_{i}")

    def zatwierdz() -> None:
        dni = []
        for i in range(7):
            typ = st.session_state.get(f"ob_plan_{i}") or ODPOCZYNEK
            dni.append({"Dzien": i, "Aktywny": typ != ODPOCZYNEK, "Typ": "" if typ == ODPOCZYNEK else typ, "Godzina": "", "Notatka": ""})
        _koniec(dni)

    def pusty() -> None:
        _koniec(None)

    def _koniec(dni_planu: list[dict] | None) -> None:
        stan = st.session_state.get("ob_stan") or {}
        zakoncz(stan.get("cel"), stan.get("dni"), dni_planu)
        for k in [k for k in st.session_state if str(k).startswith("ob_")]:
            del st.session_state[k]
        st.toast("Gotowe, zaczynamy!")

    st.button("Zatwierdź plan i zacznij", type="primary", use_container_width=True, key="ob_zatwierdz", on_click=zatwierdz)
    a, b = st.columns(2)
    a.button("Wstecz", use_container_width=True, key="ob_wstecz_5", on_click=_idz, args=(4,))
    b.button("Zacznij bez planu", use_container_width=True, key="ob_pusty", on_click=pusty,
             help="Plan ułożysz sam w zakładce Mój plan.")


def widok() -> None:
    import streamlit as st
    s = st.session_state
    krok = int(s.get("ob_krok", 1))
    # Przygotowanie bazy, ćwiczeń i presetów (jednorazowo na nowe konto): potrzebne do listy sprzętu i planu
    import sesja_treningowa
    baza.przygotuj_baze()
    sesja_treningowa.przygotuj_tabele()
    presety.wczytaj_presety_startowe()
    imie = profil.pierwsze_imie()
    tytuly = {1: ("Witaj w STRUO", "Zacznijmy od kilku pytań"), 2: ("Prywatność", "Twoje dane, Twoja decyzja"),
              3: ("Twoja siłownia", "Sprzęt, który masz"), 4: ("Twój cel", "Po co trenujesz"),
              5: ("Twój plan", f"Propozycja dla {imie}" if imie else "Propozycja na start")}
    _naglowek(*tytuly.get(krok, tytuly[1]))
    _pasek(krok)
    {1: _krok_dane, 2: _krok_zgody, 3: _krok_sprzet, 4: _krok_cel, 5: _krok_plan}.get(krok, _krok_dane)()


def wymagaj_onboardingu() -> None:
    if not wymagany():
        return
    widok()
    import streamlit as st
    st.stop()
