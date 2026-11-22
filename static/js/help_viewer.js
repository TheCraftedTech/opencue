// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Anleitungen im Programm (Hilfe -> Anleitungen, F1): zeigt die Dateien static/help/<seite>.<de|en>.md als Dialog - ohne Internet, mit Suche.
 *
 * Aufbau: links die Liste der Anleitungen (die aktive klappt ihre Ueberschriften auf; bei einer Suche stehen dort auch die Treffer je Abschnitt),
 * oben ein Suchfeld (Strg+F, Enter / Umschalt+Enter springt zum naechsten / vorigen Treffer, Esc loescht die Suche), rechts der Text im Stil der Oberflaeche.
 * Die Sprache folgt der Programmsprache (DE / EN umschaltbar; fehlt eine Datei, wird Englisch genommen). Der Markdown-Text wird NIE als HTML eingesetzt:
 * ein kleiner eigener Wandler baut DOM-Knoten (Ueberschriften, Absaetze, verschachtelte Listen, Tabellen, Zitate, Code, **fett**, *kursiv*, `Code`).
 *
 * Aufruf: window.OCHelp.open({ page: "error-codes", find: "OC-1002" })  (beides optional), window.OCHelp.focusSearch().
 * Neue Anleitung: Datei static/help/<name>.de.md + .en.md anlegen und den Namen in PAGES eintragen. */
