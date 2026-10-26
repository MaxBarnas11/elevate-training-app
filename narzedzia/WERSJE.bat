@echo off
rem Zapisuje dokladne wersje zainstalowanych bibliotek i sprawdza je pod katem znanych luk (pip-audit).
rem Nie czyta zadnych plikow z danymi ani kluczami. Potrzebny internet.
cd /d "%~dp0.."
title STRUO-WERSJE
if not exist "venv\Scripts\python.exe" (
  echo Brak folderu venv w folderze aplikacji.
  pause
  exit /b 1
)
echo.
echo 1/3 Zapisuje wersje zainstalowanych bibliotek do requirements-przypiete.txt
"venv\Scripts\python.exe" -m pip freeze > requirements-przypiete.txt
echo.
echo 2/3 Przygotowuje narzedzie pip-audit w folderze tymczasowym
set "AUDYT=%TEMP%\struo_audyt"
if exist "%AUDYT%" rmdir /s /q "%AUDYT%"
"venv\Scripts\python.exe" -m venv "%AUDYT%"
"%AUDYT%\Scripts\python.exe" -m pip install --quiet pip-audit
echo.
echo 3/3 Sprawdzam biblioteki pod katem znanych luk
"%AUDYT%\Scripts\python.exe" -m pip_audit -r requirements-przypiete.txt --no-deps > narzedzia\wynik_audytu.txt 2>&1
type narzedzia\wynik_audytu.txt
rmdir /s /q "%AUDYT%"
echo.
echo Gotowe. Wersje: requirements-przypiete.txt, wynik sprawdzenia: narzedzia\wynik_audytu.txt
echo Mozesz wkleic mi zawartosc wynik_audytu.txt (sa tam tylko nazwy bibliotek, wersje i numery luk).
pause
