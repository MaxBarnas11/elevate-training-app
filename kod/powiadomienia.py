"""Powiadomienia push przez ntfy (np. koniec przerwy przy zablokowanym telefonie).

Działa tylko, gdy obok aplikacji leży plik ntfy_temat.txt (tworzy go test_push.py) i powiadomienia nie są wyłączone
w ustawieniach. Każdy błąd (brak internetu, brak pliku) jest połykany: powiadomienie nie może zepsuć treningu.
Budziki żyją w procesie aplikacji; po jej zatrzymaniu przepadają.
"""
from __future__ import annotations

import json
import threading
import urllib.request
from datetime import datetime
from pathlib import Path

import uzytkownik

SERWER = "https://ntfy.sh"
PLIK_TEMATU = Path(__file__).with_name("ntfy_temat.txt")

_blokada = threading.Lock()
_budziki: dict[str, tuple[threading.Timer, str]] = {}   # klucz -> (zegar, czas docelowy)


def temat() -> str | None:
    """Nazwa tematu ntfy albo None, gdy powiadomienia nie są skonfigurowane."""
    try:
        t = PLIK_TEMATU.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return t or None


def dostepne() -> bool:
    """Powiadomienia o końcu przerwy idą na telefon właściciela, więc tylko jego konto może je włączyć."""
    return temat() is not None and uzytkownik.czy_wlasciciel()


def wyslij(tytul: str, tresc: str, priorytet: int = 4, tag: str = "alarm_clock") -> bool:
    """Wysyła powiadomienie. Zwraca True, gdy serwer je przyjął."""
    t = temat()
    if not t:
        return False
    try:
        dane = json.dumps({"topic": t, "title": tytul, "message": tresc, "priority": priorytet,
                           "tags": [tag]}).encode("utf-8")
        zapytanie = urllib.request.Request(SERWER, data=dane, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(zapytanie, timeout=10) as odp:
            return odp.status == 200
    except Exception:
        return False


def anuluj(klucz: str) -> None:
    with _blokada:
        wpis = _budziki.pop(klucz, None)
    if wpis:
        wpis[0].cancel()


def zaplanuj(klucz: str, kiedy: datetime, tytul: str, tresc: str, teraz: datetime | None = None) -> bool:
    """Ustawia budzik (jeden na klucz: nowy zastępuje stary; ten sam czas nic nie zmienia)."""
    teraz = teraz or datetime.now()
    opoznienie = (kiedy - teraz).total_seconds()
    znacznik = kiedy.isoformat()
    if opoznienie <= 0:
        anuluj(klucz)
        return False
    with _blokada:
        stary = _budziki.get(klucz)
        if stary and stary[1] == znacznik:
            return True
    anuluj(klucz)

    def _odpal() -> None:
        with _blokada:
            if _budziki.get(klucz, (None, ""))[1] == znacznik:
                _budziki.pop(klucz, None)
            else:
                return   # w międzyczasie zastąpiony lub anulowany
        wyslij(tytul, tresc)

    zegar = threading.Timer(opoznienie, _odpal)
    zegar.daemon = True
    with _blokada:
        _budziki[klucz] = (zegar, znacznik)
    zegar.start()
    return True


def synchronizuj_przerwe(przerwa_do: str | None, wlaczone: bool = True) -> None:
    """Ustawia budzik „koniec przerwy” na podaną godzinę (ISO) albo go kasuje (None, wyłączone, brak konfiguracji)."""
    try:
        if not przerwa_do or not wlaczone or not dostepne():
            anuluj("przerwa")
            return
        zaplanuj("przerwa", datetime.fromisoformat(przerwa_do), "Koniec przerwy", "Czas na kolejną serię.")
    except Exception:
        pass
