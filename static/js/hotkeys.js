// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Eigene Tastaturbelegung: eine Taste oder Tastenkombination (Strg+H, Strg+H+J, Leertaste, Ziffernblock 1 ...) loest einen Befehl der Befehlszeile aus.
 *
 * - Die Liste liegt am Server (app/hotkeys.py, App-Config, gilt fuer alle Geraete): window.__hotkeys, Aenderungen kommen als `hotkeys-changed`.
 * - Eine Zeile bekommt ihre Taste NUR ueber den Dialog "Taste festlegen" (Tastatur-Knopf der Zeile): dort wird aufgenommen (10 s) und die Geltung gewaehlt
 *   ("Alle Tastaturen" oder "Nur diese Tastatur"). An der Konsole unter Windows nimmt der Server auf (app/rawkeys.py: er erkennt die Tastatur); sonst - Tablet,
 *   andere Systeme - nimmt der Browser auf (nur "Alle Tastaturen").
 * - Ausloesen beim DRUECKEN (nicht beim Loslassen): ein Tastendruck in der Aufnahme-Phase des Dokuments (vor allen anderen Kuerzeln). Das Programm belegte
 *   Kombinationen sind gesperrt. Eine Kombination darf mehrere Haupttasten haben (Strg+H+J): sie gilt, sobald alle gedrueckt sind. Gibt es zu einer
 *   Kombination eine laengere (Strg+H und Strg+H+J), wartet die kuerzere kurz, ob noch eine Taste dazukommt.
 *   In Eingabefeldern gelten nur Kombinationen mit Strg (nicht Strg+Alt = AltGr), bei offenem Dialog keine einfachen Tasten, im Hotkey-Dialog selbst gar keine.
 * - Der Befehl laeuft ueber window.__widgetAction (dieselbe Funktion wie Button/Toggle/Fader): "direkt ausfuehren" oder "nur in die Befehlszeile schreiben", mit/ohne Verlauf.
 * - Zeilen fuer eine BESTIMMTE Tastatur (device) loest der Server aus (Windows Raw Input), nicht der Browser.
 * Die Schreibweise der Taste ist unabhaengig von der Tastaturbelegung (Browser-`code`): "Ctrl+Shift+H", "Ctrl+H+J", "Space", "Num1", "F5". Haupttasten stehen sortiert. */
