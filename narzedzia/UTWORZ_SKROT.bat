@echo off
rem Jednorazowo: tworzy na pulpicie skrot "Struo aktualizacja" ze skrotem klawiszowym Ctrl+Alt+F9.
cd /d "%~dp0.."
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Struo aktualizacja.lnk'); $s.TargetPath='%CD%\AKTUALIZUJ.bat'; $s.WorkingDirectory='%CD%'; $s.Hotkey='CTRL+ALT+F9'; $s.Save()"
if errorlevel 1 (echo BLAD: nie udalo sie utworzyc skrotu) else (echo Gotowe. Na pulpicie jest skrot "Struo aktualizacja", dziala tez po wcisnieciu Ctrl+Alt+F9.)
echo.
pause
