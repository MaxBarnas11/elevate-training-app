@echo off
rem PORZADKI.bat - JEDNORAZOWO: przenosi pliki do nowej struktury folderow:
rem   kod\          moduly aplikacji (.py) i dane_cwiczen.json
rem   narzedzia\    skrypty pomocnicze (COMMIT.bat, GOSC.bat, UTWORZ_SKROT.bat, zarzadzaj.ps1, narzedzia_bazy.py ...)
rem   dokumentacja\ DOKUMENTACJA.md i STRUKTURA.md
rem Na wierzchu zostaja: app.py, START.bat, AKTUALIZUJ.bat, PRZELACZ_LOGOWANIE.bat oraz README.md i pliki konfiguracji.
rem Twoje dane (treningi.db, dane\, kopie\, .env, ntfy_temat.txt, .garmin_tokeny\) zostaja w miejscu i nie sa ruszane.
rem Przed przenosinami robi zapis wersji w gicie, wiec calosc mozna cofnac.
setlocal EnableExtensions
cd /d "%~dp0"
echo.
echo ===== PORZADKI: nowa struktura folderow OVRLD =====
echo.
if not exist "app.py" goto :zlyfolder
if exist "kod\baza.py" goto :juz
if not exist "narzedzia\COMMIT.bat" goto :brakpaczki
if not exist "narzedzia\GOSC.bat" goto :brakpaczki
if not exist "dokumentacja\STRUKTURA.md" goto :brakpaczki
if not exist "app_NOWA.py" goto :brakpaczki

echo [1/6] Zamykam aplikacje...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0zarzadzaj.ps1" zamknij
timeout /t 2 /nobreak >nul

echo [2/6] Zapisuje biezacy stan w gicie ^(punkt powrotu^)...
call "%~dp0COMMIT.bat" auto "Przed porzadkami"
set "BRUDNY="
for /f "delims=" %%i in ('git status --porcelain') do set "BRUDNY=1"
if defined BRUDNY goto :niezapisane

echo [3/6] Tworze foldery...
if not exist "kod" mkdir "kod"
if not exist "narzedzia" mkdir "narzedzia"
if not exist "dokumentacja" mkdir "dokumentacja"

echo [4/6] Przenosze pliki...
set "BLAD="
for %%f in (baza.py baza_cwiczen.py cwiczenia_meta.py dziennik.py garmin.py karty.py karty_presety.py karty_start.py logowanie.py mapa_ciala.py motywy.py plan.py postepy.py powiadomienia.py presety.py presety_dane.py profil.py regeneracja.py rekomendacje.py sesja_treningowa.py styl.py szklo.py uwagi.py uzytkownik.py wykresy.py dane_cwiczen.json) do call :przenies "%%f" kod
for %%f in (COMMIT.bat GOSC.bat GOSCIE.bat UTWORZ_SKROT.bat zarzadzaj.ps1 narzedzia_bazy.py test_push.py) do call :przenies "%%f" narzedzia
call :przenies DOKUMENTACJA.md dokumentacja
if exist "PODMIANA.bat" del /q "PODMIANA.bat"
if exist "NAPRAW_GIT.bat" del /q "NAPRAW_GIT.bat"
if exist "komponenty" rmdir /s /q "komponenty"
if exist "__pycache__" rmdir /s /q "__pycache__"
if defined BLAD goto :bledy

echo [5/6] Sprawdzam, czy wszystko jest na miejscu...
set "BRAK="
for %%f in (kod\baza.py kod\uzytkownik.py kod\logowanie.py kod\garmin.py kod\profil.py kod\sesja_treningowa.py kod\dane_cwiczen.json narzedzia\COMMIT.bat narzedzia\zarzadzaj.ps1 dokumentacja\DOKUMENTACJA.md dokumentacja\STRUKTURA.md app_NOWA.py) do if not exist "%%f" (echo BRAK: %%f & set "BRAK=1")
if defined BRAK goto :bledy

echo [6/6] Zapisuje nowa strukture w gicie i uruchamiam aplikacje...
call "%~dp0narzedzia\COMMIT.bat" auto "Porzadki: nowa struktura folderow"
call "%~dp0AKTUALIZUJ.bat"
echo.
echo ===== GOTOWE. Nowa struktura opisana jest w dokumentacja\STRUKTURA.md =====
echo Ten plik PORZADKI.bat usunie sie teraz sam.
pause
(goto) 2>nul & del "%~f0"

:przenies
rem  %1 = nazwa pliku w glownym folderze, %2 = folder docelowy.
rem  Jesli nowa wersja pliku lezy juz w folderze docelowym, stary plik z glownego folderu jest usuwany.
if not exist "%~1" goto :eof
if exist "%~2\%~1" (
  del /q "%~1"
  goto :eof
)
move /Y "%~1" "%~2\" >nul
if errorlevel 1 (echo BLAD przy przenoszeniu %~1 & set "BLAD=1")
goto :eof

:zlyfolder
echo Nie widze pliku app.py. Uruchom PORZADKI.bat z glownego folderu aplikacji.
pause
exit /b 1
:juz
echo Foldery sa juz uporzadkowane ^(jest kod\baza.py^). Nic nie robie.
pause
exit /b 0
:brakpaczki
echo Brakuje plikow z paczki ^(narzedzia\, dokumentacja\ lub app_NOWA.py^). Nic nie zmieniam.
echo Zrob zrzut ekranu tego okna i wklej go do Claude.
pause
exit /b 1
:niezapisane
echo STOP: nie udalo sie zapisac biezacego stanu w gicie ^(COMMIT.bat odmowil albo wystapil blad^). Nic nie przenosilem.
echo Zrob zrzut ekranu tego okna i wklej go do Claude.
pause
exit /b 1
:bledy
echo.
echo STOP: nie wszystko sie udalo ^(patrz wyzej^). Nie uruchamiam aplikacji.
echo Nic nie zostalo utracone: poprzedni stan jest zapisany w gicie jako "Przed porzadkami".
echo Zrob zrzut ekranu tego okna i wklej go do Claude, a przywroce porzadek.
pause
exit /b 1
