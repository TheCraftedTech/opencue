// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Einstellungsdialog: gemeinsame Ordnung fuer ALLE Kategorien (window.OCSettings).
 *  - Nichts gilt, bevor "Speichern" gedrueckt wird. Der Knopf zaehlt mit: "Speichern (3 Änderungen)".
 *  - Jede geaenderte Zeile ist markiert (Akzentfarbe) und hat einen Zurueck-Pfeil, der nur diese eine Aenderung zuruecknimmt; die Kategorie in der Seitenleiste zeigt, wie viele
 *    Aenderungen in ihr stecken.
 *  - Jede Kategorie hat oben denselben Kopf: Titel, Beschreibung und "Zurücksetzen" (fragt nach; setzt die Standardwerte als ENTWURF - gespeichert wird erst mit "Speichern").
 *  - "Speichern" speichert und laesst den Dialog offen (der gespeicherte Stand ist danach der neue Ausgangspunkt); "Schliessen" fragt bei ungespeicherten Aenderungen nach.
 * Bausteine ("Anbieter"): window.OCSettings.register({ id, category, changes(), reset() }). changes() liefert die aktuell geaenderten Zeilen
 *   [{ key, label, row (Element), revert() }]; reset() setzt den Entwurf der Kategorie auf die Standardwerte. Wer seine Zeilen neu zeichnet oder etwas aendert, ruft OCSettings.touch().
 * Die festen Seiten (Allgemein, Darstellung/Neue Panels, DMX-Ausgabe, Fernzugriff) braucht keinen eigenen Code: alle ".settings-field"-Zeilen mit Eingabefeldern werden
 *   automatisch beobachtet (Ausnahme: Bereiche mit data-track-skip, schreibgeschuetzte Felder und Knoepfe); ihre Standardwerte stehen unten in staticDefaults().
 * Andere Seiten (Farben, KI-Assistent, Sprachsteuerung) melden sich selbst an (app.js ThemeUI, ai_settings.js, voice_settings.js). Klassisches Skript, laeuft nach app.js. */
