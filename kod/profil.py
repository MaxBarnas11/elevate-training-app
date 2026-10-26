"""Profil użytkownika: dane osobiste, zdjęcie, „Moja siłownia” (sprzęt), ulubione ćwiczenia oraz dane i prywatność
(eksport, kopia zapasowa, usuwanie).

Dziś aplikacja ma jednego użytkownika, więc profil to pojedyncze wiersze w bazie. Gdy dojdą konta, te same tabele dostaną
kolumnę z użytkownikiem i strona zadziała bez zmian. Zbieramy tylko to, co potrzebne (imię, data urodzenia, wzrost, cel wagi);
bez płci, adresu, telefonu i e-maila.
"""
from __future__ import annotations

import base64
import io
import json
import re
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

import pandas as pd

import baza
import uzytkownik

MAKS_IMIE = 40
MIN_WZROST, MAKS_WZROST = 100, 250
MIN_WAGA, MAKS_WAGA = 30.0, 300.0
WIEK_DOROSLOSCI = 18
WIEK_ZGODY_CYFROWEJ = 16            # w Polsce poniżej 16 lat dane przetwarza się za zgodą rodzica lub opiekuna
CEL_REDUKCJA = "Redukcja tkanki tłuszczowej"
CELE = ("Siła", "Masa mięśniowa", CEL_REDUKCJA, "Kondycja i zdrowie")   # cel treningowy (onboarding i Profil)
ROZMIAR_ZDJECIA = 256               # px, kwadrat
MAKS_BAJTOW_ZDJECIA = 8 * 1024 * 1024
MAKS_PIKSELI_ZDJECIA = 40_000_000

SPRZET_ZAWSZE = ("Masa ciała",)    # sprzęt, który „masz” zawsze (własne ciało); nie trzeba go zaznaczać
# „Typowa siłownia”: zestaw sprzętu większości klubów sieciowych; punkt wyjścia do poprawienia ręcznie
SPRZET_TYPOWY = ("Hantle", "Wyciąg", "Sztanga", "Sztanga łamana", "Maszyna", "Maszyna cardio", "Suwnica Smitha",
                 "Kettlebell", "Guma", "Piłka gimnastyczna", "Piłka lekarska")

# Tabele z danymi użytkownika, które zostają przy usuwaniu (to baza ćwiczeń i listy systemowe, nie dane osobowe)
TABELE_SYSTEMOWE = {"cwiczenia", "cwiczenia_aliasy", "typy_treningu", "sqlite_sequence"}
# Historia: wszystko, co powstaje z treningu i codziennych wpisów
TABELE_HISTORII = ("serie_wykonane", "wpisy_cwiczen", "sesje", "treningi", "trening_w_toku", "garmin_dziennie",
                   "samopoczucie", "dziennik_reczny", "uwagi")
KLUCZE_POUFNE = re.compile(r"topic|temat|ntfy|haslo|password|token|secret|klucz|key", re.IGNORECASE)
USTAWIENIA_ZOSTAJA = ("motyw",)     # po usunięciu wszystkiego motyw wyglądu zostaje (nie jest daną osobową)


# ---------------------------------------------------------------- baza

def _polacz() -> sqlite3.Connection:
    db = sqlite3.connect(baza.SCIEZKA_BAZY)
    db.execute("CREATE TABLE IF NOT EXISTS profil (Klucz TEXT PRIMARY KEY, Wartosc TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS profil_zdjecie (id INTEGER PRIMARY KEY CHECK (id = 1), Dane BLOB NOT NULL, Zapisano TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS profil_sprzet (Sprzet TEXT PRIMARY KEY)")
    db.execute("CREATE TABLE IF NOT EXISTS ulubione_cwiczenia (Nazwa TEXT PRIMARY KEY, Dodano TEXT)")
    return db


def _tabele(db: sqlite3.Connection) -> list[str]:
    return [w[0] for w in db.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]


# ---------------------------------------------------------------- dane osobowe

def wczytaj() -> dict:
    """Dane profilu: imie, data_ur (date), wzrost (int), waga_cel (float), cel (cel treningowy), onboarding (data ukończenia pierwszych
    kroków; puste = jeszcze nie przeszedł), zgoda_zdrowie i zgoda_opiekun (data zgody, tekst)."""
    with closing(_polacz()) as db:
        surowe = dict(db.execute("SELECT Klucz, Wartosc FROM profil").fetchall())
    wynik: dict = {"imie": (surowe.get("imie") or "").strip(), "data_ur": None, "wzrost": None, "waga_cel": None,
                   "zgoda_zdrowie": surowe.get("zgoda_zdrowie") or "", "zgoda_opiekun": surowe.get("zgoda_opiekun") or "",
                   "cel": surowe.get("cel") if surowe.get("cel") in CELE else "", "onboarding": surowe.get("onboarding") or ""}
    try:
        if surowe.get("data_ur"):
            wynik["data_ur"] = date.fromisoformat(surowe["data_ur"])
    except ValueError:
        pass
    try:
        if surowe.get("wzrost"):
            wynik["wzrost"] = int(float(surowe["wzrost"]))
    except ValueError:
        pass
    try:
        if surowe.get("waga_cel"):
            wynik["waga_cel"] = float(surowe["waga_cel"])
    except ValueError:
        pass
    return wynik


def zapisz(**pola) -> None:
    """Zapisuje podane pola. Wartość None albo pusty tekst usuwa pole. Walidacja zakresów jest tutaj, nie tylko w formularzu."""
    with closing(_polacz()) as db:
        for klucz, wartosc in pola.items():
            if klucz == "imie" and wartosc is not None:
                wartosc = re.sub(r"\s+", " ", str(wartosc)).strip()[:MAKS_IMIE]
            if klucz == "data_ur" and isinstance(wartosc, date):
                if wartosc > date.today() or wartosc.year < 1900:
                    wartosc = None
                else:
                    wartosc = wartosc.isoformat()
            if klucz == "wzrost" and wartosc is not None:
                wartosc = int(wartosc) if MIN_WZROST <= int(wartosc) <= MAKS_WZROST else None
            if klucz == "waga_cel" and wartosc is not None:
                wartosc = round(float(wartosc), 1) if MIN_WAGA <= float(wartosc) <= MAKS_WAGA else None
            if wartosc in (None, ""):
                db.execute("DELETE FROM profil WHERE Klucz = ?", (klucz,))
            else:
                db.execute("INSERT INTO profil (Klucz, Wartosc) VALUES (?, ?) "
                           "ON CONFLICT(Klucz) DO UPDATE SET Wartosc = excluded.Wartosc", (klucz, str(wartosc)))
        db.commit()


def wiek(data_ur: date | None, dzis: date | None = None) -> int | None:
    if not data_ur:
        return None
    dzis = dzis or date.today()
    return dzis.year - data_ur.year - ((dzis.month, dzis.day) < (data_ur.month, data_ur.day))


def niepelnoletni(dane: dict | None = None, dzis: date | None = None) -> bool:
    """Prawda, gdy z daty urodzenia wynika wiek poniżej 18 lat. Bez daty urodzenia: fałsz."""
    dane = dane if dane is not None else wczytaj()
    w = wiek(dane.get("data_ur"), dzis)
    return w is not None and w < WIEK_DOROSLOSCI


def wymaga_zgody_opiekuna(dane: dict | None = None, dzis: date | None = None) -> bool:
    dane = dane if dane is not None else wczytaj()
    w = wiek(dane.get("data_ur"), dzis)
    return w is not None and w < WIEK_ZGODY_CYFROWEJ


def pierwsze_imie(dane: dict | None = None) -> str:
    """Pierwsze słowo imienia, oczyszczone ze znaków Markdown (trafia do nagłówków)."""
    dane = dane if dane is not None else wczytaj()
    slowa = re.findall(r"[^\W\d_]+(?:[-'][^\W\d_]+)*", dane.get("imie") or "")
    return slowa[0] if slowa else ""


