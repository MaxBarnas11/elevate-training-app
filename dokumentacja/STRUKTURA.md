# OVRLD: struktura folderów i plików

Ten plik mówi, gdzie co leży i gdzie czego szukać. Stan na 26.10.2026 (po uporządkowaniu folderów).

## Widok z góry

```
TrainingApp/
├─ START.bat                  uruchamia aplikację
├─ AKTUALIZUJ.bat             podmienia nowe pliki, zapisuje wersję w gicie i startuje od nowa (Ctrl+Alt+F9)
├─ PRZELACZ_LOGOWANIE.bat     przełącza tryb TELEFON (bez logowania) ↔ LOGOWANIE (Google)
├─ app.py                     jedyny plik startowy aplikacji (menu, strony, motywy)
├─ README.md                  opis dla GitHuba
├─ requirements.txt           lista bibliotek Pythona
├─ .env.example               wzór pliku z hasłem do Garmina (prawdziwy .env jest u Ciebie, poza gitem)
├─ .gitignore                 co nigdy nie trafia do gita (hasła, bazy, tokeny)
│
├─ kod/                       wszystkie moduły aplikacji (.py) i baza ćwiczeń
├─ narzedzia/                 skrypty pomocnicze (zapis wersji, goście, skrót na pulpit, kopie bazy)
├─ dokumentacja/              DOKUMENTACJA.md (jak działa i jak używać), STRUKTURA.md (ten plik)
├─ static/  logo.svg          zasoby publiczne: ikona na ekran początkowy, logo
├─ .streamlit/                konfiguracja Streamlita (config.toml) i klucze logowania (secrets.toml / .off)
│
└─ Twoje dane (poza gitem, nie ruszać ręcznie):
   treningi.db   dane/   kopie/   .env   ntfy_temat.txt   .garmin_tokeny/   goscie/   venv/
```

## Trzy skróty na wierzchu

Codziennie używasz tylko trzech plików w głównym folderze:

| Plik | Kiedy |
| --- | --- |
| `START.bat` | uruchomienie aplikacji (np. po restarcie komputera) |
| `AKTUALIZUJ.bat` (Ctrl+Alt+F9) | po tym, jak dostaniesz nowe pliki `*_NOWA.py`; też zwykły restart |
| `PRZELACZ_LOGOWANIE.bat` | zmiana trybu telefon ↔ logowanie |

Nowe wersje plików dostajesz jako `nazwa_NOWA.py` w głównym folderze. `AKTUALIZUJ.bat` sam wkłada je tam, gdzie ich miejsce (`app_NOWA.py` do głównego folderu, reszta do `kod\`).

## kod\ (moduły aplikacji)

| Grupa | Pliki | Za co odpowiadają |
| --- | --- | --- |
| Logowanie i konta | `logowanie.py`, `uzytkownik.py` | bramka Google, lista adresów, ścieżka bazy danej osoby |
| Baza i dane | `baza.py`, `baza_cwiczen.py`, `cwiczenia_meta.py`, `dane_cwiczen.json`, `presety.py`, `presety_dane.py`, `plan.py` | tabele SQLite, 847 ćwiczeń, presety, plan tygodnia |
| Trening | `sesja_treningowa.py`, `rekomendacje.py`, `dziennik.py` | prowadzony trening, historia, rekordy, reguły „Na dziś”, dziennik bez zegarka |
| Strony i widoki | `profil.py`, `postepy.py`, `regeneracja.py`, `mapa_ciala.py` | profil i „Moja siłownia”, postępy, regeneracja, mapa ciała |
| Wygląd | `karty.py`, `karty_start.py`, `karty_presety.py`, `wykresy.py`, `motywy.py`, `styl.py`, `szklo.py` | kafelki, wykresy, kolory motywów, efekt szkła |
| Usługi zewnętrzne | `garmin.py`, `powiadomienia.py`, `uwagi.py` | zegarek Garmin, powiadomienia ntfy, „Zgłoś uwagę” |

Moduły importują się nawzajem po zwykłych nazwach (`import baza`). Folder `kod\` jest dopisany do ścieżek Pythona na początku `app.py`, dlatego nic poza tym nie wymagało zmian.

## narzedzia\ (skrypty pomocnicze)

| Plik | Do czego |
| --- | --- |
| `COMMIT.bat` | zapis wersji w gicie (też wywoływany automatycznie przez `AKTUALIZUJ.bat`); z `"opis" wyslij` wysyła na GitHub |
| `zarzadzaj.ps1` | zamyka starą aplikację i otwiera nową kartę (używa go `AKTUALIZUJ.bat`) |
| `UTWORZ_SKROT.bat` | jednorazowo tworzy skrót „OVRLD aktualizacja” na pulpicie (Ctrl+Alt+F9) |
| `GOSC.bat`, `GOSCIE.bat` | awaryjne osobne instancje dla gości (opis w projekcie: `instancje-gosci.md`) |
| `narzedzia_bazy.py` | kopia bazy, lista i usuwanie treningów z wiersza poleceń: `python narzedzia/narzedzia_bazy.py kopia` |
| `test_push.py` | jednorazowy test powiadomień ntfy, tworzy `ntfy_temat.txt` |

## Gdzie czego szukać

| Szukasz | Plik |
| --- | --- |
| Jak działa logowanie, co zabezpiecza | `kod\logowanie.py`, `kod\uzytkownik.py`, `dokumentacja\DOKUMENTACJA.md` rozdział 7 |
| Skąd bierze się ścieżka bazy | `kod\uzytkownik.py` (`sciezka_bazy`), `kod\baza.py` |
| Wygląd jednej strony | `app.py` (funkcje `strona_*`), karty w `kod\karty*.py` |
| Reguły podpowiedzi „Na dziś” | `kod\rekomendacje.py` (progi w słowniku `PROGI`) |
| Dodać ćwiczenie do bazy | `kod\dane_cwiczen.json`, `kod\cwiczenia_meta.py` |
| Klucze logowania Google | `.streamlit\secrets.toml` (lub `.off`), nie otwieraj w obecności innych |
| Zapis i cofanie wersji | `narzedzia\COMMIT.bat`, `git log --oneline -20` |
| Dokumentacja dla użytkownika | `dokumentacja\DOKUMENTACJA.md` |

## Zasady porządku

- Nowy moduł `.py` idzie do `kod\` (i dopisujesz go do tabeli wyżej). Nowy skrypt pomocniczy do `narzedzia\`.
- Dane osobiste (bazy, tokeny, klucze) nigdy nie lądują w `kod\`, `narzedzia\` ani `dokumentacja\`.
- W głównym folderze zostaje tylko to, co potrzebne od razu: trzy skróty, `app.py`, konfiguracja i `README.md`.
- Wszystkie ścieżki do danych liczy `uzytkownik.FOLDER_APLIKACJI` (główny folder aplikacji), dzięki czemu moduły w `kod\` nie zgadują ich z własnego położenia.
