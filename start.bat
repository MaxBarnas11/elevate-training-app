@echo off
rem Uruchamia aplikacje tak, zeby byla widoczna z telefonu (ta sama siec Wi-Fi albo Tailscale).
cd /d "%~dp0"
title ELEVATE-START
call venv\Scripts\activate
echo.
echo ===== Adresy tego komputera (szukaj IPv4; Tailscale zaczyna sie od 100.) =====
ipconfig | findstr /i "IPv4"
echo ===== Na telefonie wpisz: http://ADRES:8501 =====
echo.
streamlit run app.py --server.address 0.0.0.0
pause
