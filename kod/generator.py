"""Trening na dziś: układanie jednego treningu z ulubionych ćwiczeń, sprzętu z „Mojej siłowni”, partii i czasu. Reguły, bez modelu AI.

Użytkownik wybiera partie, które chce dziś zrobić, i czas. Aplikacja proponuje trzy różne treningi:
- 1–2 ulubione ćwiczenia z wybranych partii (zawsze, jeśli ma takie przy sprzęcie, który ma),
- 1–2 nowe, czyli takie, których jeszcze nie robił (rozwój, urozmaicenie),
- reszta to sprawdzone, podstawowe ćwiczenia (wielostawowe na początku).
Czas jest najmniej ważny: skraca trening, ale nie usuwa ulubionych ani nowych. Gdy w presetach jest już coś pasującego do
wybranych partii i czasu, najpierw pokazujemy to.

Logika (`uloz_dzis`, `trzy_warianty`, `pasujacy_preset`) nie zależy od Streamlita i nie czyta bazy. Okno (`okno_generatora`) jest na końcu.
"""
from __future__ import annotations

import html
import re
import sqlite3
import unicodedata
from contextlib import closing
from dataclasses import dataclass, field

import streamlit as st

W, I = "Wielostawowe", "Izolowane"        # typ ćwiczenia (jak w bazie ćwiczeń)
CZASY = (30, 45, 60, 75, 90, 120)         # minuty (cały trening, razem z rozgrzewką i schłodzeniem)
CZAS_DOMYSLNY = 60
NARZUT_MIN = 15                           # rozgrzewka i schłodzenie, w minutach (nie wpisujemy ich w trening, ale zajmują czas)
ZAPAS_PRZERW = 1.1                        # dłuższe przerwy niż w tabelce: dolicza ok. 10% do czasu serii
LIMIT_ULUBIONYCH = 2
WYKLUCZONE_RODZAJE = {"Plyometria", "Strongman", "Olimpijskie", "Cardio"}   # nie wchodzą do zwykłych slotów

CEL_SILA, CEL_MASA, CEL_REDUKCJA, CEL_KONDYCJA = "Siła", "Masa mięśniowa", "Redukcja tkanki tłuszczowej", "Kondycja i zdrowie"
CELE_KROTSZE_PRZERWY = (CEL_REDUKCJA, CEL_KONDYCJA)

# Grupy partii widoczne dla użytkownika (kolejność = od dużych do małych; w takiej kolejności układa się trening)
GRUPY = {
    "Nogi": ("Czworogłowe", "Dwugłowe uda"),
    "Plecy": ("Plecy szerokie", "Plecy górne", "Plecy dolne"),
    "Klatka": ("Klatka",),
    "Barki": ("Barki przód", "Barki bok", "Barki tył"),
    "Pośladki": ("Pośladki",),
    "Biceps": ("Biceps",),
    "Triceps": ("Triceps",),
    "Brzuch": ("Brzuch",),
    "Łydki": ("Łydki",),
}
# Kolejne ćwiczenia w grupie: (partie, typ). Typ: wielostawowe, potem izolacje (None = obojętne, np. małe partie).
_PL = GRUPY["Plecy"]
SLOTY_GRUPY = {
    "Nogi": [(("Czworogłowe",), W), (("Dwugłowe uda",), W), (("Czworogłowe",), I), (("Dwugłowe uda",), I), (GRUPY["Nogi"], W),
             (("Czworogłowe",), I), (("Dwugłowe uda",), I)],
    "Plecy": [(("Plecy szerokie",), W), (("Plecy górne",), W), (_PL, I), (_PL, W), (_PL, I), (_PL, W), (_PL, I)],
    "Klatka": [(("Klatka",), W), (("Klatka",), I), (("Klatka",), W), (("Klatka",), I), (("Klatka",), W), (("Klatka",), I), (("Klatka",), I)],
    "Barki": [(("Barki przód",), W), (("Barki bok",), I), (("Barki tył",), I), (("Barki bok",), I), (("Barki przód",), W), (("Barki tył",), I)],
    "Pośladki": [(("Pośladki",), W), (("Pośladki",), I), (("Pośladki",), I), (("Pośladki",), W), (("Pośladki",), I)],
    "Biceps": [(("Biceps",), None)] * 5, "Triceps": [(("Triceps",), None)] * 5,
    "Brzuch": [(("Brzuch",), None)] * 5, "Łydki": [(("Łydki",), None)] * 4,
}
RDZEN = 3                                 # tyle pierwszych wielostawowych nie wypadnie przy skracaniu do czasu

POPULARNOSC = {"Sztanga": 6, "Hantle": 6, "Maszyna": 5, "Wyciąg": 5, "Suwnica Smitha": 3, "Masa ciała": 3, "Kettlebell": 2,
               "Sztanga łamana": 3, "Landmine / T-bar": 2, "Inny sprzęt": -5}
SPRZET_CIEZKI = ("Sztanga", "Suwnica Smitha", "Landmine / T-bar", "Sztanga trap bar")
SPRZET_IZOLACJE = ("Wyciąg", "Maszyna", "Hantle")


