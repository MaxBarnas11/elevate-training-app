@echo off
rem NAPRAW_GIT.bat - JEDNORAZOWO. Usuwa z lokalnych, jeszcze nie wyslanych na GitHub zapisow (commitow) plik z kluczami logowania,
rem ktory git zapisal po zmianie jego nazwy (secrets.off.toml). Wszystkie pliki zostaja na dysku bez zmian.
rem Nic nie jest wysylane na GitHub. Po udanym przebiegu mozesz ten plik usunac.
cd /d "%~dp0"
where git >nul 2>nul
if errorlevel 1 goto brakgita
git rev-parse --verify origin/main >nul 2>nul
if errorlevel 1 goto brakorigin
echo Scalam lokalne zapisy w jeden, bez pliku z kluczami...
git reset --soft origin/main
git rm --cached -q --ignore-unmatch ".streamlit/secrets.off.toml" ".streamlit/secrets.toml" ".streamlit/secrets.toml.off" ".streamlit/secrets.off"
call "%~dp0COMMIT.bat" auto "Logowanie Google, dokumentacja, skrypty (bez kluczy)"
echo.
echo ===== SPRAWDZENIE: ponizej NIE powinno byc zadnej nazwy pliku =====
git ls-files | findstr /i secrets
echo ===== koniec sprawdzenia =====
echo.
echo Gotowe. Wersja jest zapisana lokalnie, na GitHub nic nie poszlo.
pause
exit /b 0
:brakgita
echo Nie znaleziono gita.
pause
exit /b 1
:brakorigin
echo Brak odniesienia origin/main (nie robiono jeszcze wysylki). Zrob zrzut ekranu i wklej do Claude.
pause
exit /b 1
