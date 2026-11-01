@echo off
rem Osobna instancja Struo dla goscia: wlasna, pusta baza (folder goscie\imie), wlasny port, bez Garmina wlasciciela.
rem Uzycie: narzedzia\GOSC.bat imie [port] [cicho]      np.  GOSC.bat ania 8502
rem Gosc wchodzi pod http://ADRES-TAILSCALE:port (musi miec dostep do Twojego komputera w Tailscale).
cd /d "%~dp0.."
if "%~1"=="" (
  echo Uzycie: GOSC.bat imie [port]    np.  GOSC.bat ania 8502
  pause
  exit /b 1
)
set "IMIE=%~1"
set "PORT=%~2"
if "%PORT%"=="" set "PORT=8502"
if not exist "goscie\%IMIE%" mkdir "goscie\%IMIE%"
set "ZAPISANY="
if exist goscie.txt for /f "usebackq tokens=1" %%a in ("goscie.txt") do if /i "%%a"=="%IMIE%" set "ZAPISANY=1"
if not defined ZAPISANY >>goscie.txt echo %IMIE% %PORT%
set "STRUO_BAZA=%CD%\goscie\%IMIE%\treningi.db"
set "STREAMLIT_SERVER_PORT=%PORT%"
call START.bat %3
