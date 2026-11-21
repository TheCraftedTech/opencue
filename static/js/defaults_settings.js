// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Einstellungen -> Kategorie "Standardwerte" (nur an der Konsole selbst; Server: app/console_defaults.py).
 * Gilt fuer das ganze Programm, ueber alle Shows hinweg: Vorgaben fuer NEUE Cues (Abspielart, Zeiten, MIB) und der Grundzustand nach Clear Clear (Dimmer, Farbe, Position).
 * Wie die anderen Einstellungen: die Seite bearbeitet einen ENTWURF; erst "Speichern" schickt ihn an den Server (Ereignis "settings-saved"), "Abbrechen"/Schliessen verwirft ihn.
 * Geaenderte Zeilen markiert und zaehlt settings_tracker.js (Anbieter "defaults": changes(), reset()). Klassisches Skript, laeuft nach settings_tracker.js. */
(function () {
  "use strict";
  const t = (key) => i18n(key);
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const root = () => document.getElementById("settings-defaults-root");
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const FACTORY = { cue_play_mode: "tracking", cue_trigger: "go", cue_delay: 0, cue_fade: 0, cue_fx_fade_in: 0, cue_fx_fade_out: 0, cue_mib: "Off", update_mode: "ask",
    clear_dimmer: 0, clear_color: "#ffffff", clear_position: "zero", start_master_mode: "show", start_grand_master: 100, start_blackout: false, executor_start: 100,
    confirm_delete_cues: true, confirm_delete_fixtures: true, confirm_delete_library: true, confirm_delete_files: true, confirm_delete_other: true };     // wie app/console_defaults.py
  const KEYS = [["cue_play_mode", "DEFAULTS_CUE_PLAY"], ["cue_trigger", "DEFAULTS_CUE_TRIGGER"], ["cue_delay", "DEFAULTS_CUE_DELAY"], ["cue_fade", "DEFAULTS_CUE_FADE"], ["cue_fx_fade_in", "DEFAULTS_CUE_FX_IN"],
    ["cue_fx_fade_out", "DEFAULTS_CUE_FX_OUT"], ["cue_mib", "DEFAULTS_CUE_MIB"], ["update_mode", "DEFAULTS_UPDATE_MODE"],
    ["clear_dimmer", "DEFAULTS_CLEAR_DIMMER"], ["clear_color", "DEFAULTS_CLEAR_COLOR"], ["clear_position", "DEFAULTS_CLEAR_POSITION"],
    ["start_master_mode", "DEFAULTS_START_MASTER"], ["start_grand_master", "DEFAULTS_START_MASTER_VALUE"], ["start_blackout", "DEFAULTS_START_BLACKOUT"], ["executor_start", "DEFAULTS_EXECUTOR_START"],
    ["confirm_delete_cues", "DEFAULTS_DEL_CUES"], ["confirm_delete_fixtures", "DEFAULTS_DEL_FIXTURES"], ["confirm_delete_library", "DEFAULTS_DEL_LIBRARY"], ["confirm_delete_files", "DEFAULTS_DEL_FILES"], ["confirm_delete_other", "DEFAULTS_DEL_OTHER"]];
  let saved = null;            // gespeicherte Werte (Server)
  let draft = null;            // Entwurf dieser Sitzung des Dialogs (null = noch nicht geladen / verworfen)
  let factory = { ...FACTORY };
  const rowOf = {};
  const touch = () => { if (window.OCSettings) window.OCSettings.touch(); };

  function changes() {
    if (!saved || !draft) return [];
    const out = [];
    KEYS.forEach(([key, labelKey]) => {
      if (draft[key] === saved[key] || !rowOf[key] || !rowOf[key].isConnected) return;
      out.push({ key: "defaults:" + key, label: t(labelKey), row: rowOf[key], revert: () => { draft[key] = saved[key]; render(); } });
    });
    return out;
  }
  async function reset() {
    if (!draft) await load();
    if (!draft) return;
    draft = { ...draft, ...factory };
    render();
  }
  async function load() {
    let data;
    try { data = await (await fetch("/api/defaults", { cache: "no-store" })).json(); } catch (err) { return; }
    saved = data.config;
    if (data.defaults) factory = data.defaults;
    if (!draft) draft = { ...saved };
    render();
  }

  function row(key, label, control, hint) {
    const wrap = el("div", "ai-row");
    if (key) rowOf[key] = wrap;
    const left = el("label", "ai-row__label");
    left.appendChild(el("span", "ai-row__name", label));
    const right = el("div", "ai-row__control");
    right.appendChild(control);
    if (hint) right.appendChild(el("p", "ai-row__hint", hint));
    wrap.append(left, right);
    return wrap;
  }
  const section = (title, intro) => { const box = el("div", "settings-section"); box.appendChild(el("div", "settings-section__title", title)); if (intro) box.appendChild(el("p", "ai-row__hint", intro)); return box; };
  function change(patch) { draft = Object.assign(draft || { ...saved }, patch); touch(); }
  function select(id, options, value, onChange) {
    const s = el("select", "ai-wide");
    s.id = id;
    options.forEach(([v, text]) => { const o = el("option", "", text); o.value = v; s.appendChild(o); });
    s.value = value;
    s.addEventListener("change", () => onChange(s.value));
    return s;
  }
  function toggle(id, on, onChange) {
    const label = el("label", "toggle-switch");
    const box = el("input");
    box.type = "checkbox"; box.id = id; box.checked = !!on;
    box.addEventListener("change", () => onChange(box.checked));
    label.append(box, el("span", "toggle-switch__track"));
    return label;
  }
  function number(id, value, min, max, step, onChange, unit) {
    const wrap = el("div", "defaults-number");
    const input = el("input", "ai-wide");
    input.type = "number"; input.id = id; input.min = String(min); input.max = String(max); input.step = String(step);
    input.value = String(value);
    input.addEventListener("input", () => { const n = parseFloat(input.value); if (!isNaN(n)) onChange(Math.max(min, Math.min(max, n))); });
    wrap.appendChild(input);
    if (unit) wrap.appendChild(el("span", "defaults-number__unit", unit));
    return wrap;
  }

  function render() {
    const host = root();
    if (!host || !draft) return;
    host.textContent = "";
    const cues = section(t("DEFAULTS_SECTION_CUES"), t("DEFAULTS_SECTION_CUES_HINT"));
    cues.appendChild(row("cue_play_mode", t("DEFAULTS_CUE_PLAY"), select("settings-defaults-play", [["tracking", t("CUE_PLAY_TRACKING")], ["absolute", t("CUE_PLAY_ABSOLUTE")]], draft.cue_play_mode, (v) => change({ cue_play_mode: v })), t("DEFAULTS_CUE_PLAY_HINT")));
    cues.appendChild(row("cue_trigger", t("DEFAULTS_CUE_TRIGGER"), select("settings-defaults-trigger", [["go", t("CUE_TRIGGER_GO")], ["follow", t("CUE_TRIGGER_FOLLOW")]], draft.cue_trigger, (v) => change({ cue_trigger: v })), t("DEFAULTS_CUE_TRIGGER_HINT")));
    cues.appendChild(row("cue_delay", t("DEFAULTS_CUE_DELAY"), number("settings-defaults-delay", draft.cue_delay, 0, 3600, 0.1, (v) => change({ cue_delay: v }), "s")));
    cues.appendChild(row("cue_fade", t("DEFAULTS_CUE_FADE"), number("settings-defaults-fade", draft.cue_fade, 0, 3600, 0.1, (v) => change({ cue_fade: v }), "s")));
    cues.appendChild(row("cue_fx_fade_in", t("DEFAULTS_CUE_FX_IN"), number("settings-defaults-fx-in", draft.cue_fx_fade_in, 0, 3600, 0.1, (v) => change({ cue_fx_fade_in: v }), "s")));
    cues.appendChild(row("cue_fx_fade_out", t("DEFAULTS_CUE_FX_OUT"), number("settings-defaults-fx-out", draft.cue_fx_fade_out, 0, 3600, 0.1, (v) => change({ cue_fx_fade_out: v }), "s")));
    cues.appendChild(row("cue_mib", t("DEFAULTS_CUE_MIB"), select("settings-defaults-mib", [["Off", t("CUE_MIB_OFF")], ["Auto", t("CUE_MIB_AUTO")], ["On", t("CUE_MIB_ON")]], draft.cue_mib, (v) => change({ cue_mib: v }))));
    cues.appendChild(row("update_mode", t("DEFAULTS_UPDATE_MODE"), select("settings-defaults-update", [["ask", t("DEFAULTS_UPDATE_ASK")], ["normal", t("DEFAULTS_UPDATE_NORMAL")], ["only", t("DEFAULTS_UPDATE_ONLY")]], draft.update_mode, (v) => change({ update_mode: v })), t("DEFAULTS_UPDATE_HINT")));
    host.appendChild(cues);

    const clear = section(t("DEFAULTS_SECTION_CLEAR"), t("DEFAULTS_SECTION_CLEAR_HINT"));
    clear.appendChild(row("clear_dimmer", t("DEFAULTS_CLEAR_DIMMER"), number("settings-defaults-dimmer", draft.clear_dimmer, 0, 100, 1, (v) => change({ clear_dimmer: v }), "%"), t("DEFAULTS_CLEAR_DIMMER_HINT")));
    const color = el("input", "color-swatch-input");
    color.type = "color"; color.id = "settings-defaults-color"; color.value = draft.clear_color || "#ffffff";
    color.addEventListener("input", () => change({ clear_color: color.value.toLowerCase() }));
    clear.appendChild(row("clear_color", t("DEFAULTS_CLEAR_COLOR"), color, t("DEFAULTS_CLEAR_COLOR_HINT")));
    clear.appendChild(row("clear_position", t("DEFAULTS_CLEAR_POSITION"), select("settings-defaults-position", [["zero", t("DEFAULTS_POS_ZERO")], ["center", t("DEFAULTS_POS_CENTER")]], draft.clear_position, (v) => change({ clear_position: v }))));
    host.appendChild(clear);

    const start = section(t("DEFAULTS_SECTION_START"), t("DEFAULTS_SECTION_START_HINT"));
    start.appendChild(row("start_master_mode", t("DEFAULTS_START_MASTER"), select("settings-defaults-master-mode", [["show", t("DEFAULTS_MASTER_SHOW")], ["fixed", t("DEFAULTS_MASTER_FIXED")]], draft.start_master_mode, (v) => { change({ start_master_mode: v }); render(); })));
    const masterValue = number("settings-defaults-master", draft.start_grand_master, 0, 100, 1, (v) => change({ start_grand_master: v }), "%");
    masterValue.querySelector("input").disabled = draft.start_master_mode !== "fixed";
    start.appendChild(row("start_grand_master", t("DEFAULTS_START_MASTER_VALUE"), masterValue));
    start.appendChild(row("start_blackout", t("DEFAULTS_START_BLACKOUT"), toggle("settings-defaults-blackout", draft.start_blackout, (on) => change({ start_blackout: on })), t("DEFAULTS_START_BLACKOUT_HINT")));
    start.appendChild(row("executor_start", t("DEFAULTS_EXECUTOR_START"), number("settings-defaults-executor", draft.executor_start, 0, 100, 1, (v) => change({ executor_start: v }), "%"), t("DEFAULTS_EXECUTOR_START_HINT")));
    host.appendChild(start);

    const del = section(t("DEFAULTS_SECTION_DELETE"), t("DEFAULTS_SECTION_DELETE_HINT"));
    [["confirm_delete_cues", "DEFAULTS_DEL_CUES", "settings-defaults-del-cues"], ["confirm_delete_fixtures", "DEFAULTS_DEL_FIXTURES", "settings-defaults-del-fixtures"],
     ["confirm_delete_library", "DEFAULTS_DEL_LIBRARY", "settings-defaults-del-library"], ["confirm_delete_files", "DEFAULTS_DEL_FILES", "settings-defaults-del-files"],
     ["confirm_delete_other", "DEFAULTS_DEL_OTHER", "settings-defaults-del-other"]].forEach(([key, labelKey, id]) => {
      del.appendChild(row(key, t(labelKey), toggle(id, draft[key] !== false, (on) => change({ [key]: on }))));
    });
    host.appendChild(del);
    touch();
  }

  async function commit() {
    const pending = draft && saved && !same({ ...saved, ...draft }, saved) ? { ...draft } : null;
    if (!pending) return;
    try {
      const res = await fetch("/api/defaults", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(pending) });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || res.status);
      saved = data.config;
      draft = { ...saved };                    // der Dialog bleibt offen: weiter mit dem frisch gespeicherten Stand
      render();
    } catch (err) {
      if (typeof _showToast === "function") _showToast(t("DEFAULTS_SAVE_FAILED"), "error", 4000);
    }
  }

  async function exportData() {
    if (!saved) await load();
    return saved ? { ...saved } : null;
  }
  async function importData(data) {                  // nur bekannte Schluessel mit passendem Typ; als Entwurf (Speichern uebernimmt)
    if (!data || typeof data !== "object") return;
    if (!draft) await load();
    if (!draft) return;
    const patch = {};
    Object.keys(FACTORY).forEach((key) => { if (key in data && typeof data[key] === typeof FACTORY[key]) patch[key] = data[key]; });
    draft = Object.assign(draft, patch);
    render();
  }
  const register = () => { if (window.OCSettings) window.OCSettings.register({ id: "defaults", category: "defaults", changes, reset, exportData, importData }); else setTimeout(register, 50); };
  register();
  document.addEventListener("settings-opened", () => { draft = null; });
  document.addEventListener("settings-cancelled", () => { draft = null; });
  document.addEventListener("settings-saved", commit);
  document.addEventListener("settings-category-shown", (e) => { if (e.detail && e.detail.category === "defaults") load(); });
  document.addEventListener("i18n-applied", () => { const r = root(); if (r && r.offsetParent) render(); });
})();
