// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Panel "Assistent": Chat mit dem lokalen Sprachmodell (app/ai/). Die Gespraeche liegen als Dateien im Datenordner und sind voneinander unabhaengig; jedes Panel auf
 * jedem Geraet zeigt dieselben Chats. Senden / Stopp laufen ueber den WebSocket (ai_send, ai_stop), die gestreamte Antwort kommt als Ereignis ai_event; Chat-Verwaltung,
 * Modelle und Einstellungen ueber /api/ai. Unten links waehlt ein Knopf den Modus (Chat / Wegweiser / Arbeiten); der Modus gehoert zum Chat und kann jederzeit
 * gewechselt werden. Der Text im Verlauf ist markier- und kopierbar. Der erste Chat entsteht von selbst beim ersten Senden. Laeuft nach app.js. */
(function () {
  "use strict";

  const t = (key, fallback) => { try { const v = typeof i18n === "function" ? i18n(key) : ""; return v && v !== key ? v : (fallback !== undefined ? fallback : key); } catch (err) { return fallback !== undefined ? fallback : key; } };
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  // Die Modi (Reihenfolge = Reihenfolge im Menue). `ready` kommt vom Server (/api/ai/modes); bis dahin gilt dieser Stand.
  const MODES = [
    { id: "chat", icon: "chat", ready: true, name: ["AIP_MODE_CHAT", "Chat"], desc: ["AIP_MODE_CHAT_DESC", "Normal conversation with the AI."] },
    { id: "guide", icon: "signpost", ready: false, name: ["AIP_MODE_GUIDE", "Guide"], desc: ["AIP_MODE_GUIDE_DESC", "Shows you where something is in the program."] },
    { id: "work", icon: "fixture", ready: true, name: ["AIP_MODE_WORK", "Work"], desc: ["AIP_MODE_WORK_DESC", "The AI works for you with functions."] },
  ];
  const modeById = (id) => MODES.find((m) => m.id === id) || MODES[0];

  // ------------------------------------------------------------------------------------------ gemeinsamer Zustand (alle Panels)
  const S = { enabled: false, model: "", chats: [], cache: {}, live: {}, running: new Set(), models: [], modelsLoaded: false, loaded: false, open: new Set(), defaultMode: "chat", asks: {}, seenManual: new Set(), tools: null, targets: null };      // open: aufgeklappte Funktionsbloecke / -zeilen (ueberlebt das Neuzeichnen)
  const views = new Set();

  async function api(method, path, body) {
    const res = await fetch(path, { method, cache: "no-store", headers: body !== undefined ? { "Content-Type": "application/json" } : {}, body: body !== undefined ? JSON.stringify(body) : undefined });
    let json = null;
    try { json = await res.json(); } catch (err) { /* keine JSON-Antwort */ }
    if (!res.ok) throw new Error((json && json.error && json.error.message) || ("HTTP " + res.status));
    return json;
  }

  const each = (fn) => {
    [...views].forEach((v) => { if (v.root.isConnected) { v.seen = true; fn(v); } else if (v.seen) views.delete(v); });
  };

  async function copyText(text) {
    let ok = false;
    try { ok = typeof _copyText === "function" ? await _copyText(text) : (await navigator.clipboard.writeText(text), true); } catch (err) { ok = false; }
    if (typeof _showToast === "function") _showToast(t(ok ? "AIP_COPIED" : "AIP_COPY_FAILED", ok ? "Copied" : "Copying is not possible"), ok ? "info" : "error", 2000);
    return ok;
  }

  async function loadAll() {
    try {
      const [st, chats, modes] = await Promise.all([api("GET", "/api/ai/state"), api("GET", "/api/ai/chats"), api("GET", "/api/ai/modes").catch(() => null)]);
      S.enabled = !!st.enabled; S.model = st.model || ""; S.defaultMode = st.default_mode || "chat";
      S.chats = chats.chats || [];
      (chats.running || []).forEach((id) => S.running.add(id));
      if (modes && modes.modes) modes.modes.forEach((m) => { const known = MODES.find((x) => x.id === m.id); if (known) known.ready = !!m.ready; });
    } catch (err) { /* offline: leere Liste */ }
    S.loaded = true;
    each((v) => v.renderAll());
  }

  async function loadModels(force) {
    if (S.modelsLoaded && !force) return;
    try { S.models = (await api("GET", "/api/ai/models")).models || []; } catch (err) { S.models = []; }
    S.modelsLoaded = true;
    each((v) => v.renderHeader());
  }

  async function loadChat(id) {
    if (S.cache[id]) return S.cache[id];
    const chat = await api("GET", "/api/ai/chats/" + id);
    S.cache[id] = chat;
    if (chat.running) S.running.add(id);
    (chat.pending || []).forEach((p) => { S.asks[p.call_id] = { chatId: id, name: p.name, arguments: p.arguments, access: p.access }; });          // offene Rueckfragen "darf die KI das?"
    return chat;
  }

  function touchList(chatId, patch) {
    const entry = S.chats.find((c) => c.id === chatId);
    if (entry) Object.assign(entry, patch);
    else S.chats.unshift(Object.assign({ id: chatId, title: "", model: "", mode: "chat", messages: 0, updated: Date.now() / 1000 }, patch));
    S.chats.sort((a, b) => (b.updated || 0) - (a.updated || 0));
  }

  /** Offene Rueckfragen eines Chats vergessen (der Lauf ist zu Ende, gestoppt oder fehlgeschlagen). */
  function clearAsks(chatId) {
    Object.keys(S.asks).forEach((k) => { if (S.asks[k].chatId === chatId) delete S.asks[k]; });
  }

  /** Wird der Chat in einem sichtbaren Panel gezeigt? Dann ist eine fertige Antwort gleich "gesehen". */
  const isShown = (id) => document.visibilityState !== "hidden" && [...views].some((v) => v.chatId === id && v.root.isConnected);

  /** Eine neue Antwort wurde gesehen: der gelbe Punkt in der Chat-Liste verschwindet (hier sofort, auf den anderen Geraeten ueber den Server). */
  function markSeen(id) {
    const entry = S.chats.find((c) => c.id === id);
    if (!entry || !entry.unread) return;
    entry.unread = false;
    each((v) => v.renderList());
    api("POST", "/api/ai/chats/" + id + "/seen").catch(() => null);
  }
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") views.forEach((v) => { if (v.chatId && v.root.isConnected) markSeen(v.chatId); }); });

  // ------------------------------------------------------------------------------------------ Wegweiser: Schaltflaechen, die Dialoge oeffnen
  /** Dialoge, die der Wegweiser anbieten darf (Id -> was die Schaltflaeche ausloest); vom Server, in der Sprache der Oberflaeche. */
  async function ensureTargets() {
    if (S.targets) return S.targets;
    try { S.targets = (await api("GET", "/api/ai/ui-targets")).targets || []; } catch (err) { S.targets = []; }
    return S.targets;
  }
  document.addEventListener("i18n-applied", () => { S.targets = null; });

  /** Oeffnet einen Dialog des Programms genau wie der Menuepunkt: der Klick ist derselbe, nichts wird gespeichert oder geloescht. */
  async function openUi(id) {
    const target = (await ensureTargets()).find((x) => x.id === id);
    const click = (target && target.click) || {};
    const find = () => {
      if (click.action === "open-settings-modal") return document.querySelector('.menubar__icon-button[data-action="open-settings-modal"]');
      return document.querySelector('[data-action="' + click.action + '"]' + (click.fm_kind ? '[data-fm-kind="' + click.fm_kind + '"]' : ""));
    };
    const node = target ? find() : null;
    if (!node) { if (typeof _showToast === "function") _showToast(t("AIP_UI_MISSING", "This is not available here."), "error", 3000); return; }
    const press = () => {
      if (click.category) node.dataset.settingsCategory = click.category;
      node.click();
      if (click.category) delete node.dataset.settingsCategory;
    };
    if (click.needs === "edit-mode" && !document.querySelector(".edit-mode")) {            // das Menue "Panel hinzufuegen" geht nur im Bearbeitungsmodus
      const toggle = document.querySelector('[data-action="toggle-edit-mode"]');
      if (toggle) { toggle.click(); setTimeout(press, 250); return; }
    }
    press();
  }

  /** Die Schaltflaechen, die die KI in dieser Frage ueber show_dialog angeboten hat (einmal je Ziel). */
  function turnActions(turn) {
    const out = [];
    const seen = new Set();
    turn.rounds.forEach((round) => round.tools.forEach((tool) => {
      if (tool.tool_name !== "show_dialog" || tool.ok !== true || !tool.content) return;
      let data = null;
      try { data = JSON.parse(tool.content); } catch (err) { return; }
      const b = data && data.button;
      if (b && b.target && !seen.has(b.target)) { seen.add(b.target); out.push(b); }
    }));
    return out;
  }

  function actionRow(actions) {
    const row = el("div", "aip__actions");
    actions.forEach((b) => {
      const button = el("button", "modal__button aip__action", (b.kind === "toggle" ? t("AIP_SWITCH_UI", "Switch") : t("AIP_OPEN_UI", "Open")) + ": " + b.label);
      button.type = "button";
      button.dataset.target = b.target;
      button.addEventListener("click", () => openUi(b.target));
      row.appendChild(button);
    });
    return row;
  }

  // ------------------------------------------------------------------------------------------ Ereignisse vom Server
  function onEvent(ev) {
    const id = ev.chat_id;
    const chat = S.cache[id];
    const live = S.live[id];
    const redraw = (fn) => each((v) => { if (v.chatId === id) fn(v); });
    switch (ev.type) {
      case "chat":
        touchList(id, { title: ev.title, model: ev.model, mode: ev.mode, updated: Date.now() / 1000 });
        if (chat) { chat.title = ev.title; chat.model = ev.model; chat.mode = ev.mode; }
        each((v) => { v.renderList(); if (v.chatId === id) v.renderHeader(); });
        return;
      case "user":
        S.running.add(id);
        if (chat) chat.messages.push({ role: "user", content: ev.text, ts: Date.now() / 1000, manual: !!ev.manual });
        redraw((v) => { v.renderMessages(); v.renderInput(); });
        each((v) => v.renderList());                                                  // in der Liste beginnt der Chat zu "schreiben" (Animation)
        return;
      case "start":
        S.live[id] = { text: "", thinking: "", model: ev.model, mode: ev.mode };
        redraw((v) => { v.thinkOpen = null; v.renderLive(true); v.renderInput(); });
        return;
      case "thinking":
        if (live) { if (!live.thinkFrom) live.thinkFrom = Date.now(); live.thinking += ev.text; redraw((v) => v.scheduleLive()); }
        return;
      case "token":
        if (live) { if (live.thinkFrom && !live.thinkMs) live.thinkMs = Date.now() - live.thinkFrom; live.text += ev.text; redraw((v) => v.scheduleLive()); }
        return;
      case "warning":
        if (chat) chat.messages.push({ role: "notice", content: WARNINGS[ev.code] ? t(WARNINGS[ev.code][0], WARNINGS[ev.code][1]) : (ev.message || ""), ts: Date.now() / 1000 });
        redraw((v) => v.renderMessages());
        return;
      case "assistant_done":
        if (chat) {
          const msg = { role: "assistant", content: ev.content !== undefined ? ev.content : (live ? live.text : ""), ts: Date.now() / 1000, stats: ev.stats, thinking: ev.thinking || "", model: live ? live.model : "", mode: live ? live.mode : "" };
          if (ev.has_calls) msg.tool_calls = ev.tool_calls || [];
          if (ev.manual) msg.manual = true;                                      // vom Benutzer von Hand aufgerufen (/name ...): keine Antwort der KI
          chat.messages.push(msg);
        }
        delete S.live[id];
        redraw((v) => v.renderMessages());
        return;
      case "tool_call":
        if (chat && !chat.messages.some((m) => m.role === "tool" && m.call_id === ev.call_id)) chat.messages.push({ role: "tool", call_id: ev.call_id, tool_name: ev.name, arguments: ev.arguments, content: "", ok: null, ms: null });
        redraw((v) => v.renderMessages());
        return;
      case "tool_ask":
        S.asks[ev.call_id] = { chatId: id, name: ev.name, arguments: ev.arguments, access: ev.access };
        redraw((v) => v.renderMessages());
        return;
      case "tool_answer":
        delete S.asks[ev.call_id];
        redraw((v) => v.renderMessages());
        return;
      case "tool_result":
        delete S.asks[ev.call_id];
        if (chat) {
          let m = chat.messages.find((x) => x.role === "tool" && x.call_id === ev.call_id);
          if (!m) {                                    // die Seite wurde mitten in der Frage neu geladen: der Aufruf steht nur in der Nachricht der KI, sein Ergebnis kommt jetzt
            const asked = [].concat(...chat.messages.filter((x) => x.role === "assistant" && x.tool_calls).map((x) => x.tool_calls)).find((c) => c.id === ev.call_id);
            m = { role: "tool", call_id: ev.call_id, tool_name: ev.name, arguments: asked ? asked.arguments : {}, content: "", ok: null, ms: null };
            chat.messages.push(m);
          }
          m.ok = ev.ok; m.ms = ev.ms; m.skipped = !!ev.skipped; m.denied = !!ev.denied; m.content = JSON.stringify(ev.result);
        }
        redraw((v) => v.renderMessages());
        return;
      case "stopped":
        clearAsks(id);
        S.running.delete(id); delete S.live[id];
        each((v) => v.renderList());
        if (chat) { delete S.cache[id]; loadChat(id).catch(() => null).then(() => redraw((v) => { v.renderMessages(); v.renderInput(); })); }
        else redraw((v) => v.renderInput());
        return;
      case "error":
        clearAsks(id);
        delete S.live[id];
        if (chat) chat.messages.push({ role: "assistant", content: "", error: ev.message, error_code: ev.code, ts: Date.now() / 1000 });
        redraw((v) => v.renderMessages());
        return;
      case "done":
        clearAsks(id);
        S.running.delete(id); delete S.live[id];
        const shown = isShown(id);                                                    // fertig, aber der Chat ist gerade nicht zu sehen: gelber Punkt "neue Antwort"
        const patch = { updated: Date.now() / 1000, unread: !shown };
        if (chat) patch.messages = chat.messages.filter((m) => (m.role === "user" || m.role === "assistant") && m.content).length;          // ohne geladenen Chat bleibt die bisherige Anzahl stehen
        touchList(id, patch);
        if (shown) api("POST", "/api/ai/chats/" + id + "/seen").catch(() => null);
        each((v) => { v.renderList(); if (v.chatId === id) { v.renderMessages(); v.renderInput(); } });
        if (chat && (chat.messages.slice().reverse().find((m) => m.role === "user") || {}).manual) each((v) => { if (v.chatId === id) v.scrollToLastQuestion(); });          // ein langes Ergebnis von Hand: oben anfangen zu lesen, nicht am Ende
        return;
      default:
    }
  }

  const WARNINGS = {
    mode_not_ready: ["AIP_MODE_NOT_READY", "This mode is still being built - until then the AI answers as in chat mode."],
    repeat: ["AIP_LIMIT_REPEAT", "The AI kept calling the same function with the same values - it was stopped and answers with what it has."],
    tools_too_big: ["AIP_TOOLS_TOO_BIG", "All functions at once do not fit into the context window of this model - the common functions plus collection functions are used instead (Settings -> AI assistant -> Work mode -> Function list)."],
    max_calls: ["AIP_LIMIT_MAX", "That was a lot of function calls for one question - the AI was stopped and answers with what it has."],
  };

  client.registerModule("ai", {
    onMessage(message) {
      if (message.type === "ai_event") onEvent(message.payload || {});
      else if (message.type === "ai_chats_changed") {
        S.chats = (message.payload && message.payload.chats) || [];
        Object.keys(S.cache).forEach((id) => {
          const entry = S.chats.find((c) => c.id === id);
          if (!entry) delete S.cache[id];
          else { S.cache[id].title = entry.title; S.cache[id].model = entry.model; S.cache[id].mode = entry.mode; }          // Umbenennen / Modell- / Moduswechsel von einem anderen Panel oder Geraet
        });
        each((v) => { v.renderList(); v.ensureChat(); });
      } else if (message.type === "ai_state") {
        const p = message.payload || {};
        const turnedOn = !!p.enabled && !S.enabled;
        document.dispatchEvent(new CustomEvent("ai-state-changed"));          // die Einstellungsseite gleicht sich an (z. B. nach "Immer erlauben" im Chat)
        S.enabled = !!p.enabled; S.model = p.model || ""; S.defaultMode = p.default_mode || "chat";
        each((v) => v.renderAll());
        if (p.enabled && (turnedOn || !S.modelsLoaded || !S.models.length)) { S.modelsLoaded = false; loadModels(false); }        // Adresse oder Schalter geaendert: die Modellliste neu holen
      } else if (message.type === "state_snapshot") { loadAll(); }
    },
  });

  // ------------------------------------------------------------------------------------------ Darstellung: Text (ohne HTML)
  /** Kleines Markdown ohne HTML: Absaetze, Listen, ```Code```, `code`, **fett**. Alles wird als Text eingefuegt, nie als HTML. */
  function inline(parent, text) {
    String(text).split(/(`[^`\n]+`|\*\*[^*\n]+\*\*)/g).forEach((part) => {
      if (!part) return;
      if (part.startsWith("`") && part.endsWith("`") && part.length > 2) parent.appendChild(el("code", "aip__code", part.slice(1, -1)));
      else if (part.startsWith("**") && part.endsWith("**") && part.length > 4) parent.appendChild(el("strong", "", part.slice(2, -2)));
      else parent.appendChild(document.createTextNode(part));
    });
  }

  function renderText(container, text) {
    container.textContent = "";
    let paragraph = null, list = null, code = null;
    const closeBlocks = () => { paragraph = null; list = null; };
    String(text).split("\n").forEach((line) => {
      if (/^```/.test(line)) {
        if (code) { container.appendChild(code.pre); code = null; }
        else { closeBlocks(); const pre = el("pre", "aip__pre"); code = { pre, node: el("code") }; pre.appendChild(code.node); }
        return;
      }
      if (code) { code.node.textContent += (code.node.textContent ? "\n" : "") + line; return; }
      const bullet = /^\s*[-*]\s+(.*)$/.exec(line);
      if (bullet) { if (!list) { list = el("ul", "aip__list"); container.appendChild(list); paragraph = null; } const li = el("li"); inline(li, bullet[1]); list.appendChild(li); return; }
      if (!line.trim()) { closeBlocks(); return; }
      list = null;
      if (!paragraph) { paragraph = el("p", "aip__p"); container.appendChild(paragraph); } else paragraph.appendChild(document.createElement("br"));
      inline(paragraph, line);
    });
    if (code) container.appendChild(code.pre);
  }

  /** Dauer lesbar; 0 / unbekannt = leer (dann steht nichts da statt "0 ms"). */
  const fmtMs = (ms) => {
    const n = Number(ms);
    if (ms == null || !isFinite(n) || n <= 0) return "";
    if (n < 1000) return Math.round(n) + " ms";
    return (n / 1000).toFixed(n < 10000 ? 1 : 0) + " s";
  };

  /** Messwerte direkt unter der Antwort, kompakt: Modus, Gesamtzeit der Frage, Tokens/s, (Ladezeit des Modells nur wenn sie auffaellt), Modell. */
  function statsLine(stats, model, mode) {
    if (!stats) return "";
    const parts = [];
    if (mode) { const m = MODES.find((x) => x.id === mode); if (m) parts.push(t(m.name[0], m.name[1])); }
    if (fmtMs(stats.run_ms)) parts.push(t("AIP_TOTAL", "total") + " " + fmtMs(stats.run_ms));
    if (stats.tokens) parts.push(stats.tokens + " " + t("AIP_TOKENS", "tokens") + (stats.tokens_per_s ? " (" + stats.tokens_per_s + "/s)" : ""));
    if (stats.load_ms > 1000) parts.push(t("AIP_LOADED", "model loaded") + " " + fmtMs(stats.load_ms));
    if (model) parts.push(model);
    if (stats.truncated) parts.push(t("AIP_TRUNCATED", "cut off: answer limit reached"));
    return parts.join(" · ");
  }

  /** Oeffnet die Einstellungen direkt in der Kategorie KI-Assistent (nur am Konsolenrechner). */
  function openAiSettings() {
    const b = document.querySelector('.menubar__icon-button[data-action="open-settings-modal"]');
    if (b) { b.dataset.settingsCategory = "ai"; b.click(); delete b.dataset.settingsCategory; }
  }

  /** Drei springende Punkte: die KI arbeitet (sonst sieht man nicht, ob sie haengt). */
  function typingDots() {
    const dots = el("span", "aip__dots");
    dots.setAttribute("aria-hidden", "true");
    for (let i = 0; i < 3; i++) dots.appendChild(el("i"));
    return dots;
  }

  function copyButton(getText) {
    const button = el("button", "aip__copy");
    button.type = "button";
    button.appendChild(Icons.svg("copy"));
    button.title = t("AIP_COPY", "Copy");
    button.addEventListener("click", () => copyText(getText()));
    return button;
  }

  function userNode(msg) {
    const row = el("div", "aip__msg aip__msg--user");
    const bubble = el("div", "aip__bubble");
    renderText(bubble, msg.content);
    row.append(copyButton(() => msg.content), bubble);               // der Knopf steht neben der Blase und erscheint beim Darueberfahren
    return row;
  }

  function infoNode(text, error) {
    const note = el("div", "aip__notice" + (error ? " aip__notice--error" : ""));
    const icon = Icons.svg(error ? "alert" : "info");
    icon.classList.add("aip__notice-icon");
    note.append(icon, el("span", "", text));
    return note;
  }

  /** Der ausklappbare Block "Denkschritte" (bei Modellen, die vor der Antwort nachdenken). `set(text, ms, open)` aktualisiert ihn (auch waehrend das Modell noch denkt). */
  function thinkNode(opts) {
    const box = el("div", "aip__think" + (opts.live ? " aip__think--live" : ""));
    const head = el("button", "aip__think-head");
    head.type = "button";
    const icon = Icons.svg("bulb");
    icon.classList.add("aip__think-icon");
    const label = el("span", "aip__think-label");
    head.append(icon, label, chevron());
    const body = el("div", "aip__think-body");
    box.append(head, body);
    const api = {
      node: box,
      set(text, ms, open) {
        body.textContent = text;
        label.textContent = ms ? t("AIP_THOUGHT_FOR", "Thought for {t}").replace("{t}", fmtMs(ms)) : opts.live && !opts.done ? t("AIP_THINKING_LIVE", "Thinking ...") : t("AIP_THINKING", "Thinking steps");
        body.hidden = !open;
        box.classList.toggle("aip__think--open", open);
        if (open && opts.live) body.scrollTop = body.scrollHeight;
      },
    };
    head.addEventListener("click", () => opts.onToggle(!box.classList.contains("aip__think--open")));
    return api;
  }

  /** Der gespeicherte Block (zugeklappt, bis er angeklickt wird; der Zustand ueberlebt das Neuzeichnen). */
  function storedThink(text, ms, key) {
    const n = thinkNode({ onToggle: (open) => { if (open) S.open.add(key); else S.open.delete(key); n.set(text, ms, open); } });
    n.set(text, ms, S.open.has(key));
    return n.node;
  }

  function answerNode(msg) {
    const row = el("div", "aip__msg aip__msg--assistant");
    if (msg.thinking) row.appendChild(storedThink(msg.thinking, msg.stats && msg.stats.think_ms, "k:a" + (msg.ts || "")));
    const bubble = el("div", "aip__bubble");
    renderText(bubble, msg.content || "");
    if (msg.stopped) bubble.appendChild(el("div", "aip__stopped", t("AIP_STOPPED", "(stopped)")));
    const line = el("div", "aip__line");
    line.append(bubble);
    if (msg.content) line.append(copyButton(() => msg.content));
    row.appendChild(line);
    return row;
  }

  /** Die Messwerte einer Antwort (Modus, Zeit, Tokens, Modell) als eigene Zeile - sie steht in renderTurn UNTER den Schaltflaechen der Frage. */
  function statsNode(msg) {
    const figures = statsLine(msg.stats, msg.model, msg.mode);
    return figures ? el("div", "aip__stats", figures) : null;
  }

  const prettyJson = (value) => { try { return JSON.stringify(typeof value === "string" ? JSON.parse(value) : value, null, 2); } catch (err) { return String(value == null ? "" : value); } };
  const chevron = () => { const c = Icons.svg("chevron-down"); c.classList.add("aip__chev"); return c; };
  const callStatus = (tool) => (S.asks[tool.call_id] ? "waiting" : tool.ok === null || tool.ok === undefined ? "running" : tool.denied ? "denied" : tool.skipped ? "skipped" : tool.ok ? "done" : "error");
  const STATUS = { waiting: ["AIP_TOOL_WAITING", "waiting for you"], running: ["AIP_TOOL_RUNNING", "running"], done: ["AIP_TOOL_DONE", "done"], error: ["AIP_TOOL_ERROR", "failed"], skipped: ["AIP_TOOL_SKIPPED", "not run"],
    denied: ["AIP_TOOL_DENIED", "not allowed"] };
  const STATUS_ICON = { waiting: "info", running: "refresh", done: "check", error: "close", skipped: "close", denied: "lock" };
  const ACCESS_LABEL = { read: ["AI_ACCESS_READ", "Reads the show"], write: ["AI_ACCESS_WRITE", "Changes the show"], critical: ["AI_ACCESS_CRITICAL", "Critical action"] };
  const isLocal = () => !!(client.state && client.state.is_local);

  /** Rueckfrage "Darf der Assistent das?": zeigt Funktion und Werte; Einmal erlauben / Immer erlauben (nur am Konsolenrechner, nie bei kritischen Funktionen) / Nicht erlauben.
   *  Die Antwort geht ueber den WebSocket (ai_confirm); die Karte verschwindet, wenn der Server `tool_answer` meldet - auf jedem Geraet. */
  function approvalBar(ask, callId) {
    const bar = el("div", "aip__ask");
    bar.dataset.callId = callId;
    const what = el("div", "aip__ask-what");
    const icon = Icons.svg(ask.access === "critical" ? "alert" : "info");
    icon.classList.add("aip__ask-icon");
    const argText = ask.arguments && Object.keys(ask.arguments).length ? JSON.stringify(ask.arguments) : "";
    const kind = ACCESS_LABEL[ask.access];
    what.append(icon, el("span", "aip__ask-text", t("AIP_ASK", "The assistant wants to run this function. Allow it?")), kind ? el("span", "aip__ask-kind", t(kind[0], kind[1])) : document.createTextNode(""),
      el("code", "aip__ask-call", ask.name + (argText ? " " + argText : "")));
    const buttons = el("div", "aip__ask-buttons");
    const once = el("button", "modal__button modal__button--primary", t("AIP_ALLOW_ONCE", "Allow once"));
    const deny = el("button", "modal__button", t("AIP_DENY", "Don't allow"));
    once.type = deny.type = "button";
    once.dataset.action = "allow-once"; deny.dataset.action = "deny";
    const all = [once, deny];
    const reply = (approve, always) => {
      all.forEach((b) => { b.disabled = true; });
      client.send("ai_confirm", { chat_id: ask.chatId, call_id: callId, approve, always: !!always });
      if (approve && always && typeof _showToast === "function") _showToast(t("AIP_SAVED_ALWAYS", "Saved: \"{name}\" now runs without asking. Undo it in Settings -> AI assistant -> Permissions.").replace("{name}", ask.name), "info", 6000);
    };
    once.addEventListener("click", () => reply(true, false));
    deny.addEventListener("click", () => reply(false, false));
    buttons.append(once);
    {
      const always = el("button", "modal__button", t("AIP_ALLOW_ALWAYS", "Always allow"));
      always.type = "button"; always.dataset.action = "allow-always";
      always.title = t("AIP_ALLOW_ALWAYS_TIP", "This function runs without asking from now on. You can undo it in Settings -> AI assistant -> Permissions.");
      always.addEventListener("click", () => reply(true, true));
      all.push(always);
      buttons.append(always);
    }
    buttons.append(deny);
    bar.append(what, buttons);
    return bar;
  }

  /** Eine einzelne Funktion (Zeile im Funktionsblock); ein Klick zeigt Eingabe und Ergebnis als JSON. */
  function toolRow(tool) {
    const status = callStatus(tool);
    const key = "t:" + tool.call_id;
    const card = el("div", "aip__tool aip__tool--" + status);
    card.dataset.callId = tool.call_id;
    const head = el("button", "aip__tool-head");
    head.type = "button";
    const icon = Icons.svg(STATUS_ICON[status]);
    icon.classList.add("aip__tool-icon");
    const argText = tool.arguments && Object.keys(tool.arguments).length ? JSON.stringify(tool.arguments) : "";
    const time = status === "done" || status === "error" ? fmtMs(tool.ms) : "";
    head.append(icon, el("span", "aip__tool-name", tool.tool_name), el("span", "aip__tool-args", argText.length > 70 ? argText.slice(0, 67) + "..." : argText),
      el("span", "aip__tool-status", t(STATUS[status][0], STATUS[status][1]) + (time ? " · " + time : "")), chevron());
    const body = el("div", "aip__tool-body");
    const shownIn = prettyJson(tool.arguments || {});
    const shownOut = tool.content ? prettyJson(tool.content) : "";
    body.append(el("div", "aip__tool-label", t("AIP_TOOL_INPUT", "Input")), el("pre", "aip__pre", shownIn));
    if (shownOut) body.append(el("div", "aip__tool-label", t("AIP_TOOL_RESULT", "Result")), el("pre", "aip__pre", shownOut));
    const copy = copyButton(() => tool.tool_name + "\n" + shownIn + (shownOut ? "\n\n" + shownOut : ""));
    copy.classList.add("aip__copy--corner");
    body.appendChild(copy);
    const sync = () => { const open = S.open.has(key); body.hidden = !open; card.classList.toggle("aip__tool--open", open); };
    sync();
    head.addEventListener("click", () => { if (S.open.has(key)) S.open.delete(key); else S.open.add(key); sync(); });
    if (status === "waiting") card.append(head, approvalBar(S.asks[tool.call_id], tool.call_id), body);
    else card.append(head, body);
    return card;
  }

  /** Alle Funktionen, die die KI bei EINER Frage aufruft, in einem ausklappbaren Block (zugeklappt: Anzahl, Namen, Stand, Gesamtzeit). */
  function toolGroup(rounds) {
    const rows = [].concat(...rounds.map((r) => r.tools));
    const key = "g:" + (rows[0] ? rows[0].call_id : "x");
    if (rounds.some((r) => r.manual) && !S.seenManual.has(key)) {          // eine von Hand aufgerufene Funktion: das Ergebnis ist das, was man sehen will - gleich aufgeklappt
      S.seenManual.add(key);
      S.open.add(key);
      rows.forEach((r) => S.open.add("t:" + r.call_id));
    }
    const counts = {};
    let totalMs = 0;
    rows.forEach((tool) => { const s = callStatus(tool); counts[s] = (counts[s] || 0) + 1; if ((s === "done" || s === "error") && tool.ms > 0) totalMs += Number(tool.ms); });
    const waiting = !!counts.waiting;
    const running = !!counts.running;
    const bad = !!(counts.error || counts.skipped || counts.denied);
    const box = el("div", "aip__tools aip__tools--" + (waiting ? "waiting" : running ? "running" : bad ? "error" : "done"));
    const head = el("button", "aip__tools-head");
    head.type = "button";
    const icon = Icons.svg(waiting ? "info" : running ? "refresh" : bad ? "close" : "check");
    icon.classList.add("aip__tools-icon");
    const label = rows.length === 1 ? t("AIP_TOOLS_ONE", "1 function") : t("AIP_TOOLS_MANY", "{n} functions").replace("{n}", String(rows.length));
    const names = [...new Set(rows.map((r) => r.tool_name))].join(", ");
    const summary = Object.keys(counts).map((k) => (counts[k] > 1 || Object.keys(counts).length > 1 ? counts[k] + " " : "") + t(STATUS[k][0], STATUS[k][1])).join(" · ") + (totalMs ? " · " + fmtMs(totalMs) : "");
    head.append(icon, el("span", "aip__tools-label", label), el("span", "aip__tools-names", names), el("span", "aip__tools-summary", summary), chevron());
    const list = el("div", "aip__tools-list");
    rounds.forEach((round) => {
      if (round.think) list.appendChild(storedThink(round.think, round.thinkMs, "k:" + (round.tools[0] ? round.tools[0].call_id : "x")));
      if (round.say) list.appendChild(el("div", "aip__tools-say", round.say));
      round.tools.forEach((tool) => list.appendChild(toolRow(tool)));
    });
    const sync = () => { const open = S.open.has(key) || waiting; list.hidden = !open; box.classList.toggle("aip__tools--open", open); };       // mit offener Rueckfrage ist der Block immer offen
    sync();
    head.addEventListener("click", () => { if (S.open.has(key)) S.open.delete(key); else S.open.add(key); sync(); });
    box.append(head, list);
    return box;
  }

  /** Der Verlauf in Fragen (ab einer Benutzernachricht) zerlegt. Je Frage steht IMMER in dieser Reihenfolge (renderTurn): 1. die Funktionen (ein Block), 2. die Antwort der KI,
   *  3. Schaltflaechen (Dialog oeffnen), 4. die Messwerte (Zeit, Tokens, Modell), 5. ganz unten Hinweise und Fehler. */
  function splitTurns(chat) {
    const turns = [];
    let cur = null;
    const start = (user) => { cur = { user, rounds: [], infos: [], answers: [] }; turns.push(cur); };
    chat.messages.forEach((m) => {
      if (m.role === "user") { start(m); return; }
      if (m.role === "tool") return;
      if (m.role !== "notice" && m.role !== "assistant") return;
      if (!cur) start(null);
      if (m.role === "notice") { cur.infos.push({ text: m.content }); return; }
      if (m.error) { cur.infos.push({ text: m.error, error: true }); return; }
      if (m.tool_calls && m.tool_calls.length) {
        cur.rounds.push({ manual: !!m.manual, say: m.content || "", think: m.thinking || "", thinkMs: m.stats && m.stats.think_ms, tools: m.tool_calls.map((call) => chat.messages.find((x) => x.role === "tool" && x.call_id === call.id) || { call_id: call.id, tool_name: call.name, arguments: call.arguments, ok: null }) });
      } else if (m.content || m.stopped) cur.answers.push(m);
    });
    return turns;
  }

  function renderTurn(turn, parent) {
    if (turn.user) parent.appendChild(userNode(turn.user));
    if (turn.rounds.length) {
      const row = el("div", "aip__msg aip__msg--assistant aip__msg--tools");
      row.appendChild(toolGroup(turn.rounds));
      parent.appendChild(row);
    }
    turn.answers.forEach((msg) => parent.appendChild(answerNode(msg)));
    const actions = turnActions(turn);
    if (actions.length) parent.appendChild(actionRow(actions));
    turn.answers.forEach((msg) => { const stats = statsNode(msg); if (stats) parent.appendChild(stats); });
    turn.infos.forEach((info) => parent.appendChild(infoNode(info.text, info.error)));
  }

  // ------------------------------------------------------------------------------------------ Menue eines Chats (Umbenennen / Duplizieren / Loeschen)
  let openMenu = null;
  function closeChatMenu() { if (openMenu) { openMenu.remove(); openMenu = null; } }
  document.addEventListener("pointerdown", (e) => { if (openMenu && !openMenu.contains(e.target)) closeChatMenu(); }, true);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeChatMenu(); });
  window.addEventListener("resize", closeChatMenu);

  /** `items`: [{ icon, label, danger, run }]; das Menue erscheint unter `anchor` (oder darueber, wenn unten kein Platz ist). */
  function showChatMenu(anchor, items) {
    closeChatMenu();
    const menu = el("div", "aip__ctx");
    menu.setAttribute("role", "menu");
    items.forEach((it) => {
      const b = el("button", "aip__ctx-item" + (it.danger ? " aip__ctx-item--danger" : ""));
      b.type = "button";
      b.setAttribute("role", "menuitem");
      b.dataset.action = it.action;
      b.append(Icons.svg(it.icon), el("span", "", it.label));
      b.addEventListener("click", () => { closeChatMenu(); it.run(); });
      menu.appendChild(b);
    });
    document.body.appendChild(menu);
    const r = anchor.getBoundingClientRect();
    const left = Math.max(6, Math.min(r.right - menu.offsetWidth, window.innerWidth - menu.offsetWidth - 6));
    const top = r.bottom + 4 + menu.offsetHeight > window.innerHeight - 6 ? Math.max(6, r.top - menu.offsetHeight - 4) : r.bottom + 4;
    menu.style.left = left + "px";
    menu.style.top = top + "px";
    openMenu = menu;
    const first = menu.querySelector("button");
    if (first) first.focus();
  }

  // ------------------------------------------------------------------------------------------ Das Panel
  function buildPanel(panel) {
    const root = el("div", "aip");
    const view = { root, chatId: null, seen: false, raf: 0, thinkOpen: null, liveThink: null, forceBottom: false, pendingModel: "", pendingMode: "", panelId: panel && panel.id ? panel.id : "" };
    const KEY = "oc-ai-chat-" + view.panelId;
    const LIST_KEY = "oc-ai-list-off-" + view.panelId;               // "1" = die Chat-Liste ist eingeklappt (je Panel gemerkt, nur im breiten Panel)
    try { view.chatId = localStorage.getItem(KEY) || null; } catch (err) { /* ohne Speicher */ }
    try { if (localStorage.getItem(LIST_KEY) === "1") root.classList.add("aip--side-off"); } catch (err) { /* ohne Speicher */ }

    // ---- Kopf: Chats / Titel / Modell / Neuer Chat
    const header = el("div", "aip__header");
    const toggleList = el("button", "aip__icon");
    toggleList.type = "button"; toggleList.appendChild(Icons.svg("sidebar"));
    const syncToggle = () => {
      const off = root.classList.contains("aip--side-off") && !root.classList.contains("aip--narrow");
      const shown = root.classList.contains("aip--narrow") ? root.classList.contains("aip--list") : !off;
      toggleList.title = shown ? t("AIP_LIST_HIDE", "Hide chat list") : t("AIP_LIST_SHOW", "Show chat list");
      toggleList.setAttribute("aria-label", toggleList.title);
      toggleList.setAttribute("aria-pressed", shown ? "true" : "false");
    };
    const title = el("div", "aip__title");
    const dd = el("div", "aip__dd");
    const ddButton = el("button", "aip__dd-btn");
    ddButton.type = "button"; ddButton.title = t("AIP_MODEL_TIP", "Model of this chat (you can change it at any time)");
    const ddLabel = el("span", "aip__dd-label");
    ddButton.append(ddLabel, Icons.svg("chevron-down"));
    const ddMenu = el("div", "aip__dd-menu");
    ddMenu.hidden = true;
    dd.append(ddButton, ddMenu);
    const newButton = el("button", "aip__icon aip__new");
    newButton.type = "button"; newButton.appendChild(Icons.svg("plus")); newButton.title = t("AIP_NEW_CHAT", "New chat");
    header.append(toggleList, title, dd, newButton);

    // ---- Liste, Verlauf, Eingabe: [Modus-Knopf] [Textfeld] [Senden / Stopp]
    const body = el("div", "aip__body");
    const side = el("div", "aip__side");
    const list = el("div", "aip__list-items");
    side.appendChild(list);
    const main = el("div", "aip__main");
    const notice = el("div", "aip__empty");
    const scroller = el("div", "aip__scroll");
    const messages = el("div", "aip__messages");
    const jump = el("button", "aip__jump");
    jump.type = "button"; jump.hidden = true;
    jump.appendChild(Icons.svg("arrow-down"));
    const inputRow = el("div", "aip__input");
    const modeButton = el("button", "aip__mode");
    modeButton.type = "button";
    modeButton.setAttribute("aria-haspopup", "true");
    const modeMenu = el("div", "aip__mode-menu");
    modeMenu.hidden = true;
    const text = el("textarea", "aip__text");
    text.rows = 1; text.maxLength = 8000;
    const send = el("button", "aip__send");
    send.type = "button";
    const mic = el("button", "aip__mic");                // Diktieren: Sprache -> Text im Eingabefeld (app/dictation.py), nur an der Konsole
    mic.type = "button";
    mic.appendChild(Icons.svg("mic"));
    const dict = el("div", "aip__dictate");              // ersetzt waehrenddessen das Eingabefeld: Balken, Zeit, Abbrechen / Fertig
    dict.hidden = true;
    const slash = el("div", "aip__slash");              // Vorschlaege, solange man "/Funktionsname" tippt (Funktionen von Hand aufrufen)
    slash.hidden = true;
    slash.setAttribute("role", "listbox");
    inputRow.append(modeButton, text, dict, mic, send, modeMenu, slash);
    scroller.append(messages, jump);
    main.append(notice, scroller, inputRow);
    body.append(side, main);
    root.append(header, body);

    const chat = () => (view.chatId ? S.cache[view.chatId] : null);
    const entry = () => S.chats.find((x) => x.id === view.chatId);
    const running = () => !!view.chatId && S.running.has(view.chatId);
    const stick = () => messages.scrollHeight - messages.scrollTop - messages.clientHeight < 60;
    /** Der Knopf "nach unten" erscheint, sobald man nicht mehr am Ende steht (z. B. weil man oben liest, waehrend unten noch geschrieben wird). */
    const updateJump = () => { jump.hidden = stick(); jump.classList.toggle("aip__jump--busy", !jump.hidden && running()); };
    jump.title = t("AIP_JUMP_BOTTOM", "Jump to the latest message");
    jump.setAttribute("aria-label", jump.title);
    jump.addEventListener("click", () => { messages.scrollTo({ top: messages.scrollHeight, behavior: "smooth" }); });
    messages.addEventListener("scroll", updateJump, { passive: true });
    const currentModel = () => { const c = chat(); const e = entry(); return (c && c.model) || (e && e.model) || view.pendingModel || S.model || ""; };
    const currentMode = () => { const c = chat(); const e = entry(); return modeById((c && c.mode) || (e && e.mode) || view.pendingMode || S.defaultMode).id; };

    // ---- Modus: Knopf + kleines Menue
    const closeModeMenu = () => { modeMenu.hidden = true; modeButton.classList.remove("aip__mode--open"); };
    function renderMode() {
      const mode = modeById(currentMode());
      modeButton.textContent = "";
      modeButton.appendChild(Icons.svg(mode.icon));
      modeButton.title = t(mode.name[0], mode.name[1]) + " - " + t("AIP_MODE_TIP", "change mode");
      modeButton.setAttribute("aria-label", modeButton.title);
      modeMenu.textContent = "";
      MODES.forEach((m) => {
        const item = el("button", "aip__mode-item" + (m.id === mode.id ? " aip__mode-item--on" : ""));
        item.type = "button";
        item.dataset.mode = m.id;
        const name = el("span", "aip__mode-name", t(m.name[0], m.name[1]));
        if (!m.ready) name.appendChild(el("span", "aip__mode-soon", t("AIP_MODE_SOON", "soon")));
        item.append(Icons.svg(m.icon), name, el("span", "aip__mode-desc", t(m.desc[0], m.desc[1])));
        item.addEventListener("click", () => { closeModeMenu(); chooseMode(m.id); text.focus(); });
        modeMenu.appendChild(item);
      });
    }
    async function chooseMode(id) {
      if (!view.chatId) { view.pendingMode = id; renderMode(); return; }
      const c = chat(); if (c) c.mode = id;
      touchList(view.chatId, { mode: id });
      renderMode();
      try { await api("PATCH", "/api/ai/chats/" + view.chatId, { mode: id }); } catch (err) { /* der Server bekommt den Modus ohnehin mit jeder Nachricht */ }
    }
    modeButton.addEventListener("click", () => {
      if (!modeMenu.hidden) { closeModeMenu(); return; }
      renderMode();
      modeMenu.hidden = false;
      modeButton.classList.add("aip__mode--open");
    });
    document.addEventListener("pointerdown", (e) => { if (!modeMenu.hidden && !modeMenu.contains(e.target) && !modeButton.contains(e.target)) closeModeMenu(); }, true);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !modeMenu.hidden) closeModeMenu(); });

    // ---- Modellauswahl (eigene Liste mit Groesse)
    const closeMenu = () => { ddMenu.hidden = true; dd.classList.remove("aip__dd--open"); };
    const fmtSize = (bytes) => (bytes ? (bytes >= 1e9 ? (bytes / 1e9).toFixed(1) + " GB" : Math.round(bytes / 1e6) + " MB") : "");
    function renderMenu() {
      ddMenu.textContent = "";
      const current = currentModel();
      const items = S.models.slice();
      if (current && !items.some((m) => m.name === current)) items.unshift({ name: current, missing: true });
      if (!items.length) ddMenu.appendChild(el("div", "aip__dd-none", t("AIP_NO_MODELS", "No model found. Check the server in Settings -> AI assistant.")));
      items.forEach((m) => {
        const item = el("button", "aip__dd-item" + (m.name === current ? " aip__dd-item--on" : ""));
        item.type = "button";
        item.dataset.model = m.name;
        const meta = m.missing ? t("AI_MODEL_MISSING", "not available") : [m.parameters, fmtSize(m.size)].filter(Boolean).join(" · ");
        item.append(el("span", "aip__dd-name", m.name), el("span", "aip__dd-meta", meta));
        item.addEventListener("click", () => { closeMenu(); chooseModel(m.name); });
        ddMenu.appendChild(item);
      });
    }
    async function chooseModel(name) {
      if (!view.chatId) { view.pendingModel = name; view.renderHeader(); view.renderNotice(); return; }
      try {
        await api("PATCH", "/api/ai/chats/" + view.chatId, { model: name });
        const c = chat(); if (c) c.model = name;
        touchList(view.chatId, { model: name });
        view.renderList(); view.renderHeader();
      } catch (err) { /* bleibt */ }
    }
    ddButton.addEventListener("click", () => {
      if (!ddMenu.hidden) { closeMenu(); return; }
      renderMenu();
      ddMenu.hidden = false;
      dd.classList.add("aip__dd--open");
      loadModels(true).then(() => { if (!ddMenu.hidden) renderMenu(); });
    });
    document.addEventListener("pointerdown", (e) => { if (!ddMenu.hidden && !dd.contains(e.target)) closeMenu(); }, true);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !ddMenu.hidden) closeMenu(); });

    view.renderHeader = () => {
      const c = chat();
      const e = entry();
      title.textContent = (c && c.title) || (e && e.title) || t("AIP_NEW_TITLE", "New chat");
      const model = currentModel();
      ddLabel.textContent = model || t("AIP_MODEL_NONE", "- model -");
      ddButton.classList.toggle("aip__dd-btn--empty", !model);
      if (!ddMenu.hidden) renderMenu();
    };

    /** Benennt einen Chat direkt in der Liste um (Eingabe / Enter = speichern, Esc = abbrechen). Ein leerer Name aendert nichts. */
    function startRename(c, label) {
      const input = el("input", "aip__rename");
      input.value = c.title || ""; input.maxLength = 80; input.placeholder = t("AIP_NEW_TITLE", "New chat");
      label.textContent = "";
      label.appendChild(input);
      input.focus(); input.select();
      let done = false;
      const finish = async (apply) => {
        if (done) return; done = true;
        const value = input.value.trim();
        if (apply && value && value !== c.title) {
          touchList(c.id, { title: value });
          const cached = S.cache[c.id]; if (cached) cached.title = value;
          each((v) => { v.renderList(); v.renderHeader(); });
          try { await api("PATCH", "/api/ai/chats/" + c.id, { title: value }); } catch (err) { /* der Server meldet den echten Stand gleich */ }
        } else view.renderList();
      };
      input.addEventListener("keydown", (e) => { e.stopPropagation(); if (e.key === "Enter") finish(true); else if (e.key === "Escape") finish(false); });
      input.addEventListener("click", (e) => e.stopPropagation());
      input.addEventListener("blur", () => finish(true));
    }

    async function duplicateChat(c) {
      try {
        const name = c.title || t("AIP_NEW_TITLE", "New chat");
        const created = await api("POST", "/api/ai/chats/" + c.id + "/duplicate", { title: t("AIP_COPY_NAME", "{name} (copy)").replace("{name}", name) });
        touchList(created.id, { title: created.title, model: created.model, mode: created.mode, messages: c.messages, updated: Date.now() / 1000 });
        await view.select(created.id);
      } catch (err) {
        if (typeof _showToast === "function") _showToast(err.message, "error", 3500);
      }
    }

    async function deleteChat(c) {
      const name = c.title || t("AIP_NEW_TITLE", "New chat");
      if (!(await _askDelete("other", { title: t("AIP_DELETE_CHAT_TITLE", "Delete chat?"), body: t("AIP_DELETE_CHAT_BODY", "The chat \"{name}\" and all its messages will be deleted. This cannot be undone.").replace("{name}", name), confirmKey: "LAYOUT_DELETE_CONFIRM" }))) return;
      try { await api("DELETE", "/api/ai/chats/" + c.id); } catch (err) { /* schon weg */ }
    }

    view.renderList = () => {
      list.textContent = "";
      S.chats.forEach((c) => {
        const item = el("div", "aip__chat" + (c.id === view.chatId ? " aip__chat--on" : "") + (c.unread && !S.running.has(c.id) ? " aip__chat--unread" : ""));
        item.dataset.chatId = c.id;
        const mode = modeById(c.mode);
        const modeIcon = Icons.svg(mode.icon);
        modeIcon.classList.add("aip__chat-mode");
        const label = el("div", "aip__chat-title", c.title || t("AIP_NEW_TITLE", "New chat"));
        const meta = el("div", "aip__chat-meta", [c.model, c.messages ? c.messages + " " + t("AIP_MESSAGES", "messages") : ""].filter(Boolean).join(" · "));
        const text = el("div", "aip__chat-text");
        const head = el("div", "aip__chat-head");
        head.appendChild(label);
        if (S.running.has(c.id)) {                                                     // die KI schreibt gerade in diesem Chat
          const live = el("span", "aip__chat-live");
          live.title = t("AIP_CHAT_WRITING", "The AI is writing");
          live.appendChild(typingDots());
          head.appendChild(live);
        } else if (c.unread) {                                                         // fertig, noch nicht angesehen
          const dot = el("span", "aip__chat-unread");
          dot.title = t("AIP_CHAT_UNREAD", "New answer");
          head.appendChild(dot);
        }
        text.append(head, meta);
        const more = el("button", "aip__chat-more");
        more.type = "button"; more.appendChild(Icons.svg("dots")); more.title = t("AIP_CHAT_MENU", "More"); more.setAttribute("aria-label", more.title); more.setAttribute("aria-haspopup", "menu");
        const openFor = (anchor) => showChatMenu(anchor, [
          { action: "rename", icon: "edit", label: t("AIP_RENAME_CHAT", "Rename"), run: () => startRename(c, label) },
          { action: "duplicate", icon: "copy", label: t("AIP_DUPLICATE_CHAT", "Duplicate"), run: () => duplicateChat(c) },
          { action: "delete", icon: "trash", label: t("AIP_DELETE_CHAT", "Delete chat"), danger: true, run: () => deleteChat(c) },
        ]);
        more.addEventListener("click", (e) => { e.stopPropagation(); openFor(more); });
        item.addEventListener("contextmenu", (e) => { e.preventDefault(); openFor(more); });
        item.append(modeIcon, text, more);
        item.addEventListener("click", () => view.select(c.id));
        list.appendChild(item);
      });
      if (!S.chats.length) list.appendChild(el("div", "aip__chat-empty", t("AIP_NO_CHATS", "No chats yet.")));
    };

    function welcome() {
      const box = el("div", "aip__welcome");
      box.appendChild(el("div", "aip__welcome-title", t("AIP_WELCOME_TITLE", "How can I help?")));
      box.appendChild(el("div", "aip__welcome-text", t("AIP_WELCOME_TEXT", "Write a message below. The button at the bottom left switches the mode.")));
      return box;
    }

    view.renderMessages = () => {
      const c = chat();
      const follow = stick() || view.forceBottom;
      const keep = messages.scrollTop;
      messages.textContent = "";
      if (c) splitTurns(c).forEach((turn) => renderTurn(turn, messages));
      if ((!c || !c.messages.length) && S.enabled && !(view.chatId && S.live[view.chatId])) messages.appendChild(welcome());
      view.liveNode = null;
      view.liveThink = null;
      view.typingNode = null;
      view.renderLive(false);
      messages.scrollTop = follow ? messages.scrollHeight : keep;          // wer oben liest, bleibt dort - auch wenn unten gerade etwas dazukommt
      if (c) view.forceBottom = false;
      updateJump();
    };

    view.renderLive = (create) => {
      const live = view.chatId ? S.live[view.chatId] : null;
      if (!live) {
        if (view.liveNode) { view.liveNode.remove(); view.liveNode = null; view.liveThink = null; }
        if (running()) {                                                   // gesendet, die Antwort hat noch nicht begonnen: Punkte zeigen, dass gearbeitet wird
          if (!view.typingNode) {
            const row = el("div", "aip__msg aip__msg--assistant aip__msg--typing");
            const bubble = el("div", "aip__bubble aip__bubble--wait");
            bubble.append(typingDots());
            row.appendChild(bubble);
            messages.appendChild(row);
            view.typingNode = row;
            if (stick() || view.forceBottom) messages.scrollTop = messages.scrollHeight;
          }
        } else if (view.typingNode) { view.typingNode.remove(); view.typingNode = null; }
        updateJump();
        return;
      }
      if (view.typingNode) { view.typingNode.remove(); view.typingNode = null; }
      const welcomeBox = messages.querySelector(".aip__welcome");
      if (welcomeBox) welcomeBox.remove();
      if (!view.liveNode) {
        const row = el("div", "aip__msg aip__msg--assistant aip__msg--live");
        row.appendChild(el("div", "aip__bubble"));
        messages.appendChild(row);
        view.liveNode = row;
        view.liveThink = null;
      }
      const bubble = view.liveNode.querySelector(".aip__bubble");
      const follow = stick();
      if (live.thinking) {                                                 // Denkschritte: offen, solange noch kein Text kommt (oder bis der Benutzer es anders will)
        if (!view.liveThink) {
          view.liveThink = thinkNode({ live: true, onToggle: (open) => { view.thinkOpen = open; view.renderLive(false); } });
          view.liveNode.insertBefore(view.liveThink.node, view.liveNode.firstChild);
        }
        view.liveThink.set(live.thinking, live.text ? live.thinkMs : 0, view.thinkOpen !== null ? view.thinkOpen : !live.text);
      }
      bubble.hidden = !live.text && !!live.thinking;
      if (live.text) { bubble.classList.remove("aip__bubble--wait"); renderText(bubble, live.text); }
      else if (!live.thinking) { bubble.classList.add("aip__bubble--wait"); bubble.textContent = ""; bubble.append(typingDots()); }
      if (follow || view.forceBottom) messages.scrollTop = messages.scrollHeight;          // nur wer unten steht (oder gerade gesendet hat) wird mitgenommen
      updateJump();
    };
    /** Die letzte Frage des Benutzers an den oberen Rand holen (nach einer von Hand aufgerufenen Funktion mit langem Ergebnis). */
    view.scrollToLastQuestion = () => {
      const users = messages.querySelectorAll(".aip__msg--user");
      const last = users[users.length - 1];
      if (!last) return;
      messages.scrollTop = last.getBoundingClientRect().top - messages.getBoundingClientRect().top + messages.scrollTop - 8;
      updateJump();
    };
    view.scheduleLive = () => { if (!view.raf) view.raf = requestAnimationFrame(() => { view.raf = 0; view.renderLive(false); }); };

    view.renderInput = () => {
      const off = !S.enabled;
      const busy = running();
      text.placeholder = t("AIP_PLACEHOLDER", "Write a message...");
      text.disabled = off;
      send.disabled = off;
      modeButton.disabled = off;
      send.textContent = "";
      send.appendChild(Icons.svg(busy ? "stop" : "arrow-up"));
      send.title = busy ? t("AIP_STOP", "Stop") : t("AIP_SEND", "Send");
      send.setAttribute("aria-label", send.title);
      send.classList.toggle("aip__send--stop", busy);
      renderMode();
      renderDictation();
    };

    view.renderNotice = () => {
      notice.textContent = "";
      notice.hidden = true;
      if (!S.loaded) return;
      if (!S.enabled) {
        notice.hidden = false;
        notice.appendChild(el("p", "aip__p", t("AIP_DISABLED", "The AI assistant is switched off. Turn it on in Settings -> AI assistant and choose a model.")));
        {
          const open = el("button", "modal__button modal__button--primary", t("AIP_OPEN_SETTINGS", "Open settings"));
          open.type = "button";
          open.addEventListener("click", openAiSettings);
          notice.appendChild(open);
        }
      } else if (!currentModel()) {
        notice.hidden = false;
        notice.appendChild(el("p", "aip__p", t("AIP_NO_MODEL", "No model chosen yet. Pick one in the header or in Settings -> AI assistant.")));
      }
    };

    view.renderAll = () => { view.renderNotice(); view.renderHeader(); view.renderList(); view.renderMessages(); view.renderInput(); };

    view.select = async (id) => {
      view.chatId = id;
      view.forceBottom = true;                                  // ein geoeffneter Chat beginnt unten
      try { if (id) localStorage.setItem(KEY, id); else localStorage.removeItem(KEY); } catch (err) { /* ohne Speicher */ }
      if (id) { try { await loadChat(id); markSeen(id); } catch (err) { view.chatId = null; } }
      view.renderAll();
      if (root.classList.contains("aip--narrow")) root.classList.remove("aip--list");
      text.focus();
    };

    view.ensureChat = () => {
      if (view.chatId && !S.chats.some((c) => c.id === view.chatId)) view.chatId = null;
      if (!view.chatId && S.chats.length) { view.select(S.chats[0].id); return; }
      view.renderAll();
    };

    async function createChat() {
      try {
        const created = await api("POST", "/api/ai/chats", { model: view.pendingModel || undefined, mode: view.pendingMode || S.defaultMode });
        S.cache[created.id] = created;
        touchList(created.id, { title: "", model: created.model, mode: created.mode, messages: 0, updated: created.updated });
        view.pendingModel = "";
        view.pendingMode = "";                                      // der naechste neue Chat startet wieder im Standardmodus der Einstellungen
        await view.select(created.id);
        return created.id;
      } catch (err) {
        if (typeof _showToast === "function") _showToast(err.message, "error", 3500);
        return null;
      }
    }

    // ---- Diktieren: Mikrofon-Knopf -> Balken waehrend der Aufnahme -> "Fertig" schreibt um und setzt den Text in das Eingabefeld (abgeschickt wird von Hand)
    const D = () => window.OCDictation;
    const BARS = 30;
    const levels = new Array(BARS).fill(0);
    let dictating = false;                               // dieses Panel hat die Aufnahme gestartet
    const bars = [];
    const dictInfo = el("div", "aip__dictate-info");
    const barBox = el("div", "aip__dictate-bars");
    for (let i = 0; i < BARS; i++) { const b = el("span", "aip__dictate-bar"); bars.push(b); barBox.appendChild(b); }
    const dictTime = el("span", "aip__dictate-time", "0:00");
    const dictCancel = el("button", "aip__dictate-btn aip__dictate-btn--cancel");
    dictCancel.type = "button"; dictCancel.appendChild(Icons.svg("close"));
    const dictDone = el("button", "aip__dictate-btn aip__dictate-btn--done");
    dictDone.type = "button"; dictDone.appendChild(Icons.svg("check"));
    const dictProgress = el("div", "aip__dictate-progress");
    const dictProgressFill = el("div", "aip__dictate-progress-fill");
    dictProgress.appendChild(dictProgressFill);
    dict.append(dictCancel, el("span", "aip__dictate-dot"), barBox, dictInfo, dictTime, dictProgress, dictDone);
    const toast = (key, fallback, type) => { if (typeof _showToast === "function") _showToast(t(key, fallback), type || "warn", 4500); };
    const fmtTime = (s) => Math.floor(s / 60) + ":" + String(Math.floor(s % 60)).padStart(2, "0");

    function renderDictation() {
      const d = D();
      const available = !!d && d.available();
      const busyElsewhere = !!d && !dictating && ["recording", "transcribing", "downloading"].includes(d.status().state);
      mic.hidden = !available || dictating;
      mic.disabled = !S.enabled || busyElsewhere;
      mic.title = t("DICT_START", "Dictate (speech to text)");
      mic.setAttribute("aria-label", mic.title);
      dict.hidden = !dictating;
      text.hidden = dictating;
      if (dictating) send.disabled = true;
      dictCancel.title = t("DICT_CANCEL", "Discard");
      dictDone.title = t("DICT_DONE", "Done - write the text");
      if (dictating && d) paintDictation(d.status());
    }
    function paintDictation(st) {
      const recording = st.state === "recording";
      const working = st.state === "transcribing" || st.state === "downloading";
      dict.classList.toggle("aip__dictate--rec", recording);
      dict.classList.toggle("aip__dictate--work", working);
      barBox.hidden = !recording;
      dictTime.hidden = !recording;
      dictDone.hidden = !recording;
      dictInfo.hidden = recording;
      dictProgress.hidden = st.state !== "downloading";
      if (recording) {
        bars.forEach((b, i) => { b.style.height = Math.max(8, Math.round(levels[i] * 100)) + "%"; });
        dictTime.textContent = fmtTime(st.seconds || 0);
      } else if (st.state === "downloading") {
        dictInfo.textContent = t("DICT_DOWNLOADING", "Loading the speech model ({p} %) - only the first time...").replace("{p}", Math.round(st.percent || 0));
        dictProgressFill.style.width = Math.max(2, st.percent || 0) + "%";
      } else if (st.state === "transcribing") {
        dictInfo.textContent = t("DICT_TRANSCRIBING", "Writing it down...");
      }
    }
    function onDictation(st, extra) {
      if (!root.isConnected) return;
      if (extra && extra.level) {
        levels.push(st.level || 0); levels.shift();
        if (dictating) {
          paintDictation(st);
          if ((st.seconds || 0) >= (st.limit_s || 120) - 0.5 && st.state === "recording") finishDictation();         // laengste Aufnahme erreicht
        }
        return;
      }
      if (!dictating) { mic.disabled = !S.enabled || ["recording", "transcribing", "downloading"].includes(st.state); return; }
      paintDictation(st);
    }
    async function startDictation() {
      const d = D();
      if (!d || dictating) return;
      dictating = true;
      levels.fill(0);
      renderDictation();
      const r = await d.start();
      if (!r || !r.ok) {
        dictating = false;
        renderDictation();
        if (typeof _showToast === "function") _showToast(t("DICT_FAILED", "Dictation did not start: {e}").replace("{e}", d.errorText(r && r.error)), "warn", 5000);
      }
    }
    async function finishDictation() {
      const d = D();
      if (!d || !dictating) return;
      const r = await d.stop();
      dictating = false;
      renderDictation();
      if (!r || !r.ok) {
        if (r && r.error === "cancelled") return;
        if (typeof _showToast === "function") _showToast(t("DICT_FAILED", "Dictation did not start: {e}").replace("{e}", d.errorText(r && r.error)), "warn", 5000);
        return;
      }
      const add = String(r.text || "").trim();
      if (!add) { toast("DICT_NOTHING", "Nothing was understood.", "info"); return; }
      const cur = text.value;
      text.value = cur && !/\s$/.test(cur) ? cur + " " + add : cur + add;
      text.dispatchEvent(new Event("input"));
      text.focus();
      text.setSelectionRange(text.value.length, text.value.length);
    }
    async function cancelDictation() {
      const d = D();
      if (!d || !dictating) return;
      dictating = false;
      renderDictation();
      await d.cancel();
    }
    mic.addEventListener("click", startDictation);
    dictDone.addEventListener("click", finishDictation);
    dictCancel.addEventListener("click", cancelDictation);
    dict.addEventListener("keydown", (e) => { if (e.key === "Escape") { e.preventDefault(); cancelDictation(); } });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && dictating && root.isConnected) cancelDictation(); });
    if (window.OCDictation) {
      const off = window.OCDictation.subscribe((st, extra) => { if (!root.isConnected && view.seen) { off(); return; } onDictation(st, extra); });
    }

    /** Sendet eine Nachricht; gibt es noch keinen Chat (erster Start), entsteht er jetzt von selbst. */
    async function sendText(value) {
      value = String(value || "").trim();
      if (!value || !S.enabled) return;
      if (!view.chatId) { if (!(await createChat())) return; }
      if (running()) return;
      S.running.add(view.chatId);
      view.renderInput();
      view.forceBottom = true;                                    // wer sendet, will die Antwort sehen
      view.renderLive(true);                                      // die Punkte erscheinen sofort, noch bevor der Server antwortet
      client.send("ai_send", { chat_id: view.chatId, text: value, mode: currentMode() });
    }

    // ---- "/": eine Funktion von Hand aufrufen (ohne dass die KI antwortet): /read_fixtures {"fixtures": "6-8"}, /read_fixtures 6-8, /help
    let slashItems = [];
    let slashIndex = 0;
    const shortText = (value) => { const s = String(value || "").replace(/\s+/g, " ").trim(); const first = s.split(/[.!?]\s/)[0]; return first.length > 90 ? first.slice(0, 87) + "..." : first; };
    async function ensureTools() {
      if (S.tools) return S.tools;
      try { S.tools = [].concat(...((await api("GET", "/api/ai/tools")).collections || []).map((c) => c.tools)); } catch (err) { S.tools = []; }
      return S.tools;
    }
    function renderSlash() {
      slash.textContent = "";
      slashItems.forEach((tool, i) => {
        const b = el("button", "aip__slash-item" + (i === slashIndex ? " aip__slash-item--on" : ""));
        b.type = "button";
        b.dataset.name = tool.name;
        b.setAttribute("role", "option");
        const kind = ACCESS_LABEL[tool.access];
        b.append(el("span", "aip__slash-name", "/" + tool.name), kind ? el("span", "aip__slash-kind", t(kind[0], kind[1])) : document.createTextNode(""), el("span", "aip__slash-desc", tool.name === "help" ? t("AIP_SLASH_HELP", "Lists all functions and how to call them") : shortText(tool.description)));
        b.addEventListener("mousedown", (e) => { e.preventDefault(); acceptSlash(tool); });             // mousedown: das Textfeld behaelt den Fokus
        slash.appendChild(b);
      });
      slash.hidden = !slashItems.length;
      const on = slash.querySelector(".aip__slash-item--on");
      if (on && on.scrollIntoView) on.scrollIntoView({ block: "nearest" });
    }
    async function updateSlash() {
      const found = /^\/([A-Za-z_0-9]*)$/.exec(text.value);                        // nur solange der Name getippt wird
      if (!found) { slashItems = []; renderSlash(); return; }
      const all = [{ name: "help", access: "free", description: "" }].concat(await ensureTools());
      const q = found[1].toLowerCase();
      slashItems = all.filter((x) => x.name.toLowerCase().includes(q)).sort((a, b) => (b.name.toLowerCase().startsWith(q) ? 1 : 0) - (a.name.toLowerCase().startsWith(q) ? 1 : 0));
      slashIndex = 0;
      if (/^\/([A-Za-z_0-9]*)$/.test(text.value)) renderSlash(); else { slashItems = []; renderSlash(); }
    }
    function acceptSlash(tool) {
      text.value = "/" + tool.name + (tool.name === "help" ? "" : " ");
      slashItems = [];
      renderSlash();
      autosize();
      text.focus();
    }

    function autosize() {
      const rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
      text.style.height = "auto";
      text.style.height = Math.min(text.scrollHeight, 9 * rem) + "px";
    }

    function submit() {
      if (running()) { client.send("ai_stop", { chat_id: view.chatId }); return; }
      const value = text.value.trim();
      if (!value) return;
      text.value = "";
      slashItems = [];
      renderSlash();
      autosize();
      sendText(value);
    }

    send.addEventListener("click", submit);
    text.addEventListener("keydown", (e) => {
      if (!slash.hidden && slashItems.length && !e.isComposing) {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); slashIndex = (slashIndex + (e.key === "ArrowDown" ? 1 : slashItems.length - 1)) % slashItems.length; renderSlash(); return; }
        if (e.key === "Escape") { slashItems = []; renderSlash(); return; }
        const exact = text.value.trim().toLowerCase() === "/" + slashItems[slashIndex].name.toLowerCase();
        if (e.key === "Tab" || (e.key === "Enter" && !e.shiftKey && !exact)) { e.preventDefault(); acceptSlash(slashItems[slashIndex]); return; }          // Enter bei vollstaendigem Namen sendet
      }
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); submit(); }
    });
    text.addEventListener("input", () => { autosize(); updateSlash(); });
    text.addEventListener("blur", () => { slashItems = []; renderSlash(); });
    newButton.addEventListener("click", () => { view.pendingMode = ""; createChat(); });          // ein neuer Chat startet im Standardmodus der Einstellungen
    toggleList.addEventListener("click", () => {
      if (root.classList.contains("aip--narrow")) root.classList.toggle("aip--list");          // schmal: die Liste liegt ueber dem Verlauf (nicht gemerkt)
      else {
        const off = root.classList.toggle("aip--side-off");
        try { localStorage.setItem(LIST_KEY, off ? "1" : "0"); } catch (err) { /* ohne Speicher */ }
      }
      syncToggle();
    });
    title.addEventListener("dblclick", () => {
      if (!view.chatId) return;
      const input = el("input", "aip__rename");
      input.value = title.textContent; input.maxLength = 80;
      title.textContent = ""; title.appendChild(input); input.focus(); input.select();
      let done = false;
      const finish = async (apply) => {
        if (done) return; done = true;
        if (apply && input.value.trim()) { try { await api("PATCH", "/api/ai/chats/" + view.chatId, { title: input.value }); } catch (err) { /* bleibt */ } }
        view.renderHeader();
      };
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") finish(true); else if (e.key === "Escape") finish(false); });
      input.addEventListener("blur", () => finish(true));
    });

    if (typeof ResizeObserver !== "undefined") {
      new ResizeObserver(() => { const narrow = root.clientWidth < 34 * parseFloat(getComputedStyle(root).fontSize || 16); root.classList.toggle("aip--narrow", narrow); if (!narrow) root.classList.remove("aip--list"); syncToggle(); }).observe(root);
    }

    syncToggle();
    views.add(view);
    view.renderAll();
    (async () => {
      if (!S.loaded) await loadAll();
      loadModels(false);
      if (view.chatId) { try { await loadChat(view.chatId); markSeen(view.chatId); } catch (err) { view.chatId = null; } }
      if (!view.chatId && S.chats.length) { view.chatId = S.chats[0].id; await loadChat(view.chatId).catch(() => {}); markSeen(view.chatId); }
      view.renderAll();
    })();
    document.addEventListener("i18n-applied", () => { if (root.isConnected) { syncToggle(); jump.title = t("AIP_JUMP_BOTTOM", "Jump to the latest message"); view.renderAll(); } });
    return root;
  }

  window.__panelPlugins.register({ type: "assistant", buildContent: buildPanel });
  if (typeof PANEL_TITLE_KEYS !== "undefined") PANEL_TITLE_KEYS.assistant = "PANEL_ASSISTANT";
  window.OCAiPanel = { state: S, modes: MODES, splitTurns };          // fuer Tests
})();
