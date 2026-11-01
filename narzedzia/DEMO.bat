@echo off
rem Struo w trybie demo: przykladowe dane w folderze demo\, bez logowania, Garmina i powiadomien.
rem Twoja prawdziwa baza (treningi.db) nie jest otwierana. Adres: http://localhost:8503
rem Parametr "od-nowa" kasuje dane demo i tworzy je jeszcze raz:  narzedzia\DEMO.bat od-nowa
cd /d "%~dp0.."
title STRUO-DEMO
call venv\Scripts\activate
if /i "%~1"=="od-nowa" (python narzedzia\demo.py --od-nowa) else (python narzedzia\demo.py)
if errorlevel 1 pause
