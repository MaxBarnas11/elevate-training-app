# Struo

Polska aplikacja treningowa, której używam na co dzień na siłowni, głównie z iPhone'a. Łączy prowadzenie treningu seria po serii (z odliczaniem przerw) z danymi o regeneracji z zegarka Garmin, a historię i postępy trzyma w lokalnej bazie SQLite.

Interfejs jest po polsku i projektowany mobile first: podstawowe, powtarzalne czynności są kompaktowe, a te wymagające decyzji opisane słowami.

> Status: działający prototyp w Streamlicie, rozwijany iteracyjnie na podstawie realnego używania. Plan na dalej (własny front i back end, konta, powiadomienia) jest na końcu.

## Zrzuty ekranu

<!-- Dodaj tu własne zrzuty ekranu (zasłoń wagę i inne prywatne dane), np.:
![Start treningu](docs/screenshots/start.png)
![Trening w toku](docs/screenshots/trening.png)
![Postępy](docs/screenshots/postepy.png)
-->

## Co potrafi

**Trening w toku**
- Start z gotowego presetu, z poprzedniego treningu tego presetu („jak ostatnio”) albo od zera.
- Jedna seria na ekranie: ciężar, powtórzenia (albo czas, dystans), RPE 1–10 w jednym rzędzie, cofnięcie ostatniej serii.
- Przypięty pasek z czasem treningu, odliczaniem przerwy (+30 s, pomiń, wyłącz) i postępem serii.
- Propozycja ciężaru z historii (progresja po osiągnięciu górnej granicy zakresu powtórzeń).
- Serie rozgrzewkowe: nie liczą się do objętości, rekordów ani planu, a aplikacja podpowiada ich schemat.
- Notatki przypięte do ćwiczenia (np. ustawienie maszyny), widoczne przy każdym kolejnym treningu.
- Ćwiczenia w powtórzeniach, sekundach, minutach i metrach, z jednostką dobieraną automatycznie.
- Zamiana, dodawanie, usuwanie i przesuwanie ćwiczeń w trakcie treningu. Trening w toku zapisuje się w bazie, więc przetrwa odświeżenie strony.

**Po treningu i historia**
- Podsumowanie z nowymi rekordami (najcięższa seria, szacowane 1RM) i porównaniem z poprzednim treningiem tego presetu.
- Zapis treningu jako nowy preset.
- Historia z edycją i usuwaniem treningów, automatyczne kopie bazy (raz dziennie i przed każdą edycją), eksport do CSV (do Excela) i pobranie pliku bazy.

**Postępy**
- Rekordy, objętość tygodniowa, regularność (tygodnie z rzędu), wykresy dla wybranego ćwiczenia.
- Serie na partię mięśniową w bieżącym tygodniu na tle średniej z poprzednich.

**Regeneracja i plan**
- Dane z Garmin Connect (sen i jego fazy, tętno spoczynkowe, kroki, kalorie, stres) zapisywane w bazie i pokazywane na kartach z wykresami.
- Plan tygodnia przypisany do presetów i kafelek tygodnia (plan kontra wykonane treningi).

## Technologie

- Python, [Streamlit](https://streamlit.io) (interfejs), pandas
- SQLite (lokalna baza, bez serwera)
- [garminconnect](https://github.com/cyberjunky/python-garminconnect) (nieoficjalna biblioteka do Garmin Connect, projekt nie jest powiązany z firmą Garmin)
- Własne wykresy SVG i karty w HTML/CSS w kolorach aplikacji
- Dostęp z telefonu przez sieć domową albo [Tailscale](https://tailscale.com)

## Uruchomienie

Wymagany jest Python (rozwijam na wersji 3.14).

```bash
git clone https://github.com/MaxBarnas11/elevate-training-app.git
cd elevate-training-app

python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
# source venv/bin/activate

pip install -r requirements.txt
```

Dane do Garmin Connect (opcjonalne, bez nich działa cała część treningowa): skopiuj `.env.example` jako `.env` i uzupełnij.

```
GARMIN_EMAIL=twoj@email.pl
GARMIN_PASSWORD=twoje-haslo
```

Start aplikacji:

```bash
streamlit run app.py
```

Na Windowsie pomaga `start.bat`: uruchamia aplikację dostępną w sieci i wypisuje adres komputera, który wpisujesz na telefonie (`http://ADRES:8501`).

Przy pierwszym uruchomieniu powstaje plik bazy `treningi.db` z listą ćwiczeń i gotowymi presetami, które możesz edytować w aplikacji.

## Dane i prywatność

Wszystko jest zapisywane lokalnie w `treningi.db`, a kopie w folderze `kopie/`. Baza i plik `.env` z hasłem są w `.gitignore`, więc nigdy nie trafiają do repozytorium.

## Struktura

| Plik | Do czego służy |
| --- | --- |
| `app.py` | strony aplikacji, menu, formularz ręcznego treningu |
| `sesja_treningowa.py` | prowadzony trening, historia, edycja, kopie, rekordy |
| `postepy.py` | strona Postępy |
| `regeneracja.py`, `karty.py`, `karty_start.py`, `wykresy.py` | karty i wykresy z danych Garmina |
| `baza.py`, `presety.py`, `presety_dane.py`, `plan.py` | baza SQLite, presety startowe, plan tygodnia |
| `garmin.py` | pobieranie danych z Garmin Connect |

## Plany

- Własny front i back end zamiast Streamlita (m.in. dla powiadomień push na iPhone'a i pracy offline na siłowni).
- Aplikacja na serwerze z kontami użytkowników.
- Powiadomienia o końcu przerwy przy zablokowanym ekranie.
- Rekomendacja dnia na podstawie regeneracji i analiza treningów.
