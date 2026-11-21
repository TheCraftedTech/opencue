// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Auswahl des Effekttyps: ein grosser Dialog mit drei Spalten (Kategorie | Effekte | Beschreibung) und einer Suche ueber alle Effekte.
 *  - Spalte 1: Kategorien in der Reihenfolge der Scheinwerfer-Steuerung (Dimmer, Farbe, Position, Zoom, Fokus, Gobo) mit Anzahl; "Alle Effekte" zeigt jeden Treffer.
 *  - Spalte 2: die Effekte der Kategorie mit ihrem NAMEN (#NAME) und dem Dateinamen in Klammern, dazu die Schlagworte (#TAGS; "audio" setzt das Programm selbst,
 *    sobald ein Skript Audio-Variablen liest).
 *  - Spalte 3: Beschreibung, Schlagworte, Regler und Datei des gewaehlten Effekts; "Auswaehlen" (oder Doppelklick) uebernimmt ihn.
 *  - Suche: Name, Datei, Beschreibung, Schlagworte; die Schlagwort-Knoepfe filtern zusaetzlich (alle gewaehlten muessen passen).
 * Aufruf: OCFxPicker.open({ scripts: { name: {name, label, category, description, tags, variables, rate, ...} }, current: "kind", onSelect: (kind) => ... }). Laeuft nach app.js. */