(function () {
  "use strict";

  const PAGES = ["getting-started", "fixtures", "fixture-editor", "keyboard-shortcuts", "remote", "audio", "effect-studio", "commands", "voice-commands", "midi", "dmx-input", "timeline", "assistant", "chat", "api", "show-safety", "startup-options", "automation", "error-codes"];
  const MAX_RESULTS = 80;
  const ROOT = '[data-modal-backdrop="help"]';
  const STORE = "opencue.help";

  const t = (key, fallback) => { try { const v = typeof i18n === "function" ? i18n(key) : ""; return v && v !== key ? v : fallback; } catch (err) { return fallback; } };
  const $ = (selector) => document.querySelector(ROOT + " " + selector);
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const icon = (name) => (typeof Icons !== "undefined" && Icons.svg ? Icons.svg(name) : document.createTextNode(""));

  const state = {
    lang: "en", docs: {}, page: PAGES[0], query: "", marks: [], cur: -1, bound: false, ui: null, results: null, loading: null,
  };

  // ------------------------------------------------------------------------------------------------------ Markdown -> DOM
  const slug = (s) => s.toLowerCase().replace(/[^a-z0-9äöüß]+/g, "-").replace(/^-+|-+$/g, "") || "x";
  const INLINE = /(`[^`]+`)|(\*\*(?:[^*]|\*(?!\*))+\*\*)|(\*(?![\s*])(?:[^*`]|`[^`]*`)+?\*(?!\*))/;       // Code | fett | kursiv (kein Lookbehind: aeltere iPad-Browser)

  function inline(text, xref) {
    const nodes = [];
    let rest = text;
    while (rest) {
      const m = INLINE.exec(rest);
      if (!m) { nodes.push(document.createTextNode(rest)); break; }
      if (m.index > 0) nodes.push(document.createTextNode(rest.slice(0, m.index)));
      const token = m[0];
      if (m[3] && /\s\*$/.test(token)) {                                // "*" nach einem Leerzeichen schliesst nichts: wie ein normales Zeichen behandeln
        nodes.push(document.createTextNode("*"));
        rest = rest.slice(m.index + 1);
        continue;
      }
      if (m[1]) {
        nodes.push(el("code", "hv-code", token.slice(1, -1)));
      } else if (m[2]) {
        const strong = el("strong");
        strong.append(...inline(token.slice(2, -2), xref));
        nodes.push(strong);
      } else {
        const inner = token.slice(1, -1);
        const target = xref && xref(inner);
        if (target) {
          const link = el("a", "hv-xref");
          link.href = "#";
          link.dataset.hvPage = target;
          link.append(...inline(inner, null));
          nodes.push(link);
        } else {
          const em = el("em");
          em.append(...inline(inner, xref));
          nodes.push(em);
        }
      }
      rest = rest.slice(m.index + token.length);
    }
    return nodes;
  }

  const LIST_ITEM = /^(\s*)([-*]|\d+\.)\s+(.*)$/;
  const indentOf = (line) => line.match(/^\s*/)[0].length;
  const BLOCK_START = /^(```|#{1,4}\s|\||>|\s*([-*]|\d+\.)\s|---+\s*$)/;

  function parseList(lines, start, xref) {
    const base = indentOf(lines[start]);
    const list = el(/^\s*\d+\./.test(lines[start]) ? "ol" : "ul", "hv-list");
    let i = start;
    let last = null;
    while (i < lines.length) {
      const m = LIST_ITEM.exec(lines[i]);
      if (!m) break;
      const indent = m[1].length;
      if (indent < base) break;
      if (indent > base && last) {                                       // eingerueckt: Unterliste des letzten Punktes
        const [sub, next] = parseList(lines, i, xref);
        last.appendChild(sub);
        i = next;
        continue;
      }
      let text = m[3];
      i++;
      while (i < lines.length && lines[i].trim() !== "" && !LIST_ITEM.test(lines[i]) && indentOf(lines[i]) > base && !/^\s*```/.test(lines[i])) text += " " + lines[i++].trim();
      last = el("li");
      last.append(...inline(text, xref));
      list.appendChild(last);
      let j = i;                                                          // Leerzeile zwischen zwei Punkten derselben Liste
      while (j < lines.length && lines[j].trim() === "") j++;
      if (j > i && j < lines.length && LIST_ITEM.test(lines[j]) && indentOf(lines[j]) >= base) i = j;
    }
    return [list, i];
  }

  function blocks(lines, root, headings, ids, xref) {
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      let m;
      if ((m = /^```(\w*)\s*$/.exec(line))) {
        const code = [];
        i++;
        while (i < lines.length && !/^```\s*$/.test(lines[i])) code.push(lines[i++]);
        i++;
        const pre = el("pre", "hv-pre");
        pre.appendChild(el("code", "", code.join("\n")));
        root.appendChild(pre);
      } else if ((m = /^(#{1,4})\s+(.*\S)\s*$/.exec(line))) {
        const level = m[1].length;
        const heading = el("h" + level, "hv-h");
        let id = slug(m[2]);
        for (let n = 2; ids.has(id); n++) id = slug(m[2]) + "-" + n;
        ids.add(id);
        heading.id = "hv-" + id;
        heading.append(...inline(m[2], null));
        root.appendChild(heading);
        headings.push({ level, id: heading.id, text: heading.textContent, node: heading });
        i++;
      } else if (/^---+\s*$/.test(line)) {
        root.appendChild(el("hr", "hv-hr"));
        i++;
      } else if (/^\|/.test(line)) {
        const rows = [];
        while (i < lines.length && /^\|/.test(lines[i])) rows.push(lines[i++]);
        const cells = (row) => row.replace(/\\\|/g, "\u0001").replace(/^\||\|\s*$/g, "").split("|").map((c) => c.replace(/\u0001/g, "|").trim());
        const wrap = el("div", "hv-tablewrap");
        const table = el("table", "hv-table");
        const head = el("tr");
        cells(rows[0]).forEach((c) => { const th = el("th"); th.append(...inline(c, xref)); head.appendChild(th); });
        table.appendChild(head);
        rows.slice(/^\|[\s:|-]+\|?\s*$/.test(rows[1] || "") ? 2 : 1).forEach((row) => {
          const tr = el("tr");
          cells(row).forEach((c) => { const td = el("td"); td.append(...inline(c, xref)); tr.appendChild(td); });
          table.appendChild(tr);
        });
        wrap.appendChild(table);
        root.appendChild(wrap);
      } else if (/^>/.test(line)) {
        const inner = [];
        while (i < lines.length && /^>/.test(lines[i])) inner.push(lines[i++].replace(/^>\s?/, ""));
        const quote = el("blockquote", "hv-quote");
        blocks(inner, quote, [], new Set(), xref);
        root.appendChild(quote);
      } else if (LIST_ITEM.test(line)) {
        const [list, next] = parseList(lines, i, xref);
        root.appendChild(list);
        i = next;
      } else if (line.trim() === "") {
        i++;
      } else {
        const para = [];
        while (i < lines.length && lines[i].trim() !== "" && !(para.length && BLOCK_START.test(lines[i]))) para.push(lines[i++].trim());
        const p = el("p", "hv-p");
        p.append(...inline(para.join(" "), xref));
        root.appendChild(p);
      }
    }
  }

  /** Markdown -> { root, headings[], sections[] }; sections = Textabschnitte je Ueberschrift fuer die Suche. */
  function render(markdown, xref) {
    const root = el("div", "hv-md");
    const headings = [];
    blocks(markdown.replace(/\r/g, "").split("\n"), root, headings, new Set(), xref);
    const sections = [];
    let current = { id: "", title: "", level: 1, nodes: [] };
    sections.push(current);
    [...root.children].forEach((node) => {
      const h = headings.find((x) => x.node === node);
      if (h) { current = { id: h.id, title: h.text, level: h.level, nodes: [] }; sections.push(current); }
      current.nodes.push(node);
    });
    sections.forEach((s) => {
      s.text = s.nodes.map((n) => n.textContent).join("\n");
      s.lower = s.text.toLowerCase();
    });
    return { root, headings, sections: sections.filter((s) => s.text.trim()) };
  }

  // ------------------------------------------------------------------------------------------------------ Laden
  const titleOf = (md) => { const m = /^#\s+(.+?)\s*$/m.exec(md); return m ? m[1].replace(/[`*]/g, "") : ""; };

  async function fetchPage(lang, page) {
    const res = await fetch("/static/help/" + page + "." + lang + ".md", { cache: "no-cache" });
    if (!res.ok) throw new Error(page + " " + res.status);
    return res.text();
  }

  async function load(lang) {
    if (state.docs[lang]) return state.docs[lang];
    const texts = await Promise.all(PAGES.map(async (page) => {
      try { return [page, await fetchPage(lang, page), lang]; } catch (err) { /* Datei fehlt: Englisch */ }
      try { return [page, await fetchPage("en", page), "en"]; } catch (err) { return [page, "", lang]; }
    }));
    const titles = {};                                                   // kursive Namen einer Anleitung im Text werden zu Verweisen
    texts.forEach(([page, md]) => { const ti = titleOf(md); if (ti) titles[ti.toLowerCase()] = page; });
    const xref = (name) => titles[name.trim().toLowerCase()] || null;
    const docs = {};
    texts.forEach(([page, md, used]) => {
      if (!md) return;
      const built = render(md, xref);
      docs[page] = { page, title: titleOf(md) || page, lang: used, root: built.root, headings: built.headings, sections: built.sections };
    });
    state.docs[lang] = docs;
    return docs;
  }

  // ------------------------------------------------------------------------------------------------------ Suche
  const terms = () => state.query.toLowerCase().split(/\s+/).filter(Boolean);
  const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  function countIn(text, ts) {
    let n = 0;
    ts.forEach((term) => { let from = 0; for (;;) { const at = text.indexOf(term, from); if (at < 0) break; n++; from = at + term.length; } });
    return n;
  }

  function snippet(section, ts) {
    const text = section.text.replace(/\s+/g, " ");
    const low = text.toLowerCase();
    let at = -1;
    ts.forEach((term) => { const p = low.indexOf(term); if (p >= 0 && (at < 0 || p < at)) at = p; });
    const from = Math.max(0, at - 40);
    return (from > 0 ? "…" : "") + text.slice(from, from + 120) + (from + 120 < text.length ? "…" : "");
  }

  /** Treffer ueber alle Anleitungen: ein Abschnitt trifft, wenn ALLE Suchwoerter in ihm vorkommen. */
  function search() {
    const ts = terms();
    const docs = state.docs[state.lang] || {};
    const counts = {};
    const list = [];
    if (!ts.length) return { counts, list, ts, total: 0 };
    PAGES.forEach((page) => {
      const doc = docs[page];
      if (!doc) return;
      doc.sections.forEach((section) => {
        if (!ts.every((term) => section.lower.includes(term))) return;
        const n = countIn(section.lower, ts);
        counts[page] = (counts[page] || 0) + n;
        list.push({ page, doc, section, n });
      });
    });
    return { counts, list, ts, total: list.length };
  }

  function clearMarks(root) {
    root.querySelectorAll("mark.hv-mark").forEach((m) => { m.replaceWith(document.createTextNode(m.textContent)); });
    root.normalize();
  }

  function highlight(root, ts) {
    clearMarks(root);
    state.marks = [];
    state.cur = -1;
    if (!ts.length) return;
    const re = new RegExp(ts.slice().sort((a, b) => b.length - a.length).map(escapeRe).join("|"), "gi");
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    for (let n = walker.nextNode(); n; n = walker.nextNode()) nodes.push(n);
    nodes.forEach((node) => {
      const text = node.nodeValue;
      re.lastIndex = 0;
      let last = 0;
      let m;
      let frag = null;
      while ((m = re.exec(text))) {
        if (!m[0]) { re.lastIndex++; continue; }
        frag = frag || document.createDocumentFragment();
        if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
        const mark = el("mark", "hv-mark", m[0]);
        frag.appendChild(mark);
        state.marks.push(mark);
        last = m.index + m[0].length;
      }
      if (frag) {
        if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
        node.replaceWith(frag);
      }
    });
  }

  function select(index, scroll) {
    if (!state.marks.length) { state.cur = -1; updateCount(); return; }
    state.cur = (index + state.marks.length) % state.marks.length;
    state.marks.forEach((m, k) => m.classList.toggle("hv-mark--cur", k === state.cur));
    if (scroll !== false) state.marks[state.cur].scrollIntoView({ block: "center" });
    updateCount();
  }

  function updateCount() {
    const ui = state.ui;
    if (!ui) return;
    const has = !!terms().length;
    ui.count.hidden = !has;
    ui.prev.disabled = ui.next.disabled = !state.marks.length;
    ui.count.textContent = !has ? "" : (state.marks.length ? (state.cur + 1) + " / " + state.marks.length : t("HELP_VIEWER_NONE", "No matches"));
    ui.count.classList.toggle("hv__count--none", has && !state.marks.length);
  }

  // ------------------------------------------------------------------------------------------------------ Anzeige
  function buildNav() {
    const ui = state.ui;
    const docs = state.docs[state.lang] || {};
    const found = state.results || search();
    state.results = found;
    ui.nav.textContent = "";
    const list = el("div", "hv-nav__pages");
    PAGES.forEach((page) => {
      const doc = docs[page];
      if (!doc) return;
      const active = page === state.page;
      const count = found.counts[page] || 0;
      const row = el("div", "hv-nav__row" + (active ? " hv-nav__row--on" : "") + (found.ts.length && !count ? " hv-nav__row--none" : ""));
      const button = el("button", "hv-nav__page", doc.title);
      button.type = "button";
      button.dataset.hvPage = page;
      row.appendChild(button);
      if (found.ts.length && count) row.appendChild(el("span", "hv-nav__badge", String(count)));
      list.appendChild(row);
      if (active && !found.ts.length) {                                   // die Ueberschriften nur ohne Suche: bei einer Suche stehen die Treffer gleich darunter
        const toc = el("div", "hv-nav__toc");
        doc.headings.filter((h) => h.level === 2).forEach((h) => {
          const link = el("button", "hv-nav__heading", h.text);
          link.type = "button";
          link.dataset.hvHeading = h.id;
          toc.appendChild(link);
        });
        list.appendChild(toc);
      }
    });
    ui.nav.appendChild(list);
    if (found.ts.length) {
      const box = el("div", "hv-nav__results");
      box.appendChild(el("div", "hv-nav__results-title", found.total ? t("HELP_VIEWER_RESULTS", "{n} sections").replace("{n}", String(found.total)) : t("HELP_VIEWER_NONE", "No matches")));
      found.list.slice(0, MAX_RESULTS).forEach((hit) => {
        const item = el("button", "hv-hit");
        item.type = "button";
        item.dataset.hvPage = hit.page;
        item.dataset.hvHeading = hit.section.id;
        item.appendChild(el("span", "hv-hit__where", hit.doc.title + (hit.section.title && hit.section.title !== hit.doc.title ? " › " + hit.section.title : "")));
        const text = el("span", "hv-hit__text");
        const sn = snippet(hit.section, found.ts);
        const re = new RegExp("(" + found.ts.slice().sort((a, b) => b.length - a.length).map(escapeRe).join("|") + ")", "ig");
        sn.split(re).forEach((part, k) => { text.appendChild(k % 2 ? el("mark", "hv-mark", part) : document.createTextNode(part)); });
        item.appendChild(text);
        box.appendChild(item);
      });
      if (found.total > MAX_RESULTS) box.appendChild(el("div", "hv-nav__more", t("HELP_VIEWER_MORE", "More matches - refine the search.")));
      ui.nav.appendChild(box);
    }
    ui.select.textContent = "";
    PAGES.forEach((page) => { if (docs[page]) { const o = el("option", "", docs[page].title); o.value = page; o.selected = page === state.page; ui.select.appendChild(o); } });
  }

  function showPage(page, heading) {
    const docs = state.docs[state.lang] || {};
    if (!docs[page]) page = PAGES.find((p) => docs[p]) || page;
    const doc = docs[page];
    if (!doc) return;
    const ui = state.ui;
    if (state.page !== page || !ui.content.contains(doc.root)) {
      state.page = page;
      ui.content.textContent = "";
      ui.content.appendChild(doc.root);
      ui.content.scrollTop = 0;
    }
    try { localStorage.setItem(STORE, JSON.stringify({ page, lang: state.lang })); } catch (err) { /* ohne Speicher: egal */ }
    highlight(doc.root, terms());
    buildNav();
    if (heading) {
      const node = document.getElementById(heading);
      if (node) {
        node.scrollIntoView({ block: "start" });
        const mark = state.marks.findIndex((m) => (node.compareDocumentPosition(m) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0);
        if (mark >= 0) select(mark, false);
        else updateCount();
        return;
      }
    }
    if (state.marks.length) select(0); else updateCount();
  }

  function onQuery() {
    state.query = state.ui.input.value.trim();
    state.results = null;
    const found = search();
    state.results = found;
    const docs = state.docs[state.lang] || {};
    if (found.ts.length && !found.counts[state.page] && found.list.length) state.page = found.list[0].page;     // die aktuelle Anleitung hat keinen Treffer: zur ersten mit Treffer wechseln
    const doc = docs[state.page];
    if (doc && !state.ui.content.contains(doc.root)) { state.ui.content.textContent = ""; state.ui.content.appendChild(doc.root); }
    showPage(state.page);
  }

  async function setLang(lang) {
    state.lang = lang;
    state.ui.langButtons.forEach((b) => b.classList.toggle("hv__lang--on", b.dataset.hvLang === lang));
    state.ui.content.textContent = "";
    state.ui.content.appendChild(el("div", "hv__loading", t("HELP_VIEWER_LOADING", "Loading ...")));
    await load(lang);
    state.results = null;
    state.ui.content.textContent = "";
    showPage(state.page);
  }

  // ------------------------------------------------------------------------------------------------------ Aufbau und Bedienung
  function build() {
    const body = $("#help-body");
    body.textContent = "";
    const bar = el("div", "hv__bar");
    const searchBox = el("label", "hv__search");
    searchBox.appendChild(icon("search"));
    const input = el("input", "hv__input");
    input.type = "search";
    input.autocomplete = "off";
    input.spellcheck = false;
    input.placeholder = t("HELP_VIEWER_SEARCH", "Search the guides ...");
    const count = el("span", "hv__count");
    count.hidden = true;
    const prev = el("button", "hv__step");
    prev.type = "button";
    prev.title = t("HELP_VIEWER_PREV", "Previous match (Shift+Enter)");
    prev.appendChild(icon("chevron-up"));
    const next = el("button", "hv__step");
    next.type = "button";
    next.title = t("HELP_VIEWER_NEXT", "Next match (Enter)");
    next.appendChild(icon("chevron-down"));
    searchBox.append(input, count, prev, next);
    const langs = el("div", "hv__langs");
    const LANG_NAMES = { en: "English", de: "Deutsch", fr: "Français", nl: "Nederlands", it: "Italiano", es: "Español" };
    const langButtons = ["en", "de", "fr", "nl", "it", "es"].map((l) => {
      const b = el("button", "hv__lang", l.toUpperCase());
      b.type = "button";
      b.dataset.hvLang = l;
      b.title = LANG_NAMES[l];
      langs.appendChild(b);
      return b;
    });
    const select = el("select", "hv__select");
    select.setAttribute("aria-label", t("HELP_VIEWER_TITLE", "Guides"));
    bar.append(select, searchBox, langs);
    const main = el("div", "hv__main");
    const nav = el("nav", "hv__nav");
    const content = el("article", "hv__content");
    content.tabIndex = -1;
    main.append(nav, content);
    body.append(bar, main);
    state.ui = { input, count, prev, next, nav, content, select, langButtons };

    input.addEventListener("input", onQuery);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); select_(e.shiftKey ? state.cur - 1 : state.cur + 1); }
      else if (e.key === "F3") { e.preventDefault(); select_(e.shiftKey ? state.cur - 1 : state.cur + 1); }
    });
    prev.addEventListener("click", () => select_(state.cur - 1));
    next.addEventListener("click", () => select_(state.cur + 1));
    langs.addEventListener("click", (e) => { const b = e.target.closest("[data-hv-lang]"); if (b && b.dataset.hvLang !== state.lang) setLang(b.dataset.hvLang); });
    select.addEventListener("change", () => showPage(select.value));
    body.addEventListener("click", (e) => {
      const link = e.target.closest("[data-hv-page], [data-hv-heading]");
      if (!link) return;
      e.preventDefault();
      if (link.dataset.hvPage) showPage(link.dataset.hvPage, link.dataset.hvHeading || null);
      else { const node = document.getElementById(link.dataset.hvHeading); if (node) node.scrollIntoView({ block: "start" }); }
    });
    if (typeof Modal !== "undefined") Modal._escape.help = () => { if (state.ui.input.value) { state.ui.input.value = ""; onQuery(); state.ui.input.focus(); } else Modal.close("help"); };
  }

  function select_(index) { if (state.marks.length) select(index); }

  function focusSearch() {
    if (!state.ui) return;
    state.ui.input.focus();
    state.ui.input.select();
  }

  async function open(options) {
    const opts = options || {};
    if (!state.ui) build();
    let saved = {};
    try { saved = JSON.parse(localStorage.getItem(STORE) || "{}"); } catch (err) { /* ohne Speicher */ }
    const own = typeof translator !== "undefined" ? translator.language : "en";
    const lang = ["en", "de", "fr", "nl", "it", "es"].includes(own) ? own : "en";
    state.lang = opts.lang || lang;
    state.page = PAGES.includes(opts.page) ? opts.page : (PAGES.includes(saved.page) ? saved.page : PAGES[0]);
    state.ui.langButtons.forEach((b) => b.classList.toggle("hv__lang--on", b.dataset.hvLang === state.lang));
    Modal.open("help");
    if (opts.find !== undefined) state.ui.input.value = String(opts.find);
    state.query = state.ui.input.value.trim();
    state.ui.content.textContent = "";
    state.ui.content.appendChild(el("div", "hv__loading", t("HELP_VIEWER_LOADING", "Loading ...")));
    try {
      await load(state.lang);
    } catch (err) {
      state.ui.content.textContent = t("HELP_VIEWER_FAILED", "The guides could not be loaded.");
      return;
    }
    state.results = null;
    state.ui.content.textContent = "";
    if (state.query) onQuery(); else showPage(state.page);
    if (opts.find !== undefined || !opts.page) focusSearch();
  }

  /** Markdown -> DOM-Knoten (ohne innerHTML), z. B. fuer die Versionshinweise im Update-Fenster. */
  const renderMarkdown = (markdown) => render(String(markdown || ""), null).root;
  window.OCHelp = { open, focusSearch, renderMarkdown, isOpen: () => typeof Modal !== "undefined" && Modal.isOpen("help") };
})();
