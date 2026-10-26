@echo off
rem Cofa pillow do wersji zgodnej ze Streamlitem 1.65 i sprawdza (bez instalowania), czy jest nowszy Streamlit zgodny z pillow 13.
rem Nie czyta zadnych plikow z danymi ani kluczami. Potrzebny internet.
cd /d "%~dp0.."
title STRUO-STREAMLIT
if not exist "venv\Scripts\python.exe" (
  echo Brak folderu venv w folderze aplikacji.
  pause
  exit /b 1
)
echo.
echo 1/3 Cofam pillow do 12.3.0 (zgodny z obecnym Streamlitem), certifi zostaje nowy
"venv\Scripts\python.exe" -m pip install --quiet "pillow==12.3.0"
"venv\Scripts\python.exe" -m pip check > narzedzia\wynik_streamlit.txt 2>&1
echo pip check po cofnieciu: >> narzedzia\wynik_streamlit.txt
echo.
echo 2/3 Dostepne wersje Streamlita
"venv\Scripts\python.exe" -m pip index versions streamlit >> narzedzia\wynik_streamlit.txt 2>&1
echo.
echo 3/3 Co zainstalowalby pip, gdyby pillow mialo byc 13 (tylko podglad, nic nie jest instalowane)
"venv\Scripts\python.exe" -m pip install --dry-run --upgrade streamlit "pillow>=13" >> narzedzia\wynik_streamlit.txt 2>&1
type narzedzia\wynik_streamlit.txt
echo.
echo Gotowe. Wynik jest tez w narzedzia\wynik_streamlit.txt (tylko nazwy i wersje bibliotek).
pause
