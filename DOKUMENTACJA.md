# OVRLD: dokumentacja

Ten plik jest dla Ciebie: jak aplikacja działa, jak jej używać na co dzień, gdzie leżą dane i co robić, gdy coś nie działa. Nie trzeba go czytać od początku do końca, każdy rozdział stoi osobno. Stan na 24.10.2026.

## Spis treści

1. Czym jest OVRLD
2. Codzienne używanie (start, aktualizacja, telefon)
3. Strony aplikacji
4. Jak wygląda trening krok po kroku
5. Rekomendacje i regeneracja
6. Dane: gdzie leżą, kopie, eksport, usuwanie
7. Logowanie i konta (dwa tryby pracy)
8. Garmin i powiadomienia
9. Wersje w gicie: zapis, wysyłka, cofanie
10. Pliki aplikacji
11. Ustawienia przez zmienne środowiskowe
12. Gdy coś nie działa
13. Słowniczek
14. Plany
15. Historia zmian (skrót)
16. Zasady dostępu do danych (Claude)

## 1. Czym jest OVRLD

Polska aplikacja treningowa, której używasz głównie z iPhone'a na siłowni. Prowadzi trening seria po serii (z odliczaniem przerw), pamięta historię i liczy postępy. Opcjonalnie pobiera dane z zegarka Garmin (sen, tętno spoczynkowe, stres, kroki, kalorie) i na ich podstawie podpowiada, jak trenować danego dnia.

- Technologia: Python 3 (środowisko `venv`), Streamlit 1.65, baza SQLite (jeden plik), biblioteka `garminconnect`.
- Aplikacja działa na Twoim komputerze. Telefon łączy się z nim przez Tailscale (prywatna sieć), więc komputer musi być włączony i aplikacja uruchomiona.
- Interfejs jest po polsku, projektowany pod telefon. Wygląd: ciemny motyw „Neon” (prawie czarne tło, akcenty pomarańcz, róż, fiolet) albo jasny „Piasek”. Wybór: Ustawienia i połączenie, przełącznik Auto / Jasny / Ciemny.
- Repozytorium prywatne na GitHubie: `MaxBarnas11/elevate-training-app` (nazwę zmienisz w wolnej chwili).

## 2. Codzienne używanie

### Uruchomienie

- Dwuklik `START.bat` albo skrót na pulpicie. Okno startowe pokazuje, w którym trybie działa aplikacja (patrz rozdział 7) i pod jakim adresem ją otworzyć.
- Tryb TELEFON (bez logowania): okno pokazuje adres dla telefonu, np. `http://100.x.x.x:8501`. Wpisujesz go w Safari (albo klikasz ikonę dodaną do ekranu początkowego). Gdy Tailscale nie działa, aplikacja stoi tylko na komputerze i okno pisze o tym na górze: włącz Tailscale i uruchom ponownie.
- Tryb LOGOWANIE (Google): okno pisze „LOGOWANIE GOOGLE WŁĄCZONE”, a aplikację otwierasz na komputerze pod `http://localhost:8501` (nie `127.0.0.1`, nie adres Tailscale).
- Tryb awaryjny `START.bat siec` udostępnia aplikację w całej sieci Wi-Fi. Bez logowania robisz to tylko w zaufanej sieci.

### Aktualizacja aplikacji

Nowe wersje plików dostajesz jako `*_NOWA.py` (np. `app_NOWA.py`).

1. Naciśnij Ctrl+Alt+F9 (skrót „ELEVATE aktualizacja”, starą nazwę możesz zostawić) albo kliknij dwukrotnie `AKTUALIZUJ.bat`.
2. Skrypt zamyka starą aplikację, podmienia `*_NOWA.py` na właściwe pliki, zapisuje wersję w gicie (lokalnie) i uruchamia aplikację od nowa. Przeglądarka otwiera się sama (w trybie logowania pod `localhost`).
3. Odśwież kartę w przeglądarce telefonu.

### Ikona na ekranie początkowym (iPhone)