@dataclass
class Ustawienia:
    cel: str = ""
    ulubione: frozenset = frozenset()
    dozwolony: frozenset | None = None      # None = nie filtruj po sprzęcie
    czas: int = CZAS_DOMYSLNY


@dataclass
class Pozycja:
    nazwa: str
    partia: str
    typ: str
    slot_typ: str | None
    serie: int
    powt_od: int
    powt_do: int
    jednostka: str
    etykieta: str = ""                       # „ulubione” / „nowe” / „” (sprawdzone)
    powody: list = field(default_factory=list)
    alternatywa: str = ""
    chroniona: bool = False                  # ulubione i nowe: czas ich nie przytnie
    rdzen: bool = False


def _norma(t: str) -> str:
    """Małe litery bez polskich znaków."""
    return "".join(z for z in unicodedata.normalize("NFKD", (t or "").lower().replace("ł", "l")) if not unicodedata.combining(z))


# Dane o typie ćwiczeń w bazie są przybliżone (np. rozpiętki bywają „wielostawowe”), więc nazwa ma pierwszeństwo.
RE_IZOL = re.compile(r"(rozpiet|pullover|wznos|uginanie|prostowanie|odwodzenie|przywodzenie|wspiecia|unoszenie ramion|face ?pull|"
                     r"szrugs|skrecan|brzuszki|spiecie|kickback|francusk|modlitewnik|zginanie nadgarstk)")
RE_WIELO = re.compile(r"^(wyciskanie|przysiad|martwy ciag|wioslowanie|sciaganie|podciaganie|hip thrust|wypychanie|rumunski|zakrok|"
                      r"dipy|pompki|wykrok|wejscia)")
RE_DZIWNE = re.compile(r"(jednorac|jednonoz|jedna reka|naprzemienn|plie|dookola|gilotyn|szyi|neck|z gumami|izometr|zegarow|rotacj|"
                       r"podwyzszeni|wzdluz tulowia|bradford|dnem do gory|boczny|na brzuchu|odwrotn|na podlodze|przelozon|zawieszeni|"
                       r"trx|svend|z przejsciem|wycieraczk|kettlebell|ugietych|anti-gravity)")
RE_BRZUCH = re.compile(r"(plank|deska|brzuszki|unoszenie (nog|kolan)|spiecie|allah|robak|roller|rowerek|russian)")


def rodzaj_ruchu(c: dict) -> str | None:
    """Wielostawowe / izolowane: z nazwy, a gdy nazwa nic nie mówi, z typu zapisanego w bazie."""
    n = _norma(c["nazwa"])
    if RE_IZOL.search(n):
        return I
    if RE_WIELO.search(n):
        return W
    return c["typ"] or None


def _schemat(cel: str, typ: str | None, numer_wielostawowego: int, partia: str, jednostka_dom: str):
    """Serie i zakres powtórzeń z celu i rodzaju ćwiczenia. Zwraca (serie, od, do, jednostka)."""
    jedn = jednostka_dom or "powt."
    if jedn in ("s", "min", "m"):
        return (3, 30, 60, "s") if jedn == "s" else (1, 10, 15, jedn) if jedn == "min" else (3, 20, 40, "m")
    if partia == "Łydki":
        return 3, 10, 15, jedn
    if partia == "Brzuch":
        return 3, 12, 20, jedn
    if cel == CEL_SILA:
        if typ == W:
            return (4, 3, 6, jedn) if numer_wielostawowego < 2 else (3, 6, 8, jedn)
        return 3, 8, 12, jedn
    if cel in CELE_KROTSZE_PRZERWY:
        return (3, 8, 12, jedn) if typ == W else (3, 12, 15, jedn)
    if typ == W:                                          # masa i brak celu
        return (4, 6, 10, jedn) if numer_wielostawowego < 2 else (3, 8, 12, jedn)
    return 3, 10, 15, jedn


def _minuty(p: Pozycja, cel: str) -> float:
    if p.jednostka == "min":
        return (p.powt_od + p.powt_do) / 2
    ciezko = cel == CEL_SILA
    krotko = cel in CELE_KROTSZE_PRZERWY
    if p.slot_typ == W or p.typ == W:
        na_serie = 3.5 if ciezko else 2.3 if krotko else 3.0
    else:
        na_serie = 2.5 if ciezko else 1.6 if krotko else 2.0
    return p.serie * na_serie * ZAPAS_PRZERW


def szacunek_minut(pozycje: list[Pozycja], cel: str) -> int:
    return round(NARZUT_MIN + sum(_minuty(p, cel) for p in pozycje))


def _punkty(c: dict, slot_typ: str | None, cel: str, poziom: str) -> float:
    """Ocena kandydata do slotu (im wyżej, tym lepiej pasuje do celu i jest typowym ćwiczeniem)."""
    pkt = 0.0
    if cel == CEL_SILA and slot_typ == W and c["sprzet"] in SPRZET_CIEZKI:
        pkt += 20
    elif cel == CEL_MASA and slot_typ != W and c["sprzet"] in SPRZET_IZOLACJE:
        pkt += 15
    elif cel == CEL_MASA and slot_typ == W and c["sprzet"] in ("Sztanga", "Hantle", "Maszyna"):
        pkt += 10
    elif cel in CELE_KROTSZE_PRZERWY and c["sprzet"] in ("Hantle", "Kettlebell", "Maszyna", "Masa ciała"):
        pkt += 6
    pkt += POPULARNOSC.get(c["sprzet"], 0)
    n = _norma(c["nazwa"])
    if RE_DZIWNE.search(n):
        pkt -= 25 if slot_typ == W else 12
    elif slot_typ == W and RE_WIELO.search(n):
        pkt += 15
    if c["partia"] == "Brzuch" and RE_BRZUCH.search(n):
        pkt += 20
    if poziom == "Zaawansowany":
        pkt -= 15
    elif poziom == "Początkujący":
        pkt += 3
    return pkt


