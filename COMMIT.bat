@echo off
rem COMMIT.bat - zapisuje biezacy stan aplikacji jako commit w gicie (tylko lokalnie).
rem Uzycie:  COMMIT.bat                     -> commit z data
rem          COMMIT.bat "opis zmian"        -> commit z opisem
rem          COMMIT.bat "opis" wyslij       -> commit i wyslanie na GitHub (push)
rem Parametr "auto" (uzywa go AKTUALIZUJ.bat) = bez pauzy na koncu.
setlocal
cd /d "%~dp0"
set "auto=0"
set "push=0"
set "opis="
for %%a in (%*) do call :arg "%%~a"

where git >nul 2>nul
if errorlevel 1 goto brakgita
if not exist ".git" goto brakrepo

git add -A 2>nul

rem Bezpiecznik: jesli git sledzi haslo, baze lub token, nic nie zapisujemy.
git ls-files | findstr /r /i "^\.env$ secrets\.toml \.db$ ^dane/ ^kopie/ ntfy_temat \.garmin_tokeny" >nul
if not errorlevel 1 goto wrazliwe

git diff --cached --quiet
if not errorlevel 1 goto brakzmian

for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH:mm"') do set "ts=%%i"
if "%opis%"=="" set "opis=Zmiany"
set "opis=%opis% [%ts%]"

git commit -q -m "%opis%"
if errorlevel 1 goto bladcommit
echo Zapisano wersje: %opis%
if "%push%"=="1" git push
goto koniec

:arg
if /i "%~1"=="auto" set "auto=1" & goto :eof
if /i "%~1"=="wyslij" set "push=1" & goto :eof
set "opis=%~1"
goto :eof

:brakgita
echo Nie znaleziono gita - wersja nie zostala zapisana.
goto koniec
:brakrepo
echo Ten folder nie jest repozytorium git - wersja nie zostala zapisana.
goto koniec
:wrazliwe
echo STOP: git sledzi plik z haslami lub danymi. Nic nie zapisano.
echo Podejrzane pliki:
git ls-files | findstr /r /i "^\.env$ secrets\.toml \.db$ ^dane/ ^kopie/ ntfy_temat \.garmin_tokeny"
git reset -q
echo Zrob zrzut ekranu tego okna i wklej go do Claude.
goto koniec
:bladcommit
echo Nie udalo sie zapisac wersji (blad gita).
goto koniec
:brakzmian
echo Brak zmian do zapisania.
:koniec
if "%auto%"=="0" pause
endlocal
exit /b 0
