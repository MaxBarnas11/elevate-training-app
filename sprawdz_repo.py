"""Kontrola repozytorium przed upublicznieniem. Uruchamiaj przez SPRAWDZ_REPO.bat.

Zasady bezpieczeństwa tego skryptu:
- niczego nie zmienia (tylko czyta przez git i wypisuje wyniki),
- nie wypisuje treści plików ani znalezionych sekretów, tylko NAZWY plików, skrócone numery commitów i liczby,
- pliki wrażliwe, które są w .gitignore (np. .env, baza, tokeny), w ogóle nie są otwierane: patrzymy tylko na to, co jest w gicie.
Raport zapisuje się w ..\\DOKUMENTACJA\\raport_repo.txt (poza repozytorium).
"""
from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KATALOG = Path(__file__).resolve().parent
RAPORT = KATALOG.parent / "DOKUMENTACJA" / "raport_repo.txt"
SLOWA = KATALOG.parent / "DOKUMENTACJA" / "sprawdz_slowa.txt"   # opcjonalnie: po jednym słowie w linii (nazwisko, miasto, siłownia)

WIERSZE: list[str] = []
LICZNIK = {"KRYTYCZNE": 0, "SPRAWDZ": 0}


def pisz(tekst: str = "") -> None:
    print(tekst)
    WIERSZE.append(tekst)


def uwaga(poziom: str, tekst: str) -> None:
    LICZNIK[poziom] += 1
    pisz(f"  [{poziom}] {tekst}")


def git(korzen: str, *arg: str, ok_kody: tuple[int, ...] = (0,)) -> str:
    wynik = subprocess.run(["git", "-c", "core.quotepath=false", "-C", korzen, *arg],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if wynik.returncode not in ok_kody:
        return ""
    return wynik.stdout


# Wzorce NAZW plików, których w publicznym repozytorium nie powinno być (ani w historii).
WRAZLIWE_SCIEZKI = [
    (r"(^|/)\.env$", "plik .env (hasła)"),
    (r"(^|/)secrets[^/]*$", "plik secrets* (sekrety logowania)"),
    (r"\.(db|sqlite|sqlite3)(-wal|-shm|-journal)?$", "baza danych"),
    (r"(^|/)ntfy_temat\.txt$", "ntfy_temat.txt (działa jak hasło)"),
    (r"(^|/)\.garmin_tokeny(/|$)", "tokeny Garmina"),
    (r"(^|/)\.garmin_blokada$", "plik stanu Garmina"),
    (r"^(dane|kopie|goscie)/", "dane użytkowników, kopie albo instancje gości"),
    (r"(^|/)goscie\.txt$", "lista gości"),
    (r"\.(pem|key|p12|pfx)$", "klucz lub certyfikat"),
    (r"\.(zip|7z|rar)$", "archiwum (eksport, kopia?)"),
    (r"(^|/)(export|eksport)[^/]*\.(csv|json)$", "eksport danych"),
]

# Wzorce TREŚCI (sprawdzane w całej historii; wypisujemy tylko nazwę pliku i commit, nigdy dopasowania).
WZORCE_SEKRETOW = [
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "klucz prywatny"),
    (r"ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}", "token GitHub"),
    (r"sk-ant-[A-Za-z0-9_-]{20,}", "klucz API Anthropic"),
    (r"AIza[0-9A-Za-z_-]{30,}", "klucz API Google"),
    (r"GOCSPX-[A-Za-z0-9_-]{10,}", "sekret klienta Google OAuth"),
    (r"(client_secret|cookie_secret)[[:space:]]*[=:][[:space:]]*[\"'][^\"']{8,}", "sekret w konfiguracji"),
    (r"(GARMIN_(PASSWORD|HASLO|PASS))[[:space:]]*=[[:space:]]*[^[:space:]#]{3,}", "hasło Garmina"),
    (r"ntfy\.sh/[A-Za-z0-9_-]{8,}", "adres tematu ntfy (działa jak hasło)"),
]