(function () {
  "use strict";

  const BACKDROP = "fx-type-picker";
  const CATEGORY_ORDER = ["dimmer", "color", "position", "zoom", "focus", "gobo"];     // wie in der Scheinwerfer-Steuerung (app/fx_categories.py)
  const t = (key) => i18n(key);
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const $ = (id) => document.getElementById(id);
  const catLabel = (category) => { const key = "FXS_CAT_" + String(category).toUpperCase(); const v = t(key); return v === key ? category : v; };
  // ---- Beschriftungen der Regler und Beschreibung je Sprache: erst #INFO / #DESCRIPTION des Skripts, dann das Glossar der Oberflaeche (FXV_<KATEGORIE>_<NAME>, FXV_<NAME>), sonst der Variablenname
  const uiLang = () => ((typeof translator !== "undefined" && translator.language) || "de");
  const upper = (text) => String(text).toUpperCase().replace(/[^A-Z0-9]/g, "_");
  const gloss = (key) => { const v = t(key); return v === key ? "" : v; };
  const pick = (map) => { const m = map || {}; return m[uiLang()] || m.en || m.de || ""; };               // Sprache der Oberflaeche, sonst Englisch, sonst Deutsch
  function varLabel(script, v) {
    return pick(v.labels) || gloss("FXV_" + upper(script.category) + "_" + upper(v.name)) || gloss("FXV_" + upper(v.name)) || v.name;
  }
  function varHint(script, v) {
    return pick(v.hints) || gloss("FXV_" + upper(script.category) + "_" + upper(v.name) + "_H") || gloss("FXV_" + upper(v.name) + "_H") || "";
  }
  function description(script) {
    return pick(script.descriptions) || script.description || "";
  }
  /** Mouseover eines Reglers: Erklaerung und in eckigen Klammern der Variablenname (so heisst er im Skript). */
  const varTip = (script, v) => { const hint = varHint(script, v); return hint ? hint + "  [" + v.name + "]" : v.name; };
  const tagLabel = (tag) => { const key = "FXTAG_" + String(tag).toUpperCase().replace(/[^A-Z0-9]/g, "_"); const v = t(key); return v === key ? tag.charAt(0).toUpperCase() + tag.slice(1) : v; };

  const tagRank = (tag) => (tag === "basic" ? 0 : tag === "advanced" ? 1 : tag === "audio" ? 2 : 3);      // Stufe (Basis / Erweitert) zuerst, dann Audio, dann der Rest
  let scripts = [];                       // Liste der Skripte (Objekte aus /api/effects)
  let onSelect = null;
  const view = { category: "dimmer", query: "", tags: new Set(), selected: "" };
  let wired = false;

  const haystack = (s) => [s.label, s.name, s.description, Object.values(s.descriptions || {}).join(" "), (s.tags || []).join(" ")].join(" ").toLowerCase();
  const sortByLabel = (list) => list.sort((a, b) => String(a.label).localeCompare(String(b.label), undefined, { sensitivity: "base" }));

  function matching(ignoreCategory) {
    const words = view.query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    return scripts.filter((s) => {
      if (!ignoreCategory && view.category !== "all" && s.category !== view.category) return false;
      if ([...view.tags].some((tag) => !(s.tags || []).includes(tag))) return false;
      if (!words.length) return true;
      const text = haystack(s);
      return words.every((w) => text.includes(w));
    });
  }

  // ------------------------------------------------------------------------------------------------ Spalten
  function renderCategories() {
    const box = $("fx-picker-cats");
    box.textContent = "";
    const hits = matching(true);
    const counts = {};
    hits.forEach((s) => { counts[s.category] = (counts[s.category] || 0) + 1; });
    const known = [...new Set(scripts.map((s) => s.category))];
    const order = CATEGORY_ORDER.filter((c) => known.includes(c)).concat(known.filter((c) => !CATEGORY_ORDER.includes(c)));
    const add = (key, label, count) => {
      const button = el("button", "fxpick__cat" + (view.category === key ? " fxpick__cat--on" : "") + (count ? "" : " fxpick__cat--empty"));
      button.type = "button";
      button.dataset.category = key;
      button.append(el("span", "fxpick__cat-name", label), el("span", "fxpick__cat-count", String(count)));
      button.addEventListener("click", () => { view.category = key; saveView(); render(); });
      box.appendChild(button);
    };
    add("all", t("FXP_ALL"), hits.length);
    order.forEach((c) => add(c, catLabel(c), counts[c] || 0));
  }

  function renderTags() {
    const box = $("fx-picker-tags");
    box.textContent = "";
    const counts = {};
    scripts.forEach((s) => (s.tags || []).forEach((tag) => { counts[tag] = (counts[tag] || 0) + 1; }));
    Object.keys(counts).sort((a, b) => (tagRank(a) - tagRank(b)) || a.localeCompare(b)).forEach((tag) => {
      const chip = el("button", "fxpick__tag fxpick__tag--" + tag + (view.tags.has(tag) ? " fxpick__tag--on" : ""), tagLabel(tag));
      chip.type = "button";
      chip.dataset.tag = tag;
      chip.title = counts[tag] + " ×";
      chip.addEventListener("click", () => { if (view.tags.has(tag)) view.tags.delete(tag); else view.tags.add(tag); saveView(); render(); });
      box.appendChild(chip);
    });
  }

  function renderList() {
    const box = $("fx-picker-list");
    box.textContent = "";
    const list = sortByLabel(matching(false));
    if (!list.length) {
      box.appendChild(el("div", "fxpick__none", t("FXP_NONE")));
      return;
    }
    list.forEach((s) => {
      const row = el("div", "fxpick__row" + (view.selected === s.name ? " fxpick__row--on" : ""));
      row.dataset.kind = s.name;
      row.tabIndex = 0;
      const main = el("div", "fxpick__row-main");
      main.append(el("span", "fxpick__row-name", s.label), el("span", "fxpick__row-file", "(" + s.name + ")"));
      const meta = el("div", "fxpick__row-meta");
      if (view.category === "all") meta.appendChild(el("span", "fxpick__row-cat", catLabel(s.category)));
      (s.tags || []).forEach((tag) => meta.appendChild(el("span", "fxpick__badge fxpick__badge--" + tag, tagLabel(tag))));
      row.append(main, meta);
      row.addEventListener("click", () => { view.selected = s.name; renderList(); renderDetail(); });
      row.addEventListener("dblclick", () => choose(s.name));
      box.appendChild(row);
    });
    const on = box.querySelector(".fxpick__row--on");
    if (on && on.scrollIntoView) on.scrollIntoView({ block: "nearest" });
  }

  function renderDetail() {
    const box = $("fx-picker-detail");
    box.textContent = "";
    const s = scripts.find((x) => x.name === view.selected);
    $("fx-picker-select").disabled = !s;
    if (!s) {
      box.appendChild(el("div", "fxpick__none", t("FXP_PICK_HINT")));
      return;
    }
    box.appendChild(el("h3", "fxpick__title", s.label));
    const facts = el("div", "fxpick__facts");
    facts.append(el("span", "", catLabel(s.category)), el("span", "fxpick__file", s.name + ".fx"));
    if (s.rate) facts.appendChild(el("span", "", t("FXS_RATE_SHORT").replace("{n}", s.rate)));
    box.appendChild(facts);
    if ((s.tags || []).length) {
      const tags = el("div", "fxpick__row-meta");
      s.tags.forEach((tag) => tags.appendChild(el("span", "fxpick__badge fxpick__badge--" + tag, tagLabel(tag))));
      box.appendChild(tags);
    }
    box.appendChild(el("p", "fxpick__desc", description(s) || t("FXP_NO_DESC")));
    const vars = s.variables || [];
    if (vars.length) {
      box.appendChild(el("div", "fxpick__sub", t("FXP_SETTINGS")));
      const list = el("ul", "fxpick__vars");
      vars.forEach((v) => {
        const range = v.kind === "ColorPicker" ? "" : v.min + " … " + v.max;
        const item = el("li", "fxpick__var");
        item.title = varTip(s, v);
        item.append(el("span", "fxpick__var-name", varLabel(s, v)), el("span", "fxpick__var-meta", " [" + v.name + (range ? ", " + range : "") + "]"));
        const hint = varHint(s, v);
        if (hint) item.appendChild(el("div", "fxpick__var-hint", hint));
        list.appendChild(item);
      });
      box.appendChild(list);
    }
  }

  function render() {
    renderTags();
    renderCategories();
    renderList();
    renderDetail();
  }

  function choose(kind) {
    Modal.close(BACKDROP);
    if (onSelect) onSelect(kind);
  }

  // ------------------------------------------------------------------------------------------------ Aufbau und Bedienung
  function wire() {
    if (wired) return;
    wired = true;
    const search = $("fx-picker-search");
    search.addEventListener("input", () => {
      view.query = search.value;
      if (view.query.trim() && view.category !== "all") view.category = "all";          // Suche gilt ueber alle Effekte
      render();
    });
    $("fx-picker-select").addEventListener("click", () => { if (view.selected) choose(view.selected); });
    $("fx-picker-clear").addEventListener("click", () => { view.query = ""; view.tags.clear(); search.value = ""; render(); search.focus(); });
    $("fx-picker-root").addEventListener("keydown", (event) => {
      if (event.key === "Enter" && view.selected && event.target.tagName !== "BUTTON") { event.preventDefault(); choose(view.selected); return; }
      if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
      const rows = [...document.querySelectorAll("#fx-picker-list .fxpick__row")];
      if (!rows.length) return;
      event.preventDefault();
      let index = rows.findIndex((r) => r.dataset.kind === view.selected);
      index = Math.max(0, Math.min(rows.length - 1, index + (event.key === "ArrowDown" ? 1 : -1)));
      view.selected = rows[index].dataset.kind;
      renderList();
      renderDetail();
    });
  }

  function saveView() { if (window.OCViewState) OCViewState.set("global", "fxpicker", { category: view.category, tags: [...view.tags] }); }

  function open(options) {
    wire();
    const map = (options && options.scripts) || {};
    scripts = Object.values(map).map((s) => Object.assign({ tags: [] }, s));
    onSelect = options && options.onSelect;
    const current = options && options.current;
    const known = scripts.find((s) => s.name === current);
    view.selected = known ? known.name : "";
    view.category = known ? known.category : "dimmer";
    view.query = "";
    view.tags.clear();
    if (!known && window.OCViewState) {                     // sonst die zuletzt benutzte Kategorie und Schlagworte (Basis / Erweitert ...) dieses Geraets
      const last = OCViewState.get("global", "fxpicker", null);
      if (last && typeof last.category === "string" && (last.category === "all" || scripts.some((s) => s.category === last.category))) view.category = last.category;
      if (last && Array.isArray(last.tags)) last.tags.forEach((tag) => { if (scripts.some((s) => (s.tags || []).includes(tag))) view.tags.add(tag); });
    }
    $("fx-picker-search").value = "";
    render();
    Modal.open(BACKDROP);
    setTimeout(() => $("fx-picker-search").focus(), 30);
  }

  window.OCFxPicker = { open, tagLabel, catLabel, varLabel, varHint, varTip, description };
})();
