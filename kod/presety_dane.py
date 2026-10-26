"""Presety treningów: dane startowe.

Wczytują się do bazy RAZ, przy pierwszym otwarciu strony Presety. Potem edytujesz je w aplikacji,
a ten plik niczego już nie nadpisuje.

Nazwy ćwiczeń są dopasowane do tych, które już masz w bazie (np. "Przysiad ze sztangą",
"RDL (rumuński martwy ciąg)"). Nowe ćwiczenia zostaną dopisane do bazy ćwiczeń z podaną partią.
"""
from __future__ import annotations


def _c(nazwa: str, partia: str, serie: int, od: int, do: int | None = None,
       jednostka: str = "powt.", alternatywa: str = "", wskazowka: str = "") -> dict:
    """Jedno ćwiczenie w presecie. Gdy podasz tylko 'od', zakres to jedna wartość (np. 10 powt.)."""
    return {
        "Cwiczenie": nazwa, "Partia": partia, "Serie": serie,
        "Powt_od": od, "Powt_do": do if do is not None else od,
        "Jednostka": jednostka, "Alternatywa": alternatywa, "Wskazowka": wskazowka,
    }


PRESETY = [
    # ------------------------------------------------------------------ DÓŁ
    {
        "Nazwa": "Dół siła: przysiad, RDL i suwnica", "Typ": "Dół Siła", "Kategoria": "Dół",
        "Cel": "Fundament siłowy oparty na wolnych ciężarach i ciężkich maszynach.",
        "Cwiczenia": [
            _c("Przysiad ze sztangą", "Czworogłowe", 4, 5, 8,
               alternatywa="Przysiad na maszynie Hack Squat", wskazowka="Sztanga na karku"),
            _c("Wypychanie na suwnicy (obunóż)", "Czworogłowe", 4, 10, 12,
               wskazowka="Suwnica 45°. Stopy niżej i węziej: mocniejsza praca czworogłowych"),
            _c("RDL (rumuński martwy ciąg)", "Dwugłowe uda", 4, 8, 10,
               alternatywa="RDL na maszynie Smitha"),
            _c("Prostowanie nóg na maszynie", "Czworogłowe", 3, 12, 15,
               wskazowka="Maksymalne spięcie mięśnia na górze na 1 sekundę"),
            _c("Uginanie nóg na maszynie", "Dwugłowe uda", 3, 12, 15, wskazowka="Siedząc"),
            _c("Wspięcia na palce stojąc", "Łydki", 4, 15, 20, wskazowka="Na suwnicy lub maszynie"),
            _c("Allahy (spięcia brzucha na wyciągu)", "Brzuch", 3, 15, 20,
               alternatywa="Maszyna do brzuszków", wskazowka="Wyciąg górny"),
        ],
    },
    {
        "Nazwa": "Dół jednonóż: bułgarski i pośladki", "Typ": "Dół Asymetria", "Kategoria": "Dół",
        "Cel": "Wyrównywanie różnic między prawą a lewą stroną, praca nad pośladkami i stabilizacją.",
        "Cwiczenia": [
            _c("Przysiad bułgarski", "Czworogłowe", 4, 8, 10, "powt./nogę",
               alternatywa="Wykroki w miejscu na maszynie Smitha", wskazowka="Z hantlami"),
            _c("Martwy ciąg jednonóż z hantlą (single-leg RDL)", "Dwugłowe uda", 3, 10, None, "powt./nogę"),
            _c("Uginanie nóg leżąc", "Dwugłowe uda", 4, 10, 12, wskazowka="Leżąc przodem na maszynie"),
            _c("Odwodziciele na maszynie", "Pośladki", 3, 15,
               wskazowka="Siedząc. Angażuje mięśnie odwodzące biodro, m.in. średni pośladek"),
            _c("Przywodziciele na maszynie", "Przywodziciele", 3, 15, wskazowka="Siedząc"),
            _c("Wspięcia na palce siedząc", "Łydki", 4, 15, 20, wskazowka="Na maszynie (mięsień płaszczkowaty)"),
            _c("Deska (plank)", "Brzuch", 3, 45, 60, "s",
               alternatywa="Kółko do brzucha (ab roller)", wskazowka="Z talerzem na plecach"),
        ],
    },
    # ------------------------------------------------------------------ GÓRA
    {
        "Nazwa": "Góra push: klatka i barki", "Typ": "Góra Push", "Kategoria": "Góra",
        "Cel": "Siła wypychania, nacisk na klatkę piersiową i przedni akton barku.",
        "Cwiczenia": [
            _c("Wyciskanie sztangi na ławce płaskiej", "Klatka", 4, 6, 8,
               alternatywa="Wyciskanie na maszynie (chest press)"),
            _c("Wyciskanie hantli na ławce skośnej dodatniej", "Klatka", 4, 8, 10,
               alternatywa="Maszyna Hammer Strength (skos)"),
            _c("Rozpiętki na bramie (wyciągi górne)", "Klatka", 3, 12, 15,
               alternatywa="Maszyna Pec-Dec"),
            _c("Wyciskanie hantli nad głowę siedząc", "Barki", 4, 8, 10,
               alternatywa="Maszyna Shoulder Press"),
            _c("Wznosy ramion bokiem z hantlami", "Barki", 4, 15,
               alternatywa="Maszyna do wznosów bokiem"),
            _c("Francuskie wyciskanie sztangi leżąc", "Triceps", 3, 10, 12),
            _c("Prostowanie ramion na wyciągu górnym z liną", "Triceps", 3, 12, 15),
        ],
    },
    {
        "Nazwa": "Góra pull: plecy i biceps", "Typ": "Góra Pull", "Kategoria": "Góra",
        "Cel": "Szerokość i grubość pleców oraz mocny biceps.",
        "Cwiczenia": [
            _c("Podciąganie na drążku", "Plecy", 4, 6, 10,
               alternatywa="Ściąganie drążka wyciągu górnego do klatki",
               wskazowka="Nachwyt lub chwyt neutralny"),
            _c("Wiosłowanie sztangą w opadzie tułowia", "Plecy", 4, 8, 10,
               alternatywa="Wiosłowanie na maszynie z oparciem klatki lub T-bar row"),
            _c("Przyciąganie uchwytu wyciągu dolnego siedząc", "Plecy", 3, 10, 12),
            _c("Ściąganie drążka wyciągu na prostych ramionach", "Plecy", 3, 12, 15),
            _c("Face pulls (przyciąganie liny do twarzy)", "Barki", 4, 15,
               alternatywa="Odwrotne rozpiętki na maszynie Pec-Dec",
               wskazowka="Zdrowie barków i tył barku"),
            _c("Uginanie ramion ze sztangą łamaną", "Biceps", 3, 10, 12,
               alternatywa="Modlitewnik na maszynie"),
            _c("Uginanie ramion z hantlami chwytem młotkowym", "Biceps", 3, 12),
        ],
    },
    {
        "Nazwa": "Góra objętość: hantle i maszyny", "Typ": "Góra Hipertrofia", "Kategoria": "Góra",
        "Cel": "Hantle i maszyny, izolacja i objętość (pompa mięśniowa).",
        "Cwiczenia": [
            _c("Wyciskanie hantli leżąc na podłodze (floor press)", "Klatka", 4, 8,
               alternatywa="Wyciskanie na ławce płaskiej na maszynie Smitha"),
            _c("Wiosłowanie jednorącz hantlą w oparciu o ławkę", "Plecy", 4, 8, 10, "powt./stronę"),
            _c("Wyciskanie Arnoldki siedząc", "Barki", 3, 10, 12),
            _c("Podciąganie sztangi wzdłuż tułowia (upright row)", "Barki", 3, 12,
               wskazowka="Sztanga lub linka wyciągu. Chwyt szeroki, łokcie nie wyżej niż do wysokości klatki"),
            _c("Dipy na maszynie (seated dip machine)", "Triceps", 3, 10, 12,
               alternatywa="Pompki na poręczach z gumą asekuracyjną"),
            _c("Uginanie ramion na wyciągu dolnym tyłem (Bayesian curl)", "Biceps", 3, 12, 15),
            _c("Szrugsy (kaptury)", "Plecy", 4, 15, wskazowka="Na maszynie lub ze sztangą"),
        ],
    },
    {
        "Nazwa": "Góra siła: ciężkie wyciskanie i wiosło", "Typ": "Góra Siła", "Kategoria": "Góra",
        "Cel": "Ciężkie ruchy wielostawowe i stabilizacja tułowia w górnych partiach.",
        "Cwiczenia": [
            _c("Wyciskanie żołnierskie (OHP ze sztangą stojąc)", "Barki", 4, 5, 8),
            _c("Ściąganie uchwytu neutralnego (V-grip) wyciągu górnego do klatki", "Plecy", 4, 8, 10),
            _c("Pompki na poręczach z obciążeniem", "Klatka", 3, 8, 10,
               alternatywa="Wyciskanie hantli na ławce ujemnej"),
            _c("Wiosłowanie Pendlaya", "Plecy", 4, 6, 8,
               wskazowka="Sztanga odkładana na ziemię po każdym powtórzeniu"),
            _c("Wznosy ramion przodem z linką wyciągu dolnego", "Barki", 3, 15),
            _c("Spacer farmera (obie ręce)", "Cały", 3, 30, 40, "m", wskazowka="Najcięższe hantle na siłowni"),
            _c("Rotacje tułowia na wyciągu (woodchoppers)", "Brzuch", 3, 12, None, "powt./stronę"),
        ],
    },
    # ------------------------------------------------------------------ PLYOMETRIA
    {
        "Nazwa": "Plyo moc: skoki i rzuty", "Typ": "Plyo", "Kategoria": "Plyometria",
        "Cel": "Moc i eksplozywność w pionie. Wykonuj świeży: liczy się jakość ruchu, nie zmęczenie.",
        "Cwiczenia": [
            _c("Wskoki na wysoką skrzynię (box jumps)", "Plyometria", 4, 5),
            _c("Skoki w dal z miejsca obunóż (broad jumps)", "Plyometria", 4, 5),
            _c("Rzuty piłką lekarską zza głowy o ścianę lub podłogę", "Plyometria", 3, 8),
            _c("Pompki plyometryczne (z oderwaniem rąk od ziemi)", "Plyometria", 3, 6, 8),
            _c("Wyskoki z przysiadu z lekkimi hantlami (jump squats)", "Plyometria", 3, 8),
            _c("Slam balls (rzuty piłką o ziemię)", "Plyometria", 3, 10),
            _c("Battle ropes (uderzenia linami)", "Plyometria", 4, 30, None, "s",
               wskazowka="Intensywna praca. To już kondycja, więc na końcu treningu"),
        ],
    },
    {
        "Nazwa": "Plyo zwinność: skoki boczne i sprint", "Typ": "Plyo", "Kategoria": "Plyometria",
        "Cel": "Zwinność, odbicie i szybkość. Wykonuj świeży: liczy się jakość ruchu, nie zmęczenie.",
        "Cwiczenia": [
            _c("Zeskoki z odbiciem (depth jumps)", "Plyometria", 4, 5,
               wskazowka="Skrzynia 30-40 cm. Jak najkrótszy kontakt stopy z ziemią"),
            _c("Skoki boczne przez płotki lub ławkę", "Plyometria", 4, 6, None, "powt./stronę"),
            _c("Skoki łyżwiarskie (skater jumps)", "Plyometria", 3, 10, None, "powt./stronę"),
            _c("Rotacyjne rzuty piłką lekarską o ścianę", "Plyometria", 3, 8, None, "powt./stronę"),
            _c("Wejścia na skrzynię z wyskokiem (step-up jumps)", "Plyometria", 3, 6, None, "powt./nogę",
               wskazowka="Jednonóż, z odbiciem"),
            _c("Sprinty na bieżni (napędzanej nogami)", "Plyometria", 5, 10, 15, "s",
               wskazowka="Bieżnia bez silnika, sprint z pochyloną sylwetką"),
            _c("Mountain climbers (bieg górski w podporze)", "Plyometria", 3, 40, None, "s",
               wskazowka="Ekstremalne tempo. To już kondycja, więc na końcu treningu"),
        ],
    },
    # ------------------------------------------------------------------ CARDIO
    {
        "Nazwa": "Cardio rower: interwały", "Typ": "Cardio", "Kategoria": "Cardio",
        "Cel": "Wytrzymałość beztlenowa i spalanie kalorii.",
        "Cwiczenia": [
            _c("Rozgrzewka (lekkie cardio)", "Cardio", 1, 10, None, "min", wskazowka="Lekko na rowerze"),
            _c("Rower Assault lub Echo: interwały", "Cardio", 10, 20, None, "s",
               wskazowka="20 s maksymalnego sprintu, potem 40 s bardzo luźnego pedałowania"),
            _c("Schłodzenie (wolne tempo)", "Cardio", 1, 5, None, "min", wskazowka="Bardzo wolne kręcenie"),
        ],
    },
    {
        "Nazwa": "Cardio schody: spokojne tempo", "Typ": "Cardio", "Kategoria": "Cardio",
        "Cel": "Praca tlenowa o niskim udarze dla stawów, mocno angażuje pośladki i łydki.",
        "Cwiczenia": [
            _c("Maszyna schodowa (Stairmaster)", "Cardio", 1, 30, 45, "min",
               wskazowka="Jednostajne tempo w strefie tętna 2 (zakresy sprawdź w Garminie). "
                         "Sylwetka wyprostowana, nie wieszaj się na poręczach"),
        ],
    },
    {
        "Nazwa": "Cardio wioślarz: odcinki z przerwą", "Typ": "Cardio", "Kategoria": "Cardio",
        "Cel": "Wytrzymałość siłowa, praca całego ciała (plecy, nogi, ramiona).",
        "Cwiczenia": [
            _c("Rozgrzewka techniczna (wioślarz)", "Cardio", 1, 5, None, "min"),
            _c("Wioślarz (Concept2)", "Cardio", 1, 500, None, "m",
               wskazowka="Szybko, potem 1 min przerwy. Ruch zaczynaj od pchnięcia nogami, "
                         "potem plecy i ramiona"),
            _c("Wioślarz (Concept2)", "Cardio", 1, 1000, None, "m",
               wskazowka="Średnie tempo, potem 2 min przerwy"),
            _c("Wioślarz (Concept2)", "Cardio", 1, 500, None, "m", wskazowka="Szybko. Koniec"),
        ],
    },
]