Safari, przycisk Udostępnij, „Dodaj do ekranu początkowego”. Ikona („O” w stylu szkła) leży w folderze `static`.

## 3. Strony aplikacji

Menu boczne (kolejność): Start, Jutro (tylko gdy jutro jest dniem treningowym), Na dziś, Dziś, Regeneracja, Treningi, Postępy, Historia, Mój plan, Profil.

| Strona | Co tam jest |
| --- | --- |
| **Start** | Dzień w kafelkach: gotowość, sen i jego fazy, tętno spoczynkowe, stres, kroki, kalorie, tydzień treningowy. Bez zegarka: ręczny wpis snu, wagi i energii. Karta „Na dziś” z rekomendacją. |
| **Jutro** | Plan na jutro z planu tygodnia i podgląd presetu, który wypada. Przycisk „Zmień plan”. |
| **Na dziś** | Szczegóły rekomendacji (lżejszy trening, odpoczynek, inne partie niż wczoraj) i przyciski przenoszące do wyboru treningu. |
| **Dziś** | Dzisiejszy trening z planu. |
| **Regeneracja** | Wykresy snu, tętna spoczynkowego, HRV i trendy z wybranego zakresu dni. Bez zegarka: sen w godzinach, energia i waga. |
| **Treningi** | Wybór presetu i start prowadzonego treningu, preset „jak ostatnio”, trening od zera, formularz „Dodaj trening” (wpis po fakcie), edycja presetów. |
| **Postępy** | Rekordy, objętość tygodniowa, regularność (tygodnie z rzędu), wykresy wybranego ćwiczenia, serie na partię i mapa ciała. |
| **Historia** | Wszystkie treningi z szukaniem, edycją i usuwaniem; narzędzia (nazwy, eksport, kopie); samopoczucie. |
| **Mój plan** | Plan tygodnia: który dzień jest treningowy, jaki preset, godzina, notatka. |
| **Profil** | Imię, zdjęcie, data urodzenia, wzrost, cel wagi, „Moja siłownia” (sprzęt), ulubione ćwiczenia, konto i wylogowanie, dane i prywatność. |

Objaśnienia są pod małym znakiem „?”: dotknij go, żeby zobaczyć opis. Panel „Zgłoś uwagę” w menu zapisuje uwagę w bazie i wysyła powiadomienie na telefon właściciela.

## 4. Jak wygląda trening krok po kroku

1. Treningi, wybierz preset (kategorie: Góra, Dół, Plyo, Cardio, Całe ciało, sporty, Własne). Obok widać kafelki ćwiczeń z numerami.
2. „Rozpocznij: preset” startuje trening. Dostępne są też „jak ostatnio” (te same ćwiczenia, serie i zakresy) i „Zacznij pusty trening” (ćwiczenia dodajesz w trakcie).
3. Na ekranie jest jedno ćwiczenie. Wpisujesz ciężar i powtórzenia (albo czas, dystans), opcjonalnie RPE 1–10 jednym stuknięciem, i zapisujesz serię. „Powtórz poprzednią” zapisuje identyczną serię jednym przyciskiem.
4. Po serii rusza przerwa. Przypięty pasek u góry pokazuje czas treningu, odliczanie przerwy i postęp serii. Masz „+30 s”, „Pomiń” i przełącznik przerw wł./wył.
5. Seria rozgrzewkowa (przełącznik) nie liczy się do objętości, rekordów ani planu. Aplikacja podpowiada schemat rozgrzewki przy ćwiczeniach z ciężarem od 40 kg.
6. Propozycja ciężaru bierze się z historii: gdy wszystkie serie na najcięższym ciężarze doszły do górnej granicy zakresu powtórzeń, aplikacja proponuje więcej.
7. W trakcie możesz zamienić ćwiczenie (u góry lista „Podobne do tego ćwiczenia”: ta sama partia, Twój sprzęt), dodać, usunąć lub zrobić „później” (przenosi na koniec). Do ćwiczenia możesz przypiąć notatkę (np. ustawienie maszyny), pokaże się w kolejnych treningach.
8. Trening w toku zapisuje się w bazie, więc przetrwa odświeżenie strony i zamknięcie karty.
9. „Zakończ i zapisz” pokazuje podsumowanie: nowe rekordy (najcięższa seria, szacowane 1RM, najwięcej powtórzeń) i porównanie z poprzednim takim treningiem. Możesz zapisać trening jako nowy preset (kategoria „Własne”).

