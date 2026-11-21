// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Einstellungen: weniger Text, bessere Suche.
 *  1. Erklaertexte (kleine graue Absaetze unter den Einstellungen) sind standardmaessig eingeklappt; hinter jeder Beschriftung steht ein kleines (i), das GENAU diesen Text auf- und zuklappt.
 *     Der Schalter neben dem Suchfeld blendet alle Erklaerungen ein / aus (wird pro Geraet gemerkt). Status- und Warntexte (settings-hint-keep, --note) bleiben immer sichtbar.
 *  2. Suchergebnisse als Liste ueber ALLE Kategorien: "Einstellung - Kategorie / Abschnitt"; Klick springt zur Zeile, oeffnet ihre Erklaerung und hebt sie kurz hervor.
 * Laeuft nach app.js. Die Seiten API, KI, MIDI ... entstehen teils erst beim Oeffnen: ein MutationObserver bearbeitet auch spaeter gezeichnete Zeilen. */
(function () {
  "use strict";

  const KEY = "opencue.settingsHints";
  const HINTS = ".settings-field-hint, .ai-row__hint, .theme-hint";
  const KEEP = ".settings-hint-keep, .ai-row__hint--note, .ai-row__hint--intro, .settings-pane-intro";
  const ROWS = ".settings-field, .ai-row, .theme-row";
  const t = (key, fallback) => { const v = typeof i18n === "function" ? i18n(key) : key; return v && v !== key ? v : fallback; };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };

  let root = null;
  let input = null;
  let on = false;
  let pending = false;

  const load = () => { try { return localStorage.getItem(KEY) === "1"; } catch (e) { return false; } };
  const save = () => { try { localStorage.setItem(KEY, on ? "1" : "0"); } catch (e) { /* privates Fenster */ } };

  // ------------------------------------------------------------------------------------------------ Erklaerungen ein- / ausklappen
  /** Die Zeile (Beschriftung + Bedienelement), zu der der Hinweis gehoert: er steht in der Zeile selbst oder direkt hinter ihr. */
  function rowOf(hint) {
    const inside = hint.closest(ROWS);
    if (inside) return inside;
    const prev = hint.previousElementSibling;
    return prev && prev.matches(ROWS) ? prev : null;
  }

  function label(row) {
    return row.querySelector(":scope > label, :scope > .ai-row__label, :scope > .settings-field__label, label");
  }

  function decorate() {
    if (!root) return;
    root.querySelectorAll(".sh-hint").forEach((hint) => {                    // die Beschriftung wird bei jeder Uebersetzung neu geschrieben (textContent) und nimmt das (i) mit: wieder anhaengen
      const btn = hint._btn;
      if (btn && !btn.isConnected && btn._row && btn._row.isConnected) { const lab = label(btn._row); if (lab) lab.appendChild(btn); }
    });
    root.querySelectorAll(HINTS).forEach((hint) => {
      if (hint.dataset.sh || hint.matches(KEEP) || hint.closest(".io-row, .io-list")) return;
      const row = rowOf(hint);
      const lab = row && label(row);
      if (!lab) return;                                                      // ohne Beschriftung gibt es keinen Platz fuer das (i): der Text bleibt sichtbar
      hint.dataset.sh = "1";
      hint.classList.add("sh-hint");
      let btn = row.querySelector(":scope .sh-info");
      if (!btn) {
        btn = el("button", "sh-info"); btn.type = "button";
        btn.title = t("SET_HINT_INFO", "Show / hide explanation"); btn.setAttribute("aria-label", btn.title);
        if (typeof Icons !== "undefined") btn.appendChild(Icons.svg("info")); else btn.textContent = "i";
        btn.addEventListener("click", (e) => {
          e.preventDefault(); e.stopPropagation();
          const open = !btn.classList.contains("sh-info--open");
          btn.classList.toggle("sh-info--open", open);
          (btn._hints || []).forEach((h) => h.classList.toggle("sh-open", open));
        });
        btn._hints = [];
        btn._row = row;
        lab.appendChild(btn);
      }
      btn._hints.push(hint);
      hint._btn = btn;
    });
  }

  function paintToggle() {
    if (!root) return;
    root.classList.toggle("settings--hints-on", on);
    const b = root.querySelector("#settings-hints-toggle");
    if (b) { b.classList.toggle("sh-toggle--on", on); b.setAttribute("aria-pressed", on ? "true" : "false"); b.title = t(on ? "SET_HINTS_HIDE" : "SET_HINTS_SHOW", on ? "Hide explanations" : "Show explanations"); }
  }

  // ------------------------------------------------------------------------------------------------ Suche: Ergebnisliste
  function categoryOf(pane) {
    const btn = root.querySelector('[data-settings-category="' + pane.dataset.settingsPane + '"]');
    return { btn, name: btn ? btn.textContent.trim() : pane.dataset.settingsPane };
  }

  function words() { return input.value.trim().toLowerCase().split(/\s+/).filter(Boolean); }

  function results() {
    const ws = words();
    const out = [];
    if (!ws.length) return out;
    const has = (node) => { const hay = (node.textContent || "").toLowerCase(); return ws.every((w) => hay.includes(w)); };
    root.querySelectorAll("[data-settings-pane]").forEach((pane) => {
      const cat = categoryOf(pane);
      if (cat.btn && cat.btn.hidden) return;
      let rows = 0;
      pane.querySelectorAll(ROWS).forEach((row) => {
        if (row.querySelector(ROWS) || !has(row)) return;                    // nur die innerste Zeile
        const lab = label(row);
        const name = (lab ? lab.textContent : row.textContent).replace(/\s+/g, " ").trim().slice(0, 70);
        const sec = row.closest(".settings-section");
        const secTitle = sec && sec.querySelector(".settings-section__title");
        out.push({ name: name || cat.name, where: cat.name + (secTitle ? " / " + secTitle.textContent.trim() : ""), row, cat: cat.btn });
        rows += 1;
      });
      if (!rows && (has(pane) || (pane.dataset.searchKeys && ws.every((w) => pane.dataset.searchKeys.toLowerCase().includes(w)))) && cat.btn) out.push({ name: cat.name, where: "", row: null, cat: cat.btn });
    });
    return out.sort((a, b) => (a.row ? 0 : 1) - (b.row ? 0 : 1));              // Zeilen zuerst, reine Kategorie-Treffer danach
  }

  let list = null;
  function renderList() {
    if (!root || !input) return;
    if (!list) {
      list = el("div", "sh-results"); list.hidden = true;
      input.closest(".settings-modal__search").appendChild(list);
    }
    list.textContent = "";
    const items = results();
    list.hidden = !items.length || !words().length;
    items.slice(0, 14).forEach((r) => {
      const b = el("button", "sh-result"); b.type = "button";
      b.append(el("span", "sh-result__name", r.name), el("span", "sh-result__where", r.where || t("SET_HINTS_CATEGORY", "Category")));
      b.addEventListener("click", () => go(r));
      list.appendChild(b);
    });
    if (items.length > 14) list.appendChild(el("div", "sh-result__more", "+ " + (items.length - 14)));
  }

  function go(r) {
    list.hidden = true;
    if (r.cat && !r.cat.classList.contains("settings-modal__category--active")) r.cat.click();
    if (!r.row) return;
    setTimeout(() => {
      r.row.classList.remove("settings-filter-off");
      const sec = r.row.closest(".settings-section"); if (sec) sec.classList.remove("settings-filter-off");
      const btn = r.row.querySelector(".sh-info"); if (btn && !btn.classList.contains("sh-info--open")) btn.click();
      r.row.scrollIntoView({ block: "center", behavior: "smooth" });
      r.row.classList.add("sh-flash");
      setTimeout(() => r.row.classList.remove("sh-flash"), 1800);
    }, 60);
  }

  /** Passt der Suchtext zu einer (eingeklappten) Erklaerung, wird sie aufgeklappt - sonst saehe man nicht, warum die Zeile gefunden wurde. */
  function openMatchingHints() {
    const ws = words();
    root.querySelectorAll(".sh-hint").forEach((h) => {
      const hit = ws.length && ws.every((w) => h.textContent.toLowerCase().includes(w));
      if (hit) { h.classList.add("sh-open", "sh-auto"); if (h._btn) h._btn.classList.add("sh-info--open"); }
      else if (h.classList.contains("sh-auto")) { h.classList.remove("sh-open", "sh-auto"); if (h._btn && !h._btn._hints.some((x) => x.classList.contains("sh-open"))) h._btn.classList.remove("sh-info--open"); }
    });
  }

  function onSearch() { openMatchingHints(); renderList(); }

  // ------------------------------------------------------------------------------------------------ Aufbau
  function schedule() {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => { pending = false; decorate(); });
  }

  function init() {
    root = document.querySelector(".modal--settings");
    input = root && root.querySelector("#settings-search");
    if (!root || !input) return;
    on = load();
    const box = input.closest(".settings-modal__search");
    const toggle = el("button", "sh-toggle"); toggle.type = "button"; toggle.id = "settings-hints-toggle";
    if (typeof Icons !== "undefined") toggle.appendChild(Icons.svg("info")); else toggle.textContent = "i";
    toggle.addEventListener("click", () => { on = !on; save(); paintToggle(); });
    box.appendChild(toggle);
    paintToggle();
    decorate();
    new MutationObserver(schedule).observe(root.querySelector(".settings-modal__content") || root, { childList: true, subtree: true });
    input.addEventListener("input", onSearch);
    document.addEventListener("settings-search-refresh", onSearch);
    document.addEventListener("i18n-applied", () => { paintToggle(); root.querySelectorAll(".sh-info").forEach((b) => { b.title = t("SET_HINT_INFO", "Show / hide explanation"); }); });
    input.addEventListener("blur", () => setTimeout(() => { if (list && !list.matches(":hover")) list.hidden = true; }, 200));
    input.addEventListener("focus", () => { if (list && words().length) renderList(); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
  window.OCSettingsHints = { decorate, results };
})();