def _klucz_ruchu(nazwa: str) -> str:
    """Pierwsze dwa słowa nazwy (bez polskich znaków): ogranicza powtarzanie prawie tego samego ruchu."""
    return " ".join(_norma(nazwa).split()[:2])


def _dozwolone(c: dict, u: Ustawienia) -> bool:
    if c["ukryte"] or c["rodzaj"] in WYKLUCZONE_RODZAJE:
        return False
    return u.dozwolony is None or c["sprzet"] in u.dozwolony


def _kandydaci(lista: list[dict], poziomy: dict, partie: tuple, slot_typ: str | None, u: Ustawienia, uzyte: set, klucze: set) -> list[dict]:
    """Ćwiczenia pasujące do slotu, od najlepszego. Ulubione są tu pomijane: dobieramy je osobno (limit na trening)."""
    wynik = []
    for c in lista:
        if c["nazwa"] in uzyte or c["nazwa"] in u.ulubione or c["partia"] not in partie or not _dozwolone(c, u):
            continue
        if slot_typ is not None and rodzaj_ruchu(c) != slot_typ:
            continue
        if _klucz_ruchu(c["nazwa"]) in klucze:
            continue
        wynik.append((_punkty(c, slot_typ, u.cel, poziomy.get(c["nazwa"], "")), c))
    wynik.sort(key=lambda x: (-x[0], x[1]["nazwa"]))
    return [c for _, c in wynik]


def _wybierz(kand: list[dict], przesuniecie: int) -> tuple[dict | None, str]:
    """Wybiera ćwiczenie z listy kandydatów: sprawdzone (robione wcześniej) mają pierwszeństwo. Przesunięcie 0 bierze najlepsze,
    większe bierze kolejne (spośród trzech najlepszych). Zwraca (ćwiczenie, powód)."""
    if not kand:
        return None, ""
    znane = [c for c in kand if c["uzycia"] > 0]
    pula = znane or kand
    c = pula[przesuniecie % min(3, len(pula))]
    return c, ("już to robiłeś" if c["uzycia"] > 0 else "podstawowe ćwiczenie")


