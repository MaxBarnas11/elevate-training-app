"""Małe własne komponenty interfejsu (HTML w ramce), których wygląd nie zależy od wersji Streamlita.

Dziś: wybór RPE 1-10 w jednym rzędzie (kolor od zielonego do czerwonego). Zwykłe przyciski Streamlita nie nadawały się do tego:
każde stuknięcie zmieniało klucz przycisku, więc przycisk powstawał od nowa (migotanie, znikające liczby), a kolory zależały od
wewnętrznych klas Streamlita. Komponent zaznacza wartość od razu po stuknięciu (bez czekania na serwer) i zawsze sam rysuje swoje kolory.
"""
from __future__ import annotations

from pathlib import Path

RPE_OPCJE = tuple(range(1, 11))
_KLUCZE_PALETY = ("tlo", "tekst", "przyg", "obram2", "kafelek") + tuple(f"rpe_{i}" for i in range(10)) + tuple(f"rpe_t_{i}" for i in range(10))

HTML_RPE = r'''<!doctype html>
<html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
* { box-sizing: border-box; }
html, body { margin: 0; background: transparent; font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; -webkit-tap-highlight-color: transparent; }
body { padding: 3px 1px 5px 1px; }
.rzad { display: flex; gap: 4px; }
.rzad button { flex: 1 1 0; min-width: 0; height: 40px; padding: 0; border-radius: 12px; border: 2px solid var(--k);
  background: transparent; color: var(--tekst); font: inherit; font-weight: 700; font-size: 15px; cursor: pointer;
  transition: background-color .14s ease, color .14s ease, transform .14s ease, box-shadow .14s ease; touch-action: manipulation; }
.rzad button:active { transform: scale(0.93); }
.rzad button.tak { background: var(--k); color: var(--t); box-shadow: 0 0 14px color-mix(in srgb, var(--k) 55%, transparent); transform: translateY(-1px); }
.rzad button:focus-visible { outline: 2px solid var(--tekst); outline-offset: 2px; }
</style></head>
<body><div class="rzad" id="rzad" role="group" aria-label="RPE od 1 do 10"></div>
<script>
(function () {
  var dane = {}, motyw = "dark", wybrane = null, przyciski = [];
  function wyslij(typ, reszta) { window.parent.postMessage(Object.assign({isStreamlitMessage: true, type: typ}, reszta || {}), "*"); }
  function wysokosc() { wyslij("streamlit:setFrameHeight", {height: Math.ceil(document.body.getBoundingClientRect().height) + 2}); }
  function id() { return (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now()) + Math.random(); }
  function zaznacz() {
    przyciski.forEach(function (b, i) {
      var tak = wybrane === i + 1;
      b.classList.toggle("tak", tak);
      b.setAttribute("aria-pressed", tak ? "true" : "false");
    });
  }
  function stuknij(n) {
    wybrane = (wybrane === n) ? null : n;        // ponowne stuknięcie zdejmuje zaznaczenie (RPE jest opcjonalne)
    zaznacz();
    wyslij("streamlit:setComponentValue", {value: {id: id(), wartosc: wybrane}, dataType: "json"});
  }
  function zbuduj(p) {
    var rzad = document.getElementById("rzad");
    rzad.innerHTML = "";
    przyciski = [];
    for (var i = 1; i <= 10; i++) {
      var b = document.createElement("button");
      b.type = "button"; b.textContent = String(i);
      b.style.setProperty("--k", p["rpe_" + (i - 1)]); b.style.setProperty("--t", p["rpe_t_" + (i - 1)]);
      (function (n) { b.addEventListener("click", function () { stuknij(n); }); })(i);
      rzad.appendChild(b); przyciski.push(b);
    }
  }
  function rysuj() {
    var p = (dane.paleta || {})[motyw] || (dane.paleta || {}).dark;
    if (!p) { return; }
    var r = document.documentElement.style;
    r.setProperty("--tekst", p.tekst);
    r.colorScheme = motyw;
    r.background = "transparent";
    zbuduj(p);
    zaznacz();
    wysokosc();
  }
  window.addEventListener("message", function (ev) {
    if (!ev.data || ev.data.type !== "streamlit:render") { return; }
    var nowe = ev.data.args || {};
    var t = ev.data.theme && ev.data.theme.base;
    var m = (t === "light" || t === "dark") ? t : (window.matchMedia && matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    if (nowe.motyw === "light" || nowe.motyw === "dark") { m = nowe.motyw; }
    var zmienionaPaleta = JSON.stringify(nowe.paleta) !== JSON.stringify(dane.paleta) || m !== motyw || !przyciski.length;
    dane = nowe; motyw = m;
    // Zaznaczenie trzyma sam komponent (argumenty się nie zmieniają, więc Streamlit nie tworzy ramki od nowa).
    // Po zapisie serii aplikacja zmienia klucz komponentu i dostajemy nowy, pusty rząd.
    if (zmienionaPaleta) { rysuj(); }
  });
  window.addEventListener("resize", wysokosc);
  wyslij("streamlit:componentReady", {apiVersion: 1});
  wysokosc();
})();
</script>
</body></html>
'''

_KOMPONENT = None


def paleta_rpe() -> dict:
    """Kolory dla obu motywów (tylko te, których komponent używa)."""
    from motywy import PALETA
    return {"light": {k: PALETA[k][0] for k in _KLUCZE_PALETY}, "dark": {k: PALETA[k][1] for k in _KLUCZE_PALETY}}


