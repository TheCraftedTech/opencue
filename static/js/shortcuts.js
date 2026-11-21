// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Eingebaute Tastenkuerzel des Programms (Strg+S, F11 ...) umbelegen oder abschalten: Dialog "Tastenkuerzel" -> "Kuerzel bearbeiten".
 *
 * Die Standardtasten und was jede Aktion tut stehen hier (ACTIONS); der Server (app/hotkeys.py) speichert nur die Umbelegungen {Aktion: Kombination, "" = aus} in der App-Config und
 * verteilt sie (WS `set_shortcut_overrides` -> `shortcuts_changed`). Eingebaut wird das als Schicht VOR den festen Kuerzeln in app.js (setupKeyboardShortcuts ruft handle(e)):
 *   - ist die gedrueckte Kombination die NEUE Taste einer Aktion, wird diese ausgefuehrt;
 *   - ist es die STANDARDtaste einer umbelegten Aktion, passiert nichts (sie ist frei, der Browser bekommt sie auch nicht);
 *   - sonst laufen die festen Kuerzel wie immer.
 * Nicht umbelegbar sind die Kuerzel, die vom Zusammenhang abhaengen (Esc, Strg+C/X/V fuer Panels, Strg+1-9, Pfeile, 3D-Bearbeitung).
 * Aufnahme der Taste: dieselbe Aufnahme wie bei "Eigene Tastaturbelegung" (static/js/hotkeys.js): anklicken, Kombination druecken, loslassen = gesetzt.
 * Aufruf: window.OCShortcuts.handle(event) -> true, wenn die Taste verbraucht wurde. */