def powitanie(dane: dict | None = None, teraz: datetime | None = None) -> str | None:
    """Powitanie z imieniem zależne od pory dnia, np. „Dzień dobry, Maxi”. Bez imienia: None."""
    imie = pierwsze_imie(dane)
    if not imie:
        return None
    godz = (teraz or datetime.now()).hour
    pora = "Dzień dobry" if 5 <= godz < 17 else "Dobry wieczór" if 17 <= godz < 23 else "Cześć"
    return f"{pora}, {imie}"


def ostatnia_waga() -> tuple[float, str] | None:
    """Najnowsza waga ze wszystkich źródeł (wpis dnia, formularz treningu, trening w toku): (kg, data ISO)."""
    with closing(_polacz()) as db:
        zapytania = []
        tabele = set(_tabele(db))
        for tabela, kolumna_daty in (("dziennik_reczny", "Data"), ("treningi", "Data"), ("sesje", "Data")):
            if tabela in tabele:
                zapytania.append(f"SELECT {kolumna_daty} AS d, Waga AS w FROM {tabela} WHERE Waga IS NOT NULL")
        if not zapytania:
            return None
        w = db.execute(f"SELECT w, d FROM ({' UNION ALL '.join(zapytania)}) ORDER BY d DESC LIMIT 1").fetchone()
    return (float(w[0]), str(w[1])[:10]) if w else None


def zapisz_zgode(rodzaj: str, zgoda: bool) -> None:
    """Zapamiętuje zgodę z datą (rodzaj: zgoda_zdrowie albo zgoda_opiekun); odznaczenie ją usuwa."""
    if rodzaj not in ("zgoda_zdrowie", "zgoda_opiekun"):
        return
    zapisz(**{rodzaj: date.today().isoformat() if zgoda else None})


# ---------------------------------------------------------------- zdjęcie

def przetworz_zdjecie(bajty: bytes) -> tuple[bytes | None, str]:
    """Zdjęcie z telefonu → mały kwadratowy JPEG bez metadanych (EXIF z lokalizacją znika). Zwraca (dane, komunikat błędu)."""
    from PIL import Image, ImageOps, UnidentifiedImageError
    try:      # zdjęcia z iPhone'a (HEIC): działają, gdy zainstalowano pillow-heif (pip install pillow-heif)
        import pillow_heif
        pillow_heif.register_heif_opener()
    except Exception:   # noqa: BLE001 (brak biblioteki nie jest błędem; Safari na iPhonie i tak konwertuje zdjęcie)
        pass

    if not bajty:
        return None, "Pusty plik."
    if len(bajty) > MAKS_BAJTOW_ZDJECIA:
        return None, "Zdjęcie jest za duże (limit 8 MB)."
    try:
        with Image.open(io.BytesIO(bajty)) as obraz:
            if obraz.format not in ("JPEG", "PNG", "WEBP", "HEIF"):
                return None, "Obsługiwane formaty: JPG, PNG, WEBP i HEIC (z iPhone'a)."
            if obraz.width * obraz.height > MAKS_PIKSELI_ZDJECIA:
                return None, "Zdjęcie ma za dużo pikseli."
            obraz = ImageOps.exif_transpose(obraz)
            obraz = obraz.convert("RGBA")
            tlo = Image.new("RGB", obraz.size, (20, 20, 24))      # przezroczystość PNG na ciemnym tle
            tlo.paste(obraz, mask=obraz.getchannel("A"))
            obraz = ImageOps.fit(tlo, (ROZMIAR_ZDJECIA, ROZMIAR_ZDJECIA), method=Image.LANCZOS, centering=(0.5, 0.4))
            wyjscie = io.BytesIO()
            obraz.save(wyjscie, "JPEG", quality=86, optimize=True)      # bez parametru exif: metadane nie przechodzą
            return wyjscie.getvalue(), ""
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return None, "Nie udało się odczytać zdjęcia (format HEIC z iPhone'a wymaga pakietu pillow-heif albo wgrania z telefonu). Spróbuj inny plik."


def zapisz_zdjecie(bajty: bytes) -> tuple[bool, str]:
    dane, blad = przetworz_zdjecie(bajty)
    if dane is None:
        return False, blad
    with closing(_polacz()) as db:
        db.execute("INSERT INTO profil_zdjecie (id, Dane, Zapisano) VALUES (1, ?, ?) "
                   "ON CONFLICT(id) DO UPDATE SET Dane = excluded.Dane, Zapisano = excluded.Zapisano",
                   (dane, datetime.now().strftime("%Y-%m-%d %H:%M")))
        db.commit()
    return True, ""


def zdjecie() -> bytes | None:
    with closing(_polacz()) as db:
        w = db.execute("SELECT Dane FROM profil_zdjecie WHERE id = 1").fetchone()
    return bytes(w[0]) if w else None


def usun_zdjecie() -> None:
    with closing(_polacz()) as db:
        db.execute("DELETE FROM profil_zdjecie")
        db.commit()


def inicjaly(imie: str) -> str:
    slowa = re.findall(r"[^\W\d_]+", imie or "")
    return "".join(s[0] for s in slowa[:2]).upper()


_SYLWETKA_SVG = ("<svg viewBox='0 0 24 24' width='55%' height='55%' fill='none' stroke='currentColor' stroke-width='1.8' "
                 "stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='8' r='4'/><path d='M4 21c0-4.2 3.6-7 8-7s8 2.8 8 7'/></svg>")


def avatar_html(rozmiar: int = 64, dane: dict | None = None, foto: bytes | None = None) -> str:
    """Okrągły avatar w neonowej ramce: zdjęcie, a bez niego inicjały albo sylwetka."""
    dane = dane if dane is not None else wczytaj()
    foto = foto if foto is not None else zdjecie()
    if foto:
        zawartosc = ""
        tlo = f"background-image:url(data:image/jpeg;base64,{base64.b64encode(foto).decode('ascii')});background-size:cover;background-position:center;"
    else:
        ini = inicjaly(dane.get("imie", ""))
        zawartosc = _html_escape(ini) if ini else _SYLWETKA_SVG
        tlo = "background:var(--sz-mgla-lekka), var(--e-kafelek);"
    return (
        f"<div class='pr-av' style='width:{rozmiar}px;height:{rozmiar}px;'>"
        f"<div class='pr-av-w' style='{tlo}font-size:{max(rozmiar * 0.36, 12):.0f}px;'>{zawartosc}</div></div>"
    )


def _html_escape(tekst: str) -> str:
    import html
    return html.escape(tekst, quote=True)


# ---------------------------------------------------------------- siłownia: sprzęt i ulubione

def dostepny_sprzet() -> list[str]:
    """Rodzaje sprzętu z bazy ćwiczeń (bez ukrytych zaawansowanych), od najczęstszych."""
    with closing(_polacz()) as db:
        try:
            wiersze = db.execute(
                "SELECT Sprzet, COUNT(*) FROM cwiczenia WHERE Sprzet IS NOT NULL AND Sprzet <> '' AND COALESCE(Ukryte, 0) = 0 "
                "GROUP BY Sprzet ORDER BY COUNT(*) DESC, Sprzet").fetchall()
        except sqlite3.OperationalError:
            return []
    return [w[0] for w in wiersze]


def sprzet_wybrany() -> list[str]:
    with closing(_polacz()) as db:
        return [w[0] for w in db.execute("SELECT Sprzet FROM profil_sprzet ORDER BY Sprzet")]


def zapisz_sprzet(lista: list[str]) -> None:
    with closing(_polacz()) as db:
        db.execute("DELETE FROM profil_sprzet")
        db.executemany("INSERT OR IGNORE INTO profil_sprzet (Sprzet) VALUES (?)", [(s,) for s in dict.fromkeys(lista) if s])
        db.commit()


def dozwolony_sprzet(wybrany: list[str] | None = None) -> set[str] | None:
    """Zbiór nazw sprzętu, który masz (z „Masą ciała” i ćwiczeniami bez określonego sprzętu); None = nie filtruj
    (nic nie zaznaczono, więc zakładamy, że możesz wszystko)."""
    wybrany = sprzet_wybrany() if wybrany is None else wybrany
    if not wybrany:
        return None
    return set(wybrany) | set(SPRZET_ZAWSZE) | {""}