def uloz_dzis(lista: list[dict], poziomy: dict[str, str], u: Ustawienia, grupy: list[str], poziom: int = 0, seria: int = 0) -> dict:
    """Układa jeden trening. Zwraca {nazwa, opis, pozycje, minuty, uwagi, poziom}. Te same argumenty dają zawsze ten sam wynik.
    Poziom 0: układ podstawowy. Poziom 1: zmienione jedno ćwiczenie główne albo ulubione, reszta jak w poziomie 0. Poziom 2: to samo
    i dodatkowo 2–3 inne ćwiczenia (więcej nowości). `seria` przesuwa wszystkie wybory naraz (przycisk „Ułóż inne”)."""
    grupy = [g for g in GRUPY if g in grupy]                 # kolejność od dużych partii do małych
    wszystkie_partie = {p for g in grupy for p in GRUPY[g]}
    uwagi: list[str] = []

    # sloty: najpierw po jednym na grupę, potem drugie itd.
    sloty: list[dict] = []
    for poziom_slotu in range(max((len(SLOTY_GRUPY[g]) for g in grupy), default=0)):
        for g in grupy:
            if poziom_slotu < len(SLOTY_GRUPY[g]):
                partie_slotu, typ_slotu = SLOTY_GRUPY[g][poziom_slotu]
                sloty.append({"grupa": g, "partie": partie_slotu, "typ": typ_slotu, "c": None, "etykieta": "", "powod": ""})

    po_nazwie = {c["nazwa"]: c for c in lista}
    uzyte: set[str] = set()
    klucze: set[str] = set()

    # 1) ulubione: najwyżej dwa, z wybranych partii, ze sprzętem, który masz; kolejne warianty biorą inne
    ulub = sorted(n for n in u.ulubione if n in po_nazwie and po_nazwie[n]["partia"] in wszystkie_partie
                  and not po_nazwie[n]["ukryte"] and (u.dozwolony is None or po_nazwie[n]["sprzet"] in u.dozwolony))
    if ulub:
        start = ((1 if poziom >= 1 and len(ulub) > LIMIT_ULUBIONYCH else 0) + seria) % len(ulub)
        kolejnosc = ulub[start:] + ulub[:start]
        wybrane, grupy_uzyte = [], set()
        for n in kolejnosc:                                   # najpierw z różnych grup
            g = next(g for g in grupy if po_nazwie[n]["partia"] in GRUPY[g])
            if g not in grupy_uzyte and len(wybrane) < LIMIT_ULUBIONYCH:
                wybrane.append(n)
                grupy_uzyte.add(g)
        for n in kolejnosc:
            if n not in wybrane and len(wybrane) < LIMIT_ULUBIONYCH:
                wybrane.append(n)
        for n in wybrane:
            c = po_nazwie[n]
            g = next(g for g in grupy if c["partia"] in GRUPY[g])
            ruch = rodzaj_ruchu(c)
            wolne_g = [s for s in sloty if s["grupa"] == g and s["c"] is None]
            slot = (next((s for s in wolne_g if c["partia"] in s["partie"] and s["typ"] in (None, ruch)), None)
                    or next((s for s in wolne_g if c["partia"] in s["partie"]), None) or (wolne_g[0] if wolne_g else None))
            if slot is None:
                slot = {"grupa": g, "partie": GRUPY[g], "typ": ruch, "c": None, "etykieta": "", "powod": ""}
                sloty.append(slot)
            slot.update(c=c, etykieta="ulubione", powod="ulubione", typ=ruch if ruch else slot["typ"])
            uzyte.add(n)
            klucze.add(_klucz_ruchu(n))

    # przesunięcia wyboru: seria przesuwa wszystko; poziom 1 zmienia jedno ćwiczenie główne (gdy ulubione nie mają z czego się zmienić),
    # poziom 2 dodatkowo do trzech innych ćwiczeń
    for s in sloty:
        s["off"] = seria
    zmiana = None
    wolne_po_ulubionych = [s for s in sloty if s["c"] is None]
    if poziom >= 1 and not (len(ulub) > LIMIT_ULUBIONYCH):
        glowne = [s for s in wolne_po_ulubionych if s["typ"] == W] or wolne_po_ulubionych
        if glowne:
            zmiana = glowne[min(1, len(glowne) - 1)]
            zmiana["off"] += 1
    if poziom >= 2:
        for s in [x for x in reversed(wolne_po_ulubionych) if x is not zmiana][:3]:
            s["off"] += 1

    # 2) nowe: 1–2 ćwiczenia, których jeszcze nie robiłeś (izolacje i małe partie, nie ciężkie podstawowe)
    wolne = [s for s in sloty if s["c"] is None]
    ile_nowych = 1 if len(sloty) <= 4 else 2
    kolejnosc_nowych = [s for s in reversed(wolne) if s["typ"] != W] + [s for s in reversed(wolne) if s["typ"] == W]
    for s in kolejnosc_nowych:
        if sum(1 for x in sloty if x["etykieta"] == "nowe") >= ile_nowych:
            break
        kand = [c for c in _kandydaci(lista, poziomy, s["partie"], s["typ"], u, uzyte, klucze) if c["uzycia"] == 0]
        if not kand:
            continue
        c = kand[s["off"] % min(5, len(kand))]
        s.update(c=c, etykieta="nowe", powod="nowe, jeszcze tego nie robiłeś: na rozwój")
        uzyte.add(c["nazwa"])
        klucze.add(_klucz_ruchu(c["nazwa"]))

    # 3) reszta: sprawdzone, podstawowe ćwiczenia (wielostawowe na początek)
    for s in sloty:
        if s["c"] is not None:
            continue
        kand = _kandydaci(lista, poziomy, s["partie"], s["typ"], u, uzyte, klucze)
        if not kand and s["typ"] is not None:     # slot izolacji bez kandydata: spróbuj szerzej w obrębie grupy
            kand = _kandydaci(lista, poziomy, GRUPY[s["grupa"]], s["typ"], u, uzyte, klucze)
        if not kand:
            continue
        c, powod = _wybierz(kand, s["off"])
        if c is None:
            continue
        s.update(c=c, powod=powod if s["typ"] != W else ("wielostawowe, na początek" if c["uzycia"] == 0 else powod))
        uzyte.add(c["nazwa"])
        klucze.add(_klucz_ruchu(c["nazwa"]))
    for g in grupy:
        if not any(s["c"] is not None and s["grupa"] == g for s in sloty):
            uwagi.append(f"Brak ćwiczeń na „{g}” przy sprzęcie z Twojej siłowni.")

    # kolejność: wielostawowe najpierw (ulubione zostają na swoich miejscach w obrębie grup)
    wypelnione = [s for s in sloty if s["c"] is not None]
    wypelnione.sort(key=lambda s: 0 if (s["typ"] == W or rodzaj_ruchu(s["c"]) == W) else 1)

    pozycje: list[Pozycja] = []
    wielo = 0
    for s in wypelnione:
        c = s["c"]
        typ = W if (s["typ"] == W or rodzaj_ruchu(c) == W) else I
        serie, od, do, jedn = _schemat(u.cel, typ, wielo, c["partia"], c.get("jednostka") or "powt.")
        if typ == W:
            wielo += 1
        alt_kand = _kandydaci(lista, poziomy, s["partie"], s["typ"], u, uzyte - {c["nazwa"]}, set())
        alt = next((x["nazwa"] for x in alt_kand if x["sprzet"] != c["sprzet"]), "") or (alt_kand[0]["nazwa"] if alt_kand else "")
        pozycje.append(Pozycja(c["nazwa"], c["partia"], c["typ"] or "", typ, serie, od, do, jedn, s["etykieta"], [s["powod"]],
                               alt, chroniona=(s["etykieta"] == "ulubione"), rdzen=(typ == W and wielo <= RDZEN)))
    _przytnij(pozycje, u, uwagi)
    return {"nazwa": "Na dziś: " + ", ".join(grupy), "opis": ", ".join(g.lower() for g in grupy), "pozycje": pozycje,
            "minuty": szacunek_minut(pozycje, u.cel), "uwagi": uwagi, "poziom": poziom, "seria": seria}