# ---------------------------------------------------------------------------
# Główne ćwiczenia i dodatki
# Każdy trening ma maksymalnie 5 ćwiczeń głównych. Pozostałe są "dodatkami"
# (do dołożenia, gdy masz siły i czas). Zamienniki sprzętowe są w polu "Alternatywa".
# Tu wpisujesz, które ćwiczenia są dodatkami; wszystkie pozostałe są głównymi.
# ---------------------------------------------------------------------------
DODATKI = {
    "Dół siła: przysiad, RDL i suwnica": {"Wspięcia na palce stojąc", "Allahy (spięcia brzucha na wyciągu)"},
    "Dół jednonóż: bułgarski i pośladki": {"Wspięcia na palce siedząc", "Deska (plank)"},
    "Góra push: klatka i barki": {"Rozpiętki na bramie (wyciągi górne)",
                                      "Francuskie wyciskanie sztangi leżąc"},
    "Góra pull: plecy i biceps": {"Ściąganie drążka wyciągu na prostych ramionach",
                             "Uginanie ramion z hantlami chwytem młotkowym"},
    "Góra objętość: hantle i maszyny": {"Podciąganie sztangi wzdłuż tułowia (upright row)",
                                      "Szrugsy (kaptury)"},
    "Góra siła: ciężkie wyciskanie i wiosło": {"Wznosy ramion przodem z linką wyciągu dolnego",
                                    "Rotacje tułowia na wyciągu (woodchoppers)"},
    "Plyo moc: skoki i rzuty": {"Slam balls (rzuty piłką o ziemię)", "Battle ropes (uderzenia linami)"},
    "Plyo zwinność: skoki boczne i sprint": {"Sprinty na bieżni (napędzanej nogami)",
                                    "Mountain climbers (bieg górski w podporze)"},
}