## 5. Rekomendacje i regeneracja

Aplikacja tylko proponuje, decyzja jest zawsze Twoja. Reguły są stałe i jawne (plik `rekomendacje.py`, progi w słowniku `PROGI`).

- **Słaby dzień:** wynik snu poniżej 50 ORAZ gotowość poniżej 50% (Garmin). Bez zegarka: energia 1–2 ORAZ sen poniżej 6 godzin.
- **Pierwszy słaby dzień:** propozycja lżejszego treningu (około 20% mniej serii, ciężary bez zmian). **Drugi z rzędu:** propozycja odpoczynku.
- **Brak danych:** brak rekomendacji, Start pisze wprost, że nie ma dzisiejszych danych.
- **Partie z wczoraj:** gdy wczoraj mocno pracowały (co najmniej 4 serie wielostawowe, albo 8 serii w sumie, albo 3 serie ze średnim RPE od 9) i wybrany preset w co najmniej 40% wypada na nie, karta proponuje preset z innymi partiami.
- **Waga serii:** partia główna liczy się za 1, każda dodatkowa za 0,5 (np. wiosłowanie: plecy górne 1, plecy szerokie 0,5).
- **Mapa ciała (Postępy):** sylwetka z przodu i z tyłu, kolor wg liczby serii w bieżącym tygodniu (pon–ndz): szary brak, jasnozielony 1–4, zielony 5–9, fioletowy 10–16 (idealnie), żółty 17–20, pomarańczowy 21–25, czerwony 26 i więcej.

## 6. Dane: gdzie leżą, kopie, eksport, usuwanie

| Co | Gdzie |
| --- | --- |
| Twoja baza (właściciel) | `treningi.db` w folderze aplikacji |
| Baza zaproszonej osoby | `dane\<identyfikator>\treningi.db` |
| Kopie zapasowe | folder `kopie\` (kopia raz dziennie przy pierwszym uruchomieniu, zostaje 30 najnowszych; dodatkowe kopie przed edycją, usunięciem i dużymi migracjami) |
| Tokeny Garmina | folder `.garmin_tokeny\` |
| Temat powiadomień ntfy | `ntfy_temat.txt` |
| Klucze logowania Google | `.streamlit\secrets.toml` (po wyłączeniu logowania: `secrets.toml.off`) |

Żaden z tych elementów nie trafia do gita (pilnuje tego `.gitignore`, który łapie też każdą nazwę z „secrets”, np. `secrets.off.toml`).

- **Eksport:** Historia, Narzędzia: eksport CSV (otwiera się w Excelu). Profil, Dane i prywatność: eksport ZIP (tabele jako CSV, zdjęcie i opis) oraz kopia bazy do pobrania.
- **Kopia ręczna:** przycisk „Zrób kopię teraz”.
- **Ważne:** kopie leżą na tym samym dysku co baza. Raz na jakiś czas skopiuj `treningi.db`, `kopie\` i `dane\` na dysk zewnętrzny albo do chmury.
- **Usuwanie:** Profil, Dane i prywatność: usunięcie historii albo wszystkiego (trzeba wpisać słowo USUŃ). Przed usunięciem treningu aplikacja robi kopię, więc pomyłkę da się cofnąć z folderu `kopie\`.
- **Przywracanie kopii:** zamknij aplikację, skopiuj wybrany plik z `kopie\` jako `treningi.db` (zachowaj starą bazę pod inną nazwą), uruchom aplikację.

## 7. Logowanie i konta (dwa tryby pracy)

Pełny opis (zabezpieczenia, konfiguracja Google, test, dodawanie osób, tabela błędów) jest w dokumencie „OVRLD – logowanie, bezpieczeństwo i instrukcja obsługi” w Claude (Docs) i w projekcie TrainingApp. Tutaj to, co potrzebne na co dzień.

### Dwa tryby

| | TRYB TELEFON (bez logowania) | TRYB LOGOWANIE (Google) |
| --- | --- | --- |
| Plik z kluczami | `.streamlit\secrets.toml.off` (zmieniona nazwa) | `.streamlit\secrets.toml` (dokładnie taka nazwa) |
| Skąd otwierasz | telefon przez Tailscale (`http://100.x.x.x:8501`) i komputer | tylko komputer, `http://localhost:8501` |
| Logowanie | brak, od razu widzisz swoje dane | ekran „Zaloguj się przez Google”, wpuszcza tylko adresy z listy |
| Czyje dane | Twoje (`treningi.db`) | zależnie od konta: Twoje albo osobna baza osoby |
| Garmin i ntfy | działają | działają tylko na koncie właściciela |
| Do czego | codzienne używanie z telefonu na siłowni | testy logowania, sprawdzanie kont znajomych |

