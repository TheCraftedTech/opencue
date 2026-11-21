// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Einstellungen -> Kategorie "Sprachsteuerung" (nur an der Konsole; Server: app/voice.py).
 * Wie die anderen Einstellungen: die Seite bearbeitet einen ENTWURF; erst "Speichern" schickt ihn an den Server (Ereignis "settings-saved" aus app.js),
 * "Abbrechen"/Schliessen verwirft ihn ("settings-cancelled"). Geaenderte Zeilen markiert und zaehlt settings_tracker.js (Anbieter "voice": changes(), reset()).
 * Ob das Weckwort zum Wortschatz passt, prueft die Seite schon beim Tippen (/api/voice/check, ohne zu speichern).
 * Unten "Ausprobieren": Stand der laufenden Erkennung (mit den GESPEICHERTEN Einstellungen) - Pegel, zuletzt verstanden, zuletzt erkannt, Knopf "Jetzt ausloesen".
 * Braucht voice.js (window.OCVoice). Klassisches Skript, laeuft nach voice.js. */
(function () {
  "use strict";
  const t = (key, vars) => { let s = i18n(key); if (vars) for (const [k, v] of Object.entries(vars)) s = s.split("{" + k + "}").join(String(v)); return s; };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const root = () => document.getElementById("settings-voice-root");               // Triggerwort
  const dictRoot = () => document.getElementById("settings-dictation-root");       // Diktieren
  const visible = () => { const r = root(); return !!(r && r.offsetParent); };
  const dictVisible = () => { const r = dictRoot(); return !!(r && r.offsetParent); };
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  let saved = null;            // gespeicherte Einstellungen (Server)
  let draft = null;            // Entwurf dieser Sitzung des Dialogs (null = noch nicht geladen / verworfen)
  let mics = [];
  let wordCheck = null;        // {phrase, unknown, error} zum Weckwort im Entwurf
  let checkTimer = 0;
  let pollTimer = 0;
  let model = { present: true, download: { state: "idle", percent: 0, error: "" } };       // Sprachmodell vorhanden? / wird gerade geladen? (Quelle: GET /api/voice)
  let modelTimer = 0;
  const refs = {};
  const rowOf = {};
  // Triggerwort (Sprachaktivierung) und Diktieren sind zwei getrennte Kategorien; beide bearbeiten denselben Entwurf der Sprach-Konfiguration (ein Speichern schickt alles)
  const WAKE_KEYS = [["enabled", "VOICE_ENABLE"], ["device", "VOICE_DEVICE"], ["wake_word", "VOICE_WORD"], ["sensitivity", "VOICE_SENSITIVITY"]];
  const DICT_KEYS = [["dictation_device", "DICT_DEVICE"], ["dictation_model", "DICT_MODEL"]];
  const DEFAULTS = { enabled: false, device: "", wake_word: "OpenCue", sensitivity: 60, dictation_device: "", dictation_model: "accurate" };       // wie app/voice.py DEFAULTS
  const touch = () => { if (window.OCSettings) window.OCSettings.touch(); };

  /** Zeilen, die vom Gespeicherten abweichen - jede mit eigenem Zurueck-Pfeil. */
  const changesOf = (keys, prefix) => () => {
    if (!saved || !draft) return [];
    const out = [];
    keys.forEach(([key, labelKey]) => {
      if (draft[key] === saved[key] || !rowOf[key] || !rowOf[key].isConnected) return;
      out.push({ key: prefix + ":" + key, label: t(labelKey), row: rowOf[key], revert: () => { draft[key] = saved[key]; renderAll(); checkWord(); } });
    });
    return out;
  };
  const resetOf = (keys) => async () => {
    if (!draft) await load(false);                  // Seite noch nie geoeffnet (z. B. "Alles zuruecksetzen"): erst den gespeicherten Stand holen
    if (!draft) return;
    keys.forEach(([key]) => { draft[key] = DEFAULTS[key]; });
    renderAll();
    checkWord();
  };

  async function load(withDevices) {
    let data;
    try { data = await (await fetch("/api/voice" + (withDevices ? "?devices=1" : ""), { cache: "no-store" })).json(); } catch (err) { return; }
    saved = data.config;
    model = { present: data.model_present !== false, download: data.model_download || model.download };
    if (Array.isArray(data.microphones)) mics = data.microphones;
    if (!draft) draft = { ...saved };
    if (withDevices && window.OCDictation) window.OCDictation.refresh();
    renderAll();
    checkWord();
    poll();
  }
  function renderAll() { render(); renderDictationPane(); }

  /** Passt das Weckwort im Entwurf zum Wortschatz des Modells? (Kurz nach dem Tippen.) */
  function checkWord() {
    clearTimeout(checkTimer);
    checkTimer = setTimeout(async () => {
      if (!draft) return;
      try {
        wordCheck = await (await fetch("/api/voice/check", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ wake_word: draft.wake_word }) })).json();
      } catch (err) { wordCheck = null; }
      paintWordHint();
    }, 250);
  }

  /** Fehlt das Sprachmodell (es wird nicht mit dem Programm ausgeliefert), zeigt die Seite einen Hinweis mit Knopf zum Laden und den Fortschritt. */
  function modelBox() {
    const dl = model.download || {};
    if (model.present && dl.state !== "downloading" && dl.state !== "extracting") return null;
    const box = el("div", "voice-model");
    box.id = "settings-voice-model";
    if (dl.state === "downloading" || dl.state === "extracting") {
      box.appendChild(el("p", "ai-row__hint ai-row__hint--note", dl.state === "extracting" ? t("VOICE_MODEL_EXTRACTING") : t("VOICE_MODEL_DOWNLOADING", { p: Math.round(dl.percent || 0) })));
      const bar = el("progress"); bar.max = 100; bar.value = dl.percent || 0; bar.className = "voice-model__bar";
      box.appendChild(bar);
      scheduleModelPoll();
      return box;
    }
    box.appendChild(el("p", "ai-row__hint ai-row__hint--note", t("VOICE_MODEL_MISSING")));
    if (dl.state === "error") box.appendChild(el("p", "ai-row__hint ai-row__hint--note voice-model__err", t("VOICE_MODEL_ERROR", { error: dl.error || "?" })));
    const button = el("button", "modal__button modal__button--primary", t("VOICE_MODEL_DOWNLOAD"));
    button.type = "button";
    button.id = "settings-voice-model-download";
    button.addEventListener("click", async () => {
      button.disabled = true;
      try { await fetch("/api/voice/model/download", { method: "POST" }); } catch (err) { /* der Stand zeigt den Fehler */ }
      scheduleModelPoll(true);
    });
    box.appendChild(button);
    return box;
  }
  function scheduleModelPoll(now) {
    clearTimeout(modelTimer);
    modelTimer = setTimeout(async () => { await load(false); }, now ? 400 : 1000);
  }

  /** Hauptschalter: grosse Zeile ganz oben (wie bei Fernzugriff und REST-API), Hinweis darunter. */
  function masterRow(key, label, control, hint) {
    const wrap = el("div", "settings-field settings-master");
    wrap.append(el("label", "", label), control);
    if (key) rowOf[key] = wrap;
    return [wrap, hint ? el("p", "settings-field-hint settings-keep", hint) : null].filter(Boolean);
  }
  function row(key, label, controls, hint) {
    const wrap = el("div", "ai-row");
    if (key) rowOf[key] = wrap;
    const left = el("label", "ai-row__label");
    left.appendChild(el("span", "ai-row__name", label));
    const right = el("div", "ai-row__control");
    [].concat(controls).forEach((n) => right.appendChild(n));
    if (hint) right.appendChild(hint instanceof Node ? hint : el("p", "ai-row__hint", hint));
    wrap.append(left, right);
    return wrap;
  }
  const section = (title, intro) => { const box = el("div", "settings-section"); box.appendChild(el("div", "settings-section__title", title)); if (intro) box.appendChild(el("p", "ai-row__hint", intro)); return box; };
  function change(patch) {
    draft = Object.assign(draft || { ...saved }, patch);
    touch();
  }

  function render() {
    const host = root();
    if (!host || !draft) return;
    host.textContent = "";
    const wake = section(t("VOICE_SECTION_WAKE"));
    const modelRow = modelBox();
    if (modelRow) wake.appendChild(modelRow);

    const toggle = el("label", "toggle-switch");
    const box = el("input");
    box.type = "checkbox";
    box.id = "settings-voice-enabled";
    box.checked = !!draft.enabled;
    box.addEventListener("change", () => change({ enabled: box.checked }));
    toggle.append(box, el("span", "toggle-switch__track"));
    masterRow("enabled", t("VOICE_ENABLE"), toggle, t("VOICE_ENABLE_HINT")).forEach((node) => wake.appendChild(node));

    const select = el("select", "ai-wide");
    select.id = "settings-voice-device";
    const add = (value, text) => { const o = el("option", "", text); o.value = value; select.appendChild(o); };
    add("", t("VOICE_DEVICE_DEFAULT"));
    mics.forEach((m) => add(m.id, m.name + (m.default ? " " + t("VOICE_DEVICE_IS_DEFAULT") : "")));
    if (draft.device && !mics.some((m) => m.id === draft.device)) add(draft.device, t("VOICE_DEVICE_MISSING", { name: draft.device.replace(/^input:/, "") }));
    select.value = draft.device || "";
    select.addEventListener("change", () => change({ device: select.value }));
    const reload = el("button", "modal__button", t("VOICE_DEVICE_REFRESH"));
    reload.type = "button";
    reload.addEventListener("click", () => load(true));
    wake.appendChild(row("device", t("VOICE_DEVICE"), [select, reload], t("VOICE_DEVICE_HINT")));

    const word = el("input", "ai-wide");
    word.type = "text";
    word.id = "settings-voice-word";
    word.maxLength = 40;
    word.spellcheck = false;
    word.value = draft.wake_word || "";
    word.placeholder = "OpenCue";
    word.addEventListener("input", () => { change({ wake_word: word.value.trim() || "OpenCue" }); checkWord(); });
    refs.wordHint = el("p", "ai-row__hint");
    wake.appendChild(row("wake_word", t("VOICE_WORD"), word, refs.wordHint));

    const slider = el("input");
    slider.type = "range";
    slider.min = "0"; slider.max = "100"; slider.step = "5";
    slider.id = "settings-voice-sensitivity";
    slider.value = String(draft.sensitivity);
    // so lange muss das Weckwort stabil erkannt sein (wie stable_chunks_needed in app/voice.py: 5 bis 8 Schritte je 0,1 s)
    const holdText = (v) => slider.value + " % · " + t("VOICE_SENSITIVITY_HOLD", { s: (Math.floor(8 - Number(v) / 100 * 3 + 0.5) / 10).toFixed(1).replace(".", ",") });
    const value = el("span", "voice-slider-value", holdText(slider.value));
    slider.addEventListener("input", () => { value.textContent = holdText(slider.value); change({ sensitivity: Number(slider.value) }); });
    const sliderWrap = el("div", "voice-slider");
    sliderWrap.append(slider, value);
    wake.appendChild(row("sensitivity", t("VOICE_SENSITIVITY"), sliderWrap, t("VOICE_SENSITIVITY_HINT")));
    host.appendChild(wake);

    const test = section(t("VOICE_SECTION_TEST"));
    refs.state = el("p", "voice-status");
    const meter = el("div", "voice-meter");
    refs.bar = el("div", "voice-meter__bar");
    meter.appendChild(refs.bar);
    refs.heard = el("p", "ai-row__hint");
    refs.woke = el("p", "ai-row__hint");
    test.appendChild(row(null, t("VOICE_STATUS"), [refs.state, meter, refs.heard, refs.woke], ""));
    const fire = el("button", "modal__button", t("VOICE_TEST_BUTTON"));
    fire.type = "button";
    fire.id = "settings-voice-trigger";
    fire.addEventListener("click", () => window.OCVoice.trigger());
    test.appendChild(row(null, "", fire, t("VOICE_TEST_HINT")));
    host.appendChild(test);

    paintWordHint();
    paintStatus(window.OCVoice.status());
    if (window.OCSettings) window.OCSettings.bindMasters(host);
    touch();
  }

  /** Kategorie "Diktieren": eigene Seite mit Mikrofon, Sprachmodell und Stand des Modells. */
  function renderDictationPane() {
    const host = dictRoot();
    if (!host || !draft) return;
    host.textContent = "";
    host.appendChild(dictationSection());
    touch();
  }

  /** Diktieren: Mikrofon, Sprachmodell (schnell / genau), Stand des Modells mit Knopf "Jetzt laden". */
  function dictationSection() {
    const box = section(t("DICT_SECTION"), t("DICT_SECTION_HINT"));
    const select = el("select", "ai-wide");
    select.id = "settings-dictation-device";
    const add = (value, text) => { const o = el("option", "", text); o.value = value; select.appendChild(o); };
    add("", t("VOICE_DEVICE_DEFAULT"));
    mics.forEach((m) => add(m.id, m.name + (m.default ? " " + t("VOICE_DEVICE_IS_DEFAULT") : "")));
    if (draft.dictation_device && !mics.some((m) => m.id === draft.dictation_device)) add(draft.dictation_device, t("VOICE_DEVICE_MISSING", { name: draft.dictation_device.replace(/^input:/, "") }));
    select.value = draft.dictation_device || "";
    select.addEventListener("change", () => change({ dictation_device: select.value }));
    box.appendChild(row("dictation_device", t("DICT_DEVICE"), select, t("DICT_DEVICE_HINT")));

    const models = (window.OCDictation && window.OCDictation.status().models) || {};
    const model = el("select", "ai-wide");
    model.id = "settings-dictation-model";
    [["fast", "DICT_MODEL_FAST"], ["accurate", "DICT_MODEL_ACCURATE"]].forEach(([value, key]) => { const o = el("option", "", t(key, { mb: (models[value] || {}).mb || "" })); o.value = value; model.appendChild(o); });
    model.value = draft.dictation_model || "accurate";
    model.addEventListener("change", () => { change({ dictation_model: model.value }); paintModelStatus(); });
    refs.modelStatus = el("p", "ai-row__hint");
    refs.modelButton = el("button", "modal__button", t("DICT_MODEL_DOWNLOAD"));
    refs.modelButton.type = "button";
    refs.modelButton.id = "settings-dictation-download";
    refs.modelButton.addEventListener("click", async () => {
      const d = window.OCDictation;
      if (!d) return;
      const result = await d.download(draft.dictation_model);
      if (!result || !result.ok) { if (typeof _showToast === "function") _showToast(t("DICT_MODEL_FAILED"), "warn", 5000); }
      else if (typeof _showToast === "function") _showToast(t("DICT_MODEL_DONE"), "info", 3000);
      paintModelStatus();
    });
    refs.modelBar = el("div", "dict-progress");
    refs.modelBarFill = el("div", "dict-progress__fill");
    refs.modelBar.appendChild(refs.modelBarFill);
    box.appendChild(row("dictation_model", t("DICT_MODEL"), [model, refs.modelStatus, refs.modelButton, refs.modelBar], t("DICT_MODEL_HINT")));
    paintModelStatus();
    return box;
  }
  function paintModelStatus() {
    if (!refs.modelStatus || !refs.modelStatus.isConnected || !draft) return;
    const d = window.OCDictation;
    const st = d ? d.status() : { models: {}, state: "idle" };
    const info = (st.models || {})[draft.dictation_model || "accurate"] || {};
    const loading = st.state === "downloading";
    refs.modelStatus.textContent = loading ? t("DICT_MODEL_LOADING", { p: Math.round(st.percent || 0) }) : (info.present ? t("DICT_MODEL_STATUS_PRESENT") : t("DICT_MODEL_STATUS_MISSING"));
    refs.modelButton.hidden = !!info.present && !loading;
    refs.modelButton.disabled = loading;
    refs.modelBar.hidden = !loading;
    refs.modelBarFill.style.width = Math.max(2, st.percent || 0) + "%";
  }
  function paintWordHint() {
    const hint = refs.wordHint;
    if (!hint || !hint.isConnected) return;
    hint.classList.remove("voice-hint--bad");
    if (!wordCheck) { hint.textContent = t("VOICE_WORD_HINT_OFF"); return; }
    if (wordCheck.error) { hint.textContent = window.OCVoice.errorText(wordCheck.error); hint.classList.add("voice-hint--bad"); return; }
    if (wordCheck.unknown && wordCheck.unknown.length) {
      hint.textContent = t("VOICE_WORD_UNKNOWN", { words: wordCheck.unknown.join(", ") });
      hint.classList.add("voice-hint--bad");
      return;
    }
    hint.textContent = t("VOICE_WORD_HINT", { phrase: wordCheck.phrase });
  }
  function paintStatus(s) {
    if (!s || !refs.state || !refs.state.isConnected) return;
    const cfg = s.config || {};
    refs.state.className = "voice-status" + (s.error ? " voice-status--bad" : s.running ? " voice-status--ok" : "");
    refs.state.textContent = s.error ? window.OCVoice.errorText(s.error) : s.running ? t("VOICE_STATE_LISTENING", { device: s.device || "" }) : cfg.enabled ? t("VOICE_STATE_STARTING") : t("VOICE_STATE_OFF");
    refs.bar.style.transform = "scaleX(" + Math.max(0, Math.min(1, s.level || 0)) + ")";
    refs.heard.textContent = s.last_heard ? t("VOICE_LAST_HEARD", { text: s.last_heard }) : "";
    const w = s.last_wake;
    refs.woke.textContent = w ? (w.source === "button" ? t("VOICE_LAST_WAKE_BUTTON", { at: w.at }) : w.heard_s ? t("VOICE_LAST_WAKE", { at: w.at, phrase: w.phrase, s: String(w.heard_s).replace(".", ",") }) : t("VOICE_LAST_WAKE_PLAIN", { at: w.at, phrase: w.phrase })) : "";
  }
  /** Pegel und "zuletzt verstanden" live, solange die Seite sichtbar ist. */
  function poll() {
    clearInterval(pollTimer);
    pollTimer = setInterval(() => { if (!visible()) { clearInterval(pollTimer); return; } window.OCVoice.refresh(); }, 300);
  }

  // ---- Speichern / Abbrechen des Einstellungs-Dialogs
  async function commit() {
    const pending = draft && saved && !same({ ...saved, ...draft }, saved) ? { ...draft } : null;
    if (!pending) return;
    try {
      const res = await fetch("/api/voice/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(pending) });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || res.status);
      saved = data.config;
      draft = { ...saved };                    // der Dialog bleibt offen: weiter mit dem frisch gespeicherten Stand
      renderAll();
      window.OCVoice.refresh();
    } catch (err) {
      if (typeof _showToast === "function") _showToast(t("VOICE_SAVE_FAILED"), "error", 4000);
    }
  }

  const register = () => {
    if (window.OCSettings) {
      const PORTABLE = ["enabled", "wake_word", "sensitivity", "dictation_model"];                  // ohne Mikrofone (rechnerbezogen)
      const exportData = async () => { if (!saved) await load(false); return saved ? Object.fromEntries(PORTABLE.filter((k) => k in saved).map((k) => [k, saved[k]])) : null; };
      const importData = async (data) => {
        if (!data || typeof data !== "object") return;
        if (!draft) await load(false);
        if (!draft) return;
        PORTABLE.forEach((key) => { if (key in data && typeof data[key] === typeof DEFAULTS[key]) draft[key] = data[key]; });
        renderAll();
        checkWord();
      };
      window.OCSettings.register({ id: "voice", category: "voice", changes: changesOf(WAKE_KEYS, "voice"), reset: resetOf(WAKE_KEYS), exportData, importData });
      window.OCSettings.register({ id: "dictation", category: "dictation", changes: changesOf(DICT_KEYS, "dictation"), reset: resetOf(DICT_KEYS) });
    } else setTimeout(register, 50);
  };
  register();
  window.OCVoice.subscribe(paintStatus);
  window.OCVoice.subscribe((s) => {                                    // der Mikrofon-Schalter in der Menueleiste wurde benutzt: die Einstellungen folgen (nur wenn dort "An" nicht selbst geaendert ist)
    const enabled = !!(s && s.config && s.config.enabled);
    if (!saved || saved.enabled === enabled) return;
    if (draft && draft.enabled === saved.enabled) draft.enabled = enabled;
    saved.enabled = enabled;
    if (draft && (visible() || dictVisible())) renderAll();
  });
  if (window.OCDictation) window.OCDictation.subscribe(paintModelStatus);
  document.addEventListener("settings-opened", () => { draft = null; });
  document.addEventListener("settings-cancelled", () => { draft = null; });
  document.addEventListener("settings-saved", commit);
  document.addEventListener("settings-category-shown", (e) => { if (e.detail && (e.detail.category === "voice" || e.detail.category === "dictation")) load(true); });
  document.addEventListener("i18n-applied", () => { if (visible() || dictVisible()) renderAll(); });
})();
