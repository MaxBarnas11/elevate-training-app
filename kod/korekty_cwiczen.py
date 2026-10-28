"""Poprawki bazy ćwiczeń po ręcznym przeglądzie (28.10.2026): sprzęt, partie, typ ruchu, ukrycie dziwnych i zdublowanych ćwiczeń,
mylące nazwy, brakujące maszyny i nowy rodzaj sprzętu „Talerz”.

Bezpieczne dla historii i własnych zmian: każda poprawka ma starą wartość i zmienia pole tylko wtedy, gdy w bazie wciąż jest ta
stara wartość (jeśli sam coś zmieniłeś, np. partię w Postępach, zostaje Twoje). Nazwy zmieniamy tylko ćwiczeniom, których
nigdzie nie używasz (historia, presety, trening w toku, ulubione, notatka); w innym razie nowa nazwa trafia do wyszukiwania jako
alias. Przed pierwszym zastosowaniem powstaje kopia bazy. Jednorazowe (flaga w tabeli ustawienia).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

FLAGA = "korekty_cwiczen_v1"

# (nazwa, kolumna, stara wartość, nowa wartość); pusty tekst w Typ oznacza brak typu
ZMIANY: tuple[tuple[str, str, object, object], ...] = (
    ('Wznosy hantli przed siebie', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Wznosy hantli przed siebie', 'Partia_dod', 'Biceps', ''),
    ('Rotacja wewnętrzna barku na wyciągu', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Odwrócone rozpiętki z gumą', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Odwrócone rozpiętki z gumą', 'Partia_dod', 'Plecy górne,Triceps', 'Plecy górne'),
    ('Rotacja zewnętrzna barku z gumą', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Częściowe powtórzenia (power partials)', 'Partia', 'Barki przód', 'Barki bok'),
    ('Wznosy hantli na ławce skośnej', 'Partia_dod', 'Triceps', ''),
    ('Wznosy bokiem i przodem', 'Partia_dod', 'Plecy górne', 'Barki przód'),
    ('Battle ropes (uderzenia linami)', 'Jednostka_dom', 'powt.', 's'),
    ('Battle ropes (uderzenia linami)', 'Typ', 'Wielostawowe', ''),
    ('Wznosy talerza przed siebie', 'Sprzet', 'Inny sprzęt', 'Talerz'),
    ('Kierowca (obroty talerza)', 'Sprzet', 'Sztanga', 'Talerz'),
    ('Wyciskanie landmine jednorącz (jammer)', 'Sprzet', 'Sztanga', 'Landmine / T-bar'),
    ('Uginanie ramion na wyciągach górnych', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Uginanie ramion przy tułowiu (drag curl)', 'Sprzet', 'Sanie', 'Sztanga'),
    ('Uginanie ramion z talerzem nachwytem', 'Sprzet', 'Inny sprzęt', 'Talerz'),
    ('Uginanie ramion ze sztangą łamaną wąskim chwytem', 'Sprzet', 'Sztanga', 'Sztanga łamana'),
    ('Uginanie ramion na wyciągu dolnym tyłem (Bayesian curl)', 'Sprzet', '', 'Wyciąg'),
    ('Uginanie ramion na wyciągu dolnym tyłem (Bayesian curl)', 'Typ', '', 'Izolowane'),
    ('Uginanie ramion na wyciągu dolnym tyłem (Bayesian curl)', 'Rodzaj', '', 'Siłowe'),
    ('Brzuszki z obciążeniem i gumą', 'Sprzet', 'Inny sprzęt', 'Guma'),
    ('Brzuszki z obciążeniem i gumą', 'Ukryte', 0, 1),
    ('Otis-up', 'Sprzet', 'Inny sprzęt', 'Talerz'),
    ('Skręty tułowia z talerzem', 'Sprzet', 'Inny sprzęt', 'Talerz'),
    ('Unoszenie kolan na poręczach', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Spell caster', 'Ukryte', 0, 1),
    ('Gorilla chin/crunch', 'Ukryte', 0, 1),
    ('Unoszenie bioder na suwnicy Smitha', 'Ukryte', 0, 1),
    ('Nożyce poziome (flutter kicks)', 'Partia', 'Pośladki', 'Brzuch'),
    ('Nożyce poziome (flutter kicks)', 'Partia_dod', 'Dwugłowe uda', ''),
    ('Nożyce poziome (flutter kicks)', 'Typ', 'Wielostawowe', ''),
    ('Bieg / marsz w terenie', 'Sprzet', 'Maszyna cardio', 'Masa ciała'),
    ('Skakanka', 'Sprzet', 'Maszyna cardio', 'Inny sprzęt'),
    ('Podwójne skoki na skakance (double under)', 'Sprzet', 'Masa ciała', 'Inny sprzęt'),
    ('Łyżwiarstwo / rolki', 'Sprzet', 'Maszyna cardio', 'Inny sprzęt'),
    ('Jazda na rowerze (na zewnątrz)', 'Sprzet', 'Masa ciała', 'Inny sprzęt'),
    ('Bieg na zewnątrz', 'Sprzet', '', 'Masa ciała'),
    ('Bieg na zewnątrz', 'Rodzaj', '', 'Cardio'),
    ('Bieg na zewnątrz', 'Jednostka_dom', '', 'min'),
    ('Marsz pod górę na bieżni', 'Sprzet', '', 'Maszyna cardio'),
    ('Marsz pod górę na bieżni', 'Rodzaj', '', 'Cardio'),
    ('Marsz pod górę na bieżni', 'Jednostka_dom', '', 'min'),
    ('Rower Assault lub Echo: interwały', 'Sprzet', '', 'Maszyna cardio'),
    ('Rower Assault lub Echo: interwały', 'Rodzaj', '', 'Cardio'),
    ('Rower Assault lub Echo: interwały', 'Jednostka_dom', '', 'min'),
    ('Rozgrzewka techniczna (wioślarz)', 'Sprzet', '', 'Maszyna cardio'),
    ('Rozgrzewka techniczna (wioślarz)', 'Rodzaj', '', 'Cardio'),
    ('Rozgrzewka techniczna (wioślarz)', 'Jednostka_dom', '', 'min'),
    ('Kettlebell swing', 'Sprzet', '', 'Kettlebell'),
    ('Kettlebell swing', 'Rodzaj', '', 'Siłowe'),
    ('Spacer farmera jednorącz', 'Sprzet', '', 'Hantle'),
    ('Spacer farmera jednorącz', 'Rodzaj', '', 'Siłowe'),
    ('Zgięcie biodra z gumą', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Wykroki chodzone z własną masą ciała', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Przysiad jednonóż na wysoką skrzynię', 'Sprzet', 'Inny sprzęt', 'Skrzynia plyo'),
    ('Przysiad z obciążeniem', 'Ukryte', 0, 1),
    ('Sprint z wykroków', 'Ukryte', 0, 1),
    ('Przysiad z talerzem (plate movers)', 'Ukryte', 0, 1),
    ('Sissy squat z obciążeniem', 'Sprzet', 'Sztanga', 'Talerz'),
    ('Przywodzenie nogi na wyciągu', 'Partia', 'Czworogłowe', 'Przywodziciele'),
    ('Manualny opór na dwugłowe leżąc na brzuchu', 'Ukryte', 0, 1),
    ('Uginanie nóg siedząc z gumą', 'Sprzet', 'Inny sprzęt', 'Guma'),
    ('Uginanie nóg na podłodze (glute-ham raise)', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Wykrok z przekładaniem piłki', 'Partia', 'Dwugłowe uda', 'Czworogłowe'),
    ('Wykrok z przekładaniem piłki', 'Partia_dod', 'Łydki,Pośladki,Czworogłowe', 'Pośladki,Dwugłowe uda'),
    ('Martwy ciąg', 'Partia_dod', 'Łydki,Przedramiona,Pośladki,Dwugłowe uda,Czworogłowe', 'Pośladki,Plecy dolne,Czworogłowe,Przedramiona'),
    ('Przysiad na jednej nodze na skrzynię', 'Sprzet', '', 'Skrzynia plyo'),
    ('Przysiad na jednej nodze na skrzynię', 'Rodzaj', '', 'Siłowe'),
    ('Wyciskanie na suwnicy na jedną nogę', 'Sprzet', '', 'Maszyna'),
    ('Wyciskanie na suwnicy na jedną nogę', 'Rodzaj', '', 'Siłowe'),
    ('Wykroki chodzone', 'Sprzet', '', 'Masa ciała'),
    ('Wykroki chodzone', 'Rodzaj', '', 'Siłowe'),
    ('Wykroki w miejscu', 'Sprzet', '', 'Masa ciała'),
    ('Wykroki w miejscu', 'Rodzaj', '', 'Siłowe'),
    ('Martwy ciąg jednonóż z hantlą (single-leg RDL)', 'Sprzet', '', 'Hantle'),
    ('Martwy ciąg jednonóż z hantlą (single-leg RDL)', 'Rodzaj', '', 'Siłowe'),
    ('Martwy ciąg jednonóż z hantlą (single-leg RDL)', 'Typ', '', 'Wielostawowe'),
    ('Glute-ham raise (GHR)', 'Rodzaj', 'Trójbój', 'Siłowe'),
    ('Hip thrust', 'Rodzaj', 'Trójbój', 'Siłowe'),
    ('Mostek biodrowy ze sztangą', 'Rodzaj', 'Trójbój', 'Siłowe'),
    ('Przysiad w klęku', 'Ukryte', 0, 1),
    ('Monster walk z gumą', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Wyprost biodra z gumą', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Odwodzenie nogi w tył (kickback)', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Mostek biodrowy na piłce', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Równowaga w pochyleniu (jaskółka)', 'Ukryte', 0, 1),
    ('Hip thrust na jednej nodze', 'Sprzet', '', 'Masa ciała'),
    ('Hip thrust na jednej nodze', 'Rodzaj', '', 'Siłowe'),
    ('Wykroki w tył', 'Sprzet', '', 'Masa ciała'),
    ('Wykroki w tył', 'Rodzaj', '', 'Siłowe'),
    ('Trening na platformie balansowej', 'Ukryte', 0, 1),
    ('Wspięcia na palce stojąc z bujaniem', 'Ukryte', 0, 1),
    ('Pompki na poręczach z obciążeniem', 'Sprzet', '', 'Masa ciała'),
    ('Pompki na poręczach z obciążeniem', 'Rodzaj', '', 'Siłowe'),
    ('Pompki na poręczach z obciążeniem', 'Typ', '', 'Wielostawowe'),
    ('Pompki na poręczach z obciążeniem', 'Partia_dod', '', 'Triceps,Barki przód'),
    ('Rozpiętki z gumami (crossover)', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Rozpiętki z gumami (crossover)', 'Partia_dod', 'Biceps,Barki przód', 'Barki przód'),
    ('Pullover z hantlą na prostych ramionach', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Pullover z hantlą na ugiętych ramionach', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Pullover ze sztangą na ławce ujemnej', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Pullover ze sztangą na ugiętych ramionach', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Wznos i pullover ze sztangą', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Rozpiętki z hantlami na ławce skośnej', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Rozpiętki z hantlami na ławce skośnej ujemnej', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Rozpiętki z hantlami na ławce skośnej z rotacją', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Wznosy hantli dookoła świata (around the worlds)', 'Typ', 'Wielostawowe', 'Izolowane'),
    ('Dipy na poręczach (klatka)', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Pompki na poręczach (klatka, pochylony tułów)', 'Ukryte', 0, 1),
    ('Pompki na skosie ujemnym (nogi wyżej)', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Pompki na skosie ujemnym (nogi wyżej)', 'Ukryte', 0, 1),
    ('Svend press (ściskanie talerzy)', 'Sprzet', 'Inny sprzęt', 'Talerz'),
    ('Wycieraczki izometryczne', 'Ukryte', 0, 1),
    ('Rozpiętki na własnym ciężarze', 'Ukryte', 0, 1),
    ('Wyciskanie sztangi leżąc z gumami', 'Sprzet', 'Guma', 'Sztanga'),
    ('Wyciskanie sztangi leżąc z gumami', 'Rodzaj', 'Siłowe', 'Trójbój'),
    ('Wyciskanie sztangi leżąc z gumami', 'Ukryte', 0, 1),
    ('Szrugsy (kaptury)', 'Sprzet', '', 'Sztanga'),
    ('Szrugsy (kaptury)', 'Rodzaj', '', 'Siłowe'),
    ('Szrugsy (kaptury)', 'Typ', '', 'Izolowane'),
    ('Wiosłowanie Pendlaya', 'Sprzet', '', 'Sztanga'),
    ('Wiosłowanie Pendlaya', 'Rodzaj', '', 'Siłowe'),
    ('Wiosłowanie Pendlaya', 'Typ', '', 'Wielostawowe'),
    ('Wiosłowanie na maszynie', 'Sprzet', '', 'Maszyna'),
    ('Wiosłowanie na maszynie', 'Rodzaj', '', 'Siłowe'),
    ('Wiszenie na drążku', 'Sprzet', '', 'Masa ciała'),
    ('Wiszenie na drążku', 'Rodzaj', '', 'Siłowe'),
    ('Wiszenie na drążku', 'Typ', 'Wielostawowe', ''),
    ('Wiszenie na drążku', 'Jednostka_dom', '', 's'),
    ('London bridges', 'Ukryte', 0, 1),
    ('Wiosłowanie pod drążkiem', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Wiosłowanie pod drążkiem (własny ciężar)', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Wiosłowanie pod drążkiem (własny ciężar)', 'Ukryte', 0, 1),
    ('Wiosłowanie kettlebell naprzemiennie', 'Typ', 'Izolowane', 'Wielostawowe'),
    ('Wiosłowanie z sankami', 'Ukryte', 0, 1),
    ('Wiosłowanie leżąc ze sztangą łamaną', 'Typ', 'Izolowane', 'Wielostawowe'),
    ('Wiosłowanie leżąc ze sztangą łamaną', 'Ukryte', 0, 1),
    ('Wiosłowanie na ławce skośnej (na brzuchu)', 'Typ', 'Izolowane', 'Wielostawowe'),
    ('Prostowanie ramion na wyciągu w skłonie', 'Partia', 'Plecy górne', 'Plecy szerokie'),
    ('Prostowanie ramion na wyciągu w skłonie', 'Partia_dod', 'Plecy szerokie', 'Plecy górne'),
    ('Prostowanie tułowia na ławce rzymskiej', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Muscle-up', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Muscle-up z kippingiem', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Muscle-up z kippingiem', 'Ukryte', 0, 1),
    ("Podciąganie Rocky'ego", 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ("Podciąganie Rocky'ego", 'Ukryte', 0, 1),
    ('Podciąganie chwytem mieszanym', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Podciąganie do mostka (Gironda)', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Podciąganie jednorącz', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Podciąganie z gumą wspomagającą', 'Sprzet', 'Inny sprzęt', 'Guma'),
    ('Podciąganie z obciążeniem', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Podciąganie z przejściem z boku na bok', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Podciąganie z przejściem z boku na bok', 'Ukryte', 0, 1),
    ('Podciąganie łopatek w zwisie', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Wspinaczka po linie', 'Ukryte', 0, 1),
    ('Bieg krzyżowy (carioca)', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Mountain climbers (bieg górski w podporze)', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Odbicie z jednej nogi', 'Sprzet', 'Inny sprzęt', 'Skrzynia plyo'),
    ('Pompki z zeskokiem (drop push)', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Pompki z zeskokiem z podwyższenia', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Progresja skoków na jednej nodze', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Seria „pazur” (moving claw)', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Skok boczny na jednej nodze', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Skok krokowy na jednej nodze', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Skok krokowy z krzyżowaniem', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Skok w dal bokiem', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Skoki boczne ze sprintem', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Skoki diagonalne z nogi na nogę', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Sprint z wskokami na ławkę', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Szybki skok (quick leap)', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Technika startu liniowego (3 fazy)', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Zeskok i skok (depth jump leap)', 'Sprzet', 'Inny sprzęt', 'Skrzynia plyo'),
    ('Zeskok i skok liniowy (depth jump)', 'Sprzet', 'Inny sprzęt', 'Skrzynia plyo'),
    ('Ćwiczenie przyspieszenia przy ścianie', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Ćwiczenie ramion w klęku', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Uderzenia młotem', 'Sprzet', 'Sanie', 'Inny sprzęt'),
    ('Rotacyjne rzuty piłką lekarską o ścianę', 'Sprzet', '', 'Piłka lekarska'),
    ('Rotacyjne rzuty piłką lekarską o ścianę', 'Rodzaj', '', 'Plyometria'),
    ('Rzuty piłką lekarską zza głowy o ścianę lub podłogę', 'Sprzet', '', 'Piłka lekarska'),
    ('Rzuty piłką lekarską zza głowy o ścianę lub podłogę', 'Rodzaj', '', 'Plyometria'),
    ('Skoki boczne przez płotki lub ławkę', 'Sprzet', '', 'Pachołki / płotki'),
    ('Skoki boczne przez płotki lub ławkę', 'Rodzaj', '', 'Plyometria'),
    ('Skoki w dal z miejsca obunóż (broad jumps)', 'Sprzet', '', 'Masa ciała'),
    ('Skoki w dal z miejsca obunóż (broad jumps)', 'Rodzaj', '', 'Plyometria'),
    ('Skoki łyżwiarskie (skater jumps)', 'Sprzet', '', 'Masa ciała'),
    ('Skoki łyżwiarskie (skater jumps)', 'Rodzaj', '', 'Plyometria'),
    ('Slam balls (rzuty piłką o ziemię)', 'Sprzet', '', 'Piłka lekarska'),
    ('Slam balls (rzuty piłką o ziemię)', 'Rodzaj', '', 'Plyometria'),
    ('Sprinty na bieżni (napędzanej nogami)', 'Sprzet', '', 'Maszyna cardio'),
    ('Sprinty na bieżni (napędzanej nogami)', 'Rodzaj', '', 'Plyometria'),
    ('Wejścia na skrzynię z wyskokiem (step-up jumps)', 'Sprzet', '', 'Skrzynia plyo'),
    ('Wejścia na skrzynię z wyskokiem (step-up jumps)', 'Rodzaj', '', 'Plyometria'),
    ('Wyskoki z przysiadu z lekkimi hantlami (jump squats)', 'Sprzet', '', 'Hantle'),
    ('Wyskoki z przysiadu z lekkimi hantlami (jump squats)', 'Rodzaj', '', 'Plyometria'),
    ('Zeskoki z odbiciem (depth jumps)', 'Sprzet', '', 'Skrzynia plyo'),
    ('Zeskoki z odbiciem (depth jumps)', 'Rodzaj', '', 'Plyometria'),
    ('Ściskanie talerza olimpijskiego dłonią', 'Sprzet', 'Inny sprzęt', 'Talerz'),
    ('Ściskanie talerzy (pinch)', 'Sprzet', 'Inny sprzęt', 'Talerz'),
    ('Opór talerza na kark leżąc na brzuchu', 'Sprzet', 'Inny sprzęt', 'Talerz'),
    ('Opór talerza na szyję leżąc na plecach', 'Sprzet', 'Inny sprzęt', 'Talerz'),
    ('Wyciskanie hantli leżąc na podłodze (floor press)', 'Rodzaj', 'Trójbój', 'Siłowe'),
    ('Dipy na poręczach równoległych', 'Sprzet', 'Inny sprzęt', 'Masa ciała'),
    ('Dipy na poręczach równoległych', 'Ukryte', 0, 1),
    ('Dipy na ławce z obciążeniem', 'Sprzet', 'Inny sprzęt', 'Talerz'),
    ('Prostowanie ramion z sankami nad głową', 'Ukryte', 0, 1),
    ('Francuskie wyciskanie na ławce skośnej ujemnej', 'Sprzet', 'Sztanga', 'Sztanga łamana'),
    ('Wyciskanie jednorącz leżąc na podłodze', 'Ukryte', 0, 1),
    ('Wyciskanie sztangi leżąc (styl trójboju)', 'Partia', 'Triceps', 'Klatka'),
    ('Wyciskanie sztangi leżąc (styl trójboju)', 'Partia_dod', 'Klatka,Przedramiona,Plecy górne,Barki przód', 'Triceps,Barki przód'),
    ('Prostowanie ramienia na wyciągu dolnym stojąc', 'Partia_dod', 'Klatka,Barki przód', ''),
    ('Wspięcia na palce stojąc na maszynie', 'Ukryte', 0, 1),
)

# stara nazwa -> nowa nazwa
NAZWY = {
    "Rower powietrzny (Assault/Echo)": "Rowerek leżąc (brzuch, air bike)",
    "Kettlebell dnem do góry": "Unoszenie bioder leżąc (bottoms up)",
    "Sprinty (wind sprints)": "Przyciąganie kolan w zwisie naprzemiennie (wind sprints)",
    "Łokieć do kolana (skręty w zwisie)": "Łokieć do kolana (skośne spięcia leżąc)",
    "Wykrok z przekładaniem piłki": "Wykrok z przekładaniem kettlebell pod nogą",
    "Częściowe powtórzenia (power partials)": "Wznosy bokiem w niepełnym zakresie (power partials)",
    "Wyciskanie hantli leżąc na podłodze naprzemiennie": "Wyciskanie kettlebell leżąc na podłodze naprzemiennie",
    "Prostowanie ramion na wyciągu w skłonie": "Ściąganie wyciągu prostymi ramionami w skłonie",
    "Ściąganie drążka na wyciągu": "Prostowanie ramion na wyciągu górnym: drążek prosty",
}

# nazwa -> dodatkowe słowa do wyszukiwania (bez polskich znaków)
ALIASY = {
    "Przyciąganie uchwytu wyciągu dolnego siedząc": [
        "wioslowanie siedzac na wyciagu dolnym",
        "seated row"
    ],
    "Ściąganie drążka na wyciągu": [
        "prostowanie ramion wyciag gorny drazek",
        "pushdown"
    ],
    "Prostowanie ramion na wyciągu w skłonie": [
        "sciaganie prostymi ramionami",
        "straight arm pulldown"
    ],
    "Rozpiętki na maszynie": [
        "butterfly",
        "pec deck"
    ],
    "Hack squat na maszynie": [
        "hack przysiad"
    ],
    "Wypychanie na suwnicy (obunóż)": [
        "leg press",
        "prasa nozna",
        "wyciskanie nogami"
    ],
}

# ćwiczenia, których brakowało (popularne maszyny i stanowiska)
NOWE: tuple[dict, ...] = (
    {'nazwa': 'Odwodzenie nogi w tył na maszynie (glute kickback)', 'en': 'glute kickback machine', 'partia': 'Pośladki', 'dod': 'Dwugłowe uda', 'sprzet': 'Maszyna', 'rodzaj': 'Siłowe', 'typ': 'Izolowane', 'poziom': 'Początkujący', 'jednostka': 'powt./nogę'},
    {'nazwa': 'Przysiad na maszynie z pasem (belt squat)', 'en': 'belt squat machine', 'partia': 'Czworogłowe', 'dod': 'Pośladki,Dwugłowe uda', 'sprzet': 'Maszyna', 'rodzaj': 'Siłowe', 'typ': 'Wielostawowe', 'poziom': 'Średniozaawansowany', 'jednostka': 'powt.'},
    {'nazwa': 'Wiosłowanie siedząc na maszynie z oparciem klatki', 'en': 'seated row machine chest supported', 'partia': 'Plecy górne', 'dod': 'Plecy szerokie,Biceps,Barki tył', 'sprzet': 'Maszyna', 'rodzaj': 'Siłowe', 'typ': 'Wielostawowe', 'poziom': 'Początkujący', 'jednostka': 'powt.'},
    {'nazwa': 'Unoszenie kolan na stanowisku (kapitańskie krzesło)', 'en': "captain's chair knee raise", 'partia': 'Brzuch', 'dod': '', 'sprzet': 'Masa ciała', 'rodzaj': 'Siłowe', 'typ': None, 'poziom': 'Początkujący', 'jednostka': 'powt.'},
    {'nazwa': 'Wyciskanie na maszynie siedząc (ławka skośna)', 'en': 'incline chest press machine selectorized', 'partia': 'Klatka', 'dod': 'Barki przód,Triceps', 'sprzet': 'Maszyna', 'rodzaj': 'Siłowe', 'typ': 'Wielostawowe', 'poziom': 'Początkujący', 'jednostka': 'powt.'},
    {'nazwa': 'Prostowanie tułowia na ławce rzymskiej 45°', 'en': '45 degree back extension', 'partia': 'Plecy dolne', 'dod': 'Pośladki,Dwugłowe uda', 'sprzet': 'Masa ciała', 'rodzaj': 'Siłowe', 'typ': 'Izolowane', 'poziom': 'Początkujący', 'jednostka': 'powt.'},
)

# tabele i kolumny, w których zapisane są nazwy ćwiczeń (zmiana nazwy tylko, gdy żadna z nich jej nie używa)
_UZYCIA = (("treningi", "Nazwa_cwiczenia"), ("wpisy_cwiczen", "Cwiczenie"), ("serie_wykonane", "Cwiczenie"),
           ("presety_cwiczenia", "Cwiczenie"), ("presety_cwiczenia", "Alternatywa"), ("ulubione_cwiczenia", "Nazwa"))


def _tabele(db: sqlite3.Connection) -> set[str]:
    return {w[0] for w in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def _uzywana(db: sqlite3.Connection, nazwa: str, tabele: set[str]) -> bool:
    for tabela, kolumna in _UZYCIA:
        if tabela in tabele and db.execute(f"SELECT 1 FROM {tabela} WHERE {kolumna} = ? LIMIT 1", (nazwa,)).fetchone():
            return True
    if "trening_w_toku" in tabele and db.execute("SELECT 1 FROM trening_w_toku WHERE Dane LIKE ? LIMIT 1",
                                                 (f"%{nazwa}%",)).fetchone():
        return True
    kolumny = {w[1] for w in db.execute("PRAGMA table_info(cwiczenia)")}
    return "Notatka" in kolumny and bool(db.execute(
        "SELECT 1 FROM cwiczenia WHERE Nazwa = ? AND COALESCE(Notatka, '') <> ''", (nazwa,)).fetchone())


def _alias(db: sqlite3.Connection, alias: str, nazwa: str) -> None:
    from baza_cwiczen import _norma
    if _norma(alias):
        db.execute("INSERT OR IGNORE INTO cwiczenia_aliasy (Alias, Nazwa) VALUES (?, ?)", (_norma(alias), nazwa))


def _uzupelnij_puste(db: sqlite3.Connection) -> None:
    """Tylko uzupełnienia pustych pól (bezpieczne przy każdym starcie)."""
    for nazwa, kolumna, stara, nowa in ZMIANY:
        if stara == "" and nowa != "":
            db.execute(f"UPDATE cwiczenia SET {kolumna} = ? WHERE Nazwa = ? AND COALESCE({kolumna}, '') = ''", (nowa, nazwa))


def zastosuj(db: sqlite3.Connection, sciezka_bazy: Path | None = None) -> bool:
    """Wprowadza poprawki raz. Zwraca True, gdy coś zostało zastosowane."""
    tabele = _tabele(db)
    if "cwiczenia" not in tabele or "ustawienia" not in tabele or "cwiczenia_aliasy" not in tabele:
        return False
    kolumny = {w[1] for w in db.execute("PRAGMA table_info(cwiczenia)")}
    if not {"Sprzet", "Typ", "Ukryte"} <= kolumny:
        return False
    if db.execute("SELECT 1 FROM ustawienia WHERE Klucz = ?", (FLAGA,)).fetchone():
        _uzupelnij_puste(db)       # ćwiczenia z presetów dopisane po pierwszym starcie (świeża baza) dostają sprzęt
        return False
    from baza_cwiczen import _kopia
    _kopia(db, sciezka_bazy)

    for nazwa, kolumna, stara, nowa in ZMIANY:
        if kolumna == "Ukryte":
            db.execute("UPDATE cwiczenia SET Ukryte = ? WHERE Nazwa = ? AND COALESCE(Ukryte, 0) = ?", (nowa, nazwa, stara))
        else:
            db.execute(f"UPDATE cwiczenia SET {kolumna} = ? WHERE Nazwa = ? AND COALESCE({kolumna}, '') = ?",
                       (nowa if nowa != "" else None, nazwa, stara))

    from cwiczenia_meta import typ_cwiczenia
    for r in NOWE:
        if db.execute("SELECT 1 FROM cwiczenia WHERE Nazwa = ?", (r["nazwa"],)).fetchone():
            continue
        typ = r["typ"] or typ_cwiczenia(r["nazwa"], r["partia"])
        db.execute("INSERT INTO cwiczenia (Nazwa, Partia, Typ, Partia_dod, Sprzet, Rodzaj, Poziom, Jednostka_dom, Ukryte, Zrodlo) "
                   "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 'baza')",
                   (r["nazwa"], r["partia"], typ, r["dod"], r["sprzet"], r["rodzaj"], r["poziom"], r["jednostka"]))
        _alias(db, r["en"], r["nazwa"])
        _alias(db, r["nazwa"], r["nazwa"])

    for stara, nowa in NAZWY.items():
        if not db.execute("SELECT 1 FROM cwiczenia WHERE Nazwa = ?", (stara,)).fetchone():
            continue
        if db.execute("SELECT 1 FROM cwiczenia WHERE Nazwa = ?", (nowa,)).fetchone() or _uzywana(db, stara, tabele):
            _alias(db, nowa, stara)          # nazwa zostaje, ale wyszukiwarka znajdzie ją po nowej
            continue
        db.execute("UPDATE cwiczenia SET Nazwa = ? WHERE Nazwa = ?", (nowa, stara))
        db.execute("UPDATE OR IGNORE cwiczenia_aliasy SET Nazwa = ? WHERE Nazwa = ?", (nowa, stara))
        db.execute("DELETE FROM cwiczenia_aliasy WHERE Nazwa = ?", (stara,))
        _alias(db, nowa, nowa)
        _alias(db, stara, nowa)              # stara nazwa nadal działa w wyszukiwarce

    for nazwa, aliasy in ALIASY.items():
        cel = nazwa if db.execute("SELECT 1 FROM cwiczenia WHERE Nazwa = ?", (nazwa,)).fetchone() else NAZWY.get(nazwa)
        if cel:
            for a in aliasy:
                _alias(db, a, cel)

    # nowy rodzaj sprzętu „Talerz”: kto ma zaznaczoną sztangę, ma też talerze
    if "profil_sprzet" in tabele:
        wybrane = {w[0] for w in db.execute("SELECT Sprzet FROM profil_sprzet")}
        if "Sztanga" in wybrane:
            db.execute("INSERT OR IGNORE INTO profil_sprzet (Sprzet) VALUES ('Talerz')")
    db.execute("INSERT OR REPLACE INTO ustawienia (Klucz, Wartosc) VALUES (?, '1')", (FLAGA,))
    return True
