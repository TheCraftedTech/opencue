/*
 * OpenCue website – main.js
 * Language switch (English is the page's own text; German is translated here).
 * Choice: ?lang=de|en in the address, else the saved choice, else the browser language.
 * The saved choice lives in localStorage (this browser only, never sent anywhere; no cookies).
 *
 * Download: the buttons first point at the releases page. Then the newest release is read from the
 * GitHub API (the repository is hosted there anyway) and the buttons switch to the direct link of the
 * installer, with its version. The answer is cached for an hour (localStorage) so repeat visits and
 * the rate limit of the API are no problem; if GitHub cannot be reached the buttons keep working
 * as links to the releases page.
 */
(function () {
  "use strict";

  var RELEASE_API = "https://api.github.com/repos/TheCraftedTech/opencue/releases/latest";
  var DOWNLOAD_PREFIX = "https://github.com/TheCraftedTech/opencue/releases/download/";
  var CACHE_KEY = "opencue-latest-release";
  var CACHE_MS = 60 * 60 * 1000;

  // English texts that are not in the HTML itself (set from script)
  var EN_EXTRA = { "theme.toDark": "Switch to dark theme" };

  var DE = {
    "skip": "Zum Inhalt springen",
    "nav.label": "Hauptnavigation",
    "nav.features": "Funktionen",
    "nav.workflow": "So funktioniert's",
    "nav.download": "Download",
    "lang.label": "Sprache",
    "theme.toLight": "Zum hellen Design wechseln",
    "theme.toDark": "Zum dunklen Design wechseln",

    "meta.title": "OpenCue – Open-Source-DMX-Lichtpult für Windows",
    "meta.desc": "OpenCue ist ein kostenloses Open-Source-Lichtsteuerpult für DMX unter Windows: Scheinwerfer patchen, Cues und Effekte programmieren, die Bühne in 3D ansehen und die Show per Tablet steuern. Läuft komplett offline.",

    "hero.eyebrow": "Open-Source-DMX-Lichtpult für Windows",
    "hero.title": "Licht programmieren. In 3D sehen.",
    "hero.lead": "OpenCue macht aus einem Windows-PC ein komplettes Lichtpult: Scheinwerfer patchen, Cues und Effekte programmieren, die Bühne in 3D ansehen und die Show per Tablet steuern. Kostenlos, offline, ohne Konto.",
    "hero.download": "Für Windows herunterladen",
    "hero.source": "Quellcode auf GitHub",
    "hero.fine": "Windows 10/11 · 64 Bit · kostenlos · GPL-3.0-or-later",
    "hero.logoAlt": "Das OpenCue-Logo: ein Pixel-Art-Scheinwerfer mit gelbem Lichtkegel über dem Schriftzug OpenCue",
    "hero.cmdLabel": "Beispiele für Eingaben in der OpenCue-Befehlszeile",
    "hero.cmdTitle": "Befehlszeile in OpenCue",

    "why.title": "Warum OpenCue",
    "why.offline.t": "Komplett offline",
    "why.offline.d": "Kein Konto, kein Lizenzschlüssel, keine Cloud, kein Tracking. Funktioniert auch im Veranstaltungsraum ohne Internet.",
    "why.open.t": "Kostenlos und Open Source",
    "why.open.d": "GNU GPL v3 oder neuer. Code lesen, selbst bauen, verbessern, weitergeben.",
    "why.one.t": "Eine Oberfläche für Pult und Tablet",
    "why.one.d": "Tablet oder Handy zeigen dieselbe Oberfläche mit denselben Rechten – als Web-App installierbar.",
    "why.files.t": "Lesbare Dateien",
    "why.files.d": "Shows, Layouts und Farbprofile sind einfache JSON-Dateien – leicht zu sichern, zu kopieren und zu teilen.",

    "features.title": "Alles, was eine kleine bis mittlere Show braucht",
    "features.lead": "Für Bands, Theater, Schulen, Clubs und Heimstudios.",
    "f.fix.t": "Scheinwerfer und Programmer",
    "f.fix.d": "GDTF-Scheinwerferbibliothek mit Patchen, Gruppen, Presets und Variablen. Jeder Kanal bekommt sein eigenes Bedienelement: Dimmer, Farbe, Position, Beam, Fokus, Gobo, Prisma und Shutter.",
    "f.cue.t": "Cues und Executor",
    "f.cue.d": "Cue-Listen mit Überblendungen, Verzögerungen und Go-, Follow- oder Timecode-Triggern. Mehrere Listen gleichzeitig, jede mit eigenem Mix-Fader.",
    "f.fx.t": "Effekte und Skripte",
    "f.fx.d": "Eine Effekt-Engine in Echtzeit mit 60 fertigen Effekten und ein Effekt-Studio, in dem du eigene Effekte in einer kleinen C++/Arduino-ähnlichen Skriptsprache schreibst.",
    "f.cmd.t": "Befehlszeile",
    "f.cmd.d": "Befehle tippen, zum Beispiel Fixture 1 Thru 5 At Full: Tab-Autovervollständigung, Eingabeprüfung sowie Ziffernblock- und Befehlsknopf-Panels für Touchscreens.",
    "f.sim.t": "3D-Simulation",
    "f.sim.d": "Bühne bauen, Scheinwerfer mit ihren echten GDTF-Modellen aufhängen und Lichtkegel, Lichtpool, Gobos, Strobe und Fokus passend zum DMX-Signal sehen. Moving Heads per Klick auf einen Bühnenpunkt ausrichten.",
    "f.dmx.t": "DMX-Ausgabe",
    "f.dmx.d": "Art-Net, sACN (E1.31) und USB-DMX (Enttec DMX USB Pro und kompatible), beliebig viele Universen, mit Blackout, Grand Master und DMX-Monitor.",
    "f.tc.t": "Timecode und Medien",
    "f.tc.d": "Globaler Timecode, der Cues starten kann, ein Video-/Audio-Player-Panel, das ihm folgt, und ein Kamera- und Livestream-Panel.",
    "f.rem.t": "Fernsteuerung",
    "f.rem.d": "Bedienung per Tablet oder Handy im lokalen Netz, mit Passwort und QR-Code. Standardmäßig aus und jederzeit umschaltbar.",
    "f.ui.t": "Dein Layout",
    "f.ui.d": "Frei gestaltbare Panel-Layouts mit Bearbeitungsmodus, Farbprofile, Touch-Unterstützung und GUI-Skalierung. Englisch und Deutsch. Ganze Shows als ZIP exportieren und importieren.",

    "flow.title": "Von der Installation zum ersten Cue",
    "flow.1.t": "Installieren",
    "flow.1.d": "Installer starten. OpenCue öffnet sich mit einer kleinen Demo-Show.",
    "flow.2.t": "Hinzufügen und patchen",
    "flow.2.d": "Scheinwerfer aus der GDTF-Bibliothek importieren und mit Universum und Adresse versehen.",
    "flow.3.t": "Auswählen und einstellen",
    "flow.3.d": "Scheinwerfer per Kachel, Lasso, Gruppe oder Befehlszeile wählen und Helligkeit, Farbe, Position und Beam einstellen.",
    "flow.4.t": "Speichern und Go",
    "flow.4.d": "Looks als Cues speichern, Effekte zuweisen und im Executor abfahren.",
    "flow.5.t": "Ausgeben oder simulieren",
    "flow.5.d": "Art-Net, sACN oder USB-DMX senden – oder alles in der 3D-Simulation ansehen, ganz ohne Hardware.",

    "dl.title": "OpenCue herunterladen",
    "dl.lead": "Im Windows-Installer wählst du Sprache, Programmordner und Datenordner. Neuere Versionen aktualisieren über denselben Installer, und OpenCue meldet, wenn eine neue Version erscheint.",
    "dl.button": "Installer herunterladen",
    "dl.all": "Alle Versionen",
    "dl.changelog": "Änderungsprotokoll",
    "dl.file": "Installer-Datei:",
    "dl.newer": "Neuere Versionen stehen auf der Releases-Seite bei GitHub.",
    "req.title": "Voraussetzungen",
    "req.1": "Windows 10 oder 11, 64 Bit",
    "req.2": "Microsoft Edge WebView2 Runtime – in Windows 11 enthalten; der Installer lädt sie bei Bedarf nach (einmalig Internet nötig)",
    "req.3": "Für echte Scheinwerfer: ein Art-Net- oder sACN-Netzwerkknoten oder ein USB-DMX-Interface",
    "lim.title": "Gut zu wissen",
    "lim.1": "Nur Windows – kein Installer für macOS oder Linux.",
    "lim.2": "Version 1.0 und ein Ein-Personen-Projekt: Teste deine Show, bevor du dich live darauf verlässt.",
    "lim.3": "Scheinwerferdateien liegen nicht bei. Du importierst GDTF-Dateien oder lädst sie von GDTF Share (dafür ist dort ein kostenloses Konto nötig).",
    "src.title": "Aus dem Quellcode starten",
    "src.d": "Du brauchst Python 3.13 (64 Bit) und für den ersten Start Internet. run.bat richtet alles ein.",

    "foot.copy": "© 2026 Samuel Zenker. Lizenziert unter der GNU General Public License v3.0 oder neuer.",
    "foot.privacy": "Diese Website verwendet keine Cookies, keine Analyse-Dienste und keine Fremd-Schriften oder -Skripte. Sie fragt nur bei GitHub die neueste Installer-Version ab.",
    "foot.source": "Quellcode",
    "foot.releases": "Releases",
    "foot.changelog": "Änderungsprotokoll",
    "foot.license": "Lizenz"
  };

  var ATTRS = ["aria-label", "alt", "title"];
  var EN = {};          // English texts, read once from the page itself
  var current = "en";

  function store(key, value) {
    try {
      if (value === undefined) { return window.localStorage.getItem(key); }
      window.localStorage.setItem(key, value);
    } catch (e) { /* storage blocked: the page still works */ }
    return null;
  }

  function collectEnglish() {
    Object.keys(EN_EXTRA).forEach(function (key) { EN[key] = EN_EXTRA[key]; });
    EN["meta.title"] = document.title;
    var meta = document.querySelector('meta[name="description"]');
    EN["meta.desc"] = meta ? meta.getAttribute("content") : "";

    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      EN[el.getAttribute("data-i18n")] = el.textContent;
    });
    ATTRS.forEach(function (attr) {
      document.querySelectorAll("[data-i18n-" + attr + "]").forEach(function (el) {
        EN[el.getAttribute("data-i18n-" + attr)] = el.getAttribute(attr);
      });
    });
  }

  function t(key) {
    var table = current === "de" ? DE : EN;
    return table[key] !== undefined ? table[key] : EN[key];
  }

  function applyAttributes() {
    ATTRS.forEach(function (attr) {
      document.querySelectorAll("[data-i18n-" + attr + "]").forEach(function (el) {
        el.setAttribute(attr, t(el.getAttribute("data-i18n-" + attr)));
      });
    });
  }

  function apply(lang) {
    current = lang === "de" ? "de" : "en";
    document.documentElement.lang = current;
    document.title = t("meta.title");
    var meta = document.querySelector('meta[name="description"]');
    if (meta) { meta.setAttribute("content", t("meta.desc")); }

    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      el.textContent = t(el.getAttribute("data-i18n"));
    });
    applyAttributes();
    document.querySelectorAll(".lang button").forEach(function (btn) {
      btn.setAttribute("aria-pressed", btn.getAttribute("data-lang") === current ? "true" : "false");
    });
  }

  function initialLanguage() {
    var fromUrl = /[?&]lang=(de|en)\b/.exec(window.location.search);
    if (fromUrl) { return fromUrl[1]; }
    var saved = store("opencue-lang");
    if (saved === "de" || saved === "en") { return saved; }
    var langs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || "en"];
    return /^de\b/i.test(langs[0]) ? "de" : "en";
  }

  // ---- newest installer --------------------------------------------------------------------

  function showRelease(rel) {
    document.querySelectorAll("[data-download]").forEach(function (a) { a.setAttribute("href", rel.url); });
    document.querySelectorAll("[data-version]").forEach(function (el) { el.textContent = "v" + rel.version; });
    document.querySelectorAll("[data-filename]").forEach(function (el) { el.textContent = rel.file; });
  }

  // GitHub release JSON -> { version, url, file } or null (only accepts this repository's installer)
  function parseRelease(json) {
    var assets = json && json.assets ? json.assets : [];
    for (var i = 0; i < assets.length; i++) {
      var a = assets[i];
      if (/^OpenCue-Setup.*\.exe$/i.test(a.name || "") && String(a.browser_download_url || "").indexOf(DOWNLOAD_PREFIX) === 0) {
        return { version: String(json.tag_name || "").replace(/^v/i, ""), url: a.browser_download_url, file: a.name };
      }
    }
    return null;
  }

  function readCache() {
    try {
      var cached = JSON.parse(store(CACHE_KEY) || "null");
      if (cached && cached.rel && cached.rel.url && cached.rel.url.indexOf(DOWNLOAD_PREFIX) === 0) { return cached; }
    } catch (e) { /* damaged cache: ignore */ }
    return null;
  }

  function setupDownload() {
    var cached = readCache();
    if (cached) { showRelease(cached.rel); }
    if (cached && Date.now() - cached.time < CACHE_MS) { return; }
    if (!window.fetch) { return; }
    window.fetch(RELEASE_API, { headers: { "Accept": "application/vnd.github+json" } })
      .then(function (response) { return response.ok ? response.json() : Promise.reject(new Error("HTTP " + response.status)); })
      .then(function (json) {
        var rel = parseRelease(json);
        if (!rel) { return; }
        showRelease(rel);
        store(CACHE_KEY, JSON.stringify({ time: Date.now(), rel: rel }));
      })
      .catch(function () { /* offline or rate limited: the buttons stay links to the releases page */ });
  }

  function init() {
    collectEnglish();
    setupDownload();
    document.addEventListener("opencue:relabel", applyAttributes);
    document.querySelectorAll(".lang button").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var lang = btn.getAttribute("data-lang");
        apply(lang);
        store("opencue-lang", lang);
      });
    });
    var lang = initialLanguage();
    if (lang !== "en") { apply(lang); }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
