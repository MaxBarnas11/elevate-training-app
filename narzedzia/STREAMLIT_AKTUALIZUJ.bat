@echo off
rem Aktualizuje Streamlit do 1.66.1 razem z pillow 13 (naprawa luk), sprawdza zgodnosc i powtarza audyt (WERSJE.bat).
rem Nie czyta zadnych plikow z danymi ani kluczami. Potrzebny internet.
cd /d "%~dp0.."
title STRUO-STREAMLIT-AKTUALIZACJA
if not exist "venv\Scripts\python.exe" (
  echo Brak folderu venv w folderze aplikacji.
  pause
  exit /b 1
)
echo.
echo 1/4 Zapisuje kopie obecnych wersji (requirements-przed-streamlit.txt)
"venv\Scripts\python.exe" -m pip freeze > requirements-przed-streamlit.txt
echo.
echo 2/4 Zatrzymuje aplikacje (inaczej Windows blokuje pliki bibliotek)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0zarzadzaj.ps1" zamknij
echo.
echo 3/4 Aktualizuje Streamlit i pillow
"venv\Scripts\python.exe" -m pip install --upgrade streamlit "pillow>=13"
echo.
echo Sprawdzam zgodnosc bibliotek (pip check). Brak uwag = wszystko pasuje do siebie:
"venv\Scripts\python.exe" -m pip check > narzedzia\wynik_pip_check.txt 2>&1
type narzedzia\wynik_pip_check.txt
echo.
echo 4/4 Powtarzam sprawdzenie luk
call "%~dp0WERSJE.bat"
echo.
echo Gdyby cos nie dzialalo, wersje sprzed zmiany: pip install -r requirements-przed-streamlit.txt
echo Na koniec uruchom AKTUALIZUJ.bat, zeby aplikacja wystartowala od nowa.
pause
