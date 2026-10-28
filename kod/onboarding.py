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
SILOWE_DO_WYBORU = (1, 2, 3, 4, 5)
CARDIO_DO_WYBORU = (0, 1, 2, 3)
DLUGOSCI = ("Pełne (ok. godziny)", "Krótkie (ok. 30 min)")
CARDIO_TRYBY = ("W osobne dni", "Na koniec treningu siłowego")
ODPOCZYNEK = "Odpoczynek"
MAKS_DNI = 6                                       # co najmniej jeden dzień w tygodniu bez treningu

# Domyślnie dla celu: (treningi siłowe, cardio w tygodniu)
DOMYSLNE = {"Siła": (4, 0), "Masa mięśniowa": (4, 0), CEL_REDUKCJA: (3, 2), "Kondycja i zdrowie": (3, 2)}

# Które dni tygodnia (0 = poniedziałek) zajmują treningi przy danej liczbie dni: z przerwami na regenerację
UKLAD_DNI = {1: (2,), 2: (1, 4), 3: (0, 2, 4), 4: (0, 1, 3, 4), 5: (0, 1, 3, 4, 5), 6: (0, 1, 2, 3, 4, 5)}

# Kolejne treningi siłowe tygodnia dla celu (rodzaj presetu = pole Typ). Przy mniejszej liczbie bierzemy początek listy.
# Pełne treningi to podział na dół i górę; krótkie (ok. 30 min) to całe ciało oraz skrócona góra i dół.
SZABLONY_PELNE = {
    "Siła": ("Dół Siła", "Góra Siła", "Góra Pull", "Dół Asymetria", "Góra Hipertrofia"),
    "Masa mięśniowa": ("Góra Push", "Dół Siła", "Góra Pull", "Góra Hipertrofia", "Dół Asymetria"),
    CEL_REDUKCJA: ("Dół Siła", "Góra Push", "Góra Pull", "Dół Asymetria", "Góra Hipertrofia"),
    "Kondycja i zdrowie": ("Dół Siła", "Góra Push", "Góra Pull", "Dół Asymetria", "Góra Hipertrofia"),
}
SZABLON_KROTKI = ("Całe ciało", "Góra Szybka", "Całe ciało", "Dół Szybki", "Całe ciało")
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
        if dozwolony is None or "*" in dozwolony or sprzet in dozwolony:
            p["pasuje"] += 1
    for p in zebrane.values():
        p["ocena"] = p["pasuje"] / p["ile"] if p["ile"] else 0.0
        if p["kategoria"] == "Cardio" and dozwolony is not None and not {"*", "Maszyna cardio"} & dozwolony:
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


def _notatka_cardio(maszyna_cardio: bool) -> str:
    return ("Na koniec: cardio 15-20 min (rower, bieżnia lub wioślarz)" if maszyna_cardio
            else "Na koniec: 15-20 min szybkiego marszu lub truchtu")