def _przytnij(pozycje: list[Pozycja], u: Ustawienia, uwagi: list[str]) -> None:
    """Skraca trening do podanego czasu. Kolejność: znikają zwykłe ćwiczenia z końca, potem serie do trzech, potem nowe ćwiczenia,
    serie do dwóch i dodatkowe ćwiczenia z rdzenia (zostaje co najmniej jedno). Ulubionych czas nigdy nie usuwa."""
    def dluga(minimum: int):
        return max((p for p in pozycje if p.etykieta != "ulubione" and p.serie > minimum and p.jednostka != "min"),
                   key=lambda p: p.serie, default=None)

    while szacunek_minut(pozycje, u.cel) > u.czas:
        ofiara = next((p for p in reversed(pozycje) if p.etykieta == "" and not p.rdzen), None)
        if ofiara is not None:
            pozycje.remove(ofiara)
            continue
        if (p := dluga(3)) is not None:
            p.serie -= 1
            continue
        ofiara = next((p for p in reversed(pozycje) if p.etykieta == "nowe"), None)
        if ofiara is not None:
            pozycje.remove(ofiara)
            continue
        if (p := dluga(2)) is not None:
            p.serie -= 1
            continue
        zwykle = [p for p in pozycje if p.etykieta == ""]
        if len(zwykle) > 1:
            pozycje.remove(zwykle[-1])
            continue
        uwagi.append(f"Ulubione ćwiczenia nie mieszczą się w {u.czas} min (wychodzi ok. {szacunek_minut(pozycje, u.cel)} min); "
                     "zostawiłem je, bo są ważniejsze niż czas.")
        return


OPISY_POZIOMOW = (
    "Układ podstawowy: ulubione, kilka nowych i sprawdzone ćwiczenia.",
    "To samo, ale z innym ćwiczeniem głównym albo ulubionym.",
    "Więcej nowości: dodatkowo kilka innych ćwiczeń na zmianę.",
)


def trzy_warianty(lista: list[dict], poziomy: dict[str, str], u: Ustawienia, grupy: list[str], seria: int = 0) -> list[dict]:
    """Trzy treningi o rosnącej odmienności: podstawowy, z jedną zmianą głównego/ulubionego i z kilkoma dodatkowymi zmianami.
    `seria` 0 daje pierwszą trójkę, kolejne dają inne (przycisk „Ułóż inne”). Gdy dwa treningi wyszłyby takie same, bierzemy kolejny wybór."""
    wyniki: list[dict] = []
    widziane: set[frozenset] = set()
    for poziom in range(3):
        for dod in range(4):
            t = uloz_dzis(lista, poziomy, u, grupy, poziom, seria * 4 + dod)
            klucz = frozenset(p.nazwa for p in t["pozycje"])
            if t["pozycje"] and klucz not in widziane:
                widziane.add(klucz)
                t["poziom"] = len(wyniki)
                wyniki.append(t)
                break
    return wyniki


def pasujacy_preset(lista: list[dict], presety: list[dict], grupy: list[str], czas: int) -> dict | None:
    """Preset, który już masz i który pasuje do wybranych partii oraz czasu. `presety`: [{id, nazwa, kategoria, cwiczenia: [{nazwa, serie}]}]."""
    wybrane = {p for g in grupy if g in GRUPY for p in GRUPY[g]}
    if not wybrane:
        return None
    partia = {c["nazwa"]: c["partia"] for c in lista}
    najlepszy, wynik = None, 0.0
    for p in presety:
        cw = [c for c in p["cwiczenia"] if c["nazwa"]]
        if len(cw) < 3:
            continue
        w_wybranych = [c for c in cw if partia.get(c["nazwa"]) in wybrane]
        udzial = len(w_wybranych) / len(cw)
        pokrycie = len({partia[c["nazwa"]] for c in w_wybranych}) / len(wybrane)
        minuty = NARZUT_MIN + sum((c.get("serie") or 3) * 2.7 * ZAPAS_PRZERW for c in cw)
        if udzial < 0.75 or pokrycie < 0.5 or minuty > czas * 1.25:
            continue
        punkty = udzial + pokrycie + (0.05 if p.get("kategoria") == "Własne" else 0)
        if punkty > wynik:
            najlepszy, wynik = p, punkty
    return najlepszy


def etykieta_partii(grupy: list[str]) -> str:
    return ", ".join(g for g in GRUPY if g in grupy)


# ---------------------------------------------------------------- dane z bazy i zapis

def _polacz() -> sqlite3.Connection:
    import baza
    return sqlite3.connect(baza.SCIEZKA_BAZY)


