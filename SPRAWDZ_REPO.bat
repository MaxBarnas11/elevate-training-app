@echo off
rem Kontrola repozytorium przed upublicznieniem. Niczego nie zmienia, nie pokazuje tresci plikow ani sekretow,
rem tylko nazwy plikow i liczby. Raport zapisuje sie w folderze DOKUMENTACJA (raport_repo.txt).
chcp 65001 >nul
cd /d "%~dp0"
where git >nul 2>nul
if errorlevel 1 (
  echo Nie znaleziono gita. Zainstaluj Git for Windows i uruchom ponownie.
  pause
  exit /b 1
)
if exist "venv\Scripts\python.exe" (set "PY=venv\Scripts\python.exe") else (set "PY=py")
"%PY%" sprawdz_repo.py
echo.
pause