def zaproponuj_plan(cel: str, silowe: int, cardio: int, krotkie: bool, osobno: bool, lista: list[dict],
                    maszyna_cardio: bool = True) -> list[dict]:
    """Plan na 7 dni (format zapisz_plan). Treningi siłowe bierzemy z szablonu celu (pełne albo krótkie), każdy pasujący do sprzętu.
    Cardio trafia w osobne dni (presety cardio, a bez maszyn presety plyo) albo jako dopisek na końcu treningu siłowego.
    Co najmniej jeden dzień w tygodniu zostaje wolny; nadmiar cardio w osobne dni zamienia się w dopiski."""
    silowe = silowe if silowe in SILOWE_DO_WYBORU else 3
    cardio = cardio if cardio in CARDIO_DO_WYBORU else 0
    bez_sportu = [p for p in lista if p["kategoria"] not in presety_sportowe()]
    uzyte: set[str] = set()

    def wybierz(slot: str) -> str:
        p = _najlepszy(_kandydaci(slot, bez_sportu, uzyte)) or _najlepszy(_kandydaci("Całe ciało", bez_sportu, uzyte))
        if p is None:   # brakło nowych treningów pasujących do sprzętu: powtarzamy najlepszy trening na całe ciało (typowe w domu)
            p = _najlepszy(_kandydaci("Całe ciało", bez_sportu, set()))
        if p is None:   # nic nie pasuje do sprzętu: bierzemy najlepiej dopasowany, który jeszcze nie jest w planie
            reszta = [x for x in bez_sportu if x["nazwa"] not in uzyte and x["ile"] and x["kategoria"] != "Cardio"]
            p = max(reszta, key=lambda x: (x["ocena"], -x["kolejnosc"])) if reszta else None
        if p is None:
            return ""
        uzyte.add(p["nazwa"])
        return p["nazwa"]

    if krotkie:
        sloty = SZABLON_KROTKI[:silowe]
    elif silowe == 1:
        sloty = ("Całe ciało",)
    else:
        sloty = SZABLONY_PELNE.get(cel, SZABLONY_PELNE["Kondycja i zdrowie"])[:silowe]
    treningi = [{"Typ": wybierz(s), "Notatka": ""} for s in sloty]

    osobne_chciane = cardio if osobno else max(0, cardio - silowe)
    osobne: list[str] = []
    for _ in range(min(osobne_chciane, MAKS_DNI - silowe)):
        p = _najlepszy(_kandydaci("Cardio", bez_sportu, uzyte)) or _najlepszy(_kandydaci("Plyo", bez_sportu, uzyte))
        if p is None:
            break
        uzyte.add(p["nazwa"])
        osobne.append(p["nazwa"])
    dolacz = min(cardio - len(osobne), silowe)     # reszta (np. nie ma jak zmieścić) zamienia się w dopiski przy treningach
    for j in range(dolacz):
        treningi[int(j * silowe / dolacz)]["Notatka"] = _notatka_cardio(maszyna_cardio)

    # rozłożenie cardio w osobne dni równomiernie między treningami siłowymi
    razem = len(treningi) + len(osobne)
    uklad = UKLAD_DNI[min(max(razem, 1), MAKS_DNI)]
    kolejnosc: list[dict] = []
    s_idx = c_idx = 0
    for i in range(razem):
        if len(osobne) and int((i + 1) * len(osobne) / razem) > int(i * len(osobne) / razem):
            kolejnosc.append({"Typ": osobne[c_idx], "Notatka": ""})
            c_idx += 1
        else:
            kolejnosc.append(treningi[s_idx])
            s_idx += 1
    dni_treningowe = dict(zip(uklad, kolejnosc))
    return [{"Dzien": i, "Aktywny": bool(dni_treningowe.get(i, {}).get("Typ")), "Typ": dni_treningowe.get(i, {}).get("Typ", ""),
             "Godzina": "", "Notatka": dni_treningowe.get(i, {}).get("Notatka", "")} for i in range(7)]


def presety_sportowe() -> tuple[str, ...]:
    from presety_dane import SPORTY
    return tuple(SPORTY) + ("Sport",)


