@echo off
rem Jednym kliknieciem: zamyka stara aplikacje, jej okna i stara karte w przegladarce, podmienia pliki *_NOWA.py i uruchamia aplikacje od nowa.
rem Nowe wersje lezace w glownym folderze jako nazwa_NOWA.py trafiaja do kod\nazwa.py (a app_NOWA.py do app.py).
cd /d "%~dp0"
if not exist "kod\baza.py" (
  echo Najpierw uruchom PORZADKI.bat ^(jednorazowe uporzadkowanie folderow^).
  pause
  exit /b 1
)
echo Zatrzymuje aplikacje...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0narzedzia\zarzadzaj.ps1" zamknij
timeout /t 2 /nobreak >nul
echo Podmieniam pliki...
set znaleziono=0
set "lista="
for %%f in (*_NOWA.py) do call :kopiuj "%%f"
if "%znaleziono%"=="0" echo Brak plikow *_NOWA.py do podmiany.
rem Zapis wersji w gicie (lokalnie, bez wysylania). Nie blokuje startu aplikacji.
if exist "%~dp0narzedzia\COMMIT.bat" (
  if "%lista%"=="" (call "%~dp0narzedzia\COMMIT.bat" auto "Zmiany reczne") else (call "%~dp0narzedzia\COMMIT.bat" auto "Aktualizacja:%lista%")
)
echo Uruchamiam aplikacje...
start "STRUO-START" "%~dp0START.bat" cicho
rem Instancje gosci startujemy tylko wtedy, gdy sa zapisani (goscie.txt); cmd /c zamyka okno po zakonczeniu.
if exist "%~dp0goscie.txt" if exist "%~dp0narzedzia\GOSCIE.bat" start "" /min cmd /c "%~dp0narzedzia\GOSCIE.bat"
start "" /min powershell -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File "%~dp0narzedzia\zarzadzaj.ps1" otworz
timeout /t 2 /nobreak >nul
exit /b

:kopiuj
set "n=%~nx1"
set "c=%n:_NOWA.py=.py%"
if /i "%c%"=="app.py" (set "cel=%~dp0app.py") else (set "cel=%~dp0kod\%c%")
copy /Y "%n%" "%cel%" >nul
if not errorlevel 1 set "lista=%lista% %c%"
if errorlevel 1 (echo BLAD przy %c%) else (echo Podmieniono %c% & del "%n%")
set znaleziono=1
goto :eof
