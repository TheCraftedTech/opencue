/**
 * app.js
 * WebSocket handler, module manager & i18n system of OpenCue.
 *
 * The client is entirely state-driven: the only source of show data is the
 * server (via WebSocket JSON). Purely local UI state (which dialog is open,
 * which language is selected, ...) is managed here in the client and never
 * synced back to the server. There is no server-side HTML rendering and no
 * page reload - every update happens through targeted DOM changes.
 */

const RECONNECT_DELAY_MS = 2000;       // Obergrenze des Reconnect-Backoffs
const RECONNECT_MIN_DELAY_MS = 400;
const HEARTBEAT_INTERVAL_MS = 10000;   // Client-Ping, haelt Safari/iPad-Verbindungen offen
const LIVE_MIN_DELAY_MS = 16;           // Live-Daten (DMX, Effekte, Fades) werden hoechstens so oft verarbeitet ...
const LIVE_MAX_DELAY_MS = 1000;         // ... auf langsamen Geraeten seltener (siehe _coalesceLive)
const STALE_CONNECTION_MS = 35000;     // keine Nachricht (auch kein Ping/Pong) -> Socket tot
const DEFAULT_LANGUAGE = "en";
const LANGUAGE_STORAGE_KEY = "opencue.language";
const APP_VERSION = "v0.1";

// ---- Unsaved-Changes-Guard --------------------------------------------------
// _isDirty wird vom Server (state_snapshot / fixtures_changed / show_saved)
// autoritaer gesetzt. _pendingNavAction haelt die Funktion, die nach Bestaetigung
// des "Unsaved Changes"-Modals ausgefuehrt werden soll.
let _isDirty = false;
let _pendingNavAction = null;
// Beenden-Dialog "mit Speichern" bei noch unbenannter Show: nach dem Speichern
// unter neuem Namen (show_saved) wird das Beenden bestaetigt.
let _pendingCloseAfterSave = false;

// ---- Layout Preset System --------------------------------------------------
// Versionsnummer dieses Standes (aus der Adresse dieses Skripts, ?v=...): haengt an den nachgeladenen Sprachdateien, damit auch sie
// nach einem Update nie aus einem alten Browser-/WebView2-Cache kommen.
const ASSET_VERSION = (() => {
  try { return new URL(document.currentScript.src).searchParams.get("v") || ""; } catch (error) { return ""; }
})();
const _assetQuery = ASSET_VERSION ? "?v=" + encodeURIComponent(ASSET_VERSION) : "";

let _activeLayoutName = null;     // Anzeigename des aktuellen Layouts
let _activeLayoutFilename = null; // Dateiname (z.B. "My Layout.json") für API-Aufrufe
let _layoutPendingDeleteFilename = null;
let _layoutPendingDeleteName = null;
// Herkunfts-Tracking: wo die aktive Layout-/Showfile-Datei gespeichert ist.
// Wird beim Laden, Erstellen und Speichern gesetzt; steuert direktes "Speichern".
let _activeLayoutOrigin = { target: "local", drive: "", filename: "", filepath: "" };
let _cachedLayouts = [];          // Geordnete Layout-Liste für Ctrl+1–9 Shortcuts

function _setDirty(dirty) {
  const changed = _isDirty !== dirty;
  _isDirty = dirty;
  // Titelzeile sofort aktualisieren
  if (typeof client !== "undefined" && client.state) {
    updateWindowTitle(client.state.showfile_name, dirty);
  }
  if (changed) _notifyFileManager("shows");
}

/** Prueft, ob ungespeicherte Aenderungen vorliegen. Wenn ja, oeffnet das
 *  Unsaved-Changes-Modal und merkt sich die auszufuehrende Aktion.
 *  Wenn nein, fuehrt die Aktion sofort aus. */
function _guardUnsavedChanges(action) {
  if (!_isDirty) {
    action();
    return;
  }
  _pendingNavAction = action;
  Modal.open("unsaved-changes");
}

// ---- Panel plugin registry --------------------------------------------------
// Panel types register synchronously via inline IIFEs at the bottom of this
// file. The host exposes helpers via window.__panelAPI (populated just before
// the IIFEs run).

window.__panelPlugins = (() => {
  const _reg = {};
  return {
    register(plugin) {
      if (!plugin?.type) { console.warn("[OpenCue] Panel plugin missing type:", plugin); return; }
      _reg[plugin.type] = plugin;
    },
    get(panelType) { return _reg[panelType] || null; },
    has(panelType) { return panelType in _reg; },
  };
})();


// ---- i18n --------------------------------------------------------------

class Translator {
  constructor() {
    this.translations = {};
    this.fallback = null;      // Englisch: Rueckfall fuer Schluessel, die in der Sprache fehlen
    this.ready = null;
    this.language = this._loadStoredLanguage();
  }

  _loadStoredLanguage() {
    try {
      return localStorage.getItem(LANGUAGE_STORAGE_KEY) || DEFAULT_LANGUAGE;
    } catch (error) {
      return DEFAULT_LANGUAGE; // localStorage unavailable (e.g. private mode)
    }
  }

  /** Laedt die Sprachdateien genau einmal. Panels und Dialoge werden erst danach aufgebaut
   *  (siehe OpenCueClient: die WebSocket-Verbindung startet nach diesem Promise). */
  init() {
    if (!this.ready) {
      this.ready = (async () => {
        try {
          await this._loadLanguage(this.language);
        } catch (error) {
          console.error(error);   // weiter mit Schluesseln statt gar keiner Oberflaeche
        }
        this.apply();
        document.documentElement.classList.remove("i18n-loading");
      })();
    }
    return this.ready;
  }

  async setLanguage(language) {
    if (language === this.language) return;
    await this._loadLanguage(language);
    this.language = language;
    try {
      localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    } catch (error) {
      /* language choice just won't persist across sessions */
    }
    this.apply();
  }

  async _loadLanguage(language) {
    const response = await fetch(`/static/locales/${language}.json${_assetQuery}`);
    if (!response.ok) {
      throw new Error(`Failed to load locale "${language}": ${response.status}`);
    }
    this.translations = await response.json();
    if (language === "en") {
      this.fallback = this.translations;
    } else if (!this.fallback) {
      try {
        const en = await fetch("/static/locales/en.json" + _assetQuery);
        if (en.ok) this.fallback = await en.json();
      } catch (error) { /* ohne Rueckfall weiter */ }
    }
  }

  t(key) {
    const direct = this.translations[key] || (this.fallback && this.fallback[key]);
    if (direct) return direct;
    // Schluessel in anderer Schreibweise (z.B. wakeLock_unsupported statt WAKELOCK_UNSUPPORTED)
    const lower = String(key).toLowerCase();
    if (!this._lowerIndex || this._lowerSource !== this.translations) {
      this._lowerSource = this.translations;
      this._lowerIndex = {};
      for (const dict of [this.fallback || {}, this.translations]) {
        for (const name of Object.keys(dict)) this._lowerIndex[name.toLowerCase()] = dict[name];
      }
    }
    return this._lowerIndex[lower] || key;
  }

  /** Re-translates every element carrying a data-i18n / data-i18n-placeholder /
   * data-lang attribute. Called both after the initial locale fetch (page
   * load) AND after every language switch - this is what makes a
   * data-i18n-placeholder-marked <input> immune to the race where a panel's
   * buildContent() runs (via the state_snapshot WS message, which can arrive
   * before translator.init()'s own fetch resolves) and sets its placeholder
   * from an as-yet-empty translations table: whatever raw key it briefly
   * showed gets corrected here the moment the locale actually loads. */
  apply() {
    document.documentElement.lang = this.language;

    document.querySelectorAll("[data-i18n]").forEach((element) => {
      element.textContent = this.t(element.dataset.i18n);
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
      element.placeholder = this.t(element.dataset.i18nPlaceholder);
    });

    // Zugaenglichkeits-Beschriftung (Screenreader) und Tooltip statischer Elemente
    document.querySelectorAll("[data-i18n-aria]").forEach((element) => {
      element.setAttribute("aria-label", this.t(element.dataset.i18nAria));
    });
    document.querySelectorAll("[data-i18n-tip]").forEach((element) => {
      element.title = this.t(element.dataset.i18nTip);
    });
    // Texte, die der Theme-Editor aus Code erzeugt, folgen dem Sprachwechsel
    if (typeof ThemeUI !== "undefined") ThemeUI.relabel();
    if (typeof _renderLayoutChip === "function") _renderLayoutChip();
    if (window.FixtureLibrary) window.FixtureLibrary.relabel();
    // Dynamisch aufgebaute Panels (Livestream, Player, Timecode ...) beschriften sich bei jedem Laden/Wechseln der Sprache neu: egal, in welcher
    // Reihenfolge Sprachdatei und Panel-Aufbau eintreffen, nie bleibt ein Roh-Schluessel stehen.
    document.dispatchEvent(new CustomEvent("i18n-applied"));

    document.querySelectorAll("[data-lang]").forEach((element) => {
      element.classList.toggle("menu__item--active", element.dataset.lang === this.language);
    });
  }
}

const translator = new Translator();

/** Small helper to translate a single key using the currently loaded language. */
// Meldet einen globalen Listener ab, sobald sein Panel aus dem DOM entfernt wurde.
// Erst nach der ersten Verbindung aktiv, damit der Erstaufbau unberuehrt bleibt.
function _panelGone(panelEl, eventName, handler) {
  if (panelEl.isConnected) {
    panelEl._wasConnected = true;
    return false;
  }
  if (!panelEl._wasConnected) return false;
  document.removeEventListener(eventName, handler);
  return true;
}

/** Lesbarer Name eines Geraetetyps aus seiner Kennung: die eingebauten Geraete ("__generic_dimmer") und GDTF-Dateien ("Hersteller@Name@Revision" -> "Hersteller Name"). */
const _BUILTIN_TYPE_NAMES = { "__generic_dimmer": "Generic Dimmer", "__generic_rgbw_par": "Generic RGBW LED Par", "__generic_moving_head": "Generic Moving Head Spot 16ch" };
function _fixtureTypeLabel(id) {
  const key = String(id || "");
  if (_BUILTIN_TYPE_NAMES[key]) return _BUILTIN_TYPE_NAMES[key];
  const parts = key.split("@");
  if (parts.length >= 2) return (parts[0] + " " + parts[1]).replace(/_/g, " ").replace(/\s+/g, " ").trim();
  return key;
}

function i18n(key) {
  return translator.t(key);
}

/** Baut denselben Toggle-Switch (.toggle-switch/.toggle-switch__track) wie
 * die globalen Panel-Properties (Erscheinungsbild/Farben) und die App-
 * Settings - fuer 100% einheitliches Design auch in modulspezifischen
 * Moduleinstellungen. Gibt { label, input } zurueck; `input` ist ein
 * normales <input type="checkbox">, .checked/change-Events funktionieren
 * wie gewohnt. */
function makeToggleSwitch(id, checked) {
  const label = document.createElement("label");
  label.className = "toggle-switch";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.id = id;
  input.checked = !!checked;
  const track = document.createElement("span");
  track.className = "toggle-switch__track";
  label.appendChild(input);
  label.appendChild(track);
  return { label, input };
}

// ---- Browser-Autovervollstaendigung in ALLEN Eingabefeldern aus --------------------------------------------------
// Jedes Text-/Zahlen-/Passwort-Feld und jede Textarea (auch spaeter dynamisch eingefuegte) bekommt autocomplete="off"
// (Passwortfelder "new-password": Chrome ignoriert "off" bei Passwoertern und bietet sonst gespeicherte an),
// autocorrect/autocapitalize "off", spellcheck "false" und - wenn keiner da ist - einen eindeutigen, nicht erkennbaren
// name (Browser fuehren ihren Eingabeverlauf je name/id; ohne erkennbaren Namen gibt es keine Vorschlaege). Kein <datalist>.
(function installNoAutofill() {
  const SKIP_TYPES = new Set(["checkbox", "radio", "range", "button", "submit", "reset", "file", "color", "hidden", "image"]);
  let seq = 0;
  function harden(el) {
    if (el.dataset.noAutofill) return;
    el.dataset.noAutofill = "1";
    const type = (el.getAttribute("type") || "text").toLowerCase();
    if (el.tagName === "INPUT" && SKIP_TYPES.has(type)) return;
    el.setAttribute("autocomplete", type === "password" ? "new-password" : "off");
    el.setAttribute("autocorrect", "off");
    el.setAttribute("autocapitalize", "off");
    el.setAttribute("spellcheck", "false");
    if (!el.getAttribute("name")) el.setAttribute("name", "oc-" + (++seq) + "-" + Math.random().toString(36).slice(2, 8));
  }
  function scan(root) {
    if (root.nodeType !== 1) return;
    if (root.matches("input, textarea")) harden(root);
    root.querySelectorAll("input, textarea").forEach(harden);
    if (root.tagName === "FORM") root.setAttribute("autocomplete", "off");
    root.querySelectorAll("form").forEach((form) => form.setAttribute("autocomplete", "off"));
  }
  const start = () => {
    scan(document.documentElement);
    new MutationObserver((mutations) => mutations.forEach((m) => m.addedNodes.forEach(scan)))
      .observe(document.documentElement, { childList: true, subtree: true });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();

// ---- WebSocket client & module manager ----------------------------------

// ---- Theme-Engine ---------------------------------------------------------------------------
// Ein Theme ist ein flaches Objekt { base: "dark"|"light", tokens: { tokenName: "#rrggbb" }, radius }.
// tokens enthaelt nur Abweichungen von der Basis-Palette (theme.css). Jeder Eintrag wird als
// CSS-Variable auf :root gesetzt; --accent-ink wird aus der Helligkeit des wirksamen Akzents berechnet.
const THEME_TOKENS = ["bg", "toolbar-bg", "menu-bg", "panel-bg", "panel-border", "panel-header-bg",
  "surface-1", "surface-2", "surface-3", "border", "border-strong", "text-1", "text-2", "text-3",
  "accent", "ok", "warn", "error", "live"];
const THEME_DEFAULT_RADIUS = 0;   // Standard: eckig (siehe state_manager.DEFAULT_RADIUS)
const THEME_MAX_RADIUS = 16;
const THEME_CACHE_KEY = "opencue.theme";

const ACCENT_PRESETS = [
  { key: "amber",   nameKey: "THEME_PRESET_AMBER",   accent: "#ffb000" },
  { key: "ice",     nameKey: "THEME_PRESET_ICE",     accent: "#4fc3f7" },
  { key: "signal",  nameKey: "THEME_PRESET_SIGNAL",  accent: "#ff5a3c" },
  { key: "lime",    nameKey: "THEME_PRESET_LIME",    accent: "#9adb3c" },
  { key: "magenta", nameKey: "THEME_PRESET_MAGENTA", accent: "#e23cff" },
];

function accentInk(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex).trim());
  if (!m) return "#1a1200";
  const channel = (i) => {
    const v = parseInt(m[1].slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  };
  const luminance = 0.2126 * channel(0) + 0.7152 * channel(2) + 0.0722 * channel(4);
  return luminance > 0.35 ? "#14110a" : "#ffffff";
}

function normalizeTheme(raw) {
  const theme = { base: "dark", tokens: {}, radius: THEME_DEFAULT_RADIUS };
  if (!raw || typeof raw !== "object") return theme;
  theme.base = raw.base === "light" ? "light" : "dark";
  if (raw.tokens && typeof raw.tokens === "object") {
    for (const name of THEME_TOKENS) {
      const value = raw.tokens[name];
      if (typeof value === "string" && /^#[0-9a-f]{6}$/i.test(value)) theme.tokens[name] = value.toLowerCase();
    }
  }
  const radius = Math.round(Number(raw.radius));
  if (Number.isFinite(radius)) theme.radius = Math.max(0, Math.min(THEME_MAX_RADIUS, radius));
  return theme;
}

/** Wendet ein Theme auf :root an (Basis, Token-Abweichungen, Rundungsgrad, Akzent-Schrift). */
function applyTheme(rawTheme) {
  const theme = normalizeTheme(rawTheme);
  const root = document.documentElement;
  THEME_TOKENS.forEach((name) => root.style.removeProperty("--" + name));
  root.dataset.theme = theme.base;
  for (const [name, value] of Object.entries(theme.tokens)) root.style.setProperty("--" + name, value);
  // Rundungsgrad: ein Regler skaliert alle drei Stufen proportional (4 : 7 : 12)
  root.style.setProperty("--radius-md", theme.radius + "px");
  root.style.setProperty("--radius-sm", Math.round(theme.radius * 4 / 7) + "px");
  root.style.setProperty("--radius-lg", Math.round(theme.radius * 12 / 7) + "px");
  const accent = getComputedStyle(root).getPropertyValue("--accent").trim();
  const ink = accentInk(accent);
  root.style.setProperty("--accent-ink", ink);
  try {
    localStorage.setItem(THEME_CACHE_KEY, JSON.stringify({ base: theme.base, tokens: theme.tokens, radius: theme.radius, ink }));
  } catch (error) { /* Cache ist nur fuer den Erstanstrich */ }
}

// GUI-Skalierung (global UND je Panel) gehoert dem jeweiligen Geraet (localStorage) und wird nie zwischen Clients
// synchronisiert: 80 % am iPad aendern nichts am Laptop. Gespeichert wird je Layout (Dateiname) und Geraet:
//   opencue.guiScale@<layout>   globale Skalierung dieses Layouts auf diesem Geraet
//   opencue.guiScale            zuletzt gesetzter Wert dieses Geraets = Startwert fuer Layouts ohne eigenen Wert (und Altbestand)
//   opencue.panelScale@<layout> { panel_id: Skalierung } - nur Panels, die auf diesem Geraet geaendert wurden
// Das Layout auf dem Server behaelt nur den Standard (Panel.panel_scale) fuer Geraete ohne eigenen Wert; er wird durch
// Aenderungen an einem Geraet nie veraendert.
const GUI_SCALE_KEY = "opencue.guiScale";
const PANEL_SCALE_KEY = "opencue.panelScale";
const GUI_SCALE_MIN = 0.5;
const GUI_SCALE_MAX = 2.0;

const _clampScale = (value) => Math.min(GUI_SCALE_MAX, Math.max(GUI_SCALE_MIN, value));
function layoutScaleKey() { return _activeLayoutFilename || "(none)"; }

function _readScale(storageKey) {
  try {
    const value = parseFloat(localStorage.getItem(storageKey));
    if (Number.isFinite(value)) return _clampScale(value);
  } catch (error) { /* localStorage gesperrt */ }
  return null;
}

/** Globale Skalierung dieses Geraets fuer das aktuelle Layout (sonst der Geraete-Standard; null = nie gesetzt). */
function loadLocalGuiScale() {
  const keyed = _readScale(GUI_SCALE_KEY + "@" + layoutScaleKey());
  return keyed !== null ? keyed : _readScale(GUI_SCALE_KEY);
}

function saveLocalGuiScale(scale) {
  try {
    localStorage.setItem(GUI_SCALE_KEY + "@" + layoutScaleKey(), String(scale));
    localStorage.setItem(GUI_SCALE_KEY, String(scale));
  } catch (error) { /* localStorage gesperrt */ }
}

function _panelScaleMap(layoutKey) {
  try {
    const parsed = JSON.parse(localStorage.getItem(PANEL_SCALE_KEY + "@" + layoutKey) || "{}");
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch (error) { return {}; }
}

function loadLocalPanelScale(panelId, layoutKey) {
  const value = Number(_panelScaleMap(layoutKey || layoutScaleKey())[panelId]);
  return Number.isFinite(value) ? _clampScale(value) : null;
}

function saveLocalPanelScale(panelId, scale) {
  const map = _panelScaleMap(layoutScaleKey());
  map[panelId] = scale;
  try { localStorage.setItem(PANEL_SCALE_KEY + "@" + layoutScaleKey(), JSON.stringify(map)); } catch (error) { /* gesperrt */ }
}

/** Wirksame Skalierung eines Panels auf diesem Geraet: der lokale Wert, sonst der Standard aus dem Layout. */
function effectivePanelScale(panel) {
  const local = loadLocalPanelScale(panel.id);
  return local !== null ? local : (panel.panel_scale || 1);
}

/** "Speichern unter" neuer Name: die lokalen Werte folgen dem Layout (sonst saehe es danach anders aus). */
function copyLocalScales(fromKey, toKey) {
  if (fromKey === toKey) return;
  try {
    const global = localStorage.getItem(GUI_SCALE_KEY + "@" + fromKey);
    if (global !== null) localStorage.setItem(GUI_SCALE_KEY + "@" + toKey, global);
    const panels = localStorage.getItem(PANEL_SCALE_KEY + "@" + fromKey);
    if (panels !== null) localStorage.setItem(PANEL_SCALE_KEY + "@" + toKey, panels);
  } catch (error) { /* gesperrt */ }
}

/** Nach einem Layout-Wechsel (oder geaendertem Layout-Namen): globale und Panel-Skalierung dieses Geraets neu anwenden. */
function refreshLocalScales() {
  if (typeof client === "undefined" || !client) return;
  const local = loadLocalGuiScale();
  const st = client.state;
  client._applyGuiScale(local !== null ? local : (st && st.is_local ? st.gui_scale : 1.0));
  ((st && st.panels) || []).forEach((panel) => {
    const el = document.querySelector(`[data-panel-id="${panel.id}"]`);
    if (!el) return;
    const scale = effectivePanelScale(panel);
    const content = el.querySelector(".panel__content");
    if (content) content.style.zoom = scale;
    el.dataset.panelScale = String(scale);
  });
}

class OpenCueClient {
  constructor() {
    const savedScale = loadLocalGuiScale();
    if (savedScale !== null) this._applyGuiScale(savedScale);   // sofort, vor dem ersten Snapshot
    this.socket = null;
    this.state = null;
    this.modules = new Map();
    this._retry = 0;
    this._reconnectTimer = null;
    this._lastMessageAt = Date.now();
    this._hadConnection = false;
    this._gate = null;          // haelt Nachrichten zurueck, solange die Sprache gewechselt wird
    this._hiddenAt = 0;
    this._probeTimer = null;
    // Erst verbinden, wenn die Sprachdateien geladen sind: Panels und Dialoge entstehen so
    // nie mit Roh-Keys oder Platzhaltern.
    translator.init().then(() => this._connect());
    this._startConnectionWatch();
  }

  /** Eingehende Nachricht. Weicht die Sprache im Snapshot von der geladenen ab, wird sie
   *  zuerst gewechselt, damit die Panels gleich in der richtigen Sprache entstehen. Nachrichten
   *  davor und danach behalten ihre Reihenfolge. */
  _onSocketMessage(event) {
    this._lastMessageAt = Date.now();
    clearTimeout(this._probeTimer);
    const run = () => this._handleMessage(event);
    const settle = (promise) => {
      this._gate = promise;
      promise.then(() => { if (this._gate === promise) this._gate = null; });
    };
    if (this._gate) {
      settle(this._gate.then(run));
      return;
    }
    if (typeof event.data === "string" && event.data.indexOf('"state_snapshot"') > -1 && event.data.indexOf('"state_snapshot"') < 40) {
      try {
        const language = JSON.parse(event.data).payload.language;
        if (language && language !== translator.language) {
          settle(translator.setLanguage(language).catch(() => {}).then(run));
          return;
        }
      } catch (error) { /* normal weiter */ }
    }
    run();
  }

  // ---- Verbindungs-Ueberwachung ---------------------------------------------
  _startConnectionWatch() {
    // Heartbeat + Watchdog: ein stillschweigend getrennter Socket (Standby, WLAN-Wechsel)
    // wird am ausbleibenden Pong erkannt und neu aufgebaut.
    setInterval(() => {
      if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
      if (Date.now() - this._lastMessageAt > STALE_CONNECTION_MS) {
        this.socket.close();
        return;
      }
      this.send("ping");
    }, HEARTBEAT_INTERVAL_MS);

    // Tab wieder sichtbar / Netz zurueck: sofort pruefen statt auf den Timer zu warten.
    const wake = () => {
      if (document.visibilityState === "hidden") {
        this._hiddenAt = Date.now();
        return;
      }
      const wasAsleep = this._hiddenAt && Date.now() - this._hiddenAt > 3000;   // Standby/Tab-Wechsel
      this._hiddenAt = 0;
      if (!this.socket || this.socket.readyState >= WebSocket.CLOSING) {
        this._showConnectionBanner(this._hadConnection);
        this._scheduleReconnect(true);
      } else if (this.socket.readyState === WebSocket.OPEN) {
        // Nach dem Aufwachen ist der Socket oft tot, obwohl er "offen" meldet: Overlay zeigen,
        // Resync anfordern und bei ausbleibender Antwort neu verbinden.
        if (wasAsleep) this._showConnectionBanner(true);
        clearTimeout(this._probeTimer);
        this._probeTimer = setTimeout(() => { if (this.socket) this.socket.close(); }, 3000);
        this.send("request_full_state");   // verpasste Aenderungen nachladen
      }
    };
    document.addEventListener("visibilitychange", wake);
    window.addEventListener("online", wake);
    window.addEventListener("pageshow", wake);
  }

  _scheduleReconnect(immediate = false) {
    if (this._reconnectTimer) {
      if (!immediate) return;
      clearTimeout(this._reconnectTimer);
    }
    const delay = immediate ? 0 : Math.min(RECONNECT_DELAY_MS * 2.5, RECONNECT_MIN_DELAY_MS * 2 ** this._retry);
    this._retry += 1;
    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this._connect();
    }, delay);
  }

  /** Vollbild-Overlay "Verbindung wird wiederhergestellt ...": sperrt die Bedienung, solange die
   *  Verbindung fehlt oder der Resync nach einem Standby noch laeuft (verschwindet mit dem Snapshot). */
  _showConnectionBanner(show) {
    let overlay = document.getElementById("connection-overlay");
    if (!show) {
      if (overlay) overlay.hidden = true;
      return;
    }
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "connection-overlay";
      overlay.className = "connection-overlay";
      overlay.setAttribute("role", "status");
      overlay.setAttribute("aria-live", "polite");
      overlay.innerHTML = '<div class="connection-overlay__box"><div class="connection-overlay__spinner"></div>' +
                          '<div class="connection-overlay__text"></div></div>';
      document.body.appendChild(overlay);
    }
    overlay.querySelector(".connection-overlay__text").textContent = i18n("CONNECTION_RESTORING");
    overlay.hidden = false;
  }

  // ---- Connection handling ----------------------------------------------
  _connect() {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${protocol}://${window.location.host}/ws`;
    if (this.socket && this.socket.readyState < WebSocket.CLOSING) {
      this.socket.onclose = null;   // alten Socket sauber verwerfen, kein doppelter Reconnect
      this.socket.close();
    }
    const socket = new WebSocket(url);
    this.socket = socket;

    socket.addEventListener("open", () => {
      this._retry = 0;
      this._lastMessageAt = Date.now();
      // Das Overlay bleibt, bis der Snapshot da ist (Resync abgeschlossen).
      // Der Server schickt beim Verbinden automatisch den kompletten Zustand (Snapshot,
      // Programmer, Effekte) - damit sind nach einem Reconnect alle Aenderungen nachgezogen.
      this._hadConnection = true;
    });

    socket.addEventListener("close", (event) => {
      if (socket !== this.socket) return;
      if (event.code === 4401) {          // Sitzung abgelaufen / Passwort geaendert
        window.location.reload();         // der Server zeigt dann die Login-Maske
        return;
      }
      if (event.code === 4402) {          // vom Host getrennt (Kick): nicht erneut verbinden
        document.body.textContent = i18n("REMOTE_KICKED");
        return;
      }
      if (event.code === 4403) {          // Remote-Zugriff deaktiviert: nicht erneut verbinden
        document.body.textContent = i18n("REMOTE_DISABLED");
        return;
      }
      this._showConnectionBanner(this._hadConnection);
      this._scheduleReconnect();
    });
    socket.addEventListener("error", () => socket.close());
    socket.addEventListener("message", (event) => this._onSocketMessage(event));
  }

  send(type, payload = {}) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type, payload }));
    }
  }

  // ---- Incoming message dispatch -----------------------------------------
  _handleMessage(event) {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch (error) {
      console.error("Invalid server JSON received:", event.data);
      return;
    }
    if (this._coalesceLive(message)) return;
    this._dispatch(message);
  }

  // ---- Live-Daten zusammenfassen -------------------------------------------------
  // DMX-Universen, Effekt-/Cue-Werte und Scheinwerfer-Zustand kommen waehrend eines Fades oder Effekts bis zu 25x pro
  // Sekunde. Ein schwaches Geraet (iPad) schafft deren Verarbeitung nicht in Echtzeit: Die Nachrichten stauen sich, der
  // Hauptthread ist voll ausgelastet, "Weiter" kommt nicht mehr durch und die Oberflaeche steht. Deshalb wird je Art nur der
  // neueste Stand behalten und in einem Takt verarbeitet, der sich an der gemessenen Rechenzeit orientiert (schnelle
  // Geraete: ~25 Hz wie bisher, langsame: seltener, dafuer bleibt der Hauptthread frei). Alles andere laeuft sofort.
  _coalesceLive(message) {
    const type = message.type;
    if (type === "state_snapshot" || type === "show_loaded") {
      this._livePending = null;                       // veraltet: der Snapshot und der Live-Zustand danach ersetzen alles
      return false;
    }
    if (type === "programmer_command_update" || type === "programmer_cleared") {
      this._flushLive();                              // Reihenfolge zu Bedienereignissen am Programmer bleibt erhalten
      return false;
    }
    if (type !== "dmx_universe_changed" && type !== "programmer_live_update" && type !== "fixtures_live" && type !== "fixtures_changed") {
      return false;
    }
    const pending = this._livePending || (this._livePending = { universes: new Map(), live: null, fixtures: null, fixturesChanged: null });
    const payload = message.payload || {};
    if (type === "dmx_universe_changed") {
      pending.universes.set(payload.universe, message);                  // der Snapshot eines Universums ersetzt den vorigen
    } else if (type === "fixtures_changed") {
      pending.fixturesChanged = message;
    } else {
      const slot = type === "fixtures_live" ? "fixtures" : "live";
      const target = pending[slot];
      if (!target) {
        pending[slot] = message;
      } else {                                                           // je Scheinwerfer gewinnt der neueste Stand
        const values = target.payload.values || (target.payload.values = {});
        for (const [id, attrs] of Object.entries(payload.values || {})) values[id] = Object.assign(values[id] || {}, attrs);
      }
    }
    if (!this._liveTimer) {
      const delay = this._liveDelay || LIVE_MIN_DELAY_MS;
      this._liveDue = performance.now() + delay;
      this._liveTimer = setTimeout(() => this._flushLive(), delay);
    }
    return true;
  }

  _flushLive() {
    clearTimeout(this._liveTimer);
    this._liveTimer = null;
    const pending = this._livePending;
    if (!pending) return;
    this._livePending = null;
    const started = performance.now();
    const late = this._liveDue ? Math.max(0, started - this._liveDue) : 0;   // Timer kam verspaetet = Hauptthread (Zeichnen) war belegt
    const messages = [...pending.universes.values()];
    if (pending.live) messages.push(pending.live);
    if (pending.fixtures) messages.push(pending.fixtures);
    if (pending.fixturesChanged) messages.push(pending.fixturesChanged);
    const run = () => {
      for (const message of messages) {
        try {
          this._dispatch(message);
        } catch (error) {
          console.error("Live-Update fehlgeschlagen:", error);
        }
      }
    };
    if (window.ProgrammerState && window.ProgrammerState.batch) window.ProgrammerState.batch(run); else run();
    // Takt an die Rechenzeit anpassen: etwa ein Drittel der Zeit geht an Live-Daten, der Rest gehoert der Bedienung
    const cost = performance.now() - started;
    this._liveDelay = Math.min(LIVE_MAX_DELAY_MS, Math.max(LIVE_MIN_DELAY_MS, Math.round(Math.max(cost * 2, late))));
  }

  _dispatch(message) {
    switch (message.type) {
      case "ping":
        this.send("pong");
        break;
      case "pong":
        break;   // Antwort auf unseren Heartbeat (Zeitstempel ist oben schon gesetzt)
      case "command_value_updated":
        if (window.__applyCommandUpdate) window.__applyCommandUpdate(message.payload);
        break;
      case "command_values_state":
        // Stand aller befehlsbasierten Fader - nach (Re-)Connect/request_full_state
        Object.assign(window.__commandValues || (window.__commandValues = {}), message.payload.values || {});
        if (window.__syncCommandPanels) window.__syncCommandPanels();
        if (window.__mirrorGrandMaster) window.__mirrorGrandMaster();
        break;
      case "show_loaded":
        // Neue/geladene Show: Programmer-Zustand der alten Show verwerfen; der Snapshot und der
        // wiederhergestellte Live-Zustand folgen unmittelbar.
        if (window.ProgrammerState) window.ProgrammerState.reset();
        window.__fixturesLive = {};
        break;
      case "blackout_changed":
        window.__blackout = !!message.payload.enabled;
        if (window.__syncBlackout) window.__syncBlackout();
        break;
      case "cmd_suggestions_changed":
        window.__cmdSuggestions = !!message.payload.enabled;
        if (window.__syncCmdSuggestions) window.__syncCmdSuggestions();
        break;
      case "grand_master_changed":
        window.__grandMaster = message.payload.value;
        if (window.__mirrorGrandMaster) window.__mirrorGrandMaster();
        this._dispatchToPanelPlugins(message);
        break;
      case "sim_stage_changed":
        // 3D-Simulation: die aktive Buehne hat sich geaendert (Objekte, Name, Datei, "ungespeichert")
        document.dispatchEvent(new CustomEvent("sim-stage-changed", { detail: message.payload }));
        if (message.payload && message.payload.show_dirty !== undefined) _setDirty(!!message.payload.show_dirty);      // die Buehne steckt in der Show
        break;
      case "state_snapshot":
        document.dispatchEvent(new Event("sim-stage-resync"));          // nach (Wieder-)Verbindung: aktive Buehne neu holen
        this.state = message.payload;
        _setDirty(!!message.payload.is_dirty);
        _onShowfilesChanged();
        this._applyFullState(message.payload);
        _applyRemoteSnapshot(message.payload);
        this._showConnectionBanner(false);   // Resync fertig
        _restoreDeviceLayout(message.payload);
        if (message.payload.grand_master != null) window.__grandMaster = message.payload.grand_master;
        window.__blackout = !!message.payload.blackout;
        if (window.__syncBlackout) window.__syncBlackout();
        if (message.payload.cmd_suggestions != null) window.__cmdSuggestions = !!message.payload.cmd_suggestions;      // Schalter "Vorschlaege" der Befehlszeile
        if (window.__syncCmdSuggestions) window.__syncCmdSuggestions();
        if (window.__syncCommandPanels) window.__syncCommandPanels();
        if (window.__mirrorGrandMaster) window.__mirrorGrandMaster();
        // Port-Liste sofort befüllen – unabhängig vom Enable-Status
        if (message.payload.enttec_ports) {
          _populateEnttecPorts(message.payload.enttec_port || "", message.payload.enttec_ports);
        }
        if (message.payload.enttec_status) {
          _updateEnttecStatusUI(message.payload.enttec_status);
        }
        _updateDmxHeart(message.payload);
        // Server-autoritative Selektion beim (Wieder-)Verbinden uebernehmen,
        // damit ein spaet beigetretener Client dieselbe Scheinwerfer-
        // Markierung sieht wie alle anderen (siehe selection_changed).
        if (window.ProgrammerState) window.ProgrammerState.setSelectionFromServer(message.payload.selected_fixture_ids || []);
        this._dispatchToModules(message);
        this._dispatchToPanelPlugins(message);
        break;
      case "gui_scale_changed":
        break;   // veraltet: die Skalierung ist pro Geraet und wird nicht mehr verteilt
      case "fixture_groups_changed":
        // Scheinwerfer-Gruppen (rein organisatorisch): Spiegel im Client-Zustand, Kachelraster neu sortieren
        if (this.state) this.state.groups = message.payload.groups || {};
        _setDirty(message.payload.is_dirty !== false);
        this._dispatchToPanelPlugins(message);
        break;
      case "fixture_library_changed":
        // Installierte Scheinwerfertypen haben sich geaendert (Installieren/Deinstallieren/Import, auch von einem anderen Geraet)
        document.dispatchEvent(new CustomEvent("fixture-library-changed"));
        break;
      case "fixture_group_result":
        if (!message.payload.ok) _showToast(message.payload.code === "duplicate" ? "FXGRP_ERR_DUP" : "FXGRP_ERR_INVALID", "warn", 3500);
        break;
      case "language_changed":
        if (this.state) this.state.language = message.payload.language;
        translator.setLanguage(message.payload.language).then(() => {
          updateSettingsFieldsInAllPanels("language", message.payload.language);
          this._dispatchToPanelPlugins(message);
        });
        break;
      case "data_path_changed": {
        if (this.state) {
          this.state.data_root = message.payload.path;
          this.state.custom_data_path = message.payload.is_custom ? message.payload.path : "";
        }
        const dp = document.getElementById("settings-data-path-display");
        if (dp) dp.value = message.payload.path || "";
        break;
      }
      case "remote_client_count":
        _updateRemoteIndicator(message.payload.count || 0, !!message.payload.enabled);
        break;
      case "remote_clients_changed":
        _remoteClients = message.payload.clients || [];
        _remoteClientsAt = Date.now();
        _renderRemoteClients();
        break;
      case "kicked":
        break;   // der Close-Code 4402 folgt unmittelbar
      case "remote_changed":
        if (this.state) this.state.remote = message.payload;
        _updateRemoteIndicator(_remoteCount, !!message.payload.enabled);
        _renderRemoteSettings();
        break;
      case "artnet_ip_changed":
        if (this.state) this.state.artnet_ip = message.payload.ip;
        updateSettingsFieldsInAllPanels("artnet_ip", message.payload.ip);
        break;
      case "artnet_bind_ip_changed":
        if (this.state) this.state.artnet_bind_ip = message.payload.ip;
        updateSettingsFieldsInAllPanels("artnet_bind_ip", message.payload.ip);
        break;
      case "artnet_enabled_changed":
        if (this.state) this.state.artnet_enabled = message.payload.enabled;
        updateSettingsFieldsInAllPanels("artnet_enabled", message.payload.enabled);
        _updateArtnetStatusUI(message.payload.enabled);
        _updateDmxHeart(this.state);
        break;
      case "sacn_enabled_changed":
        if (this.state) this.state.sacn_enabled = message.payload.enabled;
        updateSettingsFieldsInAllPanels("sacn_enabled", message.payload.enabled);
        _updateSacnStatusUI(message.payload.enabled);
        _updateDmxHeart(this.state);
        break;
      case "enttec_enabled_changed":
        if (this.state) this.state.enttec_enabled = message.payload.enabled;
        updateSettingsFieldsInAllPanels("enttec_enabled", message.payload.enabled);
        break;
      case "enttec_port_changed":
        if (this.state) this.state.enttec_port = message.payload.port;
        updateSettingsFieldsInAllPanels("enttec_port", message.payload.port);
        break;
      case "enttec_universe_changed":
        if (this.state) this.state.enttec_universe = message.payload.universe;
        updateSettingsFieldsInAllPanels("enttec_universe", message.payload.universe);
        break;
      case "enttec_status_changed": {
        const _prevConnected = !!(this.state && this.state.enttec_status && this.state.enttec_status.connected);
        if (this.state) this.state.enttec_status = message.payload.status;
        _updateEnttecStatusUI(message.payload.status);
        _updateDmxHeart(this.state);
        const _nowStatus = message.payload.status || {};
        if (_prevConnected && !_nowStatus.connected) {
          _showToast(i18n("TOAST_ENTTEC_DISCONNECTED"), "error");
        } else if (!_prevConnected && _nowStatus.connected) {
          _showToast(i18n("TOAST_ENTTEC_RECONNECTED").replace("{port}", _nowStatus.port || ""), "ok");
        }
        this._dispatchToPanelPlugins(message);
        break;
      }
      case "dmx_reinit_done":
        _showToast(i18n("TOAST_DMX_REINIT_OK"), "ok");
        document.getElementById("settings-dmx-reinit-btn")?.removeAttribute("disabled");
        this._dispatchToPanelPlugins(message);
        break;
      case "default_universe_changed":
        if (this.state) this.state.default_universe = message.payload.universe;
        updateSettingsFieldsInAllPanels("default_universe", message.payload.universe);
        break;
      case "theme_changed":
        if (this.state) this.state.theme = message.payload.theme;
        this._applyTheme(message.payload.theme);
        ThemeUI.sync(message.payload.theme);
        if (window.OCFileManager) window.OCFileManager.changed("themes");           // "aktiv"-Markierung im Dateimanager
        break;
      case "theme_profiles_changed":
        if (this.state) this.state.theme_profiles = message.payload.profiles;
        ThemeUI.setProfiles(message.payload.profiles);
        if (window.OCFileManager) window.OCFileManager.changed("themes");
        break;
      case "panel_defaults_changed":
        if (this.state) this.state.panel_defaults = message.payload.panel_defaults;
        break;
      case "settings_reset":
        if (this.state) Object.assign(this.state, message.payload);
        applySettingsResetToUI(message.payload);
        break;
      case "panels_pasted":
        selectPanels(message.payload.ids || []);       // die neuen Kopien sind danach markiert (naechstes Strg+V / Duplizieren)
        break;
      case "panels_changed":
        if (this.state) this.state.panels = message.payload.panels;
        renderPanels(message.payload.panels); // DOM-level reconciliation, not a full rebuild - see renderPanels()
        _scheduleLayoutStatus();               // "ungespeicherte Aenderungen" neu bewerten
        if (window.__syncCommandPanels) window.__syncCommandPanels();
        if (window.__mirrorGrandMaster) window.__mirrorGrandMaster();
        break;
//3D-AUS//       case "stage_changed":
//3D-AUS//         // 3D-Buehne (app/stage3d.py): der Server sendet nach jeder Aenderung die ganze Buehne (klein) an alle Geraete
//3D-AUS//         if (this.state) {
//3D-AUS//           Object.assign(this.state, { room: message.payload.room, rig: message.payload.rig, room_library: message.payload.room_library, rig_library: message.payload.rig_library });
//3D-AUS//         }
//3D-AUS//         _setDirty(message.payload.is_dirty !== false);
//3D-AUS//         document.dispatchEvent(new CustomEvent("stage-changed", { detail: message.payload }));
//3D-AUS//         this._dispatchToPanelPlugins(message);
//3D-AUS//         break;
//3D-AUS//       case "stage_error":
//3D-AUS//         _showToast(i18n("ST3D_ERR_" + String((message.payload && message.payload.error) || "invalid_op").toUpperCase()), "error", 4000);
//3D-AUS//         break;
      case "fixtures_changed":
        if (this.state) this.state.fixtures = message.payload.fixtures;
        _setDirty(message.payload.is_dirty !== false); // default dirty=true
        this._dispatchToPanelPlugins(message);
        break;
      case "presets_changed":
        if (this.state) {
          this.state.presets = message.payload.presets;
          this.state.preset_groups = message.payload.preset_groups;
        }
        _setDirty(message.payload.is_dirty !== false);
        this._dispatchToPanelPlugins(message);
        break;
      case "cuelists_changed":
        if (this.state) {
          this.state.cuelists = message.payload.cuelists;
          this.state.active_cuelist_id = message.payload.active_cuelist_id;
          this.state.active_cue_ids = message.payload.active_cue_ids;
        }
        _setDirty(message.payload.is_dirty !== false);
        this._dispatchToPanelPlugins(message);
        break;
      case "programmer_refs":
        // Welche Variable gibt gerade welchen Teil welcher Fixture vor: Dropdowns und gesperrte Fader folgen daraus
        if (window.ProgrammerState) window.ProgrammerState.setPresetRefs(message.payload.refs || {});
        document.dispatchEvent(new CustomEvent("programmer-state-updated"));
        break;
      case "programmer_values_quiet":
        if (window.ProgrammerState) window.ProgrammerState.applyQuiet(message.payload.values || {});
        this._dispatchToPanelPlugins(message);
        break;
      case "programmer_live_update":
        // Fade-Tick der CueEngine (Go/Back + laufende Ueberblendung):
        // synct die abstrakten Fixture-Werte in den Programmer, OHNE sie
        // als "touched" zu markieren - das ist Cue-Output, keine manuelle
        // Bedienung. Loest ueber syncFromEngine() denselben
        // "programmer-state-updated"-Refresh aus wie jede manuelle
        // Fader-Aenderung (Tiles/Fader/Color-Picker aktualisieren sich live).
        if (window.ProgrammerState) window.ProgrammerState.syncFromEngine(message.payload.values || {});
        document.dispatchEvent(new CustomEvent("programmer-live-values", { detail: message.payload.values || {} }));
        this._dispatchToPanelPlugins(message);
        break;
      case "fixtures_live": {
        // DMX-Puffer ist die Wahrheit: Scheinwerfersteuerung (Kacheln, Fader, Farbe, Position) folgt live
        if (window.ProgrammerState) {
          const forProgrammer = {};
          for (const [id, attrs] of Object.entries(message.payload.values || {})) { const { wheels, ...rest } = attrs; forProgrammer[id] = rest; }       // rohe Rad-Bytes gehoeren nur der 3D-Simulation
          window.ProgrammerState.syncFromDmx(forProgrammer);
        }
        // Letzter bekannter Stand je Scheinwerfer (fuer Panels, die spaeter entstehen, z. B. die 3D-Simulation) + Ereignis fuer Panels, die schon laufen
        const live = message.payload.values || {};
        const cache = window.__fixturesLive || (window.__fixturesLive = {});
        for (const [id, attrs] of Object.entries(live)) cache[id] = Object.assign(cache[id] || {}, attrs);
        document.dispatchEvent(new CustomEvent("fixtures-live-values", { detail: live }));
        break;
      }
      case "programmer_command_update":
        // Command-Line-getriebene Werteaenderung ("At 80" etc.) - anders
        // als programmer_live_update WIRD hier touched markiert (siehe
        // ProgrammerState.applyFromServer).
        if (window.ProgrammerState) window.ProgrammerState.applyFromServer(message.payload.values || {});
        this._dispatchToPanelPlugins(message);
        break;
      case "programmer_cleared":
        // "Store Cue": nur die touched-Markierung aufraeumen (Werte sind
        // bereits im Cue gesichert, DMX-Ausgabe bleibt unveraendert).
        // "Clear Clear": liefert zusaetzlich reset_values - die
        // tatsaechlichen Neutralwerte (Dimmer 0/Farbe schwarz/Pan+Tilt
        // Mitte/Beam 0) je Fixture, die die CueEngine-DMX-Ausgabe bereits
        // real geschrieben hat. syncFromEngine() spiegelt sie in den
        // Programmer, OHNE touched zu markieren (das sind Neutralwerte,
        // keine manuelle Bedienung) - darauf folgt clearTouchedByIds() als
        // Sicherheitsnetz. Beides zusammen loest denselben
        // "programmer-state-updated"-Refresh aus, den Scheinwerfer-Karten,
        // Farbfelder, das 2D-Positionierungs-Raster und die roten
        // Programmer-Badges in der Scheinwerferliste bereits abonniert
        // haben - keine weitere Panel-spezifische Logik noetig.
        if (window.ProgrammerState) {
          if (message.payload.reset_values) window.ProgrammerState.syncFromEngine(message.payload.reset_values);
          window.ProgrammerState.clearTouchedByIds(message.payload.fixture_ids || []);
        }
        if (message.payload.reset_dropdowns) {
          document.dispatchEvent(new CustomEvent("programmer-dropdowns-reset"));
        }
        this._dispatchToPanelPlugins(message);
        break;
      case "selection_changed":
        // Server-autoritative Selektion (Mausklick auf einem beliebigen
        // Client ODER Command-Line-Befehl "Fixture"/"Group") - ersetzt die
        // lokale Selektion, OHNE sie zurueck zu senden (siehe
        // ProgrammerState.setSelectionFromServer).
        if (this.state) this.state.selected_fixture_ids = message.payload.selected_ids || [];
        if (window.ProgrammerState) window.ProgrammerState.setSelectionFromServer(message.payload.selected_ids || []);
        this._dispatchToPanelPlugins(message);
        break;
      case "command_log":
        // Gemeinsame Befehlshistorie der Command Line - geht an alle
        // Clients, jedes geoeffnete Command-Line-Panel zeigt dieselbe Liste.
        this._dispatchToPanelPlugins(message);
        break;
      case "layout_update_notice":
        _handleLayoutUpdateNotice(message.payload);
        break;
      case "layout_status_changed":
        _onLayoutsChanged();
        break;
      case "cue_store_result":
        if (window.__cueUi) window.__cueUi.onResult(message.payload);
        break;
      case "showfile_status_changed":
        _refreshShowfileStatus(true);
        break;
      case "close_requested":
        _pendingCloseAfterSave = false;
        Modal.open("close-confirm");
        setTimeout(() => document.getElementById("close-save-button")?.focus(), 50);
        break;
      case "fx_changed":
        _setDirty(message.payload.is_dirty !== false);
        document.dispatchEvent(new CustomEvent("fx-data-updated", { detail: message.payload }));
        break;
      case "show_saved": {
        if (this.state) {
          this.state.showfile_name = message.payload.showfile_name;
        }
        _setDirty(false);
        updateWindowTitle(message.payload.showfile_name, false);
        _onShowfilesChanged();
        // Ausstehende Navigation nach dem Speichern ausfuehren
        const savedAction = _pendingNavAction;
        _pendingNavAction = null;
        if (savedAction) savedAction();
        if (_pendingCloseAfterSave) {
          _pendingCloseAfterSave = false;
          client.send("close_decision", { choice: "save" });
        }
        break;
      }
      case "error":
        if (message.payload?.code === "CUELIST_DUPE") {
          _showToast(i18n("CUELIST_DUPE_NAME").replace("{name}", message.payload.name || ""), "warn");
        } else if (message.payload?.code === "FX_DUPE") {
          _showToast(i18n("FXE_DUPE_NAME").replace("{name}", message.payload.name || ""), "warn");
        } else if (message.payload?.code === "PRESET_DUPE") {
          _showToast(
            i18n("PRESET_DUPE_NAME").replace("{name}", message.payload.name || ""),
            "warn"
          );
        }
        break;
      default:
        this._dispatchToModules(message);
        this._dispatchToPanelPlugins(message);
    }
  }

  _dispatchToPanelPlugins(message) {
    document.querySelectorAll("[data-panel-type]").forEach((panelEl) => {
      const plugin = window.__panelPlugins.get(panelEl.dataset.panelType);
      if (plugin?.onMessage) plugin.onMessage(panelEl, message.type, message.payload || {});
    });
  }

  _dispatchToModules(message) {
    for (const moduleInstance of this.modules.values()) {
      if (typeof moduleInstance.onMessage === "function") {
        moduleInstance.onMessage(message);
      }
    }
  }

  // ---- Module registration (Phase 2+: Fixture View, Executors, ...) -----
  registerModule(name, moduleInstance) {
    this.modules.set(name, moduleInstance);
    if (typeof moduleInstance.onMessage === "function" && this.state) {
      moduleInstance.onMessage({ type: "state_snapshot", payload: this.state });
    }
  }

  // ---- Global UI base state ----------------------------------------------
  _applyFullState(payload) {
    updateWindowTitle(payload.showfile_name, !!payload.is_dirty);
    // Das Layout dieses Geraets zuerst: die lokale Skalierung ist je Layout gespeichert.
    if (payload.last_active_layout) {
      _activeLayoutName = payload.last_active_layout;
      _activeLayoutFilename = _toLayoutFilename(payload.last_active_layout);
    }
    // Lokaler Wert hat Vorrang; die Konsole faellt auf ihren gespeicherten Standard zurueck,
    // externe Geraete auf 100 %. Der Server-Wert wird nie an andere Geraete verteilt.
    const localScale = loadLocalGuiScale();
    this._applyGuiScale(localScale !== null ? localScale : (payload.is_local ? payload.gui_scale : 1.0));
    this._applyTheme(payload.theme);
    ThemeUI.sync(payload.theme);
    ThemeUI.setProfiles(payload.theme_profiles || {});
    renderPanels(payload.panels);
    updateAddPanelModalList(payload.panel_types || []);
    // Letztes aktives Layout aus dem Snapshot übernehmen; Submenu sofort
    // auffrischen, damit die Hervorhebung beim nächsten Öffnen korrekt ist.
    if (payload.last_active_layout) {
      _activeLayoutName = payload.last_active_layout;
      _activeLayoutFilename = _toLayoutFilename(payload.last_active_layout);
      _refreshLayoutsSubmenu();
    }
    _scheduleLayoutStatus();

    // The server is authoritative for the persisted language (app_config.json).
    // The locally cached (localStorage) guess used for instant first paint is
    // corrected here if it differs.
    if (payload.language && payload.language !== translator.language) {
      translator.setLanguage(payload.language);
    }
  }

  _applyGuiScale(scale) {
    document.documentElement.style.setProperty("--gui-scale", scale);
  }

  /** Skalierung dieses Geraets setzen und lokal merken. Nur die Konsole sichert zusaetzlich
   *  einen Standardwert auf dem Server (falls ihr Browser nichts dauerhaft speichert). */
  setGuiScale(scale) {
    scale = Math.min(GUI_SCALE_MAX, Math.max(GUI_SCALE_MIN, Number(scale) || 1.0));
    this._applyGuiScale(scale);
    saveLocalGuiScale(scale);
    if (this.state && this.state.is_local) this.send("set_gui_scale", { scale });
  }

  // Wendet das vom Server gelieferte Theme an (Snapshot, theme_changed, settings_reset).
  _applyTheme(theme) {
    applyTheme(theme);
  }
}

// ---- Menu bar (File / View / Language dropdowns) -------------------------

function setupMenuBar() {
  const menus = Array.from(document.querySelectorAll(".menu"));
  const LEAVE_DELAY_MS = 160;   // Toleranz beim Wandern zwischen zwei Ausloesern: kein Flackern

  // Zustand: hoechstens EIN Toolbar-Menue ist offen. "pinned" = per Klick fixiert.
  let openMenu = null;
  let pinned = false;
  let leaveTimer = null;
  // Zuletzt benutzte Eingabeart: nur bei der Maus gibt es "Zeiger verlassen" (Hover). Auf Touch schliesst ein Menue
  // ausschliesslich ein Tipp ausserhalb - nie ein Timer (Touch kennt kein echtes Hover; emulierte Hover-Ereignisse
  // eines Tipps duerfen das Menue nicht nach 160 ms wieder zuklappen).
  let lastPointerType = "mouse";
  document.addEventListener("pointerdown", (event) => { lastPointerType = event.pointerType || "mouse"; }, true);

  const resetSubmenus = () => {
    document.querySelectorAll("[data-submenu]").forEach((item) => {
      item.classList.remove("menu__item--submenu-open");
    });
  };

  const closeAllMenus = () => {
    clearTimeout(leaveTimer);
    menus.forEach((menu) => menu.classList.remove("menu--open"));
    resetSubmenus();
    openMenu = null;
    pinned = false;
  };

  const openOnly = (menu, pin) => {
    if (openMenu && openMenu !== menu) {
      openMenu.classList.remove("menu--open");
      resetSubmenus();
    }
    menu.classList.add("menu--open");
    openMenu = menu;
    pinned = pin;
  };

  // Nach kurzer Verzoegerung schliessen, wenn nichts mehr unter dem Zeiger liegt (Ausloeser, Dropdown,
  // Untermenue) und das Menue nur per Hover offen war. Per Klick fixierte Menues bleiben stehen.
  const scheduleLeave = () => {
    clearTimeout(leaveTimer);
    if (lastPointerType !== "mouse") return;
    leaveTimer = setTimeout(() => {
      if (lastPointerType !== "mouse") return;
      if (openMenu && !pinned && !menus.some((menu) => menu.matches(":hover"))) closeAllMenus();
    }, LEAVE_DELAY_MS);
  };

  menus.forEach((menu) => {
    const trigger = menu.querySelector(".menu__trigger");
    if (!trigger) return;
    trigger.addEventListener("click", (event) => {
      event.stopPropagation();
      if (openMenu === menu && pinned) closeAllMenus();   // erneuter Klick schliesst
      else openOnly(menu, true);                          // Klick oeffnet bzw. fixiert (auch ein Hover-Menue)
    });
    // Hover (nur Maus; Touch bleibt reines Tippen). Ist schon ein Menue offen, uebernimmt dieses sofort.
    menu.addEventListener("pointerenter", (event) => {
      if (event.pointerType !== "mouse") return;
      clearTimeout(leaveTimer);
      if (openMenu && openMenu !== menu) openOnly(menu, pinned);
      else if (!openMenu) openOnly(menu, false);
    });
    menu.addEventListener("pointerleave", (event) => {
      if (event.pointerType === "mouse") scheduleLeave();
    });
  });

  // Klick irgendwo ausserhalb bzw. Escape schliesst alles.
  document.addEventListener("click", closeAllMenus);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeAllMenus();
  });

  // Nested submenu (View -> Add Panel -> ...): toggling it must not bubble
  // up to the document click listener above, or it would close the parent
  // menu (and itself) in the same click. A click on one of the submenu's OWN
  // leaf items (e.g. "Settings") must NOT be swallowed here though - it
  // needs to keep bubbling so the [data-action="add-panel"] delegated
  // listener below (and the normal closeAllMenus cleanup) still run.
  document.querySelectorAll("[data-submenu]").forEach((item) => {
    item.addEventListener("click", (event) => {
      if (event.target.closest(".menu__submenu")) return;
      event.stopPropagation();
      const isOpen = item.classList.contains("menu__item--submenu-open");
      document.querySelectorAll("[data-submenu]").forEach((el) => {
        el.classList.remove("menu__item--submenu-open");
      });
      if (!isOpen) item.classList.add("menu__item--submenu-open");
    });
  });

  // View -> Add Panel -> <type>: create a new panel of that type. Delegated
  // so it also matches leaves inside any future submenu.
  document.addEventListener("click", (event) => {
    const addPanelItem = event.target.closest("[data-action='add-panel']");
    if (addPanelItem) client.send("add_panel", { panel_type: addPanelItem.dataset.panelType });
  });

  // Edit -> Edit Panels: toggles the whole workspace between Live and Edit Mode.
  const editModeItem = document.querySelector('[data-action="toggle-edit-mode"]');
  if (editModeItem) {
    editModeItem.addEventListener("click", () => toggleEditModeInteractive());
  }

  // Edit -> Undo / Redo: dasselbe wie Strg+Z / Strg+Y (ohne Tastatur, z.B. am iPad).
  // Wie die Kuerzel nur im Bearbeitungsmodus wirksam (Panel-Anordnung); ausserhalb passiert nichts.
  document.querySelector('[data-action="undo"]')?.addEventListener("click", () => { if (isEditMode) client.send("undo"); });
  document.querySelector('[data-action="redo"]')?.addEventListener("click", () => { if (isEditMode) client.send("redo"); });

  // Language menu: switch translation set locally (instant) and persist it
  // server-side (app_config.json), which also syncs any other open client.
  document.querySelectorAll("[data-lang]").forEach((item) => {
    item.addEventListener("click", () => {
      const language = item.dataset.lang;
      translator.setLanguage(language).then(() => {
        client.send("set_language", { language });
      });
    });
  });

  // Language > Toggle Language item (also wired to Ctrl+Shift+L shortcut)
  document.querySelector('[data-action="toggle-language"]')?.addEventListener("click", () => {
    _toggleLanguage();
  });

  // File menu: Exit. Dummy-container principle - the desktop window has no
  // js_api bridge (that path caused COM/threading crashes under WebView2:
  // "CoreWebView2 members can only be accessed from the UI thread" and
  // recursion errors). Instead this is just another WebSocket message; the
  // server flags an exit request that main.py's watcher thread picks up and
  // closes the window with (same native close-confirmation dialog as "X").
  // File -> Sign out (nur Remote-Geraete): Sitzung und gemerkte Anmeldung ungueltig machen, dann zur Anmeldung.
  document.querySelector('[data-action="logout"]')?.addEventListener("click", async () => {
    try { await fetch("/auth/logout", { method: "POST" }); } catch (error) { /* Server weg: trotzdem neu laden */ }
    window.location.href = "/remote/";
  });

  const exitItem = document.querySelector('[data-action="exit"]');
  if (exitItem) {
    exitItem.addEventListener("click", () => client.send("exit_app"));
  }
}

// ---- Modal system (reusable) ---------------------------------------------

const MODAL_Z_BASE = 100100;   // ueber allen festen Oberflaechen-Ebenen (Menues 100002, Kontextmenue 100010, dynamische Dialoge 100004-100006); Toasts liegen darueber

// Regler: der Teil links vom Griff wird in der Akzentfarbe gefuellt (CSS-Variable --pct, siehe modern.css "Regler").
window.ocRangeFill = function (el) {
  if (!el || el.type !== "range") return;
  const min = parseFloat(el.min || "0"), max = parseFloat(el.max || "100"), v = parseFloat(el.value);
  const pct = max > min && !isNaN(v) ? Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100)) : 0;
  el.style.setProperty("--pct", pct + "%");
};
document.addEventListener("input", (e) => { if (e.target && e.target.type === "range") window.ocRangeFill(e.target); }, true);
// Dynamisch erzeugte Regler (Effekt-Parameter, Studio-Dialoge ...) bekommen ihre Fuellung, sobald sie im Dokument stehen.
new MutationObserver((records) => {
  for (const rec of records) {
    rec.addedNodes.forEach((node) => {
      if (node.nodeType !== 1) return;
      if (node.matches && node.matches('input[type="range"]')) window.ocRangeFill(node);
      if (node.querySelectorAll) node.querySelectorAll('input[type="range"]').forEach(window.ocRangeFill);
    });
  }
}).observe(document.documentElement, { childList: true, subtree: true });

const Modal = {
  _stack: [],
  _hooks: {},   // id -> Funktion, die einmalig beim Schliessen (X, Abbrechen, Escape) laeuft
  open(id) {
    const backdrop = document.querySelector(`[data-modal-backdrop="${id}"]`);
    if (backdrop) {
      backdrop.classList.add("modal-backdrop--visible");
      if (!this._stack.includes(id)) this._stack.push(id);
      // Der zuletzt geoeffnete Dialog liegt immer ganz vorne (ueber jedem schon offenen, auch ueber dynamisch erzeugten Dialogen
      // und Menues) - sonst kann z.B. "Programm beenden" hinter einem grossen Dialog verschwinden.
      backdrop.style.zIndex = String(MODAL_Z_BASE + this._stack.indexOf(id));
      translator.apply();
      backdrop.querySelectorAll('input[type="range"]').forEach(window.ocRangeFill);
    }
  },
  close(id) {
    const backdrop = document.querySelector(`[data-modal-backdrop="${id}"]`);
    if (backdrop) { backdrop.classList.remove("modal-backdrop--visible"); backdrop.style.zIndex = ""; }
    const idx = this._stack.lastIndexOf(id);
    if (idx !== -1) this._stack.splice(idx, 1);
    const hook = this._hooks[id];
    if (hook) { delete this._hooks[id]; hook(); }
  },
  isOpen(id) {
    const backdrop = document.querySelector(`[data-modal-backdrop="${id}"]`);
    return !!backdrop && backdrop.classList.contains("modal-backdrop--visible");
  },
  closeTop() {
    if (this._stack.length > 0) {
      const topId = this._stack[this._stack.length - 1];
      this.close(topId);
      return topId;
    }
    return null;
  },
};

// ---- Global modal cancel/close delegation --------------------------------
document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-modal-cancel],[data-modal-close]");
  if (!btn) return;
  const id = btn.dataset.modalCancel || btn.dataset.modalClose;
  if (id) Modal.close(id);
});

// ---- Escape-Key: schliesst das oberste aktive Modal ----------------------
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  // Zuerst HTML-gesteuerte Modals (via Modal-Stack)
  if (Modal.closeTop()) { e.preventDefault(); return; }
  // Dann dynamisch erzeugte Backdrops (Fixtures-Modals, Library)
  const dynamicBackdrop = [...document.querySelectorAll(
    ".fx-panel-modal-backdrop, .fx-library-backdrop"
  )].filter(el => el.isConnected).pop();
  if (dynamicBackdrop) { dynamicBackdrop.remove(); e.preventDefault(); }
});

// ---- GUI Scale modal (View -> GUI Scale...) -------------------------------

function setupGuiScaleModal() {
  const slider = document.getElementById("gui-scale-modal-slider");
  const numberInput = document.getElementById("gui-scale-modal-number");
  const applyButton = document.getElementById("gui-scale-modal-apply");
  const closeButton = document.querySelector('[data-modal-close="gui-scale"]');
  const cancelButton = document.querySelector('[data-modal-cancel="gui-scale"]');
  if (!slider || !numberInput || !applyButton || !closeButton || !cancelButton) return;

  let scaleBeforeOpen = 1.0;

  const syncFields = (scale) => {
    slider.value = scale;
    numberInput.value = Math.round(scale * 100);
  };

  const cancelAndClose = () => {
    client._applyGuiScale(scaleBeforeOpen);
    Modal.close("gui-scale");
  };

  // Delegated (not a single querySelector'd trigger): the toolbar's static
  // "GUI Scale..." menu item AND the Settings panel's dynamically-created
  // "Adjust GUI Scale" button both just carry data-action="open-gui-scale-modal".
  document.addEventListener("click", (event) => {
    if (!event.target.closest('[data-action="open-gui-scale-modal"]')) return;
    const current = getComputedStyle(document.documentElement).getPropertyValue("--gui-scale");
    scaleBeforeOpen = parseFloat(current) || 1.0;
    syncFields(scaleBeforeOpen);
    Modal.open("gui-scale");
  });

  // Live preview while dragging, per spec.
  slider.addEventListener("input", (event) => {
    const scale = parseFloat(event.target.value);
    numberInput.value = Math.round(scale * 100);
    client._applyGuiScale(scale);
  });

  numberInput.addEventListener("input", (event) => {
    const percent = parseFloat(event.target.value);
    if (Number.isNaN(percent)) return;
    const scale = Math.min(200, Math.max(50, percent)) / 100;
    slider.value = scale;
    client._applyGuiScale(scale);
  });

  // Save & Close: commit to the server (persists to app_config.json).
  applyButton.addEventListener("click", () => {
    client.setGuiScale(parseFloat(slider.value));
    Modal.close("gui-scale");
  });

  // Cancel / "x" close / Escape: discard the live preview and revert.
  cancelButton.addEventListener("click", cancelAndClose);
  closeButton.addEventListener("click", cancelAndClose);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && Modal.isOpen("gui-scale")) cancelAndClose();
  });
}

// ---- Edit Mode -------------------------------------------------------------

let isEditMode = false;

function setEditMode(value) {
  isEditMode = value;

  // Kein stilles Speichern beim Verlassen: toggleEditModeInteractive() fragt bei ungespeicherten Aenderungen nach.
  const viewport = document.getElementById("viewport");
  if (viewport) viewport.classList.toggle("edit-mode", isEditMode);
  document.querySelectorAll('[data-action="undo"], [data-action="redo"]').forEach((item) => item.classList.toggle("menu__item--disabled", !isEditMode));      // Undo/Redo gelten nur im Bearbeitungsmodus

  const editModeItem = document.querySelector('[data-action="toggle-edit-mode"]');
  if (editModeItem) {
    editModeItem.classList.toggle("menu__item--active-edit", isEditMode);
    // Dynamic label: "Edit Panels" <-> "Exit Edit Mode". Kept in sync via
    // data-i18n (not just textContent) so a later language switch re-
    // translates whichever of the two is CURRENTLY shown, not always the
    // "off" label - same pattern used for the connection-status pill.
    const labelKey = isEditMode ? "EXIT_EDIT_MODE" : "EDIT_PANELS";
    // Target the label span when the item uses the shortcut-hint layout,
    // fall back to the li itself for the plain single-text layout.
    const labelEl = editModeItem.querySelector("span[data-i18n]") ?? editModeItem;
    labelEl.dataset.i18n = labelKey;
    labelEl.textContent = i18n(labelKey);
  }

  // Edit-only actions (e.g. Add Panel...) stay inert/dimmed until Edit Mode
  // is switched on.
  document.querySelectorAll("[data-edit-only]").forEach((item) => {
    item.classList.toggle("menu__item--disabled", !isEditMode);
    item.setAttribute("aria-disabled", String(!isEditMode));
  });

  if (!isEditMode) clearPanelSelection();
  hideContextMenu();
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

// ---- Workspace panels (dynamic module system) ------------------------------

const MIN_PANEL_WIDTH_PERCENT = 12;
const MIN_PANEL_HEIGHT_PERCENT = 10;
const MIN_COMPACT_WIDTH_PERCENT = 1;
const MIN_COMPACT_HEIGHT_PERCENT = 1;
const COMPACT_PANEL_TYPES = new Set(["button", "fader", "executor"]);

function getPanelMinSize(panelEl) {
  const type = panelEl ? panelEl.dataset.panelType : "";
  return COMPACT_PANEL_TYPES.has(type)
    ? { w: MIN_COMPACT_WIDTH_PERCENT, h: MIN_COMPACT_HEIGHT_PERCENT }
    : { w: MIN_PANEL_WIDTH_PERCENT, h: MIN_PANEL_HEIGHT_PERCENT };
}

const PANEL_TITLE_KEYS = {
  settings: "PANEL_SETTINGS",
  dmx_monitor: "PANEL_DMX_MONITOR",
  fixtures: "PANEL_FIXTURES",
  programmer: "PANEL_PROGRAMMER",
  presets: "PANEL_PRESETS",
  cuelist: "PANEL_CUELIST",
  executor: "PANEL_EXECUTOR",
  command_line: "PANEL_COMMAND_LINE",
  command_numpad: "PANEL_COMMAND_NUMPAD",
  command_buttons: "PANEL_COMMAND_BUTTONS",
  fx_studio: "PANEL_FX_STUDIO",
  button: "PANEL_BUTTON",
  fader: "PANEL_FADER",
  stream: "PANEL_STREAM",
  sim3d: "PANEL_SIM3D",
//3D-AUS//   stage3d: "PANEL_STAGE3D",
};

/** Reconciles the workspace with the server's panel list - no
 * innerHTML/full-teardown. Existing panels get their geometry/colors
 * patched in place (their content, focus, open dropdowns, in-progress
 * form edits, etc. are left completely alone); only genuinely new panels
 * are created and only genuinely removed ones are torn down. This is what
 * keeps a `panels_changed` broadcast (from this client's own edit, or from
 * another connected client) from ever flickering or interrupting whatever
 * the user is doing in an already-open panel. */
function renderPanels(panels) {
  const workspace = document.getElementById("app-root");
  if (!workspace) return;

  const incoming = panels || [];
  const incomingIds = new Set(incoming.map((panel) => panel.id));

  Array.from(workspace.querySelectorAll(".workspace-panel")).forEach((el) => {
    if (!incomingIds.has(el.dataset.panelId)) {
      el.remove();
      _selectedPanels.delete(el.dataset.panelId);
    }
  });

  let panelsAdded = false;
  incoming.forEach((panel) => {
    const existingEl = workspace.querySelector(`[data-panel-id="${panel.id}"]`);
    if (existingEl) {
      applyPanelGeometry(existingEl, panel);
    } else {
      const newEl = buildPanelElement(panel);
      workspace.appendChild(newEl);
      scheduleUiStateRestore(newEl, panel);
      panelsAdded = true;
    }
  });

  // Neu gebaute Panels sofort mit dem aktuellen Live-State befüllen:
  // Fixture-Grid, Programmer-Selektion, GDTF-Attribute, DMX-Farben.
  if (panelsAdded) refreshActivePanels();
  // Panels koennen den Bestand kennen wollen (z.B. zeigt das Tasten-Panel eine eigene Anzeige, solange es keine Befehlszeile gibt).
  document.dispatchEvent(new CustomEvent("panels-rendered"));
}

// ---- Panel-UI-Zustand (Scrollpositionen, Eingabefelder) --------------------
// Elemente im Panel-Inhalt werden ueber ihren Kind-Index-Pfad adressiert,
// damit der gespeicherte Zustand nach einem Neuaufbau auf dieselben Elemente
// trifft. Eingesammelt wird nur beim manuellen Speichern (collectAllPanelUiStates),
// angewandt beim Aufbau eines Panels (scheduleUiStateRestore).
const UI_STATE_SKIP_INPUT_TYPES = ["password", "file", "button", "submit", "reset", "image", "hidden"];

function _uiPathOf(root, el) {
  const path = [];
  for (let node = el; node && node !== root; node = node.parentElement) {
    path.unshift(Array.prototype.indexOf.call(node.parentElement.children, node));
  }
  return path.join(".");
}

function _uiElementAt(root, key) {
  let node = root;
  if (!key) return node;
  for (const idx of key.split(".")) {
    node = node.children[Number(idx)];
    if (!node) return null;
  }
  return node;
}

function collectPanelUiState(panelEl) {
  const content = panelEl.querySelector(".panel__content");
  if (!content) return {};
  const scroll = {};
  const values = {};
  for (const el of [content, ...content.querySelectorAll("*")]) {
    const key = _uiPathOf(content, el);
    if (el.scrollTop || el.scrollLeft) scroll[key] = [el.scrollTop, el.scrollLeft];
    if (el.matches("input, select, textarea") && !UI_STATE_SKIP_INPUT_TYPES.includes(el.type) && !el.classList.contains("cmdline-input")) {
      values[key] = (el.type === "checkbox" || el.type === "radio") ? el.checked : el.value;
    }
  }
  return { scroll, values };
}

function applyPanelUiState(panelEl, uiState) {
  const content = panelEl.querySelector(".panel__content");
  if (!content || !uiState) return;
  for (const [key, value] of Object.entries(uiState.values || {})) {
    const el = _uiElementAt(content, key);
    if (!el || !el.matches("input, select, textarea")) continue;
    if (el.type === "checkbox" || el.type === "radio") el.checked = !!value;
    else el.value = value;
  }
  for (const [key, pos] of Object.entries(uiState.scroll || {})) {
    const el = _uiElementAt(content, key);
    if (el) { el.scrollTop = pos[0]; el.scrollLeft = pos[1]; }
  }
}

function scheduleUiStateRestore(panelEl, panel) {
  const uiState = panel.ui_state || {};
  if (!Object.keys(uiState).length) return;
  // Plugins bauen Teile ihres Inhalts erst im naechsten Frame auf.
  requestAnimationFrame(() => requestAnimationFrame(() => applyPanelUiState(panelEl, uiState)));
}

// Fuer das manuelle Speichern: Zustand aller Panels, keyed by Panel-ID.
function collectAllPanelUiStates() {
  const states = {};
  document.querySelectorAll(".workspace-panel[data-panel-id]").forEach((panelEl) => {
    states[panelEl.dataset.panelId] = collectPanelUiState(panelEl);
  });
  return states;
}

// ---- Panel-Farben: Standard = Design-Tokens ---------------------------------------------------
// Panels speichern ihre Farben im Layout. Der fruehere Standard (weisser Rahmen, #1a1a1a ...) und
// der aktuelle Standard gelten als "kein eigener Wert": dann greifen die Tokens aus theme.css.
// Nur bewusst abweichende Farben werden inline gesetzt und bleiben unveraendert erhalten.
const PANEL_COLOR_DEFAULTS = {
  border_color:            { legacy: "#ffffff", current: "#323237", prop: "borderColor" },
  background_color:        { legacy: "#1a1a1a", current: "#151517", prop: "backgroundColor" },
  text_color:              { legacy: "#e6e6e6", current: "#ededf0", prop: "color" },
  header_background_color: { legacy: "#141414", current: "#151517", prop: null },
};

function effectivePanelColors(source) {
  const result = {};
  for (const [field, def] of Object.entries(PANEL_COLOR_DEFAULTS)) {
    const value = String(source[field] || "").toLowerCase();
    const isDefault = !value || value === def.legacy || value === def.current;
    result[field] = { isDefault, value: isDefault ? def.current : source[field] };
  }
  return result;
}

/** Setzt Farben, Schatten und Akzent eines Panels (Aufbau UND Live-Vorschau der Eigenschaften). */
function applyPanelAppearance(el, source) {
  const colors = effectivePanelColors(source);
  for (const [field, def] of Object.entries(PANEL_COLOR_DEFAULTS)) {
    const target = field === "header_background_color" ? el.querySelector(".panel__header") : el;
    if (!target) continue;
    const prop = def.prop || "backgroundColor";
    if (colors[field].isDefault) target.style[prop] = "";
    else target.style[prop] = colors[field].value;
  }
  // Leer = Standard-Schatten (--shadow-1); "none" = bewusst ausgeschaltet
  el.style.boxShadow = source.drop_shadow === false ? "none" : "";
  // Eckenradius nur dieses Panels: ueberschreibt lokal --radius-lg (Rundungsgrad aus dem Theme).
  // "global" = nichts setzen, "round" = feste 12px, "square" = 0px.
  if (source.corner_style === "square") el.style.setProperty("--radius-lg", "0px");
  else if (source.corner_style === "round") el.style.setProperty("--radius-lg", "12px");
  else el.style.removeProperty("--radius-lg");
  // Eigener Akzent nur im Teilbaum dieses Panels: --accent-color ist ein aufgeloester Alias,
  // deshalb werden Alias, Token und Schriftfarbe auf Akzentflaechen gemeinsam gesetzt.
  if (source.use_custom_accent) {
    el.style.setProperty("--accent-color", source.accent_color);
    el.style.setProperty("--accent", source.accent_color);
    el.style.setProperty("--accent-ink", accentInk(source.accent_color));
  } else {
    el.style.removeProperty("--accent-color");
    el.style.removeProperty("--accent");
    el.style.removeProperty("--accent-ink");
  }
  return colors;
}

function buildPanelElement(panel) {
  const el = document.createElement("section");
  el.className = "panel workspace-panel";
  el.dataset.panelId = panel.id;
  el.dataset.panelType = panel.type;

  const header = document.createElement("div");
  header.className = "panel__header";
  const title = document.createElement("span");
  title.className = "panel__header-title";
  header.appendChild(title);
  el.appendChild(header);

  const content = document.createElement("div");
  content.className = "panel__content";
  content.appendChild(buildPanelContent(panel));
  el.appendChild(content);

  ["nw", "ne", "sw", "se"].forEach((corner) => {
    const handle = document.createElement("div");
    handle.className = `resize-handle resize-handle--${corner}`;
    handle.dataset.corner = corner;
    el.appendChild(handle);
  });

  // Must run AFTER .panel__header/.panel__header-title/.panel__content
  // exist above - it looks them up via querySelector to apply the title,
  // show_header and panel_scale fields onto them.
  applyPanelGeometry(el, panel);

  wirePanelInteractions(el);
  return el;
}

function applyPanelGeometry(el, panel) {
  el.style.left = `${panel.x}%`;
  el.style.top = `${panel.y}%`;
  el.style.width = `${panel.width}%`;
  el.style.height = `${panel.height}%`;
  el.style.zIndex = panel.z_index;
  const colors = applyPanelAppearance(el, panel);

  const header = el.querySelector(".panel__header");
  if (header) header.hidden = !panel.show_header;
  const titleEl = el.querySelector(".panel__header-title");
  if (titleEl) {
    const titleKey = PANEL_TITLE_KEYS[panel.type] || panel.type;
    if (panel.title) {
      titleEl.removeAttribute("data-i18n"); // custom title overrides the type's i18n default - must not get re-translated over
      titleEl.textContent = panel.title;
    } else {
      titleEl.dataset.i18n = titleKey;
      titleEl.textContent = i18n(titleKey);
    }
  }

  // Panel-specific scale, independent of the global --gui-scale (which
  // drives the root font-size and therefore every rem-sized element app-
  // wide). rem units always resolve against the ROOT font-size regardless
  // of ancestor overrides, so a local font-size change here wouldn't affect
  // them - `zoom` (Chromium/WebView2-only, which is exactly what this app
  // runs on) genuinely re-lays-out the content at the given factor instead,
  // scoped to just .panel__content so the panel's own frame/header/resize
  // handles stay at their normal, geometry-accurate size.
  const contentEl = el.querySelector(".panel__content");
  const panelScale = effectivePanelScale(panel);       // lokaler Wert dieses Geraets, sonst der Standard aus dem Layout
  if (contentEl) contentEl.style.zoom = panelScale;
  // Der Dialog "Panel-Eigenschaften" zeigt den wirksamen Wert (bei Standard: den aktuellen Token-Hex).
  el.dataset.borderColor = colors.border_color.value;
  el.dataset.backgroundColor = colors.background_color.value;
  el.dataset.textColor = colors.text_color.value;
  el.dataset.headerBackgroundColor = colors.header_background_color.value;
  // Alter Standard-Akzent (Neon-Gruen) im gespeicherten Layout wird angehoben - nur wenn kein eigener Akzent
  // aktiv ist; ein bewusst gesetzter Panel-Akzent bleibt unveraendert.
  el.dataset.accentColor = (!panel.use_custom_accent && String(panel.accent_color).toLowerCase() === "#00ff66")
    ? "#ffb000" : panel.accent_color;
  el.dataset.useCustomAccent = String(!!panel.use_custom_accent);
  el.dataset.title = panel.title || "";
  el.dataset.showHeader = String(panel.show_header !== false);
  el.dataset.panelScale = String(panelScale);
  el.dataset.dropShadow = String(panel.drop_shadow !== false);
  el.dataset.cornerStyle = panel.corner_style || "global";

  // module_config: store as JSON for Panel Properties to read back; if it
  // changed on an existing panel (e.g. new highlight_color or universe),
  // re-apply module-specific rendering without a full content rebuild.
  const newModuleConfigJson = JSON.stringify(panel.module_config || {});
  if (el.dataset.moduleConfig !== newModuleConfigJson) {
    el.dataset.moduleConfig = newModuleConfigJson;
    const mc = panel.module_config || {};
    const plugin = window.__panelPlugins.get(panel.type);
    if (plugin?.onModuleConfigChanged) plugin.onModuleConfigChanged(el, mc);
  }
}

function buildPanelContent(panel) {
  const plugin = window.__panelPlugins.get(panel.type);
  if (plugin?.buildContent) return plugin.buildContent(panel);
  const fallback = document.createElement("p");
  fallback.style.cssText = "padding:0.5rem;color:var(--secondary-text);font-size:0.8rem;";
  fallback.textContent = panel.type;
  return fallback;
}

// ---- Touch-Bruecke (iPad/Tablet) ---------------------------------------------------
// Ziehen von Fadern, Panels und Reglern ist ueber Maus-Events gebaut. Beginnt eine
// Beruehrung auf einer Flaeche mit `touch-action: none` (oder auf einem Panel im
// Edit-Modus), werden die Touch-Events als Maus-Events weitergegeben und der Browser
// scrollt/zoomt dabei nicht. Alles andere (Listen, Tabellen) scrollt normal.
(function installTouchBridge() {
  let active = null;
  const isDragSurface = (target) => {
    for (let node = target; node && node.nodeType === 1; node = node.parentElement) {
      if (node.matches("input, textarea, select")) return false;
//3D-AUS//       if (node.classList.contains("st3d__canvas")) return false;      // 3D-Buehne: Kamera und Gizmos arbeiten selbst mit Pointer-Ereignissen (auch Zwei-Finger-Gesten)
      if (node.classList.contains("sim3d__canvas")) return false;      // 3D-Simulation: die Kamera arbeitet selbst mit Pointer-Ereignissen (Ein-/Zwei-Finger-Gesten)
      if (getComputedStyle(node).touchAction === "none") return true;
      if (typeof isEditMode !== "undefined" && isEditMode && node.matches("[data-panel-id]")) return true;
    }
    return false;
  };
  const fire = (type, touch, target) => {
    (target && target.isConnected ? target : document).dispatchEvent(new MouseEvent(type, {
      bubbles: true, cancelable: true, view: window, button: 0,
      buttons: type === "mouseup" ? 0 : 1,
      clientX: touch.clientX, clientY: touch.clientY, screenX: touch.screenX, screenY: touch.screenY,
    }));
  };
  const find = (list) => active && Array.from(list).find((t) => t.identifier === active.id);

  document.addEventListener("touchstart", (event) => {
    if (active || event.touches.length !== 1 || !isDragSurface(event.target)) return;
    const touch = event.touches[0];
    active = { id: touch.identifier, target: event.target, x: touch.clientX, y: touch.clientY,
               at: Date.now(), moved: false };
    event.preventDefault();
    fire("mousedown", touch, event.target);
  }, { passive: false });
  document.addEventListener("touchmove", (event) => {
    const touch = find(event.touches);
    if (!touch) return;
    event.preventDefault();
    if (Math.hypot(touch.clientX - active.x, touch.clientY - active.y) > 12) active.moved = true;
    fire("mousemove", touch, document);
  }, { passive: false });
  const end = (event) => {
    const touch = find(event.changedTouches);
    if (!touch) return;
    fire("mouseup", touch, document);
    // preventDefault auf touchstart unterdrueckt Safaris eigenen click - ein kurzer Tipp
    // ohne Wischen wird deshalb hier als click nachgereicht (Buttons, Kacheln, Schalter).
    if (event.type === "touchend" && !active.moved && Date.now() - active.at < 700 && active.target.isConnected &&
        !(window.__longPress && window.__longPress.suppress)) {
      active.target.dispatchEvent(new MouseEvent("click", {
        bubbles: true, cancelable: true, view: window, button: 0,
        clientX: touch.clientX, clientY: touch.clientY,
      }));
    }
    active = null;
  };
  document.addEventListener("touchend", end);
  document.addEventListener("touchcancel", end);

  // Kein Pinch-Zoom und keine Browser-Geste ueber der Bedienoberflaeche
  ["gesturestart", "gesturechange", "gestureend"].forEach((name) =>
    document.addEventListener(name, (event) => event.preventDefault()));
  document.addEventListener("touchmove", (event) => {
    if (event.touches.length > 1) event.preventDefault();
  }, { passive: false });
})();

// ---- Long-Press (Touch) = Rechtsklick ---------------------------------------------------------------
// ~500 ms ruhig halten loest ein synthetisches `contextmenu` am Ziel aus: Kontextmenues von
// Kacheln, Cues, Presets und Panels sind damit auch auf dem iPad erreichbar. Der Finger-Hub
// (Pointerup/Click) danach wird verschluckt, damit nichts zusaetzlich ausgeloest wird.
(function installLongPress() {
  const HOLD_MS = 500;
  const SLOP = 10;
  const state = window.__longPress = { suppress: false };
  let timer = null;
  let press = null;

  const cancel = () => { clearTimeout(timer); timer = null; press = null; };

  document.addEventListener("pointerdown", (event) => {
    state.suppress = false;
    cancel();
    if (event.pointerType === "mouse" || !event.isPrimary) return;
    const target = event.target;
    if (target.closest && target.closest("input, textarea, select, [contenteditable='true']")) return;
    press = { x: event.clientX, y: event.clientY, target, id: event.pointerId };
    timer = setTimeout(() => {
      if (!press || !press.target.isConnected) { cancel(); return; }
      const { x, y, target: el } = press;
      cancel();
      state.suppress = true;
      if (navigator.vibrate) { try { navigator.vibrate(12); } catch (err) { /* egal */ } }
      const handled = !el.dispatchEvent(new MouseEvent("contextmenu", {
        bubbles: true, cancelable: true, view: window, button: 2, buttons: 2, clientX: x, clientY: y,
      }));
      // Hat nichts ein Kontextmenue geoeffnet, ersetzt der Long-Press den Hover-Tooltip: der title-Text
      // erscheint kurz als Hinweis (am iPad gibt es sonst keinen Weg, ihn zu lesen).
      const tip = !handled && el.closest && el.closest("[title]");
      if (tip && tip.getAttribute("title")) _showToast(tip.getAttribute("title"), "info", 3500, true);
    }, HOLD_MS);
  }, true);

  document.addEventListener("pointermove", (event) => {
    if (press && event.pointerId === press.id &&
        Math.hypot(event.clientX - press.x, event.clientY - press.y) > SLOP) cancel();
  }, true);
  ["pointerup", "pointercancel"].forEach((name) =>
    document.addEventListener(name, (event) => { if (press && event.pointerId === press.id) cancel(); }, true));

  // Der Click nach einem Long-Press waere sonst "Kontextmenue sofort wieder schliessen".
  document.addEventListener("click", (event) => {
    if (!state.suppress) return;
    state.suppress = false;
    event.stopImmediatePropagation();
    event.preventDefault();
  }, true);
})();

// ---- Layout-Wechsel per Wischgeste (geraetespezifisch, Standard: aus) ------------------------------------------
// Eine deutliche waagerechte Wischgeste ueber weite Teile des Bildschirms (Finger von rechts nach links = naechstes,
// von links nach rechts = vorheriges Layout, Reihenfolge wie Strg+1-9). Die Einstellung liegt NUR im localStorage dieses
// Geraets (nie auf dem Server).
// Erkennung ueber die RICHTUNG der ersten Bewegung, nicht ueber den Startort: Beginnt die Bewegung von Anfang an
// deutlich waagerecht (Winkel <= 25 Grad), zaehlt sie - auch ueber normalem Panel-Inhalt. Nicht zaehlt sie, wenn
//  - die Bewegung eher senkrecht ist (Scrollen bleibt Scrollen),
//  - sie auf einem Element mit eigener Drag-Funktion beginnt (Fader, Lasso/Kacheln, Wisch-Zahlenfeld, Eingabefelder,
//    Farbrad, Spaltenbreiten-Griff, Panel-Griffe ...),
//  - unter dem Finger ein waagerecht scrollbarer Bereich liegt, der in Wischrichtung noch Platz zum Scrollen hat
//    (an seiner Scroll-Grenze zaehlt die Geste dagegen),
//  - Bearbeitungsmodus, offenes Menue/Dialog.
const LAYOUT_SWIPE_KEY = "opencue.layoutSwipe";
const LAYOUT_SWIPE = {
  minFraction: 0.4, minPx: 220,   // Mindestweg: 40 % der Breite, mindestens 220 px
  decidePx: 12,                   // ab so viel Bewegung wird die Richtung bestimmt
  maxAngle: 25,                   // Grad zur Waagerechten
  maxVertical: 0.3, maxVerticalPx: 90,
  maxMs: 1500,
};

// Standard: an. Nur wer die Geste auf diesem Geraet ausdruecklich abgeschaltet hat ("0"), bekommt sie nicht.
function layoutSwipeEnabled() {
  try { return localStorage.getItem(LAYOUT_SWIPE_KEY) !== "0"; } catch (error) { return true; }
}
function setLayoutSwipeEnabled(on) {
  try { localStorage.setItem(LAYOUT_SWIPE_KEY, on ? "1" : "0"); } catch (error) { /* privates Fenster */ }
}

// Elemente, die eine Wischbewegung selbst brauchen (eigene Drag-Funktion) oder die Eingaben aufnehmen.
const SWIPE_OWN_DRAG = "input, select, textarea, canvas, [contenteditable], .vfader, .executor__track, .cue-td--delay, .fxprog-sheet, .fxprog-tile, " +
  ".fxprog-numfield-wrap, .cue-col-resizer, .resize-handle, .panel-fader__track, .menu, .modal-backdrop, .ctx-menu, " +
  ".toast, .layout-update-banner";

// Ist unter dem Finger etwas, das die Geste fuer sich braucht? (nur der Startpunkt; die Richtung entscheidet spaeter)
function _swipeBlockedAt(target) {
  for (let node = target; node && node.nodeType === 1 && node !== document.documentElement; node = node.parentElement) {
    // Checkboxen (z. B. die Auswahl-Spalte der Cue-Liste) haben keine eigene Wischfunktion
    if (node.matches(SWIPE_OWN_DRAG) && !node.matches("input[type='checkbox']")) return true;
    if (getComputedStyle(node).touchAction === "none") return true;
  }
  return false;
}

// Waagerecht scrollbare Vorfahren, die in Richtung `dx` noch scrollen wuerden (dann gehoert die Geste dem Scrollen).
function _swipeWouldScroll(target, dx) {
  for (let node = target; node && node.nodeType === 1 && node !== document.documentElement; node = node.parentElement) {
    const style = getComputedStyle(node);
    if (!/(auto|scroll)/.test(style.overflowX) || node.scrollWidth <= node.clientWidth + 1) continue;
    const atStart = node.scrollLeft <= 0;
    const atEnd = node.scrollLeft + node.clientWidth >= node.scrollWidth - 1;
    if (dx > 0 ? !atStart : !atEnd) return true;   // Finger nach rechts scrollt zurueck, nach links vorwaerts
  }
  return false;
}

(function installLayoutSwipe() {
  let start = null;
  document.addEventListener("touchstart", (event) => {
    start = null;
    if (!layoutSwipeEnabled() || event.touches.length !== 1) return;
    if (typeof isEditMode !== "undefined" && isEditMode) return;
    if (Modal._stack.length || document.querySelector(".menu--open")) return;
    if (_swipeBlockedAt(event.target)) return;
    const t = event.touches[0];
    start = { id: t.identifier, x: t.clientX, y: t.clientY, at: Date.now(), target: event.target, horizontal: false };
  }, { passive: true });
  document.addEventListener("touchmove", (event) => {
    if (!start) return;
    if (event.touches.length > 1) { start = null; return; }   // Zwei-Finger-Geste ist keine Wischgeste
    if (start.horizontal) return;
    const t = Array.from(event.touches).find((x) => x.identifier === start.id);
    if (!t) return;
    const dx = t.clientX - start.x;
    const dy = t.clientY - start.y;
    if (Math.hypot(dx, dy) < LAYOUT_SWIPE.decidePx) return;
    // Richtung der ersten Bewegung: deutlich waagerecht? Sonst gehoert die Bewegung dem Scrollen/dem Panel.
    const angle = Math.atan2(Math.abs(dy), Math.abs(dx)) * 180 / Math.PI;
    if (angle > LAYOUT_SWIPE.maxAngle || _swipeWouldScroll(start.target, dx)) { start = null; return; }
    start.horizontal = true;
  }, { passive: true });
  const finish = (event) => {
    if (!start) return;
    const t = Array.from(event.changedTouches).find((x) => x.identifier === start.id);
    const s = start;
    start = null;
    if (!t || event.type === "touchcancel" || !s.horizontal) return;
    const dx = t.clientX - s.x;
    const dy = t.clientY - s.y;
    const needed = Math.max(LAYOUT_SWIPE.minPx, window.innerWidth * LAYOUT_SWIPE.minFraction);
    if (Math.abs(dx) < needed) return;
    if (Math.abs(dy) > Math.min(Math.abs(dx) * LAYOUT_SWIPE.maxVertical, LAYOUT_SWIPE.maxVerticalPx)) return;
    if (Date.now() - s.at > LAYOUT_SWIPE.maxMs) return;
    _stepLayout(dx < 0 ? 1 : -1);
  };
  document.addEventListener("touchend", finish, { passive: true });
  document.addEventListener("touchcancel", finish, { passive: true });
})();

// ---- Doppeltipp (Touch) = Doppelklick -----------------------------------------------------------------
// iOS/Safari liefert fuer zwei schnelle Tipps kein verlaessliches `dblclick` (z.B. Cue-Zellen bearbeiten).
// Zwei Tipps kurz hintereinander am selben Ziel loesen deshalb ein synthetisches `dblclick` aus.
(function installDoubleTap() {
  const GAP_MS = 350;
  const SLOP = 24;
  let down = null;
  let last = null;
  document.addEventListener("pointerdown", (event) => {
    down = event.pointerType === "mouse" || !event.isPrimary ? null : { x: event.clientX, y: event.clientY };
  }, true);
  document.addEventListener("pointerup", (event) => {
    if (!down || event.pointerType === "mouse" || !event.isPrimary) return;
    const start = down;
    down = null;
    if (Math.hypot(event.clientX - start.x, event.clientY - start.y) > SLOP) { last = null; return; }   // Wischen
    if (window.__longPress && window.__longPress.suppress) { last = null; return; }
    const now = Date.now();
    if (last && now - last.at < GAP_MS && last.target === event.target &&
        Math.hypot(event.clientX - last.x, event.clientY - last.y) < SLOP) {
      last = null;
      event.target.dispatchEvent(new MouseEvent("dblclick", {
        bubbles: true, cancelable: true, view: window, clientX: event.clientX, clientY: event.clientY,
      }));
      return;
    }
    last = { at: now, x: event.clientX, y: event.clientY, target: event.target };
  }, true);
})();

// ---- iPad: Seite nach Dropdown/Tastatur zurueck auf Position 0 ---------------------------------------
// iOS verschiebt die Seite, wenn eine Auswahlliste oder die virtuelle Tastatur aufgeht, und
// stellt sie beim Schliessen nicht immer zurueck.
(function installViewportGuard() {
  if (!window.matchMedia || !window.matchMedia("(pointer: coarse)").matches) return;
  const reset = () => {
    window.scrollTo(0, 0);
    const root = document.scrollingElement || document.documentElement;
    root.scrollTop = 0;
    root.scrollLeft = 0;
    document.body.scrollTop = 0;
  };
  const resetSoon = () => { setTimeout(reset, 60); setTimeout(reset, 350); };   // 2. Mal nach der Tastatur-Animation
  document.addEventListener("focusout", (event) => {
    if (event.target.matches && event.target.matches("input, select, textarea")) resetSoon();
  }, true);
  document.addEventListener("change", (event) => {
    if (event.target.matches && event.target.matches("select")) resetSoon();
  }, true);
  if (window.visualViewport) window.visualViewport.addEventListener("resize", resetSoon);
  window.addEventListener("orientationchange", resetSoon);
})();

// ---- Remote-Geraete: Seite laesst sich unter keinen Umstaenden ziehen oder scrollen ----------------
// Nur echte Scroll-Container (Listen, Tabellen, Dialoge mit Inhalt) duerfen scrollen; ein Wisch
// ueber alles andere wird verworfen, damit iOS die Seite nicht verschiebt (Gummiband).
(function installRemoteScrollLock() {
  if (!document.documentElement.classList.contains("is-remote")) return;
  const canScroll = (start) => {
    for (let node = start; node && node !== document.body && node.nodeType === 1; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (/(auto|scroll)/.test(style.overflowY) && node.scrollHeight > node.clientHeight + 1) return true;
      if (/(auto|scroll)/.test(style.overflowX) && node.scrollWidth > node.clientWidth + 1) return true;
    }
    return false;
  };
  document.addEventListener("touchmove", (event) => {
    if (event.touches.length === 1 && !canScroll(event.target)) event.preventDefault();
  }, { passive: false });
})();

// ---- Panel drag & resize (Edit Mode only) ----------------------------------

function wirePanelInteractions(panelEl) {
  // Grabbable from anywhere on the box, not just the header - panel__content
  // is pointer-events:none while editing (see style.css), so a mousedown
  // over the content area already lands on panelEl itself here.
  panelEl.addEventListener("mousedown", (event) => {
    if (!isEditMode || event.button !== 0) return;
    event.preventDefault();
    const id = panelEl.dataset.panelId;
    if (event.shiftKey || event.ctrlKey || event.metaKey) {          // Mehrfachauswahl: hinzufuegen / wegnehmen, kein Ziehen
      togglePanelSelection(id);
      return;
    }
    if (!_selectedPanels.has(id)) selectPanels([id]);
    startDrag(panelEl, event);
  });

  panelEl.querySelectorAll(".resize-handle").forEach((handle) => {
    handle.addEventListener("mousedown", (event) => {
      if (!isEditMode || event.button !== 0) return;
      event.preventDefault();
      event.stopPropagation(); // don't also start a whole-panel drag
      startResize(panelEl, handle.dataset.corner, event);
    });
  });

  panelEl.addEventListener("contextmenu", (event) => {
    if (!isEditMode) return;
    event.preventDefault();
    showContextMenu(panelEl.dataset.panelId, event.clientX, event.clientY);
  });
}

document.addEventListener("mousedown", (event) => {
  if (!isEditMode || event.button !== 0 || !_selectedPanels.size) return;
  if (event.target && event.target.id === "app-root") clearPanelSelection();
});

// ---- Smart guides ------------------------------------------------------
// While dragging, the moved panel's edges/centers are compared (in pixels,
// converted from the stored percentages) against every other panel's
// edges/centers. A match within SNAP_TOLERANCE_PX snaps the dragged panel
// flush to it and draws a thin red line across that axis of the workspace.

const SNAP_TOLERANCE_PX = 8;

function getPanelEdgesPx(leftPx, topPx, widthPx, heightPx) {
  return {
    left: leftPx,
    right: leftPx + widthPx,
    centerX: leftPx + widthPx / 2,
    top: topPx,
    bottom: topPx + heightPx,
    centerY: topPx + heightPx / 2,
  };
}

function getOtherPanelEdgesPx(excludePanelEl, workspaceRect) {
  return Array.from(document.querySelectorAll(".workspace-panel"))
    .filter((el) => el !== excludePanelEl)
    .map((el) => {
      const leftPx = (parseFloat(el.style.left) / 100) * workspaceRect.width;
      const topPx = (parseFloat(el.style.top) / 100) * workspaceRect.height;
      const widthPx = (parseFloat(el.style.width) / 100) * workspaceRect.width;
      const heightPx = (parseFloat(el.style.height) / 100) * workspaceRect.height;
      return getPanelEdgesPx(leftPx, topPx, widthPx, heightPx);
    });
}

/** Finds the closest-within-tolerance match on each axis across every
 * dragged-edge x other-edge combination (edge-to-edge AND edge-to-center,
 * matching how design tools like Figma/Sketch snap). */
function findBestSnap(draggedEdges, otherPanelsEdges) {
  const xKeys = ["left", "centerX", "right"];
  const yKeys = ["top", "centerY", "bottom"];
  let bestX = null;
  let bestY = null;

  otherPanelsEdges.forEach((other) => {
    xKeys.forEach((draggedKey) => {
      xKeys.forEach((otherKey) => {
        const delta = other[otherKey] - draggedEdges[draggedKey];
        if (Math.abs(delta) <= SNAP_TOLERANCE_PX && (!bestX || Math.abs(delta) < Math.abs(bestX.delta))) {
          bestX = { delta, guidePos: other[otherKey] };
        }
      });
    });
    yKeys.forEach((draggedKey) => {
      yKeys.forEach((otherKey) => {
        const delta = other[otherKey] - draggedEdges[draggedKey];
        if (Math.abs(delta) <= SNAP_TOLERANCE_PX && (!bestY || Math.abs(delta) < Math.abs(bestY.delta))) {
          bestY = { delta, guidePos: other[otherKey] };
        }
      });
    });
  });

  return { bestX, bestY };
}

function createSmartGuideElements(workspace) {
  const guideX = document.createElement("div");
  guideX.className = "smart-guide smart-guide--vertical";
  guideX.hidden = true;
  const guideY = document.createElement("div");
  guideY.className = "smart-guide smart-guide--horizontal";
  guideY.hidden = true;
  workspace.appendChild(guideX);
  workspace.appendChild(guideY);
  return { guideX, guideY };
}

function startDrag(panelEl, startEvent) {
  const workspace = document.getElementById("app-root");
  const workspaceRect = workspace.getBoundingClientRect();
  const startX = startEvent.clientX;
  const startY = startEvent.clientY;
  const startLeft = parseFloat(panelEl.style.left);
  const startTop = parseFloat(panelEl.style.top);
  const widthPercent = parseFloat(panelEl.style.width);
  const heightPercent = parseFloat(panelEl.style.height);
  const widthPx = (widthPercent / 100) * workspaceRect.width;
  const heightPx = (heightPercent / 100) * workspaceRect.height;

  const { guideX, guideY } = createSmartGuideElements(workspace);

  const onMove = (event) => {
    const deltaXPercent = ((event.clientX - startX) / workspaceRect.width) * 100;
    const deltaYPercent = ((event.clientY - startY) / workspaceRect.height) * 100;
    let leftPercent = clamp(startLeft + deltaXPercent, 0, 100 - widthPercent);
    let topPercent = clamp(startTop + deltaYPercent, 0, 100 - heightPercent);

    let leftPx = (leftPercent / 100) * workspaceRect.width;
    let topPx = (topPercent / 100) * workspaceRect.height;
    const draggedEdges = getPanelEdgesPx(leftPx, topPx, widthPx, heightPx);
    const others = getOtherPanelEdgesPx(panelEl, workspaceRect);
    const { bestX, bestY } = findBestSnap(draggedEdges, others);

    if (bestX) {
      leftPx += bestX.delta;
      leftPercent = clamp((leftPx / workspaceRect.width) * 100, 0, 100 - widthPercent);
      guideX.style.left = `${bestX.guidePos}px`;
      guideX.hidden = false;
    } else {
      guideX.hidden = true;
    }

    if (bestY) {
      topPx += bestY.delta;
      topPercent = clamp((topPx / workspaceRect.height) * 100, 0, 100 - heightPercent);
      guideY.style.top = `${bestY.guidePos}px`;
      guideY.hidden = false;
    } else {
      guideY.hidden = true;
    }

    panelEl.style.left = `${leftPercent}%`;
    panelEl.style.top = `${topPercent}%`;
  };

  const onUp = () => {
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
    guideX.remove();
    guideY.remove();
    client.send("update_panel", {
      id: panelEl.dataset.panelId,
      x: parseFloat(panelEl.style.left),
      y: parseFloat(panelEl.style.top),
    });
  };

  document.addEventListener("mousemove", onMove);
  document.addEventListener("mouseup", onUp);
}

const DIMENSION_SNAP_TOLERANCE_PX = 10;

/** Snap search for ONE moving edge during a resize. Considers both:
 *  - edge alignment: the moving edge lines up with another panel's
 *    left/center/right (or top/center/bottom) - same idea as drag.
 *  - dimension match: the resulting width/height ends up EQUAL to another
 *    panel's width/height, regardless of where that panel actually is.
 * Both candidate kinds are expressed in the same unit (how far the moving
 * edge needs to shift), so the closer one simply wins.
 *
 * @param movingEdgePx current position of the edge being dragged
 * @param fixedEdgePx position of the opposite (stationary) edge
 * @param growsPositive true if moving the edge in the positive direction
 *   (right/down) grows the panel (e/s handles); false if it's the
 *   negative direction that grows it (n/w handles)
 * @param otherPanelsEdges edge sets of every other panel (px)
 * @param otherSizesPx that axis's size (width or height, px) of every
 *   other panel
 * @param edgeKeys which 3 edge keys to compare against (x or y axis)
 */
function findResizeSnap(movingEdgePx, fixedEdgePx, growsPositive, otherPanelsEdges, otherSizesPx, edgeKeys) {
  let best = null;

  otherPanelsEdges.forEach((other) => {
    edgeKeys.forEach((key) => {
      const delta = other[key] - movingEdgePx;
      if (Math.abs(delta) <= SNAP_TOLERANCE_PX && (!best || Math.abs(delta) < Math.abs(best.movingEdgeDelta))) {
        best = { movingEdgeDelta: delta, guidePos: other[key] };
      }
    });
  });

  const currentSize = growsPositive ? movingEdgePx - fixedEdgePx : fixedEdgePx - movingEdgePx;
  otherSizesPx.forEach((otherSize) => {
    const sizeDelta = otherSize - currentSize;
    if (Math.abs(sizeDelta) > DIMENSION_SNAP_TOLERANCE_PX) return;
    const movingEdgeDelta = growsPositive ? sizeDelta : -sizeDelta;
    if (!best || Math.abs(movingEdgeDelta) < Math.abs(best.movingEdgeDelta)) {
      best = { movingEdgeDelta, guidePos: movingEdgePx + movingEdgeDelta };
    }
  });

  return best;
}

function startResize(panelEl, corner, startEvent) {
  const workspace = document.getElementById("app-root");
  const workspaceRect = workspace.getBoundingClientRect();
  const startX = startEvent.clientX;
  const startY = startEvent.clientY;
  const startLeft = parseFloat(panelEl.style.left);
  const startTop = parseFloat(panelEl.style.top);
  const startWidth = parseFloat(panelEl.style.width);
  const startHeight = parseFloat(panelEl.style.height);
  const minSize = getPanelMinSize(panelEl);

  const { guideX, guideY } = createSmartGuideElements(workspace);

  const onMove = (event) => {
    const deltaX = ((event.clientX - startX) / workspaceRect.width) * 100;
    const deltaY = ((event.clientY - startY) / workspaceRect.height) * 100;

    let leftPercent = startLeft;
    let topPercent = startTop;
    let widthPercent = startWidth;
    let heightPercent = startHeight;

    if (corner.includes("e")) {
      widthPercent = clamp(startWidth + deltaX, minSize.w, 100 - startLeft);
    }
    if (corner.includes("w")) {
      widthPercent = clamp(startWidth - deltaX, minSize.w, startLeft + startWidth);
      leftPercent = startLeft + startWidth - widthPercent;
    }
    if (corner.includes("s")) {
      heightPercent = clamp(startHeight + deltaY, minSize.h, 100 - startTop);
    }
    if (corner.includes("n")) {
      heightPercent = clamp(startHeight - deltaY, minSize.h, startTop + startHeight);
      topPercent = startTop + startHeight - heightPercent;
    }

    // ---- Smart guides: snap whichever edge(s) this corner is moving ----
    let leftPx = (leftPercent / 100) * workspaceRect.width;
    let topPx = (topPercent / 100) * workspaceRect.height;
    let widthPx = (widthPercent / 100) * workspaceRect.width;
    let heightPx = (heightPercent / 100) * workspaceRect.height;

    const others = getOtherPanelEdgesPx(panelEl, workspaceRect);
    const otherWidthsPx = others.map((o) => o.right - o.left);
    const otherHeightsPx = others.map((o) => o.bottom - o.top);

    if (corner.includes("e")) {
      const snap = findResizeSnap(leftPx + widthPx, leftPx, true, others, otherWidthsPx, ["left", "centerX", "right"]);
      if (snap) {
        widthPx += snap.movingEdgeDelta;
        guideX.style.left = `${snap.guidePos}px`;
        guideX.hidden = false;
      } else {
        guideX.hidden = true;
      }
    } else if (corner.includes("w")) {
      const snap = findResizeSnap(leftPx, leftPx + widthPx, false, others, otherWidthsPx, ["left", "centerX", "right"]);
      if (snap) {
        leftPx += snap.movingEdgeDelta;
        widthPx -= snap.movingEdgeDelta;
        guideX.style.left = `${snap.guidePos}px`;
        guideX.hidden = false;
      } else {
        guideX.hidden = true;
      }
    } else {
      guideX.hidden = true;
    }

    if (corner.includes("s")) {
      const snap = findResizeSnap(topPx + heightPx, topPx, true, others, otherHeightsPx, ["top", "centerY", "bottom"]);
      if (snap) {
        heightPx += snap.movingEdgeDelta;
        guideY.style.top = `${snap.guidePos}px`;
        guideY.hidden = false;
      } else {
        guideY.hidden = true;
      }
    } else if (corner.includes("n")) {
      const snap = findResizeSnap(topPx, topPx + heightPx, false, others, otherHeightsPx, ["top", "centerY", "bottom"]);
      if (snap) {
        topPx += snap.movingEdgeDelta;
        heightPx -= snap.movingEdgeDelta;
        guideY.style.top = `${snap.guidePos}px`;
        guideY.hidden = false;
      } else {
        guideY.hidden = true;
      }
    } else {
      guideY.hidden = true;
    }

    // Back to percent, with a final safety clamp against the workspace/min-size bounds.
    leftPercent = clamp((leftPx / workspaceRect.width) * 100, 0, 100 - minSize.w);
    topPercent = clamp((topPx / workspaceRect.height) * 100, 0, 100 - minSize.h);
    widthPercent = clamp((widthPx / workspaceRect.width) * 100, minSize.w, 100 - leftPercent);
    heightPercent = clamp((heightPx / workspaceRect.height) * 100, minSize.h, 100 - topPercent);

    panelEl.style.left = `${leftPercent}%`;
    panelEl.style.top = `${topPercent}%`;
    panelEl.style.width = `${widthPercent}%`;
    panelEl.style.height = `${heightPercent}%`;
  };

  const onUp = () => {
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
    guideX.remove();
    guideY.remove();
    client.send("update_panel", {
      id: panelEl.dataset.panelId,
      x: parseFloat(panelEl.style.left),
      y: parseFloat(panelEl.style.top),
      width: parseFloat(panelEl.style.width),
      height: parseFloat(panelEl.style.height),
    });
  };

  document.addEventListener("mousemove", onMove);
  document.addEventListener("mouseup", onUp);
}

// ---- Kontextmenue: EINE Komponente fuer alle Panels -----------------------------------------------
// Rechtsklick bzw. Long-Press. Cue-Liste, Scheinwerferliste, Presets/Effekte und der Panel-Editor
// bauen ihr Menue nur noch als Eintragsliste und rufen ContextMenu.show() auf - Optik, Position,
// Schliessen (Klick daneben, Escape, Fensterwechsel) und Touch-Zielgroesse stehen an dieser Stelle
// (CSS: .ctx-menu in modern.css). Es ist immer nur ein Kontextmenue offen.
//   items: [{ label, onClick, danger }, { separator: true }]
const ContextMenu = (() => {
  let menu = null;
  let teardown = null;

  function hide() {
    if (teardown) { teardown(); teardown = null; }
    if (menu) { menu.remove(); menu = null; }
  }

  function show(x, y, items) {
    hide();
    menu = document.createElement("div");
    menu.className = "ctx-menu";
    menu.setAttribute("role", "menu");
    items.forEach((item) => {
      if (item.separator) {
        const line = document.createElement("div");
        line.className = "ctx-menu__separator";
        line.setAttribute("role", "separator");
        menu.appendChild(line);
        return;
      }
      const row = document.createElement("div");
      row.className = "ctx-menu__item" + (item.danger ? " ctx-menu__item--danger" : "");
      row.setAttribute("role", "menuitem");
      row.textContent = item.label;
      row.addEventListener("click", (event) => {
        event.stopPropagation();
        hide();
        if (item.onClick) item.onClick();
      });
      menu.appendChild(row);
    });
    menu.style.left = x + "px";
    menu.style.top = y + "px";
    document.body.appendChild(menu);

    // im sichtbaren Bereich halten
    const r = menu.getBoundingClientRect();
    if (r.right > window.innerWidth) menu.style.left = Math.max(0, x - r.width) + "px";
    if (r.bottom > window.innerHeight) menu.style.top = Math.max(0, y - r.height) + "px";

    const outside = (event) => { if (menu && !menu.contains(event.target)) hide(); };
    const onKey = (event) => { if (event.key === "Escape") hide(); };
    document.addEventListener("pointerdown", outside, true);
    document.addEventListener("keydown", onKey);
    window.addEventListener("blur", hide);
    window.addEventListener("resize", hide);
    window.addEventListener("wheel", hide, { passive: true });
    teardown = () => {
      document.removeEventListener("pointerdown", outside, true);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("blur", hide);
      window.removeEventListener("resize", hide);
      window.removeEventListener("wheel", hide);
    };
  }

  return { show, hide };
})();

// ---- Panel-Kontextmenue (Rechtsklick, nur im Bearbeitungsmodus) ----------------------------------

// ---- Panel-Auswahl, Duplizieren, Kopieren / Ausschneiden / Einfuegen (nur im Bearbeitungsmodus) --------------------
// Auswahl: Klick auf ein Panel markiert es (Umschalt-/Strg-Klick fuegt hinzu bzw. nimmt weg, Klick auf die freie Flaeche
// hebt sie auf). Die Zwischenablage liegt im Speicher dieser Seite und ueberlebt Layout-Wechsel; Einfuegen legt Kopien
// mit neuen IDs versetzt an die naechste freie Stelle (Server: StateManager.paste_panels).
const _selectedPanels = new Set();
let _panelClipboard = [];

function _syncPanelSelection() {
  document.querySelectorAll(".workspace-panel").forEach((el) => {
    el.classList.toggle("workspace-panel--selected", isEditMode && _selectedPanels.has(el.dataset.panelId));
  });
}

function selectPanels(ids) {
  _selectedPanels.clear();
  ids.forEach((id) => _selectedPanels.add(id));
  _syncPanelSelection();
}

function clearPanelSelection() {
  if (!_selectedPanels.size) return;
  _selectedPanels.clear();
  _syncPanelSelection();
}

function togglePanelSelection(id) {
  if (_selectedPanels.has(id)) _selectedPanels.delete(id); else _selectedPanels.add(id);
  _syncPanelSelection();
}

/** Panels, auf die sich eine Aktion am Panel `panelId` bezieht: die ganze Auswahl, wenn es dazugehoert, sonst nur dieses. */
function panelsForAction(panelId) {
  return _selectedPanels.has(panelId) ? [..._selectedPanels] : [panelId];
}

function duplicatePanels(ids) {
  if (ids.length) client.send("duplicate_panels", { ids });
}

function copySelectedPanels(cut) {
  const panels = (client.state && client.state.panels) || [];
  const chosen = panels.filter((panel) => _selectedPanels.has(panel.id));
  if (!chosen.length) return false;
  _panelClipboard = JSON.parse(JSON.stringify(chosen));
  _showToast(i18n(cut ? "PANELS_CUT" : "PANELS_COPIED").replace("{n}", String(chosen.length)), "info", 1800, true);
  if (cut) {
    client.send("delete_panels", { ids: chosen.map((panel) => panel.id) });
    clearPanelSelection();
  }
  return true;
}

function pasteCopiedPanels() {
  if (!_panelClipboard.length) return false;
  client.send("paste_panels", { panels: JSON.parse(JSON.stringify(_panelClipboard)) });
  return true;
}

function showContextMenu(panelId, x, y) {
  const send = (type, extra) => () => client.send(type, { id: panelId, ...(extra || {}) });
  if (!_selectedPanels.has(panelId)) selectPanels([panelId]);        // Rechtsklick auf ein nicht markiertes Panel waehlt es aus
  ContextMenu.show(x, y, [
    { label: i18n("PANEL_PROPERTIES_MENU"), onClick: () => openPanelPropertiesModal(panelId) },
    { label: i18n("DUPLICATE_PANEL"), onClick: () => duplicatePanels(panelsForAction(panelId)) },
    { separator: true },
    { label: i18n("BRING_TO_FRONT"), onClick: send("bring_panel_to_front") },
    { label: i18n("SEND_TO_BACK"), onClick: send("send_panel_to_back") },
    { label: i18n("MOVE_LAYER_UP"), onClick: send("move_panel_layer", { delta: 1 }) },
    { label: i18n("MOVE_LAYER_DOWN"), onClick: send("move_panel_layer", { delta: -1 }) },
    { separator: true },
    { label: i18n("DELETE_PANEL"), danger: true, onClick: send("delete_panel") },
  ]);
}

function hideContextMenu() {
  ContextMenu.hide();
}

// =============================================================================
// BUTTON PANEL PLUGIN// =============================================================================
// BUTTON PANEL PLUGIN
// =============================================================================

(function () {
  "use strict";
  window.__panelPlugins.register({
    type: "button",
    buildContent: function (panel) {
      var mc = panel.module_config || {};
      var wrap = document.createElement("div");
      wrap.className = "panel-btn__wrap";
      var btn = document.createElement("button");
      btn.className = "panel-btn";
      btn.type = "button";
      btn.textContent = mc.label || "";
      if (mc.font_size) btn.style.fontSize = mc.font_size + "rem";
      btn.addEventListener("click", function () {
        if (typeof isEditMode !== "undefined" && isEditMode) return;
        var panelEl = btn.closest(".workspace-panel");
        if (!panelEl) return;
        var config = {};
        try { config = JSON.parse(panelEl.dataset.moduleConfig || "{}"); } catch (e) {}
        var cmd = (config.command || "").trim();
        var logToHistory = config.log_to_history !== false;
        if (cmd) {
          window.__panelAPI.sendToServer("run_command", { command: cmd, log_to_history: logToHistory });
          var key = window.__commandKey(cmd);
          window.__panelAPI.sendToServer("command_value_updated", { pattern: key, kind: "button" });
          window.__pulseCommandButtons(key);
        }
      });
      wrap.appendChild(btn);
      return wrap;
    },
    onModuleConfigChanged: function (panelEl, config) {
      var btn = panelEl.querySelector(".panel-btn");
      if (!btn) return;
      var mc = config || {};
      btn.textContent = mc.label || "";
      btn.style.fontSize = mc.font_size ? mc.font_size + "rem" : "";
    },
    buildPropertiesPane: function (moduleConfig, api) {
      var mc = moduleConfig || {};
      var frag = document.createDocumentFragment();
      var cmdField = document.createElement("div"); cmdField.className = "modal__field";
      var cmdLabel = document.createElement("label"); cmdLabel.htmlFor = "panel-button-command";
      cmdLabel.textContent = api.i18n("BUTTON_SETTINGS_COMMAND");
      var cmdInput = document.createElement("input"); cmdInput.type = "text";
      cmdInput.id = "panel-button-command"; cmdInput.className = "modal__input";
      cmdInput.value = mc.command || ""; cmdInput.placeholder = "Fixture 1 At Full";
      cmdField.appendChild(cmdLabel); cmdField.appendChild(cmdInput); frag.appendChild(cmdField);
      var lblField = document.createElement("div"); lblField.className = "modal__field";
      var lblLabel = document.createElement("label"); lblLabel.htmlFor = "panel-button-label";
      lblLabel.textContent = api.i18n("BUTTON_SETTINGS_LABEL");
      var lblInput = document.createElement("input"); lblInput.type = "text";
      lblInput.id = "panel-button-label"; lblInput.className = "modal__input";
      lblInput.value = mc.label || "";
      lblField.appendChild(lblLabel); lblField.appendChild(lblInput); frag.appendChild(lblField);
      var fsField = document.createElement("div"); fsField.className = "modal__field";
      var fsLabel = document.createElement("label"); fsLabel.htmlFor = "panel-button-fontsize";
      fsLabel.textContent = api.i18n("BUTTON_SETTINGS_FONT_SIZE");
      var fsInput = document.createElement("input"); fsInput.type = "number";
      fsInput.id = "panel-button-fontsize"; fsInput.className = "modal__input";
      fsInput.value = mc.font_size || 1; fsInput.min = "0.5"; fsInput.max = "5"; fsInput.step = "0.1";
      fsField.appendChild(fsLabel); fsField.appendChild(fsInput); frag.appendChild(fsField);
      var logField = document.createElement("div"); logField.className = "modal__field modal__field--checkbox";
      var logTgl = makeToggleSwitch("panel-button-log-to-history", mc.log_to_history !== false);
      var logLabel = document.createElement("label"); logLabel.htmlFor = "panel-button-log-to-history";
      logLabel.textContent = api.i18n("BUTTON_LOG_TO_HISTORY");
      logField.appendChild(logTgl.label); logField.appendChild(logLabel); frag.appendChild(logField);
      return frag;
    },
    readPropertiesPane: function () {
      return {
        command: (document.getElementById("panel-button-command")?.value || "").trim(),
        label: document.getElementById("panel-button-label")?.value || "",
        font_size: parseFloat(document.getElementById("panel-button-fontsize")?.value || "1"),
        log_to_history: document.getElementById("panel-button-log-to-history")?.checked !== false,
      };
    },
  });
})();

// =============================================================================
// FADER PANEL PLUGIN
// =============================================================================

(function () {
  "use strict";
  var _faderThrottle = null;
  var FADER_THROTTLE_MS = 40;

  function _applyFaderVal(fill, track, thumb, value, min, max) {
    var range = max - min;
    var fraction = range === 0 ? 0 : Math.max(0, Math.min(1, (value - min) / range));
    var pct = Math.round(fraction * 100);
    fill.style.height = pct + "%";
    track.style.setProperty("--fv", pct + "%");
    thumb.textContent = Number.isInteger(value) ? String(value) : value.toFixed(1);
  }

  // ---- Befehls-Synchronisation -------------------------------------------------------
  // Fader und Buttons mit demselben Befehl ("Fixture 1 At {value}") bilden eine Gruppe:
  // bewegt man einen, folgen alle anderen - in jedem Panel und auf jedem Geraet.
  function _commandKey(template) {
    return String(template || "").trim().replace(/\s+/g, " ").toLowerCase();
  }
  window.__commandKey = _commandKey;
  window.__commandValues = window.__commandValues || {};

  function _faderPanels(key) {
    var result = [];
    document.querySelectorAll('.workspace-panel[data-panel-type="fader"]').forEach(function (panelEl) {
      var mc;
      try { mc = JSON.parse(panelEl.dataset.moduleConfig || "{}"); } catch (e) { return; }
      var k = _commandKey(mc.command);
      if (!k || k.indexOf("{value}") === -1 || (key && k !== key)) return;
      result.push({ panelEl: panelEl, mc: mc, key: k });
    });
    return result;
  }

  window.__syncCommandPanels = function (key) {
    _faderPanels(key).forEach(function (item) {
      var value = window.__commandValues[item.key];
      if (value == null) return;
      var track = item.panelEl.querySelector(".panel-fader__track");
      var fill = item.panelEl.querySelector(".vfader__fill");
      var thumb = item.panelEl.querySelector(".vfader__thumb");
      if (!track || !fill || !thumb || track._dragging) return;
      var min = parseFloat(item.mc.fader_min != null ? item.mc.fader_min : 0);
      var max = parseFloat(item.mc.fader_max != null ? item.mc.fader_max : 100);
      _applyFaderVal(fill, track, thumb, Math.max(min, Math.min(max, value)), min, max);
    });
  };

  window.__pulseCommandButtons = function (key) {
    document.querySelectorAll('.workspace-panel[data-panel-type="button"]').forEach(function (panelEl) {
      var mc;
      try { mc = JSON.parse(panelEl.dataset.moduleConfig || "{}"); } catch (e) { return; }
      if (_commandKey(mc.command) !== key) return;
      var btn = panelEl.querySelector(".panel-btn");
      if (!btn) return;
      btn.classList.add("panel-btn--pulse");
      setTimeout(function () { btn.classList.remove("panel-btn--pulse"); }, 220);
    });
  };

  // Eingehendes command_value_updated / command_values_state vom Server
  window.__applyCommandUpdate = function (payload) {
    if (!payload || !payload.pattern) return;
    if (payload.kind === "button") {
      window.__pulseCommandButtons(payload.pattern);
      return;
    }
    window.__commandValues[payload.pattern] = Number(payload.value);
    window.__syncCommandPanels(payload.pattern);
  };

  // Fader-Panels mit Master-Kommando ("Master {value}") zeigen immer den echten Grand
  // Master - egal, ob er an diesem Geraet, am Laptop/iPad oder per Command Line bewegt wurde.
  window.__mirrorGrandMaster = function () {
    var value = window.__grandMaster;
    if (value == null) return;
    document.querySelectorAll('.workspace-panel[data-panel-type="fader"]').forEach(function (panelEl) {
      var mc;
      try { mc = JSON.parse(panelEl.dataset.moduleConfig || "{}"); } catch (e) { return; }
      if (!/^\s*(grand\s*)?master\b/i.test(mc.command || "")) return;
      var track = panelEl.querySelector(".panel-fader__track");
      var fill = panelEl.querySelector(".vfader__fill");
      var thumb = panelEl.querySelector(".vfader__thumb");
      if (!track || !fill || !thumb || track._dragging) return;
      _applyFaderVal(fill, track, thumb, value,
        parseFloat(mc.fader_min != null ? mc.fader_min : 0), parseFloat(mc.fader_max != null ? mc.fader_max : 100));
    });
  };

  function _startFaderDrag(track, fill, thumb, startEvent) {
    var panelEl = track.closest(".workspace-panel");
    if (!panelEl) return;
    track._dragging = true;
    function getMc() { try { return JSON.parse(panelEl.dataset.moduleConfig || "{}"); } catch(e) { return {}; } }
    var mc = getMc();
    var min = parseFloat(mc.fader_min != null ? mc.fader_min : 0);
    var max = parseFloat(mc.fader_max != null ? mc.fader_max : 100);
    var logToHistory = mc.log_to_history === true;
    function valueFromEvent(event) {
      var rect = track.getBoundingClientRect();
      var fraction = 1 - Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height));
      return min + fraction * (max - min);
    }
    var lastSent = null;
    function sendCommand(value) {
      var template = getMc().command || "";
      if (!template.trim()) return;
      var rounded = Math.round(value);
      var cmd = template.replace(/\{value\}/gi, String(rounded));
      window.__panelAPI.sendToServer("run_command", { command: cmd, log_to_history: logToHistory });
      // Alle anderen Fader mit demselben Befehl (auch auf anderen Geraeten) ziehen mit.
      var key = _commandKey(template);
      window.__commandValues[key] = rounded;
      window.__panelAPI.sendToServer("command_value_updated", { pattern: key, value: rounded, kind: "fader" });
      window.__syncCommandPanels(key);
      lastSent = rounded;
    }
    function applyValue(value) {
      _applyFaderVal(fill, track, thumb, value, min, max);
      if (!_faderThrottle) {
        sendCommand(value);
        _faderThrottle = setTimeout(function () { _faderThrottle = null; }, FADER_THROTTLE_MS);
      }
    }
    applyValue(valueFromEvent(startEvent));
    var onMove = function (event) { applyValue(valueFromEvent(event)); };
    var onUp = function (event) {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      track._dragging = false;
      var finalValue = valueFromEvent(event);
      // Der Endwert darf nicht im Throttle verloren gehen.
      if (lastSent === null || Math.round(finalValue) !== lastSent) sendCommand(finalValue);
      var currentMc = getMc();
      currentMc.fader_value = finalValue;
      window.__panelAPI.sendToServer("update_panel", { id: panelEl.dataset.panelId, module_config: currentMc });
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }

  window.__panelPlugins.register({
    type: "fader",
    buildContent: function (panel) {
      var mc = panel.module_config || {};
      var wrap = document.createElement("div");
      wrap.className = "panel-fader__wrap";
      var labelEl = document.createElement("div");
      labelEl.className = "panel-fader__label";
      labelEl.textContent = mc.label || "";
      if (mc.show_label === false) labelEl.hidden = true;
      wrap.appendChild(labelEl);
      var track = document.createElement("div");
      track.className = "vfader__track panel-fader__track";
      var fill = document.createElement("div"); fill.className = "vfader__fill";
      var thumb = document.createElement("div"); thumb.className = "vfader__thumb";
      track.appendChild(fill); track.appendChild(thumb);
      wrap.appendChild(track);
      var min = parseFloat(mc.fader_min != null ? mc.fader_min : 0);
      var max = parseFloat(mc.fader_max != null ? mc.fader_max : 100);
      _applyFaderVal(fill, track, thumb, parseFloat(mc.fader_value || 0), min, max);
      track.addEventListener("mousedown", function (event) {
        if (typeof isEditMode !== "undefined" && isEditMode) return;
        if (event.button !== 0) return;
        event.preventDefault(); event.stopPropagation();
        _startFaderDrag(track, fill, thumb, event);
      });
      return wrap;
    },
    onModuleConfigChanged: function (panelEl, config) {
      var mc = config || {};
      var label = panelEl.querySelector(".panel-fader__label");
      if (label) { label.textContent = mc.label || ""; label.hidden = mc.show_label === false; }
      var fill = panelEl.querySelector(".vfader__fill");
      var track = panelEl.querySelector(".panel-fader__track");
      var thumb = panelEl.querySelector(".vfader__thumb");
      if (fill && track && thumb) {
        _applyFaderVal(fill, track, thumb, parseFloat(mc.fader_value || 0),
          parseFloat(mc.fader_min != null ? mc.fader_min : 0),
          parseFloat(mc.fader_max != null ? mc.fader_max : 100));
      }
    },
    buildPropertiesPane: function (moduleConfig, api) {
      var mc = moduleConfig || {};
      var frag = document.createDocumentFragment();
      var lblField = document.createElement("div"); lblField.className = "modal__field";
      var lblLabel = document.createElement("label"); lblLabel.htmlFor = "panel-fader-label";
      lblLabel.textContent = api.i18n("FADER_SETTINGS_LABEL");
      var lblInput = document.createElement("input"); lblInput.type = "text";
      lblInput.id = "panel-fader-label"; lblInput.className = "modal__input"; lblInput.value = mc.label || "";
      lblField.appendChild(lblLabel); lblField.appendChild(lblInput); frag.appendChild(lblField);
      var slField = document.createElement("div"); slField.className = "modal__field modal__field--checkbox";
      var slCb = document.createElement("input"); slCb.type = "checkbox";
      slCb.id = "panel-fader-show-label"; slCb.checked = mc.show_label !== false;
      var slLabel = document.createElement("label"); slLabel.htmlFor = "panel-fader-show-label";
      slLabel.textContent = api.i18n("FADER_SETTINGS_SHOW_LABEL");
      slField.appendChild(slCb); slField.appendChild(slLabel); frag.appendChild(slField);
      var cmdField = document.createElement("div"); cmdField.className = "modal__field";
      var cmdLabel = document.createElement("label"); cmdLabel.htmlFor = "panel-fader-command";
      cmdLabel.textContent = api.i18n("FADER_SETTINGS_COMMAND");
      var cmdInput = document.createElement("input"); cmdInput.type = "text";
      cmdInput.id = "panel-fader-command"; cmdInput.className = "modal__input";
      cmdInput.value = mc.command || ""; cmdInput.placeholder = "Fixture 1 At {value}";
      cmdField.appendChild(cmdLabel); cmdField.appendChild(cmdInput); frag.appendChild(cmdField);
      var minField = document.createElement("div"); minField.className = "modal__field";
      var minLabel = document.createElement("label"); minLabel.htmlFor = "panel-fader-min";
      minLabel.textContent = api.i18n("FADER_SETTINGS_MIN");
      var minInput = document.createElement("input"); minInput.type = "number";
      minInput.id = "panel-fader-min"; minInput.className = "modal__input";
      minInput.value = mc.fader_min != null ? mc.fader_min : 0; minInput.step = "1";
      minField.appendChild(minLabel); minField.appendChild(minInput); frag.appendChild(minField);
      var maxField = document.createElement("div"); maxField.className = "modal__field";
      var maxLabel = document.createElement("label"); maxLabel.htmlFor = "panel-fader-max";
      maxLabel.textContent = api.i18n("FADER_SETTINGS_MAX");
      var maxInput = document.createElement("input"); maxInput.type = "number";
      maxInput.id = "panel-fader-max"; maxInput.className = "modal__input";
      maxInput.value = mc.fader_max != null ? mc.fader_max : 100; maxInput.step = "1";
      maxField.appendChild(maxLabel); maxField.appendChild(maxInput); frag.appendChild(maxField);
      var logField = document.createElement("div"); logField.className = "modal__field modal__field--checkbox";
      var logTgl = makeToggleSwitch("panel-fader-log-to-history", mc.log_to_history === true);
      var logLabel = document.createElement("label"); logLabel.htmlFor = "panel-fader-log-to-history";
      logLabel.textContent = api.i18n("FADER_LOG_TO_HISTORY");
      logField.appendChild(logTgl.label); logField.appendChild(logLabel); frag.appendChild(logField);
      return frag;
    },
    readPropertiesPane: function () {
      return {
        label: document.getElementById("panel-fader-label")?.value || "",
        show_label: document.getElementById("panel-fader-show-label")?.checked !== false,
        command: (document.getElementById("panel-fader-command")?.value || "").trim(),
        fader_min: parseFloat(document.getElementById("panel-fader-min")?.value || "0"),
        fader_max: parseFloat(document.getElementById("panel-fader-max")?.value || "100"),
        log_to_history: document.getElementById("panel-fader-log-to-history")?.checked === true,
      };
    },
  });
})();


// ---- Panel Properties modal (right-click -> Panel Properties...) ----------
// Restructured analogous to the central Settings modal: a sidebar of
// categories (General / Appearance & Colors / Module Settings) - see
// setupCategorySidebar() below, shared by both modals. Every field
// live-previews straight onto the target panel; Cancel restores the exact
// pre-open snapshot, Save & Close sends everything as a single
// update_panel message.

const HEX_COLOR_PATTERN = /^#[0-9a-fA-F]{6}$/;

let panelPropertiesTargetId = null;
let panelPropertiesTargetType = null;
let panelPropertiesSnapshotBeforeOpen = null;
// module_config-Snapshot vor dem Oeffnen des Dialogs. Modul-spezifische
// Einstellungen (z.B. DMX-Monitor Fixture-Umrandung, Programmer Fader-
// Breiten) wenden sich ueber afterPropertiesPaneInserted als LIVE-PREVIEW
// direkt auf das Panel an - applyPanelPropertiesPreview kennt nur die
// generischen Chrome-Felder (Farbe/Titel/Groesse). Ohne diesen Snapshot
// wuerde "Abbrechen" Modul-Einstellungen NICHT zurücksetzen.
let panelPropertiesModuleConfigBeforeOpen = null;

function getPanelPropertiesSnapshot(panelId) {
  const panelEl = document.querySelector(`[data-panel-id="${panelId}"]`);
  if (!panelEl) return null;
  return {
    x: parseFloat(panelEl.style.left),
    y: parseFloat(panelEl.style.top),
    width: parseFloat(panelEl.style.width),
    height: parseFloat(panelEl.style.height),
    z_index: parseInt(panelEl.style.zIndex, 10) || 10,
    title: panelEl.dataset.title || "",
    show_header: panelEl.dataset.showHeader !== "false",
    panel_scale: parseFloat(panelEl.dataset.panelScale) || 1,
    border_color: panelEl.dataset.borderColor || PANEL_COLOR_DEFAULTS.border_color.current,
    background_color: panelEl.dataset.backgroundColor || PANEL_COLOR_DEFAULTS.background_color.current,
    text_color: panelEl.dataset.textColor || PANEL_COLOR_DEFAULTS.text_color.current,
    header_background_color: panelEl.dataset.headerBackgroundColor || PANEL_COLOR_DEFAULTS.header_background_color.current,
    accent_color: panelEl.dataset.accentColor || "#ffb000",
    use_custom_accent: panelEl.dataset.useCustomAccent === "true",
    drop_shadow: panelEl.dataset.dropShadow !== "false",
    corner_style: panelEl.dataset.cornerStyle || "global",
  };
}

function applyPanelPropertiesPreview(panelId, snapshot) {
  const panelEl = document.querySelector(`[data-panel-id="${panelId}"]`);
  if (!panelEl || !snapshot) return;
  panelEl.style.left = `${snapshot.x}%`;
  panelEl.style.top = `${snapshot.y}%`;
  panelEl.style.width = `${snapshot.width}%`;
  panelEl.style.height = `${snapshot.height}%`;
  panelEl.style.zIndex = snapshot.z_index;
  applyPanelAppearance(panelEl, snapshot);

  const header = panelEl.querySelector(".panel__header");
  if (header) header.hidden = !snapshot.show_header;
  const titleEl = panelEl.querySelector(".panel__header-title");
  if (titleEl) {
    const titleKey = PANEL_TITLE_KEYS[panelEl.dataset.panelType] || panelEl.dataset.panelType;
    if (snapshot.title) {
      titleEl.removeAttribute("data-i18n");
      titleEl.textContent = snapshot.title;
    } else {
      titleEl.dataset.i18n = titleKey;
      titleEl.textContent = i18n(titleKey);
    }
  }
  const contentEl = panelEl.querySelector(".panel__content");
  if (contentEl) contentEl.style.zoom = snapshot.panel_scale || 1;
}

/** Wires a sidebar-category modal (Settings / Panel Properties both use the
 * same .settings-modal__category / .settings-modal__pane markup) - scoped
 * to its own modal root so the two independent sidebars never cross-wire
 * each other despite sharing identical data-attributes/classes. */
function setupCategorySidebar(modalRootSelector) {
  const root = document.querySelector(modalRootSelector);
  if (!root) return;
  root.querySelectorAll("[data-settings-category]").forEach((button) => {
    button.addEventListener("click", () => {
      const category = button.dataset.settingsCategory;
      root.querySelectorAll("[data-settings-category]").forEach((btn) => {
        btn.classList.toggle("settings-modal__category--active", btn === button);
      });
      root.querySelectorAll("[data-settings-pane]").forEach((pane) => {
        pane.classList.toggle("settings-modal__pane--active", pane.dataset.settingsPane === category);
      });
    });
  });
}

/** Resets a sidebar-category modal back to its first category/pane -
 * called every time Panel Properties re-opens (for a possibly different
 * panel) so it doesn't stay stuck wherever the previous panel's edit left
 * it. */
function resetCategorySidebar(modalRootSelector, firstCategory) {
  const root = document.querySelector(modalRootSelector);
  if (!root) return;
  root.querySelectorAll("[data-settings-category]").forEach((btn) => {
    btn.classList.toggle("settings-modal__category--active", btn.dataset.settingsCategory === firstCategory);
  });
  root.querySelectorAll("[data-settings-pane]").forEach((pane) => {
    pane.classList.toggle("settings-modal__pane--active", pane.dataset.settingsPane === firstCategory);
  });
}

function openPanelPropertiesModal(panelId) {
  const snapshot = getPanelPropertiesSnapshot(panelId);
  if (!snapshot) return;

  const targetPanelEl = document.querySelector(`[data-panel-id="${panelId}"]`);
  panelPropertiesTargetId = panelId;
  panelPropertiesTargetType = targetPanelEl ? targetPanelEl.dataset.panelType : "";
  panelPropertiesSnapshotBeforeOpen = snapshot;

  document.getElementById("panel-properties-title").value = snapshot.title;
  document.getElementById("panel-properties-show-header").checked = snapshot.show_header;
  document.getElementById("panel-properties-scale").value = snapshot.panel_scale.toFixed(2);
  document.getElementById("panel-properties-scale-slider").value = snapshot.panel_scale;
  document.getElementById("panel-properties-color-swatch").value = snapshot.border_color;
  document.getElementById("panel-properties-color-hex").value = snapshot.border_color;
  document.getElementById("panel-properties-x").value = snapshot.x.toFixed(1);
  document.getElementById("panel-properties-y").value = snapshot.y.toFixed(1);
  document.getElementById("panel-properties-width").value = snapshot.width.toFixed(1);
  document.getElementById("panel-properties-height").value = snapshot.height.toFixed(1);
  document.getElementById("panel-properties-zindex").value = snapshot.z_index;
  document.getElementById("panel-properties-bg-swatch").value = snapshot.background_color;
  document.getElementById("panel-properties-bg-hex").value = snapshot.background_color;
  document.getElementById("panel-properties-text-swatch").value = snapshot.text_color;
  document.getElementById("panel-properties-text-hex").value = snapshot.text_color;
  document.getElementById("panel-properties-header-bg-swatch").value = snapshot.header_background_color;
  document.getElementById("panel-properties-header-bg-hex").value = snapshot.header_background_color;
  document.getElementById("panel-properties-accent-swatch").value = snapshot.accent_color;
  document.getElementById("panel-properties-accent-hex").value = snapshot.accent_color;
  document.getElementById("panel-properties-use-global-accent").checked = !snapshot.use_custom_accent;
  updateAccentColorRowDisabled();
  document.getElementById("panel-properties-drop-shadow").checked = snapshot.drop_shadow;
  document.getElementById("panel-properties-corners").value = snapshot.corner_style || "global";

  // Rebuild module settings pane — delegated entirely to the panel plugin
  const modulePane = document.querySelector('.modal--panel-properties [data-settings-pane="module"]');
  if (modulePane) {
    modulePane.innerHTML = "";
    let moduleConfig = {};
    const panelEl2 = document.querySelector(`[data-panel-id="${panelId}"]`);
    if (panelEl2) {
      try { moduleConfig = JSON.parse(panelEl2.dataset.moduleConfig || "{}"); } catch (e) { /* ignored */ }
    }
    panelPropertiesModuleConfigBeforeOpen = moduleConfig;
    const panelType = panelEl2 ? panelEl2.dataset.panelType : "";
    const plugin = window.__panelPlugins.get(panelType);
    if (plugin?.buildPropertiesPane) {
      modulePane.appendChild(plugin.buildPropertiesPane(moduleConfig, window.__panelAPI));
    } else {
      const placeholder = document.createElement("p");
      placeholder.className = "settings-modal__placeholder";
      placeholder.dataset.i18n = "PANEL_MODULE_SETTINGS_PLACEHOLDER";
      placeholder.textContent = i18n("PANEL_MODULE_SETTINGS_PLACEHOLDER");
      modulePane.appendChild(placeholder);
    }
    if (plugin?.afterPropertiesPaneInserted) {
      plugin.afterPropertiesPaneInserted(modulePane, panelId, window.__panelAPI);
    }
  }

  resetCategorySidebar(".modal--panel-properties", "general"); // always start on the first category
  Modal.open("panel-properties");
}

/** The custom accent swatch/hex row is inert while "Use Global Accent
 * Color" is checked - it has no effect in that state. */
function updateAccentColorRowDisabled() {
  const useGlobal = document.getElementById("panel-properties-use-global-accent").checked;
  const row = document.getElementById("panel-properties-accent-color-row");
  if (row) row.classList.toggle("modal__field--disabled", useGlobal);
  document.getElementById("panel-properties-accent-swatch").disabled = useGlobal;
  document.getElementById("panel-properties-accent-hex").disabled = useGlobal;
}

/** Wires a swatch + hex-text input pair to stay in sync with each other and
 * to call back with the resolved hex value on every valid change. Used for
 * all three color pairs (border/background/text) in this modal. */
function wireColorPair(swatchId, hexId, onChange) {
  const swatch = document.getElementById(swatchId);
  const hexInput = document.getElementById(hexId);
  if (!swatch || !hexInput) return;

  swatch.addEventListener("input", () => {
    hexInput.value = swatch.value;
    onChange(swatch.value);
  });

  hexInput.addEventListener("input", () => {
    const value = hexInput.value.trim();
    if (HEX_COLOR_PATTERN.test(value)) {
      swatch.value = value;
      onChange(value);
    }
  });
}

function setupPanelPropertiesModal() {
  const saveButton = document.getElementById("panel-properties-save");
  const cancelButton = document.querySelector('[data-modal-cancel="panel-properties"]');
  const closeButton = document.querySelector('[data-modal-close="panel-properties"]');
  const titleInput = document.getElementById("panel-properties-title");
  const showHeaderCheckbox = document.getElementById("panel-properties-show-header");
  const scaleInput = document.getElementById("panel-properties-scale");
  const scaleSlider = document.getElementById("panel-properties-scale-slider");
  const xInput = document.getElementById("panel-properties-x");
  const yInput = document.getElementById("panel-properties-y");
  const widthInput = document.getElementById("panel-properties-width");
  const heightInput = document.getElementById("panel-properties-height");
  const zIndexInput = document.getElementById("panel-properties-zindex");
  const useGlobalAccentCheckbox = document.getElementById("panel-properties-use-global-accent");
  const dropShadowCheckbox = document.getElementById("panel-properties-drop-shadow");
  const cornersSelect = document.getElementById("panel-properties-corners");
  if (!saveButton || !cancelButton || !closeButton) return;

  setupCategorySidebar(".modal--panel-properties");

  // Re-reads every field currently in the form and re-applies the whole
  // preview in one go - simpler and safer than trying to patch a single
  // style property per listener, since position/size fields interact.
  const previewCurrentFormState = () => {
    if (!panelPropertiesTargetId) return;
    applyPanelPropertiesPreview(panelPropertiesTargetId, {
      x: parseFloat(xInput.value),
      y: parseFloat(yInput.value),
      width: parseFloat(widthInput.value),
      height: parseFloat(heightInput.value),
      z_index: parseInt(zIndexInput.value, 10),
      title: titleInput.value.trim(),
      show_header: showHeaderCheckbox.checked,
      panel_scale: clamp(parseFloat(scaleInput.value) || 1, 0.5, 2.0),
      border_color: document.getElementById("panel-properties-color-hex").value,
      background_color: document.getElementById("panel-properties-bg-hex").value,
      text_color: document.getElementById("panel-properties-text-hex").value,
      header_background_color: document.getElementById("panel-properties-header-bg-hex").value,
      accent_color: document.getElementById("panel-properties-accent-hex").value,
      use_custom_accent: !useGlobalAccentCheckbox.checked,
      drop_shadow: dropShadowCheckbox.checked,
      corner_style: cornersSelect.value,
    });
  };

  wireColorPair("panel-properties-color-swatch", "panel-properties-color-hex", previewCurrentFormState);
  wireColorPair("panel-properties-bg-swatch", "panel-properties-bg-hex", previewCurrentFormState);
  wireColorPair("panel-properties-text-swatch", "panel-properties-text-hex", previewCurrentFormState);
  wireColorPair("panel-properties-header-bg-swatch", "panel-properties-header-bg-hex", previewCurrentFormState);
  wireColorPair("panel-properties-accent-swatch", "panel-properties-accent-hex", previewCurrentFormState);
  [titleInput, scaleInput, xInput, yInput, widthInput, heightInput, zIndexInput].forEach((input) => {
    input.addEventListener("input", previewCurrentFormState);
  });
  showHeaderCheckbox.addEventListener("change", previewCurrentFormState);

  // Scaling category: slider and number field mirror each other (same
  // pattern as the standalone GUI Scale modal's own slider/number pair).
  scaleSlider.addEventListener("input", () => {
    scaleInput.value = scaleSlider.value;
    previewCurrentFormState();
  });
  scaleInput.addEventListener("input", () => {
    const value = clamp(parseFloat(scaleInput.value) || 1, 0.5, 2.0);
    scaleSlider.value = value;
  });

  useGlobalAccentCheckbox.addEventListener("change", () => {
    updateAccentColorRowDisabled();
    previewCurrentFormState();
  });

  dropShadowCheckbox.addEventListener("change", previewCurrentFormState);
  cornersSelect.addEventListener("change", previewCurrentFormState);

  const cancelAndClose = () => {
    applyPanelPropertiesPreview(panelPropertiesTargetId, panelPropertiesSnapshotBeforeOpen);
    // Modul-spezifische Live-Preview-Aenderungen (z.B. DMX-Monitor Fixture-
    // Umrandung, Programmer Fader-Breiten) ebenfalls auf den Zustand vor
    // dem Oeffnen zuruecksetzen - applyPanelPropertiesPreview deckt nur die
    // generischen Chrome-Felder ab.
    const panelEl = document.querySelector(`[data-panel-id="${panelPropertiesTargetId}"]`);
    const plugin = window.__panelPlugins.get(panelPropertiesTargetType || "");
    if (panelEl && plugin?.onModuleConfigChanged) {
      plugin.onModuleConfigChanged(panelEl, panelPropertiesModuleConfigBeforeOpen || {});
    }
    Modal.close("panel-properties");
  };

  saveButton.addEventListener("click", () => {
    if (!panelPropertiesTargetId) return;

    const payload = { id: panelPropertiesTargetId };
    const borderHex = document.getElementById("panel-properties-color-hex").value.trim();
    const bgHex = document.getElementById("panel-properties-bg-hex").value.trim();
    const textHex = document.getElementById("panel-properties-text-hex").value.trim();
    const headerBgHex = document.getElementById("panel-properties-header-bg-hex").value.trim();
    const accentHex = document.getElementById("panel-properties-accent-hex").value.trim();
    if (HEX_COLOR_PATTERN.test(borderHex)) payload.border_color = borderHex;
    if (HEX_COLOR_PATTERN.test(bgHex)) payload.background_color = bgHex;
    if (HEX_COLOR_PATTERN.test(textHex)) payload.text_color = textHex;
    if (HEX_COLOR_PATTERN.test(headerBgHex)) payload.header_background_color = headerBgHex;
    if (HEX_COLOR_PATTERN.test(accentHex)) payload.accent_color = accentHex;
    payload.use_custom_accent = !useGlobalAccentCheckbox.checked;
    payload.title = titleInput.value.trim();
    payload.show_header = showHeaderCheckbox.checked;
    // Die Skalierung gehoert diesem Geraet: lokal (je Layout) speichern, nie ans Layout auf dem Server senden. Ein
    // unveraenderter Wert legt keinen eigenen Wert an (das Panel folgt weiter dem Standard des Layouts).
    const newPanelScale = clamp(parseFloat(scaleInput.value) || 1, 0.5, 2.0);
    if (panelPropertiesTargetId && Math.abs(newPanelScale - (panelPropertiesSnapshotBeforeOpen?.panel_scale || 1)) > 1e-9) {
      saveLocalPanelScale(panelPropertiesTargetId, newPanelScale);
    }
    {
      const scaledEl = document.querySelector(`[data-panel-id="${panelPropertiesTargetId}"]`);
      const scaledContent = scaledEl && scaledEl.querySelector(".panel__content");
      if (scaledContent) scaledContent.style.zoom = newPanelScale;
      if (scaledEl) scaledEl.dataset.panelScale = String(newPanelScale);
    }
    payload.drop_shadow = dropShadowCheckbox.checked;
    payload.corner_style = cornersSelect.value;

    const x = parseFloat(xInput.value);
    const y = parseFloat(yInput.value);
    const width = parseFloat(widthInput.value);
    const height = parseFloat(heightInput.value);
    const zIndex = parseInt(zIndexInput.value, 10);
    if (!Number.isNaN(x)) payload.x = x;
    if (!Number.isNaN(y)) payload.y = y;
    if (!Number.isNaN(width)) payload.width = width;
    if (!Number.isNaN(height)) payload.height = height;
    if (!Number.isNaN(zIndex)) payload.z_index = zIndex;

    const _savePlugin = window.__panelPlugins.get(panelPropertiesTargetType || "");
    const moduleConfig = _savePlugin?.readPropertiesPane?.() || null;
    if (moduleConfig) payload.module_config = moduleConfig;

    client.send("update_panel", payload);
    Modal.close("panel-properties");
  });

  cancelButton.addEventListener("click", cancelAndClose);
  closeButton.addEventListener("click", cancelAndClose);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && Modal.isOpen("panel-properties")) cancelAndClose();
  });
}

// ---- Add Panel modal (Edit -> Add Panel...) --------------------------------

const ADD_PANEL_CATEGORIES = [
  ["all", "ADDP_CAT_ALL", "grid"],
  ["programming", "ADDP_CAT_PROGRAMMING", "programmer"],
  ["cues", "ADDP_CAT_CUES", "cuelist"],
  ["input", "ADDP_CAT_INPUT", "button"],
  ["media", "ADDP_CAT_MEDIA", "film"],
//3D-AUS//   ["stage", "ADDP_CAT_STAGE", "stage"],
  ["other", "ADDP_CAT_OTHER", "panel"],
];
const addPanelState = { category: "all", query: "" };

/** Builds the Add Panel dialog (large landscape modal) from the PanelRegistry info sent in the state_snapshot: a category column,
 * a search field and one card per panel type (icon, name, short description). Called on every snapshot; the cards are only
 * built once per type list - filtering just hides them. */
function updateAddPanelModalList(panelTypes) {
  const list = document.getElementById("add-panel-type-list");
  const cats = document.getElementById("add-panel-cats");
  if (!list || !cats) return;
  const infos = panelTypes || [];
  const key = JSON.stringify(infos.map((info) => [info.type, info.category, info.icon]));
  if (list.dataset.built === key) return;
  list.dataset.built = key;
  list.innerHTML = "";
  cats.innerHTML = "";
  const present = new Set(infos.map((info) => info.category || "other"));
  ADD_PANEL_CATEGORIES.filter(([id]) => id === "all" || present.has(id)).forEach(([id, labelKey, icon]) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "addpanel__cat";
    btn.dataset.cat = id;
    btn.appendChild(Icons.svg(icon));
    const label = document.createElement("span");
    label.className = "addpanel__cat-label";
    label.dataset.i18n = labelKey;
    label.textContent = i18n(labelKey);
    const count = document.createElement("span");
    count.className = "addpanel__count";
    count.textContent = String(id === "all" ? infos.length : infos.filter((info) => (info.category || "other") === id).length);
    btn.append(label, count);
    cats.appendChild(btn);
  });
  ADD_PANEL_CATEGORIES.forEach(([id, labelKey]) => {
    const members = infos.filter((info) => (info.category || "other") === id);
    if (!members.length) return;
    const heading = document.createElement("li");
    heading.className = "addpanel__heading";
    heading.dataset.group = id;
    heading.dataset.i18n = labelKey;
    heading.textContent = i18n(labelKey);
    list.appendChild(heading);
    members.forEach((info) => {
      const li = document.createElement("li");
      li.className = "addpanel__item";
      li.dataset.cat = id;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "add-panel__type-item addpanel__card";
      btn.dataset.panelTypeItem = info.type;
      btn.appendChild(Icons.svg(info.icon || "panel", "addpanel__icon"));
      const text = document.createElement("span");
      text.className = "addpanel__text";
      const name = document.createElement("span");
      name.className = "add-panel__name";
      name.dataset.i18n = info.name;
      name.textContent = i18n(info.name);
      text.appendChild(name);
      if (info.description) {
        const desc = document.createElement("span");
        desc.className = "addpanel__desc";
        desc.dataset.i18n = info.description;
        desc.textContent = i18n(info.description);
        text.appendChild(desc);
      }
      btn.appendChild(text);
      li.appendChild(btn);
      list.appendChild(li);
    });
  });
  filterAddPanelList();
}

/** Shows the cards matching the chosen category and the search text (name + description, any language of the current UI). */
function filterAddPanelList() {
  const list = document.getElementById("add-panel-type-list");
  if (!list) return;
  const query = addPanelState.query.trim().toLowerCase();
  const shown = {};
  list.querySelectorAll(".addpanel__item").forEach((li) => {
    const inCategory = addPanelState.category === "all" || li.dataset.cat === addPanelState.category;
    const hay = li.textContent.toLowerCase();
    const match = inCategory && (!query || query.split(/\s+/).every((word) => hay.includes(word)));
    li.hidden = !match;
    if (match) shown[li.dataset.cat] = (shown[li.dataset.cat] || 0) + 1;
  });
  list.querySelectorAll(".addpanel__heading").forEach((h) => {
    h.hidden = !(shown[h.dataset.group] && addPanelState.category === "all");
  });
  document.querySelectorAll("#add-panel-cats .addpanel__cat").forEach((btn) => {
    btn.setAttribute("aria-pressed", btn.dataset.cat === addPanelState.category ? "true" : "false");
  });
  const none = document.getElementById("add-panel-none");
  if (none) none.hidden = Object.keys(shown).length > 0;
}

function setupAddPanelModal() {
  const list = document.getElementById("add-panel-type-list");
  const cats = document.getElementById("add-panel-cats");
  const search = document.getElementById("add-panel-search");
  const closeButton = document.querySelector('[data-modal-close="add-panel"]');
  const cancelButton = document.querySelector('[data-modal-cancel="add-panel"]');
  if (!list) return;

  // Delegated opener: [data-action="open-add-panel-modal"] in the Edit menu.
  document.addEventListener("click", (event) => {
    if (!event.target.closest('[data-action="open-add-panel-modal"]')) return;
    if (!isEditMode) return;
    addPanelState.category = "all";
    addPanelState.query = "";
    if (search) search.value = "";
    filterAddPanelList();
    Modal.open("add-panel");
    list.scrollTop = 0;
    // Touch devices: no automatic focus (it would pop up the on-screen keyboard over the cards)
    if (search && window.matchMedia("(hover: hover)").matches) setTimeout(() => search.focus(), 50);
  });

  const pick = (type) => {
    client.send("add_panel", { panel_type: type });
    Modal.close("add-panel");
  };

  // Panel type selected: create a new panel of that type then close.
  list.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-panel-type-item]");
    if (btn) pick(btn.dataset.panelTypeItem);
  });

  if (cats) {
    cats.addEventListener("click", (event) => {
      const btn = event.target.closest("[data-cat]");
      if (!btn) return;
      addPanelState.category = btn.dataset.cat;
      filterAddPanelList();
    });
  }

  if (search) {
    search.addEventListener("input", () => {
      addPanelState.query = search.value;
      filterAddPanelList();
    });
    search.addEventListener("keydown", (event) => {
      const first = list.querySelector(".addpanel__item:not([hidden]) [data-panel-type-item]");
      if (event.key === "Enter" && first) { event.preventDefault(); pick(first.dataset.panelTypeItem); }
      else if (event.key === "ArrowDown" && first) { event.preventDefault(); first.focus(); }
    });
  }

  // Arrow keys move between the cards (Tab works as well)
  list.addEventListener("keydown", (event) => {
    const keys = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 };
    if (!(event.key in keys)) return;
    const cards = [...list.querySelectorAll(".addpanel__item:not([hidden]) [data-panel-type-item]")];
    const at = cards.indexOf(document.activeElement);
    if (at < 0) return;
    event.preventDefault();
    const next = cards[at + keys[event.key]];
    if (next) next.focus();
    else if (event.key === "ArrowUp" && search) search.focus();
  });

  const close = () => Modal.close("add-panel");
  if (closeButton) closeButton.addEventListener("click", close);
  if (cancelButton) cancelButton.addEventListener("click", close);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && Modal.isOpen("add-panel")) close();
  });
}

// ---- Central Settings modal (toolbar gear icon) ----------------------------
// Sidebar category switching + snapshot-based Cancel/Save & Apply: GUI Scale
// and theme colors live-preview immediately while adjusting (and are
// reverted on Cancel, same pattern as the GUI Scale modal); the DMX/Network
// and Language fields have no meaningful "preview" and are simply staged in
// the form, read out and sent to the server only on Save & Apply. Every
// field still carries data-settings-field, so it stays in sync with the old
// workspace Settings panel (and any other connected client) via the
// existing updateSettingsFieldsInAllPanels() broadcast handling regardless
// of this modal's own open/closed state.


/** Panel Defaults (Settings -> Panel Defaults): plain persisted values read
 * by the server's add_panel() for newly created panels - NOT CSS theme
 * variables, so no live-preview mapping like SETTINGS_THEME_FIELDS above. */
const PANEL_DEFAULTS_COLOR_FIELDS = [
  { key: "background_color", swatch: "settings-panel-defaults-bg-swatch", hex: "settings-panel-defaults-bg-hex" },
  { key: "text_color", swatch: "settings-panel-defaults-text-swatch", hex: "settings-panel-defaults-text-hex" },
  { key: "header_background_color", swatch: "settings-panel-defaults-header-bg-swatch", hex: "settings-panel-defaults-header-bg-hex" },
];

const SETTINGS_GUI_SCALE_MIN = 0.5;
const SETTINGS_GUI_SCALE_MAX = 2.0;


// ---- Einstellungen -> Farben: Theme-Editor und Profile ---------------------------------------------
const ThemeUI = (() => {
  const GROUPS = [
    { title: "THEME_GROUP_SURFACES", tokens: [
      ["bg", "THEME_TOKEN_BG"], ["toolbar-bg", "THEME_TOKEN_TOOLBAR_BG"], ["menu-bg", "THEME_TOKEN_MENU_BG"],
      ["panel-bg", "THEME_TOKEN_PANEL_BG"], ["panel-border", "THEME_TOKEN_PANEL_BORDER"],
      ["panel-header-bg", "THEME_TOKEN_PANEL_HEADER_BG"], ["surface-1", "THEME_TOKEN_SURFACE_1"],
      ["surface-2", "THEME_TOKEN_SURFACE_2"], ["surface-3", "THEME_TOKEN_SURFACE_3"]] },
    { title: "THEME_GROUP_TEXT", tokens: [
      ["text-1", "THEME_TOKEN_TEXT_1"], ["text-2", "THEME_TOKEN_TEXT_2"], ["text-3", "THEME_TOKEN_TEXT_3"]] },
    { title: "THEME_GROUP_BORDERS", tokens: [
      ["border", "THEME_TOKEN_BORDER"], ["border-strong", "THEME_TOKEN_BORDER_STRONG"]] },
    { title: "THEME_GROUP_ACCENT", tokens: [["accent", "THEME_TOKEN_ACCENT"]], presets: true },
    { title: "THEME_GROUP_STATUS", hint: "THEME_STATUS_HINT", tokens: [
      ["ok", "THEME_TOKEN_OK"], ["warn", "THEME_TOKEN_WARN"], ["error", "THEME_TOKEN_ERROR"], ["live", "THEME_TOKEN_LIVE"]] },
  ];
  const BUILTIN = [["dark", "THEME_BASE_DARK"], ["light", "THEME_BASE_LIGHT"]];

  let draft = normalizeTheme(null);
  let profiles = {};
  let built = false;
  const rows = {};
  const refs = {};
  let armedDelete = null;
  let armedTimer = null;

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  };
  const tr = (key) => i18n(key);
  const clone = (theme) => normalizeTheme(JSON.parse(JSON.stringify(theme || {})));
  const isCustom = () => Object.keys(draft.tokens).length > 0 || draft.radius !== THEME_DEFAULT_RADIUS;

  function effectiveHex(token) {
    let value = getComputedStyle(document.documentElement).getPropertyValue("--" + token).trim().toLowerCase();
    if (/^#[0-9a-f]{3}$/.test(value)) value = "#" + value.slice(1).split("").map((c) => c + c).join("");
    return /^#[0-9a-f]{6}$/.test(value) ? value : "#000000";
  }

  function label(node, key) {
    node.dataset.i18n = key;
    node.textContent = tr(key);
    return node;
  }

  function changed() {
    applyTheme(draft);
    refresh();
  }

  function onColor(token, value) {
    draft.tokens[token] = value.toLowerCase();
    applyTheme(draft);
    refresh(token);
  }

  function setBase(base) {
    draft = { base, tokens: {}, radius: THEME_DEFAULT_RADIUS };   // Basis wechseln = Ausgangspunkt neu
    changed();
  }

  function refresh(exceptToken) {
    if (!built) return;
    const custom = isCustom();
    refs.segDark.classList.toggle("segmented__btn--active", !custom && draft.base === "dark");
    refs.segLight.classList.toggle("segmented__btn--active", !custom && draft.base === "light");
    refs.segCustom.classList.toggle("segmented__btn--active", custom);
    refs.baseNote.textContent = custom
      ? tr("THEME_BASE_FROM").replace("{base}", tr(draft.base === "light" ? "THEME_BASE_LIGHT" : "THEME_BASE_DARK"))
      : "";
    for (const [token, row] of Object.entries(rows)) {
      if (token !== exceptToken && document.activeElement !== row.hex) {
        const value = effectiveHex(token);
        row.swatch.value = value;
        row.hex.value = value;
      }
      row.reset.hidden = !(token in draft.tokens);
    }
    refs.radius.value = draft.radius;
    refs.radiusValue.textContent = draft.radius + " px";
    document.querySelectorAll("#settings-theme-root .accent-preset").forEach((chip) => {
      chip.classList.toggle("accent-preset--active", chip.dataset.accent === effectiveHex("accent"));
    });
  }

  function colorRow(token, labelKey) {
    const row = el("div", "settings-field theme-row");
    row.appendChild(label(el("label"), labelKey));
    const box = el("div", "modal__field");
    const swatch = el("input", "color-swatch-input");
    swatch.type = "color";
    const hex = el("input", "color-hex-input");
    hex.type = "text";
    hex.maxLength = 7;
    const reset = el("button", "btn btn--ghost theme-row__reset", "↺");
    reset.type = "button";
    reset.dataset.i18nTip = "THEME_TOKEN_RESET";
    reset.title = tr("THEME_TOKEN_RESET");
    reset.hidden = true;
    box.append(swatch, hex, reset);
    row.appendChild(box);
    swatch.addEventListener("input", () => { hex.value = swatch.value; onColor(token, swatch.value); });
    hex.addEventListener("input", () => {
      const value = hex.value.trim();
      if (HEX_COLOR_PATTERN.test(value)) { swatch.value = value; onColor(token, value); }
    });
    reset.addEventListener("click", () => { delete draft.tokens[token]; changed(); });
    rows[token] = { swatch, hex, reset };
    return row;
  }

  function profileButton(textKey, onClick, extraClass) {
    const button = el("button", "btn btn--ghost theme-profile__btn" + (extraClass ? " " + extraClass : ""));
    button.type = "button";
    label(button, textKey);
    button.addEventListener("click", onClick);
    return button;
  }

  function applyProfile(theme) {
    draft = clone(theme);
    changed();
    client.send("set_theme", draft);   // Klick = sofort anwenden und speichern
  }

  function renderProfiles() {
    if (!built) return;
    const list = refs.profileList;
    list.textContent = "";
    BUILTIN.forEach(([base, key]) => {
      const item = el("div", "theme-profile theme-profile--builtin");
      const name = el("button", "theme-profile__name");
      name.type = "button";
      label(name, key);
      name.addEventListener("click", () => applyProfile({ base, tokens: {}, radius: THEME_DEFAULT_RADIUS }));
      const actions = el("div", "theme-profile__actions");
      actions.appendChild(profileButton("THEME_PROFILE_DUPLICATE", () => {
        const copyName = `${tr(key)} 2`;
        client.send("save_theme_profile", { name: copyName, theme: { base, tokens: {}, radius: THEME_DEFAULT_RADIUS } });
      }));
      item.append(name, el("span", "theme-profile__tag", tr("THEME_PROFILE_BUILTIN")), actions);
      list.appendChild(item);
    });
    const names = Object.keys(profiles).sort((a, b) => a.localeCompare(b));
    if (!names.length) list.appendChild(el("div", "theme-profile-empty", tr("THEME_PROFILE_EMPTY")));
    names.forEach((profileName) => {
      const item = el("div", "theme-profile");
      const name = el("button", "theme-profile__name", profileName);
      name.type = "button";
      name.addEventListener("click", () => applyProfile(profiles[profileName]));
      const actions = el("div", "theme-profile__actions");
      actions.appendChild(profileButton("THEME_PROFILE_DUPLICATE", () => client.send("duplicate_theme_profile", { name: profileName })));
      actions.appendChild(profileButton("THEME_PROFILE_RENAME", () => {
        const input = el("input", "settings__text-input theme-profile__rename");
        input.type = "text";
        input.maxLength = 60;
        input.value = profileName;
        item.replaceChild(input, name);
        input.focus();
        input.select();
        const commit = () => {
          const next = input.value.trim();
          if (next && next !== profileName) client.send("rename_theme_profile", { name: profileName, new_name: next });
          else renderProfiles();
        };
        input.addEventListener("keydown", (event) => {
          if (event.key === "Enter") commit();
          if (event.key === "Escape") renderProfiles();
        });
        input.addEventListener("blur", commit);
      }));
      const del = profileButton("THEME_PROFILE_DELETE", () => {
        if (armedDelete !== profileName) {   // zweistufig: erst scharf schalten, dann loeschen
          armedDelete = profileName;
          del.textContent = tr("THEME_PROFILE_DELETE_CONFIRM");
          del.classList.add("btn--danger");
          clearTimeout(armedTimer);
          armedTimer = setTimeout(() => { armedDelete = null; renderProfiles(); }, 3000);
          return;
        }
        armedDelete = null;
        clearTimeout(armedTimer);
        client.send("delete_theme_profile", { name: profileName });
      });
      actions.appendChild(del);
      item.append(name, actions);
      list.appendChild(item);
    });
  }

  function build() {
    const root = document.getElementById("settings-theme-root");
    if (!root || built) return;
    root.textContent = "";

    // Basis
    const baseSection = el("div", "settings-section");
    baseSection.appendChild(label(el("div", "settings-section__title"), "THEME_BASE_LABEL"));
    const seg = el("div", "segmented");
    refs.segDark = el("button", "segmented__btn"); refs.segLight = el("button", "segmented__btn");
    refs.segCustom = el("button", "segmented__btn");
    [refs.segDark, refs.segLight, refs.segCustom].forEach((b) => { b.type = "button"; });
    label(refs.segDark, "THEME_BASE_DARK"); label(refs.segLight, "THEME_BASE_LIGHT"); label(refs.segCustom, "THEME_BASE_CUSTOM");
    refs.segDark.addEventListener("click", () => setBase("dark"));
    refs.segLight.addEventListener("click", () => setBase("light"));
    refs.segCustom.addEventListener("click", () => {});   // "Eigenes" entsteht durch Aenderungen, nicht per Klick
    refs.segCustom.classList.add("segmented__btn--indicator");
    seg.append(refs.segDark, refs.segLight, refs.segCustom);
    refs.baseNote = el("div", "theme-hint");
    baseSection.append(seg, refs.baseNote);
    root.appendChild(baseSection);

    // Farben
    GROUPS.forEach((group) => {
      const section = el("div", "settings-section");
      section.appendChild(label(el("div", "settings-section__title"), group.title));
      group.tokens.forEach(([token, key]) => section.appendChild(colorRow(token, key)));
      if (group.presets) {
        const field = el("div", "settings-field");
        field.appendChild(label(el("label"), "THEME_PRESETS"));
        const box = el("div", "accent-presets");
        ACCENT_PRESETS.forEach((preset) => {
          const chip = el("button", "accent-preset");
          chip.type = "button";
          chip.dataset.accent = preset.accent;
          chip.style.setProperty("--preset-color", preset.accent);
          chip.innerHTML = '<span class="accent-preset__dot"></span><span></span>';
          chip.lastChild.dataset.i18n = preset.nameKey;
          chip.lastChild.textContent = tr(preset.nameKey);
          chip.addEventListener("click", () => onColor("accent", preset.accent));
          box.appendChild(chip);
        });
        field.appendChild(box);
        section.appendChild(field);
      }
      if (group.hint) section.appendChild(label(el("div", "theme-hint"), group.hint));
      root.appendChild(section);
    });

    // Form
    const shape = el("div", "settings-section");
    shape.appendChild(label(el("div", "settings-section__title"), "THEME_GROUP_SHAPE"));
    const radiusRow = el("div", "settings-field");
    radiusRow.appendChild(label(el("label"), "THEME_RADIUS"));
    const radiusBox = el("div", "modal__field");
    refs.radius = el("input");
    refs.radius.type = "range";
    refs.radius.min = "0";
    refs.radius.max = String(THEME_MAX_RADIUS);
    refs.radius.step = "1";
    refs.radiusValue = el("span", "theme-radius-value");
    refs.radius.addEventListener("input", () => { draft.radius = parseInt(refs.radius.value, 10); changed(); });
    radiusBox.append(refs.radius, refs.radiusValue);
    radiusRow.appendChild(radiusBox);
    shape.appendChild(radiusRow);
    root.appendChild(shape);

    // Profile
    const prof = el("div", "settings-section");
    prof.appendChild(label(el("div", "settings-section__title"), "THEME_GROUP_PROFILES"));
    const saveRow = el("div", "theme-save-row");
    refs.profileName = el("input", "settings__text-input");
    refs.profileName.type = "text";
    refs.profileName.maxLength = 60;
    refs.profileName.dataset.i18nPlaceholder = "THEME_PROFILE_NAME_PLACEHOLDER";
    refs.profileName.placeholder = tr("THEME_PROFILE_NAME_PLACEHOLDER");
    const saveBtn = el("button", "btn btn--primary");
    saveBtn.type = "button";
    label(saveBtn, "THEME_PROFILE_SAVE");
    const saveProfile = () => {
      const name = refs.profileName.value.trim();
      if (!name) { _showToast(tr("THEME_PROFILE_NAME_REQUIRED"), "warn", 3000); return; }
      client.send("save_theme_profile", { name, theme: draft });
      _showToast(tr("THEME_PROFILE_SAVED").replace("{name}", name), "info", 2500);
      refs.profileName.value = "";
    };
    saveBtn.addEventListener("click", saveProfile);
    refs.profileName.addEventListener("keydown", (event) => { if (event.key === "Enter") saveProfile(); });
    saveRow.append(refs.profileName, saveBtn);
    refs.profileList = el("div", "theme-profile-list");
    prof.append(saveRow, refs.profileList);
    root.appendChild(prof);

    // Export / Import als JSON (Textfeld statt Datei-Dialog: geht in jedem Browser und auf dem iPad)
    const transfer = el("div", "settings-section");
    transfer.appendChild(label(el("div", "settings-section__title"), "THEME_GROUP_TRANSFER"));
    refs.transfer = el("textarea", "theme-transfer");
    refs.transfer.rows = 4;
    refs.transfer.spellcheck = false;
    refs.transfer.dataset.i18nPlaceholder = "THEME_TRANSFER_PLACEHOLDER";
    refs.transfer.placeholder = tr("THEME_TRANSFER_PLACEHOLDER");
    const buttons = el("div", "theme-transfer-buttons");
    const exportBtn = el("button", "btn"); exportBtn.type = "button"; label(exportBtn, "THEME_EXPORT");
    const importBtn = el("button", "btn"); importBtn.type = "button"; label(importBtn, "THEME_IMPORT");
    exportBtn.addEventListener("click", () => {
      refs.transfer.value = JSON.stringify({ opencue_theme: 1, theme: draft }, null, 2);
      refs.transfer.select();
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(refs.transfer.value).then(
          () => _showToast(tr("THEME_EXPORT_COPIED"), "info", 2500), () => {});
      }
    });
    importBtn.addEventListener("click", () => {
      try {
        const parsed = JSON.parse(refs.transfer.value);
        const source = parsed && parsed.theme && typeof parsed.theme === "object" ? parsed.theme : parsed;
        if (!source || typeof source !== "object" || !("tokens" in source || "base" in source)) throw new Error("kein Theme");
        draft = clone(source);
        changed();
        _showToast(tr("THEME_IMPORT_OK"), "info", 4000);
      } catch (error) {
        _showToast(tr("THEME_IMPORT_INVALID"), "error", 4000);
      }
    });
    buttons.append(exportBtn, importBtn);
    transfer.append(refs.transfer, buttons);
    root.appendChild(transfer);

    built = true;
    renderProfiles();
  }

  return {
    /** Dialog oeffnet: Entwurf = aktuell gueltiges Theme. */
    open(theme) { draft = clone(theme); build(); refresh(); },
    /** Das bestaetigte Theme hat sich (auch von anderer Seite) geaendert. */
    sync(theme) { draft = clone(theme); refresh(); },
    setProfiles(next) { profiles = next || {}; renderProfiles(); },
    getDraft() { return clone(draft); },
    /** Sprache gewechselt: dynamisch erzeugte Texte (Basis-Hinweis, Profil-Liste) neu setzen. */
    relabel() { refresh(); renderProfiles(); },
  };
})();

function setupSettingsModal() {
  const closeButton = document.querySelector('[data-modal-close="settings"]');
  const cancelButton = document.querySelector('[data-modal-cancel="settings"]');
  const saveButton = document.getElementById("settings-save");
  const languageSelect = document.getElementById("settings-language");
  const guiScaleNumber = document.getElementById("settings-gui-scale-number");
  if (!closeButton || !cancelButton || !saveButton || !guiScaleNumber) return;

  let snapshotBeforeOpen = null;

  setupCategorySidebar(".modal--settings");

  // Geraeteeinstellung (nur localStorage dieses Geraets): wirkt sofort, ohne "Speichern & Anwenden"
  document.getElementById("settings-layout-swipe")?.addEventListener("change", (event) => {
    setLayoutSwipeEnabled(event.target.checked);
  });
  // Update-Pruefung beim Start (gilt fuer das Programm, nicht nur fuer dieses Geraet): wirkt sofort
  document.getElementById("settings-update-check")?.addEventListener("change", (event) => {
    if (client.state) client.state.update_check_enabled = event.target.checked;
    fetch("/api/update/enabled", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled: event.target.checked }) }).catch(() => {});
  });

  // ---- Open: snapshot current values, populate every field ----
  document.addEventListener("click", (event) => {
    if (!event.target.closest('[data-action="open-settings-modal"]')) return;
    const state = client.state || {};
    const theme = state.theme || {};
    const currentScale = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--gui-scale")) || 1.0;

    snapshotBeforeOpen = {
      gui_scale: currentScale,
      theme: { ...theme },
    };

    if (languageSelect) languageSelect.value = translator.language;
    guiScaleNumber.value = currentScale.toFixed(2);
    const swipeBox = document.getElementById("settings-layout-swipe");
    if (swipeBox) swipeBox.checked = layoutSwipeEnabled();
    const updateBox = document.getElementById("settings-update-check");
    if (updateBox) updateBox.checked = state.update_check_enabled !== false;
    document.getElementById("settings-artnet-enabled").checked = !!state.artnet_enabled;
    document.getElementById("settings-artnet-target-ip").value = state.artnet_ip || "";
    document.getElementById("settings-artnet-bind-ip").value = state.artnet_bind_ip || "";
    _updateArtnetStatusUI(!!state.artnet_enabled);
    document.getElementById("settings-sacn-enabled").checked = !!state.sacn_enabled;
    _updateSacnStatusUI(!!state.sacn_enabled);
    document.getElementById("settings-default-universe").value = state.default_universe || 1;
    _renderRemoteSettings(true);

    // Enttec USB DMX
    document.getElementById("settings-enttec-enabled").checked = !!state.enttec_enabled;
    document.getElementById("settings-enttec-universe").value = state.enttec_universe || 1;
    _populateEnttecPorts(state.enttec_port || "", []);
    _updateEnttecStatusUI(state.enttec_status || {});
    // Port-Liste asynchron holen (zeigt aktuelle COM-Ports ohne Wartezeit beim Oeffnen)
    fetch("/api/dmx/enttec-ports").then(r => r.json()).then(data => {
      _populateEnttecPorts(
        document.getElementById("settings-enttec-port").value,
        data.ports || []
      );
    }).catch(() => {});

    ThemeUI.open(theme);

    const panelDefaults = state.panel_defaults || {};
    PANEL_DEFAULTS_COLOR_FIELDS.forEach(({ key, swatch, hex }) => {
      const value = panelDefaults[key] || "#000000";
      document.getElementById(swatch).value = value;
      document.getElementById(hex).value = value;
    });
    document.getElementById("settings-panel-defaults-shadow").checked = panelDefaults.shadow_enabled !== false;
    document.getElementById("settings-panel-defaults-corners").value = panelDefaults.corner_style || "global";

    // Storage: lade aktuellen Datenpfad
    fetch("/api/data-path").then(r => r.json()).then(data => {
      const display = document.getElementById("settings-data-path-display");
      const custom  = document.getElementById("settings-custom-data-path");
      if (display) display.value = data.path || "";
      if (custom)  custom.value  = data.is_custom ? (state.custom_data_path || data.path) : "";
    }).catch(() => {});

    Modal.open("settings");

    // If the trigger carries a category hint, navigate to that tab
    const trigger = event.target.closest('[data-action="open-settings-modal"]');
    const category = trigger && trigger.dataset.settingsCategory;
    if (category) {
      const root = document.querySelector(".settings-modal");
      if (root) {
        root.querySelectorAll("[data-settings-category]").forEach(btn => {
          btn.classList.toggle("settings-modal__category--active", btn.dataset.settingsCategory === category);
        });
        root.querySelectorAll("[data-settings-pane]").forEach(pane => {
          pane.classList.toggle("settings-modal__pane--active", pane.dataset.settingsPane === category);
        });
      }
    }
  });

  // ---- Enttec: Refresh-Button - Port-Liste neu einlesen ----
  const enttecRefreshBtn = document.getElementById("settings-enttec-refresh");
  if (enttecRefreshBtn) {
    enttecRefreshBtn.addEventListener("click", () => {
      fetch("/api/dmx/enttec-ports").then(r => r.json()).then(data => {
        _populateEnttecPorts(
          document.getElementById("settings-enttec-port").value,
          data.ports || []
        );
      }).catch(() => {});
    });
  }

  // ---- Enttec: Reconnect-Button - Verbindung manuell neu aufbauen ----
  const enttecReconnectBtn = document.getElementById("settings-enttec-reconnect");
  if (enttecReconnectBtn) {
    enttecReconnectBtn.addEventListener("click", () => {
      client.send("reconnect_enttec", {});
    });
  }

  // ---- Storage: Open folder in Explorer ----
  const openDataFolderBtn = document.getElementById("settings-open-data-folder");
  if (openDataFolderBtn) {
    openDataFolderBtn.addEventListener("click", () => {
      fetch("/api/data-path/open", { method: "POST" }).catch(() => {});
    });
  }

  // ---- Storage: confirmation modal shared by Apply + Reset ----
  let _pendingDataPathAction = null;

  const _openDataPathConfirm = (titleKey, msgKey, msgArg, confirmKey, action) => {
    const titleEl   = document.getElementById("data-path-confirm-title");
    const msgEl     = document.getElementById("data-path-confirm-message");
    const confirmEl = document.getElementById("data-path-confirm-button");
    if (titleEl)   titleEl.textContent   = translator.t(titleKey);
    if (confirmEl) confirmEl.textContent = translator.t(confirmKey);
    if (msgEl) {
      const tmpl = translator.t(msgKey);
      msgEl.textContent = msgArg ? tmpl.replace("{path}", msgArg) : tmpl;
    }
    _pendingDataPathAction = action;
    Modal.open("data-path-confirm");
  };

  // ---- Storage: Apply custom path (with confirmation) ----
  const setDataPathBtn = document.getElementById("settings-set-data-path");
  if (setDataPathBtn) {
    setDataPathBtn.addEventListener("click", () => {
      const val = (document.getElementById("settings-custom-data-path")?.value || "").trim();
      if (!val) return;
      _openDataPathConfirm(
        "STORAGE_CONFIRM_CHANGE_TITLE",
        "STORAGE_CONFIRM_CHANGE_MSG",
        val,
        "STORAGE_CONFIRM_CHANGE_BTN",
        () => {
          fetch("/api/data-path/set", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: val }),
          }).then(r => r.json()).then(data => {
            if (data.error) { alert(_serverErrorText(data.error)); return; }
            const display = document.getElementById("settings-data-path-display");
            if (display) display.value = data.path || "";
          }).catch(() => {});
        }
      );
    });
  }

  // ---- Storage: Reset to default path (with confirmation) ----
  const resetDataPathBtn = document.getElementById("settings-reset-data-path");
  if (resetDataPathBtn) {
    resetDataPathBtn.addEventListener("click", () => {
      _openDataPathConfirm(
        "STORAGE_CONFIRM_RESET_TITLE",
        "STORAGE_CONFIRM_RESET_MSG",
        null,
        "STORAGE_CONFIRM_RESET_BTN",
        () => {
          fetch("/api/data-path/set", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: "" }),
          }).then(r => r.json()).then(data => {
            if (data.error) { alert(_serverErrorText(data.error)); return; }
            const display = document.getElementById("settings-data-path-display");
            const custom  = document.getElementById("settings-custom-data-path");
            if (display) display.value = data.path || "";
            if (custom)  custom.value  = "";
          }).catch(() => {});
        }
      );
    });
  }

  // ---- Storage: wire confirm/cancel buttons of the confirmation modal ----
  const dataPathConfirmBtn  = document.getElementById("data-path-confirm-button");
  const dataPathCancelBtn   = document.querySelector('[data-modal-cancel="data-path-confirm"]');
  const dataPathCloseBtn    = document.querySelector('[data-modal-close="data-path-confirm"]');
  const _closeDataPathConfirm = () => {
    Modal.close("data-path-confirm");
    _pendingDataPathAction = null;
  };
  if (dataPathConfirmBtn) {
    dataPathConfirmBtn.addEventListener("click", () => {
      if (_pendingDataPathAction) _pendingDataPathAction();
      _closeDataPathConfirm();
    });
  }
  if (dataPathCancelBtn) dataPathCancelBtn.addEventListener("click", _closeDataPathConfirm);
  if (dataPathCloseBtn)  dataPathCloseBtn.addEventListener("click",  _closeDataPathConfirm);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && Modal.isOpen("data-path-confirm")) _closeDataPathConfirm();
  });

  // ---- Globaler DMX-Neustart-Button (Re-initialize DMX Interfaces) ----
  const dmxReinitBtn = document.getElementById("settings-dmx-reinit-btn");
  if (dmxReinitBtn) {
    dmxReinitBtn.addEventListener("click", () => {
      dmxReinitBtn.disabled = true;
      client.send("reinitialize_dmx", {});
      // Knopf nach kurzer Zeit wieder aktivieren (Antwort kommt via dmx_reinit_done)
      setTimeout(() => { dmxReinitBtn.disabled = false; }, 3000);
    });
  }

  // ---- Live preview: GUI scale ----
  guiScaleNumber.addEventListener("input", () => {
    const scale = parseFloat(guiScaleNumber.value);
    if (Number.isNaN(scale)) return;
    client._applyGuiScale(clamp(scale, SETTINGS_GUI_SCALE_MIN, SETTINGS_GUI_SCALE_MAX));
  });

  // "Launch Scale Tool...": no dedicated listener needed here - the button
  // already carries data-action="open-gui-scale-modal" in the HTML, which
  // the generic delegated listener in setupGuiScaleModal() picks up on its
  // own. The Settings modal is deliberately left open behind it (true
  // sub-modal stacking, see modal-backdrop--stacked in style.css): nothing
  // needs closing or reverting here, since the Settings modal was never
  // hidden in the first place. Cancel/Save & Close in the scale tool only
  // ever closes ITS OWN backdrop, returning seamlessly to the still-open
  // Settings modal underneath.

  // ---- Panel Defaults: no live preview (nothing on screen uses these
  // until a NEW panel is created) - swatch/hex just stay in sync with
  // each other, values are only read out on Save & Apply below. ----
  PANEL_DEFAULTS_COLOR_FIELDS.forEach(({ swatch, hex }) => {
    wireColorPair(swatch, hex, () => {});
  });

  // ---- Cancel / close / Escape: revert live previews, discard everything ----
  const cancelAndClose = () => {
    if (snapshotBeforeOpen) {
      client._applyGuiScale(snapshotBeforeOpen.gui_scale);
      client._applyTheme(client.state.theme);   // zuletzt vom Server bestaetigtes Theme (inkl. angewendeter Profile)
    }
    Modal.close("settings");
  };

  // ---- Save & Apply: commit everything staged in the form to the server ----
  saveButton.addEventListener("click", () => {
    if (languageSelect && languageSelect.value !== translator.language) {
      translator.setLanguage(languageSelect.value).then(() => {
        client.send("set_language", { language: languageSelect.value });
      });
    }

    const scale = clamp(parseFloat(guiScaleNumber.value) || 1.0, SETTINGS_GUI_SCALE_MIN, SETTINGS_GUI_SCALE_MAX);
    client.setGuiScale(scale);

    _saveRemoteSettings();

    client.send("set_artnet_enabled", { enabled: document.getElementById("settings-artnet-enabled").checked });
    client.send("set_artnet_ip", { ip: document.getElementById("settings-artnet-target-ip").value.trim() });
    client.send("set_artnet_bind_ip", { ip: document.getElementById("settings-artnet-bind-ip").value.trim() });
    client.send("set_sacn_enabled", { enabled: document.getElementById("settings-sacn-enabled").checked });

    client.send("set_enttec_enabled", { enabled: document.getElementById("settings-enttec-enabled").checked });
    client.send("set_enttec_port", { port: document.getElementById("settings-enttec-port").value });
    const enttecUniverse = clamp(parseInt(document.getElementById("settings-enttec-universe").value, 10) || 1, 1, 64);
    client.send("set_enttec_universe", { universe: enttecUniverse });

    const universe = clamp(parseInt(document.getElementById("settings-default-universe").value, 10) || 1, 1, 64);
    client.send("set_default_universe", { universe });

    client.send("set_theme", ThemeUI.getDraft());

    const panelDefaults = {};
    PANEL_DEFAULTS_COLOR_FIELDS.forEach(({ key, hex }) => {
      const value = document.getElementById(hex).value.trim();
      if (HEX_COLOR_PATTERN.test(value)) panelDefaults[key] = value;
    });
    panelDefaults.shadow_enabled = document.getElementById("settings-panel-defaults-shadow").checked;
    panelDefaults.corner_style = document.getElementById("settings-panel-defaults-corners").value;
    client.send("set_panel_defaults", panelDefaults);

    Modal.close("settings");
  });

  cancelButton.addEventListener("click", cancelAndClose);
  closeButton.addEventListener("click", cancelAndClose);
  document.addEventListener("keydown", (event) => {
    // Guarded against reset-confirm or the GUI Scale sub-modal being open on
    // top of this modal - Escape should only ever dismiss the topmost
    // dialog, not cascade through and close the Settings modal underneath.
    if (
      event.key === "Escape" &&
      Modal.isOpen("settings") &&
      !Modal.isOpen("reset-confirm") &&
      !Modal.isOpen("gui-scale") &&
      !Modal.isOpen("data-path-confirm")
    ) {
      cancelAndClose();
    }
  });

  // ---- Reset Defaults: opens a small confirmation dialog STACKED on top
  // of this still-open modal (see .modal-backdrop--stacked in style.css) -
  // confirming or cancelling only ever closes that confirmation dialog,
  // never this one. The actual reset (server-side) is applied live via the
  // settings_reset broadcast handling in OpenCueClient._handleMessage,
  // which refreshes every field this modal currently shows in place.
  const resetButton = document.getElementById("settings-reset-defaults");
  const resetConfirmButton = document.getElementById("reset-confirm-button");
  const resetCancelButton = document.querySelector('[data-modal-cancel="reset-confirm"]');
  const resetCloseButton = document.querySelector('[data-modal-close="reset-confirm"]');

  if (resetButton) {
    resetButton.addEventListener("click", () => Modal.open("reset-confirm"));
  }
  if (resetConfirmButton) {
    resetConfirmButton.addEventListener("click", () => {
      client.send("reset_settings");
      Modal.close("reset-confirm");
    });
  }
  const closeResetConfirm = () => Modal.close("reset-confirm");
  if (resetCancelButton) resetCancelButton.addEventListener("click", closeResetConfirm);
  if (resetCloseButton) resetCloseButton.addEventListener("click", closeResetConfirm);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && Modal.isOpen("reset-confirm")) closeResetConfirm();
  });
}

// Speichern geht immer in den lokalen Datenordner.
function _readLocationPicker(_pickerId) {
  return { target: "local", drive: "" };
}

/** Refreshes every field the Settings modal (and, via
 * updateSettingsFieldsInAllPanels, the old workspace Settings panel) shows,
 * after a server-side "Reset Defaults". Applies live (theme/gui-scale)
 * exactly like the individual *_changed broadcasts already do, just for
 * every reset field at once in a single message. */
function applySettingsResetToUI(payload) {
  // "Reset Defaults" gilt fuer die Konsole; externe Geraete behalten ihre eigene Skalierung.
  if (client.state && client.state.is_local) client.setGuiScale(payload.gui_scale);
  client._applyTheme(payload.theme);
  translator.setLanguage(payload.language).then(() => {
    client._dispatchToPanelPlugins({ type: "language_changed", payload: { language: payload.language } });
  });

  const guiScaleNumber = document.getElementById("settings-gui-scale-number");
  if (guiScaleNumber) guiScaleNumber.value = payload.gui_scale.toFixed(2);

  ThemeUI.sync(payload.theme);

  if (payload.panel_defaults) {
    PANEL_DEFAULTS_COLOR_FIELDS.forEach(({ key, swatch, hex }) => {
      const value = payload.panel_defaults[key];
      if (!value) return;
      const swatchEl = document.getElementById(swatch);
      const hexEl = document.getElementById(hex);
      if (swatchEl) swatchEl.value = value;
      if (hexEl) hexEl.value = value;
    });
    const shadowCheckbox = document.getElementById("settings-panel-defaults-shadow");
    if (shadowCheckbox) shadowCheckbox.checked = payload.panel_defaults.shadow_enabled !== false;
    const cornersSelect = document.getElementById("settings-panel-defaults-corners");
    if (cornersSelect) cornersSelect.value = payload.panel_defaults.corner_style || "global";
  }

  updateSettingsFieldsInAllPanels("artnet_enabled", payload.artnet_enabled);
  updateSettingsFieldsInAllPanels("artnet_ip", payload.artnet_ip);
  updateSettingsFieldsInAllPanels("artnet_bind_ip", payload.artnet_bind_ip);
  _updateArtnetStatusUI(!!payload.artnet_enabled);
  updateSettingsFieldsInAllPanels("sacn_enabled", payload.sacn_enabled);
  _updateSacnStatusUI(!!payload.sacn_enabled);
  updateSettingsFieldsInAllPanels("default_universe", payload.default_universe);
  updateSettingsFieldsInAllPanels("enttec_enabled", payload.enttec_enabled);
  updateSettingsFieldsInAllPanels("enttec_port", payload.enttec_port);
  updateSettingsFieldsInAllPanels("enttec_universe", payload.enttec_universe);
  if (payload.enttec_status) _updateEnttecStatusUI(payload.enttec_status);
  updateSettingsFieldsInAllPanels("language", payload.language);
}

// ---- Settings panel (first real workspace module) --------------------------

function buildFieldRow(labelKey, controlElement) {
  const row = document.createElement("div");
  row.className = "settings-field";
  const label = document.createElement("label");
  label.dataset.i18n = labelKey;
  label.textContent = i18n(labelKey);
  row.appendChild(label);
  row.appendChild(controlElement);
  return row;
}

function buildTextField(labelKey, value, onChange, fieldName) {
  const input = document.createElement("input");
  input.type = "text";
  input.value = value;
  if (fieldName) input.dataset.settingsField = fieldName;
  input.addEventListener("change", () => onChange(input.value.trim()));
  return buildFieldRow(labelKey, input);
}

function buildNumberField(labelKey, value, min, max, onChange, fieldName) {
  const input = document.createElement("input");
  input.type = "number";
  input.min = String(min);
  input.max = String(max);
  input.value = value;
  if (fieldName) input.dataset.settingsField = fieldName;
  input.addEventListener("change", () => {
    const parsed = clamp(parseInt(input.value, 10) || min, min, max);
    input.value = parsed;
    onChange(parsed);
  });
  return buildFieldRow(labelKey, input);
}

function buildToggleField(labelKey, checked, onChange, fieldName) {
  const wrapper = document.createElement("label");
  wrapper.className = "toggle-switch";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.checked = checked;
  if (fieldName) input.dataset.settingsField = fieldName;
  input.addEventListener("change", () => onChange(input.checked));
  const track = document.createElement("span");
  track.className = "toggle-switch__track";
  wrapper.appendChild(input);
  wrapper.appendChild(track);
  return buildFieldRow(labelKey, wrapper);
}

function buildSelectField(labelKey, currentValue, options, onChange, fieldName) {
  const select = document.createElement("select");
  if (fieldName) select.dataset.settingsField = fieldName;
  options.forEach((opt) => {
    const optionEl = document.createElement("option");
    optionEl.value = opt.value;
    optionEl.dataset.i18n = opt.labelKey;
    optionEl.textContent = i18n(opt.labelKey);
    if (opt.value === currentValue) optionEl.selected = true;
    select.appendChild(optionEl);
  });
  select.addEventListener("change", () => onChange(select.value));
  return buildFieldRow(labelKey, select);
}

/** Shows a toast notification that slides in from the top-right. */
/** Ein Schluessel wie "wakeLock_unsupported" wird uebersetzt; bleibt er unbekannt, erscheint
 *  eine neutrale Meldung statt des Key-Namens. `raw` = Text des Nutzers (z. B. Layoutname "Show_1" oder ein Tooltip):
 *  er wird nie als Schluessel gedeutet. */
function _toastText(msg, raw) {
  const text = String(msg == null ? "" : msg);
  if (!raw && /^[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+$/.test(text)) {
    const resolved = translator.t(text);
    if (resolved !== text) return resolved;
    console.warn("[i18n] Toast-Schluessel ohne Uebersetzung:", text);
    const unknown = translator.t("TOAST_UNKNOWN");
    // Sind die Sprachdateien noch nicht geladen, bleibt auch TOAST_UNKNOWN unaufgeloest: dann ein fester Text.
    return unknown === "TOAST_UNKNOWN" ? (translator.language === "de" ? "Unbekannte Meldung" : "Unknown message") : unknown;
  }
  return text;
}

// Fehlertexte des Servers (feste Strings) in der Oberflaechensprache; Unbekanntes bleibt unveraendert.
const SERVER_ERROR_KEYS = {
  "drive required": "ERR_DRIVE_REQUIRED",
  "Absoluter Pfad erforderlich": "ERR_ABSOLUTE_PATH_REQUIRED",
};
function _serverErrorText(error) {
  const key = SERVER_ERROR_KEYS[String(error)];
  return key ? translator.t(key) : String(error);
}

function _showToast(msg, type, duration, raw) {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = "toast toast--" + (type || "info");
  toast.textContent = _toastText(msg, raw);
  container.appendChild(toast);
  requestAnimationFrame(() => requestAnimationFrame(() => toast.classList.add("toast--visible")));
  const dismiss = () => {
    toast.classList.remove("toast--visible");
    toast.classList.add("toast--hiding");
    setTimeout(() => { if (toast.parentNode) toast.remove(); }, 350);
  };
  const timer = setTimeout(dismiss, duration || 4000);
  toast.addEventListener("click", () => { clearTimeout(timer); dismiss(); });
}

let _heartWasError = false;

/** Updates the DMX heart icon in the toolbar based on current DMX state. */
function _updateDmxHeart(stateObj) {
  const heart = document.getElementById("dmx-heart-icon");
  const btn   = document.getElementById("dmx-heart-btn");
  if (!heart) return;
  const artnetOn = !!(stateObj && stateObj.artnet_enabled);
  const sacnOn   = !!(stateObj && stateObj.sacn_enabled);
  const enttecConnected = !!(stateObj && stateObj.enttec_enabled &&
                             stateObj.enttec_status && stateObj.enttec_status.connected);
  const enttecError = !!(stateObj && stateObj.enttec_enabled &&
                         stateObj.enttec_status && stateObj.enttec_status.error);
  const anyActive = artnetOn || sacnOn || enttecConnected;
  const isError = enttecError && !enttecConnected;

  heart.classList.remove("menubar__dmx-heart--active", "menubar__dmx-heart--error", "menubar__dmx-heart--broken");

  if (isError) {
    if (!_heartWasError) {
      heart.classList.add("menubar__dmx-heart--broken");
      heart.addEventListener("animationend", () => {
        heart.classList.remove("menubar__dmx-heart--broken");
        heart.classList.add("menubar__dmx-heart--error");
      }, { once: true });
    } else {
      heart.classList.add("menubar__dmx-heart--error");
    }
    _heartWasError = true;
  } else if (anyActive) {
    heart.classList.add("menubar__dmx-heart--active");
    _heartWasError = false;
  } else {
    _heartWasError = false;
  }
  if (btn) btn.title = i18n(anyActive || isError ? "DMX_HEART_ACTIVE" : "DMX_HEART_INACTIVE");
}

/** Updates the Art-Net status badge in the open Settings modal. */
function _updateArtnetStatusUI(enabled) {
  const el = document.getElementById("settings-artnet-status");
  if (!el) return;
  el.className = "settings-protocol-status";
  if (enabled) {
    el.textContent = i18n("DMX_STATUS_ACTIVE");
    el.classList.add("settings-protocol-status--ok");
  } else {
    el.textContent = i18n("DMX_STATUS_INACTIVE");
    el.classList.add("settings-protocol-status--inactive");
  }
}

/** Updates the sACN status badge in the open Settings modal. */
function _updateSacnStatusUI(enabled) {
  const el = document.getElementById("settings-sacn-status");
  if (!el) return;
  el.className = "settings-protocol-status";
  if (enabled) {
    el.textContent = i18n("DMX_STATUS_ACTIVE");
    el.classList.add("settings-protocol-status--ok");
  } else {
    el.textContent = i18n("DMX_STATUS_INACTIVE");
    el.classList.add("settings-protocol-status--inactive");
  }
}

/** Updates the Enttec status badge in any open Settings modal. */
function _updateEnttecStatusUI(status) {
  if (!status) return;
  const el = document.getElementById("settings-enttec-status");
  if (!el) return;
  el.className = "settings-enttec-status";
  if (!status.available) {
    el.textContent = i18n("SETTINGS_ENTTEC_NO_PYSERIAL");
    el.classList.add("settings-enttec-status--warn");
  } else if (!status.enabled) {
    el.textContent = "";
  } else if (status.connected) {
    el.textContent = i18n("SETTINGS_ENTTEC_CONNECTED").replace("{port}", status.port || "");
    el.classList.add("settings-enttec-status--ok");
  } else if (status.error) {
    el.textContent = status.error;
    el.classList.add("settings-enttec-status--error");
  } else {
    el.textContent = i18n("SETTINGS_ENTTEC_DISCONNECTED");
    el.classList.add("settings-enttec-status--warn");
  }
}

/** Populates the Enttec COM-Port dropdown. selectedPort is set as selected value. */
function _populateEnttecPorts(selectedPort, ports) {
  const sel = document.getElementById("settings-enttec-port");
  if (!sel) return;
  const prev = sel.value || selectedPort || "";
  sel.innerHTML = "";
  const emptyOpt = document.createElement("option");
  emptyOpt.value = "";
  emptyOpt.textContent = i18n("SETTINGS_ENTTEC_PORT_NONE");
  sel.appendChild(emptyOpt);
  if (ports && ports.length) {
    ports.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p;
      opt.textContent = p;
      sel.appendChild(opt);
    });
  } else if (prev && prev !== "") {
    // Port nicht mehr gefunden - trotzdem eintragen damit der Wert sichtbar bleibt
    const opt = document.createElement("option");
    opt.value = prev;
    opt.textContent = prev + " (?)";
    sel.appendChild(opt);
  }
  sel.value = prev || "";
}

/** Live-syncs every open instance of a settings field (across however many
 * Settings panels/clients happen to have one mounted) when its value
 * changes via WebSocket - skips any input the user currently has focused,
 * so an incoming update never clobbers what they're mid-typing. */
function updateSettingsFieldsInAllPanels(fieldName, value) {
  document.querySelectorAll(`[data-settings-field="${fieldName}"]`).forEach((input) => {
    if (document.activeElement === input) return;
    if (input.type === "checkbox") {
      input.checked = !!value;
    } else {
      input.value = value;
    }
  });
}

// ---- Remote-Einstellungen (nur an der Konsole selbst; Server sendet state.remote nur dorthin) ----
let _remoteQrUrl = null;      // Adresse, deren QR-Code gerade gezeigt wird

/** Text in die Zwischenablage (Clipboard-API, sonst der klassische Weg ueber ein verstecktes Textfeld). */
async function _copyText(text) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) { await navigator.clipboard.writeText(text); return true; }
  } catch (error) { /* weiter mit dem Rueckfall */ }
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.cssText = "position:fixed;left:-9999px;top:0;opacity:0";
  document.body.appendChild(area);
  area.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch (error) { ok = false; }
  area.remove();
  return ok;
}

function _renderRemoteSettings(fillInputs) {
  const remote = client.state && client.state.remote;
  const category = document.getElementById("settings-remote-category");
  if (category) category.hidden = !remote;
  if (!remote) return;
  const enabled = document.getElementById("settings-remote-enabled");
  const password = document.getElementById("settings-remote-password");
  if (fillInputs) {
    if (enabled) enabled.checked = !!remote.enabled;
    if (password) password.value = remote.password || "";
    const portInput = document.getElementById("settings-remote-port");
    if (portInput) portInput.value = remote.configured_port || remote.port || "";
  }
  const staged = enabled ? enabled.checked : !!remote.enabled;
  const pending = staged !== !!remote.enabled;                       // Schalter umgelegt, aber noch nicht gespeichert
  const status = document.getElementById("settings-remote-status");
  if (status) {
    status.classList.toggle("settings-remote-status--on", !!remote.listening_on_network && !pending);
    status.textContent = pending ? i18n("SETTINGS_REMOTE_PENDING")
      : remote.listening_on_network ? i18n("SETTINGS_REMOTE_STATUS_ON")
      : remote.enabled ? i18n("SETTINGS_REMOTE_STATUS_NONET")
      : i18n("SETTINGS_REMOTE_STATUS_OFF").replace("{url}", remote.local_url || "");
  }
  const info = document.getElementById("settings-remote-info");
  if (info) {
    info.textContent = "";
    const live = remote.urls || [];
    const urls = live.length ? live : (remote.candidate_urls || []);
    if (!live.length && urls.length) {
      const hint = document.createElement("div");
      hint.className = "settings-remote-hint";
      hint.textContent = i18n("SETTINGS_REMOTE_CANDIDATES");
      info.appendChild(hint);
    }
    if (!_remoteQrUrl || !live.includes(_remoteQrUrl)) _remoteQrUrl = live[0] || null;
    urls.forEach((url) => {
      const row = document.createElement("div");
      row.className = "settings-remote-row" + (live.length ? "" : " settings-remote-row--idle") + (url === _remoteQrUrl ? " settings-remote-row--selected" : "");
      const text = document.createElement("span");
      text.className = "settings-remote-url";
      text.textContent = url;
      const copy = document.createElement("button");
      copy.type = "button";
      copy.className = "modal__button settings-remote-copy";
      copy.textContent = i18n("SETTINGS_REMOTE_COPY");
      copy.addEventListener("click", async (event) => {
        event.stopPropagation();
        _showToast(i18n(await _copyText(url) ? "SETTINGS_REMOTE_COPIED" : "SETTINGS_REMOTE_COPY_FAILED"), "info", 2500);
      });
      row.append(text, copy);
      if (live.length) row.addEventListener("click", () => { _remoteQrUrl = url; _renderRemoteSettings(false); });
      info.appendChild(row);
    });
    if (!urls.length) {
      const none = document.createElement("div");
      none.className = "settings-remote-hint";
      none.textContent = i18n("SETTINGS_REMOTE_NO_ADDRESS");
      info.appendChild(none);
    }
    Object.entries(remote.listen_errors || {}).forEach(([ip, message]) => {
      const err = document.createElement("div");
      err.className = "settings-remote-error";
      err.textContent = i18n("SETTINGS_REMOTE_ERROR").replace("{ip}", ip).replace("{msg}", message);
      info.appendChild(err);
    });
  }
  const qr = document.getElementById("settings-remote-qr");
  if (qr) {
    const svg = _remoteQrUrl && remote.qr ? remote.qr[_remoteQrUrl] : "";
    qr.hidden = !svg;
    qr.textContent = "";
    if (svg) {
      const code = document.createElement("div");
      code.className = "settings-remote-qr__code";
      code.innerHTML = svg;                                           // vom eigenen Server erzeugtes SVG (segno), kein Fremdinhalt
      const caption = document.createElement("div");
      caption.className = "settings-remote-hint";
      caption.textContent = i18n("SETTINGS_REMOTE_QR");
      qr.append(code, caption);
    }
  }
  const restart = document.getElementById("settings-remote-restart");
  const portField = document.getElementById("settings-remote-port");
  const portPending = portField && portField.value !== "" && Number(portField.value) !== remote.port;
  if (restart) restart.hidden = !(remote.restart_required || portPending);        // nur ein geaenderter Port braucht einen Neustart
}

function _saveRemoteSettings() {
  const remote = client.state && client.state.remote;
  if (!remote) return;
  const enabled = document.getElementById("settings-remote-enabled");
  const password = document.getElementById("settings-remote-password");
  if (password && password.value !== remote.password) {
    if (password.value.length < 4) {
      _showToast(i18n("SETTINGS_REMOTE_PASSWORD_SHORT"), "error", 4000);
    } else {
      client.send("set_remote_password", { password: password.value });
    }
  }
  if (enabled && enabled.checked !== !!remote.enabled) {
    client.send("set_remote_enabled", { enabled: enabled.checked });
  }
  const portInput = document.getElementById("settings-remote-port");
  if (portInput && Number(portInput.value) !== remote.configured_port) {
    const port = Number(portInput.value);
    if (Number.isInteger(port) && port >= 1024 && port <= 65535) {
      client.send("set_server_port", { port });
    } else {
      _showToast(i18n("SETTINGS_REMOTE_PORT_INVALID"), "error", 4000);
    }
  }
}

document.addEventListener("change", (event) => {
  if (event.target && event.target.id === "settings-remote-enabled") _renderRemoteSettings(false);
});
document.addEventListener("input", (event) => {
  if (event.target && event.target.id === "settings-remote-port") _renderRemoteSettings(false);
});
document.addEventListener("click", (event) => {
  if (event.target && event.target.id === "settings-remote-refresh") client.send("remote_refresh", {});       // Adressen neu erkennen (WLAN gewechselt ...)
});
document.addEventListener("click", (event) => {
  if (!event.target || event.target.id !== "settings-remote-password-toggle") return;
  const input = document.getElementById("settings-remote-password");
  if (!input) return;
  const reveal = input.type === "password";
  input.type = reveal ? "text" : "password";
  event.target.textContent = i18n(reveal ? "SETTINGS_REMOTE_HIDE" : "SETTINGS_REMOTE_SHOW");
});

// ---- Remote-Clients: Toolbar-Icon, Verwaltungs-Dialog, Kick ------------------------------
let _remoteClients = [];
let _remoteClientsAt = 0;
let _remoteClientsTimer = null;

let _remoteCount = 0;
let _remoteEnabled = false;

function _isRemoteClient() {
  return document.documentElement.classList.contains("is-remote");
}

function _updateRemoteIndicator(count, enabled) {
  _remoteCount = count;
  _remoteEnabled = enabled;
  const btn = document.getElementById("remote-clients-btn");
  if (!btn) return;
  const badge = document.getElementById("remote-clients-badge");
  // Remote aus -> Icon ganz weg. Remote-Geraete (iPad/Browser) sehen und oeffnen die
  // Client-Verwaltung nie.
  btn.hidden = !enabled;
  btn.classList.toggle("menubar__remote-btn--idle", count === 0);
  btn.classList.toggle("menubar__remote-btn--active", count > 0);   // gruen + Zahl
  if (badge) {
    badge.textContent = String(count);
    badge.hidden = count === 0;
  }
  btn.title = i18n("REMOTE_BTN_COUNT").replace("{n}", count);
  const summary = document.getElementById("remote-clients-summary");
  if (summary) summary.textContent = i18n("REMOTE_CLIENTS_SUMMARY").replace("{n}", count);
  if (!enabled && Modal.isOpen("remote-clients")) Modal.close("remote-clients");
}

function _formatDuration(totalSeconds) {
  const sec = Math.max(0, Math.floor(totalSeconds));
  const pad = (n) => String(n).padStart(2, "0");
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  return h ? `${h}:${pad(m)}:${pad(sec % 60)}` : `${pad(m)}:${pad(sec % 60)}`;
}

function _renderRemoteClients() {
  const body = document.getElementById("remote-clients-list");   // <tbody>
  if (!body) return;
  const table = document.getElementById("remote-clients-table");
  const empty = document.getElementById("remote-clients-empty");
  if (table) table.hidden = !_remoteClients.length;
  if (empty) empty.hidden = _remoteClients.length > 0;

  const ids = _remoteClients.map((c) => c.id).join(",");
  if (body.dataset.ids !== ids) {          // Zeilen nur neu aufbauen, wenn sich die Clients aendern
    body.dataset.ids = ids;
    body.textContent = "";
    _remoteClients.forEach((c) => {
      const row = document.createElement("tr");
      row.className = "remote-row";
      row.dataset.id = c.id;

      const ip = document.createElement("td");
      ip.className = "remote-cell remote-cell--ip";
      ip.textContent = c.ip;

      const device = document.createElement("td");
      device.className = "remote-cell remote-cell--device";
      device.textContent = c.device === "?" ? i18n("REMOTE_DEVICE_UNKNOWN") : c.device;
      if (c.ua) device.title = c.ua;       // vollstaendiger User-Agent als Tooltip

      const time = document.createElement("td");
      time.className = "remote-cell remote-cell--time";

      const action = document.createElement("td");
      action.className = "remote-cell remote-cell--action";
      const kick = document.createElement("button");
      kick.type = "button";
      kick.className = "modal__button remote-client__kick";
      kick.dataset.id = c.id;
      kick.dataset.i18n = "REMOTE_CLIENT_KICK";   // folgt Sprachwechseln
      kick.textContent = i18n("REMOTE_CLIENT_KICK");
      action.appendChild(kick);

      row.append(ip, device, time, action);
      body.appendChild(row);
    });
  }
  const elapsed = (Date.now() - _remoteClientsAt) / 1000;
  _remoteClients.forEach((c) => {
    const cell = body.querySelector(`.remote-row[data-id="${c.id}"] .remote-cell--time`);
    if (cell) cell.textContent = _formatDuration(c.connected_for + elapsed);
  });
}

function _applyRemoteSnapshot(payload) {
  _remoteClients = payload.remote_clients || [];
  _remoteClientsAt = Date.now();
  _updateRemoteIndicator(payload.remote_client_count || 0, !!payload.remote_enabled);
  _renderRemoteClients();
  if (payload.is_local === false) WakeLockKeeper.enable();   // nur Tablets/Remote-Geraete
}

document.addEventListener("click", (event) => {
  const openBtn = event.target.closest && event.target.closest("#remote-clients-btn");
  if (openBtn) {   // auch am Remote-Geraet: die Liste zeigt, welche Geraete verbunden sind (Trennen nur an der Konsole)
    _renderRemoteClients();
    Modal.open("remote-clients");
    clearInterval(_remoteClientsTimer);
    _remoteClientsTimer = setInterval(() => {
      if (!Modal.isOpen("remote-clients")) { clearInterval(_remoteClientsTimer); return; }
      _renderRemoteClients();   // Verbindungsdauer laeuft sekuendlich mit
    }, 1000);
    return;
  }
  const kickBtn = event.target.closest && event.target.closest(".remote-client__kick");
  if (kickBtn) {
    kickBtn.disabled = true;
    const ip = (_remoteClients.find((c) => c.id === kickBtn.dataset.id) || {}).ip || "";
    fetch("/api/remote/kick", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: kickBtn.dataset.id }),
    }).then((res) => {
      if (res.ok) {
        _showToast(i18n("REMOTE_KICK_OK").replace("{ip}", ip), "info", 3000);
      } else {
        kickBtn.disabled = false;
        _showToast(i18n("REMOTE_KICK_FAILED"), "error", 4000);
      }
    }).catch(() => {
      kickBtn.disabled = false;
      _showToast(i18n("REMOTE_KICK_FAILED"), "error", 4000);
    });
  }
});

// ---- Display Wake-Lock (Tablets): Bildschirm bleibt waehrend der Bedienung an ------------------
// Die Screen Wake Lock API gibt es nur in sicheren Kontexten (HTTPS oder localhost). Ueber
// http://<IP> im LAN fehlt navigator.wakeLock - dann bleibt nur die Geraete-Einstellung
// "Automatische Sperre: Nie".
const WakeLockKeeper = (() => {
  let sentinel = null;
  let enabled = false;
  let warned = false;

  async function acquire() {
    if (!enabled || sentinel || document.visibilityState !== "visible") return;
    if (!("wakeLock" in navigator)) {
      if (!warned) {
        warned = true;
        _showToast(i18n("wakeLock_unsupported"), "warn", 8000);
      }
      return;
    }
    try {
      sentinel = await navigator.wakeLock.request("screen");
      sentinel.addEventListener("release", () => { sentinel = null; });
    } catch (error) {
      sentinel = null;   // z.B. Energiesparmodus - beim naechsten Tippen erneut versuchen
    }
  }

  function enable() {
    if (enabled) return;
    enabled = true;
    acquire();
    // Der Browser gibt den Lock beim Tab-Wechsel/Sperren frei - bei Rueckkehr neu holen.
    document.addEventListener("visibilitychange", acquire);
    ["pointerdown", "touchend"].forEach((name) => document.addEventListener(name, acquire, { passive: true }));
  }

  return { enable };
})();

function buildSectionTitle(labelKey) {
  const title = document.createElement("div");
  title.className = "settings-section__title";
  title.dataset.i18n = labelKey;
  title.textContent = i18n(labelKey);
  return title;
}

function buildSettingsPanelContent() {
  const state = client.state || {};
  const container = document.createElement("div");

  const dmxSection = document.createElement("div");
  dmxSection.className = "settings-section";
  dmxSection.appendChild(buildSectionTitle("SETTINGS_SECTION_DMX"));
  dmxSection.appendChild(
    buildToggleField(
      "SETTINGS_ARTNET_ENABLE",
      !!state.artnet_enabled,
      (checked) => client.send("set_artnet_enabled", { enabled: checked }),
      "artnet_enabled"
    )
  );
  dmxSection.appendChild(
    buildTextField(
      "SETTINGS_ARTNET_IP",
      state.artnet_ip || "",
      (value) => client.send("set_artnet_ip", { ip: value }),
      "artnet_ip"
    )
  );
  dmxSection.appendChild(
    buildToggleField(
      "SETTINGS_SACN_ENABLE",
      !!state.sacn_enabled,
      (checked) => client.send("set_sacn_enabled", { enabled: checked }),
      "sacn_enabled"
    )
  );
  dmxSection.appendChild(
    buildNumberField(
      "SETTINGS_DEFAULT_UNIVERSE",
      state.default_universe || 1,
      1,
      64,
      (value) => client.send("set_default_universe", { universe: value }),
      "default_universe"
    )
  );
  container.appendChild(dmxSection);

  const interfaceSection = document.createElement("div");
  interfaceSection.className = "settings-section";
  interfaceSection.appendChild(buildSectionTitle("SETTINGS_SECTION_INTERFACE"));
  interfaceSection.appendChild(
    buildSelectField(
      "SETTINGS_LANGUAGE",
      translator.language,
      [
        { value: "en", labelKey: "LANGUAGE_EN" },
        { value: "de", labelKey: "LANGUAGE_DE" },
      ],
      (value) => {
        translator.setLanguage(value).then(() => {
          client.send("set_language", { language: value });
        });
      },
      "language"
    )
  );

  const guiScaleButton = document.createElement("button");
  guiScaleButton.type = "button";
  guiScaleButton.dataset.action = "open-gui-scale-modal"; // reuses the existing modal (delegated click)
  guiScaleButton.dataset.i18n = "SETTINGS_ADJUST_GUI_SCALE";
  guiScaleButton.textContent = i18n("SETTINGS_ADJUST_GUI_SCALE");
  const guiScaleField = document.createElement("div");
  guiScaleField.className = "settings-field";
  guiScaleField.appendChild(guiScaleButton);
  interfaceSection.appendChild(guiScaleField);

  container.appendChild(interfaceSection);

  return container;
}

// ---- Window title & toolbar clock ------------------------------------------

/** document.title AND die Toolbar-Anzeige (inkl. farbigem Dirty-Sternchen) werden hier gesetzt. */
function updateWindowTitle(showfileName, dirty) {
  const d = dirty ?? _isDirty;
  const name = (!showfileName || showfileName === "Untitled") ? i18n("SHOWFILE_UNTITLED") : showfileName;
  document.title = "OpenCue";   // fester Titel - Showfile und Version stehen in der Toolbar
  const indicator = document.getElementById("toolbar-showfile-name");
  if (indicator) {
    indicator.textContent = name;
    // Separator-Border am Name-Span wenn kein Stern sichtbar, sonst am Stern
    indicator.classList.toggle("menubar__showfile-name--sep", !d);
  }
  const star = document.getElementById("toolbar-dirty-star");
  if (star) star.hidden = !d;
}

function setupClock() {
  const clockElement = document.getElementById("menubar-clock");
  if (!clockElement) return;

  const pad = (n) => String(n).padStart(2, "0");
  const tick = () => {
    const now = new Date();
    clockElement.textContent = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  };

  tick();
  setInterval(tick, 1000);
}

// ---- Fullscreen: F11 shortcut + View -> Fullscreen toggle --------------
// Real OS-level fullscreen (hides the taskbar too, unlike "maximized") can
// only be toggled from the Python side (window.toggle_fullscreen()) - per
// the dummy-container principle this is just another WebSocket message;
// main.py's watcher thread does the actual toggling. See app/window_signals.py.
//
// There's no event coming back from Python confirming the new state (that
// would need a whole extra broadcast channel for a single-window desktop
// app), so this is the one piece of state the client tracks optimistically:
// F11 and the menu item are the ONLY two ways fullscreen can ever be
// toggled, both go through this same function, so flipping a local flag
// every time either fires stays accurate.
let isFullscreenActive = false;

// Remote-Geraete haben ihr eigenes Browserfenster: Vollbild ist dort rein lokal (Fullscreen-API des Browsers),
// es geht nichts an den Server und nichts kommt von ihm. Nur das Fenster der Konsole (PyWebView) schaltet ueber
// den Server um.
function _browserFullscreenElement() {
  return document.fullscreenElement || document.webkitFullscreenElement || null;
}

function _syncFullscreenMenu() {
  const menuItem = document.querySelector('[data-action="toggle-fullscreen"]');
  if (menuItem) menuItem.classList.toggle("menu__item--checked", !!_browserFullscreenElement());
}
["fullscreenchange", "webkitfullscreenchange"].forEach((name) => {
  document.addEventListener(name, () => { if (_isRemoteClient()) _syncFullscreenMenu(); });
});

function toggleFullscreen() {
  if (_isRemoteClient()) {
    const root = document.documentElement;
    const request = root.requestFullscreen || root.webkitRequestFullscreen;
    const leave = document.exitFullscreen || document.webkitExitFullscreen;
    if (!request) {   // z.B. iPhone-Safari: kein Vollbild fuer Webseiten
      _showToast(i18n("FULLSCREEN_UNSUPPORTED"), "info", 5000);
      return;
    }
    try {
      const result = _browserFullscreenElement() ? leave.call(document) : request.call(root);
      if (result && result.catch) result.catch(() => _showToast(i18n("FULLSCREEN_UNSUPPORTED"), "info", 5000));
    } catch (error) {
      _showToast(i18n("FULLSCREEN_UNSUPPORTED"), "info", 5000);
    }
    return;
  }
  isFullscreenActive = !isFullscreenActive;
  client.send("toggle_fullscreen");
  const menuItem = document.querySelector('[data-action="toggle-fullscreen"]');
  if (menuItem) menuItem.classList.toggle("menu__item--checked", isFullscreenActive);
}

function setupFullscreenToggle() {
  const menuItem = document.querySelector('[data-action="toggle-fullscreen"]');
  if (menuItem) {
    menuItem.addEventListener("click", () => toggleFullscreen());
  }
}

// ---- File menu (New / Open / Save / Save As) --------------------------------

// Beenden-Dialog (X, Datei > Beenden, Ctrl+Q): "mit Speichern" speichert wie
// Strg+S, "ohne Speichern" beendet ohne Schreibvorgang, "Abbrechen" bleibt offen.
function setupCloseConfirmModal() {
  document.getElementById("close-save-button")?.addEventListener("click", (e) => {
    e.preventDefault();
    Modal.close("close-confirm");
    const name = client.state?.showfile_name;
    if (!name || name === "Untitled") {
      _pendingCloseAfterSave = true;   // show_saved bestaetigt das Beenden
      _openSaveAsModal();
      return;
    }
    // Nachrichten kommen auf derselben Verbindung in Reihenfolge an: der Server
    // beendet erst, nachdem das Speichern durchgelaufen ist.
    client.send("save_show", { panels_ui: collectAllPanelUiStates() });
    client.send("close_decision", { choice: "save" });
  });

  document.getElementById("close-discard-button")?.addEventListener("click", (e) => {
    e.preventDefault();
    Modal.close("close-confirm");
    client.send("close_decision", { choice: "discard" });
  });

  document.getElementById("close-cancel-button")?.addEventListener("click", (e) => {
    e.preventDefault();
    _pendingCloseAfterSave = false;
    fetch("/api/update/disarm", { method: "POST" }).catch(() => {});             // abgebrochen: ein vorgemerktes Update-Setup nicht doch noch starten
    Modal.close("close-confirm");
  });

  // Enter im Beenden-Dialog = Speichern & Beenden. Esc schliesst den Dialog ueber
  // den Modal-Stack wie "Abbrechen".
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" || !Modal.isOpen("close-confirm")) return;
    e.preventDefault();
    document.getElementById("close-save-button")?.click();
  });

  // Speichern unter... abgebrochen: das Beenden nicht spaeter ungewollt bestaetigen.
  document.querySelectorAll('[data-modal-close="save-show-as"], [data-modal-cancel="save-show-as"]')
    .forEach((el) => el.addEventListener("click", () => { _pendingCloseAfterSave = false; }));
}

function setupFileMenu() {
  const fileMenu = document.querySelector('[data-menu="file"]');
  if (!fileMenu) return;

  fileMenu.addEventListener("click", (e) => {
    const item = e.target.closest("[data-action]");
    if (!item) return;
    const action = item.dataset.action;

    _closeAllMenus();
    if (action === "new-show") {
      // Wenn dirty: Guard oeffnet unsaved-changes, dessen Aktion dann new-show-confirm oeffnet.
      // Wenn clean: direkt new-show-confirm.
      _guardUnsavedChanges(() => Modal.open("new-show-confirm"));
    } else if (action === "open-show") {
      window.OCFileManager.open("shows");              // das Oeffnen selbst fragt bei ungespeicherten Aenderungen nach
    } else if (action === "save-show") {
      _saveShowDirect();
    } else if (action === "save-show-as") {
      _openSaveAsModal();
    }
  });

  // ---- Unsaved-Changes-Modal Buttons ----
  document.getElementById("unsaved-save-button")?.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    Modal.close("unsaved-changes");
    const name = client.state?.showfile_name;
    if (!name || name === "Untitled") {
      // Save-As oeffnen; nach show_saved wird _pendingNavAction ausgefuehrt
      _openSaveAsModal();
    } else {
      _saveShowDirect();
      // _pendingNavAction wird in show_saved-Handler ausgefuehrt
    }
  });

  document.getElementById("unsaved-dont-save-button")?.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    Modal.close("unsaved-changes");
    const action = _pendingNavAction;
    _pendingNavAction = null;
    if (action) action();
  });

  document.getElementById("unsaved-cancel-button")?.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    _pendingNavAction = null;
    Modal.close("unsaved-changes");
  });

  // ---- New Show confirm button ----
  document.getElementById("new-show-confirm-button")?.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    Modal.close("new-show-confirm");
    client.send("new_show");
  });

  // ---- Save As confirm button ----
  document.getElementById("save-as-confirm")?.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    const name = (document.getElementById("save-as-name")?.value || "").trim();
    if (!name) return;
    client.send("save_show_as", { name, target: "local", drive: "", panels_ui: collectAllPanelUiStates() });
    Modal.close("save-show-as");
  });

}

// ---- Layout Preset System --------------------------------------------------

function _toLayoutFilename(name) {
  const safe = (name || "").replace(/[\\/:*?"<>|]/g, '_').trim().slice(0, 60) || "layout";
  return safe + ".json";
}

function _closeAllMenus() {
  document.querySelectorAll(".menu").forEach(m => m.classList.remove("menu--open"));
  document.querySelectorAll("[data-submenu]").forEach(m => m.classList.remove("menu__item--submenu-open"));
}

// ---- Layout-Verwaltung: aktuelles Layout, Speichern, Neu, Umbenennen, Duplizieren -------------------------
// Der Server kennt je Geraet das geladene Layout und den gespeicherten Stand (Live-Sync-Baseline); daraus kommt
// "ungespeicherte Aenderungen". Der Client holt diesen Status nach jeder Aenderung und zeigt ihn ueberall an.
let _layoutState = { name: null, filename: null, dirty: false };
let _layoutStatusSeq = 0;
let _layoutStatusTimer = null;

async function _layoutApi(path, body) {
  try {
    const res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    let data = {};
    try { data = await res.json(); } catch { /* leere Antwort */ }
    return { ok: res.ok && data.ok !== false, exists: res.status === 409 && data.error === "exists", data };
  } catch { return { ok: false, exists: false, data: {} }; }
}

function _renderLayoutChip() {
  const chip = document.getElementById("toolbar-layout-chip");
  if (!chip) return;
  const named = !!_layoutState.name;
  document.getElementById("toolbar-layout-name").textContent = named ? _layoutState.name : i18n("LAYOUT_NONE");
  document.getElementById("toolbar-layout-dirty").hidden = !_layoutState.dirty;
  chip.classList.toggle("menubar__layout-chip--dirty", _layoutState.dirty);
  chip.classList.toggle("menubar__layout-chip--none", !named);
  chip.title = (named ? _layoutState.name : i18n("LAYOUT_NONE")) + (_layoutState.dirty ? " - " + i18n("LAYOUT_DIRTY") : "")
    + " (" + i18n("LAYOUT_CHIP_TITLE") + ")";
}

function _applyLayoutStatus(status) {
  _layoutState = { name: status.name || null, filename: status.filename || null, dirty: !!status.dirty };
  const previousLayoutFile = _activeLayoutFilename;
  _activeLayoutName = _layoutState.name;
  _activeLayoutFilename = _layoutState.filename;
  if (previousLayoutFile !== _activeLayoutFilename) refreshLocalScales();
  _renderLayoutChip();
  _notifyFileManager("layouts");
}

async function _refreshLayoutStatus() {
  const seq = ++_layoutStatusSeq;
  try {
    const res = await fetch("/api/layouts/status");
    const status = await res.json();
    if (seq === _layoutStatusSeq) _applyLayoutStatus(status);
    return status;
  } catch { return _layoutState; }
}

function _scheduleLayoutStatus() {
  clearTimeout(_layoutStatusTimer);
  _layoutStatusTimer = setTimeout(_refreshLayoutStatus, 150);
}

/** Layout-Liste und -Status neu holen (nach Aenderungen an den Layout-Dateien, auch von anderen Geraeten). */
function _onLayoutsChanged() {
  _refreshLayoutsSubmenu();
  _scheduleLayoutStatus();
  _notifyFileManager("layouts");
}

// Dialoge, die ein Ergebnis liefern. Schliessen ueber X, Abbrechen oder Escape liefert den Abbruchwert.
function _modalResult(id, cancelValue, wire) {
  return new Promise((resolve) => {
    let done = false;
    const undo = [];
    const finish = (value) => {
      if (done) return;
      done = true;
      delete Modal._hooks[id];
      undo.forEach((fn) => fn());
      Modal.close(id);
      resolve(value);
    };
    const listen = (el, type, fn) => { el.addEventListener(type, fn); undo.push(() => el.removeEventListener(type, fn)); };
    Modal._hooks[id] = () => finish(cancelValue);
    wire(finish, listen);
    Modal.open(id);
  });
}

function _askLayoutName({ title, confirmKey, value = "", note = "", labelKey = "LAYOUT_NAME_LABEL", labelText = "" }) {
  const labelEl = document.querySelector('label[for="layout-name-prompt-input"]');
  if (labelEl) { if (labelText) delete labelEl.dataset.i18n; else labelEl.dataset.i18n = labelKey; labelEl.textContent = labelText || i18n(labelKey); }      // dieselbe Abfrage dient auch den Buehnen (eigene Beschriftung)
  const input = document.getElementById("layout-name-prompt-input");
  const ok = document.getElementById("layout-name-prompt-confirm");
  const noteEl = document.getElementById("layout-name-prompt-note");
  document.getElementById("layout-name-prompt-title").textContent = title;
  ok.textContent = i18n(confirmKey);
  noteEl.hidden = !note;
  noteEl.textContent = note;
  input.value = value;
  setTimeout(() => { input.focus(); input.select(); }, 60);
  return _modalResult("layout-name-prompt", null, (finish, listen) => {
    const accept = () => {
      const name = input.value.trim();
      if (!name) { input.focus(); return; }
      finish(name);
    };
    listen(ok, "click", accept);
    listen(input, "keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); accept(); } });
  });
}

function _askLayoutConfirm({ title, body, confirmKey }) {
  document.getElementById("layout-confirm-title").textContent = title;
  document.getElementById("layout-confirm-body").textContent = body;
  const ok = document.getElementById("layout-confirm-ok");
  ok.textContent = i18n(confirmKey);
  return _modalResult("layout-confirm", false, (finish, listen) => {
    listen(ok, "click", () => finish(true));
  });
}

/** "save" | "discard" | "cancel". options.body ersetzt den Text (die 3D-Buehne nutzt denselben Dialog fuer Raum und Rig). */
function _askExitEdit(name, options) {
  document.getElementById("layout-exit-edit-body").textContent = (options && options.body) || i18n("LAYOUT_EXIT_BODY").replace("{name}", name || "");
  return _modalResult("layout-exit-edit", "cancel", (finish, listen) => {
    listen(document.getElementById("layout-exit-edit-save"), "click", () => finish("save"));
    listen(document.getElementById("layout-exit-edit-discard"), "click", () => finish("discard"));
    listen(document.getElementById("layout-exit-edit-continue"), "click", () => finish("cancel"));
  });
}

/** Bestaetigung "X existiert bereits - ueberschreiben?" */
function _askOverwrite(name) {
  return _askLayoutConfirm({
    title: i18n("LAYOUT_EXISTS_TITLE"),
    body: i18n("LAYOUT_EXISTS_BODY").replace("{name}", name),
    confirmKey: "LAYOUT_OVERWRITE",
  });
}

function _layoutFailed() { _showToast("LAYOUT_ACTION_FAILED", "error", 4000); }

/** Speichert die Panels unter `name`. Liefert "ok", "exists" (andere Datei dieses Namens, nicht bestaetigt) oder "error". */
async function _saveCurrentLayout(name, overwrite = false) {
  if (!name) return "error";
  const result = await _layoutApi("/api/layouts/save", { name, panels_ui: collectAllPanelUiStates(), overwrite });
  if (!result.ok) return result.exists ? "exists" : "error";
  const scaleKeyBefore = layoutScaleKey();
  _activeLayoutName = name;
  _activeLayoutFilename = result.data.filename;
  copyLocalScales(scaleKeyBefore, layoutScaleKey());     // Speichern unter: die lokale Skalierung zieht mit um
  refreshLocalScales();
  _activeLayoutOrigin = { target: "local", drive: "", filename: result.data.filename, filepath: "" };
  _rememberDeviceLayout(result.data.filename);
  await _refreshLayoutStatus();
  _refreshLayoutsSubmenu();
  return "ok";
}

/** Speichern unter einem neuen Namen (fragt nach; warnt, bevor eine andere Datei ueberschrieben wuerde). */
async function _saveLayoutWithPrompt() {
  let value = "";
  for (;;) {
    const name = await _askLayoutName({ title: i18n("LAYOUT_SAVE_TITLE"), confirmKey: "LAYOUT_SAVE_CONFIRM", value });
    if (!name) return false;
    let outcome = await _saveCurrentLayout(name);
    if (outcome === "exists") {
      if (!(await _askOverwrite(name))) { value = name; continue; }
      outcome = await _saveCurrentLayout(name, true);
    }
    if (outcome !== "ok") { _layoutFailed(); return false; }
    _showToast(i18n("LAYOUT_SAVED_TOAST").replace("{name}", name), "info", 2500);
    return true;
  }
}

/** "Speichern": ueberschreibt das aktuell geladene Layout; ohne geladenes Layout wird nach einem Namen gefragt. */
async function _saveLayoutDirect() {
  await _refreshLayoutStatus();
  if (!_layoutState.name) return _saveLayoutWithPrompt();
  const name = _layoutState.name;
  const outcome = await _saveCurrentLayout(name);
  if (outcome === "ok") {
    _showToast(i18n("LAYOUT_SAVED_TOAST").replace("{name}", name), "info", 2500);
    return true;
  }
  if (outcome === "exists") {   // Datei des Layouts passt nicht zum Namen: wie "Speichern unter" mit Warnung behandeln
    if (!(await _askOverwrite(name))) return false;
    if ((await _saveCurrentLayout(name, true)) === "ok") return true;
  }
  _layoutFailed();
  return false;
}

/** "Neu": leeres Layout unter einem Namen anlegen und laden. */
async function _layoutNewFlow() {
  const note = _layoutState.dirty ? i18n("LAYOUT_NEW_DIRTY_WARNING") : "";
  let value = "";
  for (;;) {
    const name = await _askLayoutName({ title: i18n("LAYOUT_NEW_TITLE"), confirmKey: "LAYOUT_NEW_CONFIRM", value, note });
    if (!name) return false;
    let result = await _layoutApi("/api/layouts/new", { name });
    if (result.exists) {
      if (!(await _askOverwrite(name))) { value = name; continue; }
      result = await _layoutApi("/api/layouts/new", { name, overwrite: true });
    }
    if (!result.ok) { _layoutFailed(); return false; }
    _activeLayoutOrigin = { target: "local", drive: "", filename: result.data.filename, filepath: "" };
    _rememberDeviceLayout(result.data.filename);
    await _refreshLayoutStatus();
    _refreshLayoutsSubmenu();
    return true;
  }
}

/** Bearbeitungsmodus ein-/ausschalten. Beim Verlassen mit ungespeicherten Aenderungen: Speichern / Verwerfen / Weiter bearbeiten. */
async function toggleEditModeInteractive() {
  if (!isEditMode) { setEditMode(true); return; }
  const status = await _refreshLayoutStatus();
  if (status && status.dirty) {
    const choice = await _askExitEdit(status.name);
    if (choice === "cancel") return;
    if (choice === "save") {
      if (!(await _saveLayoutDirect())) return;      // Speichern abgebrochen/fehlgeschlagen: im Bearbeitungsmodus bleiben
    } else {
      await _loadLayoutByFilename(status.filename, status.name);   // verwerfen = gespeicherten Stand neu laden
    }
  }
  setEditMode(false);
}

function _saveShowDirect() {
  const name = client.state?.showfile_name;
  if (!name || name === "Untitled") { _openSaveAsModal(); return; }
  client.send("save_show", { panels_ui: collectAllPanelUiStates() });
}


async function _loadLayoutByFilename(filename, name) {
  try {
    const res = await fetch("/api/layouts/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename }),
    });
    const data = await res.json();
    if (data.ok) {
      _activeLayoutName = name;
      _activeLayoutFilename = filename;
      refreshLocalScales();                       // Skalierung dieses Geraets fuer das neu geladene Layout
      _activeLayoutOrigin = { target: "local", drive: "", filename, filepath: "" };
      _rememberDeviceLayout(filename);
      _closeAllMenus();
      _refreshLayoutsSubmenu(); // Hervorhebung sofort aktualisieren
      await _refreshLayoutStatus();
    }
  } catch { /* noop */ }
}

// ---- Live-Sync: ein offenes Layout wurde von einem anderen Geraet ueberschrieben ------------------------------
// Ohne eigene ungespeicherte Aenderungen uebernimmt der Server die neue Anordnung selbst (applied = true, nur ein
// kurzer Hinweis). Mit eigenen Aenderungen wird nichts ueberschrieben: ein nicht blockierender Hinweis bietet
// "Uebernehmen" oder "Eigene Version behalten" an.
function _removeLayoutUpdateBanner() {
  document.getElementById("layout-update-banner")?.remove();
}

function _handleLayoutUpdateNotice(notice) {
  _removeLayoutUpdateBanner();
  if (notice.applied) {
    _showToast(i18n("LAYOUT_UPDATED_APPLIED").replace("{name}", notice.name), "info", 4500);
    return;
  }
  const banner = document.createElement("div");
  banner.id = "layout-update-banner";
  banner.className = "layout-update-banner";
  banner.setAttribute("role", "status");
  const text = document.createElement("span");
  text.className = "layout-update-banner__text";
  text.textContent = i18n("LAYOUT_UPDATED_PENDING");
  const take = document.createElement("button");
  take.type = "button";
  take.className = "modal__button modal__button--primary";
  take.dataset.action = "take";
  take.textContent = i18n("LAYOUT_UPDATE_TAKE");
  take.addEventListener("click", async () => {
    _removeLayoutUpdateBanner();
    await _loadLayoutByFilename(notice.filename, notice.name);
  });
  const keep = document.createElement("button");
  keep.type = "button";
  keep.className = "modal__button";
  keep.dataset.action = "keep";
  keep.textContent = i18n("LAYOUT_UPDATE_KEEP");
  keep.addEventListener("click", _removeLayoutUpdateBanner);
  banner.append(text, take, keep);
  document.body.appendChild(banner);
}

// ---- Layout je Geraet merken --------------------------------------------------------------
// Die Layout-Dateien liegen zentral auf dem Server (einzige Quelle der Wahrheit). Jedes Geraet merkt sich nur
// lokal, welches Layout es zuletzt geladen oder gespeichert hat, und holt es nach einem Neuladen der Seite
// wieder - sofern der Server (Sitzung/Host) nicht ohnehin schon dieses Layout zeigt. Dadurch verwirft ein
// blosses Neuladen keine ungespeicherten Aenderungen im geladenen Layout.
const DEVICE_LAYOUT_KEY = "opencue.lastLayout";
let _deviceLayoutRestored = false;

function _rememberDeviceLayout(filename) {
  try { localStorage.setItem(DEVICE_LAYOUT_KEY, filename); } catch (error) { /* privates Fenster */ }
}

async function _restoreDeviceLayout(snapshot) {
  if (_deviceLayoutRestored) return;
  _deviceLayoutRestored = true;
  let stored = null;
  try { stored = localStorage.getItem(DEVICE_LAYOUT_KEY); } catch (error) { /* privates Fenster */ }
  if (!stored) return;
  const activeFile = snapshot.last_active_layout ? _toLayoutFilename(snapshot.last_active_layout) : null;
  if (stored === activeFile) return;                       // der Server zeigt dieses Layout bereits
  const match = (await _fetchLayouts()).find((layout) => layout.filename === stored);
  if (!match) {
    // Das Layout wurde geloescht: Erinnerung verwerfen. Das Geraet bleibt beim Stand des Servers
    // (Layout des Hauptrechners bzw. zuletzt gezeigtes Layout) statt in einen Fehler zu laufen.
    try { localStorage.removeItem(DEVICE_LAYOUT_KEY); } catch (error) { /* privates Fenster */ }
    return;
  }
  await _loadLayoutByFilename(match.filename, match.name);
}

async function _fetchLayouts() {
  try {
    const res = await fetch("/api/layouts");
    return await res.json();
  } catch { return []; }
}

async function _deleteLayoutByFilename(filename) {
  try {
    const res = await fetch("/api/layouts/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename }),
    });
    return (await res.json()).ok;
  } catch { return false; }
}

/** Layout loeschen; war es das geladene, wird auf ein verbleibendes gewechselt. true = geloescht. */
async function _deleteLayoutAndSwitch(filename) {
  const wasActive = (_activeLayoutFilename === filename);
  const ok = await _deleteLayoutByFilename(filename);
  if (ok && wasActive) {
    _activeLayoutName = null;
    _activeLayoutFilename = null;
    refreshLocalScales();
    const remaining = await _fetchLayouts();
    if (remaining.length > 0) {
      const next = remaining[0];
      await _loadLayoutByFilename(next.filename, next.name);
    }
  }
  _refreshLayoutsSubmenu();
  return ok;
}

async function _toggleFavoriteLayout(filename) {
  try {
    await fetch("/api/layouts/favorite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename }),
    });
    _refreshLayoutsSubmenu();
  } catch { /* noop */ }
}

const _layoutAlpha = (a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" });

/** Layouts in der Reihenfolge von Strg+1-9 (Favoriten A-Z, dann die uebrigen A-Z). */
function _orderedLayouts(layouts) {
  return [...layouts.filter(l => l.is_favorite).sort(_layoutAlpha), ...layouts.filter(l => !l.is_favorite).sort(_layoutAlpha)];
}

/** Zum naechsten (+1) bzw. vorherigen (-1) Layout in der Strg+1-9-Reihenfolge wechseln (am Ende springt es herum). */
async function _stepLayout(direction) {
  const ordered = _orderedLayouts(await _fetchLayouts());
  if (ordered.length < 2) return;
  const index = ordered.findIndex(l => l.filename === _activeLayoutFilename);
  const next = ordered[index < 0 ? (direction > 0 ? 0 : ordered.length - 1) : (index + direction + ordered.length) % ordered.length];
  await _loadLayoutByFilename(next.filename, next.name);
  _showToast(next.name, "info", 1800, true);
}

async function _refreshLayoutsSubmenu() {
  const submenu = document.getElementById("layouts-submenu");
  if (!submenu) return;

  let layouts = [];
  try {
    const res = await fetch("/api/layouts");
    layouts = await res.json();
  } catch { layouts = []; }

  // Unveraendert? Dann die vorhandenen Eintraege stehen lassen: ein Neuaufbau waehrend des Tippens (Touch loest
  // nach dem Tipp emulierte Hover-Ereignisse aus, die dieses Auffrischen anstossen) wuerde den Eintrag unter dem
  // Finger austauschen und den Tipp verschlucken.
  const signature = JSON.stringify([layouts.map(l => [l.filename, l.name, !!l.is_favorite]), _activeLayoutFilename, i18n("LAYOUT_EMPTY")]);
  if (submenu.dataset.signature === signature && submenu.childElementCount) return;
  submenu.dataset.signature = signature;
  submenu.innerHTML = "";

  if (layouts.length === 0) {
    const empty = document.createElement("li");
    empty.className = "menu__item menu__item--empty";
    empty.dataset.i18n = "LAYOUT_EMPTY";
    empty.textContent = i18n("LAYOUT_EMPTY");
    submenu.appendChild(empty);
    return;
  }

  // Hilfsfunktion: erzeugt einen vollständigen Layout-Eintrag
  const makeItem = (layout, shortcutIdx) => {
    const li = document.createElement("li");
    li.className = "menu__item menu__item--layout";
    if (layout.filename === _activeLayoutFilename) li.classList.add("menu__item--active");

    const star = document.createElement("button");
    star.type = "button";
    star.className = "layout-star" + (layout.is_favorite ? " layout-star--active" : "");
    star.title = i18n(layout.is_favorite ? "LAYOUT_UNFAVORITE" : "LAYOUT_FAVORITE");
    star.textContent = "★";
    star.addEventListener("click", (e) => {
      e.stopPropagation();
      _toggleFavoriteLayout(layout.filename);
    });

    const nameSpan = document.createElement("span");
    nameSpan.className = "layout-item__name";
    nameSpan.textContent = layout.name;
    nameSpan.addEventListener("click", () => _loadLayoutByFilename(layout.filename, layout.name));

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "layout-delete-btn";
    deleteBtn.title = i18n("LAYOUT_DELETE_TITLE");
    deleteBtn.textContent = "✕";
    deleteBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      _layoutPendingDeleteFilename = layout.filename;
      _layoutPendingDeleteName = layout.name;
      const body = document.getElementById("layout-delete-confirm-body");
      if (body) body.textContent = i18n("LAYOUT_DELETE_BODY").replace("{name}", layout.name);
      Modal.open("layout-delete-confirm");
    });

    li.appendChild(star);
    li.appendChild(nameSpan);
    if (shortcutIdx >= 0 && shortcutIdx < 9) {
      const badge = document.createElement("span");
      badge.className = "layout-item__shortcut";
      badge.textContent = `${i18n("SHORTCUT_CTRL_KEY")}+${shortcutIdx + 1}`;
      li.appendChild(badge);
    }
    li.appendChild(deleteBtn);
    return li;
  };

  // Stabile Reihenfolge: Gruppe 1 = Favoriten A–Z, Gruppe 2 = Nicht-Favoriten A–Z.
  // Das aktive Layout wird NUR visuell hervorgehoben (menu__item--active), bleibt
  // aber an seiner alphabetischen Position — Strg+1–9 Nummern springen nie.
  const favs    = layouts.filter(l =>  l.is_favorite).sort(_layoutAlpha);
  const normals = layouts.filter(l => !l.is_favorite).sort(_layoutAlpha);

  _cachedLayouts = [...favs, ...normals];

  favs.forEach((l, i) => submenu.appendChild(makeItem(l, i)));
  if (favs.length > 0 && normals.length > 0) {
    const sep = document.createElement("li");
    sep.className = "layout-separator";
    sep.setAttribute("role", "separator");
    submenu.appendChild(sep);
  }
  normals.forEach((l, i) => submenu.appendChild(makeItem(l, favs.length + i)));
}

function setupLayoutMenu() {
  // Layouts-Submenu bei Hover über das View-Menü / den Menüeintrag auffrischen
  const viewMenu = document.querySelector('[data-menu="view"]');
  if (viewMenu) {
    viewMenu.addEventListener("mouseenter", _refreshLayoutsSubmenu);
  }
  const layoutsItem = document.getElementById("layouts-menu-item");
  if (layoutsItem) {
    layoutsItem.addEventListener("mouseenter", _refreshLayoutsSubmenu);
  }

  _renderLayoutChip();

  // Modal: Layout löschen bestätigen
  document.getElementById("layout-delete-confirm-button")?.addEventListener("click", async (e) => {
    e.preventDefault(); e.stopPropagation();
    Modal.close("layout-delete-confirm");
    if (_layoutPendingDeleteFilename) {
      const filename = _layoutPendingDeleteFilename;
      _layoutPendingDeleteFilename = null;
      _layoutPendingDeleteName = null;
      await _deleteLayoutAndSwitch(filename);
    }
  });
}

// ---- Language toggle helper -------------------------------------------------

function _toggleLanguage() {
  const current = client.state?.language || "en";
  const next = current === "en" ? "de" : "en";
  translator.setLanguage(next).then(() => {
    client.send("set_language", { language: next });
  });
}

// ---- Central Keyboard Shortcut Registry ------------------------------------
// Handles ALL global keyboard shortcuts in one place.
// Guards: Ctrl+N / Ctrl+O skip when focus is in a text input.
//         Ctrl+S / Ctrl+Shift+S work everywhere (safe to use in modal name fields).

function setupKeyboardShortcuts() {
  document.addEventListener("keydown", (e) => {
    const ctrl = e.ctrlKey || e.metaKey;
    const tag = document.activeElement?.tagName;
    const isInput = tag === "INPUT" || tag === "TEXTAREA" ||
                    document.activeElement?.contentEditable === "true";

    // F11 — fullscreen toggle
    if (e.key === "F11") {
      e.preventDefault();
      toggleFullscreen();
      return;
    }

    // Ctrl+S — save (fires even in text inputs, e.g. "Save As" name field)
    if (ctrl && !e.shiftKey && e.key === "s") {
      e.preventDefault();
      const name = client.state?.showfile_name;
      if (!name || name === "Untitled") { _openSaveAsModal(); } else { _saveShowDirect(); }
      return;
    }

    // Ctrl+Shift+S — save as (fires even in text inputs)
    if (ctrl && e.shiftKey && e.key === "S") {
      e.preventDefault();
      _openSaveAsModal();
      return;
    }

    // Suppress all remaining shortcuts while a text input has focus
    if (isInput) return;

    // Ctrl+C / Ctrl+X / Ctrl+V — markierte Panels kopieren / ausschneiden / einfuegen (nur im Bearbeitungsmodus)
    if (isEditMode && ctrl && !e.shiftKey && !e.altKey && !Modal._stack.length) {
      const key = e.key.toLowerCase();
      if ((key === "c" || key === "x") && copySelectedPanels(key === "x")) { e.preventDefault(); return; }
      if (key === "v" && pasteCopiedPanels()) { e.preventDefault(); return; }
    }

    // Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z — Undo/Redo fuer Panel-Aenderungen (server-seitig). NUR im Bearbeitungsmodus: ausserhalb tut das Kuerzel nichts.
    if (isEditMode && ctrl && !e.shiftKey && e.key.toLowerCase() === "z") {
      e.preventDefault();
      client.send("undo");
      return;
    }
    if (isEditMode && ctrl && (e.key.toLowerCase() === "y" || (e.shiftKey && e.key.toLowerCase() === "z"))) {
      e.preventDefault();
      client.send("redo");
      return;
    }

    // Ctrl+Q — exit application
    if (ctrl && !e.shiftKey && e.key === "q") {
      e.preventDefault();
      client.send("exit_app");
      return;
    }

    // Ctrl+E — toggle panel edit mode
    if (ctrl && !e.shiftKey && e.key === "e") {
      e.preventDefault();
      toggleEditModeInteractive();
      return;
    }

    // Ctrl+Shift+L — toggle language (en ↔ de)
    if (ctrl && e.shiftKey && e.key === "L") {
      e.preventDefault();
      _toggleLanguage();
      return;
    }

    // Ctrl+N — new show (with unsaved-changes guard)
    if (ctrl && !e.shiftKey && e.key === "n") {
      e.preventDefault();
      _guardUnsavedChanges(() => Modal.open("new-show-confirm"));
      return;
    }

    // Ctrl+O — open show (Dateimanager, Art "Shows"; das Oeffnen fragt bei ungespeicherten Aenderungen nach)
    if (ctrl && !e.shiftKey && e.key === "o") {
      e.preventDefault();
      window.OCFileManager.open("shows");
      return;
    }

    // Ctrl+0 — reset GUI scale to 100%
    if (ctrl && e.key === "0") {
      e.preventDefault();
      client.setGuiScale(1.0);   // lokal gespeichert, nicht an andere Geraete verteilt
      return;
    }

    // Ctrl++ / Ctrl+= — increase GUI scale
    if (ctrl && !e.shiftKey && (e.key === "+" || e.key === "=")) {
      e.preventDefault();
      const cur = parseFloat(document.documentElement.style.getPropertyValue("--gui-scale")) ||
                  (client.state?.gui_scale ?? 1.0);
      const next = Math.min(SETTINGS_GUI_SCALE_MAX, parseFloat((cur + 0.05).toFixed(2)));
      client.setGuiScale(next);   // lokal gespeichert, nicht an andere Geraete verteilt
      return;
    }

    // Ctrl+- — decrease GUI scale
    if (ctrl && e.key === "-") {
      e.preventDefault();
      const cur = parseFloat(document.documentElement.style.getPropertyValue("--gui-scale")) ||
                  (client.state?.gui_scale ?? 1.0);
      const next = Math.max(SETTINGS_GUI_SCALE_MIN, parseFloat((cur - 0.05).toFixed(2)));
      client.setGuiScale(next);   // lokal gespeichert, nicht an andere Geraete verteilt
      return;
    }

    // Pfeil links/rechts (ohne Modifier) - vorheriges/naechstes Layout in der Strg+1-9-Reihenfolge. Gilt nicht in
    // Eingabefeldern (oben schon abgefangen), bei offenem Dialog/Menue oder im Bearbeitungsmodus.
    if (!ctrl && !e.shiftKey && !e.altKey && !e.metaKey && (e.key === "ArrowLeft" || e.key === "ArrowRight") &&
        !e.defaultPrevented && !Modal._stack.length && !document.querySelector(".menu--open") && !isEditMode &&
        !(e.target.closest && e.target.closest("select, [role='slider'], [contenteditable], .fxprog-numfield"))) {
      e.preventDefault();
      _stepLayout(e.key === "ArrowRight" ? 1 : -1);
      return;
    }

    // Ctrl+1–9 — load layout by index (uses _cachedLayouts set by _refreshLayoutsSubmenu)
    if (ctrl && !e.shiftKey && e.key >= "1" && e.key <= "9") {
      e.preventDefault();
      const layout = _cachedLayouts[parseInt(e.key) - 1];
      if (layout) _loadLayoutByFilename(layout.filename, layout.name);
      return;
    }
  });
}

// ---- Help Menu Setup --------------------------------------------------------

function setupHelpMenu() {
  document.querySelector('[data-menu="help"]')?.addEventListener("click", (e) => {
    const item = e.target.closest("[data-action]");
    if (!item) return;
    if (item.dataset.action === "open-shortcuts-modal") {
      _closeAllMenus();
      Modal.open("keyboard-shortcuts");
    } else if (item.dataset.action === "open-github") {
      _closeAllMenus();
      window.open("https://thecraftedtech.github.io/opencue/", "_blank");
    } else if (item.dataset.action === "check-updates") {
      _closeAllMenus();
      if (window.OCUpdate) window.OCUpdate.checkNow(true);
    } else if (item.dataset.action === "open-about-modal") {
      _closeAllMenus();
      if (window.OCAbout) window.OCAbout.open();
    }
  });
}

// ---- Layout Re-Render nach Layout-Wechsel ----------------------------------

/**
 * Dispatcht den aktuellen App-State an alle gemounteten Panel-Plugins.
 * Wird nach einem Layout-Wechsel aufgerufen, damit neu erstellte Panels
 * sofort die aktuelle Live-Ansicht zeigen (Fixture-Grid, Programmer-
 * Selektion, Fader-Positionen, GDTF-Attribute) – ohne auf den nächsten
 * Server-Broadcast zu warten.
 */
function refreshActivePanels() {
  if (!client || !client.state) return;
  client._dispatchToPanelPlugins({ type: "state_snapshot", payload: client.state });
}

// ---------------------------------------------------------------------------

// ---- Showfile-Status ------------------------------------------------------------------------------------------
// Verwaltet wird im Dateimanager (static/js/file_manager.js). Neu, Speichern und Speichern unter bleiben Datei-Menue/Strg+N/S.
// Das Showfile ist global (ein geladenes fuer alle Geraete); "ungespeichert" kommt wie bisher vom Server (_isDirty).

/** Dateimanager (falls offen) ueber eine Aenderung an Dateien oder am geladenen Stand dieser Art informieren. */
function _notifyFileManager(kind) {
  if (window.OCFileManager) window.OCFileManager.changed(kind);
}

/** Status vom Server holen; mit apply=true auch Name und Ungespeichert-Marke der Menueleiste angleichen. */
async function _refreshShowfileStatus(apply = false) {
  let status;
  try { status = await (await fetch("/api/showfiles/status")).json(); } catch { return; }
  if (apply && client && client.state) {
    client.state.showfile_name = status.name;
    _setDirty(!!status.dirty);
  }
  _notifyFileManager("shows");
}

/** Nach Laden/Speichern/Snapshot: ein offener Dateimanager holt Liste und Stand neu. */
function _onShowfilesChanged() {
  _notifyFileManager("shows");
}

function _openSaveAsModal() {
  Modal.open("save-show-as");
  const input = document.getElementById("save-as-name");
  if (input) {
    input.value = client.state?.showfile_name || "Untitled";
    input.focus();
    input.select();
  }
}

// ---- Panel API (host utilities exposed to panel plugins) -------------------
window.__panelAPI = {
  wireColorPair,
  i18n,
  sendToServer: (type, payload) => client.send(type, payload),
  getState: () => client.state || {},
};

// ---- Inline panel registrations (DMX Monitor + Fixtures) -------------------

(function () {
  "use strict";

  // Letzter bekannter DMX-Output pro Universum (Array[512]).
  // Global (window.__dmxUniverseValueCache) damit auch der Programmer-
  // Plugin-IIFE im DMX-Direct-Tab darauf zugreifen kann.
  window.__dmxUniverseValueCache = window.__dmxUniverseValueCache || {};

  /* ---- Color helpers ---- */
  function dmxValueToColor(value, hex) {
    if (!value) return "#000";
    var r = parseInt(hex.slice(1, 3), 16) || 0;
    var g = parseInt(hex.slice(3, 5), 16) || 0;
    var b = parseInt(hex.slice(5, 7), 16) || 0;
    var f = value / 255;
    return "rgb(" + Math.round(r * f) + "," + Math.round(g * f) + "," + Math.round(b * f) + ")";
  }

  function dmxCellTextColor(value, hex) {
    if (!value) return "transparent";
    var r = parseInt(hex.slice(1, 3), 16) || 0;
    var g = parseInt(hex.slice(3, 5), 16) || 0;
    var b = parseInt(hex.slice(5, 7), 16) || 0;
    var f = value / 255;
    var lum = (r * f * 0.299 + g * f * 0.587 + b * f * 0.114) / 255;
    return lum > 0.45 ? "rgba(0,0,0,0.85)" : "rgba(255,255,255,0.9)";
  }

  // ── Fixture-Gruppierung: zusammengehoerige DMX-Adressen eines Fixtures
  // erhalten eine gemeinsame, farbige Umrandung (Perimeter statt Einzel-
  // Zellrahmen - Nachbarzellen derselben Fixture bleiben ohne Trennlinie). ──
  var FIXTURE_GROUP_COLORS = ["#ff6666", "#66aaff", "#ffcc44", "#66ff99", "#cc88ff", "#ff9944", "#44ddcc", "#ff66cc"];

  function _hashStr(s) {
    var h = 0;
    for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
    return Math.abs(h);
  }

  // border_mode (Panel-Property, strikt getrennt vom Signal-/Kanal-Farbmodus
  // der Zellen-FUELLUNG): "individual" = jede Fixture-Instanz eigene Farbe,
  // "uniform" = alle Umrandungen dieselbe (konfigurierbare) neutrale Farbe,
  // "by_type" = Fixtures desselben GDTF-Typs teilen sich eine Farbe.
  function _fixtureGroupColor(fx, borderMode, borderColor) {
    if (borderMode === "uniform") return borderColor || "#888888";
    if (borderMode === "by_type") return FIXTURE_GROUP_COLORS[_hashStr(fx.fixture_type || "") % FIXTURE_GROUP_COLORS.length];
    return FIXTURE_GROUP_COLORS[(fx.fid != null ? fx.fid : 0) % FIXTURE_GROUP_COLORS.length];
  }

  // Kanalname -> Farbkategorie (fuer "Kanal-Farben"-Modus). Nutzt dieselbe
  // Namenskonvention wie die Feature-Erkennung im Programmer-Panel.
  var CHANNEL_COLOR_CATEGORY = [
    [/coloradd_r|^red/i, "#ff3b3b"],
    [/coloradd_g|^green/i, "#3bff3b"],
    [/coloradd_b|^blue/i, "#3b8bff"],
    [/colorsub_c|^cyan/i, "#00ffff"],
    [/colorsub_m|magenta/i, "#ff00ff"],
    [/colorsub_y|yellow/i, "#ffe600"],
    [/coloradd_w|^white/i, "#ffffff"],
    [/pan|tilt/i, "#9aa0a6"],
    [/dim|intensity/i, "#00ff00"],
    [/gobo|prism|iris|frost|shutter|strobe/i, "#ffa63b"],
    [/focus|zoom/i, "#b083ff"],
  ];
  function _channelColorCategory(name) {
    if (!name) return null;
    for (var i = 0; i < CHANNEL_COLOR_CATEGORY.length; i++) {
      if (CHANNEL_COLOR_CATEGORY[i][0].test(name)) return CHANNEL_COLOR_CATEGORY[i][1];
    }
    return null;
  }

  // Fixture-Typen-Cache (fuer Kanalname-Aufloesung im "Kanal-Farben"-Modus
  // sowie fuer die Gruppierungs-Kanalliste) - eigener kleiner Cache statt
  // Zugriff auf den Programmer-eigenen (andere IIFE/Modul-Scope).
  var _dmxFixtureTypesCache = null;
  var _dmxFixtureTypesPromise = null;
  document.addEventListener("fixture-library-changed", function () { _dmxFixtureTypesCache = null; _dmxFixtureTypesPromise = null; });
  function _loadDmxFixtureTypes(cb) {
    if (_dmxFixtureTypesCache) { cb(_dmxFixtureTypesCache); return; }
    if (!_dmxFixtureTypesPromise) {
      _dmxFixtureTypesPromise = fetch("/fixture-types")
        .then(function (r) { return r.json(); })
        .then(function (t) { _dmxFixtureTypesCache = t; return t; })
        .catch(function () { _dmxFixtureTypesCache = []; return []; });
    }
    _dmxFixtureTypesPromise.then(cb);
  }

  function _channelsForFixtureType(fx, types) {
    var ft = null;
    for (var i = 0; i < types.length; i++) { if (types[i].id === fx.fixture_type) { ft = types[i]; break; } }
    if (!ft) return [];
    var modes = ft.modes || [];
    var modeDef = null;
    for (var j = 0; j < modes.length; j++) { if (modes[j].name === fx.mode) { modeDef = modes[j]; break; } }
    if (!modeDef) modeDef = modes[0];
    return modeDef ? (modeDef.channels || []) : [];
  }

  // Einmal pro Fixture-/Universe-Aenderung berechnete Kanal-Info: welches
  // Fixture (+ Gruppierungsfarbe + Kanalname) liegt auf welcher DMX-Adresse.
  // Wird sowohl fuer die Gruppierungs-Umrandung als auch fuer den "Kanal-
  // Farben"-Anzeigemodus verwendet, um doppelte Arbeit zu vermeiden.
  function _buildChannelInfo(monitorEl) {
    var universe = parseInt(monitorEl.dataset.universe, 10) || 1;
    var fixtures = (client.state && client.state.fixtures) || {};
    var types = _dmxFixtureTypesCache || [];
    var borderMode = monitorEl.dataset.borderMode || "individual";
    var borderColor = monitorEl.dataset.borderColor || "#888888";
    var info = {};
    Object.keys(fixtures).forEach(function (fxId) {
      var fx = fixtures[fxId];
      if (fx.universe !== universe) return;
      var groupColor = _fixtureGroupColor(fx, borderMode, borderColor);
      var channels = _channelsForFixtureType(fx, types);
      var byOffset = {};
      channels.forEach(function (c) { byOffset[c.offset] = c.name; });
      var count = fx.channel_count || 1;
      for (var i = 0; i < count; i++) {
        var ch = fx.start_channel + i;
        if (ch >= 1 && ch <= 512) {
          info[ch] = {
            id: fxId,
            groupColor: groupColor,
            channelName: byOffset[i] || null,
            fidLabel: i === 0 ? (fx.fid != null ? String(fx.fid) : "?") : null,
          };
        }
      }
    });
    return info;
  }

  function _getChannelInfo(monitorEl, forceRebuild) {
    if (forceRebuild || !monitorEl._channelInfo) monitorEl._channelInfo = _buildChannelInfo(monitorEl);
    return monitorEl._channelInfo;
  }

  // Fixture-Gruppierung: farbige Perimeter-Umrandung via box-shadow (siehe
  // .dmx-cell--grouped) statt border-color - so bleibt das normale Grund-
  // Kachelraster (border: 1px solid var(--border-color)) IMMER sichtbar,
  // auch innerhalb einer Gruppe.
  function applyFixtureGrouping(monitorEl, info) {
    info = info || _getChannelInfo(monitorEl);
    function sameGroup(n, id) { return !!n && n.id === id; }
    monitorEl.querySelectorAll(".dmx-cell[data-channel]").forEach(function (cell) {
      var ch = parseInt(cell.dataset.channel, 10);
      var grp = info[ch];
      if (!grp) {
        cell.classList.remove("dmx-cell--grouped");
        ["--grp-l", "--grp-r", "--grp-t", "--grp-b"].forEach(function (v) { cell.style.removeProperty(v); });
        delete cell.dataset.fidLabel;
        return;
      }
      cell.classList.add("dmx-cell--grouped");
      var col = (ch - 1) % 10;
      cell.style.setProperty("--grp-l", (col > 0 && sameGroup(info[ch - 1], grp.id)) ? "transparent" : grp.groupColor);
      cell.style.setProperty("--grp-r", (col < 9 && sameGroup(info[ch + 1], grp.id)) ? "transparent" : grp.groupColor);
      cell.style.setProperty("--grp-t", sameGroup(info[ch - 10], grp.id) ? "transparent" : grp.groupColor);
      cell.style.setProperty("--grp-b", sameGroup(info[ch + 10], grp.id) ? "transparent" : grp.groupColor);
      if (grp.fidLabel) { cell.dataset.fidLabel = grp.fidLabel; } else { delete cell.dataset.fidLabel; }
    });
  }

  // color_mode: "signal" (Modus 1, Standardfarbe/Grau mit dynamischer
  // Signalstaerke - highlight_color aus den Panel-Properties) oder
  // "channel" (Modus 2, Farbe je Attribut/RGB aus CHANNEL_COLOR_CATEGORY).
  // Der Textknoten bleibt immer bestehen (bei 0 nur unsichtbar): ein leerer Knoten wird im Layout entfernt und wieder angelegt,
  // das kostet auf einem iPad pro Wechsel ein Neuberechnen der ganzen Tabelle.
  function _setCellValue(cell, v) {
    var valueEl = cell.firstElementChild;
    if (!valueEl || !valueEl.classList.contains("dmx-cell__v")) {
      cell.textContent = "";
      valueEl = document.createElement("span");
      valueEl.className = "dmx-cell__v";
      cell.appendChild(valueEl);
    }
    var text = String(v);
    var node = valueEl.firstChild;
    if (!node) valueEl.textContent = text;
    else if (node.nodeValue !== text) node.nodeValue = text;
    var hidden = v <= 0;
    if (cell._zeroHidden !== hidden) {
      valueEl.style.visibility = hidden ? "hidden" : "";
      cell._zeroHidden = hidden;
    }
  }

  function applyDmxCellColors(monitorEl, info, onlyCells) {
    var highlight = monitorEl.dataset.highlightColor || "#00ff00";
    var mode = monitorEl.dataset.colorMode || "signal";
    if (mode === "channel") info = info || _getChannelInfo(monitorEl);
    (onlyCells || monitorEl.querySelectorAll(".dmx-cell[data-channel]")).forEach(function (cell) {
      var v = parseInt(cell.dataset.value || "0", 10);
      var base = highlight;
      if (mode === "channel") {
        var grp = info && info[parseInt(cell.dataset.channel, 10)];
        var cat = grp ? _channelColorCategory(grp.channelName) : null;
        if (cat) base = cat;
      }
      cell.style.backgroundColor = dmxValueToColor(v, base);
      cell.style.color = dmxCellTextColor(v, base);
      _setCellValue(cell, v);
    });
  }

  // Kennung des Fixture-Patches (ohne die laufenden Werte): aendert sie sich nicht, bleibt die Kanal-Info gueltig
  function _patchSignature(fixtures) {
    return Object.keys(fixtures || {}).map(function (id) {
      var fx = Object.assign({}, fixtures[id]);
      delete fx.values;
      return JSON.stringify(fx);
    }).join("|");
  }

  function _refreshMonitor(monitorEl, forceRebuild) {
    var info = _getChannelInfo(monitorEl, forceRebuild);
    applyFixtureGrouping(monitorEl, info);
    applyDmxCellColors(monitorEl, info);
  }

  /* ---- Table builder ---- */
  function buildTable(universe) {
    var table = document.createElement("table");
    table.className = "dmx-monitor__table";

    var thead = document.createElement("thead");
    var headerRow = document.createElement("tr");
    var corner = document.createElement("th");
    corner.className = "dmx-monitor__corner";
    corner.textContent = "Address";
    headerRow.appendChild(corner);
    for (var col = 1; col <= 10; col++) {
      var th = document.createElement("th");
      th.className = "dmx-monitor__col-header";
      th.textContent = col;
      headerRow.appendChild(th);
    }
    thead.appendChild(headerRow);
    table.appendChild(thead);

    var tbody = document.createElement("tbody");
    for (var row = 0; row < 52; row++) {
      var startCh = row * 10 + 1;
      if (startCh > 512) break;
      var tr = document.createElement("tr");
      var rowHeader = document.createElement("td");
      rowHeader.className = "dmx-monitor__row-header";
      rowHeader.dataset.startChannel = startCh;
      rowHeader.textContent = universe + ". " + startCh;
      tr.appendChild(rowHeader);
      for (var c = 0; c < 10; c++) {
        var ch = startCh + c;
        var td = document.createElement("td");
        if (ch > 512) {
          td.className = "dmx-cell dmx-cell--empty";
        } else {
          td.className = "dmx-cell";
          td.dataset.channel = ch;
          td.dataset.value = "0";
          // Der Zahlenwert steht in einem absolut positionierten Span: eine Textaenderung loest so kein Neuberechnen der ganzen
          // Tabelle aus (das war auf dem iPad der Hauptkostenfaktor: ~25x teurer als der Span)
          var valueEl = document.createElement("span");
          valueEl.className = "dmx-cell__v";
          td.appendChild(valueEl);
        }
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    return table;
  }

  window.__panelPlugins.register({
    type: "dmx_monitor",

    buildContent: function (panel) {
      var mc = panel.module_config || {};
      var highlight = mc.highlight_color || "#00ff00";
      var universe = mc.universe || 1;

      var wrap = document.createElement("div");
      wrap.className = "dmx-monitor";
      wrap.dataset.highlightColor = highlight;
      wrap.dataset.universe = universe;
      wrap.dataset.colorMode = mc.color_mode || "signal";
      wrap.dataset.borderMode = mc.border_mode || "uniform";
      wrap.dataset.borderColor = mc.border_color || "#888888";
      wrap.appendChild(buildTable(universe));
      // Gecachte DMX-Werte sofort eintragen, falls ein vorheriges Broadcast
      // für dieses Universum bekannt ist – verhindert "Alle-Null"-Anzeige
      // nach einem Layout-Wechsel.
      var _cached = window.__dmxUniverseValueCache[universe];
      if (_cached) {
        wrap.querySelectorAll(".dmx-cell[data-channel]").forEach(function (cell) {
          var ch = parseInt(cell.dataset.channel, 10) - 1;
          cell.dataset.value = _cached[ch] || 0;
        });
      }
      setTimeout(function () {
        _loadDmxFixtureTypes(function () { _refreshMonitor(wrap, true); });
      }, 0);
      return wrap;
    },

    onModuleConfigChanged: function (panelEl, mc) {
      var monitor = panelEl.querySelector(".dmx-monitor");
      if (!monitor) return;
      var universe = mc.universe || 1;
      monitor.dataset.highlightColor = mc.highlight_color || "#00ff00";
      monitor.dataset.universe = universe;
      monitor.dataset.colorMode = mc.color_mode || "signal";
      monitor.dataset.borderMode = mc.border_mode || "uniform";
      monitor.dataset.borderColor = mc.border_color || "#888888";
      monitor.querySelectorAll(".dmx-monitor__row-header").forEach(function (th) {
        var startCh = parseInt(th.dataset.startChannel, 10);
        if (!isNaN(startCh)) th.textContent = universe + ". " + startCh;
      });
      _refreshMonitor(monitor, true);
    },

    buildPropertiesPane: function (moduleConfig, api) {
      var mc = moduleConfig || {};
      var frag = document.createDocumentFragment();

      var univRow = document.createElement("div");
      univRow.className = "modal__field";
      var univLabel = document.createElement("label");
      univLabel.htmlFor = "module-settings-universe";
      univLabel.dataset.i18n = "DMX_UNIVERSE";
      univLabel.textContent = api.i18n("DMX_UNIVERSE");
      var univInput = document.createElement("input");
      univInput.type = "number";
      univInput.id = "module-settings-universe";
      univInput.className = "modal__input";
      univInput.min = 1;
      univInput.max = 64;
      univInput.step = 1;
      univInput.value = mc.universe || 1;
      univRow.appendChild(univLabel);
      univRow.appendChild(univInput);
      frag.appendChild(univRow);

      var hlLabelRow = document.createElement("div");
      hlLabelRow.className = "modal__field";
      var hlLabel = document.createElement("label");
      hlLabel.htmlFor = "module-settings-highlight-hex";
      hlLabel.dataset.i18n = "DMX_MONITOR_HIGHLIGHT_COLOR";
      hlLabel.textContent = api.i18n("DMX_MONITOR_HIGHLIGHT_COLOR");
      hlLabelRow.appendChild(hlLabel);
      frag.appendChild(hlLabelRow);

      var hlColorRow = document.createElement("div");
      hlColorRow.className = "modal__field";
      var hlSwatch = document.createElement("input");
      hlSwatch.type = "color";
      hlSwatch.id = "module-settings-highlight-swatch";
      hlSwatch.className = "color-swatch-input";
      hlSwatch.value = mc.highlight_color || "#00ff00";
      var hlHex = document.createElement("input");
      hlHex.type = "text";
      hlHex.id = "module-settings-highlight-hex";
      hlHex.className = "color-hex-input";
      hlHex.maxLength = 7;
      hlHex.value = mc.highlight_color || "#00ff00";
      hlColorRow.appendChild(hlSwatch);
      hlColorRow.appendChild(hlHex);
      frag.appendChild(hlColorRow);

      // Modus 2: Kanal-Farben (bunt je Attribut) statt Standard-Signalfarbe
      var cmRow = document.createElement("div");
      cmRow.className = "modal__field modal__field--checkbox";
      var cmToggle = makeToggleSwitch("module-settings-color-mode", mc.color_mode === "channel");
      var cmLabel = document.createElement("span");
      cmLabel.dataset.i18n = "DMX_MONITOR_CHANNEL_COLORS";
      cmLabel.textContent = api.i18n("DMX_MONITOR_CHANNEL_COLORS");
      cmRow.appendChild(cmToggle.label);
      cmRow.appendChild(cmLabel);
      frag.appendChild(cmRow);

      // Scheinwerfer-Umrandung: individuell/bunt, einheitlich (grau/custom),
      // oder nach Scheinwerfer-Typ gruppiert - strikt getrennt vom Signal-/
      // Kanal-Farbmodus der Zellen-FUELLUNG oben.
      var bmLabelRow = document.createElement("div");
      bmLabelRow.className = "modal__field";
      var bmLabel = document.createElement("label");
      bmLabel.htmlFor = "module-settings-border-mode";
      bmLabel.dataset.i18n = "DMX_MONITOR_BORDER_MODE";
      bmLabel.textContent = api.i18n("DMX_MONITOR_BORDER_MODE");
      bmLabelRow.appendChild(bmLabel);
      frag.appendChild(bmLabelRow);

      var bmRow = document.createElement("div");
      bmRow.className = "modal__field";
      var bmSelect = document.createElement("select");
      bmSelect.id = "module-settings-border-mode";
      bmSelect.className = "modal__input";
      [
        ["individual", "DMX_MONITOR_BORDER_INDIVIDUAL"],
        ["uniform",    "DMX_MONITOR_BORDER_UNIFORM"],
        ["by_type",    "DMX_MONITOR_BORDER_BY_TYPE"],
      ].forEach(function ([val, key]) {
        var opt = document.createElement("option");
        opt.value = val;
        opt.dataset.i18n = key;
        opt.textContent = api.i18n(key);
        if (val === (mc.border_mode || "uniform")) opt.selected = true;
        bmSelect.appendChild(opt);
      });
      bmRow.appendChild(bmSelect);
      frag.appendChild(bmRow);

      var bcRow = document.createElement("div");
      bcRow.className = "modal__field";
      bcRow.id = "module-settings-border-color-row";
      bcRow.style.display = (mc.border_mode === "uniform") ? "" : "none";
      var bcSwatch = document.createElement("input");
      bcSwatch.type = "color";
      bcSwatch.id = "module-settings-border-color-swatch";
      bcSwatch.className = "color-swatch-input";
      bcSwatch.value = mc.border_color || "#888888";
      var bcHex = document.createElement("input");
      bcHex.type = "text";
      bcHex.id = "module-settings-border-color-hex";
      bcHex.className = "color-hex-input";
      bcHex.maxLength = 7;
      bcHex.value = mc.border_color || "#888888";
      bcRow.appendChild(bcSwatch);
      bcRow.appendChild(bcHex);
      frag.appendChild(bcRow);

      return frag;
    },

    afterPropertiesPaneInserted: function (paneEl, targetPanelId, api) {
      api.wireColorPair(
        "module-settings-highlight-swatch",
        "module-settings-highlight-hex",
        function (value) {
          var mon = document.querySelector('[data-panel-id="' + targetPanelId + '"] .dmx-monitor');
          if (mon) { mon.dataset.highlightColor = value; applyDmxCellColors(mon, _getChannelInfo(mon, false)); }
        }
      );
      var cmInput = paneEl.querySelector("#module-settings-color-mode");
      if (cmInput) {
        cmInput.addEventListener("change", function () {
          var mon = document.querySelector('[data-panel-id="' + targetPanelId + '"] .dmx-monitor');
          if (mon) { mon.dataset.colorMode = cmInput.checked ? "channel" : "signal"; _refreshMonitor(mon, true); }
        });
      }
      api.wireColorPair(
        "module-settings-border-color-swatch",
        "module-settings-border-color-hex",
        function (value) {
          var mon = document.querySelector('[data-panel-id="' + targetPanelId + '"] .dmx-monitor');
          if (mon) { mon.dataset.borderColor = value; _refreshMonitor(mon, true); }
        }
      );
      var bmSelect = paneEl.querySelector("#module-settings-border-mode");
      var bcRow = paneEl.querySelector("#module-settings-border-color-row");
      if (bmSelect) {
        bmSelect.addEventListener("change", function () {
          if (bcRow) bcRow.style.display = (bmSelect.value === "uniform") ? "" : "none";
          var mon = document.querySelector('[data-panel-id="' + targetPanelId + '"] .dmx-monitor');
          if (mon) { mon.dataset.borderMode = bmSelect.value; _refreshMonitor(mon, true); }
        });
      }
    },

    readPropertiesPane: function () {
      var univInput = document.getElementById("module-settings-universe");
      var hexInput = document.getElementById("module-settings-highlight-hex");
      var cmInput = document.getElementById("module-settings-color-mode");
      var bmSelect = document.getElementById("module-settings-border-mode");
      var bcHex = document.getElementById("module-settings-border-color-hex");
      var config = {};
      if (univInput) {
        var u = parseInt(univInput.value, 10);
        if (!isNaN(u) && u >= 1 && u <= 64) config.universe = u;
      }
      if (hexInput) {
        var h = hexInput.value.trim();
        if (/^#[0-9a-fA-F]{6}$/.test(h)) config.highlight_color = h;
      }
      if (cmInput) config.color_mode = cmInput.checked ? "channel" : "signal";
      if (bmSelect) config.border_mode = bmSelect.value;
      if (bcHex) {
        var bh = bcHex.value.trim();
        if (/^#[0-9a-fA-F]{6}$/.test(bh)) config.border_color = bh;
      }
      return Object.keys(config).length ? config : null;
    },

    onMessage: function (panelEl, messageType, payload) {
      var monitor = panelEl.querySelector(".dmx-monitor");
      if (!monitor) return;

      if (messageType === "fixtures_changed" || messageType === "state_snapshot") {
        // Fixture-Patch hat sich geaendert (neue/geloeschte/verschobene
        // Fixtures) - Kanal-Info + Gruppierung/Farben neu berechnen. Waehrend eines Fades/Effekts kommt
        // fixtures_changed im Livetakt mit unveraendertem Patch: dann ist die teure Neuberechnung unnoetig.
        var signature = _patchSignature(payload.fixtures || (client.state && client.state.fixtures));
        if (messageType === "state_snapshot" || signature !== monitor._patchSignature) {
          monitor._patchSignature = signature;
          _refreshMonitor(monitor, true);
        }
        return;
      }

      if (messageType !== "dmx_universe_changed") return;
      var panelUniverse = parseInt(monitor.dataset.universe, 10) || 1;
      // Werte immer cachen – unabhängig davon, welches Universum dieses
      // Panel gerade anzeigt, damit neu geöffnete Panels sofort befüllt
      // werden können.
      if (payload.universe !== undefined) {
        window.__dmxUniverseValueCache[payload.universe] = payload.values || [];
      }
      if (payload.universe !== undefined && payload.universe !== panelUniverse) return;
      // Der Monitor ist eine reine Zahlenanzeige und der teuerste Teil der Oberflaeche: er hat einen eigenen Takt, der sich an
      // seiner gemessenen Zeichenzeit orientiert (schnelles Geraet: jede Aktualisierung, iPad: seltener). Dazwischen gilt der
      // neueste Stand. Kacheln und Fader laufen unabhaengig davon weiter im schnellen Takt.
      var wait = (monitor._nextPaint || 0) - performance.now();
      if (wait > 0) {
        monitor._pendingPaint = { universe: panelUniverse, values: payload.values || [] };
        if (!monitor._paintTimer) {
          monitor._paintTimer = setTimeout(function () {
            monitor._paintTimer = null;
            var pending = monitor._pendingPaint;
            monitor._pendingPaint = null;
            if (pending && monitor.isConnected && (parseInt(monitor.dataset.universe, 10) || 1) === pending.universe) {
              _paintMonitorValues(monitor, pending.values);
            }
          }, wait);
        }
        return;
      }
      monitor._pendingPaint = null;
      _paintMonitorValues(monitor, payload.values || []);
    },
  });

  function _paintMonitorValues(monitor, values) {
      var started = performance.now();
      var cells = monitor._dmxCells;
      if (!cells || !cells.length || !cells[0].isConnected) {
        cells = monitor._dmxCells = Array.prototype.slice.call(monitor.querySelectorAll(".dmx-cell[data-channel]"));
      }
      // Nur Zellen mit neuem Wert anfassen (bei 512 Zellen und 25 Hz spart das auf schwachen Geraeten den Grossteil der Arbeit)
      var changed = [];
      for (var i = 0; i < cells.length; i++) {
        var cell = cells[i];
        var value = String(values[parseInt(cell.dataset.channel, 10) - 1] || 0);
        if (cell.dataset.value !== value) {
          cell.dataset.value = value;
          changed.push(cell);
        }
      }
      // Kanal-Info bereits gecacht (kein Fixture-/Universe-Wechsel) - nur
      // die Wertfarben neu anwenden, keine teure Neuberechnung noetig.
      if (changed.length) applyDmxCellColors(monitor, _getChannelInfo(monitor, false), changed);
      var cost = performance.now() - started;
      monitor._nextPaint = performance.now() + Math.min(500, Math.max(40, cost * 4));
  }
})();

(function () {
  "use strict";

  const t = (key, vars) => {
    let s = i18n(key);
    if (vars) for (const [k, v] of Object.entries(vars)) s = s.replace(`{${k}}`, v);
    return s;
  };

  // Global drag-handler für alle vfader: ersetzt N×document.addEventListener(mousemove)
  // durch einen einzigen, der nur beim aktiven Fader arbeitet.
  let _vfDragFn = null;
  // Touch-Geste auf einem Fader: erst entscheidet die Richtung der ersten Bewegung.
  //   vertikal   -> der Fader folgt dem Finger
  //   horizontal -> der Fader bleibt unveraendert, die Fader-Reihe scrollt (touch-action: pan-x)
  //   Tippen     -> der Wert springt auf die Tippposition
  let _vfTouch = null;      // { id, x, y, fn, mode: "pending" | "drag" }
  const VF_DIRECTION_SLOP = 8;
  document.addEventListener("mousemove", (e) => { if (_vfDragFn) _vfDragFn(e.clientY); });
  document.addEventListener("touchmove", (e) => {
    const gesture = _vfTouch;
    if (!gesture) return;
    const touch = Array.from(e.touches).find((t) => t.identifier === gesture.id);
    if (!touch) return;
    if (gesture.mode === "pending") {
      const dx = touch.clientX - gesture.x;
      const dy = touch.clientY - gesture.y;
      if (Math.hypot(dx, dy) < VF_DIRECTION_SLOP) return;
      if (Math.abs(dy) > Math.abs(dx)) {
        gesture.mode = "drag";
        _vfDragFn = gesture.fn;
      } else {
        _vfTouch = null;          // horizontal: den Browser scrollen lassen, Wert unveraendert
        return;
      }
    }
    gesture.fn(touch.clientY);
    if (e.cancelable) e.preventDefault();
  }, { passive: false });
  document.addEventListener("mouseup",  () => { _vfDragFn = null; });
  const endVfTouch = (e) => {
    const gesture = _vfTouch;
    _vfTouch = null;
    _vfDragFn = null;
    if (gesture && gesture.mode === "pending" && e.type === "touchend") {
      gesture.fn(gesture.y);      // reines Tippen: Wert an der Tippposition setzen
      if (e.cancelable) e.preventDefault();
    }
  };
  document.addEventListener("touchend", endVfTouch, { passive: false });
  document.addEventListener("touchcancel", endVfTouch);

  const _state = new WeakMap();
  function _getState(panelEl) {
    if (!_state.has(panelEl)) _state.set(panelEl, { fixtures: {} });
    return _state.get(panelEl);
  }

  function _fixturesFromGlobal() {
    try { return (client.state || {}).fixtures || {}; } catch { return {}; }
  }

  function _nextFreeChannel(fixtures, universe) {
    let max = 0;
    for (const fx of Object.values(fixtures)) {
      if (fx.universe === universe) {
        const end = fx.start_channel + fx.channel_count - 1;
        if (end > max) max = end;
      }
    }
    return Math.min(512, max + 1);
  }

  // Ermittelt den nächsten freien Namensindex für einen Präfix, z. B. "PAR 5" → 6
  function _nextNameIndex(fixtures, baseName) {
    const base = (baseName || "").trim();
    if (!base) return 1;
    let maxIdx = 0;
    for (const fx of Object.values(fixtures)) {
      const name = (fx.name || "").trim();
      if (name === base) {
        maxIdx = Math.max(maxIdx, 1);
      } else if (name.startsWith(base + " ")) {
        const rest = name.slice(base.length + 1);
        const n = parseInt(rest, 10);
        if (!isNaN(n) && String(n) === rest) maxIdx = Math.max(maxIdx, n);
      }
    }
    return maxIdx > 0 ? maxIdx + 1 : 1;
  }

  function _confirmDeleteFixtures(panelEl, ids) {
    const st = _getState(panelEl);
    const n = ids.length;
    if (!n) return;
    const firstName = st.fixtures[ids[0]]?.name || ids[0];
    const bodyText = n === 1
      ? t("FX_DELETE_BODY_ONE", { name: firstName })
      : t("FX_DELETE_BODY_MANY", { n });
    const bodyEl = document.createElement("p");
    bodyEl.style.cssText = "font-size:0.87rem;line-height:1.5;margin:0;";
    bodyEl.textContent = bodyText;
    if (n > 1) {
      const nameList = ids.slice(0, 8).map(id => st.fixtures[id]?.name || id).join(", ");
      const sub = document.createElement("span");
      sub.style.cssText = "display:block;font-size:0.75rem;color:var(--secondary-text,var(--text-dim));margin-top:0.35rem;";
      sub.textContent = nameList + (ids.length > 8 ? ` …+${ids.length - 8}` : "");
      bodyEl.appendChild(sub);
    }
    const { backdrop } = _makeModal(
      "fx-panel-modal-sm",
      t("FX_DELETE_TITLE"),
      bodyEl,
      [
        [t("CANCEL"), "", () => backdrop.remove()],
        [t("FX_DELETE_CONFIRM"), "modal__button--danger", () => {
          client.send("delete_fixtures", { ids });
          backdrop.remove();
        }],
      ]
    );
  }

  // ── DMX-Wertberechnung (reine, UI-unabhängige Konvertierungsfunktionen) ──
  // Einzige Quelle für alle Fader<->DMX-Umrechnungsfaktoren. Sowohl die UI-
  // Schicht (_makeVFader-Formatierung) als auch die State-Schicht
  // (ProgrammerState) rufen ausschliesslich diese Funktionen auf, statt
  // Umrechnungsfaktoren (z.B. "* 2.55") verstreut im Code zu wiederholen.
  const DMX = {
    pctToByte: (pct) => Math.round(pct * 2.55),                 // 0-100%  -> 0-255
    byteToPct: (byte) => Math.round(byte / 2.55),                // 0-255   -> 0-100%
    pctToDeg360: (pct) => Math.round(pct * 3.6),                 // 0-100%  -> 0-360°
    pctToPanTiltDeg: (pct) => ((pct - 50) * 5.4).toFixed(0),     // 0-100%  -> -270..+270°
    pctToV16: (pct) => Math.round(Math.max(0, Math.min(100, pct)) * 655.35),   // 0-100% -> 0-65535 (16 Bit)
    v16ToPct: (v16) => Math.max(0, Math.min(65535, v16)) / 655.35,
  };

  // ── Programmer State (State-Management-Schicht, global, multi-panel) ────
  // Kennt nur Fixture-IDs (Array) + Zielwerte - unabhaengig davon, ob die
  // IDs aus einer direkten Fixture-Selektion, einer Gruppe oder (zukuenftig)
  // einem Preset stammen. Gruppen/Presets muessen lediglich auf ein Array
  // von Fixture-IDs aufloesen und dieselben set*()-Funktionen aufrufen -
  // an dieser Schicht ist dafuer keine Aenderung noetig.
  if (!window.ProgrammerState) {
    window.ProgrammerState = (() => {
      const selectedIds  = new Set();
      const activeValues = {};
      // fxId -> {Variablen-Typ: preset-id}: welche Variable (Platzhalter) gerade welchen Teil der Fixture vorgibt. Die Wahrheit liegt auf dem Server
      // (state.programmer_refs, Nachricht "programmer_refs"); hier steht nur die Spiegelung fuer Dropdowns, gesperrte Fader und "Cue speichern":
      // der Cue bekommt dann den Verweis auf die Variable statt fester Werte und folgt ihr spaeter live.
      let _presetRefs = {};
      const PRESET_TYPE_ATTRS = {
        dimmer: ["dimmer"], position: ["pan", "tilt"], color: ["color"], focus: ["focus"], zoom: ["zoom"],
        gobo: ["gobo", "gobo_spin", "gobo2", "gobo2_spin"],
      };
      // fxId -> Set<attrName>: "active/touched"-Status (rot markiert im
      // Fixture-Panel) fuer manuell veraenderte Parameter ODER zugewiesene
      // Presets - NICHT fuer per Cue/Fade synchronisierte Werte (siehe
      // syncFromEngine). "Cue Speichern" uebernimmt exakt diese Menge
      // (getCueSnapshot) und raeumt sie danach auf (clearTouched).
      const touchedAttrs = {};
      function _breakPresetLink() { /* Verknuepfungen loest der Server (set_fixture_values, Cue, Effekt) und meldet sie per "programmer_refs" */ }
      // Zeitpunkt der letzten manuellen Aenderung je Fixture: der Echo-Wert aus dem DMX-Puffer ueberschreibt die Bedienelemente
      // waehrend/kurz nach einer Bedienung nicht (sonst "zuckt" der Fader unter dem Finger).
      const _manualAt = {};
      function _markTouched(ids, attrs, fromServer) {
        const now = Date.now();
        for (const id of ids) {
          if (!touchedAttrs[id]) touchedAttrs[id] = new Set();
          for (const a of attrs) touchedAttrs[id].add(a);
          if (!fromServer) _manualAt[id] = now;       // Schutzfrist nur fuer lokale Bedienung, nicht fuer Server-Daten
        }
      }
      /** Hat irgendeine Fixture ein manuell veraendertes Attribut aus `attrs` (Liste oder Pruefer-Funktion)? */
      function hasTouched(attrs) {
        const match = typeof attrs === "function" ? attrs : (a) => attrs.includes(a);
        return Object.values(touchedAttrs).some((set) => set && [...set].some(match));
      }
      function isFixtureTouched(id) { return !!touchedAttrs[id] && touchedAttrs[id].size > 0; }
      function isAttrTouched(id, attr) { return !!touchedAttrs[id] && touchedAttrs[id].has(attr); }
      // Waehrend eines Live-Takts (mehrere Nachrichten in einem Durchlauf) wird das Signal nur EINMAL am Ende gesendet:
      // jeder Empfaenger geht alle Kacheln/Fader durch, das wiederholt zu tun war auf dem iPad ein Hauptkostenfaktor.
      let _batchDepth = 0, _batchFire = false;
      function _fire() {
        if (_batchDepth > 0) { _batchFire = true; return; }
        document.dispatchEvent(new CustomEvent("programmer-state-updated"));
      }
      function batch(fn) {
        _batchDepth++;
        try { fn(); } finally {
          if (--_batchDepth === 0 && _batchFire) { _batchFire = false; _fire(); }
        }
      }
      // Show gewechselt (new_show/load_show): lokale Programmer-Werte, Markierungen und
      // Preset-Verknuepfungen der alten Show verwerfen. Die Selektion kommt vom Server.
      function reset() {
        for (const key of Object.keys(activeValues)) delete activeValues[key];
        for (const key of Object.keys(touchedAttrs)) delete touchedAttrs[key];
        _presetRefs = {};
        _fire();
      }
      const _EMPTY_VAL = { dimmer: null, color: null, pan: null, tilt: null, strobe: null, gobo: null, gobo_spin: null, gobo2: null, gobo2_spin: null, prism: null, focus: null, zoom: null };
      function _ensure(id) { if (!activeValues[id]) activeValues[id] = { ..._EMPTY_VAL }; }
      function getVal(id) { return activeValues[id] || _EMPTY_VAL; }
      // Live-Link zum DMX-Monitor: pusht ABSTRAKTE Werte (dimmer/pan/tilt/color,
      // 0-255) an den Server. Welcher konkrete GDTF-Kanalname (z.B. "Dimmer",
      // "ColorAdd_R" oder ersatzweise "ColorSub_C") dahinter tatsaechlich
      // beschrieben wird, loest der Server anhand des echten Fixture-Profils
      // auf - das Frontend kennt/rät keine rohen Kanalnamen mehr.
      function sendToServer(ids, semanticValues) {
        if (window.__panelAPI && typeof window.__panelAPI.sendToServer === "function") {
          window.__panelAPI.sendToServer("set_fixture_values", { ids, ...semanticValues });
        }
      }
      // Selektion ist server-autoritativ (siehe state.selected_fixture_ids,
      // app/command_line.py) - jede lokale Mausklick-Aenderung wird an den
      // Server gespiegelt, damit ein anschliessender Command-Line-Befehl
      // ("At 80") dieselbe Selektion sieht, UND damit ein "Fixture 1"-
      // Befehl umgekehrt sofort die Scheinwerferliste auf allen Clients
      // markiert (selection_changed-Broadcast, siehe setSelectionFromServer).
      function _syncSelectionToServer() {
        if (window.__panelAPI && typeof window.__panelAPI.sendToServer === "function") {
          window.__panelAPI.sendToServer("set_selection", { ids: [...selectedIds] });
        }
      }
      function toggleSelect(id) { selectedIds.has(id) ? selectedIds.delete(id) : selectedIds.add(id); _fire(); _syncSelectionToServer(); }
      function rangeAdd(ids) { for (const id of ids) selectedIds.add(id); _fire(); _syncSelectionToServer(); }
      /** Gruppen-Kopf: sind alle schon gewaehlt, werden sie abgewaehlt, sonst alle hinzugefuegt (die uebrige Auswahl bleibt). */
      function toggleMany(ids) {
        if (!ids.length) return;
        const all = ids.every((id) => selectedIds.has(id));
        for (const id of ids) { if (all) selectedIds.delete(id); else selectedIds.add(id); }
        _fire();
        _syncSelectionToServer();
      }
      // Eingehender selection_changed-Broadcast (Command Line ODER ein
      // anderer Client) - ersetzt die lokale Selektion 1:1, OHNE sie
      // zurueck an den Server zu senden (sonst Echo-Schleife).
      function setSelectionFromServer(ids) {
        selectedIds.clear();
        for (const id of ids) selectedIds.add(id);
        _fire();
      }
      function setDimmer(ids, value) {
        _breakPresetLink(ids);
        _markTouched(ids, ["dimmer"]);
        for (const id of ids) { _ensure(id); activeValues[id].dimmer = value; }
        _fire();
        sendToServer(ids, { dimmer: DMX.pctToByte(value) });
      }
      function deltaDimmer(ids, delta) {
        _breakPresetLink(ids);
        _markTouched(ids, ["dimmer"]);
        for (const id of ids) {
          _ensure(id);
          const c = activeValues[id].dimmer ?? 0;
          const nv = Math.max(0, Math.min(100, c + delta));
          activeValues[id].dimmer = nv;
          sendToServer([id], { dimmer: DMX.pctToByte(nv) });
        }
        _fire();
      }
      function setColor(ids, r, g, b) {
        _breakPresetLink(ids);
        _markTouched(ids, ["color"]);
        for (const id of ids) { _ensure(id); activeValues[id].color = { r, g, b }; }
        _fire();
        sendToServer(ids, { color: { r, g, b } });
      }
      function setPan(ids, value) {
        _breakPresetLink(ids);
        _markTouched(ids, ["pan"]);
        for (const id of ids) { _ensure(id); activeValues[id].pan = value; }
        _fire();
        // pan16: voller 16-Bit-Wert - Fixtures mit Fein-Kanal nutzen ihn, alle anderen das Grob-Byte
        sendToServer(ids, { pan: DMX.pctToByte(value), pan16: DMX.pctToV16(value) });
      }
      function setTilt(ids, value) {
        _breakPresetLink(ids);
        _markTouched(ids, ["tilt"]);
        for (const id of ids) { _ensure(id); activeValues[id].tilt = value; }
        _fire();
        sendToServer(ids, { tilt: DMX.pctToByte(value), tilt16: DMX.pctToV16(value) });
      }
      // Generischer Setter fuer Beam-/Fokus-Attribute (strobe/gobo/prism/
      // focus/zoom) - server.py loest den passenden GDTF-Kanalnamen auf
      // (z.B. "strobe" -> "Shutter1", "gobo" -> "Gobo1").
      function setBeamAttr(attr, ids, value) {
        _breakPresetLink(ids);
        _markTouched(ids, [attr]);
        for (const id of ids) { _ensure(id); activeValues[id][attr] = value; }
        _fire();
        sendToServer(ids, { [attr]: DMX.pctToByte(value) });
      }
      function setRawChannel(ids, channelOffset, value) {
        _breakPresetLink(ids);
        // Rohe DMX-Direct-Edits sind nicht Teil des abstrakten Cue-Formats,
        // zaehlen aber genauso als manuelle Aenderung fuer die Touched-
        // Markierung - pro Kanal-Offset, damit der DMX-Direct-Fader genau
        // den touched Kanal akzentuieren kann (siehe isAttrTouched).
        _markTouched(ids, ["_raw" + channelOffset]);
        if (window.__panelAPI && typeof window.__panelAPI.sendToServer === "function") {
          window.__panelAPI.sendToServer("set_fixture_raw_channel", { ids, channel_offset: channelOffset, value });
        }
      }
      // Variable anwenden: der Server setzt den Wert UND verknuepft die Variable mit den Fixtures (Platzhalter, nicht nur ein Wert). Aendert man die
      // Variable spaeter, folgen Programmer und Cues live; die Antwort ("programmer_command_update" + "programmer_refs") aktualisiert Fader und Dropdowns.
      function applyPreset(ids, presetId, type) {
        if (!ids.length || !window.__panelAPI || typeof window.__panelAPI.sendToServer !== "function") return;
        if (type) for (const id of ids) (_presetRefs[id] = _presetRefs[id] || {})[type] = presetId;          // sofort zeigen; der Server bestaetigt per "programmer_refs"
        window.__panelAPI.sendToServer("preset_apply", { fixture_ids: ids, preset_id: presetId });
      }
      /** Zurueck auf "Manuell": nur die Verknuepfung entfaellt, die Werte bleiben. */
      function releasePreset(ids, type) {
        if (!ids.length || !window.__panelAPI || typeof window.__panelAPI.sendToServer !== "function") return;
        for (const id of ids) { if (_presetRefs[id]) { delete _presetRefs[id][type]; if (!Object.keys(_presetRefs[id]).length) delete _presetRefs[id]; } }
        window.__panelAPI.sendToServer("preset_release", { fixture_ids: ids, type });
        _fire();
      }
      function setPresetRefs(refs) { _presetRefs = refs && typeof refs === "object" ? refs : {}; _fire(); }
      /** Nur Werte uebernehmen, ohne sie als angefasst zu markieren (eine Variable wurde geaendert und die Fixtures folgen ihr). */
      function applyQuiet(values) {
        for (const [id, attrs] of Object.entries(values)) { _ensure(id); Object.assign(activeValues[id], attrs); }
        _fire();
      }
      function batchSet(fn) { fn(activeValues, _ensure); _fire(); }
      function hasDimmer() { return Object.values(activeValues).some(v => v.dimmer !== null); }
      function hasColor()  { return Object.values(activeValues).some(v => v.color  !== null); }
      // Live-Sync waehrend eines Cue-Go/-Back-Fades (programmer_live_update
      // vom Server, siehe cue_engine.py): aktualisiert NUR die angezeigten
      // Werte, OHNE sie als "touched" zu markieren - Cue-Output ist keine
      // manuelle Bedienung. Hebt den touched-Status fuer genau die hier
      // gelieferten Attribute auf (neue "saubere" Baseline durch den Cue).
      function syncFromEngine(values) {
        for (const [id, attrs] of Object.entries(values)) {
          _ensure(id);
          Object.assign(activeValues[id], attrs);
          if (touchedAttrs[id]) {
            for (const key of Object.keys(attrs)) touchedAttrs[id].delete(key);
            if (touchedAttrs[id].size === 0) delete touchedAttrs[id];
          }
        }
        _fire();
      }
      // Quelle der Wahrheit ist der DMX-Puffer (was der DMX-Monitor zeigt): der Server schickt die daraus abgeleiteten
      // abstrakten Werte (fixtures_live). Aktualisiert NUR die Anzeige - nie die "angefasst"-Markierung (die gibt es nur
      // fuer manuelle Bedienung, nicht fuer Cue-Wiedergabe, Executor-Fader oder Effekte).
      function syncFromDmx(values) {
        const now = Date.now();
        let changed = false;
        for (const [id, attrs] of Object.entries(values)) {
          if (now - (_manualAt[id] || 0) < 500) continue;
          _ensure(id);
          Object.assign(activeValues[id], attrs);
          changed = true;
        }
        if (changed) _fire();
      }
      // Nach erfolgreichem "Cue Speichern": raeumt den touched-Status (und
      // eine evtl. gemerkte Preset-Verknuepfung) fuer genau die Fixtures auf,
      // die in snapshot (= das Ergebnis von getCueSnapshot()) enthalten sind -
      // ihre Werte sind jetzt im Cue gesichert, die rote Markierung verschwindet.
      function clearTouched(snapshot) {
        for (const id of Object.keys(snapshot)) delete touchedAttrs[id];
        _fire();
      }
      // Raeumt touched-Status + Preset-Verknuepfung fuer eine einfache
      // ID-Liste auf (statt eines snapshot-foermigen Objekts) - genutzt vom
      // "programmer_cleared"-Broadcast (Command Line "Clear Clear" / nach
      // "Store Cue", siehe app/command_line.py).
      function clearTouchedByIds(ids) {
        for (const id of ids) { delete touchedAttrs[id]; delete _presetRefs[id]; }
        _fire();
      }
      // Command-Line-getriebene Werteaenderung ("At 80" etc., siehe
      // "programmer_command_update" in server.py/command_line.py): anders
      // als syncFromEngine() WIRD hier touched markiert - ein Konsolen-
      // befehl ist eine manuelle Bedienung, kein Cue-Playback.
      function applyFromServer(values) {
        for (const [id, attrs] of Object.entries(values)) {
          _ensure(id);
          Object.assign(activeValues[id], attrs);
          _markTouched([id], Object.keys(attrs), true);
        }
        _fire();
      }
      // Snapshot der aktuell im Programmer gesetzten (relativen) Werte fuer
      // "Cue Speichern" - NUR tatsaechlich angefasste (touched) Fixtures/
      // Attribute (kein voller DMX-Snapshot). Ist seit der letzten
      // Preset-Anwendung nichts manuell veraendert worden, wird die
      // preset_uuid gespeichert statt fester Werte - siehe CueList-Panel.
      function getCueSnapshot() {
        const out = {};
        for (const [id, attrSet] of Object.entries(touchedAttrs)) {
          if (!attrSet || attrSet.size === 0) continue;
          const v = activeValues[id] || _EMPTY_VAL;
          const vals = {};
          const refs = {};
          const covered = new Set();
          for (const [type, presetId] of Object.entries(_presetRefs[id] || {})) {         // Variablen bleiben Platzhalter: der Cue speichert den Verweis
            const attrs = PRESET_TYPE_ATTRS[type] || [];
            if (attrs.some((a) => attrSet.has(a))) { refs[type] = presetId; attrs.forEach((a) => covered.add(a)); }
          }
          for (const key of ["dimmer", "color", "pan", "tilt", "strobe", "gobo", "gobo_spin", "gobo2", "gobo2_spin", "prism", "focus", "zoom"]) {
            if (attrSet.has(key) && v[key] != null && !covered.has(key)) vals[key] = v[key];
          }
          for (const key of attrSet) {                                    // rohe DMX-Kanaele ("ch<Offset>", Byte): DMX Direkt, Gobo-Rad 2, Drehung, Frost, Iris, Fein-Kanaele ...
            if (/^ch\d+$/.test(key) && v[key] != null) vals[key] = v[key];
          }
          if (Object.keys(vals).length > 0 || Object.keys(refs).length > 0) out[id] = Object.keys(refs).length ? { values: vals, refs } : { values: vals };
        }
        return out;
      }
      return {
        selectedIds, getVal, toggleSelect, rangeAdd, toggleMany, setDimmer, deltaDimmer, setColor, setPan, setTilt,
        setBeamAttr, setRawChannel, applyPreset, batchSet, sendToServer, hasDimmer, hasColor,
        isFixtureTouched, isAttrTouched, hasTouched, syncFromEngine, syncFromDmx, batch, clearTouched, clearTouchedByIds,
        applyFromServer, setSelectionFromServer, getCueSnapshot, reset,
        releasePreset, setPresetRefs, applyQuiet,
        getPresetRef: (id, type) => (_presetRefs[id] && _presetRefs[id][type]) || null,
        clearAllPresetLinks: () => { _presetRefs = {}; },
      };
    })();
  }

  // ── Tile visual update ────────────────────────────────────────────
  function _updateTile(tileEl, id) {
    const p = window.ProgrammerState.getVal(id);
    const dimPct = p.dimmer ?? 0;
    // Nur schreiben, was sich geaendert hat: Textknoten/Styles bei gleichem Wert neu zu setzen kostete bei jedem Live-Takt Layout
    // und Neuzeichnen fuer ALLE Kacheln, auch fuer die, die gar nicht laufen.
    const shown = tileEl._shown || (tileEl._shown = {});
    const barScale = Math.max(0, Math.min(1, dimPct / 100));
    if (shown.bar !== barScale) {
      const bar = tileEl.querySelector(".fxprog-tile__dimbar");
      if (bar) bar.style.transform = "scaleY(" + barScale + ")";
      shown.bar = barScale;
    }
    const pctText = Math.round(dimPct) + "%";
    if (shown.pct !== pctText) {
      const pct = tileEl.querySelector(".fxprog-tile__pct");
      if (pct) {
        if (pct.firstChild) pct.firstChild.nodeValue = pctText;      // Textknoten behalten statt ersetzen (kein Entfernen/Hinzufuegen im Layout)
        else pct.textContent = pctText;
      }
      shown.pct = pctText;
    }
    const active = dimPct > 0;
    if (shown.active !== active) {
      tileEl.classList.toggle("fxprog-tile--active", active);
      shown.active = active;
    }
    let background;
    if (tileEl.dataset.hasColor === "false") {
      // Reine Dimmer-Fixture (keine Farb-Kanaele): ausschliesslich
      // Graustufen Schwarz(0%) -> Weiss(100%) je nach Dimmer-Wert.
      const g = Math.round(dimPct * 2.55);
      background = `rgb(${g},${g},${g})`;
    } else {
      const c = p.color;
      background = c ? `rgb(${c.r},${c.g},${c.b})` : "";
    }
    if (shown.background !== background) {
      const colorEl = tileEl.querySelector(".fxprog-tile__color");
      if (colorEl) colorEl.style.background = background;
      shown.background = background;
    }
  }

  // ── Dot2 Grid renderer ────────────────────────────────────────────
  function _renderDot2Grid(panelEl, fixtures) {
    const st = _getState(panelEl);
    st.fixtures = fixtures;

    const sheet = panelEl.querySelector(".fxprog-sheet");
    if (!sheet) return;
    sheet.innerHTML = "";

    const entries = Object.entries(fixtures);
    if (entries.length === 0) {
      const empty = document.createElement("div");
      empty.className = "fxprog-empty";
      empty.dataset.i18n = "FXPROG_EMPTY";
      empty.textContent = t("FXPROG_EMPTY");
      sheet.appendChild(empty);
      return;
    }

    // Reihenfolge: zuerst die benannten Gruppen (in ihrer Anlege-Reihenfolge; darin nach Typ, dann Adresse), danach wie bisher
    // alle uebrigen Scheinwerfer nach Typ gruppiert, je nach Adresse sortiert. Ohne Gruppen aendert sich nichts.
    const byAddress = (a, b) => (a[1].universe !== b[1].universe ? a[1].universe - b[1].universe : a[1].start_channel - b[1].start_channel);
    // Standard: nach der Nummer (FID) des Scheinwerfers - wie in der Scheinwerfer-Liste. Der freie Sortier-Index ersetzt die
    // FID als Sortierwert (z. B. 2,5 ordnet zwischen FID 2 und 3 ein); bei Gleichstand FID, dann DMX-Adresse.
    const sortKey = (fx) => {
      const idx = fx.sort_index;
      if (idx !== null && idx !== undefined && Number.isFinite(Number(idx))) return Number(idx);
      return fx.fid > 0 ? fx.fid : 1e9;
    };
    const byIndex = (a, b) => (sortKey(a[1]) - sortKey(b[1])) || ((a[1].fid || 1e9) - (b[1].fid || 1e9)) || byAddress(a, b);
    entries.sort(byIndex);
    const sections = [];                 // { group: Name | null, title, list: [[id, fx], ...] }
    const grouped = new Set();
    for (const [groupName, memberIds] of Object.entries((client.state && client.state.groups) || {})) {
      const list = (memberIds || []).filter((id) => fixtures[id]).map((id) => [id, fixtures[id]]);
      list.sort(byIndex);
      list.forEach(([id]) => grouped.add(id));
      sections.push({ group: groupName, title: groupName, list });
    }
    const types = new Map();
    for (const [id, fx] of entries) {
      if (grouped.has(id)) continue;
      const key = fx.fixture_type || "Unknown";
      if (!types.has(key)) types.set(key, []);
      types.get(key).push([id, fx]);
    }
    for (const [typeName, list] of types) sections.push({ group: null, title: _fixtureTypeLabel(typeName), list });

    let allTiles = [];
    let lastClickedIdx = -1;

    for (const section of sections) {
      const fxList = section.list;
      const group = document.createElement("div");
      group.className = "fxprog-group" + (section.group !== null ? " fxprog-group--named" : "");

      const label = document.createElement("div");
      label.className = "fxprog-group__label";
      label.textContent = section.title;
      if (section.group !== null) {
        // Gruppen-Kopf: Klick waehlt alle Scheinwerfer der Gruppe (ab), Rechtsklick/Long-Press: umbenennen / loeschen
        const memberIds = fxList.map(([id]) => id);
        label.classList.add("fxprog-group__label--group");
        label.dataset.group = section.group;
        label.title = t("FXGRP_HEADER_TIP");
        const count = document.createElement("span");
        count.className = "fxprog-group__count";
        count.textContent = String(memberIds.length);
        label.appendChild(count);
        label.classList.toggle("fxprog-group__label--selected", memberIds.length > 0 && memberIds.every((id) => window.ProgrammerState.selectedIds.has(id)));
        label.addEventListener("click", () => {
          if (_dragMoved) return;
          if (window.__longPress && window.__longPress.suppress) return;
          window.ProgrammerState.toggleMany(memberIds);
        });
      }
      group.appendChild(label);

      const tilesWrap = document.createElement("div");
      tilesWrap.className = "fxprog-group__tiles";
      if (section.group !== null && !fxList.length) {
        const hint = document.createElement("div");
        hint.className = "fxprog-group__empty";
        hint.textContent = t("FXGRP_EMPTY");
        group.appendChild(hint);
      }

      for (const [id, fx] of fxList) {
        const tile = document.createElement("div");
        tile.className = "fxprog-tile" + (window.ProgrammerState.selectedIds.has(id) ? " fxprog-tile--selected" : "");
        tile.dataset.fxId = id;
        // Farb-Vorschau nur rendern, wenn die Fixture tatsaechlich Farb-
        // Kanaele besitzt - reine Dimmer-Fixtures zeigen ausschliesslich
        // Graustufen (siehe _updateTile). Faellt bei unbekanntem/noch nicht
        // geladenem Profil auf "hat Farbe" zurueck (kein Flackern).
        tile.dataset.hasColor = _fixtureHasFeature(fx, "color") ? "true" : "false";

        const idEl = document.createElement("span");
        idEl.className = "fxprog-tile__id";
        idEl.textContent = fx.fid != null ? fx.fid : "";

        const dimbar = document.createElement("div");
        dimbar.className = "fxprog-tile__dimbar";

        const colorEl = document.createElement("div");
        colorEl.className = "fxprog-tile__color";

        const pctEl = document.createElement("span");
        pctEl.className = "fxprog-tile__pct";
        pctEl.textContent = "0%";

        tile.appendChild(idEl);
        tile.appendChild(dimbar);
        tile.appendChild(colorEl);
        tile.appendChild(pctEl);

        _updateTile(tile, id);

        const tileIdx = allTiles.length;
        const selectTile = (e) => {
          const PS = window.ProgrammerState;
          if (e.shiftKey && lastClickedIdx >= 0) {
            const lo = Math.min(lastClickedIdx, tileIdx);
            const hi = Math.max(lastClickedIdx, tileIdx);
            PS.rangeAdd(allTiles.slice(lo, hi + 1).map(tl => tl.dataset.fxId));
          } else {
            PS.toggleSelect(id);
          }
          lastClickedIdx = tileIdx;
        };
        // Touch/Stift: Auswahl direkt beim Loslassen (pointerup) - kein Umweg ueber :hover
        // oder einen verzoegerten click. Ein Wisch (Lasso) waehlt selbst aus und toggelt nicht.
        tile.addEventListener("pointerup", (e) => {
          if (e.pointerType === "mouse" || _dragMoved) return;
          if (window.__longPress && window.__longPress.suppress) return;   // Long-Press oeffnete das Kontextmenue
          tile._pointerSelectAt = Date.now();
          selectTile(e);
        });
        tile.addEventListener("click", (e) => {
          // Eine echte Wisch-Geste (Drag ueber mehrere Tiles) hat die
          // Selektion bereits live per pointermove gesetzt - kein Toggle.
          if (_dragMoved) return;
          // Wurde per pointerup schon ausgewaehlt, ist der nachgereichte click nur ein Echo.
          if (Date.now() - (tile._pointerSelectAt || 0) < 800) return;
          selectTile(e);
        });

        tilesWrap.appendChild(tile);
        allTiles.push(tile);
      }

      group.appendChild(tilesWrap);
      sheet.appendChild(group);
    }

    // Delete-Key-Handler
    panelEl._fxKeyHandler && document.removeEventListener("keydown", panelEl._fxKeyHandler);
    panelEl._fxKeyHandler = (e) => {
      if (_panelGone(panelEl, "keydown", panelEl._fxKeyHandler)) return;
      if (e.key !== "Delete" && e.key !== "Backspace") return;
      if (!panelEl.contains(document.activeElement) && document.activeElement !== document.body) return;
      const ids = [...window.ProgrammerState.selectedIds];
      if (!ids.length) return;
      _confirmDeleteFixtures(panelEl, ids);
    };
    document.addEventListener("keydown", panelEl._fxKeyHandler);
  }

  // ── Farb-Konvertierungshelfer (HSV ↔ RGB, CMY ↔ RGB) ─────────────
  function _rgb2hsv(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
    let h = 0;
    if (d > 0) {
      if      (max === r) h = (((g - b) / d) % 6) / 6;
      else if (max === g) h = ((b - r) / d + 2) / 6;
      else                h = ((r - g) / d + 4) / 6;
      if (h < 0) h += 1;
    }
    return { h: Math.round(h * 100), s: Math.round((max === 0 ? 0 : d / max) * 100), v: Math.round(max * 100) };
  }
  function _hsv2rgb(h, s, v) {
    const hd = (h / 100) * 360; s /= 100; v /= 100;
    const c = v * s, x = c * (1 - Math.abs((hd / 60) % 2 - 1)), m = v - c;
    let r = 0, g = 0, b = 0;
    if      (hd < 60)  { r=c; g=x; b=0; }
    else if (hd < 120) { r=x; g=c; b=0; }
    else if (hd < 180) { r=0; g=c; b=x; }
    else if (hd < 240) { r=0; g=x; b=c; }
    else if (hd < 300) { r=x; g=0; b=c; }
    else               { r=c; g=0; b=x; }
    return { r: Math.round((r+m)*255), g: Math.round((g+m)*255), b: Math.round((b+m)*255) };
  }

  // ── Throttle (Leading+Trailing) fuer hochfrequente Fader-Events ──────
  // Verhindert das DMX-Freeze/Aufstau-Problem: ein Drag am Fader feuert
  // pointermove/touchmove mit bis zu 100+ Events/Sek. Jeder onChange-Aufruf
  // loest einen vollen DOM-Sync (programmer-state-updated) UND einen
  // WebSocket-Versand samt Server-Broadcast aus - ungebremst laufen diese
  // schneller auf, als sie verarbeitet werden koennen, und "stauen sich".
  // Feuert sofort beim ersten Tick (fuehlt sich reaktionsschnell an), dann
  // max. alle `ms` - garantiert einen abschliessenden Aufruf mit dem
  // LETZTEN Wert, damit der finale Fader-Stand nie verloren geht.
  function _throttle(fn, ms) {
    let lastCall = 0;
    let pendingArgs = null;
    let timer = null;
    const invoke = () => {
      lastCall = Date.now();
      timer = null;
      const args = pendingArgs;
      pendingArgs = null;
      fn(...args);
    };
    return (...args) => {
      const now = Date.now();
      const remaining = ms - (now - lastCall);
      if (remaining <= 0) {
        if (timer) { clearTimeout(timer); timer = null; }
        lastCall = now;
        fn(...args);
      } else {
        pendingArgs = args;
        if (!timer) timer = setTimeout(invoke, remaining);
      }
    };
  }

  // ── Vertikaler Fader (dot2-Konsolen-Stil) ─────────────────────────
  function _makeVFader({ label, labelKey, value = 0, onChange, trackClass, formatVal } = {}) {
    const wrap  = document.createElement("div");
    wrap.className = "vfader";
    const track = document.createElement("div");
    track.className = "vfader__track";
    if (trackClass) track.classList.add(trackClass);
    const fill  = document.createElement("div");
    fill.className = "vfader__fill";
    const thumb = document.createElement("div");
    thumb.className = "vfader__thumb";
    track.appendChild(fill);
    track.appendChild(thumb);
    const labelEl = document.createElement("div");
    labelEl.className = "vfader__label";
    if (label) labelEl.textContent = label;
    // labelKey: uebersetzter Text (statt fixer String wie "Pan"/"Hue") -
    // data-i18n sorgt dafuer, dass translator.apply() den Text auch dann
    // korrigiert, wenn die Locale-Datei beim ersten Rendern noch nicht
    // geladen war (Race-Condition) oder die Sprache spaeter gewechselt wird.
    if (labelKey) labelEl.dataset.i18n = labelKey;
    wrap.appendChild(track);
    wrap.appendChild(labelEl);

    const _fmt = formatVal || ((v) => v + "%");
    let cur = 0;
    let shownValue = null;
    const applyValue = (v) => {
      cur = Math.max(0, Math.min(100, Math.round(v)));
      if (cur === shownValue) return cur;                    // unveraendert (z. B. Live-Takt): kein Layout/Neuzeichnen
      shownValue = cur;
      fill.style.height = cur + "%";
      track.style.setProperty("--fv", cur + "%");
      thumb.textContent = _fmt(cur);
      return cur;
    };
    applyValue(value);

    const calcPct = (clientY) => {
      const r = track.getBoundingClientRect();
      return r.height > 0 ? Math.max(0, Math.min(100, Math.round((1 - (clientY - r.top) / r.height) * 100))) : cur;
    };
    // Visuelles Update (applyValue) bleibt IMMER sofort/ungedrosselt fuer
    // fluessiges Dragging - nur der teure onChange-Callback (State-Sync +
    // Netzwerk-Versand) wird auf ~33Hz gedrosselt (siehe _throttle oben).
    const throttledChange = onChange ? _throttle(onChange, 30) : null;
    const onMove = (y) => { const p = calcPct(y); applyValue(p); if (throttledChange) throttledChange(p); };

    // Drag-Start setzt den globalen Handler (_vfDragFn), damit nur ein
    // einziger document-mousemove-Listener fuer alle Fader benoetigt wird.
    track.addEventListener("mousedown", (e) => { _vfDragFn = onMove; onMove(e.clientY); e.preventDefault(); });
    track.addEventListener("touchstart", (e) => {
      if (e.touches.length !== 1) return;
      const t = e.touches[0];
      _vfTouch = { id: t.identifier, x: t.clientX, y: t.clientY, fn: onMove, mode: "pending" };
    }, { passive: true });

    wrap.setValue = applyValue;
    wrap.getValue = () => cur;
    // isDragging: prueft ob genau dieser Fader aktuell gezogen wird.
    Object.defineProperty(wrap, "isDragging", { get: () => _vfDragFn === onMove });
    return wrap;
  }

  // ── Position: Zahlenfelder mit Wisch-Feineinstellung (Pan/Tilt) ────────────────────────────
  // Wert-Modell: 16 Bit pro Achse (0-65535). Grob = das hohe Byte (der Grob-Kanal), Fein = das niedrige Byte
  // (der Fein-Kanal). Ein Grob-Schritt ist +256, ein Fein-Schritt +1; Fixtures ohne Fein-Kanal nutzen nur das Grob-Byte.
  // Skalierung der Wischgeste (Pixel je Schritt): relativ zum Wert bei Beginn der Geste (kein Aufsummieren, kein Drift).
  //   Grob: 2 px je Grob-Schritt. Ein Schritt = 1/255 des Bereichs (bei -270..+270° rund 2,1°). Eine volle
  //         Bereichsdurchquerung braucht ~510 px - 10 px Wischen bewegen also ~10° statt den ganzen Bereich zu springen.
  //   Fein: 4 px je Fein-Schritt. Ein Schritt = 1/65535 des Bereichs (~0,008°) - fuer Millimeterarbeit ist
  //         ein Fein-Schritt pro 4 px sicher beherrschbar (256 Schritte = ein Grob-Schritt = 1024 px).
  // Unter 4 px Bewegung gilt die Geste als Tippen (Zahleneingabe bleibt moeglich).
  const POS_SWIPE = { coarse: { step: 256, px: 2 }, fine: { step: 1, px: 4 }, slop: 4 };

  function _axisV16(axis) {
    const PS = window.ProgrammerState;
    if (!PS.selectedIds.size) return null;
    const v = PS.getVal([...PS.selectedIds][0])[axis];
    return DMX.pctToV16(v == null ? 50 : v);
  }

  function _setAxisV16(axis, v16) {
    const PS = window.ProgrammerState;
    const sel = [...PS.selectedIds];
    if (!sel.length) return;
    const pct = DMX.v16ToPct(Math.max(0, Math.min(65535, Math.round(v16))));
    if (axis === "pan") PS.setPan(sel, pct); else PS.setTilt(sel, pct);
  }

  // Wie viele der selektierten Fixtures haben einen Fein-Kanal fuer Pan bzw. Tilt?
  function _fineSupport(panelEl) {
    const PS = window.ProgrammerState;
    const fixtures = _getState(panelEl).fixtures || {};
    const out = { total: 0, pan: 0, tilt: 0, known: !!_fixtureTypesCache };
    for (const id of PS.selectedIds) {
      const fx = fixtures[id];
      if (!fx) continue;
      out.total++;
      const names = new Set(_channelsForFixture(fx, _fixtureTypesCache).map(c => c.name));
      if (names.has("PanFine")) out.pan++;
      if (names.has("TiltFine")) out.tilt++;
    }
    return out;
  }

  // ── Anleuchten: Knoepfe zur 3D-Simulation (Position: Punkt setzen; Fokus: Auto-Fokus / Auto-Zoom) ──
  // Sie erscheinen nur, wenn eine 3D-Simulation im selben Layout steht und Scheinwerfer auf ihrer Buehne platziert sind (window.OCSimAim, sim3d_boot.js), und sind ohne gewaehlte Moving Heads
  // gesperrt. Mehr steht hier bewusst nicht: Erklaerung im Tooltip, Rueckmeldung im Banner der Simulation bzw. an den Fadern.
  function _buildSimAimButton(panelEl, { cls, labelKey, tipKey, toggle, onClick }) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = cls + " fxprog-aimbtn";
    btn.dataset.act = "sim-aim";
    btn.hidden = true;
    const label = document.createElement("span");
    label.dataset.i18n = labelKey;
    label.textContent = t(labelKey);
    btn.append(Icons.svg("target"), label);
    btn.addEventListener("click", () => { const A = window.OCSimAim; if (A) onClick(A, [...window.ProgrammerState.selectedIds]); });
    const refresh = () => {
      if (_panelGone(panelEl, "sim-aim-changed", refresh)) return;
      const A = window.OCSimAim;
      const available = !!A && A.available();
      btn.hidden = !available;
      if (!available) return;
      const armed = !!toggle && A.armed;
      const none = A.aimable(window.ProgrammerState ? [...window.ProgrammerState.selectedIds] : []) === 0;
      btn.disabled = none && !armed;
      btn.classList.toggle("fxprog-qbtn--active", armed);
      btn.setAttribute("aria-pressed", String(armed));
      btn.title = none && !armed ? t("FXPROG_AIM_NONE_TIP") : t(tipKey);
    };
    document.addEventListener("sim-aim-changed", refresh);
    document.addEventListener("programmer-state-updated", refresh);
    refresh();
    return btn;
  }
  const _aimMissToast = (r) => {
    if (!r) return;
    if (r.done === 0) _showToast(t("FXPROG_AIM_MISS"), "info", 3500, true);
    else if (r.clamped) _showToast(t("FXPROG_AIM_CLAMPED").split("{n}").join(String(r.clamped)), "info", 3500, true);
  };
  const _aimNum = (v) => (Math.round(v * 100) / 100).toString().replace(".", ",");
  // Auto-Zoom: Dialog nach dem Radius des Lichtkreises; in Klammern steht, was auf die Wurfweite moeglich ist (je Geraet aus seinem Zoombereich; bei mehreren der gemeinsame Bereich bzw. die Spanne).
  async function _autoZoomDialog(A, ids) {
    const info = A.zoomInfo(ids);
    const hint = !info ? "" : t(info.kind === "one" ? "FXPROG_AIM_RANGE_ONE" : info.kind === "all" ? "FXPROG_AIM_RANGE_ALL" : "FXPROG_AIM_RANGE_SPAN").split("{min}").join(_aimNum(info.min)).split("{max}").join(_aimNum(info.max));
    const value = await _askLayoutName({ title: t("FXPROG_AIM_RADIUS_TITLE"), confirmKey: "FXPROG_AIM_RADIUS_OK", value: _aimNum(A.radius), labelKey: "FXPROG_AIM_RADIUS_LABEL", labelText: t("FXPROG_AIM_RADIUS_LABEL") + (hint ? " (" + hint + ")" : "") });
    if (!value) return;
    const radius = Number(String(value).replace(",", "."));
    if (!Number.isFinite(radius) || radius <= 0) return;
    A.radius = radius;
    _aimMissToast(A.auto("zoom", ids, A.radius));
  }

  function _makeSwipeField(panelEl, axis, kind) {
    const wrap = document.createElement("div");
    wrap.className = "fxprog-numfield-wrap";
    wrap.dataset.axis = axis;
    wrap.dataset.kind = kind;
    const input = document.createElement("input");
    input.type = "text";
    input.className = "fxprog-numfield";
    input.setAttribute("inputmode", "decimal");
    input.setAttribute("autocomplete", "off");
    input.setAttribute("autocorrect", "off");
    input.setAttribute("spellcheck", "false");
    input.dataset.axis = axis;
    input.dataset.kind = kind;
    wrap.appendChild(input);
    const { step, px } = POS_SWIPE[kind];

    const range = () => _panTiltPhysicalRange(panelEl, axis);
    const display = (v16) => {
      if (v16 == null) return "–";
      if (kind === "fine") return String(v16 & 0xFF);
      const [from, to] = range();
      return (from + (v16 / 65535) * (to - from)).toFixed(1) + "°";
    };
    const refresh = () => {
      if (document.activeElement === input || wrap.classList.contains("fxprog-numfield-wrap--swiping")) return;
      input.value = display(_axisV16(axis));
      const caption = wrap.parentElement && wrap.parentElement.querySelector(".fxprog-numfield-caption");
      if (caption && wrap.dataset.kind === "fine") {
        const v = _axisV16(axis);
        const [from, to] = range();
        caption.textContent = v == null ? "" : (from + (v / 65535) * (to - from)).toFixed(3) + "°";
      }
    };
    wrap._refresh = refresh;

    // Zahleneingabe (Tippen): Grob in Grad, Fein als 0-255
    const commit = () => {
      const current = _axisV16(axis);
      if (current == null) { refresh(); return; }
      const text = input.value.replace(",", ".").replace(/[^0-9.+-]/g, "");
      const num = parseFloat(text);
      if (!Number.isFinite(num)) { refresh(); return; }
      if (kind === "fine") {
        _setAxisV16(axis, (current & ~0xFF) | Math.max(0, Math.min(255, Math.round(num))));
      } else {
        const [from, to] = range();
        _setAxisV16(axis, ((num - from) / (to - from)) * 65535);
      }
      refresh();
    };
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); input.blur(); }
      else if (e.key === "Escape") { input.value = display(_axisV16(axis)); input.blur(); }
    });
    input.addEventListener("blur", () => { commit(); });
    input.addEventListener("focus", () => { setTimeout(() => input.select(), 0); });

    // Wischgeste (Maus und Touch ueber Pointer-Events): hoch = mehr, runter = weniger. Bewegung und Loslassen werden
    // am document verfolgt, damit die Geste auch ausserhalb des kleinen Feldes weiterlaeuft (Pointer-Capture allein
    // ist bei der Maus nicht in jedem Browser verlaesslich).
    let drag = null;
    const send = _throttle((v16) => _setAxisV16(axis, v16), 30);
    const onMove = (e) => {
      if (!drag || e.pointerId !== drag.id) return;
      const dy = drag.y0 - e.clientY;
      if (!drag.moved) {
        if (Math.abs(dy) < POS_SWIPE.slop) return;
        drag.moved = true;
        wrap.classList.add("fxprog-numfield-wrap--swiping");
        input.blur();
        try { input.setPointerCapture(e.pointerId); } catch (err) { /* Zeiger schon weg */ }
      }
      if (e.cancelable) e.preventDefault();
      drag.last = Math.max(0, Math.min(65535, drag.v0 + Math.round(dy / px) * step));
      input.value = display(drag.last);
      send(drag.last);
    };
    const finish = (e) => {
      if (!drag || e.pointerId !== drag.id) return;
      const d = drag;
      drag = null;
      document.removeEventListener("pointermove", onMove, true);
      document.removeEventListener("pointerup", finish, true);
      document.removeEventListener("pointercancel", finish, true);
      wrap.classList.remove("fxprog-numfield-wrap--swiping");
      if (d.moved) {
        _setAxisV16(axis, d.last);   // abschliessender Wert garantiert
        refresh();
      } else if (e.type === "pointerup") {
        input.focus();               // Tippen ohne Wischen: Zahl eingeben
      }
    };
    input.addEventListener("pointerdown", (e) => {
      if (e.pointerType === "mouse" && e.button !== 0) return;
      const v0 = _axisV16(axis);
      if (v0 == null || wrap.closest(".fxprog-ctrl-gated--disabled")) return;
      drag = { id: e.pointerId, y0: e.clientY, v0, moved: false, last: v0 };
      document.addEventListener("pointermove", onMove, true);
      document.addEventListener("pointerup", finish, true);
      document.addEventListener("pointercancel", finish, true);
      if (e.pointerType === "mouse") e.preventDefault();   // kein Textmarkieren/Fokus waehrend des Ziehens
    });
    return wrap;
  }

  function _syncPosFields(panelEl) {
    panelEl.querySelectorAll(".fxprog-numfield-wrap").forEach((w) => w._refresh && w._refresh());
    const fine = panelEl.querySelector(".fxprog-posfine");
    if (!fine) return;
    const sup = _fineSupport(panelEl);
    let state = "unknown";
    if (sup.known && sup.total) state = sup.pan + sup.tilt === 0 ? "none" : (sup.pan === sup.total && sup.tilt === sup.total ? "all" : "some");
    fine.dataset.fine = state;
    const hint = fine.querySelector(".fxprog-posfine__hint");
    if (hint) {
      if (state === "none") hint.textContent = t("FXPROG_POS_FINE_NONE");
      else if (state === "some") hint.textContent = t("FXPROG_POS_FINE_SOME", { n: Math.max(sup.pan, sup.tilt), m: sup.total });
      else hint.textContent = t("FXPROG_POS_SWIPE_HINT");
    }
  }

  // ── Unteransichten: Umschalten (Klick UND programmatisch) + Standardansicht je Kategorie ─────────
  function _activateSubtab(panelEl, stab, opts) {
    const tabsBar = stab.closest(".fxprog-subtabs");
    if (!tabsBar) return;
    const container = tabsBar.parentElement;
    tabsBar.querySelectorAll(".fxprog-subtab").forEach(s => s.classList.remove("fxprog-subtab--active"));
    stab.classList.add("fxprog-subtab--active");
    const id = stab.dataset.subtab;
    container.querySelectorAll("[data-panel]").forEach(p => {
      p.style.display = p.dataset.panel === id ? "" : "none";
    });
    if (id === "fine") _syncPosFields(panelEl);
    // Gobo-Fader + Thumbnails laden sobald Gobo-Sub-Tab per Klick aktiviert wird
    if ((id === "gobo" || id === "prism" || id === "wheel") && !(opts && opts.silent)) {
      _refreshWheelViews(panelEl);
    }
  }

  // Kategorie -> [Konfig-Schluessel, Standard, Pane-Id]. Jede Kategorie mit Unteransichten steht hier.
  const _DEFAULT_SUBVIEWS = {
    color:    { key: "default_view_color",    fallback: "fader" },
    position: { key: "default_view_position", fallback: "coarse" },
    beam:     { key: "default_view_beam",     fallback: "shutter" },
  };

  function _applyDefaultSubview(panelEl, category) {
    const def = _DEFAULT_SUBVIEWS[category];
    if (!def || !panelEl) return;
    const mc = panelEl._progMc || {};
    const pane = panelEl.querySelector(`.fxprog-pane[data-pane="${category}"]`);
    if (!pane) return;
    let want = mc[def.key] || def.fallback;
    let stab = pane.querySelector(`.fxprog-subtab[data-subtab="${want}"]`);
    if (!stab || stab.style.display === "none") {            // z.B. Picker ausgeblendet: auf den Standard zurueck
      stab = pane.querySelector(`.fxprog-subtab[data-subtab="${def.fallback}"]`);
    }
    if (stab) _activateSubtab(panelEl, stab, { silent: true });
  }

  // ── Panel-Aufbau: Panes in fxprog-main, Tab-Streifen in fxprog-tabs ──
  // ── Modul-Konfiguration live anwenden (Build + spaetere Properties-Aenderung) ──
  function _applyProgConfig(root, mc) {
    if (!root) return;
    mc = mc || {};
    root.style.setProperty("--prog-sel-color",   mc.sel_color   || "#ffe600");
    root.style.setProperty("--prog-fader-color", mc.fader_color || "#00ff00");
    root.classList.toggle("fxprog--no-glow", mc.sel_glow === false);

    // Pro-Fader-Typ Breite in % (Dimmer/Pan/Tilt): 0 (oder unset) = Auto
    // (breiter Standardwert aus CSS, siehe .vfader--main/.fxprog-pos-fader-col),
    // 1-100 erzwingt exakt diesen Prozentsatz der Zeilenbreite fuer GENAU
    // diesen einen Fader-Typ.
    [
      ["dimmer", "dimmer_width_pct", "--dimmer-fader-pct"],
      ["pan",    "pan_width_pct",    "--pan-fader-pct"],
      ["tilt",   "tilt_width_pct",   "--tilt-fader-pct"],
      ["dmx",    "dmx_width_pct",    "--dmx-fader-pct"],
    ].forEach(([, field, cssVar]) => {
      const v = parseInt(mc[field], 10);
      if (v > 0 && v <= 100) root.style.setProperty(cssVar, v + "%");
      else root.style.removeProperty(cssVar);
    });
    // Gobo-Icon-Groesse: 0 = Auto (CSS-Standard 32px), 16-80 = px-Override
    const iconPx = parseInt(mc.gobo_icon_size, 10) || 0;
    if (iconPx >= 16 && iconPx <= 80) {
      root.style.setProperty("--gobo-img-size", iconPx + "px");
      root.style.setProperty("--gobo-btn-size", (iconPx + 14) + "px");
    } else {
      root.style.removeProperty("--gobo-img-size");
      root.style.removeProperty("--gobo-btn-size");
    }
    // Modul-Config am Panel speichern fuer DMX-Direct-Fader-Breite
    const panelEl2 = root.closest("[data-panel-type]");
    if (panelEl2) panelEl2._progMc = mc;

    // HSV/CMY/RGB-Bloecke im Color-Fader-Tab ein-/ausblenden. flex:1 auf
    // .fxprog-cf-group sorgt dafuer, dass sich die verbleibenden sichtbaren
    // Bloecke den freiwerdenden Platz automatisch/augenblicklich teilen
    // (native Flexbox-Neuverteilung, kein weiterer JS-Eingriff noetig).
    let _firstVisibleGroup = null;
    root.querySelectorAll(".fxprog-cf-group[data-group]").forEach(g => {
      const key = "show_" + g.dataset.group;
      const visible = mc[key] !== false;
      g.style.display = visible ? "" : "none";
      g.classList.remove("fxprog-cf-group--first-visible");
      if (visible && !_firstVisibleGroup) _firstVisibleGroup = g;
    });
    _firstVisibleGroup?.classList.add("fxprog-cf-group--first-visible");

    // Picker-Subtab ein-/ausblenden; ist er gerade aktiv und wird ausgeblendet,
    // zurueck auf den Fader-Subtab wechseln.
    const pickerTab = root.querySelector('.fxprog-subtab[data-subtab="picker"]');
    if (pickerTab) {
      const show = mc.show_picker !== false;
      pickerTab.style.display = show ? "" : "none";
      if (!show && pickerTab.classList.contains("fxprog-subtab--active")) {
        root.querySelector('.fxprog-subtab[data-subtab="fader"]')?.click();
      }
    }

    // Standard-Unteransicht je Kategorie (Farbe, Position, Beam) - gilt beim Aufbau und bei jeder Aenderung
    if (panelEl2) Object.keys(_DEFAULT_SUBVIEWS).forEach(cat => _applyDefaultSubview(panelEl2, cat));

    // Ansichts-Modus: "combined" (Standard) zeigt die normale Tab-Sidebar
    // mit allen freigeschalteten Bereichen. Ein spezifischer Modus (z.B.
    // "position") blendet die Sidebar komplett aus und zeigt AUSSCHLIESSLICH
    // diesen einen Kontrollbereich in voller Breite - die Fixture-Selektion
    // bleibt global (window.ProgrammerState) und erfolgt dann ueber ein
    // anderes Panel (z.B. ein zweites Programmer-Panel im Combined-Modus
    // oder das Fixtures-Panel).
    const viewMode = mc.view_mode || "combined";
    const tabsEl = root.querySelector(".fxprog-tabs");
    root.classList.toggle("fxprog--single-view", viewMode !== "combined");
    if (tabsEl) tabsEl.style.display = (viewMode === "combined") ? "" : "none";
    if (viewMode !== "combined") {
      root.querySelectorAll(".fxprog-pane").forEach(pane => {
        pane.classList.toggle("fxprog-pane--active", pane.dataset.pane === viewMode);
      });
      root.querySelectorAll(".fxprog-tab").forEach(tab => {
        tab.classList.toggle("fxprog-tab--active", tab.dataset.tab === viewMode);
      });
    }
  }

  function _buildSidebar(panelEl, mc) {
    const main     = panelEl.querySelector(".fxprog-main");
    const tabStrip = panelEl.querySelector(".fxprog-tabs");
    if (!main || !tabStrip) return;

    const TABS = [
      { id: "fixtures", key: "FXPROG_TAB_FIXTURES" },
      { id: "dimmer",   key: "FXPROG_TAB_DIMMER" },
      { id: "position", key: "FXPROG_TAB_POSITION" },
      { id: "color",    key: "FXPROG_TAB_COLOR" },
      { id: "beam",     key: "FXPROG_TAB_BEAM" },
      { id: "focus",    key: "FXPROG_TAB_FOCUS" },
      { id: "dmx",      key: "FXPROG_TAB_DMX" },
    ];

    // Fixture-Typen (Kanal-Listen) einmalig laden, dann Tab-Verfuegbarkeit
    // fuer die aktuelle Selektion nachtraeglich aktualisieren.
    _loadFixtureTypes(() => { _updateTabAvailability(panelEl); _syncPosFields(panelEl); _syncRawFaders(panelEl); });

    // Tab-Streifen aufbauen
    TABS.forEach(({ id, key }, i) => {
      const tab = document.createElement("div");
      tab.className = "fxprog-tab" + (i === 0 ? " fxprog-tab--active" : "");
      tab.dataset.tab = id;
      tab.dataset.i18n = key;
      tab.textContent = t(key);
      tab.addEventListener("click", () => {
        if (tab.classList.contains("fxprog-tab--disabled")) return;
        tabStrip.querySelectorAll(".fxprog-tab").forEach(el => el.classList.remove("fxprog-tab--active"));
        tab.classList.add("fxprog-tab--active");
        main.querySelectorAll(".fxprog-pane").forEach(el => el.classList.remove("fxprog-pane--active"));
        main.querySelector(`.fxprog-pane[data-pane="${id}"]`)?.classList.add("fxprog-pane--active");
        if (_DEFAULT_SUBVIEWS[id]) _applyDefaultSubview(panelEl, id);   // beim Auswaehlen: Standardansicht zuerst
        if (id === "color") {
          requestAnimationFrame(() => {
            const cv = panelEl.querySelector("#__fxp_color_canvas");
            if (cv) _drawColorCanvas(cv);
          });
        }
        if (id === "beam") {
          _refreshWheelViews(panelEl);
        }
        _updateSidebarForSelection(panelEl);
      });
      tabStrip.appendChild(tab);
    });

    // Fixtures-Pane (enthält das Tile-Grid)
    const fixturesPane = document.createElement("div");
    fixturesPane.className = "fxprog-pane fxprog-pane--active";
    fixturesPane.dataset.pane = "fixtures";
    const sheet = document.createElement("div");
    sheet.className = "fxprog-sheet";
    fixturesPane.appendChild(sheet);
    main.appendChild(fixturesPane);

    // Dimmer-Pane (programmatisch: vertikaler Fader links + Quick-Button-Grid rechts)
    const dimmerPane = document.createElement("div");
    dimmerPane.className = "fxprog-pane";
    dimmerPane.dataset.pane = "dimmer";

    const dimmerWrap = document.createElement("div");
    dimmerWrap.className = "fxprog-dimmer";

    // Steuerelemente bleiben IMMER sichtbar & layoutstabil; ohne Selektion
    // werden sie nur ausgegraut/deaktiviert (siehe _updateSidebarForSelection),
    // statt durch einen Platzhaltertext ersetzt zu werden.
    const dimCtrl = document.createElement("div");
    dimCtrl.className = "fxprog-dimmer-controls fxprog-dimmer-layout fxprog-ctrl-gated fxprog-ctrl-gated--disabled";
    dimCtrl.dataset.feature = "dimmer";

    const dimFader = _makeVFader({
      label: t("FXPROG_TAB_DIMMER"),
      labelKey: "FXPROG_TAB_DIMMER",
      value: 0,
      onChange: (v) => {
        const sel = [...window.ProgrammerState.selectedIds];
        if (sel.length) window.ProgrammerState.setDimmer(sel, v);
      }
    });
    dimFader.dataset.faderId = "dimmer";
    dimFader.classList.add("vfader--main", "vfader--neutral");
    dimCtrl.appendChild(dimFader);

    // Vereinfachtes Layout: genau 5 Touch-Buttons, einspaltig, volle Hoehe.
    const qGrid = document.createElement("div");
    qGrid.className = "fxprog-quickbtns fxprog-quickbtns--dimmer";
    [
      { val: 100, label: "100%" },
      { val: 75,  label: "75%" },
      { val: 50,  label: "50%" },
      { val: 25,  label: "25%" },
      { val: 0,   label: "0%" },
    ].forEach(({ val, label }) => {
      const btn = document.createElement("button");
      btn.className = "fxprog-qbtn";
      btn.textContent = label;
      btn.addEventListener("click", () => {
        const sel = [...window.ProgrammerState.selectedIds];
        if (!sel.length) return;
        window.ProgrammerState.setDimmer(sel, val);
      });
      qGrid.appendChild(btn);
    });
    dimCtrl.appendChild(qGrid);
    dimmerWrap.appendChild(dimCtrl);
    dimmerPane.appendChild(dimmerWrap);
    main.appendChild(dimmerPane);

    // Color-Pane
    const colorPane = document.createElement("div");
    colorPane.className = "fxprog-pane";
    colorPane.dataset.pane = "color";
    colorPane.innerHTML = `
      <div class="fxprog-color">
        <div class="fxprog-subtabs fxprog-ctrl-gated fxprog-ctrl-gated--disabled" data-feature="color">
          <div class="fxprog-subtab fxprog-subtab--active" data-subtab="fader" data-i18n="FXPROG_SUBTAB_FADER">${t("FXPROG_SUBTAB_FADER")}</div>
          <div class="fxprog-subtab" data-subtab="picker" data-i18n="FXPROG_SUBTAB_PICKER">${t("FXPROG_SUBTAB_PICKER")}</div>
          <div class="fxprog-subtab" data-subtab="wheel" data-i18n="FXPROG_SUBTAB_WHEEL" style="display:none">${t("FXPROG_SUBTAB_WHEEL")}</div>
        </div>
        <div class="fxprog-color-picker-wrap fxprog-ctrl-gated fxprog-ctrl-gated--disabled" data-feature="color" data-panel="picker" style="display:none">
          <canvas class="fxprog-color-picker" id="__fxp_color_canvas"></canvas>
          <div class="fxprog-color-preview" id="__fxp_color_preview" style="background:#00ffff"></div>
        </div>
        <div class="fxprog-attrpane fxprog-beam-content fxprog-beam-content--gobo fxprog-ctrl-gated fxprog-ctrl-gated--disabled fxprog-color-wheel-wrap" data-feature="color" data-panel="wheel" style="display:none">
          <div class="fxprog-beam-faders fxprog-color-faders-wrap"></div>
          <div class="fxprog-gobo-strip fxprog-color-strip"></div>
        </div>
      </div>
    `;

    // Color-Fader Subtab: 3 Gruppen (HSV, CMY, RGB) mit Echtzeit-Kopplung
    const colorFaderWrap = document.createElement("div");
    colorFaderWrap.className = "fxprog-color-faders fxprog-ctrl-gated fxprog-ctrl-gated--disabled";
    colorFaderWrap.dataset.panel = "fader";
    colorFaderWrap.dataset.feature = "color";

    const _cf = {};
    let _cfUpdating = false;

    const _syncFromRgb = (r255, g255, b255, skipGroup) => {
      _cfUpdating = true;
      if (skipGroup !== "rgb") {
        _cf.red.setValue(DMX.byteToPct(r255));
        _cf.green.setValue(DMX.byteToPct(g255));
        _cf.blue.setValue(DMX.byteToPct(b255));
      }
      if (skipGroup !== "cmy") {
        _cf.cyan.setValue(100 - DMX.byteToPct(r255));
        _cf.magenta.setValue(100 - DMX.byteToPct(g255));
        _cf.yellow.setValue(100 - DMX.byteToPct(b255));
      }
      if (skipGroup !== "hsv") {
        const { h, s, v } = _rgb2hsv(r255, g255, b255);
        _cf.hue.setValue(h); _cf.sat.setValue(s); _cf.bright.setValue(v);
      }
      // Sat.-Fader-Verlauf folgt dynamisch der aktuellen Hue (dot2-Look):
      // grau (0%) -> volle Hue-Farbe (100%), statt statischem Grau-Verlauf.
      const satTrack = _cf.sat && _cf.sat.querySelector(".vfader__track");
      if (satTrack) satTrack.style.setProperty("--sat-hue", DMX.pctToDeg360(_cf.hue.getValue()));
      const preview = panelEl.querySelector("#__fxp_color_preview");
      if (preview) preview.style.background = `rgb(${r255},${g255},${b255})`;
      _cfUpdating = false;
    };
    const _applyColor = (r, g, b) => {
      const sel = [...window.ProgrammerState.selectedIds];
      if (sel.length) window.ProgrammerState.setColor(sel, r, g, b);
    };

    [
      { groupKey: "hsv", label: "HSV", faders: [
        { key: "hue",   label: "Hue",    trackClass: "vfader__track--hue",
          formatVal: v => DMX.pctToDeg360(v) + "°" },
        { key: "sat",   label: "Sat.",   trackClass: "vfader__track--sat" },
        { key: "bright",label: "Brt.",   trackClass: "vfader__track--bright" },
      ]},
      { groupKey: "cmy", label: "CMY", faders: [
        { key: "cyan",   label: "Cyan", trackClass: "vfader__track--cyan" },
        { key: "magenta",label: "Mag.", trackClass: "vfader__track--magenta" },
        { key: "yellow", label: "Yel.", trackClass: "vfader__track--yellow" },
      ]},
      { groupKey: "rgb", label: "RGB", faders: [
        { key: "red",  label: "Red",  trackClass: "vfader__track--red",
          formatVal: v => String(DMX.pctToByte(v)) },
        { key: "green",label: "Grn.", trackClass: "vfader__track--green",
          formatVal: v => String(DMX.pctToByte(v)) },
        { key: "blue", label: "Blue", trackClass: "vfader__track--blue",
          formatVal: v => String(DMX.pctToByte(v)) },
      ]},
    ].forEach(({ groupKey, label: gLabel, faders }) => {
      const group = document.createElement("div");
      group.className = "fxprog-cf-group";
      group.dataset.group = groupKey;
      const gTitle = document.createElement("div");
      gTitle.className = "fxprog-cf-group__label";
      gTitle.textContent = gLabel;
      group.appendChild(gTitle);
      const gFaders = document.createElement("div");
      gFaders.className = "fxprog-cf-group__faders";
      // Reset-Default: Cyan=100%, Magenta=0%, Yellow=0% (== RGB Cyan)
      const _CF_DEFAULTS = { hue: 50, sat: 100, bright: 100, cyan: 100, magenta: 0, yellow: 0, red: 0, green: 100, blue: 100 };
      faders.forEach(({ key, label: fLabel, trackClass, formatVal: fmtFn }) => {
        const vf = _makeVFader({
          label: fLabel, value: _CF_DEFAULTS[key] ?? 0, trackClass, formatVal: fmtFn,
          onChange: () => {
            if (_cfUpdating) return;
            let r, g, b;
            if (groupKey === "hsv") {
              ({ r, g, b } = _hsv2rgb(_cf.hue.getValue(), _cf.sat.getValue(), _cf.bright.getValue()));
            } else if (groupKey === "cmy") {
              r = DMX.pctToByte(100 - _cf.cyan.getValue());
              g = DMX.pctToByte(100 - _cf.magenta.getValue());
              b = DMX.pctToByte(100 - _cf.yellow.getValue());
            } else {
              r = DMX.pctToByte(_cf.red.getValue());
              g = DMX.pctToByte(_cf.green.getValue());
              b = DMX.pctToByte(_cf.blue.getValue());
            }
            _syncFromRgb(r, g, b, groupKey);
            _applyColor(r, g, b);
          }
        });
        vf.dataset.color = key;
        _cf[key] = vf;
        gFaders.appendChild(vf);
      });
      group.appendChild(gFaders);
      colorFaderWrap.appendChild(group);
    });
    // Initialen Sat.-Verlauf auf die Default-Hue (Cyan = 180°) setzen
    const _satTrackInit = _cf.sat && _cf.sat.querySelector(".vfader__track");
    if (_satTrackInit) _satTrackInit.style.setProperty("--sat-hue", DMX.pctToDeg360(_cf.hue.getValue()));
    colorPane.querySelector(".fxprog-color").appendChild(colorFaderWrap);
    main.appendChild(colorPane);

    // Position-Pane: Pan + Tilt Fader + Quick-Actions
    const posPane = document.createElement("div");
    posPane.className = "fxprog-pane";
    posPane.dataset.pane = "position";

    const posWrap = document.createElement("div");
    posWrap.className = "fxprog-pos";

    // Umschalter Grob / Fein (wie Farbe: Fader / Picker). Grob ist die bisherige Ansicht.
    const posSubtabs = document.createElement("div");
    posSubtabs.className = "fxprog-subtabs fxprog-ctrl-gated fxprog-ctrl-gated--disabled";
    posSubtabs.dataset.feature = "position";
    [["coarse", "FXPROG_POS_COARSE"], ["fine", "FXPROG_POS_FINE"]].forEach(([id, key], i) => {
      const s = document.createElement("div");
      s.className = "fxprog-subtab" + (i === 0 ? " fxprog-subtab--active" : "");
      s.dataset.subtab = id;
      s.dataset.i18n = key;
      s.textContent = t(key);
      posSubtabs.appendChild(s);
    });
    posWrap.appendChild(posSubtabs);

    const posCtrl = document.createElement("div");
    posCtrl.className = "fxprog-dimmer-controls fxprog-dimmer-layout fxprog-ctrl-gated fxprog-ctrl-gated--disabled";
    posCtrl.dataset.feature = "position";
    posCtrl.dataset.panel = "coarse";

    ["pan", "tilt"].forEach(axis => {
      const col = document.createElement("div");
      col.className = "fxprog-pos-fader-col";
      col.dataset.axis = axis;
      const fader = _makeVFader({
        label: axis === "pan" ? "Pan" : "Tilt",
        value: 50,
        // Echte Gradzahlen aus dem GDTF-Profil der Selektion (z.B. Pan
        // -270..+270°) statt einer fixen Annahme - live pro Selektion.
        formatVal: v => {
          const [from, to] = _panTiltPhysicalRange(panelEl, axis);
          return (from + (v / 100) * (to - from)).toFixed(1) + "°";
        },
        onChange: (v) => {
          const sel = [...window.ProgrammerState.selectedIds];
          if (!sel.length) return;
          if (axis === "pan") window.ProgrammerState.setPan(sel, v);
          else                window.ProgrammerState.setTilt(sel, v);
        }
      });
      fader.dataset.faderId = axis;
      fader.classList.add("vfader--neutral");
      const centerBtn = document.createElement("button");
      centerBtn.className = "fxprog-qbtn fxprog-center-btn";
      centerBtn.dataset.i18n = "FXPROG_POS_CENTER";
      centerBtn.textContent = t("FXPROG_POS_CENTER");
      centerBtn.addEventListener("click", () => {
        const sel = [...window.ProgrammerState.selectedIds];
        if (!sel.length) return;
        if (axis === "pan") window.ProgrammerState.setPan(sel, 50);
        else                window.ProgrammerState.setTilt(sel, 50);
        fader.setValue(50);
      });
      col.appendChild(fader);
      col.appendChild(_makeSwipeField(panelEl, axis, "coarse"));   // Zahl: tippen = eingeben, wischen = aendern
      col.appendChild(centerBtn);
      posCtrl.appendChild(col);
    });
    _buildRawFaderCols(panelEl, "position", posCtrl);                       // Speed neben Pan/Tilt (nur Geraete mit diesem Kanal)

    // Grosse Haupt-Buttons: nur Home + Flip (fett, touch-freundlich)
    const posMainBtns = document.createElement("div");
    posMainBtns.className = "fxprog-pos-mainbtns";
    [
      { key: "FXPROG_POS_HOME",  action: () => {
          const sel = [...window.ProgrammerState.selectedIds]; if (!sel.length) return;
          window.ProgrammerState.batchSet((av, en) => { for (const id of sel) { en(id); av[id].pan = 50; av[id].tilt = 50; } });
          sel.forEach(id => window.ProgrammerState.sendToServer([id], { pan: DMX.pctToByte(50), tilt: DMX.pctToByte(50), pan16: DMX.pctToV16(50), tilt16: DMX.pctToV16(50) }));
        }},
      { key: "FXPROG_POS_FLIP",  action: () => {
          const sel = [...window.ProgrammerState.selectedIds]; if (!sel.length) return;
          window.ProgrammerState.batchSet((av, en) => { for (const id of sel) { en(id); av[id].pan = ((av[id].pan ?? 50) + 50) % 100; } });
          sel.forEach(id => {
            const v = window.ProgrammerState.getVal(id);
            window.ProgrammerState.sendToServer([id], { pan: DMX.pctToByte(v.pan ?? 50), pan16: DMX.pctToV16(v.pan ?? 50) });
          });
        }},
    ].forEach(({ key, action }) => {
      const btn = document.createElement("button");
      btn.className = "fxprog-qbtn fxprog-qbtn--big";
      btn.dataset.i18n = key;
      btn.textContent = t(key);
      btn.addEventListener("click", action);
      posMainBtns.appendChild(btn);
    });
    posMainBtns.appendChild(_buildSimAimButton(panelEl, { cls: "fxprog-qbtn fxprog-qbtn--big", labelKey: "FXPROG_AIM_SET", tipKey: "FXPROG_AIM_SET_TIP", toggle: true, onClick: (A) => A.arm(!A.armed) }));
    posCtrl.appendChild(posMainBtns);

    posWrap.appendChild(posCtrl);

    // Fein-Ansicht: pro Achse das Feld des Fein-Kanals (0-255), wischbar; ohne Fein-Kanal klarer Hinweis statt Leere
    const posFine = document.createElement("div");
    posFine.className = "fxprog-posfine fxprog-ctrl-gated fxprog-ctrl-gated--disabled";
    posFine.dataset.feature = "position";
    posFine.dataset.panel = "fine";
    posFine.dataset.fine = "unknown";
    posFine.style.display = "none";
    const fineFields = document.createElement("div");
    fineFields.className = "fxprog-posfine__fields";
    ["pan", "tilt"].forEach(axis => {
      const col = document.createElement("div");
      col.className = "fxprog-posfine__col";
      col.dataset.axis = axis;
      const label = document.createElement("div");
      label.className = "fxprog-posfine__label";
      label.dataset.i18n = axis === "pan" ? "FXPROG_POS_PAN_FINE" : "FXPROG_POS_TILT_FINE";
      label.textContent = t(label.dataset.i18n);
      col.appendChild(label);
      col.appendChild(_makeSwipeField(panelEl, axis, "fine"));
      const caption = document.createElement("div");
      caption.className = "fxprog-numfield-caption";
      col.appendChild(caption);
      fineFields.appendChild(col);
    });
    posFine.appendChild(fineFields);
    const fineHint = document.createElement("div");
    fineHint.className = "fxprog-posfine__hint";
    fineHint.setAttribute("role", "status");
    posFine.appendChild(fineHint);
    posWrap.appendChild(posFine);
    posPane.appendChild(posWrap);
    main.appendChild(posPane);

    // Beam-Pane: Shutter/Strobe/Gobo/Prism mit Sub-Tabs (dot2-Stil)
    {
      const beamPane = document.createElement("div");
      beamPane.className = "fxprog-pane";
      beamPane.dataset.pane = "beam";

      const beamWrap = document.createElement("div");
      beamWrap.className = "fxprog-beam fxprog-ctrl-gated fxprog-ctrl-gated--disabled";
      beamWrap.dataset.feature = "beam";

      const beamSubtabs = document.createElement("div");
      beamSubtabs.className = "fxprog-subtabs";
      [
        { id: "shutter", key: "FXPROG_BEAM_SUBTAB_SHUTTER" },
        { id: "gobo",    key: "FXPROG_BEAM_SUBTAB_GOBO" },
        { id: "prism",   key: "FXPROG_BEAM_SUBTAB_PRISM" },
      ].forEach(({ id: stId, key: stKey }, i) => {
        const s = document.createElement("div");
        s.className = "fxprog-subtab" + (i === 0 ? " fxprog-subtab--active" : "");
        s.dataset.subtab = stId;
        s.dataset.i18n = stKey;
        s.textContent = t(stKey);
        beamSubtabs.appendChild(s);
      });
      beamWrap.appendChild(beamSubtabs);

      [
        { id: "shutter", attrs: [{ key: "strobe", label: "Strobe" }] },
        { id: "gobo",    attrs: [{ key: "gobo",   label: "Gobo" }] },
        { id: "prism",   attrs: [{ key: "prism",  label: "Prism" }] },
      ].forEach(({ id: contentId, attrs }, i) => {
        const content = document.createElement("div");
        content.className = "fxprog-attrpane fxprog-beam-content";
        if (contentId === "gobo") content.classList.add("fxprog-beam-content--gobo");
        content.dataset.panel = contentId;
        if (i !== 0) content.style.display = "none";

        if (contentId === "prism") content.classList.add("fxprog-beam-content--gobo");
        if (contentId === "prism") {
          // Prisma: wie Gobo - eine Fader-Spalte je Prismenrad oben, die Prismen (Slots) als Knoepfe darunter (siehe _rebuildWheelFaders)
          const prismFaders = document.createElement("div");
          prismFaders.className = "fxprog-beam-faders fxprog-prism-faders-wrap";
          content.appendChild(prismFaders);
          const prismStrip = document.createElement("div");
          prismStrip.className = "fxprog-gobo-strip fxprog-prism-strip";
          content.appendChild(prismStrip);
        } else if (contentId === "gobo") {
          // Gobo: dynamische Fader-Spalten (1 pro Wheel) oben, Thumbnail-Strip unten.
          // _rebuildGoboFaders() befuellt fadersWrap auf Basis der selektierten Fixture.
          const fadersWrap = document.createElement("div");
          fadersWrap.className = "fxprog-beam-faders fxprog-gobo-faders-wrap";
          content.appendChild(fadersWrap);

          const thumbStrip = document.createElement("div");
          thumbStrip.className = "fxprog-gobo-strip";
          content.appendChild(thumbStrip);
        } else {
          attrs.forEach(({ key, label }) => {
            const vf = _makeVFader({
              label, value: 0,
              onChange: (v) => {
                const sel = [...window.ProgrammerState.selectedIds];
                if (sel.length) window.ProgrammerState.setBeamAttr(key, sel, v);
              }
            });
            vf.classList.add("vfader--neutral", "vfader--main");
            vf.dataset.faderId = key;
            if (contentId === "shutter") {
              // Shutter/Strobe: Fader mit Voreinstellungs-Knoepfen darunter (aus den DMX-Bereichen des Geraets, siehe _renderShutterPresets)
              const col = document.createElement("div");
              col.className = "fxprog-focus-col";
              col.appendChild(vf);
              const presets = document.createElement("div");
              presets.className = "fxprog-focus-presets fxprog-shutter-presets";
              col.appendChild(presets);
              content.appendChild(col);
            } else content.appendChild(vf);
          });
        }
        beamWrap.appendChild(content);
      });
      beamPane.appendChild(beamWrap);
      main.appendChild(beamPane);
    }

    // Fokus-Pane: Focus + Zoom Fader mit Preset-Buttons (Near/Center/Far)
    {
      const focusPane = document.createElement("div");
      focusPane.className = "fxprog-pane";
      focusPane.dataset.pane = "focus";

      const focusWrap = document.createElement("div");
      focusWrap.className = "fxprog-attrpane fxprog-ctrl-gated fxprog-ctrl-gated--disabled";
      focusWrap.dataset.feature = "focus";

      [
        { key: "focus", label: "Focus", presets: [
          { key: "FXPROG_FOCUS_NEAR",   val: 0 },
          { key: "FXPROG_POS_CENTER",   val: 50 },
          { key: "FXPROG_FOCUS_FAR",    val: 100 },
        ]},
        { key: "zoom", label: "Zoom", presets: [
          { key: "FXPROG_FOCUS_WIDE",   val: 0 },
          { key: "FXPROG_POS_CENTER",   val: 50 },
          { key: "FXPROG_FOCUS_NARROW", val: 100 },
        ]},
      ].forEach(({ key: attrKey, label, presets }) => {
        const col = document.createElement("div");
        col.className = "fxprog-focus-col";

        const vf = _makeVFader({
          label, value: 0,
          onChange: (v) => {
            const sel = [...window.ProgrammerState.selectedIds];
            if (sel.length) window.ProgrammerState.setBeamAttr(attrKey, sel, v);
          }
        });
        vf.classList.add("vfader--neutral", "vfader--main");
        vf.dataset.faderId = attrKey;
        col.appendChild(vf);

        const presetRow = document.createElement("div");
        presetRow.className = "fxprog-focus-presets";
        presets.forEach(({ key: presetKey, val }) => {
          const btn = document.createElement("button");
          btn.className = "fxprog-qbtn";
          btn.dataset.i18n = presetKey;
          btn.textContent = t(presetKey);
          btn.addEventListener("click", () => {
            const sel = [...window.ProgrammerState.selectedIds];
            if (!sel.length) return;
            window.ProgrammerState.setBeamAttr(attrKey, sel, val);
            vf.setValue(val);
          });
          presetRow.appendChild(btn);
        });
        col.appendChild(presetRow);
        col.appendChild(attrKey === "focus"
          ? _buildSimAimButton(panelEl, { cls: "fxprog-qbtn", labelKey: "FXPROG_AIM_AUTO_FOCUS", tipKey: "FXPROG_AIM_AUTO_FOCUS_TIP", onClick: (A, ids) => _aimMissToast(A.auto("focus", ids)) })
          : _buildSimAimButton(panelEl, { cls: "fxprog-qbtn", labelKey: "FXPROG_AIM_AUTO_ZOOM", tipKey: "FXPROG_AIM_AUTO_ZOOM_TIP", onClick: (A, ids) => _autoZoomDialog(A, ids) }));
        focusWrap.appendChild(col);
      });
      _buildRawFaderCols(panelEl, "focus", focusWrap);                       // Iris/Frost neben Fokus/Zoom (nur Geraete mit diesen Kanaelen)
      focusPane.appendChild(focusWrap);
      main.appendChild(focusPane);
    }

    // DMX-Direct-Pane: ein Fader pro GDTF-Kanal der selektierten Fixture
    {
      const dmxPane = document.createElement("div");
      dmxPane.className = "fxprog-pane";
      dmxPane.dataset.pane = "dmx";

      const dmxWrap = document.createElement("div");
      dmxWrap.className = "fxprog-dmxdirect";

      const dmxFadersRow = document.createElement("div");
      dmxFadersRow.className = "fxprog-dmxdirect__faders";
      dmxFadersRow.style.display = "none";

      const dmxEmpty = document.createElement("div");
      dmxEmpty.className = "fxprog-stub fxprog-dmxdirect__empty";
      dmxEmpty.dataset.i18n = "FXPROG_DMX_EMPTY";
      dmxEmpty.textContent = t("FXPROG_DMX_EMPTY");

      dmxWrap.appendChild(dmxFadersRow);
      dmxWrap.appendChild(dmxEmpty);
      dmxPane.appendChild(dmxWrap);
      main.appendChild(dmxPane);
    }

    _wireSidebarEvents(panelEl);

    // Global State Sync: alle Panels bei ProgrammerState-Änderungen aktualisieren
    if (panelEl._progSyncUI) document.removeEventListener("programmer-state-updated", panelEl._progSyncUI);
    const _syncPanelUI = () => {
      if (_panelGone(panelEl, "programmer-state-updated", _syncPanelUI)) return;
      const PS = window.ProgrammerState;
      panelEl.querySelectorAll(".fxprog-tile[data-fx-id]").forEach(tile => {
        tile.classList.toggle("fxprog-tile--selected", PS.selectedIds.has(tile.dataset.fxId));
        _updateTile(tile, tile.dataset.fxId);
      });
      // Markierung "ungespeicherte Aenderung" je Kategorie: NUR wenn dort manuell etwas bedient wurde (nicht, wenn eine Cue
      // Werte setzt - die stehen zwar im Programmer-Zustand, sind aber nicht "angefasst")
      const TAB_ATTRS = { dimmer: ["dimmer"], position: ["pan", "tilt"], color: ["color"], beam: ["strobe", "gobo", "prism"], focus: ["focus", "zoom"] };
      panelEl.querySelectorAll(".fxprog-tab[data-tab]").forEach((tab) => {
        const id = tab.dataset.tab;
        const dirty = id === "dmx" ? PS.hasTouched((a) => a.startsWith("_raw")) : (TAB_ATTRS[id] ? PS.hasTouched(TAB_ATTRS[id]) : false);
        tab.classList.toggle("fxprog-tab--dirty", dirty);
      });

      // Selektion tracken: nur bei Selektionswechsel vollstaendigen DOM-Rebuild
      // ausloesen. Reine Wertaenderungen (Fader-Drag) aktualisieren nur Fader-
      // Werte -> verhindert das Flackern der Gobo-Auswahl.
      const selKey = [...PS.selectedIds].sort().join(",");
      const selChanged = selKey !== panelEl._lastSelKey;
      panelEl._lastSelKey = selKey;

      if (selChanged) {
        _updateSidebarForSelection(panelEl);
      } else if (PS.selectedIds.size > 0) {
        const firstId = [...PS.selectedIds][0];
        const val = PS.getVal(firstId);
        const dimEl = panelEl.querySelector(".vfader[data-fader-id='dimmer']");
        if (dimEl?.setValue && !dimEl.isDragging) dimEl.setValue(val.dimmer ?? 0);
        const panEl = panelEl.querySelector(".vfader[data-fader-id='pan']");
        if (panEl?.setValue && !panEl.isDragging) panEl.setValue(val.pan ?? 50);
        const tiltEl = panelEl.querySelector(".vfader[data-fader-id='tilt']");
        if (tiltEl?.setValue && !tiltEl.isDragging) tiltEl.setValue(val.tilt ?? 50);
        ["strobe", "gobo", "prism", "focus", "zoom"].forEach(key => {
          const el = panelEl.querySelector(`.vfader[data-fader-id='${key}']`);
          if (el?.setValue && !el.isDragging) el.setValue(val[key] ?? 0);
        });
      }

      // Color-Picker/Fader/andere Panels -> Fader-Tab-Sync
      if (PS.selectedIds.size > 0) {
        const firstId = [...PS.selectedIds][0];
        const col = PS.getVal(firstId).color;
        if (col) _syncFromRgb(col.r, col.g, col.b);
      }

      // Dezentes "touched"-Akzentlinie (rot, rechte Seite des jeweiligen
      // Fader-Tracks, siehe .vfader--touched) fuer manuell veraenderte/per
      // Preset zugewiesene Attribute - unabhaengig von selChanged, damit
      // der Akzent auch nach einem vollstaendigen Sidebar-Rebuild stimmt.
      const touchId = PS.selectedIds.size > 0 ? [...PS.selectedIds][0] : null;
      ["dimmer", "pan", "tilt", "strobe", "gobo", "prism", "focus", "zoom"].forEach(key => {
        const el = panelEl.querySelector(`.vfader[data-fader-id='${key}']`);
        if (el) el.classList.toggle("vfader--touched", !!touchId && PS.isAttrTouched(touchId, key));
      });
      ["hue", "sat", "bright", "red", "green", "blue"].forEach(key => {
        const el = panelEl.querySelector(`.vfader[data-fader-id='${key}']`);
        if (el) el.classList.toggle("vfader--touched", !!touchId && PS.isAttrTouched(touchId, "color"));
      });
      panelEl.querySelectorAll(".vfader[data-dmx-offset]").forEach(el => {
        const offset = el.dataset.dmxOffset;
        el.classList.toggle("vfader--touched", !!touchId && PS.isAttrTouched(touchId, "_raw" + offset));
      });
    };
    document.addEventListener("programmer-state-updated", _syncPanelUI);
    panelEl._progSyncUI = _syncPanelUI;
    const _syncGroupHeads = () => {
      if (!panelEl.isConnected) { document.removeEventListener("programmer-state-updated", _syncGroupHeads); return; }
      const PSg = window.ProgrammerState;
      const stGroups = (client.state && client.state.groups) || {};
      panelEl.querySelectorAll(".fxprog-group__label--group").forEach((el) => {
        const ids = (stGroups[el.dataset.group] || []).filter((id) => (_getState(panelEl).fixtures || {})[id]);
        el.classList.toggle("fxprog-group__label--selected", ids.length > 0 && ids.every((id) => PSg.selectedIds.has(id)));
      });
    };
    document.addEventListener("programmer-state-updated", _syncGroupHeads);

    // Race-condition fix: Fixtures bereits im State → sofort rendern
    requestAnimationFrame(() => {
      const st = _getState(panelEl);
      if (st.fixtures && Object.keys(st.fixtures).length > 0) {
        _renderDot2Grid(panelEl, st.fixtures);
        _updateSidebarForSelection(panelEl);
      }
      // Gleiches Rennen bei den Preset-Auswahlen der Reiter: der state_snapshot kommt, bevor die Seitenleiste steht, das
      // Ereignis ginge verloren (Dropdowns fehlten nach dem ersten Laden bis zu einem Neuladen) - jetzt nachreichen.
      const globalState = (typeof client !== "undefined" && client.state) || {};
      document.dispatchEvent(new CustomEvent("presets-data-updated", { detail: {
        presets: globalState.presets || {},
        preset_groups: globalState.preset_groups || [],
      }}));
    });

    _applyProgConfig(panelEl.querySelector(".fxprog"), mc);
  }

  function _wireSidebarEvents(panelEl) {
    // Sub-Tabs: generisch fuer alle Panes (Color, Position, Beam, ...)
    panelEl.querySelectorAll(".fxprog-subtab[data-subtab]").forEach(stab => {
      stab.addEventListener("click", () => {
        if (stab.closest(".fxprog-ctrl-gated--disabled")) return;
        _activateSubtab(panelEl, stab);
      });
    });
    // Canvas-Click + ResizeObserver
    const canvas = panelEl.querySelector("#__fxp_color_canvas");
    if (canvas) {
      canvas.addEventListener("click", (e) => {
        if (canvas.closest(".fxprog-ctrl-gated--disabled")) return;
        const ctx2d = canvas.getContext("2d");
        if (!ctx2d) return;
        const rect = canvas.getBoundingClientRect();
        const px = ctx2d.getImageData(Math.round(e.clientX - rect.left), Math.round(e.clientY - rect.top), 1, 1).data;
        const r = px[0], g = px[1], b = px[2];
        const preview = panelEl.querySelector("#__fxp_color_preview");
        if (preview) preview.style.background = `rgb(${r},${g},${b})`;
        const sel = [...window.ProgrammerState.selectedIds];
        if (!sel.length) return;
        window.ProgrammerState.setColor(sel, r, g, b);
      });
      if (typeof ResizeObserver !== "undefined") {
        const ro = new ResizeObserver(() => {
          if (canvas.closest(".fxprog-pane--active")) _drawColorCanvas(canvas);
        });
        ro.observe(canvas);
      }
    }
  }

  function _drawColorCanvas(canvas) {
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const bcr = canvas.getBoundingClientRect();
    const w = Math.round(bcr.width)  || canvas.offsetWidth  || 200;
    const h = Math.round(bcr.height) || canvas.offsetHeight || 120;
    if (w <= 0 || h <= 0) return;
    canvas.width = w;
    canvas.height = h;
    const hueGrad = ctx.createLinearGradient(0, 0, w, 0);
    for (let i = 0; i <= 360; i += 30) hueGrad.addColorStop(i / 360, `hsl(${i},100%,50%)`);
    ctx.fillStyle = hueGrad;
    ctx.fillRect(0, 0, w, h);
    const satGrad = ctx.createLinearGradient(0, 0, 0, h);
    satGrad.addColorStop(0, "rgba(255,255,255,0)");
    satGrad.addColorStop(1, "rgba(0,0,0,1)");
    ctx.fillStyle = satGrad;
    ctx.fillRect(0, 0, w, h);
  }

  // ── Feature-Erkennung: welche Sidebar-Tabs passen zur Selektion? ────
  let _fixtureTypesCache = null;
  let _fixtureTypesPromise = null;
  document.addEventListener("fixture-library-changed", () => { _fixtureTypesCache = null; _fixtureTypesPromise = null; });
  function _loadFixtureTypes(onReady) {
    if (_fixtureTypesCache) { onReady?.(_fixtureTypesCache); return; }
    if (!_fixtureTypesPromise) {
      _fixtureTypesPromise = fetch("/fixture-types")
        .then(res => res.json())
        .then(types => { _fixtureTypesCache = types; return types; })
        .catch(() => { _fixtureTypesCache = []; return []; });
    }
    _fixtureTypesPromise.then(onReady);
  }

  const _FEATURE_MATCHERS = {
    dimmer:   /dim|intensity/i,
    position: /pan|tilt/i,
    color:    /red|green|blue|cyan|magenta|yellow|colou?r|cto|white/i,
    beam:     /gobo|prism|strobe|shutter/i,
    focus:    /focus|zoom|iris|frost/i,
  };

  // Einzel-Fixture-Feature-Check (im Gegensatz zu _featuresForSelection,
  // das die UNION ueber die gesamte Selektion bildet). Faellt bei noch
  // nicht geladenem/unbekanntem Profil auf "true" zurueck (fail-open, kein
  // Flackern/Verstecken bevor Fixture-Typen geladen sind).
  function _fixtureHasFeature(fx, feature) {
    const channels = _channelsForFixture(fx, _fixtureTypesCache);
    if (!channels.length) return true;
    const re = _FEATURE_MATCHERS[feature];
    return channels.some(c => re.test(c.name || ""));
  }

  function _channelsForFixture(fx, fixtureTypes) {
    const ft = (fixtureTypes || []).find(t => t.id === fx.fixture_type);
    if (!ft) return [];
    const modes = ft.modes || [];
    const modeDef = modes.find(m => m.name === fx.mode) || modes[0];
    return modeDef ? (modeDef.channels || []) : [];
  }

  // Echter physikalischer Gradbereich (z.B. Pan -270..+270°) aus dem GDTF-
  // Profil der aktuell (ersten) selektierten Fixture - fuer die Live-
  // Gradanzeige im Position-Tab. Faellt auf plausible Standardwerte zurueck,
  // wenn keine Selektion vorliegt oder das Profil keinen Bereich liefert.
  function _panTiltPhysicalRange(panelEl, axis) {
    const defaults = axis === "pan" ? [-270, 270] : [-135, 135];
    const PS = window.ProgrammerState;
    if (!PS.selectedIds.size) return defaults;
    const fx = (_getState(panelEl).fixtures || {})[[...PS.selectedIds][0]];
    if (!fx) return defaults;
    const chName = axis === "pan" ? "Pan" : "Tilt";
    const ch = _channelsForFixture(fx, _fixtureTypesCache).find(c => c.name === chName);
    if (ch && typeof ch.physical_from === "number" && typeof ch.physical_to === "number") {
      return [ch.physical_from, ch.physical_to];
    }
    return defaults;
  }

  function _featuresForSelection(panelEl) {
    const PS = window.ProgrammerState;
    const fixtures = _getState(panelEl).fixtures || {};
    const feats = new Set();
    let anyChannelsResolved = false;
    for (const id of PS.selectedIds) {
      const fx = fixtures[id];
      if (!fx) continue;
      const channels = _channelsForFixture(fx, _fixtureTypesCache);
      if (channels.length) anyChannelsResolved = true;
      for (const ch of channels) {
        const name = ch.name || "";
        for (const [feat, re] of Object.entries(_FEATURE_MATCHERS)) {
          if (re.test(name)) feats.add(feat);
        }
      }
    }
    return { feats, anyChannelsResolved };
  }

  // Berechnet Tab-/Feature-Verfuegbarkeit EINMAL und wendet sie auf die
  // Tab-Buttons an. Gibt {feats, anyChannelsResolved, hasSel} zurueck, damit
  // _updateSidebarForSelection dieselbe Berechnung auch fuer das strikte
  // Pane-Control-Disabling wiederverwenden kann (kein zweifaches Berechnen,
  // und Tab- und Control-Freischaltung koennen so nie auseinanderlaufen).
  function _updateTabAvailability(panelEl) {
    const PS = window.ProgrammerState;
    const hasSel = PS.selectedIds.size > 0;
    const { feats, anyChannelsResolved } = hasSel
      ? _featuresForSelection(panelEl)
      : { feats: new Set(), anyChannelsResolved: false };
    panelEl.querySelectorAll(".fxprog-tab[data-tab]").forEach(tab => {
      const id = tab.dataset.tab;
      if (id === "fixtures") { tab.classList.remove("fxprog-tab--disabled"); return; }
      if (id === "dmx") { tab.classList.toggle("fxprog-tab--disabled", !hasSel); return; }
      if (!hasSel) { tab.classList.add("fxprog-tab--disabled"); return; }
      // Jeder Tab richtet sich strikt danach, ob mindestens eine gewaehlte
      // Fixture den passenden Kanal besitzt (Union bei Multi-Select). Ein
      // reines Dimmer-Pack darf den Farbe-Tab NICHT freischalten. Kann fuer
      // KEINE gewaehlte Fixture auch nur ein Kanal aufgeloest werden (z.B.
      // Fixture-Typen noch nicht geladen), schalten wir sicherheitshalber
      // alle Tabs frei statt sie dauerhaft zu blockieren.
      const enabled = !anyChannelsResolved || feats.has(id);
      tab.classList.toggle("fxprog-tab--disabled", !enabled);
    });
    return { feats, anyChannelsResolved, hasSel };
  }

  function _updateSidebarForSelection(panelEl) {
    const PS = window.ProgrammerState;
    const { feats, anyChannelsResolved, hasSel } = _updateTabAvailability(panelEl);
    // Steuerelemente bleiben immer sichtbar/layoutstabil - werden aber
    // STRIKT nach demselben Feature-Check wie die Tabs deaktiviert: ohne
    // Selektion ODER wenn keine gewaehlte Fixture das jeweilige Feature
    // unterstuetzt, sind Fader/Buttons weder klickbar noch draggbar
    // (pointer-events:none + natives disabled auf <button>-Elementen).
    panelEl.querySelectorAll(".fxprog-ctrl-gated").forEach(el => {
      const feature = el.dataset.feature;
      const enabled = hasSel && (!feature || !anyChannelsResolved || feats.has(feature));
      el.classList.toggle("fxprog-ctrl-gated--disabled", !enabled);
      el.querySelectorAll("button").forEach(btn => { btn.disabled = !enabled; });
    });
    if (hasSel) {
      const firstId = [...PS.selectedIds][0];
      const val = PS.getVal(firstId);
      const dimEl = panelEl.querySelector(".vfader[data-fader-id='dimmer']");
      if (dimEl?.setValue) dimEl.setValue(val.dimmer ?? 0);
      const panEl = panelEl.querySelector(".vfader[data-fader-id='pan']");
      if (panEl?.setValue) panEl.setValue(val.pan ?? 50);
      const tiltEl = panelEl.querySelector(".vfader[data-fader-id='tilt']");
      if (tiltEl?.setValue) tiltEl.setValue(val.tilt ?? 50);
      ["strobe", "gobo", "prism", "focus", "zoom"].forEach(key => {
        const el = panelEl.querySelector(`.vfader[data-fader-id='${key}']`);
        if (el?.setValue) el.setValue(val[key] ?? 0);
      });
    }
    _syncPosFields(panelEl);   // Pan/Tilt-Zahlenfelder + Fein-Verfuegbarkeit
    _rebuildDmxDirectPane(panelEl);
    // Raeder (Gobo, Prisma, Farbrad): Fader-Spalten + Slot-Knoepfe der selektierten Geraete aktualisieren
    _refreshWheelViews(panelEl);
  }

  // ── DMX Direct: Fader-Reihe neu aufbauen (bei Selektionswechsel) ────
  function _rebuildDmxDirectPane(panelEl) {
    const fadersRow = panelEl.querySelector(".fxprog-dmxdirect__faders");
    const emptyMsg  = panelEl.querySelector(".fxprog-dmxdirect__empty");
    if (!fadersRow) return;
    fadersRow.innerHTML = "";

    const PS = window.ProgrammerState;
    const show = (hasFaders) => {
      fadersRow.style.display = hasFaders ? "" : "none";
      if (emptyMsg) emptyMsg.style.display = hasFaders ? "none" : "";
    };

    if (!PS.selectedIds.size) { show(false); return; }

    const firstId = [...PS.selectedIds][0];
    const fixtures = _getState(panelEl).fixtures || {};
    const fx = fixtures[firstId];
    if (!fx) { show(false); return; }

    const channels = _channelsForFixture(fx, _fixtureTypesCache);
    if (!channels.length) {
      // Fixture-Typen evtl. noch nicht geladen - Rebuild triggern sobald bereit
      _loadFixtureTypes(() => _rebuildDmxDirectPane(panelEl));
      show(false); return;
    }

    show(true);
    const mc = (panelEl._progMc || {});
    const overridePct = parseInt(mc.dmx_width_pct, 10) || 0;
    // Breite: Override (5-100%) → feste Prozentbreite (data-override steuert flex-shrink 0).
    // Auto → kein Override-Attribut, CSS flex:1 1 28px passt Breite wie Color-Fader an.
    if (overridePct >= 5 && overridePct <= 100) {
      fadersRow.setAttribute("data-override", "true");
      fadersRow.style.setProperty("--dmx-fader-pct", overridePct + "%");
    } else {
      fadersRow.removeAttribute("data-override");
      fadersRow.style.removeProperty("--dmx-fader-pct");
    }

    const cached = window.__dmxUniverseValueCache[fx.universe] || [];
    channels.forEach(({ name, offset }) => {
      const rawVal = cached[(fx.start_channel - 1) + offset] || 0;
      const pctVal = DMX.byteToPct(rawVal);
      const vf = _makeVFader({
        label: String(offset + 1),   // wird sofort durch zweizeiligen DOM ersetzt
        value: pctVal,
        formatVal: v => String(DMX.pctToByte(v)),
        onChange: (v) => {
          const sel = [...PS.selectedIds];
          if (!sel.length) return;
          window.ProgrammerState.setRawChannel(sel, offset, DMX.pctToByte(v));
        }
      });
      // Zweizeilige Beschriftung: Zeile 1 = Kanal-Nr., Zeile 2 = Attributname
      const labelEl = vf.querySelector(".vfader__label");
      if (labelEl) {
        labelEl.innerHTML = "";
        const l1 = document.createElement("span");
        l1.className = "vfader__label-ch";
        l1.textContent = "Ch " + (offset + 1);
        const l2 = document.createElement("span");
        l2.className = "vfader__label-attr";
        l2.textContent = name || "CH";
        labelEl.appendChild(l1);
        labelEl.appendChild(l2);
      }
      vf.dataset.dmxOffset = String(offset);
      fadersRow.appendChild(vf);
    });
  }

  // ── Raeder (Gobo / Prisma / Farbrad): Fader-Spalten und Slot-Knoepfe ───
  // Je Rad der selektierten Fixture eine Fader-Spalte (.fxprog-gobo-col) und darunter alle Slots als Knoepfe: Gobo-Muster als Bild, Farben als Farbfeld,
  // Prismen mit Facettenzahl. Ein Klick setzt den DMX-Kanal des Rads auf die Mitte des Slot-Bereichs. Die Daten kommen von
  // /api/fixture-types/<id>/wheels (aus der GDTF-Datei; siehe fixture_manager.get_fixture_wheels).
  const _wheelDataCache = new Map();
  const _beamfxCache = new Map();                              // Typ -> Gobo-/Prismenkanaele (siehe /api/fixture-types/<id>/beamfx): Drehung/Position je Rad
  const _WHEEL_UI = {
    gobo:  { faders: ".fxprog-gobo-faders-wrap",  strip: ".fxprog-gobo-strip:not(.fxprog-prism-strip):not(.fxprog-color-strip)", label: "Gobo",  fallbackAttr: "gobo",  channel: /^Gobo1$|^Gobo$/i },
    prism: { faders: ".fxprog-prism-faders-wrap", strip: ".fxprog-prism-strip",  label: "Prism", fallbackAttr: "prism", channel: /^Prism1$|^Prism$/i },
    color: { faders: ".fxprog-color-faders-wrap", strip: ".fxprog-color-strip",  label: "Color", fallbackAttr: "",      channel: /^Color1$|^ColorWheel|^Color$/i },
  };

  function _wheelsOfFirstSelected(panelEl) {
    const PS = window.ProgrammerState;
    if (!PS.selectedIds.size) return { fx: null, wheels: null };
    const fx = (_getState(panelEl).fixtures || {})[[...PS.selectedIds][0]];
    const wheels = fx && _wheelDataCache.has(fx.fixture_type) ? _wheelDataCache.get(fx.fixture_type) : null;
    return { fx: fx || null, wheels };
  }

  function _wheelChannel(wheel, channels, type) {
    let wheelCh = wheel.attribute_name ? channels.find(c => c.name === wheel.attribute_name) : null;
    return wheelCh || channels.find(c => _WHEEL_UI[type].channel.test(c.name)) || null;
  }

  function _rebuildWheelFaders(panelEl, type) {
    const ui = _WHEEL_UI[type];
    const wrap = panelEl.querySelector(ui.faders);
    if (!wrap) return;
    wrap.innerHTML = "";
    const PS = window.ProgrammerState;
    const { fx, wheels } = _wheelsOfFirstSelected(panelEl);
    const ofType = wheels ? wheels.filter(w => w.type === type) : [];
    const channels = fx ? _channelsForFixture(fx, _fixtureTypesCache) : [];
    if (!ofType.length) {
      if (!ui.fallbackAttr) return;                        // Farbrad: ohne Rad gibt es nichts zu zeigen (die Unteransicht ist dann ausgeblendet)
      const vf = _makeVFader({
        label: ui.label, value: 0,
        onChange: (v) => { const sel = [...PS.selectedIds]; if (sel.length) PS.setBeamAttr(ui.fallbackAttr, sel, v); }
      });
      vf.classList.add("vfader--neutral", "vfader--main");
      vf.dataset.faderId = ui.fallbackAttr;
      wrap.appendChild(vf);
      return;
    }
    ofType.forEach((wheel) => {
      const wheelCh = _wheelChannel(wheel, channels, type);
      const col = document.createElement("div");
      col.className = "fxprog-gobo-col";
      const colLabel = document.createElement("div");
      colLabel.className = "fxprog-gobo-col__label";
      colLabel.textContent = wheel.name;
      col.appendChild(colLabel);
      const cached = window.__dmxUniverseValueCache[fx && fx.universe] || [];
      const initVal = wheelCh ? DMX.byteToPct(cached[(fx.start_channel - 1) + wheelCh.offset] || 0) : 0;
      const vf = _makeVFader({
        label: wheel.attribute_name || wheel.name,
        value: initVal,
        formatVal: v => String(DMX.pctToByte(v)),
        onChange: (v) => {
          const sel = [...PS.selectedIds];
          if (!sel.length) return;
          if (wheelCh) PS.setRawChannel(sel, wheelCh.offset, DMX.pctToByte(v));
          else if (ui.fallbackAttr) PS.setBeamAttr(ui.fallbackAttr, sel, v);
        }
      });
      vf.classList.add("vfader--neutral", "vfader--main");
      vf.dataset.faderId = type + "-" + (wheel.attribute_name || wheel.name);
      if (wheelCh) vf.dataset.dmxOffset = String(wheelCh.offset);
      col.appendChild(vf);
      wrap.appendChild(col);
    });
    // Drehung/Position der Raeder (z. B. Gobo1SelectSpin, Prism1PosRotate): eine eigene Fader-Spalte je Dreh-Kanal, direkt hinter den Rad-Faddern
    const beamfx = fx ? _beamfxCache.get(fx.fixture_type) : null;
    if (!beamfx) return;
    ofType.forEach((wheel) => {
      Object.entries(beamfx).forEach(([attribute, info]) => {
        if (info.role !== "spin" || info.type !== type || info.wheel !== wheel.name) return;
        const spinCh = channels.find(c => c.name === attribute);
        if (!spinCh) return;
        const col = document.createElement("div");
        col.className = "fxprog-gobo-col";
        const colLabel = document.createElement("div");
        colLabel.className = "fxprog-gobo-col__label";
        colLabel.textContent = wheel.name + " · " + t("FXPROG_WHEEL_ROTATION");
        col.appendChild(colLabel);
        const cachedUni = window.__dmxUniverseValueCache[fx.universe] || [];
        const vf = _makeVFader({
          label: attribute,
          value: DMX.byteToPct(cachedUni[(fx.start_channel - 1) + spinCh.offset] || 0),
          formatVal: v => String(DMX.pctToByte(v)),
          onChange: (v) => { const sel = [...PS.selectedIds]; if (sel.length) PS.setRawChannel(sel, spinCh.offset, DMX.pctToByte(v)); }
        });
        vf.classList.add("vfader--neutral", "vfader--main");
        vf.dataset.faderId = type + "-" + attribute;
        vf.dataset.dmxOffset = String(spinCh.offset);
        col.appendChild(vf);
        wrap.appendChild(col);
      });
    });
  }

  function _renderWheelStrip(panelEl, type) {
    const ui = _WHEEL_UI[type];
    const strip = panelEl.querySelector(ui.strip);
    if (!strip) return;
    strip.innerHTML = "";
    const { fx, wheels } = _wheelsOfFirstSelected(panelEl);
    const ofType = wheels ? wheels.filter(w => w.type === type) : [];
    if (!fx || !ofType.length) return;
    const channels = _channelsForFixture(fx, _fixtureTypesCache);
    const PS = window.ProgrammerState;
    ofType.forEach((wheel) => {
      const wheelCh = _wheelChannel(wheel, channels, type);
      const wLabel = document.createElement("div");
      wLabel.className = "fxprog-gobo-strip__wheel-label";
      const typeBadge = wheel.attribute_name ? wheel.attribute_name : wheel.name;
      wLabel.textContent = wheel.name + (typeBadge !== wheel.name ? "  [" + typeBadge + "]" : "");
      strip.appendChild(wLabel);
      const row = document.createElement("div");
      row.className = "fxprog-gobo-strip__row";
      if (wheelCh) row.dataset.channelOffset = String(wheelCh.offset);
      wheel.slots.forEach(slot => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "fxprog-gobo-btn";
        btn.title = slot.name + " (DMX " + slot.dmx_from + "–" + slot.dmx_to + ")";
        btn.dataset.dmxFrom = String(slot.dmx_from);
        btn.dataset.dmxTo = String(slot.dmx_to);
        btn.dataset.dmxCenter = String(slot.dmx_center);
        if (slot.image && type === "gobo") {
          const img = document.createElement("img");
          img.src = slot.image;
          img.alt = slot.name;
          img.className = "fxprog-gobo-btn__img";
          btn.appendChild(img);
        } else if (type === "color") {
          const swatch = document.createElement("span");
          swatch.className = "fxprog-gobo-btn__swatch";
          if (slot.color) swatch.style.background = "rgb(" + slot.color.join(",") + ")";
          else swatch.classList.add("fxprog-gobo-btn__swatch--open");
          btn.appendChild(swatch);
        } else if (type === "prism" && slot.facets) {
          const facets = document.createElement("span");
          facets.className = "fxprog-gobo-btn__facets";
          facets.textContent = slot.facets + "×";
          btn.appendChild(facets);
        } else {
          btn.classList.add("fxprog-gobo-btn--text");
        }
        const nameEl = document.createElement("div");
        nameEl.className = "fxprog-gobo-btn__name";
        nameEl.textContent = slot.name;
        btn.appendChild(nameEl);
        btn.addEventListener("click", () => {
          const sel = [...PS.selectedIds];
          if (!sel.length) return;
          if (wheelCh) {
            PS.setRawChannel(sel, wheelCh.offset, slot.dmx_center);
            // der Fader des Rads springt sofort auf den Wert des Slots (nicht erst mit dem naechsten DMX-Stand vom Server)
            panelEl.querySelectorAll('.vfader[data-dmx-offset="' + wheelCh.offset + '"]').forEach((vf) => { if (!vf.isDragging && vf.setValue) vf.setValue(DMX.byteToPct(slot.dmx_center)); });
          } else if (_WHEEL_UI[type].fallbackAttr) PS.setBeamAttr(_WHEEL_UI[type].fallbackAttr, sel, DMX.byteToPct(slot.dmx_center));
          row.querySelectorAll(".fxprog-gobo-btn--selected").forEach(b => b.classList.remove("fxprog-gobo-btn--selected"));
          btn.classList.add("fxprog-gobo-btn--selected");
        });
        row.appendChild(btn);
      });
      strip.appendChild(row);
    });
  }

  // ── Shutter/Strobe: Voreinstellungs-Knoepfe aus den DMX-Bereichen der GDTF (/api/fixture-types/<id>/shutter) ───
  const _shutterDataCache = new Map();
  const _SHUTTER_KIND_LABEL = { pulse_in: "FXPROG_SHUTTER_PULSE_IN", pulse_out: "FXPROG_SHUTTER_PULSE_OUT", random: "FXPROG_SHUTTER_RANDOM" };

  /** Knoepfe fuer die Bereiche eines Shutter-Kanals: [{key (i18n) | text, byte, title}]. Offen/Zu je einmal, der erste Strobe-Bereich als Langsam/Schnell, Puls und Zufall je Bereich;
   * weitere Strobe-Bereiche (z. B. "Pulse FX") als ein Knopf in der Mitte mit dem Namen des Bereichs. */
  function _shutterPresets(rawRanges) {
    const out = [];
    const ranges = [];                                         // aneinandergrenzende Bereiche gleicher Art zusammenfassen (GDTF teilt Strobe oft in "min", Verlauf, "max")
    rawRanges.forEach((r) => {
      const prev = ranges[ranges.length - 1];
      if (prev && prev.kind === r.kind && r.kind !== "open" && r.kind !== "closed" && r.from <= prev.to + 1) ranges[ranges.length - 1] = { ...prev, to: Math.max(prev.to, r.to) };
      else ranges.push({ ...r });
    });
    const mid = (r) => Math.round((r.from + r.to) / 2);
    const title = (r) => r.name + " (DMX " + r.from + "–" + r.to + ")";
    const open = ranges.find(r => r.kind === "open");
    const closed = ranges.find(r => r.kind === "closed");
    if (open) out.push({ key: "FXPROG_SHUTTER_OPEN", byte: mid(open), title: title(open) });
    if (closed) out.push({ key: "FXPROG_SHUTTER_CLOSED", byte: mid(closed), title: title(closed) });
    let firstStrobe = true;
    ranges.forEach((r) => {
      if (r.kind === "strobe") {
        const span = r.to - r.from;
        if (firstStrobe && span >= 4) {
          out.push({ key: "FXPROG_SHUTTER_SLOW", byte: r.from + Math.round(span * 0.1), title: title(r) });
          out.push({ key: "FXPROG_SHUTTER_FAST", byte: r.to - Math.round(span * 0.1), title: title(r) });
        } else if (firstStrobe) {
          out.push({ key: "FXPROG_SHUTTER_STROBE", byte: mid(r), title: title(r) });
        } else {
          out.push(/pulse/i.test(r.name) ? { key: "FXPROG_SHUTTER_PULSE", byte: mid(r), title: title(r) } : { text: r.name, byte: mid(r), title: title(r) });
        }
        firstStrobe = false;
      } else if (_SHUTTER_KIND_LABEL[r.kind]) {
        out.push({ key: _SHUTTER_KIND_LABEL[r.kind], byte: mid(r), title: title(r) });
      }
    });
    return out;
  }

  function _renderShutterPresets(panelEl) {
    const row = panelEl.querySelector(".fxprog-shutter-presets");
    if (!row) return;
    row.innerHTML = "";
    const PS = window.ProgrammerState;
    if (!PS.selectedIds.size) return;
    const fx = (_getState(panelEl).fixtures || {})[[...PS.selectedIds][0]];
    const data = fx && _shutterDataCache.get(fx.fixture_type);
    if (!data) return;
    const attribute = Object.keys(data).find(a => Array.isArray(data[a]) && data[a].length);
    if (!attribute) return;
    const channels = _channelsForFixture(fx, _fixtureTypesCache);
    const channel = channels.find(c => c.name === attribute) || channels.find(c => /^Shutter/i.test(c.name)) || null;
    _shutterPresets(data[attribute]).forEach((preset) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "fxprog-qbtn";
      if (preset.key) { btn.dataset.i18n = preset.key; btn.textContent = t(preset.key); } else btn.textContent = preset.text;
      btn.title = preset.title;
      btn.dataset.dmxByte = String(preset.byte);
      btn.addEventListener("click", () => {
        const sel = [...PS.selectedIds];
        if (!sel.length) return;
        if (channel) PS.setRawChannel(sel, channel.offset, preset.byte);
        else PS.setBeamAttr("strobe", sel, DMX.byteToPct(preset.byte));
        panelEl.querySelectorAll(".vfader[data-fader-id='strobe']").forEach((vf) => { if (!vf.isDragging && vf.setValue) vf.setValue(DMX.byteToPct(preset.byte)); });
      });
      row.appendChild(btn);
    });
  }

  function _loadShutterPresets(panelEl) {
    const PS = window.ProgrammerState;
    if (!PS.selectedIds.size) { _renderShutterPresets(panelEl); return; }
    const fx = (_getState(panelEl).fixtures || {})[[...PS.selectedIds][0]];
    if (!fx) { _renderShutterPresets(panelEl); return; }
    if (_shutterDataCache.has(fx.fixture_type)) { _renderShutterPresets(panelEl); return; }
    _renderShutterPresets(panelEl);
    fetch("/api/fixture-types/" + encodeURIComponent(fx.fixture_type) + "/shutter")
      .then(r => (r.ok ? r.json() : {}))
      .then(data => { _shutterDataCache.set(fx.fixture_type, data || {}); _renderShutterPresets(panelEl); })
      .catch(() => { /* ohne Daten keine Knoepfe */ });
  }

  // ── Fest verdrahtete Zusatz-Fader je Kategorie ───────────────────────────────────────────────────────
  // Nur was hier ausdruecklich steht, erscheint in einer Kategorie - und zwar als Spalte neben den vorhandenen Fadern (Position: Speed neben Pan/Tilt, Fokus: Iris/Frost neben Fokus/Zoom).
  // Alle anderen Kanaele einer GDTF-Datei (Reset, Funktion, Klingen, Farbmakros, Fein-Kanaele ...) bedient man unter "DMX Direkt".
  // attrs = GDTF-Attributnamen, die diese Funktion bedeuten (der erste, den das Geraet hat, gilt); die Spalte ist nur sichtbar, wenn das gewaehlte Geraet den Kanal hat.
  const _RAW_FADERS = [
    { id: "speed", cat: "position", attrs: ["PositionMSpeed", "PT Speed", "XY speed", "PanTiltSpeed"], labelKey: "FXPROG_POS_SPEED",
      presets: [["FXPROG_POS_SPEED_FAST", 0], ["FXPROG_POS_SPEED_SLOW", 100]] },                // DMX 0 = schnell ... 255 = langsam (z. B. "Fast to Slow" in der Datei)
    { id: "iris", cat: "focus", attrs: ["Iris"], labelKey: "FXPROG_FOCUS_IRIS", presets: [["FXPROG_FOCUS_OPEN", 0], ["FXPROG_FOCUS_CLOSED", 100]] },
    { id: "frost1", cat: "focus", attrs: ["Frost1"], labelKey: "FXPROG_FOCUS_FROST", presets: [["FXPROG_FOCUS_OFF", 0], ["FXPROG_FOCUS_FULL", 100]] },
    { id: "frost2", cat: "focus", attrs: ["Frost2"], labelKey: "FXPROG_FOCUS_FROST2", presets: [["FXPROG_FOCUS_OFF", 0], ["FXPROG_FOCUS_FULL", 100]] },
  ];

  /** Spalten der Zusatz-Fader anlegen (zunaechst versteckt; _syncRawFaders zeigt sie fuer die Selektion). parent = Container der Kategorie. */
  function _buildRawFaderCols(panelEl, cat, parent) {
    _RAW_FADERS.filter((spec) => spec.cat === cat).forEach((spec) => {
      const col = document.createElement("div");
      col.className = (cat === "position" ? "fxprog-pos-fader-col" : "fxprog-focus-col") + " fxprog-rawcol";
      col.dataset.axis = spec.id;
      col.dataset.rawId = spec.id;
      col.style.display = "none";
      const vf = _makeVFader({
        label: t(spec.labelKey),
        labelKey: spec.labelKey,
        value: 0,
        onChange: (v) => {
          const sel = [...window.ProgrammerState.selectedIds];
          const offset = parseInt(vf.dataset.dmxOffset, 10);
          if (sel.length && !isNaN(offset)) window.ProgrammerState.setRawChannel(sel, offset, DMX.pctToByte(v));
        }
      });
      vf.classList.add("vfader--neutral", "vfader--main", "fxprog-rawfader");
      vf.dataset.faderId = "raw-" + spec.id;
      col.appendChild(vf);
      const row = document.createElement("div");
      row.className = cat === "position" ? "fxprog-rawpresets" : "fxprog-focus-presets";
      spec.presets.forEach(([key, val]) => {
        const btn = document.createElement("button");
        btn.className = "fxprog-qbtn" + (cat === "position" ? " fxprog-center-btn" : "");
        btn.dataset.i18n = key;
        btn.textContent = t(key);
        btn.addEventListener("click", () => {
          const sel = [...window.ProgrammerState.selectedIds];
          const offset = parseInt(vf.dataset.dmxOffset, 10);
          if (!sel.length || isNaN(offset)) return;
          window.ProgrammerState.setRawChannel(sel, offset, DMX.pctToByte(val));
          vf.setValue(val);
        });
        row.appendChild(btn);
      });
      col.appendChild(row);
      parent.appendChild(col);
    });
  }

  /** Zusatz-Fader fuer die erste gewaehlte Fixture: Spalte zeigen (Kanal vorhanden) oder verstecken, DMX-Offset und aktuellen Wert setzen. */
  function _syncRawFaders(panelEl) {
    const PS = window.ProgrammerState;
    const fx = PS.selectedIds.size ? (_getState(panelEl).fixtures || {})[[...PS.selectedIds][0]] : null;
    const channels = fx ? _channelsForFixture(fx, _fixtureTypesCache) : [];
    const cached = fx ? (window.__dmxUniverseValueCache[fx.universe] || []) : [];
    panelEl.querySelectorAll(".fxprog-rawcol").forEach((col) => {
      const spec = _RAW_FADERS.find((r) => r.id === col.dataset.rawId);
      const vf = col.querySelector(".fxprog-rawfader");
      let channel = null;
      for (const attr of spec.attrs) { channel = channels.find((c) => c.name === attr); if (channel) break; }
      col.style.display = channel ? "" : "none";
      if (!channel) { delete vf.dataset.dmxOffset; return; }
      vf.dataset.dmxOffset = String(channel.offset);
      if (!vf.isDragging) vf.setValue(DMX.byteToPct(cached[(fx.start_channel - 1) + channel.offset] || 0));
    });
    const posCtrl = panelEl.querySelector('.fxprog-dimmer-controls[data-panel="coarse"]');
    if (posCtrl) posCtrl.classList.toggle("fxprog-pos-has-speed", !!panelEl.querySelector('.fxprog-rawcol[data-raw-id="speed"]:not([style*="display: none"])'));
  }

  /** Raeder der gerade selektierten Geraete aktualisieren: Daten (einmal je Typ) holen, dann Farbrad-Unteransicht ein-/ausblenden und die
   * sichtbaren Ansichten (Gobo, Prisma, Farbrad) neu aufbauen. */
  function _refreshWheelViews(panelEl) {
    const PS = window.ProgrammerState;
    const colorTab = panelEl.querySelector('.fxprog-color .fxprog-subtab[data-subtab="wheel"]');
    const apply = () => {
      const { wheels } = _wheelsOfFirstSelected(panelEl);
      const hasColor = !!(wheels && wheels.some(w => w.type === "color"));
      if (colorTab) {
        colorTab.style.display = hasColor ? "" : "none";
        if (!hasColor && colorTab.classList.contains("fxprog-subtab--active")) {
          const fader = panelEl.querySelector('.fxprog-color .fxprog-subtab[data-subtab="fader"]');
          if (fader) _activateSubtab(panelEl, fader, { silent: true });
        }
      }
      ["gobo", "prism", "color"].forEach((type) => { _rebuildWheelFaders(panelEl, type); _renderWheelStrip(panelEl, type); });
      _loadShutterPresets(panelEl);
      _syncRawFaders(panelEl);
    };
    if (!PS.selectedIds.size) { apply(); return; }
    const fx = (_getState(panelEl).fixtures || {})[[...PS.selectedIds][0]];
    if (!fx) { apply(); return; }
    if (_wheelDataCache.has(fx.fixture_type) && _beamfxCache.has(fx.fixture_type)) { apply(); return; }
    apply();                                                          // sofort mit Fallbacks, danach mit den Daten
    const typeId = fx.fixture_type;
    const url = "/api/fixture-types/" + encodeURIComponent(typeId);
    Promise.all([
      _wheelDataCache.has(typeId) ? _wheelDataCache.get(typeId) : fetch(url + "/wheels").then(r => r.json()),
      _beamfxCache.has(typeId) ? _beamfxCache.get(typeId) : fetch(url + "/beamfx").then(r => (r.ok ? r.json() : {})).catch(() => ({})),
    ])
      .then(([wheels, beamfx]) => { _wheelDataCache.set(typeId, wheels); _beamfxCache.set(typeId, beamfx || {}); apply(); })
      .catch(() => { /* ohne Daten bleiben die Fallbacks */ });
  }

  // Alte Namen (Aufrufe aus dem Gobo-Code und von Tests)
  function _rebuildGoboFaders(panelEl) { _rebuildWheelFaders(panelEl, "gobo"); }
  function _refreshGoboThumbnails(panelEl) { _refreshWheelViews(panelEl); }

  // ── Originale Tabellen-Ansicht (Fixtures Patch-Panel) ─────────────
  function _buildTable(panelEl, fixtures) {
    const st = _getState(panelEl);
    st.fixtures = fixtures;

    const wrap = panelEl.querySelector(".fx-table-wrap");
    if (!wrap) return;
    wrap.innerHTML = "";

    const entries = Object.entries(fixtures);
    if (entries.length === 0) {
      const empty = document.createElement("div");
      empty.className = "fx-empty";
      empty.textContent = t("FX_EMPTY");
      wrap.appendChild(empty);
      return;
    }

    const table = document.createElement("table");
    table.className = "fx-table";

    const thead = document.createElement("thead");
    thead.innerHTML = `<tr>
      <th class="fx-th fx-th--fid">${t("FX_COL_FID")}</th>
      <th class="fx-th fx-th--name">${t("FX_COL_NAME")}</th>
      <th class="fx-th fx-th--type">${t("FX_COL_TYPE")}</th>
      <th class="fx-th fx-th--univ">${t("FX_COL_UNIV")}</th>
      <th class="fx-th fx-th--addr">${t("FX_COL_ADDR")}</th>
      <th class="fx-th fx-th--ch">${t("FX_COL_CH")}</th>
    </tr>`;
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    entries.sort((a, b) =>
      a[1].universe !== b[1].universe
        ? a[1].universe - b[1].universe
        : a[1].start_channel - b[1].start_channel
    );

    let lastClickedIdx = null;
    const PS = window.ProgrammerState;

    entries.forEach(([id, fx], idx) => {
      const tr = document.createElement("tr");
      tr.className = "fx-row" + (PS.selectedIds.has(id) ? " fx-row--selected" : "");
      tr.dataset.fxId = id;
      tr.innerHTML = `
        <td class="fx-td fx-td--fid">${fx.fid || ""}${PS.isFixtureTouched(id) ? '<span class="fx-touched-dot" title="' + _esc(t("FX_TOUCHED_HINT")) + '"></span>' : ""}</td>
        <td class="fx-td">${fx.name ? _esc(fx.name) : `<em class="fx-unnamed">${_esc(t("FX_UNNAMED"))}</em>`}</td>
        <td class="fx-td" title="${_esc(fx.fixture_type || "")}">${_esc(_fixtureTypeLabel(fx.fixture_type))}</td>
        <td class="fx-td">${fx.universe}</td>
        <td class="fx-td">${fx.start_channel}</td>
        <td class="fx-td">${fx.channel_count}</td>
      `;

      // Selektion laeuft ausschliesslich ueber window.ProgrammerState -
      // dieselbe globale Quelle, die auch das Programmer-Panel-Tilegrid
      // nutzt. So schaltet eine Auswahl hier sofort dessen Tabs frei.
      tr.addEventListener("click", (e) => {
        const allRows = [...tbody.querySelectorAll(".fx-row")];
        if (e.shiftKey && lastClickedIdx !== null) {
          const lo = Math.min(lastClickedIdx, idx);
          const hi = Math.max(lastClickedIdx, idx);
          PS.rangeAdd(allRows.slice(lo, hi + 1).map(r => r.dataset.fxId));
        } else {
          PS.toggleSelect(id);
        }
        lastClickedIdx = idx;
      });

      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    wrap.appendChild(table);

    // Live-Sync: Aenderungen an der globalen Selektion (z.B. aus dem
    // Programmer-Panel-Tilegrid) sofort in der Tabelle widerspiegeln, sowie
    // den "active/touched"-Status (rote Markierung fuer unsaved Programmer-
    // Werte, siehe ProgrammerState.isFixtureTouched()).
    if (panelEl._fxTableSyncUI) document.removeEventListener("programmer-state-updated", panelEl._fxTableSyncUI);
    const _fxTableSyncUI = () => {
      if (_panelGone(panelEl, "programmer-state-updated", _fxTableSyncUI)) return;
      panelEl.querySelectorAll(".fx-row[data-fx-id]").forEach(r => {
        r.classList.toggle("fx-row--selected", PS.selectedIds.has(r.dataset.fxId));
        // Dezenter Status-Punkt statt flaechiger Zeilenfarbe (siehe Punkt 4):
        // wird dynamisch in die FID-Zelle ein-/ausgehaengt.
        const fidCell = r.querySelector(".fx-td--fid");
        if (fidCell) {
          const touched = PS.isFixtureTouched(r.dataset.fxId);
          let dot = fidCell.querySelector(".fx-touched-dot");
          if (touched && !dot) {
            dot = document.createElement("span");
            dot.className = "fx-touched-dot";
            dot.title = i18n("FX_TOUCHED_HINT");
            fidCell.appendChild(dot);
          } else if (!touched && dot) {
            dot.remove();
          }
        }
      });
    };
    document.addEventListener("programmer-state-updated", _fxTableSyncUI);
    panelEl._fxTableSyncUI = _fxTableSyncUI;

    panelEl._fxKeyHandler && document.removeEventListener("keydown", panelEl._fxKeyHandler);
    panelEl._fxKeyHandler = (e) => {
      if (_panelGone(panelEl, "keydown", panelEl._fxKeyHandler)) return;
      if (e.key !== "Delete" && e.key !== "Backspace") return;
      if (!panelEl.contains(document.activeElement) && document.activeElement !== document.body) return;
      const ids = [...window.ProgrammerState.selectedIds];
      if (!ids.length) return;
      _confirmDeleteFixtures(panelEl, ids);
    };
    document.addEventListener("keydown", panelEl._fxKeyHandler);
  }

  function _esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function _showContextMenu(x, y, panelEl, fx, id) {
    const selCount = window.ProgrammerState.selectedIds.size;
    const items = [{ label: t("FX_CTX_PROPERTIES"), onClick: () => _openFixtureDialog(panelEl, fx, id) }];   // immer genau EIN Scheinwerfer
    // Mehrfachauswahl: nur die Gruppenzuordnung aller markierten Scheinwerfer auf einmal aendern
    if (selCount > 1) items.push({ label: t("FX_CTX_MOVE_TO_GROUP", { n: selCount }), onClick: () => _showGroupPicker(x, y, [...window.ProgrammerState.selectedIds]) });
    items.push({
      label: selCount > 1 ? t("FX_CTX_DELETE_MANY", { n: selCount }) : t("FX_CTX_DELETE_ONE"),
      danger: true,
      onClick: () => _confirmDeleteFixtures(panelEl, [...window.ProgrammerState.selectedIds]),
    });
    ContextMenu.show(x, y, items);
  }

  /** Auswahlmenue "In Gruppe verschieben": vorhandene Gruppen, "Keine Gruppe" und "Neue Gruppe..." - aendert nur die Zuordnung. */
  function _showGroupPicker(x, y, ids) {
    const groups = Object.keys((client.state && client.state.groups) || {});
    const items = groups.map((g) => ({ label: g, onClick: () => client.send("assign_fixture_group", { ids, group: g }) }));
    items.push({ label: t("FX_GROUP_NONE"), onClick: () => client.send("assign_fixture_group", { ids, group: "" }) });
    items.push({ separator: true });
    items.push({ label: t("FXGRP_NEW"), onClick: () => _openGroupNameDialog(null, ids) });
    ContextMenu.show(x, y, items);
  }

  function _removeContextMenu() {
    ContextMenu.hide();
  }

  function _makeModal(sizeClass, headerText, bodyContent, footerButtons) {
    const backdrop = document.createElement("div");
    backdrop.className = "fx-panel-modal-backdrop";

    const modal = document.createElement("div");
    modal.className = `modal ${sizeClass}`;
    modal.style.overflow = "hidden";

    const header = document.createElement("div");
    header.className = "modal__header";
    const titleSpan = document.createElement("span");
    titleSpan.textContent = headerText;
    const closeBtn = document.createElement("button");
    closeBtn.className = "modal__close";
    closeBtn.textContent = "×";
    closeBtn.addEventListener("click", () => backdrop.remove());
    header.appendChild(titleSpan);
    header.appendChild(closeBtn);

    const body = document.createElement("div");
    body.className = "modal__body fx-form-body";
    if (typeof bodyContent === "string") body.innerHTML = bodyContent;
    else body.appendChild(bodyContent);

    const footer = document.createElement("div");
    footer.className = "modal__footer";
    for (const [label, cls, handler] of footerButtons) {
      const btn = document.createElement("button");
      btn.className = `modal__button ${cls}`;
      btn.textContent = label;
      btn.addEventListener("click", handler);
      footer.appendChild(btn);
    }

    modal.appendChild(header);
    modal.appendChild(body);
    modal.appendChild(footer);
    backdrop.appendChild(modal);

    backdrop.addEventListener("click", (e) => { if (e.target === backdrop) backdrop.remove(); });
    document.body.appendChild(backdrop);
    return { backdrop, modal, body, footer };
  }

  /** Ein Dialog fuer alles, was zu EINEM Scheinwerfer gehoert: Name, Universum, DMX-Adresse und Gruppe (frueher getrennte Dialoge). */
  function _openFixtureDialog(panelEl, fx, id) {
    const groups = Object.keys((client.state && client.state.groups) || {});
    const current = groups.find((g) => ((client.state.groups[g] || []).includes(id))) || "";
    const body = document.createElement("div");
    body.className = "fx-form-fields";
    const field = (labelText, control) => {
      const wrap = document.createElement("div");
      wrap.className = "fx-form-field";
      const lbl = document.createElement("label");
      lbl.textContent = labelText;
      wrap.append(lbl, control);
      return wrap;
    };
    const nameInput = document.createElement("input");
    nameInput.className = "fx-form-input";
    nameInput.id = "__fx_dlg_name";
    nameInput.type = "text";
    nameInput.maxLength = 80;
    nameInput.value = fx.name || "";
    const univInput = document.createElement("input");
    univInput.className = "fx-form-input";
    univInput.id = "__fx_dlg_univ";
    univInput.type = "number";
    univInput.min = "1";
    univInput.max = "64";
    univInput.value = String(fx.universe);
    const addrInput = document.createElement("input");
    addrInput.className = "fx-form-input";
    addrInput.id = "__fx_dlg_addr";
    addrInput.type = "number";
    addrInput.min = "1";
    addrInput.max = "512";
    addrInput.value = String(fx.start_channel);
    const sortInput = document.createElement("input");
    sortInput.className = "fx-form-input";
    sortInput.id = "__fx_dlg_sort";
    sortInput.type = "number";
    sortInput.step = "any";
    sortInput.placeholder = fx.fid > 0 ? String(fx.fid) : "";     // leer = Standard: die Nummer (FID)
    sortInput.value = fx.sort_index === null || fx.sort_index === undefined ? "" : String(fx.sort_index);
    const sortHint = document.createElement("div");
    sortHint.className = "fx-form-hint";
    sortHint.textContent = t("FX_PROPS_SORT_HINT");
    const groupSelect = document.createElement("select");
    groupSelect.className = "fx-form-input";
    groupSelect.id = "__fx_dlg_group";
    const opt = (value, text) => { const o = document.createElement("option"); o.value = value; o.textContent = text; groupSelect.appendChild(o); };
    opt("", t("FX_GROUP_NONE"));
    groups.forEach((g) => opt(g, g));
    groupSelect.value = current;
    const row = document.createElement("div");
    row.className = "fx-form-row-2";
    row.append(field(t("FX_EDIT_UNIV"), univInput), field(t("FX_EDIT_ADDR"), addrInput));
    const row2 = document.createElement("div");
    row2.className = "fx-form-row-2";
    row2.append(field(t("FX_PROPS_GROUP"), groupSelect), field(t("FX_PROPS_SORT"), sortInput));
    body.append(field(t("FX_PROPS_NAME"), nameInput), row, row2, sortHint);

    const save = () => {
      const newName = nameInput.value.trim();
      const universe = parseInt(univInput.value, 10);
      const startChannel = parseInt(addrInput.value, 10);
      const group = groupSelect.value;
      if (newName && newName !== (fx.name || "")) client.send("rename_fixture", { id, name: newName });
      if (!isNaN(universe) && !isNaN(startChannel) && (universe !== fx.universe || startChannel !== fx.start_channel)) {
        client.send("update_fixture", { id, universe, start_channel: startChannel });
      }
      if (group !== current) client.send("assign_fixture_group", { ids: [id], group });
      const sortText = sortInput.value.trim();
      const oldSort = fx.sort_index === null || fx.sort_index === undefined ? "" : String(fx.sort_index);
      if (sortText !== oldSort && (sortText === "" || Number.isFinite(Number(sortText)))) client.send("set_fixture_sort_index", { id, value: sortText === "" ? null : Number(sortText) });
      backdrop.remove();
    };
    const { backdrop } = _makeModal(
      "fx-panel-modal-fixture",
      t("FX_PROPS_TITLE", { name: fx.name || id }),
      body,
      [[t("CANCEL"), "", () => backdrop.remove()], [t("SAVE"), "modal__button--primary", save]]
    );
    body.addEventListener("keydown", (e) => { if (e.key === "Enter" && e.target.tagName !== "SELECT") { e.preventDefault(); save(); } });
    setTimeout(() => { nameInput.focus(); nameInput.select(); }, 50);
  }

  /** Neue Gruppe (groupName = null) oder Gruppe umbenennen: ein Namensfeld, doppelte Namen werden abgelehnt. */
  function _openGroupNameDialog(groupName, assignIds) {
    const existing = Object.keys((client.state && client.state.groups) || {});
    const wrap = document.createElement("div");
    wrap.className = "fx-form-field";
    const lbl = document.createElement("label");
    lbl.textContent = t("FXGRP_NAME_LABEL");
    const input = document.createElement("input");
    input.className = "fx-form-input";
    input.id = "__fx_group_name";
    input.type = "text";
    input.maxLength = 40;
    input.value = groupName || "";
    const err = document.createElement("div");
    err.className = "fx-form-error";
    err.id = "__fx_group_err";
    err.hidden = true;
    wrap.append(lbl, input, err);
    const save = () => {
      const name = input.value.trim().replace(/\s+/g, " ").slice(0, 40);
      if (!name) { err.textContent = t("FXGRP_ERR_EMPTY"); err.hidden = false; return; }
      if (existing.some((g) => g.toLowerCase() === name.toLowerCase() && g !== groupName)) { err.textContent = t("FXGRP_ERR_DUP"); err.hidden = false; return; }
      if (groupName === null) {
        client.send("add_fixture_group", { name });
        if (assignIds && assignIds.length) client.send("assign_fixture_group", { ids: assignIds, group: name });   // "Neue Gruppe..." im Verschieben-Menue
      }
      else if (name !== groupName) client.send("rename_fixture_group", { name: groupName, new_name: name });
      backdrop.remove();
    };
    const { backdrop } = _makeModal(
      "fx-panel-modal-sm",
      t(groupName === null ? "FXGRP_NEW_TITLE" : "FXGRP_RENAME_TITLE"),
      wrap,
      [[t("CANCEL"), "", () => backdrop.remove()], [t("SAVE"), "modal__button--primary", save]]
    );
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); save(); } });
    setTimeout(() => { input.focus(); input.select(); }, 50);
  }

  /** Gruppe loeschen mit Bestaetigung (die Scheinwerfer bleiben, nur ohne Gruppe). Vom Gruppen-Kopf mit festem Namen; aus dem
   *  Menue der freien Flaeche (groupName = null) mit einer Auswahl aller vorhandenen Gruppen - dieselbe Funktion, derselbe Dialog. */
  function _confirmDeleteGroup(groupName) {
    const groups = Object.keys((client.state && client.state.groups) || {});
    const picker = groupName === null;
    let current = picker ? groups[0] : groupName;
    if (current === undefined) return;
    const wrap = document.createElement("div");
    wrap.className = "fx-form-fields";
    const body = document.createElement("p");
    body.style.cssText = "margin:0;line-height:1.5";
    const refresh = () => { body.textContent = t("FXGRP_DELETE_BODY", { name: current }); };
    if (picker) {
      const field = document.createElement("div");
      field.className = "fx-form-field";
      const lbl = document.createElement("label");
      lbl.textContent = t("FXGRP_PICK_LABEL");
      const select = document.createElement("select");
      select.className = "fx-form-input";
      select.id = "__fx_group_pick";
      groups.forEach((g) => { const o = document.createElement("option"); o.value = g; o.textContent = g; select.appendChild(o); });
      select.value = current;
      select.addEventListener("change", () => { current = select.value; refresh(); });
      field.append(lbl, select);
      wrap.appendChild(field);
    }
    refresh();
    wrap.appendChild(body);
    const { backdrop } = _makeModal(
      "fx-panel-modal-sm",
      t("FXGRP_DELETE_TITLE"),
      wrap,
      [[t("CANCEL"), "", () => backdrop.remove()],
       [t("FXGRP_DELETE"), "modal__button--danger", () => { client.send("delete_fixture_group", { name: current }); backdrop.remove(); }]]
    );
  }

  // Aktuell gewählter Fixture-Typ (persistiert über Modal-Öffnungen)
  let _addFxSel = { id: null, name: null, modeName: "default", channelCount: 1 };

  async function _openAddFixturesModal() {
    let fixtureTypes = [];
    try {
      const res = await fetch("/fixture-types");
      fixtureTypes = await res.json();
    } catch { fixtureTypes = []; }

    // Standard: ersten Typ vorauswählen, falls noch kein Typ gewählt
    if (!_addFxSel.id && fixtureTypes.length > 0) {
      const ft = fixtureTypes[0];
      const m = ft.modes?.[0] || { name: "default", channel_count: 1 };
      _addFxSel = { id: ft.id, name: ft.name, modeName: m.name, channelCount: m.channel_count || 1 };
    }

    const fixtures = _fixturesFromGlobal();
    const suggestedUniv = 1;
    const suggestedAddr = _nextFreeChannel(fixtures, suggestedUniv);
    const initialNameIdx = _nextNameIndex(fixtures, _addFxSel.name || "");

    // ── Overflow-Warnung live aktualisieren ───────────────────────────
    function _updateOverflow() {
      const qty  = parseInt(document.getElementById("__fx_add_qty")?.value, 10) || 1;
      const addr = parseInt(document.getElementById("__fx_add_addr")?.value, 10) || 1;
      const univ = parseInt(document.getElementById("__fx_add_univ")?.value, 10) || 1;
      const end  = addr + qty * (_addFxSel.channelCount || 1) - 1;
      const warn = document.getElementById("__fx_add_warn");
      if (!warn) return;
      if (end > 512) {
        warn.textContent = t("FX_OVERFLOW_WARN", { end, univ });
        warn.hidden = false;
      } else {
        warn.hidden = true;
      }
    }

    // ── Name-Index-Hint aktualisieren ─────────────────────────────────
    function _updateNameHint(prefix) {
      const idx  = _nextNameIndex(_fixturesFromGlobal(), prefix || _addFxSel.name || "");
      const hint = document.getElementById("__fx_name_idx_hint");
      if (!hint) return;
      hint.hidden = idx <= 1;
      hint.textContent = idx > 1 ? t("FX_ADD_NEXT_IDX", { idx }) : "";
    }

    // ── Body: 2-Spalten-Layout ────────────────────────────────────────
    const bodyFrag = document.createElement("div");
    bodyFrag.className = "fx-add-form";

    const leftCol = document.createElement("div");
    leftCol.className = "fx-add-form__col";

    const rightCol = document.createElement("div");
    rightCol.className = "fx-add-form__col";

    // Linke Spalte: Typ-Anzeige + "Select Other..."
    const typeRow = document.createElement("div");
    typeRow.className = "fx-form-field";
    const typeLabel = document.createElement("label");
    typeLabel.textContent = t("FX_ADD_TYPE");
    const typeDisplay = document.createElement("div");
    typeDisplay.className = "fx-type-display";
    const typeText = document.createElement("span");
    typeText.id = "__fx_add_type_text";
    typeText.className = "fx-type-display__name";
    typeText.textContent = _addFxSel.name
      ? `${_addFxSel.name}  ·  ${_addFxSel.modeName} (${_addFxSel.channelCount}ch)`
      : "—";
    const selectBtn = document.createElement("button");
    selectBtn.className = "fx-btn";
    selectBtn.type = "button";
    selectBtn.textContent = t("FX_SELECT_OTHER");
    typeDisplay.appendChild(typeText);
    typeDisplay.appendChild(selectBtn);
    typeRow.appendChild(typeLabel);
    typeRow.appendChild(typeDisplay);
    leftCol.appendChild(typeRow);

    // Linke Spalte: Name mit Auto-Nummerierungs-Hint
    const nameRow = document.createElement("div");
    nameRow.className = "fx-form-field";
    nameRow.innerHTML = `
      <label>${t("FX_ADD_NAME")}</label>
      <input class="fx-form-input" id="__fx_add_name" type="text" placeholder="${_esc(t("FX_ADD_NAME_HINT"))}">
      <span class="fx-form-idx-hint" id="__fx_name_idx_hint"${initialNameIdx <= 1 ? " hidden" : ""}>${initialNameIdx > 1 ? _esc(t("FX_ADD_NEXT_IDX", { idx: initialNameIdx })) : ""}</span>
      <span class="fx-form-hint">${_esc(t("FX_ADD_NAME_HINT"))}</span>
    `;
    leftCol.appendChild(nameRow);

    // Rechte Spalte: Menge, Universum, Startkanal + Overflow-Warnung
    rightCol.innerHTML = `
      <div class="fx-form-field">
        <label>${t("FX_ADD_QTY")}</label>
        <div class="fx-qty-control">
          <button class="fx-qty-btn" id="__fx_qty_dec" type="button">−</button>
          <input class="fx-form-input fx-qty-input" id="__fx_add_qty" type="number" min="1" max="512" value="1">
          <button class="fx-qty-btn" id="__fx_qty_inc" type="button">+</button>
        </div>
      </div>
      <div class="fx-form-field">
        <label>${t("FX_ADD_UNIV")}</label>
        <input class="fx-form-input" id="__fx_add_univ" type="number" min="1" max="64" value="${suggestedUniv}">
      </div>
      <div class="fx-form-field">
        <label>${t("FX_ADD_ADDR")}</label>
        <input class="fx-form-input" id="__fx_add_addr" type="number" min="1" max="512" value="${suggestedAddr}">
        <div id="__fx_add_warn" class="fx-form-warn" hidden></div>
      </div>
    `;

    bodyFrag.appendChild(leftCol);
    bodyFrag.appendChild(rightCol);

    const { backdrop } = _makeModal(
      "fx-panel-modal-lg",
      t("FX_ADD_TITLE"),
      bodyFrag,
      [
        [t("CANCEL"), "", () => backdrop.remove()],
        [t("FX_ADD_CONFIRM"), "modal__button--primary", () => {
          if (!_addFxSel.id) return;
          const prefix = document.getElementById("__fx_add_name")?.value.trim() || _addFxSel.name;
          client.send("add_fixtures", {
            fixture_type_id:   _addFxSel.id,
            fixture_type_name: _addFxSel.name,
            channel_count:     _addFxSel.channelCount,
            mode:              _addFxSel.modeName,
            name_prefix:       prefix,
            name_start_index:  _nextNameIndex(_fixturesFromGlobal(), prefix),
            quantity:    Math.max(1, parseInt(document.getElementById("__fx_add_qty")?.value, 10) || 1),
            universe:    parseInt(document.getElementById("__fx_add_univ")?.value, 10) || 1,
            start_channel: parseInt(document.getElementById("__fx_add_addr")?.value, 10) || 1,
          });
          backdrop.remove();
        }],
      ]
    );

    // +/- Buttons für Menge (mit Overflow-Update)
    document.getElementById("__fx_qty_dec")?.addEventListener("click", () => {
      const inp = document.getElementById("__fx_add_qty");
      if (inp) { inp.value = Math.max(1, (parseInt(inp.value, 10) || 1) - 1); _updateOverflow(); }
    });
    document.getElementById("__fx_qty_inc")?.addEventListener("click", () => {
      const inp = document.getElementById("__fx_add_qty");
      if (inp) { inp.value = Math.min(512, (parseInt(inp.value, 10) || 1) + 1); _updateOverflow(); }
    });
    document.getElementById("__fx_add_qty")?.addEventListener("input", _updateOverflow);
    document.getElementById("__fx_add_addr")?.addEventListener("input", _updateOverflow);

    // Universum-Wechsel → nächste freie Adresse + Overflow-Update
    document.getElementById("__fx_add_univ")?.addEventListener("change", () => {
      const univ = parseInt(document.getElementById("__fx_add_univ")?.value, 10);
      if (!isNaN(univ)) {
        const el = document.getElementById("__fx_add_addr");
        if (el) el.value = _nextFreeChannel(_fixturesFromGlobal(), univ);
        _updateOverflow();
      }
    });

    // Name-Eingabe → Auto-Nummerierungs-Hint aktualisieren
    document.getElementById("__fx_add_name")?.addEventListener("input", (e) => {
      _updateNameHint(e.target.value.trim());
    });

    // "Select Other..." → Bibliothek öffnen, dann Hints aktualisieren
    selectBtn.addEventListener("click", () => {
      _openFixtureLibraryModal(fixtureTypes, (sel) => {
        _addFxSel = sel;
        const typeEl = document.getElementById("__fx_add_type_text");
        if (typeEl) typeEl.textContent = `${sel.name}  ·  ${sel.modeName} (${sel.channelCount}ch)`;
        const nameInp = document.getElementById("__fx_add_name");
        _updateNameHint(nameInp?.value.trim() || sel.name);
        _updateOverflow();
      });
    });

    // Initiale Overflow-Prüfung (z. B. wenn Addr nahe 512 vorausgefüllt)
    _updateOverflow();
  }

  // ── Fixture-Bibliothek (3-Spalten-Browser, dot2-Style) ────────────
  function _openFixtureLibraryModal(fixtureTypes, onSelect) {
    const backdrop = document.createElement("div");
    backdrop.className = "fx-library-backdrop";

    const modal = document.createElement("div");
    modal.className = "fx-library-modal";

    // Header
    const header = document.createElement("div");
    header.className = "modal__header";
    const title = document.createElement("span");
    title.textContent = t("FX_LIB_TITLE");
    const closeBtn = document.createElement("button");
    closeBtn.className = "modal__close";
    closeBtn.type = "button";
    closeBtn.textContent = "×";
    closeBtn.addEventListener("click", () => backdrop.remove());
    header.appendChild(title);
    header.appendChild(closeBtn);

    // Suchfeld
    const searchWrap = document.createElement("div");
    searchWrap.className = "fx-library-search";
    const searchInput = document.createElement("input");
    searchInput.className = "fx-form-input";
    searchInput.type = "text";
    searchInput.dataset.i18nPlaceholder = "FX_LIB_SEARCH";
    searchInput.placeholder = t("FX_LIB_SEARCH");
    searchWrap.appendChild(searchInput);

    // 3-Spalten-Browser
    function _makeCol(headKey, listId) {
      const col = document.createElement("div");
      col.className = "fx-library-col";
      const hdr = document.createElement("div");
      hdr.className = "fx-library-col__header";
      hdr.textContent = t(headKey);
      const ul = document.createElement("ul");
      ul.className = "fx-library-list";
      ul.id = listId;
      col.appendChild(hdr);
      col.appendChild(ul);
      return { col, ul };
    }
    const browser = document.createElement("div");
    browser.className = "fx-library-browser";
    const { col: col1, ul: mfrList }  = _makeCol("FX_LIB_MANUFACTURER", "__fxl_mfr");
    const { col: col2, ul: devList }  = _makeCol("FX_LIB_DEVICE",       "__fxl_dev");
    const { col: col3, ul: modeList } = _makeCol("FX_LIB_MODE",         "__fxl_mode");
    browser.appendChild(col1);
    browser.appendChild(col2);
    browser.appendChild(col3);

    // Footer
    const footer = document.createElement("div");
    footer.className = "modal__footer";
    const cancelBtn = document.createElement("button");
    cancelBtn.className = "modal__button";
    cancelBtn.type = "button";
    cancelBtn.textContent = t("CANCEL");
    cancelBtn.addEventListener("click", () => backdrop.remove());
    const okBtn = document.createElement("button");
    okBtn.className = "modal__button modal__button--primary";
    okBtn.type = "button";
    okBtn.textContent = t("FX_LIB_OK");
    okBtn.disabled = true;
    footer.appendChild(cancelBtn);
    footer.appendChild(okBtn);

    modal.appendChild(header);
    modal.appendChild(searchWrap);
    modal.appendChild(browser);
    modal.appendChild(footer);
    backdrop.appendChild(modal);
    document.body.appendChild(backdrop);

    // Zustand
    let selMfr = null, selFt = null, selMode = null;

    function _renderMfrs(filter) {
      const q = filter?.toLowerCase() || "";
      // Hersteller-Map aufbauen (nur gefilterte Fixtures)
      const map = new Map();
      for (const ft of fixtureTypes) {
        const mfr = ft.manufacturer || "Unknown";
        if (q && !mfr.toLowerCase().includes(q) && !ft.name.toLowerCase().includes(q)) continue;
        if (!map.has(mfr)) map.set(mfr, []);
        map.get(mfr).push(ft);
      }
      const sorted = [...map.keys()].sort((a, b) =>
        a === "Generic" ? -1 : b === "Generic" ? 1 : a.localeCompare(b)
      );

      mfrList.innerHTML = "";
      for (const mfr of sorted) {
        const li = document.createElement("li");
        li.className = "fx-library-item" + (mfr === selMfr ? " fx-library-item--active" : "");
        li.textContent = mfr;
        li.addEventListener("click", () => {
          selMfr = mfr; selFt = null; selMode = null;
          mfrList.querySelectorAll(".fx-library-item").forEach(i =>
            i.classList.toggle("fx-library-item--active", i.textContent === mfr));
          _renderDevs(map.get(mfr) || []);
          modeList.innerHTML = "";
          _updateOk();
        });
        mfrList.appendChild(li);
      }
      // Ersten Hersteller automatisch auswählen
      if (!selMfr && sorted.length > 0) {
        selMfr = sorted[0];
        mfrList.firstChild?.classList.add("fx-library-item--active");
        _renderDevs(map.get(selMfr) || []);
      }
    }

    function _renderDevs(fts) {
      devList.innerHTML = "";
      for (const ft of fts) {
        const li = document.createElement("li");
        li.className = "fx-library-item" + (ft === selFt ? " fx-library-item--active" : "");
        li.textContent = ft.name;
        li.addEventListener("click", () => {
          selFt = ft; selMode = null;
          devList.querySelectorAll(".fx-library-item").forEach(i =>
            i.classList.toggle("fx-library-item--active", i === li));
          _renderModes(ft.modes || []);
          _updateOk();
        });
        devList.appendChild(li);
      }
    }

    function _renderModes(modes) {
      modeList.innerHTML = "";
      for (const m of modes) {
        const cc = m.channel_count || 1;
        const li = document.createElement("li");
        li.className = "fx-library-item";
        li.textContent = `${m.name}  (${cc}ch)`;
        li.addEventListener("click", () => {
          selMode = { name: m.name, channelCount: cc };
          modeList.querySelectorAll(".fx-library-item").forEach(i =>
            i.classList.toggle("fx-library-item--active", i === li));
          _updateOk();
        });
        modeList.appendChild(li);
      }
      // Ersten Modus automatisch auswählen
      if (modes.length > 0) {
        const first = modes[0];
        selMode = { name: first.name, channelCount: first.channel_count || 1 };
        modeList.firstChild?.classList.add("fx-library-item--active");
        _updateOk();
      }
    }

    function _updateOk() { okBtn.disabled = !selFt || !selMode; }

    okBtn.addEventListener("click", () => {
      if (!selFt || !selMode) return;
      onSelect({ id: selFt.id, name: selFt.name, modeName: selMode.name, channelCount: selMode.channelCount });
      backdrop.remove();
    });

    searchInput.addEventListener("input", () => _renderMfrs(searchInput.value));
    backdrop.addEventListener("click", (e) => { if (e.target === backdrop) backdrop.remove(); });

    _renderMfrs("");
    setTimeout(() => searchInput.focus(), 60);
  }

  // ── Gelbes Auswahl-Lasso (Maus + Touch) fuer das Fixture-Tilegrid ───
  // Beim Druecken+Ziehen innerhalb der Fixture-Sheet erscheint eine sicht-
  // bare gelbe Box (border: 2px solid #ffff00). Waehrend des Ziehens werden
  // beruehrte Tiles nur in einem gedaempften VORSCHAU-Zustand markiert
  // (.fxprog-tile--preview) - die echte Selektion (window.ProgrammerState,
  // inkl. Programmer-Update-Events) wird ERST bei pointerup/touchend fuer
  // die zu diesem Zeitpunkt beruehrten Tiles ausgeloest (rangeAdd = reines
  // Hinzufuegen, NIE Toggle). Ein Klick ohne nennenswerte Bewegung toggelt
  // weiterhin ganz normal ueber den bestehenden Klick-Handler.
  let _lassoActive = false;       // Lasso zeichnet bzw. darf zeichnen
  let _lassoArmed = false;        // Touch: nach kurzem Halten scharf (Scrollen ist dann gesperrt)
  let _lassoArmTimer = null;
  let _lassoPointerId = null;
  let _lassoSheet = null;
  let _lassoStartX = 0;
  let _lassoStartY = 0;
  let _lassoEl = null;
  let _dragMoved = false;
  let _lassoPreviewIds = [];
  let _lassoCaptured = false;
  const LASSO_HOLD_MS = 350;      // Touch auf dem Zwischenraum: erst Halten, dann Lasso (sonst Scrollen)
  const LASSO_SLOP = 10;

  function _rectsIntersect(a, b) {
    return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
  }

  function _clearLassoPreview() {
    document.querySelectorAll(".fxprog-tile--preview").forEach(tile => tile.classList.remove("fxprog-tile--preview"));
    _lassoPreviewIds = [];
  }

  document.addEventListener("pointerdown", (e) => {
    const sheet = e.target.closest && e.target.closest(".fxprog-sheet");
    if (!sheet || !e.isPrimary) return;
    clearTimeout(_lassoArmTimer);
    _lassoArmTimer = null;
    _lassoPointerId = e.pointerId;
    _lassoSheet = sheet;
    _dragMoved = false;
    _lassoArmed = false;
    _lassoStartX = e.clientX;
    _lassoStartY = e.clientY;
    if (e.pointerType === "mouse" || e.target.closest(".fxprog-tile")) {
      // Maus bzw. Finger auf einer Kachel (touch-action: none): sofort Lasso-Kandidat
      _lassoActive = true;
    } else {
      // Finger auf dem Zwischenraum scrollt zuerst. Nur wer ~350 ms ruhig haelt, zeichnet ein Lasso.
      _lassoActive = false;
      _lassoArmTimer = setTimeout(() => {
        _lassoArmTimer = null;
        _lassoActive = true;
        _lassoArmed = true;
        sheet.classList.add("fxprog-sheet--arming");
        if (navigator.vibrate) { try { navigator.vibrate(8); } catch (err) { /* egal */ } }
      }, LASSO_HOLD_MS);
    }
  });

  document.addEventListener("pointermove", (e) => {
    if (e.pointerId !== _lassoPointerId) return;
    if (!_lassoActive) {
      // Bewegung vor dem Scharfschalten: der Finger scrollt - kein Lasso
      if (_lassoArmTimer && Math.hypot(e.clientX - _lassoStartX, e.clientY - _lassoStartY) > LASSO_SLOP) {
        clearTimeout(_lassoArmTimer);
        _lassoArmTimer = null;
      }
      return;
    }
    const threshold = e.pointerType === "mouse" ? 4 : LASSO_SLOP;   // Finger zittern mehr als Maeuse
    if (!_dragMoved && Math.abs(e.clientX - _lassoStartX) < threshold && Math.abs(e.clientY - _lassoStartY) < threshold) return;
    _dragMoved = true;
    // Scrollen des Rasters sperren, solange das Lasso gezeichnet wird: die Kacheln bleiben stehen.
    if (_lassoSheet) {
      _lassoSheet.classList.add("fxprog-sheet--lasso");
      if (!_lassoCaptured) {
        // Die Geste gehoert diesem Panel: Zeiger festhalten (kein Hover/Ereignis in Nachbar-Panels,
        // Loslassen ausserhalb kommt trotzdem hier an) und Nachbar-Panels waehrenddessen sperren.
        _lassoCaptured = true;
        try { _lassoSheet.setPointerCapture(e.pointerId); } catch (error) { /* Zeiger schon weg */ }
        document.body.classList.add("lasso-active");
        const owner = _lassoSheet.closest(".workspace-panel");
        if (owner) owner.classList.add("lasso-owner");
      }
    }

    if (!_lassoEl) {
      _lassoEl = document.createElement("div");
      _lassoEl.className = "fxprog-lasso";
      document.body.appendChild(_lassoEl);
    }
    // Grenze = der Rahmen des Scheinwerfer-Steuerung-Panels: die Lasso-Flaeche endet dort, auch wenn
    // der Zeiger weiterlaeuft. Gilt fuer Maus und Touch gleichermassen.
    const panelBox = ((_lassoSheet && _lassoSheet.closest(".workspace-panel")) || _lassoSheet).getBoundingClientRect();
    const pointerX = clamp(e.clientX, panelBox.left, panelBox.right);
    const pointerY = clamp(e.clientY, panelBox.top, panelBox.bottom);
    const left   = Math.min(_lassoStartX, pointerX);
    const top    = Math.min(_lassoStartY, pointerY);
    const right  = Math.max(_lassoStartX, pointerX);
    const bottom = Math.max(_lassoStartY, pointerY);
    _lassoEl.style.left   = left + "px";
    _lassoEl.style.top    = top + "px";
    _lassoEl.style.width  = (right - left) + "px";
    _lassoEl.style.height = (bottom - top) + "px";

    // Vorschau frisch neu berechnen (kein commit!): Tiles, die die Box
    // wieder verlassen, bevor losgelassen wird, verlieren die Vorschau.
    const lassoRect = { left, top, right, bottom };
    const touched = [];
    // nur Kacheln des eigenen Panels (die Auswahl selbst ist global und erscheint danach ueberall)
    (_lassoSheet || document).querySelectorAll(".fxprog-tile[data-fx-id]").forEach(tile => {
      const isTouched = _rectsIntersect(lassoRect, tile.getBoundingClientRect());
      tile.classList.toggle("fxprog-tile--preview", isTouched);
      if (isTouched) touched.push(tile.dataset.fxId);
    });
    _lassoPreviewIds = touched;
  });

  // Browser-Scrollen waehrend eines scharfen/laufenden Lassos verhindern (Touch).
  document.addEventListener("touchmove", (e) => {
    if (_lassoActive && (_lassoArmed || _dragMoved) && e.cancelable) e.preventDefault();
  }, { passive: false });

  function _endLasso(commit) {
    clearTimeout(_lassoArmTimer);
    _lassoArmTimer = null;
    const moved = _dragMoved;
    const endedPointerId = _lassoPointerId;
    _lassoActive = false;
    _lassoArmed = false;
    _lassoPointerId = null;
    if (_lassoSheet) {
      _lassoSheet.classList.remove("fxprog-sheet--lasso", "fxprog-sheet--arming");
      if (_lassoCaptured && endedPointerId !== null) {
        try { _lassoSheet.releasePointerCapture(endedPointerId); } catch (error) { /* schon frei */ }
      }
      _lassoSheet = null;
    }
    _lassoCaptured = false;
    document.body.classList.remove("lasso-active");
    document.querySelectorAll(".lasso-owner").forEach((panel) => panel.classList.remove("lasso-owner"));
    if (_lassoEl) { _lassoEl.remove(); _lassoEl = null; }
    // Commit: die beim Loslassen beruehrten Tiles werden JETZT erst final
    // selektiert (reines Hinzufuegen, nie Toggle). Ein abgebrochener Zeiger
    // (pointercancel, z.B. Systemgeste) waehlt nichts aus.
    if (commit && moved && _lassoPreviewIds.length) window.ProgrammerState.rangeAdd(_lassoPreviewIds);
    _clearLassoPreview();
  }
  document.addEventListener("pointerup", (e) => { if (e.pointerId === _lassoPointerId) _endLasso(true); });
  document.addEventListener("pointercancel", (e) => { if (e.pointerId === _lassoPointerId) _endLasso(false); });

  document.addEventListener("contextmenu", (e) => {
    const target = e.target.closest(".fxprog-tile[data-fx-id], tr[data-fx-id]");
    // Kein _removeContextMenu() hier: das Kontextmenue ist eine gemeinsame Komponente, ein anderes
    // Panel (z.B. der Panel-Editor) hat sein Menue in demselben Ereignis moeglicherweise gerade geoeffnet.
    if (!target) {
      // Freie Flaeche der Scheinwerfer-Liste (Programmer-Panel, Reiter Scheinwerfer): neue Gruppe; Gruppen-Kopf: umbenennen/loeschen
      const sheet = e.target.closest && e.target.closest(".fxprog-sheet");
      if (!sheet || document.getElementById("viewport")?.classList.contains("edit-mode")) return;
      e.preventDefault();
      const head = e.target.closest(".fxprog-group__label--group");
      if (head) {
        const groupName = head.dataset.group;
        ContextMenu.show(e.clientX, e.clientY, [
          { label: t("FXGRP_RENAME"), onClick: () => _openGroupNameDialog(groupName) },
          { label: t("FXGRP_DELETE"), danger: true, onClick: () => _confirmDeleteGroup(groupName) },
        ]);
      } else {
        const items = [{ label: t("FXGRP_NEW"), onClick: () => _openGroupNameDialog(null) }];
        if (Object.keys((client.state && client.state.groups) || {}).length) items.push({ label: t("FXGRP_DELETE_PICK"), danger: true, onClick: () => _confirmDeleteGroup(null) });
        ContextMenu.show(e.clientX, e.clientY, items);
      }
      return;
    }
    if (document.getElementById("viewport")?.classList.contains("edit-mode")) return;
    e.preventDefault();
    const fxId = target.dataset.fxId;
    const panelEl = target.closest("[data-panel-type='fixtures'], [data-panel-type='programmer']");
    if (!panelEl) return;
    const curSt = _getState(panelEl);
    const fx = curSt.fixtures[fxId];
    if (!fx) return;
    // Selektion laeuft global ueber window.ProgrammerState (dieselbe Quelle
    // wie Tilegrid, Fixtures-Tabelle und Tab-Freischaltung) - direktes
    // Feuern des Sync-Events aktualisiert alle Panels konsistent.
    const PS = window.ProgrammerState;
    if (!PS.selectedIds.has(fxId)) {
      PS.selectedIds.clear();
      PS.selectedIds.add(fxId);
      document.dispatchEvent(new CustomEvent("programmer-state-updated"));
    }
    _showContextMenu(e.clientX, e.clientY, panelEl, fx, fxId);
  });

  // ── Fixtures-Panel (Patch-Verwaltung: Tabelle mit Add/Edit/Delete) ─
  window.__panelPlugins.register({
    type: "fixtures",

    buildContent(panel) {
      const container = document.createElement("div");
      container.style.display = "contents";

      const toolbar = document.createElement("div");
      toolbar.className = "fx-toolbar";

      const addBtn = document.createElement("button");
      addBtn.className = "fx-btn";
      addBtn.dataset.i18n = "FX_TOOLBAR_ADD";
      addBtn.textContent = t("FX_TOOLBAR_ADD");
      addBtn.addEventListener("click", () => _openAddFixturesModal());
      toolbar.appendChild(addBtn);

      const deleteBtn = document.createElement("button");
      deleteBtn.className = "fx-btn";
      deleteBtn.dataset.i18n = "FX_TOOLBAR_DELETE";
      deleteBtn.textContent = t("FX_TOOLBAR_DELETE");
      deleteBtn.addEventListener("click", () => {
        const panelEl = deleteBtn.closest("[data-panel-type='fixtures']");
        const ids = [...window.ProgrammerState.selectedIds];
        if (!ids.length) return;
        _confirmDeleteFixtures(panelEl, ids);
      });
      toolbar.appendChild(deleteBtn);

      const wrap = document.createElement("div");
      wrap.className = "fx-table-wrap";

      container.appendChild(toolbar);
      container.appendChild(wrap);
      return container;
    },

    onMessage(panelEl, messageType, payload) {
      if (messageType === "fixtures_changed" || messageType === "state_snapshot") {
        const fixtures = payload.fixtures || {};
        const newIds = new Set(Object.keys(fixtures));
        const PS = window.ProgrammerState;
        for (const id of [...PS.selectedIds]) {
          if (!newIds.has(id)) PS.selectedIds.delete(id);
        }
        _buildTable(panelEl, fixtures);
      } else if (messageType === "language_changed") {
        _buildTable(panelEl, _getState(panelEl).fixtures || {});
      }
    },
  });

  // ── Programmer-Panel (dot2-Kachelgrid + Feature-Tabs) ─────────────
  window.__panelPlugins.register({
    type: "programmer",

    buildContent(panel) {
      const mc = panel.module_config || {};
      const container = document.createElement("div");
      container.style.display = "contents";

      const root = document.createElement("div");
      root.className = "fxprog";
      root.style.setProperty("--prog-sel-color",   mc.sel_color   || "#ffe600");
      root.style.setProperty("--prog-fader-color", mc.fader_color || "#00ff00");
      if (mc.sel_glow === false) root.classList.add("fxprog--no-glow");

      // Hauptbereich links (Panes)
      const main = document.createElement("div");
      main.className = "fxprog-main";

      // Tab-Streifen rechts
      const tabs = document.createElement("div");
      tabs.className = "fxprog-tabs";

      root.appendChild(main);
      root.appendChild(tabs);
      container.appendChild(root);

      setTimeout(() => {
        const panelEl = root.closest("[data-panel-type='programmer']");
        if (panelEl) _buildSidebar(panelEl, mc);
      }, 0);

      return container;
    },

    onModuleConfigChanged(panelEl, mc) {
      _applyProgConfig(panelEl.querySelector(".fxprog"), mc);
    },

    buildPropertiesPane(moduleConfig, api) {
      const mc = moduleConfig || {};
      const frag = document.createDocumentFragment();
      const autoTxt = api.i18n("FXPROG_PROP_FADER_WIDTH_AUTO");

      // ── Hilfsfunktionen ──────────────────────────────────────────────
      // Erzeugt einen Abschnittskopf mit modalem Grid-Title-Stil.
      const _sec = (i18nKey) => {
        const el = document.createElement("div");
        el.className = "modal__field-grid-title";
        el.dataset.i18n = i18nKey;
        el.textContent = api.i18n(i18nKey);
        frag.appendChild(el);
      };
      // Erzeugt Label + Farbpicker-Zeile.
      const _colorRow = (labelKey, swatchId, hexId, defaultVal) => {
        const lbl = document.createElement("div");
        lbl.className = "modal__field";
        const l = document.createElement("label");
        l.htmlFor = hexId;
        l.dataset.i18n = labelKey;
        l.textContent = api.i18n(labelKey);
        lbl.appendChild(l);
        frag.appendChild(lbl);
        const row = document.createElement("div");
        row.className = "modal__field";
        const sw = document.createElement("input");
        sw.type = "color";
        sw.id = swatchId;
        sw.className = "color-swatch-input";
        sw.value = mc[hexId.replace("prog-module-", "").replace(/-/g, "_")] || defaultVal;
        const hex = document.createElement("input");
        hex.type = "text";
        hex.id = hexId;
        hex.className = "color-hex-input";
        hex.maxLength = 7;
        hex.value = sw.value;
        row.appendChild(sw);
        row.appendChild(hex);
        frag.appendChild(row);
      };
      // Erzeugt einen Toggle-Switch mit Label.
      const _toggle = (field, labelKey, defaultOn = true) => {
        const id = "prog-module-" + field.replace(/_/g, "-");
        const row = document.createElement("div");
        row.className = "modal__field modal__field--checkbox";
        const tgl = makeToggleSwitch(id, (mc[field] === undefined ? defaultOn : mc[field] !== false));
        const lbl = document.createElement("label");
        lbl.htmlFor = id;
        lbl.dataset.i18n = labelKey;
        lbl.textContent = api.i18n(labelKey);
        row.appendChild(tgl.label);
        row.appendChild(lbl);
        frag.appendChild(row);
      };
      // Erzeugt einen Slider-Eintrag fuer das Propgrid.
      const _sliderRow = (grid, field, labelKey, rMin, rMax, rStep, unit) => {
        const id = "prog-module-" + field.replace(/_/g, "-");
        const val = parseInt(mc[field], 10) || 0;
        const lbl = document.createElement("label");
        lbl.htmlFor = id;
        lbl.dataset.i18n = labelKey;
        lbl.textContent = api.i18n(labelKey);
        grid.appendChild(lbl);
        const ctrl = document.createElement("div");
        ctrl.className = "fxprog-propgrid__control";
        const rng = document.createElement("input");
        rng.type = "range";
        rng.id = id;
        rng.min = String(rMin);
        rng.max = String(rMax);
        rng.step = String(rStep);
        rng.value = String(val);
        const fmt = v => v > 0 ? v + unit : autoTxt;
        const vLbl = document.createElement("span");
        vLbl.className = "fxprog-propgrid__value";
        vLbl.id = id + "-value";
        vLbl.textContent = fmt(val);
        rng.addEventListener("input", () => { vLbl.textContent = fmt(parseInt(rng.value, 10) || 0); });
        ctrl.appendChild(rng);
        ctrl.appendChild(vLbl);
        grid.appendChild(ctrl);
      };

      // ─── 1. Ansicht ──────────────────────────────────────────────────
      _sec("FXPROG_PROP_SECTION_VIEW");
      const viewRow = document.createElement("div");
      viewRow.className = "modal__field";
      const viewLabel = document.createElement("label");
      viewLabel.htmlFor = "prog-module-view-mode";
      viewLabel.dataset.i18n = "FXPROG_PROP_VIEW_MODE";
      viewLabel.textContent = api.i18n("FXPROG_PROP_VIEW_MODE");
      const viewSel = document.createElement("select");
      viewSel.id = "prog-module-view-mode";
      viewSel.className = "modal__input";
      [
        ["combined", "FXPROG_VIEW_COMBINED"],
        ["fixtures", "FXPROG_VIEW_FIXTURES"],
        ["dimmer",   "FXPROG_VIEW_DIMMER"],
        ["position", "FXPROG_VIEW_POSITION"],
        ["color",    "FXPROG_VIEW_COLOR"],
        ["beam",     "FXPROG_VIEW_BEAM"],
        ["focus",    "FXPROG_VIEW_FOCUS"],
        ["dmx",      "FXPROG_VIEW_DMX"],
      ].forEach(([val, key]) => {
        const opt = document.createElement("option");
        opt.value = val;
        opt.dataset.i18n = key;
        opt.textContent = api.i18n(key);
        if (val === (mc.view_mode || "combined")) opt.selected = true;
        viewSel.appendChild(opt);
      });
      viewRow.appendChild(viewLabel);
      viewRow.appendChild(viewSel);
      frag.appendChild(viewRow);

      // Standardansicht je Kategorie mit Unteransichten: welche zuerst erscheint, wenn die Kategorie geoeffnet wird
      _sec("FXPROG_PROP_SECTION_DEFAULT_VIEW");
      [
        ["default_view_color",    "FXPROG_PROP_DEFAULT_VIEW_COLOR",    "fader",   [["fader", "FXPROG_SUBTAB_FADER"], ["picker", "FXPROG_SUBTAB_PICKER"]]],
        ["default_view_position", "FXPROG_PROP_DEFAULT_VIEW_POSITION", "coarse",  [["coarse", "FXPROG_POS_COARSE"], ["fine", "FXPROG_POS_FINE"]]],
        ["default_view_beam",     "FXPROG_PROP_DEFAULT_VIEW_BEAM",     "shutter", [["shutter", "FXPROG_BEAM_SUBTAB_SHUTTER"], ["gobo", "FXPROG_BEAM_SUBTAB_GOBO"], ["prism", "FXPROG_BEAM_SUBTAB_PRISM"]]],
      ].forEach(([field, labelKey, fallback, options]) => {
        const id = "prog-module-" + field.replace(/_/g, "-");
        const row = document.createElement("div");
        row.className = "modal__field";
        const lbl = document.createElement("label");
        lbl.htmlFor = id;
        lbl.dataset.i18n = labelKey;
        lbl.textContent = api.i18n(labelKey);
        const sel = document.createElement("select");
        sel.id = id;
        sel.className = "modal__input";
        options.forEach(([val, key]) => {
          const opt = document.createElement("option");
          opt.value = val;
          opt.dataset.i18n = key;
          opt.textContent = api.i18n(key);
          if (val === (mc[field] || fallback)) opt.selected = true;
          sel.appendChild(opt);
        });
        row.appendChild(lbl);
        row.appendChild(sel);
        frag.appendChild(row);
      });

      // ─── 2. Darstellung ──────────────────────────────────────────────
      _sec("FXPROG_PROP_SECTION_APPEARANCE");
      _colorRow("FXPROG_PROP_SEL_COLOR",   "prog-module-sel-color-swatch",   "prog-module-sel-color-hex",   mc.sel_color   || "#ffe600");
      _colorRow("FXPROG_PROP_FADER_COLOR", "prog-module-fader-color-swatch", "prog-module-fader-color-hex", mc.fader_color || "#00ff00");
      _toggle("sel_glow", "FXPROG_PROP_SEL_GLOW", true);

      // ─── 3. Fader-Breiten & Gobo-Icon ────────────────────────────────
      _sec("FXPROG_PROP_SECTION_WIDTHS");
      const fwGrid = document.createElement("div");
      fwGrid.className = "fxprog-propgrid";
      [
        ["dimmer_width_pct", "FXPROG_PROP_DIMMER_WIDTH_PCT",  0, 100, 5,  "%"],
        ["pan_width_pct",    "FXPROG_PROP_PAN_WIDTH_PCT",     0, 100, 5,  "%"],
        ["tilt_width_pct",   "FXPROG_PROP_TILT_WIDTH_PCT",    0, 100, 5,  "%"],
        ["dmx_width_pct",    "FXPROG_PROP_DMX_WIDTH_PCT",     0, 100, 5,  "%"],
        ["gobo_icon_size",   "FXPROG_PROP_GOBO_ICON_SIZE",    0,  80, 4, "px"],
      ].forEach(([f, lk, a, b, s, u]) => _sliderRow(fwGrid, f, lk, a, b, s, u));
      frag.appendChild(fwGrid);

      // ─── 4. Farb-Fader ───────────────────────────────────────────────
      _sec("FXPROG_PROP_SECTION_COLOR_FADERS");
      [
        ["show_hsv",    "FXPROG_PROP_SHOW_HSV"],
        ["show_cmy",    "FXPROG_PROP_SHOW_CMY"],
        ["show_rgb",    "FXPROG_PROP_SHOW_RGB"],
        ["show_picker", "FXPROG_PROP_SHOW_PICKER"],
      ].forEach(([f, lk]) => _toggle(f, lk, true));

      return frag;
    },

    afterPropertiesPaneInserted(paneEl, targetPanelId, api) {
      const root = document.querySelector(`[data-panel-id="${targetPanelId}"] .fxprog`);
      const livePreview = () => {
        if (root) _applyProgConfig(root, this.readPropertiesPane() || {});
      };
      // Farbfelder: wireColorPair synchronisiert Swatch <-> Hex-Textfeld.
      // livePreview als onChange-Callback stellt sicher, dass Panel-Farben
      // (Selektions- und Fader-Farbe) sofort und ohne Klick auf "Speichern"
      // im Hintergrund sichtbar werden.
      api.wireColorPair("prog-module-sel-color-swatch",   "prog-module-sel-color-hex",   livePreview);
      api.wireColorPair("prog-module-fader-color-swatch", "prog-module-fader-color-hex", livePreview);

      paneEl.querySelectorAll(
        "#prog-module-view-mode, #prog-module-sel-glow, " +
        "#prog-module-default-view-color, #prog-module-default-view-position, #prog-module-default-view-beam, " +
        "#prog-module-show-hsv, #prog-module-show-cmy, #prog-module-show-rgb, #prog-module-show-picker"
      ).forEach(el => el.addEventListener("change", livePreview));
      paneEl.querySelectorAll(
        "#prog-module-dimmer-width-pct, #prog-module-pan-width-pct, #prog-module-tilt-width-pct, " +
        "#prog-module-dmx-width-pct, #prog-module-gobo-icon-size"
      ).forEach(el => el.addEventListener("input", livePreview));
    },

    readPropertiesPane() {
      const viewSel       = document.getElementById("prog-module-view-mode");
      const hexInput      = document.getElementById("prog-module-sel-color-hex");
      const faderHexInput = document.getElementById("prog-module-fader-color-hex");
      const glowCb         = document.getElementById("prog-module-sel-glow");
      const dimmerWidthEl = document.getElementById("prog-module-dimmer-width-pct");
      const panWidthEl    = document.getElementById("prog-module-pan-width-pct");
      const tiltWidthEl   = document.getElementById("prog-module-tilt-width-pct");
      const dmxWidthEl    = document.getElementById("prog-module-dmx-width-pct");
      const goboIconEl    = document.getElementById("prog-module-gobo-icon-size");
      const showHsvCb      = document.getElementById("prog-module-show-hsv");
      const showCmyCb      = document.getElementById("prog-module-show-cmy");
      const showRgbCb      = document.getElementById("prog-module-show-rgb");
      const showPickerCb   = document.getElementById("prog-module-show-picker");
      const config = {};
      if (viewSel)  config.view_mode = viewSel.value;
      ["color", "position", "beam"].forEach(cat => {
        const el = document.getElementById("prog-module-default-view-" + cat);
        if (el) config["default_view_" + cat] = el.value;
      });
      if (hexInput) {
        const h = hexInput.value.trim();
        if (/^#[0-9a-fA-F]{6}$/.test(h)) config.sel_color = h;
      }
      if (faderHexInput) {
        const h = faderHexInput.value.trim();
        if (/^#[0-9a-fA-F]{6}$/.test(h)) config.fader_color = h;
      }
      if (glowCb) config.sel_glow = glowCb.checked;
      if (dimmerWidthEl) config.dimmer_width_pct = parseInt(dimmerWidthEl.value, 10) || 0;
      if (panWidthEl)    config.pan_width_pct    = parseInt(panWidthEl.value, 10) || 0;
      if (tiltWidthEl)   config.tilt_width_pct   = parseInt(tiltWidthEl.value, 10) || 0;
      if (dmxWidthEl)    config.dmx_width_pct    = parseInt(dmxWidthEl.value, 10) || 0;
      if (goboIconEl)    config.gobo_icon_size   = parseInt(goboIconEl.value, 10) || 0;
      if (showHsvCb)    config.show_hsv    = showHsvCb.checked;
      if (showCmyCb)    config.show_cmy    = showCmyCb.checked;
      if (showRgbCb)    config.show_rgb    = showRgbCb.checked;
      if (showPickerCb) config.show_picker = showPickerCb.checked;
      return Object.keys(config).length ? config : null;
    },

    onMessage(panelEl, messageType, payload) {
      if (messageType === "fixture_groups_changed") {
        _renderDot2Grid(panelEl, _getState(panelEl).fixtures || {});       // neue Gruppen-Sortierung
        _updateSidebarForSelection(panelEl);
      } else if (messageType === "fixtures_changed" || messageType === "state_snapshot") {
        const fixtures = payload.fixtures || {};
        const newIds = new Set(Object.keys(fixtures));
        const PS = window.ProgrammerState;
        for (const id of [...PS.selectedIds]) {
          if (!newIds.has(id)) PS.selectedIds.delete(id);
        }
        _renderDot2Grid(panelEl, fixtures);
        _updateSidebarForSelection(panelEl);
      } else if (messageType === "dmx_universe_changed") {
        // Cache immer aktualisieren - unabhaengig von Selektion/Universum -
        // damit _rebuildDmxDirectPane frische Werte liest, auch wenn kein
        // DMX-Monitor-Panel geoeffnet ist (der sonst den Cache befuellt).
        if (payload.universe !== undefined) {
          window.__dmxUniverseValueCache[payload.universe] = payload.values || [];
        }
        // DMX-Direct-Fader + Gobo-Fader live aktualisieren
        const PS = window.ProgrammerState;
        if (!PS.selectedIds.size) return;
        const firstId = [...PS.selectedIds][0];
        const fx = (_getState(panelEl).fixtures || {})[firstId];
        if (!fx || fx.universe !== payload.universe) return;
        const values = payload.values || [];
        // DMX-Direct-Fader
        panelEl.querySelectorAll(".fxprog-dmxdirect__faders .vfader[data-dmx-offset], .fxprog-rawfader[data-dmx-offset]").forEach(vf => {
          if (vf.isDragging) return;
          const offset = parseInt(vf.dataset.dmxOffset, 10);
          const rawVal = values[(fx.start_channel - 1) + offset] || 0;
          if (vf.setValue) vf.setValue(DMX.byteToPct(rawVal));
        });
        // Rad-Fader (Gobo, Prisma, Farbrad): Fader-Position nach Slot-Klick oder externem Update
        panelEl.querySelectorAll(".fxprog-gobo-faders-wrap .vfader[data-dmx-offset], .fxprog-prism-faders-wrap .vfader[data-dmx-offset], .fxprog-color-faders-wrap .vfader[data-dmx-offset]").forEach(vf => {
          if (vf.isDragging) return;
          const offset = parseInt(vf.dataset.dmxOffset, 10);
          const rawVal = values[(fx.start_channel - 1) + offset] || 0;
          if (vf.setValue) vf.setValue(DMX.byteToPct(rawVal));
        });
        // Gobo-Button-Highlight: aktiven Slot aller Strip-Rows anzeigen
        panelEl.querySelectorAll(".fxprog-gobo-strip__row[data-channel-offset]").forEach(row => {
          const offset = parseInt(row.dataset.channelOffset, 10);
          if (isNaN(offset)) return;
          const rawVal = values[(fx.start_channel - 1) + offset] || 0;
          row.querySelectorAll(".fxprog-gobo-btn[data-dmx-from]").forEach(btn => {
            const from = parseInt(btn.dataset.dmxFrom, 10);
            const to   = parseInt(btn.dataset.dmxTo,   10);
            btn.classList.toggle("fxprog-gobo-btn--selected", rawVal >= from && rawVal <= to);
          });
        });
      } else if (messageType === "language_changed") {
        _renderDot2Grid(panelEl, _getState(panelEl).fixtures || {});
        // Re-populate preset dropdowns so translated "Manual" label shows immediately
        const langState = window.__panelAPI.getState();
        document.dispatchEvent(new CustomEvent("presets-data-updated", { detail: {
          presets: langState.presets || {},
          preset_groups: langState.preset_groups || [],
        }}));
      } else if (messageType === "presets_changed" || messageType === "state_snapshot") {
        // presets_changed arrives from the Presets panel — refresh preset dropdowns
        // state_snapshot is already handled above (fixtures branch), but we also
        // need to update the preset dropdowns whenever we get a fresh snapshot.
        // The fixtures branch above already ran for state_snapshot, so we just
        // update the dropdowns here without re-rendering the grid.
        document.dispatchEvent(new CustomEvent("presets-data-updated", { detail: {
          presets: payload.presets || {},
          preset_groups: payload.preset_groups || [],
        }}));
      }
    },
  });
})();

// ═══════════════════════════════════════════════════════════════════
// Presets Panel Plugin
// ═══════════════════════════════════════════════════════════════════
(function () {
  "use strict";

  // ── Shared state ──────────────────────────────────────────────────
  let _allPresets = {};       // id → preset object (mirrored from server)
  let _allGroups  = [];       // string[]
  let _editingId  = null;     // null = add new, string = editing existing
  let _pendingDeleteId = null;
  let _pendingDeleteGroup = null;

  // ── Anordnung: automatisch nach Typ (Abschnitte mit Symbol, einklappbar) oder nach eigenen Gruppen ──
  const TYPE_ORDER = ["dimmer", "position", "color", "focus", "zoom", "gobo"];
  const TYPE_ICON = { dimmer: "bulb", color: "drop", position: "move", zoom: "scale", focus: "eye", gobo: "wheel" };
  const _sortMode = (panelEl) => (panelEl && panelEl.dataset.presetSort === "group" ? "group" : "type");
  const _typeLabel = (type) => { const key = "PRESET_TYPE_" + String(type).toUpperCase(); const text = i18n(key); return text === key ? String(type) : text; };

  /** Typ-Zeile einer Kachel: Symbol + Beschriftung in der Farbe des Typs. */
  function _typeBadge(type, text) {
    const el = document.createElement("div");
    el.className = "preset-tile__type fxs-cat--" + type;
    el.appendChild(Icons.svg(TYPE_ICON[type] || "fx"));
    const label = document.createElement("span");
    label.textContent = text;
    el.appendChild(label);
    return el;
  }

  /** Zeichnet Abschnitte je Typ (Dimmer, Position, Farbe, Fokus, Zoom, Gobo): Kopf mit Symbol, Name, Anzahl; Klick auf den Kopf klappt den Abschnitt ein. */
  function _renderTypeSections(grid, panelEl, scope, items, typeOf, nameOf, buildGrid) {
    const collapsed = panelEl._collapsedTypes || (panelEl._collapsedTypes = new Set());
    const byType = {};
    for (const item of items) (byType[typeOf(item) || "other"] = byType[typeOf(item) || "other"] || []).push(item);
    const order = [...TYPE_ORDER, ...Object.keys(byType).filter((t) => !TYPE_ORDER.includes(t))];
    for (const type of order) {
      const list = byType[type];
      if (!list || !list.length) continue;
      list.sort((a, b) => String(nameOf(a)).localeCompare(String(nameOf(b)), undefined, { sensitivity: "base", numeric: true }));
      const key = scope + ":" + type;
      const hdr = document.createElement("button");
      hdr.type = "button";
      hdr.className = "preset-type-header fxs-cat--" + type;
      hdr.dataset.type = type;
      hdr.setAttribute("aria-expanded", collapsed.has(key) ? "false" : "true");
      hdr.appendChild(Icons.svg(TYPE_ICON[type] || "fx", "preset-type-header__icon"));
      const name = document.createElement("span");
      name.className = "preset-type-header__name";
      name.textContent = _typeLabel(type);
      const count = document.createElement("span");
      count.className = "preset-type-header__count";
      count.textContent = String(list.length);
      const chevron = Icons.svg(collapsed.has(key) ? "expand" : "collapse", "preset-type-header__chevron");
      hdr.append(name, count, chevron);
      hdr.addEventListener("click", () => {
        if (collapsed.has(key)) collapsed.delete(key); else collapsed.add(key);
        _renderPanel(panelEl);
      });
      grid.appendChild(hdr);
      if (!collapsed.has(key)) grid.appendChild(buildGrid(list));
    }
  }

  // ── Helper: build color preview style ─────────────────────────────
  function _previewStyle(preset) {
    if (preset.type === "color") {
      const v = preset.values || {};
      return `background:rgb(${v.r||0},${v.g||0},${v.b||0})`;
    }
    if (preset.type === "dimmer") {
      const pct = Math.round(preset.values && preset.values.level != null ? preset.values.level : 0);
      const lum = Math.round(pct * 0.85);
      return `background:hsl(0,0%,${lum}%)`;
    }
    if (preset.type === "focus" || preset.type === "zoom" || preset.type === "gobo") {      // Fokus, Zoom, Gobo: ein Wert 0-100 % als Balken (Gobo: das Gobo-Rad 1)
      const pct = Math.round(preset.values && preset.values.level != null ? preset.values.level : 0);
      return `background: linear-gradient(90deg, #2d5f8a ${pct}%, #1a2a3a ${pct}%)`;
    }
    // position
    return `background: linear-gradient(135deg, #1a3a5c 0%, #0d2340 100%)`;
  }

  // ── Helper: build preview content ─────────────────────────────────
  function _previewContent(preset) {
    if (preset.type === "dimmer") {
      return `${Math.round(preset.values && preset.values.level != null ? preset.values.level : 0)}%`;
    }
    if (preset.type === "color") {
      return "";
    }
    if (preset.type === "gobo") {
      const v = preset.values || {};
      const parts = [];
      if (v.level != null) parts.push(`G${Math.round(v.level)}`);
      if (v.spin != null) parts.push(`R${Math.round(v.spin)}`);
      if (v.gobo2 != null) parts.push(`G2 ${Math.round(v.gobo2)}`);
      if (v.gobo2_spin != null) parts.push(`R2 ${Math.round(v.gobo2_spin)}`);
      return parts.join("\n") || "-";
    }
    if (preset.type === "focus" || preset.type === "zoom") {
      return `${Math.round(preset.values && preset.values.level != null ? preset.values.level : 0)}%`;
    }
    // position (praezise Werte: eine Nachkommastelle zeigen, wenn der Wert nicht ganzzahlig ist)
    const v = preset.values || {};
    const shown = (x) => { const n = x != null ? x : 50; return Math.abs(n - Math.round(n)) < 0.05 ? String(Math.round(n)) : n.toFixed(1); };
    return `P${shown(v.pan)}\nT${shown(v.tilt)}`;
  }

  // ── Render all panels of type "presets" ───────────────────────────
  function _renderAllPanels() {
    document.querySelectorAll('[data-panel-type="presets"]').forEach(panelEl => {
      _renderPanel(panelEl);
    });
  }

  function _renderPanel(panelEl) {
    if (panelEl && panelEl.dataset.presetMode === "fx") { _renderFxPanel(panelEl); return; }
    const grid = panelEl ? panelEl.querySelector(".preset-scroll") : null;
    if (!grid) return;

    const filterBtn = panelEl.querySelector(".preset-filter__btn--active");
    const filter = filterBtn ? (filterBtn.dataset.filter || "all") : "all";

    grid.innerHTML = "";

    // Filter presets
    const presets = Object.values(_allPresets).filter(p =>
      filter === "all" || p.type === filter
    );

    const byType = _sortMode(panelEl) === "type";
    if (presets.length === 0 && (byType || _allGroups.length === 0)) {
      const empty = document.createElement("div");
      empty.className = "preset-empty";
      empty.textContent = i18n("PRESET_EMPTY");
      grid.appendChild(empty);
      return;
    }
    if (byType) {
      _renderTypeSections(grid, panelEl, "presets", presets, (p) => p.type, (p) => p.name, _buildTileGrid);
      return;
    }

    // Group presets
    const grouped = {};   // group name → preset[]
    const ungrouped = [];
    for (const p of presets) {
      if (p.group && _allGroups.includes(p.group)) {
        (grouped[p.group] = grouped[p.group] || []).push(p);
      } else {
        ungrouped.push(p);
      }
    }

    // Render groups (render header even if group is empty)
    for (const gname of _allGroups) {
      const gPresets = grouped[gname];
      const hdr = document.createElement("div");
      hdr.className = "preset-group-header";
      hdr.innerHTML = `<span>${gname}</span>`;
      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "preset-group-header__delete";
      delBtn.title = i18n("PRESET_GROUP_DELETE");
      delBtn.textContent = "✕";
      delBtn.dataset.group = gname;
      delBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        _confirmDeleteGroup(gname);
      });
      hdr.appendChild(delBtn);
      grid.appendChild(hdr);
      if (gPresets && gPresets.length > 0) {
        grid.appendChild(_buildTileGrid(gPresets));
      }
    }

    // Render ungrouped
    if (ungrouped.length > 0) {
      if (_allGroups.length > 0) {
        const hdr = document.createElement("div");
        hdr.className = "preset-group-header";
        hdr.textContent = i18n("PRESET_GROUP_UNGROUPED");
        grid.appendChild(hdr);
      }
      grid.appendChild(_buildTileGrid(ungrouped));
    }
  }

  function _buildTileGrid(presets) {
    const gridEl = document.createElement("div");
    gridEl.className = "preset-grid";
    for (const p of presets) {
      const tile = document.createElement("div");
      tile.className = "preset-tile";
      tile.dataset.presetId = p.id;
      tile.title = p.group ? `${p.name} (${p.group})` : p.name;

      const preview = document.createElement("div");
      preview.className = "preset-tile__preview";
      preview.setAttribute("style", _previewStyle(p));
      const txt = _previewContent(p);
      if (txt) {
        preview.style.whiteSpace = "pre";
        preview.style.lineHeight = "1.1";
        preview.textContent = txt;
      }
      tile.appendChild(preview);

      const nameEl = document.createElement("div");
      nameEl.className = "preset-tile__name";
      nameEl.textContent = p.name;
      tile.appendChild(nameEl);

      tile.appendChild(_typeBadge(p.type, _typeLabel(p.type)));

      // Right-click → context menu
      tile.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        e.stopPropagation();
        _showContextMenu(p.id, e.clientX, e.clientY);
      });

      gridEl.appendChild(tile);
    }
    return gridEl;
  }

  // ── Quick-apply: send preset values to selected fixtures ──────────
  function _applyPreset(preset) {
    const PS = window.ProgrammerState;
    if (!PS || !PS.selectedIds.size) return;
    const ids = [...PS.selectedIds];
    // applyPreset() uebernimmt Wertesetzung + merkt sich die preset_uuid
    // je Fixture (solange unveraendert) - fuer indirekte Referenzierung
    // beim Cue-Speichern im CueList-Panel.
    PS.applyPreset(ids, preset.id, preset.type);          // der Server setzt den Wert und verknuepft die Variable; die Antwort aktualisiert alle Panels
  }

  // ── Context menu ──────────────────────────────────────────────────
  function _showContextMenu(presetId, x, y, kind = "preset") {
    ContextMenu.show(x, y, [
      {
        label: i18n("PRESET_CTX_EDIT"),
        onClick: () => { if (kind === "fx") _openFxEditDialog(presetId); else _openEditDialog(presetId); },
      },
      {
        label: i18n("PRESET_CTX_DELETE"),
        danger: true,
        onClick: () => { if (kind === "fx") _confirmDeleteFx(presetId); else _confirmDelete(presetId); },
      },
    ]);
  }

  function _hideContextMenu() {
    ContextMenu.hide();
  }

  // ── Delete preset ─────────────────────────────────────────────────
  function _confirmDelete(presetId) {
    _pendingDeleteId = presetId;
    const p = _allPresets[presetId];
    const body = document.getElementById("preset-delete-confirm-body");
    if (body && p) {
      body.textContent = i18n("PRESET_DELETE_BODY").replace("{name}", p.name);
    }
    Modal.open("preset-delete-confirm");
  }

  // ── Delete group ──────────────────────────────────────────────────
  function _confirmDeleteGroup(groupName) {
    _pendingDeleteGroup = groupName;
    const body = document.getElementById("preset-group-delete-confirm-body");
    if (body) body.textContent = i18n("PRESET_GROUP_DELETE_CONFIRM").replace("{name}", groupName);
    Modal.open("preset-group-delete-confirm");
  }

  // ── Add/Edit dialog ───────────────────────────────────────────────
  function _openAddDialog() {
    _editingId = null;
    const titleEl = document.getElementById("preset-edit-title");
    if (titleEl) { titleEl.dataset.i18n = "PRESET_ADD_TITLE"; titleEl.textContent = i18n("PRESET_ADD_TITLE"); }
    const nameEl = document.getElementById("preset-edit-name");
    const typeEl = document.getElementById("preset-edit-type");
    if (nameEl) nameEl.value = "";
    if (typeEl) { typeEl.value = "dimmer"; typeEl.disabled = false; }
    _setPresetDialogMode(false);
    _updateEditValues("dimmer", {});
    _populateGroupDropdown("");
    Modal.open("preset-edit");
    if (nameEl) nameEl.focus();
  }

  function _openEditDialog(presetId) {
    _editingId = presetId;
    const p = _allPresets[presetId];
    if (!p) return;
    const titleEl = document.getElementById("preset-edit-title");
    if (titleEl) { titleEl.dataset.i18n = "PRESET_EDIT_TITLE"; titleEl.textContent = i18n("PRESET_EDIT_TITLE"); }
    const nameEl = document.getElementById("preset-edit-name");
    const typeEl = document.getElementById("preset-edit-type");
    if (nameEl) nameEl.value = p.name;
    if (typeEl) { typeEl.value = p.type; typeEl.disabled = true; }       // der Typ gehoert zu den Werten: beim Bearbeiten nur umbenennen und Werte aendern
    _setPresetDialogMode(true);
    _updateEditValues(p.type, p.values || {});
    _populateGroupDropdown(p.group || "");
    Modal.open("preset-edit");
  }

  /** Bearbeiten-Modus: Typ gesperrt (mit Hinweis), Knopf heisst "Speichern & Schliessen"; sonst "Erstellen". */
  function _setPresetDialogMode(editing) {
    const hint = document.getElementById("preset-edit-type-hint");
    if (hint) hint.hidden = !editing;
    const ok = document.getElementById("preset-edit-confirm");
    if (ok) { ok.dataset.i18n = editing ? "SAVE_CLOSE" : "FXS_NEW_CREATE"; ok.textContent = i18n(ok.dataset.i18n); }
  }

  function _populateGroupDropdown(selected) {
    const sel = document.getElementById("preset-edit-group");
    if (!sel) return;
    sel.innerHTML = `<option value="" ${!selected ? "selected" : ""}>${i18n("PRESET_GROUP_NONE")}</option>`;
    for (const g of _allGroups) {
      const opt = document.createElement("option");
      opt.value = g;
      opt.textContent = g;
      if (g === selected) opt.selected = true;
      sel.appendChild(opt);
    }
    // "New group..." option
    const newOpt = document.createElement("option");
    newOpt.value = "__new__";
    newOpt.textContent = i18n("PRESET_GROUP_NEW");
    sel.appendChild(newOpt);
  }

  // ── Wert-Felder des Variablen-Dialogs ─────────────────────────────
  // Jeder Wert ist eine Zeile: Beschriftung, Schieberegler, Zahlenfeld (und bei optionalen Werten ein Haken "Wert setzen"). Position hat je Achse einen groben und einen
  // feinen Regler (16 Bit): Grob = ganze Prozent, Fein = der Rest bis zum naechsten Prozent; das Zahlenfeld zeigt/nimmt die Summe mit vier Nachkommastellen.
  const _GOBO_FIELDS = [
    { key: "level", labelKey: "PRESET_GOBO_SELECT", optional: false },
    { key: "spin", labelKey: "PRESET_GOBO_SPIN", optional: true },
    { key: "gobo2", labelKey: "PRESET_GOBO2_SELECT", optional: true },
    { key: "gobo2_spin", labelKey: "PRESET_GOBO2_SPIN", optional: true },
  ];

  function _peRow(labelText) {
    const row = document.createElement("div");
    row.className = "pe-row";
    const label = document.createElement("div");
    label.className = "pe-row__label";
    label.textContent = labelText;
    row.appendChild(label);
    return { row, label };
  }

  function _peNumber(value, min, max, step) {
    const num = document.createElement("input");
    num.type = "number";
    num.className = "pe-number";
    num.min = min; num.max = max; num.step = step;
    num.value = value;
    return num;
  }

  function _peRange(value, min, max, step) {
    const range = document.createElement("input");
    range.type = "range";
    range.className = "pe-range";
    range.min = min; range.max = max; range.step = step;
    range.value = value;
    if (window.ocRangeFill) window.ocRangeFill(range);
    return range;
  }

  /** Ein Prozentwert (0-100): Regler + Zahlenfeld, optional mit Haken. */
  function _peLevelRow(id, labelText, value, { optional = false, enabled = true, step = 1, decimals = 0 } = {}) {
    const { row, label } = _peRow(labelText);
    let check = null;
    if (optional) {
      check = document.createElement("input");
      check.type = "checkbox";
      check.className = "pe-check";
      check.id = id + "-on";
      check.checked = enabled;
      check.title = i18n("PRESET_ENABLE");
      label.prepend(check);
    }
    const controls = document.createElement("div");
    controls.className = "pe-row__controls";
    const range = _peRange(value, 0, 100, step);
    range.id = id;
    const num = _peNumber(Number(value).toFixed(decimals), 0, 100, step);
    num.id = id + "-num";
    range.addEventListener("input", () => { num.value = Number(range.value).toFixed(decimals); });
    num.addEventListener("input", () => {
      const v = Math.max(0, Math.min(100, parseFloat(num.value)));
      if (!isNaN(v)) { range.value = v; if (window.ocRangeFill) window.ocRangeFill(range); }
    });
    controls.append(range, num, document.createTextNode("%"));
    row.appendChild(controls);
    if (check) {
      const apply = () => { row.classList.toggle("pe-row--off", !check.checked); range.disabled = num.disabled = !check.checked; };
      check.addEventListener("change", apply);
      apply();
    }
    return row;
  }

  /** Eine Positionsachse: Grob-Regler (ganze %), Fein-Regler (0-1 %) und die Summe als Zahl (4 Nachkommastellen = 16 Bit). */
  function _peAxisRow(id, labelText, value) {
    const wrap = document.createElement("div");
    wrap.className = "pe-axis";
    const { row, label } = _peRow(labelText);
    const total = Math.max(0, Math.min(100, Number(value)));
    const coarse = Math.min(100, Math.floor(total));
    const fine = total >= 100 ? 0 : total - coarse;
    const num = _peNumber(total.toFixed(4), 0, 100, 0.0001);
    num.id = id;
    const controls = document.createElement("div");
    controls.className = "pe-row__controls pe-row__controls--axis";
    const mk = (suffixKey, id2, v, max, step) => {
      const cell = document.createElement("label");
      cell.className = "pe-axis__cell";
      const name = document.createElement("span");
      name.textContent = i18n(suffixKey);
      const range = _peRange(v, 0, max, step);
      range.id = id2;
      cell.append(name, range);
      return { cell, range };
    };
    const c = mk("PRESET_COARSE", id + "-coarse", coarse, 100, 1);
    const f = mk("PRESET_FINE", id + "-fine", fine, 1, 0.0001);
    const fromSliders = () => {
      const v = Math.min(100, parseFloat(c.range.value) + (parseFloat(c.range.value) >= 100 ? 0 : parseFloat(f.range.value)));
      num.value = v.toFixed(4);
    };
    c.range.addEventListener("input", fromSliders);
    f.range.addEventListener("input", fromSliders);
    num.addEventListener("input", () => {
      const v = Math.max(0, Math.min(100, parseFloat(num.value)));
      if (isNaN(v)) return;
      c.range.value = Math.min(100, Math.floor(v));
      f.range.value = v >= 100 ? 0 : v - Math.floor(v);
      if (window.ocRangeFill) { window.ocRangeFill(c.range); window.ocRangeFill(f.range); }
    });
    controls.append(c.cell, f.cell, num, document.createTextNode("%"));
    row.appendChild(controls);
    wrap.appendChild(row);
    return wrap;
  }

  function _updateEditValues(type, values) {
    const wrap = document.getElementById("preset-edit-values");
    if (!wrap) return;
    wrap.innerHTML = "";
    values = values || {};

    if (type === "dimmer") {
      wrap.appendChild(_peLevelRow("preset-val-level", i18n("PRESET_VALUE_LEVEL"), values.level != null ? values.level : 50));

    } else if (type === "focus" || type === "zoom") {
      wrap.appendChild(_peLevelRow("preset-val-level", i18n("PRESET_TYPE_" + type.toUpperCase()), values.level != null ? values.level : 50, { step: 0.5, decimals: 1 }));

    } else if (type === "gobo") {
      const hint = document.createElement("div");
      hint.className = "pe-hint";
      hint.textContent = i18n("PRESET_GOBO_HINT");
      wrap.appendChild(hint);
      _GOBO_FIELDS.forEach(({ key, labelKey, optional }) => {
        const present = values[key] != null;
        wrap.appendChild(_peLevelRow("preset-val-" + key, i18n(labelKey), present ? values[key] : (key === "level" ? 0 : 0),
          { optional, enabled: optional ? present : true, step: 0.5, decimals: 1 }));
      });

    } else if (type === "position") {
      const hint = document.createElement("div");
      hint.className = "pe-hint";
      hint.textContent = i18n("PRESET_POSITION_HINT");
      wrap.appendChild(hint);
      wrap.appendChild(_peAxisRow("preset-val-pan", "Pan", values.pan != null ? values.pan : 50));
      wrap.appendChild(_peAxisRow("preset-val-tilt", "Tilt", values.tilt != null ? values.tilt : 50));

    } else if (type === "color") {
      const { row, label } = _peRow(i18n("PRESET_VALUE_COLOR"));
      const r = values.r != null ? values.r : 255;
      const g = values.g != null ? values.g : 0;
      const b = values.b != null ? values.b : 0;
      const hex = "#" + [r, g, b].map(x => Math.round(x).toString(16).padStart(2, "0")).join("");
      const controls = document.createElement("div");
      controls.className = "pe-row__controls";
      controls.innerHTML = `<input id="preset-val-color-swatch" type="color" class="color-swatch-input" value="${hex}">
          <input id="preset-val-color-hex" type="text" class="color-hex-input" value="${hex}" maxlength="7" style="flex:1">`;
      row.appendChild(controls);
      wrap.appendChild(row);
      const swatchEl = controls.querySelector("#preset-val-color-swatch");
      const hexEl    = controls.querySelector("#preset-val-color-hex");
      swatchEl.addEventListener("input", () => { hexEl.value = swatchEl.value; });
      hexEl.addEventListener("input", () => { if (/^#[0-9a-fA-F]{6}$/.test(hexEl.value)) swatchEl.value = hexEl.value; });
    }
  }

  function _readNumber(id, fallback) {
    const el = document.getElementById(id);
    const v = el ? parseFloat(el.value) : NaN;
    return isNaN(v) ? fallback : Math.max(0, Math.min(100, v));
  }

  function _readEditValues(type) {
    if (type === "dimmer") {
      return { level: Math.round(_readNumber("preset-val-level", 50)) };
    }
    if (type === "focus" || type === "zoom") {
      return { level: Math.round(_readNumber("preset-val-level", 50) * 10) / 10 };
    }
    if (type === "gobo") {
      const out = {};
      for (const { key, optional } of _GOBO_FIELDS) {
        const on = document.getElementById("preset-val-" + key + "-on");
        if (optional && on && !on.checked) continue;
        out[key] = Math.round(_readNumber("preset-val-" + key, 0) * 10) / 10;
      }
      return out;
    }
    if (type === "position") {
      return {
        pan: Number(_readNumber("preset-val-pan", 50).toFixed(4)),
        tilt: Number(_readNumber("preset-val-tilt", 50).toFixed(4)),
      };
    }
    if (type === "color") {
      const hexEl = document.getElementById("preset-val-color-hex");
      const hex = hexEl ? hexEl.value : "#ff0000";
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      return { r: isNaN(r) ? 255 : r, g: isNaN(g) ? 0 : g, b: isNaN(b) ? 0 : b };
    }
    return {};
  }

  // ── Wire dialogs (called once after DOM ready) ────────────────────
  function _wireDialogs() {
    _wireFxDialogs();
    // Type-change → update value fields
    const typeEl = document.getElementById("preset-edit-type");
    if (typeEl) {
      typeEl.addEventListener("change", () => {
        _updateEditValues(typeEl.value, {});
      });
    }

    // Group change → "New Group" opens group-add dialog
    const groupEl = document.getElementById("preset-edit-group");
    if (groupEl) {
      groupEl.addEventListener("change", () => {
        if (groupEl.value === "__new__") {
          _groupAddTarget = "preset";
          _openGroupAddDialog();
          groupEl.value = "";
        }
      });
    }

    // Confirm save preset
    const confirmBtn = document.getElementById("preset-edit-confirm");
    if (confirmBtn) {
      confirmBtn.addEventListener("click", () => {
        const nameInput = document.getElementById("preset-edit-name");
        const name = nameInput ? nameInput.value.trim() : "";             // leer: der Server vergibt Typ_1, Typ_2 ...
        const typeInput = document.getElementById("preset-edit-type");
        const type = typeInput ? typeInput.value : "dimmer";
        const groupInput = document.getElementById("preset-edit-group");
        let group = groupInput ? groupInput.value : "";
        if (group === "__new__") group = "";
        // Duplikats-Prüfung: gleicher Name (case-insensitive) + Typ + Gruppe
        const nameLower = name.toLowerCase();
        const isDupe = !!name && Object.entries(_allPresets).some(([pid, p]) =>
          p.name.toLowerCase() === nameLower && pid !== _editingId
        );
        if (isDupe) {
          _showToast(i18n("PRESET_DUPE_NAME").replace("{name}", name), "warn");
          return;
        }
        const values = _readEditValues(type);
        if (_editingId) {
          window.__panelAPI.sendToServer("update_preset", { id: _editingId, name, type, group, values });
        } else {
          window.__panelAPI.sendToServer("add_preset", { name, type, group, values });
        }
        Modal.close("preset-edit");
      });
    }

    // Delete confirm
    const deleteBtn = document.getElementById("preset-delete-confirm-button");
    if (deleteBtn) {
      deleteBtn.addEventListener("click", () => {
        if (_pendingDeleteFxId) {
          window.__panelAPI.sendToServer("delete_fx", { id: _pendingDeleteFxId });
          _pendingDeleteFxId = null;
        }
        if (_pendingDeleteId) {
          window.__panelAPI.sendToServer("delete_preset", { id: _pendingDeleteId });
          _pendingDeleteId = null;
        }
        Modal.close("preset-delete-confirm");
      });
    }

    // Group add confirm
    const groupAddBtn = document.getElementById("preset-group-add-confirm");
    if (groupAddBtn) {
      groupAddBtn.addEventListener("click", () => {
        const nameInput = document.getElementById("preset-group-add-name");
        const name = nameInput ? nameInput.value.trim() : "";
        if (name) {
          window.__panelAPI.sendToServer(_groupAddTarget === "fx" ? "add_fx_group" : "add_preset_group", { name });
        }
        Modal.close("preset-group-add");
      });
    }

    // Group delete confirm
    const groupDeleteBtn = document.getElementById("preset-group-delete-confirm-button");
    if (groupDeleteBtn) {
      groupDeleteBtn.addEventListener("click", () => {
        if (_pendingDeleteFxGroup) {
          window.__panelAPI.sendToServer("delete_fx_group", { name: _pendingDeleteFxGroup });
          _pendingDeleteFxGroup = null;
        }
        if (_pendingDeleteGroup) {
          window.__panelAPI.sendToServer("delete_preset_group", { name: _pendingDeleteGroup });
          _pendingDeleteGroup = null;
        }
        Modal.close("preset-group-delete-confirm");
      });
    }
  }

  // ── Programmer preset dropdowns ───────────────────────────────────
  // Injects a small preset-select row at the top of dimmer/position/color panes.
  // Eine Dropdown-Zeile (Manuell / Variable / Effekt) je Effekt-Kategorie. Die Kategorie ist zugleich der Preset-Typ ("Variable") und der Schluessel der Effekt-Zuweisung.
  // Dimmer/Position/Farbe: eine Zeile oben in der Ansicht, die beim Wirken die ganze Ansicht sperrt. Fokus und Zoom teilen sich die Fokus-Ansicht, Gobo steht im Gobo-Reiter des
  // Beam-Bereichs: dort sperrt die Zeile nur den eigenen Fader bzw. die Gobo-Raeder (CSS .fxprog-pane--lock-<kategorie>).
  const PROGRAMMER_ROWS = [
    { pane: "dimmer", cat: "dimmer", labelKey: "PRESET_LABEL", lockAll: true },
    { pane: "position", cat: "position", labelKey: "PRESET_LABEL", lockAll: true },
    { pane: "color", cat: "color", labelKey: "PRESET_LABEL", lockAll: true },
    { pane: "focus", cat: "focus", labelKey: "FXPROG_ROW_FOCUS", multi: true },
    { pane: "focus", cat: "zoom", labelKey: "FXPROG_ROW_ZOOM", multi: true },
    { pane: "beam", cat: "gobo", labelKey: "FXPROG_ROW_GOBO", into: '.fxprog-attrpane[data-panel="gobo"]' },
  ];
  const _programmerRowCfg = (cat) => PROGRAMMER_ROWS.find((r) => r.cat === cat);

  function _updateProgrammerPresetDropdowns() {
    document.querySelectorAll('[data-panel-type="programmer"]').forEach(panelEl => {
      PROGRAMMER_ROWS.forEach(cfg => {
        const pane = panelEl.querySelector(`.fxprog-pane[data-pane="${cfg.pane}"]`);
        if (!pane) return;
        let row = pane.querySelector(`.fxprog-preset-row[data-cat="${cfg.cat}"]`);
        if (!row) {
          let host = cfg.into ? pane.querySelector(cfg.into) : pane;
          if (!host) return;
          if (cfg.multi) {                                        // mehrere Zeilen nebeneinander in einem Behaelter
            let group = pane.querySelector(":scope > .fxprog-preset-rows");
            if (!group) { group = document.createElement("div"); group.className = "fxprog-preset-rows"; pane.insertBefore(group, pane.firstChild); }
            host = group;
          }
          row = document.createElement("div");
          row.className = "fxprog-preset-row";
          row.dataset.cat = cfg.cat;
          const label = document.createElement("span");
          label.className = "fxprog-preset-row__label";
          label.dataset.i18n = cfg.labelKey;
          label.textContent = i18n(cfg.labelKey);
          const sel = document.createElement("select");
          sel.className = "fxprog-preset-row__select";
          sel.dataset.cat = cfg.cat;
          row.appendChild(label);
          row.appendChild(sel);
          sel.addEventListener("change", () => _onProgrammerPresetChange(sel, cfg.cat));
          if (cfg.multi) host.appendChild(row); else host.insertBefore(row, host.firstChild);
        }
        _populateProgrammerDropdown(row.querySelector("select"), cfg.cat);
      });
    });
  }

  function _populateProgrammerDropdown(sel, paneType) {
    if (!sel) return;
    const current = sel.value;
    sel.innerHTML = `<option value="">${i18n("PRESET_MANUAL")}</option>`;
    const filtered = Object.values(_allPresets).filter(p => p.type === paneType);
    for (const p of filtered) {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = i18n("PRESET_DROPDOWN_VARIABLE").replace("{name}", p.name);
      if (p.id === current) opt.selected = true;
      sel.appendChild(opt);
    }
    for (const [fxId, d] of Object.entries(_allFx)) {
      if (_fxCategoryOf(d.kind) !== paneType) continue;
      const opt = document.createElement("option");
      opt.value = "fx:" + fxId;
      opt.textContent = i18n("FXE_DROPDOWN_EFFECT").replace("{name}", d.name);
      if (opt.value === current) opt.selected = true;
      sel.appendChild(opt);
    }
    sel.classList.toggle("fxprog-preset-row__select--active", !!sel.value);
    // Sync locked pane state in case the active preset was deleted
    const panelEl = sel.closest('[data-panel-type="programmer"]');
    if (panelEl) {
      if (!panelEl._activePresets) panelEl._activePresets = {};
      panelEl._activePresets[paneType] = sel.value || null;
      _lockProgrammerRow(sel, paneType, !!sel.value);
    }
  }

  /** Sperrt die Bedienelemente, die ein Preset/Effekt gerade steuert: die ganze Ansicht (Dimmer/Position/Farbe) oder nur den Teil dieser Kategorie (Fokus, Zoom, Gobo). */
  function _lockProgrammerRow(sel, cat, locked) {
    const pane = sel.closest(".fxprog-pane");
    if (!pane) return;
    const cfg = _programmerRowCfg(cat);
    if (cat === "position") {
      // Ein Effekt sperrt nur die Achsen, die sein Skript wirklich setzt (nur `pan` -> Tilt bleibt von Hand bedienbar); eine Variable setzt immer beide.
      let attrs = ["pan", "tilt"];
      if (String(sel.value).startsWith("fx:")) {
        const d = _allFx[String(sel.value).slice(3)];
        const script = d && _fxScripts[d.kind];
        if (script && Array.isArray(script.attrs) && script.attrs.length) attrs = script.attrs;
      }
      const pan = locked && attrs.includes("pan"), tilt = locked && attrs.includes("tilt");
      pane.classList.toggle("fxprog-pane--preset-active", pan && tilt);
      pane.classList.toggle("fxprog-pane--lock-pan", pan && !tilt);
      pane.classList.toggle("fxprog-pane--lock-tilt", tilt && !pan);
      return;
    }
    pane.classList.toggle(cfg && cfg.lockAll ? "fxprog-pane--preset-active" : "fxprog-pane--lock-" + cat, locked);
  }

  function _onProgrammerPresetChange(sel, paneType) {
    const prevValue = sel.dataset.prevValue || "";
    sel.dataset.prevValue = sel.value;
    const PS = window.ProgrammerState;
    const fixtureIds = PS ? [...PS.selectedIds] : [];
    if (prevValue.startsWith("fx:") && prevValue !== sel.value) {
      window.__panelAPI.sendToServer("fx_assign", { fixture_ids: fixtureIds, category: paneType, fx_id: null });
    }
    if (sel.value.startsWith("fx:")) {
      window.__panelAPI.sendToServer("fx_assign", { fixture_ids: fixtureIds, category: paneType, fx_id: sel.value.slice(3) });
    }
    sel.classList.toggle("fxprog-preset-row__select--active", !!sel.value);
    const panelEl = sel.closest('[data-panel-type="programmer"]');
    if (panelEl) {
      if (!panelEl._activePresets) panelEl._activePresets = {};
      panelEl._activePresets[paneType] = sel.value || null;
      _lockProgrammerRow(sel, paneType, !!sel.value);
    }
    if (!sel.value) {
      if (PS && prevValue && !prevValue.startsWith("fx:")) PS.releasePreset(fixtureIds, paneType);      // zurueck auf Manuell: die Verknuepfung entfaellt, die Werte bleiben
      return;
    }
    const preset = _allPresets[sel.value];
    if (preset) _applyPreset(preset);
  }

  // ── FX-Bibliothek (Modus "FX" im Presets-Panel) ───────────────────
  // FX liegen wie Presets in der Show (state.fx_effects). Im Programmer werden
  // sie ueber das Attribut-Dropdown als "fx:<id>" zugewiesen; der Server rechnet
  // die Modulation (app/fx_engine.py).
  // Skript-Verzeichnis aus dem Server (fx_changed.scripts): name -> {label, category, variables}.
  let _fxScripts = {};
  function _fxCategoryOf(kind) {
    return _fxScripts[kind] ? _fxScripts[kind].category : null;
  }
  function _fxKindLabel(kind) {
    return _fxScripts[kind] ? _fxScripts[kind].label : kind;
  }
  let _allFx = {};             // id -> FX-Definition
  let _allFxGroups = [];       // string[]
  let _fxAssignments = {};     // fixture_id -> {kategorie: {fx_id, index, count}}
  let _fxEditingId = null;
  let _pendingDeleteFxId = null;
  let _pendingDeleteFxGroup = null;
  let _groupAddTarget = "preset";   // "preset" | "fx" - welche Gruppen-Liste der Dialog bedient

  function _fxPreviewStyle(d) {
    if (_fxCategoryOf(d.kind) === "color") return "background:linear-gradient(90deg,#f00,#ff0,#0f0,#0ff,#00f,#f0f,#f00)";
    if (_fxCategoryOf(d.kind) === "position") return "background:repeating-linear-gradient(45deg,#333 0 6px,#555 6px 12px)";
    if (["zoom", "focus", "gobo"].includes(_fxCategoryOf(d.kind))) return "background:repeating-linear-gradient(90deg,#1a2a3a 0 8px,#2d5f8a 8px 16px)";
    return "background:linear-gradient(90deg,#111,#eee)";
  }

  function _renderFxPanel(panelEl) {
    const grid = panelEl.querySelector(".preset-scroll");
    if (!grid) return;
    grid.innerHTML = "";
    const filterBtn = panelEl.querySelector(".preset-filter__btn--active");
    const filter = filterBtn ? (filterBtn.dataset.filter || "all") : "all";
    const entries = Object.entries(_allFx).filter(([, d]) =>
      filter === "all" || _fxCategoryOf(d.kind) === filter
    );
    const byType = _sortMode(panelEl) === "type";
    if (!entries.length && (byType || !_allFxGroups.length)) {
      const empty = document.createElement("div");
      empty.className = "preset-empty";
      empty.dataset.i18n = "FXE_EMPTY";
      empty.textContent = i18n("FXE_EMPTY");
      grid.appendChild(empty);
      return;
    }
    if (byType) {
      _renderTypeSections(grid, panelEl, "fx", entries, ([, d]) => _fxCategoryOf(d.kind), ([, d]) => d.name, _buildFxTileGrid);
      return;
    }
    const grouped = {};
    const ungrouped = [];
    for (const entry of entries) {
      const g = entry[1].group;
      if (g && _allFxGroups.includes(g)) (grouped[g] = grouped[g] || []).push(entry);
      else ungrouped.push(entry);
    }
    for (const gname of _allFxGroups) {
      const hdr = document.createElement("div");
      hdr.className = "preset-group-header";
      const label = document.createElement("span");
      label.textContent = gname;
      hdr.appendChild(label);
      const del = document.createElement("button");
      del.type = "button";
      del.className = "preset-group-header__delete";
      del.title = i18n("PRESET_GROUP_DELETE");
      del.textContent = "✕";
      del.addEventListener("click", (e) => { e.stopPropagation(); _confirmDeleteFxGroup(gname); });
      hdr.appendChild(del);
      grid.appendChild(hdr);
      if (grouped[gname]) grid.appendChild(_buildFxTileGrid(grouped[gname]));
    }
    if (ungrouped.length) {
      if (_allFxGroups.length) {
        const hdr = document.createElement("div");
        hdr.className = "preset-group-header";
        hdr.dataset.i18n = "PRESET_GROUP_UNGROUPED";
        hdr.textContent = i18n("PRESET_GROUP_UNGROUPED");
        grid.appendChild(hdr);
      }
      grid.appendChild(_buildFxTileGrid(ungrouped));
    }
  }

  function _buildFxTileGrid(entries) {
    const gridEl = document.createElement("div");
    gridEl.className = "preset-grid";
    for (const [fxId, d] of entries) {
      const tile = document.createElement("div");
      tile.className = "preset-tile";
      tile.dataset.fxId = fxId;
      tile.title = d.group ? `${d.name} (${d.group})` : d.name;

      const preview = document.createElement("div");
      preview.className = "preset-tile__preview";
      preview.setAttribute("style", _fxPreviewStyle(d));
      tile.appendChild(preview);

      const nameEl = document.createElement("div");
      nameEl.className = "preset-tile__name";
      nameEl.textContent = d.name;
      tile.appendChild(nameEl);

      tile.appendChild(_typeBadge(_fxCategoryOf(d.kind) || "fx", _fxKindLabel(d.kind)));

      tile.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        e.stopPropagation();
        _showContextMenu(fxId, e.clientX, e.clientY, "fx");
      });
      gridEl.appendChild(tile);
    }
    return gridEl;
  }

  function _setPanelMode(panelEl, mode) {
    panelEl.dataset.presetMode = mode;
    const isFx = mode === "fx";
    panelEl.querySelectorAll(".preset-mode .fxprog-subtab").forEach(tab => {
      tab.classList.toggle("fxprog-subtab--active", tab.dataset.mode === mode);
    });
    panelEl.querySelectorAll(".preset-toolbar__btn--add").forEach(b => {
      b.dataset.i18n = isFx ? "FXE_TOOLBAR_ADD" : "PRESET_ADD";
      b.textContent = i18n(b.dataset.i18n);
    });
    panelEl.querySelectorAll(".preset-toolbar__btn--group").forEach(b => {
      b.dataset.i18n = isFx ? "FXE_TOOLBAR_GROUP" : "PRESET_GROUP_ADD";
      b.textContent = i18n(b.dataset.i18n);
    });
    _renderPanel(panelEl);
  }

  function _openGroupAddDialog() {
    const title = document.getElementById("preset-group-add-title");
    if (title) {
      title.dataset.i18n = _groupAddTarget === "fx" ? "FXE_GROUP_ADD_TITLE" : "PRESET_GROUP_ADD_TITLE";
      title.textContent = i18n(title.dataset.i18n);
    }
    const inp = document.getElementById("preset-group-add-name");
    if (inp) inp.value = "";
    Modal.open("preset-group-add");
  }

  function _hexOfColor(c) {
    return "#" + [c.r, c.g, c.b]
      .map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("");
  }

  function _colorOfHex(hex) {
    return {
      r: parseInt(hex.slice(1, 3), 16),
      g: parseInt(hex.slice(3, 5), 16),
      b: parseInt(hex.slice(5, 7), 16),
    };
  }

  // Parameter-Regler aus den #VAR-Deklarationen des Skripts (Slider, ColorPicker, NumberInput).
  function _renderFxParams(kind, params) {
    const box = document.getElementById("fx-edit-params");
    if (!box) return;
    box.textContent = "";
    const script = _fxScripts[kind];
    let desc = document.getElementById("fx-edit-desc");
    if (!desc) {                                           // Beschreibung (#DESCRIPTION) und Durchlaeufe pro Sekunde (#RATE) unter der Auswahl der Art
      desc = document.createElement("div");
      desc.id = "fx-edit-desc";
      desc.className = "fx-edit__desc";
      const select = document.getElementById("fx-edit-type");
      if (select) select.insertAdjacentElement("afterend", desc);
    }
    desc.textContent = script ? [script.description, script.rate ? i18n("FXS_RATE_SHORT").replace("{n}", script.rate) : ""].filter(Boolean).join(" \u00b7 ") : "";
    if (!script) return;
    for (const v of script.variables) {
      const row = document.createElement("label");
      row.className = "fx-edit__param";
      const name = document.createElement("span");
      name.className = "fx-edit__param-name";
      name.textContent = v.name;
      row.appendChild(name);
      const current = params && params[v.name] !== undefined ? params[v.name] : v.default;
      if (v.kind === "ColorPicker") {
        const input = document.createElement("input");
        input.type = "color";
        input.value = _hexOfColor(current);
        input.dataset.param = v.name;
        input.dataset.paramKind = "ColorPicker";
        row.appendChild(input);
      } else if (v.kind === "NumberInput") {
        const input = document.createElement("input");
        input.type = "number";
        input.className = "modal__input";
        input.min = String(v.min);
        input.max = String(v.max);
        input.step = String(v.step);
        input.value = String(current);
        input.dataset.param = v.name;
        input.dataset.paramKind = "NumberInput";
        row.appendChild(input);
      } else {
        const wrap = document.createElement("div");
        wrap.className = "fx-edit__slider";
        const input = document.createElement("input");
        input.type = "range";
        input.min = String(v.min);
        input.max = String(v.max);
        input.step = String(v.step);
        input.value = String(current);
        input.dataset.param = v.name;
        input.dataset.paramKind = "Slider";
        const readout = document.createElement("span");
        readout.className = "fx-edit__readout";
        readout.textContent = Number(current).toFixed(2);
        input.addEventListener("input", () => { readout.textContent = Number(input.value).toFixed(2); });
        wrap.appendChild(input);
        wrap.appendChild(readout);
        row.appendChild(wrap);
      }
      box.appendChild(row);
    }
  }

  function _collectFxParams() {
    const out = {};
    document.querySelectorAll("#fx-edit-params [data-param]").forEach(el => {
      out[el.dataset.param] = el.dataset.paramKind === "ColorPicker"
        ? _colorOfHex(el.value)
        : parseFloat(el.value);
    });
    return out;
  }

  function _openFxEditDialog(fxId) {
    _fxEditingId = fxId || null;
    const d = fxId ? _allFx[fxId] : null;
    const title = document.getElementById("fx-edit-title");
    if (title) {
      title.dataset.i18n = d ? "FXE_TITLE_EDIT" : "FXE_TITLE_CREATE";
      title.textContent = i18n(title.dataset.i18n);
    }
    const okBtn = document.getElementById("fx-edit-confirm");
    if (okBtn) { okBtn.dataset.i18n = d ? "SAVE_CLOSE" : "FXS_NEW_CREATE"; okBtn.textContent = i18n(okBtn.dataset.i18n); }
    const typeHint = document.getElementById("fx-edit-type-hint");
    if (typeHint) typeHint.hidden = !d;
    const setVal = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };
    setVal("fx-edit-name", d ? d.name : "");

    const typeSel = document.getElementById("fx-edit-type");
    if (typeSel) {
      typeSel.textContent = "";
      const byCategory = {};
      Object.values(_fxScripts).forEach(s => { (byCategory[s.category] = byCategory[s.category] || []).push(s); });
      Object.keys(byCategory).forEach(category => {                       // nach Kategorie gruppiert (Dimmer, Farbe, Position, Zoom ...), je Gruppe nach Namen
        const group = document.createElement("optgroup");
        const labelKey = "FXS_CAT_" + category.toUpperCase();
        group.label = i18n(labelKey) === labelKey ? category : i18n(labelKey);
        byCategory[category].sort((a, b) => String(a.label).localeCompare(String(b.label), undefined, { sensitivity: "base" })).forEach(s => {
          const opt = document.createElement("option");
          opt.value = s.name;
          opt.textContent = s.label;
          group.appendChild(opt);
        });
        typeSel.appendChild(group);
      });
      if (d && !Object.prototype.hasOwnProperty.call(_fxScripts, d.kind)) {          // Skript fehlt (Datei geloescht): die Art trotzdem anzeigen
        const lost = document.createElement("option");
        lost.value = d.kind;
        lost.textContent = d.kind;
        typeSel.appendChild(lost);
      }
      typeSel.value = d ? d.kind : (Object.keys(_fxScripts)[0] || "");
      typeSel.disabled = !!d;                                  // beim Bearbeiten nur umbenennen und Parameter aendern, nicht die Art wechseln
    }

    const grp = document.getElementById("fx-edit-group");
    if (grp) {
      grp.textContent = "";
      const none = document.createElement("option");
      none.value = "";
      none.dataset.i18n = "FXE_GROUP_NONE";
      none.textContent = i18n("FXE_GROUP_NONE");
      grp.appendChild(none);
      _allFxGroups.forEach(g => {
        const opt = document.createElement("option");
        opt.value = g;
        opt.textContent = g;
        grp.appendChild(opt);
      });
      const created = document.createElement("option");
      created.value = "__new__";
      created.dataset.i18n = "FXE_GROUP_NEW";
      created.textContent = i18n("FXE_GROUP_NEW");
      grp.appendChild(created);
      grp.value = d && d.group && _allFxGroups.includes(d.group) ? d.group : "";
    }
    _renderFxParams(typeSel ? typeSel.value : "", d ? d.params : null);
    Modal.open("fx-edit");
  }

  function _confirmDeleteFx(fxId) {
    _pendingDeleteFxId = fxId;
    const d = _allFx[fxId];
    const body = document.getElementById("preset-delete-confirm-body");
    if (body && d) body.textContent = i18n("FXE_DELETE_BODY").replace("{name}", d.name);
    Modal.open("preset-delete-confirm");
  }

  function _confirmDeleteFxGroup(groupName) {
    _pendingDeleteFxGroup = groupName;
    const body = document.getElementById("preset-group-delete-confirm-body");
    if (body) body.textContent = i18n("PRESET_GROUP_DELETE_CONFIRM").replace("{name}", groupName);
    Modal.open("preset-group-delete-confirm");
  }

  function _wireFxDialogs() {
    const typeEl = document.getElementById("fx-edit-type");
    if (typeEl) typeEl.addEventListener("change", () => _renderFxParams(typeEl.value, null));
    const grp = document.getElementById("fx-edit-group");
    if (grp) {
      grp.addEventListener("change", () => {
        if (grp.value === "__new__") {
          _groupAddTarget = "fx";
          _openGroupAddDialog();
          grp.value = "";
        }
      });
    }
    const confirmBtn = document.getElementById("fx-edit-confirm");
    if (confirmBtn) {
      confirmBtn.addEventListener("click", () => {
        const name = (document.getElementById("fx-edit-name")?.value || "").trim();          // leer: der Server vergibt Kategorie_1, Kategorie_2 ...
        if (!typeEl || !typeEl.value) return;
        if (name && Object.entries(_allFx).some(([id, d]) => id !== _fxEditingId && String(d.name).trim().toLowerCase() === name.toLowerCase())) {
          _showToast(i18n("FXE_DUPE_NAME").replace("{name}", name), "warn");
          return;
        }
        const grpValue = document.getElementById("fx-edit-group")?.value || "";
        const payload = {
          name,
          kind: typeEl.value,
          group: grpValue === "__new__" ? "" : grpValue,
          params: _collectFxParams(),
        };
        if (_fxEditingId) {
          window.__panelAPI.sendToServer("update_fx", { id: _fxEditingId, ...payload });
        } else {
          window.__panelAPI.sendToServer("add_fx", payload);
        }
        Modal.close("fx-edit");
      });
    }
  }

  // Effekt-Liste aus dem Backend (GET /api/effects) - Grundlage aller Effekt-Dropdowns.
  // Wird beim Start und nach jedem gespeicherten oder kompilierten Skript neu geladen.
  async function refreshEffectDropdowns() {
    try {
      const res = await fetch("/api/effects");
      const data = await res.json();
      _fxScripts = Object.fromEntries((data.effects || []).map(s => [s.name, s]));
    } catch (err) {
      return;
    }
    _renderAllPanels();
    _updateProgrammerPresetDropdowns();
    _syncProgrammerDropdownsToFx();
  }
  window.refreshEffectDropdowns = refreshEffectDropdowns;
  refreshEffectDropdowns();

  document.addEventListener("fx-data-updated", (e) => {
    _allFx = e.detail.effects || {};
    _fxScripts = Object.fromEntries((e.detail.scripts || []).map(s => [s.name, s]));
    _allFxGroups = e.detail.groups || [];
    _fxAssignments = e.detail.assignments || {};
    _renderAllPanels();
    _updateProgrammerPresetDropdowns();
    _syncProgrammerDropdownsToFx();
  });

  // Clear Clear: alle Attribut-Dropdowns zurueck auf "Manuell".
  document.addEventListener("programmer-dropdowns-reset", () => {
    if (window.ProgrammerState) window.ProgrammerState.clearAllPresetLinks();
    _setAllProgrammerDropdowns("");
  });

  // Dropdowns zeigen den Zustand des Programmers: ein Effekt, der (manuell oder per Cue)
  // auf den selektierten Fixtures laeuft, wird als "Effekt · Name" angezeigt.
  document.addEventListener("programmer-state-updated", _syncProgrammerDropdownsToFx);

  function _setProgrammerSelectState(sel, value) {
    sel.value = value;
    sel.dataset.prevValue = value;
    sel.classList.toggle("fxprog-preset-row__select--active", !!value);
    const panelEl = sel.closest('[data-panel-type="programmer"]');
    const paneType = sel.dataset.cat || sel.closest(".fxprog-pane")?.dataset.pane || null;
    if (panelEl && paneType) {
      if (!panelEl._activePresets) panelEl._activePresets = {};
      panelEl._activePresets[paneType] = value || null;
    }
    if (paneType) _lockProgrammerRow(sel, paneType, !!value);
  }

  function _setAllProgrammerDropdowns(value) {
    document.querySelectorAll('[data-panel-type="programmer"] .fxprog-preset-row__select').forEach(sel => {
      _setProgrammerSelectState(sel, value);
    });
  }

  // Jedes Dropdown zeigt den echten Zustand der Auswahl: Effekt (alle selektierten
  // Fixtures laufen denselben Effekt dieser Kategorie), sonst Variable (alle teilen
  // dieselbe Variable), sonst Manuell.
  function _syncProgrammerDropdownsToFx() {
    const PS = window.ProgrammerState;
    const ids = PS ? [...PS.selectedIds] : [];
    document.querySelectorAll('[data-panel-type="programmer"] .fxprog-preset-row__select').forEach(sel => {
      const paneType = sel.dataset.cat || sel.closest(".fxprog-pane")?.dataset.pane;
      if (!paneType) return;
      const fxRefs = ids.map(fid => _fxAssignments[fid] && _fxAssignments[fid][paneType] && _fxAssignments[fid][paneType].fx_id);
      const sharedFx = fxRefs.length && fxRefs.every(r => r && r === fxRefs[0]) ? fxRefs[0] : null;
      const links = ids.map(fid => (PS && PS.getPresetRef) ? PS.getPresetRef(fid, paneType) : null);
      const sharedPreset = links.length && links.every(l => l && l === links[0]) ? links[0] : null;
      let target = "";
      if (sharedFx && sel.querySelector(`option[value="fx:${sharedFx}"]`)) target = "fx:" + sharedFx;
      else if (sharedPreset && _allPresets[sharedPreset] && _allPresets[sharedPreset].type === paneType) target = sharedPreset;
      if (sel.value !== target) _setProgrammerSelectState(sel, target);
    });
  }

  // Listen for presets data updated event (dispatched by programmer IIFE)
  document.addEventListener("presets-data-updated", (e) => {
    _allPresets = e.detail.presets || {};
    _allGroups  = e.detail.preset_groups || [];
    _renderAllPanels();
    _updateProgrammerPresetDropdowns();
    // Eine geaenderte Variable verteilt der Server selbst (Programmer und aktive Cues): hier nur neu zeichnen.
  });

  // ── Plugin registration ───────────────────────────────────────────
  window.__panelPlugins.register({
    type: "presets",

    buildContent(panel) {
      const wrap = document.createElement("div");
      wrap.style.cssText = "display:flex;flex-direction:column;height:100%;overflow:hidden;";

      // Toolbar
      const tb = document.createElement("div");
      tb.className = "preset-toolbar";

      const modeWrap = document.createElement("div");
      modeWrap.className = "preset-mode fxprog-subtabs";
      [["presets", "PRESET_MODE_VARIABLES"], ["fx", "FXE_MODE_FX"]].forEach(([mode, key]) => {
        const tab = document.createElement("div");
        tab.className = "fxprog-subtab" + (mode === "presets" ? " fxprog-subtab--active" : "");
        tab.dataset.mode = mode;
        tab.dataset.i18n = key;
        tab.textContent = i18n(key);
        tab.addEventListener("click", () => {
          const pe = wrap.closest("[data-panel-type='presets']") || wrap;
          _setPanelMode(pe, mode);
        });
        modeWrap.appendChild(tab);
      });

      const addBtn = document.createElement("button");
      addBtn.type = "button";
      addBtn.className = "preset-toolbar__btn preset-toolbar__btn--add";
      addBtn.dataset.i18n = "PRESET_ADD";
      addBtn.textContent = i18n("PRESET_ADD");
      addBtn.addEventListener("click", () => {
        const pe = wrap.closest("[data-panel-type='presets']") || wrap;
        if (pe.dataset.presetMode === "fx") _openFxEditDialog(null);
        else _openAddDialog();
      });

      const grpBtn = document.createElement("button");
      grpBtn.type = "button";
      grpBtn.className = "preset-toolbar__btn preset-toolbar__btn--group";
      grpBtn.dataset.i18n = "PRESET_GROUP_ADD";
      grpBtn.textContent = i18n("PRESET_GROUP_ADD");
      grpBtn.addEventListener("click", () => {
        const pe = wrap.closest("[data-panel-type='presets']") || wrap;
        _groupAddTarget = pe.dataset.presetMode === "fx" ? "fx" : "preset";
        const inp = document.getElementById("preset-group-add-name");
        if (inp) inp.value = "";
        _openGroupAddDialog();
      });

      // Filter buttons
      const filterWrap = document.createElement("div");
      filterWrap.className = "preset-filter";
      ["all", "dimmer", "position", "color", "focus", "zoom", "gobo"].forEach((f) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "preset-filter__btn" + (f === "all" ? " preset-filter__btn--active" : "");
        btn.dataset.filter = f;
        const key = f === "all" ? "PRESET_FILTER_ALL" : "PRESET_TYPE_" + f.toUpperCase();
        btn.dataset.i18n = key;
        btn.textContent = i18n(key);
        btn.addEventListener("click", () => {
          tb.querySelectorAll(".preset-filter__btn").forEach(b => b.classList.remove("preset-filter__btn--active"));
          btn.classList.add("preset-filter__btn--active");
          const panelEl = wrap.closest("[data-panel-type='presets']") || wrap;
          _renderPanel(panelEl);
        });
        filterWrap.appendChild(btn);
      });

      // Anordnung: automatisch nach Typ (Standard) oder nach eigenen Gruppen
      const sortWrap = document.createElement("div");
      sortWrap.className = "preset-sort";
      [["type", "PRESET_SORT_TYPE"], ["group", "PRESET_SORT_GROUP"]].forEach(([mode, key]) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "preset-sort__btn" + (mode === "type" ? " preset-sort__btn--active" : "");
        btn.dataset.sort = mode;
        btn.dataset.i18n = key;
        btn.textContent = i18n(key);
        btn.addEventListener("click", () => {
          const panelEl = wrap.closest("[data-panel-type='presets']") || wrap;
          panelEl.dataset.presetSort = mode;
          sortWrap.querySelectorAll(".preset-sort__btn").forEach(b => b.classList.toggle("preset-sort__btn--active", b === btn));
          _renderPanel(panelEl);
        });
        sortWrap.appendChild(btn);
      });

      tb.appendChild(addBtn);
      tb.appendChild(grpBtn);
      tb.appendChild(sortWrap);
      tb.appendChild(filterWrap);

      // Scroll area
      const scroll = document.createElement("div");
      scroll.className = "preset-scroll";

      wrap.appendChild(modeWrap);
      wrap.appendChild(tb);
      wrap.appendChild(scroll);

      // Render after DOM attach (next frame)
      requestAnimationFrame(() => {
        const panelEl = wrap.closest("[data-panel-type='presets']") || wrap;
        _renderPanel(panelEl);
      });
      return wrap;
    },

    onModuleConfigChanged(panelEl, mc) {
      // No special behavior needed
    },

    onMessage(panelEl, messageType, payload) {
      if (messageType === "state_snapshot" || messageType === "presets_changed") {
        _allPresets = payload.presets || {};
        _allGroups  = payload.preset_groups || [];
        _renderPanel(panelEl);
        _updateProgrammerPresetDropdowns();
      } else if (messageType === "language_changed") {
        _renderPanel(panelEl);
        _updateProgrammerPresetDropdowns();
      }
    },
  });

  // Wire dialogs when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", _wireDialogs);
  } else {
    _wireDialogs();
  }

})();

// ═══════════════════════════════════════════════════════════════════
// CueList Panel Plugin (Anlegen/Verwalten/weiches Abfeuern via CueEngine)
// ═══════════════════════════════════════════════════════════════════
(function () {
  "use strict";

  let _allCuelists   = {};   // id -> cuelist object (mirrored from server)
  let _activeCuelistId = null;
  let _activeCueIds  = {};   // cuelist_id -> aktuell aktiver cue_id
  let _editingCuelistId = null;
  let _editingCueId  = null;
  let _pendingDelete = null; // { cuelistId, cueId }
  // Markierte Zeilen (Mehrfachauswahl per Checkbox-Spalte, Umschalt-/Strg-Tippen oder "alle"). Bearbeiten, Loeschen und
  // "Speichern auf diese Nummer" brauchen genau EINE markierte Zeile; die Wisch-Anpassung des Delays wirkt auf alle.
  const _sel = new Set();
  let _swipeEndedAt = 0;     // Zeitpunkt der letzten Wischgeste (das folgende click darf nichts markieren)
  const _singleId = () => (_sel.size === 1 ? [..._sel][0] : null);
  // Mehrfachmodus (Touch): ein Long-Press auf eine Zeile markiert sie und schaltet ihn ein; solange er laeuft, markiert/entmarkiert
  // jeder weitere Tipp auf eine Zeile diese. Er endet, wenn nichts mehr markiert ist oder neben die Zeilen getippt wird.
  let _multi = false;
  let _anchorCueId = null;   // zuletzt angeklickte Zeile: Anker fuer Umschalt-Klick (Bereich), wie lastClickedIdx der Scheinwerfersteuerung
  let _lastStore = null;     // zuletzt gesendeter save_cue (fuer die Rueckfrage, falls der Server einen Konflikt meldet)
  // cuelist_id -> Wiedergabezustand der CueEngine: { cue_id, progress (0-1), remaining (s), state, at }.
  // state: running | paused | stopped | done. "at" ist der Empfangszeitpunkt (performance.now()).
  // Der Ladebalken wird allein daraus gezeichnet: bei "running" EINE lineare CSS-Transition ueber die
  // Restzeit (laeuft auf dem Compositor, ohne dass pro Frame JavaScript oder Layout noetig ist), bei
  // "done" sofort voll (auch bei 0 s Fade: keine Fuell-Animation), bei "paused"/"stopped" eingefroren.
  // Der Zustand bleibt ueber Renders hinweg erhalten - _renderPanel() malt daraus den Balken neu.
  let _playback = {};

  function _ingestPlayback(map) {
    const at = performance.now();
    Object.values(map || {}).forEach((pb) => {
      if (pb && pb.cuelist_id) _playback[pb.cuelist_id] = { ...pb, at };
    });
  }

  function _paintFill(fill, pb) {
    fill.style.transition = "none";
    if (!pb || pb.state === "done") { fill.style.transform = "scaleX(1)"; return; }
    if (pb.state === "paused" || pb.state === "stopped") { fill.style.transform = "scaleX(" + pb.progress + ")"; return; }
    const elapsed = (performance.now() - pb.at) / 1000;
    const remaining = pb.remaining - elapsed;
    if (!(pb.remaining > 0) || remaining <= 0) { fill.style.transform = "scaleX(1)"; return; }
    const now = pb.progress + (1 - pb.progress) * (elapsed / pb.remaining);
    fill.style.transform = "scaleX(" + now + ")";
    void fill.offsetWidth;                                   // Startwert festschreiben, dann animieren
    fill.style.transition = "transform " + remaining + "s linear";
    fill.style.transform = "scaleX(1)";
  }

  function _paintActiveBar(panelEl, cuelistId) {
    const pb = _playback[cuelistId];
    if (!pb) return;
    const fill = panelEl.querySelector('.cue-row[data-cue-id="' + pb.cue_id + '"] .cue-progress-bar__fill');
    if (fill) _paintFill(fill, pb);
  }

  // Follow-Delay des unmittelbar folgenden Cues: derselbe Balken wie bei einer Ueberblendung, nur in der
  // Zeile des Follow-Cues und fuer die Delay-Restzeit (eine Transition, keine Tick-Nachrichten).
  function _syncFollowBar(panelEl, cuelistId) {
    panelEl.querySelectorAll(".cue-progress-bar--follow").forEach((el) => el.remove());
    const pb = _playback[cuelistId];
    const follow = pb && pb.follow;
    if (!follow || panelEl.dataset.showProgressBar === "false") return;
    const cell = panelEl.querySelector('.cue-row[data-cue-id="' + follow.cue_id + '"] .cue-td--name');
    if (!cell) return;
    const bar = document.createElement("span");
    bar.className = "cue-progress-bar cue-progress-bar--follow";
    const fill = document.createElement("span");
    fill.className = "cue-progress-bar__fill";
    bar.appendChild(fill);
    cell.appendChild(bar);
    const done = Math.min(1, Math.max(0, 1 - follow.remaining / Math.max(follow.duration, 1e-6)));
    _paintFill(fill, { state: "running", progress: done, remaining: follow.remaining, at: pb.at });
  }

  // Markierung in allen Cue-Listen-Panels nachfuehren, ohne die Tabelle neu aufzubauen.
  function _syncSelection() {
    if (!_sel.size) _multi = false;
    document.querySelectorAll("[data-panel-type='cuelist']").forEach((panelEl) => {
      panelEl.querySelectorAll(".cue-row").forEach((row) => row.classList.toggle("cue-row--selected", _sel.has(row.dataset.cueId)));
      panelEl.classList.toggle("cuelist--multi", _multi && _sel.size > 0);
      _updateActions(panelEl);
    });
  }

  // Aktionen der Listen-Leiste: Bearbeiten/Loeschen brauchen eine markierte Zeile, Aktualisieren einen aktiven Cue.
  function _updateActions(panelEl) {
    const cl = _currentCuelist(panelEl);
    const hasSelection = !!(cl && _singleId() && cl.cues.some(c => c.id === _singleId()));   // Bearbeiten: genau eine Zeile
    const hasAny = !!(cl && _sel.size && cl.cues.some(c => _sel.has(c.id)));                  // Loeschen: eine oder mehrere
    const hasActive = !!(cl && _activeCueIds[cl.id] && cl.cues.some(c => c.id === _activeCueIds[cl.id]));
    const set = (sel, enabled) => { const b = panelEl.querySelector(sel); if (b) b.disabled = !enabled; };
    set(".cuelist-toolbar__btn--save", !!cl);
    set(".cuelist-toolbar__btn--update", hasActive);
    set(".cuelist-toolbar__btn--edit", hasSelection);
    set(".cuelist-toolbar__btn--delete", hasAny);
  }

  function _esc(s) {
    return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function _fmtNum(n) {
    const num = Number(n);
    return Number.isFinite(num) ? num.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 3 }) : String(n);
  }

  // Attribut-spezifische Fade/Delay-Zeiten sind optional (None = "nutzt die
  // allgemeine Zeit dieser Gruppe", siehe cue_engine.py) - Anzeige dafuer
  // ein dezenter Gedankenstrich statt einer irrefuehrenden "0".
  function _fmtOptNum(n) {
    return (n === null || n === undefined || n === "") ? "—" : _fmtNum(n);
  }

  // ── Spaltenbreiten (pro Geraet im localStorage) ───────────────────────────────────────
  // Name ist standardmaessig deutlich breiter. Ziehen am Spaltenrand aendert die Breite;
  // Doppelklick/Doppeltipp auf den Kopf passt sie an den laengsten Text an.
  const CUE_COLUMNS = [
    { key: "status",      width: 28,  min: 28 },
    { key: "number",      width: 72,  min: 44 },
    { key: "name",        width: 340, min: 80 },
    { key: "trigger",     width: 150, min: 60 },
    { key: "fade",        width: 90,  min: 44 },
    { key: "delay",       width: 90,  min: 44 },
    { key: "mib",         width: 80,  min: 50 },
    { key: "fade_color",  width: 100, min: 44 },
    { key: "delay_color", width: 100, min: 44 },
    { key: "fade_pos",    width: 100, min: 44 },
    { key: "delay_pos",   width: 100, min: 44 },
    { key: "fade_beam",   width: 100, min: 44 },
    { key: "delay_beam",  width: 100, min: 44 },
    { key: "fade_zoom",   width: 100, min: 44 },
    { key: "delay_zoom",  width: 100, min: 44 },
    { key: "fx_fade_in",  width: 110, min: 44 },
    { key: "fx_fade_out", width: 110, min: 44 },
    { key: "cmd",         width: 280, min: 80 },
  ];
  const CUE_COLUMNS_STORAGE = "opencue.cuelistColumns";
  const CUE_COLUMN_MAX = 900;

  let _cueColWidths = (() => {
    try {
      const stored = JSON.parse(localStorage.getItem(CUE_COLUMNS_STORAGE));
      return stored && typeof stored === "object" && !Array.isArray(stored) ? stored : {};
    } catch (error) { return {}; }
  })();

  function _cueColWidth(key) {
    const def = CUE_COLUMNS.find((c) => c.key === key);
    const stored = Number(_cueColWidths[key]);
    return Number.isFinite(stored) && stored > 0 ? Math.max(def.min, Math.min(CUE_COLUMN_MAX, stored)) : def.width;
  }

  function _applyCueColumns(table) {
    const tables = table ? [table] : document.querySelectorAll(".cuelist-table");
    tables.forEach((tbl) => {
      let sum = 0;
      tbl.querySelectorAll("col").forEach((col) => {
        const width = _cueColWidth(col.dataset.col);
        col.style.width = width + "px";
        sum += width;
      });
      tbl.style.width = sum + "px";
    });
  }

  function _saveCueColumns() {
    try { localStorage.setItem(CUE_COLUMNS_STORAGE, JSON.stringify(_cueColWidths)); } catch (error) { /* egal */ }
  }

  function _autoFitCueColumn(table, key) {
    const index = CUE_COLUMNS.findIndex((c) => c.key === key);
    if (index < 0 || key === "status") return;
    const cells = [table.tHead.rows[0].cells[index]]
      .concat(Array.from(table.tBodies[0].rows).map((row) => row.cells[index])).filter(Boolean);
    const probe = document.createElement("span");
    probe.style.cssText = "position:absolute;visibility:hidden;white-space:nowrap;left:-9999px;top:0";
    document.body.appendChild(probe);
    let widest = 0;
    cells.forEach((cell) => {
      const cs = getComputedStyle(cell);
      probe.style.font = cs.font;
      probe.style.letterSpacing = cs.letterSpacing;
      probe.style.textTransform = cs.textTransform;
      const field = cell.querySelector("input");
      probe.textContent = ((field ? field.value : (cell.querySelector(".cue-name-text") || cell).textContent) || "").trim();
      const pad = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
      widest = Math.max(widest, probe.offsetWidth + pad + (cell.tagName === "TH" ? 12 : 4));
    });
    probe.remove();
    const def = CUE_COLUMNS[index];
    _cueColWidths[key] = Math.ceil(Math.max(def.min, Math.min(CUE_COLUMN_MAX, widest)));
    _applyCueColumns();
    _saveCueColumns();
  }

  function _setupCueColumns(table) {
    const colgroup = document.createElement("colgroup");
    CUE_COLUMNS.forEach((def) => {
      const col = document.createElement("col");
      col.dataset.col = def.key;
      colgroup.appendChild(col);
    });
    table.insertBefore(colgroup, table.firstChild);

    Array.from(table.tHead.rows[0].cells).forEach((th, index) => {
      const def = CUE_COLUMNS[index];
      th.dataset.col = def.key;
      if (def.key === "status") return;

      // Das uebersetzte Label liegt in einem eigenen Span: translator.apply() setzt textContent
      // und wuerde sonst den Resizer-Griff im Kopf loeschen.
      if (th.dataset.i18n) {
        const label = document.createElement("span");
        label.className = "cue-th-label";
        label.dataset.i18n = th.dataset.i18n;
        label.textContent = th.textContent;
        th.removeAttribute("data-i18n");
        th.textContent = "";
        th.appendChild(label);
      }

      const handle = document.createElement("span");
      handle.className = "cue-col-resizer";
      th.appendChild(handle);

      handle.addEventListener("pointerdown", (event) => {
        event.preventDefault();
        event.stopPropagation();
        handle.setPointerCapture(event.pointerId);
        handle.classList.add("is-dragging");
        const startX = event.clientX;
        const startWidth = _cueColWidth(def.key);
        const move = (ev) => {
          _cueColWidths[def.key] = Math.max(def.min, Math.min(CUE_COLUMN_MAX, startWidth + ev.clientX - startX));
          _applyCueColumns();
        };
        const stop = () => {
          handle.removeEventListener("pointermove", move);
          handle.removeEventListener("pointerup", stop);
          handle.removeEventListener("pointercancel", stop);
          handle.classList.remove("is-dragging");
          _saveCueColumns();
        };
        handle.addEventListener("pointermove", move);
        handle.addEventListener("pointerup", stop);
        handle.addEventListener("pointercancel", stop);
      });
      handle.addEventListener("dblclick", () => _autoFitCueColumn(table, def.key));

      // Doppelklick (Maus) bzw. Doppeltipp (Touch, siehe installDoubleTap) auf den Spaltenkopf: Breite an den Inhalt anpassen.
      th.addEventListener("dblclick", (event) => {
        if (!event.target.closest(".cue-col-resizer")) _autoFitCueColumn(table, def.key);
      });
    });
    _applyCueColumns(table);
  }

  const OPTIONAL_FLOAT_FIELDS = new Set(["fade_color", "delay_color", "fade_pos", "delay_pos", "fade_beam", "delay_beam", "fade_zoom", "delay_zoom"]);
  const FX_FADE_FIELDS = new Set(["fx_fade_in", "fx_fade_out"]);        // Effekt ein-/ausblenden: Zahl >= 0 (leer/0 = sofort)

  /** Welche Liste zeigt dieses Panel? Mit ausgeblendeter Listen-Auswahl die in den Eigenschaften gewaehlte (feste Zuordnung,
   *  wie beim Executor), sonst - und wenn die feste Liste nicht (mehr) existiert - die aktive Liste. */
  function _panelListId(panelEl) {
    if (panelEl && panelEl.dataset.showListSelect === "false" && panelEl.dataset.fixedList && _allCuelists[panelEl.dataset.fixedList]) {
      return panelEl.dataset.fixedList;
    }
    return _activeCuelistId;
  }

  function _currentCuelist(panelEl) {
    const id = _panelListId(panelEl);
    return id ? (_allCuelists[id] || null) : null;
  }

  /** Listen-Auswahl (Dropdown, "Liste loeschen", "+ Neue Liste") ein-/ausblenden; ausgeblendet bleibt nur die Button-Leiste. */
  function _applyListSelect(panelEl) {
    const show = panelEl.dataset.showListSelect !== "false";
    const row = panelEl.querySelector(".cuelist-listrow");
    if (row) row.hidden = !show;
    const add = panelEl.querySelector(".cuelist-toolbar__btn--new");
    if (add) add.hidden = !show;
  }

  function _readListConfig(panelEl, mc) {
    mc = mc || {};
    panelEl.dataset.showProgressBar = String(mc.show_progress_bar !== false);
    panelEl.dataset.showListSelect = String(mc.show_list_select !== false);
    panelEl.dataset.fixedList = mc.cuelist_id || "";
  }

  // ── Render ──────────────────────────────────────────────────────
  function _renderPanel(panelEl) {
    _applyListSelect(panelEl);
    const selectEl = panelEl.querySelector(".cuelist-select");
    if (selectEl) {
      const prevValue = selectEl.value;
      selectEl.innerHTML = "";
      Object.values(_allCuelists).forEach(cl => {
        const opt = document.createElement("option");
        opt.value = cl.id;
        opt.textContent = cl.name;
        selectEl.appendChild(opt);
      });
      selectEl.value = _activeCuelistId || prevValue || "";
    }

    const cl = _currentCuelist(panelEl);
    const tableWrap = panelEl.querySelector(".cuelist-table-wrap");
    const emptyEl = panelEl.querySelector(".cuelist-empty");
    const tbody = panelEl.querySelector(".cuelist-table tbody");

    if (!cl || !cl.cues.length) {
      if (tableWrap) tableWrap.hidden = true;
      if (emptyEl) { emptyEl.hidden = false; emptyEl.textContent = i18n("CUELIST_EMPTY"); }
      _updateActions(panelEl);
      return;
    }
    [..._sel].forEach((id) => { if (!cl.cues.some(c => c.id === id)) _sel.delete(id); });
    if (tableWrap) tableWrap.hidden = false;
    if (emptyEl) emptyEl.hidden = true;
    if (!tbody) return;

    const activeCueId = _activeCueIds[cl.id];
    // Naechster Cue (wird mit Go gestartet): der Cue nach dem aktiven, ohne aktiven der erste.
    const activeIndex = cl.cues.findIndex(c => c.id === activeCueId);
    // Am Listenende laeuft Go zum ersten Cue (kleinste Nummer > 0) um - die Vorschau zeigt das schon vorher.
    const firstCue = cl.cues.filter(c => c.number > 0).sort((a, b) => a.number - b.number)[0] || cl.cues[0];
    const nextCue = activeIndex < 0 ? cl.cues[0] : (cl.cues[activeIndex + 1] || firstCue);
    // Panel-Eigenschaft (Zahnrad -> Modul-Einstellungen): Standard an, kann
    // pro Panel-Instanz ausgeblendet werden (siehe onModuleConfigChanged).
    const showProgressBar = panelEl.dataset.showProgressBar !== "false";
    tbody.innerHTML = "";
    cl.cues.forEach(cue => {
      const tr = document.createElement("tr");
      const isActive = cue.id === activeCueId;
      const isNext = !!nextCue && cue.id === nextCue.id && !isActive;
      tr.className = "cue-row" + (isActive ? " cue-row--active" : "") + (isNext ? " cue-row--next" : "")
        + (_sel.has(cue.id) ? " cue-row--selected" : "");
      tr.dataset.cueId = cue.id;
      const triggerLabel = _triggerLabel(cue);
      // Der Ladebalken wird EXKLUSIV fuer den aktuell aktiven Cue gerendert -
      // inaktive Zeilen bekommen gar kein Balken-Markup (nicht nur per CSS
      // ausgeblendet), damit der Wechsel beim Triggern eines neuen Cues
      // sofort und eindeutig ist (siehe auch die .cue-row:not(--active)
      // Sicherheitsregel in style.css).
      const progressBarHtml = (isActive && showProgressBar)
        ? `<span class="cue-progress-bar"><span class="cue-progress-bar__fill"></span></span>`
        : "";
      // dot2-exakte Spaltenreihenfolge: Cue # -> Name -> Trigger -> Fade ->
      // Delay -> MIB -> Color Fade/Delay -> Pos Fade/Delay -> Beam Fade/
      // Delay -> CMD. Attribut-spezifische Zeiten sind optional (None =
      // "nutzt die allgemeine Fade/Delay-Zeit") - _fmtOptNum() zeigt dafuer
      // einen Gedankenstrich statt "null"/"0".
      tr.innerHTML = `
        <td class="fx-td cue-td--status"><span class="cue-status-dot${isActive ? " cue-status-dot--active" : isNext ? " cue-status-dot--next" : ""}"></span></td>
        <td class="fx-td cue-td--num" data-field="number">${_esc(_fmtNum(cue.number))}</td>
        <td class="fx-td cue-td--name" data-field="name">
          <span class="cue-name-text">${_esc(cue.name)}</span>
          ${progressBarHtml}
        </td>
        <td class="fx-td cue-td--trigger" data-field="trigger">${_esc(triggerLabel)}</td>
        <td class="fx-td cue-td--fade" data-field="fade">${_esc(_fmtNum(cue.fade))}</td>
        <td class="fx-td cue-td--fade cue-td--delay" data-field="delay"><input type="text" class="cue-delay-field" inputmode="decimal" autocomplete="off" autocorrect="off" spellcheck="false" value="${_esc(_fmtNum(cue.delay))}" title="${_esc(i18n("CUE_DELAY_SWIPE_TIP"))}" aria-label="${_esc(i18n("CUELIST_COL_DELAY"))}"></td>
        <td class="fx-td cue-td--mib" data-field="mib">${_esc(cue.mib || "Off")}</td>
        <td class="fx-td cue-td--fade" data-field="fade_color">${_esc(_fmtOptNum(cue.fade_color))}</td>
        <td class="fx-td cue-td--fade" data-field="delay_color">${_esc(_fmtOptNum(cue.delay_color))}</td>
        <td class="fx-td cue-td--fade" data-field="fade_pos">${_esc(_fmtOptNum(cue.fade_pos))}</td>
        <td class="fx-td cue-td--fade" data-field="delay_pos">${_esc(_fmtOptNum(cue.delay_pos))}</td>
        <td class="fx-td cue-td--fade" data-field="fade_beam">${_esc(_fmtOptNum(cue.fade_beam))}</td>
        <td class="fx-td cue-td--fade" data-field="delay_beam">${_esc(_fmtOptNum(cue.delay_beam))}</td>
        <td class="fx-td cue-td--fade" data-field="fade_zoom">${_esc(_fmtOptNum(cue.fade_zoom))}</td>
        <td class="fx-td cue-td--fade" data-field="delay_zoom">${_esc(_fmtOptNum(cue.delay_zoom))}</td>
        <td class="fx-td cue-td--fade" data-field="fx_fade_in">${_esc(_fmtNum(cue.fx_fade_in || 0))}</td>
        <td class="fx-td cue-td--fade" data-field="fx_fade_out">${_esc(_fmtNum(cue.fx_fade_out || 0))}</td>
        <td class="fx-td cue-td--cmd" data-field="cmd">${_esc(cue.cmd || "")}</td>
      `;
      const toggle = () => { if (_sel.has(cue.id)) _sel.delete(cue.id); else _sel.add(cue.id); _syncSelection(); };
      // Klick-/Auswahl-Logik wie die Fixture-Auswahl der Scheinwerfersteuerung (Tilegrid/Liste): Umschalt-Klick waehlt den
      // Bereich vom zuletzt angeklickten Eintrag bis hierher (rangeAdd: es wird hinzugefuegt, nichts abgewaehlt). Zusaetzlich
      // (die Cue-Liste hat anders als die Kacheln keinen Wisch-Auswahlmodus ohne Zusatztaste): Strg-Klick schaltet einzelne
      // Zeilen um, im Mehrfachmodus (Long-Press / Rechteck per Touch) schaltet jeder Tipp um. Ein einfacher Klick waehlt NUR
      // diese Zeile (ersetzt die bisherige Auswahl); ein Klick auf die freie Flaeche hebt die ganze Auswahl auf.
      // Die Zeilen bleiben bestehen (sonst ginge der zweite Tipp eines Doppeltipps ins Leere).
      tr.addEventListener("click", (e) => {
        if (Date.now() - _swipeEndedAt < 350) return;                 // Ende einer Wischgeste, kein Tipp
        if (e.target.closest(".cue-td-edit-input, .cue-delay-field")) return;
        const anchorIdx = cl.cues.findIndex((c) => c.id === _anchorCueId);
        const ownIdx = cl.cues.findIndex((c) => c.id === cue.id);
        if (e.shiftKey && anchorIdx >= 0) {
          const lo = Math.min(anchorIdx, ownIdx), hi = Math.max(anchorIdx, ownIdx);
          cl.cues.slice(lo, hi + 1).forEach((c) => _sel.add(c.id));
          _syncSelection();
          _anchorCueId = cue.id;
          return;
        }
        _anchorCueId = cue.id;
        if (e.ctrlKey || e.metaKey || _multi) { toggle(); return; }
        if (_sel.size === 1 && _sel.has(cue.id)) return;
        _sel.clear();
        _sel.add(cue.id);
        _syncSelection();
      });
      _attachDelayField(panelEl, cl, cue, tr.querySelector(".cue-delay-field"));
      tr.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        e.stopPropagation();
        // Long-Press (Touch): markiert die Zeile und startet den Mehrfachmodus. Ein zweiter Long-Press auf die allein
        // markierte Zeile oeffnet das Kontextmenue (Hierhin faden / Bearbeiten / Loeschen), die Maus (Rechtsklick) immer.
        if (window.__longPress && window.__longPress.suppress && !(_sel.size === 1 && _sel.has(cue.id))) {
          _multi = true;
          _sel.add(cue.id);
          _syncSelection();
          return;
        }
        _showContextMenu(cl.id, cue.id, e.clientX, e.clientY);
      });
      tr.querySelectorAll("[data-field]").forEach(cellEl => {
        if (cellEl.dataset.field === "delay") return;       // Delay ist ein Zahlenfeld mit Wischgeste
        cellEl.addEventListener("dblclick", () => _startInlineEdit(panelEl, cl, cue, cellEl, cellEl.dataset.field));
      });
      tbody.appendChild(tr);
    });
    _paintActiveBar(panelEl, cl.id);
    _syncFollowBar(panelEl, cl.id);
    _updateActions(panelEl);
  }

  // ── Delay: Zahlenfeld mit Wischgeste ─────────────────────────────────────────────────────────────────
  // Genau wie die Zahlenfelder der Position (Scheinwerfersteuerung): ein echtes <input> direkt auf dem Wert. Vertikal
  // wischen aendert ihn (hoch = mehr), Grob 2 px je 0,1 s, mit Umschalt (Maus) fein 4 px je 0,01 s, immer relativ zum
  // Wert bei Gestenbeginn. Unter 4 px Bewegung gilt es als Tippen und fokussiert das Feld zur normalen Eingabe.
  // Sind mehrere Zeilen markiert und gehoert die angefasste dazu, erhalten ALLE markierten Zeilen denselben Delta-Wert
  // (nicht denselben Zielwert); sonst wirkt es nur auf die angefasste Zeile.
  const DELAY_SWIPE = { coarse: { step: 0.1, px: 2 }, fine: { step: 0.01, px: 4 }, slop: 4 };
  const _round2 = (n) => Math.round(n * 100) / 100;
  let _gestureActive = false;      // waehrend einer Wischgeste wird die Tabelle nicht neu aufgebaut (das Feld muss bestehen bleiben)
  const _deferredPanels = new Set();

  function _endGesture() {
    _gestureActive = false;
    _deferredPanels.forEach((panelEl) => { if (panelEl.isConnected) _renderPanel(panelEl); });
    _deferredPanels.clear();
  }

  function _attachDelayField(panelEl, cl, cue, input) {
    const show = (v) => _fmtNum(v);
    // Zahleneingabe (Tippen)
    const commit = () => {
      const num = parseFloat(String(input.value).replace(",", "."));
      if (!Number.isFinite(num) || num < 0) { input.value = show(cue.delay); return; }
      const value = Math.round(num * 1000) / 1000;
      if (value !== Number(cue.delay)) {
        cue.delay = value;
        window.__panelAPI.sendToServer("update_cue", { cuelist_id: cl.id, cue_id: cue.id, delay: value });
      }
      input.value = show(value);
    };
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); input.blur(); }
      else if (e.key === "Escape") { input.value = show(cue.delay); input.blur(); }
    });
    input.addEventListener("blur", commit);
    input.addEventListener("focus", () => { setTimeout(() => input.select(), 0); });

    // Wischgeste (Maus und Touch ueber Pointer-Events); Bewegung und Loslassen werden am document verfolgt
    let drag = null;
    let lastSend = 0;
    const cell = input.closest("td");
    const apply = (force) => {
      const { step, px } = drag.fine ? DELAY_SWIPE.fine : DELAY_SWIPE.coarse;
      const steps = Math.round((drag.y0 - drag.lastY) / px);
      const updates = [];
      drag.group.forEach((c) => {
        const value = Math.max(0, _round2(drag.starts.get(c.id) + steps * step));
        c.delay = value;
        const field = panelEl.querySelector('.cue-row[data-cue-id="' + c.id + '"] .cue-delay-field');
        if (field) field.value = show(value);
        updates.push({ cue_id: c.id, delay: value });
      });
      const now = performance.now();
      if (force || now - lastSend >= 60) {
        lastSend = now;
        window.__panelAPI.sendToServer("update_cues", { cuelist_id: cl.id, updates });
      }
    };
    const onMove = (e) => {
      if (!drag || e.pointerId !== drag.id) return;
      drag.lastY = e.clientY;
      if (!drag.moved) {
        if (Math.abs(drag.y0 - e.clientY) < DELAY_SWIPE.slop) return;
        drag.moved = true;
        _gestureActive = true;
        cell.classList.add("cue-td--swiping");
        input.blur();
        try { input.setPointerCapture(e.pointerId); } catch (err) { /* Zeiger schon weg */ }
      }
      if (e.cancelable) e.preventDefault();
      apply(false);
    };
    const finish = (e) => {
      if (!drag || e.pointerId !== drag.id) return;
      const d = drag;
      document.removeEventListener("pointermove", onMove, true);
      document.removeEventListener("pointerup", finish, true);
      document.removeEventListener("pointercancel", finish, true);
      cell.classList.remove("cue-td--swiping");
      if (d.moved) {
        apply(true);                      // abschliessender Wert garantiert
        drag = null;
        _swipeEndedAt = Date.now();
        _endGesture();
      } else {
        drag = null;
        if (e.type === "pointerup") input.focus();      // Tippen ohne Wischen: Zahl eingeben
      }
    };
    input.addEventListener("pointerdown", (e) => {
      if (e.pointerType === "mouse" && e.button !== 0) return;
      if (typeof isEditMode !== "undefined" && isEditMode) return;
      const group = _sel.size > 1 && _sel.has(cue.id) ? cl.cues.filter(c => _sel.has(c.id)) : [cue];
      drag = { id: e.pointerId, y0: e.clientY, lastY: e.clientY, moved: false, fine: e.shiftKey, group,
               starts: new Map(group.map(c => [c.id, Number(c.delay) || 0])) };
      document.addEventListener("pointermove", onMove, true);
      document.addEventListener("pointerup", finish, true);
      document.addEventListener("pointercancel", finish, true);
    });
  }

  // ── Rechteck-Auswahl (Marquee) - dieselbe Mechanik und Optik wie das Lasso der Scheinwerfersteuerung ───────────────────
  // Ziehen zeichnet ein gelbes Auswahl-Rechteck (.fxprog-lasso, begrenzt auf das Panel); alle Zeilen, die es beruehrt,
  // zeigen waehrenddessen live eine Vorschau und werden beim Loslassen markiert (reines Hinzufuegen, nie Toggle). Maus:
  // links druecken und ziehen (auch ab der freien Flaeche unter den Zeilen). Touch: ~350 ms ruhig halten (der Rahmen
  // leuchtet auf), dann ziehen - ohne Halten scrollt der Finger die Liste wie bisher. Rechtsklick (Maus) und Long-Press
  // ohne Bewegung (Touch) oeffnen weiterhin das Kontextmenue: die Geste startet nur mit der linken Maustaste und
  // verlangt eine Bewegung.
  const ROW_SWIPE = { holdMs: 350, slopTouch: 10, slopMouse: 4 };
  let _rowSwipe = null;

  function _attachRowSwipe(tableWrap) {
    const rows = () => [...tableWrap.querySelectorAll(".cue-row")];
    const clearPreview = () => tableWrap.querySelectorAll(".cue-row--preview").forEach((r) => r.classList.remove("cue-row--preview"));

    function finish(commit) {
      const g = _rowSwipe;
      if (!g) return;
      _rowSwipe = null;
      clearTimeout(g.timer);
      document.removeEventListener("pointermove", onMove, true);
      document.removeEventListener("pointerup", onUp, true);
      document.removeEventListener("pointercancel", onCancel, true);
      document.removeEventListener("selectstart", noSelect, true);
      tableWrap.classList.remove("cuelist--arming", "cuelist--swiping");
      if (g.captured) {
        try { tableWrap.releasePointerCapture(g.id); } catch (err) { /* schon frei */ }
        document.body.classList.remove("lasso-active");
        document.querySelectorAll(".lasso-owner").forEach((panel) => panel.classList.remove("lasso-owner"));
      }
      if (g.box) g.box.remove();
      const ids = g.ids;
      clearPreview();
      if (g.moved) {
        _swipeEndedAt = Date.now();
        if (commit && ids.length) {
          ids.forEach((id) => _sel.add(id));
          if (g.touch) _multi = true;                    // wie nach einem Long-Press: weitere Tipps markieren/entmarkieren
          _syncSelection();
        }
        _endGesture();
      }
    }
    const onUp = (e) => { if (_rowSwipe && e.pointerId === _rowSwipe.id) finish(true); };
    const onCancel = (e) => { if (_rowSwipe && e.pointerId === _rowSwipe.id) finish(false); };
    const noSelect = (e) => { if (_rowSwipe && _rowSwipe.active) e.preventDefault(); };

    function onMove(e) {
      const g = _rowSwipe;
      if (!g || e.pointerId !== g.id) return;
      const dist = Math.hypot(e.clientX - g.x0, e.clientY - g.y0);
      if (!g.active) {                                   // Finger bewegt sich vor dem Scharfschalten: normales Scrollen
        if (g.timer && dist > ROW_SWIPE.slopTouch) { clearTimeout(g.timer); g.timer = null; }
        return;
      }
      if (!g.moved) {
        if (dist < (g.touch ? ROW_SWIPE.slopTouch : ROW_SWIPE.slopMouse)) return;
        g.moved = true;
        _gestureActive = true;                           // keine Neuaufbauten der Tabelle waehrend der Geste
        tableWrap.classList.add("cuelist--swiping");
        tableWrap.classList.remove("cuelist--arming");
        // Die Geste gehoert diesem Panel: Zeiger festhalten, Nachbar-Panels sperren (wie beim Lasso der Fixture-Raster)
        g.captured = true;
        try { tableWrap.setPointerCapture(g.id); } catch (err) { /* Zeiger schon weg */ }
        document.body.classList.add("lasso-active");
        const owner = tableWrap.closest(".workspace-panel");
        if (owner) owner.classList.add("lasso-owner");
        g.box = document.createElement("div");
        g.box.className = "fxprog-lasso cuelist-marquee";
        document.body.appendChild(g.box);
      }
      if (e.cancelable) e.preventDefault();
      const panelBox = (tableWrap.closest(".workspace-panel") || tableWrap).getBoundingClientRect();
      const px = Math.max(panelBox.left, Math.min(panelBox.right, e.clientX));
      const py = Math.max(panelBox.top, Math.min(panelBox.bottom, e.clientY));
      const left = Math.min(g.x0, px), right = Math.max(g.x0, px);
      const top = Math.min(g.y0, py), bottom = Math.max(g.y0, py);
      g.box.style.left = left + "px";
      g.box.style.top = top + "px";
      g.box.style.width = (right - left) + "px";
      g.box.style.height = (bottom - top) + "px";
      const hit = [];
      rows().forEach((row) => {
        const r = row.getBoundingClientRect();
        const on = r.top < bottom && r.bottom > top && r.left < right && r.right > left;
        row.classList.toggle("cue-row--preview", on);
        if (on) hit.push(row.dataset.cueId);
      });
      g.ids = hit;
    }

    tableWrap.addEventListener("pointerdown", (e) => {
      if (!e.isPrimary || (e.pointerType === "mouse" && e.button !== 0)) return;
      if (typeof isEditMode !== "undefined" && isEditMode) return;
      if (!e.target.closest || e.target.closest("thead, th, input, button, select, textarea, .cue-delay-field, .cue-td-edit-input, .cue-col-resizer")) return;
      if (_rowSwipe) finish(false);
      const touch = e.pointerType !== "mouse";
      const g = _rowSwipe = { id: e.pointerId, x0: e.clientX, y0: e.clientY, touch, active: !touch, moved: false, ids: [], timer: null, box: null, captured: false };
      if (touch) {
        g.timer = setTimeout(() => {
          g.timer = null;
          if (_rowSwipe !== g) return;
          g.active = true;
          tableWrap.classList.add("cuelist--arming");
          if (navigator.vibrate) { try { navigator.vibrate(8); } catch (err) { /* egal */ } }
        }, ROW_SWIPE.holdMs);
      }
      document.addEventListener("pointermove", onMove, true);
      document.addEventListener("pointerup", onUp, true);
      document.addEventListener("pointercancel", onCancel, true);
      document.addEventListener("selectstart", noSelect, true);
    });
  }
  // Browser-Scrollen waehrend einer scharfen/laufenden Wischgeste verhindern (Touch)
  document.addEventListener("touchmove", (e) => {
    if (_rowSwipe && _rowSwipe.touch && (_rowSwipe.active || _rowSwipe.moved) && e.cancelable) e.preventDefault();
  }, { passive: false });

  // ── Inline-Editing (Doppelklick auf Name/Cue #/Fade/Attribut-Zeiten/CMD sowie Trigger und MIB als Textfeld;
  // Delay ist ein eigenes Zahlenfeld mit Wischgeste) ───────────────────
  /** Trigger-Eingabe: "go" / "follow" (Gross-/Kleinschreibung egal, auch der uebersetzte Anzeigetext) -> Schluessel, sonst null. */
  function _parseTrigger(text) {
    const t = String(text).trim().toLowerCase();
    if (t === "go" || t === String(i18n("CUE_TRIGGER_GO")).toLowerCase()) return "go";
    if (t === "follow" || t === String(i18n("CUE_TRIGGER_FOLLOW")).toLowerCase()) return "follow";
    return null;
  }

  /** Anzeige des Ausloesers: Go | Follow | "TC 00:00:04.300" (Timecode-Ausloeser mit seiner Zeit). */
  function _triggerLabel(cue) {
    if (cue.trigger === "follow") return i18n("CUE_TRIGGER_FOLLOW");
    if (cue.trigger === "timecode") return "TC " + (window.OCTimecode ? window.OCTimecode.fmt(cue.timecode_ms || 0) : String(cue.timecode_ms || 0));
    return i18n("CUE_TRIGGER_GO");
  }

  /** Eingabe im Ausloeser-Feld: "go", "follow", "tc" / "timecode" (+ optional Zeit, z. B. "tc 4.3") oder nur eine Zeit (bei einem
   *  Timecode-Cue). Ergebnis { trigger, timecode_ms? } oder null (ungueltig). */
  function _parseTriggerEdit(text, cue) {
    const raw = String(text).trim();
    const simple = _parseTrigger(raw);
    if (simple) return { trigger: simple };
    const match = raw.match(/^(?:timecode|tc)\s*(.*)$/i);
    const timeText = match ? match[1] : (cue && cue.trigger === "timecode" ? raw : null);
    if (timeText === null || !window.OCTimecode) return null;
    if (timeText === "") return { trigger: "timecode", timecode_ms: cue && cue.trigger === "timecode" ? (cue.timecode_ms || 0) : 0 };
    const ms = window.OCTimecode.parse(timeText);
    return ms === null ? null : { trigger: "timecode", timecode_ms: ms };
  }

  /** MIB-Eingabe: On/Off, 1/0, True/False (egal wie geschrieben) sowie Auto -> "On" | "Off" | "Auto", sonst null. */
  function _parseMib(text) {
    const t = String(text).trim().toLowerCase();
    if (t === "on" || t === "1" || t === "true") return "On";
    if (t === "off" || t === "0" || t === "false") return "Off";
    if (t === "auto") return "Auto";
    return null;
  }

  function _startInlineEdit(panelEl, cl, cue, cellEl, field) {
    if (cellEl.classList.contains("cue-td--editing")) return;
    const originalHTML = cellEl.innerHTML;
    const isChoice = field === "trigger" || field === "mib";           // Textfeld mit festen Werten (normalisiert)
    const isText = field === "name" || field === "cmd" || isChoice;
    const isOptional = OPTIONAL_FLOAT_FIELDS.has(field);
    const currentValue = field === "trigger" ? _triggerLabel(cue)
      : field === "mib" ? (cue.mib || "Off")
      : (isOptional ? (cue[field] != null ? cue[field] : "") : FX_FADE_FIELDS.has(field) ? (cue[field] || 0) : cue[field]);

    cellEl.classList.add("cue-td--editing");
    cellEl.innerHTML = "";
    const input = document.createElement("input");
    input.className = "cue-td-edit-input";
    if (isText) {
      input.type = "text";
      input.maxLength = isChoice ? 24 : field === "cmd" ? 200 : 80;
      if (isChoice) {                                 // feste Werte, freie Eingabe - bewusst ohne Browser-Vorschlaege
        input.autocomplete = "off";
        input.setAttribute("autocorrect", "off");
        input.setAttribute("autocapitalize", "off");
        input.spellcheck = false;
        input.name = "oc-cue-" + field + "-" + Math.random().toString(36).slice(2, 8);
      }
    } else {
      input.type = "number";
      input.step = field === "number" ? "0.001" : "0.1";
      if (field !== "number") input.min = "0";
      if (isOptional) {
        input.dataset.i18nPlaceholder = "CUE_FIELD_DEFAULT";
        input.placeholder = i18n("CUE_FIELD_DEFAULT");
      }
    }
    input.value = currentValue;
    cellEl.appendChild(input);
    input.focus();
    input.select();

    let settled = false;
    const commit = () => {
      if (settled) return;
      settled = true;
      const raw = input.value;
      let changed = false;
      const msg = { cuelist_id: cl.id, cue_id: cue.id };
      if (isChoice && field === "trigger") {
        const parsed = _parseTriggerEdit(raw, cue);
        if (parsed === null) {
          cellEl.classList.remove("cue-td--editing");
          cellEl.innerHTML = originalHTML;
          _showToast("CUE_ERR_TRIGGER", "warn", 3500);
          return;
        }
        if (parsed.trigger !== (cue.trigger || "go") || (parsed.trigger === "timecode" && parsed.timecode_ms !== cue.timecode_ms)) {
          msg.trigger = parsed.trigger;
          if (parsed.trigger === "timecode") msg.timecode_ms = parsed.timecode_ms;
          changed = true;
        }
      } else if (isChoice) {
        const parsed = _parseMib(raw);
        if (parsed === null) {                                       // ungueltig: Zelle bleibt unveraendert, kurze Meldung
          cellEl.classList.remove("cue-td--editing");
          cellEl.innerHTML = originalHTML;
          _showToast("CUE_ERR_MIB", "warn", 3500);
          return;
        }
        if (parsed !== (cue.mib || "Off")) { msg[field] = parsed; changed = true; }
      } else if (field === "name") {
        const trimmed = raw.trim();
        if (trimmed && trimmed !== cue.name) { msg.name = trimmed; changed = true; }
      } else if (field === "cmd") {
        const trimmed = raw.trim();
        if (trimmed !== (cue.cmd || "")) { msg.cmd = trimmed; changed = true; }
      } else if (isOptional) {
        const trimmed = raw.trim();
        if (trimmed === "") {
          if (cue[field] != null) { msg[field] = null; changed = true; }
        } else {
          const num = parseFloat(trimmed);
          if (!isNaN(num) && num !== cue[field]) { msg[field] = num; changed = true; }
        }
      } else {
        const num = parseFloat(raw);
        if (!isNaN(num) && num !== cue[field]) { msg[field] = num; changed = true; }
      }
      if (changed) {
        window.__panelAPI.sendToServer("update_cue", msg);
        // Optimistisches lokales Update: sofortiges visuelles Feedback statt
        // auf den naechsten cuelists_changed-Broadcast zu warten.
        if (field !== "number") cue[field] = Object.prototype.hasOwnProperty.call(msg, field) ? msg[field] : cue[field];
        if (field === "trigger" && msg.trigger === "timecode") cue.timecode_ms = msg.timecode_ms;
        _renderPanel(panelEl);
      } else {
        cellEl.classList.remove("cue-td--editing");
        cellEl.innerHTML = originalHTML;
      }
    };
    const cancel = () => {
      if (settled) return;
      settled = true;
      cellEl.classList.remove("cue-td--editing");
      cellEl.innerHTML = originalHTML;
    };
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); commit(); }
      else if (e.key === "Escape") { e.preventDefault(); cancel(); }
    });
    input.addEventListener("blur", commit);
  }

  // ── Toolbar actions ────────────────────────────────────────────
  const _sameNumber = (a, b) => Math.abs(a - b) < 1e-6;

  function _parseNumber(text) {
    const n = Number(String(text).trim().replace(",", "."));
    return String(text).trim() !== "" && Number.isFinite(n) && n >= 0 ? Math.round(n * 1000) / 1000 : null;
  }

  /** Vorschlag fuer die Nummer: am Ende die naechste ganze Zahl, nach einem Cue eine freie Nummer zwischen ihm und
   *  seinem Nachfolger (ganze Zahl, wenn Platz ist, sonst die Mitte). null = zwischen den Cues ist kein Platz. */
  function _suggestNumber(cl, position, afterId) {
    const cues = cl.cues;
    if (position === "end") return cues.length ? Math.floor(cues[cues.length - 1].number) + 1 : 1;
    if (position === "after") {
      const idx = cues.findIndex(c => c.id === afterId);
      if (idx < 0) return null;
      const lower = cues[idx].number;
      const upper = idx + 1 < cues.length ? cues[idx + 1].number : null;
      const whole = Math.floor(lower) + 1;
      if (upper === null || whole < upper) return whole;
      const mid = Math.round(((lower + upper) / 2) * 1000) / 1000;
      return mid > lower && mid < upper ? mid : null;
    }
    return null;
  }

  /** Meldet, was an der Eingabe nicht stimmt ("" = in Ordnung); `info` weist auf eine bestehende Nummer hin. */
  function _validateStore(cl, position, afterId, text) {
    const n = _parseNumber(text);
    if (n === null) return { error: i18n("CUE_STORE_ERR_INVALID") };
    const existing = cl.cues.find(c => _sameNumber(c.number, n));
    if (existing) return { n, info: i18n("CUE_STORE_HINT_EXISTS").replace("{n}", _fmtNum(n)).replace("{name}", existing.name) };
    if (position === "end" && cl.cues.length && n <= cl.cues[cl.cues.length - 1].number) {
      return { error: i18n("CUE_STORE_ERR_RANGE_END").replace("{lower}", _fmtNum(cl.cues[cl.cues.length - 1].number)) };
    }
    if (position === "after") {
      const idx = cl.cues.findIndex(c => c.id === afterId);
      const lower = idx >= 0 ? cl.cues[idx].number : 0;
      const upper = idx >= 0 && idx + 1 < cl.cues.length ? cl.cues[idx + 1].number : null;
      if (!(n > lower && (upper === null || n < upper))) {
        return { error: upper === null ? i18n("CUE_STORE_ERR_RANGE_END").replace("{lower}", _fmtNum(lower))
          : i18n("CUE_STORE_ERR_RANGE").replace("{lower}", _fmtNum(lower)).replace("{upper}", _fmtNum(upper)) };
      }
    }
    return { n, info: "" };
  }

  /** Dialog "Cue speichern": Position, Nummer, Name. Liefert {number, position, after_cue_id, name} oder null. */
  function _askStore(cl) {
    const posEl = document.getElementById("cue-store-position");
    const numEl = document.getElementById("cue-store-number");
    const nameEl = document.getElementById("cue-store-name");
    const hintEl = document.getElementById("cue-store-hint");
    const okEl = document.getElementById("cue-store-confirm");
    posEl.innerHTML = "";
    const addOpt = (value, label) => { const o = document.createElement("option"); o.value = value; o.textContent = label; posEl.appendChild(o); };
    addOpt("free", i18n("CUE_STORE_POS_FREE"));
    const last = cl.cues[cl.cues.length - 1];
    addOpt("end", last ? i18n("CUE_STORE_POS_END").replace("{n}", _fmtNum(last.number)) : i18n("CUE_STORE_POS_END_EMPTY"));
    cl.cues.forEach(c => addOpt("after:" + c.id, i18n("CUE_STORE_POS_AFTER").replace("{n}", _fmtNum(c.number)).replace("{name}", c.name)));
    const selected = _singleId() ? cl.cues.find(c => c.id === _singleId()) : null;
    // Standard: "Frei" - die Nummer bestimmt die Position. Vorbelegt mit der naechsten ganzen Zahl (bei markiertem Cue mit dessen Nummer: speichert auf ihn).
    posEl.value = "free";
    numEl.value = selected ? _fmtNumPlain(selected.number) : _fmtNumPlain(_suggestNumber(cl, "end"));
    nameEl.value = "";
    let touchedNumber = !!selected;

    const state = () => {
      const v = posEl.value;
      return v.startsWith("after:") ? { position: "after", afterId: v.slice(6) } : { position: v, afterId: null };
    };
    const refresh = () => {
      const { position, afterId } = state();
      const result = _validateStore(cl, position, afterId, numEl.value);
      hintEl.textContent = result.error || result.info || "";
      hintEl.classList.toggle("cue-store__hint--error", !!result.error);
      hintEl.hidden = !hintEl.textContent;
      okEl.disabled = !!result.error;
      // Vorschau des Namens, der ohne Eingabe vergeben wird (wie der Server: "Cue <Nummer>")
      nameEl.placeholder = result.n !== undefined ? "Cue " + _fmtNumPlain(result.n) : "";
      return result;
    };
    posEl.onchange = () => {
      const { position, afterId } = state();
      if (position !== "free") {                      // Ende / nach Cue X: passende freie Nummer vorschlagen
        const suggestion = _suggestNumber(cl, position, afterId);
        numEl.value = suggestion === null ? "" : _fmtNumPlain(suggestion);
        touchedNumber = false;
      }
      refresh();
    };
    numEl.oninput = () => { touchedNumber = true; refresh(); };
    refresh();
    setTimeout(() => { numEl.focus(); numEl.select(); }, 60);
    return _modalResult("cue-store", null, (finish, listen) => {
      const accept = () => {
        const result = refresh();
        if (result.error) return;
        const { position, afterId } = state();
        finish({ number: result.n, position, after_cue_id: afterId, name: nameEl.value.trim() });
      };
      listen(okEl, "click", accept);
      listen(numEl, "keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); accept(); } });
      listen(nameEl, "keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); accept(); } });
    });
  }

  // Zahl fuer ein Eingabefeld: Punkt als Dezimaltrenner, ohne Tausendertrenner (der Nutzer darf auch ein Komma tippen).
  function _fmtNumPlain(n) { return n === null || n === undefined ? "" : String(Math.round(Number(n) * 1000) / 1000); }

  /** Rueckfrage bei bestehender Nummer: "merge" | "overwrite" | null (Abbrechen). */
  function _askConflict(number, name, bodyKey) {
    document.getElementById("cue-conflict-body").textContent =
      i18n(bodyKey || "CUE_CONFLICT_BODY").replace("{n}", _fmtNum(number)).replace("{name}", name || "");
    return _modalResult("cue-conflict", null, (finish, listen) => {
      listen(document.getElementById("cue-conflict-merge"), "click", () => finish("merge"));
      listen(document.getElementById("cue-conflict-overwrite"), "click", () => finish("overwrite"));
    });
  }

  function _sendStore(msg) {
    _lastStore = msg;
    window.__panelAPI.sendToServer("save_cue", msg);
    // Optimistisches Clear: die gesicherten Werte sind jetzt im Cue - die rote "touched"-Markierung verschwindet sofort
    const PS = window.ProgrammerState;
    if (PS) PS.clearTouched(msg.fixture_values || {});
  }

  /** "Cue speichern": Dialog fuer Position/Nummer/Name; bei bestehender Nummer fragt ein zweiter Dialog nach. */
  async function _saveCue(panelEl) {
    const cl = _currentCuelist(panelEl);
    if (!cl) return;
    const choice = await _askStore(cl);
    if (!choice) return;
    const PS = window.ProgrammerState;
    const msg = {
      cuelist_id: cl.id, fixture_values: PS ? PS.getCueSnapshot() : {},    // leer ist erlaubt: der Server ergaenzt Effekte
      number: choice.number, position: choice.position, after_cue_id: choice.after_cue_id,
    };
    if (choice.name) msg.name = choice.name;
    const existing = cl.cues.find(c => _sameNumber(c.number, choice.number));
    if (existing) {
      const mode = await _askConflict(existing.number, existing.name);
      if (!mode) return;
      msg.mode = mode;
    }
    _sendStore(msg);
  }

  /** "Aktualisieren": aktive Cue mit den aktuellen Werten, ohne Store-Dialog; Modus Normal / Nur diese Cue. */
  async function _updateCue(panelEl) {
    const cl = _currentCuelist(panelEl);
    const cue = cl && cl.cues.find(c => c.id === _activeCueIds[cl.id]);
    if (!cue) { _showToast("CUE_ERR_NO_ACTIVE", "warn", 3500); return; }
    document.getElementById("cue-update-body").textContent =
      i18n("CUE_UPDATE_BODY").replace("{n}", _fmtNum(cue.number)).replace("{name}", cue.name);
    const mode = await _modalResult("cue-update", null, (finish, listen) => {
      listen(document.getElementById("cue-update-normal"), "click", () => finish("normal"));
      listen(document.getElementById("cue-update-only"), "click", () => finish("only"));
    });
    if (!mode) return;
    const PS = window.ProgrammerState;
    const fixtureValues = PS ? PS.getCueSnapshot() : {};
    window.__panelAPI.sendToServer("update_active_cue", { cuelist_id: cl.id, mode, fixture_values: fixtureValues });
    if (PS) PS.clearTouched(fixtureValues);
  }

  function _editSelected(panelEl) {
    const cl = _currentCuelist(panelEl);
    if (cl && _singleId()) _openEditDialog(cl.id, _singleId());
  }

  function _deleteSelected(panelEl) {
    const cl = _currentCuelist(panelEl);
    if (!cl) return;
    const ids = cl.cues.filter(c => _sel.has(c.id)).map(c => c.id);
    if (ids.length > 1) _confirmDeleteCues(cl.id, ids);       // mehrere: eine Sammel-Bestaetigung
    else if (ids.length === 1) _confirmDeleteCue(cl.id, ids[0]);
  }

  /** Ganze Cue-Liste loeschen (nach Bestaetigung). Executor mit dieser Liste fallen auf die aktive Liste zurueck. */
  function _deleteList(panelEl) {
    const cl = _currentCuelist(panelEl);
    if (!cl) return;
    _pendingDelete = { cuelistId: cl.id, wholeList: true };
    const title = document.getElementById("cue-delete-confirm-title");
    if (title) { title.dataset.i18n = "CUELIST_DELETE_LIST_TITLE"; title.textContent = i18n("CUELIST_DELETE_LIST_TITLE"); }
    const body = document.getElementById("cue-delete-confirm-body");
    if (body) body.textContent = i18n("CUELIST_DELETE_LIST_BODY").replace("{name}", cl.name).replace("{n}", String(cl.cues.length));
    Modal.open("cue-delete-confirm");
  }

  function _confirmDeleteCues(cuelistId, cueIds) {
    _pendingDelete = { cuelistId, cueIds };
    const title = document.getElementById("cue-delete-confirm-title");
    if (title) { title.dataset.i18n = "CUE_DELETE_MULTI_TITLE"; title.textContent = i18n("CUE_DELETE_MULTI_TITLE"); }   // data-i18n: Modal.open() uebersetzt neu
    const body = document.getElementById("cue-delete-confirm-body");
    if (body) body.textContent = i18n("CUE_DELETE_MULTI_BODY").replace("{n}", String(cueIds.length));
    Modal.open("cue-delete-confirm");
  }

  /** Ergebnisse des Servers: Hinweise und Rueckfragen (Konflikt bei bestehender Nummer). */
  async function _onResult(p) {
    const n = p.number !== undefined ? _fmtNum(p.number) : "";
    if (p.ok) {
      const key = { created: "CUE_TOAST_STORED", merged: "CUE_TOAST_MERGED", overwritten: "CUE_TOAST_OVERWRITTEN",
        updated: p.mode === "only" ? "CUE_TOAST_UPDATED_ONLY" : "CUE_TOAST_UPDATED" }[p.code];
      if (key) _showToast(i18n(key).replace("{n}", n), "info", 2500);
      return;
    }
    if (p.code === "conflict" && _lastStore) {
      // Die Nummer wurde zwischenzeitlich (z.B. von einem anderen Geraet) vergeben: nachfragen und erneut senden
      const mode = await _askConflict(p.number, p.name);
      if (mode) _sendStore({ ..._lastStore, mode });
      return;
    }
    if (p.code === "renumber_conflict") {
      const mode = await _askConflict(p.number, p.name, "CUE_CONFLICT_RENUMBER_BODY");
      const owner = Object.values(_allCuelists).find(c => c.cues.some(x => x.id === p.cue_id));
      if (mode && owner) window.__panelAPI.sendToServer("update_cue", { cuelist_id: owner.id, cue_id: p.cue_id, number: p.number, on_conflict: mode });
      return;
    }
    const key = { empty: "CUE_ERR_EMPTY", no_active_cue: "CUE_ERR_NO_ACTIVE", invalid: "CUE_ERR_INVALID", out_of_bounds: "CUE_ERR_RANGE" }[p.code] || "CUE_ERR_GENERIC";
    _showToast(key, "warn", 4000);
  }

  window.__cueUi = { onResult: _onResult };

  function _openNewCuelistDialog() {
    const inp = document.getElementById("cuelist-new-name");
    if (inp) inp.value = "";
    Modal.open("cuelist-new");
  }

  const _cuelistNameTaken = (name, exceptId) => Object.values(_allCuelists).some((c) => c.id !== exceptId && c.name.trim().toLowerCase() === String(name).trim().toLowerCase());

  // ── Cue-Listen verwalten ──────────────────────────────────────────
  // Alle Listen in der Reihenfolge des Dropdowns, je mit Cues (aufklappbar): nach oben/unten schieben, umbenennen (Name anklicken), aktiv setzen, duplizieren, loeschen; oben eine neue Liste.
  // Namen sind eindeutig, jede Liste hat eine feste ID (die Verknuepfungen von Executoren und Cues laufen darueber, der Name ist nur die Anzeige).
  const _manageOpen = new Set();            // aufgeklappte Listen
  let _manageEditing = null;                // id der Liste, deren Name gerade bearbeitet wird

  function _openManageDialog() {
    _manageEditing = null;
    if (_activeCuelistId && !_manageOpen.size) _manageOpen.add(_activeCuelistId);
    _renderManage();
    Modal.open("cuelist-manage");
  }

  function _iconBtn(icon, titleKey, onClick, disabled, extra) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cm-btn" + (extra ? " " + extra : "");
    b.title = i18n(titleKey);
    b.setAttribute("aria-label", i18n(titleKey));
    b.appendChild(Icons.svg(icon));
    if (disabled) b.disabled = true;
    b.addEventListener("click", onClick);
    return b;
  }

  function _moveCuelist(id, delta) {
    const order = Object.keys(_allCuelists);
    const i = order.indexOf(id);
    const j = i + delta;
    if (i < 0 || j < 0 || j >= order.length) return;
    [order[i], order[j]] = [order[j], order[i]];
    window.__panelAPI.sendToServer("reorder_cuelists", { order });
  }

  function _commitRename(cl, value) {
    _manageEditing = null;
    const name = String(value || "").trim();
    if (name && name !== cl.name) {
      if (_cuelistNameTaken(name, cl.id)) { _showToast(i18n("CUELIST_DUPE_NAME").replace("{name}", name), "warn"); _renderManage(); return; }
      window.__panelAPI.sendToServer("rename_cuelist", { id: cl.id, name });
    }
    _renderManage();
  }

  async function _confirmDeleteList(cl) {
    const ok = await _askLayoutConfirm({ title: i18n("CUELIST_DELETE_LIST_TITLE"), body: i18n("CUELIST_DELETE_LIST_BODY").replace("{name}", cl.name).replace("{n}", String(cl.cues.length)), confirmKey: "CUELIST_DELETE_LIST" });
    if (!ok) return;
    _manageOpen.delete(cl.id);
    _sel.clear();
    _multi = false;
    window.__panelAPI.sendToServer("delete_cuelist", { id: cl.id });
  }

  function _renderManage() {
    const body = document.getElementById("cuelist-manage-body");
    if (!body) return;
    const lists = Object.values(_allCuelists);
    body.textContent = "";

    const addRow = document.createElement("div");
    addRow.className = "cm-add";
    const input = document.createElement("input");
    input.type = "text";
    input.maxLength = 80;
    input.className = "settings__text-input cm-add__input";
    input.id = "cuelist-manage-new";
    input.autocomplete = "off";
    input.placeholder = i18n("CUELIST_NAME_PLACEHOLDER");
    const addBtn = document.createElement("button");
    addBtn.type = "button";
    addBtn.className = "modal__button modal__button--primary cm-add__btn";
    addBtn.id = "cuelist-manage-add";
    addBtn.append(Icons.svg("plus"), document.createTextNode(i18n("CUELIST_NEW_SHORT")));
    const create = () => {
      const name = input.value.trim();
      if (name && _cuelistNameTaken(name)) { _showToast(i18n("CUELIST_DUPE_NAME").replace("{name}", name), "warn"); return; }
      window.__panelAPI.sendToServer("add_cuelist", { name });
      input.value = "";
    };
    addBtn.addEventListener("click", create);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") create(); });
    addRow.append(input, addBtn);
    body.appendChild(addRow);

    if (!lists.length) {
      const empty = document.createElement("div");
      empty.className = "cm-empty";
      empty.textContent = i18n("CUELIST_MANAGE_EMPTY");
      body.appendChild(empty);
      return;
    }
    const wrap = document.createElement("div");
    wrap.className = "cm-lists";
    lists.forEach((cl, index) => {
      const card = document.createElement("div");
      card.className = "cm-card" + (cl.id === _activeCuelistId ? " cm-card--active" : "");
      card.dataset.id = cl.id;
      const head = document.createElement("div");
      head.className = "cm-head";
      const open = _manageOpen.has(cl.id);
      const toggle = _iconBtn(open ? "chevron-down" : "chevron-right", open ? "CUELIST_MANAGE_COLLAPSE" : "CUELIST_MANAGE_EXPAND", () => { if (_manageOpen.has(cl.id)) _manageOpen.delete(cl.id); else _manageOpen.add(cl.id); _renderManage(); }, false, "cm-toggle");
      const order = document.createElement("span");
      order.className = "cm-index";
      order.textContent = String(index + 1);
      head.append(toggle, order);
      if (_manageEditing === cl.id) {
        const edit = document.createElement("input");
        edit.type = "text";
        edit.className = "settings__text-input cm-name-input";
        edit.maxLength = 80;
        edit.value = cl.name;
        edit.addEventListener("keydown", (e) => { if (e.key === "Enter") _commitRename(cl, edit.value); else if (e.key === "Escape") { _manageEditing = null; _renderManage(); } });
        edit.addEventListener("blur", () => { if (_manageEditing === cl.id) _commitRename(cl, edit.value); });
        head.appendChild(edit);
        setTimeout(() => { edit.focus(); edit.select(); }, 0);
      } else {
        const name = document.createElement("button");
        name.type = "button";
        name.className = "cm-name";
        name.title = i18n("CUELIST_MANAGE_RENAME");
        name.textContent = cl.name;
        name.addEventListener("click", () => { _manageEditing = cl.id; _renderManage(); });
        head.appendChild(name);
      }
      const meta = document.createElement("span");
      meta.className = "cm-meta";
      meta.textContent = i18n("CUELIST_MANAGE_CUES").replace("{n}", String(cl.cues.length));
      head.appendChild(meta);
      if (cl.id === _activeCuelistId) {
        const badge = document.createElement("span");
        badge.className = "cm-badge";
        badge.textContent = i18n("CUELIST_MANAGE_ACTIVE");
        head.appendChild(badge);
      }
      const acts = document.createElement("div");
      acts.className = "cm-acts";
      if (cl.id !== _activeCuelistId) acts.appendChild(_iconBtn("check", "CUELIST_MANAGE_MAKE_ACTIVE", () => window.__panelAPI.sendToServer("set_active_cuelist", { id: cl.id }), false, "cm-activate"));
      acts.append(
        _iconBtn("arrow-up", "CUELIST_MANAGE_UP", () => _moveCuelist(cl.id, -1), index === 0, "cm-up"),
        _iconBtn("arrow-down", "CUELIST_MANAGE_DOWN", () => _moveCuelist(cl.id, 1), index === lists.length - 1, "cm-down"),
        _iconBtn("edit", "CUELIST_MANAGE_RENAME", () => { _manageEditing = cl.id; _renderManage(); }, false, "cm-rename"),
        _iconBtn("copy", "CUELIST_MANAGE_DUPLICATE", () => window.__panelAPI.sendToServer("duplicate_cuelist", { id: cl.id }), false, "cm-dup"),
        _iconBtn("trash", "CUELIST_DELETE_LIST", () => _confirmDeleteList(cl), false, "cm-del cm-btn--danger"),
      );
      head.appendChild(acts);
      card.appendChild(head);
      if (open) {
        const table = document.createElement("table");
        table.className = "cm-cues";
        const cols = ["CUELIST_COL_NUMBER", "CUELIST_COL_NAME", "CUELIST_COL_TRIGGER", "CUELIST_COL_FADE", "CUELIST_COL_DELAY", "CUELIST_MANAGE_COL_FIXTURES", "CUELIST_MANAGE_COL_EFFECTS"];
        const thead = document.createElement("thead");
        const hr = document.createElement("tr");
        cols.forEach((k) => { const th = document.createElement("th"); th.textContent = i18n(k); hr.appendChild(th); });
        thead.appendChild(hr);
        table.appendChild(thead);
        const tb = document.createElement("tbody");
        if (!cl.cues.length) {
          const tr = document.createElement("tr");
          const td = document.createElement("td");
          td.colSpan = cols.length;
          td.className = "cm-cues__empty";
          td.textContent = i18n("CUELIST_EMPTY");
          tr.appendChild(td);
          tb.appendChild(tr);
        }
        for (const cue of cl.cues) {
          const tr = document.createElement("tr");
          const fxCount = Object.values(cue.fx || {}).filter((v) => v && Object.keys(v).length).length;
          [_fmtNum(cue.number), cue.name, _triggerLabel(cue), _fmtNum(cue.fade), _fmtNum(cue.delay), String(Object.keys(cue.fixture_values || {}).length), String(fxCount)].forEach((text, i) => {
            const td = document.createElement("td");
            td.textContent = text;
            if (i === 1) td.className = "cm-cues__name";
            tr.appendChild(td);
          });
          tb.appendChild(tr);
        }
        table.appendChild(tb);
        card.appendChild(table);
      }
      wrap.appendChild(card);
    });
    body.appendChild(wrap);
  }

  // ── Context menu ───────────────────────────────────────────────
  function _jumpToCue(cuelistId, cueId) {
    window.__panelAPI.sendToServer("jump_to_cue", { cuelist_id: cuelistId, cue_id: cueId });
  }

  function _showContextMenu(cuelistId, cueId, x, y) {
    ContextMenu.show(x, y, [
      { label: i18n("CUE_CTX_JUMP"), onClick: () => _jumpToCue(cuelistId, cueId) },
      { label: i18n("CUE_CTX_EDIT"), onClick: () => _openEditDialog(cuelistId, cueId) },
      { label: i18n("CUE_CTX_DELETE"), danger: true, onClick: () => _confirmDeleteCue(cuelistId, cueId) },
    ]);
  }

  function _hideContextMenu() {
    ContextMenu.hide();
  }

  // ── Edit dialog ────────────────────────────────────────────────
  function _openEditDialog(cuelistId, cueId) {
    const cl = _allCuelists[cuelistId];
    const cue = cl && cl.cues.find(c => c.id === cueId);
    if (!cue) return;
    _editingCuelistId = cuelistId;
    _editingCueId = cueId;
    const titleEl = document.getElementById("cue-edit-title");
    if (titleEl) titleEl.textContent = i18n("CUE_EDIT_TITLE").replace("{name}", cue.name);
    const set = (id, value) => { const el = document.getElementById(id); if (el) el.value = value; };
    set("cue-edit-name", cue.name);
    set("cue-edit-number", cue.number);
    set("cue-edit-trigger", cue.trigger || "go");
    set("cue-edit-timecode", window.OCTimecode ? window.OCTimecode.fmt(cue.timecode_ms || 0) : "");
    _syncTimecodeField();
    set("cue-edit-fade", cue.fade);
    set("cue-edit-delay", cue.delay);
    set("cue-edit-mib", cue.mib || "Off");
    // Attribut-spezifische Zeiten sind optional (null = Platzhalter leer
    // lassen -> "nutzt die allgemeine Fade/Delay-Zeit", siehe cue_engine.py).
    ["fade_color", "delay_color", "fade_pos", "delay_pos", "fade_beam", "delay_beam", "fade_zoom", "delay_zoom"].forEach(field => {
      set("cue-edit-" + field.replace("_", "-"), cue[field] != null ? cue[field] : "");
    });
    set("cue-edit-fx-fade-in", cue.fx_fade_in || "");
    set("cue-edit-fx-fade-out", cue.fx_fade_out || "");
    set("cue-edit-cmd", cue.cmd || "");
    Modal.open("cue-edit");
  }

  function _confirmDeleteCue(cuelistId, cueId) {
    const cl = _allCuelists[cuelistId];
    const cue = cl && cl.cues.find(c => c.id === cueId);
    if (!cue) return;
    // Ein leerer Cue (keine Werte, keine Effekte) geht ohne Nachfrage; sonst kurze Bestaetigung
    const empty = !Object.keys(cue.fixture_values || {}).length && !Object.keys(cue.fx || {}).length;
    if (empty) {
      window.__panelAPI.sendToServer("delete_cue", { cuelist_id: cuelistId, cue_id: cueId });
      return;
    }
    _pendingDelete = { cuelistId, cueId };
    const title = document.getElementById("cue-delete-confirm-title");
    if (title) { title.dataset.i18n = "CUE_DELETE_TITLE"; title.textContent = i18n("CUE_DELETE_TITLE"); }
    const body = document.getElementById("cue-delete-confirm-body");
    if (body && cue) body.textContent = i18n("CUE_DELETE_BODY").replace("{name}", cue.name);
    Modal.open("cue-delete-confirm");
  }

  /** Das Zeitfeld ist nur sichtbar, wenn der Ausloeser 'Timecode' gewaehlt ist. */
  function _syncTimecodeField() {
    const select = document.getElementById("cue-edit-trigger");
    const wrap = document.getElementById("cue-edit-timecode-wrap");
    if (select && wrap) wrap.hidden = select.value !== "timecode";
  }

  // ── Wire static dialogs (once) ─────────────────────────────────
  function _wireDialogs() {
    document.getElementById("cue-edit-trigger")?.addEventListener("change", _syncTimecodeField);
    const newConfirmBtn = document.getElementById("cuelist-new-confirm");
    if (newConfirmBtn) {
      newConfirmBtn.addEventListener("click", () => {
        const inp = document.getElementById("cuelist-new-name");
        const name = inp ? inp.value.trim() : "";                          // leer: der Server vergibt "Cue List 1", "Cue List 2" ...
        if (name && _cuelistNameTaken(name)) { _showToast(i18n("CUELIST_DUPE_NAME").replace("{name}", name), "warn"); return; }
        window.__panelAPI.sendToServer("add_cuelist", { name });
        Modal.close("cuelist-new");
      });
    }

    const editConfirmBtn = document.getElementById("cue-edit-confirm");
    if (editConfirmBtn) {
      editConfirmBtn.addEventListener("click", () => {
        if (!_editingCuelistId || !_editingCueId) return;
        const name = document.getElementById("cue-edit-name")?.value.trim() || "";
        const number = parseFloat(document.getElementById("cue-edit-number")?.value);
        const fade = parseFloat(document.getElementById("cue-edit-fade")?.value);
        const delay = parseFloat(document.getElementById("cue-edit-delay")?.value);
        const triggerVal = document.getElementById("cue-edit-trigger")?.value;
        const mibVal = document.getElementById("cue-edit-mib")?.value;
        const cmdVal = document.getElementById("cue-edit-cmd")?.value;
        const msg = { cuelist_id: _editingCuelistId, cue_id: _editingCueId };
        if (name) msg.name = name;
        if (!isNaN(number)) msg.number = number;
        if (!isNaN(fade)) msg.fade = fade;
        if (!isNaN(delay)) msg.delay = delay;
        if (triggerVal === "go" || triggerVal === "follow") msg.trigger = triggerVal;
        if (triggerVal === "timecode") {
          const tcMs = window.OCTimecode ? window.OCTimecode.parse(document.getElementById("cue-edit-timecode")?.value) : null;
          if (tcMs === null) { _showToast("TC_ERR_PARSE", "warn", 3500); document.getElementById("cue-edit-timecode")?.focus(); return; }   // Dialog bleibt offen
          msg.trigger = "timecode";
          msg.timecode_ms = tcMs;
        }
        if (mibVal === "Off" || mibVal === "Auto" || mibVal === "On") msg.mib = mibVal;
        if (cmdVal != null) msg.cmd = cmdVal.trim();
        // Attribut-spezifische Zeiten: leeres Feld -> null ("nutzt die
        // allgemeine Zeit"), sonst der eingegebene Wert.
        ["fade_color", "delay_color", "fade_pos", "delay_pos", "fade_beam", "delay_beam", "fade_zoom", "delay_zoom"].forEach(field => {
          const raw = document.getElementById("cue-edit-" + field.replace("_", "-"))?.value;
          if (raw === undefined) return;
          const trimmed = String(raw).trim();
          msg[field] = trimmed === "" ? null : parseFloat(trimmed);
        });
        // Effekt-Ein-/Ausblendzeit: leer = 0 (sofort).
        msg.fx_fade_in = parseFloat(document.getElementById("cue-edit-fx-fade-in")?.value) || 0;
        msg.fx_fade_out = parseFloat(document.getElementById("cue-edit-fx-fade-out")?.value) || 0;
        window.__panelAPI.sendToServer("update_cue", msg);
        Modal.close("cue-edit");
      });
    }

    const deleteConfirmBtn = document.getElementById("cue-delete-confirm-button");
    if (deleteConfirmBtn) {
      deleteConfirmBtn.addEventListener("click", () => {
        if (_pendingDelete) {
          if (_pendingDelete.wholeList) {
            window.__panelAPI.sendToServer("delete_cuelist", { id: _pendingDelete.cuelistId });
            _sel.clear();
            _multi = false;
          } else if (_pendingDelete.cueIds) {
            window.__panelAPI.sendToServer("delete_cues", { cuelist_id: _pendingDelete.cuelistId, cue_ids: _pendingDelete.cueIds });
            _pendingDelete.cueIds.forEach(id => _sel.delete(id));
          } else {
            window.__panelAPI.sendToServer("delete_cue", { cuelist_id: _pendingDelete.cuelistId, cue_id: _pendingDelete.cueId });
          }
          _pendingDelete = null;
        }
        Modal.close("cue-delete-confirm");
      });
    }
  }

  // ── Plugin registration ────────────────────────────────────────
  window.__panelPlugins.register({
    type: "cuelist",

    buildContent(panel) {
      const wrap = document.createElement("div");
      wrap.style.cssText = "display:flex;flex-direction:column;height:100%;overflow:hidden;";

      // Toolbar/Tabelle verwenden bewusst dieselben Klassen wie die
      // Scheinwerferliste (fx-toolbar/fx-btn/fx-table*) - 1:1 identisches
      // Erscheinungsbild statt einer eigenen, nur leicht abweichenden
      // Styling-Variante. cuelist-*/cue-*-Klassen bleiben als reine
      // Selektor-Hooks bzw. fuer tatsaechlich CueList-spezifische
      // Abweichungen (Status-Punkt, Trigger-Spalte, Akzentfarben) erhalten.
      const tb = document.createElement("div");
      tb.className = "fx-toolbar cuelist-toolbar";

      const selectEl = document.createElement("select");
      selectEl.className = "cuelist-select";
      selectEl.addEventListener("change", () => {
        window.__panelAPI.sendToServer("set_active_cuelist", { id: selectEl.value });
      });

      // Aktionen in einer Reihe, jede Taste gleich breit ueber die volle Panel-Breite (keine Wiedergabe-Tasten:
      // Go / Pause / Zurueck / Stopp liegen im Executor-Panel, die Liste verwaltet nur die Cues).
      const actions = document.createElement("div");
      actions.className = "cuelist-actions";
      const mkBtn = (cls, key, tipKey, onClick, disabled) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "fx-btn " + cls;
        // Text in einem Label (Auslassungspunkte dort): der Button selbst darf nicht abschneiden, sonst waere die unsichtbare
        // Trefferflaeche (44 px) ueber/unter der sichtbaren Taste weg.
        const labelEl = document.createElement("span");
        labelEl.className = "cuelist-btn__label";
        labelEl.dataset.i18n = key;
        labelEl.textContent = i18n(key);
        btn.appendChild(labelEl);
        btn.dataset.i18nTip = tipKey;
        btn.title = i18n(tipKey);
        if (disabled) btn.disabled = true;
        btn.addEventListener("click", () => onClick(btn.closest("[data-panel-type='cuelist']")));
        actions.appendChild(btn);
        return btn;
      };
      mkBtn("cuelist-toolbar__btn--new", "CUELIST_NEW", "CUELIST_NEW_TIP", _openNewCuelistDialog);
      mkBtn("cuelist-toolbar__btn--save", "CUELIST_SAVE_CUE", "CUELIST_SAVE_CUE_TIP", _saveCue);
      mkBtn("cuelist-toolbar__btn--update", "CUELIST_UPDATE", "CUELIST_UPDATE_TIP", _updateCue, true);
      mkBtn("cuelist-toolbar__btn--edit", "CUELIST_EDIT", "CUELIST_EDIT_TIP", _editSelected, true);
      mkBtn("cuelist-toolbar__btn--delete", "CUELIST_DELETE", "CUELIST_DELETE_TIP", _deleteSelected, true);

      // Zeile 1: Listenauswahl + "Verwalten" (alle Listen: Reihenfolge, umbenennen, duplizieren, loeschen, neu); Zeile 2: die Cue-Aktionen
      const listRow = document.createElement("div");
      listRow.className = "cuelist-listrow";
      const delList = document.createElement("button");
      delList.type = "button";
      delList.className = "fx-btn cuelist-toolbar__btn--manage";
      delList.dataset.i18n = "CUELIST_MANAGE";
      delList.textContent = i18n("CUELIST_MANAGE");
      delList.dataset.i18nTip = "CUELIST_MANAGE_TIP";
      delList.title = i18n("CUELIST_MANAGE_TIP");
      delList.addEventListener("click", () => _openManageDialog());
      listRow.append(selectEl, delList);
      tb.appendChild(listRow);
      tb.appendChild(actions);

      const tableWrap = document.createElement("div");
      tableWrap.className = "fx-table-wrap cuelist-table-wrap";
      tableWrap.innerHTML = `
        <table class="fx-table cuelist-table list--zebra">
          <thead>
            <tr>
              <th class="fx-th cue-th--status"></th>
              <th class="fx-th cue-th--num" data-i18n="CUELIST_COL_NUMBER">${_esc(i18n("CUELIST_COL_NUMBER"))}</th>
              <th class="fx-th cue-th--name" data-i18n="CUELIST_COL_NAME">${_esc(i18n("CUELIST_COL_NAME"))}</th>
              <th class="fx-th cue-th--trigger" data-i18n="CUELIST_COL_TRIGGER">${_esc(i18n("CUELIST_COL_TRIGGER"))}</th>
              <th class="fx-th cue-th--fade" data-i18n="CUELIST_COL_FADE">${_esc(i18n("CUELIST_COL_FADE"))}</th>
              <th class="fx-th cue-th--fade" data-i18n="CUELIST_COL_DELAY">${_esc(i18n("CUELIST_COL_DELAY"))}</th>
              <th class="fx-th cue-th--mib" data-i18n="CUELIST_COL_MIB">${_esc(i18n("CUELIST_COL_MIB"))}</th>
              <th class="fx-th cue-th--fade" data-i18n="CUELIST_COL_COLOR_FADE">${_esc(i18n("CUELIST_COL_COLOR_FADE"))}</th>
              <th class="fx-th cue-th--fade" data-i18n="CUELIST_COL_COLOR_DELAY">${_esc(i18n("CUELIST_COL_COLOR_DELAY"))}</th>
              <th class="fx-th cue-th--fade" data-i18n="CUELIST_COL_POS_FADE">${_esc(i18n("CUELIST_COL_POS_FADE"))}</th>
              <th class="fx-th cue-th--fade" data-i18n="CUELIST_COL_POS_DELAY">${_esc(i18n("CUELIST_COL_POS_DELAY"))}</th>
              <th class="fx-th cue-th--fade" data-i18n="CUELIST_COL_BEAM_FADE">${_esc(i18n("CUELIST_COL_BEAM_FADE"))}</th>
              <th class="fx-th cue-th--fade" data-i18n="CUELIST_COL_BEAM_DELAY">${_esc(i18n("CUELIST_COL_BEAM_DELAY"))}</th>
              <th class="fx-th cue-th--fade" data-i18n="CUELIST_COL_ZOOM_FADE">${_esc(i18n("CUELIST_COL_ZOOM_FADE"))}</th>
              <th class="fx-th cue-th--fade" data-i18n="CUELIST_COL_ZOOM_DELAY">${_esc(i18n("CUELIST_COL_ZOOM_DELAY"))}</th>
              <th class="fx-th cue-th--fade" data-i18n="CUELIST_COL_FX_IN">${_esc(i18n("CUELIST_COL_FX_IN"))}</th>
              <th class="fx-th cue-th--fade" data-i18n="CUELIST_COL_FX_OUT">${_esc(i18n("CUELIST_COL_FX_OUT"))}</th>
              <th class="fx-th cue-th--cmd" data-i18n="CUELIST_COL_CMD">${_esc(i18n("CUELIST_COL_CMD"))}</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      `;

      _setupCueColumns(tableWrap.querySelector(".cuelist-table"));
      _attachRowSwipe(tableWrap);
      // Tippen neben die Zeilen hebt die Markierung auf
      tableWrap.addEventListener("click", (e) => {
        if (Date.now() - _swipeEndedAt < 350) return;                 // Ende einer Wischgeste, kein Tipp
        if (e.target.closest(".cue-row, th") || !_sel.size) return;
        _sel.clear();
        _multi = false;
        _syncSelection();
      });

      const emptyEl = document.createElement("div");
      emptyEl.className = "cuelist-empty fx-empty";
      emptyEl.hidden = true;

      wrap.appendChild(tb);
      wrap.appendChild(tableWrap);
      wrap.appendChild(emptyEl);

      requestAnimationFrame(() => {
        const panelEl = wrap.closest("[data-panel-type='cuelist']") || wrap;
        _readListConfig(panelEl, panel.module_config);
        _renderPanel(panelEl);
      });
      return wrap;
    },

    onModuleConfigChanged(panelEl, mc) {
      // Sichtbarkeit des gelben Fade-Ladebalkens ist pro Panel-Instanz
      // konfigurierbar (Zahnrad -> Panel-Eigenschaften) - _renderPanel()
      // liest panelEl.dataset.showProgressBar beim Bau jeder Zeile.
      _readListConfig(panelEl, mc);
      _renderPanel(panelEl);
    },

    // Eigenschaften: Listen-Auswahl anzeigen (aus = feste Liste, nur Tabelle + Button-Leiste), feste Liste, Fortschrittsbalken
    buildPropertiesPane(moduleConfig, api) {
      const mc = moduleConfig || {};
      const frag = document.createDocumentFragment();
      const toggle = (id, key, checked) => {
        const field = document.createElement("div");
        field.className = "modal__field modal__field--checkbox";
        const tgl = makeToggleSwitch(id, checked);
        const lbl = document.createElement("label");
        lbl.htmlFor = id;
        lbl.dataset.i18n = key;
        lbl.textContent = api.i18n(key);
        field.append(tgl.label, lbl);
        frag.appendChild(field);
      };
      toggle("cuelist-prop-show-select", "CUELIST_PROP_SHOW_SELECT", mc.show_list_select !== false);
      const row = document.createElement("div");
      row.className = "modal__field";
      row.id = "cuelist-prop-list-row";
      const label = document.createElement("label");
      label.htmlFor = "cuelist-prop-list";
      label.dataset.i18n = "CUELIST_PROP_LIST";
      label.textContent = api.i18n("CUELIST_PROP_LIST");
      const select = document.createElement("select");
      select.id = "cuelist-prop-list";
      select.className = "modal__input";
      const add = (value, text) => { const o = document.createElement("option"); o.value = value; o.textContent = text; select.appendChild(o); };
      add("", api.i18n("CUELIST_PROP_LIST_AUTO"));
      Object.values(_allCuelists).forEach((cl) => add(cl.id, cl.name));
      select.value = mc.cuelist_id && _allCuelists[mc.cuelist_id] ? mc.cuelist_id : "";
      const hint = document.createElement("div");
      hint.className = "modal__hint";
      hint.dataset.i18n = "CUELIST_PROP_LIST_HINT";
      hint.textContent = api.i18n("CUELIST_PROP_LIST_HINT");
      row.append(label, select, hint);
      frag.appendChild(row);
      toggle("cuelist-prop-progress", "CUELIST_PROP_SHOW_PROGRESS", mc.show_progress_bar !== false);
      return frag;
    },

    afterPropertiesPaneInserted(paneEl) {
      const show = paneEl.querySelector("#cuelist-prop-show-select");
      const row = paneEl.querySelector("#cuelist-prop-list-row");
      const sync = () => {                                 // die feste Liste gilt nur bei ausgeblendeter Listen-Auswahl
        row.classList.toggle("modal__field--disabled", show.checked);
        row.querySelector("select").disabled = show.checked;
      };
      show.addEventListener("change", sync);
      sync();
    },

    readPropertiesPane() {
      return {
        show_list_select: document.getElementById("cuelist-prop-show-select")?.checked !== false,
        cuelist_id: document.getElementById("cuelist-prop-list")?.value || "",
        show_progress_bar: document.getElementById("cuelist-prop-progress")?.checked !== false,
      };
    },

    onMessage(panelEl, messageType, payload) {
      if (messageType === "state_snapshot" || messageType === "cuelists_changed") {
        // Wiedergabezustand aus dem Snapshot (Reconnect, zweites Geraet, geladene Show) bzw. aus cuelists_changed
        if (payload.cue_playback) _ingestPlayback(payload.cue_playback);
        _allCuelists = payload.cuelists || {};
        _activeCuelistId = payload.active_cuelist_id || null;
        _activeCueIds = payload.active_cue_ids || {};
        if (Modal.isOpen("cuelist-manage") && _manageEditing === null) _renderManage();          // der Verwalten-Dialog folgt jeder Aenderung (auch von einem anderen Geraet)
        if (_gestureActive) _deferredPanels.add(panelEl);        // nach der Wischgeste (das Feld unter dem Finger muss bestehen bleiben)
        else _renderPanel(panelEl);
      } else if (messageType === "language_changed") {
        _renderPanel(panelEl);
      } else if (messageType === "cuelist_progress") {
        // Nur bei einem Wechsel des Wiedergabezustands (Start, Pause, Weiter, Stopp, Ende) - nicht mehr pro
        // Tick. Kein _renderPanel()-Rebuild: der Balken des betroffenen Cues wird neu angesetzt und laeuft
        // dann von allein (CSS-Transition ueber die Restzeit).
        _ingestPlayback({ [payload.cuelist_id]: payload });
        _paintActiveBar(panelEl, payload.cuelist_id);
        _syncFollowBar(panelEl, payload.cuelist_id);
      }
    },
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", _wireDialogs);
  } else {
    _wireDialogs();
  }

})();

// ═══════════════════════════════════════════════════════════════════
// Executor-Panel (dot2-Stil): Fader MISCHT zwischen manuellem Wert (0 %) und Cue-Wert (100 %) fuer jedes Attribut der
// zugeordneten Cue-Liste (nicht die Gesamthelligkeit - der Grand Master ist davon unabhaengig). Darunter Go / Pause /
// Zurueck / Stopp. Die Cue-Liste verwaltet nur die Cues; die Wiedergabe laeuft ueber den Executor. Mehrere Executoren auf
// verschiedene Cue-Listen mischen unabhaengig, die gespeicherten Cue-Werte bleiben unveraendert.
// Darstellung je Panel (Panel-Eigenschaften): Fader und jede Taste einzeln ein-/ausblendbar, Groesse je Taste (klein/
// normal/gross), "Titel anzeigen", "Kompakte Anordnung" (keine Zwischenraeume), "Smarte Anordnung" (Go ueber die volle
// Breite, darunter Pause/Zurueck/Stopp in einer Reihe), Fader-Farbe. Alle Tasten sind immer bedienbar.
// ═══════════════════════════════════════════════════════════════════
(function () {
  "use strict";

  let _lists = {};            // id -> Cue-Liste (Spiegel des Servers)
  let _activeListId = null;
  let _activeCues = {};       // cuelist_id -> aktiver cue_id
  let _playback = {};         // cuelist_id -> Wiedergabezustand der CueEngine (+ "at" = Empfangszeit)
  let _masters = {};          // cuelist_id -> Fader 0-100 (Spiegel des Servers)
  const SEND_MS = 40;
  // Taste -> Konfig-Schluessel und Klasse (die Klassen bleiben die der frueheren Listen-Tasten)
  const BUTTONS = [
    { key: "go",    cfg: "show_go",    size: "size_go",    cls: "cuelist-toolbar__btn--go",    i18n: "CUELIST_GO",    prop: "EXEC_PROP_SHOW_GO" },
    { key: "pause", cfg: "show_pause", size: "size_pause", cls: "cuelist-toolbar__btn--pause", i18n: "CUELIST_PAUSE", prop: "EXEC_PROP_SHOW_PAUSE" },
    { key: "back",  cfg: "show_back",  size: "size_back",  cls: "cuelist-toolbar__btn--back",  i18n: "CUELIST_BACK",  prop: "EXEC_PROP_SHOW_BACK" },
    { key: "stop",  cfg: "show_stop",  size: "size_stop",  cls: "cuelist-toolbar__btn--stop",  i18n: "CUELIST_STOP",  prop: "EXEC_PROP_SHOW_STOP" },
  ];
  const SIZES = ["small", "normal", "large"];

  const _fmt = (n) => { const x = Number(n); return Number.isFinite(x) ? String(Math.round(x * 1000) / 1000) : String(n); };
  const _cfg = (panelEl) => { try { return JSON.parse(panelEl.dataset.moduleConfig || "{}"); } catch (e) { return {}; } };

  function _ingestPlayback(pb) {
    if (pb && pb.cuelist_id) _playback[pb.cuelist_id] = { ...pb, at: performance.now() };
  }

  /** Die diesem Executor zugeordnete Liste; ohne Auswahl (oder wenn sie geloescht wurde) die aktive Liste. */
  function _boundList(panelEl) {
    const id = _cfg(panelEl).cuelist_id;
    return (id && _lists[id]) || (_activeListId && _lists[_activeListId]) || null;
  }

  function _live(cl) {
    const pb = cl ? _playback[cl.id] : null;
    return pb && pb.cue_id === _activeCues[cl.id] ? pb : null;
  }

  function _paintFader(panelEl, level) {
    const track = panelEl.querySelector(".executor__track");
    if (!track || track._dragging) return;
    _setFader(panelEl, level);
  }

  function _setFader(panelEl, level) {
    const track = panelEl.querySelector(".executor__track");
    if (!track) return;
    const pct = Math.max(0, Math.min(100, Math.round(level)));
    track.querySelector(".vfader__fill").style.height = pct + "%";
    track.style.setProperty("--fv", pct + "%");
    track.querySelector(".vfader__thumb").textContent = pct;
    track.setAttribute("aria-valuenow", String(pct));
  }

  /** Restzeit des laufenden Fades als Fuellbalken im Go-Button: EINE lineare CSS-Transition ueber die Restzeit (wie die
   *  Balken der Cue-Liste, ohne Tick-Nachrichten); bei Pause/Stopp eingefroren, bei Ende ausgeblendet. */
  function _paintGoProgress(panelEl, cl) {
    const fill = panelEl.querySelector(".executor__goprog");
    if (!fill) return;
    const pb = _live(cl);
    const key = pb ? pb.cue_id + ":" + pb.state + ":" + Math.round(pb.at) : "";
    if (fill._key === key) return;                   // nichts Neues: laufende Transition nicht neu starten
    fill._key = key;
    fill.style.transition = "none";
    if (!pb || pb.state === "done") { fill.style.opacity = "0"; fill.style.transform = "scaleX(0)"; return; }
    fill.style.opacity = "1";
    if (pb.state === "paused" || pb.state === "stopped") { fill.style.transform = "scaleX(" + pb.progress + ")"; return; }
    const elapsed = (performance.now() - pb.at) / 1000;
    const remaining = pb.remaining - elapsed;
    if (!(pb.remaining > 0) || remaining <= 0) { fill.style.opacity = "0"; fill.style.transform = "scaleX(0)"; return; }
    fill.style.transform = "scaleX(" + (pb.progress + (1 - pb.progress) * (elapsed / pb.remaining)) + ")";
    void fill.offsetWidth;                            // Startwert festschreiben, dann animieren
    fill.style.transition = "transform " + remaining + "s linear";
    fill.style.transform = "scaleX(1)";
  }

  /** Darstellung aus den Panel-Eigenschaften: Fader/Tasten sichtbar, Groessen, Titel, kompakt, smart, Fader-Farbe. */
  function _applyConfig(panelEl) {
    const wrap = panelEl.querySelector(".executor");
    if (!wrap) return;
    const mc = _cfg(panelEl);
    wrap.classList.toggle("executor--compact", mc.compact === true);
    wrap.classList.toggle("executor--smart", mc.smart === true);
    wrap.classList.toggle("executor--no-title", mc.show_title === false);
    wrap.querySelector(".executor__track").hidden = mc.show_fader === false;
    let visible = 0;
    let others = 0;
    BUTTONS.forEach((b) => {
      const on = mc[b.cfg] !== false;
      const btn = wrap.querySelector("." + b.cls);
      if (btn) {
        btn.hidden = !on;
        btn.dataset.size = SIZES.includes(mc[b.size]) ? mc[b.size] : "normal";
      }
      if (on) { visible++; if (b.key !== "go") others++; }
    });
    wrap.querySelector(".executor__buttons").hidden = visible === 0;
    wrap.style.setProperty("--exec-n", String(Math.max(1, others)));   // Spalten der Reihe unter der grossen Go-Taste
    if (mc.fader_color) wrap.style.setProperty("--exec-fader-color", mc.fader_color);
    else wrap.style.removeProperty("--exec-fader-color");
  }

  function _render(panelEl) {
    const cl = _boundList(panelEl);
    const nameEl = panelEl.querySelector(".executor__name");
    const cueEl = panelEl.querySelector(".executor__cue");
    const track = panelEl.querySelector(".executor__track");
    if (!nameEl) return;
    _applyConfig(panelEl);
    panelEl.dataset.cuelistId = cl ? cl.id : "";
    nameEl.textContent = cl ? cl.name : i18n("EXEC_NO_LIST");
    const active = cl && cl.cues.find(c => c.id === _activeCues[cl.id]);
    cueEl.textContent = active ? i18n("EXEC_ACTIVE_CUE").replace("{cue}", _fmt(active.number) + " " + active.name) : i18n("EXEC_NO_ACTIVE");
    if (track) {
      track.classList.toggle("executor__track--disabled", !cl);
      _paintFader(panelEl, cl ? (_masters[cl.id] != null ? _masters[cl.id] : 100) : 0);
    }
    // Go-Vorschau: naechster Cue (nach dem aktiven; am Ende der erste mit Nummer > 0), wie bisher im Listen-Panel
    const goBtn = panelEl.querySelector(".cuelist-toolbar__btn--go");
    if (goBtn) {
      let next = null;
      if (cl && cl.cues.length) {
        const idx = cl.cues.findIndex(c => c.id === _activeCues[cl.id]);
        const first = cl.cues.filter(c => c.number > 0).sort((a, b) => a.number - b.number)[0] || cl.cues[0];
        next = idx < 0 ? cl.cues[0] : (cl.cues[idx + 1] || first);
      }
      goBtn.title = next ? i18n("CUELIST_NEXT_CUE").replace("{cue}", `${_fmt(next.number)} ${next.name}`) : i18n("CUELIST_NO_NEXT_CUE");
    }
    // Alle Tasten sind IMMER bedienbar (nie disabled). Pause zeigt "Weiter" im pausierten Zustand und ist ohne laufenden
    // Fade nur gedimmt (kein Effekt beim Druecken), statt gesperrt zu sein.
    const pb = _live(cl);
    const state = pb ? pb.state : "idle";
    const pauseBtn = panelEl.querySelector(".cuelist-toolbar__btn--pause");
    if (pauseBtn) {
      const key = state === "paused" ? "CUELIST_RESUME" : "CUELIST_PAUSE";
      const label = pauseBtn.querySelector(".executor__label");
      if (label.dataset.i18n !== key) { label.dataset.i18n = key; label.textContent = i18n(key); }
      pauseBtn.classList.toggle("executor__btn--idle", !(state === "running" || state === "paused"));
      pauseBtn.classList.toggle("cuelist-toolbar__btn--held", state === "paused");
    }
    _paintGoProgress(panelEl, cl);
  }

  function _send(panelEl, type, extra) {
    const cl = _boundList(panelEl);
    if (cl) window.__panelAPI.sendToServer(type, { cuelist_id: cl.id, ...(extra || {}) });
  }

  // ---- Fader: Maus (Touch laeuft ueber die Touch-Bruecke, die Flaeche hat touch-action: none) -----------------------------
  function _startDrag(panelEl, track, startEvent) {
    const cl = _boundList(panelEl);
    if (!cl) return;
    track._dragging = true;
    let last = 0;
    let lastSent = null;
    const levelFrom = (event) => {
      const r = track.getBoundingClientRect();
      return Math.max(0, Math.min(100, Math.round((1 - (event.clientY - r.top) / r.height) * 100)));
    };
    const apply = (level, force) => {
      _setFader(panelEl, level);
      _masters[cl.id] = level;
      const now = performance.now();
      if (force || (now - last >= SEND_MS && level !== lastSent)) {
        last = now;
        lastSent = level;
        window.__panelAPI.sendToServer("set_cuelist_master", { cuelist_id: cl.id, value: level });
      }
    };
    apply(levelFrom(startEvent));
    const onMove = (event) => apply(levelFrom(event));
    const onUp = (event) => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      track._dragging = false;
      apply(levelFrom(event), true);       // der Endwert darf nicht im Takt verloren gehen
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }

  function _button(def, onClick) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "fx-btn executor__btn " + def.cls;
    btn.dataset.size = "normal";
    if (def.key === "go") {
      const fill = document.createElement("span");       // Fuellbalken der Restzeit (siehe _paintGoProgress)
      fill.className = "executor__goprog";
      fill.setAttribute("aria-hidden", "true");
      btn.appendChild(fill);
    }
    // Beschriftung in eigenem Span: translator.apply() ersetzt den Text nur dort (nicht den Fuellbalken)
    const label = document.createElement("span");
    label.className = "executor__label";
    label.dataset.i18n = def.i18n;
    label.textContent = i18n(def.i18n);
    btn.appendChild(label);
    btn.addEventListener("click", onClick);
    return btn;
  }

  window.__panelPlugins.register({
    type: "executor",

    buildContent(panel) {
      const wrap = document.createElement("div");
      wrap.className = "executor";
      const nameEl = document.createElement("div");
      nameEl.className = "executor__name";
      const cueEl = document.createElement("div");
      cueEl.className = "executor__cue";

      const track = document.createElement("div");
      track.className = "vfader__track executor__track";
      track.setAttribute("role", "slider");
      track.setAttribute("aria-valuemin", "0");
      track.setAttribute("aria-valuemax", "100");
      track.dataset.i18nTip = "EXEC_FADER_TIP";      // translator.apply() setzt den Tooltip (auch nach spaetem Laden der Sprache)
      track.title = i18n("EXEC_FADER_TIP");
      const fill = document.createElement("div"); fill.className = "vfader__fill";
      const thumb = document.createElement("div"); thumb.className = "vfader__thumb";
      track.append(fill, thumb);

      const buttons = document.createElement("div");
      buttons.className = "executor__buttons";
      const panelOf = () => wrap.closest("[data-panel-type='executor']") || wrap;
      const actions = {
        go: () => _send(panelOf(), "cue_go"),
        pause: () => {
          const panelEl = panelOf();
          const pb = _live(_boundList(panelEl));
          _send(panelEl, pb && pb.state === "paused" ? "cue_resume" : "cue_pause");
        },
        back: () => _send(panelOf(), "cue_back"),
        stop: () => _send(panelOf(), "cue_stop"),
      };
      BUTTONS.forEach((def) => buttons.appendChild(_button(def, actions[def.key])));

      track.addEventListener("mousedown", (event) => {
        if (typeof isEditMode !== "undefined" && isEditMode) return;
        if (event.button !== 0) return;
        event.preventDefault();
        event.stopPropagation();
        _startDrag(panelOf(), track, event);
      });
      // Bedienung per Tastatur: Pfeile +/- 5 %
      track.tabIndex = 0;
      track.addEventListener("keydown", (event) => {
        const cl = _boundList(panelOf());
        if (!cl || !["ArrowUp", "ArrowDown"].includes(event.key)) return;
        event.preventDefault();
        const level = Math.max(0, Math.min(100, (_masters[cl.id] != null ? _masters[cl.id] : 100) + (event.key === "ArrowUp" ? 5 : -5)));
        _masters[cl.id] = level;
        _setFader(panelOf(), level);
        window.__panelAPI.sendToServer("set_cuelist_master", { cuelist_id: cl.id, value: level });
      });

      wrap.append(nameEl, cueEl, track, buttons);
      requestAnimationFrame(() => _render(panelOf()));
      return wrap;
    },

    onModuleConfigChanged(panelEl) { _render(panelEl); },

    onMessage(panelEl, messageType, payload) {
      if (messageType === "state_snapshot" || messageType === "cuelists_changed") {
        _lists = payload.cuelists || {};
        _activeListId = payload.active_cuelist_id || null;
        _activeCues = payload.active_cue_ids || {};
        if (payload.cue_playback) {
          Object.values(payload.cue_playback).forEach((pb) => {
            const old = _playback[pb.cuelist_id];
            // Gleicher Zustand wie schon bekannt: keinen neuen Empfangszeitpunkt (die laufende Transition nicht neu starten)
            if (!old || old.cue_id !== pb.cue_id || old.state !== pb.state) _ingestPlayback(pb);
          });
        }
        if (payload.cuelist_masters) _masters = { ...payload.cuelist_masters };
        _render(panelEl);
      } else if (messageType === "cuelist_progress") {
        _ingestPlayback(payload);
        _render(panelEl);
      } else if (messageType === "cuelist_master_changed") {
        _masters[payload.cuelist_id] = payload.value;
        _render(panelEl);
      } else if (messageType === "language_changed") {
        _render(panelEl);
      }
    },

    // Eigenschaften: Cue-Liste, Fader, jede Taste (sichtbar + Groesse), Titel, Kompakt, Smart, Fader-Farbe
    buildPropertiesPane(moduleConfig, api) {
      const mc = moduleConfig || {};
      const frag = document.createDocumentFragment();
      const row = document.createElement("div");
      row.className = "modal__field";
      const label = document.createElement("label");
      label.htmlFor = "executor-cuelist";
      label.dataset.i18n = "EXEC_PROP_CUELIST";
      label.textContent = api.i18n("EXEC_PROP_CUELIST");
      const select = document.createElement("select");
      select.id = "executor-cuelist";
      select.className = "modal__input";
      const add = (value, text) => { const o = document.createElement("option"); o.value = value; o.textContent = text; select.appendChild(o); };
      add("", api.i18n("EXEC_LIST_AUTO"));
      Object.values(_lists).forEach(cl => add(cl.id, cl.name));
      select.value = mc.cuelist_id && _lists[mc.cuelist_id] ? mc.cuelist_id : "";
      row.append(label, select);
      frag.appendChild(row);

      const toggle = (id, labelKey, checked) => {
        const field = document.createElement("div");
        field.className = "modal__field modal__field--checkbox";
        const tgl = makeToggleSwitch(id, checked);
        const lbl = document.createElement("label");
        lbl.htmlFor = id;
        lbl.dataset.i18n = labelKey;
        lbl.textContent = api.i18n(labelKey);
        field.append(tgl.label, lbl);
        frag.appendChild(field);
      };
      const sizePicker = (def) => {
        const field = document.createElement("div");
        field.className = "modal__field";
        const lbl = document.createElement("label");
        lbl.htmlFor = "executor-" + def.size.replace(/_/g, "-");
        lbl.textContent = api.i18n("EXEC_PROP_SIZE").replace("{button}", api.i18n(def.i18n));
        const sel = document.createElement("select");
        sel.id = lbl.htmlFor;
        sel.className = "modal__input";
        SIZES.forEach((s) => {
          const o = document.createElement("option");
          o.value = s;
          o.textContent = api.i18n("EXEC_SIZE_" + s.toUpperCase());
          sel.appendChild(o);
        });
        sel.value = SIZES.includes(mc[def.size]) ? mc[def.size] : "normal";
        field.append(lbl, sel);
        frag.appendChild(field);
      };
      toggle("executor-show-fader", "EXEC_PROP_SHOW_FADER", mc.show_fader !== false);
      BUTTONS.forEach((b) => {
        toggle("executor-" + b.cfg.replace(/_/g, "-"), b.prop, mc[b.cfg] !== false);
        sizePicker(b);
      });
      toggle("executor-show-title", "EXEC_PROP_SHOW_TITLE", mc.show_title !== false);
      toggle("executor-compact", "EXEC_PROP_COMPACT", mc.compact === true);
      toggle("executor-smart", "EXEC_PROP_SMART", mc.smart === true);

      // Fader-Farbe: dieselbe Farbwahl (Swatch + Hex) wie in den anderen Panel-Eigenschaften; "Akzentfarbe" = keine eigene
      toggle("executor-fader-accent", "EXEC_PROP_FADER_ACCENT", !mc.fader_color);
      const colorRow = document.createElement("div");
      colorRow.className = "modal__field";
      colorRow.id = "executor-fader-color-row";
      const colorLabel = document.createElement("label");
      colorLabel.dataset.i18n = "EXEC_PROP_FADER_COLOR";
      colorLabel.textContent = api.i18n("EXEC_PROP_FADER_COLOR");
      const sw = document.createElement("input");
      sw.type = "color";
      sw.id = "executor-fader-color-sw";
      sw.className = "color-swatch-input";
      sw.value = mc.fader_color || "#ffb000";
      const hex = document.createElement("input");
      hex.type = "text";
      hex.id = "executor-fader-color-hex";
      hex.className = "color-hex-input";
      hex.maxLength = 7;
      hex.value = sw.value;
      colorRow.append(colorLabel, sw, hex);
      frag.appendChild(colorRow);
      return frag;
    },

    afterPropertiesPaneInserted(paneEl, panelId, api) {
      const panelEl = document.querySelector('[data-panel-id="' + panelId + '"]');
      const wrap = panelEl && panelEl.querySelector(".executor");
      const accent = paneEl.querySelector("#executor-fader-accent");
      const sw = paneEl.querySelector("#executor-fader-color-sw");
      const hex = paneEl.querySelector("#executor-fader-color-hex");
      const row = paneEl.querySelector("#executor-fader-color-row");
      const preview = () => {
        if (!wrap) return;
        if (accent.checked) wrap.style.removeProperty("--exec-fader-color");
        else wrap.style.setProperty("--exec-fader-color", hex.value);
      };
      const sync = () => {
        row.classList.toggle("modal__field--disabled", accent.checked);
        sw.disabled = hex.disabled = accent.checked;
        preview();
      };
      api.wireColorPair("executor-fader-color-sw", "executor-fader-color-hex", preview);
      accent.addEventListener("change", sync);
      sync();
      // Komfort: "Kompakt" einschalten blendet auch den Titel aus (der Titel-Schalter bleibt danach unabhaengig bedienbar)
      const compact = paneEl.querySelector("#executor-compact");
      const title = paneEl.querySelector("#executor-show-title");
      if (compact && title) compact.addEventListener("change", () => { if (compact.checked) title.checked = false; });
    },

    readPropertiesPane() {
      const on = (id) => document.getElementById(id)?.checked !== false;
      const cfg = { cuelist_id: document.getElementById("executor-cuelist")?.value || "" };
      cfg.show_fader = on("executor-show-fader");
      BUTTONS.forEach((b) => {
        cfg[b.cfg] = on("executor-" + b.cfg.replace(/_/g, "-"));
        const value = document.getElementById("executor-" + b.size.replace(/_/g, "-"))?.value;
        cfg[b.size] = SIZES.includes(value) ? value : "normal";
      });
      cfg.show_title = document.getElementById("executor-show-title")?.checked !== false;
      cfg.compact = document.getElementById("executor-compact")?.checked === true;
      cfg.smart = document.getElementById("executor-smart")?.checked === true;
      const hex = (document.getElementById("executor-fader-color-hex")?.value || "").trim();
      cfg.fader_color = document.getElementById("executor-fader-accent")?.checked !== false || !/^#[0-9a-fA-F]{6}$/.test(hex) ? "" : hex;
      return cfg;
    },
  });
})();

// ═══════════════════════════════════════════════════════════════════
// Blackout: Umschalter in der Werkzeugleiste (und die Taste im Panel "Befehls-Tasten"). Der Server haelt den Zustand (alle Helligkeiten auf 0, die Werte
// bleiben); "blackout_changed" bzw. der Snapshot setzt window.__blackout, __syncBlackout() zeichnet Knopf und Tasten.
// ═══════════════════════════════════════════════════════════════════
(function () {
  "use strict";
  window.__syncBlackout = function () {
    const on = !!window.__blackout;
    const btn = document.getElementById("toolbar-blackout");
    if (btn) {
      btn.classList.toggle("menubar__blackout--on", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      btn.title = i18n(on ? "BLACKOUT_ACTIVE" : "BLACKOUT_TITLE");
    }
    document.querySelectorAll(".cmdbtn--blackout").forEach((el) => el.classList.toggle("cmdbtn--on", on));
    document.dispatchEvent(new CustomEvent("fixtures-live-values", { detail: {} }));       // die 3D-Simulation zeichnet neu (der Blackout dunkelt sie ab)
    document.dispatchEvent(new CustomEvent("blackout-changed"));                           // weitere Anzeigen (Knopf in der 3D-Simulation)
  };
  const btn = document.getElementById("toolbar-blackout");
  if (btn) btn.addEventListener("click", () => window.__panelAPI.sendToServer("set_blackout", {}));
})();

// ═══════════════════════════════════════════════════════════════════
// Befehls-Eingabepuffer: der Text, den die Ziffern-/Befehlstasten aufbauen und den "Please"/Enter ausfuehrt. Er ist
// ein eigener Zustand und NICHT der Inhalt eines <input>: die Tasten schreiben direkt hinein (kein Fokus, damit auf
// Tablets nie die Bildschirmtastatur aufgeht), das Befehlszeilen-Panel zeigt ihn an und schreibt echte Tastatur-
// eingaben zurueck. Ohne Befehlszeilen-Panel lebt er unsichtbar weiter (das Tasten-Panel zeigt dann eine eigene
// kleine Anzeige, siehe command_numpad).
// ═══════════════════════════════════════════════════════════════════
const CommandBuffer = (() => {
  let value = "";
  const subscribers = new Set();
  const api = {
    get value() { return value; },
    /** Setzt den Puffer; `source` ist der Aufrufer (ein <input> erkennt so seine eigenen Aenderungen). */
    set(next, source) {
      next = String(next == null ? "" : next);
      if (next === value) return;
      value = next;
      subscribers.forEach((fn) => fn(value, source));
    },
    append(text) { api.set(value + text); },                       // Ziffern/Punkt: ohne Leerzeichen
    appendKeyword(word) {                                          // Schluesselwoerter/Operatoren: mit Leerzeichen
      api.set(value + (value.length && !value.endsWith(" ") ? " " : "") + word + " ");
    },
    backspace() { api.set(value.slice(0, -1)); },
    subscribe(fn) { subscribers.add(fn); return () => subscribers.delete(fn); },
  };
  return api;
})();

// ═══════════════════════════════════════════════════════════════════
// Command Line Panel Plugin (dot2-/MA-Lighting-Stil, siehe documentation/commands.md
// und app/command_line.py) - Log + Eingabezeile mit History, sendet jeden
// Befehl per WebSocket ("run_command") an den serverseitigen Parser.
// Log UND Historie sind modul-weit (nicht pro Panel-Instanz) geteilt -
// mehrere gleichzeitig geoeffnete Command-Line-Panels zeigen dieselbe,
// gemeinsame Konsole (konsistent mit der server-autoritativen Selektion).
// ═══════════════════════════════════════════════════════════════════
(function () {
  "use strict";

  let _log = [];          // { command, success, message, timestamp, source }[] - aelteste zuerst
  let _history = [];       // getippte Befehle, aelteste zuerst
  let _autoScroll = true;
  let _systemReadyLogged = false;
  let _lastEnttecStatus = null; // Dedup-Key: verhindert doppelte Eintraege bei mehrfachen Broadcasts
  let _historyIndex = -1;  // -1 = aktueller (noch nicht abgeschickter) Entwurf
  let _draftBeforeHistory = "";

  // Tab-Autocomplete (Grammatik und Zustand liegen auf dem Server: app/command_line.py get_suggestions() - das Frontend haelt hier bewusst
  // KEINE eigene Keyword-Liste). Jeder Vorschlag traegt `start` (Index im Eingabetext, ab dem `insert` das getippte Wort ersetzt) und
  // ggf. `info` (nur ein Hinweis auf den erwarteten Wert, nicht einfuegbar).
  let _suggestions = [];          // letzte Antwort des Servers
  let _activeInputEl = null;
  let _tab = null;                // laufender Tab-Zyklus: { items, index }
  let _suggestIndex = -1;
  let _suggestTimer = null;
  const _suggestionsOn = () => window.__cmdSuggestions !== false;     // Schalter neben der Befehlszeile (gespeichert in der App-Config)

  // Schalter und Anzeige auf allen Befehlszeilen-Panels an den gespeicherten Stand angleichen
  window.__syncCmdSuggestions = () => {
    document.querySelectorAll(".cmdline-sugg__input").forEach((el) => { el.checked = _suggestionsOn(); });
    if (!_suggestionsOn()) { _tab = null; _hideAllSuggestions(); }
    else if (_activeInputEl && document.activeElement === _activeInputEl) _requestSuggestions(_activeInputEl);
  };

  function _requestSuggestions(inputEl) {
    _activeInputEl = inputEl;
    if (!_suggestionsOn()) return;
    clearTimeout(_suggestTimer);
    _suggestTimer = setTimeout(() => {
      if (inputEl.selectionStart !== inputEl.value.length) { _hideAllSuggestions(); return; }      // nur am Zeilenende
      window.__panelAPI.sendToServer("autocomplete", { text: inputEl.value });
    }, 30);
  }
  function _hideSuggestions(panelEl) {
    const box = panelEl.querySelector(".cmdline-suggestions");
    if (!box) return;
    box.hidden = true;
    box.innerHTML = "";
  }
  function _hideAllSuggestions() {
    document.querySelectorAll('[data-panel-type="command_line"]').forEach(_hideSuggestions);
    _suggestions = [];
    _suggestIndex = -1;
  }
  function _renderSuggestions(panelEl, suggestions) {
    const box = panelEl.querySelector(".cmdline-suggestions");
    if (!box) return;
    if (!suggestions || !suggestions.length) { _hideSuggestions(panelEl); return; }
    box.innerHTML = suggestions.map((s, i) => `
      <div class="cmdline-suggestion${s.info ? " cmdline-suggestion--info" : ""}${i === _suggestIndex ? " cmdline-suggestion--active" : ""}" data-index="${i}">
        <span class="cmdline-suggestion__label">${_esc(s.label || "")}</span>
        ${s.hint ? `<span class="cmdline-suggestion__hint">${_esc(s.hint)}</span>` : ""}
      </div>
    `).join("");
    box.hidden = false;
    const active = box.querySelector(".cmdline-suggestion--active");
    if (active) active.scrollIntoView({ block: "nearest" });
  }
  function _applySuggestion(inputEl, suggestion) {
    inputEl.value = inputEl.value.slice(0, suggestion.start) + (suggestion.insert != null ? suggestion.insert : (suggestion.label || ""));
    CommandBuffer.set(inputEl.value, inputEl);                       // Enter fuehrt den Eingabepuffer aus: er muss den eingefuegten Text kennen
    const pos = inputEl.value.length;
    inputEl.setSelectionRange(pos, pos);
  }
  // Tab: erster Vorschlag, jeder weitere Tab der naechste (Umschalt+Tab rueckwaerts); jede Eingabe beendet den Durchlauf.
  function _handleTab(inputEl, panelEl, backwards) {
    if (!_tab) {
      const items = _suggestions.filter((s) => !s.info);
      if (!items.length) return;
      _tab = { items, index: backwards ? items.length - 1 : 0 };
    } else {
      _tab.index = (_tab.index + (backwards ? -1 : 1) + _tab.items.length) % _tab.items.length;
    }
    _applySuggestion(inputEl, _tab.items[_tab.index]);
    if (_tab.items.length === 1) {                                   // eindeutig: weiter mit den Vorschlaegen fuer das naechste Wort
      _tab = null;
      _requestSuggestions(inputEl);
      return;
    }
    _suggestIndex = _tab.index;
    _renderSuggestions(panelEl, _tab.items);
  }

  function _esc(s) {
    return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function _renderLog(panelEl) {
    const logEl = panelEl.querySelector(".cmdline-log");
    if (!logEl) return;
    // Smart auto-scroll: per panel element (data attribute tracks state)
    const wasAtBottom = logEl.dataset.autoScroll !== "false";
    logEl.innerHTML = _log.map(entry => {
      if (entry.source === "system") {
        return `<div class="cmdline-log__entry cmdline-log__entry--system ${entry.success !== false ? "" : "cmdline-log__entry--error"}">` +
          `<span class="cmdline-log__time">[${_esc(entry.timestamp || "")}]</span>` +
          `<span class="cmdline-log__prompt cmdline-log__prompt--sys">SYS&gt;</span>` +
          `<span class="cmdline-log__msg">${_esc(entry.command)}</span>` +
          `</div>`;
      }
      return `<div class="cmdline-log__entry ${entry.success ? "cmdline-log__entry--ok" : "cmdline-log__entry--error"}">` +
        `<span class="cmdline-log__time">[${_esc(entry.timestamp || "")}]</span>` +
        `<span class="cmdline-log__prompt">OpenCue&gt;</span>` +
        `<span class="cmdline-log__cmd">${_esc(entry.command)}</span>` +
        `<span class="cmdline-log__msg">${_esc(entry.message)}</span>` +
        `</div>`;
    }).join("");
    if (wasAtBottom) {
      requestAnimationFrame(() => logEl.scrollTo({ top: logEl.scrollHeight, behavior: "smooth" }));
    }
  }

  function _renderAllLogs() {
    document.querySelectorAll('[data-panel-type="command_line"]').forEach(_renderLog);
  }

  // Fuehrt den Eingabepuffer aus (Enter in der Befehlszeile oder "Please" im Tasten-Panel).
  function _submit() {
    const value = CommandBuffer.value.trim();
    if (!value) return;
    window.__panelAPI.sendToServer("run_command", { command: value });
    _history.push(value);
    if (_history.length > 100) _history.shift();
    _historyIndex = -1;
    _draftBeforeHistory = "";
    CommandBuffer.set("");
    _tab = null;
    _hideAllSuggestions();
  }
  window.__commandLine = { submit: _submit };

  function _recallHistory(inputEl, direction) {
    // direction: +1 = Hoch (aelter), -1 = Runter (neuer)
    if (direction > 0) {
      if (!_history.length || _historyIndex >= _history.length - 1) return;
      if (_historyIndex === -1) _draftBeforeHistory = inputEl.value;
      _historyIndex += 1;
    } else {
      if (_historyIndex === -1) return;
      _historyIndex -= 1;
    }
    inputEl.value = _historyIndex === -1 ? _draftBeforeHistory : _history[_history.length - 1 - _historyIndex];
    CommandBuffer.set(inputEl.value, inputEl);
    requestAnimationFrame(() => inputEl.setSelectionRange(inputEl.value.length, inputEl.value.length));
  }

  // Schriftfarben (Standard/Erfolg/Fehler) sind pro Panel-Instanz konfigurierbar
  // (Zahnrad -> Panel-Eigenschaften -> Modul-Einstellungen) - angewandt als
  // CSS-Variablen, die .cmdline-log__msg/--ok/--error in style.css nutzen.
  function _applyCmdlineConfig(panelEl, mc) {
    mc = mc || {};
    panelEl.style.setProperty("--cmdline-text-color", mc.text_color || "#e6e6e6");
    panelEl.style.setProperty("--cmdline-success-color", mc.success_color || "#00ff66");
    panelEl.style.setProperty("--cmdline-error-color", mc.error_color || "#ff5555");
    panelEl.style.setProperty("--cmdline-timestamp-color", mc.timestamp_color || "");
    panelEl.classList.toggle("cmdline--no-ts", mc.show_timestamp === false);
  }

  window.__panelPlugins.register({
    type: "command_line",

    buildContent(panel) {
      const wrap = document.createElement("div");
      wrap.style.cssText = "display:flex;flex-direction:column;height:100%;overflow:hidden;";

      const logEl = document.createElement("div");
      logEl.className = "cmdline-log";
      logEl.addEventListener("scroll", () => {
        const atBottom = logEl.scrollHeight - logEl.scrollTop - logEl.clientHeight < 30;
        logEl.dataset.autoScroll = String(atBottom);
      });

      const inputRow = document.createElement("div");
      inputRow.className = "cmdline-input-row";

      const suggestionsEl = document.createElement("div");
      suggestionsEl.className = "cmdline-suggestions";
      suggestionsEl.hidden = true;

      // Kleiner Schalter rechts: Vorschlaege ein/aus (die Treffflaeche ist trotzdem gross genug fuer Touch)
      const suggToggle = document.createElement("label");
      suggToggle.className = "cmdline-sugg";
      suggToggle.dataset.i18nTitle = "CMDLINE_SUGGESTIONS_TOGGLE";
      suggToggle.title = i18n("CMDLINE_SUGGESTIONS_TOGGLE");
      const suggSwitch = document.createElement("span");
      suggSwitch.className = "toggle-switch toggle-switch--mini";
      const suggInput = document.createElement("input");
      suggInput.type = "checkbox";
      suggInput.className = "cmdline-sugg__input";
      suggInput.checked = _suggestionsOn();
      suggInput.setAttribute("aria-label", i18n("CMDLINE_SUGGESTIONS_TOGGLE"));
      const suggTrack = document.createElement("span");
      suggTrack.className = "toggle-switch__track";
      suggSwitch.appendChild(suggInput);
      suggSwitch.appendChild(suggTrack);
      suggToggle.appendChild(suggSwitch);
      suggInput.addEventListener("change", () => {
        window.__cmdSuggestions = suggInput.checked;
        window.__panelAPI.sendToServer("set_cmd_suggestions", { enabled: suggInput.checked });
        window.__syncCmdSuggestions();
      });

      const promptEl = document.createElement("span");
      promptEl.className = "cmdline-prompt";
      promptEl.textContent = "OpenCue>";

      const inputEl = document.createElement("input");
      inputEl.type = "text";
      inputEl.className = "cmdline-input";
      inputEl.autocomplete = "off";
      inputEl.setAttribute("autocorrect", "off");
      inputEl.setAttribute("autocapitalize", "off");
      inputEl.spellcheck = false;
      inputEl.dataset.i18nPlaceholder = "CMDLINE_PLACEHOLDER";
      inputEl.placeholder = i18n("CMDLINE_PLACEHOLDER");

      const panelElFor = () => wrap.closest("[data-panel-type='command_line']") || wrap;

      // Das Feld zeigt den gemeinsamen Eingabepuffer und schreibt echte Tastatureingaben dorthin zurueck.
      inputEl.value = CommandBuffer.value;
      inputEl.addEventListener("input", () => { CommandBuffer.set(inputEl.value, inputEl); _tab = null; _requestSuggestions(inputEl); });
      const unsubscribe = CommandBuffer.subscribe((text, source) => {
        if (!inputEl.isConnected) { if (inputEl._seen) unsubscribe(); return; }   // Panel wurde entfernt
        inputEl._seen = true;
        if (source !== inputEl && inputEl.value !== text) inputEl.value = text;
      });

      inputEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          _submit();
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          _recallHistory(inputEl, 1);
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          _recallHistory(inputEl, -1);
        } else if (e.key === "Tab" && _suggestionsOn()) {
          e.preventDefault();
          _handleTab(inputEl, panelElFor(), e.shiftKey);
        } else if (e.key === "Escape") {
          _tab = null;
          _hideAllSuggestions();
        }
      });

      inputEl.addEventListener("focus", () => { _requestSuggestions(inputEl); });
      inputEl.addEventListener("blur", () => {
        setTimeout(() => { if (document.activeElement !== inputEl) { _tab = null; _hideSuggestions(panelElFor()); } }, 150);
      });
      suggestionsEl.addEventListener("mousedown", (e) => {            // mousedown statt click: das Feld soll den Fokus behalten
        const item = e.target.closest(".cmdline-suggestion");
        if (!item) return;
        e.preventDefault();
        const suggestion = (_tab ? _tab.items : _suggestions)[Number(item.dataset.index)];
        if (!suggestion || suggestion.info) return;
        _tab = null;
        _applySuggestion(inputEl, suggestion);
        inputEl.focus();
        _requestSuggestions(inputEl);
      });

      inputRow.appendChild(promptEl);
      inputRow.appendChild(inputEl);
      inputRow.appendChild(suggToggle);
      inputRow.appendChild(suggestionsEl);

      wrap.appendChild(logEl);
      wrap.appendChild(inputRow);

      requestAnimationFrame(() => {
        const panelEl = panelElFor();
        _applyCmdlineConfig(panelEl, panel.module_config);
        _renderLog(panelEl);
      });
      return wrap;
    },

    onModuleConfigChanged(panelEl, mc) {
      _applyCmdlineConfig(panelEl, mc);
    },

    onMessage(panelEl, messageType, payload) {
      if (messageType === "command_log") {
        _log.push({
          command: payload.command,
          success: !!payload.success,
          message: payload.message || "",
          timestamp: payload.timestamp || new Date().toLocaleTimeString(undefined, { hour12: false }),
          source: payload.source || "user",
        });
        _renderAllLogs();
      } else if (messageType === "state_snapshot") {
        if (!_systemReadyLogged) {
          _systemReadyLogged = true;
          _log.push({ command: "Application ready", success: true, message: "", timestamp: new Date().toLocaleTimeString(undefined, { hour12: false }), source: "system" });
          _renderAllLogs();
        }
      } else if (messageType === "enttec_status_changed") {
        const s = payload.status || {};
        const ts = new Date().toLocaleTimeString(undefined, { hour12: false });
        if (s.connected) {
          const key = `connected:${s.port || ""}`;
          if (key !== _lastEnttecStatus) {
            _lastEnttecStatus = key;
            _log.push({ command: `USB DMX connected: ${s.port || ""}`, success: true, message: "", timestamp: ts, source: "system" });
          }
        } else if (s.enabled) {
          const key = `not_connected:${s.error || ""}`;
          if (key !== _lastEnttecStatus) {
            _lastEnttecStatus = key;
            _log.push({ command: `USB DMX not connected${s.error ? ": " + s.error : ""}`, success: false, message: "", timestamp: ts, source: "system" });
          }
        }
        _renderAllLogs();
      } else if (messageType === "dmx_reinit_done") {
        _log.push({ command: "DMX interfaces re-initialized", success: !!payload.ok, message: "", timestamp: new Date().toLocaleTimeString(undefined, { hour12: false }), source: "system" });
        _renderAllLogs();
      }
      else if (messageType === "autocomplete_result") {
        const inputEl = panelEl.querySelector(".cmdline-input");
        if (!inputEl || inputEl !== _activeInputEl || document.activeElement !== inputEl) return;
        if (payload.text !== inputEl.value) return;                   // veraltete Antwort
        _suggestions = payload.suggestions || [];
        _suggestIndex = -1;
        _renderSuggestions(panelEl, _suggestions);
      }
      // Kein eigener "language_changed"-Zweig fuer das Platzhalter-Attribut
      // noetig: translator.setLanguage() ruft apply() VOR diesem onMessage-
      // Aufruf auf, und apply() sweept bereits jedes [data-i18n-placeholder]-
      // Element (siehe Translator.apply() - deckt auch den Seiten-Ladevorgang
      // ab, falls buildContent() vor dem Laden der Locale-Datei lief).
    },

    buildPropertiesPane: function (moduleConfig, api) {
      var mc = moduleConfig || {};
      var frag = document.createDocumentFragment();

      // Zeitstempel anzeigen
      var tsField = document.createElement("div");
      tsField.className = "modal__field modal__field--checkbox";
      var tsTgl = makeToggleSwitch("cmdline-show-timestamp", mc.show_timestamp !== false);
      var tsLabel = document.createElement("label");
      tsLabel.htmlFor = "cmdline-show-timestamp";
      tsLabel.dataset.i18n = "CMDLINE_PROP_SHOW_TIMESTAMP";
      tsLabel.textContent = api.i18n("CMDLINE_PROP_SHOW_TIMESTAMP");
      tsField.appendChild(tsTgl.label);
      tsField.appendChild(tsLabel);
      frag.appendChild(tsField);

      // Farbfelder
      [
        { key: "CMDLINE_PROP_TIMESTAMP_COLOR", sw: "cmdline-ts-color-sw",      hex: "cmdline-ts-color-hex",      cfgKey: "timestamp_color", def: "#888888" },
        { key: "CMDLINE_PROP_TEXT_COLOR",      sw: "cmdline-text-color-sw",     hex: "cmdline-text-color-hex",    cfgKey: "text_color",       def: "#e6e6e6" },
        { key: "CMDLINE_PROP_SUCCESS_COLOR",   sw: "cmdline-success-color-sw",  hex: "cmdline-success-color-hex", cfgKey: "success_color",    def: "#00ff66" },
        { key: "CMDLINE_PROP_ERROR_COLOR",     sw: "cmdline-error-color-sw",    hex: "cmdline-error-color-hex",   cfgKey: "error_color",      def: "#ff5555" },
      ].forEach(function (item) {
        var row = document.createElement("div");
        row.className = "modal__field";
        var lbl = document.createElement("label");
        lbl.dataset.i18n = item.key;
        lbl.textContent = api.i18n(item.key);
        var swEl = document.createElement("input");
        swEl.type = "color";
        swEl.id = item.sw;
        swEl.className = "color-swatch-input";
        swEl.value = mc[item.cfgKey] || item.def;
        var hexEl = document.createElement("input");
        hexEl.type = "text";
        hexEl.id = item.hex;
        hexEl.className = "color-hex-input";
        hexEl.maxLength = 7;
        hexEl.value = mc[item.cfgKey] || item.def;
        row.appendChild(lbl);
        row.appendChild(swEl);
        row.appendChild(hexEl);
        frag.appendChild(row);
      });

      return frag;
    },

    afterPropertiesPaneInserted: function (paneEl, targetPanelId, api) {
      var panelEl = document.querySelector('[data-panel-id="' + targetPanelId + '"]');
      [
        { sw: "cmdline-ts-color-sw",      hex: "cmdline-ts-color-hex",      cssVar: "--cmdline-timestamp-color" },
        { sw: "cmdline-text-color-sw",     hex: "cmdline-text-color-hex",    cssVar: "--cmdline-text-color" },
        { sw: "cmdline-success-color-sw",  hex: "cmdline-success-color-hex", cssVar: "--cmdline-success-color" },
        { sw: "cmdline-error-color-sw",    hex: "cmdline-error-color-hex",   cssVar: "--cmdline-error-color" },
      ].forEach(function (item) {
        api.wireColorPair(item.sw, item.hex, function (value) {
          if (panelEl) panelEl.style.setProperty(item.cssVar, value);
        });
      });
      var tsTgl = paneEl.querySelector("#cmdline-show-timestamp");
      if (tsTgl) {
        tsTgl.addEventListener("change", function () {
          if (panelEl) panelEl.classList.toggle("cmdline--no-ts", !tsTgl.checked);
        });
      }
    },

    readPropertiesPane: function () {
      return {
        show_timestamp:  document.getElementById("cmdline-show-timestamp")?.checked !== false,
        timestamp_color: document.getElementById("cmdline-ts-color-hex")?.value || "#888888",
        text_color:      document.getElementById("cmdline-text-color-hex")?.value || "#e6e6e6",
        success_color:   document.getElementById("cmdline-success-color-hex")?.value || "#00ff66",
        error_color:     document.getElementById("cmdline-error-color-hex")?.value || "#ff5555",
      };
    },
  });

})();

// ---- Command Numpad & Command Buttons Panels -------------------------------
// Two independent, self-contained panels: a compact 4x5 numpad grid (digits/syntax/Please) and a fully responsive
// flat grid of keyword buttons. Both write into the shared CommandBuffer (see above) - they never touch or focus a
// text field, so tapping them cannot open the on-screen keyboard. Digits/period: appended directly (no space).
// Keywords/operators: with spaces. Please = execute, Clear = execute immediately (empty buffer) or append keyword.
(() => {

  // Digits and period are appended without spaces; everything else gets spaces.
  const NO_SPACE = new Set(["0","1","2","3","4","5","6","7","8","9","."]);

  const _appendDirect = (char) => CommandBuffer.append(char);
  const _appendKeyword = (kw) => CommandBuffer.appendKeyword(kw);
  const _backspace = () => CommandBuffer.backspace();
  const _please = () => { if (window.__commandLine) window.__commandLine.submit(); };

  function _clear() {
    if (!CommandBuffer.value.trim()) {
      CommandBuffer.set("Clear");
      _please();
    } else {
      _appendKeyword("Clear");
    }
  }

  function _makeButton(def) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "cmdbtn";
    if (typeof def === "string") {
      btn.textContent = def;
      const titleKey = KEYWORD_TITLE_KEYS[def];
      if (titleKey) {
        btn.dataset.i18nTitle = titleKey;
        btn.title = i18n(titleKey);
      }
      btn.addEventListener("click", NO_SPACE.has(def)
        ? () => _appendDirect(def)
        : () => _appendKeyword(def));
    } else {
      const isI18nKey = def.label && def.label.toUpperCase() === def.label && def.label.length > 3;
      if (isI18nKey) {
        btn.dataset.i18n = def.label;
        btn.textContent = i18n(def.label);
      } else {
        btn.textContent = def.label || "";
      }
      if (def.cls) btn.classList.add(def.cls);
      if      (def.action === "please")    btn.addEventListener("click", _please);
      else if (def.action === "backspace") btn.addEventListener("click", _backspace);
      else if (def.action === "clear")     btn.addEventListener("click", _clear);
      else if (def.action === "blackout")  btn.addEventListener("click", () => window.__panelAPI.sendToServer("set_blackout", {}));      // sofort umschalten (wie der Befehl "Blackout")
      else                                 btn.addEventListener("click", () => _appendKeyword(def.label || ""));
    }
    return btn;
  }

  function _langChangeHandler(panelEl, messageType) {
    if (messageType === "language_changed") {
      panelEl.querySelectorAll("[data-i18n]").forEach(el => {
        el.textContent = i18n(el.dataset.i18n);
      });
      panelEl.querySelectorAll("[data-i18n-title]").forEach(el => {
        el.title = i18n(el.dataset.i18nTitle);
      });
    }
  }

  // ---- Panel 1: Command Numpad ---------------------------------------------
  // Fixed 4x5 grid (digits/syntax rows + full-width Please row) that fills
  // the panel proportionally via grid-template-rows/columns: repeat(N, 1fr) -
  // no clipped buttons, no leftover empty space regardless of panel size.
  const NUMPAD_ROWS = [
    ["7", "8", "9", "+"],
    ["4", "5", "6", "Thru"],
    ["1", "2", "3", "-"],
    ["0", ".", "At", { label: "←", action: "backspace", cls: "cmdbtn--back" }],
  ];

  window.__panelPlugins.register({
    type: "command_numpad",

    buildContent() {
      const grid = document.createElement("div");
      grid.className = "cnp";
      // Ohne Befehlszeilen-Panel im Layout waere unsichtbar, was man tippt: dann zeigt das Tasten-Panel selbst eine
      // schmale Anzeige (Puffer + kurzes Ergebnis des letzten Befehls). Mit Befehlszeilen-Panel bleibt sie versteckt.
      const display = document.createElement("div");
      display.className = "cnp__display";
      display.setAttribute("role", "status");
      grid.appendChild(display);
      let resultTimer = null;
      const hasCommandLine = () => !!document.querySelector("[data-panel-type='command_line']");
      const refresh = () => {
        if (!grid.isConnected) { if (grid._seen) { unsubscribe(); document.removeEventListener("panels-rendered", refresh); } return; }
        grid._seen = true;
        const standalone = !hasCommandLine();
        grid.classList.toggle("cnp--standalone", standalone);
        if (!standalone || display.dataset.result) return;
        display.textContent = "";
        const prompt = document.createElement("span");
        prompt.className = "cnp__prompt";
        prompt.textContent = "OpenCue>";
        const text = document.createElement("span");
        text.className = "cnp__text";
        text.textContent = CommandBuffer.value;
        display.append(prompt, text);
      };
      const unsubscribe = CommandBuffer.subscribe(refresh);
      document.addEventListener("panels-rendered", refresh);
      grid._showResult = (ok, message) => {
        if (!grid.classList.contains("cnp--standalone")) return;
        display.dataset.result = "1";
        display.textContent = message;
        display.classList.toggle("cnp__display--error", !ok);
        clearTimeout(resultTimer);
        resultTimer = setTimeout(() => { delete display.dataset.result; display.classList.remove("cnp__display--error"); refresh(); }, 2500);
      };
      requestAnimationFrame(refresh);
      for (const row of NUMPAD_ROWS) {
        for (const def of row) {
          grid.appendChild(_makeButton(def));
        }
      }
      const pleaseBtn = _makeButton({ label: "KEYPAD_PLEASE", action: "please", cls: "cmdbtn--please" });
      grid.appendChild(pleaseBtn);
      return grid;
    },

    onMessage(panelEl, messageType, payload) {
      _langChangeHandler(panelEl, messageType);
      if (messageType === "command_log" && payload && payload.source !== "system") {
        const grid = panelEl.querySelector(".cnp");
        if (grid && grid._showResult) grid._showResult(!!payload.success, `${payload.command} ${payload.success ? "→ OK" : "→ " + (payload.message || "")}`.trim());
      }
    },
  });

  // ---- Panel 2: Command Buttons ---------------------------------------------
  // Flat list of all keyword buttons in a responsive CSS grid
  // (auto-fit/minmax) - wraps cleanly into as many columns/rows as fit,
  // never clipping a button regardless of window size.
  const BUTTON_KEYWORDS = [
    "Fixture", "Group", "Cue", "Exec",
    "Store", "Edit", "Delete", "Move", "Label",
    { label: "Clear", action: "clear", cls: "cmdbtn--clear" },
    "Full", "Color", "Pan", "Tilt", "Master", "Go", "Off",
    { label: "Blackout", action: "blackout", cls: "cmdbtn--blackout" },
  ];

  // Befehlswoerter bleiben englisch (der Parser kennt nur diese Schreibweise);
  // uebersetzt wird nur der Hinweistext beim Ueberfahren.
  const KEYWORD_TITLE_KEYS = { Master: "CMDBTN_MASTER_TITLE" };

  window.__panelPlugins.register({
    type: "command_buttons",

    buildContent() {
      const grid = document.createElement("div");
      grid.className = "cbtn";
      for (const def of BUTTON_KEYWORDS) {
        grid.appendChild(_makeButton(def));
      }
      requestAnimationFrame(() => { if (window.__syncBlackout) window.__syncBlackout(); });
      return grid;
    },

    onMessage: _langChangeHandler,
  });

})();

// ---- Effekt-Studio (Skripte in einer C++/Arduino-aehnlichen Sprache) ----------------------------------------------
// Editor fuer Effekt-Skripte (.fx; Sprache und Anleitung: static/help/effect-studio.de.md bzw. .en.md, auch ueber den Knopf "Hilfe"). Der Server speichert, laedt und
// prueft die Dateien (app/fx_script.py, Sprache in app/fxlang.py). Aufbau:
//  - Werkzeugleiste: Oeffnen / Neu (jeweils ein Dialog), Speichern, Speichern unter, Loeschen, Hilfe, Vorschau
//  - Editor mit Farbhervorhebung (durchsichtiges Textfeld ueber einer gefaerbten Kopie), Zeilennummern, Fehlerzeile; alle Befehle stehen in der Hilfe (Knopf "Hilfe")
//  - Vorschau: der Server rechnet das Skript beim Tippen ohne Scheinwerfer durch (fx_script_preview) und liefert die Kurven genau im #RATE-Raster;
//    Standard: 1 Scheinwerfer, 2 Sekunden. Dieselbe Antwort meldet Fehler mit Zeilennummer.
(() => {
  const RATE_MIN = 1;
  const RATE_MAX = 40;
  const T = (key, vars) => {
    let s = i18n(key);
    if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
    return s;
  };
  const studios = new Set();
  const model = new WeakMap();       // Studio-Wurzel -> Zustand
  let files = [];
  let previewSeq = 0;
  let onFilesChanged = null;         // der offene "Oeffnen"-Dialog zeichnet sich bei neuer Dateiliste neu

  function send(type, payload) {
    if (window.__panelAPI && typeof window.__panelAPI.sendToServer === "function") window.__panelAPI.sendToServer(type, payload || {});
  }
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  const $ = (id) => document.getElementById(id);
  const textOf = (root) => root.querySelector(".fxs-text").value;
  const isDirty = (root) => { const st = model.get(root); return !!st && textOf(root) !== st.savedText; };
  const toast = (key, type, vars) => _showToast(T(key, vars), type || "success", type === "error" ? 5000 : 3000);

  // ------------------------------------------------------------------------------------------ Vorlagen fuer "Neu"
  const SPEED = "#VAR speed Slider 1 0.05 8 0.05";
  const SIZE = "#VAR size Slider 100 0 100 1";
  const SPREAD = "#VAR spread Slider 0 0 1 0.05";
  const head = (cat, key, rate, vars) => `#NAME ${T("FXS_TPL_" + key)}\n#DESCRIPTION ${T("FXS_TPL_" + key + "_D")}\n#CATEGORY ${cat}\n#RATE ${rate}\n${vars.join("\n")}\n\n`;
  const TEMPLATES = {
    dimmer: [
      { id: "EMPTY", code: (r) => head("dimmer", "DIMMER_EMPTY", r, [SPEED]) + "loop() {\n  dimmer = 100;\n}\n" },
      { id: "SINE", code: (r) => head("dimmer", "DIMMER_SINE", r, [SPEED, SIZE, SPREAD]) + "loop() {\n  dimmer = size * (0.5 + 0.5 * sin(2 * PI * (speed * elapsed + index * spread)));\n}\n" },
      { id: "PULSE", code: (r) => head("dimmer", "DIMMER_PULSE", r, [SPEED, SIZE, "#VAR duty Slider 0.25 0.05 1 0.05", SPREAD]) + "loop() {\n  float p = fract(speed * elapsed + index * spread);\n  dimmer = p < duty ? size : 0;\n}\n" },
      { id: "CHASE", code: (r) => head("dimmer", "DIMMER_CHASE", r, [SPEED, "#VAR width Slider 1 0.5 8 0.5"]) + "loop() {\n  float pos = fract(speed * elapsed) * count;   // aktueller Schritt\n  float d = abs(index - pos);\n  if (d > count / 2) d = count - d;                // Abstand auf dem Kreis\n  dimmer = d < width ? 100 : 0;\n}\n" },
      { id: "FLICKER", code: (r) => head("dimmer", "DIMMER_FLICKER", r, [SPEED, SIZE]) + "float level = 0;\nfloat target = 0;\n\nloop() {\n  if (tick % max(1, round(rate / speed)) == 0) {\n    target = random(0, size);\n  }\n  level += (target - level) * 0.3;\n  dimmer = level;\n}\n" },
    ],
    color: [
      { id: "EMPTY", code: (r) => head("color", "COLOR_EMPTY", r, [SPEED]) + "loop() {\n  r = 255;\n  g = 255;\n  b = 255;\n}\n" },
      { id: "RAINBOW", code: (r) => head("color", "COLOR_RAINBOW", r, [SPEED, SIZE, SPREAD]) + "loop() {\n  hsv(speed * elapsed + index * spread, 1, size / 100);\n}\n" },
      { id: "TWO", code: (r) => head("color", "COLOR_TWO", r, [SPEED, SPREAD, "#VAR color_a ColorPicker #ff0000", "#VAR color_b ColorPicker #0000ff"]) + "loop() {\n  float mix = 0.5 + 0.5 * sin(2 * PI * (speed * elapsed + index * spread));\n  r = color_a_r * (1 - mix) + color_b_r * mix;\n  g = color_a_g * (1 - mix) + color_b_g * mix;\n  b = color_a_b * (1 - mix) + color_b_b * mix;\n}\n" },
      { id: "RANDOM", code: (r) => head("color", "COLOR_RANDOM", r, [SPEED]) + "float hue = 0;\n\nloop() {\n  if (tick % max(1, round(rate / speed)) == 0) {\n    hue = random();\n  }\n  hsv(hue, 1, 1);\n}\n" },
    ],
    position: [
      { id: "EMPTY", code: (r) => head("position", "POS_EMPTY", r, [SPEED]) + "loop() {\n  pan = 50;\n  tilt = 50;\n}\n" },
      { id: "CIRCLE", code: (r) => head("position", "POS_CIRCLE", r, [SPEED, "#VAR size Slider 40 0 50 1", SPREAD]) + "loop() {\n  float a = 2 * PI * (speed * elapsed + index * spread);\n  pan = 50 + size * cos(a);\n  tilt = 50 + size * sin(a);\n}\n" },
      { id: "EIGHT", code: (r) => head("position", "POS_EIGHT", r, [SPEED, "#VAR size Slider 40 0 50 1", SPREAD]) + "loop() {\n  float a = 2 * PI * (speed * elapsed + index * spread);\n  pan = 50 + size * sin(a);\n  tilt = 50 + size * sin(2 * a) / 2;\n}\n" },
      { id: "RANDOM", code: (r) => head("position", "POS_RANDOM", r, [SPEED, "#VAR size Slider 40 0 50 1"]) + "float px = 50;\nfloat py = 50;\nfloat tx = 50;\nfloat ty = 50;\n\nloop() {\n  if (tick % max(1, round(rate / speed)) == 0) {\n    tx = 50 + random(-size, size);\n    ty = 50 + random(-size, size);\n  }\n  px += (tx - px) * 0.15;\n  py += (ty - py) * 0.15;\n  pan = px;\n  tilt = py;\n}\n" },
    ],
  };
  const CATEGORY_ICON = { dimmer: "bulb", color: "drop", position: "move", zoom: "scale", focus: "eye", gobo: "wheel" };
  const LOW = "#VAR low Slider 0 0 100 1";
  const HIGH = "#VAR high Slider 100 0 100 1";
  Object.assign(TEMPLATES, {
    zoom: [
      { id: "EMPTY", code: (r) => head("zoom", "ZOOM_EMPTY", r, [SPEED]) + "loop() {\n  zoom = 50;\n}\n" },
      { id: "PULSE", code: (r) => head("zoom", "ZOOM_PULSE", r, [SPEED, LOW, HIGH, SPREAD]) + "loop() {\n  float k = 0.5 + 0.5 * sin(2 * PI * (speed * elapsed + index * spread));\n  zoom = lerp(low, high, k);\n}\n" },
      { id: "SWEEP", code: (r) => head("zoom", "ZOOM_SWEEP", r, [SPEED, LOW, HIGH, SPREAD]) + "loop() {\n  zoom = lerp(low, high, tri(speed * elapsed + index * spread));\n}\n" },
      { id: "BEAT", code: (r) => head("zoom", "ZOOM_BEAT", r, [SPEED, LOW, HIGH, SPREAD]) + "loop() {\n  float p = fract(speed * elapsed + index * spread);\n  zoom = lerp(low, high, pow(1 - p, 3));\n}\n" },
    ],
    focus: [
      { id: "EMPTY", code: (r) => head("focus", "FOCUS_EMPTY", r, [SPEED]) + "loop() {\n  focus = 50;\n}\n" },
      { id: "BREATHE", code: (r) => head("focus", "FOCUS_BREATHE", r, [SPEED, LOW, HIGH, SPREAD]) + "loop() {\n  float k = 0.5 + 0.5 * sin(2 * PI * (speed * elapsed + index * spread));\n  focus = lerp(low, high, k);\n}\n" },
      { id: "SWEEP", code: (r) => head("focus", "FOCUS_SWEEP", r, [SPEED, LOW, HIGH, SPREAD]) + "loop() {\n  focus = lerp(low, high, tri(speed * elapsed + index * spread));\n}\n" },
    ],
    gobo: [
      { id: "EMPTY", code: (r) => head("gobo", "GOBO_EMPTY", r, [SPEED]) + "loop() {\n  gobo = slot(0);          // erstes Gobo des Geräts (meist offen)\n}\n" },
      { id: "CYCLE", code: (r) => head("gobo", "GOBO_CYCLE", r, ["#VAR speed Slider 0.5 0.05 8 0.05", "#VAR first Slider 0 0 20 1"]) + "loop() {\n  float n = max(1, slots - first);                      // slots = Anzahl der Gobos des Geräts\n  gobo = slot(first + mod(floor(speed * elapsed), n));\n}\n" },
      { id: "ALTERNATE", code: (r) => head("gobo", "GOBO_ALTERNATE", r, ["#VAR speed Slider 0.5 0.05 8 0.05", "#VAR slot_a Slider 0 0 20 1", "#VAR slot_b Slider 1 0 20 1"]) + "loop() {\n  gobo = fract(speed * elapsed) < 0.5 ? slot(slot_a) : slot(slot_b);\n}\n" },
    ],
  });
  const tplKey = (category, id) => (category === "position" ? "POS" : category.toUpperCase()) + "_" + id;

  // Kategorien: kommen vom Server (/api/effects -> categories; Tabelle app/fx_categories.py). Das Studio kennt nur die drei Vorlagen-Gruppen; jede weitere Kategorie
  // bekommt eine "Leer"-Vorlage, die ihre Ausgaben auf den Neutralwert setzt, und erscheint ohne weiteren Code im Neu-Dialog.
  let categories = [
    { name: "dimmer", outputs: [{ name: "dimmer", neutral: 0 }] },
    { name: "color", outputs: [{ name: "r", neutral: 0 }, { name: "g", neutral: 0 }, { name: "b", neutral: 0 }] },
    { name: "position", outputs: [{ name: "pan", neutral: 50 }, { name: "tilt", neutral: 50 }] },
  ];
  const categoryInfo = (name) => categories.find((c) => c.name === name) || { name, outputs: [] };
  function templatesFor(name) {
    if (TEMPLATES[name]) return TEMPLATES[name];
    const lines = categoryInfo(name).outputs.map((o) => `  ${o.name} = ${o.neutral};`).join("\n");
    return [{ id: "EMPTY", generic: true, code: (r) => `#NAME ${T("FXS_TPL_GENERIC_EMPTY")}\n#CATEGORY ${name}\n#RATE ${r}\n${SPEED}\n\nloop() {\n${lines}\n}\n` }];
  }

  // ------------------------------------------------------------------------------------------ Farbhervorhebung
  const KEYWORDS = new Set(["if", "else", "for", "while", "do", "break", "continue", "return", "const"]);
  const TYPES = new Set(["float", "double", "int", "long", "short", "byte", "bool", "boolean", "void"]);
  const CONSTANTS = new Set(["PI", "TWO_PI", "HALF_PI", "E", "true", "false", "HIGH", "LOW"]);
  const SYSTEM = new Set(["t", "elapsed", "dt", "tick", "loop_count", "rate", "index", "count", "phase"]);
  const OUTPUTS = new Set(["dimmer", "r", "g", "b", "pan", "tilt"]);          // wird aus den Kategorien des Servers ergaenzt
  const FUNCTION_NAMES = new Set(["sin", "cos", "tan", "asin", "acos", "atan", "atan2", "sqrt", "pow", "exp", "log", "abs", "sign", "min", "max", "floor", "ceil", "round",
    "fract", "mod", "constrain", "map", "lerp", "smoothstep", "saw", "tri", "square", "radians", "degrees", "random", "hsv"]);
  const HL_RE = /(\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|(?![\s\S])))|(^[ \t]*#[A-Za-z]+[^\n]*)|(\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+)|([A-Za-z_][A-Za-z0-9_]*)/gm;
  const escapeHtml = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  function paramNames(text) {
    const names = new Set();
    for (const m of text.matchAll(/^[ \t]*#VAR[ \t]+([A-Za-z_]\w*)[ \t]+(\w+)/gm)) {
      if (m[2] === "ColorPicker") ["r", "g", "b"].forEach((c) => names.add(`${m[1]}_${c}`));
      else names.add(m[1]);
    }
    return names;
  }

  /** Kopfzeile (#NAME, #VAR ...): Schluesselwort, Name, Typ und Zahlen eigens gefaerbt, Freitext (Name, Beschreibung) schlicht. */
  function headerHtml(line) {
    const m = /^([ \t]*)(#[A-Za-z]+)([\s\S]*)$/.exec(line);
    const word = m[2].toUpperCase();
    let rest;
    if (word === "#VAR") {
      let position = 0;
      rest = m[3].replace(/(\s+)|(\S+)/g, (all, space, token) => {
        if (space) return space;
        position++;
        const cls = position === 1 ? "hl-param" : position === 2 ? "hl-type" : "hl-num";
        return `<span class="${cls}">${escapeHtml(token)}</span>`;
      });
    } else if (word === "#CATEGORY" || word === "#RATE") {
      rest = m[3].replace(/(\S+)/g, (token) => `<span class="${word === "#RATE" ? "hl-num" : "hl-type"}">${escapeHtml(token)}</span>`);
    } else {
      rest = escapeHtml(m[3]);
    }
    return escapeHtml(m[1]) + `<span class="hl-dir">${escapeHtml(m[2])}</span>` + rest;
  }

  /** Text -> HTML mit <span class="hl-...">; alles andere bleibt unveraendert (wird maskiert). */
  function highlight(text) {
    const params = paramNames(text);
    let out = "";
    let last = 0;
    for (const m of text.matchAll(HL_RE)) {
      out += escapeHtml(text.slice(last, m.index));
      last = m.index + m[0].length;
      const word = m[0];
      let cls = "";
      if (m[2] !== undefined) { out += headerHtml(word); continue; }
      if (m[1] !== undefined) cls = "hl-com";
      else if (m[3] !== undefined) cls = "hl-num";
      else {
        const next = text[last] === "(" || /^[ \t]*\(/.test(text.slice(last, last + 8));
        if (KEYWORDS.has(word)) cls = "hl-kw";
        else if (TYPES.has(word)) cls = "hl-type";
        else if (CONSTANTS.has(word)) cls = "hl-const";
        else if (OUTPUTS.has(word)) cls = "hl-out";
        else if (SYSTEM.has(word)) cls = "hl-sys";
        else if (next && FUNCTION_NAMES.has(word)) cls = "hl-fn";
        else if (next && (word === "loop" || word === "setup")) cls = "hl-fn2";
        else if (params.has(word)) cls = "hl-param";
      }
      out += cls ? `<span class="${cls}">${escapeHtml(word)}</span>` : escapeHtml(word);
    }
    return out + escapeHtml(text.slice(last));
  }

  // ------------------------------------------------------------------------------------------ Mini-Markdown fuer die Hilfe
  function inlineNodes(text) {
    const nodes = [];
    for (const part of text.split(/(`[^`]+`|\*\*[^*]+\*\*)/)) {
      if (!part) continue;
      if (part.startsWith("`")) nodes.push(el("code", "fxs-md-code-inline", part.slice(1, -1)));
      else if (part.startsWith("**")) nodes.push(el("strong", "", part.slice(2, -2)));
      else nodes.push(document.createTextNode(part));
    }
    return nodes;
  }
  function renderMarkdown(markdown) {
    const root = el("div", "fxs-md");
    const lines = markdown.replace(/\r/g, "").split("\n");
    let i = 0;
    const slug = (s) => s.toLowerCase().replace(/[^a-z0-9äöüß]+/g, "-").replace(/^-|-$/g, "");
    while (i < lines.length) {
      const line = lines[i];
      if (/^```/.test(line)) {
        const code = [];
        i++;
        while (i < lines.length && !/^```/.test(lines[i])) code.push(lines[i++]);
        i++;
        const pre = el("pre", "fxs-md-pre");
        pre.innerHTML = highlight(code.join("\n"));
        root.appendChild(pre);
      } else if (/^#{1,4}\s/.test(line)) {
        const level = line.match(/^#+/)[0].length;
        const heading = el("h" + level);
        heading.id = "fxs-h-" + slug(line.replace(/^#+\s*/, ""));
        heading.append(...inlineNodes(line.replace(/^#+\s*/, "")));
        root.appendChild(heading);
        i++;
      } else if (/^\|/.test(line)) {
        const rows = [];
        while (i < lines.length && /^\|/.test(lines[i])) rows.push(lines[i++]);
        const cells = (row) => row.replace(/\\\|/g, "\u0001").replace(/^\||\|$/g, "").split("|").map((c) => c.replace(/\u0001/g, "|").trim());
        const table = el("table", "fxs-md-table");
        const header = cells(rows[0]);
        const thead = el("tr");
        header.forEach((c) => { const th = el("th"); th.append(...inlineNodes(c)); thead.appendChild(th); });
        table.appendChild(thead);
        rows.slice(/^\|[\s:|-]+\|?$/.test(rows[1] || "") ? 2 : 1).forEach((row) => {
          const tr = el("tr");
          cells(row).forEach((c) => { const td = el("td"); td.append(...inlineNodes(c)); tr.appendChild(td); });
          table.appendChild(tr);
        });
        root.appendChild(table);
      } else if (/^\s*([-*]|\d+\.)\s/.test(line)) {
        const ordered = /^\s*\d+\./.test(line);
        const list = el(ordered ? "ol" : "ul");
        while (i < lines.length && /^\s*([-*]|\d+\.)\s/.test(lines[i])) {
          const item = el("li");
          item.append(...inlineNodes(lines[i].replace(/^\s*([-*]|\d+\.)\s+/, "")));
          list.appendChild(item);
          i++;
        }
        root.appendChild(list);
      } else if (/^---+\s*$/.test(line)) {
        root.appendChild(el("hr"));
        i++;
      } else if (line.trim() === "") {
        i++;
      } else {
        const para = [];
        while (i < lines.length && lines[i].trim() !== "" && !/^(```|#{1,4}\s|\||\s*([-*]|\d+\.)\s|---)/.test(lines[i])) para.push(lines[i++]);
        const p = el("p");
        p.append(...inlineNodes(para.join(" ")));
        root.appendChild(p);
      }
    }
    return root;
  }

  // ------------------------------------------------------------------------------------------ Dialoge
  const catLabel = (name) => { const key = "FXS_CAT_" + String(name).toUpperCase(); const s = i18n(key); return s === key ? name : s; };
  const catDescription = (name) => {
    const key = "FXS_CAT_" + String(name).toUpperCase() + "_D";
    const s = i18n(key);
    return s === key ? T("FXS_CAT_OUTPUTS", { list: categoryInfo(name).outputs.map((o) => o.name).join(", ") }) : s;
  };
  const tag = (category) => el("span", "fxs-tag fxs-tag--" + category, catLabel(category));
  const sortedFiles = () => files.slice().sort((a, b) => (b.favorite ? 1 : 0) - (a.favorite ? 1 : 0) || String(a.name).localeCompare(String(b.name), undefined, { sensitivity: "base", numeric: true }));

  /** Dialog "Effekt oeffnen" im Stil des Panel-Dialogs: links die Kategorien (Alle, Lieblinge, je Kategorie mit Anzahl), rechts Suche und ein Raster aus
   *  Karten (Symbol, Name, Beschreibung, Rate/Herkunft, Standard-Kennzeichnung). Klick auf eine Karte oeffnet den Effekt, Stern = Liebling, Papierkorb loescht.
   *  Die Zahlen links folgen der Suche. Liefert den Namen oder null. */
  function chooseEffect() {
    return _modalResult("fxs-open", null, (finish, listen) => {
      const body = $("fxs-open-body");
      const footer = $("fxs-open-footer");
      body.textContent = "";
      footer.textContent = "";
      const view = { category: "all" };
      const catList = el("div", "addpanel__cats fxs-open__cats");
      const main = el("div", "addpanel__main");
      const searchBox = el("label", "addpanel__search");
      searchBox.appendChild(Icons.svg("search"));
      const search = el("input", "addpanel__input fxs-open__search");
      search.type = "search";
      search.autocomplete = "off";
      search.spellcheck = false;
      search.placeholder = T("FXS_OPEN_SEARCH");
      searchBox.appendChild(search);
      const list = el("div", "fxs-open__list");
      main.append(searchBox, list);
      body.append(catList, main);
      const restore = el("button", "modal__button", T("FXS_OPEN_RESTORE"));
      restore.type = "button";
      restore.title = T("FM_RESTORE_FX_INFO");
      const close = el("button", "modal__button", T("CLOSE"));
      close.type = "button";
      close.dataset.modalCancel = "fxs-open";
      footer.append(restore, close);

      const matches = (f, q) => !q || [f.name, f.label, f.description, f.category].some((x) => String(x || "").toLowerCase().includes(q));
      const entries = () => [
        { id: "all", icon: "fx", label: T("FXS_OPEN_ALL"), test: () => true },
        { id: "favorites", icon: "star", label: T("FXS_OPEN_FAVORITES"), test: (f) => !!f.favorite },
        ...categories.map((c) => ({ id: c.name, icon: CATEGORY_ICON[c.name] || "fx", label: catLabel(c.name), test: (f) => f.category === c.name })),
      ];
      const render = () => {
        const q = search.value.trim().toLowerCase();
        const found = files.filter((f) => matches(f, q));
        const all = entries();
        if (!all.some((e) => e.id === view.category)) view.category = "all";
        catList.textContent = "";
        for (const entry of all) {
          const btn = el("button", "addpanel__cat");
          btn.type = "button";
          btn.dataset.cat = entry.id;
          btn.setAttribute("aria-pressed", entry.id === view.category ? "true" : "false");
          btn.append(Icons.svg(entry.icon), el("span", "addpanel__cat-label", entry.label), el("span", "addpanel__count", String(found.filter(entry.test).length)));
          btn.addEventListener("click", () => { view.category = entry.id; render(); });
          catList.appendChild(btn);
        }
        const current = all.find((e) => e.id === view.category);
        const rows = sortedFiles().filter((f) => matches(f, q) && current.test(f));
        list.textContent = "";
        if (!rows.length) {
          list.appendChild(el("div", "fxs-open__empty", T(q ? "FXS_OPEN_NO_MATCH" : view.category === "favorites" ? "FXS_OPEN_NO_FAVORITES" : "FXS_NO_FILES")));
          return;
        }
        for (const f of rows) {
          const row = el("div", "fxs-open__row" + (f.ok ? "" : " fxs-open__row--error"));
          row.dataset.name = f.name;
          row.tabIndex = 0;
          const icon = Icons.svg(CATEGORY_ICON[f.category] || "fx");
          icon.classList.add("fxs-open__icon", "fxs-cat--" + (f.category || "none"));
          const text = el("div", "fxs-open__text");
          const title = el("div", "fxs-open__name");
          title.append(el("span", "fxs-open__title", f.name));
          if (f.default) {
            const badge = el("span", "fxs-badge", T("FXS_BADGE_DEFAULT"));
            if (f.default_modified) badge.title = T("FXS_DEFAULT_MODIFIED");
            title.appendChild(badge);
          }
          text.appendChild(title);
          if (f.label && f.label !== f.name) text.appendChild(el("div", "fxs-open__label", f.label));
          text.appendChild(el("div", "fxs-open__desc", f.ok ? (f.description || "") : (f.line ? `${T("FXS_LINE", { line: f.line })}: ${f.message}` : f.message)));
          const meta = el("div", "fxs-open__meta");
          if (f.category) meta.appendChild(tag(f.category));
          if (f.rate) meta.appendChild(el("span", "fxs-open__rate", T("FXS_RATE_SHORT", { n: f.rate })));
          meta.appendChild(el("span", "fxs-open__origin", T("FXS_ORIGIN_" + String(f.origin || "user").toUpperCase())));
          text.appendChild(meta);
          const acts = el("div", "fxs-open__acts");
          const star = el("button", "fxs-open__act fxs-open__fav" + (f.favorite ? " fxs-open__fav--on" : ""));
          star.type = "button";
          star.title = T(f.favorite ? "FXS_UNFAVORITE" : "FXS_FAVORITE");
          star.appendChild(Icons.svg("star"));
          star.addEventListener("click", (e) => { e.stopPropagation(); send("fx_script_favorite", { name: f.name }); });
          const del = el("button", "fxs-open__act fxs-open__del");
          del.type = "button";
          del.title = f.origin === "user" ? T("FXS_DELETE") : T("FXS_DELETE_FORBIDDEN");
          del.disabled = f.origin !== "user";
          del.appendChild(Icons.svg("trash"));
          del.addEventListener("click", async (e) => {
            e.stopPropagation();
            if (!(await _askLayoutConfirm({ title: T("FXS_DELETE_TITLE"), body: T("FXS_DELETE_BODY", { name: f.name }), confirmKey: "FXS_DELETE_OK" }))) return;
            await deleteFile(f.name);
          });
          acts.append(star, del);
          row.append(icon, text, acts);
          row.addEventListener("click", () => finish(f.name));
          row.addEventListener("keydown", (e) => { if (e.key === "Enter") finish(f.name); });
          list.appendChild(row);
        }
      };
      onFilesChanged = render;
      listen(search, "input", render);
      listen(restore, "click", async () => {
        const result = await fetch("/api/files/effects/restore-defaults", { method: "POST" }).then((r) => r.json()).catch(() => null);
        if (!result || !result.ok) { toast("FXS_ERROR", "error"); return; }
        const { restored = [], modified = [] } = result;
        if (restored.length) toast("FM_RESTORED", "success", { n: restored.length, list: restored.join(", ") }); else toast("FM_RESTORE_NONE");
        if (modified.length) toast("FM_RESTORE_MODIFIED", "success", { n: modified.length, list: modified.join(", ") });
        send("fx_script_list");
      });
      send("fx_script_list");
      render();
      setTimeout(() => search.focus(), 60);
    }).then((value) => { onFilesChanged = null; return value; });
  }

  /** Loescht eine Effekt-Datei (Benutzerordner). Zeigt ein Studio sie gerade, wird sein Editor leer. */
  async function deleteFile(name) {
    try {
      const res = await fetch("/api/effects/" + encodeURIComponent(name), { method: "DELETE" });
      if (!res.ok) { toast({ 403: "FXS_DELETE_FORBIDDEN", 404: "FXS_NOT_FOUND" }[res.status] || "FXS_ERROR", "error"); return false; }
    } catch (err) {
      toast("FXS_ERROR", "error");
      return false;
    }
    studios.forEach((root) => {
      const st = model.get(root);
      if (root.isConnected && st && st.name === name) setScript(root, { name: null, origin: "", text: "" });
    });
    toast("FXS_DELETED", "success", { name });
    if (window.refreshEffectDropdowns) window.refreshEffectDropdowns();
    send("fx_script_list");
    return true;
  }

  /** Dialog "Neuer Effekt": Kategorie (oder komplett leere Datei), Vorlage (Vorgabe "Leer"), Durchlaeufe pro Sekunde. Liefert {category, template, rate} oder null;
   *  category "blank" = leere Datei ohne Kopfzeilen. */
  function chooseNew() {
    return _modalResult("fxs-new", null, (finish, listen) => {
      const body = $("fxs-new-body");
      const footer = $("fxs-new-footer");
      body.textContent = "";
      footer.textContent = "";
      const choice = { category: categories[0].name, template: "EMPTY", rate: RATE_MAX };
      const sectionTitle = (key) => el("div", "fxs-new__title", T(key));
      const cats = el("div", "fxs-new__cats");
      const templates = el("div", "fxs-new__templates");
      const templatesTitle = sectionTitle("FXS_NEW_TEMPLATE");
      const rateTitle = sectionTitle("FXS_NEW_RATE");
      const rateRow = el("div", "fxs-new__rate");
      const renderTemplates = () => {
        const blank = choice.category === "blank";
        for (const node of [templatesTitle, templates, rateTitle, rateRow]) node.hidden = blank;
        templates.textContent = "";
        if (blank) return;
        for (const tpl of templatesFor(choice.category)) {
          const key = tpl.generic ? "GENERIC_EMPTY" : tplKey(choice.category, tpl.id);
          const row = el("label", "fxs-new__tpl" + (choice.template === tpl.id ? " fxs-new__tpl--on" : ""));
          const radio = el("input");
          radio.type = "radio";
          radio.name = "fxs-tpl";
          radio.checked = choice.template === tpl.id;
          radio.addEventListener("change", () => { choice.template = tpl.id; renderTemplates(); });
          const text = el("div");
          text.append(el("div", "fxs-new__tpl-name", T("FXS_TPL_" + key)), el("div", "fxs-new__tpl-desc", T("FXS_TPL_" + key + "_D")));
          row.append(radio, text);
          templates.appendChild(row);
        }
      };
      const renderCats = () => {
        cats.textContent = "";
        const entries = [...categories.map((c) => ({ name: c.name, icon: CATEGORY_ICON[c.name] || "fx", label: catLabel(c.name), description: catDescription(c.name) })),
          { name: "blank", icon: "edit", label: T("FXS_CAT_BLANK"), description: T("FXS_CAT_BLANK_D") }];
        for (const entry of entries) {
          const card = el("button", "fxs-new__cat" + (choice.category === entry.name ? " fxs-new__cat--on" : ""));
          card.type = "button";
          card.dataset.category = entry.name;
          const icon = Icons.svg(entry.icon);
          icon.classList.add("fxs-new__cat-icon");
          card.append(icon, el("div", "fxs-new__cat-name", entry.label), el("div", "fxs-new__cat-desc", entry.description));
          card.addEventListener("click", () => { choice.category = entry.name; choice.template = "EMPTY"; renderCats(); renderTemplates(); });
          cats.appendChild(card);
        }
      };
      const range = el("input");
      range.type = "range"; range.min = RATE_MIN; range.max = RATE_MAX; range.step = 1; range.value = choice.rate;
      const number = el("input", "modal__input fxs-new__rate-number");
      number.type = "number"; number.min = RATE_MIN; number.max = RATE_MAX; number.value = choice.rate;
      const sync = (v) => { const n = Math.max(RATE_MIN, Math.min(RATE_MAX, Math.round(Number(v)) || RATE_MAX)); choice.rate = n; range.value = n; number.value = n; };
      range.addEventListener("input", () => sync(range.value));
      number.addEventListener("change", () => sync(number.value));
      rateRow.append(range, number, el("span", "fxs-new__rate-unit", T("FXS_RATE_UNIT")));
      body.append(sectionTitle("FXS_NEW_CATEGORY"), cats, templatesTitle, templates, rateTitle, rateRow);
      renderCats();
      renderTemplates();
      const cancel = el("button", "modal__button", T("CANCEL"));
      cancel.type = "button";
      cancel.dataset.modalCancel = "fxs-new";
      const create = el("button", "modal__button modal__button--primary", T("FXS_NEW_CREATE"));
      create.type = "button";
      create.id = "fxs-new-create";
      footer.append(cancel, create);
      listen(create, "click", () => finish({ ...choice }));
    });
  }

  let helpCache = {};
  async function showHelp() {
    const lang = (typeof translator !== "undefined" && translator.language) || "de";
    const body = $("fxs-help-body");
    body.textContent = "";
    body.appendChild(el("div", "fxs-open__empty", T("FM_LOADING")));
    Modal.open("fxs-help");
    try {
      if (!helpCache[lang]) {
        const res = await fetch("/static/help/effect-studio." + (lang === "de" ? "de" : "en") + ".md");
        if (!res.ok) throw new Error("help");
        helpCache[lang] = await res.text();
      }
      const doc = renderMarkdown(helpCache[lang]);
      const nav = el("nav", "fxs-help__nav");
      doc.querySelectorAll("h2").forEach((h) => {
        const link = el("a", "", h.textContent);
        link.href = "#" + h.id;
        link.addEventListener("click", (e) => { e.preventDefault(); h.scrollIntoView({ block: "start" }); });
        nav.appendChild(link);
      });
      body.textContent = "";
      const layout = el("div", "fxs-help");
      const content = el("div", "fxs-help__content");
      content.appendChild(doc);
      layout.append(nav, content);
      body.appendChild(layout);
    } catch (err) {
      body.textContent = "";
      body.appendChild(el("div", "fxs-open__empty", T("FXS_HELP_ERROR")));
    }
  }

  // ------------------------------------------------------------------------------------------ Editor-Hilfen
  function paintCode(root) {
    const code = root.querySelector(".fxs-hl-code");
    code.innerHTML = highlight(textOf(root)) + "\n ";
  }

  function syncScroll(root) {
    const text = root.querySelector(".fxs-text");
    root.querySelector(".fxs-hl").style.transform = `translate(${-text.scrollLeft}px, ${-text.scrollTop}px)`;
    root.querySelector(".fxs-gutter").scrollTop = text.scrollTop;
    positionErrorBand(root);
  }

  function positionErrorBand(root) {
    const st = model.get(root);
    const band = root.querySelector(".fxs-errband");
    if (!st || !st.errorLine) { band.hidden = true; return; }
    const text = root.querySelector(".fxs-text");
    const style = getComputedStyle(text);
    const lineHeight = parseFloat(style.lineHeight) || 18;
    band.hidden = false;
    band.style.height = lineHeight + "px";
    band.style.top = (parseFloat(style.paddingTop) + (st.errorLine - 1) * lineHeight - text.scrollTop) + "px";
  }

  function updateGutter(root) {
    const text = root.querySelector(".fxs-text");
    const gutter = root.querySelector(".fxs-gutter");
    const st = model.get(root);
    const count = Math.max(1, text.value.split("\n").length);
    while (gutter.children.length > count) gutter.lastChild.remove();
    while (gutter.children.length < count) gutter.appendChild(el("span", "fxs-ln", String(gutter.children.length + 1)));
    for (let i = 0; i < count; i++) gutter.children[i].classList.toggle("fxs-ln--err", !!st && st.errorLine === i + 1);
    paintCode(root);
    syncScroll(root);
  }

  function setStatus(root, ok, message) {
    const status = root.querySelector(".fxs-status");
    if (!status) return;
    status.className = "fxs-status " + (ok ? "fxs-status--ok" : "fxs-status--error");
    status.querySelector(".fxs-status__msg").textContent = message;
  }

  function updatePosition(root) {
    const text = root.querySelector(".fxs-text");
    const before = text.value.slice(0, text.selectionStart);
    root.querySelector(".fxs-status__pos").textContent = T("FXS_POS", { line: before.split("\n").length, col: before.length - before.lastIndexOf("\n") });
  }

  /** Text an der Schreibmarke einfuegen (haelt den Rueckgaengig-Verlauf des Feldes). */
  function insertText(root, str) {
    const text = root.querySelector(".fxs-text");
    text.focus();
    if (!document.execCommand || !document.execCommand("insertText", false, str)) {
      text.setRangeText(str, text.selectionStart, text.selectionEnd, "end");
      text.dispatchEvent(new Event("input"));
    }
    updatePosition(root);
  }

  // ------------------------------------------------------------------------------------------ Titel
  function renderTitle(root) {
    const st = model.get(root);
    const box = root.querySelector(".fxs-title");
    if (!st || !box) return;
    box.textContent = "";
    const entry = files.find((f) => f.name === st.name);
    box.appendChild(el("span", "fxs-title__name", st.name || T("FXS_UNNAMED")));
    const dot = el("span", "fxs-dot", "●");
    dot.title = T("FXS_UNSAVED");
    dot.hidden = !isDirty(root);
    box.appendChild(dot);
    const category = (st.last && st.last.ok && st.last.category) || (entry && entry.category);
    if (category) box.appendChild(tag(category));
    const rate = (st.last && st.last.ok && st.last.rate) || (entry && entry.rate);
    if (rate) box.appendChild(el("span", "fxs-title__rate", T("FXS_RATE_SHORT", { n: rate })));
    if (st.name && st.origin) box.appendChild(el("span", "fxs-title__origin", T("FXS_ORIGIN_" + String(st.origin).toUpperCase())));
    root.querySelector(".fxs-save").classList.toggle("fxs-btn--primary", isDirty(root) || !st.name);
    const del = root.querySelector(".fxs-delete");
    del.disabled = !st.name || st.origin !== "user";
    del.title = del.disabled ? T("FXS_DELETE_TIP_NONE") : T("FXS_DELETE_TIP");
  }

  // ------------------------------------------------------------------------------------------ Aktionen
  async function confirmDiscard(root) {
    if (!isDirty(root)) return true;
    return _askLayoutConfirm({ title: T("FXS_DISCARD_TITLE"), body: T("FXS_DISCARD_BODY"), confirmKey: "FXS_DISCARD_CONFIRM" });
  }

  function setScript(root, { name, origin, text }) {
    const st = model.get(root);
    st.name = name;
    st.origin = origin || "";
    st.savedText = text;
    st.params = {};
    st.errorLine = null;
    st.last = null;
    st.good = null;
    root.querySelector(".fxs-text").value = text;
    root.querySelector(".fxs-text").scrollTop = 0;
    updateGutter(root);
    updatePosition(root);
    renderTitle(root);
    requestPreview(root, 0);
  }

  async function newScript(root) {
    const st = model.get(root);
    if (st.busy) return;
    st.busy = true;
    try {
      const choice = await chooseNew();
      if (!choice) return;
      if (!(await confirmDiscard(root))) return;
      if (choice.category === "blank") {
        setScript(root, { name: null, origin: "", text: "" });
      } else {
        const list = templatesFor(choice.category);
        const tpl = list.find((x) => x.id === choice.template) || list[0];
        setScript(root, { name: null, origin: "", text: tpl.code(choice.rate) });
        setStatus(root, true, T("FXS_NEW_HINT"));
      }
      root.querySelector(".fxs-text").focus();
    } finally { st.busy = false; }
  }

  async function openScript(root) {
    const st = model.get(root);
    if (st.busy) return;
    st.busy = true;
    try {
      const name = await chooseEffect();
      if (!name) return;
      if (!(await confirmDiscard(root))) return;
      st.pendingLoad = name;
      send("fx_script_load", { name });
    } finally { st.busy = false; }
  }

  function saveRequest(root, name, text, overwrite) {
    const st = model.get(root);
    return new Promise((resolve) => {
      const timer = setTimeout(() => { if (st.waiter) { st.waiter = null; resolve({ ok: false, saved: false, message: T("FXS_ERROR") }); } }, 8000);
      st.waiter = (payload) => { clearTimeout(timer); st.waiter = null; resolve(payload); };
      send("fx_script_save", { name, text, overwrite });
    });
  }

  function afterSave(root, payload, text) {
    const st = model.get(root);
    st.name = payload.name;
    st.origin = "user";
    st.savedText = text;
    renderTitle(root);
    if (window.refreshEffectDropdowns) window.refreshEffectDropdowns();
    if (payload.ok) {
      const hot = payload.active ? " - " + T("FXS_HOT", { n: payload.active }) : "";
      setStatus(root, true, T("FXS_SAVED", { name: payload.name }) + hot);
    } else {
      const where = payload.line ? T("FXS_LINE", { line: payload.line }) + ": " : "";
      setStatus(root, false, T("FXS_SAVED", { name: payload.name }) + " - " + where + payload.message);
    }
  }

  async function saveAs(root) {
    const st = model.get(root);
    const text = textOf(root);
    let value = st.name || "";
    for (;;) {
      const name = await _askLayoutName({ title: T("FXS_SAVE_AS_TITLE"), confirmKey: "FXS_SAVE", value, labelKey: "FXS_NAME_LABEL" });
      if (!name) return false;
      let payload = await saveRequest(root, name, text, false);
      if (payload.exists) {
        const sure = await _askLayoutConfirm({ title: T("FXS_EXISTS_TITLE"), body: T("FXS_EXISTS_BODY", { name: payload.name }), confirmKey: "LAYOUT_OVERWRITE" });
        if (!sure) { value = name; continue; }
        payload = await saveRequest(root, name, text, true);
      }
      if (!payload.saved) { setStatus(root, false, payload.message || T("FXS_ERROR")); return false; }
      afterSave(root, payload, text);
      return true;
    }
  }

  async function save(root) {
    const st = model.get(root);
    if (!st.name) return saveAs(root);
    const text = textOf(root);
    let payload = await saveRequest(root, st.name, text, st.origin === "user");
    if (payload.exists) {
      const sure = await _askLayoutConfirm({ title: T("FXS_EXISTS_TITLE"), body: T("FXS_EXISTS_BODY", { name: payload.name }), confirmKey: "LAYOUT_OVERWRITE" });
      if (!sure) return false;
      payload = await saveRequest(root, st.name, text, true);
    }
    if (!payload.saved) { setStatus(root, false, payload.message || T("FXS_ERROR")); return false; }
    afterSave(root, payload, text);
    return true;
  }

  async function deleteScript(root) {
    const st = model.get(root);
    if (!st.name || st.origin !== "user") return;
    const name = st.name;
    if (!(await _askLayoutConfirm({ title: T("FXS_DELETE_TITLE"), body: T("FXS_DELETE_BODY", { name }), confirmKey: "FXS_DELETE_OK" }))) return;
    if (await deleteFile(name)) setStatus(root, true, T("FXS_DELETED", { name }));
  }

  // ------------------------------------------------------------------------------------------ Vorschau
  function requestPreview(root, delay) {
    const st = model.get(root);
    clearTimeout(st.timer);
    st.timer = setTimeout(() => {
      if (!textOf(root).trim()) { showEmpty(root); return; }
      st.seq = ++previewSeq;
      send("fx_script_preview", { seq: st.seq, name: st.name || "", text: textOf(root), params: st.params, count: st.count, duration: st.duration });
    }, delay === undefined ? 350 : delay);
  }

  const palette = (i, n) => `hsl(${Math.round((38 + i * 360 / Math.max(n, 3)) % 360)} 85% 62%)`;

  function prepareCanvas(canvas) {
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    if (!w || !h) return null;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    const g = canvas.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    const css = getComputedStyle(canvas);
    return { g, w, h, grid: css.getPropertyValue("--border-color").trim() || "#333", text: css.getPropertyValue("--secondary-text").trim() || "#888" };
  }

  function drawTime(canvas, data) {
    const c = prepareCanvas(canvas);
    if (!c) return;
    const { g, w, h } = c;
    const pad = { l: 30, r: 8, t: 8, b: 16 };
    const pw = w - pad.l - pad.r;
    const ph = h - pad.t - pad.b;
    const ymax = data.category === "color" ? 255 : 100;
    const xAt = (time) => pad.l + (time / data.duration) * pw;
    const yAt = (value) => pad.t + ph - (Math.max(0, Math.min(ymax, value)) / ymax) * ph;
    g.font = "10px sans-serif";
    g.lineWidth = 1;
    g.strokeStyle = c.grid;
    g.fillStyle = c.text;
    g.textAlign = "right";
    for (const f of [0, 0.5, 1]) {
      const y = yAt(ymax * f);
      g.beginPath(); g.moveTo(pad.l, y); g.lineTo(w - pad.r, y); g.stroke();
      g.fillText(String(Math.round(ymax * f)), pad.l - 4, y + 3);
    }
    g.textAlign = "center";
    const stepX = data.duration <= 3 ? 0.5 : 1;
    for (let s = 0; s <= data.duration + 1e-9; s += stepX) {
      const x = xAt(s);
      g.beginPath(); g.moveTo(x, pad.t); g.lineTo(x, pad.t + ph); g.stroke();
      g.fillText(s + " s", x, h - 4);
    }
    const stairs = data.rate <= 20 || data.category === "gobo";       // wenig Durchlaeufe pro Sekunde: der Ausgang bleibt zwischen zwei Durchlaeufen stehen; Gobos springen immer
    const curve = (values, color, dash, width) => {
      g.beginPath();
      values.forEach((value, k) => {
        const x = xAt(data.times[k]);
        const y = yAt(value);
        if (!k) g.moveTo(x, y);
        else { if (stairs) g.lineTo(x, yAt(values[k - 1])); g.lineTo(x, y); }
      });
      g.strokeStyle = color; g.lineWidth = width; g.setLineDash(dash || []); g.stroke(); g.setLineDash([]);
      if (data.rate <= 10) { g.fillStyle = color; values.forEach((value, k) => { g.beginPath(); g.arc(xAt(data.times[k]), yAt(value), 2.5, 0, Math.PI * 2); g.fill(); }); }
    };
    const legend = [];
    if (data.category !== "color" && data.category !== "position") {       // Dimmer, Zoom, Fokus, Gobo ...: eine Kurve je Scheinwerfer
      const rows = data.series[Object.keys(data.series)[0]];
      for (let i = data.count - 1; i >= 0; i--) curve(rows[i], palette(i, data.count), null, i === 0 ? 2 : 1.4);
    } else if (data.category === "color") {
      curve(data.series.r[0], "#ff5555", null, 2); curve(data.series.g[0], "#55dd55", null, 2); curve(data.series.b[0], "#5599ff", null, 2);
      legend.push(["R", "#ff5555"], ["G", "#55dd55"], ["B", "#5599ff"]);
    } else {
      for (let i = data.count - 1; i >= 1; i--) curve(data.series.pan[i], palette(i, data.count), null, 1);
      curve(data.series.pan[0], "#ffb000", null, 2); curve(data.series.tilt[0], "#58a6ff", [5, 3], 2);
      legend.push(["pan", "#ffb000"], ["tilt", "#58a6ff"]);
    }
    g.textAlign = "right";
    let lx = w - pad.r - 4;
    for (const [label, color] of legend.reverse()) { g.fillStyle = color; g.fillText(label, lx, pad.t + 10); lx -= g.measureText(label).width + 10; }
  }

  function drawExtra(canvas, data) {
    const c = prepareCanvas(canvas);
    if (!c) return;
    const { g, w, h } = c;
    if (data.category === "color") {
      const rows = data.count;
      const rowH = Math.max(4, Math.min(28, (h - 6) / rows));
      const steps = data.times.length;
      for (let i = 0; i < rows; i++) {
        for (let k = 0; k < steps; k++) {
          const x0 = 30 + (k / steps) * (w - 38);
          g.fillStyle = `rgb(${Math.round(data.series.r[i][k])},${Math.round(data.series.g[i][k])},${Math.round(data.series.b[i][k])})`;
          g.fillRect(x0, 3 + i * rowH, (w - 38) / steps + 1, rowH - 1);
        }
        g.fillStyle = c.text; g.font = "10px sans-serif"; g.textAlign = "right";
        if (rowH >= 10) g.fillText(String(i + 1), 24, 3 + i * rowH + rowH / 2 + 3);
      }
    } else if (data.category === "position") {
      const side = Math.min(w - 16, h - 16);
      const x0 = (w - side) / 2;
      const y0 = (h - side) / 2;
      g.strokeStyle = c.grid; g.lineWidth = 1;
      g.strokeRect(x0, y0, side, side);
      g.beginPath(); g.moveTo(x0 + side / 2, y0); g.lineTo(x0 + side / 2, y0 + side); g.moveTo(x0, y0 + side / 2); g.lineTo(x0 + side, y0 + side / 2); g.stroke();
      for (let i = data.count - 1; i >= 0; i--) {
        g.beginPath();
        data.series.pan[i].forEach((pan, k) => {
          const x = x0 + (Math.max(0, Math.min(100, pan)) / 100) * side;
          const y = y0 + side - (Math.max(0, Math.min(100, data.series.tilt[i][k])) / 100) * side;
          if (k) g.lineTo(x, y); else g.moveTo(x, y);
        });
        g.strokeStyle = palette(i, data.count); g.lineWidth = i === 0 ? 2 : 1.3; g.stroke();
        const sx = x0 + (Math.max(0, Math.min(100, data.series.pan[i][0])) / 100) * side;
        const sy = y0 + side - (Math.max(0, Math.min(100, data.series.tilt[i][0])) / 100) * side;
        g.fillStyle = palette(i, data.count); g.beginPath(); g.arc(sx, sy, 3.5, 0, Math.PI * 2); g.fill();
      }
      g.fillStyle = c.text; g.font = "10px sans-serif"; g.textAlign = "left";
      g.fillText("pan →", x0 + 4, y0 + side - 4);
    }
  }

  function drawPreview(root) {
    const st = model.get(root);
    const preview = root.querySelector(".fxs-preview");
    if (!st || !preview || preview.hidden) return;
    const data = st.good;
    const timeCanvas = root.querySelector(".fxs-pv-time");
    const extraCanvas = root.querySelector(".fxs-pv-extra");
    extraCanvas.hidden = !data || data.category === "dimmer";
    preview.classList.toggle("fxs-preview--stale", !!st.errorLine || (st.last && !st.last.ok));
    if (!data) { prepareCanvas(timeCanvas); return; }
    drawTime(timeCanvas, data);
    if (!extraCanvas.hidden) drawExtra(extraCanvas, data);
  }

  function renderParams(root) {
    const st = model.get(root);
    const box = root.querySelector(".fxs-pv-params");
    const variables = st.good ? st.good.variables : [];
    const signature = JSON.stringify(variables.map((v) => [v.name, v.kind, v.min, v.max, v.step]));
    if (box.dataset.sig === signature) return;            // gleiche Parameter: Regler bleiben stehen (kein Ruckeln beim Tippen)
    box.dataset.sig = signature;
    box.textContent = "";
    if (!variables.length) { box.appendChild(el("div", "fxs-pv-hint", T("FXS_PV_NO_PARAMS"))); return; }
    for (const v of variables) {
      const row = el("label", "fxs-param");
      row.appendChild(el("span", "fxs-param__name", v.name));
      const current = st.params[v.name] !== undefined ? st.params[v.name] : v.default;
      if (v.kind === "ColorPicker") {
        const input = el("input");
        input.type = "color";
        const hex = (n) => Math.round(n).toString(16).padStart(2, "0");
        input.value = "#" + hex(current.r) + hex(current.g) + hex(current.b);
        input.addEventListener("input", () => {
          st.params[v.name] = { r: parseInt(input.value.slice(1, 3), 16), g: parseInt(input.value.slice(3, 5), 16), b: parseInt(input.value.slice(5, 7), 16) };
          requestPreview(root, 80);
        });
        row.appendChild(input);
      } else {
        const input = el("input", "fxs-param__range");
        input.type = "range";
        input.min = v.min; input.max = v.max; input.step = v.step || "any";
        input.value = current;
        const readout = el("span", "fxs-param__value", String(Math.round(Number(current) * 1000) / 1000));
        input.addEventListener("input", () => {
          st.params[v.name] = Number(input.value);
          readout.textContent = String(Math.round(Number(input.value) * 1000) / 1000);
          requestPreview(root, 80);
        });
        row.append(input, readout);
      }
      box.appendChild(row);
    }
  }

  /** Leere Datei: nichts zu pruefen oder zu zeichnen - ein Hinweis statt einer Fehlermeldung. */
  function showEmpty(root) {
    const st = model.get(root);
    st.seq = ++previewSeq;                                // eine noch unterwegs befindliche Antwort verwerfen
    st.last = null;
    st.good = null;
    st.errorLine = null;
    updateGutter(root);
    renderTitle(root);
    renderParams(root);
    root.querySelector(".fxs-pv-msg").textContent = "";
    drawPreview(root);
    setStatus(root, true, T("FXS_EMPTY"));
  }

  function onPreview(root, payload) {
    const st = model.get(root);
    if (!st || payload.seq !== st.seq) return;            // veraltete Antwort
    st.last = payload;
    if (payload.ok) {
      st.good = payload;
      st.errorLine = null;
      for (const v of payload.variables) if (st.params[v.name] === undefined) st.params[v.name] = payload.params[v.name];
      setStatus(root, true, T("FXS_OK"));
    } else {
      st.errorLine = payload.line || null;
      const where = payload.line ? T("FXS_LINE", { line: payload.line }) + ": " : "";
      setStatus(root, false, where + payload.message);
    }
    updateGutter(root);
    renderTitle(root);
    renderParams(root);
    root.querySelector(".fxs-pv-msg").textContent = payload.ok ? "" : T("FXS_PV_ERROR");
    drawPreview(root);
  }

  // ------------------------------------------------------------------------------------------ Aufbau
  function applyI18n(root) {
    root.querySelectorAll("[data-i18n]").forEach((node) => { node.textContent = T(node.dataset.i18n); });
    const st = model.get(root);
    if (!st) return;
    delete root.querySelector(".fxs-pv-params").dataset.sig;
    renderTitle(root);
    renderParams(root);
    updatePosition(root);
    drawPreview(root);
  }

  function button(cls, key, handler) {
    const b = el("button", "fxs-btn" + (cls ? " " + cls : ""), T(key));
    b.type = "button";
    b.dataset.i18n = key;
    b.addEventListener("click", handler);
    return b;
  }

  function buildStudio(root) {
    const st = { name: null, origin: "", savedText: "", params: {}, count: 1, duration: 2, seq: 0, last: null, good: null, errorLine: null, timer: 0, waiter: null, pendingLoad: null, busy: false };
    model.set(root, st);

    const head = el("div", "fxs-head");
    const spacer = el("div", "fxs-title");
    head.append(
      button("fxs-open-btn", "FXS_OPEN", () => openScript(root)),
      button("fxs-new-btn", "FXS_NEW", () => newScript(root)),
      button("fxs-save", "FXS_SAVE", () => save(root)),
      button("fxs-save-as", "FXS_SAVE_AS", () => saveAs(root)),
      button("fxs-btn--danger fxs-delete", "FXS_DELETE", () => deleteScript(root)),
      spacer,
      button("fxs-help-btn", "FXS_HELP", showHelp),
      button("fxs-pv-toggle", "FXS_PREVIEW", () => {
        const preview = root.querySelector(".fxs-preview");
        preview.hidden = !preview.hidden;
        root.classList.toggle("fxs--no-preview", preview.hidden);
        if (!preview.hidden) requestAnimationFrame(() => drawPreview(root));
      }));

    const editor = el("div", "fxs-editor");
    const gutter = el("div", "fxs-gutter");
    const code = el("div", "fxs-code");
    const hl = el("pre", "fxs-hl");
    hl.appendChild(el("code", "fxs-hl-code"));
    const band = el("div", "fxs-errband");
    band.hidden = true;
    const text = el("textarea", "fxs-text");
    text.spellcheck = false;
    text.wrap = "off";
    text.setAttribute("autocomplete", "off");
    text.setAttribute("autocapitalize", "off");
    text.addEventListener("input", () => { updateGutter(root); updatePosition(root); renderTitle(root); requestPreview(root); });
    text.addEventListener("scroll", () => syncScroll(root));
    text.addEventListener("keyup", () => updatePosition(root));
    text.addEventListener("click", () => updatePosition(root));
    text.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {      // Strg+S speichert den Effekt (nicht die Show)
        e.preventDefault();
        e.stopPropagation();
        if (e.shiftKey) saveAs(root); else save(root);
        return;
      }
      if (e.key === "Tab" && !e.shiftKey) { e.preventDefault(); insertText(root, "  "); return; }
      if (e.key === "Enter" && !e.ctrlKey && !e.altKey && !e.shiftKey && !e.metaKey) {      // Einrueckung der Zeile uebernehmen, nach "{" zwei Leerzeichen mehr
        const before = text.value.slice(text.value.lastIndexOf("\n", text.selectionStart - 1) + 1, text.selectionStart);
        e.preventDefault();
        insertText(root, "\n" + /^[ \t]*/.exec(before)[0] + (/\{\s*$/.test(before) ? "  " : ""));
      }
    });
    code.append(hl, band, text);
    editor.append(gutter, code);

    const preview = el("div", "fxs-preview");
    const pvHead = el("div", "fxs-pv-head");
    const pvTitle = el("span", "fxs-pv-title", T("FXS_PREVIEW"));
    pvTitle.dataset.i18n = "FXS_PREVIEW";
    const stepper = (key, min, max, step, get, set, unit) => {
      const wrap = el("label", "fxs-pv-field");
      const label = el("span", "", T(key));
      label.dataset.i18n = key;
      const input = el("input", "fxs-pv-number");
      input.type = "number"; input.min = min; input.max = max; input.step = step; input.value = get();
      input.addEventListener("change", () => { const v = Math.max(min, Math.min(max, Number(input.value) || min)); input.value = v; set(v); requestPreview(root, 0); });
      wrap.append(label, input);
      if (unit) wrap.appendChild(el("span", "fxs-pv-unit", unit));
      return wrap;
    };
    pvHead.append(pvTitle,
      stepper("FXS_PV_FIXTURES", 1, 16, 1, () => st.count, (v) => { st.count = v; }),
      stepper("FXS_PV_SECONDS", 1, 20, 1, () => st.duration, (v) => { st.duration = v; }, "s"));
    const params = el("div", "fxs-pv-params");
    const timeCanvas = el("canvas", "fxs-pv-time");
    const extraCanvas = el("canvas", "fxs-pv-extra");
    const msg = el("div", "fxs-pv-msg");
    preview.append(pvHead, params, timeCanvas, extraCanvas, msg);

    const main = el("div", "fxs-main");
    main.append(editor, preview);

    const status = el("div", "fxs-status fxs-status--ok");
    const statusMsg = el("span", "fxs-status__msg", T("FXS_READY"));
    statusMsg.dataset.i18n = "FXS_READY";
    status.append(statusMsg, el("span", "fxs-status__pos"));

    root.append(head, main, status);
    root.classList.add("fxs");
    studios.add(root);
    const observer = new ResizeObserver(() => {
      if (!root.isConnected) { observer.disconnect(); return; }
      root.classList.toggle("fxs--narrow", root.clientWidth < 720);
      drawPreview(root);
      positionErrorBand(root);
    });
    observer.observe(root);
    send("fx_script_list");
    // Ein neues Studio beginnt mit der Vorlage "Sinus" (Dimmer, volle Rate): 1 Scheinwerfer, 2 Sekunden, speed 1
    const first = TEMPLATES.dimmer.find((x) => x.id === "SINE");
    setScript(root, { name: null, origin: "", text: first.code(RATE_MAX) });
  }

  fetch("/api/effects").then((r) => r.json()).then((data) => {
    if (Array.isArray(data.categories) && data.categories.length) {
      categories = data.categories;
      categories.forEach((c) => c.outputs.forEach((o) => OUTPUTS.add(o.name)));
      studios.forEach((root) => { if (root.isConnected) updateGutter(root); });
    }
  }).catch(() => { /* Vorgabe: dimmer, color, position */ });

  window.__panelPlugins.register({
    type: "fx_studio",

    buildContent() {
      const root = el("div", "fxs-root");
      requestAnimationFrame(() => buildStudio(root));
      return root;
    },

    onMessage(panelEl, messageType, payload) {
      const live = [];
      studios.forEach((root) => { if (root.isConnected) live.push(root); else studios.delete(root); });      // entferntes Panel: Referenz freigeben
      if (messageType === "fx_script_list") {
        files = (payload && payload.files) || [];
        live.forEach((root) => renderTitle(root));
        if (onFilesChanged) onFilesChanged();
      } else if (messageType === "fx_script_source") {
        const root = live.find((r) => model.get(r) && model.get(r).pendingLoad === payload.name);       // nur das Studio, das geladen hat
        if (!root) return;
        model.get(root).pendingLoad = null;
        const entry = files.find((f) => f.name === payload.name);
        setScript(root, { name: payload.name, origin: entry ? entry.origin : "user", text: payload.text });
        setStatus(root, true, T("FXS_LOADED", { name: payload.name }));
      } else if (messageType === "fx_script_result") {
        const root = live.find((r) => model.get(r) && model.get(r).waiter);
        if (root) model.get(root).waiter(payload);
      } else if (messageType === "fx_script_preview") {
        live.forEach((root) => onPreview(root, payload));
      } else if (messageType === "language_changed") {
        live.forEach(applyI18n);
      }
    },
  });
})();

// ---- Bootstrapping ---------------------------------------------------------
// PWA: Der Service Worker gilt nur fuer /remote/ (siehe app/remote_pwa.py), nie fuer die Konsole selbst.
if ("serviceWorker" in navigator && location.pathname.indexOf("/remote/") === 0) {
  navigator.serviceWorker.register("/remote/sw.js", { scope: "/remote/" }).catch(() => { /* kein sicherer Kontext */ });
}

const client = new OpenCueClient();

// Uhrzeit sofort starten — kein DOMContentLoaded-Delay, da das Script am Ende
// von <body> steht und alle Elemente bereits im DOM existieren.
setupClock();

document.addEventListener("DOMContentLoaded", async () => {
  await translator.init();       // Sprachdateien zuerst - dann erst Dialoge und Menues aufbauen
  updateWindowTitle("Untitled"); // corrected once the state snapshot arrives
  setupMenuBar();
  setupGuiScaleModal();
  setupAddPanelModal();
  setupSettingsModal();
  setupCloseConfirmModal();
  setupPanelPropertiesModal();
  setupFullscreenToggle();
  setupFileMenu();
  setupLayoutMenu();
  setupKeyboardShortcuts();
  setupHelpMenu();
  setEditMode(false); // establishes the initial disabled/label state
});
