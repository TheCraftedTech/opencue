// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* MIDI-Belegung: Eine Taste, ein Regler, ein Drehgeber oder ein Programmwechsel eines MIDI-Geraets loest einen Befehl der Befehlszeile aus (Hilfe -> MIDI-Belegung).
 *
 * - Die Belegung liegt am Server (app/midi_engine.py, App-Config `midi`, gilt fuer alle Geraete): window.__midi, Aenderungen kommen als `midi-changed`.
 *   Ausgeloest wird NUR am Server (er hoert die MIDI-Anschluesse); dieses Skript bearbeitet die Liste, lernt Signale ein und zeigt den Monitor.
 * - Eine Zeile bekommt ihr Signal ueber den Dialog "Signal einlernen" (Klick auf das Signal-Feld): am Geraet druecken oder bewegen - das erste Signal gilt. An Tablets
 *   (ohne die Geraete am Rechner) traegt man es von Hand ein.
 * - Arten: Taste (beim Druecken), Schalter (abwechselnd zwei Befehle), Halten (Druecken / Loslassen), Regler ({value}), Drehgeber ({delta}).
 * - Der Monitor unten zeigt live, was die Geraete senden (so findet man Noten- und Reglernummern); Zeilen, die gerade ausloesen, leuchten kurz.
 * Klassisches Skript, laeuft nach app.js. */
