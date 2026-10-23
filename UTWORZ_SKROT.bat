@echo off
rem Jednorazowo: tworzy na pulpicie skrot "OVRLD aktualizacja" ze skrotem klawiszowym Ctrl+Alt+F9.
cd /d "%~dp0"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\OVRLD aktualizacja.lnk'); $s.TargetPath='%~dp0AKTUALIZUJ.bat'; $s.WorkingDirectory='%~dp0'; $s.Hotkey='CTRL+ALT+F9'; $s.Save()"
if errorlevel 1 (echo BLAD: nie udalo sie utworzyc skrotu) else (echo Gotowe. Na pulpicie jest skrot "OVRLD aktualizacja", dziala tez po wcisnieciu Ctrl+Alt+F9.)
echo.
pause
