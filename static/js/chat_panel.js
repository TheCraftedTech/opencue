// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Panel "Chat & Notizen": Unterhaltungen zwischen den verbundenen Geraeten und Notizen / Checklisten in Markdown (app/notebook.py, /api/notebook).
 * Alles liegt als Dateien auf dem Server; jedes Panel auf jedem Geraet zeigt dieselben Eintraege. Aenderungen kommen als WebSocket-Nachricht `notebook_event`.
 *  - Chat: Nachrichten mit Namen des Absenders (je Geraet frei waehlbar), Uhrzeit, Kopieren / Loeschen; Enter sendet, Umschalt+Enter macht eine neue Zeile.
 *  - Notiz: Markdown mit Werkzeugleiste (fett, kursiv, unterstrichen, durchgestrichen, Ueberschrift, Liste, Nummerierung, Checkbox, Zitat, Code); Ansicht oder Bearbeiten;
 *    Checkboxen lassen sich in der Ansicht direkt abhaken; automatisch gespeichert; wer gleichzeitig schreibt, ueberschreibt (der letzte Stand gewinnt).
 * Der Text im Panel ist markier- und kopierbar. Laeuft nach app.js. */
(function () {
  "use strict";

  const t = (key, fallback) => { try { const v = typeof i18n === "function" ? i18n(key) : ""; return v && v !== key ? v : (fallback !== undefined ? fallback : key); } catch (err) { return fallback !== undefined ? fallback : key; } };
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const isRemote = () => document.documentElement.classList.contains("is-remote");

  const CID_KEY = "opencue.chat.cid";
  const NAME_KEY = "opencue.chat.name";
  const SEEN_KEY = "opencue.chat.seen";

  const S = { threads: [], cache: {}, typing: {}, loaded: false, limits: { text: 4000, body: 100000, title: 80, name: 40 }, seen: {}, unread: new Set() };
  const views = new Set();

  // ------------------------------------------------------------------------------------------ Kennung und Name dieses Geraets
  function cid() {
    let v = "";
    try { v = localStorage.getItem(CID_KEY) || ""; } catch (err) { /* ohne Speicher */ }
    if (!v) {
      v = Math.random().toString(36).slice(2, 12) + Date.now().toString(36).slice(-3);
      try { localStorage.setItem(CID_KEY, v); } catch (err) { /* ohne Speicher */ }
    }
    return v;
  }
  function defaultName() {
    if (!isRemote()) return t("CHP_CONSOLE", "Console");
    let n = 0;
    for (const c of cid()) n = (n * 31 + c.charCodeAt(0)) % 90;
    return t("CHP_REMOTE", "Remote") + " " + (n + 10);
  }
  function myName() {
    let v = "";
    try { v = localStorage.getItem(NAME_KEY) || ""; } catch (err) { /* ohne Speicher */ }
    return v.trim() || defaultName();
  }
  function setMyName(value) {
    const v = String(value || "").replace(/\s+/g, " ").trim().slice(0, S.limits.name);
    try { if (v) localStorage.setItem(NAME_KEY, v); else localStorage.removeItem(NAME_KEY); } catch (err) { /* ohne Speicher */ }
  }
  try { S.seen = JSON.parse(localStorage.getItem(SEEN_KEY) || "{}") || {}; } catch (err) { S.seen = {}; }
  const saveSeen = () => { try { localStorage.setItem(SEEN_KEY, JSON.stringify(S.seen)); } catch (err) { /* ohne Speicher */ } };

  async function api(method, path, body) {
    const res = await fetch(path, { method, cache: "no-store", headers: body !== undefined ? { "Content-Type": "application/json" } : {}, body: body !== undefined ? JSON.stringify(body) : undefined });
    let json = null;
    try { json = await res.json(); } catch (err) { /* keine JSON-Antwort */ }
    if (!res.ok) throw new Error((json && json.error && json.error.message) || ("HTTP " + res.status));
    return json;
  }

  const each = (fn) => { [...views].forEach((v) => { if (v.root.isConnected) { v.seen = true; fn(v); } else if (v.seen) views.delete(v); }); };

  async function copyText(text) {
    let ok = false;
    try { ok = typeof _copyText === "function" ? await _copyText(text) : (await navigator.clipboard.writeText(text), true); } catch (err) { ok = false; }
    if (typeof _showToast === "function") _showToast(t(ok ? "AIP_COPIED" : "AIP_COPY_FAILED", ok ? "Copied" : "Copying is not possible"), ok ? "info" : "error", 2000);
  }

  // ------------------------------------------------------------------------------------------ Markdown (eigener, kleiner Umsetzer; Text wird immer zuerst maskiert)
  const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ESC[c]);

  /** Zeichenformate: `Code`, **fett**, *kursiv* / _kursiv_, ++unterstrichen++, ~~durchgestrichen~~, [Text](https://...) und lose Web-Adressen. */
  function inline(text) {
    let s = esc(text);
    const codes = [];
    s = s.replace(/`([^`\n]+)`/g, (m, c) => { codes.push(c); return "\u0000" + (codes.length - 1) + "\u0000"; });
    s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/\+\+(.+?)\+\+/g, "<u>$1</u>");
    s = s.replace(/~~(.+?)~~/g, "<s>$1</s>");
    s = s.replace(/(^|[^*\w])\*(?![\s*])(.+?)\*(?![\w*])/g, "$1<em>$2</em>");
    s = s.replace(/(^|[^\w_])_(?![\s_])(.+?)_(?![\w_])/g, "$1<em>$2</em>");
    s = s.replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    s = s.replace(/(^|[\s(])(https?:\/\/[^\s<]+[^\s<.,;:!?)])/g, '$1<a href="$2" target="_blank" rel="noopener noreferrer">$2</a>');
    return s.replace(/\u0000(\d+)\u0000/g, (m, i) => "<code>" + codes[Number(i)] + "</code>");
  }

  const RE_TASK = /^(\s*)[-*+]\s+\[([ xX])\]\s+(.*)$/;
  const RE_UL = /^(\s*)[-*+]\s+(.*)$/;
  const RE_OL = /^(\s*)(\d+)[.)]\s+(.*)$/;

  /** Ganzer Text als HTML (Notiz). `interactive`: Checkboxen sind bedienbar (data-line = Zeilennummer im Quelltext). */
  function blocks(text, interactive) {
    const lines = String(text || "").replace(/\r\n/g, "\n").split("\n");
    const out = [];
    let para = [];
    let quote = [];
    let fence = null;
    const flush = () => {
      if (para.length) { out.push('<p class="chp-p">' + para.map(inline).join("<br>") + "</p>"); para = []; }
      if (quote.length) { out.push('<blockquote class="chp-quote">' + quote.map(inline).join("<br>") + "</blockquote>"); quote = []; }
    };
    lines.forEach((line, i) => {
      if (fence !== null) {
        if (/^\s*```/.test(line)) { out.push('<pre class="chp-pre"><code>' + esc(fence.join("\n")) + "</code></pre>"); fence = null; } else fence.push(line);
        return;
      }
      if (/^\s*```/.test(line)) { flush(); fence = []; return; }
      let m;
      if (!line.trim()) { flush(); return; }
      if ((m = /^(#{1,3})\s+(.*)$/.exec(line))) { flush(); out.push("<h" + (m[1].length + 1) + ' class="chp-h">' + inline(m[2]) + "</h" + (m[1].length + 1) + ">"); return; }
      if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) { flush(); out.push('<hr class="chp-hr">'); return; }
      if ((m = /^>\s?(.*)$/.exec(line))) { if (para.length) flush(); quote.push(m[1]); return; }
      if ((m = RE_TASK.exec(line))) {
        flush();
        const done = m[2] !== " ";
        out.push('<div class="chp-li chp-li--task' + (done ? " chp-li--done" : "") + '" style="--lvl:' + Math.floor(m[1].length / 2) + '"><input type="checkbox" class="chp-task" data-line="' + i + '"' + (done ? " checked" : "") + (interactive ? "" : " disabled") + '><span>' + inline(m[3]) + "</span></div>");
        return;
      }
      if ((m = RE_UL.exec(line))) { flush(); out.push('<div class="chp-li chp-li--ul" style="--lvl:' + Math.floor(m[1].length / 2) + '"><span class="chp-mark">&bull;</span><span>' + inline(m[2]) + "</span></div>"); return; }
      if ((m = RE_OL.exec(line))) { flush(); out.push('<div class="chp-li chp-li--ol" style="--lvl:' + Math.floor(m[1].length / 2) + '"><span class="chp-mark">' + esc(m[2]) + '.</span><span>' + inline(m[3]) + "</span></div>"); return; }
      if (quote.length) flush();
      para.push(line);
    });
    if (fence !== null) out.push('<pre class="chp-pre"><code>' + esc(fence.join("\n")) + "</code></pre>");
    flush();
    return out.join("");
  }

  /** Nachricht im Chat: Zeichenformate und Zeilenumbrueche (keine Bloecke). */
  const messageHtml = (text) => String(text).split("\n").map(inline).join("<br>");

  // ------------------------------------------------------------------------------------------ Zeit und Farben
  const hue = (name) => { let h = 0; for (const c of String(name)) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
  const authorColor = (name) => "hsl(" + hue(name) + " 70% 68%)";
  const clock = (ts) => new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const dayKey = (ts) => { const d = new Date(ts * 1000); return d.getFullYear() * 400 + d.getMonth() * 31 + d.getDate(); };
  function dayLabel(ts) {
    const now = Date.now() / 1000;
    if (dayKey(ts) === dayKey(now)) return t("CHP_TODAY", "Today");
    if (dayKey(ts) === dayKey(now - 86400)) return t("CHP_YESTERDAY", "Yesterday");
    return new Date(ts * 1000).toLocaleDateString([], { weekday: "short", day: "numeric", month: "short", year: "numeric" });
  }
  function shortTime(ts) {
    if (!ts) return "";
    return dayKey(ts) === dayKey(Date.now() / 1000) ? clock(ts) : new Date(ts * 1000).toLocaleDateString([], { day: "numeric", month: "short" });
  }
  const threadName = (th) => th.title || (th.kind === "note" ? t("CHP_DEFAULT_NOTE", "Note") : t("CHP_DEFAULT_CHAT", "Chat")) + " " + new Date((th.created || Date.now() / 1000) * 1000).toLocaleDateString([], { day: "numeric", month: "short" });

  // ------------------------------------------------------------------------------------------ gemeinsamer Zustand
  function touchList(summary) {
    const i = S.threads.findIndex((x) => x.id === summary.id);
    if (i >= 0) S.threads[i] = summary; else S.threads.unshift(summary);
    S.threads.sort((a, b) => (b.updated || 0) - (a.updated || 0));
  }

  async function loadList() {
    try {
      const data = await api("GET", "/api/notebook");
      S.threads = data.threads || [];
      if (data.limits) S.limits = data.limits;
      let fresh = false;
      S.threads.forEach((th) => { if (S.seen[th.id] === undefined) { S.seen[th.id] = th.updated || 0; fresh = true; } });          // was schon da war, gilt beim ersten Start als gelesen
      if (fresh) saveSeen();
    } catch (err) { /* offline: leere Liste */ }
    S.loaded = true;
    each((v) => v.renderAll());
  }

  async function loadThread(id) {
    if (S.cache[id]) return S.cache[id];
    const th = await api("GET", "/api/notebook/" + id);
    S.cache[id] = th;
    return th;
  }

  const isShown = (id) => document.visibilityState !== "hidden" && [...views].some((v) => v.threadId === id && v.root.isConnected);

  function markSeen(id) {
    S.seen[id] = Date.now() / 1000;
    S.unread.delete(id);
    saveSeen();
    each((v) => v.renderList());
  }
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") views.forEach((v) => { if (v.threadId && v.root.isConnected) markSeen(v.threadId); }); });

  const isUnread = (th) => {
    if (S.unread.has(th.id)) return true;
    if (th.kind === "chat" && th.last && th.last.cid && th.last.cid !== cid() && (th.last.ts || 0) > (S.seen[th.id] || 0)) return true;
    return false;
  };

  /** Abgelaufene "schreibt gerade"-Eintraege entfernen (nach 4,5 s ohne neues Signal) und die Anzeige nachfuehren. */
  let sweep = 0;
  function ensureSweep() {
    if (sweep) return;
    sweep = setInterval(() => {
      const now = Date.now();
      let any = false;
      Object.keys(S.typing).forEach((id) => Object.keys(S.typing[id]).forEach((k) => { if (S.typing[id][k].until <= now) delete S.typing[id][k]; else any = true; }));
      each((v) => v.renderTyping && v.renderTyping());
      if (!any) { clearInterval(sweep); sweep = 0; }
    }, 1000);
  }

  /** Ein Ereignis vom Server (jedes Geraet bekommt jedes Ereignis, auch das eigene). */
  function onEvent(p) {
    const id = p.id;
    const mine = p.by === cid() || (p.message && p.message.cid === cid());
    if (p.op === "reload") {                                                                          // eine Sicherung / ein Paket wurde eingelesen
      S.cache = {};
      loadList().then(() => each((v) => v.openThread(v.threadId)));
      return;
    }
    if (p.op === "typing") {
      if (!mine) {
        (S.typing[id] = S.typing[id] || {})[p.by] = { name: p.author, until: Date.now() + 4500, what: p.what };
        each((v) => { if (v.threadId === id) v.renderTyping(); });
        ensureSweep();
      }
      return;
    }
    if (p.op === "message" && S.typing[id]) delete S.typing[id][p.message.cid];                     // wer gesendet hat, schreibt nicht mehr
    if (p.op === "deleted") {
      S.threads = S.threads.filter((x) => x.id !== id);
      delete S.cache[id]; S.unread.delete(id);
      each((v) => { if (v.threadId === id) v.threadId = null; v.renderAll(); });
      return;
    }
    if (p.thread) touchList(p.thread);
    const cached = S.cache[id];
    if (p.op === "renamed" && cached) cached.title = p.thread.title;
    if (p.op === "message") {
      if (cached && !cached.messages.some((m) => m.id === p.message.id)) { cached.messages.push(p.message); cached.updated = p.thread.updated; }
      if (!mine) {
        if (isShown(id)) markSeen(id);
        else {
          S.unread.add(id);
          if (typeof _showToast === "function") _showToast(p.message.author + ": " + String(p.message.text).replace(/\s+/g, " ").slice(0, 80), "info", 4500);
        }
      } else S.seen[id] = Date.now() / 1000;
    }
    if (p.op === "message_deleted" && cached) cached.messages = cached.messages.filter((m) => m.id !== p.message_id);
    if (p.op === "note") {
      if (cached) { cached.body = p.body; cached.rev = p.rev; cached.updated = p.thread.updated; }
      if (!mine) {
        if (isShown(id)) { S.seen[id] = Date.now() / 1000; saveSeen(); } else S.unread.add(id);
        if (p.conflict && typeof _showToast === "function") _showToast(t("CHP_CHANGED_BY", "{name} edited this note at the same time - the last save wins.").replace("{name}", p.author || "?"), "info", 5000);
      }
    }
    each((v) => {
      v.renderList();
      if (v.threadId === id) {
        if (p.op === "note") v.applyRemoteNote();
        else if (p.op === "message" || p.op === "message_deleted") { v.renderHeader(); v.renderMessages(true); }          // das Eingabefeld darunter bleibt unberuehrt (Entwurf!)
        else v.renderHeader();
      } else if (p.op === "created" && !v.threadId) { v.threadId = id; v.openThread(id); }
    });
  }

  client.registerModule("notebook", {
    onMessage(message) {
      if (message.type === "notebook_event") onEvent(message.payload || {});
      else if (message.type === "state_snapshot" && S.loaded) { S.cache = {}; loadList().then(() => each((v) => v.openThread(v.threadId))); }          // nach dem Wiederverbinden alles neu holen
    },
  });

  // ------------------------------------------------------------------------------------------ Menue (an <body>, ueber allen Dialogen)
  let openMenu = null;
  function closeMenu() { if (openMenu) { openMenu.remove(); openMenu = null; } }
  document.addEventListener("pointerdown", (e) => { if (openMenu && !openMenu.contains(e.target)) closeMenu(); }, true);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeMenu(); });
  function popup(anchor, items) {
    closeMenu();
    const menu = el("div", "chp__ctx");
    menu.setAttribute("role", "menu");
    items.forEach((it) => {
      const b = el("button", "chp__ctx-item" + (it.danger ? " chp__ctx-item--danger" : ""));
      b.type = "button"; b.setAttribute("role", "menuitem");
      b.append(Icons.svg(it.icon), el("span", "", it.label));
      b.addEventListener("click", () => { closeMenu(); it.run(); });
      menu.appendChild(b);
    });
    document.body.appendChild(menu);
    const r = anchor.getBoundingClientRect();
    const w = menu.offsetWidth, h = menu.offsetHeight;
    menu.style.left = Math.max(4, Math.min(window.innerWidth - w - 4, r.right - w)) + "px";
    menu.style.top = Math.max(4, Math.min(window.innerHeight - h - 4, r.bottom + 4)) + "px";
    openMenu = menu;
    const first = menu.querySelector("button");
    if (first) first.focus();
  }

  // ------------------------------------------------------------------------------------------ Textfeld-Werkzeuge der Notiz
  /** Ersetzt einen Bereich so, dass Rueckgaengig (Strg+Z) funktioniert; danach ist `selStart..selEnd` markiert. */
  function replaceRange(ta, start, end, text, selStart, selEnd) {
    ta.focus();
    ta.setSelectionRange(start, end);
    let done = false;
    try { done = document.execCommand("insertText", false, text); } catch (err) { done = false; }
    if (!done || ta.value.slice(start, start + text.length) !== text) { ta.setRangeText(text, start, end, "end"); ta.dispatchEvent(new Event("input", { bubbles: true })); }
    ta.setSelectionRange(selStart === undefined ? start + text.length : selStart, selEnd === undefined ? start + text.length : selEnd);
  }

  function wrap(ta, left, right) {
    const v = ta.value, s = ta.selectionStart, e = ta.selectionEnd, sel = v.slice(s, e);
    if (sel.length >= left.length + right.length && sel.startsWith(left) && sel.endsWith(right)) {          // schon umschlossen: wieder entfernen
      const inner = sel.slice(left.length, sel.length - right.length);
      replaceRange(ta, s, e, inner, s, s + inner.length);
    } else if (v.slice(s - left.length, s) === left && v.slice(e, e + right.length) === right) {
      replaceRange(ta, s - left.length, e + right.length, sel, s - left.length, s - left.length + sel.length);
    } else {
      replaceRange(ta, s, e, left + sel + right, s + left.length, s + left.length + sel.length);
    }
  }

  const LINE_PREFIX = { ul: /^(\s*)[-*+]\s(?!\[[ xX]\]\s)/, todo: /^(\s*)[-*+]\s\[[ xX]\]\s/, ol: /^(\s*)\d+[.)]\s/, quote: /^>\s?/, h: /^#{1,3}\s/ };
  const stripPrefix = (line) => line.replace(LINE_PREFIX.todo, "$1").replace(LINE_PREFIX.ul, "$1").replace(LINE_PREFIX.ol, "$1").replace(LINE_PREFIX.quote, "").replace(LINE_PREFIX.h, "");

  /** Zeilenanfang-Formate (Liste, Nummerierung, Checkbox, Zitat, Ueberschrift) fuer alle markierten Zeilen. */
  function linePrefix(ta, kind) {
    const v = ta.value;
    let s = ta.selectionStart, e = ta.selectionEnd;
    const ls = v.lastIndexOf("\n", s - 1) + 1;
    if (e > s && v[e - 1] === "\n") e -= 1;
    let le = v.indexOf("\n", e);
    if (le < 0) le = v.length;
    const lines = v.slice(ls, le).split("\n");
    let result;
    if (kind === "h") {
      result = lines.map((ln) => {
        const m = /^(#{1,3})\s/.exec(ln);
        const level = m ? m[1].length : 0;
        const base = ln.replace(LINE_PREFIX.h, "");
        return level >= 3 ? base : "#".repeat(level + 1) + " " + base;
      });
    } else {
      const re = LINE_PREFIX[kind];
      const all = lines.every((ln) => !ln.trim() || re.test(ln));
      result = lines.map((ln, i) => {
        if (all) return ln.replace(re, kind === "quote" ? "" : "$1");
        const body = stripPrefix(ln);
        const indent = /^\s*/.exec(body)[0];
        const rest = body.slice(indent.length);
        const mark = kind === "ul" ? "- " : kind === "todo" ? "- [ ] " : kind === "quote" ? "> " : (i + 1) + ". ";
        return kind === "quote" ? mark + body : indent + mark + rest;
      });
    }
    const text = result.join("\n");
    replaceRange(ta, ls, le, text, ls, ls + text.length);
  }

  /** Enter in einer Liste: naechster Punkt; Enter in einem leeren Punkt beendet die Liste. Gibt true zurueck, wenn die Taste behandelt wurde. */
  function continueList(ta) {
    if (ta.selectionStart !== ta.selectionEnd) return false;
    const v = ta.value, pos = ta.selectionStart;
    const ls = v.lastIndexOf("\n", pos - 1) + 1;
    let le = v.indexOf("\n", pos);
    if (le < 0) le = v.length;
    const line = v.slice(ls, le);
    let m, prefix = "", body = "";
    if ((m = /^(\s*[-*+]\s\[[ xX]\]\s)(.*)$/.exec(line))) { prefix = m[1].replace(/\[[xX]\]/, "[ ]"); body = m[2]; }
    else if ((m = /^(\s*[-*+]\s)(.*)$/.exec(line))) { prefix = m[1]; body = m[2]; }
    else if ((m = /^(\s*)(\d+)([.)]\s)(.*)$/.exec(line))) { prefix = m[1] + (Number(m[2]) + 1) + m[3]; body = m[4]; }
    else if ((m = /^(>\s?)(.*)$/.exec(line))) { prefix = m[1]; body = m[2]; }
    else return false;
    if (pos < ls + line.length - body.length) return false;                      // Cursor steht noch im Zeilenanfang (Markierung): normales Enter
    if (!body.trim()) { replaceRange(ta, ls, le, "", ls, ls); return true; }          // leerer Punkt: Liste beenden
    replaceRange(ta, pos, pos, "\n" + prefix);
    return true;
  }

  /** Tab / Umschalt+Tab in Listen: um zwei Leerzeichen ein- bzw. ausruecken. */
  function indentLines(ta, outdent) {
    const v = ta.value;
    let s = ta.selectionStart, e = ta.selectionEnd;
    const ls = v.lastIndexOf("\n", s - 1) + 1;
    if (e > s && v[e - 1] === "\n") e -= 1;
    let le = v.indexOf("\n", e);
    if (le < 0) le = v.length;
    const lines = v.slice(ls, le).split("\n").map((ln) => (outdent ? ln.replace(/^ {1,2}/, "") : "  " + ln));
    const text = lines.join("\n");
    replaceRange(ta, ls, le, text, ls, ls + text.length);
  }

  // ------------------------------------------------------------------------------------------ das Panel
  function buildPanel(panel) {
    const root = el("div", "chp");
    const view = { root, threadId: null, seen: false, panelId: panel && panel.id ? panel.id : "", mode: "view", saveTimer: 0, saving: false, dirty: false, lastBody: "", baseRev: 0 };
    const KEY = "oc-chat-thread-" + view.panelId;
    const LIST_KEY = "oc-chat-list-off-" + view.panelId;
    try { view.threadId = localStorage.getItem(KEY) || null; } catch (err) { /* ohne Speicher */ }
    try { if (localStorage.getItem(LIST_KEY) === "1") root.classList.add("chp--side-off"); } catch (err) { /* ohne Speicher */ }

    // ---- Kopf
    const header = el("div", "chp__header");
    const toggleList = el("button", "chp__icon");
    toggleList.type = "button"; toggleList.appendChild(Icons.svg("sidebar"));
    const title = el("div", "chp__title");
    const renameBtn = el("button", "chp__icon"); renameBtn.type = "button"; renameBtn.appendChild(Icons.svg("edit"));
    const exportBtn = el("button", "chp__icon"); exportBtn.type = "button"; exportBtn.appendChild(Icons.svg("download"));
    const deleteBtn = el("button", "chp__icon"); deleteBtn.type = "button"; deleteBtn.appendChild(Icons.svg("trash"));
    const newBtn = el("button", "chp__icon chp__new"); newBtn.type = "button"; newBtn.appendChild(Icons.svg("plus"));
    header.append(toggleList, title, renameBtn, exportBtn, deleteBtn, newBtn);

    // ---- Liste links
    const side = el("div", "chp__side");
    const list = el("div", "chp__list");
    const me = el("div", "chp__me");
    side.append(list, me);

    // ---- Hauptflaeche rechts
    const main = el("div", "chp__main");
    const body = el("div", "chp__body");
    body.append(side, main);
    root.append(header, body);

    const syncToggle = () => {
      const narrow = root.classList.contains("chp--narrow");
      const shown = narrow ? root.classList.contains("chp--list") : !root.classList.contains("chp--side-off");
      toggleList.title = shown ? t("CHP_LIST_HIDE", "Hide the list") : t("CHP_LIST_SHOW", "Show the list");
      toggleList.setAttribute("aria-label", toggleList.title);
      toggleList.setAttribute("aria-pressed", shown ? "true" : "false");
    };

    const current = () => (view.threadId ? S.threads.find((x) => x.id === view.threadId) : null);

    // "X schreibt gerade ..." (Chat) bzw. "X bearbeitet die Notiz ..." (Notiz): kommt vom Server, laeuft nach 4,5 s ohne neues Signal ab
    let typingEl = null, noteTypingEl = null, lastTypingSent = 0;
    const typingNames = (what) => {
      const now = Date.now(), m = S.typing[view.threadId] || {};
      return Object.keys(m).filter((k) => m[k].until > now && m[k].what === what).map((k) => m[k].name);
    };
    view.renderTyping = () => {
      if (typingEl) {
        const names = typingNames("chat");
        let text = "";
        if (names.length === 1) text = t("CHP_TYPING_ONE", "{name} is typing").replace("{name}", names[0]);
        else if (names.length === 2) text = t("CHP_TYPING_TWO", "{a} and {b} are typing").replace("{a}", names[0]).replace("{b}", names[1]);
        else if (names.length > 2) text = t("CHP_TYPING_MANY", "Several people are typing");
        typingEl.classList.toggle("chp__typing--on", names.length > 0);
        typingEl.querySelector(".chp__typing-text").textContent = text;
      }
      if (noteTypingEl) {
        const names = typingNames("note");
        noteTypingEl.textContent = names.length ? t("CHP_EDITING", "{name} is editing").replace("{name}", names.join(", ")) : "";
      }
    };
    const notifyTyping = (what) => {
      const now = Date.now();
      if (!view.threadId || now - lastTypingSent < 2500) return;
      lastTypingSent = now;
      api("POST", "/api/notebook/" + view.threadId + "/typing", { cid: cid(), author: myName(), what }).catch(() => null);
    };

    view.renderHeader = () => {
      const th = current();
      if (!view.renaming) title.textContent = th ? threadName(th) : t("PANEL_CHAT", "Chat & Notes");          // waehrend des Umbenennens bleibt das Eingabefeld
      renameBtn.hidden = exportBtn.hidden = deleteBtn.hidden = !th;
      renameBtn.title = renameBtn.ariaLabel = t("CHP_RENAME", "Rename");
      deleteBtn.title = deleteBtn.ariaLabel = t("CHP_DELETE", "Delete");
      exportBtn.title = exportBtn.ariaLabel = t("CHP_EXPORT", "Save as a Markdown file");
      newBtn.title = newBtn.ariaLabel = t("CHP_NEW", "New chat or note");
    };

    view.renderList = () => {
      list.textContent = "";
      if (!S.threads.length) { list.appendChild(el("div", "chp__empty-list", S.loaded ? t("CHP_LIST_EMPTY", "No chats or notes yet.") : "...")); }
      S.threads.forEach((th) => {
        const row = el("div", "chp__row" + (th.id === view.threadId ? " chp__row--on" : "") + (isUnread(th) && th.id !== view.threadId ? " chp__row--unread" : ""));
        row.tabIndex = 0; row.setAttribute("role", "button"); row.dataset.id = th.id;
        const ico = Icons.svg(th.kind === "note" ? "notes" : "chat");
        const text = el("div", "chp__row-text");
        const head = el("div", "chp__row-head");
        head.append(el("span", "chp__row-title", threadName(th)));
        if (isUnread(th) && th.id !== view.threadId) head.appendChild(el("span", "chp__dot"));
        let meta = "";
        if (th.kind === "chat") meta = th.last ? th.last.author + ": " + th.last.text.replace(/\s+/g, " ") : t("CHP_EMPTY_SHORT", "No messages yet");
        else {
          meta = th.snippet || t("CHP_NOTE_EMPTY_SHORT", "Empty note");
          if (th.tasks && th.tasks.total) meta = th.tasks.done + "/" + th.tasks.total + " - " + meta;
        }
        text.append(head, el("div", "chp__row-meta", meta));
        const when = el("span", "chp__row-time", shortTime(th.updated));
        row.append(ico, text, when);
        const open = () => { closeMenu(); view.openThread(th.id); if (root.classList.contains("chp--narrow")) root.classList.remove("chp--list"); syncToggle(); };
        row.addEventListener("click", open);
        row.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
        list.appendChild(row);
      });
      if (view.editingName) return;                                       // waehrend der Name geaendert wird, bleibt das Eingabefeld
      me.textContent = "";
      const meBtn = el("button", "chp__me-btn");
      meBtn.type = "button";
      meBtn.append(el("span", "chp__me-label", t("CHP_YOUR_NAME", "Your name") + ":"), el("strong", "", myName()), Icons.svg("edit"));
      meBtn.title = t("CHP_NAME_HINT", "Shown next to your messages on all devices. Click to change.");
      meBtn.addEventListener("click", startNameEdit);
      me.appendChild(meBtn);
    };

    // ---- Chat-Ansicht ----------------------------------------------------------------------------------------------------
    let msgs = null, input = null, sendBtn = null, pill = null;
    const nearBottom = () => !msgs || msgs.scrollHeight - msgs.scrollTop - msgs.clientHeight < 90;
    const toBottom = () => { if (msgs) { msgs.scrollTop = msgs.scrollHeight; if (pill) pill.hidden = true; } };

    function messageNode(m, prev) {
      const mineMsg = m.cid === cid();
      const wrapper = el("div", "chp__msg" + (mineMsg ? " chp__msg--mine" : ""));
      wrapper.dataset.id = m.id;
      const sameAuthor = prev && prev.cid === m.cid && prev.author === m.author && (m.ts - prev.ts) < 300 && dayKey(prev.ts) === dayKey(m.ts);
      if (!sameAuthor) {
        const meta = el("div", "chp__meta");
        const who = el("span", "chp__author", m.author);
        who.style.color = authorColor(m.author);
        meta.append(who, el("span", "chp__time", clock(m.ts)));
        wrapper.appendChild(meta);
      }
      const line = el("div", "chp__line");
      const bubble = el("div", "chp__bubble");
      bubble.innerHTML = messageHtml(m.text);
      const actions = el("div", "chp__actions");
      const copy = el("button", "chp__mini"); copy.type = "button"; copy.title = t("CHP_COPY", "Copy"); copy.appendChild(Icons.svg("copy"));
      copy.addEventListener("click", () => copyText(m.text));
      const del = el("button", "chp__mini"); del.type = "button"; del.title = t("CHP_DELETE", "Delete"); del.appendChild(Icons.svg("trash"));
      del.addEventListener("click", async () => {
        if (!(await _askDelete("other", { title: t("CHP_DELETE_MSG_TITLE", "Delete message?"), body: t("CHP_DELETE_MSG_BODY", "The message will be deleted on all devices."), confirmKey: "LAYOUT_DELETE_CONFIRM" }))) return;
        try { await api("DELETE", "/api/notebook/" + view.threadId + "/messages/" + m.id + "?cid=" + encodeURIComponent(cid())); } catch (err) { if (typeof _showToast === "function") _showToast(err.message, "error", 3000); }
      });
      actions.append(copy, del);
      line.append(mineMsg ? actions : bubble, mineMsg ? bubble : actions);
      wrapper.appendChild(line);
      return wrapper;
    }

    function renderMessages(keep) {
      const th = S.cache[view.threadId];
      if (!msgs || !th) return;
      const stick = !keep || nearBottom();
      const before = msgs.scrollHeight - msgs.scrollTop;
      msgs.textContent = "";
      if (!th.messages.length) msgs.appendChild(el("div", "chp__hint", t("CHP_EMPTY_CHAT", "No messages yet. Write the first one.")));
      let prev = null;
      th.messages.forEach((m) => {
        if (!prev || dayKey(prev.ts) !== dayKey(m.ts)) msgs.appendChild(el("div", "chp__day", dayLabel(m.ts)));
        msgs.appendChild(messageNode(m, prev && dayKey(prev.ts) === dayKey(m.ts) ? prev : null));
        prev = m;
      });
      if (stick) toBottom(); else { msgs.scrollTop = msgs.scrollHeight - before; if (pill) pill.hidden = false; }
    }

    function buildChat() {
      main.textContent = "";
      msgs = el("div", "chp__msgs");
      pill = el("button", "chp__pill", t("CHP_NEW_BELOW", "New messages")); pill.type = "button"; pill.hidden = true;
      pill.addEventListener("click", toBottom);
      msgs.addEventListener("scroll", () => { if (pill && nearBottom()) pill.hidden = true; });
      const scroll = el("div", "chp__scroll"); scroll.append(msgs, pill);
      const bar = el("div", "chp__input");
      input = el("textarea", "chp__text");
      input.rows = 1; input.maxLength = S.limits.text; input.placeholder = t("CHP_PLACEHOLDER", "Write a message...");
      input.setAttribute("aria-label", input.placeholder);
      sendBtn = el("button", "chp__send"); sendBtn.type = "button"; sendBtn.title = sendBtn.ariaLabel = t("CHP_SEND", "Send");
      sendBtn.appendChild(Icons.svg("play"));
      bar.append(input, sendBtn);
      typingEl = el("div", "chp__typing");
      const dots = el("span", "chp__typing-dots"); dots.append(el("i"), el("i"), el("i"));
      typingEl.append(dots, el("span", "chp__typing-text"));
      noteTypingEl = null;
      main.append(scroll, typingEl, bar);
      const autosize = () => { const rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16; input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 8 * rem) + "px"; };
      const submit = async () => {
        const value = input.value.trim();
        if (!value || !view.threadId) return;
        input.value = ""; autosize();
        try {
          const message = await api("POST", "/api/notebook/" + view.threadId + "/messages", { author: myName(), cid: cid(), text: value });
          const th = S.cache[view.threadId];
          if (th && !th.messages.some((m) => m.id === message.id)) { th.messages.push(message); renderMessages(false); }
          toBottom();
        } catch (err) { input.value = value; autosize(); if (typeof _showToast === "function") _showToast(err.message, "error", 3500); }
        input.focus();
      };
      sendBtn.addEventListener("click", submit);
      input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); submit(); } });
      input.addEventListener("input", () => { autosize(); if (input.value.trim()) notifyTyping("chat"); });
      view.renderTyping();
    }

    // ---- Notiz-Ansicht ---------------------------------------------------------------------------------------------------
    let ta = null, rendered = null, status = null, tools = null, modeBtn = null;

    const setStatus = (text) => { if (status) status.textContent = text; };

    async function flushSave() {
      clearTimeout(view.saveTimer); view.saveTimer = 0;
      if (!view.dirty || !view.threadId || !ta) return;
      const id = view.threadId;
      const value = ta.value;
      view.dirty = false; view.saving = true; setStatus(t("CHP_SAVING", "Saving..."));
      try {
        const r = await api("PUT", "/api/notebook/" + id + "/body", { body: value, base_rev: view.baseRev, cid: cid(), author: myName() });
        view.baseRev = r.rev; view.lastBody = value;
        const th = S.cache[id];
        if (th) { th.body = value; th.rev = r.rev; }
        setStatus(view.dirty ? "" : t("CHP_SAVED", "Saved"));
        if (r.conflict && typeof _showToast === "function") _showToast(t("CHP_CHANGED_BY", "{name} edited this note at the same time - the last save wins.").replace("{name}", "?"), "info", 4000);
      } catch (err) { view.dirty = true; setStatus(t("CHP_SAVE_FAILED", "Not saved")); if (typeof _showToast === "function") _showToast(err.message, "error", 3500); }
      view.saving = false;
      if (view.dirty && !view.saveTimer) view.saveTimer = setTimeout(flushSave, 800);
    }
    const scheduleSave = () => { view.dirty = true; setStatus(t("CHP_SAVING", "Saving...")); clearTimeout(view.saveTimer); view.saveTimer = setTimeout(flushSave, 700); };
    view.flush = flushSave;

    function renderNoteView() {
      if (!rendered) return;
      const th = S.cache[view.threadId];
      const text = ta ? ta.value : (th ? th.body : "");
      rendered.innerHTML = text.trim() ? blocks(text, true) : "";
      if (!text.trim()) rendered.appendChild(el("div", "chp__hint", t("CHP_NOTE_EMPTY", "This note is empty. Click Edit and start writing - or use the buttons for lists and checkboxes.")));
    }

    function syncMode() {
      if (!ta) return;
      const edit = view.mode === "edit";
      ta.hidden = !edit; rendered.hidden = edit; tools.classList.toggle("chp__tools--off", !edit);
      modeBtn.textContent = "";
      modeBtn.append(Icons.svg(edit ? "eye" : "edit"), el("span", "", edit ? t("CHP_VIEW", "View") : t("CHP_EDIT", "Edit")));
      modeBtn.title = edit ? t("CHP_VIEW_TIP", "Show the finished note") : t("CHP_EDIT_TIP", "Edit the note");
      if (edit) { ta.focus(); } else { flushSave(); renderNoteView(); }
    }

    function buildNote() {
      main.textContent = "";
      tools = el("div", "chp__tools");
      const add = (label, tip, run, icon, extra) => {
        const b = el("button", "chp__tool" + (extra ? " " + extra : ""));
        b.type = "button"; b.title = b.ariaLabel = tip;
        if (icon) b.appendChild(Icons.svg(icon)); else b.textContent = label;
        b.addEventListener("mousedown", (e) => e.preventDefault());                     // das Textfeld behaelt Fokus und Markierung
        b.addEventListener("click", () => { run(); });
        tools.appendChild(b);
      };
      add("B", t("CHP_T_BOLD", "Bold (Ctrl+B)"), () => wrap(ta, "**", "**"), null, "chp__tool--b");
      add("I", t("CHP_T_ITALIC", "Italic (Ctrl+I)"), () => wrap(ta, "*", "*"), null, "chp__tool--i");
      add("U", t("CHP_T_UNDERLINE", "Underline (Ctrl+U)"), () => wrap(ta, "++", "++"), null, "chp__tool--u");
      add("S", t("CHP_T_STRIKE", "Strikethrough"), () => wrap(ta, "~~", "~~"), null, "chp__tool--s");
      tools.appendChild(el("span", "chp__sep"));
      add("H", t("CHP_T_HEADING", "Heading (click again for a smaller one)"), () => linePrefix(ta, "h"), null, "chp__tool--h");
      add("", t("CHP_T_UL", "Bulleted list"), () => linePrefix(ta, "ul"), "list");
      add("", t("CHP_T_OL", "Numbered list"), () => linePrefix(ta, "ol"), "olist");
      add("", t("CHP_T_TODO", "Checklist"), () => linePrefix(ta, "todo"), "todo");
      add("", t("CHP_T_QUOTE", "Quote"), () => linePrefix(ta, "quote"), "quote");
      add("", t("CHP_T_CODE", "Code"), () => wrap(ta, "`", "`"), "code");
      noteTypingEl = el("span", "chp__editing");
      typingEl = null;
      status = el("span", "chp__status");
      modeBtn = el("button", "chp__mode"); modeBtn.type = "button";
      const bar = el("div", "chp__notebar"); bar.append(tools, noteTypingEl, status, modeBtn);
      ta = el("textarea", "chp__note");
      ta.spellcheck = true; ta.maxLength = S.limits.body;
      ta.setAttribute("aria-label", t("CHP_NOTE_LABEL", "Note"));
      ta.placeholder = t("CHP_NOTE_HELP", "Markdown: **bold**, *italic*, ++underline++, - list, 1. numbered, - [ ] checkbox");
      rendered = el("div", "chp__rendered");
      main.append(bar, ta, rendered);
      const th = S.cache[view.threadId];
      ta.value = th ? th.body : "";
      view.lastBody = ta.value; view.baseRev = th ? th.rev : 0;
      ta.addEventListener("input", () => { scheduleSave(); notifyTyping("note"); });
      ta.addEventListener("blur", flushSave);
      ta.addEventListener("keydown", (e) => {
        if (e.isComposing) return;
        const mod = e.ctrlKey || e.metaKey;
        if (mod && !e.shiftKey && !e.altKey) {
          const k = e.key.toLowerCase();
          if (k === "b") { e.preventDefault(); wrap(ta, "**", "**"); return; }
          if (k === "i") { e.preventDefault(); wrap(ta, "*", "*"); return; }
          if (k === "u") { e.preventDefault(); wrap(ta, "++", "++"); return; }
        }
        if (e.key === "Enter" && !e.shiftKey && !mod && !e.altKey) { if (continueList(ta)) e.preventDefault(); return; }
        if (e.key === "Tab" && !mod && !e.altKey) {
          const v = ta.value, p = ta.selectionStart, ls = v.lastIndexOf("\n", p - 1) + 1, line = v.slice(ls, (v.indexOf("\n", p) < 0 ? v.length : v.indexOf("\n", p)));
          if (/^\s*([-*+]\s|\d+[.)]\s)/.test(line)) { e.preventDefault(); indentLines(ta, e.shiftKey); }
        }
        if (e.key === "Escape") { e.preventDefault(); view.mode = "view"; syncMode(); }
      });
      rendered.addEventListener("click", (e) => {
        const box = e.target.closest && e.target.closest("input.chp-task");
        if (box) {
          const line = Number(box.dataset.line);
          const rows = ta.value.split("\n");
          if (rows[line] !== undefined) {
            rows[line] = rows[line].replace(/\[([ xX])\]/, (m, c) => (c === " " ? "[x]" : "[ ]"));
            ta.value = rows.join("\n");
            renderNoteView(); scheduleSave(); flushSave();
          }
          return;
        }
        if (e.detail === 2 && !(e.target.closest && e.target.closest("a"))) { view.mode = "edit"; syncMode(); }                 // Doppelklick: bearbeiten
      });
      modeBtn.addEventListener("click", () => { view.mode = view.mode === "edit" ? "view" : "edit"; syncMode(); });
      view.mode = (th && th.body.trim()) ? "view" : "edit";
      syncMode();
    }

    /** Eine Aenderung von einem anderen Geraet: wer gerade tippt, behaelt den eigenen Stand (der naechste Speichervorgang gewinnt). */
    view.applyRemoteNote = () => {
      const th = S.cache[view.threadId];
      if (!th || !ta) { view.renderHeader(); return; }
      if (view.dirty || view.saving) return;
      if (ta.value !== th.body) {
        const s = ta.selectionStart, e = ta.selectionEnd;
        ta.value = th.body;
        ta.setSelectionRange(Math.min(s, ta.value.length), Math.min(e, ta.value.length));
      }
      view.baseRev = th.rev; view.lastBody = th.body;
      if (view.mode !== "edit") renderNoteView();
      view.renderHeader();
    };

    // ---- zusammenbauen
    view.renderMain = () => {
      const th = current();
      msgs = input = sendBtn = pill = null; ta = rendered = status = tools = modeBtn = null; typingEl = noteTypingEl = null;
      if (!th) {
        main.textContent = "";
        const empty = el("div", "chp__start");
        empty.append(el("div", "chp__hint", S.loaded ? t("CHP_START", "Start a chat with the other devices or write a note.") : "..."));
        const row = el("div", "chp__start-btns");
        const c = el("button", "chp__big"); c.type = "button"; c.append(Icons.svg("chat"), el("span", "", t("CHP_NEW_CHAT", "New chat")));
        const n = el("button", "chp__big"); n.type = "button"; n.append(Icons.svg("notes"), el("span", "", t("CHP_NEW_NOTE", "New note")));
        c.addEventListener("click", () => create("chat")); n.addEventListener("click", () => create("note"));
        row.append(c, n); empty.appendChild(row); main.appendChild(empty);
        return;
      }
      if (!S.cache[th.id]) { main.textContent = ""; main.appendChild(el("div", "chp__hint", "...")); return; }
      if (th.kind === "chat") { buildChat(); renderMessages(false); } else buildNote();
    };

    view.renderMessages = (keep) => renderMessages(keep);
    view.renderAll = () => { view.renderHeader(); view.renderList(); view.renderMain(); };

    view.openThread = async (id) => {
      await flushSave();
      view.dirty = false;
      view.threadId = id && S.threads.some((x) => x.id === id) ? id : null;
      try { if (view.threadId) localStorage.setItem(KEY, view.threadId); else localStorage.removeItem(KEY); } catch (err) { /* ohne Speicher */ }
      if (view.threadId) {
        try { await loadThread(view.threadId); } catch (err) { view.threadId = null; }
      }
      if (view.threadId) markSeen(view.threadId);
      view.renderAll();
      if (view.threadId && S.cache[view.threadId] && S.cache[view.threadId].kind === "chat" && input && !isRemote()) input.focus();
    };

    async function create(kind) {
      try {
        const th = await api("POST", "/api/notebook", { kind, cid: cid() });
        S.cache[th.id] = th;
        touchList({ id: th.id, kind: th.kind, title: th.title, created: th.created, updated: th.updated, rev: th.rev, count: 0, last: null, snippet: "", tasks: { done: 0, total: 0 } });
        view.threadId = null;
        await view.openThread(th.id);
        if (kind === "note") { view.mode = "edit"; syncMode(); }
      } catch (err) { if (typeof _showToast === "function") _showToast(err.message, "error", 3500); }
    }

    // ---- Bedienung
    newBtn.addEventListener("click", () => popup(newBtn, [
      { icon: "chat", label: t("CHP_NEW_CHAT", "New chat"), run: () => create("chat") },
      { icon: "notes", label: t("CHP_NEW_NOTE", "New note"), run: () => create("note") },
    ]));
    toggleList.addEventListener("click", () => {
      if (root.classList.contains("chp--narrow")) root.classList.toggle("chp--list");
      else {
        const off = root.classList.toggle("chp--side-off");
        try { localStorage.setItem(LIST_KEY, off ? "1" : "0"); } catch (err) { /* ohne Speicher */ }
      }
      syncToggle();
    });
    function startRename() {
      const th = current();
      if (!th) return;
      const field = el("input", "chp__rename");
      field.value = th.title || ""; field.placeholder = threadName(th); field.maxLength = S.limits.title;
      view.renaming = true;
      title.textContent = ""; title.appendChild(field); field.focus(); field.select();
      let done = false;
      const finish = async (apply) => {
        if (done) return; done = true;
        view.renaming = false;
        if (apply && field.value.trim() !== (th.title || "")) { try { await api("PATCH", "/api/notebook/" + th.id, { title: field.value, cid: cid() }); } catch (err) { /* bleibt */ } }
        view.renderHeader();
      };
      field.addEventListener("keydown", (e) => { e.stopPropagation(); if (e.key === "Enter") finish(true); else if (e.key === "Escape") finish(false); });
      field.addEventListener("blur", () => finish(true));
    }
    title.addEventListener("dblclick", startRename);
    renameBtn.addEventListener("click", startRename);
    exportBtn.addEventListener("click", async () => {
      const th = current();
      if (!th) return;
      if (view.dirty) await flushSave();                                             // erst den letzten Stand speichern, dann herunterladen
      const url = "/api/notebook/" + th.id + "/export";
      try {                                                                         // Programmfenster: der Server oeffnet den Standard-Browser (wie im Dateimanager)
        const res = await fetch("/api/files/open-download", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url }) });
        const body = await res.json();
        if (res.ok && body.opened) { if (typeof _showToast === "function") _showToast(t("FM_DL_STARTED", "Download started in the browser"), "info", 3000); return; }
      } catch (err) { /* dann laedt dieser Browser selbst */ }
      const link = document.createElement("a");
      link.href = url; link.download = "";
      document.body.appendChild(link); link.click(); link.remove();
    });
    deleteBtn.addEventListener("click", async () => {
      const th = current();
      if (!th) return;
      if (!(await _askDelete("other", { title: t("CHP_DELETE_THREAD_TITLE", "Delete this chat or note?"), body: t("CHP_DELETE_THREAD_BODY", "\"{name}\" and everything in it will be deleted on all devices. This cannot be undone.").replace("{name}", threadName(th)), confirmKey: "LAYOUT_DELETE_CONFIRM" }))) return;
      view.dirty = false;
      try { await api("DELETE", "/api/notebook/" + th.id + "?cid=" + encodeURIComponent(cid())); } catch (err) { if (typeof _showToast === "function") _showToast(err.message, "error", 3500); }
    });
    function startNameEdit() {
      const field = el("input", "chp__rename");
      field.value = myName(); field.maxLength = S.limits.name;
      view.editingName = true;
      me.textContent = ""; me.appendChild(field); field.focus(); field.select();
      let done = false;
      const finish = (apply) => { if (done) return; done = true; view.editingName = false; if (apply) setMyName(field.value); each((v) => v.renderList()); };
      field.addEventListener("keydown", (e) => { e.stopPropagation(); if (e.key === "Enter") finish(true); else if (e.key === "Escape") finish(false); });
      field.addEventListener("blur", () => finish(true));
    }

    if (typeof ResizeObserver !== "undefined") {
      new ResizeObserver(() => { const narrow = root.clientWidth < 32 * parseFloat(getComputedStyle(root).fontSize || 16); root.classList.toggle("chp--narrow", narrow); if (!narrow) root.classList.remove("chp--list"); syncToggle(); }).observe(root);
    }
    window.addEventListener("pagehide", () => { if (view.dirty) flushSave(); });

    syncToggle();
    views.add(view);
    view.renderAll();
    (async () => {
      if (!S.loaded) await loadList();
      if (view.threadId && !S.threads.some((x) => x.id === view.threadId)) view.threadId = null;
      if (!view.threadId && S.threads.length) view.threadId = S.threads[0].id;
      await view.openThread(view.threadId);
    })();
    document.addEventListener("i18n-applied", () => { if (root.isConnected) { syncToggle(); view.renderHeader(); view.renderList(); } });
    return root;
  }

  window.__panelPlugins.register({ type: "chat", buildContent: buildPanel });
  if (typeof PANEL_TITLE_KEYS !== "undefined") PANEL_TITLE_KEYS.chat = "PANEL_CHAT";
  window.OCChatPanel = { state: S, markdown: blocks, inline, cid, myName };          // fuer Tests
})();
