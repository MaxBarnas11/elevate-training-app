"""Diagnostyka listy zaproszonych. Pokazuje tylko nazwy sekcji i kluczy oraz zamaskowane adresy, nigdy hasel ani sekretow."""
import os
import sys
import tomllib
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent
PLIK = FOLDER / ".streamlit" / "secrets.toml"


def maska(a: str) -> str:
    lok, _, dom = a.partition("@")
    return (lok[:2] + "***@" + dom) if dom else (a[:2] + "***")


def lista(surowe) -> list[str]:
    return [a for a in (x.strip().lower() for x in str(surowe or "").replace(";", ",").split(",")) if a]


print("=== DIAGNOZA LOGOWANIA (bez wartosci tajnych) ===")
for nazwa in ("OVRLD_LOGOWANIE", "OVRLD_WLASCICIEL", "OVRLD_DOZWOLONE", "OVRLD_BAZA"):
    print(f"zmienna srodowiskowa {nazwa}: {'USTAWIONA' if os.environ.get(nazwa) else 'nieustawiona'}")
if not PLIK.is_file():
    print("Brak pliku .streamlit\\secrets.toml (tryb telefonu albo plik ma inna nazwe).")
    sys.exit(0)
try:
    dane = tomllib.loads(PLIK.read_text(encoding="utf-8-sig"))
except Exception as e:   # noqa: BLE001
    print("Plik secrets.toml ma BLAD SKLADNI:", type(e).__name__, str(e)[:120])
    sys.exit(0)
print("Sekcje w pliku:", ", ".join(f"[{k}]" for k, v in dane.items() if isinstance(v, dict)) or "brak")
print("Klucze luzem (poza sekcjami):", ", ".join(k for k, v in dane.items() if not isinstance(v, dict)) or "brak")
ov = dane.get("ovrld")
if not isinstance(ov, dict):
    print("UWAGA: nie ma sekcji [ovrld]. Klucze wlasciciel i dozwolone musza stac pod nagloweniem [ovrld].")
else:
    print("Klucze w [ovrld]:", ", ".join(ov) or "brak")
    for k in ("wlasciciel", "dozwolone"):
        print(f"  {k}:", [maska(a) for a in lista(ov.get(k))] or "PUSTE albo brak")
auth = dane.get("auth")
if isinstance(auth, dict):
    print("Klucze w [auth]:", ", ".join(auth))
    if "dozwolone" in auth or "wlasciciel" in auth:
        print("UWAGA: wlasciciel/dozwolone stoja w [auth], a maja byc w [ovrld].")
wpisany = input("\nWpisz adres drugiego konta (zostaje tylko na tym komputerze): ").strip().lower()
tak = isinstance(ov, dict) and wpisany in set(lista(ov.get("dozwolone"))) | set(lista(ov.get("wlasciciel")))
print("Ten adres jest na liscie:", "TAK" if tak else "NIE")
