@echo off
rem Uruchamia aplikacje tak, zeby byla widoczna z telefonu przez Tailscale (adres zaczyna sie od 100.).
rem Bez Tailscale aplikacja nasluchuje tylko na tym komputerze (127.0.0.1), a nie w calej sieci Wi-Fi: nie ma logowania,
rem wiec nie moze byc dostepna dla kazdego w domu, na silowni czy w hotelu.
rem Parametry (w dowolnej kolejnosci): "cicho" = bez otwierania przegladarki (tak robi AKTUALIZUJ.bat),
rem "siec" = awaryjnie nasluchuj w calej sieci Wi-Fi (jak dawniej; tylko w zaufanej sieci).
cd /d "%~dp0"
title STRUO-START
call venv\Scripts\activate

set "TS="
for /f "usebackq delims=" %%i in (`tailscale ip -4 2^>nul`) do if not defined TS set "TS=%%i"
if not defined TS if exist "%ProgramFiles%\Tailscale\tailscale.exe" for /f "usebackq delims=" %%i in (`"%ProgramFiles%\Tailscale\tailscale.exe" ip -4 2^>nul`) do if not defined TS set "TS=%%i"
if defined TS if not "%TS:~0,4%"=="100." set "TS="

if not defined STREAMLIT_SERVER_PORT set "STREAMLIT_SERVER_PORT=8501"
set "ADRES=127.0.0.1"
if defined TS set "ADRES=%TS%"
if /i "%~1"=="siec" set "ADRES=0.0.0.0"
if /i "%~2"=="siec" set "ADRES=0.0.0.0"

rem Logowanie Google dziala tylko pod adresem localhost (Google nie przyjmuje powrotu na adres Tailscale).
rem Gdy w .streamlit\secrets.toml jest sekcja [auth] (i nie ustawiono STRUO_LOGOWANIE=0), startujemy tylko lokalnie.
rem Dawna nazwa zmiennej OVRLD_LOGOWANIE dziala dalej jako zapas.
set "TRYB_LOG=%STRUO_LOGOWANIE%"
if not defined TRYB_LOG set "TRYB_LOG=%OVRLD_LOGOWANIE%"
set "LOGOWANIE="
if exist ".streamlit\secrets.toml" findstr /i /c:"[auth]" ".streamlit\secrets.toml" >nul && set "LOGOWANIE=1"
if "%TRYB_LOG%"=="0" set "LOGOWANIE="
if "%TRYB_LOG%"=="1" set "LOGOWANIE=1"
if defined LOGOWANIE if not "%ADRES%"=="0.0.0.0" set "ADRES=127.0.0.1"

echo.
if defined LOGOWANIE goto :info_logowanie
if "%ADRES%"=="0.0.0.0" echo ===== TRYB "siec": aplikacja dostepna w calej sieci tego komputera, bez logowania! =====
if "%ADRES%"=="127.0.0.1" echo ===== UWAGA: Tailscale nie dziala, aplikacja jest tylko na tym komputerze. Wlacz Tailscale i uruchom ponownie. =====
if defined TS echo ===== Na telefonie wpisz: http://%TS%:%STREAMLIT_SERVER_PORT% =====
goto :po_info
:info_logowanie
echo ===== LOGOWANIE GOOGLE WLACZONE: otworz na tym komputerze http://localhost:%STREAMLIT_SERVER_PORT% =====
echo ===== Telefon przez Tailscale sie nie zaloguje. Zeby z niego korzystac, zmien nazwe .streamlit\secrets.toml na secrets.toml.off =====
:po_info
echo.

set "OPCJE=--server.address %ADRES%"
if /i "%~1"=="cicho" set "OPCJE=%OPCJE% --server.headless true"
if /i "%~2"=="cicho" set "OPCJE=%OPCJE% --server.headless true"
streamlit run app.py %OPCJE%
rem Okno zostaje tylko wtedy, gdy aplikacja zakonczyla sie bledem (zeby dalo sie go przeczytac)
if errorlevel 1 pause