(function () {
  "use strict";

  const RECORD_SECONDS = 10;
  const MAX_ROWS = 500;
  const MAX_KEYS = 4;
  const CHORD_WAIT = 180;                              // ms: so lange wartet eine kuerzere Kombination auf eine moegliche laengere
  const DEVICE_WAIT = 150;                             // ms: eine Zeile fuer "alle Tastaturen" wartet kurz, ob dieselbe Taste gerade von einer bestimmten Tastatur kam (alte Listen)
  const DEBOUNCE_MS = 80;                              // dieselbe Zeile loest nie zweimal innerhalb dieser Zeit aus
  const STALE_MS = 30000;
  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    Object.keys(vars || {}).forEach((name) => { text = text.split("{" + name + "}").join(String(vars[name])); });
    return text;
  };
  const el = (tag, cls, text) => { const node = document.createElement(tag); if (cls) node.className = cls; if (text != null) node.textContent = text; return node; };
  const send = (type, payload) => { if (typeof client !== "undefined" && client && client.send) client.send(type, payload || {}); };
  const isLocal = () => { try { return !!(client.state && client.state.is_local); } catch (err) { return false; } };
  const $ = (id) => document.getElementById(id);

  // ------------------------------------------------------------------ Tastennamen
  const MOD_ORDER = ["Ctrl", "Alt", "Shift", "Meta"];
  const MOD_CODES = { ControlLeft: "Ctrl", ControlRight: "Ctrl", AltLeft: "Alt", AltRight: "Alt", ShiftLeft: "Shift", ShiftRight: "Shift", MetaLeft: "Meta", MetaRight: "Meta", OSLeft: "Meta", OSRight: "Meta" };
  const NAMED = {
    Space: "Space", Enter: "Enter", Tab: "Tab", Backspace: "Backspace", Delete: "Delete", Insert: "Insert", Home: "Home", End: "End", PageUp: "PageUp", PageDown: "PageDown",
    ArrowUp: "Up", ArrowDown: "Down", ArrowLeft: "Left", ArrowRight: "Right", Escape: "Esc", Minus: "-", Equal: "=", BracketLeft: "[", BracketRight: "]", Backslash: "\\",
    Semicolon: ";", Quote: "'", Comma: ",", Period: ".", Slash: "/", Backquote: "`", IntlBackslash: "<", CapsLock: "CapsLock", ScrollLock: "ScrollLock", NumLock: "NumLock", PrintScreen: "PrintScreen",
    NumpadAdd: "NumAdd", NumpadSubtract: "NumSub", NumpadMultiply: "NumMul", NumpadDivide: "NumDiv", NumpadDecimal: "NumDec", NumpadEnter: "NumEnter",
  };
  // (Kein "+" in einem Tastennamen: "+" trennt die Teile einer Kombination - app/rawkeys.py benutzt dieselben Namen.)

  /** Name der Haupttaste ("H", "5", "Num1", "F5", "Space") oder "" fuer Modifikatoren / Unbekanntes. */
  function mainKey(e) {
    const code = e.code || "";
    if (MOD_CODES[code]) return "";
    let m;
    if ((m = /^Key([A-Z])$/.exec(code))) return m[1];
    if ((m = /^Digit([0-9])$/.exec(code))) return m[1];
    if ((m = /^Numpad([0-9])$/.exec(code))) return "Num" + m[1];
    if (/^F([1-9]|1[0-9]|2[0-4])$/.test(code)) return code;
    if (NAMED[code]) return NAMED[code];
    if (!code || code === "Unidentified") return e.key && e.key.length === 1 && /[A-Za-z0-9]/.test(e.key) ? e.key.toUpperCase() : "";           // z. B. Bildschirmtastatur
    return "";
  }

  function modsOf(e) {
    const mods = [];
    if (e.ctrlKey) mods.push("Ctrl");
    if (e.altKey) mods.push("Alt");
    if (e.shiftKey) mods.push("Shift");
    if (e.metaKey) mods.push("Meta");
    return mods;
  }

  /** "Ctrl+H+J": Modifikatoren in fester Reihenfolge, dann die Haupttasten sortiert. */
  const build = (mods, keys) => MOD_ORDER.filter((m) => mods.includes(m)).concat([...keys].sort()).join("+");
  function parse(combo) {
    const mods = [], keys = [];
    String(combo || "").split("+").forEach((part) => { if (!part) return; (MOD_ORDER.includes(part) ? mods : keys).push(part); });
    return { mods, keys };
  }

  // ------------------------------------------------------------------ vom Programm belegt
  const RESERVED = {
    "Ctrl+N": "SHORTCUTS_NEW", "Ctrl+O": "SHORTCUTS_OPEN", "Ctrl+S": "SHORTCUTS_SAVE", "Ctrl+Shift+S": "SHORTCUTS_SAVE_AS", "Ctrl+Q": "SHORTCUTS_EXIT",
    "F1": "SHORTCUTS_HELP_VIEWER", "F11": "SHORTCUTS_FULLSCREEN", "Ctrl+=": "SHORTCUTS_SCALE_UP", "Ctrl+Shift+=": "SHORTCUTS_SCALE_UP", "Ctrl+NumAdd": "SHORTCUTS_SCALE_UP",
    "Ctrl+-": "SHORTCUTS_SCALE_DOWN", "Ctrl+NumSub": "SHORTCUTS_SCALE_DOWN", "Ctrl+0": "SHORTCUTS_SCALE_RESET", "Ctrl+Num0": "SHORTCUTS_SCALE_RESET",
    "Ctrl+F": "SHORTCUTS_CMD_WINDOW", "Esc": "SHORTCUTS_CLOSE_DIALOG", "Ctrl+E": "SHORTCUTS_EDIT_PANELS",
    "Ctrl+C": "SHORTCUTS_PANEL_CLIPBOARD", "Ctrl+X": "SHORTCUTS_PANEL_CLIPBOARD", "Ctrl+V": "SHORTCUTS_PANEL_CLIPBOARD",
    "Ctrl+Z": "SHORTCUTS_UNDO", "Ctrl+Shift+Z": "SHORTCUTS_UNDO", "Ctrl+Y": "SHORTCUTS_REDO", "Ctrl+Shift+L": "SHORTCUTS_LANGUAGE_TOGGLE", "Ctrl+M": "SHORTCUTS_FILE_MANAGER", "Ctrl+L": "SHORTCUTS_LOCK", "F5": "SHORTCUTS_RELOAD_LAYOUT", "Ctrl+F5": "SHORTCUTS_RELOAD_UI",
    "Left": "SHORTCUTS_LAYOUT_STEP", "Right": "SHORTCUTS_LAYOUT_STEP",
  };
  for (let n = 1; n <= 9; n += 1) { RESERVED["Ctrl+" + n] = "SHORTCUTS_LAYOUT"; RESERVED["Ctrl+Num" + n] = "SHORTCUTS_LAYOUT"; }
  const SYSTEM = ["Ctrl+A", "Ctrl+W", "Ctrl+T", "Ctrl+R", "Ctrl+P", "Ctrl+Tab", "Ctrl+Shift+T", "Ctrl+Shift+N", "Ctrl+Shift+I", "F12", "Alt+F4", "Alt+Tab", "Ctrl+Shift+Tab"];

  /** Text, wofuer die Kombination (oder die erste Taste darin mit denselben Modifikatoren) schon vergeben ist: Programm oder Browser/System; sonst "". */
  function reservedLabel(combo) {
    const { mods, keys } = parse(combo);
    for (const candidate of [combo].concat(keys.length > 1 ? keys.map((k) => build(mods, [k])) : [])) {
      if (RESERVED[candidate]) return t(RESERVED[candidate]);
      if (SYSTEM.includes(candidate)) return t("HOTKEYS_RESERVED_SYSTEM");
    }
    return "";
  }

  // ------------------------------------------------------------------ Liste
  let list = [];                                       // Arbeitskopie (wird nach jeder Aenderung zum Server geschickt)
  let byKeys = new Map();                              // Kombination -> erster aktiver Eintrag (alle Tastaturen) mit Befehl
  let parsed = [];                                     // { entry, mods, keys } der aktiven Eintraege fuer "alle Tastaturen"
  let deviceCombos = new Set();                        // Kombinationen, die auch fuer eine bestimmte Tastatur belegt sind
  const recentDevice = new Map();                      // Kombination -> Zeit, zu der der Server sie fuer eine bestimmte Tastatur ausgeloest hat
  const lastFire = new Map();                          // Zeilen-Id -> Zeit des letzten Ausloesens (Entprellen)
  const sentSigs = [];                                 // Abdruck der zuletzt gesendeten Listen (das Echo des Servers wird nicht noch einmal eingespielt)
  let sendTimer = null;

  const clone = (value) => JSON.parse(JSON.stringify(value));
  const sig = (rows) => JSON.stringify(rows.map((r) => [r.id, !!r.enabled, r.keys, String(r.command || "").split(/\s+/).filter(Boolean).join(" "), r.run !== false, r.log !== false, r.device || "", r.device_name || ""]));
  const active = (row) => row.enabled && row.keys && String(row.command || "").trim();

  function rebuild() {
    byKeys = new Map();
    parsed = [];
    deviceCombos = new Set();
    list.forEach((row) => {
      if (!active(row)) return;
      if (row.device) { deviceCombos.add(row.keys); return; }
      if (!byKeys.has(row.keys)) { byKeys.set(row.keys, row); parsed.push(Object.assign({ entry: row }, parse(row.keys))); }
    });
  }

  function persist(immediate) {
    rebuild();
    clearTimeout(sendTimer);
    const go = () => {
      sendTimer = null;
      sentSigs.push(sig(list));
      if (sentSigs.length > 30) sentSigs.shift();
      send("set_hotkeys", { hotkeys: clone(list) });
    };
    if (immediate) go(); else sendTimer = setTimeout(go, 350);
  }

  function randomId() { return Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-3); }

  // ------------------------------------------------------------------ Ausloesen
  const down = new Map();                              // code -> { name, seen }: gerade gedrueckte Haupttasten
  const handledUp = new Set();
  let pending = null;                                  // wartende (kuerzere) Kombination
  const isTyping = (target) => !!(target && target.closest && target.closest("input, textarea, select, [contenteditable='true'], [contenteditable='']"));

  function fire(entry) {
    const now = Date.now();
    if (now - (lastFire.get(entry.id) || 0) < DEBOUNCE_MS) return;                // doppelte Meldung derselben Taste
    lastFire.set(entry.id, now);
    if (typeof window.__widgetAction === "function") {
      window.__widgetAction({ action_mode: entry.run === false ? "write" : "run", log_to_history: entry.log !== false, write_append: false }, entry.command, true);
    }
  }

  function hasLonger(mods, keys) {
    return parsed.some((p) => p.mods.length === mods.length && mods.every((m) => p.mods.includes(m)) && p.keys.length > keys.length && keys.every((k) => p.keys.includes(k)));
  }

  function onKeyDown(e) {
    if (e.isComposing) return;
    const name = mainKey(e);
    if (name) {
      const now = Date.now();
      down.forEach((v, k) => { if (now - v.seen > STALE_MS) down.delete(k); });
      down.set(e.code, { name, seen: now });
    }
    if (rec || !name) return;
    if (pending) { clearTimeout(pending); pending = null; }
    if (!byKeys.size) return;
    const mods = modsOf(e);
    const keys = [...down.values()].map((v) => v.name);
    const combo = build(mods, keys);
    const entry = byKeys.get(combo);
    if (!entry) return;
    const strong = (e.ctrlKey || e.metaKey) && !e.altKey;                       // Strg/Cmd ohne Alt (Strg+Alt = AltGr beim Tippen)
    if (Modal.isOpen("hotkeys")) return;                                         // beim Bearbeiten der Liste loest nichts aus
    if (isTyping(e.target) && !strong) return;                                   // beim Tippen nur Strg-Kombinationen
    if (Modal._stack.length && !(e.ctrlKey || e.metaKey)) return;                // bei offenem Dialog keine einfachen Tasten
    e.preventDefault();
    e.stopImmediatePropagation();
    handledUp.add(e.code);
    if (e.repeat) return;                                                        // Taste gehalten: nur einmal
    const wait = hasLonger(mods, keys) ? CHORD_WAIT : (deviceCombos.has(combo) ? DEVICE_WAIT : 0);
    if (!wait) { fire(entry); return; }
    pending = setTimeout(() => {
      pending = null;
      if (deviceCombos.has(combo) && Date.now() - (recentDevice.get(combo) || 0) < 600) return;       // dieselbe Taste kam von einer bestimmten Tastatur: der Server hat es erledigt
      fire(entry);
    }, wait);
  }

  function onKeyUp(e) {
    down.delete(e.code);
    if (!handledUp.delete(e.code)) return;
    e.preventDefault();                                                           // z. B. Leertaste auf einem Knopf: kein zusaetzlicher Klick
  }

  window.addEventListener("blur", () => { down.clear(); if (pending) { clearTimeout(pending); pending = null; } });

  // ------------------------------------------------------------------ Meldung im Dialog
  /** Pruefung vor dem Uebernehmen einer Kombination fuer die Zeile `rowId` mit Geltung `device` ("" = alle Tastaturen). Gibt die Meldung oder "".
   *  Eine Taste gilt entweder fuer ALLE Tastaturen oder fuer bestimmte - nie beides (sonst koennte sie doppelt ausloesen); fuer zwei bestimmte Tastaturen darf sie verschieden sein. */
  function conflict(combo, rowId, device) {
    const reserved = reservedLabel(combo);
    if (reserved) return t("HOTKEYS_RESERVED", { keys: combo, what: reserved });
    const other = list.find((r) => r.id !== rowId && r.keys === combo && ((r.device || "") === (device || "") || !r.device || !device));
    if (other) return t(other.device && device ? "HOTKEYS_DUPLICATE" : "HOTKEYS_SCOPE_CLASH", { keys: combo });
    return "";
  }

  // ------------------------------------------------------------------ Aufnehmen im Browser (Tablet / ohne Windows) und Abfangen der Tasten waehrend der Aufnahme
  let rec = null;                                      // { collect, pressed:Set, mods:Set, keys:[], onLive, onDone, onCancel }

  function stopBrowserRecorder() {
    if (!rec) return;
    rec = null;
    delete document.documentElement.dataset.keyCapture;
    document.removeEventListener("keydown", onRecDown, true);
    document.removeEventListener("keyup", onRecUp, true);
  }

  /** Faengt alle Tasten ab (kein Kuerzel, kein Klick auf einen Knopf); mit collect=true werden sie zu einer Kombination aufgenommen. Esc ohne andere Taste bricht ab. */
  function startBrowserRecorder(options) {
    stopBrowserRecorder();
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
    rec = Object.assign({ collect: true, pressed: new Set(), mods: new Set(), keys: [], onLive: null, onDone: null, onCancel: null }, options);
    document.addEventListener("keydown", onRecDown, true);
    document.addEventListener("keyup", onRecUp, true);
    document.documentElement.dataset.keyCapture = "1";                 // Escape gehoert jetzt der Aufnahme (siehe app.js, Escape fuer Dialoge)
  }

  function onRecDown(e) {
    e.preventDefault();
    e.stopImmediatePropagation();
    if (!rec || e.repeat) return;
    if (e.code === "Escape" && !rec.pressed.size) { const cancel = rec.onCancel; stopBrowserRecorder(); if (cancel) cancel(); return; }
    rec.pressed.add(e.code);
    if (!rec.collect) return;
    modsOf(e).forEach((m) => rec.mods.add(m));
    const name = mainKey(e);
    if (name && !rec.keys.includes(name) && rec.keys.length < MAX_KEYS) rec.keys.push(name);
    if (rec.onLive) rec.onLive((rec.keys.length || rec.mods.size) ? build([...rec.mods], rec.keys) + (rec.keys.length ? "" : "+") : "");
  }

  function onRecUp(e) {
    e.preventDefault();
    e.stopImmediatePropagation();
    if (!rec) return;
    rec.pressed.delete(e.code);
    if (!rec.collect) return;
    const modifierUp = !!MOD_CODES[e.code];
    if (rec.keys.length && (!rec.pressed.size || modifierUp)) {                          // alle los (oder ein Modifikator losgelassen: macOS meldet das Loslassen der Haupttaste dann nicht immer)
      const combo = build([...rec.mods], rec.keys);
      const done = rec.onDone;
      stopBrowserRecorder();
      if (done) done(combo);
    } else if (!rec.pressed.size) { rec.mods.clear(); if (rec.onLive) rec.onLive(""); }
  }

  // ------------------------------------------------------------------ Liste im Dialog
  let pendingDelete = null;

  function toggle(row, field, tipKey, checkedDefault) {
    const { label, input } = makeToggleSwitch("hk-" + field + "-" + row.id, row[field] === undefined ? checkedDefault : row[field] !== false);
    label.title = t(tipKey);
    input.setAttribute("aria-label", t(tipKey));
    input.addEventListener("change", () => { row[field] = input.checked; persist(true); });
    return label;
  }

  const deviceLabel = (row) => row.device_name || t("HOTKEYS_DEV_UNKNOWN", { id: row.device });

  function buildRow(row) {
    const node = el("div", "hk__row");
    node.dataset.id = row.id;

    const on = toggle(row, "enabled", "HOTKEYS_ON_TIP", true);
    on.classList.add("hk__on");

    // Taste: ein Feld (Kombination, darunter ggf. die Tastatur) und der Tastatur-Knopf - beide oeffnen denselben Dialog
    const keyCell = el("div", "hk__keycell");
    const key = el("button", "modal__button hk__key" + (row.keys ? "" : " hk__key--empty"));
    key.type = "button";
    key.title = t("HOTKEYS_DEV_TIP");
    key.appendChild(el("span", "hk__keytext", row.keys || t("HOTKEYS_KEY_NONE")));
    if (row.device) {
      const chip = el("span", "hk__keydev");
      chip.append(Icons.svg("keyboard"), el("span", "", deviceLabel(row)));
      key.appendChild(chip);
    }
    key.addEventListener("click", () => openDeviceDialog(row.id));
    const dev = el("button", "modal__button hk__icon hk__devbtn" + (row.device ? " hk__devbtn--on" : ""));
    dev.type = "button";
    dev.title = t("HOTKEYS_DEV_TIP");
    dev.setAttribute("aria-label", t("HOTKEYS_DEV_TIP"));
    dev.appendChild(Icons.svg("keyboard"));
    dev.addEventListener("click", () => openDeviceDialog(row.id));
    keyCell.append(key, dev);

    const command = el("input", "modal__input hk__cmd");
    command.type = "text";
    command.value = row.command || "";
    command.placeholder = t("HOTKEYS_CMD_PLACEHOLDER");
    command.maxLength = 1000;
    command.addEventListener("input", () => { row.command = command.value; persist(false); });
    command.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); command.blur(); } });

    const run = toggle(row, "run", "HOTKEYS_RUN_TIP", true);
    const log = toggle(row, "log", "HOTKEYS_LOG_TIP", true);

    const del = el("button", "modal__button hk__icon hk__del");
    del.type = "button";
    del.title = t("HOTKEYS_DELETE_TIP");
    del.setAttribute("aria-label", t("HOTKEYS_DELETE_TIP"));
    del.appendChild(Icons.svg("trash"));
    del.addEventListener("click", () => askDelete(row));

    node.append(on, keyCell, command, run, log, del);
    return node;
  }

  function render() {
    const box = $("hotkeys-list");
    const empty = $("hotkeys-empty");
    if (!box) return;
    box.textContent = "";
    list.forEach((row) => box.appendChild(buildRow(row)));
    if (empty) empty.hidden = list.length > 0;
    const add = $("hotkeys-add");
    if (add) add.disabled = list.length >= MAX_ROWS;
  }

  /** Eine leere Zeile anhaengen - ohne Aufnahme: die Taste kommt nur ueber den Tastatur-Knopf der Zeile. */
  /** Neue Zeile. Mit `command` (Schnellstart: "Go" ...) ist der Befehl schon eingetragen und die Taste ist das Naechste, was fehlt: ein Klick darauf nimmt sie auf. */
  function addRow(command) {
    if (list.length >= MAX_ROWS) return;
    const row = { id: randomId(), enabled: true, keys: "", command: command || "", run: true, log: true, device: "", device_name: "" };
    list.push(row);
    persist(true);
    render();
    const node = document.querySelector('#hotkeys-list [data-id="' + row.id + '"]');
    if (node) { node.scrollIntoView({ block: "nearest" }); const focus = node.querySelector(command ? ".hk__key" : ".hk__cmd"); if (focus) focus.focus(); }
  }

  /** Die Belegung als Datei sichern / eine solche Datei einlesen. Beim Import kommen die Zeilen NEU DAZU; Tasten, die das Programm belegt oder die schon vergeben sind, werden uebersprungen. */
  function exportFile() {
    flush();
    window.OCTransfer.save("opencue-keyboard-mapping.json", { opencue_hotkeys: 1, hotkeys: clone(list) });
  }
  async function importFile() {
    const data = await window.OCTransfer.pickJson();
    if (data === null) return;
    const rows = Array.isArray(data) ? data : (data && data.hotkeys);
    if (!Array.isArray(rows)) { if (typeof _showToast === "function") _showToast(t("HOTKEYS_IMPORT_FAILED"), "error", 4000, true); return; }
    let added = 0, skipped = 0;
    rows.forEach((raw) => {
      if (!raw || typeof raw !== "object" || list.length >= MAX_ROWS) { skipped += 1; return; }
      const row = Object.assign({ enabled: true, keys: "", command: "", run: true, log: true, device: "", device_name: "" }, raw, { id: randomId() });
      if (row.keys && (reservedLabel(row.keys) || conflict(row.keys, row.id, row.device || ""))) { skipped += 1; return; }
      list.push(row);
      added += 1;
    });
    if (added) { persist(true); render(); }
    if (typeof _showToast === "function") _showToast(skipped ? t("HOTKEYS_IMPORTED_SKIPPED", { n: added, skipped }) : t("HOTKEYS_IMPORTED", { n: added }), added ? "info" : "error", 4500, true);
  }

  function askDelete(row) {
    pendingDelete = row.id;
    const body = $("hotkey-delete-body");
    if (body) body.textContent = row.keys ? t("HOTKEYS_DELETE_BODY", { keys: row.keys }) : t("HOTKEYS_DELETE_BODY_NONE");
    Modal.open("hotkey-delete-confirm");
  }

  function openDialog() {
    if (Modal.isOpen("keyboard-shortcuts")) Modal.close("keyboard-shortcuts");
    list = clone(window.__hotkeys || []);
    rebuild();
    render();
    Modal._hooks.hotkeys = () => flush();
    Modal.open("hotkeys");
  }

  function flush() { if (sendTimer) persist(true); }

  // ------------------------------------------------------------------ Dialog "Taste festlegen"
  let dev = null;                                      // { id, keys, device, name, recording, mode: "raw"|"browser", deadline, timer, live, info }

  function devMessage(text) {
    const box = $("hkdev-msg");
    box.textContent = text || "";
    box.hidden = !text;
  }

  function devPaint() {
    if (!dev || !$("hkdev-capture")) return;
    const capture = $("hkdev-capture");
    capture.classList.toggle("hk__capture--rec", dev.recording);
    capture.classList.toggle("hk__capture--empty", !dev.recording && !dev.keys);
    if (dev.recording) {
      const left = Math.max(0, Math.ceil((dev.deadline - Date.now()) / 1000));
      capture.textContent = dev.live ? dev.live + " …" : t("HOTKEYS_PRESS", { n: left });
    } else {
      capture.textContent = dev.keys || t("HOTKEYS_KEY_NONE");
    }
    const name = dev.device ? (dev.name || t("HOTKEYS_DEV_UNKNOWN", { id: dev.device })) : "";
    $("hkdev-from").textContent = name ? t("HOTKEYS_DEV_FROM", { name }) : "";
    $("hkdev-from").hidden = !name;
    const canDevice = !!dev.device;
    const one = $("hkdev-scope-one");
    one.disabled = !canDevice;
    $("hkdev-scope-one-sub").textContent = canDevice ? name : t(dev.mode === "browser" ? "HOTKEYS_DEV_ONE_SUB_BROWSER" : "HOTKEYS_DEV_ONE_SUB_NONE");
    if (!canDevice && one.checked) $("hkdev-scope-all").checked = true;
    $("hkdev-apply").disabled = !dev.keys;
  }

  function devStopRecording(notifyServer) {
    if (!dev) return;
    clearInterval(dev.timer);
    dev.recording = false;
    stopBrowserRecorder();
    if (notifyServer && dev.mode === "raw") send("rawkeys_record", { on: false });
    if (!dev.keys && dev.prev) { dev.keys = dev.prev.keys; dev.device = dev.prev.device; dev.name = dev.prev.name; }          // nichts aufgenommen (Esc, Zeit um): es bleibt bei der bisherigen Taste
    dev.prev = null;
  }

  /** Die Aufnahme im Dialog: an der Konsole nimmt der Server auf (er erkennt die Tastatur) und der Browser faengt die Tasten nur ab; sonst nimmt der Browser auf. */
  function devStartRecording() {
    if (!dev) return;
    clearInterval(dev.timer);
    devMessage("");
    if (!dev.recording) dev.prev = { keys: dev.keys, device: dev.device, name: dev.name };      // (laeuft sie schon - z. B. Wechsel auf Browser-Aufnahme - bleibt die bisherige Taste vermerkt)
    dev.keys = ""; dev.device = ""; dev.name = ""; dev.live = "";
    dev.recording = true;
    dev.mode = isLocal() && !(dev.info && dev.info.available === false) ? "raw" : "browser";
    dev.deadline = Date.now() + RECORD_SECONDS * 1000;
    dev.timer = setInterval(() => { if (Date.now() >= dev.deadline) devStopRecording(true); devPaint(); }, 200);
    startBrowserRecorder({
      collect: dev.mode === "browser",
      onLive: (label) => { dev.live = label; devPaint(); },
      onDone: (combo) => devGotKey(combo, "", ""),
      onCancel: () => { devStopRecording(true); devPaint(); },
    });
    if (dev.mode === "raw") send("rawkeys_record", { on: true });
    devPaint();
  }

  /** Die Geltung ("Alle Tastaturen" / "Nur diese Tastatur") prueft die Taste noch einmal gegen die Liste. */
  function devScopeDevice() { return $("hkdev-scope-one").checked && dev.device ? dev.device : ""; }

  /** Eine Taste wurde aufgenommen (Browser oder Server). */
  function devGotKey(combo, device, name) {
    dev.prev = null;
    devStopRecording(true);
    dev.live = "";
    dev.keys = combo;
    dev.device = device || "";
    dev.name = name || "";
    const reserved = reservedLabel(combo);
    if (reserved) {                                                                // vom Programm/Browser belegt: nicht uebernehmen
      devMessage(t("HOTKEYS_RESERVED", { keys: combo, what: reserved }));
      dev.keys = ""; dev.device = ""; dev.name = "";
    } else {
      devMessage(conflict(combo, dev.id, devScopeDevice()));
    }
    devPaint();
  }

  function openDeviceDialog(rowId) {
    const row = list.find((r) => r.id === rowId);
    if (!row) return;
    dev = { id: rowId, keys: row.keys, device: row.device || "", name: row.device_name || "", recording: false, mode: isLocal() ? "raw" : "browser", deadline: 0, timer: null, live: "", info: null };
    $("hkdev-reset").title = t("HOTKEYS_RESET");
    $("hkdev-reset").setAttribute("aria-label", t("HOTKEYS_RESET"));
    $("hkdev-scope-" + (row.device ? "one" : "all")).checked = true;
    devMessage("");
    Modal._hooks["hotkey-device"] = () => { devStopRecording(true); dev = null; };
    Modal.open("hotkey-device");
    if (isLocal()) send("rawkeys_status");
    devStartRecording();
  }

  function devApply() {
    if (!dev || !dev.keys) return;
    const row = list.find((r) => r.id === dev.id);
    if (!row) { Modal.close("hotkey-device"); return; }
    const device = $("hkdev-scope-one").checked && dev.device ? dev.device : "";
    const problem = conflict(dev.keys, row.id, device);
    if (problem) { devMessage(problem); return; }
    row.keys = dev.keys;
    row.device = device;
    row.device_name = device ? (dev.name || "") : "";
    persist(true);
    Modal.close("hotkey-device");
    render();
  }

  document.addEventListener("oc-hotkey-event", (e) => {
    const message = e.detail || {};
    const payload = message.payload || {};
    if (message.type === "hotkey_fire") {                                           // eine Taste einer bestimmten Tastatur hat etwas ausgeloest
      recentDevice.set(payload.keys, Date.now());
      if (payload.run === false && typeof window.__widgetAction === "function") window.__widgetAction({ action_mode: "write", write_append: false }, payload.command, false);
    } else if (message.type === "rawkeys_status") {
      if (!dev) return;
      dev.info = payload;
      if (payload.available === false && dev.recording && dev.mode === "raw") devStartRecording();         // ohne Windows-Mithoeren: der Browser nimmt auf
      else devPaint();
    } else if (message.type === "rawkeys_live") {
      if (dev && dev.recording && dev.mode === "raw") { dev.live = payload.keys || ""; devPaint(); }
    } else if (message.type === "rawkeys_recorded") {
      if (dev && dev.recording && dev.mode === "raw") devGotKey(payload.keys || "", payload.device || "", payload.name || "");
    }
  });

  document.addEventListener("change", (e) => {
    if (dev && e.target && e.target.name === "hkdev-scope" && dev.keys) devMessage(conflict(dev.keys, dev.id, devScopeDevice()));
  });

  document.addEventListener("click", (e) => {
    const target = e.target.closest ? e.target : null;
    if (!target) return;
    if (target.closest('[data-action="open-hotkeys-modal"]')) { if (typeof _closeAllMenus === "function") _closeAllMenus(); openDialog(); return; }
    if (target.closest("#hotkeys-add")) { addRow(); return; }
    const quick = target.closest("#hotkeys-quick [data-quick]");
    if (quick) { addRow(quick.dataset.quick); return; }
    if (target.closest("#hotkeys-export")) { exportFile(); return; }
    if (target.closest("#hotkeys-import")) { importFile(); return; }
    if (target.closest("#hkdev-reset")) { devStartRecording(); return; }
    if (target.closest("#hkdev-apply")) { devApply(); return; }
    if (target.closest("#hotkey-delete-confirm-button")) {
      const id = pendingDelete;
      pendingDelete = null;
      Modal.close("hotkey-delete-confirm");
      list = list.filter((r) => r.id !== id);
      persist(true);
      render();
    }
  });

  // Aenderungen vom Server (anderes Geraet, Start): nur uebernehmen, wenn sie nicht das Echo der eigenen Liste sind
  document.addEventListener("hotkeys-changed", () => {
    const incoming = Array.isArray(window.__hotkeys) ? window.__hotkeys : [];
    const mine = sig(incoming);
    if (sentSigs.includes(mine) || mine === sig(list)) { rebuild(); return; }
    const typing = document.activeElement && document.activeElement.classList && document.activeElement.classList.contains("hk__cmd");
    list = clone(incoming);
    rebuild();
    if (Modal.isOpen("hotkeys") && !typing && !dev) render();
  });

  document.addEventListener("keydown", onKeyDown, true);
  document.addEventListener("keyup", onKeyUp, true);

  const comboOf = (e) => { const k = mainKey(e); return k ? build(modsOf(e), [k]) : ""; };          // Kombination einer Taste ("Ctrl+S"), "" fuer Modifikatoren allein
  window.OCHotkeys = { open: openDialog, reservedLabel, get list() { return list; }, parse, build, comboOf, reserved: RESERVED, startRecorder: startBrowserRecorder, stopRecorder: stopBrowserRecorder };
  list = clone(window.__hotkeys || []);
  rebuild();
})();
