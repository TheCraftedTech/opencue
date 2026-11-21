// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Einstellungen -> Kategorie "KI-Assistent" (Server: app/ai/routes.py, nur an der Konsole selbst).
 * Wie alle Einstellungen arbeitet die Seite mit einem ENTWURF: jede Aenderung ist nur markiert (settings_tracker.js zaehlt sie und bietet den Zurueck-Pfeil je Zeile), erst
 * "Speichern" schickt die Aenderungen an den Server (Ereignis "settings-saved"), "Abbrechen" verwirft sie ("settings-cancelled"). "Verbindung testen" und "Liste aktualisieren"
 * benutzen die Adresse und den Schluessel aus dem Entwurf, ohne sie zu speichern. Aendert sich draussen etwas (z. B. "Immer erlauben" im Chat), wird es uebernommen, soweit
 * die Zeile nicht gerade selbst geaendert ist. */
(function () {
  "use strict";
  const t = (key, fallback) => { try { const v = typeof i18n === "function" ? i18n(key) : ""; return v && v !== key ? v : fallback; } catch (err) { return fallback; } };
  const SIMPLE = ["enabled", "default_mode", "base_url", "model", "auto_title", "tools_mode", "num_ctx", "temperature", "num_predict", "timeout_s"];
  const NUMBERS = new Set(["num_ctx", "temperature", "num_predict", "timeout_s"]);
  const PERMS = ["read", "write", "critical"];
  let saved = null;                        // so steht es auf dem Server (GET /api/ai/config)
  let draft = null;                        // der Entwurf dieser Sitzung des Dialogs (null = noch nicht geladen / verworfen)
  let newKey = null;                       // neuer Zugangsschluessel (null = unveraendert, "" = loeschen)
  let removed = new Set();                 // "Immer erlaubt"-Funktionen, die mit "Speichern" entfernt werden
  let toolList = [];                       // alle Funktionen mit ihrer Klasse (/api/ai/tools): damit die Einstellungen zeigen, was zu welcher Klasse gehoert
  let models = [];
  let modelsNote = "";
  let advancedOpen = false;
  const rowOf = {};                        // Schluessel -> Zeile (fuer die Markierung geaenderter Zeilen)

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  const root = () => document.getElementById("settings-ai-root");
  const toast = (message, type) => { if (typeof _showToast === "function") _showToast(message, type || "info", 3500); };
  const touch = () => { if (window.OCSettings) window.OCSettings.touch(); };
  const num = (v) => (v === "" || v === null || v === undefined ? NaN : Number(v));
  const same = (key, a, b) => (NUMBERS.has(key) ? num(a) === num(b) : a === b);

  async function api(method, path, body) {
    const res = await fetch(path, { method, cache: "no-store", headers: body !== undefined ? { "Content-Type": "application/json" } : {}, body: body !== undefined ? JSON.stringify(body) : undefined });
    let json = null;
    try { json = await res.json(); } catch (err) { /* keine JSON-Antwort */ }
    if (!res.ok) throw new Error((json && json.error && json.error.message) || ("HTTP " + res.status));
    return json;
  }

  // ------------------------------------------------------------------------------------------ Entwurf
  function change(patch) { Object.assign(draft, patch); touch(); }
  const setPerm = (kind, value) => { draft.permissions = { ...draft.permissions, [kind]: value }; touch(); };

  /** Kopie der gespeicherten Werte als Entwurf. */
  function fresh() {
    draft = {};
    SIMPLE.forEach((k) => { draft[k] = saved[k]; });
    draft.permissions = { ...(saved.permissions || {}) };
    newKey = null;
    removed = new Set();
  }

  /** Die Zeilen, die vom Gespeicherten abweichen (settings_tracker.js). Jede nimmt mit ihrem Pfeil nur sich selbst zurueck. */
  function changes() {
    if (!saved || !draft) return [];
    const out = [];
    const add = (key, label, revert) => { if (rowOf[key] && rowOf[key].isConnected) out.push({ key: "ai:" + key, label, row: rowOf[key], revert: () => { revert(); render(); } }); };
    SIMPLE.forEach((key) => { if (!same(key, draft[key], saved[key])) add(key, t(LABELS[key], key), () => { draft[key] = saved[key]; }); });
    PERMS.forEach((kind) => { if ((draft.permissions || {})[kind] !== (saved.permissions || {})[kind]) add("perm-" + kind, t("AI_PERM_" + kind.toUpperCase(), kind), () => { draft.permissions[kind] = saved.permissions[kind]; }); });
    if (newKey !== null && (newKey !== "" || saved.has_key)) add("api_key", t("AI_KEY", "Access key"), () => { newKey = null; });
    removed.forEach((name) => add("tool-" + name, name, () => { removed.delete(name); }));
    return out;
  }
  const LABELS = { enabled: "AI_ENABLE", default_mode: "AI_DEFAULT_MODE", base_url: "AI_URL", model: "AI_MODEL_DEFAULT_LABEL", auto_title: "AI_AUTO_TITLE", tools_mode: "AI_TOOLS_MODE",
    num_ctx: "AI_NUM_CTX", temperature: "AI_TEMPERATURE", num_predict: "AI_NUM_PREDICT", timeout_s: "AI_TIMEOUT" };

  /** Kategorie zuruecksetzen: die Standardwerte werden Entwurf (der Zugangsschluessel wird geleert, "Immer erlaubt" faellt weg). */
  async function reset() {
    if (!draft) {                                   // Seite noch nie geoeffnet (z. B. "Alles zuruecksetzen"): erst den gespeicherten Stand holen
      if (!(await loadSaved())) return;
      fresh();
    }
    if (!saved || !draft) return;
    const d = saved.defaults || {};
    SIMPLE.forEach((k) => { if (k in d) draft[k] = d[k]; });
    draft.permissions = { ...(d.permissions || {}) };
    newKey = saved.has_key ? "" : null;
    removed = new Set(saved.allowed_tools || []);
    render();
  }

  /** "Empfohlene Werte" (Kontext, Temperatur, Antwortgrenze, Wartezeit, Denkschritte, Chat-Namen, Funktionsliste) als Entwurf. */
  function recommended() {
    Object.assign(draft, saved.recommended || {});
    toast(t("AI_RECOMMENDED_DONE", "The recommended values are set - press Save to apply."));
    render();
  }

  async function commit() {
    const wasDraft = draft;
    if (!saved || !wasDraft) return;
    const patch = {};
    SIMPLE.forEach((k) => { if (!same(k, wasDraft[k], saved[k])) patch[k] = NUMBERS.has(k) ? num(wasDraft[k]) : wasDraft[k]; });
    if (PERMS.some((k) => (wasDraft.permissions || {})[k] !== (saved.permissions || {})[k])) patch.permissions = { ...wasDraft.permissions };
    if (newKey !== null && (newKey !== "" || saved.has_key)) patch.api_key = newKey;
    if (removed.size) patch.allowed_tools = (saved.allowed_tools || []).filter((n) => !removed.has(n));
    if (!Object.keys(patch).length) return;
    try {
      saved = await api("POST", "/api/ai/config", patch);
      fresh();                                    // der Dialog bleibt offen: weiter mit dem frisch gespeicherten Stand
      render();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  // ------------------------------------------------------------------------------------------ Server
  async function loadSaved() {
    try { saved = await api("GET", "/api/ai/config"); } catch (err) { return false; }
    try { toolList = [].concat(...((await api("GET", "/api/ai/tools")).collections || []).map((c) => c.tools)); } catch (err) { toolList = []; }
    return true;
  }

  /** Modelle des Servers aus dem ENTWURF (Adresse, Schluessel), ohne zu speichern. Gibt {ok, version, models, error} zurueck. */
  async function probe() {
    const body = { base_url: draft ? draft.base_url : saved.base_url };
    if (newKey !== null) body.api_key = newKey;
    try { return await api("POST", "/api/ai/test", body); } catch (err) { return { ok: false, error: { message: err.message }, models: [] }; }
  }
  async function loadModels() {
    modelsNote = "";
    const data = await probe();
    models = data.models || [];
    if (!data.ok) modelsNote = (data.error && data.error.message) || "";
  }

  async function show() {
    if (!draft) {
      if (!(await loadSaved())) return;
      fresh();
    }
    render();
    if (draft.enabled) {
      await loadModels();
      const select = document.getElementById("settings-ai-model");
      if (select) fillModelSelect(select, draft.model);
      const note = document.querySelector("#settings-ai-root .ai-row__hint--note");
      if (note) note.textContent = modelsHintText();
    }
  }

  /** Aenderung von draussen (z. B. "Immer erlauben" im Chat): uebernehmen, soweit die Zeile nicht selbst geaendert ist. */
  async function followServer() {
    if (!saved || !draft || !root() || !root().isConnected) return;
    const old = saved;
    let next;
    try { next = await api("GET", "/api/ai/config"); } catch (err) { return; }
    if (JSON.stringify([old.allowed_tools, old.permissions, old.enabled, old.tools_mode, old.default_mode]) === JSON.stringify([next.allowed_tools, next.permissions, next.enabled, next.tools_mode, next.default_mode])) return;
    saved = next;
    SIMPLE.forEach((k) => { if (same(k, draft[k], old[k])) draft[k] = next[k]; });
    PERMS.forEach((k) => { if ((draft.permissions || {})[k] === (old.permissions || {})[k]) draft.permissions[k] = (next.permissions || {})[k]; });
    removed = new Set([...removed].filter((n) => (next.allowed_tools || []).includes(n)));
    render();
  }

  // ------------------------------------------------------------------------------------------ Bausteine
  function formatSize(bytes) {
    if (!bytes) return "";
    const gb = bytes / 1e9;
    return gb >= 1 ? gb.toFixed(1) + " GB" : Math.round(bytes / 1e6) + " MB";
  }
  function modelLabel(m) {
    const extra = [m.parameters, formatSize(m.size)].filter(Boolean).join(", ");
    return m.name + (extra ? " (" + extra + ")" : "");
  }
  /** Auswahl der Modelle. `value` bleibt auch dann waehlbar, wenn der Server das Modell nicht (mehr) kennt. */
  function fillModelSelect(select, value) {
    select.textContent = "";
    if (!value || !models.some((m) => m.name === value)) { const o = el("option", "", t("AI_MODEL_NONE", "- choose a model -")); o.value = ""; select.appendChild(o); }
    models.forEach((m) => { const o = el("option", "", modelLabel(m)); o.value = m.name; select.appendChild(o); });
    if (value && !models.some((m) => m.name === value)) { const o = el("option", "", value + " (" + t("AI_MODEL_MISSING", "not available") + ")"); o.value = value; select.appendChild(o); }
    select.value = value || "";
  }
  function modelsHintText() {
    if (modelsNote) return modelsNote;
    return models.length ? "" : t("AI_NO_MODELS", "The server has no models yet. Install one with: ollama pull <name>");
  }

  function section(title) {
    const box = el("div", "settings-section");
    box.appendChild(el("div", "settings-section__title", title));
    return box;
  }
  /** Eine Zeile: links die Beschriftung, rechts das Bedienelement mit dem Hinweis darunter; `key` verbindet sie mit der Markierung geaenderter Zeilen. */
  /** Hauptschalter: grosse Zeile ganz oben (wie bei Fernzugriff und REST-API), Hinweis darunter. */
  function masterRow(key, label, control, hint) {
    const wrap = el("div", "settings-field settings-master");
    wrap.append(el("label", "", label), control);
    if (key) rowOf[key] = wrap;
    return [wrap, hint ? el("p", "settings-field-hint settings-keep", hint) : null].filter(Boolean);
  }
  function row(key, label, control, hint) {
    const wrap = el("div", "ai-row");
    const left = el("label", "ai-row__label");
    left.appendChild(el("span", "ai-row__name", label));
    const right = el("div", "ai-row__control");
    (Array.isArray(control) ? control : [control]).forEach((node) => right.appendChild(node));
    if (hint) right.appendChild(typeof hint === "string" ? el("p", "ai-row__hint", hint) : hint);
    wrap.append(left, right);
    if (key) rowOf[key] = wrap;
    return wrap;
  }
  function toggle(checked, onChange) {
    const label = el("label", "toggle-switch");
    const input = el("input");
    input.type = "checkbox";
    input.checked = checked;
    input.addEventListener("change", () => onChange(input.checked));
    label.append(input, el("span", "toggle-switch__track"));
    return label;
  }
  function numberInput(value, min, max, step, onChange) {
    const input = el("input", "ai-num");
    input.type = "number";
    input.min = String(min); input.max = String(max); input.step = String(step);
    input.value = String(value);
    input.addEventListener("input", () => onChange(input.value));
    return input;
  }
  function select(id, options, value, onChange) {
    const node = el("select", "ai-wide");
    node.id = id;
    options.forEach(([v, text]) => node.appendChild(Object.assign(el("option", "", text), { value: v })));
    node.value = value;
    node.addEventListener("change", () => onChange(node.value));
    return node;
  }

  // ------------------------------------------------------------------------------------------ Seite
  function render() {
    const host = root();
    if (!host || !saved || !draft) return;
    host.textContent = "";
    Object.keys(rowOf).forEach((k) => delete rowOf[k]);
    const rec = (key) => (saved.recommended && saved.recommended[key] !== undefined ? " " + t("AI_RECOMMENDED", "Recommended: {v}.").replace("{v}", String(saved.recommended[key])) : "");

    // ---- Hauptschalter: aus = der Rest der Seite ist gesperrt
    const general = el("div", "settings-section");
    general.dataset.masterScope = "page";
    masterRow("enabled", t("AI_ENABLE", "Enable the AI assistant"), toggle(!!draft.enabled, (on) => change({ enabled: on })), t("AI_ENABLE_HINT", "Off until you switch it on. OpenCue only talks to the server below.")).forEach((node) => general.appendChild(node));
    host.appendChild(general);

    // ---- Verbindung (Adresse, Schluessel, Modell)
    const connection = section(t("AI_SECTION_CONNECTION", "Connection"));
    const url = el("input", "ai-wide");
    url.type = "text"; url.id = "settings-ai-url"; url.maxLength = 200; url.value = draft.base_url; url.placeholder = "http://127.0.0.1:11434"; url.spellcheck = false;
    url.addEventListener("input", () => change({ base_url: url.value.trim() }));
    connection.appendChild(row("base_url", t("AI_URL", "Server address"), url));
    const key = el("input", "ai-wide");
    key.type = "password"; key.id = "settings-ai-key"; key.maxLength = 300; key.autocomplete = "off";
    key.placeholder = saved.has_key ? t("AI_KEY_SET", "(a key is saved - type a new one to replace it)") : t("AI_KEY_PH", "optional");
    key.value = newKey || "";
    key.addEventListener("input", () => { newKey = key.value.trim(); touch(); });
    connection.appendChild(row("api_key", t("AI_KEY", "Access key"), key));
    const status = el("div", "ai-status");
    status.id = "settings-ai-status";
    const test = el("button", "modal__button", t("AI_TEST", "Test connection"));
    test.type = "button"; test.id = "settings-ai-test";
    const testBox = el("div", "ai-test");
    testBox.append(test, status);
    connection.appendChild(row(null, "", testBox));
    const modelSelect = el("select", "ai-wide");
    modelSelect.id = "settings-ai-model";
    fillModelSelect(modelSelect, draft.model);
    modelSelect.addEventListener("change", () => change({ model: modelSelect.value }));
    const refresh = el("button", "modal__button", t("AI_REFRESH", "Refresh list"));
    refresh.type = "button";
    const modelsHint = el("p", "ai-row__hint ai-row__hint--note", modelsHintText());
    connection.appendChild(row("model", t("AI_MODEL_DEFAULT_LABEL", "Default model"), [modelSelect, refresh, modelsHint]));
    host.appendChild(connection);
    test.addEventListener("click", async () => {
      status.className = "ai-status";
      status.textContent = t("AI_TESTING", "Testing ...");
      const data = await probe();
      if (data.ok) {
        models = data.models || [];
        modelsNote = "";
        status.className = "ai-status ai-status--ok";
        status.textContent = "✓ " + t("AI_TEST_OK", "Connected - Ollama {v}, {n} model(s)").replace("{v}", data.version || "?").replace("{n}", String(models.length));
        fillModelSelect(modelSelect, draft.model);
        modelsHint.textContent = modelsHintText();
      } else {
        status.className = "ai-status ai-status--bad";
        status.textContent = "✗ " + ((data.error && data.error.message) || t("AI_TEST_FAILED", "Connection failed"));
      }
    });
    refresh.addEventListener("click", async () => {
      await loadModels();
      fillModelSelect(modelSelect, draft.model);
      modelsHint.textContent = modelsHintText();
    });

    // ---- Verhalten
    const work = section(t("AI_SECTION_BEHAVIOUR", "Behaviour"));
    work.appendChild(row("default_mode", t("AI_DEFAULT_MODE", "Mode of new chats"),
      select("settings-ai-default-mode", [["chat", t("AIP_MODE_CHAT", "Chat")], ["guide", t("AIP_MODE_GUIDE", "Guide")], ["work", t("AIP_MODE_WORK", "Work")]], draft.default_mode || "chat", (v) => change({ default_mode: v }))));
    work.appendChild(row("auto_title", t("AI_AUTO_TITLE", "Name chats automatically"), toggle(draft.auto_title !== false, (on) => change({ auto_title: on }))));
    work.appendChild(row("tools_mode", t("AI_TOOLS_MODE", "Function list"),
      select("settings-ai-tools-mode", [["core", t("AI_TOOLS_CORE", "Common ones at once, the rest on demand (recommended)")], ["collections", t("AI_TOOLS_COLLECTIONS", "Everything on demand")], ["all", t("AI_TOOLS_ALL", "All at once (large models only)")]],
        ["core", "collections", "all"].includes(draft.tools_mode) ? draft.tools_mode : "core", (v) => change({ tools_mode: v }))));
    host.appendChild(work);

    // ---- Berechtigungen: was darf die KI allein, wann fragt sie
    const perms = section(t("AI_SECTION_PERMS", "Permissions"));
    const kinds = [["read", t("AI_PERM_READ", "Read functions"), t("AI_PERM_READ_HINT", "Only look at the show.")],
      ["write", t("AI_PERM_WRITE", "Write functions"), t("AI_PERM_WRITE_HINT", "Change the show.")],
      ["critical", t("AI_PERM_CRITICAL", "Critical functions"), t("AI_PERM_CRITICAL_HINT", "Far-reaching, e.g. command line, deleting, loading a show.")]];
    kinds.forEach(([kind, label, hintText]) => {
      const choice = select("settings-ai-perm-" + kind, [["allow", t("AI_PERM_ALLOW", "Always allow")], ["ask", t("AI_PERM_ASK", "Ask every time")], ["never", t("AI_PERM_NEVER", "Never allow")]],
        (draft.permissions || {})[kind] || (kind === "read" ? "allow" : "ask"), (v) => setPerm(kind, v));
      const names = toolList.filter((tool) => tool.access === kind).map((tool) => tool.name);
      const note = el("div", "ai-row__note");
      note.appendChild(el("p", "ai-row__hint", hintText));
      if (names.length) {
        const funcs = el("details", "ai-funcs");
        funcs.append(el("summary", "", t("AI_PERM_FUNCS_N", "{n} functions").replace("{n}", String(names.length))), el("p", "ai-row__hint", names.join(", ")));
        note.appendChild(funcs);
      }
      perms.appendChild(row("perm-" + kind, label, choice, note));
    });
    host.appendChild(perms);

    const allowed = section(t("AI_SECTION_ALLOWED", "Always allowed functions"));
    const names = Array.isArray(saved.allowed_tools) ? saved.allowed_tools : [];
    if (!names.length) allowed.appendChild(el("p", "ai-row__hint", t("AI_ALLOWED_NONE", "None yet.")));
    const list = el("div", "ai-allowed");
    list.id = "settings-ai-allowed";
    names.forEach((name) => {
      const item = el("div", "ai-allowed__item" + (removed.has(name) ? " ai-allowed__item--removed" : ""));
      item.dataset.tool = name;
      item.appendChild(el("code", "ai-allowed__name", name));
      if (removed.has(name)) item.appendChild(el("span", "ai-allowed__note", t("AI_ALLOWED_REMOVING", "is removed when you save")));
      else {
        const remove = el("button", "modal__button", t("AI_ALLOWED_REMOVE", "Remove"));
        remove.type = "button";
        remove.addEventListener("click", () => { removed.add(name); touch(); render(); });
        item.appendChild(remove);
      }
      rowOf["tool-" + name] = item;
      list.appendChild(item);
    });
    allowed.appendChild(list);
    host.appendChild(allowed);

    // ---- Erweitert (eingeklappt)
    const advanced = el("details", "ai-advanced");
    advanced.open = advancedOpen;
    advanced.addEventListener("toggle", () => { advancedOpen = advanced.open; });
    advanced.appendChild(el("summary", "ai-advanced__summary", t("AI_SECTION_ADVANCED", "Advanced (context, temperature, waiting time)")));
    const params = el("div", "ai-advanced__body");
    params.appendChild(row("num_ctx", t("AI_NUM_CTX", "Context size (tokens)"), numberInput(draft.num_ctx, 1024, 131072, 1024, (v) => change({ num_ctx: v })),
      t("AI_NUM_CTX_HINT", "How much the model reads at once.") + rec("num_ctx")));
    params.appendChild(row("temperature", t("AI_TEMPERATURE", "Temperature"), numberInput(draft.temperature, 0, 2, 0.1, (v) => change({ temperature: v })),
      t("AI_TEMPERATURE_HINT", "Low = precise, high = more varied.") + rec("temperature")));
    params.appendChild(row("num_predict", t("AI_NUM_PREDICT", "Longest answer (tokens)"), numberInput(draft.num_predict, 64, 16384, 100, (v) => change({ num_predict: v })),
      t("AI_NUM_PREDICT_HINT", "Longest answer; the model stops after this.") + rec("num_predict")));
    params.appendChild(row("timeout_s", t("AI_TIMEOUT", "Waiting time (seconds)"), numberInput(draft.timeout_s, 10, 3600, 10, (v) => change({ timeout_s: v })),
      t("AI_TIMEOUT_HINT", "How long OpenCue waits for an answer.") + rec("timeout_s")));
    const recButton = el("button", "modal__button", t("AI_RECOMMENDED_RESET", "Set recommended values"));
    recButton.type = "button"; recButton.id = "settings-ai-recommended";
    recButton.addEventListener("click", recommended);
    params.appendChild(row(null, "", recButton, t("AI_RECOMMENDED_HINT", "Context, temperature, answer length, waiting time, chat names and function list. Address, model and permissions stay.")));
    advanced.appendChild(params);
    host.appendChild(advanced);
    if (window.OCSettings) window.OCSettings.bindMasters(host);
    touch();
  }

  function bind() {
    document.addEventListener("settings-category-shown", (e) => { if (e.detail && e.detail.category === "ai") show(); });
    document.addEventListener("settings-opened", () => { draft = null; saved = null; newKey = null; removed = new Set(); });
    document.addEventListener("settings-cancelled", () => { draft = null; saved = null; newKey = null; removed = new Set(); });
    document.addEventListener("settings-saved", commit);
    document.addEventListener("ai-state-changed", followServer);
    document.addEventListener("i18n-applied", () => { if (draft && root() && root().childElementCount) render(); });
    /** Export / Import (Einstellungen sichern): Server, Modell, Verhalten, Berechtigungen - OHNE Zugangsschluessel. */
    const exportData = async () => {
      if (!saved && !(await loadSaved())) return null;
      const out = {};
      SIMPLE.forEach((k) => { out[k] = saved[k]; });
      out.permissions = { ...(saved.permissions || {}) };
      return out;
    };
    const importData = async (data) => {
      if (!data || typeof data !== "object") return;
      if (!draft) { if (!(await loadSaved())) return; fresh(); }
      SIMPLE.forEach((k) => { if (k in data && ["string", "number", "boolean"].includes(typeof data[k])) draft[k] = data[k]; });
      if (data.permissions && typeof data.permissions === "object") PERMS.forEach((kind) => { if (typeof data.permissions[kind] === "string") draft.permissions = { ...draft.permissions, [kind]: data.permissions[kind] }; });
      render();
      touch();
    };
    const register = () => { if (window.OCSettings) window.OCSettings.register({ id: "ai", category: "ai", changes, reset, exportData, importData }); else setTimeout(register, 50); };
    register();
  }

  bind();
  window.OCAiSettings = { refresh: show, fillModelSelect, models: () => models, loadModels };
})();