def zakoncz(cel: str | None, ustawienia: dict | None, plan: list[dict] | None) -> None:
    """Zapisuje wynik onboardingu. Plan zapisujemy tylko, gdy jest (pusty plan = nic nie nadpisujemy)."""
    ustawienia = ustawienia or {}
    if plan:
        plan_tygodnia.zapisz_plan(plan)
    silowe, cardio = ustawienia.get("silowe"), ustawienia.get("cardio")
    profil.zapisz(cel=cel if cel in CELE else None,
                  treningi_silowe=silowe if silowe in SILOWE_DO_WYBORU else None,
                  treningi_cardio=cardio if cardio in CARDIO_DO_WYBORU else None,
                  dlugosc_treningu=("krotkie" if ustawienia.get("krotkie") else "pelne") if ustawienia else None,
                  cardio_tryb=("osobno" if ustawienia.get("osobno") else "dodatek") if ustawienia else None,
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


def _domyslne_dla_celu() -> None:
    import streamlit as st
    s = st.session_state
    silowe, cardio = DOMYSLNE.get(s.get("ob_cel"), (3, 0))
    s["ob_silowe"], s["ob_cardio"] = silowe, cardio


def _krok_cel() -> None:
    import streamlit as st
    s = st.session_state
    cele = cele_dla(profil.wczytaj()["data_ur"])
    stan = s.get("ob_stan") or {}     # wybór zapamiętany poza widgetami: Streamlit kasuje stan widgetów, których nie ma na ekranie
    if s.get("ob_cel") not in cele:
        s["ob_cel"] = stan.get("cel") if stan.get("cel") in cele else cele[0]
        silowe, cardio = DOMYSLNE.get(s["ob_cel"], (3, 0))
        s["ob_silowe"] = stan.get("silowe", silowe)
        s["ob_cardio"] = stan.get("cardio", cardio)
        s["ob_dlugosc"] = DLUGOSCI[1] if stan.get("krotkie") else DLUGOSCI[0]
        s["ob_cardio_tryb"] = CARDIO_TRYBY[0] if stan.get("osobno", True) else CARDIO_TRYBY[1]
    if s.get("ob_silowe") not in SILOWE_DO_WYBORU:
        s["ob_silowe"] = 3
    if s.get("ob_cardio") not in CARDIO_DO_WYBORU:
        s["ob_cardio"] = 0
    if s.get("ob_dlugosc") not in DLUGOSCI:
        s["ob_dlugosc"] = DLUGOSCI[0]
    if s.get("ob_cardio_tryb") not in CARDIO_TRYBY:
        s["ob_cardio_tryb"] = CARDIO_TRYBY[0]
    st.radio("Jaki jest Twój główny cel?", cele, key="ob_cel", on_change=_domyslne_dla_celu)
    st.segmented_control("Ile treningów siłowych w tygodniu?", list(SILOWE_DO_WYBORU), key="ob_silowe",
                         help="Zacznij od tylu, ile realnie dasz radę. Później zmienisz to w planie.")
    st.segmented_control("Jakie mają być treningi siłowe?", list(DLUGOSCI), key="ob_dlugosc",
                         help="Pełne to podział na dół i górę ciała, ok. godziny. Krótkie to trening na całe ciało, ok. 30 minut: "
                              "dla zabieganych tygodni.")
    st.segmented_control("Ile razy w tygodniu cardio?", list(CARDIO_DO_WYBORU), key="ob_cardio",
                         help="0 = bez cardio. Cardio to rower, wioślarz, schody albo bieg.")
    if s.get("ob_cardio"):
        st.segmented_control("Jak dołożyć cardio?", list(CARDIO_TRYBY), key="ob_cardio_tryb",
                             help="Osobne dni to osobny trening cardio. Na koniec treningu to dopisek do treningu siłowego: "
                                  "15-20 minut po ćwiczeniach.")
        if s.get("ob_cardio_tryb") == CARDIO_TRYBY[0] and s["ob_silowe"] + s["ob_cardio"] > MAKS_DNI:
            st.caption("W tygodniu musi zostać wolny dzień, więc część cardio dołożymy na koniec treningów siłowych.")

    def dalej() -> None:
        w = st.session_state
        stan_nowy = {"cel": w.get("ob_cel"), "silowe": w.get("ob_silowe") or 3, "cardio": w.get("ob_cardio") or 0,
                     "krotkie": w.get("ob_dlugosc") == DLUGOSCI[1],
                     "osobno": (w.get("ob_cardio_tryb") or CARDIO_TRYBY[0]) == CARDIO_TRYBY[0]}
        w["ob_stan"] = stan_nowy
        dozwolony = profil.dozwolony_sprzet(profil.sprzet_wybrany())
        lista = pasowanie_presetow(dozwolony)
        propozycja = zaproponuj_plan(stan_nowy["cel"], stan_nowy["silowe"], stan_nowy["cardio"], stan_nowy["krotkie"],
                                     stan_nowy["osobno"], lista,
                                     dozwolony is None or bool({"*", "Maszyna cardio"} & dozwolony))
        for d in propozycja:
            w[f"ob_plan_{d['Dzien']}"] = d["Typ"] or ODPOCZYNEK
            w[f"ob_notatka_{d['Dzien']}"] = d["Notatka"]
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
        if s.get(f"ob_plan_{i}") != ODPOCZYNEK and s.get(f"ob_notatka_{i}"):
            st.caption(s[f"ob_notatka_{i}"])

    def zatwierdz() -> None:
        dni = []
        for i in range(7):
            typ = st.session_state.get(f"ob_plan_{i}") or ODPOCZYNEK
            aktywny = typ != ODPOCZYNEK
            dni.append({"Dzien": i, "Aktywny": aktywny, "Typ": typ if aktywny else "", "Godzina": "",
                        "Notatka": (st.session_state.get(f"ob_notatka_{i}") or "") if aktywny else ""})
        _koniec(dni)

    def pusty() -> None:
        _koniec(None)

    def _koniec(dni_planu: list[dict] | None) -> None:
        stan = st.session_state.get("ob_stan") or {}
        zakoncz(stan.get("cel"), stan, dni_planu)
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
