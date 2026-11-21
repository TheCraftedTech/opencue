// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Einstellungen -> Gruppe "Bedienung": Kategorie "Tastatur" (Kuerzel ansehen, eigene Tastenbelegung) und Kategorie "MIDI" (MIDI verwenden, Geraete waehlen, Ausgang, Belegung oeffnen).
 *
 * - "Tastatur" ist nur eine Anlaufstelle: sie oeffnet die vorhandenen Dialoge (Tastaturkuerzel, Eigene Tastaturbelegung, MIDI-Belegung) - damit man sie nicht im Hilfe-Menue suchen muss.
 * - "MIDI" (nur an der Konsole selbst, dort haengen die Geraete) arbeitet wie die anderen Einstellungen mit einem ENTWURF: erst "Speichern" schickt ihn an den Server (Ereignis "settings-saved"),
 *   "Abbrechen" / Schliessen verwirft ihn. Der Entwurf umfasst: MIDI an/aus, welche Geraete benutzt werden (ignore-Liste), den Ausgang. Die Belegung selbst bleibt unberuehrt (Dialog "MIDI-Belegung").
 *   Geaenderte Zeilen markiert und zaehlt settings_tracker.js (Anbieter "midi": changes(), reset()). Klassisches Skript, laeuft nach midi.js. */
