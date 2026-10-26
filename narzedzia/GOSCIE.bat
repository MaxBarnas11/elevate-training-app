@echo off
rem Uruchamia wszystkie instancje gosci zapisane w goscie.txt (linia: imie port). Wywoluje to AKTUALIZUJ.bat po podmianie plikow.
cd /d "%~dp0.."
if not exist goscie.txt exit /b 0
for /f "usebackq tokens=1,2" %%a in ("goscie.txt") do start "OVRLD-GOSC-%%a" /min "%~dp0GOSC.bat" %%a %%b cicho