(function () {
  "use strict";

  const MAX_ROWS = 500;
  const LEARN_SECONDS = 40;
  const WATCH_KEEPALIVE_MS = 5000;
  const MONITOR_LINES = 14;
  const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    Object.keys(vars || {}).forEach((name) => { text = text.split("{" + name + "}").join(String(vars[name])); });
    return text;
  };
  const el = (tag, cls, text) => { const node = document.createElement(tag); if (cls) node.className = cls; if (text != null) node.textContent = text; return node; };
  const send = (type, payload) => { if (typeof client !== "undefined" && client && client.send) client.send(type, payload || {}); };
  const isLocal = () => true;                                                  // MIDI-Monitor und Einlernen gehen von jedem Geraet aus (die Nachrichten kommen vom Hauptrechner an alle Fenster)
  const $ = (id) => document.getElementById(id);
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const noteName = (n) => NOTE_NAMES[((n % 12) + 12) % 12] + (Math.floor(n / 12) - 1);

  const TRANSPORT = ["start", "stop", "continue"];                      // Start / Stop / Weiter der Musiksoftware (kein Kanal, keine Nummer)
  const MODES = ["trigger", "toggle", "hold", "double", "long", "fader", "relative"];
  const MODE_KEYS = { trigger: "MIDI_M_TRIGGER", toggle: "MIDI_M_TOGGLE", hold: "MIDI_M_HOLD", double: "MIDI_M_DOUBLE", long: "MIDI_M_LONG", fader: "MIDI_M_FADER", relative: "MIDI_M_RELATIVE" };
  const CONTINUOUS = ["pitch", "aftertouch", "pressure"];               // keine Tasten: nur als Regler
  const CURVES = [["linear", "MIDI_CURVE_LINEAR"], ["square", "MIDI_CURVE_SQUARE"], ["sqrt", "MIDI_CURVE_SQRT"]];
  const FEEDBACKS = [["", "MIDI_FB_NONE"], ["blackout", "MIDI_FB_BLACKOUT"], ["master", "MIDI_FB_MASTER"], ["selection", "MIDI_FB_SELECTION"], ["cue_active", "MIDI_FB_CUE"], ["timecode_running", "MIDI_FB_TIMECODE"], ["cuelist_fader", "MIDI_FB_FADER"]];
  const FB_BOOL = ["blackout", "selection", "cue_active", "timecode_running"];
  /** Welche Arten zu einem Signal passen (wie app/midi_engine.py normalize_config). */
  function allowedModes(type) {
    if (CONTINUOUS.includes(type)) return ["fader"];
    if (type === "pc" || TRANSPORT.includes(type)) return ["trigger", "toggle", "double"];
    if (type === "note") return ["trigger", "toggle", "hold", "double", "long", "fader"];
    if (type === "cc") return MODES;
    return ["trigger", "toggle", "hold", "double", "long", "fader", "relative"];
  }
  const ENCODINGS = [["twos", "MIDI_ENC_TWOS"], ["signed", "MIDI_ENC_SIGNED"], ["offset", "MIDI_ENC_OFFSET"]];

  let cfg = { enabled: true, output: "", ignore: [], clock: false, mtc: false, msc: false, msc_device: 127, mtc_out: false, mtc_fps: 1, clock_out: false, bindings: [] };                // Arbeitskopie (wird nach jeder Aenderung zum Server geschickt)
  let status = { available: true, error: "", inputs: [], outputs: [], output: "", enabled: true };
  const sentSigs = [];                                                  // Abdruck der zuletzt gesendeten Belegungen (das Echo des Servers wird nicht noch einmal eingespielt)
  let sendTimer = null;
  let watchTimer = null;
  let pendingDelete = null;
  const monitorLines = [];

  const squash = (text) => String(text || "").split(/\s+/).filter(Boolean).join(" ");
  /** Abdruck der Belegung ueber die Felder, die der Server unveraendert zurueckgibt (er bereinigt Leerzeichen und Bereiche): so erkennt man das Echo der eigenen Liste. */
  const sig = (value) => JSON.stringify([value.enabled !== false, value.output || "", (value.ignore || []).join("|"), !!value.clock, !!value.mtc, !!value.msc, value.msc_device === undefined ? 127 : +value.msc_device, !!value.mtc_out,
    value.mtc_fps === undefined ? 1 : +value.mtc_fps, !!value.clock_out, (value.bindings || []).map((b) => [
    b.id, b.enabled !== false, b.type || "", +b.channel || 0, +b.number || 0, b.device || "", b.mode || "trigger", squash(b.command), squash(b.command_off),
    b.run !== false, b.log !== false, +b.min || 0, b.max === undefined ? 100 : +b.max, b.invert === true, b.pickup === true, b.step === undefined ? 1 : +b.step, b.encoding || "twos",
    b.curve || "linear", b.hold_ms === undefined ? 600 : +b.hold_ms, b.feedback || "", b.fb_on === undefined ? 127 : +b.fb_on, b.fb_off === undefined ? 0 : +b.fb_off])]);
  const normalized = (value) => ({ enabled: value && value.enabled !== false, output: (value && value.output) || "", ignore: Array.isArray(value && value.ignore) ? value.ignore : [], clock: !!(value && value.clock), mtc: !!(value && value.mtc), msc: !!(value && value.msc), msc_device: value && value.msc_device !== undefined ? +value.msc_device : 127,
    mtc_out: !!(value && value.mtc_out), mtc_fps: value && value.mtc_fps !== undefined ? +value.mtc_fps : 1, clock_out: !!(value && value.clock_out), bindings: Array.isArray(value && value.bindings) ? value.bindings : [] });

  function randomId() { return Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-3); }

  function persist(immediate) {
    clearTimeout(sendTimer);
    const go = () => {
      sendTimer = null;
      sentSigs.push(sig(cfg));
      if (sentSigs.length > 30) sentSigs.shift();
      send("set_midi", { midi: clone(cfg) });
    };
    if (immediate) go(); else sendTimer = setTimeout(go, 350);
  }
  function flush() { if (sendTimer) persist(true); }

  // ------------------------------------------------------------------ Texte
  function signalText(row) {
    if (!row.type) return t("MIDI_SIGNAL_NONE");
    if (TRANSPORT.includes(row.type)) return t("MIDI_T_" + row.type.toUpperCase());
    let base;
    if (row.type === "note") base = t("MIDI_T_NOTE", { name: noteName(row.number) }) + " (" + row.number + ")";
    else if (row.type === "cc") base = t("MIDI_T_CC", { n: row.number });
    else if (row.type === "pc") base = t("MIDI_T_PC", { n: row.number });
    else if (row.type === "aftertouch") base = t("MIDI_T_AFTERTOUCH", { name: noteName(row.number) });
    else if (row.type === "pressure") base = t("MIDI_T_PRESSURE");
    else base = t("MIDI_T_PITCH");
    return base + (row.channel ? " · " + t("MIDI_CH", { n: row.channel }) : "");
  }
  const deviceLabel = (row) => row.device_name || row.device;

  // ------------------------------------------------------------------ Liste
  function toggleSwitch(row, field, tipKey, id) {
    const { label, input } = makeToggleSwitch("mi-" + field + "-" + row.id + (id || ""), row[field] === undefined ? true : row[field] !== false);
    label.title = t(tipKey);
    input.setAttribute("aria-label", t(tipKey));
    input.addEventListener("change", () => { row[field] = input.checked; persist(true); });
    return label;
  }

  function option(labelKey, control, cls) {
    const wrap = el("label", "mi__opt" + (cls ? " " + cls : ""));
    wrap.append(el("span", "mi__opt-label", t(labelKey)), control);
    return wrap;
  }

  function textInput(row, field, placeholderKey) {
    const input = el("input", "modal__input mi__optinput");
    input.type = "text";
    input.value = row[field] || "";
    input.maxLength = 1000;
    input.placeholder = t(placeholderKey);
    input.addEventListener("input", () => { row[field] = input.value; persist(false); });
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); input.blur(); } });
    return input;
  }

  function numberInput(row, field, fallback, step) {
    const input = el("input", "modal__input mi__num");
    input.type = "number";
    input.step = step || "any";
    input.value = row[field] === undefined ? fallback : row[field];
    input.addEventListener("input", () => { const v = parseFloat(input.value); if (!isNaN(v)) { row[field] = v; persist(false); } });
    return input;
  }

  const ROW_DEFAULTS = { enabled: true, type: "", channel: 0, number: 0, device: "", device_name: "", mode: "trigger", command: "", command_off: "", run: true, log: true, min: 0, max: 100, invert: false, pickup: false, curve: "linear", hold_ms: 600, step: 1, encoding: "twos", feedback: "", fb_on: 127, fb_off: 0 };
  const newRow = (spec) => Object.assign({ id: randomId() }, ROW_DEFAULTS, spec || {});

  function selectOf(options, value, onChange) {
    const s = el("select", "modal__input mi__select");
    options.forEach(([v, key]) => { const o = el("option", "", t(key)); o.value = v; if (value === v) o.selected = true; s.appendChild(o); });
    s.addEventListener("change", () => onChange(s.value));
    return s;
  }

  function optionsFor(row) {
    const box = el("div", "mi__opts");
    if (row.mode === "long") box.appendChild(option("MIDI_HOLD_MS", numberInput(row, "hold_ms", 600, "50")));
    if (row.mode === "toggle") box.appendChild(option("MIDI_OFF_CMD", textInput(row, "command_off", "MIDI_OFF_CMD_PH"), "mi__opt--wide"));
    if (row.mode === "hold") box.appendChild(option("MIDI_RELEASE_CMD", textInput(row, "command_off", "MIDI_RELEASE_CMD_PH"), "mi__opt--wide"));
    if (row.mode === "fader") {
      box.appendChild(option("MIDI_MIN", numberInput(row, "min", 0)));
      box.appendChild(option("MIDI_MAX", numberInput(row, "max", 100)));
      box.appendChild(option("MIDI_CURVE", selectOf(CURVES, row.curve || "linear", (v) => { row.curve = v; persist(true); })));
      const inv = makeToggleSwitch("mi-invert-" + row.id, row.invert === true);
      inv.input.addEventListener("change", () => { row.invert = inv.input.checked; persist(true); });
      box.appendChild(option("MIDI_INVERT", inv.label, "mi__opt--switch"));
      const pick = makeToggleSwitch("mi-pickup-" + row.id, row.pickup === true);
      pick.label.title = t("MIDI_PICKUP_TIP");
      pick.input.addEventListener("change", () => { row.pickup = pick.input.checked; persist(true); });
      box.appendChild(option("MIDI_PICKUP", pick.label, "mi__opt--switch"));
    }
    if (row.mode === "relative") {
      box.appendChild(option("MIDI_STEP", numberInput(row, "step", 1)));
      const enc = el("select", "modal__input mi__select");
      ENCODINGS.forEach(([value, key]) => { const o = el("option", "", t(key)); o.value = value; if ((row.encoding || "twos") === value) o.selected = true; enc.appendChild(o); });
      enc.addEventListener("change", () => { row.encoding = enc.value; persist(true); });
      box.appendChild(option("MIDI_ENC", enc));
    }
    if (!row.type || ["note", "cc", "pitch"].includes(row.type)) {                                   // Rueckmeldung an das Geraet (LED, Motorfader)
      box.appendChild(option("MIDI_FB", selectOf(FEEDBACKS, row.feedback || "", (v) => { row.feedback = v; persist(true); render(); })));
      if (FB_BOOL.includes(row.feedback)) {
        box.appendChild(option("MIDI_FB_ON", numberInput(row, "fb_on", 127, "1")));
        box.appendChild(option("MIDI_FB_OFF", numberInput(row, "fb_off", 0, "1")));
      }
    }
    box.appendChild(el("span", "mi__grow"));
    box.appendChild(option("MIDI_RUN", toggleSwitch(row, "run", "MIDI_RUN_TIP"), "mi__opt--switch"));
    box.appendChild(option("MIDI_LOG", toggleSwitch(row, "log", "MIDI_LOG_TIP"), "mi__opt--switch"));
    return box;
  }

  function buildRow(row) {
    const node = el("div", "mi__row");
    node.dataset.id = row.id;

    const on = toggleSwitch(row, "enabled", "MIDI_ON_TIP");
    on.classList.add("mi__on");

    const sigButton = el("button", "modal__button mi__sig" + (row.type ? "" : " mi__sig--empty"));
    sigButton.type = "button";
    sigButton.title = t("MIDI_SIGNAL_TIP");
    sigButton.appendChild(el("span", "mi__sigtext", signalText(row)));
    if (row.device) {
      const chip = el("span", "mi__sigdev");
      chip.append(Icons.svg("midi"), el("span", "", deviceLabel(row)));
      sigButton.appendChild(chip);
    }
    sigButton.addEventListener("click", () => openLearn(row.id));

    const mode = el("select", "modal__input mi__mode");
    mode.title = t(MODE_KEYS[row.mode] + "_TIP");
    const allowed = allowedModes(row.type);
    MODES.forEach((m) => {
      if (!allowed.includes(m)) return;
      const o = el("option", "", t(MODE_KEYS[m])); o.value = m; if (row.mode === m) o.selected = true; mode.appendChild(o);
    });
    mode.addEventListener("change", () => { row.mode = mode.value; persist(true); render(); });

    const command = el("input", "modal__input mi__cmd");
    command.type = "text";
    command.value = row.command || "";
    command.placeholder = t("MIDI_CMD_PH_" + String(row.mode || "trigger").toUpperCase());
    command.maxLength = 1000;
    command.addEventListener("input", () => { row.command = command.value; persist(false); });
    command.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); command.blur(); } });

    const del = el("button", "modal__button hk__icon mi__del");
    del.type = "button";
    del.title = t("MIDI_DELETE_TIP");
    del.setAttribute("aria-label", t("MIDI_DELETE_TIP"));
    del.appendChild(Icons.svg("trash"));
    del.addEventListener("click", () => askDelete(row));

    const dup = el("button", "modal__button hk__icon mi__dup");
    dup.type = "button";
    dup.title = t("MIDI_DUPLICATE_TIP");
    dup.setAttribute("aria-label", t("MIDI_DUPLICATE_TIP"));
    dup.appendChild(Icons.svg("copy"));
    dup.addEventListener("click", () => duplicateRow(row));
    const move = (dir, icon, key) => {
      const b = el("button", "modal__button hk__icon mi__move");
      b.type = "button";
      b.title = t(key);
      b.setAttribute("aria-label", t(key));
      b.disabled = !!filterText || (dir < 0 ? cfg.bindings.indexOf(row) === 0 : cfg.bindings.indexOf(row) === cfg.bindings.length - 1);
      b.appendChild(Icons.svg(icon));
      b.addEventListener("click", () => moveRow(row, dir));
      return b;
    };
    const acts = el("div", "mi__acts");
    acts.append(move(-1, "arrow-up", "MIDI_MOVE_UP"), move(1, "arrow-down", "MIDI_MOVE_DOWN"), dup, del);

    node.append(on, sigButton, mode, command, acts, optionsFor(row));
    return node;
  }

  let filterText = "";                                                 // Suchfeld ueber der Liste: Signal, Befehl, Geraet
  const matches = (row) => !filterText || [signalText(row), row.command, row.command_off, row.device_name || row.device || ""].join(" ").toLowerCase().includes(filterText);

  function moveRow(row, dir) {
    const i = cfg.bindings.indexOf(row);
    const j = i + dir;
    if (i < 0 || j < 0 || j >= cfg.bindings.length) return;
    cfg.bindings.splice(i, 1);
    cfg.bindings.splice(j, 0, row);
    persist(true);
    render();
    const node = document.querySelector('#midi-list [data-id="' + row.id + '"]');
    if (node) node.scrollIntoView({ block: "nearest" });
  }

  function render() {
    const box = $("midi-list");
    if (!box) return;
    const keepScroll = box.scrollTop;
    box.textContent = "";
    cfg.bindings.filter(matches).forEach((row) => box.appendChild(buildRow(row)));
    box.scrollTop = keepScroll;
    const empty = $("midi-empty");
    if (empty) { empty.hidden = cfg.bindings.length > 0 && box.children.length > 0; empty.textContent = cfg.bindings.length ? t("MIDI_NO_MATCH") : t("MIDI_EMPTY"); }
    const add = $("midi-add");
    if (add) add.disabled = cfg.bindings.length >= MAX_ROWS;
  }

  function addRow() {
    if (cfg.bindings.length >= MAX_ROWS) return;
    const row = newRow();
    cfg.bindings.push(row);
    persist(true);
    render();
    const node = document.querySelector('#midi-list [data-id="' + row.id + '"]');
    if (node) node.scrollIntoView({ block: "nearest" });
  }

  /** Eine Zeile kopieren (gleiche Art und gleicher Befehl, das Signal bleibt zum Festlegen leer): praktisch fuer eine Reihe aehnlicher Belegungen (Fader 1 ... 8). */
  function duplicateRow(row) {
    if (cfg.bindings.length >= MAX_ROWS) return;
    const copy = Object.assign(clone(row), { id: randomId(), type: "", number: 0, channel: 0, device: "", device_name: "" });
    cfg.bindings.splice(cfg.bindings.indexOf(row) + 1, 0, copy);
    persist(true);
    render();
    const node = document.querySelector('#midi-list [data-id="' + copy.id + '"]');
    if (node) { node.scrollIntoView({ block: "nearest" }); node.classList.add("mi__row--hit"); setTimeout(() => node.classList.remove("mi__row--hit"), 600); }
  }

  /** Belegung als Datei sichern (Server: /api/midi/export) bzw. eine solche Datei einlesen - die Zeilen kommen NEU DAZU (nichts wird ersetzt). */
  function exportFile() {
    flush();
    window.OCTransfer.save("opencue-midi-mapping.json", { opencue_midi: 1, bindings: clone(cfg.bindings) });
  }
  async function importFile() {
    const data = await window.OCTransfer.pickJson();
    if (data === null) return;
    const rows = Array.isArray(data) ? data : (data && data.bindings);
    if (!Array.isArray(rows)) { if (typeof _showToast === "function") _showToast(t("MIDI_IMPORT_FAILED"), "error", 4000, true); return; }
    const room = MAX_ROWS - cfg.bindings.length;
    const fresh = rows.filter((r) => r && typeof r === "object").slice(0, Math.max(0, room)).map((r) => Object.assign({}, r, { id: randomId() }));
    cfg.bindings.push(...fresh);
    persist(true);
    render();
    if (typeof _showToast === "function") _showToast(t("MIDI_IMPORTED", { n: fresh.length }), "info", 3500, true);
  }

  /** Aus dem Eigenschaften-Dialog eines Buttons / Schalters / Faders: legt eine Belegung mit dessen Befehl an und lernt das Signal gleich ein. */
  function assign(spec) {
    cfg = clone(normalized(window.__midi));
    if (cfg.bindings.length >= MAX_ROWS) return;
    const row = newRow(spec);
    cfg.bindings.push(row);
    persist(true);
    openDialog(true);
    openLearn(row.id);
  }
  window.__midiAssignField = function (kind) {
    const box = el("div", "modal__field mi__assign");
    const b = el("button", "modal__button");
    b.type = "button";
    b.appendChild(Icons.svg("midi"));
    b.appendChild(el("span", "", t("MIDI_ASSIGN")));
    b.addEventListener("click", () => {
      const val = (id) => { const n = document.getElementById(id); return n ? String(n.value || "").trim() : ""; };
      if (kind === "toggle") assign({ mode: "toggle", command: val("panel-toggle-command-on"), command_off: val("panel-toggle-command-off") });
      else if (kind === "fader") {
        const lo = parseFloat(val("panel-fader-min")), hi = parseFloat(val("panel-fader-max"));
        assign({ mode: "fader", command: val("panel-fader-command"), min: isNaN(lo) ? 0 : lo, max: isNaN(hi) ? 100 : hi });
      } else assign({ mode: "trigger", command: val("panel-button-command") });
    });
    box.append(b, el("p", "mi__assign-hint", t("MIDI_ASSIGN_HINT")));
    return box;
  };

  function askDelete(row) {
    pendingDelete = row.id;
    const body = $("midi-delete-body");
    if (body) body.textContent = row.type ? t("MIDI_DELETE_BODY", { signal: signalText(row) }) : t("MIDI_DELETE_BODY_NONE");
    Modal.open("midi-delete-confirm");
  }

  // ------------------------------------------------------------------ Leiste: Ein/Aus, Geraete, Ausgang
  function renderBar() {
    const slot = $("midi-enabled-slot");
    if (slot && !slot.firstChild) {
      const { label, input } = makeToggleSwitch("midi-enabled", cfg.enabled !== false);
      label.title = t("MIDI_ENABLED_TIP");
      input.setAttribute("aria-label", t("MIDI_ENABLED_TIP"));
      input.addEventListener("change", () => { cfg.enabled = input.checked; persist(true); });
      slot.appendChild(label);
    }
    const sw = $("midi-enabled");
    if (sw) sw.checked = cfg.enabled !== false;

    const devices = $("midi-devices");
    if (devices) {
      devices.textContent = "";
      devices.classList.remove("mi__devices--bad");
      if (!status.available) {
        devices.classList.add("mi__devices--bad");
        devices.appendChild(el("span", "", t("MIDI_LIB_MISSING", { e: status.error || "python-rtmidi" })));
      } else if (!isLocal()) {
        devices.appendChild(el("span", "", ""));
      } else if (!status.inputs.length) {
        devices.appendChild(el("span", "mi__devices-none", t("MIDI_DEVICES_NONE")));
      } else {
        status.inputs.forEach((port) => {
          const chip = el("span", "mi__chip" + (port.error ? " mi__chip--bad" : (port.open ? " mi__chip--open" : "")));
          chip.title = port.error || "";
          chip.append(Icons.svg("midi"), el("span", "", port.name + (port.error ? " (" + t("MIDI_DEVICE_BUSY") + ")" : "")));
          devices.appendChild(chip);
        });
      }
    }

    const out = $("midi-output");
    if (out) {
      out.textContent = "";
      const outs = status.outputs || [];
      const auto = el("option", "", outs.length ? t("MIDI_OUTPUT_AUTO") + (status.output ? " (" + status.output + ")" : "") : t("MIDI_OUTPUT_NONE"));
      auto.value = "";
      out.appendChild(auto);
      outs.forEach((port) => { const o = el("option", "", port.name); o.value = port.id; out.appendChild(o); });
      if (cfg.output && !outs.some((p) => p.id === cfg.output)) { const o = el("option", "", cfg.output); o.value = cfg.output; out.appendChild(o); }
      out.value = cfg.output || "";
      out.disabled = !isLocal() && !outs.length;
      out.title = t("MIDI_OUTPUT_TIP");
    }
    const monitor = document.querySelector(".mi__monitor");
    if (monitor) monitor.hidden = !isLocal();
  }

  // ------------------------------------------------------------------ Monitor
  function renderMonitor() {
    const box = $("midi-monitor");
    if (!box) return;
    box.textContent = "";
    if (!monitorLines.length) {
      box.appendChild(el("div", "mi__log-empty", status.inputs.length || !status.available ? t("MIDI_MONITOR_EMPTY") : t("MIDI_MONITOR_NO_DEVICE")));
      return;
    }
    monitorLines.forEach((line) => {
      const row = el("div", "mi__log-line");
      row.append(el("span", "mi__log-time", line.time), el("span", "mi__log-dev", line.device), el("span", "mi__log-ch", t("MIDI_CH", { n: line.channel })), el("span", "mi__log-text", line.text));
      box.appendChild(row);
    });
  }

  function onMonitor(payload) {
    (payload.events || []).forEach((event) => {
      const d = new Date(event.t * 1000);
      const pad = (n) => String(n).padStart(2, "0");
      monitorLines.unshift({ time: pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds()), device: event.device, channel: event.channel, text: event.text });
    });
    monitorLines.length = Math.min(monitorLines.length, MONITOR_LINES);
    renderMonitor();
    (payload.hits || []).forEach((id) => {
      const node = document.querySelector('#midi-list [data-id="' + id + '"]');
      if (!node) return;
      node.classList.add("mi__row--hit");
      clearTimeout(node.__hit);
      node.__hit = setTimeout(() => node.classList.remove("mi__row--hit"), 450);
    });
  }

  function startWatch() {
    stopWatch();
    if (!isLocal()) return;
    send("midi_watch", { on: true });
    watchTimer = setInterval(() => send("midi_watch", { on: true }), WATCH_KEEPALIVE_MS);
  }
  function stopWatch() {
    if (watchTimer) { clearInterval(watchTimer); watchTimer = null; if (isLocal()) send("midi_watch", { on: false }); }
  }

  function openDialog(keepConfig) {
    if (Modal.isOpen("keyboard-shortcuts")) Modal.close("keyboard-shortcuts");
    if (keepConfig !== true) cfg = clone(normalized(window.__midi));
    monitorLines.length = 0;
    renderBar();
    render();
    renderMonitor();
    Modal._hooks.midi = () => { flush(); stopWatch(); };
    Modal.open("midi");
    if (isLocal()) { send("midi_status"); startWatch(); }
  }

  /** Oeffnet die Einstellungen bei einer Kategorie (wie ein Menuepunkt mit data-settings-category) und schliesst diesen Dialog vorher. */
  function openSettings(category) {
    Modal.close("midi");
    const trigger = document.createElement("button");
    trigger.hidden = true;
    trigger.dataset.action = "open-settings-modal";
    trigger.dataset.settingsCategory = category;
    document.body.appendChild(trigger);
    trigger.click();
    trigger.remove();
  }

  // ------------------------------------------------------------------ Dialog "Signal einlernen"
  let L = null;                                                         // { id, type, channel, number, device, name, waiting, deadline, timer }
  let queue = [];                                                       // Zeilen, die nacheinander eingelernt werden (Vorlagen): [0] ist die aktuelle
  let queueTotal = 0;
  let advancing = false;                                                // der Lern-Dialog wird absichtlich fuer die naechste Zeile geschlossen (nicht abgebrochen)

  function learnMessage(text) {
    const box = $("mlearn-msg");
    box.textContent = text || "";
    box.hidden = !text;
  }

  function duplicateWarning() {
    if (!L || !L.type) return "";
    const clash = cfg.bindings.find((r) => r.id !== L.id && r.type === L.type && (TRANSPORT.includes(L.type) || r.channel === 0 || L.channel === 0 || r.channel === L.channel) &&
      (L.type === "pitch" || TRANSPORT.includes(L.type) || r.number === L.number) && (!r.device || !L.device || r.device === L.device));
    return clash ? t("MIDI_DUP") : "";
  }

  function paintLearn() {
    if (!L || !$("mlearn-capture")) return;
    const capture = $("mlearn-capture");
    capture.classList.toggle("hk__capture--rec", L.waiting);
    capture.classList.toggle("hk__capture--empty", !L.waiting && !L.type);
    if (L.waiting) capture.textContent = t("MIDI_LEARN_WAIT", { n: Math.max(0, Math.ceil((L.deadline - Date.now()) / 1000)) });
    else capture.textContent = L.type ? signalText(L) : t("MIDI_LEARN_NONE");
    const from = $("mlearn-from");
    const name = L.device ? (L.name || L.device) : "";
    from.textContent = name ? t("MIDI_LEARN_FROM", { name }) : "";
    from.hidden = !name;
    const one = $("mlearn-scope-one");
    one.disabled = !L.device;
    $("mlearn-scope-one-sub").textContent = L.device ? name : t("MIDI_SCOPE_ONE_SUB_NONE");
    if (!L.device && one.checked) $("mlearn-scope-all").checked = true;
    $("mlearn-apply").disabled = !L.type;
    $("mlearn-again").hidden = !isLocal();
    const progress = $("mlearn-progress");
    progress.hidden = !queue.length;
    progress.textContent = queue.length ? t("MIDI_LEARN_PROGRESS", { n: queueTotal - queue.length + 1, total: queueTotal }) : "";
    $("mlearn-skip").hidden = !queue.length;
    learnMessage(duplicateWarning());
  }

  function fillManual() {
    $("mlearn-type").value = L.type || "";
    $("mlearn-channel").value = String(L.channel || 0);
    const number = $("mlearn-number");
    number.value = ["pitch", "pressure"].includes(L.type) ? "" : L.number;
    number.disabled = ["pitch", "pressure"].includes(L.type) || !L.type || TRANSPORT.includes(L.type);
    $("mlearn-channel").disabled = TRANSPORT.includes(L.type);
    $("mlearn-notename").textContent = ["note", "aftertouch"].includes(L.type) ? noteName(L.number) : "";
  }

  function stopLearning(notify) {
    if (!L) return;
    clearInterval(L.timer);
    if (L.waiting && notify !== false && isLocal()) send("midi_learn", { on: false });
    L.waiting = false;
  }

  function startLearning() {
    if (!L || !isLocal()) return;
    clearInterval(L.timer);
    L.waiting = true;
    L.deadline = Date.now() + LEARN_SECONDS * 1000;
    send("midi_learn", { on: true });
    L.timer = setInterval(() => { if (Date.now() >= L.deadline) { stopLearning(true); } paintLearn(); }, 250);
    paintLearn();
  }

  function openLearn(rowId) {
    const row = cfg.bindings.find((r) => r.id === rowId);
    if (!row) return;
    const select = $("mlearn-channel");
    if (!select.options.length) {
      const all = el("option", "", t("MIDI_F_CHANNEL_ALL")); all.value = "0"; select.appendChild(all);
      for (let n = 1; n <= 16; n += 1) { const o = el("option", "", String(n)); o.value = String(n); select.appendChild(o); }
    }
    L = { id: rowId, type: row.type || "", channel: row.channel || 0, number: row.number || 0, device: row.device || "", name: row.device_name || "", waiting: false, deadline: 0, timer: null };
    $("mlearn-scope-" + (row.device ? "one" : "all")).checked = true;
    Modal._hooks["midi-learn"] = () => { stopLearning(true); L = null; if (!advancing) queue = []; };
    fillManual();
    Modal.open("midi-learn");
    if (isLocal()) startLearning(); else paintLearn();
  }

  function learned(payload) {
    if (!L || !L.waiting) return;
    stopLearning(false);
    L.type = payload.type; L.channel = payload.channel || 0; L.number = payload.number || 0;
    L.device = payload.device || ""; L.name = payload.name || payload.device || "";
    fillManual();
    paintLearn();
  }

  function manualChanged() {
    if (!L) return;
    stopLearning(true);
    L.type = $("mlearn-type").value;
    L.channel = parseInt($("mlearn-channel").value, 10) || 0;
    const n = parseInt($("mlearn-number").value, 10);
    L.number = isNaN(n) ? 0 : Math.max(0, Math.min(127, n));
    $("mlearn-number").disabled = ["pitch", "pressure"].includes(L.type) || !L.type || TRANSPORT.includes(L.type);
    $("mlearn-channel").disabled = TRANSPORT.includes(L.type);
    $("mlearn-notename").textContent = ["note", "aftertouch"].includes(L.type) ? noteName(L.number) : "";
    paintLearn();
  }

  function applyLearn() {
    if (!L || !L.type) return;
    const row = cfg.bindings.find((r) => r.id === L.id);
    if (!row) { Modal.close("midi-learn"); return; }
    const scoped = $("mlearn-scope-one").checked && L.device;
    const transport = TRANSPORT.includes(L.type);
    row.type = L.type; row.channel = transport ? 0 : L.channel; row.number = (["pitch", "pressure"].includes(L.type) || transport) ? 0 : L.number;
    row.device = scoped ? L.device : ""; row.device_name = scoped ? (L.name || "") : "";
    const allowed = allowedModes(row.type);
    if (!allowed.includes(row.mode)) row.mode = row.type === "note" && row.mode === "relative" ? "fader" : allowed[0];
    if (row.feedback && !["note", "cc", "pitch"].includes(row.type)) row.feedback = "";
    persist(true);
    advancing = true;
    Modal.close("midi-learn");
    advancing = false;
    render();
    proceedQueue();
  }

  /** Vorlagen: die Zeilen nacheinander einlernen ("Regler 1 bewegen, Regler 2 ..."). */
  function proceedQueue() {
    if (!queue.length) return;
    queue.shift();
    if (queue.length) openLearn(queue[0]);
  }
  function skipQueued() {
    advancing = true;
    Modal.close("midi-learn");
    advancing = false;
    proceedQueue();
  }

  // ------------------------------------------------------------------ Vorlagen
  const TEMPLATES = [
    { id: "faders", count: 8, start: 1, startKey: "MIDI_TPL_START_FIXTURE", build: (i, s) => ({ mode: "fader", command: "Fixture " + (s + i) + " At {value}", pickup: true }) },
    { id: "pads", count: 8, start: 1, startKey: "MIDI_TPL_START_CUE", build: (i, s) => ({ mode: "trigger", command: "Go Cue " + (s + i) }) },
    { id: "transport", fixed: [{ command: "Go" }, { command: "Back" }, { command: "Pause" }, { command: "Blackout", feedback: "blackout" }] },
    { id: "master", fixed: [{ mode: "fader", command: "Master {value}", pickup: true }, { mode: "toggle", command: "Blackout", feedback: "blackout" }] },
  ];
  let templateId = "faders";

  function paintTemplate() {
    const tpl = TEMPLATES.find((x) => x.id === templateId);
    const opts = $("midi-tpl-opts");
    opts.hidden = !!tpl.fixed;
    if (!tpl.fixed) {
      $("midi-tpl-start-label").textContent = t(tpl.startKey);
      const count = $("midi-tpl-count");
      if (!count.dataset.tpl || count.dataset.tpl !== tpl.id) { count.value = tpl.count; $("midi-tpl-start").value = tpl.start; count.dataset.tpl = tpl.id; }
    }
  }
  function openTemplate() {
    const list = $("midi-tpl-list");
    list.textContent = "";
    TEMPLATES.forEach((tpl) => {
      const card = el("label", "hk__card");
      const radio = el("input");
      radio.type = "radio"; radio.name = "midi-tpl"; radio.value = tpl.id; radio.checked = tpl.id === templateId;
      radio.addEventListener("change", () => { templateId = tpl.id; paintTemplate(); });
      const text = el("span", "hk__card-text");
      text.append(el("span", "hk__card-title", t("MIDI_TPL_" + tpl.id.toUpperCase())), el("span", "hk__card-sub", t("MIDI_TPL_" + tpl.id.toUpperCase() + "_SUB")));
      card.append(radio, text);
      list.appendChild(card);
    });
    $("midi-tpl-count").dataset.tpl = "";
    paintTemplate();
    Modal.open("midi-template");
  }
  function createTemplate() {
    const tpl = TEMPLATES.find((x) => x.id === templateId);
    const rows = tpl.fixed ? tpl.fixed.map((spec) => newRow(spec)) : (() => {
      const count = Math.max(1, Math.min(32, parseInt($("midi-tpl-count").value, 10) || tpl.count));
      const start = parseInt($("midi-tpl-start").value, 10);
      return Array.from({ length: count }, (_x, i) => newRow(tpl.build(i, isNaN(start) ? tpl.start : start)));
    })();
    if (cfg.bindings.length + rows.length > MAX_ROWS) return;
    cfg.bindings.push(...rows);
    persist(true);
    Modal.close("midi-template");
    render();
    if (isLocal()) {                                                              // am Konsolenrechner: gleich nacheinander einlernen
      queue = rows.map((r) => r.id);
      queueTotal = queue.length;
      openLearn(queue[0]);
    }
  }

  // ------------------------------------------------------------------ Symbol in der Werkzeugleiste (nur an der Konsole): zeigt den Zustand, Klick oeffnet die Belegung
  let paintTries = 0;
  let statusAsked = false;
  function paintToolbar() {
    const button = $("toolbar-midi");
    if (!button) return;
    const local = !!(typeof client !== "undefined" && client.state && client.state.is_local);       // das Symbol der Werkzeugleiste gibt es nur am Hauptrechner (die Kopfleiste der Fernzugriffs-Geraete bleibt schlank); der Dialog selbst geht von ueberall
    button.hidden = !local;
    if (!local) { if (paintTries < 20) { paintTries += 1; setTimeout(paintToolbar, 500); } return; }
    if (!statusAsked) { statusAsked = true; send("midi_status"); }
    const config = normalized(window.__midi);
    const usable = (status.inputs || []).filter((p) => !p.ignored);
    const busy = usable.filter((p) => p.error).length;
    const ready = usable.filter((p) => !p.error).length;
    const off = config.enabled === false;
    button.classList.toggle("menubar__voice--off", off);
    button.classList.toggle("menubar__voice--live", !off && status.available !== false && ready > 0);
    button.classList.toggle("menubar__voice--error", !off && (status.available === false || (busy > 0 && !ready)));
    const tip = off ? t("MIDI_TIP_OFF") : status.available === false ? t("MIDI_LIB_MISSING", { e: status.error || "python-rtmidi" })
      : busy && !ready ? t("MIDI_TIP_BUSY") : ready ? t("MIDI_TIP_ON", { names: usable.filter((p) => !p.error).map((p) => p.name).join(", ") }) : t("MIDI_TIP_NONE");
    button.title = tip;
    button.setAttribute("aria-label", tip);
  }

  // ------------------------------------------------------------------ Ereignisse
  document.addEventListener("oc-midi-event", (e) => {
    const message = e.detail || {};
    const payload = message.payload || {};
    if (message.type === "midi_status") {
      status = Object.assign(status, payload);
      paintToolbar();
      renderBar();
      if (Modal.isOpen("midi")) renderMonitor();
      if (Modal.isOpen("midi-learn")) paintLearn();
    } else if (message.type === "midi_monitor") {
      onMonitor(payload);
    } else if (message.type === "midi_learned") {
      if (typeof window.__cueMidiLearn === "function") { const callback = window.__cueMidiLearn; window.__cueMidiLearn = null; callback(payload); return; }       // Einlernen aus dem Cue-Dialog (Ausloeser "MIDI")
      learned(payload);
    } else if (message.type === "midi_fire") {                                             // Eintrag "nur schreiben": der Befehl kommt in die Befehlszeile
      if (typeof window.__widgetAction === "function") window.__widgetAction({ action_mode: "write", write_append: false }, payload.command, false);
    } else if (message.type === "midi_blocked") {
      if (typeof _showToast === "function") _showToast(t("MIDI_BLOCKED", { command: payload.command || "" }), "error", 5000, true);
    }
  });

  document.addEventListener("change", (e) => {
    const target = e.target;
    if (!target || !target.id) return;
    if (target.id === "midi-output") { cfg.output = target.value; persist(true); }
    else if (target.id === "mlearn-type" || target.id === "mlearn-channel" || target.id === "mlearn-number") manualChanged();
    else if (target.name === "mlearn-scope") paintLearn();
  });
  document.addEventListener("input", (e) => {
    if (!e.target) return;
    if (e.target.id === "mlearn-number") manualChanged();
    else if (e.target.id === "midi-search") { filterText = e.target.value.trim().toLowerCase(); render(); }
  });

  document.addEventListener("click", (e) => {
    const target = e.target.closest ? e.target : null;
    if (!target) return;
    if (target.closest("#toolbar-midi")) { openDialog(); return; }
    if (target.closest('[data-action="open-midi-modal"]')) { if (typeof _closeAllMenus === "function") _closeAllMenus(); openDialog(); return; }
    if (target.closest("#midi-add")) { addRow(); return; }
    if (target.closest("#midi-template")) { openTemplate(); return; }
    if (target.closest("#midi-tpl-create")) { createTemplate(); return; }
    if (target.closest("#mlearn-skip")) { skipQueued(); return; }
    if (target.closest("#cue-edit-midi")) {                                          // Cue-Dialog: eine Belegung, die genau diese Cue startet
      const name = window.__cueEditList || "";
      const number = ($("cue-edit-number") || {}).value || "";
      assign({ mode: "trigger", command: (name ? 'Cuelist "' + name.replace(/"/g, "") + '" ' : "") + "Go Cue " + number });
      return;
    }
    if (target.closest("#midi-open-settings")) { openSettings("midi"); return; }
    if (target.closest("#midi-export")) { exportFile(); return; }
    if (target.closest("#midi-import")) { importFile(); return; }
    if (target.closest("#midi-monitor-clear")) { monitorLines.length = 0; renderMonitor(); return; }
    if (target.closest("#mlearn-again")) { startLearning(); return; }
    if (target.closest("#mlearn-apply")) { applyLearn(); return; }
    if (target.closest("#midi-delete-confirm-button")) {
      const id = pendingDelete;
      pendingDelete = null;
      Modal.close("midi-delete-confirm");
      cfg.bindings = cfg.bindings.filter((r) => r.id !== id);
      persist(true);
      render();
    }
  });

  // Aenderungen vom Server (anderes Geraet, Start): nur uebernehmen, wenn sie nicht das Echo der eigenen Belegung sind
  document.addEventListener("midi-changed", () => {
    const incoming = normalized(window.__midi);
    if (sentSigs.includes(sig(incoming)) || sig(incoming) === sig(cfg)) return;
    const active = document.activeElement;
    const typing = active && active.classList && (active.classList.contains("mi__cmd") || active.classList.contains("mi__optinput") || active.classList.contains("mi__num"));
    if (typing) return;                                                            // gerade getippt: die eigene Liste bleibt (sonst haengen die Felder an alten Zeilen)
    cfg = clone(incoming);
    paintToolbar();
    if (Modal.isOpen("midi") && !L) { renderBar(); render(); }
  });

  document.addEventListener("i18n-applied", () => { paintToolbar(); if (Modal.isOpen("midi")) { renderBar(); render(); renderMonitor(); } });
  document.addEventListener("midi-changed", () => { paintToolbar(); });

  window.OCMidi = { open: () => openDialog(), assign, get config() { return cfg; }, noteName, signalText };
  cfg = clone(normalized(window.__midi));
  setTimeout(paintToolbar, 800);
})();
