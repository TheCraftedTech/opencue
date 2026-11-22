// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Fenster "Was ist neu": zeigt die neuen Funktionen der Versionen, die man noch nicht gesehen hat (nach einem Update automatisch einmal, siehe welcome.js; sonst ueber
 * Hilfe -> Was ist neu). Die Texte stehen in static/whatsnew/<sprache>.json (neueste Version zuerst): bei jeder neuen Version oben einen Eintrag je Sprache ergaenzen
 * (Symbolnamen aus static/js/icons.js). Fehlt die Sprache, faellt das Fenster auf Englisch zurueck.
 * Aufruf: window.OCWhatsNew.open(). Gesehen-Stand: state.seen_version (Server), gesetzt ueber die WS-Nachricht whats_new_seen (welcome.js). */
(function () {
  "use strict";
  const ROOT = '[data-modal-backdrop="whatsnew"]';
  const t = (key, fallback) => { try { const v = typeof i18n === "function" ? i18n(key) : ""; return v && v !== key ? v : fallback; } catch (err) { return fallback; } };
  const $ = (selector) => document.querySelector(ROOT + " " + selector);
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const fill = (text, values) => Object.keys(values || {}).reduce((s, k) => s.split("{" + k + "}").join(String(values[k])), text);
  const cache = {};
  let bound = false;
  let seenAtOpen = "";                 // der Gesehen-Stand beim Oeffnen (der Server setzt ihn gleich danach auf die aktuelle Version)

  const parts = (v) => String(v || "0").replace(/^v/i, "").split(/[.\-+]/).map((x) => parseInt(x, 10) || 0);
  /** Versionsvergleich "2.1.1" gegen "2.1.0": >0, 0, <0. */
  function compare(a, b) {
    const x = parts(a), y = parts(b);
    for (let i = 0; i < 3; i++) { if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) - (y[i] || 0); }
    return 0;
  }

  async function load(lang) {
    if (cache[lang]) return cache[lang];
    for (const code of [lang, "en"]) {
      try {
        const res = await fetch("/static/whatsnew/" + code + ".json", { cache: "no-cache" });
        if (res.ok) { cache[lang] = (await res.json()).releases || []; return cache[lang]; }
      } catch (err) { /* naechste Sprache */ }
    }
    return [];
  }

  const icon = (name) => (typeof Icons !== "undefined" && Icons.has && Icons.has(name) ? Icons.svg(name) : (typeof Icons !== "undefined" ? Icons.svg("star") : document.createTextNode("")));

  function releaseNode(rel, current) {
    const box = el("section", "wn__release");
    const head = el("div", "wn__head");
    head.append(el("h3", "wn__version", fill(t("WHATSNEW_VERSION", "Version {version}"), { version: rel.version })));
    if (rel.title) head.append(el("span", "wn__tag", rel.title));
    if (rel.date) head.append(el("span", "wn__date", rel.date));
    box.appendChild(head);
    const list = el("ul", "wn__list");
    (rel.items || []).forEach((item) => {
      const li = el("li", "wn__item");
      const ico = el("span", "wn__icon"); ico.appendChild(icon(item.icon));
      const text = el("div", "wn__text");
      text.append(el("strong", "", item.title), el("span", "", item.text));
      li.append(ico, text);
      list.appendChild(li);
    });
    box.appendChild(list);
    return box;
  }

  async function render() {
    const body = $("#wn-body");
    const lang = (typeof client !== "undefined" && client.state && client.state.language) || document.documentElement.lang || "en";
    const releases = await load(String(lang).slice(0, 2));
    body.textContent = "";
    if (!releases.length) { body.appendChild(el("p", "wn__empty", t("WHATSNEW_NONE", "No release notes available."))); return; }
    const seen = seenAtOpen;
    const unseen = releases.filter((r) => compare(r.version, seen) > 0);
    const shown = unseen.length ? unseen : [releases[0]];                 // alles gesehen (Hilfe-Menue): die neueste Version
    const rest = releases.filter((r) => !shown.includes(r));
    $("#wn-title").textContent = fill(t("WHATSNEW_TITLE", "What’s new in OpenCue {version}"), { version: shown[0].version });
    shown.forEach((r) => body.appendChild(releaseNode(r)));
    if (rest.length) {
      const more = el("details", "wn__more");
      more.appendChild(el("summary", "", t("WHATSNEW_EARLIER", "Earlier versions")));
      rest.forEach((r) => more.appendChild(releaseNode(r)));
      body.appendChild(more);
    }
  }

  function bind() {
    if (bound || !document.querySelector(ROOT)) return;
    bound = true;
    $("#wn-close").addEventListener("click", () => Modal.close("whatsnew"));
    $("#wn-all").addEventListener("click", async () => {
      try {
        const res = await (await fetch("/api/about/open", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target: "releases" }) })).json();
        if (res && res.ok && !res.opened && res.url) window.open(res.url, "_blank", "noopener");
      } catch (err) { /* offline */ }
    });
    document.addEventListener("i18n-applied", () => { if (Modal.isOpen("whatsnew")) render(); });
  }

  async function open() {
    bind();
    seenAtOpen = (typeof client !== "undefined" && client.state && client.state.seen_version) || "";
    await render();
    Modal.open("whatsnew");
  }

  window.OCWhatsNew = { open, compare };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind); else bind();
})();