(function () {
  "use strict";
  const t = (key, vars) => {
    let text = i18n(key);
    Object.keys(vars || {}).forEach((name) => { text = text.split("{" + name + "}").join(String(vars[name])); });
    return text;
  };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const send = (type, payload) => { if (typeof client !== "undefined" && client && client.send) client.send(type, payload || {}); };
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const touch = () => { if (window.OCSettings) window.OCSettings.touch(); };
  const visible = (id) => { const r = document.getElementById(id); return !!(r && r.offsetParent); };

  const section = (title, intro) => { const box = el("div", "settings-section"); box.appendChild(el("div", "settings-section__title", title)); if (intro) box.appendChild(el("p", "ai-row__hint", intro)); return box; };
  function row(label, control, hint) {
    const wrap = el("div", "ai-row");
    const left = el("label", "ai-row__label");
    left.appendChild(el("span", "ai-row__name", label));
    const right = el("div", "ai-row__control");
    right.appendChild(control);
    if (hint) right.appendChild(el("p", "ai-row__hint", hint));
    wrap.append(left, right);
    return wrap;
  }
  function toggle(id, on, onChange) {
    const label = el("label", "toggle-switch");
    const box = el("input");
    box.type = "checkbox"; box.id = id; box.checked = !!on;
    box.addEventListener("change", () => onChange(box.checked));
    label.append(box, el("span", "toggle-switch__track"));
    return label;
  }
  function button(text, id, onClick, icon) {
    const b = el("button", "modal__button");
    b.type = "button";
    if (id) b.id = id;
    if (icon && window.Icons) b.appendChild(Icons.svg(icon));
    b.appendChild(el("span", "", text));
    b.addEventListener("click", onClick);
    return b;
  }
  const buttons = (...items) => { const box = el("div", "settings-buttons"); items.forEach((b) => box.appendChild(b)); return box; };

  // ------------------------------------------------------------------ Kategorie "Tastatur"
  function renderKeyboard() {
    const host = document.getElementById("settings-keyboard-root");
    if (!host) return;
    host.textContent = "";
    const keys = section(t("KB_SECTION"), t("KB_SECTION_HINT"));
    const count = Array.isArray(window.__hotkeys) ? window.__hotkeys.filter((h) => h.enabled !== false && h.keys && h.command).length : 0;
    keys.appendChild(buttons(
      button(t("KB_SHOW"), "settings-kb-show", () => { const item = document.querySelector('[data-action="open-shortcuts-modal"]'); if (item) item.click(); }, "keyboard"),
      button(t("KB_CUSTOM"), "settings-kb-custom", () => { if (window.OCHotkeys) window.OCHotkeys.open(); }, "keys")));
    keys.appendChild(el("p", "ai-row__hint", t("KB_CUSTOM_COUNT", { n: count })));
    host.appendChild(keys);
  }

  // ------------------------------------------------------------------ Kategorie "MIDI"
  const FACTORY = { enabled: true, output: "", ignore: [], clock: false, mtc: false, msc: false, msc_device: 127, mtc_out: false, mtc_fps: 1, clock_out: false };
  const SIMPLE = [["mtc", "MIDI_SET_MTC"], ["clock", "MIDI_SET_CLOCK"], ["mtc_out", "MIDI_SET_MTC_OUT"], ["mtc_fps", "MIDI_SET_MTC_FPS"], ["clock_out", "MIDI_SET_CLOCK_OUT"], ["msc", "MIDI_SET_MSC"], ["msc_device", "MIDI_SET_MSC_DEVICE"]];
  let saved = null;
  let draft = null;
  let status = null;
  let timer = 0;
  const rows = {};                                                    // Schluessel -> Zeile (fuer die Markierung geaenderter Einstellungen)

  const midiNow = () => window.__midi || { enabled: true, output: "", ignore: [], bindings: [] };
  const pick = (c) => ({ enabled: c.enabled !== false, output: c.output || "", ignore: [...(c.ignore || [])].sort(), clock: c.clock === true, mtc: c.mtc === true,
    msc: c.msc === true, msc_device: c.msc_device === undefined ? 127 : +c.msc_device, mtc_out: c.mtc_out === true, mtc_fps: c.mtc_fps === undefined ? 1 : +c.mtc_fps, clock_out: c.clock_out === true });
  const sameIgnore = (a, b) => JSON.stringify([...a].sort()) === JSON.stringify([...b].sort());

  function load() {
    saved = pick(midiNow());
    if (!draft) draft = clone(saved);
  }

  function changes() {
    if (!saved || !draft) return [];
    const out = [];
    if (draft.enabled !== saved.enabled && rows.enabled && rows.enabled.isConnected) out.push({ key: "midi:enabled", label: t("MIDI_SET_ENABLE"), row: rows.enabled, revert: () => { draft.enabled = saved.enabled; render(); } });
    if (draft.output !== saved.output && rows.output && rows.output.isConnected) out.push({ key: "midi:output", label: t("MIDI_SET_SECTION_OUT"), row: rows.output, revert: () => { draft.output = saved.output; render(); } });
    SIMPLE.forEach(([key, labelKey]) => {
      if (draft[key] !== saved[key] && rows[key] && rows[key].isConnected) out.push({ key: "midi:" + key, label: t(labelKey), row: rows[key], revert: () => { draft[key] = saved[key]; render(); } });
    });
    const ids = new Set([...draft.ignore, ...saved.ignore]);
    ids.forEach((id) => {
      if (draft.ignore.includes(id) === saved.ignore.includes(id)) return;
      const node = rows["dev:" + id];
      if (!node || !node.isConnected) return;
      out.push({ key: "midi:dev:" + id, label: id, row: node, revert: () => { draft.ignore = saved.ignore.includes(id) ? [...new Set([...draft.ignore, id])] : draft.ignore.filter((x) => x !== id); render(); } });
    });
    return out;
  }

  function reset() {
    if (!draft) load();
    draft = clone(FACTORY);
    render();
  }

  function change(patch) { draft = Object.assign(draft, patch); touch(); }

  const pad2 = (n) => String(n).padStart(2, "0");
  function mtcText() {
    if (!saved || !saved.mtc) return "";
    if (!status || !status.mtc_locked) return t("MIDI_SET_MTC_NONE");
    const ms = Math.max(0, Math.round(status.mtc_ms));
    const frames = Math.floor(((ms % 1000) / 1000) * Math.round(status.mtc_fps || 25));
    return t("MIDI_SET_MTC_NOW", { time: pad2(Math.floor(ms / 3600000)) + ":" + pad2(Math.floor(ms / 60000) % 60) + ":" + pad2(Math.floor(ms / 1000) % 60) + ":" + pad2(frames), fps: String(status.mtc_fps).replace(/\.0+$/, "") });
  }

  function clockText() {
    if (!saved || !saved.clock) return "";
    return status && status.clock_bpm ? t("MIDI_SET_CLOCK_NOW", { bpm: status.clock_bpm }) : t("MIDI_SET_CLOCK_NONE");
  }

  function stateText(port, used) {
    if (!used) return t("MIDI_SET_STATE_OFF");
    if (port.error) return t("MIDI_SET_STATE_BUSY");
    return port.open ? t("MIDI_SET_STATE_OPEN") : t("MIDI_SET_STATE_IDLE");
  }

  function render() {
    const host = document.getElementById("settings-midi-root");
    if (!host || !draft) return;
    host.textContent = "";
    Object.keys(rows).forEach((k) => delete rows[k]);

    const main = section(t("MIDI_SET_SECTION_MAIN"));
    if (status && status.available === false) main.appendChild(el("p", "ai-row__hint", t("MIDI_LIB_MISSING", { e: status.error || "python-rtmidi" })));
    rows.enabled = row(t("MIDI_SET_ENABLE"), toggle("settings-midi-enabled", draft.enabled, (on) => { change({ enabled: on }); render(); }), t("MIDI_SET_ENABLE_HINT"));
    main.appendChild(rows.enabled);
    const select = el("select", "ai-wide");
    select.id = "settings-midi-output";
    const outs = (status && status.outputs) || [];
    const auto = el("option", "", outs.length ? t("MIDI_OUTPUT_AUTO") + (status && status.output ? " (" + status.output + ")" : "") : t("MIDI_OUTPUT_NONE"));
    auto.value = "";
    select.appendChild(auto);
    outs.forEach((p) => { const o = el("option", "", p.name); o.value = p.id; select.appendChild(o); });
    if (draft.output && !outs.some((p) => p.id === draft.output)) { const o = el("option", "", draft.output); o.value = draft.output; select.appendChild(o); }
    select.value = draft.output || "";
    select.addEventListener("change", () => change({ output: select.value }));
    rows.output = row(t("MIDI_SET_SECTION_OUT"), select, t("MIDI_SET_OUT_HINT"));
    main.appendChild(rows.output);
    host.appendChild(main);

    const inputs = section(t("MIDI_SET_SECTION_IN"));
    const list = el("div", "midi-devices");
    const present = (status && status.inputs) || [];
    present.forEach((port) => {
      const used = !draft.ignore.includes(port.id);
      const node = row(port.name, toggle("settings-midi-dev-" + port.id.replace(/[^A-Za-z0-9]+/g, "_"), used, (on) => {
        draft.ignore = on ? draft.ignore.filter((x) => x !== port.id) : [...new Set([...draft.ignore, port.id])];
        touch(); render();
      }), stateText(port, used));
      node.classList.add("midi-device-row");
      if (draft.enabled === false) node.classList.add("midi-device-row--off");
      rows["dev:" + port.id] = node;
      list.appendChild(node);
    });
    draft.ignore.filter((id) => !present.some((p) => p.id === id)).forEach((id) => {                 // ein abgewaehltes Geraet, das gerade nicht angeschlossen ist
      const node = row(id, toggle("settings-midi-dev-" + id.replace(/[^A-Za-z0-9]+/g, "_"), false, () => { draft.ignore = draft.ignore.filter((x) => x !== id); touch(); render(); }), t("MIDI_SET_ABSENT"));
      rows["dev:" + id] = node;
      list.appendChild(node);
    });
    if (!present.length && !draft.ignore.length) list.appendChild(el("p", "ai-row__hint", status ? t("MIDI_SET_NONE") : "..."));
    inputs.appendChild(list);
    inputs.appendChild(buttons(button(t("MIDI_SET_REFRESH"), "settings-midi-refresh", () => send("midi_status"), "refresh")));
    host.appendChild(inputs);

    const time = section(t("MIDI_SET_SECTION_TIME"));
    rows.mtc = row(t("MIDI_SET_MTC"), toggle("settings-midi-mtc", draft.mtc, (on) => { change({ mtc: on }); render(); }), t("MIDI_SET_MTC_HINT"));
    rows.mtc.querySelector(".ai-row__control").appendChild(el("p", "ai-row__hint midi-mtc-now", mtcText()));
    time.appendChild(rows.mtc);
    rows.clock = row(t("MIDI_SET_CLOCK"), toggle("settings-midi-clock", draft.clock, (on) => { change({ clock: on }); render(); }), t("MIDI_SET_CLOCK_HINT"));
    rows.clock.querySelector(".ai-row__control").appendChild(el("p", "ai-row__hint midi-clock-now", clockText()));
    time.appendChild(rows.clock);
    host.appendChild(time);

    const out2 = section(t("MIDI_SET_SECTION_SEND"));
    rows.mtc_out = row(t("MIDI_SET_MTC_OUT"), toggle("settings-midi-mtc-out", draft.mtc_out, (on) => { change({ mtc_out: on }); render(); }), t("MIDI_SET_MTC_OUT_HINT"));
    out2.appendChild(rows.mtc_out);
    const fps = el("select", "ai-wide");
    fps.id = "settings-midi-mtc-fps";
    [[0, "24"], [1, "25"], [2, "29,97"], [3, "30"]].forEach(([v, text]) => { const o = el("option", "", text + " " + t("MIDI_SET_FPS_UNIT")); o.value = String(v); fps.appendChild(o); });
    fps.value = String(draft.mtc_fps);
    fps.disabled = !draft.mtc_out;
    fps.addEventListener("change", () => change({ mtc_fps: parseInt(fps.value, 10) }));
    rows.mtc_fps = row(t("MIDI_SET_MTC_FPS"), fps);
    out2.appendChild(rows.mtc_fps);
    rows.clock_out = row(t("MIDI_SET_CLOCK_OUT"), toggle("settings-midi-clock-out", draft.clock_out, (on) => { change({ clock_out: on }); render(); }), t("MIDI_SET_CLOCK_OUT_HINT"));
    out2.appendChild(rows.clock_out);
    host.appendChild(out2);

    const show = section(t("MIDI_SET_SECTION_MSC"));
    rows.msc = row(t("MIDI_SET_MSC"), toggle("settings-midi-msc", draft.msc, (on) => { change({ msc: on }); render(); }), t("MIDI_SET_MSC_HINT"));
    show.appendChild(rows.msc);
    const dev = el("input", "ai-wide");
    dev.type = "number"; dev.id = "settings-midi-msc-device"; dev.min = "0"; dev.max = "127"; dev.step = "1"; dev.value = String(draft.msc_device);
    dev.disabled = !draft.msc;
    dev.addEventListener("input", () => { const n = parseInt(dev.value, 10); if (!isNaN(n)) change({ msc_device: Math.max(0, Math.min(127, n)) }); });
    rows.msc_device = row(t("MIDI_SET_MSC_DEVICE"), dev, t("MIDI_SET_MSC_DEVICE_HINT"));
    show.appendChild(rows.msc_device);
    host.appendChild(show);

    const map = section(t("MIDI_SET_SECTION_MAP"));
    const active = (midiNow().bindings || []).filter((b) => b.enabled !== false && b.type && b.command).length;
    map.appendChild(buttons(button(t("MIDI_SET_OPEN"), "settings-midi-open", () => { if (window.OCMidi) window.OCMidi.open(); }, "midi")));
    map.appendChild(el("p", "ai-row__hint", t("MIDI_SET_COUNT", { n: active })));
    host.appendChild(map);
    touch();
  }

  function commit() {
    if (!draft || !saved) return;
    const pending = draft.enabled !== saved.enabled || draft.output !== saved.output || SIMPLE.some(([key]) => draft[key] !== saved[key]) || !sameIgnore(draft.ignore, saved.ignore);
    if (!pending) return;
    send("set_midi", { midi: Object.assign(clone(midiNow()), { enabled: draft.enabled, output: draft.output, ignore: [...draft.ignore], clock: draft.clock, mtc: draft.mtc, msc: draft.msc, msc_device: draft.msc_device, mtc_out: draft.mtc_out, mtc_fps: draft.mtc_fps, clock_out: draft.clock_out }) });
    saved = clone(draft);                                           // der Dialog bleibt offen: weiter mit dem gespeicherten Stand
    render();
  }

  function poll() {
    clearInterval(timer);
    timer = setInterval(() => { if (!visible("settings-midi-root")) { clearInterval(timer); return; } send("midi_status"); }, 3000);
  }

  if (window.OCSettings || true) {
    const exportData = () => { const c = pick(midiNow()); return { enabled: c.enabled, output: c.output, clock: c.clock, mtc: c.mtc, msc: c.msc, msc_device: c.msc_device, mtc_out: c.mtc_out, mtc_fps: c.mtc_fps, clock_out: c.clock_out }; };       // ohne Geraete (rechnerbezogen) und ohne die Belegung (eigener Export)
    const importData = (data) => {
      if (!data || typeof data !== "object") return;
      load();
      ["enabled", "clock", "mtc", "msc", "mtc_out", "clock_out"].forEach((key) => { if (typeof data[key] === "boolean") draft[key] = data[key]; });
      ["msc_device", "mtc_fps"].forEach((key) => { if (typeof data[key] === "number") draft[key] = data[key]; });
      if (typeof data.output === "string") draft.output = data.output;
      render();
    };
    const register = () => { if (window.OCSettings) window.OCSettings.register({ id: "midi", category: "midi", changes, reset, exportData, importData }); else setTimeout(register, 50); };
    register();
    const registerOsc = () => { if (window.OCSettings) window.OCSettings.register({ id: "osc", category: "osc", changes: oscChanges, reset: oscReset }); else setTimeout(registerOsc, 50); };
    registerOsc();
  }
  // ------------------------------------------------------------------ Kategorie "OSC" (an / aus, Port; Zuordnungen und Adressen im Dialog "OSC ...")
  let oscSaved = null;
  let oscDraft = null;
  let oscFull = null;                                               // die ganze Konfiguration vom Server (Zuordnungen usw. bleiben beim Speichern unberuehrt)
  const oscRows = {};

  async function oscLoad() {
    try {
      const res = await fetch("/api/osc");
      const data = await res.json();
      oscFull = data.config;
      oscSaved = { enabled: !!oscFull.enabled, port: oscFull.port };
      if (!oscDraft) oscDraft = clone(oscSaved);
      oscRender(data.status);
    } catch (e) { /* offline */ }
  }

  function oscChanges() {
    if (!oscSaved || !oscDraft) return [];
    const out = [];
    if (oscDraft.enabled !== oscSaved.enabled && oscRows.enabled && oscRows.enabled.isConnected) out.push({ key: "osc:enabled", label: t("OSC_SET_ENABLE"), row: oscRows.enabled, revert: () => { oscDraft.enabled = oscSaved.enabled; oscRender(); } });
    if (oscDraft.port !== oscSaved.port && oscRows.port && oscRows.port.isConnected) out.push({ key: "osc:port", label: t("OSC_SET_PORT"), row: oscRows.port, revert: () => { oscDraft.port = oscSaved.port; oscRender(); } });
    return out;
  }

  function oscReset() {
    if (!oscDraft) return;
    oscDraft = { enabled: false, port: 9000 };
    oscRender();
  }

  function oscRender(status) {
    const host = document.getElementById("settings-osc-root");
    if (!host || !oscDraft) return;
    host.textContent = "";
    const box = section(t("OSC_SET_SECTION"), t("OSC_WARNING"));
    oscRows.enabled = row(t("OSC_SET_ENABLE"), toggle("settings-osc-enabled", oscDraft.enabled, (on) => { oscDraft.enabled = on; touch(); oscRender(); }), t("OSC_SET_ENABLE_HINT"));
    box.appendChild(oscRows.enabled);
    const port = el("input", "ai-wide");
    port.type = "number"; port.id = "settings-osc-port"; port.min = "1"; port.max = "65535"; port.step = "1"; port.value = String(oscDraft.port);
    port.disabled = !oscDraft.enabled;
    port.addEventListener("input", () => { const n = parseInt(port.value, 10); if (n >= 1 && n <= 65535) { oscDraft.port = n; touch(); } });
    oscRows.port = row(t("OSC_SET_PORT"), port);
    box.appendChild(oscRows.port);
    if (status && oscSaved && oscSaved.enabled) box.appendChild(el("p", "ai-row__hint", status.listening ? t("OSC_STATUS_ON", { addresses: (status.addresses.length ? status.addresses : ["127.0.0.1"]).map((a) => a + ":" + status.port).join(", ") }) : t("OSC_STATUS_ERROR", { error: status.error || "?" })));
    const maps = (oscFull && oscFull.bindings || []).filter((b) => b.enabled !== false && b.command).length;
    box.appendChild(buttons(button(t("OSC_SET_OPEN"), "settings-osc-open", () => { if (window.OCOsc) window.OCOsc.open(); }, "link")));
    box.appendChild(el("p", "ai-row__hint", t("OSC_SET_COUNT", { n: maps })));
    host.appendChild(box);
    touch();
  }

  async function oscCommit() {
    if (!oscDraft || !oscSaved) return;
    if (oscDraft.enabled === oscSaved.enabled && oscDraft.port === oscSaved.port) return;
    const fresh = await fetch("/api/osc").then((r) => r.json()).catch(() => null);      // den neuesten Stand holen (der OSC-Dialog speichert selbststaendig)
    const config = Object.assign({}, (fresh && fresh.config) || oscFull || {}, { enabled: oscDraft.enabled, port: oscDraft.port });
    const res = await fetch("/api/osc/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(config) }).catch(() => null);
    if (res && res.ok) { const data = await res.json(); oscFull = data.config; oscSaved = { enabled: !!oscFull.enabled, port: oscFull.port }; oscDraft = clone(oscSaved); oscRender(data.status); }
  }

  document.addEventListener("settings-opened", () => { draft = null; oscDraft = null; });
  document.addEventListener("settings-cancelled", () => { draft = null; oscDraft = null; });
  document.addEventListener("settings-saved", () => { commit(); oscCommit(); });
  document.addEventListener("settings-category-shown", (e) => {
    const category = e.detail && e.detail.category;
    if (category === "keyboard") renderKeyboard();
    if (category === "midi") { load(); render(); send("midi_status"); poll(); }
    if (category === "osc") oscLoad();
  });
  document.addEventListener("oc-midi-event", (e) => {
    const message = e.detail || {};
    if (message.type !== "midi_status") return;
    const before = status ? JSON.stringify([status.inputs, status.outputs, status.output, status.available]) : "";
    status = message.payload;
    if (!(draft && visible("settings-midi-root"))) return;
    if (before !== JSON.stringify([status.inputs, status.outputs, status.output, status.available])) { render(); return; }      // sonst nur das Tempo aktualisieren (kein Neuzeichnen: ein offenes Auswahlfeld soll offen bleiben)
    const now = document.querySelector("#settings-midi-root .midi-clock-now");
    if (now) now.textContent = clockText();
    const tc = document.querySelector("#settings-midi-root .midi-mtc-now");
    if (tc) tc.textContent = mtcText();
  });
  document.addEventListener("midi-changed", () => {
    if (!saved) return;
    const before = saved;
    load();                                                         // (load behaelt einen vorhandenen Entwurf)
    saved = pick(midiNow());
    if (draft && JSON.stringify(pick(before)) === JSON.stringify(pick(draft))) draft = clone(saved);       // unveraendert: der neue Stand uebernimmt
    if (visible("settings-midi-root")) render();
    if (visible("settings-keyboard-root")) renderKeyboard();
  });
  document.addEventListener("hotkeys-changed", () => { if (visible("settings-keyboard-root")) renderKeyboard(); });
  document.addEventListener("i18n-applied", () => { if (visible("settings-midi-root")) render(); if (visible("settings-keyboard-root")) renderKeyboard(); if (visible("settings-osc-root")) oscRender(); });
})();
