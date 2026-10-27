@echo off
rem Naprawia skrot "Struo aktualizacja" na pulpicie (sprawdza stare skroty z tym samym klawiszem, tworzy skrot z klawiszem Ctrl+Alt+U).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0SKROT_NAPRAW.ps1"
echo.
pause