# Dane osobiste i śmieci w AKTUALNEJ wersji plików (tylko liczby dopasowań na plik).
WZORCE_OSOBISTE = [
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "adres e-mail"),
    (re.compile(r"\b100\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "adres Tailscale (100.x)"),
    (re.compile(r"\.ts\.net\b", re.IGNORECASE), "domena ts.net (Tailscale)"),
    (re.compile(r"[A-Za-z]:\\\\?(Users|ProjektApp)\\\\?", re.IGNORECASE), "ścieżka z Twojego komputera"),
]
STARE_NAZWY = re.compile(r"ELEVATE|OVRLD", re.IGNORECASE)
GOOGLE_FONTS = re.compile(r"fonts\.googleapis\.com|fonts\.gstatic\.com", re.IGNORECASE)
TEKSTOWE = {".py", ".md", ".txt", ".toml", ".json", ".bat", ".cfg", ".ini", ".yml", ".yaml", ".html", ".css", ".js", ".svg", ".example", ""}


def maska_email(a: str) -> str:
    lokalna, _, domena = a.partition("@")
    return f"{lokalna[:2]}***@{domena}"


def main() -> int:
    pisz("KONTROLA REPOZYTORIUM PRZED UPUBLICZNIENIEM")
    pisz("(wypisuje tylko nazwy plików i liczby; treści plików ani sekretów nie pokazuje)")
    pisz()
    korzen = git(str(KATALOG), "rev-parse", "--show-toplevel").strip()
    if not korzen:
        pisz("Nie znaleziono repozytorium gita w tym folderze (albo git nie jest zainstalowany).")
        return 1
    pisz(f"Folder repozytorium: {korzen}")

    # --- 1. Podstawowe informacje
    pisz("\n1. PODSTAWOWE INFORMACJE")
    zdalny = git(korzen, "remote", "get-url", "origin").strip()
    zdalny = re.sub(r"//[^/@]*@", "//", zdalny)          # bez loginu i tokenu w adresie
    pisz(f"  Zdalne repozytorium: {zdalny or '(brak)'}")
    pisz(f"  Gałąź: {git(korzen, 'rev-parse', '--abbrev-ref', 'HEAD').strip() or '?'}")
    rewizje = git(korzen, "rev-list", "--all").split()
    pisz(f"  Liczba commitów w historii: {len(rewizje)}")
    tagi = git(korzen, "tag").split()
    pisz(f"  Tagi: {', '.join(tagi) if tagi else '(brak)'}")

    # --- 2. Pliki wrażliwe w historii i w bieżącym drzewie
    pisz("\n2. PLIKI WRAŻLIWE W GICIE (historia i teraz)")
    historia = git(korzen, "log", "--all", "--name-only", "--pretty=format:@@%h")
    znalezione: dict[tuple[str, str], set[str]] = defaultdict(set)
    commit = ""
    for linia in historia.splitlines():
        if linia.startswith("@@"):
            commit = linia[2:]
        elif linia.strip():
            for wzor, opis in WRAZLIWE_SCIEZKI:
                if re.search(wzor, linia):
                    znalezione[(linia, opis)].add(commit)
    sledzone = set(git(korzen, "ls-files").splitlines())
    if not znalezione:
        pisz("  OK: w całej historii nie ma plików z listy wrażliwych.")
    for (sciezka, opis), commity in sorted(znalezione.items()):
        gdzie = "JEST W AKTUALNYM DRZEWIE" if sciezka in sledzone else "tylko w starszych commitach"
        uwaga("KRYTYCZNE", f"{sciezka} ({opis}); {gdzie}; commity: {', '.join(sorted(commity)[:4])}"
                           f"{' …' if len(commity) > 4 else ''}")

    # --- 3. Sekrety w treści całej historii
    pisz("\n3. SEKRETY W TREŚCI (cała historia)")
    trafienia: dict[tuple[str, str], set[str]] = defaultdict(set)
    for wzor, opis in WZORCE_SEKRETOW:
        for start in range(0, len(rewizje), 40):
            paczka = rewizje[start:start + 40]
            wynik = git(korzen, "grep", "-I", "-l", "-E", "-e", wzor, *paczka, ok_kody=(0, 1))
            for linia in wynik.splitlines():
                rew, _, sciezka = linia.partition(":")
                if sciezka:
                    trafienia[(sciezka, opis)].add(rew[:7])
    if not trafienia:
        pisz("  OK: wzorce znanych sekretów nie występują w żadnym commicie.")
    for (sciezka, opis), commity in sorted(trafienia.items()):
        przyklad = "example" in sciezka.lower() or sciezka.lower().endswith(".md")
        uwaga("SPRAWDZ" if przyklad else "KRYTYCZNE",
              f"{sciezka}: {opis}; w {len(commity)} commitach{' (może to tylko przykład w dokumentacji)' if przyklad else ''}")

    # --- 4. Czy .gitignore faktycznie chroni
    pisz("\n4. CZY .gitignore CHRONI TE PLIKI")
    sprawdz = [".env", "treningi.db", "ntfy_temat.txt", ".garmin_tokeny/x", ".streamlit/secrets.toml",
               ".streamlit/secrets.toml.off", "dane/x/treningi.db", "kopie/x.db", "goscie/x", "goscie.txt"]
    nie = [p for p in sprawdz if not git(korzen, "check-ignore", p, ok_kody=(0,)).strip()]
    if nie:
        for p in nie:
            uwaga("KRYTYCZNE", f"{p} NIE jest w .gitignore")
    else:
        pisz("  OK: wszystkie typowe pliki prywatne są ignorowane.")
    nieSledzone = [p for p in git(korzen, "ls-files", "--others", "--exclude-standard").splitlines() if p.strip()]
    if nieSledzone:
        pisz(f"  Nowe pliki, których git jeszcze nie śledzi i nie ignoruje ({len(nieSledzone)}), pierwsze 15:")
        for p in nieSledzone[:15]:
            pisz(f"    {p}")

    # --- 5. Dane osobiste i zewnętrzne wywołania w aktualnych plikach
    pisz("\n5. DANE OSOBISTE I POZOSTAŁOŚCI W AKTUALNYCH PLIKACH")
    slowa = []
    if SLOWA.exists():
        slowa = [s.strip() for s in SLOWA.read_text(encoding="utf-8", errors="replace").splitlines() if s.strip()]
        pisz(f"  Własne słowa do wyszukania: {len(slowa)} (z sprawdz_slowa.txt)")
    osobiste: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for sciezka in sorted(sledzone):
        plik = Path(korzen) / sciezka
        if plik.name == "sprawdz_repo.py":
            continue
        if plik.suffix.lower() not in TEKSTOWE or not plik.is_file() or plik.stat().st_size > 3_000_000:
            continue
        tekst = plik.read_text(encoding="utf-8", errors="ignore")
        for wzor, opis in WZORCE_OSOBISTE:
            n = len(wzor.findall(tekst))
            if n:
                osobiste[sciezka][opis] += n
        n = len(STARE_NAZWY.findall(tekst))
        if n:
            osobiste[sciezka]["stara nazwa (ELEVATE/OVRLD)"] += n
        if GOOGLE_FONTS.search(tekst):
            osobiste[sciezka]["ładowanie czcionek z Google (RODO)"] += 1
        for s in slowa:
            n = len(re.findall(re.escape(s), tekst, re.IGNORECASE))
            if n:
                osobiste[sciezka][f"Twoje słowo #{slowa.index(s) + 1}"] += n
    if not osobiste:
        pisz("  OK: nic nie znaleziono.")
    for sciezka, opisy in sorted(osobiste.items()):
        czesci = ", ".join(f"{o}: {n}" for o, n in sorted(opisy.items()))
        pisz(f"    {sciezka}: {czesci}")
    if osobiste:
        LICZNIK["SPRAWDZ"] += 1
        pisz("  [SPRAWDZ] Przejrzyj te pliki ręcznie; część (np. stara nazwa w historii zmian) to norma.")

    # --- 6. Autorzy commitów
    pisz("\n6. AUTORZY COMMITÓW (te dane stają się publiczne razem z historią)")
    autorzy = sorted({a for a in git(korzen, "log", "--all", "--format=%an <%ae>").splitlines() if a.strip()})
    for a in autorzy:
        nazwa, _, mail = a.partition(" <")
        mail = mail.rstrip(">")
        publiczny = "noreply" in mail
        pisz(f"  {nazwa} <{maska_email(mail) if mail else '?'}>{'' if publiczny else '  <- prawdziwy adres e-mail'}")
        if not publiczny and mail:
            LICZNIK["SPRAWDZ"] += 1
    sesje = git(korzen, "log", "--all", "--grep=claude.ai/code/session", "--format=%h").split()
    if sesje:
        pisz(f"  Commity z odnośnikiem do sesji Claude w opisie: {len(sesje)} (nieszkodliwe, ale widoczne publicznie)")

    # --- 7. Struktura projektu
    pisz("\n7. CZY REPOZYTORIUM MA TO, CO POWINNO MIEĆ")
    istnieje = lambda *nazwy: any((Path(korzen) / n).exists() for n in nazwy)
    sprawy = [
        ("README.md", istnieje("README.md"), "opis projektu"),
        ("LICENSE", istnieje("LICENSE", "LICENSE.md", "LICENSE.txt"), "licencja (bez niej kod nie jest otwarty)"),
        ("NOTICE / atrybucje", istnieje("NOTICE", "NOTICE.md", "THIRD_PARTY.md"), "wzmianka o bazie ćwiczeń i bibliotekach"),
        ("requirements.txt", istnieje("requirements.txt"), "lista bibliotek"),
        (".env.example", istnieje(".env.example"), "wzór konfiguracji bez haseł"),
        (".gitignore", istnieje(".gitignore"), "ochrona prywatnych plików"),
        ("CI (.github/workflows)", istnieje(".github/workflows"), "automatyczne testy po każdym wypchnięciu"),
    ]
    for nazwa, jest, po_co in sprawy:
        pisz(f"  {'OK    ' if jest else 'BRAK  '} {nazwa}: {po_co}")
    wersje = False
    req = Path(korzen) / "requirements.txt"
    if req.exists():
        linie = [x for x in req.read_text(encoding="utf-8", errors="ignore").splitlines() if x.strip() and not x.startswith("#")]
        wersje = bool(linie) and all("==" in x for x in linie)
        pisz(f"  requirements.txt: {len(linie)} pozycji, wersje {'przypięte' if wersje else 'NIE wszystkie przypięte (==)'}")
    testy = [p for p in sledzone if re.search(r"(^|/)test[^/]*\.py$", p)]
    pisz(f"  Pliki testów w repozytorium: {len(testy)}")

    # --- 8. Duże pliki
    pisz("\n8. DUŻE PLIKI W REPOZYTORIUM (powyżej 1 MB)")
    duze = []
    for sciezka in sledzone:
        plik = Path(korzen) / sciezka
        if plik.is_file() and plik.stat().st_size > 1_000_000:
            duze.append((plik.stat().st_size, sciezka))
    if not duze:
        pisz("  OK: brak.")
    for rozmiar, sciezka in sorted(duze, reverse=True):
        pisz(f"    {sciezka}: {rozmiar / 1_000_000:.1f} MB")
    obrazy = [p for p in sledzone if re.search(r"\.(jpe?g|png|heic|webp|gif|mp4|mov)$", p, re.IGNORECASE)]
    if obrazy:
        pisz(f"  Obrazy i wideo w repozytorium ({len(obrazy)}); upewnij się, że nie ma na nich Twoich danych (waga, twarz, nazwa siłowni):")
        for p in obrazy[:20]:
            pisz(f"    {p}")

    # --- Podsumowanie
    pisz("\nPODSUMOWANIE")
    pisz(f"  KRYTYCZNE: {LICZNIK['KRYTYCZNE']}  (rozwiąż przed upublicznieniem)")
    pisz(f"  DO SPRAWDZENIA: {LICZNIK['SPRAWDZ']}")
    if LICZNIK["KRYTYCZNE"]:
        pisz("  NIE upubliczniaj repozytorium, dopóki nie omówisz punktów KRYTYCZNE (zmiana haseł, czysta historia).")
    else:
        pisz("  Nic krytycznego nie znaleziono. Przejdź jeszcze punkty DO SPRAWDZENIA i listę z PUBLIKACJA.md.")
    try:
        RAPORT.parent.mkdir(parents=True, exist_ok=True)
        RAPORT.write_text("\n".join(WIERSZE) + "\n", encoding="utf-8")
        print(f"\nRaport zapisany: {RAPORT}")
    except OSError as e:
        print(f"\nNie udało się zapisać raportu: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