def ulubione() -> list[str]:
    with closing(_polacz()) as db:
        return [w[0] for w in db.execute("SELECT Nazwa FROM ulubione_cwiczenia ORDER BY Nazwa COLLATE NOCASE")]


def zapisz_ulubione(lista: list[str]) -> None:
    teraz = datetime.now().strftime("%Y-%m-%d")
    with closing(_polacz()) as db:
        db.execute("DELETE FROM ulubione_cwiczenia")
        db.executemany("INSERT OR IGNORE INTO ulubione_cwiczenia (Nazwa, Dodano) VALUES (?, ?)", [(n, teraz) for n in dict.fromkeys(lista) if n])
        db.commit()


def przelacz_ulubione(nazwa: str) -> bool:
    """Dodaje ćwiczenie do ulubionych albo je usuwa. Zwraca, czy jest teraz w ulubionych."""
    with closing(_polacz()) as db:
        jest = db.execute("SELECT 1 FROM ulubione_cwiczenia WHERE Nazwa = ?", (nazwa,)).fetchone()
        if jest:
            db.execute("DELETE FROM ulubione_cwiczenia WHERE Nazwa = ?", (nazwa,))
        else:
            db.execute("INSERT INTO ulubione_cwiczenia (Nazwa, Dodano) VALUES (?, ?)", (nazwa, date.today().isoformat()))
        db.commit()
    return not jest


# ---------------------------------------------------------------- eksport, kopia, usuwanie

def eksport_zip() -> bytes:
    """Wszystkie Twoje dane w jednym pliku ZIP: tabele jako CSV (Excel otwiera polskie znaki), zdjęcie i opis."""
    bufor = io.BytesIO()
    teraz = datetime.now()
    opis = [f"Eksport danych z aplikacji Struo, {teraz:%Y-%m-%d %H:%M}.", "",
            "Każdy plik CSV to jedna tabela z Twoimi danymi (kodowanie UTF-8).", ""]
    with zipfile.ZipFile(bufor, "w", zipfile.ZIP_DEFLATED) as z, closing(_polacz()) as db:
        for tabela in _tabele(db):
            if tabela in ("sqlite_sequence", "cwiczenia_aliasy", "typy_treningu", "profil_zdjecie"):
                continue
            if tabela == "cwiczenia":
                kolumny = {w[1] for w in db.execute("PRAGMA table_info(cwiczenia)")}
                warunki = [f"{k} IS NOT NULL" for k in ("Notatka",) if k in kolumny]
                if "Zrodlo" in kolumny:
                    warunki.append("Zrodlo IS NULL")
                df = pd.read_sql_query("SELECT * FROM cwiczenia" + (f" WHERE {' OR '.join(warunki)}" if warunki else ""), db)
                nazwa_pliku = "cwiczenia_wlasne_i_notatki.csv"
            elif tabela == "ustawienia":
                df = pd.read_sql_query("SELECT * FROM ustawienia", db)
                df = df[~df["Klucz"].astype(str).str.contains(KLUCZE_POUFNE)]
                nazwa_pliku = "ustawienia.csv"
            else:
                df = pd.read_sql_query(f'SELECT * FROM "{tabela}"', db)
                nazwa_pliku = f"{tabela}.csv"
            if df.empty:
                continue
            z.writestr(nazwa_pliku, df.to_csv(index=False).encode("utf-8-sig"))
            opis.append(f"{nazwa_pliku}: {len(df)} wierszy")
        foto = db.execute("SELECT Dane FROM profil_zdjecie WHERE id = 1").fetchone()
        if foto:
            z.writestr("zdjecie_profilowe.jpg", bytes(foto[0]))
            opis.append("zdjecie_profilowe.jpg")
        z.writestr("profil.json", json.dumps({**{k: (v.isoformat() if isinstance(v, date) else v) for k, v in wczytaj().items()},
                                              "sprzet": sprzet_wybrany(), "ulubione": ulubione()}, ensure_ascii=False, indent=2))
        z.writestr("OPIS.txt", "\n".join(opis) + "\n")
    return bufor.getvalue()


def kopia_bajty() -> bytes:
    """Spójna kopia całej bazy do pobrania (plik .db, otwierany w aplikacji lub w przeglądarce SQLite)."""
    with tempfile.TemporaryDirectory() as folder:
        cel = Path(folder) / "treningi.db"
        with closing(sqlite3.connect(baza.SCIEZKA_BAZY)) as zrodlo, closing(sqlite3.connect(cel)) as kopia:
            zrodlo.backup(kopia)
        return cel.read_bytes()


def ostatnia_kopia() -> datetime | None:
    folder = Path(baza.SCIEZKA_BAZY).parent / "kopie"
    try:
        pliki = list(folder.glob("treningi_*.db"))
        return datetime.fromtimestamp(max(p.stat().st_mtime for p in pliki)) if pliki else None
    except OSError:
        return None


def _usun_z_tabel(db: sqlite3.Connection, tabele: list[str]) -> dict[str, int]:
    istnieje = set(_tabele(db))
    ile: dict[str, int] = {}
    for t in tabele:
        if t in istnieje:
            ile[t] = db.execute(f'DELETE FROM "{t}"').rowcount
    return ile


def _wyczysc_plik(db_sciezka) -> None:
    with closing(sqlite3.connect(db_sciezka, isolation_level=None)) as db:
        db.execute("VACUUM")      # po usunięciu dane nie zostają w wolnych stronach pliku


def usun_historie() -> dict[str, int]:
    """Usuwa historię treningów i dzienne wpisy (zostają profil, plan, presety, ustawienia, baza ćwiczeń). Zwraca liczby wierszy."""
    with closing(_polacz()) as db:
        ile = _usun_z_tabel(db, list(TABELE_HISTORII))
        db.commit()
    _wyczysc_plik(baza.SCIEZKA_BAZY)
    return ile


def usun_wszystko() -> dict[str, int]:
    """Usuwa wszystkie dane osobowe: historię, profil z deklaracjami, zdjęcie, plan, presety, własne ćwiczenia i notatki,
    ustawienia oraz wszystkie kopie zapasowe w folderze kopie/. Zostaje baza ćwiczeń i motyw wyglądu."""
    with closing(_polacz()) as db:
        wszystkie = [t for t in _tabele(db) if t not in TABELE_SYSTEMOWE]
        ile = _usun_z_tabel(db, [t for t in wszystkie if t != "ustawienia"])
        if "ustawienia" in set(_tabele(db)):
            ile["ustawienia"] = db.execute(
                f"DELETE FROM ustawienia WHERE Klucz NOT IN ({','.join('?' * len(USTAWIENIA_ZOSTAJA))})", USTAWIENIA_ZOSTAJA
            ).rowcount
        try:
            ile["cwiczenia_wlasne"] = db.execute("DELETE FROM cwiczenia WHERE Zrodlo IS NULL").rowcount
            db.execute("UPDATE cwiczenia SET Notatka = NULL WHERE Notatka IS NOT NULL")
        except sqlite3.OperationalError:
            pass
        db.commit()
    folder = Path(baza.SCIEZKA_BAZY).parent
    usuniete = 0
    for wzorzec_folder, wzorzec in ((folder / "kopie", "*.db"), (folder, "treningi_kopia_*.db")):
        try:
            for plik in wzorzec_folder.glob(wzorzec):
                if plik.resolve() != Path(baza.SCIEZKA_BAZY).resolve():
                    plik.unlink(missing_ok=True)
                    usuniete += 1
        except OSError:
            pass
    ile["kopie_zapasowe"] = usuniete
    _wyczysc_plik(baza.SCIEZKA_BAZY)
    return ile