for _preset in PRESETY:
    _dodatki = DODATKI.get(_preset["Nazwa"], set())
    for _cw in _preset["Cwiczenia"]:
        _cw["Rola"] = "Dodatek" if _cw["Cwiczenie"] in _dodatki else "Główne"
    # główne na początku, dodatki na końcu (kolejność wewnątrz grup bez zmian)
    _preset["Cwiczenia"].sort(key=lambda c: c["Rola"] != "Główne")


# ---------------------------------------------------------------------------
# Dodatkowe pakiety presetów
# Wczytują się do bazy RAZ (każdy pakiet ma swoją flagę), także u kogoś, kto ma już swoje presety.
# Istniejących presetów nie ruszają. Wszystkie ćwiczenia są z bazy ćwiczeń.
# ---------------------------------------------------------------------------
def _d(*args, **kw) -> dict:
    """Ćwiczenie-dodatek (do dołożenia, gdy masz czas i siły)."""
    return {**_c(*args, **kw), "Rola": "Dodatek"}


def _g(*args, **kw) -> dict:
    return {**_c(*args, **kw), "Rola": "Główne"}


PAKIET_KROTKIE = [
    {
        "Nazwa": "Całe ciało A: 30 min, głównie hantle", "Typ": "Całe ciało", "Kategoria": "Całe ciało",
        "Cel": "Krótki trening na cały organizm, gdy masz pół godziny. Hantle i jedna maszyna.",
        "Cwiczenia": [
            _g("Przysiad z hantlami", "Czworogłowe", 3, 10, 12),
            _g("Wyciskanie hantli na ławce płaskiej", "Klatka", 3, 8, 12),
            _g("Ściąganie drążka szerokim chwytem", "Plecy", 3, 10, 12),
            _g("Martwy ciąg na prostych nogach z hantlami", "Dwugłowe uda", 3, 10, 12),
            _g("Wyciskanie hantli nad głowę siedząc", "Barki", 2, 10, 12),
            _d("Deska (plank)", "Brzuch", 2, 45, 60, "s"),
        ],
    },
    {
        "Nazwa": "Całe ciało B: 30 min, głównie maszyny", "Typ": "Całe ciało", "Kategoria": "Całe ciało",
        "Cel": "Drugi krótki trening na cały organizm: maszyny i wyciągi, bez dużego ustawiania sprzętu.",
        "Cwiczenia": [
            _g("Wypychanie na suwnicy (obunóż)", "Czworogłowe", 3, 10, 12),
            _g("Wyciskanie na maszynie (klatka)", "Klatka", 3, 10, 12),
            _g("Wiosłowanie na wyciągu dolnym: uchwyt V", "Plecy", 3, 10, 12),
            _g("Uginanie nóg leżąc", "Dwugłowe uda", 3, 12, 15),
            _g("Wznosy bokiem siedząc", "Barki", 2, 12, 15),
            _d("Allahy (spięcia brzucha na wyciągu)", "Brzuch", 2, 15, 20),
        ],
    },
    {
        "Nazwa": "Całe ciało 20 min: wersja awaryjna", "Typ": "Całe ciało", "Kategoria": "Całe ciało",
        "Cel": "Wersja awaryjna na dni bez czasu: po jednym ruchu na nogi, klatkę, plecy i barki. Lepsze to niż nic.",
        "Cwiczenia": [
            _g("Przysiad z hantlami", "Czworogłowe", 2, 12),
            _g("Pompki", "Klatka", 2, 10, 15),
            _g("Wiosłowanie dwoma hantlami w opadzie", "Plecy", 2, 12),
            _g("Wyciskanie hantli nad głowę stojąc", "Barki", 2, 10),
            _g("Deska (plank)", "Brzuch", 2, 45, 60, "s"),
        ],
    },
    {
        "Nazwa": "Góra 30 min: klatka, plecy, barki", "Typ": "Góra Szybka", "Kategoria": "Góra",
        "Cel": "Szybka góra ciała: klatka, plecy i barki w jednym krótkim bloku, na końcu ramiona jako dodatek.",
        "Cwiczenia": [
            _g("Wyciskanie hantli na ławce skośnej dodatniej", "Klatka", 3, 8, 10),
            _g("Ściąganie drążka do klatki piersiowej", "Plecy", 3, 10, 12),
            _g("Wyciskanie hantli nad głowę siedząc", "Barki", 3, 8, 10),
            _g("Wiosłowanie na wyciągu dolnym: uchwyt V", "Plecy", 3, 10, 12),
            _g("Wznosy bokiem siedząc", "Barki", 2, 12, 15),
            _d("Uginanie ramion z hantlami chwytem młotkowym", "Biceps", 2, 10, 12),
            _d("Prostowanie ramion na wyciągu górnym z liną", "Triceps", 2, 12, 15),
        ],
    },
    {
        "Nazwa": "Dół 30 min: nogi bez sztangi", "Typ": "Dół Szybki", "Kategoria": "Dół",
        "Cel": "Szybkie nogi: jedna pozycja na przód uda, jedna na tył, wykroki, łydki. Bez ciężkiej sztangi.",
        "Cwiczenia": [
            _g("Wypychanie na suwnicy (obunóż)", "Czworogłowe", 3, 10, 12),
            _g("RDL (rumuński martwy ciąg)", "Dwugłowe uda", 3, 8, 10),
            _g("Wykroki z hantlami", "Czworogłowe", 2, 10, None, "powt./nogę"),
            _g("Uginanie nóg leżąc", "Dwugłowe uda", 3, 12, 15),
            _g("Wspięcia na palce stojąc na maszynie", "Łydki", 3, 15, 20),
            _d("Mostek biodrowy", "Pośladki", 2, 15),
            _d("Deska (plank)", "Brzuch", 2, 45, 60, "s"),
        ],
    },
    {
        "Nazwa": "Całe ciało maszyny: bez wolnych ciężarów", "Typ": "Całe ciało Maszyny", "Kategoria": "Całe ciało",
        "Cel": "Cały trening tylko na maszynach, gdy na siłowni brakuje wolnych ciężarów albo nie chcesz asekuracji.",
        "Cwiczenia": [
            _g("Wypychanie na suwnicy (obunóż)", "Czworogłowe", 3, 10, 12),
            _g("Wyciskanie na maszynie (klatka)", "Klatka", 3, 10, 12),
            _g("Ściąganie na maszynie (lat pulldown, siedząc)", "Plecy", 3, 10, 12),
            _g("Wyciskanie na maszynie (barki)", "Barki", 3, 10, 12),
            _g("Uginanie nóg na maszynie", "Dwugłowe uda", 3, 12, 15),
            _d("Uginanie ramion na maszynie", "Biceps", 2, 12),
            _d("Prostowanie ramion na maszynie", "Triceps", 2, 12),
            _d("Maszyna do spięć brzucha", "Brzuch", 2, 15, 20),
        ],
    },
    {
        "Nazwa": "Całe ciało hantle: hantle i ławka", "Typ": "Całe ciało Hantle", "Kategoria": "Całe ciało",
        "Cel": "Cały trening tylko z hantlami (wystarczy ławka). Dobry na małą siłownię albo trening w domu.",
        "Cwiczenia": [
            _g("Przysiad bułgarski z hantlami", "Czworogłowe", 3, 8, 10, "powt./nogę"),
            _g("Wyciskanie hantli na ławce płaskiej", "Klatka", 3, 8, 12),
            _g("Wiosłowanie jednorącz hantlą w oparciu o ławkę", "Plecy", 3, 10, 12, "powt./stronę"),
            _g("Martwy ciąg na prostych nogach z hantlami", "Dwugłowe uda", 3, 10, 12),
            _g("Wyciskanie hantli nad głowę stojąc", "Barki", 3, 8, 12),
            _d("Uginanie ramion z hantlami naprzemiennie", "Biceps", 2, 10, 12),
            _d("Prostowanie ramion z hantlą zza głowy", "Triceps", 2, 10, 12),
            _d("Skłony boczne z hantlą", "Brzuch", 2, 12, 15, "powt./stronę"),
        ],
    },
    {
        "Nazwa": "Całe ciało dom: bez sprzętu", "Typ": "Całe ciało Bez sprzętu", "Kategoria": "Całe ciało",
        "Cel": "Trening na własnej masie ciała: w domu, w podróży, na dworze. Jeśli idzie za łatwo, zwolnij tempo i dodaj powtórzenia.",
        "Cwiczenia": [
            _g("Przysiad z własną masą ciała", "Czworogłowe", 3, 15, 20),
            _g("Pompki", "Klatka", 3, 8, 15),
            _g("Wykroki chodzone z własną masą ciała", "Czworogłowe", 3, 10, None, "powt./nogę"),
            _g("Mostek biodrowy", "Pośladki", 3, 15, 20),
            _g("Deska (plank)", "Brzuch", 3, 45, 60, "s"),
            _d("Martwy robak (dead bug)", "Brzuch", 2, 10),
            _d("Plank boczny", "Brzuch", 2, 30, 45, "s"),
            _d("Burpees", "Cały", 3, 8, 12),
        ],
    },
]


