"""Tryb demo: Struo z przykładowymi danymi, do pokazania bez prawdziwej bazy i bez kont.

Uruchomienie (z głównego folderu projektu):
    python narzedzia/demo.py             tworzy bazę demo (jeśli jej nie ma) i uruchamia aplikację na http://localhost:8503
    python narzedzia/demo.py --od-nowa   kasuje bazę demo i tworzy ją od nowa
    python narzedzia/demo.py --tylko-dane  tylko przygotowuje bazę, bez uruchamiania aplikacji

Dane demo leżą wyłącznie w folderze demo/ (jest w .gitignore). Prawdziwy treningi.db nie jest otwierany: ścieżka bazy
jest ustawiana przez STRUO_BAZA, zanim zostanie zaimportowany jakikolwiek moduł aplikacji. W demo nie ma logowania,
Garmina ani powiadomień (to samo co konto gościa), a wszystkie liczby są wymyślone.
"""
from __future__ import annotations

import argparse
import os
import random
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent
FOLDER_DEMO = FOLDER / "demo"
BAZA_DEMO = FOLDER_DEMO / "treningi.db"
PORT = 8503

TYGODNIE = 8
# Dzień tygodnia (0 = poniedziałek) i preset; kolejność jak w typowym planie „góra, góra, dół”
PLAN = {0: "Góra push: klatka i barki", 2: "Góra pull: plecy i biceps", 4: "Dół siła: przysiad, RDL i suwnica"}
CIEZAR_STARTOWY = {"Sztanga": 40.0, "Sztanga łamana": 25.0, "Hantle": 14.0, "Maszyna": 35.0, "Wyciąg": 25.0, "Suwnica Smitha": 30.0}
# Główne boje i ćwiczenia, przy których ciężar „na sprzęt” wyglądałby nierealnie
CIEZAR_CWICZENIA = {
    "Przysiad ze sztangą": 70.0, "Wyciskanie sztangi na ławce płaskiej": 60.0, "RDL (rumuński martwy ciąg)": 60.0,
    "Wiosłowanie sztangą w opadzie tułowia": 50.0, "Wypychanie na suwnicy (obunóż)": 110.0, "Wspięcia na palce stojąc": 60.0,
    "Wznosy ramion bokiem z hantlami": 8.0, "Uginanie ramion z hantlami chwytem młotkowym": 12.0,
}
ULUBIONE = ("Wyciskanie sztangi na ławce płaskiej", "Przysiad ze sztangą", "Podciąganie na drążku")
NOTATKI = {"Wypychanie na suwnicy (obunóż)": "Oparcie na 3, stopy w połowie platformy."}


def srodowisko() -> dict:
    """Zmienne dla procesu demo: osobna baza, bez logowania. STRUO_BAZA wyłącza też Garmina i powiadomienia właściciela."""
    env = dict(os.environ)
    env.update({"STRUO_BAZA": str(BAZA_DEMO), "STRUO_DEMO": "1", "STRUO_LOGOWANIE": "0"})
    env.pop("OVRLD_BAZA", None)
    return env


def _zaokraglij(kg: float, sprzet: str) -> float:
    krok = 1.0 if sprzet == "Hantle" else 2.5
    return max(krok, round(kg / krok) * krok)