def poziomy_cwiczen() -> dict[str, str]:
    """Poziom trudności ćwiczeń z bazy (nie ma go w standardowej liście)."""
    with closing(_polacz()) as db:
        try:
            return {n: (p or "") for n, p in db.execute("SELECT Nazwa, Poziom FROM cwiczenia")}
        except sqlite3.OperationalError:
            return {}


def _wszystkie_cwiczenia() -> list[dict]:
    import baza_cwiczen
    with closing(_polacz()) as db:
        return baza_cwiczen.wszystkie(db)


def ustawienia_z_profilu(czas: int) -> Ustawienia:
    """Cel, ulubione i sprzęt z Profilu."""
    import profil
    dozw = profil.dozwolony_sprzet()
    return Ustawienia(cel=profil.wczytaj()["cel"] or "", ulubione=frozenset(profil.ulubione()),
                      dozwolony=frozenset(dozw) if dozw is not None else None, czas=czas)


def presety_do_dopasowania() -> list[dict]:
    import presety
    wynik = []
    lista = presety.lista_presetow()
    for _, w in lista.iterrows():
        cw = presety.wczytaj_cwiczenia_presetu(int(w["id"]))
        wynik.append({"id": int(w["id"]), "nazwa": str(w["Nazwa"]), "kategoria": str(w["Kategoria"] or ""),
                      "cwiczenia": [{"nazwa": str(r["Cwiczenie"] or ""), "serie": None if r["Serie"] != r["Serie"] else r["Serie"]}
                                    for _, r in cw.iterrows()]})
    return wynik


def wolna_nazwa(nazwa: str, istniejace: set[str]) -> str:
    male = {n.lower() for n in istniejace}
    kandydat, n = nazwa, 2
    while kandydat.lower() in male:
        kandydat = f"{nazwa} ({n})"
        n += 1
    return kandydat


def cwiczenia_do_zapisu(trening: dict) -> list[dict]:
    """Ćwiczenia treningu w formacie presetu / treningu w toku (główne na górze, kolejność w grupach zostaje)."""
    wynik = []
    glowne = 0
    for p in trening["pozycje"]:
        rola = "Dodatek"
        if (p.slot_typ == W or p.rdzen) and glowne < 5:
            rola = "Główne"
            glowne += 1
        wynik.append({"nazwa": p.nazwa, "rola": rola, "serie": p.serie, "powt_od": p.powt_od, "powt_do": p.powt_do,
                      "jednostka": p.jednostka, "alternatywa": p.alternatywa, "wskazowka": ""})
    wynik.sort(key=lambda c: c["rola"] != "Główne")
    return wynik


def zapisz_jako_preset(trening: dict, nazwa: str) -> str:
    """Zapisuje trening jako preset (kategoria „Własne”). Zwraca zapisaną nazwę (przy zajętej dopisuje numer)."""
    import presety
    import sesja_treningowa
    with closing(_polacz()) as db:
        presety._utworz_tabele(db)
        istniejace = {w[0] for w in db.execute("SELECT Nazwa FROM presety")}
    nazwa = wolna_nazwa((nazwa or "").strip() or trening["nazwa"], istniejace)
    sesja_treningowa.utworz_preset(nazwa, cwiczenia_do_zapisu(trening), "Własne")
    return nazwa


# ---------------------------------------------------------------- okno w zakładce Treningi

CSS_OKNO = (
    "<style>"
    "[class*='st-key-gen_rzad'] [data-testid='stHorizontalBlock']{flex-wrap:nowrap !important;gap:8px !important;}"
    "[class*='st-key-gen_rzad'] [data-testid='stColumn'],[class*='st-key-gen_rzad'] [data-testid='column']"
    "{min-width:0 !important;flex:1 1 0 !important;width:auto !important;}"
    "[class*='st-key-gen_rzad'] button{min-height:3.1rem;padding:0.3rem 0.35rem !important;}"
    "[class*='st-key-gen_rzad'] button p{font-size:0.95rem !important;font-weight:700;white-space:nowrap !important;}"
    ".gen-poz{display:flex;gap:8px;align-items:baseline;margin:3px 0;line-height:1.3;}"
    ".gen-poz .n{opacity:.55;min-width:1.2em;}"
    ".gen-poz .d{opacity:.75;white-space:nowrap;margin-left:auto;padding-left:8px;}"
    ".gen-znacznik{display:inline-block;font-size:.68rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;"
    "padding:1px 7px;border-radius:99px;margin-left:6px;border:1px solid var(--e-obram2);vertical-align:middle;}"
    ".gen-znacznik.u{color:var(--e-tytul_glow2);}"
    ".gen-znacznik.n{color:var(--e-zielony);}"
    ".gen-powod{display:block;opacity:.6;font-size:.8rem;}"
    "</style>"
)


def _reset() -> None:
    s = st.session_state
    for klucz in [k for k in s if str(k).startswith("gen_") and k != "gen_otworz"]:
        del s[klucz]
    s["gen_krok"] = "wybor"
    s["gen_grupy"] = []
    s["gen_czas"] = CZAS_DOMYSLNY


def _przelacz_grupe(g: str) -> None:
    s = st.session_state
    lista = list(s.get("gen_grupy") or [])
    if g in lista:
        lista.remove(g)
    else:
        lista.append(g)
    s["gen_grupy"] = lista


