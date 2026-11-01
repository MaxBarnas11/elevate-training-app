# Struo

Polska aplikacja treningowa, której używam na co dzień na siłowni, głównie z iPhone'a. Prowadzi trening seria po serii (z odliczaniem przerw), pamięta historię, liczy postępy i opcjonalnie łączy się z zegarkiem Garmin, żeby podpowiedzieć, jak trenować danego dnia. Dane trzyma w lokalnej bazie SQLite.

Interfejs jest po polsku i projektowany mobile first: powtarzalne czynności są kompaktowe i obsługiwane jednym kciukiem, a te wymagające decyzji opisane słowami. Wygląd w stylu szkła, ciemny motyw „Neon” i jasny „Piasek”.

> Status: działający prototyp w Streamlicie, rozwijany iteracyjnie na podstawie realnego używania. Plan na dalej (serwer, konta dla znajomych, powiadomienia push) jest na końcu.

## Zrzuty ekranu

<!-- Dodaj tu własne zrzuty ekranu (zasłoń wagę i inne prywatne dane) i odkomentuj:
| Telefon | Przeglądarka |
| --- | --- |
| ![Start](docs/screenshots/telefon-start.png) | ![Start](docs/screenshots/przegladarka-start.png) |
| ![Trening w toku](docs/screenshots/telefon-trening.png) | ![Postępy](docs/screenshots/przegladarka-postepy.png) |
-->

_Zrzuty z telefonu i przeglądarki zostaną dodane tutaj._

## Co potrafi

**Trening na dziś (generator)**
- Na karcie Treningi wybierasz partie (np. nogi, pośladki, brzuch) i czas (30–120 min), a aplikacja proponuje trzy treningi do wyboru. Układają się z reguł, bez AI.
- W każdym 1–2 ulubione ćwiczenia, 1–2 nowe (jeszcze nie robione, na rozwój) i sprawdzone podstawy. Dobór uwzględnia cel, sprzęt z „Mojej siłowni” i poziom.
- Kolejna propozycja zmienia więcej: pierwsza to układ podstawowy, druga ma inne ćwiczenie główne lub ulubione, trzecia więcej nowości.
- Liczba ćwiczeń zależy od czasu (np. 7 na 90 min, 10 na 120 min), a czas liczy się razem z ok. 15 min rozgrzewki i schłodzenia i jest traktowany luźno.
- Ćwiczenia na tę samą partię nie stoją obok siebie (np. czworogłowe, pośladki, brzuch, znowu czworogłowe), a prawie takie same ruchy nie powtarzają się w jednym treningu.
- Jeśli masz już preset, który pasuje, aplikacja najpierw go pokaże. Wynik możesz od razu zacząć albo zapisać jako preset („Własne”). Lista presetów ma przełącznik „Gotowe / Moje”.

**Trening w toku**
- Start z gotowego presetu, z poprzedniego treningu tego presetu („jak ostatnio”) albo od zera.
- Jedna seria na ekranie: ciężar, powtórzenia (albo czas, dystans), RPE 1–10 w jednym rzędzie kolorowych przycisków, cofnięcie ostatniej serii.
- Przypięty pasek z czasem treningu, odliczaniem przerwy (+30 s, pomiń, wyłącz) i postępem serii. Zegar liczy się w telefonie, więc interfejs nie zacina się podczas odliczania.
- Cztery przyciski nawigacji: poprzednie, następne, „później” i zielony ✓ „gotowe”. Kompaktowa lista ćwiczeń, jeden wiersz na ćwiczenie.
- Propozycja ciężaru z historii (progresja po osiągnięciu górnej granicy zakresu powtórzeń).
- Serie rozgrzewkowe: nie liczą się do objętości, rekordów ani planu, a aplikacja podpowiada ich schemat.
- Notatki przypięte do ćwiczenia (np. ustawienie maszyny), widoczne przy każdym kolejnym treningu.
- Ćwiczenia w powtórzeniach, sekundach, minutach i metrach, z jednostką dobieraną automatycznie.
- Zamiana ćwiczenia w krokach (podobne: ta sama partia i sprzęt, który mam na siłowni), dodawanie, usuwanie i przesuwanie. Trening w toku zapisuje się w bazie, więc przetrwa odświeżenie strony.

**Po treningu i historia**
- Podsumowanie z nowymi rekordami (najcięższa seria, szacowane 1RM) i porównaniem z poprzednim treningiem tego presetu.
- Zapis treningu jako nowy preset.
- Historia z edycją i usuwaniem treningów, automatyczne kopie bazy (raz dziennie i przed każdą edycją), eksport do CSV i ZIP oraz pobranie pliku bazy.

**Postępy**
- Rekordy, objętość tygodniowa, regularność (tygodnie z rzędu), wykresy dla wybranego ćwiczenia.
- Mapa ciała: serie na partię mięśniową w bieżącym tygodniu, z kolorami od braku pracy po przeciążenie.

**Regeneracja i rekomendacje**
- Dane z Garmin Connect (sen i jego fazy, tętno spoczynkowe, HRV, kroki, kalorie, stres) zapisywane w bazie i pokazywane na kartach z wykresami. Bez zegarka: ręczny wpis snu, energii i wagi.
- „Na dziś”: jawne, stałe reguły (bez AI) proponują lżejszy trening, odpoczynek albo inne partie niż wczoraj. To tylko propozycja, decyzja należy do mnie.
- Plan tygodnia przypisany do presetów i kafelek tygodnia (plan kontra wykonane treningi).

