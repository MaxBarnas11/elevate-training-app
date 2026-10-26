@echo off
rem Aktualizuje biblioteki ze znanymi lukami (pillow, certifi), sprawdza zgodnosc i powtarza audyt (WERSJE.bat).
rem Nie czyta zadnych plikow z danymi ani kluczami. Potrzebny internet.
cd /d "%~dp0.."
title STRUO-BIBLIOTEKI
if not exist "venv\Scripts\python.exe" (
  echo Brak folderu venv w folderze aplikacji.
  pause
  exit /b 1
)
echo.
echo 1/4 Zapisuje kopie obecnych wersji (requirements-przypiete-stare.txt)
copy /y requirements-przypiete.txt requirements-przypiete-stare.txt >nul
echo.
echo 2/4 Zatrzymuje aplikacje (inaczej Windows blokuje pliki bibliotek)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0zarzadzaj.ps1" zamknij
echo.
echo 3/4 Aktualizuje pillow i certifi
"venv\Scripts\python.exe" -m pip install --upgrade pillow certifi
echo.
echo Sprawdzam zgodnosc bibliotek (pip check). Brak uwag = wszystko pasuje do siebie:
"venv\Scripts\python.exe" -m pip check > narzedzia\wynik_pip_check.txt 2>&1
type narzedzia\wynik_pip_check.txt
echo.
echo 4/4 Powtarzam sprawdzenie luk
call "%~dp0WERSJE.bat"
echo.
echo Gdyby cos nie dzialalo, wersje sprzed zmiany: pip install -r requirements-przypiete-stare.txt
echo Na koniec uruchom AKTUALIZUJ.bat, zeby aplikacja wystartowala od nowa.
pause
