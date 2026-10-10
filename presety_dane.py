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
        "Nazwa": "Dół 1: Siła i masa", "Typ": "Dół Siła", "Kategoria": "Dół",
        "Cel": "Fundament siłowy oparty na wolnych ciężarach i ciężkich maszynach.",
        "Cwiczenia": [
            _c("Przysiad ze sztangą", "Nogi", 4, 5, 8,
               alternatywa="Przysiad na maszynie Hack Squat", wskazowka="Sztanga na karku"),
            _c("Wypychanie na suwnicy (obunóż)", "Nogi", 4, 10, 12,
               wskazowka="Suwnica 45°. Stopy niżej i węziej: mocniejsza praca czworogłowych"),
            _c("RDL (rumuński martwy ciąg)", "Nogi", 4, 8, 10,
               alternatywa="RDL na maszynie Smitha"),
            _c("Prostowanie nóg na maszynie", "Nogi", 3, 12, 15,
               wskazowka="Maksymalne spięcie mięśnia na górze na 1 sekundę"),
            _c("Uginanie nóg na maszynie", "Nogi", 3, 12, 15, wskazowka="Siedząc"),
            _c("Wspięcia na palce stojąc", "Nogi", 4, 15, 20, wskazowka="Na suwnicy lub maszynie"),
            _c("Allahy (spięcia brzucha na wyciągu)", "Brzuch", 3, 15, 20,
               alternatywa="Maszyna do brzuszków", wskazowka="Wyciąg górny"),
        ],
    },
    {
        "Nazwa": "Dół 2: Asymetria i detale", "Typ": "Dół Asymetria", "Kategoria": "Dół",
        "Cel": "Wyrównywanie różnic między prawą a lewą stroną, praca nad pośladkami i stabilizacją.",
        "Cwiczenia": [
            _c("Przysiad bułgarski", "Nogi", 4, 8, 10, "powt./nogę",
               alternatywa="Wykroki w miejscu na maszynie Smitha", wskazowka="Z hantlami"),
            _c("Martwy ciąg jednonóż z hantlą (single-leg RDL)", "Nogi", 3, 10, None, "powt./nogę"),
            _c("Uginanie nóg leżąc", "Nogi", 4, 10, 12, wskazowka="Leżąc przodem na maszynie"),
            _c("Odwodziciele na maszynie", "Nogi", 3, 15,
               wskazowka="Siedząc. Angażuje mięśnie odwodzące biodro, m.in. średni pośladek"),
            _c("Przywodziciele na maszynie", "Nogi", 3, 15, wskazowka="Siedząc"),
            _c("Wspięcia na palce siedząc", "Nogi", 4, 15, 20, wskazowka="Na maszynie (mięsień płaszczkowaty)"),
            _c("Deska (plank)", "Brzuch", 3, 45, 60, "s",
               alternatywa="Kółko do brzucha (ab roller)", wskazowka="Z talerzem na plecach"),
        ],
    },
    # ------------------------------------------------------------------ GÓRA
    {
        "Nazwa": "Góra 1: Push (klatka i barki)", "Typ": "Góra Push", "Kategoria": "Góra",
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
        "Nazwa": "Góra 2: Pull (plecy)", "Typ": "Góra Pull", "Kategoria": "Góra",
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
        "Nazwa": "Góra 3: Gęstość i hipertrofia", "Typ": "Góra Hipertrofia", "Kategoria": "Góra",
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
        "Nazwa": "Góra 4: Siła i stabilizacja", "Typ": "Góra Siła", "Kategoria": "Góra",
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
        "Nazwa": "Plyo 1: Eksplozja i moc", "Typ": "Plyo", "Kategoria": "Plyometria",
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
        "Nazwa": "Plyo 2: Zwinność i szybkość", "Typ": "Plyo", "Kategoria": "Plyometria",
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
        "Nazwa": "Cardio 1: Interwały na rowerze", "Typ": "Cardio", "Kategoria": "Cardio",
        "Cel": "Wytrzymałość beztlenowa i spalanie kalorii.",
        "Cwiczenia": [
            _c("Rozgrzewka (lekkie cardio)", "Cardio", 1, 10, None, "min", wskazowka="Lekko na rowerze"),
            _c("Rower Assault lub Echo: interwały", "Cardio", 10, 20, None, "s",
               wskazowka="20 s maksymalnego sprintu, potem 40 s bardzo luźnego pedałowania"),
            _c("Schłodzenie (wolne tempo)", "Cardio", 1, 5, None, "min", wskazowka="Bardzo wolne kręcenie"),
        ],
    },
    {
        "Nazwa": "Cardio 2: Schody (baza tlenowa)", "Typ": "Cardio", "Kategoria": "Cardio",
        "Cel": "Praca tlenowa o niskim udarze dla stawów, mocno angażuje pośladki i łydki.",
        "Cwiczenia": [
            _c("Maszyna schodowa (Stairmaster)", "Cardio", 1, 30, 45, "min",
               wskazowka="Jednostajne tempo w strefie tętna 2 (zakresy sprawdź w Garminie). "
                         "Sylwetka wyprostowana, nie wieszaj się na poręczach"),
        ],
    },
    {
        "Nazwa": "Cardio 3: Wioślarz", "Typ": "Cardio", "Kategoria": "Cardio",
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
    "Dół 1: Siła i masa": {"Wspięcia na palce stojąc", "Allahy (spięcia brzucha na wyciągu)"},
    "Dół 2: Asymetria i detale": {"Wspięcia na palce siedząc", "Deska (plank)"},
    "Góra 1: Push (klatka i barki)": {"Rozpiętki na bramie (wyciągi górne)",
                                      "Francuskie wyciskanie sztangi leżąc"},
    "Góra 2: Pull (plecy)": {"Ściąganie drążka wyciągu na prostych ramionach",
                             "Uginanie ramion z hantlami chwytem młotkowym"},
    "Góra 3: Gęstość i hipertrofia": {"Podciąganie sztangi wzdłuż tułowia (upright row)",
                                      "Szrugsy (kaptury)"},
    "Góra 4: Siła i stabilizacja": {"Wznosy ramion przodem z linką wyciągu dolnego",
                                    "Rotacje tułowia na wyciągu (woodchoppers)"},
    "Plyo 1: Eksplozja i moc": {"Slam balls (rzuty piłką o ziemię)", "Battle ropes (uderzenia linami)"},
    "Plyo 2: Zwinność i szybkość": {"Sprinty na bieżni (napędzanej nogami)",
                                    "Mountain climbers (bieg górski w podporze)"},
}

for _preset in PRESETY:
    _dodatki = DODATKI.get(_preset["Nazwa"], set())
    for _cw in _preset["Cwiczenia"]:
        _cw["Rola"] = "Dodatek" if _cw["Cwiczenie"] in _dodatki else "Główne"
    # główne na początku, dodatki na końcu (kolejność wewnątrz grup bez zmian)
    _preset["Cwiczenia"].sort(key=lambda c: c["Rola"] != "Główne")
    