(function () {
  "use strict";
  const t = (key, vars) => { let s = i18n(key); if (vars) for (const [k, v] of Object.entries(vars)) s = s.split("{" + k + "}").join(String(v)); return s; };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const root = () => document.querySelector(".modal--settings");
  const providers = new Map();
  const staticProviders = new Map();
  const STATIC_CATEGORIES = ["general", "advanced", "appearance", "dmx-network", "remote", "security"];
  let paintTimer = 0;
  let discarding = false;

  // ------------------------------------------------------------------------------------------ Anbieter
  function register(provider) {
    providers.set(provider.id, provider);
    touch();
  }
  const inCategory = (category) => [...providers.values()].filter((p) => p.category === category);
  const changesOf = (provider) => { try { return provider.changes() || []; } catch (err) { return []; } };
  function count(category) {
    return [...providers.values()].filter((p) => !category || p.category === category).reduce((sum, p) => sum + changesOf(p).length, 0);
  }

  // ------------------------------------------------------------------------------------------ Feste Seiten: Eingabefelder beobachten
  const READ_SKIP = new Set(["button", "submit", "reset", "file", "image"]);
  const isCheck = (c) => c.type === "checkbox" || c.type === "radio";
  const norm = (c) => (isCheck(c) ? !!c.checked : c.type === "number" ? (c.value === "" ? "" : Number(c.value)) : String(c.value).trim().toLowerCase());
  const raw = (c) => (isCheck(c) ? !!c.checked : c.value);
  function write(control, value) {
    if (isCheck(control)) control.checked = !!value;
    else control.value = value === undefined || value === null ? "" : String(value);
    control.dispatchEvent(new Event("input", { bubbles: true }));
    control.dispatchEvent(new Event("change", { bubbles: true }));
  }
  const rowLabel = (row) => { const l = row.querySelector("label"); return l ? l.textContent.trim() : ""; };

  /** Standardwerte der festen Felder (vom Server: state.settings_defaults), je Kennung des ersten Eingabefelds der Zeile. */
  function staticDefaults() {
    const d = client && client.state && client.state.settings_defaults;
    if (!d) return {};
    const pd = d.panel_defaults || {};
    const rem = d.remote || {};
    return {
      "settings-autostart-enabled": false, "settings-autostart-headless": false, "settings-keep-awake": true,
      "settings-backup-enabled": (d.backup || {}).enabled, "settings-backup-interval": (d.backup || {}).interval_min, "settings-backup-keep": (d.backup || {}).keep,
      "settings-language": d.language, "settings-gui-scale-number": Number(d.gui_scale).toFixed(2), "settings-layout-swipe": true, "settings-update-check": d.update_check_enabled,
      "settings-artnet-enabled": d.artnet_enabled, "settings-artnet-auto": d.artnet_ip === "auto", "settings-artnet-target-ip": d.artnet_ip === "auto" ? "" : d.artnet_ip, "settings-artnet-bind-ip": d.artnet_bind_ip,
      "settings-sacn-enabled": d.sacn_enabled, "settings-enttec-enabled": d.enttec_enabled, "settings-enttec-port": d.enttec_port, "settings-enttec-universe": d.enttec_universe,
      "settings-default-universe": d.default_universe,
      "settings-panel-defaults-bg-swatch": pd.background_color, "settings-panel-defaults-text-swatch": pd.text_color, "settings-panel-defaults-header-bg-swatch": pd.header_background_color,
      "settings-panel-defaults-shadow": pd.shadow_enabled, "settings-panel-defaults-corners": pd.corner_style,
      "settings-remote-master": !!(rem.enabled || rem.https_enabled), "settings-remote-enabled": rem.enabled, "settings-remote-port": rem.port, "settings-remote-https-enabled": rem.https_enabled, "settings-remote-https-port": rem.https_port, "settings-remote-mdns": rem.mdns_enabled,
      "settings-lock-enabled": false, "settings-lock-minutes": "0",
      "settings-tb-layout": true, "settings-tb-stage": true, "settings-tb-show": true, "settings-tb-blackout": true, "settings-tb-timecode": true, "settings-tb-clock": true, "settings-tb-dmx": true, "settings-tb-remote": true, "settings-tb-kiosk": true, "settings-tb-lock": true, "settings-tb-voice": true, "settings-tb-midi": true, "settings-tb-undogo": true,
    };
  }

  function makeStatic(category) {
    let fields = [];
    const provider = {
      id: "static:" + category, category,
      scan() {
        fields = [];
        const pane = root() && root().querySelector('[data-settings-pane="' + category + '"]');
        if (!pane) return;
        pane.querySelectorAll(".settings-field").forEach((row) => {
          if (row.closest("[data-track-skip], .theme-root, #settings-api-root, #settings-ai-root, #settings-voice-root")) return;
          const controls = [...row.querySelectorAll("input, select, textarea")].filter((c) => !READ_SKIP.has(c.type) && !c.readOnly && !c.hasAttribute("data-track-skip"));
          if (!controls.length) return;
          fields.push({ row, controls, label: rowLabel(row), baseline: controls.map(raw) });
        });
      },
      changes() {
        const out = [];
        fields.forEach((f) => {
          if (!f.row.isConnected) return;
          const now = f.controls.map(norm);
          const was = f.controls.map((c, i) => norm({ type: c.type, checked: f.baseline[i], value: f.baseline[i] }));
          if (JSON.stringify(now) === JSON.stringify(was)) return;
          out.push({ key: f.controls[0].id || f.label, label: f.label, row: f.row, revert: () => f.controls.forEach((c, i) => write(c, f.baseline[i])) });
        });
        return out;
      },
      reset() {
        const defaults = staticDefaults();
        fields.forEach((f) => {
          const id = f.controls.find((c) => c.id in defaults) && f.controls.find((c) => c.id in defaults).id;
          if (id === undefined || defaults[id] === undefined) return;
          f.controls.forEach((c) => write(c, defaults[id]));              // Farbfelder: Farbwaehler und Hex-Feld bekommen denselben Wert
        });
      },
      /** Ein Feld neu als "gespeichert" merken (z. B. nachdem es asynchron gefuellt wurde). */
      rebaseline(id) {
        fields.forEach((f) => { if (!id || f.controls.some((c) => c.id === id)) f.baseline = f.controls.map(raw); });
      },
    };
    staticProviders.set(category, provider);
    providers.set(provider.id, provider);
    return provider;
  }

  /** Alle festen Seiten neu einlesen: der aktuelle Stand der Felder gilt jetzt als gespeichert (beim Oeffnen, nach einem Zuruecksetzen auf dem Server). */
  function rebaseline(id) {
    staticProviders.forEach((p) => (id ? p.rebaseline(id) : p.scan()));
    touch();
  }

  // ------------------------------------------------------------------------------------------ Hauptschalter
  /** Jeder Abschnitt mit einer Zeile ".settings-master" (grosser An/Aus-Schalter ganz oben): ist er aus, ist der Rest des Abschnitts abgeblendet und gesperrt (inert).
   *  Ausgenommen bleiben Titel, der Hauptschalter selbst und Elemente mit ".settings-keep" (Hinweise, Status). Nach jedem Neuzeichnen einer Seite erneut aufrufen. */
  function bindMasters(scope) {
    const host = scope || root();
    if (!host) return;
    host.querySelectorAll(".settings-section").forEach((section) => {
      const master = section.querySelector(":scope > .settings-master input[type=checkbox]");
      if (!master) return;
      const sync = () => {
        const off = !master.checked;
        section.classList.toggle("settings-section--off", off);
        [...section.children].forEach((child) => {
          if (child.matches(".settings-master, .settings-keep, .settings-section__title, .settings-section__head")) return;
          child.inert = off;
        });
        if (section.dataset.masterScope === "page") {                       // gilt fuer die ganze Seite: auch die folgenden Abschnitte
          for (let next = section.nextElementSibling; next; next = next.nextElementSibling) { next.inert = off; next.classList.toggle("settings-section--off", off); }
        }
      };
      if (!master._masterBound) { master._masterBound = true; master.addEventListener("change", sync); }
      sync();
    });
  }

  // ------------------------------------------------------------------------------------------ Anzeige
  function touch() {
    clearTimeout(paintTimer);
    paintTimer = setTimeout(paint, 0);
  }

  const marked = new Set();
  function undoButton(row) {
    if (row._undo && row._undo.isConnected) return row._undo;
    const button = el("button", "settings-undo");
    button.type = "button";
    button.appendChild(Icons.svg("undo"));
    button.addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); (row._changes || []).forEach((c) => c.revert()); touch(); });
    row.appendChild(button);
    row._undo = button;
    return button;
  }
  function mark(row, changes) {
    row._changes = changes;
    row.classList.add("settings-changed");
    const button = undoButton(row);
    const text = t("SETTINGS_UNDO_TIP");
    button.title = text;
    button.setAttribute("aria-label", text);
    marked.add(row);
  }
  function unmark(row) {
    row.classList.remove("settings-changed");
    row._changes = [];
    if (row._undo) { row._undo.remove(); row._undo = null; }
    marked.delete(row);
  }

  function saveLabel(n) {
    return n > 0 ? t(n === 1 ? "SETTINGS_SAVE_ONE" : "SETTINGS_SAVE_N", { n }) : t("SETTINGS_SAVE");
  }

  function paint() {
    const modal = root();
    if (!modal) return;
    const byRow = new Map();
    const perCategory = {};
    providers.forEach((provider) => {
      changesOf(provider).forEach((change) => {
        perCategory[provider.category] = (perCategory[provider.category] || 0) + 1;
        if (!change.row) return;
        if (!byRow.has(change.row)) byRow.set(change.row, []);
        byRow.get(change.row).push(change);
      });
    });
    [...marked].forEach((row) => { if (!byRow.has(row) || !row.isConnected) unmark(row); });
    byRow.forEach((changes, row) => { if (row.isConnected) mark(row, changes); });

    let total = 0;
    modal.querySelectorAll(".settings-modal__category[data-settings-category]").forEach((button) => {
      const n = perCategory[button.dataset.settingsCategory] || 0;
      total += n;
      button.classList.toggle("settings-modal__category--changed", n > 0);
      let badge = button.querySelector(".settings-modal__count");
      if (n > 0) {
        if (!badge) { badge = el("span", "settings-modal__count"); button.appendChild(badge); }
        badge.textContent = String(n);
        badge.title = t(n === 1 ? "SETTINGS_COUNT_ONE" : "SETTINGS_COUNT_N", { n });
      } else if (badge) badge.remove();
    });
    modal.querySelectorAll(".settings-pane-head").forEach((head) => {
      const category = head.dataset.category;
      const reset = head.querySelector(".settings-pane-reset");
      if (reset) reset.hidden = !inCategory(category).some((p) => typeof p.reset === "function");
    });
    const save = document.getElementById("settings-save");
    if (save) {
      save.textContent = saveLabel(total);
      save.classList.toggle("settings-save--changes", total > 0);
      save.disabled = total === 0;                                   // ohne Aenderung gibt es nichts zu speichern
    }
  }

  // ------------------------------------------------------------------------------------------ Kopf jeder Kategorie
  function buildHeads() {
    const modal = root();
    if (!modal) return;
    modal.querySelectorAll("[data-settings-pane]").forEach((pane) => {
      if (pane.querySelector(":scope > .settings-pane-head")) return;
      const category = pane.dataset.settingsPane;
      const button = modal.querySelector('.settings-modal__category[data-settings-category="' + category + '"]');
      const label = button && button.querySelector("[data-i18n]");
      const head = el("div", "settings-pane-head");
      head.dataset.category = category;
      const text = el("div", "settings-pane-head__text");
      const title = el("h3", "settings-pane-head__title");
      if (label) { title.dataset.i18n = label.dataset.i18n; title.textContent = i18n(label.dataset.i18n); }
      text.appendChild(title);
      const intro = pane.querySelector(":scope > .settings-pane-intro");
      if (intro) text.appendChild(intro);
      head.appendChild(text);
      const reset = el("button", "modal__button settings-pane-reset");
      reset.type = "button";
      reset.hidden = true;
      reset.append(Icons.svg("refresh"), el("span", "", t("SETTINGS_RESET")));
      reset.querySelector("span").dataset.i18n = "SETTINGS_RESET";
      reset.title = t("SETTINGS_RESET_TIP");
      reset.dataset.i18nTitle = "SETTINGS_RESET_TIP";
      reset.addEventListener("click", () => resetCategory(category, title.textContent));
      head.appendChild(reset);
      pane.prepend(head);
    });
  }

  async function resetCategory(category, name) {
    const targets = inCategory(category).filter((p) => typeof p.reset === "function");
    if (!targets.length) return;
    const ok = await _askLayoutConfirm({ title: t("SETTINGS_RESET_TITLE"), body: t("SETTINGS_RESET_BODY", { name }), confirmKey: "SETTINGS_RESET" });
    if (!ok) return;
    await Promise.all(targets.map(async (p) => { try { await p.reset(); } catch (err) { console.error(err); } }));      // reset() darf asynchron sein (KI/Sprache laden ihren Stand erst)
    touch();
    if (typeof _showToast === "function") _showToast(t("SETTINGS_RESET_DONE", { name }), "info", 3500);
  }

  /** Unten links: ALLE Kategorien auf Standard (auch Sprache) - ebenfalls nur als Entwurf, gespeichert wird mit "Speichern". */
  async function resetAll() {
    const targets = [...providers.values()].filter((p) => typeof p.reset === "function");
    if (!targets.length) return;
    const ok = await _askLayoutConfirm({ title: t("SETTINGS_RESET_ALL_TITLE"), body: t("SETTINGS_RESET_ALL_BODY"), confirmKey: "SETTINGS_RESET" });
    if (!ok) return;
    await Promise.all(targets.map(async (p) => { try { await p.reset(); } catch (err) { console.error(err); } }));      // reset() darf asynchron sein (KI/Sprache laden ihren Stand erst)
    touch();
    if (typeof _showToast === "function") _showToast(t("SETTINGS_RESET_ALL_DONE"), "info", 3500);
  }

  /** Abbrechen / Schliessen / Esc: mit Aenderungen erst nachfragen. Gibt true zurueck, wenn geschlossen werden darf. */
  async function confirmDiscard() {
    const n = count();
    if (!n) return true;
    if (discarding) return false;
    discarding = true;
    try {
      return await _askLayoutConfirm({ title: t("SETTINGS_DISCARD_TITLE"), body: t(n === 1 ? "SETTINGS_DISCARD_ONE" : "SETTINGS_DISCARD_N", { n }), confirmKey: "SETTINGS_DISCARD_CONFIRM" });
    } finally {
      discarding = false;
    }
  }

  // ------------------------------------------------------------------------------------------ Einstellungen sichern: exportieren / importieren
  // Exportiert wird der GESPEICHERTE Stand aller Seiten als eine JSON-Datei; geraetebezogene Werte (Skalierung, Wischen, Datenordner) und Geheimnisse (Passwoerter, Zugangsschluessel) bleiben draussen.
  // Importieren schreibt die Werte nur als ENTWURF in die Seiten: jede Aenderung ist markiert und gezaehlt, uebernommen wird sie erst mit "Speichern".
  const EXPORT_SKIP = /gui-scale|data-path|password|swipe|token|key$/i;
  function exportControls() {
    const modal = root();
    const out = [];
    STATIC_CATEGORIES.forEach((category) => {
      const pane = modal && modal.querySelector('[data-settings-pane="' + category + '"]');
      if (!pane) return;
      pane.querySelectorAll(".settings-field").forEach((row) => {
        if (row.closest("[data-track-skip], .theme-root, #settings-api-root, #settings-ai-root, #settings-voice-root")) return;
        row.querySelectorAll("input, select, textarea").forEach((c) => {
          if (c.id && !READ_SKIP.has(c.type) && c.type !== "password" && !c.readOnly && !c.hasAttribute("data-track-skip") && !EXPORT_SKIP.test(c.id)) out.push(c);
        });
      });
    });
    return out;
  }
  async function exportAll() {
    const fields = {};
    exportControls().forEach((c) => { fields[c.id] = isCheck(c) ? !!c.checked : c.type === "number" ? (c.value === "" ? "" : Number(c.value)) : c.value; });
    const sections = {};
    for (const provider of providers.values()) {
      if (typeof provider.exportData !== "function") continue;
      try { const data = await provider.exportData(); if (data) sections[provider.id] = data; } catch (err) { console.error(err); }
    }
    const ok = await window.OCTransfer.save("opencue-settings.json", { opencue_settings: 1, fields, sections });
    return ok;
  }
  async function importAll(data) {
    if (!data || typeof data !== "object" || data.opencue_settings !== 1) { if (typeof _showToast === "function") _showToast(t("SETTINGS_IMPORT_INVALID"), "error", 4500); return; }
    const before = count();
    const fields = data.fields && typeof data.fields === "object" ? data.fields : {};
    exportControls().forEach((c) => {
      if (!(c.id in fields)) return;
      const value = fields[c.id];
      if (isCheck(c)) { if (typeof value === "boolean") write(c, value); return; }
      if (c.tagName === "SELECT" && ![...c.options].some((o) => o.value === String(value))) return;
      if (typeof value === "string" || typeof value === "number") write(c, value);
    });
    const sections = data.sections && typeof data.sections === "object" ? data.sections : {};
    for (const provider of providers.values()) {
      if (typeof provider.importData !== "function" || !(provider.id in sections)) continue;
      try { await provider.importData(sections[provider.id]); } catch (err) { console.error(err); }
    }
    touch();
    const n = count();
    if (typeof _showToast === "function") _showToast(n ? t("SETTINGS_IMPORT_DONE", { n }) : t("SETTINGS_IMPORT_SAME"), "info", 4500);
  }
  async function importFromFile() { const data = await window.OCTransfer.pickJson(); if (data !== null) await importAll(data); }
  document.addEventListener("click", (e) => {
    const target = e.target && e.target.closest ? e.target : null;
    if (!target) return;
    if (target.closest("#settings-export")) exportAll();
    else if (target.closest("#settings-import")) importFromFile();
  });

  // ------------------------------------------------------------------------------------------ Anbindung
  function init() {
    const modal = root();
    if (!modal) return;
    buildHeads();
    STATIC_CATEGORIES.forEach(makeStatic);
    if (typeof ThemeUI !== "undefined") register({ id: "theme", category: "appearance", changes: () => ThemeUI.changes(), reset: () => ThemeUI.resetToDefault(), exportData: () => ThemeUI.getDraft(), importData: (d) => ThemeUI.importDraft(d) });      // Farben (app.js)
    modal.addEventListener("input", touch, true);
    modal.addEventListener("change", touch, true);
    document.addEventListener("settings-opened", () => { rebaseline(); setTimeout(() => bindMasters(), 0); });
    document.addEventListener("settings-saved", () => { setTimeout(touch, 0); });
    document.addEventListener("i18n-applied", () => { buildHeads(); touch(); });
    bindMasters();
    touch();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();

  window.OCSettings = { register, touch, count, exportAll, importAll, rebaseline, bindMasters, confirmDiscard, resetAll, isDiscarding: () => discarding, changes: () => [...providers.values()].flatMap((p) => changesOf(p).map((c) => ({ category: p.category, ...c }))) };
})();