Na co dzień używasz trybu TELEFON. Tryb LOGOWANIE jest potrzebny tylko do testów, a docelowo (po wdrożeniu na serwer z domeną) będzie jedynym trybem, bo wtedy logowanie zadziała też z telefonu.

### Jak przełączyć tryb (jeden dwuklik)

Dwuklik **`PRZELACZ_LOGOWANIE.bat`**. Skrypt zmienia nazwę pliku z kluczami (`secrets.toml` ↔ `secrets.toml.off`), restartuje aplikację (robi to samo co `AKTUALIZUJ.bat`) i na końcu pisze, w którym trybie jesteś i co otworzyć. Nie czyta zawartości pliku z kluczami. Rozpoznaje też nazwy, które mogły powstać przy ręcznej zmianie (`secrets.off.toml`, `secrets.off`) i przywraca poprawną.

### Jak przełączyć ręcznie (gdyby skrypt nie działał)

1. Eksplorator, folder aplikacji, podfolder `.streamlit`. Włącz widoczność rozszerzeń: Widok, Pokaż, „Rozszerzenia nazw plików”. Bez tego Windows ukrywa `.toml` i łatwo o złą nazwę (np. powstaje `secrets.off.toml`).
2. Wyłączenie logowania: zmień nazwę `secrets.toml` na `secrets.toml.off`. Włączenie: odwrotnie.
3. Uruchom `AKTUALIZUJ.bat` (albo Ctrl+Alt+F9), żeby aplikacja wystartowała w nowym trybie.
4. Sprawdzenie: w oknie OVRLD-START pierwsze linie piszą „LOGOWANIE GOOGLE WŁĄCZONE” albo adres dla telefonu. W aplikacji Profil, sekcja Konto pokazuje, kto jest zalogowany.

Wyłączenie bez ruszania plików: zmienna środowiskowa `OVRLD_LOGOWANIE=0` (na stałe w Windows: Ustawienia, Zmienne środowiskowe). `OVRLD_LOGOWANIE=1` wymusza logowanie.

### Ważne zasady

- **Logowanie przez Google:** aplikacja nie zna haseł. Wchodzą tylko adresy z listy: właściciel plus zaproszeni. Każda osoba ma własną bazę.
- **Google przyjmuje powrót po zalogowaniu tylko na `http://localhost` albo https.** Dlatego w trybie logowania używasz `localhost`, a telefon przez adres Tailscale się nie zaloguje. Logowanie z telefonu zadziała po wdrożeniu na serwer z domeną.
- **Zalogowanie zostaje po restarcie** (ciasteczko w przeglądarce, mniej więcej 30 dni), dopóki się nie wylogujesz albo nie wyczyścisz ciasteczek. Dlatego po restarcie często nie widać ekranu logowania, a aplikacja i tak jest w trybie logowania.
- **Uszkodzony plik kluczy nie wyłącza logowania.** Jeśli `secrets.toml` ma błąd składni (np. brakujący cudzysłów), aplikacja pokazuje komunikat „Plik secrets.toml jest uszkodzony” i nikogo nie wpuszcza. Wcześniej taki błąd po cichu wyłączał logowanie. Na serwerze dodatkowo ustaw `OVRLD_LOGOWANIE=1`.
- **Wymagane biblioteki logowania:** `Authlib` i `httpx` (są w `requirements.txt`). Bez nich pojawia się błąd Internal Server Error.
- **Nie wklejaj do czatu, e-maili ani dokumentów** wartości `client_secret`, `cookie_secret`, haseł ani tokenów. Plik z kluczami wypełniasz sam w Notatniku.

