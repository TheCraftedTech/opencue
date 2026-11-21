// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Einstellungen -> Gruppe "Bedienung" -> Kategorie "Timecode": woher die Uhr kommt (Eingang) und wohin sie gesendet wird (Ausgang).
 *   - Wer fuehrt die Uhr gerade? (dieser Computer / MIDI Timecode / LTC) - damit man bei den vielen Moeglichkeiten den Ueberblick behaelt.
 *   - LTC LESEN (Eingang): Timecode als Audiosignal von einem Audio-Eingang; OpenCue laeuft dann im Takt der Quelle.
 *   - LTC SENDEN (Ausgang): solange der Timecode vorwaerts laeuft (z. B. nach Start im Timecode-Panel), gibt OpenCue LTC auf einem Audio-Ausgang aus.
 * Server: app/ltc.py (Decoder, Eingang, Ausgang), app/ltc_routes.py (/api/ltc). MIDI Timecode steht unter Einstellungen -> MIDI.
 * Arbeitet wie die anderen Einstellungen mit einem ENTWURF: erst "Speichern" schickt ihn an den Server (Ereignis "settings-saved"), "Abbrechen" / Schliessen verwirft ihn;
 * geaenderte Zeilen markiert und zaehlt settings_tracker.js (Anbieter "ltc"). Auch an Fernzugriffs-Geraeten einstellbar (die Audio-Geraete haengen am Hauptrechner).
 * Klassisches Skript, nach controls_settings.js. */