def _ustaw_czas(m: int) -> None:
    st.session_state["gen_czas"] = m


def _uloz() -> None:
    s = st.session_state
    grupy = list(s.get("gen_grupy") or [])
    if not grupy:
        s["gen_blad"] = "Wybierz przynajmniej jedną partię."
        return
    lista, poziomy = _wszystkie_cwiczenia(), poziomy_cwiczen()
    u = ustawienia_z_profilu(int(s.get("gen_czas") or CZAS_DOMYSLNY))
    s["gen_seria"] = 0
    s["gen_warianty"] = trzy_warianty(lista, poziomy, u, grupy, 0)
    s["gen_u"] = u
    s["gen_preset"] = pasujacy_preset(lista, presety_do_dopasowania(), grupy, u.czas)
    s["gen_idx"] = 0
    s["gen_krok"] = "wynik"


def _ulozyc_inne() -> None:
    s = st.session_state
    s["gen_seria"] = int(s.get("gen_seria") or 0) + 1
    s["gen_warianty"] = trzy_warianty(_wszystkie_cwiczenia(), poziomy_cwiczen(), s["gen_u"], list(s["gen_grupy"]), s["gen_seria"])
    s["gen_idx"] = 0


def _wybierz_wariant(i: int) -> None:
    st.session_state["gen_idx"] = i


def _krok(krok: str) -> None:
    st.session_state["gen_krok"] = krok
    st.session_state.pop("gen_blad", None)


def _wybrany() -> dict | None:
    s = st.session_state
    idx = int(s.get("gen_idx") or 0)
    if s.get("gen_preset") and idx == 0:
        return None
    warianty = s.get("gen_warianty") or []
    i = idx - (1 if s.get("gen_preset") else 0)
    return warianty[i] if 0 <= i < len(warianty) else None


def _zacznij() -> None:
    """Start treningu z wybranej propozycji albo z presetu, który już masz. Okno zamknie się przy następnym przebiegu."""
    import sesja_treningowa as S
    s = st.session_state
    trening = _wybrany()
    if trening is None and s.get("gen_preset"):
        S.rozpocznij_z_presetu(int(s["gen_preset"]["id"]))
    elif trening is not None:
        cw = [S.nowe_cwiczenie(c["nazwa"], c["rola"], c["serie"], c["powt_od"], c["powt_do"], c["jednostka"], "", c["alternatywa"])
              for c in cwiczenia_do_zapisu(trening)]
        S._uruchom(S.nowy_stan(trening["nazwa"], "", S._lzejsze_jesli_wybrano(cw)))
    else:
        return
    s["gen_zamknij"] = True


def _zapisz() -> None:
    s = st.session_state
    trening = _wybrany()
    if trening is None:
        return
    try:
        s["gen_zapisano"] = zapisz_jako_preset(trening, s.get("gen_nazwa") or trening["nazwa"])
        s["gen_krok"] = "wynik"
    except ValueError as e:
        s["gen_blad"] = str(e)


def _wiersz_przyciskow(klucz: str, etykiety: list, zaznaczone, callback, kolumn: int | None = None, ptaszek: bool = True) -> None:
    """Rząd dużych przycisków szkła; zaznaczone mają wygląd głównego przycisku i ptaszek."""
    kolumn = kolumn or len(etykiety)
    for start in range(0, len(etykiety), kolumn):
        paczka = etykiety[start:start + kolumn]
        with st.container(key=f"gen_rzad_{klucz}_{start}"):
            kol = st.columns(kolumn)
            for j, et in enumerate(paczka):
                tak = zaznaczone(et)
                kol[j].button(("✓ " if tak and ptaszek else "") + (f"{et} min" if isinstance(et, int) else str(et)), key=f"gen_{klucz}_{start + j}",
                              type="primary" if tak else "secondary", use_container_width=True, on_click=callback, args=(et,))


def _krok_wybor() -> None:
    s = st.session_state
    if "gen_blad" in s:
        st.error(s.pop("gen_blad"))
    st.markdown("**Co dziś trenujesz?**")
    _wiersz_przyciskow("partie", list(GRUPY), lambda g: g in (s.get("gen_grupy") or []), _przelacz_grupe, kolumn=3)
    st.markdown("**Ile masz czasu?**")
    _wiersz_przyciskow("czas", list(CZASY), lambda m: m == s.get("gen_czas"), _ustaw_czas, kolumn=3, ptaszek=False)
    st.caption(f"Czas to cały trening, razem z ok. {NARZUT_MIN} min rozgrzewki i schłodzenia. Użyję Twoich ulubionych ćwiczeń i sprzętu "
               "z „Mojej siłowni”, dołożę kilka nowych dla rozwoju.")
    st.button("Ułóż trening", type="primary", use_container_width=True, on_click=_uloz, key="gen_dalej",
              disabled=not s.get("gen_grupy"))


