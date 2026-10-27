"""Układanie presetów z ulubionych: reguły, bez modelu AI.

Wejście: ulubione ćwiczenia, sprzęt z „Mojej siłowni”, cel treningowy, liczba dni w tygodniu, czas jednego treningu i partie, które
mają dostać więcej uwagi. Wyjście: zwykłe presety (kategoria „Własne”), które można dalej edytować, z krótkim uzasadnieniem
każdego wyboru. Kolejność ważności: ulubione, potem cel, na końcu czas (czas tylko przycina to, co nie jest ulubione ani akcentem).

Moduł logiki (`uloz`) nie zależy od Streamlita i nie czyta bazy, więc da się go testować na samej liście ćwiczeń. Widok
(`sekcja_profilu`) i zapis (`zapisz_presety`) są poniżej.
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from contextlib import closing
from dataclasses import dataclass, field

W, I = "Wielostawowe", "Izolowane"        # typ ćwiczenia (jak w bazie ćwiczeń)
MIN_DNI, MAKS_DNI = 2, 6
CZASY = (30, 45, 60, 75, 90, 120)         # minuty jednego treningu
CZAS_DOMYSLNY, DNI_DOMYSLNE = 60, 3
NARZUT_MIN = 5                            # rozgrzewka i przygotowanie, w minutach
MAKS_AKCENTOW = 3
WYKLUCZONE_RODZAJE = {"Plyometria", "Strongman", "Olimpijskie", "Cardio"}   # nie wchodzą do zwykłych slotów (chyba że ulubione)

CEL_SILA, CEL_MASA, CEL_REDUKCJA, CEL_KONDYCJA = "Siła", "Masa mięśniowa", "Redukcja tkanki tłuszczowej", "Kondycja i zdrowie"
CELE_Z_CARDIO = (CEL_REDUKCJA, CEL_KONDYCJA)

# Slot: (partie, typ, rola w dniu). Typ None = obojętny (partie, w których i tak robi się głównie izolacje).
# „rdzeń” = pierwsze slotów wielostawowych, których czas nigdy nie przycina.
PARTIE_DOLNE = ("Czworogłowe", "Dwugłowe uda", "Pośladki")
SZABLONY = {
    "Push": [(("Klatka",), W), (("Barki przód",), W), (("Klatka",), I), (("Barki bok",), I), (("Triceps",), None), (("Triceps",), None)],
    "Pull": [(("Plecy szerokie",), W), (("Plecy górne",), W), (("Plecy szerokie", "Plecy górne", "Plecy dolne"), I),
             (("Barki tył",), I), (("Biceps",), None), (("Biceps",), None)],
    "Nogi": [(("Czworogłowe",), W), (("Dwugłowe uda", "Pośladki"), W), (("Czworogłowe",), I), (("Dwugłowe uda",), I),
             (("Łydki",), None), (("Brzuch",), None)],
    "Góra": [(("Klatka",), W), (("Plecy szerokie",), W), (("Barki przód",), W), (("Plecy górne",), W),
             (("Biceps",), None), (("Triceps",), None), (("Barki bok",), I)],
    "Całe ciało A": [(("Czworogłowe",), W), (("Klatka",), W), (("Plecy szerokie",), W), (("Dwugłowe uda", "Pośladki"), W),
                     (("Barki bok",), I), (("Brzuch",), None)],
    "Całe ciało B": [(("Dwugłowe uda", "Pośladki"), W), (("Barki przód",), W), (("Plecy górne",), W), (("Czworogłowe",), W),
                     (("Biceps",), None), (("Triceps",), None)],
    "Całe ciało C": [(("Czworogłowe", "Pośladki"), W), (("Klatka",), W), (("Plecy szerokie", "Plecy górne"), W),
                     (("Barki przód", "Barki bok"), W), (("Łydki",), None), (("Brzuch",), None)],
}
OPISY = {
    "Push": "klatka, barki, triceps", "Pull": "plecy, tył barków, biceps", "Nogi": "nogi, łydki, brzuch",
    "Góra": "klatka, plecy, barki, ramiona", "Dół": "nogi, łydki, brzuch",
    "Całe ciało A": "całe ciało", "Całe ciało B": "całe ciało", "Całe ciało C": "całe ciało",
}
# Podział tygodnia wg liczby dni: (nazwa dnia, szablon)
PODZIAL = {
    2: [("Całe ciało A", "Całe ciało A"), ("Całe ciało B", "Całe ciało B")],
    3: [("Całe ciało A", "Całe ciało A"), ("Całe ciało B", "Całe ciało B"), ("Całe ciało C", "Całe ciało C")],
    4: [("Góra A", "Góra"), ("Dół A", "Nogi"), ("Góra B", "Góra"), ("Dół B", "Nogi")],
    5: [("Push", "Push"), ("Pull", "Pull"), ("Nogi", "Nogi"), ("Góra", "Góra"), ("Dół", "Nogi")],
    6: [("Push A", "Push"), ("Pull A", "Pull"), ("Nogi A", "Nogi"), ("Push B", "Push"), ("Pull B", "Pull"), ("Nogi B", "Nogi")],
}
# Dni tygodnia (0 = poniedziałek) dla planu tygodnia
DNI_TYGODNIA = {2: (1, 4), 3: (0, 2, 4), 4: (0, 1, 3, 4), 5: (0, 1, 2, 4, 5), 6: (0, 1, 2, 3, 4, 5)}

POPULARNOSC = {"Sztanga": 6, "Hantle": 6, "Maszyna": 5, "Wyciąg": 5, "Suwnica Smitha": 3, "Masa ciała": 3, "Kettlebell": 2,
               "Sztanga łamana": 3, "Landmine / T-bar": 2, "Inny sprzęt": -5}
SPRZET_CIEZKI = ("Sztanga", "Suwnica Smitha", "Landmine / T-bar", "Sztanga trap bar")
SPRZET_IZOLACJE = ("Wyciąg", "Maszyna", "Hantle")


@dataclass
class Ustawienia:
    dni: int = DNI_DOMYSLNE
    czas: int = CZAS_DOMYSLNY
    cel: str = ""
    akcent: tuple = ()
    ulubione: frozenset = frozenset()
    unikaj: frozenset = frozenset()
    ulub_sprzet: frozenset = frozenset()
    dozwolony: frozenset | None = None      # None = nie filtruj po sprzęcie


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
    powody: list = field(default_factory=list)
    alternatywa: str = ""
    chroniona: bool = False                  # ulubione albo akcent: czas jej nie przytnie
    rdzen: bool = False
    cardio: bool = False


def _norma(t: str) -> str:
    """Małe litery bez polskich znaków."""
    return "".join(z for z in unicodedata.normalize("NFKD", (t or "").lower().replace("ł", "l")) if not unicodedata.combining(z))


# Dane o typie ćwiczeń w bazie są przybliżone (np. rozpiętki bywają „wielostawowe”), więc nazwa ma pierwszeństwo.
RE_IZOL = re.compile(r"(rozpiet|pullover|wznos|uginanie|prostowanie|odwodzenie|przywodzenie|wspiecia|unoszenie ramion|face ?pull|"
                     r"szrugs|skrecan|brzuszki|spiecie|kickback|francusk|modlitewnik|zginanie nadgarstk)")
RE_WIELO = re.compile(r"^(wyciskanie|przysiad|martwy ciag|wioslowanie|sciaganie|podciaganie|hip thrust|wypychanie|rumunski|zakrok|"
                      r"dipy|pompki|wykrok|wejscia)")
RE_DZIWNE = re.compile(r"(jednorac|jednonoz|jedna reka|naprzemienn|plie|dookola|gilotyn|szyi|neck|z gumami|izometr|zegarow|rotacj|"
                       r"podwyzszeni|wzdluz tulowia|bradford|dnem do gory|boczny|na brzuchu|odwrotn|na podlodze|przelozon|zawieszeni|trx|svend|z przejsciem|wycieraczk|kettlebell|ugietych)")
RE_BRZUCH = re.compile(r"(plank|deska|brzuszki|unoszenie (nog|kolan)|spiecie|allah|robak|roller|rowerek|russian)")


def rodzaj_ruchu(c: dict) -> str | None:
    """Wielostawowe / izolowane: z nazwy, a gdy nazwa nic nie mówi, z typu zapisanego w bazie."""
    n = _norma(c["nazwa"])
    if RE_IZOL.search(n):
        return I
    if RE_WIELO.search(n):
        return W
    return c["typ"] or None


def _klucz_ruchu(nazwa: str) -> str:
    """Pierwsze dwa słowa nazwy (bez polskich znaków): ogranicza powtarzanie prawie tego samego ruchu w jednym dniu."""
    return " ".join(_norma(nazwa).split()[:2])


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
    if cel in CELE_Z_CARDIO:
        return (3, 8, 12, jedn) if typ == W else (3, 12, 15, jedn)
    # masa (i brak celu)
    if typ == W:
        return (4, 6, 10, jedn) if numer_wielostawowego < 2 else (3, 8, 12, jedn)
    return 3, 10, 15, jedn


def _minuty(p: Pozycja, cel: str) -> float:
    if p.cardio or p.jednostka == "min":
        return (p.powt_od + p.powt_do) / 2
    ciezko = cel == CEL_SILA
    if p.slot_typ == W or p.typ == W:
        na_serie = 3.5 if ciezko else 3.0 if cel not in CELE_Z_CARDIO else 2.3
    else:
        na_serie = 2.5 if ciezko else 2.0 if cel not in CELE_Z_CARDIO else 1.6
    return p.serie * na_serie


def szacunek_minut(pozycje: list[Pozycja], cel: str) -> int:
    return round(NARZUT_MIN + sum(_minuty(p, cel) for p in pozycje))


def _punkty(c: dict, slot_typ: str | None, u: Ustawienia, poziom: str) -> tuple[float, list[str]]:
    """Ocena kandydata do slotu i powody, dla których jest wysoko."""
    pkt, powody = 0.0, []
    if c["nazwa"] in u.ulubione:
        pkt += 1000
        powody.append("ulubione")
    if c["sprzet"] and c["sprzet"] in u.ulub_sprzet:
        pkt += 60
        powody.append(f"ulubiony sprzęt: {c['sprzet']}")
    cel = u.cel
    if cel == CEL_SILA and slot_typ == W and c["sprzet"] in SPRZET_CIEZKI:
        pkt += 20
        powody.append("siła: ciężkie podstawowe ćwiczenie")
    elif cel == CEL_MASA and slot_typ != W and c["sprzet"] in SPRZET_IZOLACJE:
        pkt += 15
        powody.append("masa: izolacja pod pełną kontrolę ruchu")
    elif cel == CEL_MASA and slot_typ == W and c["sprzet"] in ("Sztanga", "Hantle", "Maszyna"):
        pkt += 10
    elif cel in CELE_Z_CARDIO and c["sprzet"] in ("Hantle", "Kettlebell", "Maszyna", "Masa ciała"):
        pkt += 6
    pkt += POPULARNOSC.get(c["sprzet"], 0)
    n = _norma(c["nazwa"])
    if RE_DZIWNE.search(n):
        pkt -= 25 if slot_typ == W else 12
    elif slot_typ == W and RE_WIELO.search(n):
        pkt += 15
    if c["partia"] == "Brzuch" and RE_BRZUCH.search(n):
        pkt += 20
    if c["uzycia"] > 0:
        pkt += min(c["uzycia"], 10)
        powody.append("już to robiłeś")
    if poziom == "Zaawansowany":
        pkt -= 15
    elif poziom == "Początkujący":
        pkt += 3
    return pkt, powody


def _kandydaci(lista: list[dict], poziomy: dict, partie: tuple, slot_typ: str | None, u: Ustawienia, uzyte: set, klucze: set):
    wynik = []
    for c in lista:
        if c["nazwa"] in uzyte or c["nazwa"] in u.unikaj:
            continue
        ulub = c["nazwa"] in u.ulubione
        if c["ukryte"] and not ulub:
            continue
        if c["partia"] not in partie:
            continue
        if c["rodzaj"] in WYKLUCZONE_RODZAJE and not ulub:
            continue
        if u.dozwolony is not None and c["sprzet"] not in u.dozwolony and not ulub:
            continue
        if slot_typ is not None and rodzaj_ruchu(c) != slot_typ and not ulub:
            continue
        if _klucz_ruchu(c["nazwa"]) in klucze and not ulub:
            continue
        pkt, powody = _punkty(c, slot_typ, u, poziomy.get(c["nazwa"], ""))
        wynik.append((pkt, c, powody))
    wynik.sort(key=lambda x: (-x[0], x[1]["nazwa"]))
    return wynik


def _cardio(lista: list[dict], u: Ustawienia, uzyte: set):
    wynik = []
    for c in lista:
        if c["nazwa"] in uzyte or c["nazwa"] in u.unikaj or c["ukryte"] and c["nazwa"] not in u.ulubione:
            continue
        if c["partia"] != "Cardio" and c["rodzaj"] != "Cardio":
            continue
        if u.dozwolony is not None and c["sprzet"] not in u.dozwolony and c["nazwa"] not in u.ulubione:
            continue
        pkt = (1000 if c["nazwa"] in u.ulubione else 0) + (50 if c["sprzet"] in u.ulub_sprzet else 0) \
            + (5 if c["sprzet"] == "Maszyna cardio" else 0) + min(c["uzycia"], 10)
        wynik.append((pkt, c))
    wynik.sort(key=lambda x: (-x[0], x[1]["nazwa"]))
    return wynik


def _ulozyc_dzien(nazwa_szablonu: str, lista: list[dict], poziomy: dict, u: Ustawienia, uzyte: set) -> tuple[list[Pozycja], list[str]]:
    uwagi: list[str] = []
    # Akcent: dodatkowe ćwiczenie na wskazaną partię, zaraz po pierwszym slocie z tą partią
    sloty = []
    for partie, typ in SZABLONY[nazwa_szablonu]:
        sloty.append((partie, typ, False))
        for a in u.akcent:
            if a in partie and not any(x[2] and a in x[0] for x in sloty):
                sloty.append(((a,), I if typ_izol(a) else typ, True))

    pozycje: list[Pozycja] = []
    klucze: set[str] = set()
    wielostawowe = 0
    for partie, typ, akcent in sloty:
        kand = _kandydaci(lista, poziomy, partie, typ, u, uzyte | {p.nazwa for p in pozycje}, klucze)
        if not kand:
            uwagi.append(f"Brak ćwiczenia na „{' / '.join(partie)}” przy Twoim sprzęcie.")
            continue
        _pkt, c, powody = kand[0]
        serie, od, do, jedn = _schemat(u.cel, typ, wielostawowe, c["partia"], _jednostka(c))
        if typ == W:
            wielostawowe += 1
        powody = list(powody)
        if akcent:
            powody.append(f"akcent: {c['partia'].lower()}")
        if not powody:
            powody.append("wielostawowe, na początek" if typ == W else "uzupełnienie partii")
        alt = next((x[1]["nazwa"] for x in kand[1:] if x[1]["sprzet"] != c["sprzet"]), "") or (kand[1][1]["nazwa"] if len(kand) > 1 else "")
        pozycje.append(Pozycja(c["nazwa"], c["partia"], c["typ"] or "", typ, serie, od, do, jedn, powody, alt,
                               chroniona=(c["nazwa"] in u.ulubione) or akcent, rdzen=(typ == W and wielostawowe <= 3)))
        klucze.add(_klucz_ruchu(c["nazwa"]))
    # ćwiczenie na kondycję/redukcję: cardio na końcu (czas może je przyciąć)
    if u.cel in CELE_Z_CARDIO:
        kard = _cardio(lista, u, uzyte | {p.nazwa for p in pozycje})
        if kard:
            c = kard[0][1]
            pozycje.append(Pozycja(c["nazwa"], c["partia"], "", None, 1, 10, 15, "min", ["cardio na koniec: " + u.cel.lower()],
                                   chroniona=c["nazwa"] in u.ulubione, cardio=True))
    return pozycje, uwagi


def typ_izol(partia: str) -> bool:
    """Partie, w których dodatkowy akcent ma być izolacją (małe partie)."""
    return partia in ("Biceps", "Triceps", "Barki bok", "Barki tył", "Łydki", "Brzuch", "Przedramiona")


def _jednostka(c: dict) -> str:
    return c.get("jednostka") or "powt."


def _przytnij(pozycje: list[Pozycja], u: Ustawienia, uwagi: list[str]) -> None:
    """Skraca trening do podanego czasu, usuwając od końca to, co nie jest ulubione, akcentem ani rdzeniem."""
    while szacunek_minut(pozycje, u.cel) > u.czas:
        ofiara = next((p for p in reversed(pozycje) if not p.chroniona and not p.rdzen), None)
        if ofiara is not None:
            pozycje.remove(ofiara)
            continue
        # zostały tylko ulubione, akcenty i rdzeń: najpierw mniej serii w rdzeniu (do 3), potem rezygnujemy z czasu
        dluga = max((p for p in pozycje if p.rdzen and not p.chroniona and p.serie > 3), key=lambda p: p.serie, default=None)
        if dluga is not None:
            dluga.serie -= 1
            continue
        komunikat = (f"Ulubione i akcenty nie mieszczą się w {u.czas} min (wychodzi ok. {szacunek_minut(pozycje, u.cel)} min); "
                     "zostawiłem je, bo są ważniejsze niż czas.")
        uwagi[:] = [x for x in uwagi if not x.startswith("Ulubione i akcenty nie mieszczą")] + [komunikat]
        return


def uloz(lista: list[dict], poziomy: dict[str, str], u: Ustawienia) -> list[dict]:
    """Układa tydzień treningów. Zwraca listę presetów: {nazwa, opis, pozycje, minuty, uwagi, szablon}."""
    dni = min(max(int(u.dni), MIN_DNI), MAKS_DNI)
    uzyte: set[str] = set()
    dni_wynik = []
    for nazwa, szablon in PODZIAL[dni]:
        pozycje, uwagi = _ulozyc_dzien(szablon, lista, poziomy, u, uzyte)
        _przytnij(pozycje, u, uwagi)
        uzyte |= {p.nazwa for p in pozycje}
        dni_wynik.append({"nazwa": nazwa, "opis": OPISY.get(szablon, ""), "szablon": szablon, "pozycje": pozycje,
                          "uwagi": uwagi})
    _dolozyc_nieulozone_ulubione(dni_wynik, lista, u, uzyte)
    for d in dni_wynik:
        _przytnij(d["pozycje"], u, d["uwagi"])             # po dołożeniu ulubionych czas może znów przekraczać limit
        d["minuty"] = szacunek_minut(d["pozycje"], u.cel)
    return dni_wynik


def _dolozyc_nieulozone_ulubione(dni_wynik: list[dict], lista: list[dict], u: Ustawienia, uzyte: set) -> None:
    """Ulubione, które nie trafiły do żadnego slotu (np. trzecia klatka albo przedramiona), dokładamy do dnia z tą partią."""
    po_nazwie = {c["nazwa"]: c for c in lista}
    for nazwa in sorted(u.ulubione):
        c = po_nazwie.get(nazwa)
        if c is None or nazwa in uzyte or nazwa in u.unikaj:
            continue
        if u.dozwolony is not None and c["sprzet"] not in u.dozwolony and c["sprzet"] != "":
            continue                                    # nie masz tego sprzętu: ulubione zostaje poza planem
        kandydaci = [d for d in dni_wynik if c["partia"] in SZABLONY_PARTII[d["szablon"]]]
        cel_dnia = min(kandydaci or dni_wynik, key=lambda d: len(d["pozycje"]))
        jedn = _jednostka(c)
        serie, od, do, jedn = _schemat(u.cel, c["typ"] or I, 5, c["partia"], jedn)
        poz = Pozycja(c["nazwa"], c["partia"], c["typ"] or "", None, serie, od, do, jedn,
                      ["ulubione (dołożone, bo nie weszło do podstawowego układu)"], chroniona=True)
        index = max((i for i, p in enumerate(cel_dnia["pozycje"]) if not p.cardio), default=-1) + 1
        cel_dnia["pozycje"].insert(index, poz)
        uzyte.add(nazwa)


SZABLONY_PARTII = {nazwa: {p for partie, _ in sloty for p in partie} for nazwa, sloty in SZABLONY.items()}


# ---------------------------------------------------------------- ustawienia w bazie i zapis presetów

KLUCZE = {"dni": "gen_dni", "czas": "gen_czas", "akcent": "gen_akcent", "unikaj": "gen_unikaj", "ulub_sprzet": "gen_sprzet_ulub"}


def _polacz():
    import baza
    db = sqlite3.connect(baza.SCIEZKA_BAZY)
    db.execute("CREATE TABLE IF NOT EXISTS profil (Klucz TEXT PRIMARY KEY, Wartosc TEXT)")
    return db


def wczytaj_ustawienia() -> dict:
    """Zapisane wybory z Profilu (dni, czas, akcent, nie chcę, ulubiony sprzęt)."""
    with closing(_polacz()) as db:
        surowe = dict(db.execute("SELECT Klucz, Wartosc FROM profil WHERE Klucz LIKE 'gen\\_%' ESCAPE '\\'").fetchall())

    def _lista(klucz):
        try:
            w = json.loads(surowe.get(klucz) or "[]")
            return [str(x) for x in w] if isinstance(w, list) else []
        except ValueError:
            return []

    def _liczba(klucz, domyslna, dozwolone):
        try:
            w = int(surowe.get(klucz) or domyslna)
        except ValueError:
            return domyslna
        return w if w in dozwolone else domyslna

    return {"dni": _liczba("gen_dni", DNI_DOMYSLNE, range(MIN_DNI, MAKS_DNI + 1)),
            "czas": _liczba("gen_czas", CZAS_DOMYSLNY, CZASY),
            "akcent": _lista("gen_akcent")[:MAKS_AKCENTOW], "unikaj": _lista("gen_unikaj"), "ulub_sprzet": _lista("gen_sprzet_ulub")}


def zapisz_ustawienia(**pola) -> None:
    with closing(_polacz()) as db:
        for nazwa, wartosc in pola.items():
            klucz = KLUCZE.get(nazwa)
            if klucz is None:
                continue
            tekst = json.dumps(list(wartosc), ensure_ascii=False) if isinstance(wartosc, (list, tuple, set)) else str(wartosc)
            if wartosc in (None, "", [], ()):
                db.execute("DELETE FROM profil WHERE Klucz = ?", (klucz,))
            else:
                db.execute("INSERT INTO profil (Klucz, Wartosc) VALUES (?, ?) ON CONFLICT(Klucz) DO UPDATE SET Wartosc = excluded.Wartosc",
                           (klucz, tekst))
        db.commit()


def poziomy_cwiczen() -> dict[str, str]:
    """Poziom trudności ćwiczeń z bazy (nie ma go w standardowej liście)."""
    with closing(_polacz()) as db:
        try:
            return {n: (p or "") for n, p in db.execute("SELECT Nazwa, Poziom FROM cwiczenia")}
        except sqlite3.OperationalError:
            return {}


def ustawienia_z_profilu(cel: str, wybory: dict | None = None) -> Ustawienia:
    """Składa ustawienia z zapisanych wyborów, ulubionych i sprzętu z Profilu."""
    import profil
    w = wybory or wczytaj_ustawienia()
    return Ustawienia(dni=w["dni"], czas=w["czas"], cel=cel or "", akcent=tuple(w["akcent"]),
                      ulubione=frozenset(profil.ulubione()), unikaj=frozenset(w["unikaj"]), ulub_sprzet=frozenset(w["ulub_sprzet"]),
                      dozwolony=(frozenset(d) if (d := profil.dozwolony_sprzet()) is not None else None))


def wolna_nazwa(nazwa: str, istniejace: set[str]) -> str:
    male = {n.lower() for n in istniejace}
    kandydat, n = nazwa, 2
    while kandydat.lower() in male:
        kandydat = f"{nazwa} ({n})"
        n += 1
    return kandydat


def zapisz_presety(wynik: list[dict], ustaw_plan: bool = False, prefiks: str = "Mój plan: ") -> list[str]:
    """Zapisuje ułożone treningi jako presety (kategoria „Własne”). Zwraca ich nazwy. Z `ustaw_plan` ustawia też plan tygodnia
    (godziny i notatki dni treningowych zostają, reszta dni dostaje odpoczynek)."""
    import plan
    import presety
    import sesja_treningowa
    with closing(_polacz()) as db:
        presety._utworz_tabele(db)
        istniejace = {w[0] for w in db.execute("SELECT Nazwa FROM presety")}
    nazwy = []
    for d in wynik:
        if not d["pozycje"]:
            continue
        nazwa = wolna_nazwa(prefiks + d["nazwa"], istniejace)
        istniejace.add(nazwa)
        glowne = 0
        cw = []
        for p in d["pozycje"]:
            rola = "Dodatek"
            if (p.slot_typ == W or p.rdzen) and glowne < presety.MAKS_GLOWNYCH:
                rola = "Główne"
                glowne += 1
            cw.append({"nazwa": p.nazwa, "rola": rola, "serie": p.serie, "powt_od": p.powt_od, "powt_do": p.powt_do,
                       "jednostka": p.jednostka, "alternatywa": p.alternatywa, "wskazowka": ""})
        cw.sort(key=lambda c: c["rola"] != "Główne")          # główne na górę, kolejność w grupach zostaje
        sesja_treningowa.utworz_preset(nazwa, cw, "Własne")
        nazwy.append(nazwa)
    if ustaw_plan and nazwy:
        obecny = plan.wczytaj_plan().set_index("Dzien")
        dni_treningowe = DNI_TYGODNIA.get(len(nazwy), tuple(range(len(nazwy))))
        przypisane = dict(zip(dni_treningowe, nazwy))
        zmiany = []
        for dzien in range(7):
            wiersz = obecny.loc[dzien]
            zmiany.append({"Dzien": dzien, "Aktywny": dzien in przypisane, "Typ": przypisane.get(dzien, ""),
                           "Godzina": wiersz["Godzina"], "Notatka": wiersz["Notatka"]})
        plan.zapisz_plan(zmiany)
    return nazwy


# ---------------------------------------------------------------- widok w Profilu

def _jednostka_opis(p: Pozycja) -> str:
    zakres = f"{p.powt_od}" if p.powt_od == p.powt_do else f"{p.powt_od}–{p.powt_do}"
    if p.jednostka == "min":
        return f"{zakres} min"
    return f"{p.serie} × {zakres}" + ("" if p.jednostka in ("powt.", "") else f" {p.jednostka}")


def _zmiana_ustawien() -> None:
    """Zapis wyborów z pól i wyczyszczenie starej propozycji (nie pasuje już do ustawień)."""
    import streamlit as st
    s = st.session_state
    zapisz_ustawienia(dni=s.get("gen_dni", DNI_DOMYSLNE), czas=s.get("gen_czas", CZAS_DOMYSLNY),
                      akcent=list(s.get("gen_akcent") or []), unikaj=list(s.get("gen_unikaj") or []),
                      ulub_sprzet=list(s.get("gen_sprzet_ulub") or []))
    s["gen_wynik"] = None
    s.pop("gen_zapisano", None)


def _zmiana_celu() -> None:
    import streamlit as st

    import profil
    profil.zapisz(cel=st.session_state.get("gen_cel") or None)
    st.session_state["gen_wynik"] = None
    st.session_state.pop("gen_zapisano", None)


def sekcja_profilu() -> None:
    """Sekcja „Układanie treningów” na stronie Profil: ustawienia, podgląd propozycji i zapis jako presety."""
    import html

    import streamlit as st

    import profil
    s = st.session_state
    dane = profil.wczytaj()
    zapisane = wczytaj_ustawienia()
    lista = [c for c in profil._wszystkie_cwiczenia() if not c["ukryte"]]
    nazwy = {c["nazwa"]: c for c in lista}
    partie = [p for p in ("Klatka", "Plecy szerokie", "Plecy górne", "Plecy dolne", "Barki przód", "Barki bok", "Barki tył", "Biceps",
                          "Triceps", "Przedramiona", "Czworogłowe", "Dwugłowe uda", "Pośladki", "Łydki", "Brzuch")
              if any(c["partia"] == p for c in lista)]
    sprzet_opcje = [x for x in (profil.sprzet_wybrany() or profil.dostepny_sprzet())]
    cele = [c for c in profil.CELE if not (profil.niepelnoletni(dane) and c == profil.CEL_REDUKCJA)]

    st.markdown("<div class='pr-sekcja'>Układanie treningów</div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("Aplikacja ułoży tydzień treningów z Twoich ulubionych ćwiczeń, sprzętu z „Mojej siłowni” i celu. "
                    "Najpierw liczą się ulubione, potem cel, na końcu czas. Wynik to zwykłe presety, które możesz edytować.")
        ulub = [n for n in profil.ulubione() if n in nazwy]
        st.caption(f"Ulubione ćwiczenia: {len(ulub)}" + ("" if ulub else ". Dodaj je wyżej w „Mojej siłowni”, wtedy układ będzie z nich zbudowany."))
        if "gen_cel" not in s:
            s["gen_cel"] = dane["cel"] if dane["cel"] in cele else None
        st.selectbox("Cel", cele, key="gen_cel", index=None, placeholder="Wybierz cel...", on_change=_zmiana_celu,
                     help="Cel decyduje o liczbie serii i powtórzeń oraz o doborze sprzętu (siła: sztanga, masa: izolacje na maszynach i wyciągach, "
                          "redukcja i kondycja: krótsze przerwy i cardio na końcu).")
        if "gen_dni" not in s:
            s["gen_dni"] = zapisane["dni"]
        st.select_slider("Dni treningowe w tygodniu", options=list(range(MIN_DNI, MAKS_DNI + 1)), key="gen_dni", on_change=_zmiana_ustawien,
                         help="2–3 dni: całe ciało. 4: góra i dół dwa razy. 5: push, pull, nogi, góra, dół. 6: push, pull, nogi dwa razy.")
        if "gen_czas" not in s:
            s["gen_czas"] = zapisane["czas"]
        st.select_slider("Czas jednego treningu", options=list(CZASY), key="gen_czas", on_change=_zmiana_ustawien,
                         format_func=lambda m: f"{m} min",
                         help="Czas jest najmniej ważny: skraca trening, ale nie usuwa ulubionych ćwiczeń ani partii z akcentem.")
        if "gen_akcent" not in s:
            s["gen_akcent"] = [a for a in zapisane["akcent"] if a in partie]
        st.multiselect("Partie z akcentem (do 3)", partie, key="gen_akcent", on_change=_zmiana_ustawien, max_selections=MAKS_AKCENTOW,
                       placeholder="Wybierz partie...", help="Dla tych partii w każdym dniu, w którym występują, dojdzie jedno ćwiczenie więcej.")
        if "gen_sprzet_ulub" not in s:
            s["gen_sprzet_ulub"] = [x for x in zapisane["ulub_sprzet"] if x in sprzet_opcje]
        st.multiselect("Ulubiony sprzęt", sprzet_opcje, key="gen_sprzet_ulub", on_change=_zmiana_ustawien,
                       placeholder="Wybierz sprzęt...", help="Przy podobnych ćwiczeniach wygra to na sprzęcie, który lubisz.")
        if "gen_unikaj" not in s:
            s["gen_unikaj"] = [n for n in zapisane["unikaj"] if n in nazwy]
        st.multiselect("Ćwiczenia, których nie chcę", list(nazwy), key="gen_unikaj", on_change=_zmiana_ustawien,
                       format_func=lambda n: f"{n} · {nazwy[n]['sprzet']}" if nazwy[n]["sprzet"] else n, placeholder="Szukaj po nazwie...")

        if st.button("Ułóż propozycję", use_container_width=True, key="gen_uloz", type="primary"):
            s.pop("gen_zapisano", None)
            u = ustawienia_z_profilu(s.get("gen_cel") or "", {"dni": s["gen_dni"], "czas": s["gen_czas"], "akcent": list(s.get("gen_akcent") or []),
                                                              "unikaj": list(s.get("gen_unikaj") or []), "ulub_sprzet": list(s.get("gen_sprzet_ulub") or [])})
            with closing(_polacz()) as db:
                import baza_cwiczen
                wszystkie = baza_cwiczen.wszystkie(db)
            s["gen_wynik"] = uloz(wszystkie, poziomy_cwiczen(), u)
            s["gen_wynik_u"] = u

        wynik = s.get("gen_wynik")
        if wynik:
            u = s.get("gen_wynik_u")
            st.markdown("**Propozycja** (jeszcze niezapisana)")
            for d in wynik:
                with st.expander(f"{d['nazwa']} · ok. {d['minuty']} min · {len(d['pozycje'])} ćw."):
                    st.caption(d["opis"])
                    for i, p in enumerate(d["pozycje"], start=1):
                        powod = f" <span style='opacity:.65'>· {html.escape('; '.join(p.powody))}</span>" if p.powody else ""
                        st.markdown(f"<div style='margin:2px 0'>{i}. <b>{html.escape(p.nazwa)}</b> · {html.escape(_jednostka_opis(p))}{powod}</div>",
                                    unsafe_allow_html=True)
                    for uw in d["uwagi"]:
                        st.warning(uw)
            if u is not None and not u.ulubione:
                st.info("Nie masz ulubionych ćwiczeń, więc układ opiera się tylko na celu i sprzęcie.")
            st.checkbox("Ustaw też plan tygodnia (zastąpi obecny plan; godziny i notatki zostają)", key="gen_plan")
            if st.button("Zapisz jako presety", use_container_width=True, key="gen_zapisz"):
                try:
                    s["gen_zapisano"] = zapisz_presety(wynik, ustaw_plan=bool(s.get("gen_plan")))
                    s["gen_wynik"] = None
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
        if s.get("gen_zapisano"):
            st.success("Zapisano presety: " + ", ".join(s["gen_zapisano"]) + ". Znajdziesz je w Treningach (kategoria Własne).")