## 8. Garmin i powiadomienia

**Garmin (tylko właściciel).** Dane do konta w pliku `.env` (`GARMIN_EMAIL`, `GARMIN_PASSWORD`, wzór w `.env.example`). Aplikacja zapamiętuje tokeny logowania w `.garmin_tokeny\`, więc nie loguje się hasłem przy każdym odświeżeniu. Po nieudanym logowaniu robi godzinną przerwę (plik `.garmin_blokada`). Gdy Garmin nie odpowiada, Start pokazuje ostatnie zapisane dane z bazy z komunikatem. Przełącznik „Mam zegarek Garmin” (Ustawienia i połączenie) wyłącza synchronizację i włącza tryb ręczny.

**Kafelki „Brak danych” na Starcie.** Garmin udostępnia wynik snu, czas snu, tętno spoczynkowe i HRV dopiero po przebudzeniu i synchronizacji zegarka z telefonem, więc wcześnie rano lub tuż po północy kafelki z dzisiejszą datą są puste, a wykresy z poprzednich dni działają. To nie jest błąd i nie zależy od logowania. Jeśli dane nie pojawiają się także w ciągu dnia: sprawdź, czy zegarek zsynchronizował się w aplikacji Garmin Connect na telefonie, czy Start nie pokazuje komunikatu „logowanie jest wstrzymane do …” (usuń wtedy plik `.garmin_blokada`, żeby przerwać pauzę), oraz czy w oknie OVRLD-START nie ma błędu połączenia.

**Powiadomienia ntfy (tylko właściciel).** Przy zablokowanym telefonie przychodzi „Koniec przerwy”. Nazwa tematu leży w `ntfy_temat.txt` i działa jak hasło: nie udostępniaj jej. Na telefonie potrzebna jest aplikacja ntfy zasubskrybowana na ten temat. Uwagi z „Zgłoś uwagę” przychodzą tą samą drogą (od innych osób z adresem nadawcy w tytule).

## 9. Wersje w gicie: zapis, wysyłka, cofanie

- **Zapis (commit):** dzieje się sam na końcu `AKTUALIZUJ.bat` (opis: „Aktualizacja: nazwy podmienionych plików” albo „Zmiany reczne”, z datą i godziną), albo ręcznie przez dwuklik `COMMIT.bat`. Z opisem: `COMMIT.bat "opis zmian"`. Skrypt przed zapisem sprawdza, czy git nie obejmuje haseł, baz i tokenów (każda nazwa z „secrets”, `.env`, `*.db`, `dane/`, `kopie/`, `ntfy_temat`, `.garmin_tokeny`), a jeśli tak, zatrzymuje się, wypisuje nazwy plików i niczego nie zapisuje.
- **Wysyłka na GitHub:** ręcznie. W folderze aplikacji otwórz wiersz poleceń (w pasku adresu Eksploratora wpisz `cmd`) i wpisz `git push`. Albo `COMMIT.bat "opis" wyslij` (zapis i wysyłka naraz).
- **Przeglądanie historii:** `git log --oneline -20` pokazuje ostatnie wersje (skrót, opis).
- **Zobaczenie, co się zmieniło:** `git show SKRÓT --stat`.
- **Cofnięcie jednego pliku do starej wersji:** `git restore --source=SKRÓT nazwa_pliku.py`, potem `AKTUALIZUJ.bat` (albo restart). Cofa tylko ten plik, nie rusza bazy ani innych plików. Baza nie jest w gicie, więc git nie cofnie danych (do tego służą kopie z folderu `kopie\`).
- **Zasada bezpieczeństwa:** w gicie nigdy nie ma `.env`, plików `secrets*`, `*.db`, `dane\`, `kopie\`, `ntfy_temat.txt`, `.garmin_tokeny\`. Jeśli dodasz nowy plik z hasłem, dopisz go do `.gitignore`.
- **Gdy plik z hasłem już trafił do lokalnego commita (a nie wysłałeś go na GitHub):** nie wysyłaj. Usuń go z lokalnych zapisów (`git rm --cached nazwa`, potem scalenie zapisów przez `git reset --soft origin/main`) i dopiero wtedy `git push`. Taki przypadek zdarzył się 24.10 po ręcznej zmianie nazwy pliku z kluczami (`secrets.off.toml`); naprawił go jednorazowy skrypt `NAPRAW_GIT.bat`. Jeśli klucz zdążył trafić na GitHub, trzeba go uznać za ujawniony: w Google Cloud wygeneruj nowy sekret klienta i unieważnij stary.

## 10. Pliki aplikacji

| Plik | Do czego służy |
| --- | --- |
| `app.py` | strony aplikacji, menu, formularz ręcznego treningu, motywy, uwagi |
| `logowanie.py`, `uzytkownik.py` | bramka logowania Google, lista adresów, ścieżka bazy danej osoby |
| `baza.py`, `narzedzia_bazy.py` | baza SQLite: tabele, zapis, odczyt, kopia |
| `sesja_treningowa.py` | prowadzony trening, historia, edycja, kopie, rekordy |
| `presety.py`, `presety_dane.py` | presety treningów (tabele, dane startowe, pakiety) |
| `baza_cwiczen.py`, `cwiczenia_meta.py`, `dane_cwiczen.json` | baza 847 ćwiczeń, wyszukiwanie, partie, typy |
| `plan.py` | plan tygodnia |
| `postepy.py`, `mapa_ciala.py` | strona Postępy i mapa ciała |
| `regeneracja.py`, `karty.py`, `karty_start.py`, `karty_presety.py`, `wykresy.py` | karty i wykresy |
| `rekomendacje.py` | reguły „Na dziś” |
| `profil.py` | profil, siłownia, dane i prywatność |
| `garmin.py`, `dziennik.py` | Garmin; ręczny dziennik dla osób bez zegarka |
| `powiadomienia.py`, `uwagi.py` | ntfy; „Zgłoś uwagę” |
| `motywy.py`, `styl.py`, `szklo.py` | kolory, motywy, efekt szkła |
| `START.bat`, `AKTUALIZUJ.bat`, `COMMIT.bat`, `PRZELACZ_LOGOWANIE.bat`, `GOSC.bat`, `GOSCIE.bat`, `PODMIANA.bat`, `UTWORZ_SKROT.bat`, `zarzadzaj.ps1` | skrypty uruchamiania, aktualizacji, zapisu wersji i przełączania trybu logowania |
| `.streamlit\config.toml` | ustawienia Streamlita i kolory widżetów |
| `static\`, `logo.svg` | ikona na ekran początkowy, logo |

Szczegółowa mapa funkcji jest w projekcie TrainingApp (`mapa-kodu.md`), po większych zmianach ją odświeżam.

## 11. Ustawienia przez zmienne środowiskowe

| Zmienna | Znaczenie |
| --- | --- |
| `OVRLD_LOGOWANIE` | `1` wymusza logowanie (serwer), `0` wyłącza (lokalnie). Bez niej: logowanie jest wymagane, gdy plik `secrets.toml` ma `[auth]` albo jest uszkodzony. |
| `OVRLD_WLASCICIEL` | adres właściciela (albo `wlasciciel` w sekcji `[ovrld]` pliku `secrets.toml`) |
| `OVRLD_DOZWOLONE` | adresy zaproszonych, po przecinku (albo `dozwolone` w `[ovrld]`) |
| `OVRLD_BAZA` | pełna ścieżka do osobnej bazy (tryb gościa, używa tego `GOSC.bat`) |
| `STREAMLIT_SERVER_PORT` | port aplikacji (domyślnie 8501) |

## 12. Gdy coś nie działa

| Objaw | Co zrobić |
| --- | --- |
| Telefon nie otwiera strony | Czy komputer jest włączony, aplikacja uruchomiona (okno OVRLD-START), Tailscale działa na komputerze i telefonie? Adres jest w oknie startowym. |
| Okno startowe pisze „Tailscale nie działa” | Włącz Tailscale i uruchom ponownie. |
| Po aktualizacji stary wygląd | Odśwież kartę na telefonie. Sprawdź, czy w folderze nie zostały pliki `*_NOWA.py` (zostają, gdy podmiana się nie udała, w oknie będzie „BLAD”). |
| Błąd w aplikacji (czerwony tekst) | Zrób zrzut ekranu i wklej do Claude. Dane są bezpieczne, baza ma kopie w `kopie\`. |
| Garmin: „chwilowo niedostępny” | To zwykle blokada po stronie Garmina. Start pokazuje ostatnie zapisane dane. Odczekaj godzinę (przerwa po nieudanym logowaniu). |
| Brak powiadomień o końcu przerwy | Czy aplikacja ntfy jest zasubskrybowana na właściwy temat, czy przełącznik powiadomień na ekranie startu jest włączony. |
| `COMMIT.bat` pisze STOP | Git obejmuje plik z hasłem lub danymi. Okno wypisuje jego nazwę. Zrób zrzut ekranu i napisz do Claude. |
| Logowanie Google: `redirect_uri_mismatch`, „Access blocked”, „Brak dostępu”, `invalid_client` | Patrz tabela błędów w dokumencie o logowaniu. Najczęściej: adres otwarty jako `127.0.0.1` zamiast `localhost`, albo w `secrets.toml` zostały wartości z szablonu (`WKLEJ_TU_...`). |
| Internal Server Error zaraz po starcie, w oknie błąd o `httpx` lub `authlib` | Brakuje bibliotek logowania. W wierszu poleceń w folderze aplikacji: `venv\Scripts\activate`, potem `pip install -r requirements.txt`. |
| Zamiast aplikacji komunikat „Plik secrets.toml jest uszkodzony” | Błąd składni w pliku kluczy (np. brak cudzysłowu, wklejony przypadkowy tekst). Otwórz plik w Notatniku i popraw wiersz albo zmień nazwę na `secrets.toml.off`, żeby wrócić do pracy bez logowania. |
| Telefon nie otwiera aplikacji, a na komputerze działa | Prawdopodobnie jesteś w trybie LOGOWANIE (okno pisze o `localhost`). Dwuklik `PRZELACZ_LOGOWANIE.bat`, żeby wrócić do trybu TELEFON. |
| Po restarcie nie ma ekranu logowania | To normalne: zalogowanie zapamiętuje ciasteczko (około 30 dni). Wyloguj się w Profilu, żeby zobaczyć ekran logowania. |
| Przy starcie otwiera się puste okno wiersza poleceń | Nowa wersja `AKTUALIZUJ.bat` nie otwiera już okna instancji gości. Jeśli nadal się pojawia, napisz do Claude. |
| Start pokazuje „Brak danych” przy śnie i tętnie | Patrz rozdział 8: Garmin podaje dzisiejsze dane po przebudzeniu i synchronizacji zegarka. |
| Usunąłeś trening przez pomyłkę | Zamknij aplikację i przywróć kopię z `kopie\` (patrz rozdział 6). |

## 13. Słowniczek

- **Preset:** gotowy zestaw ćwiczeń z seriami i zakresami powtórzeń (np. „Góra push: klatka i barki”). Nazwa presetu jest też rodzajem treningu w historii.
- **Partia:** grupa mięśni (Klatka, Plecy szerokie/górne/dolne, Barki przód/bok/tył, Biceps, Triceps, Czworogłowe, Dwugłowe uda, Pośladki, Łydki, Przywodziciele, Brzuch, Przedramiona, Szyja).
- **RPE:** skala wysiłku 1–10 (10 to maksimum, nic więcej by się nie dało).
- **1RM (szacowane):** ciężar, który podniósłbyś raz. Liczone wzorem Epleya: ciężar × (1 + powtórzenia / 30), wiarygodne do ok. 12 powtórzeń.
- **Objętość:** suma ciężar × powtórzenia (tylko ćwiczenia liczone w powtórzeniach).
- **Seria robocza / rozgrzewkowa:** robocza liczy się do planu, objętości i rekordów, rozgrzewkowa nie.
- **Gotowość:** prosty wynik 0–100% ze snu i tętna spoczynkowego, liczony przez aplikację (nie jest to wskaźnik Garmina).
- **Tailscale:** prywatna sieć między Twoim komputerem a telefonem, dzięki której aplikacja nie jest widoczna w internecie.

## 14. Plany

Kolejność ustalona 23.10.2026, stan na 24.10.2026:

1. Poprawki z telefonu (zgłaszane przez „Zgłoś uwagę”).
2. Logowanie Google: kod gotowy, lokalnie działa na koncie właściciela. Do zrobienia test na drugim koncie (dopisanie adresu w `dozwolone`) i test logowania z ikony na iPhonie (po wdrożeniu na serwer).
3. Onboarding nowej osoby: trzy kroki (imię i data urodzenia ze zgodami, sprzęt na siłowni), pusty plan, puste ekrany bez długiego samouczka.
4. Serwer VPS (Ubuntu) z domeną, https i kopiami poza serwerem (za ok. tydzień). Na serwerze: `OVRLD_LOGOWANIE=1`, nowy sekret klienta Google, osobny adres powrotu `https://adres/oauth2callback`.
5. Powiadomienia dla każdej osoby osobno (ntfy per użytkownik albo prawdziwe Web Push).
6. Przed udostępnieniem znajomym: wpisanie kontaktu administratora w tekście o prywatności, test na dwóch kontach, nowy `README.md` ze zrzutami ekranu, sprawdzenie nazwy OVRLD (znak towarowy), zmiana nazwy repozytorium.
7. Zaproszenie znajomych e-mailem (do 5 osób na start).