(function () {
  "use strict";
  const t = (key, vars) => {
    let text = i18n(key);
    Object.keys(vars || {}).forEach((name) => { text = text.split("{" + name + "}").join(String(vars[name])); });
    return text;
  };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const touch = () => { if (window.OCSettings) window.OCSettings.touch(); };
  const FACTORY = { enabled: false, device: "", channel: "left", out: { enabled: false, device: "", channel: "both", fps: 25, level: 0.5 } };
  const CHANNELS = ["left", "right", "mix"];
  const OUT_CHANNELS = ["left", "right", "both"];
  const FPS = [[24, "LTC_FPS_24"], [25, "LTC_FPS_25"], [29.97, "LTC_FPS_2997"], [30, "LTC_FPS_30"]];
  const clone = (v) => JSON.parse(JSON.stringify(v));

  let saved = null;
  let draft = null;
  let status = null;                  // Antwort von /api/ltc (mit Geraetelisten)
  let timer = 0;
  const rows = {};

  const root = () => document.getElementById("settings-timecode-root");
  const visible = () => { const r = root(); return !!(r && r.offsetParent); };
  const pick = (c) => {
    const o = (c && c.out) || {};
    return {
      enabled: !!(c && c.enabled), device: String((c && c.device) || ""), channel: CHANNELS.includes(c && c.channel) ? c.channel : "left",
      out: { enabled: !!o.enabled, device: String(o.device || ""), channel: OUT_CHANNELS.includes(o.channel) ? o.channel : "both", fps: [24, 25, 29.97, 30].includes(Number(o.fps)) ? Number(o.fps) : 25, level: Math.min(1, Math.max(0.05, Number(o.level) || 0.5)) },
    };
  };
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

  async function fetchStatus(withDevices) {
    try {
      const res = await fetch("/api/ltc" + (withDevices ? "?devices=1" : ""));
      if (!res.ok) return null;
      const data = await res.json();
      if (!withDevices && status) { data.devices = status.devices; data.outputs = status.outputs; }
      return data;
    } catch (e) { return null; }
  }

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

  function select(id, options, value, disabled, onChange) {
    const s = el("select", "ai-wide");
    s.id = id;
    s.disabled = !!disabled;
    options.forEach(([v, text]) => { const o = el("option", "", text); o.value = String(v); s.appendChild(o); });
    s.value = String(value);
    if (s.value !== String(value)) { const o = el("option", "", String(value).replace(/^(input|loopback|output):/, "")); o.value = String(value); s.appendChild(o); s.value = String(value); }
    s.addEventListener("change", () => onChange(s.value));
    return s;
  }

  function errorText(code) {
    const key = String(code || "").split(":")[0];
    if (key === "no_device") return t("LTC_ERR_NO_DEVICE");
    if (key === "device_missing") return t("LTC_ERR_MISSING");
    if (key === "open_failed") return t("LTC_ERR_OPEN");
    return t("LTC_ERR_OTHER");
  }

  function inText() {
    if (!status || !saved || !saved.enabled) return t("LTC_ST_OFF");
    if (status.error) return errorText(status.error);
    if (status.locked) return t("LTC_ST_LOCKED", { tc: status.timecode, fps: String(status.fps).replace(".", ","), drop: status.drop ? " DF" : "" });
    if (status.running) return t("LTC_ST_WAIT");
    return t("LTC_ST_OFF");
  }

  function outText() {
    const out = status && status.out;
    if (!saved || !saved.out.enabled || !out) return t("LTC_ST_OFF");
    if (out.error) return String(out.error).startsWith("no_device") ? t("LTC_ERR_NO_OUT") : errorText(out.error);
    if (out.sending) return t("LTC_OUT_ST_SENDING", { fps: String(saved.out.fps).replace(".", ",") });
    if (out.running) return t("LTC_OUT_ST_IDLE");
    return t("LTC_ST_OFF");
  }

  function sourceText() {
    const s = window.OCTimecode && window.OCTimecode.state;
    if (!s || !s.running) return t("LTC_SRC_STANDING");
    return t(s.source === "ltc" ? "LTC_SRC_LTC" : s.source === "midi" ? "LTC_SRC_MIDI" : "LTC_SRC_INTERNAL");
  }

  function paintLive() {
    const r = root();
    if (!r) return;
    const text = r.querySelector(".ltc-status--in");
    if (text) {
      text.textContent = inText();
      text.classList.toggle("ltc-status--ok", !!(status && status.locked && saved && saved.enabled));
      text.classList.toggle("ltc-status--bad", !!(status && status.error && saved && saved.enabled));
    }
    const bar = r.querySelector(".ltc-level__bar");
    if (bar) bar.style.width = Math.round(Math.min(1, (status && saved && saved.enabled ? status.level : 0) || 0) * 100) + "%";
    const out = r.querySelector(".ltc-status--out");
    if (out) {
      out.textContent = outText();
      out.classList.toggle("ltc-status--ok", !!(status && status.out && status.out.sending && saved && saved.out.enabled));
      out.classList.toggle("ltc-status--bad", !!(status && status.out && status.out.error && saved && saved.out.enabled));
    }
    const src = r.querySelector(".ltc-source");
    if (src) src.textContent = sourceText();
  }

  function statusRow(labelKey, cls) {
    const live = el("div", "ai-row");
    const left = el("label", "ai-row__label");
    left.appendChild(el("span", "ai-row__name", t(labelKey)));
    live.appendChild(left);
    const right = el("div", "ai-row__control");
    right.appendChild(el("p", "ltc-status " + cls, ""));
    live.appendChild(right);
    return { live, right };
  }

  function render() {
    const host = root();
    if (!host || !draft) return;
    host.textContent = "";

    // ---- Wer fuehrt die Uhr?
    const overview = el("div", "settings-section");
    overview.appendChild(el("div", "settings-section__title", t("LTC_SRC_TITLE")));
    overview.appendChild(el("p", "ai-row__hint", t("LTC_SRC_HINT")));
    const now = el("p", "ltc-source-line");
    now.append(el("span", "", t("LTC_SRC_NOW") + " "), el("strong", "ltc-source", ""));
    overview.appendChild(now);
    host.appendChild(overview);

    // ---- Eingang
    const box = el("div", "settings-section");
    box.appendChild(el("div", "settings-section__title", t("LTC_IN_TITLE")));
    box.appendChild(el("p", "ai-row__hint", t("LTC_SECTION_HINT")));
    rows.enabled = row(t("LTC_ENABLE"), toggle("settings-ltc-enabled", draft.enabled, (on) => { draft.enabled = on; touch(); render(); }), t("LTC_ENABLE_HINT"));
    box.appendChild(rows.enabled);
    const inputs = (status && status.devices) || [];
    const inOptions = [["", t("LTC_DEVICE_NONE")]].concat(inputs.map((d) => [d.id, d.kind === "demo" ? t("LTC_DEVICE_DEMO") : (d.kind === "loopback" ? t("LTC_DEVICE_LOOP", { name: d.name }) : d.name)]));
    rows.device = row(t("LTC_DEVICE"), select("settings-ltc-device", inOptions, draft.device, !draft.enabled, (v) => { draft.device = v; touch(); }));
    box.appendChild(rows.device);
    rows.channel = row(t("LTC_CHANNEL"), select("settings-ltc-channel", [["left", t("LTC_CH_LEFT")], ["right", t("LTC_CH_RIGHT")], ["mix", t("LTC_CH_MIX")]], draft.channel, !draft.enabled, (v) => { draft.channel = v; touch(); }), t("LTC_CHANNEL_HINT"));
    box.appendChild(rows.channel);
    const st = statusRow("LTC_STATUS", "ltc-status--in");
    const meter = el("div", "ltc-level");
    meter.appendChild(el("div", "ltc-level__bar"));
    st.right.appendChild(meter);
    box.appendChild(st.live);
    box.appendChild(el("p", "ai-row__hint", t("LTC_FOLLOW_HINT")));
    host.appendChild(box);

    // ---- Ausgang
    const out = el("div", "settings-section");
    out.appendChild(el("div", "settings-section__title", t("LTC_OUT_TITLE")));
    out.appendChild(el("p", "ai-row__hint", t("LTC_OUT_HINT")));
    rows.outEnabled = row(t("LTC_OUT_ENABLE"), toggle("settings-ltc-out-enabled", draft.out.enabled, (on) => { draft.out.enabled = on; touch(); render(); }), t("LTC_OUT_ENABLE_HINT"));
    out.appendChild(rows.outEnabled);
    const outputs = (status && status.outputs) || [];
    const outOptions = [["", t("LTC_DEVICE_NONE")]].concat(outputs.map((d) => [d.id, d.name]));
    rows.outDevice = row(t("LTC_OUT_DEVICE"), select("settings-ltc-out-device", outOptions, draft.out.device, !draft.out.enabled, (v) => { draft.out.device = v; touch(); }));
    out.appendChild(rows.outDevice);
    rows.outChannel = row(t("LTC_CHANNEL"), select("settings-ltc-out-channel", [["both", t("LTC_OCH_BOTH")], ["left", t("LTC_OCH_LEFT")], ["right", t("LTC_OCH_RIGHT")]], draft.out.channel, !draft.out.enabled, (v) => { draft.out.channel = v; touch(); }), t("LTC_OUT_CHANNEL_HINT"));
    out.appendChild(rows.outChannel);
    rows.outFps = row(t("LTC_OUT_FPS"), select("settings-ltc-out-fps", FPS.map(([v, key]) => [v, t(key)]), draft.out.fps, !draft.out.enabled, (v) => { draft.out.fps = Number(v); touch(); }));
    out.appendChild(rows.outFps);
    const level = el("input", "ai-wide");
    level.type = "range"; level.id = "settings-ltc-out-level"; level.min = "5"; level.max = "100"; level.step = "5"; level.value = String(Math.round(draft.out.level * 100));
    level.disabled = !draft.out.enabled;
    level.addEventListener("input", () => { draft.out.level = Number(level.value) / 100; touch(); });
    rows.outLevel = row(t("LTC_OUT_LEVEL"), level, t("LTC_OUT_LEVEL_HINT"));
    out.appendChild(rows.outLevel);
    const so = statusRow("LTC_STATUS", "ltc-status--out");
    out.appendChild(so.live);
    host.appendChild(out);

    paintLive();
    touch();
  }

  function changes() {
    if (!saved || !draft) return [];
    const list = [];
    const add = (key, labelKey, node, revert) => { if (node && node.isConnected) list.push({ key: "ltc:" + key, label: t(labelKey), row: node, revert: () => { revert(); render(); } }); };
    if (draft.enabled !== saved.enabled) add("enabled", "LTC_ENABLE", rows.enabled, () => { draft.enabled = saved.enabled; });
    if (draft.device !== saved.device) add("device", "LTC_DEVICE", rows.device, () => { draft.device = saved.device; });
    if (draft.channel !== saved.channel) add("channel", "LTC_CHANNEL", rows.channel, () => { draft.channel = saved.channel; });
    if (draft.out.enabled !== saved.out.enabled) add("oe", "LTC_OUT_ENABLE", rows.outEnabled, () => { draft.out.enabled = saved.out.enabled; });
    if (draft.out.device !== saved.out.device) add("od", "LTC_OUT_DEVICE", rows.outDevice, () => { draft.out.device = saved.out.device; });
    if (draft.out.channel !== saved.out.channel) add("oc", "LTC_CHANNEL", rows.outChannel, () => { draft.out.channel = saved.out.channel; });
    if (draft.out.fps !== saved.out.fps) add("of", "LTC_OUT_FPS", rows.outFps, () => { draft.out.fps = saved.out.fps; });
    if (Math.abs(draft.out.level - saved.out.level) > 0.001) add("ol", "LTC_OUT_LEVEL", rows.outLevel, () => { draft.out.level = saved.out.level; });
    return list;
  }

  function reset() {
    if (!draft) return;
    draft = clone(FACTORY);
    render();
  }

  async function load() {
    status = await fetchStatus(true);
    const config = (status && status.config) || (client.state && client.state.ltc) || FACTORY;
    saved = pick(config);
    if (!draft) draft = clone(saved);
    render();
    startPoll();
  }

  function startPoll() {
    clearInterval(timer);
    timer = setInterval(async () => {
      if (!visible()) { clearInterval(timer); timer = 0; return; }
      const next = await fetchStatus(false);
      if (next) { status = next; paintLive(); }
    }, 500);
  }

  async function commit() {
    if (!draft || !saved || same(draft, saved)) return;
    try {
      const res = await fetch("/api/ltc/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(draft) });
      if (res.ok) {
        const data = await res.json();
        status = Object.assign({}, status || {}, data);
        saved = pick(data.config);
        draft = clone(saved);
        if (client.state) client.state.ltc = saved;
        if (visible()) render();
      }
    } catch (e) { /* offline */ }
  }

  const register = () => { if (window.OCSettings) window.OCSettings.register({ id: "ltc", category: "timecode", changes, reset }); else setTimeout(register, 50); };
  register();
  document.addEventListener("settings-opened", () => { draft = null; });
  document.addEventListener("settings-cancelled", () => { draft = null; });
  document.addEventListener("settings-saved", () => { commit(); });
  document.addEventListener("settings-category-shown", (e) => { if (e.detail && e.detail.category === "timecode") load(); });
  document.addEventListener("i18n-applied", () => { if (visible() && draft) render(); });
  window.OCLtcSettings = { reload: load };
})();