def potwierdzenie_poprawne(tekst: str) -> bool:
    """Słowo potwierdzające usuwanie: „USUŃ” (przyjmujemy też „usun”, bo na telefonie trudno wpisać Ń)."""
    return (tekst or "").strip().casefold().replace("ń", "n") == "usun"


# ---------------------------------------------------------------- wygląd (kafelek w menu i nagłówek profilu)

CSS_PROFIL = """
<style>
.pr-av { border-radius: 50%; padding: 3px; flex: 0 0 auto; background: var(--sz-ramka);
         box-shadow: 0 0 18px color-mix(in srgb, var(--e-g2) 40%, transparent); }
.pr-av-w { width: 100%; height: 100%; border-radius: 50%; display: flex; align-items: center; justify-content: center;
           font-weight: 800; letter-spacing: 0.02em; color: var(--e-tekst); overflow: hidden; }
.pr-hero { display: flex; align-items: center; gap: 16px; padding: 16px; margin: 0 0 12px 0; border-radius: 18px;
           border: 1.5px solid var(--e-obram2); background: var(--sz-mgla-lekka), var(--sz-baza); box-shadow: var(--sz-polysk); }
.pr-hero-imie { font-weight: 800; font-size: 1.35rem; line-height: 1.15; color: var(--e-tekst); overflow-wrap: anywhere; }
.pr-hero-info { margin-top: 4px; font-weight: 600; color: var(--e-przyg); }
.pr-kafle { display: flex; gap: 8px; margin: 0 0 12px 0; }
.pr-kafel { flex: 1 1 0; min-width: 0; padding: 10px 12px; border-radius: 14px; border: 1.5px solid var(--e-obram2);
            background: var(--sz-mgla-lekka), var(--sz-baza); box-shadow: var(--sz-polysk); }
.pr-kafel-et { font-size: 0.68rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--e-przyg); }
.pr-kafel-w { font-weight: 800; font-size: 1.25rem; color: var(--e-tekst); white-space: nowrap; }
.pr-kafel-w small { font-size: 0.8rem; font-weight: 600; color: var(--e-przyg); }
.pr-kafel-dobry .pr-kafel-w { color: var(--e-zielony); }
.pr-sekcja { font-family: inherit; font-weight: 800; font-size: 1.05rem; letter-spacing: 0.1em; text-transform: uppercase;
             color: var(--e-tekst); margin: 6px 0 2px 0; }
.pr-bok { display: flex; align-items: center; gap: 12px; padding: 10px 14px; border-radius: 14px;
          border: 1.5px solid var(--e-obram2); background: var(--sz-mgla-lekka), var(--sz-baza); box-shadow: var(--sz-polysk); }
.pr-bok-imie { font-weight: 800; color: var(--e-tekst); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pr-bok-pod { font-size: 0.78rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--e-przyg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.st-key-profil_kafelek { position: relative; padding-bottom: 12px; }
.pr-linia { height: 1px; background: var(--e-obram2); margin: 12px 0 24px 0; }   /* odstęp ok. 19 px nad i pod kafelkiem, jak nad profilem */
.st-key-profil_kafelek [data-testid="stElementContainer"]:has([data-testid="stPageLink"]) { position: absolute; inset: 0 0 12px 0; margin: 0; height: auto !important; }
.st-key-profil_kafelek [data-testid="stPageLink"], .st-key-profil_kafelek [data-testid="stPageLink"] a { display: block; width: 100%; height: 100%; }
.st-key-profil_kafelek [data-testid="stPageLink"] a { opacity: 0; }
[class*="st-key-profil_usun"] button { color: var(--e-kasuj) !important; border-color: var(--e-kasuj_ramka) !important; }
</style>
"""


def kafelek_boczny_html(dane: dict | None = None) -> str:
    """Mały kafelek do menu bocznego: avatar, imię, podpis „Mój profil”."""
    dane = dane if dane is not None else wczytaj()
    imie = _html_escape(dane.get("imie") or "Mój profil")
    pod = "Twój profil" if dane.get("imie") else "Uzupełnij dane"
    return (f"<div class='pr-bok'>{avatar_html(44, dane)}<div style='min-width:0;'>"
            f"<div class='pr-bok-imie'>{imie}</div><div class='pr-bok-pod'>{pod}</div></div></div>")