(function () {
  "use strict";

  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    if (vars) for (const name of Object.keys(vars)) text = text.split("{" + name + "}").join(String(vars[name]));
    return text;
  };
  const $ = (selector, root) => (root || document).querySelector(selector);
  const H = () => window.OCHotkeys;
  const ROOT = '[data-modal-backdrop="keyboard-shortcuts"]';

  const scaleBy = (step) => () => {
    const cur = parseFloat(document.documentElement.style.getPropertyValue("--gui-scale")) || (client.state && client.state.gui_scale) || 1.0;
    const next = step > 0 ? Math.min(SETTINGS_GUI_SCALE_MAX, parseFloat((cur + step).toFixed(2))) : Math.max(SETTINGS_GUI_SCALE_MIN, parseFloat((cur + step).toFixed(2)));
    client.setGuiScale(next);
  };

  /** id, Standardtasten (die erste ist die "Hauptform", die anderen gelten mit), Beschriftung (Sprachschluessel), ob es auch in einem Textfeld ausloest, Menuepunkt (data-action) mit Hinweis. */
  const ACTIONS = [
    { id: "new", keys: ["Ctrl+N"], label: "SHORTCUTS_NEW", menu: "new-show", run: () => _guardUnsavedChanges(() => Modal.open("new-show-confirm")) },
    { id: "open", keys: ["Ctrl+O"], label: "SHORTCUTS_OPEN", menu: "open-show", run: () => window.OCFileManager.open("shows") },
    { id: "file_manager", keys: ["Ctrl+M"], label: "SHORTCUTS_FILE_MANAGER", menu: "file-manager", run: () => window.OCFileManager.open() },
    { id: "save", keys: ["Ctrl+S"], label: "SHORTCUTS_SAVE", menu: "save-show", inInputs: true,
      run: () => { const name = client.state && client.state.showfile_name; if (!name || name === "Untitled") _openSaveAsModal(); else _saveShowDirect(); } },
    { id: "save_as", keys: ["Ctrl+Shift+S"], label: "SHORTCUTS_SAVE_AS", menu: "save-show-as", inInputs: true, run: () => _openSaveAsModal() },
    { id: "exit", keys: ["Ctrl+Q"], label: "SHORTCUTS_EXIT", menu: "exit", run: () => client.send("exit_app") },
    { id: "help", keys: ["F1"], label: "SHORTCUTS_HELP_VIEWER", menu: "open-help-viewer", inInputs: true,
      run: () => { if (window.OCHelp) { if (window.OCHelp.isOpen()) window.OCHelp.focusSearch(); else window.OCHelp.open(); } } },
    { id: "fullscreen", keys: ["F11"], label: "SHORTCUTS_FULLSCREEN", inInputs: true, run: () => toggleFullscreen() },
    { id: "scale_up", keys: ["Ctrl+=", "Ctrl+Shift+=", "Ctrl+NumAdd"], label: "SHORTCUTS_SCALE_UP", run: scaleBy(0.05) },
    { id: "scale_down", keys: ["Ctrl+-", "Ctrl+NumSub"], label: "SHORTCUTS_SCALE_DOWN", run: scaleBy(-0.05) },
    { id: "scale_reset", keys: ["Ctrl+0", "Ctrl+Num0"], label: "SHORTCUTS_SCALE_RESET", run: () => client.setGuiScale(1.0) },
    { id: "cmd_window", keys: ["Ctrl+F"], label: "SHORTCUTS_CMD_WINDOW", inInputs: true, run: () => { if (window.OCPanelWindow) window.OCPanelWindow.toggle(window.OCPanelWindow.CONSOLE); } },
    { id: "edit_mode", keys: ["Ctrl+E"], label: "SHORTCUTS_EDIT_PANELS", menu: "toggle-edit-mode", run: () => toggleEditModeInteractive() },
    { id: "undo", keys: ["Ctrl+Z"], label: "SHORTCUTS_UNDO", menu: "undo", run: () => ocUndoRun("undo") },
    { id: "redo", keys: ["Ctrl+Y", "Ctrl+Shift+Z"], label: "SHORTCUTS_REDO", run: () => ocUndoRun("redo") },
    { id: "language", keys: ["Ctrl+Shift+L"], label: "SHORTCUTS_LANGUAGE_TOGGLE", run: () => _toggleLanguage() },
    { id: "reload_layout", keys: ["F5"], label: "SHORTCUTS_RELOAD_LAYOUT", menu: "reload-layout", inInputs: true, run: () => reloadLayout() },
    { id: "reload_ui", keys: ["Ctrl+F5"], label: "SHORTCUTS_RELOAD_UI", menu: "reload-ui", inInputs: true, run: () => reloadUi() },
    { id: "lock", keys: ["Ctrl+L"], label: "SHORTCUTS_LOCK", menu: "lock-console", inInputs: true, run: () => { if (window.OCLock) window.OCLock.lockNow(true); } },
  ];
  const BY_ID = new Map(ACTIONS.map((a) => [a.id, a]));

  let overrides = {};                                 // {id: Kombination | ""}
  let byNewKey = new Map();                           // neue Kombination -> Aktion
  let shadowed = new Set();                           // Standardtasten umbelegter / abgeschalteter Aktionen: frei, tun nichts
  let editing = false;
  let recording = null;                               // Aktions-Id, deren Taste gerade aufgenommen wird

  const effective = (action) => (action.id in overrides ? (overrides[action.id] ? [overrides[action.id]] : []) : action.keys);

  function rebuild() {
    byNewKey = new Map();
    shadowed = new Set();
    for (const action of ACTIONS) {
      if (!(action.id in overrides)) continue;
      action.keys.forEach((k) => shadowed.add(k));
      if (overrides[action.id]) byNewKey.set(overrides[action.id], action);
    }
    for (const key of byNewKey.keys()) shadowed.delete(key);          // eine Standardtaste, die jetzt einer anderen Aktion gehoert, gilt fuer diese
    syncReserved();
    paintHints();
    paintDialog();
  }

  /** Die Tabelle der "vom Programm belegten" Tasten (hotkeys.js) folgt den Umbelegungen: so verweigert auch die eigene Tastaturbelegung die richtigen Tasten. */
  function syncReserved() {
    const table = H() && H().reserved;
    if (!table) return;
    for (const action of ACTIONS) action.keys.forEach((k) => { if (table[k] === action.label) delete table[k]; });
    for (const action of ACTIONS) effective(action).forEach((k) => { table[k] = action.label; });
  }

  const pretty = (combo) => combo.replace(/Shift/g, "⇧");

  function paintHints() {
    for (const action of ACTIONS) {
      if (!action.menu) continue;
      document.querySelectorAll('[data-action="' + action.menu + '"] .menu__shortcut-hint').forEach((hint) => {
        if (!("orig" in hint.dataset)) { hint.dataset.orig = hint.textContent; hint.dataset.origKey = hint.getAttribute("data-i18n") || ""; }
        if (action.id in overrides) {
          hint.removeAttribute("data-i18n");                         // sonst schreibt die Uebersetzung den Standardtext wieder hinein
          hint.textContent = overrides[action.id] ? pretty(overrides[action.id]) : "";
        } else {
          if (hint.dataset.origKey) hint.setAttribute("data-i18n", hint.dataset.origKey);
          hint.textContent = hint.dataset.origKey ? t(hint.dataset.origKey) : hint.dataset.orig;
        }
      });
    }
  }

  // ------------------------------------------------------------------------------------------------ Tasten verarbeiten
  const isTyping = (target) => !!(target && target.closest && target.closest("input, textarea, select, [contenteditable='true'], [contenteditable='']"));

  function handle(e) {
    if (!H() || !Object.keys(overrides).length) return false;
    const combo = H().comboOf(e);
    if (!combo) return false;
    const action = byNewKey.get(combo);
    if (action) {
      if (isTyping(e.target) && !action.inInputs) return false;
      e.preventDefault();
      try { action.run(); } catch (err) { console.error("Shortcut " + action.id + ":", err); }
      return true;
    }
    if (shadowed.has(combo)) { e.preventDefault(); return true; }
    return false;
  }

  // ------------------------------------------------------------------------------------------------ Dialog
  function message(text) {
    const box = $("#shortcuts-msg");
    if (box) { box.textContent = text || ""; box.hidden = !text; }
  }

  function rowFor(id) { return $(ROOT + ' .shortcuts-row[data-sc="' + id + '"]'); }

  function paintDialog() {
    const root = $(ROOT);
    if (!root) return;
    root.classList.toggle("sc--editing", editing);
    const toggle = $("#shortcuts-edit-toggle");
    if (toggle) toggle.textContent = t(editing ? "SC_EDIT_DONE" : "SC_EDIT");
    const resetAll = $("#shortcuts-reset-all");
    if (resetAll) resetAll.hidden = !editing || !Object.keys(overrides).length;
    const hint = $("#shortcuts-edit-hint");
    if (hint) hint.hidden = !editing;
    for (const action of ACTIONS) {
      const row = rowFor(action.id);
      if (!row) continue;
      const kbd = row.querySelector("kbd");
      if (!kbd) continue;
      if (!("orig" in kbd.dataset)) kbd.dataset.orig = kbd.textContent;
      row.classList.toggle("sc-row--custom", action.id in overrides);
      row.classList.toggle("sc-row--rec", recording === action.id);
      if (recording !== action.id) kbd.textContent = action.id in overrides ? (overrides[action.id] ? pretty(overrides[action.id]) : t("SC_NONE")) : (kbd.getAttribute("data-i18n") ? t(kbd.getAttribute("data-i18n")) : kbd.dataset.orig);          // Standardtaste in der Sprache der Oberflaeche (Strg / Ctrl ...), nicht der beim ersten Zeichnen gemerkte Text
      let tools = row.querySelector(".sc-tools");
      if (!tools) {
        tools = document.createElement("span");
        tools.className = "sc-tools";
        for (const [act, icon, tip] of [["off", "close", "SC_OFF"], ["reset", "undo", "SC_RESET_ONE"]]) {
          const b = document.createElement("button");
          b.type = "button";
          b.className = "sc-mini";
          b.dataset.scAct = act;
          b.title = t(tip);
          b.setAttribute("aria-label", t(tip));
          if (typeof Icons !== "undefined") b.appendChild(Icons.svg(icon));
          tools.appendChild(b);
        }
        row.appendChild(tools);
      }
      tools.querySelectorAll("button[data-sc-act]").forEach((b) => {            // bei jedem Zeichnen neu: die Texte stehen erst nach dem Laden der Sprache (und nach einem Sprachwechsel) richtig da
        const tip = b.dataset.scAct === "off" ? "SC_OFF" : "SC_RESET_ONE";
        b.title = t(tip);
        b.setAttribute("aria-label", t(tip));
      });
      tools.querySelector('[data-sc-act="reset"]').hidden = !(action.id in overrides);
      tools.querySelector('[data-sc-act="off"]').hidden = action.id in overrides && !overrides[action.id];
    }
  }

  function persist() {
    if (typeof client !== "undefined" && client.send) client.send("set_shortcut_overrides", { overrides });
  }

  function conflictOf(combo, id) {
    const { mods, keys } = H().parse(combo);
    if (keys.length !== 1) return t("SC_ERR_ONEKEY");
    if (!mods.length && !/^F([1-9]|1[0-9]|2[0-4])$/.test(keys[0])) return t("SC_ERR_BARE");
    const own = BY_ID.get(id);
    if (effective(own).includes(combo)) return "";
    const what = H().reservedLabel(combo);
    if (what) return t("SC_ERR_CONFLICT", { keys: combo, what });
    if ((H().list || []).some((r) => r.keys === combo && !r.device)) return t("SC_ERR_ROW", { keys: combo });
    return "";
  }

  function setKey(id, combo) {
    const action = BY_ID.get(id);
    if (combo !== "" && action.keys.includes(combo)) delete overrides[id];             // wieder die Standardtaste (oder eine ihrer Nebenformen): keine Umbelegung
    else overrides[id] = combo;
    persist();
    rebuild();
  }

  function startRecording(id) {
    if (!H()) return;
    recording = id;
    message("");
    const kbd = rowFor(id).querySelector("kbd");
    kbd.textContent = t("SC_PRESS");
    paintDialog();
    H().startRecorder({
      collect: true,
      onLive: (live) => { kbd.textContent = live || t("SC_PRESS"); },
      onDone: (combo) => {
        recording = null;
        const why = conflictOf(combo, id);
        if (why) { message(why); paintDialog(); return; }
        setKey(id, combo);
      },
      onCancel: () => { recording = null; paintDialog(); },
    });
  }

  function setEditing(on) {
    editing = !!on;
    if (!editing && H()) H().stopRecorder();
    recording = null;
    message("");
    paintDialog();
  }

  function bind() {
    const root = $(ROOT);
    if (!root || root.dataset.scBound) return;
    root.dataset.scBound = "1";
    root.addEventListener("click", (e) => {
      const tog = e.target.closest("#shortcuts-edit-toggle");
      if (tog) { setEditing(!editing); return; }
      if (e.target.closest("#shortcuts-reset-all")) { overrides = {}; persist(); rebuild(); message(""); return; }
      const mini = e.target.closest("[data-sc-act]");
      const row = e.target.closest(".shortcuts-row[data-sc]");
      if (!row || !editing) return;
      const id = row.dataset.sc;
      if (mini) {
        if (mini.dataset.scAct === "reset") { delete overrides[id]; persist(); rebuild(); message(""); }
        else { overrides[id] = ""; persist(); rebuild(); message(""); }
        return;
      }
      if (e.target.closest("kbd")) startRecording(id);
    });
    document.addEventListener("click", () => { setTimeout(() => { if (editing && !Modal.isOpen("keyboard-shortcuts")) setEditing(false); }, 0); });         // Dialog geschlossen (X, Hintergrund): Aufnahme beenden
  }

  // Menue "Steuerung" -> "Tastenkuerzel ..." (das Hilfe-Menue hat seinen eigenen Eintrag fuer dieselbe Uebersicht, siehe app.js setupHelpMenu)
  document.addEventListener("click", (e) => {
    if (!e.target.closest('[data-menu="controls"] [data-action="open-shortcuts-modal"]')) return;
    if (typeof _closeAllMenus === "function") _closeAllMenus();
    Modal.open("keyboard-shortcuts");
    bind();
    setEditing(false);                                            // frisch geoeffnet: immer die Uebersicht, nicht ein uebrig gebliebener Bearbeiten-Zustand
  });

  document.addEventListener("i18n-applied", () => { paintDialog(); paintHints(); });          // Sprache gewechselt: Tastennamen (Strg / Ctrl ...) neu schreiben

  document.addEventListener("shortcuts-changed", () => {
    overrides = Object.assign({}, window.__shortcuts || {});
    rebuild();
  });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind); else bind();
  overrides = Object.assign({}, window.__shortcuts || {});
  rebuild();

  /** Taste "?": die Uebersicht ein- und ausblenden (nicht beim Tippen in ein Feld, nicht ueber einem anderen Dialog, nicht waehrend eine Taste aufgenommen wird). */
  function toggleOverview() {
    const stack = (typeof Modal !== "undefined" && Modal._stack) || [];
    if (Modal.isOpen("keyboard-shortcuts")) {
      if (stack[stack.length - 1] !== "keyboard-shortcuts" || recording) return false;
      Modal.close("keyboard-shortcuts");
      return true;
    }
    if (stack.length) return false;
    if (typeof _closeAllMenus === "function") _closeAllMenus();
    Modal.open("keyboard-shortcuts");
    bind();
    setEditing(false);
    return true;
  }

  window.OCShortcuts = { toggleOverview, handle, ACTIONS, get overrides() { return overrides; }, refresh: () => { bind(); setEditing(false); }, setEditing };
})();