def _html_pozycji(i: int, p: Pozycja) -> str:
    znacznik = {"ulubione": "<span class='gen-znacznik u'>ulubione</span>", "nowe": "<span class='gen-znacznik n'>nowe</span>"}.get(p.etykieta, "")
    zakres = f"{p.powt_od}" if p.powt_od == p.powt_do else f"{p.powt_od}–{p.powt_do}"
    dane = f"{zakres} min" if p.jednostka == "min" else f"{p.serie} × {zakres}" + ("" if p.jednostka in ("powt.", "") else f" {p.jednostka}")
    return (f"<div class='gen-poz'><span class='n'>{i}.</span><span><b>{html.escape(p.nazwa)}</b>{znacznik}</span>"
            f"<span class='d'>{html.escape(dane)}</span></div>")


def _krok_wynik() -> None:
    s = st.session_state
    warianty = s.get("gen_warianty") or []
    preset = s.get("gen_preset")
    if "gen_blad" in s:
        st.error(s.pop("gen_blad"))
    if s.get("gen_zapisano"):
        st.success(f"Zapisano preset „{s['gen_zapisano']}”. Znajdziesz go w Treningach (Własne).")
    st.caption(f"{etykieta_partii(list(s.get('gen_grupy') or []))} · {s.get('gen_czas')} min")
    if not warianty and not preset:
        st.warning("Nie udało się ułożyć treningu przy Twoim sprzęcie. Zaznacz więcej sprzętu w „Mojej siłowni” albo wybierz inne partie.")
        st.button("← Zmień wybór", use_container_width=True, on_click=_krok, args=("wybor",), key="gen_wstecz_pusty")
        return
    etykiety = (["Mój"] if preset else []) + [str(i + 1) for i in range(len(warianty))]
    idx = int(s.get("gen_idx") or 0)
    with st.container(key="gen_rzad_wariant"):
        kol = st.columns(len(etykiety))
        for i, et in enumerate(etykiety):
            kol[i].button(et, key=f"gen_wariant_{i}", type="primary" if i == idx else "secondary", use_container_width=True,
                          on_click=_wybierz_wariant, args=(i,))
    trening = _wybrany()
    with st.container(border=True):
        if trening is None and preset:
            st.markdown(f"**Masz już pasujący preset: {html.escape(preset['nazwa'])}**")
            for i, c in enumerate(preset["cwiczenia"], start=1):
                st.markdown(f"<div class='gen-poz'><span class='n'>{i}.</span><span><b>{html.escape(c['nazwa'])}</b></span></div>",
                            unsafe_allow_html=True)
        elif trening is not None:
            st.markdown(f"**Propozycja {idx + 1 - (1 if preset else 0)}** · ok. {trening['minuty']} min z rozgrzewką")
            st.caption(OPISY_POZIOMOW[min(int(trening.get("poziom", 0)), len(OPISY_POZIOMOW) - 1)])
            st.markdown("".join(_html_pozycji(i, p) for i, p in enumerate(trening["pozycje"], start=1)), unsafe_allow_html=True)
            for uw in trening["uwagi"]:
                st.caption(uw)
    st.button("Zacznij trening", type="primary", use_container_width=True, on_click=_zacznij, key="gen_zacznij")
    with st.container(key="gen_rzad_akcje"):
        k1, k2 = st.columns(2)
        k1.button("Zapisz jako preset", use_container_width=True, on_click=_krok, args=("nazwa",), key="gen_do_zapisu",
                  disabled=trening is None)
        k2.button("Ułóż inne", use_container_width=True, on_click=_ulozyc_inne, key="gen_inne")
    st.button("← Zmień wybór", use_container_width=True, on_click=_krok, args=("wybor",), key="gen_wstecz")


def _krok_nazwa() -> None:
    s = st.session_state
    trening = _wybrany()
    if "gen_blad" in s:
        st.error(s.pop("gen_blad"))
    if trening is None:
        _krok("wynik")
        return
    st.text_input("Nazwa presetu", value=trening["nazwa"], key="gen_nazwa")
    with st.container(key="gen_rzad_nazwa"):
        k1, k2 = st.columns(2)
        k1.button("← Wstecz", use_container_width=True, on_click=_krok, args=("wynik",), key="gen_nazwa_wstecz")
        k2.button("Zapisz", type="primary", use_container_width=True, on_click=_zapisz, key="gen_nazwa_zapisz")


@st.dialog("Trening na dziś")
def okno_generatora() -> None:
    s = st.session_state
    if s.pop("gen_zamknij", False):
        st.rerun()
    st.markdown(CSS_OKNO, unsafe_allow_html=True)
    krok = s.get("gen_krok", "wybor")
    if krok == "wynik":
        _krok_wynik()
    elif krok == "nazwa":
        _krok_nazwa()
    else:
        _krok_wybor()


def przycisk_generatora() -> None:
    """Przycisk „Ułóż trening na dziś” (strona Treningi): duży, w kolorach głównego przycisku, żeby było go widać. Otwiera okno w krokach."""
    st.markdown("<style>.st-key-gen_otworz button{min-height:3.4rem;}.st-key-gen_otworz button p{font-size:1.1rem !important;font-weight:800;"
                "letter-spacing:.02em;}</style>", unsafe_allow_html=True)
    if st.button("✦ Ułóż trening na dziś", use_container_width=True, key="gen_otworz", type="primary",
                 help="Wybierasz partie i czas, a aplikacja proponuje trzy treningi z Twoich ulubionych ćwiczeń, nowych i sprawdzonych."):
        _reset()
        okno_generatora()