Znane drobiazgi: czcionki ładują się z Google Fonts (do samodzielnego hostowania potrzebny plik czcionki), kilka ćwiczeń w bazie ma niedokładny sprzęt.

## 15. Historia zmian (skrót)

- **24.10.2026:** przełączanie trybów jednym skryptem (`PRZELACZ_LOGOWANIE.bat`); uszkodzony `secrets.toml` nie wyłącza już logowania; `.gitignore` chroni każdą nazwę z „secrets”, a `COMMIT.bat` blokuje zapis takiego pliku; naprawa lokalnych commitów (`NAPRAW_GIT.bat`); „Brak danych” z Garmina po północy wyjaśnione (czekanie na synchronizację zegarka).
- **23.10.2026:** zmiana nazwy ELEVATE na OVRLD; osobne dane dla każdej osoby; logowanie Google; automatyczny zapis wersji w gicie; pierwsza wysyłka na GitHub; reguła dostępu Claude do danych (rozdział 16).

## 16. Zasady dostępu do danych (Claude)

Claude ma dostęp tylko do kodu i skryptów w folderze aplikacji. Plików z danymi osobistymi i sekretami nie otwiera bez Twojej wyraźnej zgody za każdym razem: `.env`, `.streamlit\secrets.toml` (i każdy plik `secrets*`), `.garmin_tokeny\`, `ntfy_temat.txt`, `treningi.db` i inne `*.db`, `dane\`, `kopie\`, `goscie\`, `goscie.txt`, Twoje eksporty i zdjęcia. Przed odczytem takiego pliku Claude pyta i tłumaczy, po co. Sekretów nie wypisuje w całości i nie zapisuje w dokumentach ani w repozytorium. Pliki z kluczami wypełniasz Ty, a Claude daje tylko szablon z napisami `WKLEJ_TU_...`. Ta sama zasada dotyczy Ciebie: nie wklejaj wartości kluczy do czatu.