def _kg(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def kafle_wagi(dane: dict, waga: tuple[float, str] | None) -> list[dict]:
    """Kafelki pod nagłówkiem: waga, cel i różnica do celu (cel pomijamy u osób niepełnoletnich)."""
    kafle: list[dict] = []
    if waga:
        d = waga[1][8:10] + "." + waga[1][5:7] if len(waga[1]) >= 10 else ""
        kafle.append({"et": f"Waga {d}".strip(), "w": _kg(waga[0]), "jed": "kg"})
    cel = dane.get("waga_cel")
    if cel and not niepelnoletni(dane):
        kafle.append({"et": "Cel", "w": _kg(cel), "jed": "kg"})
        if waga:
            roznica = waga[0] - cel
            w_celu = abs(roznica) < 0.05
            kafle.append({"et": "Do celu", "w": "w celu" if w_celu else f"{'−' if roznica > 0 else '+'}{_kg(abs(roznica))}",
                          "jed": "" if w_celu else "kg", "dobry": w_celu})
    return kafle


def opis_wieku_i_wzrostu(dane: dict) -> str:
    w = wiek(dane.get("data_ur"))
    czesci = ([f"{w} lat"] if w is not None else []) + ([f"{dane['wzrost']} cm"] if dane.get("wzrost") else [])
    return " · ".join(czesci) or "Uzupełnij dane poniżej"


def hero_args(dane: dict, waga: tuple[float, str] | None, foto: bytes | None, motyw: str | None = None) -> dict:
    """Argumenty komponentu z nagłówkiem profilu (avatar, który jest przyciskiem wgrywania zdjęcia)."""
    from motywy import PALETA
    klucze = ("tlo", "tekst", "przyg", "obram2", "kafelek", "g1", "g2", "g3", "zielony", "kasuj", "przycisk_tekst",
              "tytul_glow2", "tytul_glow3", "cien_m")
    paleta = {"light": {k: PALETA[k][0] for k in klucze}, "dark": {k: PALETA[k][1] for k in klucze}}
    return {
        "imie": dane.get("imie") or "", "info": opis_wieku_i_wzrostu(dane), "inicjaly": inicjaly(dane.get("imie", "")),
        "foto": ("data:image/jpeg;base64," + base64.b64encode(foto).decode("ascii")) if foto else "",
        "kafle": kafle_wagi(dane, waga), "paleta": paleta, "motyw": motyw if motyw in ("light", "dark") else "",
    }


_KOMPONENT = None
_PRZETWORZONE: list[str] = []       # identyfikatory już obsłużonych zdarzeń komponentu (komponent oddaje ostatnią wartość przy każdym przebiegu)


def _komponent():
    """Komponent nagłówka (plik index.html powstaje obok aplikacji przy pierwszym użyciu)."""
    global _KOMPONENT
    if _KOMPONENT is None:
        import streamlit.components.v1 as components
        folder = Path(__file__).parent / "komponenty" / "profil_hero"
        folder.mkdir(parents=True, exist_ok=True)
        plik = folder / "index.html"
        if not plik.exists() or plik.read_text(encoding="utf-8") != HTML_HERO:
            plik.write_text(HTML_HERO, encoding="utf-8")
        _KOMPONENT = components.declare_component("ovrld_profil_hero", path=str(folder))
    return _KOMPONENT


def obsluz_odpowiedz_komponentu(odp) -> str | None:
    """Zdarzenie z nagłówka: zapis albo usunięcie zdjęcia. Zwraca komunikat błędu, "" po udanej zmianie albo None, gdy nic do zrobienia."""
    if not isinstance(odp, dict) or not odp.get("id") or odp["id"] in _PRZETWORZONE:
        return None
    _PRZETWORZONE.append(odp["id"])
    del _PRZETWORZONE[:-50]
    if odp.get("akcja") == "usun":
        usun_zdjecie()
        return ""
    if odp.get("akcja") == "zapisz":
        try:
            bajty = base64.b64decode(odp.get("dane") or "", validate=True)
        except (ValueError, TypeError):
            return "Nie udało się odczytać zdjęcia."
        ok, blad = zapisz_zdjecie(bajty)
        return "" if ok else blad
    return None


def naglowek_profilu_html(dane: dict | None = None, waga: tuple[float, str] | None = None) -> str:
    """Duży nagłówek strony Profil: avatar, imię, wiek i wzrost, a pod nim kafelki wagi i celu."""
    dane = dane if dane is not None else wczytaj()
    w = wiek(dane.get("data_ur"))
    czesci = []
    if w is not None:
        czesci.append(f"{w} lat")
    if dane.get("wzrost"):
        czesci.append(f"{dane['wzrost']} cm")
    info = " · ".join(czesci) or "Uzupełnij dane poniżej"
    imie = _html_escape(dane.get("imie") or "Twój profil")
    html_ = (f"<div class='pr-hero'>{avatar_html(84, dane)}<div style='min-width:0;'>"
             f"<div class='pr-hero-imie'>{imie}</div><div class='pr-hero-info'>{_html_escape(info)}</div></div></div>")
    kafle = [f"<div class='pr-kafel{' pr-kafel-dobry' if k.get('dobry') else ''}'><div class='pr-kafel-et'>{_html_escape(k['et'])}</div>"
             f"<div class='pr-kafel-w'>{_html_escape(k['w'])}{' <small>' + k['jed'] + '</small>' if k.get('jed') else ''}</div></div>"
             for k in kafle_wagi(dane, waga)]
    return html_ + (f"<div class='pr-kafle'>{''.join(kafle)}</div>" if kafle else "")


# ---------------------------------------------------------------- teksty: informacja o prywatności i zasady (wersja robocza do przeglądu prawnika)

KONTAKT_ADMINISTRATORA = "ovrld.kontakt@gmail.com"     # np. adres e-mail do spraw danych; puste = „osoba, która udostępniła Ci aplikację”


def informacja_o_prywatnosci() -> str:
    admin = "osoba, która udostępniła Ci tę aplikację" + (f" ({KONTAKT_ADMINISTRATORA})" if KONTAKT_ADMINISTRATORA else "")
    return (
        f"**Administrator:** {admin}.\n\n"
        "**Jakie dane zapisujemy:** imię, datę urodzenia, wzrost, cel wagi i cel treningowy, zdjęcie profilowe (jeśli dodasz), treningi, serie i ciężary, "
        "wagę, sen, tętno oraz inne dane o zdrowiu i samopoczuciu, notatki i zgłoszone uwagi.\n\n"
        "**Po co:** tylko do działania aplikacji: historia, postępy i podpowiedzi treningowe. Nie sprzedajemy danych, nie używamy ich do reklam ani analityki.\n\n"
        "**Podstawa prawna:** Twoja zgoda (art. 6 ust. 1 lit. a oraz art. 9 ust. 2 lit. a RODO). Możesz ją cofnąć w każdej chwili w Profilu "
        "(Dane i prywatność); cofnięcie nie wpływa na zgodność z prawem przetwarzania sprzed cofnięcia.\n\n"
        "**Gdzie leżą dane:** w bazie na komputerze lub serwerze, na którym działa aplikacja; dostęp ma administrator.\n\n"
        "**Co trafia poza to miejsce (tylko gdy włączone):** powiadomienia i zgłoszone uwagi do serwisu ntfy.sh (gdy skonfigurowano powiadomienia), "
        "dane pobierane z Garmina (gdy podłączysz zegarek) oraz czcionka nagłówków z Google Fonts (Google widzi wtedy Twój adres IP).\n\n"
        "**Pliki cookies i pamięć przeglądarki:** tylko niezbędne do działania: sesja, zabezpieczenie formularzy i zapamiętany motyw. "
        "Bez analityki i reklam.\n\n"
        "**Jak długo:** do czasu, aż usuniesz dane w Profilu. „Usuń wszystkie moje dane” kasuje też kopie zapasowe.\n\n"
        "**Twoje prawa:** dostęp i kopia danych (Eksport), poprawianie (Edytuj dane), usunięcie, cofnięcie zgody oraz skarga do Prezesa "
        "Urzędu Ochrony Danych Osobowych."
    )


def zasady_korzystania() -> str:
    return (
        "**Do czego służy:** do zapisywania treningów i podpowiedzi treningowych. Aplikacja **nie jest wyrobem medycznym** i nie zastępuje "
        "porady lekarza, fizjoterapeuty ani trenera. Wskaźniki (gotowość, regeneracja, podpowiedzi ciężaru) są wskazówkami, a nie oceną "
        "stanu zdrowia. Przy bólu, urazie lub chorobie skonsultuj się z lekarzem.\n\n"
        "**Twoja odpowiedzialność:** trenujesz na własne ryzyko; dobieraj ciężary do swoich możliwości i techniki.\n\n"
        "**Dla kogo:** aplikacja jest przeznaczona dla osób pełnoletnich.\n\n"
        "**Wersja testowa:** aplikacja jest rozwijana, więc mogą zdarzać się błędy i zmiany. Od czasu do czasu pobierz eksport danych.\n\n"
        "**Twoje dane:** w każdej chwili możesz je wyeksportować i usunąć (Profil → Dane i prywatność).\n\n"
        "**Uwagi:** przycisk „Zgłoś uwagę” w menu."
    )


# ---------------------------------------------------------------- strona Profil

HTML_HERO = r'''<!doctype html>
<html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
html, body { margin: 0; background: transparent; font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; -webkit-tap-highlight-color: transparent; }
body { padding: 6px 4px 14px 4px; color: var(--tekst); }
.hero { display: flex; align-items: center; gap: 16px; padding: 16px; border-radius: 18px; border: 1.5px solid var(--obram2);
        background: var(--mgla-lekka), var(--baza); box-shadow: var(--polysk), 0 8px 22px var(--cien); }
.av { position: relative; flex: 0 0 auto; width: 92px; height: 92px; padding: 0; border: 0; background: none; cursor: pointer; border-radius: 50%; transition: transform .12s ease; }
.av:active { transform: scale(0.96); }
.ring { width: 100%; height: 100%; border-radius: 50%; padding: 3px; background: var(--ramka); box-shadow: 0 0 20px color-mix(in srgb, var(--g2) 45%, transparent); }
.in { width: 100%; height: 100%; border-radius: 50%; display: flex; align-items: center; justify-content: center; overflow: hidden;
      font-weight: 800; font-size: 32px; color: var(--tekst); background: var(--mgla-lekka), var(--kafelek); background-size: cover; background-position: center; }
.in svg { width: 52%; height: 52%; }
.kam { position: absolute; right: -2px; bottom: -2px; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
       background: var(--ramka); color: var(--przycisk-tekst); border: 2px solid var(--kafelek); box-shadow: 0 4px 12px color-mix(in srgb, var(--g2) 45%, transparent); }
.kam svg { width: 17px; height: 17px; }
.txt { min-width: 0; flex: 1 1 auto; }
.imie { font-weight: 800; font-size: 1.35rem; line-height: 1.15; overflow-wrap: anywhere; }
.info { margin-top: 4px; font-weight: 600; color: var(--przyg); }
.usun { margin-top: 8px; padding: 0; border: 0; background: none; font: inherit; font-weight: 700; font-size: .85rem; color: var(--kasuj); cursor: pointer; }
.stan { margin-top: 8px; font-weight: 700; font-size: .85rem; color: var(--przyg); }
.blad { margin-top: 8px; font-weight: 700; font-size: .85rem; color: var(--kasuj); }
.kafle { display: flex; gap: 8px; margin-top: 12px; }
.kafel { flex: 1 1 0; min-width: 0; padding: 10px 12px; border-radius: 14px; border: 1.5px solid var(--obram2); background: var(--mgla-lekka), var(--baza); box-shadow: var(--polysk); }
.kafel .et { font-size: .68rem; letter-spacing: .12em; text-transform: uppercase; color: var(--przyg); white-space: nowrap; }
.kafel .w { font-weight: 800; font-size: 1.25rem; white-space: nowrap; }
.kafel .w small { font-size: .8rem; font-weight: 600; color: var(--przyg); }
.kafel.dobry .w { color: var(--zielony); }
@media (max-width: 340px) { .av { width: 76px; height: 76px; } .imie { font-size: 1.15rem; } }
</style></head>
<body>
<div class="hero">
  <button class="av" id="av" type="button" aria-label="Zmień zdjęcie profilowe">
    <div class="ring"><div class="in" id="in"></div></div>
    <span class="kam"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8h3l2-2.5h6L17 8h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"/><circle cx="12" cy="13" r="3.6"/></svg></span>
  </button>
  <div class="txt"><div class="imie" id="imie"></div><div class="info" id="info"></div><div id="dod"></div></div>
</div>
<div class="kafle" id="kafle"></div>
<input type="file" id="plik" accept="image/*,.heic,.heif" hidden>
<script>
(function () {
  var MAX_BAJTOW = 8 * 1024 * 1024, ROZMIAR = 256;
  var dane = {}, motyw = "dark", ostatnie = null;
  var sylwetka = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.2 3.6-7 8-7s8 2.8 8 7"/></svg>';
  function wyslij(typ, reszta) { window.parent.postMessage(Object.assign({isStreamlitMessage: true, type: typ}, reszta || {}), "*"); }
  function wartosc(v) { wyslij("streamlit:setComponentValue", {value: v, dataType: "json"}); }
  function wysokosc() { wyslij("streamlit:setFrameHeight", {height: Math.ceil(document.body.getBoundingClientRect().height) + 2}); }
  function id() { return (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now()) + Math.random(); }
  function esc(t) { var d = document.createElement("div"); d.textContent = t == null ? "" : String(t); return d.innerHTML; }
  function kolory(p) {
    var r = document.documentElement.style, k;
    for (k in p) { r.setProperty("--" + k.replace(/_/g, "-"), p[k]); }
    r.setProperty("--mgla-lekka", "linear-gradient(135deg, color-mix(in srgb, " + p.tytul_glow2 + " 14%, transparent) 0%, transparent 45%, color-mix(in srgb, " + p.tytul_glow3 + " 14%, transparent) 100%)");
    r.setProperty("--baza", "color-mix(in srgb, " + p.kafelek + " 84%, transparent)");
    r.setProperty("--ramka", "linear-gradient(100deg, " + p.g1 + ", " + p.g2 + " 55%, " + p.g3 + ")");
    r.setProperty("--polysk", "inset 0 1px 0 color-mix(in srgb, white 18%, transparent)");
    r.setProperty("--cien", p.cien_m);
    document.documentElement.style.colorScheme = motyw;
    // ciemny motyw: ramka komponentu bywa nieprzezroczysta (inny schemat kolorów niż strona), więc kolorujemy ją na tło strony
    document.documentElement.style.background = motyw === "dark" ? p.tlo : "transparent";
  }
  function rysuj() {
    var p = (dane.paleta || {})[motyw] || (dane.paleta || {}).dark;
    if (!p) { return; }
    kolory(p);
    var w = document.getElementById("in");
    if (dane.foto) { w.style.backgroundImage = "url(" + dane.foto + ")"; w.innerHTML = ""; }
    else { w.style.backgroundImage = ""; w.innerHTML = dane.inicjaly ? esc(dane.inicjaly) : sylwetka; }
    document.getElementById("imie").textContent = dane.imie || "Twój profil";
    document.getElementById("info").textContent = dane.info || "";
    var dod = document.getElementById("dod");
    dod.innerHTML = (dane.foto ? '<button class="usun" id="usun" type="button">Usuń zdjęcie</button>' : "");
    var u = document.getElementById("usun");
    if (u) { u.onclick = function () { wartosc({id: id(), akcja: "usun"}); }; }
    document.getElementById("kafle").innerHTML = (dane.kafle || []).map(function (k) {
      return '<div class="kafel' + (k.dobry ? " dobry" : "") + '"><div class="et">' + esc(k.et) + '</div><div class="w">' + esc(k.w) + (k.jed ? " <small>" + esc(k.jed) + "</small>" : "") + "</div></div>";
    }).join("");
    wysokosc();
  }
  function komunikat(tekst, klasa) {
    var d = document.getElementById("dod"), z = document.getElementById("usun");
    d.innerHTML = '<div class="' + klasa + '">' + esc(tekst) + "</div>"; wysokosc();
  }
  function wczytajObraz(plik) {
    // Safari (iPhone) odczytuje HEIC sam; gdy przeglądarka nie zna formatu, plik leci surowy do serwera
    return new Promise(function (ok, nie) {
      if (window.createImageBitmap) {
        createImageBitmap(plik, {imageOrientation: "from-image"}).then(ok, function () { ladujImg(); });
      } else { ladujImg(); }
      function ladujImg() {
        var url = URL.createObjectURL(plik), im = new Image();
        im.onload = function () { ok(im); };
        im.onerror = function () { URL.revokeObjectURL(url); nie(new Error("format")); };
        im.src = url;
      }
    });
  }
  function dataUrlNaBajty(du) { return du.slice(du.indexOf(",") + 1); }
  function pliknaBase64(plik) {
    return new Promise(function (ok, nie) {
      var r = new FileReader(); r.onload = function () { ok(dataUrlNaBajty(r.result)); }; r.onerror = function () { nie(r.error); }; r.readAsDataURL(plik);
    });
  }
  async function obsluz(plik) {
    if (!plik) { return; }
    komunikat("Zapisuję zdjęcie…", "stan");
    try {
      var obraz = null;
      try { obraz = await wczytajObraz(plik); } catch (e) { obraz = null; }
      if (obraz) {
        var szer = obraz.width || obraz.naturalWidth, wys = obraz.height || obraz.naturalHeight, bok = Math.min(szer, wys);
        var sx = (szer - bok) / 2, sy = Math.max(0, Math.min(wys - bok, (wys - bok) * 0.4));
        var c = document.createElement("canvas"); c.width = c.height = ROZMIAR;
        var g = c.getContext("2d"); g.fillStyle = "#141418"; g.fillRect(0, 0, ROZMIAR, ROZMIAR);
        g.drawImage(obraz, sx, sy, bok, bok, 0, 0, ROZMIAR, ROZMIAR);
        wartosc({id: id(), akcja: "zapisz", dane: dataUrlNaBajty(c.toDataURL("image/jpeg", 0.88))});
        return;
      }
      if (plik.size > MAX_BAJTOW) { komunikat("Zdjęcie jest za duże (limit 8 MB).", "blad"); return; }
      wartosc({id: id(), akcja: "zapisz", dane: await pliknaBase64(plik), surowe: true});
    } catch (e) { komunikat("Nie udało się wczytać zdjęcia.", "blad"); }
  }
  var wejscie = document.getElementById("plik");
  document.getElementById("av").addEventListener("click", function () { wejscie.value = ""; wejscie.click(); });
  wejscie.addEventListener("change", function () { obsluz(wejscie.files && wejscie.files[0]); });
  window.addEventListener("message", function (ev) {
    if (!ev.data || ev.data.type !== "streamlit:render") { return; }
    dane = ev.data.args || {};
    var t = ev.data.theme && ev.data.theme.base;
    motyw = (t === "light" || t === "dark") ? t : (window.matchMedia && matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    if (dane.motyw === "light" || dane.motyw === "dark") { motyw = dane.motyw; }
    rysuj();
  });
  window.addEventListener("resize", wysokosc);
  wyslij("streamlit:componentReady", {apiVersion: 1});
  wysokosc();
})();
</script>
</body></html>
'''

def _zapisz_dane() -> None:
    import streamlit as st
    s = st.session_state
    niepelnol = (wiek(s.get("pr_data_ur")) or 99) < WIEK_DOROSLOSCI
    cel = s.get("pr_cel")
    zapisz(imie=s.get("pr_imie"), data_ur=s.get("pr_data_ur"), wzrost=s.get("pr_wzrost"),
           waga_cel=None if niepelnol else s.get("pr_waga_cel"),
           cel=cel if cel in CELE and not (niepelnol and cel == CEL_REDUKCJA) else None)
    s["pr_edycja"] = False       # po zapisie formularz zwija się do przycisku „Edytuj dane”
    st.toast("Profil zapisany.")


def _zapisz_sprzet_z_pola() -> None:
    import streamlit as st
    zapisz_sprzet(list(st.session_state.get("pr_sprzet") or []))


def _typowy_sprzet() -> None:
    import streamlit as st
    dostepne = set(dostepny_sprzet())
    st.session_state["pr_sprzet"] = [s for s in SPRZET_TYPOWY if s in dostepne]
    _zapisz_sprzet_z_pola()


def _wyczysc_sprzet() -> None:
    import streamlit as st
    st.session_state["pr_sprzet"] = []
    _zapisz_sprzet_z_pola()


def _zapisz_ulubione_z_pola() -> None:
    import streamlit as st
    zapisz_ulubione(list(st.session_state.get("pr_ulubione") or []))


def _zmien_zgode(rodzaj: str, klucz: str) -> None:
    import streamlit as st
    zapisz_zgode(rodzaj, bool(st.session_state.get(klucz)))


def _naglowek_ze_zdjeciem(dane: dict, foto: bytes | None) -> None:
    """Nagłówek strony: avatar jest przyciskiem (dotknięcie = wybór zdjęcia z galerii albo aparatu, bez dodatkowych pól).
    Gdyby komponent się nie wczytał, zostaje zwykły nagłówek i rozwijane pole wgrywania."""
    import streamlit as st
    s = st.session_state
    try:
        motyw = st.context.theme.type
    except Exception:   # noqa: BLE001
        motyw = None
    try:
        odp = _komponent()(key="pr_hero", default=None, **hero_args(dane, ostatnia_waga(), foto, motyw))
    except Exception:   # noqa: BLE001 (nagłówek nie może zablokować strony)
        st.markdown(naglowek_profilu_html(dane, ostatnia_waga()), unsafe_allow_html=True)
        with st.expander("Zdjęcie profilowe" + (" (jest)" if foto else "")):
            plik = st.file_uploader("Wybierz zdjęcie", type=["jpg", "jpeg", "png", "webp", "heic", "heif"], key=f"pr_foto_{s.get('pr_foto_wersja', 0)}",
                                    label_visibility="collapsed")
            if plik is not None:
                ok, blad = zapisz_zdjecie(plik.getvalue())
                s["pr_foto_wersja"] = s.get("pr_foto_wersja", 0) + 1
                s["pr_foto_wynik"] = "" if ok else blad
                st.rerun()
            if foto:
                st.button("Usuń zdjęcie", key="profil_usun_zdjecie", on_click=usun_zdjecie, use_container_width=True)
        if s.get("pr_foto_wynik"):
            st.error(s.pop("pr_foto_wynik"))
        return
    wynik = obsluz_odpowiedz_komponentu(odp)
    if wynik is not None:
        if wynik:
            s["pr_foto_wynik"] = wynik
        st.rerun()
    if s.get("pr_foto_wynik"):
        st.error(s.pop("pr_foto_wynik"))


def _edytuj_dane() -> None:
    import streamlit as st
    st.session_state["pr_edycja"] = True


def _anuluj_edycje() -> None:
    import streamlit as st
    st.session_state["pr_edycja"] = False


def _sekcja_moje_dane(dane: dict, dorosly_jest: bool, wypelniony: bool) -> None:
    """Imię, data urodzenia, wzrost i cel wagi. Gdy profil jest już uzupełniony, widać tylko przycisk „Edytuj dane”."""
    import streamlit as st
    s = st.session_state
    st.markdown("<div class='pr-sekcja'>Moje dane</div>", unsafe_allow_html=True)
    with st.container(border=True):
        if wypelniony and not s.get("pr_edycja"):
            st.button("Edytuj dane", use_container_width=True, key="pr_edytuj", on_click=_edytuj_dane)
            return
        st.text_input("Imię", value=dane["imie"], max_chars=MAKS_IMIE, key="pr_imie", placeholder="Jak mamy się do Ciebie zwracać?")
        st.date_input("Data urodzenia", value=dane["data_ur"], min_value=date(1920, 1, 1), max_value=date.today(),
                      format="DD.MM.YYYY", key="pr_data_ur",
                      help="Potrzebna, żeby dopasować aplikację do wieku. Dla osób poniżej 18 lat nie ustawiamy celów wagowych, "
                           "a poniżej 16 lat potrzebna jest zgoda rodzica lub opiekuna (sekcja Dane i prywatność).")
        cele = [c for c in CELE if dorosly_jest or c != CEL_REDUKCJA]
        st.selectbox("Cel treningowy", cele, index=cele.index(dane["cel"]) if dane["cel"] in cele else None, key="pr_cel",
                     placeholder="Wybierz cel...", help="Pomaga dobrać propozycje treningów. Możesz go zmienić w każdej chwili.")
        k1, k2 = st.columns(2) if dorosly_jest else (st, None)
        k1.number_input("Wzrost (cm)", min_value=MIN_WZROST, max_value=MAKS_WZROST, value=dane["wzrost"], step=1, key="pr_wzrost")
        if k2 is not None:
            k2.number_input("Cel wagi (kg)", min_value=MIN_WAGA, max_value=MAKS_WAGA, value=dane["waga_cel"], step=0.5,
                            format="%.1f", key="pr_waga_cel",
                            help="Aktualna waga bierze się z ostatniego wpisu (formularz treningu, wpis dnia albo Garmin), więc nie wpisujesz jej drugi raz.")
        st.button("Zapisz profil", type="primary", use_container_width=True, key="pr_zapisz", on_click=_zapisz_dane)
        if wypelniony:
            st.button("Anuluj", use_container_width=True, key="pr_anuluj", on_click=_anuluj_edycje)


def widok_profilu() -> None:
    """Strona Profil: dane, siłownia, dane i prywatność."""
    import streamlit as st

    s = st.session_state
    if s.pop("pr_usunieto", None) is not None:
        st.success("Dane usunięte.")
    dane = wczytaj()
    foto = zdjecie()
    _naglowek_ze_zdjeciem(dane, foto)
    dorosly_jest = not niepelnoletni(dane)

    # Moje dane: u nowej osoby (bez imienia) formularz jest na górze; potem zwija się do przycisku „Edytuj dane” pod siłownią
    wypelniony = bool(dane["imie"])
    if not wypelniony:
        _sekcja_moje_dane(dane, dorosly_jest, wypelniony)

    # ------------------------------------------------------------ Siłownia
    st.markdown("<div class='pr-sekcja'>Moja siłownia</div>", unsafe_allow_html=True)
    with st.container(border=True):
        opcje = [x for x in dostepny_sprzet()]
        wybrany = [x for x in sprzet_wybrany() if x in opcje]
        if "pr_sprzet" not in s:
            s["pr_sprzet"] = wybrany
        else:
            s["pr_sprzet"] = [x for x in s["pr_sprzet"] if x in opcje]
        st.multiselect("Sprzęt, który masz", opcje, key="pr_sprzet", on_change=_zapisz_sprzet_z_pola,
                       placeholder="Wybierz rodzaje sprzętu...",
                       help="Z tego zaznaczenia korzystają listy ćwiczeń („Tylko mój sprzęt”) i zamiana na podobne. "
                            "Nic nie zaznaczone znaczy: pokazuj wszystko. Masa ciała jest zawsze dostępna.")
        a, b = st.columns(2)
        a.button("Typowa siłownia", use_container_width=True, key="pr_typowy", on_click=_typowy_sprzet,
                 help="Zaznacza sprzęt, który ma większość klubów sieciowych (sztangi, hantle, wyciągi, maszyny, kettlebell, guma, piłki). Potem możesz poprawić.")
        b.button("Wyczyść", use_container_width=True, key="pr_czysc_sprzet", on_click=_wyczysc_sprzet)
        lista = [c for c in _wszystkie_cwiczenia() if not c["ukryte"]]
        dozw = dozwolony_sprzet(list(s.get("pr_sprzet") or []))
        dostepnych = sum(1 for c in lista if dozw is None or c["sprzet"] in dozw)
        st.markdown(f"<div class='pr-kafle'><div class='pr-kafel'><div class='pr-kafel-et'>Ćwiczeń do wyboru</div>"
                    f"<div class='pr-kafel-w'>{dostepnych} <small>z {len(lista)}</small></div></div></div>", unsafe_allow_html=True)
        nazwy = {c["nazwa"]: c["sprzet"] for c in lista}
        ul = [n for n in ulubione() if n in nazwy]
        if "pr_ulubione" not in s:
            s["pr_ulubione"] = ul
        st.multiselect("Ulubione ćwiczenia i maszyny", list(nazwy), key="pr_ulubione", on_change=_zapisz_ulubione_z_pola,
                       format_func=lambda n: f"{n} · {nazwy[n]}" if nazwy.get(n) else n,
                       placeholder="Szukaj po nazwie...",
                       help="Ulubione są na górze listy przy wyborze ćwiczenia i oznaczone gwiazdką.")

    if wypelniony:
        _sekcja_moje_dane(dane, dorosly_jest, wypelniony)

    # ------------------------------------------------------------ Konto (tylko po zalogowaniu)
    if uzytkownik.zalogowany():
        st.markdown("<div class='pr-sekcja'>Konto</div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f"<div>Zalogowano jako <b>{_html_escape(uzytkownik.email())}</b></div>", unsafe_allow_html=True)
            st.button("Wyloguj", use_container_width=True, key="pr_wyloguj", on_click=uzytkownik.wyloguj)

    # ------------------------------------------------------------ Dane i prywatność
    st.markdown("<div class='pr-sekcja'>Dane i prywatność</div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("Twoje dane (treningi, waga, sen, notatki) leżą w bazie na komputerze, na którym działa aplikacja.",
                    help="Poza ten komputer trafia tylko: powiadomienia i zgłoszone uwagi do serwisu ntfy.sh (gdy skonfigurowano powiadomienia), "
                         "dane pobierane z Garmina (gdy jest włączony) oraz czcionka nagłówków z Google Fonts (Google widzi wtedy Twój adres IP).")
        st.checkbox("Zgadzam się na zapisywanie moich danych o zdrowiu i treningach w tej aplikacji", value=bool(dane["zgoda_zdrowie"]),
                    key="pr_zgoda_zdrowie", on_change=_zmien_zgode, args=("zgoda_zdrowie", "pr_zgoda_zdrowie"),
                    help="Waga, sen, tętno i samopoczucie to dane o zdrowiu. Zgodę zapisujemy z datą i możesz ją cofnąć w każdej chwili "
                         f"(odznaczając to pole){': ' + dane['zgoda_zdrowie'] if dane['zgoda_zdrowie'] else '.'}")
        if wymaga_zgody_opiekuna(dane):
            st.checkbox("Mam zgodę rodzica lub opiekuna na korzystanie z aplikacji", value=bool(dane["zgoda_opiekun"]),
                        key="pr_zgoda_opiekun", on_change=_zmien_zgode, args=("zgoda_opiekun", "pr_zgoda_opiekun"))
        ost = ostatnia_kopia()
        st.markdown("**Kopia zapasowa:** " + (f"ostatnia automatyczna {ost:%d.%m.%Y %H:%M}" if ost else "jeszcze nie ma automatycznej kopii"),
                    help="Aplikacja robi kopię bazy raz dziennie (folder kopie obok bazy) i zachowuje ostatnie 30.")
        c1, c2 = st.columns(2)
        if c1.button("Przygotuj eksport", use_container_width=True, key="pr_eksport",
                     help="Wszystkie Twoje dane jako pliki CSV w jednym ZIP-ie (do otwarcia w Excelu)."):
            s["pr_eksport_dane"] = eksport_zip()
            s["pr_eksport_nazwa"] = f"struo_eksport_{date.today():%Y%m%d}.zip"
        if c2.button("Przygotuj kopię", use_container_width=True, key="pr_kopia",
                     help="Pełna kopia bazy (plik .db). Przydaje się przy przenosinach na nowy komputer albo serwer."):
            s["pr_kopia_dane"] = kopia_bajty()
            s["pr_kopia_nazwa"] = f"struo_kopia_{date.today():%Y%m%d}.db"
        if s.get("pr_eksport_dane"):
            st.download_button(f"Pobierz eksport ({len(s['pr_eksport_dane']) // 1024 + 1} KB)", s["pr_eksport_dane"], file_name=s["pr_eksport_nazwa"],
                               mime="application/zip", use_container_width=True, key="pr_eksport_pobierz")
        if s.get("pr_kopia_dane"):
            st.download_button(f"Pobierz kopię ({len(s['pr_kopia_dane']) // 1024 + 1} KB)", s["pr_kopia_dane"], file_name=s["pr_kopia_nazwa"],
                               mime="application/octet-stream", use_container_width=True, key="pr_kopia_pobierz")
        with st.expander("Informacja o prywatności"):
            st.markdown(informacja_o_prywatnosci())
        with st.expander("Zasady korzystania"):
            st.markdown(zasady_korzystania())
        with st.expander("Usuwanie danych"):
            if st.button("Usuń historię treningów", use_container_width=True, key="profil_usun_historia",
                         help="Kasuje treningi, serie, wpisy dnia, dane z Garmina i samopoczucie. Profil, plan i presety zostają."):
                okno_usuniecia(wszystko=False)
            if st.button("Usuń wszystkie moje dane", use_container_width=True, key="profil_usun_wszystko",
                         help="Kasuje także profil, zdjęcie, plan, presety, własne ćwiczenia i notatki oraz wszystkie kopie zapasowe. Nie da się cofnąć."):
                okno_usuniecia(wszystko=True)


def _wszystkie_cwiczenia() -> list[dict]:
    import baza_cwiczen
    try:
        with closing(_polacz()) as db:
            return baza_cwiczen.wszystkie(db)
    except sqlite3.Error:
        return []


def okno_usuniecia(wszystko: bool) -> None:
    """Okno potwierdzenia usuwania (wpisz słowo USUŃ)."""
    import streamlit as st

    @st.dialog("Usunąć wszystkie dane?" if wszystko else "Usunąć historię treningów?")
    def _okno() -> None:
        if wszystko:
            st.markdown("Zniknie **wszystko**: historia, profil, zdjęcie, plan, presety, własne ćwiczenia, notatki i kopie zapasowe. "
                        "Zostanie baza ćwiczeń. **Tego nie da się cofnąć.**")
        else:
            st.markdown("Zniknie historia treningów, serie, wpisy dnia, dane z Garmina i samopoczucie. "
                        "Profil, plan i presety zostają. **Tego nie da się cofnąć.**")
        st.markdown("Wcześniej możesz pobrać eksport lub kopię (przyciski w sekcji Dane i prywatność).")
        potw = st.text_input("Wpisz USUŃ, żeby potwierdzić", key="pr_potw_" + ("w" if wszystko else "h"))
        if st.button("Usuń na stałe", key="profil_usun_potw" + ("_w" if wszystko else "_h"), use_container_width=True,
                     disabled=not potwierdzenie_poprawne(potw)):
            ile = usun_wszystko() if wszystko else usun_historie()
            st.cache_data.clear()
            if wszystko:
                for k in [k for k in st.session_state if not str(k).startswith("motyw")]:
                    del st.session_state[k]
            st.session_state["pr_usunieto"] = sum(v for v in ile.values())
            st.rerun()

    _okno()