PAKIET_SPORT = [
    # ----------------------------------------------------------------- SIATKÓWKA
    {
        "Nazwa": "Siatkówka nogi: skok i moc", "Typ": "Sport Siatkówka", "Kategoria": "Siatkówka",
        "Cel": "Wyskok do bloku i ataku. Skoki na początku, kiedy jesteś świeży, potem siła nóg.",
        "Cwiczenia": [
            _g("Wskoki na wysoką skrzynię (box jumps)", "Plyometria", 3, 5),
            _g("Przysiad ze sztangą", "Czworogłowe", 4, 5, 6),
            _g("RDL (rumuński martwy ciąg)", "Dwugłowe uda", 3, 8),
            _g("Wykroki w tył z hantlami", "Czworogłowe", 3, 8, None, "powt./nogę"),
            _g("Wspięcia na palce stojąc na maszynie", "Łydki", 3, 12, 15),
            _d("Skoki przez płotki", "Plyometria", 3, 6),
            _d("Deska (plank)", "Brzuch", 2, 45, 60, "s"),
        ],
    },
    {
        "Nazwa": "Siatkówka góra: barki i rotacja", "Typ": "Sport Siatkówka", "Kategoria": "Siatkówka",
        "Cel": "Mocne i stabilne barki do ataku i zagrywki, siła pleców i skręt tułowia.",
        "Cwiczenia": [
            _g("Wiosłowanie jednorącz hantlą w oparciu o ławkę", "Plecy", 3, 10, None, "powt./stronę"),
            _g("Face pulls (przyciąganie liny do twarzy)", "Barki", 3, 15),
            _g("Wyciskanie hantli jednorącz chwytem neutralnym stojąc", "Barki", 3, 8, 10, "powt./stronę"),
            _g("Rzut piłki oburącz znad głowy", "Plyometria", 3, 8),
            _g("Rotacje tułowia na wyciągu (woodchoppers)", "Brzuch", 3, 10, 12, "powt./stronę"),
            _d("Rotacja zewnętrzna barku na wyciągu", "Barki", 2, 12, 15, "powt./stronę"),
            _d("Pallof press", "Brzuch", 2, 10, 12, "powt./stronę"),
        ],
    },
    # ----------------------------------------------------------------- KOSZYKÓWKA
    {
        "Nazwa": "Koszykówka nogi: wyskok i szybkość", "Typ": "Sport Koszykówka", "Kategoria": "Koszykówka",
        "Cel": "Wyskok, szybki start i zmiany kierunku. Skoki na początku, potem nogi jednostronnie.",
        "Cwiczenia": [
            _g("Skoki boczne przez pachołki", "Plyometria", 3, 8),
            _g("Wskoki na wysoką skrzynię (box jumps)", "Plyometria", 3, 5),
            _g("Przysiad bułgarski z hantlami", "Czworogłowe", 3, 8, None, "powt./nogę"),
            _g("Hip thrust", "Pośladki", 3, 8, 10),
            _g("Uginanie nóg leżąc", "Dwugłowe uda", 3, 10, 12),
            _d("Sprint wokół pachołka", "Plyometria", 4, 6),
            _d("Wspięcia na palce stojąc z hantlami", "Łydki", 3, 15),
        ],
    },
    {
        "Nazwa": "Koszykówka góra: kontakt i podanie", "Typ": "Sport Koszykówka", "Kategoria": "Koszykówka",
        "Cel": "Siła na kontakt pod koszem, mocne podanie i rzut. Klatka, plecy, barki i piłka lekarska.",
        "Cwiczenia": [
            _g("Wyciskanie hantli na ławce płaskiej", "Klatka", 4, 6, 8),
            _g("Wiosłowanie sztangą w opadzie tułowia", "Plecy", 4, 6, 8),
            _g("Wyciskanie hantli nad głowę stojąc", "Barki", 3, 8, 10),
            _g("Podanie piłki lekarskiej od klatki", "Plyometria", 3, 8),
            _g("Szrugsy z hantlami", "Plecy", 3, 12, 15),
            _d("Spacer farmera (obie ręce)", "Cały", 3, 30, 40, "m"),
            _d("Plank boczny", "Brzuch", 2, 30, 45, "s"),
        ],
    },
    # ----------------------------------------------------------------- TENIS
    {
        "Nazwa": "Tenis nogi: zwinność i rotacja", "Typ": "Sport Tenis", "Kategoria": "Tenis",
        "Cel": "Szybkie ruchy boczne, mocne nogi na jednej stronie i skręt tułowia do uderzenia.",
        "Cwiczenia": [
            _g("Skoki boczne przez pachołki", "Plyometria", 3, 8),
            _g("Wykroki w tył z hantlami", "Czworogłowe", 3, 8, None, "powt./nogę"),
            _g("Martwy ciąg jednonóż z hantlą (single-leg RDL)", "Dwugłowe uda", 3, 8, None, "powt./nogę"),
            _g("Rotacje tułowia na wyciągu (woodchoppers)", "Brzuch", 3, 10, 12, "powt./stronę"),
            _g("Odwodziciele na maszynie", "Pośladki", 3, 15),
            _d("Wspięcia na palce stojąc z hantlami", "Łydki", 3, 15),
            _d("Plank boczny", "Brzuch", 2, 30, 45, "s"),
        ],
    },
    {
        "Nazwa": "Tenis góra: barki i przedramię", "Typ": "Sport Tenis", "Kategoria": "Tenis",
        "Cel": "Barki i plecy do serwisu i forhendu, mocny chwyt, rotacja tułowia.",
        "Cwiczenia": [
            _g("Wiosłowanie jednorącz siedząc na wyciągu", "Plecy", 3, 10, 12, "powt./stronę"),
            _g("Face pulls (przyciąganie liny do twarzy)", "Barki", 3, 15),
            _g("Rotacja zewnętrzna barku z hantlą", "Barki", 3, 12, 15, "powt./stronę"),
            _g("Wyciskanie hantli jednorącz na ławce", "Klatka", 3, 10, None, "powt./stronę"),
            _g("Skręty rosyjskie (russian twist)", "Brzuch", 3, 20),
            _d("Uginanie nadgarstków z hantlami podchwytem", "Przedramiona", 3, 15),
            _d("Uginanie nadgarstków z hantlami nachwytem", "Przedramiona", 3, 15),
        ],
    },
    # ----------------------------------------------------------------- PŁYWANIE
    {
        "Nazwa": "Pływanie plecy: ściąganie i triceps", "Typ": "Sport Pływanie", "Kategoria": "Pływanie",
        "Cel": "Trening na sucho pod pływanie: siła ściągania, szeroki grzbiet i tricepsy do fazy pchnięcia.",
        "Cwiczenia": [
            _g("Ściąganie drążka szerokim chwytem", "Plecy", 4, 8, 10),
            _g("Ściąganie drążka wyciągu na prostych ramionach", "Plecy", 3, 12),
            _g("Wiosłowanie na wyciągu dolnym: uchwyt V", "Plecy", 3, 10, 12),
            _g("Face pulls (przyciąganie liny do twarzy)", "Barki", 3, 15),
            _g("Prostowanie ramion na wyciągu górnym z liną", "Triceps", 3, 12, 15),
            _d("Pullover z hantlą na prostych ramionach", "Klatka", 3, 12),
            _d("Podciąganie na drążku", "Plecy", 3, 5, 8),
        ],
    },
    {
        "Nazwa": "Pływanie tułów: brzuch i nogi", "Typ": "Sport Pływanie", "Kategoria": "Pływanie",
        "Cel": "Sztywny tułów i mocne nogi do nawrotów i kopnięć. Dużo pracy na brzuch i pośladki.",
        "Cwiczenia": [
            _g("Wypychanie na suwnicy (obunóż)", "Czworogłowe", 3, 12),
            _g("Hip thrust", "Pośladki", 3, 10, 12),
            _g("Pallof press", "Brzuch", 3, 10, 12, "powt./stronę"),
            _g("Hollow body hold", "Brzuch", 3, 20, 30, "s"),
            _g("Plank boczny", "Brzuch", 3, 30, 45, "s"),
            _d("Scyzoryk (brzuszki z nogami)", "Brzuch", 2, 12),
            _d("Wspięcia na palce siedząc", "Łydki", 3, 15),
        ],
    },
    # ----------------------------------------------------------------- PIŁKA NOŻNA
    {
        "Nazwa": "Piłka nożna nogi: moc i sprint", "Typ": "Sport Piłka nożna", "Kategoria": "Piłka nożna",
        "Cel": "Siła nóg pod sprint i starcie, mocne tylne uda i przywodziciele. Skoki na początku, gdy jesteś świeży.",
        "Cwiczenia": [
            _g("Skoki przez płotki", "Plyometria", 3, 6),
            _g("Przysiad ze sztangą", "Czworogłowe", 4, 5, 6),
            _g("RDL (rumuński martwy ciąg)", "Dwugłowe uda", 3, 8),
            _g("Wykroki w tył z hantlami", "Czworogłowe", 3, 8, None, "powt./nogę"),
            _g("Przywodziciele na maszynie", "Przywodziciele", 3, 12, 15),
            _d("Sprint wokół pachołka", "Plyometria", 4, 6),
            _d("Odwodziciele na maszynie", "Pośladki", 3, 15),
        ],
    },
    {
        "Nazwa": "Piłka nożna tułów: zwinność i stabilizacja", "Typ": "Sport Piłka nożna", "Kategoria": "Piłka nożna",
        "Cel": "Zmiany kierunku, praca na jednej nodze i stabilny tułów do pojedynków.",
        "Cwiczenia": [
            _g("Skoki boczne przez pachołki", "Plyometria", 3, 8),
            _g("Przysiad bułgarski z hantlami", "Czworogłowe", 3, 8, None, "powt./nogę"),
            _g("Uginanie nóg na piłce", "Dwugłowe uda", 3, 10),
            _g("Pallof press", "Brzuch", 3, 10, 12, "powt./stronę"),
            _g("Wiosłowanie jednorącz hantlą w oparciu o ławkę", "Plecy", 3, 10, None, "powt./stronę"),
            _d("Plank boczny", "Brzuch", 2, 30, 45, "s"),
            _d("Wyciskanie hantli na ławce płaskiej", "Klatka", 3, 8, 10),
        ],
    },
    # ----------------------------------------------------------------- BIEGANIE
    {
        "Nazwa": "Bieganie nogi: siła jednonóż", "Typ": "Sport Bieganie", "Kategoria": "Bieganie",
        "Cel": "Siła nóg i pośladków na jednej nodze. Mocniejsze nogi pomagają utrzymać tempo na długim dystansie.",
        "Cwiczenia": [
            _g("Przysiad bułgarski z hantlami", "Czworogłowe", 3, 8, None, "powt./nogę"),
            _g("Martwy ciąg jednonóż z hantlą (single-leg RDL)", "Dwugłowe uda", 3, 8, None, "powt./nogę"),
            _g("Wejścia na podwyższenie (step-up)", "Czworogłowe", 3, 10, None, "powt./nogę"),
            _g("Mostek biodrowy jednonóż", "Pośladki", 3, 10, None, "powt./nogę"),
            _g("Wspięcia na palce stojąc z hantlami", "Łydki", 3, 15),
            _d("Odwodziciele na maszynie", "Pośladki", 3, 15),
            _d("Deska (plank)", "Brzuch", 2, 45, 60, "s"),
        ],
    },
    {
        "Nazwa": "Bieganie tułów: stabilizacja", "Typ": "Sport Bieganie", "Kategoria": "Bieganie",
        "Cel": "Stabilny tułów i biodra, żeby sylwetka nie siadała pod koniec biegu. Krótki trening, można dołożyć po lekkim biegu.",
        "Cwiczenia": [
            _g("Hip thrust", "Pośladki", 3, 10, 12),
            _g("Pallof press", "Brzuch", 3, 10, 12, "powt./stronę"),
            _g("Plank boczny", "Brzuch", 3, 30, 45, "s"),
            _g("Martwy robak (dead bug)", "Brzuch", 3, 10),
            _g("Szybkie skipy", "Plyometria", 3, 20, 30, "s"),
            _d("Wiosłowanie jednorącz hantlą w oparciu o ławkę", "Plecy", 3, 10, None, "powt./stronę"),
            _d("Hollow body hold", "Brzuch", 2, 20, 30, "s"),
        ],
    },
]