def _serie(c: dict, sprzet: str, tydzien: int, los: random.Random) -> list[dict]:
    """Serie jednego ćwiczenia: ciężar rośnie co tydzień, powtórzenia mieszczą się w zakresie z presetu."""
    od, do = c.get("powt_od") or 8, c.get("powt_do") or (c.get("powt_od") or 8) + 2
    if c["jednostka"] in ("s", "min", "m"):
        wartosc = {"s": 45, "min": 20, "m": 400}[c["jednostka"]]
        return [{"ciezar": 0.0, "powt": wartosc + 5 * tydzien, "rpe": 7} for _ in range(c["serie_plan"])]
    bazowy = CIEZAR_CWICZENIA.get(c["nazwa"], CIEZAR_STARTOWY.get(sprzet, 0.0))
    ciezar = _zaokraglij(bazowy * (1 + 0.03 * tydzien), sprzet) if bazowy else 0.0
    wynik = []
    for nr in range(c["serie_plan"]):
        powt = max(od, min(do, do - nr - los.randint(0, 1) + (tydzien % 3)))
        wynik.append({"ciezar": ciezar, "powt": powt, "rpe": min(10, 7 + nr // 2 + los.randint(0, 1))})
    return wynik


def przygotuj(od_nowa: bool = False) -> Path:
    """Tworzy bazę demo w folderze demo/ (jeśli jej nie ma). Zwraca ścieżkę do pliku bazy."""
    if od_nowa and FOLDER_DEMO.exists():
        shutil.rmtree(FOLDER_DEMO)
    if BAZA_DEMO.exists():
        return BAZA_DEMO
    FOLDER_DEMO.mkdir(parents=True, exist_ok=True)
    os.environ.update({k: v for k, v in srodowisko().items() if k.startswith("STRUO_")})
    os.environ.pop("OVRLD_BAZA", None)
    sys.path.insert(0, str(FOLDER / "kod"))
    import baza

    if Path(baza.SCIEZKA_BAZY) != BAZA_DEMO:
        raise RuntimeError("Demo może pisać tylko do folderu demo/, a baza wskazuje gdzie indziej. Nic nie zapisano.")
    wypelnij()
    return BAZA_DEMO


def wypelnij(dzis: date | None = None) -> None:
    """Wypełnia bieżącą bazę (baza.SCIEZKA_BAZY) przykładowymi danymi: profil, plan tygodnia, dziennik i treningi
    z ostatnich tygodni. Wywoływać tylko na pustej bazie demo albo testowej."""
    import sqlite3
    from contextlib import closing

    import baza
    import baza_cwiczen
    import dziennik
    import plan
    import presety
    import profil
    import sesja_treningowa as S

    baza.przygotuj_baze()
    S.przygotuj_tabele()
    presety.wczytaj_presety_startowe()
    with closing(sqlite3.connect(baza.SCIEZKA_BAZY)) as db:
        sprzet = {c["nazwa"]: c.get("sprzet") or "" for c in baza_cwiczen.wszystkie(db)}
    lista = presety.lista_presetow().set_index("Nazwa")

    profil.zapisz(imie="Demo", cel="Masa mięśniowa", wzrost=180, waga_cel=80.0, onboarding=date.today().isoformat())
    profil.zapisz_ulubione([n for n in ULUBIONE if n in sprzet])
    plan.zapisz_plan([{"Dzien": d, "Aktywny": d in PLAN, "Typ": PLAN.get(d, ""), "Godzina": "18:00" if d in PLAN else "",
                       "Notatka": ""} for d in range(7)])
    S.zapisz_ustawienie("garmin", "0")
    for nazwa, tekst in NOTATKI.items():
        if nazwa in sprzet:
            S.zapisz_notatke(nazwa, tekst)

    los = random.Random(7)            # stałe ziarno: demo wygląda tak samo przy każdym tworzeniu
    dzis = dzis or date.today()
    start = dzis - timedelta(weeks=TYGODNIE)
    waga = 82.4
    for i in range((dzis - start).days):
        dzien = start + timedelta(days=i)
        waga = round(waga - 0.03 + los.uniform(-0.15, 0.15), 1)
        dziennik.zapisz(dzien, sen_godz=round(los.uniform(6.2, 8.3), 1), waga=waga, energia=los.randint(3, 5))
        nazwa = PLAN.get(dzien.weekday())
        if not nazwa or nazwa not in lista.index or los.random() < 0.12:   # czasem trening wypada, jak w życiu
            continue
        tydzien = i // 7
        cwiczenia = S.cwiczenia_z_presetu(presety.wczytaj_cwiczenia_presetu(int(lista.loc[nazwa, "id"])))
        for c in cwiczenia:
            c["serie"] = _serie(c, sprzet.get(c["nazwa"], ""), tydzien, los)
        poczatek = datetime.combine(dzien, datetime.min.time()).replace(hour=18, minute=los.randint(0, 20))
        stan = S.nowy_stan(nazwa, str(lista.loc[nazwa, "Typ"]), cwiczenia, int(lista.loc[nazwa, "id"]), teraz=poczatek)
        S.zapisz_trening(stan, waga=waga, teraz=poczatek + timedelta(minutes=los.randint(52, 75)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Struo z przykładowymi danymi (tryb demo).")
    parser.add_argument("--od-nowa", action="store_true", help="skasuj bazę demo i utwórz ją od nowa")
    parser.add_argument("--tylko-dane", action="store_true", help="tylko przygotuj bazę, nie uruchamiaj aplikacji")
    args = parser.parse_args()
    print("Przygotowuję dane demo w folderze demo/ ...")
    przygotuj(args.od_nowa)
    if args.tylko_dane:
        print(f"Gotowe: {BAZA_DEMO}")
        return 0
    print(f"Uruchamiam Struo w trybie demo: http://localhost:{PORT}  (zamknij okno albo Ctrl+C, żeby zakończyć)")
    polecenie = [sys.executable, "-m", "streamlit", "run", str(FOLDER / "app.py"),
                 "--server.port", str(PORT), "--server.address", "127.0.0.1"]
    return subprocess.call(polecenie, cwd=FOLDER, env=srodowisko())


if __name__ == "__main__":
    sys.exit(main())
