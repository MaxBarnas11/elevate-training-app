@echo off
chcp 65001 >nul
cd /d "%~dp0"
set znaleziono=0
for %%f in (*_NOWA.py) do call :kopiuj "%%f"
if "%znaleziono%"=="0" echo Brak plikow *_NOWA.py do podmiany.
echo.
pause
goto :eof

:kopiuj
set "n=%~nx1"
set "c=%n:_NOWA.py=.py%"
copy /Y "%n%" "%c%" >nul
if errorlevel 1 (echo BLAD przy %c%) else (echo Podmieniono %c% & del "%n%")
set znaleziono=1
goto :eof