# Nazwa flagi w tabeli ustawienia -> lista presetów pakietu
# Dyscypliny sportowe: każda ma własną kategorię (filtr na stronie Presety); „Sport” to stara wspólna kategoria
SPORTY = ("Siatkówka", "Koszykówka", "Tenis", "Pływanie", "Piłka nożna", "Bieganie")

PAKIETY = {
    "presety_pakiet_krotkie_v1": PAKIET_KROTKIE,
    "presety_pakiet_sport_v1": PAKIET_SPORT,
}


# Dawne nazwy -> obecne. Przy starcie aplikacji nazwy w bazie (presety, historia, plan) są zamieniane RAZ.
PRZEMIANOWANIA = {
    "Dół 1: Siła i masa": "Dół siła: przysiad, RDL i suwnica",
    "Dół 2: Asymetria i detale": "Dół jednonóż: bułgarski i pośladki",
    "Góra 1: Push (klatka i barki)": "Góra push: klatka i barki",
    "Góra 2: Pull (plecy)": "Góra pull: plecy i biceps",
    "Góra 3: Gęstość i hipertrofia": "Góra objętość: hantle i maszyny",
    "Góra 4: Siła i stabilizacja": "Góra siła: ciężkie wyciskanie i wiosło",
    "Plyo 1: Eksplozja i moc": "Plyo moc: skoki i rzuty",
    "Plyo 2: Zwinność i szybkość": "Plyo zwinność: skoki boczne i sprint",
    "Cardio 1: Interwały na rowerze": "Cardio rower: interwały",
    "Cardio 2: Schody (baza tlenowa)": "Cardio schody: spokojne tempo",
    "Cardio 3: Wioślarz": "Cardio wioślarz: odcinki z przerwą",
    "Całe ciało A: 30 min": "Całe ciało A: 30 min, głównie hantle",
    "Całe ciało B: 30 min": "Całe ciało B: 30 min, głównie maszyny",
    "Całe ciało: minimum 20 min": "Całe ciało 20 min: wersja awaryjna",
    "Góra szybka: 30 min": "Góra 30 min: klatka, plecy, barki",
    "Dół szybki: 30 min": "Dół 30 min: nogi bez sztangi",
    "Maszyny: całe ciało": "Całe ciało maszyny: bez wolnych ciężarów",
    "Hantle: całe ciało": "Całe ciało hantle: hantle i ławka",
    "Bez sprzętu: całe ciało": "Całe ciało dom: bez sprzętu",
    "Siatkówka 1: Skok i moc nóg": "Siatkówka nogi: skok i moc",
    "Siatkówka 2: Barki, plecy i rotacja": "Siatkówka góra: barki i rotacja",
    "Koszykówka 1: Wyskok i szybkość": "Koszykówka nogi: wyskok i szybkość",
    "Koszykówka 2: Góra ciała i kontakt": "Koszykówka góra: kontakt i podanie",
    "Tenis 1: Nogi, zwinność i rotacja": "Tenis nogi: zwinność i rotacja",
    "Tenis 2: Barki, plecy i przedramię": "Tenis góra: barki i przedramię",
    "Pływanie 1: Plecy i ściąganie": "Pływanie plecy: ściąganie i triceps",
    "Pływanie 2: Tułów i nogi": "Pływanie tułów: brzuch i nogi",
    "Piłka nożna 1: Moc nóg i sprint": "Piłka nożna nogi: moc i sprint",
    "Piłka nożna 2: Zwinność i tułów": "Piłka nożna tułów: zwinność i stabilizacja",
    "Bieganie 1: Nogi biegacza": "Bieganie nogi: siła jednonóż",
    "Bieganie 2: Tułów i stabilizacja": "Bieganie tułów: stabilizacja",
}
