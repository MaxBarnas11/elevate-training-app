@echo off
rem PRZELACZ_LOGOWANIE.bat - przelacza aplikacje miedzy dwoma trybami:
rem   TRYB LOGOWANIE: plik .streamlit\secrets.toml jest na miejscu -> logowanie Google, aplikacja tylko pod http://localhost:8501
rem   TRYB TELEFON:   plik ma zmieniona nazwe (secrets.toml.off)   -> bez logowania, aplikacja dostepna z telefonu przez Tailscale
rem Skrypt tylko zmienia nazwe pliku (nie czyta jego tresci), potem uruchamia AKTUALIZUJ.bat, czyli restartuje aplikacje.
cd /d "%~dp0"
set "S=.streamlit"
if exist "%S%\secrets.toml" goto :wylacz

if exist "%S%\secrets.toml.off" ren "%S%\secrets.toml.off" secrets.toml
if exist "%S%\secrets.toml" goto :wlaczono
if exist "%S%\secrets.off.toml" ren "%S%\secrets.off.toml" secrets.toml
if exist "%S%\secrets.toml" goto :wlaczono
if exist "%S%\secrets.off" ren "%S%\secrets.off" secrets.toml
if exist "%S%\secrets.toml" goto :wlaczono
echo Nie znaleziono pliku z kluczami logowania w folderze .streamlit.
echo Szukalem: secrets.toml, secrets.toml.off, secrets.off.toml, secrets.off
pause
exit /b 1

:wlaczono
echo.
echo ===== TRYB LOGOWANIE (Google). Uruchamiam aplikacje... =====
call "%~dp0AKTUALIZUJ.bat"
echo.
echo ===== GOTOWE: TRYB LOGOWANIE =====
echo Otworz na tym komputerze:  http://localhost:8501
echo (z telefonu przez Tailscale sie nie zalogujesz; zeby uzywac z telefonu, uruchom ten skrypt jeszcze raz)
echo.
pause
exit /b 0

:wylacz
if exist "%S%\secrets.toml.off" (
  echo Jest juz plik %S%\secrets.toml.off, a obok niego secrets.toml. Nic nie zmieniam.
  echo Zrob zrzut ekranu tego okna i wklej go do Claude.
  pause
  exit /b 1
)
ren "%S%\secrets.toml" secrets.toml.off
echo.
echo ===== TRYB TELEFON (bez logowania). Uruchamiam aplikacje... =====
call "%~dp0AKTUALIZUJ.bat"
echo.
echo ===== GOTOWE: TRYB TELEFON =====
echo Na telefonie wpisz adres z okna STRUO-START (http://100.x.x.x:8501).
echo Bez logowania: kazdy, kto ma dostep do tego adresu, widzi Twoje dane (adres znasz tylko Ty i Tailscale).
echo.
pause
exit /b 0
