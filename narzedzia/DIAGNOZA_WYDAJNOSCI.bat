@echo off
rem Sprawdza, ile kopii aplikacji dziala i co obciaza komputer. Nic nie zmienia i nie czyta danych.
title STRUO-DIAGNOZA-WYDAJNOSCI
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0DIAGNOZA_WYDAJNOSCI.ps1"
pause
