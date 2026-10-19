/* Globaler Timecode (die interne Uhr) - Client-Seite.
 *  - OCTimecode: Spiegel des Server-Zustands (laeuft/Richtung/Rate/Position) mit lokaler Fortschreibung zwischen den Meldungen,
 *    Formatieren/Parsen von Zeiten, Bedienung (Nachrichten an den Server).
 *  - Panel "timecode": Anzeige + Start/Pause/Stopp/rueckwaerts/Springen/Geschwindigkeit.
 * Der Server ist die einzige Uhr: jede Meldung (und der Herzschlag jede Sekunde waehrend des Laufs) setzt Position und Zeitpunkt
 * neu; dazwischen rechnet jeder Client selbst weiter (Position + Richtung * Rate * verstrichene Zeit). Laeuft nach app.js. */
(function () {
  "use strict";

  const MAX_MS = 100 * 3600 * 1000;
  const t = (key, vars) => {
    let s = i18n(key);
    if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
    return s;
  };
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  // ------------------------------------------------------------------------------------------ Zeit formatieren/lesen
  const pad = (n, w) => String(n).padStart(w, "0");

  /** Millisekunden -> "HH:MM:SS.mmm" (withMs=false: "HH:MM:SS"). */
  function fmt(ms, withMs) {
    const total = Math.max(0, Math.floor(Number(ms) || 0));
    const h = Math.floor(total / 3600000);
    const m = Math.floor(total / 60000) % 60;
    const s = Math.floor(total / 1000) % 60;
    const base = `${pad(h, 2)}:${pad(m, 2)}:${pad(s, 2)}`;
    return withMs === false ? base : `${base}.${pad(total % 1000, 3)}`;
  }

  /** Text -> Millisekunden oder null. Erlaubt "4.3" / "4,3" (Sekunden), "1:04.300", "00:00:04.300"; hoechstens 100 Stunden. */
  function parse(text) {
    const raw = String(text == null ? "" : text).trim().replace(",", ".");
    if (!raw) return null;
    const parts = raw.split(":");
    if (parts.length > 3) return null;
    const seconds = parts.pop();
    if (!/^\d+(\.\d+)?$/.test(seconds)) return null;
    let total = parseFloat(seconds);
    const unit = [60, 3600];
    for (let i = 0; i < parts.length; i += 1) {
      const idx = parts.length - 1 - i;                 // letzte Stelle vor den Sekunden = Minuten, davor Stunden
      const part = parts[idx];
      if (!/^\d+$/.test(part)) return null;
      total += parseInt(part, 10) * unit[i];
    }
    const ms = Math.round(total * 1000);
    return ms >= 0 && ms <= MAX_MS ? ms : null;
  }

  // -------------------------------------------------------------------------------------------- Zustand + Bedienung
  let state = { running: false, direction: 1, rate: 1, position_ms: 0 };
  let receivedAt = performance.now();
  const listeners = new Set();

  function ingest(next) {
    if (!next || typeof next !== "object") return;
    state = { running: !!next.running, direction: next.direction < 0 ? -1 : 1, rate: Number(next.rate) || 1, position_ms: Number(next.position_ms) || 0 };
    receivedAt = performance.now();
    listeners.forEach((fn) => { try { fn(state); } catch (e) { console.error(e); } });
  }

  /** Aktuelle Position in ms (laeuft zwischen den Server-Meldungen lokal weiter). */
  function position() {
    if (!state.running) return state.position_ms;
    return Math.min(MAX_MS, Math.max(0, state.position_ms + state.direction * state.rate * (performance.now() - receivedAt)));
  }

  const send = (type, payload) => client.send(type, payload || {});
  const OC = {
    fmt, parse, position, ingest, MAX_MS,
    get state() { return state; },
    subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    play(direction) { send("timecode_play", { direction: direction < 0 ? -1 : 1 }); },
    pause() { send("timecode_pause"); },
    stop() { send("timecode_stop"); },
    seek(ms) { send("timecode_seek", { position_ms: Math.max(0, Math.round(ms)) }); },
    setRate(rate) { send("timecode_rate", { rate }); },
  };
  window.OCTimecode = OC;

  // ---- Toolbar-Anzeige (Chip neben der Uhrzeit): laeuft nur, solange etwas laeuft; sonst beim Zustandswechsel
  let chipRaf = 0;
  function drawChip() {
    chipRaf = 0;
    const chip = document.getElementById("toolbar-timecode");
    const text = document.getElementById("toolbar-timecode-text");
    if (!chip || !text) return;
    text.textContent = "TC " + fmt(position());
    chip.classList.toggle("menubar__tc--run", state.running);
    chip.classList.toggle("menubar__tc--pause", !state.running && state.position_ms > 0);
    chip.title = t(state.running ? (state.direction < 0 ? "TC_STATE_REVERSE" : "TC_STATE_RUNNING") : (state.position_ms > 0 ? "TC_STATE_PAUSED" : "TC_STATE_STOPPED")) + " \u00B7 " + t("PANEL_TIMECODE");
    if (state.running) chipRaf = requestAnimationFrame(drawChip);
  }
  listeners.add(() => { if (!chipRaf) drawChip(); });
  document.addEventListener("DOMContentLoaded", drawChip);

  // Module-Anbindung: bekommt state_snapshot (mit "timecode") und timecode_state
  client.registerModule("timecode", {
    onMessage(message) {
      if (message.type === "state_snapshot" && message.payload && message.payload.timecode) ingest(message.payload.timecode);
      else if (message.type === "timecode_state") ingest(message.payload);
    },
  });

  // ------------------------------------------------------------------------------------------------------ Panel
  const RATES = [0.25, 0.5, 1, 1.5, 2, 4];

  function iconButton(icon, labelKey, onClick, cls) {
    const b = el("button", "tcp__btn" + (cls ? " " + cls : ""));
    b.type = "button";
    b.appendChild(Icons.svg(icon));
    b.dataset.i18nTip = labelKey;
    b.title = t(labelKey);
    b.setAttribute("aria-label", t(labelKey));
    b.addEventListener("click", onClick);
    return b;
  }

  function buildPanel(panel) {
    const wrap = el("div", "tcp");
    const display = el("div", "tcp__display", fmt(position()));
    display.setAttribute("role", "timer");
    const status = el("div", "tcp__status");
    const dot = el("span", "tcp__dot");
    const statusText = el("span", "tcp__status-text");
    status.append(dot, statusText);

    const transport = el("div", "tcp__transport");
    const bReset = iconButton("skip-start", "TC_RESET", () => OC.stop(), "tcp__btn--reset");
    const bRev = iconButton("play-reverse", "TC_PLAY_REVERSE", () => OC.play(-1), "tcp__btn--rev");
    const bPause = iconButton("pause", "TC_PAUSE", () => OC.pause(), "tcp__btn--pause");
    const bPlay = iconButton("play", "TC_PLAY", () => OC.play(1), "tcp__btn--play");
    transport.append(bReset, bRev, bPause, bPlay);

    const step = el("div", "tcp__row tcp__row--step");
    const bBack = el("button", "tcp__small");
    bBack.type = "button";
    bBack.appendChild(Icons.svg("step-back"));
    bBack.appendChild(el("span", "", "1 s"));
    bBack.addEventListener("click", () => OC.seek(Math.max(0, position() - 1000)));
    const bFwd = el("button", "tcp__small");
    bFwd.type = "button";
    bFwd.appendChild(el("span", "", "1 s"));
    bFwd.appendChild(Icons.svg("step-forward"));
    bFwd.addEventListener("click", () => OC.seek(position() + 1000));
    step.append(bBack, bFwd);

    const goto_ = el("form", "tcp__row tcp__row--goto");
    const gotoLabel = el("label", "tcp__label");
    gotoLabel.dataset.i18n = "TC_GOTO";
    gotoLabel.textContent = t("TC_GOTO");
    const input = el("input", "tcp__input");
    input.type = "text";
    input.placeholder = "00:00:04.300";
    input.maxLength = 14;
    input.autocomplete = "off";
    input.spellcheck = false;
    input.setAttribute("aria-label", t("TC_GOTO"));
    gotoLabel.htmlFor = "";
    const go = el("button", "tcp__small tcp__small--primary", t("TC_GO"));
    go.type = "submit";
    go.dataset.i18n = "TC_GO";
    goto_.append(gotoLabel, input, go);
    goto_.addEventListener("submit", (event) => {
      event.preventDefault();
      const ms = parse(input.value);
      if (ms === null) { input.classList.add("tcp__input--bad"); _showToast("TC_ERR_PARSE", "warn", 3000); return; }
      input.classList.remove("tcp__input--bad");
      OC.seek(ms);
      input.value = "";
    });
    input.addEventListener("input", () => input.classList.remove("tcp__input--bad"));

    const speed = el("div", "tcp__row tcp__row--speed");
    const speedLabel = el("label", "tcp__label");
    speedLabel.dataset.i18n = "TC_SPEED";
    speedLabel.textContent = t("TC_SPEED");
    const select = el("select", "tcp__select");
    RATES.forEach((r) => { const o = el("option", "", `${r}×`); o.value = String(r); select.appendChild(o); });
    select.addEventListener("change", () => OC.setRate(parseFloat(select.value)));
    speed.append(speedLabel, select);

    const fs = el("button", "tcp__fs");
    fs.type = "button";
    fs.appendChild(Icons.svg("expand"));
    const labelFs = () => {
      fs.title = t(OCFullscreen.isFull(wrap) ? "TC_FULLSCREEN_EXIT" : "TC_FULLSCREEN");
      fs.setAttribute("aria-label", fs.title);
    };
    labelFs();
    fs.addEventListener("click", () => OCFullscreen.toggle(wrap));
    display.addEventListener("dblclick", () => OCFullscreen.toggle(wrap));
    wrap.addEventListener("ocfullscreen", (event) => {
      fs.textContent = "";
      fs.appendChild(Icons.svg(event.detail ? "collapse" : "expand"));
      labelFs();
    });
    wrap.append(fs, display, status, transport, step, goto_, speed);

    let raf = 0;
    const draw = () => {
      raf = 0;
      if (!wrap.isConnected) return;
      display.textContent = fmt(position());
      if (state.running) raf = requestAnimationFrame(draw);
    };
    const refresh = () => {
      if (!wrap.isConnected) return false;
      const running = state.running;
      const atZero = !running && state.position_ms <= 0;
      bPlay.classList.toggle("tcp__btn--on", running && state.direction > 0);
      bRev.classList.toggle("tcp__btn--on", running && state.direction < 0);
      bPause.classList.toggle("tcp__btn--on", !running && !atZero);
      bReset.classList.toggle("tcp__btn--on", atZero);
      dot.className = "tcp__dot" + (running ? " tcp__dot--run" : (atZero ? "" : " tcp__dot--pause"));
      statusText.textContent = running ? t(state.direction < 0 ? "TC_STATE_REVERSE" : "TC_STATE_RUNNING") : t(atZero ? "TC_STATE_STOPPED" : "TC_STATE_PAUSED");
      if (document.activeElement !== select) select.value = String(RATES.includes(state.rate) ? state.rate : 1);
      if (!RATES.includes(state.rate)) {
        let custom = select.querySelector("option[data-custom]");
        if (!custom) { custom = el("option"); custom.dataset.custom = "1"; select.appendChild(custom); }
        custom.value = String(state.rate);
        custom.textContent = `${state.rate}×`;
        select.value = String(state.rate);
      }
      if (!raf) draw();
      return true;
    };
    const unsubscribe = OC.subscribe(() => { if (!refresh()) unsubscribe(); });
    wrap._relabel = () => { labelFs(); refresh(); };
    const onTranslated = () => {
      if (wrap.isConnected) wrap._wasConnected = true;
      if (!wrap.isConnected && wrap._wasConnected && !OCFullscreen.isFull(wrap)) { document.removeEventListener("i18n-applied", onTranslated); return; }
      wrap._relabel();
    };
    document.addEventListener("i18n-applied", onTranslated);
    requestAnimationFrame(() => { applyConfig(wrap, panel && panel.module_config); refresh(); });
    return wrap;
  }

  function applyConfig(wrap, mc) {
    const cfg = mc || {};
    wrap.querySelector(".tcp__row--goto").hidden = cfg.show_goto === false;
    wrap.querySelector(".tcp__row--speed").hidden = cfg.show_speed === false;
    wrap.querySelector(".tcp__row--step").hidden = cfg.show_step === false;
  }

  window.__panelPlugins.register({
    type: "timecode",
    buildContent: buildPanel,
    onModuleConfigChanged(panelEl, mc) {
      const wrap = OCFullscreen.query(panelEl, ".tcp");
      if (wrap) applyConfig(wrap, mc);
    },
    onMessage(panelEl, messageType) {
      if (messageType === "language_changed") {
        const wrap = OCFullscreen.query(panelEl, ".tcp");
        if (wrap && wrap._relabel) wrap._relabel();
      }
    },
    buildPropertiesPane(moduleConfig, api) {
      const mc = moduleConfig || {};
      const frag = document.createDocumentFragment();
      [["tcp-prop-goto", "TC_PROP_GOTO", mc.show_goto !== false], ["tcp-prop-speed", "TC_PROP_SPEED", mc.show_speed !== false],
       ["tcp-prop-step", "TC_PROP_STEP", mc.show_step !== false]].forEach(([id, key, checked]) => {
        const field = el("div", "modal__field modal__field--checkbox");
        const toggle = makeToggleSwitch(id, checked);
        const label = el("label");
        label.htmlFor = id;
        label.dataset.i18n = key;
        label.textContent = api.i18n(key);
        field.append(toggle.label, label);
        frag.appendChild(field);
      });
      return frag;
    },
    readPropertiesPane() {
      const on = (id) => { const node = document.getElementById(id); return node ? node.checked : true; };
      return { show_goto: on("tcp-prop-goto"), show_speed: on("tcp-prop-speed"), show_step: on("tcp-prop-step") };
    },
  });

  if (typeof PANEL_TITLE_KEYS !== "undefined") PANEL_TITLE_KEYS.timecode = "PANEL_TIMECODE";
})();