def _komponent_rpe():
    """Komponent RPE (plik index.html powstaje obok aplikacji przy pierwszym użyciu)."""
    global _KOMPONENT
    if _KOMPONENT is None:
        import streamlit.components.v1 as components
        folder = Path(__file__).parent / "komponenty" / "rpe_wybor"
        folder.mkdir(parents=True, exist_ok=True)
        plik = folder / "index.html"
        if not plik.exists() or plik.read_text(encoding="utf-8") != HTML_RPE:
            plik.write_text(HTML_RPE, encoding="utf-8")
        _KOMPONENT = components.declare_component("struo_rpe_wybor", path=str(folder))
    return _KOMPONENT


def wartosc_rpe(stan_sesji, klucz: str) -> int | None:
    """Aktualny wybór RPE w komponencie o danym kluczu (None: nic nie zaznaczono albo komponentu nie ma)."""
    odp = stan_sesji.get(klucz)
    w = odp.get("wartosc") if isinstance(odp, dict) else None
    return int(w) if isinstance(w, (int, float)) and int(w) in RPE_OPCJE else None


def pole_rpe(stan_sesji, klucz: str, motyw: str | None = None) -> int | None:
    """Rysuje rząd RPE i zwraca bieżący wybór. Argumenty komponentu są stałe (paleta i motyw), więc stuknięcie nie
    przebudowuje ramki. Żeby wyczyścić wybór (np. po zapisie serii), wywołaj z nowym kluczem."""
    _komponent_rpe()(key=klucz, default=None, paleta=paleta_rpe(), motyw=motyw if motyw in ("light", "dark") else "")
    return wartosc_rpe(stan_sesji, klucz)


# --- Zegar treningu liczony w telefonie -------------------------------------------------------------------------------
# Pasek sesji (sesja_treningowa.pasek_sesji_html) ma ukryte dane (.sz-dane) i miejsca na wartości (.sz-czas, .sz-przerwa,
# .sz-pasek). Ten skrypt działa w niewidocznej ramce i co 250 ms poprawia te wartości na stronie (ramka ma dostęp do strony,
# tak jak skrypt blokujący przybliżanie). Treść skryptu jest zawsze taka sama, więc Streamlit go nie przeładowuje, a nowy
# stan (po zapisie serii, +30 s, Pomiń) przychodzi razem z paskiem. Wcześniej serwer odświeżał pasek co sekundę, przez co
# stuknięcia czekały w kolejce, a strona się zacinała. Zmieniamy tylko tekst i styl istniejących elementów (nie dodajemy
# ani nie usuwamy węzłów), żeby nie wchodzić w drogę Reactowi, który rysuje stronę Streamlita.
HTML_ZEGAR = r'''<script>
(function () {
  var P, D;
  try { P = window.parent; D = P.document; } catch (e) { return; }
  var znak = String(Math.random());
  P.__struoZegar = znak;
  var przesuniecia = {};
  function fmt(s) {
    s = Math.max(0, Math.floor(s));
    var g = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
    var mm = (m < 10 ? "0" : "") + m, ss = (x < 10 ? "0" : "") + x;
    return g ? g + ":" + mm + ":" + ss : mm + ":" + ss;
  }
  function tekst(el, t) {
    if (!el) { return; }
    var n = el.firstChild;
    if (n && n.nodeType === 3 && n.nodeValue !== t) { n.nodeValue = t; }
  }
  function styl(el, nazwa, wartosc) {
    if (el && el.style.getPropertyValue(nazwa) !== wartosc) { el.style.setProperty(nazwa, wartosc); }
  }
  function jeden(w) {
    var zrodlo = w.querySelector(".sz-dane");
    if (!zrodlo) { return; }
    var surowe = zrodlo.textContent, d;
    try { d = JSON.parse(surowe); } catch (e) { return; }
    if (!(surowe in przesuniecia)) { przesuniecia = {}; przesuniecia[surowe] = d.teraz - Date.now(); }
    var teraz = Date.now() + przesuniecia[surowe];
    tekst(w.querySelector(".sz-czas"), fmt((teraz - d.start) / 1000));
    if (d.wyl || d.koniec === null || d.koniec === undefined) { return; }
    var zostalo = Math.max(0, Math.ceil((d.koniec - teraz) / 1000)), kolor, glowny, proc;
    if (zostalo > 0) {
      var dl = Math.max(d.dl || 0, zostalo);
      kolor = zostalo <= 10 ? d.kolory.czerwony : d.kolory.przerwa;
      glowny = fmt(zostalo); proc = 100 * zostalo / dl;
    } else {
      kolor = d.kolory.zielony; glowny = "Gotowe"; proc = 100;
    }
    styl(w, "--zk", kolor);
    tekst(w.querySelector(".sz-przerwa"), glowny);
    styl(w.querySelector(".sz-pasek"), "width", (Math.round(proc * 10) / 10) + "%");
  }
  var id = setInterval(function () {
    if (P.__struoZegar !== znak) { clearInterval(id); return; }   // nowsza kopia skryptu przejęła odliczanie
    try { D.querySelectorAll(".sz-zegar").forEach(jeden); } catch (e) { /* zegar nie może zepsuć strony */ }
  }, 250);
})();
</script>'''


def zegar_w_telefonie() -> None:
    """Niewidoczna ramka ze skryptem odliczającym (pasek sesji musi być na tej samej stronie)."""
    import streamlit.components.v1 as components
    components.html(HTML_ZEGAR, height=0)
