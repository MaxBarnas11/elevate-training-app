@echo off
rem Jednym kliknieciem: zatrzymuje aplikacje, podmienia pliki *_NOWA.py i uruchamia ja od nowa.
cd /d "%~dp0"
echo Zatrzymuje aplikacje...
taskkill /F /T /FI "WINDOWTITLE eq ELEVATE-START" >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8501" ^| findstr "LISTENING"') do taskkill /F /T /PID %%p >nul 2>&1
timeout /t 2 /nobreak >nul
echo Podmieniam pliki...
set znaleziono=0
for %%f in (*_NOWA.py) do call :kopiuj "%%f"
if "%znaleziono%"=="0" echo Brak plikow *_NOWA.py do podmiany.
echo Uruchamiam aplikacje...
start "ELEVATE-START" "%~dp0START.bat"
timeout /t 2 /nobreak >nul
exit /b

:kopiuj
set "n=%~nx1"
set "c=%n:_NOWA.py=.py%"
copy /Y "%n%" "%c%" >nul
if errorlevel 1 (echo BLAD przy %c%) else (echo Podmieniono %c% & del "%n%")
set znaleziono=1
goto :eof
