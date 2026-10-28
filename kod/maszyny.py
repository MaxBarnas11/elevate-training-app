"""Konkretne maszyny i stanowiska siłowni („Moja siłownia” → Maszyny).

Rodzaj sprzętu (np. „Maszyna”, „Wyciąg”) to za mało, żeby wiedzieć, czy zrobisz dane ćwiczenie: suwnica, hack przysiad i maszyna
do uginania nóg to zupełnie różne urządzenia. Tu jest katalog typowych maszyn i stanowisk oraz reguły, które przypisują ćwiczenia
z bazy do maszyn (po polskiej nazwie i angielskim aliasie). Jedno ćwiczenie może pasować do kilku maszyn: wtedy wystarczy jedna z nich.

Zasada filtrowania: dopóki nie zaznaczysz żadnej maszyny, nic nie jest ukrywane (liczy się tylko rodzaj sprzętu). Gdy zaznaczysz
choć jedną, ćwiczenia przypisane do maszyn pokazują się tylko wtedy, gdy masz którąś z ich maszyn. Ćwiczenia bez przypisania
(wolne ciężary, masa ciała) zależą jak dotąd tylko od rodzaju sprzętu.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

ZNACZNIK = "#maszyny"          # w zbiorze „dozwolonego sprzętu”: zaznaczono maszyny, więc filtrujemy także po nich
PREFIKS = "m:"                 # w tym samym zbiorze: „m:<id>” to maszyna, którą masz


@dataclass(frozen=True)
class Maszyna:
    id: str
    nazwa: str
    grupa: str
    sprzet: str                # rodzaj sprzętu, do którego maszyna należy (zaznaczenie maszyny dokłada ten rodzaj)
    typowa: bool = False       # jest w większości siłowni sieciowych (przycisk „Typowa siłownia”)
    aliasy: str = ""           # dodatkowe słowa do wyszukiwania (po polsku i angielsku)


GRUPY = ("Nogi i pośladki", "Klatka i barki", "Plecy", "Ramiona", "Brzuch i grzbiet", "Wyciągi i suwnica Smitha",
         "Drążek, poręcze, stanowiska", "Cardio")

KATALOG: tuple[Maszyna, ...] = (
    # Nogi i pośladki
    Maszyna("suwnica", "Suwnica skośna (leg press 45°)", "Nogi i pośladki", "Maszyna", True, "leg press prasa nozna wypychanie"),
    Maszyna("suwnica_pozioma", "Suwnica pozioma (leg press siedząc)", "Nogi i pośladki", "Maszyna", False, "horizontal seated leg press"),
    Maszyna("hack", "Hack przysiad (hack squat)", "Nogi i pośladki", "Maszyna", True, "hack squat"),
    Maszyna("pendulum", "Przysiad wahadłowy (pendulum)", "Nogi i pośladki", "Maszyna", False, "pendulum squat"),
    Maszyna("przysiad_dzwignia", "Maszyna dźwigniowa do przysiadów", "Nogi i pośladki", "Maszyna", False,
            "leverage squat chair squat lying machine squat martwy ciag dzwignia"),
    Maszyna("belt_squat", "Przysiad z pasem (belt squat)", "Nogi i pośladki", "Maszyna", False, "belt squat"),
    Maszyna("prostowanie_nog", "Prostowanie nóg (leg extension)", "Nogi i pośladki", "Maszyna", True, "leg extension czworoglowe"),
    Maszyna("uginanie_lezac", "Uginanie nóg leżąc (leg curl)", "Nogi i pośladki", "Maszyna", True, "lying leg curl dwuglowe"),
    Maszyna("uginanie_siedzac", "Uginanie nóg siedząc (seated leg curl)", "Nogi i pośladki", "Maszyna", True, "seated leg curl dwuglowe"),
    Maszyna("uginanie_stojac", "Uginanie nogi stojąc", "Nogi i pośladki", "Maszyna", False, "standing leg curl"),
    Maszyna("odwodziciele", "Odwodziciele (abduktor)", "Nogi i pośladki", "Maszyna", True, "abductor abduktor odwodzenie"),
    Maszyna("przywodziciele", "Przywodziciele (adduktor)", "Nogi i pośladki", "Maszyna", True, "adductor adduktor przywodzenie"),
    Maszyna("hip_thrust", "Maszyna do hip thrust (glute drive)", "Nogi i pośladki", "Maszyna", False, "hip thrust glute drive"),
    Maszyna("kickback", "Odwodzenie nogi w tył (glute kickback)", "Nogi i pośladki", "Maszyna", False, "glute kickback posladki"),
    Maszyna("lydki_stojac", "Łydki stojąc", "Nogi i pośladki", "Maszyna", True, "standing calf raise wspiecia lydki"),
    Maszyna("lydki_siedzac", "Łydki siedząc", "Nogi i pośladki", "Maszyna", True, "seated calf raise wspiecia lydki"),
    # Klatka i barki
    Maszyna("chest_press", "Wyciskanie na klatkę (chest press)", "Klatka i barki", "Maszyna", True, "chest press klatka hammer"),
    Maszyna("chest_press_skos", "Wyciskanie skośne (incline press)", "Klatka i barki", "Maszyna", False, "incline chest press klatka gorna hammer"),
    Maszyna("butterfly", "Butterfly / pec deck", "Klatka i barki", "Maszyna", True, "pec deck rozpietki butterfly"),
    Maszyna("reverse_fly", "Tylne barki (reverse fly)", "Klatka i barki", "Maszyna", True, "rear delt reverse fly odwrocone rozpietki"),
    Maszyna("shoulder_press", "Wyciskanie nad głowę (shoulder press)", "Klatka i barki", "Maszyna", True, "shoulder press barki ohp"),
    Maszyna("wznosy_bokiem", "Wznosy bokiem (lateral raise)", "Klatka i barki", "Maszyna", False, "lateral raise barki bok"),
    # Plecy
    Maszyna("wyciag_gorny", "Wyciąg górny (ściąganie drążka)", "Plecy", "Wyciąg", True, "lat pulldown sciaganie drazka plecy"),
    Maszyna("wyciag_dolny", "Wyciąg dolny (wiosłowanie siedząc)", "Plecy", "Wyciąg", True, "seated cable row wioslowanie"),
    Maszyna("wioslowanie_maszyna", "Wiosłowanie na maszynie (Hammer, z oparciem)", "Plecy", "Maszyna", True,
            "row machine hammer iso row high row wioslowanie"),
    Maszyna("sciaganie_maszyna", "Ściąganie na maszynie dźwigniowej", "Plecy", "Maszyna", False, "lat pulldown plate loaded"),
    Maszyna("tbar", "T-bar / landmine", "Plecy", "Landmine / T-bar", False, "t-bar landmine wioslowanie dlugim gryfem"),
    Maszyna("asysta", "Podciąganie i dipy ze wspomaganiem", "Plecy", "Maszyna", True, "assisted pull-up dip gravitron asysta"),
    Maszyna("pullover_maszyna", "Pullover na maszynie", "Plecy", "Maszyna", False, "pullover machine"),
    Maszyna("szrugsy_maszyna", "Szrugsy na maszynie", "Plecy", "Maszyna", False, "shrug machine kaptury"),
    # Ramiona
    Maszyna("biceps_maszyna", "Uginanie ramion na maszynie (biceps)", "Ramiona", "Maszyna", False, "biceps curl machine"),
    Maszyna("modlitewnik", "Modlitewnik (ławka Scotta)", "Ramiona", "", True, "preacher curl scott modlitewnik"),
    Maszyna("triceps_maszyna", "Prostowanie ramion na maszynie (triceps)", "Ramiona", "Maszyna", False, "triceps extension machine"),
    Maszyna("dipy_maszyna", "Dipy na maszynie (siedząc)", "Ramiona", "Maszyna", False, "dip machine seated dips"),
    # Brzuch i grzbiet
    Maszyna("brzuch_maszyna", "Spięcia brzucha (ab crunch)", "Brzuch i grzbiet", "Maszyna", True, "ab crunch machine brzuch"),
    Maszyna("skrety_maszyna", "Skręty tułowia (rotary torso)", "Brzuch i grzbiet", "Maszyna", False, "torso rotation skosne"),
    Maszyna("lawka_rzymska", "Ławka rzymska (hiperekstensja)", "Brzuch i grzbiet", "Masa ciała", True,
            "roman chair hyperextension back extension prostowanie tulowia"),
    Maszyna("ghd", "GHD (glute-ham)", "Brzuch i grzbiet", "Maszyna", False, "glute ham developer ghr"),
    Maszyna("prostowanie_tulowia", "Prostowanie tułowia na maszynie", "Brzuch i grzbiet", "Maszyna", False, "back extension machine"),
    Maszyna("reverse_hyper", "Reverse hyper", "Brzuch i grzbiet", "Maszyna", False, "reverse hyperextension"),
    # Wyciągi i suwnica Smitha
    Maszyna("brama", "Brama / wyciągi regulowane (crossover)", "Wyciągi i suwnica Smitha", "Wyciąg", True,
            "crossover cable brama wyciag linki"),
    Maszyna("smith", "Suwnica Smitha", "Wyciągi i suwnica Smitha", "Suwnica Smitha", True, "smith machine"),
    # Drążek, poręcze, stanowiska
    Maszyna("drazek", "Drążek do podciągania", "Drążek, poręcze, stanowiska", "Masa ciała", True, "pull-up bar drazek podciaganie zwis"),
    Maszyna("porecze", "Poręcze (dipy)", "Drążek, poręcze, stanowiska", "Masa ciała", True, "dip station porecze dipy"),
    Maszyna("kapitanskie", "Kapitańskie krzesło (unoszenie nóg)", "Drążek, poręcze, stanowiska", "Masa ciała", True,
            "captain's chair unoszenie kolan nog"),
    Maszyna("trap_bar", "Sztanga trap bar (heksagonalna)", "Drążek, poręcze, stanowiska", "Sztanga trap bar", False, "trap bar hex bar"),
    Maszyna("sanie", "Sanie (prowler)", "Drążek, poręcze, stanowiska", "Sanie", False, "sled prowler sanki"),
    # Cardio
    Maszyna("bieznia", "Bieżnia", "Cardio", "Maszyna cardio", True, "treadmill bieznia"),
    Maszyna("orbitrek", "Orbitrek", "Cardio", "Maszyna cardio", True, "elliptical orbitrek"),
    Maszyna("rower", "Rower stacjonarny / spinningowy", "Cardio", "Maszyna cardio", True, "stationary bike spinning rower"),
    Maszyna("rower_poziomy", "Rower poziomy", "Cardio", "Maszyna cardio", False, "recumbent bike"),
    Maszyna("rower_powietrzny", "Rower powietrzny (Assault / Echo)", "Cardio", "Maszyna cardio", False, "air bike assault echo"),
    Maszyna("wioslarz", "Wioślarz (ergometr)", "Cardio", "Maszyna cardio", True, "rowing machine concept2 wioslarz"),
    Maszyna("skierg", "SkiErg", "Cardio", "Maszyna cardio", False, "ski erg"),
    Maszyna("schody", "Schody (stairmaster / step mill)", "Cardio", "Maszyna cardio", True, "stairmaster step mill schody"),
)
PO_ID = {m.id: m for m in KATALOG}


def _norma(t: str) -> str:
    t = (t or "").lower().replace("ł", "l")
    return "".join(z for z in unicodedata.normalize("NFKD", t) if not unicodedata.combining(z))


# Reguły: (wzorzec w nazwie lub aliasie, rodzaje sprzętu, dla których reguła działa (None = każdy), maszyny). Pierwsza pasująca wygrywa,
# więc od szczegółowych do ogólnych.
_M, _W, _S, _C, _MC = ("Maszyna",), ("Wyciąg",), ("Suwnica Smitha",), ("Maszyna cardio",), ("Masa ciała", "Guma", "Inny sprzęt", "")
REGULY: tuple[tuple[str, tuple | None, tuple[str, ...]], ...] = (
    # Cardio
    (r"biezni|treadmill", _C, ("bieznia",)),
    (r"orbitrek|elliptical", _C, ("orbitrek",)),
    (r"rower poziomy|recumbent", _C, ("rower_poziomy",)),
    (r"assault|echo|air bike", _C, ("rower_powietrzny",)),
    (r"rower|bike|bicycl|spinning", _C, ("rower",)),
    (r"wioslarz|rowing", _C, ("wioslarz",)),
    (r"skierg|ski erg", _C, ("skierg",)),
    (r"schod|stair|step mill", _C, ("schody",)),
    # Nogi
    (r"wspiecia.*suwnic|calf press", _M, ("suwnica", "suwnica_pozioma")),
    (r"suwnicy poziomej|horizontal leg press", _M, ("suwnica_pozioma",)),
    (r"suwnic|leg press", _M, ("suwnica", "suwnica_pozioma")),
    (r"hack", _M, ("hack",)),
    (r"wahadl|pendulum", _M, ("pendulum",)),
    (r"belt squat|z pasem", _M, ("belt_squat",)),
    (r"przysiad.*maszyn|machine squat|chair squat|martwy ciag na maszynie", _M, ("przysiad_dzwignia",)),
    (r"prostowanie (jednej )?nog", _M, ("prostowanie_nog",)),
    (r"uginanie nog leza|lying leg curl", _M, ("uginanie_lezac",)),
    (r"uginanie nogi stojac|standing leg curl", _M, ("uginanie_stojac",)),
    (r"uginanie nog", _M, ("uginanie_siedzac", "uginanie_lezac")),
    (r"odwodziciel|abductor", _M, ("odwodziciele",)),
    (r"przywodziciel|adductor", _M, ("przywodziciele",)),
    (r"hip thrust", _M, ("hip_thrust",)),
    (r"kickback", _M, ("kickback",)),
    (r"szrugsy na maszynie do lydek|calf-machine shoulder shrug", _M, ("lydki_stojac",)),
    (r"wspiecia.*siedzac|seated calf", _M, ("lydki_siedzac",)),
    (r"wspiecia|calf", _M, ("lydki_stojac",)),
    (r"glute-ham|glute ham", ("Maszyna",), ("ghd",)),
    (r"reverse hyper|odwrotne prostowanie tulowia", _M, ("reverse_hyper",)),
    (r"prostowanie tulowia", _M, ("prostowanie_tulowia", "lawka_rzymska")),
    # Klatka i barki
    (r"lawka skosna|incline", _M, ("chest_press_skos", "chest_press")),
    (r"wyciskanie na maszynie.*\(klatka\)|wyciskanie na maszynie (hammer|dzwigniowej) \((klatka|lawka ujemna)\)|chest press", _M,
     ("chest_press",)),
    (r"odwrocone rozpietki|rear delt|reverse.*fly", _M, ("reverse_fly", "butterfly")),
    (r"rozpietki|butterfly|pec deck", _M, ("butterfly",)),
    (r"nad glowe|barki\)|shoulder press", _M, ("shoulder_press",)),
    (r"wznosy bokiem|lateral raise", _M, ("wznosy_bokiem",)),
    # Plecy
    (r"wioslowanie.*maszyn|row machine|hammer strength row|iso row|high row", _M, ("wioslowanie_maszyna",)),
    (r"sciaganie na maszynie|plate loaded", _M, ("sciaganie_maszyna", "wyciag_gorny")),
    (r"podciaganie.*wspomag|assisted pull", _M, ("asysta",)),
    (r"dipy.*wspomag|assisted dip", _M, ("asysta",)),
    (r"pullover", _M, ("pullover_maszyna",)),
    (r"szrugsy|shrug", _M, ("szrugsy_maszyna",)),
    # Ramiona i brzuch
    (r"modlitewnik.*maszyn|preacher curls?$|machine preacher", _M, ("biceps_maszyna",)),
    (r"uginanie ramion|biceps", _M, ("biceps_maszyna",)),
    (r"prostowanie ramion|triceps", _M, ("triceps_maszyna",)),
    (r"dipy|dip machine", _M, ("dipy_maszyna",)),
    (r"spiec|crunch", _M, ("brzuch_maszyna",)),
    (r"skrety|rotation", _M, ("skrety_maszyna",)),
    # Wyciągi
    (r"triceps|pushdown", _W, ("brama", "wyciag_gorny")),
    (r"(sciaganie drazka|pulldown|lat pull|v-bar pulldown|sciaganie uchwytu)(?!.*prostymi)", _W, ("wyciag_gorny",)),
    ((r"wioslowanie (na wyciagu dolnym|jednoracz siedzac|jednoracz na wyciagu dolnym|siedzac na wyciagu)"
      r"|przyciaganie uchwytu wyciagu dolnego|seated cable row|seated one-arm cable"), _W, ("wyciag_dolny", "brama")),
    (r"pushdown|prostowanie ramion na wyciagu gorny|na wyciagu: drazek|sciaganie drazka na wyciagu|z lina zza glowy", _W,
     ("brama", "wyciag_gorny")),
    (r"modlitewnik", _W, ("brama", "modlitewnik")),
    (r"wyciag dolny|wyciagu dolnym|low pulley|low cable", _W, ("brama", "wyciag_dolny")),
    (r".", _W, ("brama",)),
    (r".", _S, ("smith",)),
    (r".", ("Landmine / T-bar",), ("tbar",)),
    (r".", ("Sztanga trap bar",), ("trap_bar",)),
    (r".", ("Sanie",), ("sanie",)),
    # Wolne ciężary na stanowisku i ćwiczenia z masą ciała
    (r"modlitewnik|preacher", ("Hantle", "Sztanga", "Sztanga łamana"), ("modlitewnik",)),
    (r"na podlodze|wzdluz tulowia|kolkach|ring dip|dipy na lawce|bench dip", _MC, ()),
    (r"unoszenie kolan na poreczach", _MC, ("porecze", "kapitanskie")),
    (r"kapitansk|captain", _MC, ("kapitanskie",)),
    (r"na poreczach|dipy na poreczach|dips|parallel bar", _MC, ("porecze",)),
    (r"podciagan|muscle-up|muscle up|chin|pull-?ups?\b|w zwisie|wiszenie|hanging|scapular", _MC, ("drazek",)),
    (r"lawce rzymskiej|hyperextension|back extension", _MC, ("lawka_rzymska", "ghd")),
    (r"glute-ham raise \(ghr\)", _MC, ("ghd",)),
)
_SKOMPILOWANE = tuple((re.compile(w), sp, ids) for w, sp, ids in REGULY)


def maszyny_cwiczenia(nazwa: str, sprzet: str, aliasy: str = "") -> tuple[str, ...]:
    """Maszyny (id), na których zrobisz ćwiczenie; pusta krotka: ćwiczenie nie wymaga konkretnej maszyny."""
    tekst = _norma(nazwa) + " | " + _norma(aliasy)
    for wzor, sprzety, ids in _SKOMPILOWANE:
        if sprzety is not None and (sprzet or "") not in sprzety:
            continue
        if wzor.search(tekst):
            return ids
    return ()


def nazwy(ids) -> list[str]:
    return [PO_ID[i].nazwa for i in ids if i in PO_ID]


def tekst_do_szukania(ids) -> str:
    """Nazwy i aliasy maszyn (bez polskich znaków), żeby wyszukiwarka ćwiczeń znajdowała je po nazwie maszyny."""
    return " ".join(_norma(PO_ID[i].nazwa + " " + PO_ID[i].aliasy) for i in ids if i in PO_ID)


def typowe() -> list[str]:
    return [m.id for m in KATALOG if m.typowa]


def szukaj(fraza: str) -> list[Maszyna]:
    """Maszyny pasujące do wpisanego tekstu (wszystkie słowa, po nazwie i aliasach, bez polskich znaków)."""
    slowa = _norma(fraza).split()
    if not slowa:
        return list(KATALOG)
    return [m for m in KATALOG if all(s in _norma(m.nazwa + " " + m.aliasy + " " + m.grupa) for s in slowa)]


def zbior_dozwolony(sprzet: set[str] | None, maszyny_wybrane: list[str]) -> set[str] | None:
    """Łączy rodzaje sprzętu i maszyny w jeden zbiór dla filtrów. Bez maszyn: zbiór sprzętu bez zmian (None = nie filtruj).
    Z maszynami: dokłada rodzaje sprzętu tych maszyn, znacznik i „m:<id>” dla każdej maszyny."""
    wybrane = [i for i in maszyny_wybrane if i in PO_ID]
    if not wybrane:
        return sprzet
    wynik = set(sprzet) if sprzet is not None else None
    if wynik is None:
        return {ZNACZNIK, *(PREFIKS + i for i in wybrane), "*"}
    wynik |= {PO_ID[i].sprzet for i in wybrane if PO_ID[i].sprzet}
    return wynik | {ZNACZNIK} | {PREFIKS + i for i in wybrane}


def dostepne(c: dict, dozwolony: set[str] | None) -> bool:
    """Czy ćwiczenie da się zrobić: rodzaj sprzętu jest w zbiorze („*” = każdy), a gdy zaznaczono maszyny, masz którąś z maszyn
    ćwiczenia (ćwiczenia bez przypisanej maszyny zależą tylko od sprzętu)."""
    if dozwolony is None:
        return True
    if "*" not in dozwolony and (c.get("sprzet") or "") not in dozwolony:
        return False
    ids = c.get("maszyny") or ()
    if ids and ZNACZNIK in dozwolony:
        return any(PREFIKS + i in dozwolony for i in ids)
    return True
