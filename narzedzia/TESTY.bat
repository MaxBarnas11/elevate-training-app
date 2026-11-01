@echo off
rem Uruchamia sprawdzenie kodu (ruff) i testy (pytest), tak samo jak GitHub po kazdym wyslaniu kodu.
rem Testy pracuja na tymczasowej bazie: nie dotykaja Twojego treningi.db. Za pierwszym razem doinstaluja pytest i ruff.
cd /d "%~dp0.."
call venv\Scripts\activate
python -m pytest --version >nul 2>nul || pip install -q -r requirements-dev.txt
echo.
echo ===== 1/2 Sprawdzenie kodu (ruff) =====
ruff check .
echo.
echo ===== 2/2 Testy (pytest) =====
python -m pytest
echo.
echo Gotowe. Jesli na koncu jest "passed" i nie ma "failed", wszystko dziala.
pause
