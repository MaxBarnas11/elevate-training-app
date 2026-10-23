@echo off
rem Jednym kliknieciem: zamyka stara aplikacje, jej okna i stara karte w przegladarce, podmienia pliki *_NOWA.py i uruchamia aplikacje od nowa.
cd /d "%~dp0"
echo Zatrzymuje aplikacje...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0zarzadzaj.ps1" zamknij
timeout /t 2 /nobreak >nul
echo Podmieniam pliki...
set znaleziono=0
set "lista="
for %%f in (*_NOWA.py) do call :kopiuj "%%f"
if "%znaleziono%"=="0" echo Brak plikow *_NOWA.py do podmiany.
rem Zapis wersji w gicie (lokalnie, bez wysylania). Nie blokuje startu aplikacji.
if exist "%~dp0COMMIT.bat" (
  if "%lista%"=="" (call "%~dp0COMMIT.bat" auto "Zmiany reczne") else (call "%~dp0COMMIT.bat" auto "Aktualizacja:%lista%")
)
echo Uruchamiam aplikacje...
start "OVRLD-START" "%~dp0START.bat" cicho
rem Instancje gosci startujemy tylko wtedy, gdy sa zapisani (goscie.txt); cmd /c zamyka okno po zakonczeniu.
if exist "%~dp0goscie.txt" if exist "%~dp0GOSCIE.bat" start "" /min cmd /c "%~dp0GOSCIE.bat"
start "" /min powershell -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File "%~dp0zarzadzaj.ps1" otworz
timeout /t 2 /nobreak >nul
exit /b

:kopiuj
set "n=%~nx1"
set "c=%n:_NOWA.py=.py%"
copy /Y "%n%" "%c%" >nul
if not errorlevel 1 set "lista=%lista% %c%"
if errorlevel 1 (echo BLAD przy %c%) else (echo Podmieniono %c% & del "%n%")
set znaleziono=1
goto :eof
