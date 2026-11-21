// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Panel "Audio": Live-Analyse des Tons (app/audio_engine.py) - Quelle waehlen, Spektrum, Pegel, Einsaetze (Bassdrum / Snare / Hi-Hat), Beat und Tempo.
 * Die Analyse laeuft auf der Konsole und gilt fuer alle Geraete: jedes Audio-Panel zeigt und bedient dieselbe Quelle und dieselben Einstellungen. Die Messwerte
 * (25 Hz) schickt der Server nur an Geraete mit offenem Audio-Panel (Nachricht audio_subscribe -> audio_frame); Quelle und Einstellungen kommen als audio_state.
 * Gesteuert wird ueber /api/audio (Geraeteliste, Start/Stopp, Einstellungen, Tap). Laeuft nach app.js. */
(function () {
  "use strict";

  const t = (key) => i18n(key);
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  // ------------------------------------------------------------------------------------------ Zustand (gemeinsam fuer alle Panels)
  let devices = [];
  let state = { running: false, error: "", device: "", device_name: "", rate: 0, config: {} };
  let frame = null;
  const views = new Set();                       // offene Panels (jedes mit .update(), .draw())
  const wants = new Set();                       // weitere Abnehmer der Messwerte (z. B. "widgets": Button / Fader / Toggle mit Audio-Signal)
  const listeners = new Set();                   // Rueckrufe bei jedem neuen Bild
  let subscribed = false;
  let raf = 0;
  let devicesLoaded = false;

  async function api(method, path, body) {
    try {
      const res = await fetch(path, { method, cache: "no-store", headers: body !== undefined ? { "Content-Type": "application/json" } : {}, body: body !== undefined ? JSON.stringify(body) : undefined });
      return res.ok ? await res.json() : null;
    } catch (err) {
      return null;
    }
  }

  async function loadDevices() {
    const data = await api("GET", "/api/audio");
    if (!data) return;
    devices = data.devices || [];
    state = Object.assign(state, data.state || {});
    devicesLoaded = true;
    views.forEach((v) => v.update());
  }

  function syncSubscription() {
    [...views].forEach((v) => {                                          // ein Panel, das einmal im Dokument war und jetzt nicht mehr, ist geschlossen
      if (v.root.isConnected) v.seen = true;
      else if (v.seen) views.delete(v);
    });
    applySubscription();
  }

  /** Der Server schickt Messwerte, solange ein Audio-Panel offen ist oder ein anderer Abnehmer sie braucht. */
  function applySubscription() {
    const want = views.size > 0 || wants.size > 0;
    if (want !== subscribed) {
      subscribed = want;
      client.send("audio_subscribe", { on: want });
    }
  }

  /** Fuer andere Teile der Oberflaeche (Signale von Button / Fader / Toggle): die Messwerte mitlesen, ohne ein Audio-Panel zu brauchen. */
  window.OCAudio = {
    want(key, on) { if (on) wants.add(key); else wants.delete(key); applySubscription(); },
    subscribe(callback) { listeners.add(callback); return () => listeners.delete(callback); },
    frame: () => frame,
    state: () => state,
  };

  function ensureLoop() {
    if (!raf && views.size) raf = requestAnimationFrame(loop);
  }

  function loop() {
    raf = 0;
    syncSubscription();
    if (!views.size) return;
    views.forEach((v) => v.draw());
    ensureLoop();
  }

  client.registerModule("audio", {
    onMessage(message) {
      if (message.type === "audio_frame") {
        frame = message.payload;
        listeners.forEach((callback) => { try { callback(frame); } catch (err) { /* ein Abnehmer darf die anderen nicht stoeren */ } });
      } else if (message.type === "audio_state") {
        state = Object.assign(state, message.payload || {});
        views.forEach((v) => v.update());
      } else if (message.type === "state_snapshot" && subscribed) {
        client.send("audio_subscribe", { on: true });                 // nach (Wieder-)Verbindung neu anmelden
      }
    },
  });

  // ------------------------------------------------------------------------------------------ Hilfen
  const cfg = () => state.config || {};
  const gainToSlider = (g) => Math.round(50 + 50 * Math.log10(Math.max(0.1, Math.min(10, g))));
  const sliderToGain = (v) => Math.pow(10, (v - 50) / 50);

  function slider(labelKey, tipKey, min, max, step, read, write, format) {
    const row = el("div", "aup__row");
    const label = el("label", "aup__label", t(labelKey));
    label.dataset.i18n = labelKey;
    const input = el("input", "aup__range");
    input.type = "range";
    input.min = String(min);
    input.max = String(max);
    input.step = String(step);
    const value = el("span", "aup__value");
    if (tipKey) { row.title = t(tipKey); row.dataset.i18nTip = tipKey; }
    let timer = 0;
    input.addEventListener("input", () => {
      value.textContent = format(Number(input.value));
      clearTimeout(timer);
      timer = setTimeout(() => api("POST", "/api/audio/config", write(Number(input.value))), 120);
    });
    row.append(label, input, value);
    row._sync = () => {
      if (document.activeElement !== input) input.value = String(read());
      value.textContent = format(Number(input.value));
      if (window.ocRangeFill) window.ocRangeFill(input);
    };
    return row;
  }

  function buildPanel(panel) {
    const root = el("div", "aup");
    const view = { root, update: () => {}, draw: () => {} };

    // ---- Quelle
    const top = el("div", "aup__top");
    const select = el("select", "aup__select");
    select.setAttribute("aria-label", t("AUDIO_SOURCE"));
    const refresh = el("button", "aup__icon");
    refresh.type = "button";
    refresh.appendChild(Icons.svg("refresh"));
    refresh.title = t("AUDIO_REFRESH");
    refresh.dataset.i18nTip = "AUDIO_REFRESH";
    const power = el("button", "aup__power");
    power.type = "button";
    top.append(select, refresh, power);

    const status = el("div", "aup__status");
    const dot = el("span", "aup__dot");
    const statusText = el("span", "aup__status-text");
    status.append(dot, statusText);

    // ---- Anzeige
    const stage = el("div", "aup__stage");
    const canvas = el("canvas", "aup__canvas");
    const hint = el("div", "aup__hint");
    const axis = el("div", "aup__axis");
    [[100, "100"], [1000, "1k"], [10000, "10k"]].forEach(([hz, text]) => {
      const tick = el("span", "aup__tick", text);
      tick.style.left = (100 * Math.log(hz / 30) / Math.log(16000 / 30)) + "%";
      axis.appendChild(tick);
    });
    stage.append(canvas, hint);

    const lamps = el("div", "aup__lamps");
    const lampDefs = [["a_kick", "AUDIO_KICK"], ["a_snare", "AUDIO_SNARE"], ["a_hat", "AUDIO_HAT"], ["a_beat", "AUDIO_BEAT"]];
    const lampNodes = {};
    lampDefs.forEach(([key, labelKey]) => {
      const lamp = el("div", "aup__lamp aup__lamp--" + key.slice(2));
      lamp.append(el("span", "aup__lamp-dot"), el("span", "aup__lamp-text", t(labelKey)));
      lamp.dataset.key = key;
      lamp.querySelector(".aup__lamp-text").dataset.i18n = labelKey;
      lamps.appendChild(lamp);
      lampNodes[key] = lamp;
    });

    const meter = el("div", "aup__meter");
    const meterLabel = el("span", "aup__meter-label", t("AUDIO_LEVEL"));
    meterLabel.dataset.i18n = "AUDIO_LEVEL";
    const meterTrack = el("div", "aup__meter-track");
    const meterFill = el("div", "aup__meter-fill");
    meterTrack.appendChild(meterFill);
    const clip = el("span", "aup__clip", t("AUDIO_CLIP"));
    clip.dataset.i18n = "AUDIO_CLIP";
    meter.append(meterLabel, meterTrack, clip);

    // ---- Tempo
    const tempo = el("div", "aup__tempo");
    const bpmBox = el("div", "aup__bpm");
    const bpmNumber = el("span", "aup__bpm-number", "--");
    const bpmUnit = el("span", "aup__bpm-unit", t("AUDIO_BPM"));
    bpmUnit.dataset.i18n = "AUDIO_BPM";
    const beatLed = el("span", "aup__beat-led");
    bpmBox.append(beatLed, bpmNumber, bpmUnit);
    const phaseTrack = el("div", "aup__phase");
    const phaseFill = el("div", "aup__phase-fill");
    phaseTrack.appendChild(phaseFill);
    const confidence = el("div", "aup__conf");
    const confFill = el("div", "aup__conf-fill");
    confidence.appendChild(confFill);
    confidence.title = t("AUDIO_CONF");
    confidence.dataset.i18nTip = "AUDIO_CONF";

    const tempoButtons = el("div", "aup__tempo-buttons");
    const mkBtn = (key, tipKey, onClick) => {
      const b = el("button", "aup__btn", t(key));
      b.type = "button";
      b.dataset.i18n = key;
      if (tipKey) { b.title = t(tipKey); b.dataset.i18nTip = tipKey; }
      b.addEventListener("click", onClick);
      return b;
    };
    const currentBpm = () => (frame && frame.v && frame.v.a_bpm) || cfg().bpm || 120;
    const bTap = mkBtn("AUDIO_TAP", "AUDIO_TAP_TIP", () => api("POST", "/api/audio/tap"));
    const bHalf = mkBtn("AUDIO_HALF", "AUDIO_HALF_TIP", () => api("POST", "/api/audio/config", { mode: "manual", bpm: currentBpm() / 2 }));
    const bDouble = mkBtn("AUDIO_DOUBLE", "AUDIO_DOUBLE_TIP", () => api("POST", "/api/audio/config", { mode: "manual", bpm: currentBpm() * 2 }));
    const bMode = mkBtn("AUDIO_AUTO", "AUDIO_MODE_TIP", () => api("POST", "/api/audio/config", { mode: cfg().mode === "manual" ? "auto" : "manual", bpm: currentBpm() }));
    bMode.classList.add("aup__btn--mode");
    const bpmInput = el("input", "aup__bpm-input");
    bpmInput.type = "number";
    bpmInput.min = "30";
    bpmInput.max = "300";
    bpmInput.step = "0.5";
    bpmInput.setAttribute("aria-label", t("AUDIO_BPM"));
    bpmInput.addEventListener("change", () => {
      const v = parseFloat(bpmInput.value);
      if (Number.isFinite(v)) api("POST", "/api/audio/config", { mode: "manual", bpm: v });
    });
    tempoButtons.append(bMode, bpmInput, bHalf, bDouble, bTap);
    tempo.append(bpmBox, phaseTrack, confidence, tempoButtons);

    // ---- Einstellungen
    const settings = el("details", "aup__settings");
    settings.open = true;
    const summary = el("summary", "aup__summary", t("AUDIO_SETTINGS"));
    summary.dataset.i18n = "AUDIO_SETTINGS";
    settings.appendChild(summary);
    const rows = [
      slider("AUDIO_GAIN", "AUDIO_GAIN_TIP", 0, 100, 1, () => gainToSlider(cfg().gain || 1), (v) => ({ gain: sliderToGain(v) }), (v) => "×" + sliderToGain(v).toFixed(2)),
      slider("AUDIO_SENS", "AUDIO_SENS_TIP", 0, 100, 1, () => Math.round((cfg().sensitivity == null ? 0.5 : cfg().sensitivity) * 100), (v) => ({ sensitivity: v / 100 }), (v) => v + " %"),
      slider("AUDIO_SMOOTH", "AUDIO_SMOOTH_TIP", 0, 100, 1, () => Math.round((cfg().smoothing == null ? 0.5 : cfg().smoothing) * 100), (v) => ({ smoothing: v / 100 }), (v) => v + " %"),
      slider("AUDIO_LATENCY", "AUDIO_LATENCY_TIP", -100, 200, 5, () => Math.round(cfg().latency_ms || 0), (v) => ({ latency_ms: v }), (v) => (v > 0 ? "+" : "") + v + " ms"),
    ];
    rows.forEach((r) => settings.appendChild(r));
    const toggles = el("div", "aup__toggles");
    const mkToggle = (id, labelKey, read, write) => {
      const row = el("div", "aup__toggle");
      const tg = makeToggleSwitch(id + "-" + Math.random().toString(36).slice(2, 7), false);
      const label = el("label", "aup__toggle-label", t(labelKey));
      label.htmlFor = tg.input.id;
      label.dataset.i18n = labelKey;
      tg.input.addEventListener("change", () => api("POST", "/api/audio/config", write(tg.input.checked)));
      row.append(tg.label, label);
      row._sync = () => { tg.input.checked = !!read(); };
      return row;
    };
    const autoGain = mkToggle("aup-ag", "AUDIO_AUTOGAIN", () => cfg().auto_gain !== false, (v) => ({ auto_gain: v }));
    const follow = mkToggle("aup-pf", "AUDIO_FOLLOW", () => cfg().phase_follow !== false, (v) => ({ phase_follow: v }));
    toggles.append(autoGain, follow);
    settings.appendChild(toggles);

    root.append(top, status, stage, axis, lamps, meter, tempo, settings);

    // ---- Verhalten
    refresh.addEventListener("click", () => loadDevices());
    select.addEventListener("change", async () => {
      const id = select.value;
      if (!id) return;
      if (state.running) await api("POST", "/api/audio/start", { device: id });
      else await api("POST", "/api/audio/config", { device: id });
    });
    power.addEventListener("click", async () => {
      if (state.running) await api("POST", "/api/audio/stop");
      else if (select.value) await api("POST", "/api/audio/start", { device: select.value });
    });

    const errorText = (code) => {
      const key = "AUDIO_ERR_" + String(code || "").split(":")[0].toUpperCase();
      const text = t(key);
      return text !== key ? text : String(code);
    };

    view.update = () => {
      // Geraeteliste
      const signature = JSON.stringify(devices.map((d) => d.id)) + "|" + (cfg().device || "");
      if (select._signature !== signature) {
        select._signature = signature;
        select.textContent = "";
        const placeholder = el("option", "", t("AUDIO_NO_SOURCE"));
        placeholder.value = "";
        select.appendChild(placeholder);
        [["loopback", "AUDIO_GROUP_LOOPBACK"], ["input", "AUDIO_GROUP_INPUT"], ["network", "AUDIO_GROUP_NETWORK"], ["demo", "AUDIO_GROUP_DEMO"]].forEach(([kind, key]) => {
          const list = devices.filter((d) => d.kind === kind);
          if (!list.length) return;
          const group = el("optgroup");
          group.label = t(key);
          list.forEach((d) => {
            const o = el("option", "", (d.kind === "demo" ? t("AUDIO_DEMO") : d.name) + (d.default ? " " + t("AUDIO_DEFAULT") : ""));
            o.value = d.id;
            group.appendChild(o);
          });
          select.appendChild(group);
        });
        select.value = cfg().device || "";
        if (select.value !== (cfg().device || "")) {                       // gewaehlte Quelle fehlt (Geraet abgezogen): als eigener Eintrag zeigen
          const missing = el("option", "", cfg().device.replace(/^(loopback|input):/, ""));
          missing.value = cfg().device;
          select.appendChild(missing);
          select.value = cfg().device;
        }
      }
      if (document.activeElement !== select) select.value = cfg().device || "";
      power.textContent = "";
      power.appendChild(Icons.svg(state.running ? "stop" : "play"));
      power.append(" " + t(state.running ? "AUDIO_STOP" : "AUDIO_START"));
      power.classList.toggle("aup__power--on", !!state.running);
      power.disabled = !state.running && !select.value;
      dot.className = "aup__dot" + (state.running ? " aup__dot--on" : (state.error && state.error !== "no_device" ? " aup__dot--err" : ""));
      statusText.textContent = state.running ? t("AUDIO_STATE_ON") + (state.device_name ? " · " + state.device_name : "") + (state.rate ? " · " + Math.round(state.rate / 100) / 10 + " kHz" : "")
        : (state.error && state.error !== "no_device" ? errorText(state.error) : t("AUDIO_STATE_OFF"));
      hint.textContent = state.running ? "" : t("AUDIO_HINT_IDLE");
      hint.hidden = !!state.running;
      bMode.textContent = t(cfg().mode === "manual" ? "AUDIO_MANUAL" : "AUDIO_AUTO");
      bMode.classList.toggle("aup__btn--on", cfg().mode === "manual");
      if (document.activeElement !== bpmInput) bpmInput.value = (cfg().bpm || 120).toFixed(1);
      bpmInput.disabled = cfg().mode !== "manual";
      rows.forEach((r) => r._sync());
      autoGain._sync();
      follow._sync();
      settings.hidden = (panel && panel.module_config && panel.module_config.show_settings === false);
    };

    const accent = () => getComputedStyle(root).getPropertyValue("--accent-color").trim() || "#ffb000";
    view.draw = () => {
      if (!root.isConnected) return;
      const v = (frame && state.running && frame.v) || null;
      const spec = (frame && frame.spectrum) || [];
      // Spektrum
      const dpr = window.devicePixelRatio || 1;
      const w = Math.max(10, Math.round(canvas.clientWidth * dpr));
      const h = Math.max(10, Math.round(canvas.clientHeight * dpr));
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, w, h);
      const color = accent();
      const n = 32;
      const gap = Math.max(1, Math.round(w / n * 0.18));
      const bw = (w - gap * (n - 1)) / n;
      const grad = ctx.createLinearGradient(0, h, 0, 0);
      grad.addColorStop(0, color + "55");
      grad.addColorStop(1, color);
      ctx.fillStyle = grad;
      for (let i = 0; i < n; i += 1) {
        const val = v ? Math.max(0, Math.min(1, spec[i] || 0)) : 0;
        const bh = Math.max(2, val * h);
        ctx.fillRect(i * (bw + gap), h - bh, bw, bh);
      }
      // Anzeigen
      const get = (k) => (v && v[k]) || 0;
      stage.style.setProperty("--beat", String(get("a_beat")));
      lampDefs.forEach(([key]) => lampNodes[key].style.setProperty("--on", String(get(key))));
      meterFill.style.width = (get("a_level") * 100).toFixed(1) + "%";
      clip.classList.toggle("aup__clip--on", !!(frame && frame.clip && state.running));
      const bpm = get("a_bpm");
      bpmNumber.textContent = v && bpm > 0 ? bpm.toFixed(1) : "--";
      beatLed.style.setProperty("--on", String(get("a_beat")));
      phaseFill.style.width = (get("a_beat_phase") * 100).toFixed(1) + "%";
      confFill.style.width = (get("a_conf") * 100).toFixed(0) + "%";
      root.classList.toggle("aup--idle", !state.running);
    };

    views.add(view);
    view.update();
    if (!devicesLoaded) loadDevices();
    syncSubscription();
    ensureLoop();
    const onTranslated = () => {
      if (!root.isConnected) { document.removeEventListener("i18n-applied", onTranslated); return; }
      select._signature = "";
      view.update();
    };
    document.addEventListener("i18n-applied", onTranslated);
    return root;
  }

  window.__panelPlugins.register({
    type: "audio",
    buildContent: buildPanel,
    onModuleConfigChanged(panelEl) {
      views.forEach((v) => { if (panelEl.contains(v.root)) v.update(); });
    },
    buildPropertiesPane(moduleConfig, api) {
      const mc = moduleConfig || {};
      const frag = document.createDocumentFragment();
      const field = el("div", "modal__field modal__field--checkbox");
      const toggle = makeToggleSwitch("aup-prop-settings", mc.show_settings !== false);
      const label = el("label");
      label.htmlFor = "aup-prop-settings";
      label.dataset.i18n = "AUDIO_PROP_SETTINGS";
      label.textContent = api.i18n("AUDIO_PROP_SETTINGS");
      field.append(toggle.label, label);
      frag.appendChild(field);
      return frag;
    },
    readPropertiesPane() {
      const node = document.getElementById("aup-prop-settings");
      return { show_settings: node ? node.checked : true };
    },
  });

  if (typeof PANEL_TITLE_KEYS !== "undefined") PANEL_TITLE_KEYS.audio = "PANEL_AUDIO";
})();