**Ćwiczenia, profil i konta**
- Baza ponad 850 ćwiczeń z partiami mięśni i sprzętem, „Moja siłownia” (rodzaje sprzętu i konkretne maszyny, np. suwnica, hack przysiad, butterfly; wyszukiwanie ćwiczeń po nazwie maszyny) i ulubione ćwiczenia.
- Logowanie przez Google z listą dozwolonych adresów; każda osoba ma własną bazę. Ekran pierwszych kroków dla nowej osoby (imię, data urodzenia ze zgodami, sprzęt).
- Powiadomienie o końcu przerwy na zablokowany telefon (ntfy), zgłaszanie uwag z aplikacji.

## Technologie

- Python, [Streamlit](https://streamlit.io) (interfejs, własne komponenty HTML dla RPE i zegara), pandas
- SQLite (lokalna baza, bez serwera)
- [garminconnect](https://github.com/cyberjunky/python-garminconnect) (nieoficjalna biblioteka do Garmin Connect, projekt nie jest powiązany z firmą Garmin)
- Logowanie: Authlib i OpenID Connect przez Google
- Własne wykresy SVG i karty w HTML/CSS w kolorach aplikacji
- Dostęp z telefonu przez [Tailscale](https://tailscale.com) (prywatna sieć) albo, docelowo, przez serwer z https
- Wersje bibliotek przypięte w `requirements.txt` i sprawdzane pod kątem znanych luk (`pip-audit`)

## Uruchomienie

Wymagany jest Python (rozwijam na wersji 3.14).

```bash
git clone <adres-tego-repozytorium>
cd <folder-repozytorium>

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

Na Windowsie pomaga `START.bat`: uruchamia aplikację i wypisuje adres, który wpisujesz na telefonie (`http://ADRES:8501`). `AKTUALIZUJ.bat` podmienia nowe pliki, zapisuje wersję w gicie i uruchamia aplikację od nowa.

Przy pierwszym uruchomieniu powstaje plik bazy `treningi.db` z listą ćwiczeń i gotowymi presetami, które możesz edytować w aplikacji.

Logowanie Google jest opcjonalne i włącza się plikiem `.streamlit/secrets.toml` (klucze klienta OAuth w sekcji `[auth]`, adres właściciela i lista dozwolonych adresów w sekcji `[struo]`). Pliku z kluczami nie ma w repozytorium.

Opcjonalne zmienne środowiskowe: `STRUO_LOGOWANIE` (`1` wymusza logowanie, `0` je wyłącza), `STRUO_WLASCICIEL` i `STRUO_DOZWOLONE` (adresy e-mail rozdzielone przecinkami), `STRUO_BAZA` (ścieżka do osobnego pliku bazy, np. dla konta gościa).

## Testy

Logika aplikacji (generator, filtr sprzętu, opisy ćwiczeń, szacowanie 1RM, przygotowanie bazy, ustawienia logowania) ma testy w folderze `testy/`. Pracują na tymczasowej bazie, więc nie dotykają prawdziwych danych.

```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

Na Windowsie to samo robi `narzedzia\TESTY.bat`. Na GitHubie te same kroki uruchamiają się automatycznie przy każdym wysłaniu kodu (`.github/workflows/testy.yml`).

## Dane i prywatność

Wszystko jest zapisywane lokalnie w `treningi.db` (dla zaproszonych osób w osobnych folderach), a kopie w folderze `kopie/`. Baza, plik `.env` z hasłem, klucze logowania, tokeny Garmina i dane użytkowników są w `.gitignore`, więc nigdy nie trafiają do repozytorium. Każdy użytkownik może wyeksportować swoje dane i usunąć je z aplikacji.

## Struktura

| Miejsce | Do czego służy |
| --- | --- |
| `app.py` | jedyny plik startowy: menu, strony, motywy |
| `kod/` | moduły aplikacji |
| `kod/sesja_treningowa.py` | prowadzony trening, historia, edycja, kopie, rekordy |
| `kod/komp_ui.py` | własne komponenty: wybór RPE, zegar liczony w telefonie |
| `kod/szklo.py`, `motywy.py`, `styl.py` | efekt szkła, kolory motywów |
| `kod/postepy.py`, `mapa_ciala.py`, `regeneracja.py`, `karty*.py`, `wykresy.py` | strony, karty i wykresy |
| `kod/baza.py`, `baza_cwiczen.py`, `presety*.py`, `plan.py` | baza SQLite, ponad 850 ćwiczeń, presety, plan tygodnia |
| `kod/maszyny.py`, `maszyny_ui.py`, `opisy_cwiczen.py` | maszyny na siłowni i filtr sprzętu, podpowiedzi „Jak wykonać” |
| `kod/rekomendacje.py` | reguły „Na dziś” |
| `kod/generator.py` | generator „Trening na dziś” (dobór ćwiczeń do partii i czasu) |
| `kod/logowanie.py`, `uzytkownik.py`, `onboarding.py`, `profil.py` | logowanie Google, konta, pierwsze kroki, profil |
| `kod/garmin.py`, `powiadomienia.py` | Garmin Connect, powiadomienia ntfy |
| `narzedzia/` | skrypty pomocnicze: zapis wersji, kopie bazy, sprawdzanie bibliotek, diagnostyka |

## Źródła

Podstawą listy ćwiczeń jest [free-exercise-db](https://github.com/yuhonas/free-exercise-db) (licencja Unlicense, domena publiczna), przetłumaczona na polski i rozszerzona o własne ćwiczenia. Szczegóły w pliku `NOTICE.md`.

## Plany

- Wdrożenie na własny serwer (VPS, domena, https), żeby logowanie Google działało także z telefonu, oraz zaproszenie kilku znajomych.
- Powiadomienia o końcu przerwy dla każdej osoby (Web Push) i praca offline na siłowni.
- Własny front i back end zamiast Streamlita.
- Większa baza ćwiczeń ze zdjęciami sprzętu („Moja siłownia”).
