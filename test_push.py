"""Test powiadomień push przez ntfy (osobny skrypt, nie jest częścią aplikacji).

Uruchomienie (w folderze projektu):  venv\\Scripts\\python test_push.py
Opcjonalnie opóźnienie testu w sekundach:  venv\\Scripts\\python test_push.py 30
"""
import json
import secrets
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

SERWER = "https://ntfy.sh"
PLIK_TEMATU = Path(__file__).with_name("ntfy_temat.txt")


def wczytaj_temat() -> str:
    """Długa, losowa nazwa tematu (to jedyne „hasło” do powiadomień), zapamiętana w pliku obok skryptu."""
    if PLIK_TEMATU.exists():
        temat = PLIK_TEMATU.read_text(encoding="utf-8").strip()
        if temat:
            return temat
    temat = "elevate-" + secrets.token_urlsafe(18)
    PLIK_TEMATU.write_text(temat, encoding="utf-8")
    return temat


def wyslij(temat: str, tytul: str, tresc: str, priorytet: int = 4) -> None:
    dane = json.dumps({"topic": temat, "title": tytul, "message": tresc, "priority": priorytet,
                       "tags": ["alarm_clock"]}).encode("utf-8")
    zapytanie = urllib.request.Request(SERWER, data=dane, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(zapytanie, timeout=15) as odpowiedz:
        if odpowiedz.status != 200:
            raise RuntimeError(f"Serwer odpowiedział kodem {odpowiedz.status}")


def main() -> None:
    opoznienie = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    temat = wczytaj_temat()
    print("\nNazwa tematu (skopiuj dokładnie, to jak hasło):\n")
    print("    " + temat + "\n")
    print("Na iPhonie: aplikacja ntfy -> plus -> wklej nazwę tematu -> Subscribe.")
    input("Gdy temat jest dodany, naciśnij Enter tutaj... ")

    wyslij(temat, "ELEVATE: test 1", "Jeśli to widzisz, połączenie działa.", priorytet=3)
    print("Wysłano test 1 (od razu). Sprawdź, czy dotarł.")
    input("Teraz zablokuj telefon i połóż go na stole. Gdy będziesz gotowy, naciśnij Enter... ")

    print(f"Test 2 zostanie wysłany za {opoznienie} s. Nie dotykaj telefonu.")
    time.sleep(opoznienie)
    czas = datetime.now().strftime("%H:%M:%S")
    wyslij(temat, "ELEVATE: koniec przerwy", f"Czas na kolejną serię. Wysłano o {czas}.", priorytet=4)
    print(f"Wysłano test 2 o {czas}. Zapisz, o której godzinie telefon go pokazał (ekran zablokowany).")


if __name__ == "__main__":
    main()
