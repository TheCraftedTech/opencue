// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
// Eigener Scheinwerfer-Editor (Bibliothek -> "Eigener Scheinwerfer"; app/fixture_editor.py baut daraus eine ECHTE GDTF-Datei, die sich auch auf anderen Rechnern importieren laesst).
// Drei Teile: Allgemein (Hersteller, Name, Kategorie, Stichwoerter ...), Kanaele (Modi, Kanaele, Bereiche, CSV-Import), Bild & 3D.
(function () {
  "use strict";
  const MODAL = "fixture-editor";
  const t = (key, vars) => {
    let s = i18n(key);
    if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
    return s;
  };
  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const ATTR_RE = /^[A-Za-z][A-Za-z0-9_ \-]{0,39}$/;
  const CATS = ["moving_head", "led_bar", "par", "dimmer", "strobe", "effect", "other"];
  const CAT_KEY = { moving_head: "FXLIB_CAT_MOVING_HEAD", led_bar: "FXLIB_CAT_LED_BAR", par: "FXLIB_CAT_PAR", dimmer: "FXLIB_CAT_DIMMER", strobe: "FXLIB_CAT_STROBE", effect: "FXLIB_CAT_EFFECT", other: "FXLIB_CAT_OTHER" };

  // thumb / model: Zustand des Bildes und des 3D-Modells. kind: "none" | "keep" (bleibt wie in der Datei) | "new" (hochgeladen, data = Base64) | "copy" (Bild einer kopierten Datei)
  const E = { snap: "", usedModes: {}, footprints: {}, spec: null, tab: "general", mode: 0, replaceId: "", palette: [], physical: {}, open: new Set(), inUse: 0, notes: null, thumb: { kind: "none" }, model: { kind: "none" }, busy: false };
  let uid = 0;

  const newChannel = (attribute, label, ranges, bits, def) => ({ _k: ++uid, attribute: attribute || "", label: label || "", bits: bits || 8, default: def || 0, ranges: ranges || [] });
  const blank = () => ({ manufacturer: "", name: "", short_name: "", description: "", category: "", tags: [], weight: "", modes: [{ name: t("FXED_MODE_DEFAULT"), channels: [newChannel("Dimmer")] }] });
  const TEMPLATES = {
    none: () => [{ name: t("FXED_MODE_DEFAULT"), channels: [newChannel("Dimmer")] }],
    fog: () => [{ name: t("FXED_MODE_DEFAULT"), channels: [newChannel("Fog1", t("FXED_TPL_FOG_LABEL"), [{ from: 0, name: t("FXED_TPL_OFF") }, { from: 10, name: t("FXED_TPL_FOG_ON") }])] }],
    dimmer: () => [{ name: t("FXED_MODE_DEFAULT"), channels: [newChannel("Dimmer", t("FXED_TPL_DIMMER_LABEL"))] }],
    rgb: () => [{ name: "3 ch", channels: [newChannel("ColorAdd_R", t("FXED_TPL_RED")), newChannel("ColorAdd_G", t("FXED_TPL_GREEN")), newChannel("ColorAdd_B", t("FXED_TPL_BLUE"))] }],
    rgbd: () => [{ name: "4 ch", channels: [newChannel("Dimmer", t("FXED_TPL_DIMMER_LABEL")), newChannel("ColorAdd_R", t("FXED_TPL_RED")), newChannel("ColorAdd_G", t("FXED_TPL_GREEN")), newChannel("ColorAdd_B", t("FXED_TPL_BLUE"))] }],
    mover: () => [{ name: "8 ch", channels: [newChannel("Pan", "", [], 16, 127), newChannel("Tilt", "", [], 16, 127), newChannel("Dimmer", t("FXED_TPL_DIMMER_LABEL")), newChannel("Shutter1", "", [{ from: 0, name: t("FXED_TPL_OPEN") }, { from: 10, name: t("FXED_TPL_STROBE") }]), newChannel("ColorAdd_R", t("FXED_TPL_RED")), newChannel("ColorAdd_G", t("FXED_TPL_GREEN")), newChannel("ColorAdd_B", t("FXED_TPL_BLUE"))] }],
  };

  function adopt(spec) {                                                   // Server-Beschreibung -> Arbeitskopie mit Schluesseln
    spec.modes.forEach((m) => { m._orig = m.name; m.channels.forEach((c) => { c._k = ++uid; c.label = c.label || ""; c.ranges = c.ranges || []; }); });
    spec.tags = spec.tags || [];
    spec.category = spec.category || "";
    spec.weight = spec.weight || "";
    return spec;
  }

  // Loeschen im Editor fragt immer nach (aus Versehen einen Modus oder Kanal zu verlieren ist aergerlich)
  const confirmDelete = (titleKey, bodyKey, vars) => _askDelete("library", { title: t(titleKey), body: t(bodyKey, vars), confirmKey: "FX_DELETE_CONFIRM" });
  const chName = (ch, i) => (ch.label || ch.attribute || "").trim() || String(i + 1);

  // Warnung (kein Verbot): Modi, die die Show benutzt, aendern ihre Kanalzahl oder verschwinden
  function warnings() {
    const out = [];
    if (!E.replaceId) return out;
    const current = {};
    E.spec.modes.forEach((m) => { current[m._orig || m.name] = m; });
    Object.keys(E.usedModes || {}).forEach((name) => {
      const m = current[name];
      if (!m) { out.push(t("FXED_W_GONE", { name, n: E.usedModes[name] })); return; }
      if (m.name !== name) out.push(t("FXED_W_GONE", { name, n: E.usedModes[name] }));
      else if (E.footprints[name] && footprint(m) !== E.footprints[name]) out.push(t("FXED_W_COUNT", { name, n: E.usedModes[name], a: E.footprints[name], b: footprint(m) }));
    });
    return out;
  }
  function renderWarnings() {
    const box = $("fxed-warn");
    if (!box) return;
    box.textContent = "";
    warnings().forEach((w) => box.appendChild(el("p", "fxed__note fxed__note--warn", w)));
  }

  // Stand beim Oeffnen vs. jetzt: nur bei Aenderungen fragt Abbrechen nach
  const snapshot = () => JSON.stringify([E.spec, E.thumb.kind, E.thumb.kind === "new" ? E.thumb.data.length : 0, E.model], (k, v) => (k.charAt(0) === "_" || k === "data" ? undefined : v));
  const isDirty = () => !!E.spec && snapshot() !== E.snap;
  let guardBusy = false;
  async function guardClose() {
    if (guardBusy) return;
    if (!isDirty()) { Modal.close(MODAL, true); return; }
    guardBusy = true;
    try {
      const choice = await _askExitEdit("", { body: t("FXED_CANCEL_BODY") });                   // Weiter bearbeiten / Aenderungen verwerfen / Speichern
      if (choice === "discard") Modal.close(MODAL, true);
      else if (choice === "save") { guardBusy = false; await save(); }
    } finally { guardBusy = false; }
  }

  const palette = (name) => E.palette.find((p) => p.name === name);
  const isCustom = (ch) => !palette(ch.attribute);
  const mode = () => E.spec.modes[E.mode];
  const footprint = (m) => m.channels.reduce((n, c) => n + (c.bits === 16 ? 2 : 1), 0);
  const isMoving = () => E.spec.modes.some((m) => m.channels.some((c) => c.attribute === "Pan" || c.attribute === "Tilt"));

  function setError(text, target, tab) {
    const box = $("fxed-error");
    if (box) { box.textContent = text || ""; box.hidden = !text; }
    document.querySelectorAll(".fxed__bad").forEach((n) => n.classList.remove("fxed__bad"));
    if (tab && tab !== E.tab) showTab(tab);
    const node = typeof target === "function" ? target() : target;
    if (node) { node.classList.add("fxed__bad"); try { node.scrollIntoView({ block: "nearest" }); if (node.focus) node.focus(); } catch (e) { /* egal */ } }
  }

  // ------------------------------------------------------------------------------------------------------ kleine Bausteine
  const field = (label, input, cls) => { const w = el("label", "fxed__field" + (cls ? " " + cls : "")); w.appendChild(el("span", "fxed__label", label)); w.appendChild(input); return w; };
  function textInput(value, onInput, max, ph) {
    const i = el("input", "settings__text-input");
    i.type = "text"; i.value = value || ""; i.maxLength = max || 60; i.autocomplete = "off";
    if (ph) i.placeholder = ph;
    i.addEventListener("input", () => { onInput(i.value); i.classList.remove("fxed__bad"); });
    return i;
  }
  const iconBtn = (icon, title, onClick, disabled) => {
    const b = el("button", "modal__button modal__button--icon fxed__ibtn");
    b.type = "button"; b.title = title; b.setAttribute("aria-label", title); b.appendChild(Icons.svg(icon)); b.disabled = !!disabled;
    b.addEventListener("click", onClick);
    return b;
  };
  const textBtn = (icon, label, onClick, cls) => {
    const b = el("button", "modal__button fxed__tbtn" + (cls ? " " + cls : "")); b.type = "button";
    if (icon) b.appendChild(Icons.svg(icon));
    b.appendChild(document.createTextNode(label));
    b.addEventListener("click", onClick);
    return b;
  };

  // ------------------------------------------------------------------------------------------------------ Reiter
  function showTab(name) {
    E.tab = name;
    document.querySelectorAll("#fxed-body [data-fxed-tab]").forEach((b) => { const on = b.dataset.fxedTab === name; b.classList.toggle("fxlib__tab--active", on); b.setAttribute("aria-selected", on ? "true" : "false"); });
    ["general", "channels", "media"].forEach((n) => { const p = $("fxed-pane-" + n); if (p) p.hidden = n !== name; });
    if (name === "media") renderMedia();
  }

  // ------------------------------------------------------------------------------------------------------ Allgemein
  function renderGeneral() {
    const box = $("fxed-pane-general");
    box.textContent = "";
    box.appendChild(el("p", "fxed__note", t("FXED_NOTE")));
    if (E.notes && Object.keys(E.notes).length) {
      const parts = [];
      if (E.notes.wheels) parts.push(t("FXED_COPY_WHEELS", { n: E.notes.wheels }));
      if (E.notes.logicals) parts.push(t("FXED_COPY_LOGICALS", { n: E.notes.logicals }));
      if (E.notes.geometry) parts.push(t("FXED_COPY_GEOMETRY"));
      box.appendChild(el("p", "fxed__note fxed__note--warn", t("FXED_COPY_NOTE") + " " + parts.join(" ")));
    }
    if (E.inUse) box.appendChild(el("p", "fxed__note fxed__note--warn", t("FXED_IN_USE", { n: E.inUse })));
    const s = E.spec;
    if (!E.replaceId) {                                                    // gut sichtbar: einen schon installierten Scheinwerfer als Grundlage laden
      const bar = el("div", "fxed__loadbar");
      const sel = el("select", "settings__text-input");
      const first = el("option", "", t("FXED_LOAD_FROM_PH")); first.value = ""; sel.appendChild(first);
      (window.FixtureEditor.types || []).forEach((x) => { const o = el("option", "", x.label); o.value = x.id; sel.appendChild(o); });
      sel.value = E.copyOf || "";
      sel.addEventListener("change", () => { if (sel.value) openEditor(sel.value, true); });
      bar.appendChild(field(t("FXED_LOAD_FROM"), sel));
      bar.appendChild(el("span", "fxed__hint", t("FXED_LOAD_FROM_HINT")));
      box.appendChild(bar);
    }
    const grid = el("div", "fxed__grid");
    const mfr = textInput(s.manufacturer, (v) => { s.manufacturer = v; }, 60); mfr.dataset.fxed = "manufacturer"; mfr.setAttribute("list", "fxed-mfr-list");
    const name = textInput(s.name, (v) => { s.name = v; }, 60); name.dataset.fxed = "name";
    grid.appendChild(field(t("FXED_MANUFACTURER"), mfr));
    grid.appendChild(field(t("FXED_NAME"), name));
    const short = textInput(s.short_name, (v) => { s.short_name = v; }, 8); short.dataset.fxed = "short_name";
    grid.appendChild(field(t("FXED_SHORT"), short));
    const cat = el("select", "settings__text-input"); cat.dataset.fxed = "category";
    const auto = el("option", "", t("FXED_CAT_AUTO")); auto.value = ""; cat.appendChild(auto);
    CATS.forEach((c) => { const o = el("option", "", t(CAT_KEY[c])); o.value = c; cat.appendChild(o); });
    cat.value = s.category || "";
    cat.addEventListener("change", () => { s.category = cat.value; });
    grid.appendChild(field(t("FXED_CATEGORY"), cat));
    const weight = el("input", "settings__text-input"); weight.type = "number"; weight.min = 0; weight.step = "0.1"; weight.value = s.weight === "" ? "" : s.weight; weight.dataset.fxed = "weight";
    weight.addEventListener("input", () => { s.weight = weight.value === "" ? "" : Number(weight.value); weight.classList.remove("fxed__bad"); });
    grid.appendChild(field(t("FXED_WEIGHT"), weight));
    const desc = textInput(s.description, (v) => { s.description = v; }, 300);
    grid.appendChild(field(t("FXED_DESC"), desc, "fxed__field--wide"));
    if (!E.replaceId && !E.copyOf) {
      const sel = el("select", "settings__text-input");
      [["none", "FXED_TPL_NONE"], ["fog", "FXED_TPL_FOG"], ["dimmer", "FXED_TPL_DIMMER"], ["rgb", "FXED_TPL_RGB"], ["rgbd", "FXED_TPL_RGBD"], ["mover", "FXED_TPL_MOVER"]].forEach(([v, k]) => { const o = el("option", "", t(k)); o.value = v; sel.appendChild(o); });
      sel.addEventListener("change", () => {
        s.modes = TEMPLATES[sel.value](); E.mode = 0; E.open.clear(); setError("");
        if (sel.value === "mover" && !s.category) { s.category = "moving_head"; cat.value = "moving_head"; }
        if ((sel.value === "fog") && !s.category) { s.category = "effect"; cat.value = "effect"; }
        renderModes();
      });
      grid.appendChild(field(t("FXED_TEMPLATE"), sel));
    }
    box.appendChild(grid);
    // Stichwoerter (Tags): Eingabe + Enter / Komma, jedes Stichwort ein Chip zum Entfernen; sie werden in der Bibliothek mitdurchsucht
    const tagsBox = el("div", "fxed__tags");
    tagsBox.appendChild(el("span", "fxed__label", t("FXED_TAGS")));
    const chips = el("div", "fxed__chips");
    const draw = () => {
      chips.textContent = "";
      s.tags.forEach((tag, i) => {
        const chip = el("span", "fxed__chip", tag);
        const x = el("button", "fxed__chipx", "×"); x.type = "button"; x.title = t("FXED_REMOVE"); x.setAttribute("aria-label", t("FXED_REMOVE") + ": " + tag);
        x.addEventListener("click", () => { s.tags.splice(i, 1); draw(); });
        chip.appendChild(x); chips.appendChild(chip);
      });
      const input = el("input", "fxed__taginput"); input.type = "text"; input.maxLength = 30; input.placeholder = t("FXED_TAGS_PH"); input.autocomplete = "off";
      const add = () => {
        const v = input.value.replace(/,/g, " ").trim();
        if (v && s.tags.length < 12 && !s.tags.some((x) => x.toLowerCase() === v.toLowerCase())) s.tags.push(v);
        input.value = ""; draw(); const n = chips.querySelector(".fxed__taginput"); if (n) n.focus();
      };
      input.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(); } else if (e.key === "Backspace" && !input.value && s.tags.length) { s.tags.pop(); draw(); chips.querySelector(".fxed__taginput").focus(); } });
      input.addEventListener("blur", () => { if (input.value.trim()) add(); });
      chips.appendChild(input);
    };
    draw();
    tagsBox.appendChild(chips);
    tagsBox.appendChild(el("span", "fxed__hint", t("FXED_TAGS_HINT")));
    box.appendChild(tagsBox);
    let list = $("fxed-mfr-list");
    if (!list) { list = el("datalist"); list.id = "fxed-mfr-list"; document.body.appendChild(list); }
    list.textContent = "";
    (window.FixtureEditor.manufacturers || []).forEach((m) => { const o = el("option"); o.value = m; list.appendChild(o); });
  }

  // ------------------------------------------------------------------------------------------------------ Kanaele
  function renderModes() {
    const bar = $("fxed-modes");
    bar.textContent = "";
    E.spec.modes.forEach((m, i) => {
      const b = el("button", "fxed__mode" + (i === E.mode ? " fxed__mode--on" : ""), m.name || "?");
      b.type = "button";
      b.addEventListener("click", () => { E.mode = i; E.open.clear(); renderModes(); });
      bar.appendChild(b);
    });
    const add = textBtn("plus", t("FXED_MODE_ADD"), () => {
      const copy = JSON.parse(JSON.stringify(mode()));
      copy.name = t("FXED_MODE_N", { n: E.spec.modes.length + 1 });
      copy.channels.forEach((c) => { c._k = ++uid; });
      E.spec.modes.push(copy); E.mode = E.spec.modes.length - 1; E.open.clear(); renderModes();
    }, "fxed__mode fxed__mode--add");
    add.title = t("FXED_MODE_ADD_TIP");
    bar.appendChild(add);
    const tools = el("div", "fxed__modetools");
    const nameIn = textInput(mode().name, (v) => { mode().name = v; const on = bar.querySelector(".fxed__mode--on"); if (on) on.textContent = v || "?"; renderWarnings(); }, 40, t("FXED_MODE_NAME"));
    nameIn.setAttribute("aria-label", t("FXED_MODE_NAME")); nameIn.dataset.fxed = "mode";
    tools.appendChild(nameIn);
    tools.appendChild(iconBtn("trash", t("FXED_MODE_DEL"), async () => {
      if (!(await confirmDelete("FXED_DEL_MODE_TITLE", "FXED_DEL_MODE_BODY", { name: mode().name || "?" }))) return;
      E.spec.modes.splice(E.mode, 1); E.mode = Math.max(0, E.mode - 1); E.open.clear(); renderModes();
    }, E.spec.modes.length < 2));
    bar.appendChild(tools);
    renderChannels();
  }

  function attrSelect(ch) {
    const sel = el("select", "settings__text-input fxed__attr");
    sel.setAttribute("aria-label", t("FXED_ATTR"));
    const groups = {};
    E.palette.forEach((p) => { (groups[p.group] = groups[p.group] || []).push(p); });
    Object.keys(groups).forEach((g) => {
      const og = el("optgroup"); og.label = t("FXED_G_" + g);
      groups[g].forEach((p) => { const o = el("option", "", p.name + (p.pretty && p.pretty !== p.name ? "  (" + p.pretty + ")" : "")); o.value = p.name; og.appendChild(o); });
      sel.appendChild(og);
    });
    const og = el("optgroup"); og.label = t("FXED_G_custom");
    const custom = el("option", "", t("FXED_CUSTOM")); custom.value = "__custom__"; og.appendChild(custom); sel.appendChild(og);     // eigener Name: ganz unten, getrennt
    sel.value = isCustom(ch) ? "__custom__" : ch.attribute;
    sel.addEventListener("change", () => {
      if (sel.value === "__custom__") ch.attribute = "";
      else { ch.attribute = sel.value; if (!E.physical[sel.value]) { delete ch.physical_from; delete ch.physical_to; } }
      renderChannels();
    });
    return sel;
  }

  function rangesPanel(ch) {
    const panel = el("div", "fxed__ranges");
    const list = el("div", "fxed__rangelist");
    ch.ranges.forEach((r, i) => {
      const row = el("div", "fxed__range");
      const from = el("input", "settings__text-input fxed__num");
      from.type = "number"; from.min = 0; from.max = 255; from.value = r.from; from.setAttribute("aria-label", t("FXED_RANGE_FROM"));
      from.readOnly = i === 0;
      from.addEventListener("input", () => { r.from = from.value === "" ? "" : Number(from.value); from.classList.remove("fxed__bad"); });
      row.appendChild(el("span", "fxed__rangeprefix", t("FXED_RANGE_FROM")));
      row.appendChild(from);
      const nm = textInput(r.name, (v) => { r.name = v; }, 40, t("FXED_RANGE_NAME"));
      nm.setAttribute("aria-label", t("FXED_RANGE_NAME"));
      row.appendChild(nm);
      row.appendChild(iconBtn("trash", t("FXED_REMOVE"), async () => {
        if (!(await confirmDelete("FXED_DEL_RANGE_TITLE", "FXED_DEL_RANGE_BODY", { name: (r.name || "").trim() || String(r.from) }))) return;
        ch.ranges.splice(i, 1); renderChannels();
      }));
      list.appendChild(row);
    });
    panel.appendChild(list);
    panel.appendChild(textBtn("plus", t("FXED_ADD_RANGE"), () => {
      const last = ch.ranges.length ? Math.min(255, Number(ch.ranges[ch.ranges.length - 1].from) + 10) : 0;
      ch.ranges.push({ from: last, name: "" }); renderChannels();
    }, "fxed__addrange"));
    if (E.physical[ch.attribute]) {
      const [lo, hi] = E.physical[ch.attribute];
      const ph = el("div", "fxed__phys");
      ph.appendChild(el("span", "fxed__label", t("FXED_PHYS")));
      [["physical_from", lo], ["physical_to", hi]].forEach(([key, dflt]) => {
        const i = el("input", "settings__text-input fxed__num"); i.type = "number"; i.step = "any";
        i.value = ch[key] !== undefined ? ch[key] : dflt;
        i.addEventListener("input", () => { ch[key] = i.value === "" ? "" : Number(i.value); });
        ph.appendChild(i);
      });
      panel.appendChild(ph);
    }
    return panel;
  }

  function renderChannels() {
    const host = $("fxed-channels");
    host.textContent = "";
    const m = mode();
    let addr = 1;
    m.channels.forEach((ch, i) => {
      const row = el("div", "fxed__ch");
      row.dataset.k = ch._k;
      row.appendChild(el("div", "fxed__no", ch.bits === 16 ? `${addr}–${addr + 1}` : String(addr)));
      addr += ch.bits === 16 ? 2 : 1;
      const sel = attrSelect(ch); sel.dataset.fxed = "attribute";
      const attrCell = el("div", "fxed__cell fxed__cell--attr");
      attrCell.appendChild(sel);
      if (isCustom(ch)) {
        const ci = textInput(ch.attribute, (v) => { ch.attribute = v; }, 40, t("FXED_CUSTOM_PH"));
        ci.dataset.fxed = "attribute"; ci.setAttribute("aria-label", t("FXED_CUSTOM_PH"));
        attrCell.appendChild(ci);
      }
      row.appendChild(attrCell);
      const lab = textInput(ch.label, (v) => { ch.label = v; }, 40, t("FXED_LABEL"));
      lab.setAttribute("aria-label", t("FXED_LABEL"));
      row.appendChild(lab);
      const bits = el("select", "settings__text-input fxed__bits"); bits.setAttribute("aria-label", t("FXED_BITS"));
      [8, 16].forEach((b) => { const o = el("option", "", b + " " + t("FXED_BITS")); o.value = b; bits.appendChild(o); });
      bits.value = String(ch.bits);
      bits.addEventListener("change", () => { ch.bits = Number(bits.value); renderChannels(); });
      row.appendChild(bits);
      const def = el("input", "settings__text-input fxed__num"); def.type = "number"; def.min = 0; def.max = 255; def.value = ch.default;
      def.title = t("FXED_DEFAULT"); def.setAttribute("aria-label", t("FXED_DEFAULT")); def.dataset.fxed = "default";
      def.addEventListener("input", () => { ch.default = def.value === "" ? "" : Number(def.value); def.classList.remove("fxed__bad"); });
      row.appendChild(def);
      const open = E.open.has(ch._k);
      const rb = el("button", "modal__button fxed__rbtn" + (open ? " fxed__rbtn--on" : "")); rb.type = "button";
      rb.appendChild(Icons.svg(open ? "chevron-down" : "chevron-right"));
      rb.appendChild(document.createTextNode(t("FXED_RANGES") + (ch.ranges.length ? " (" + ch.ranges.length + ")" : "")));
      rb.addEventListener("click", () => { if (open) E.open.delete(ch._k); else E.open.add(ch._k); renderChannels(); });
      row.appendChild(rb);
      const tools = el("div", "fxed__tools");
      tools.appendChild(iconBtn("arrow-up", t("FXED_UP"), () => { m.channels.splice(i - 1, 0, m.channels.splice(i, 1)[0]); renderChannels(); }, i === 0));
      tools.appendChild(iconBtn("arrow-down", t("FXED_DOWN"), () => { m.channels.splice(i + 1, 0, m.channels.splice(i, 1)[0]); renderChannels(); }, i === m.channels.length - 1));
      tools.appendChild(iconBtn("trash", t("FXED_REMOVE"), async () => {
        if (!(await confirmDelete("FXED_DEL_CH_TITLE", "FXED_DEL_CH_BODY", { n: i + 1, name: chName(ch, i) }))) return;
        const at = m.channels.indexOf(ch); if (at < 0) return;
        m.channels.splice(at, 1); E.open.delete(ch._k); renderChannels();
      }, m.channels.length < 2));
      row.appendChild(tools);
      host.appendChild(row);
      if (open) { const holder = el("div", "fxed__rangeholder"); holder.appendChild(rangesPanel(ch)); host.appendChild(holder); }
    });
    const bar = el("div", "fxed__addbar");
    bar.appendChild(textBtn("plus", t("FXED_ADD_CH"), () => { m.channels.push(newChannel("")); renderChannels(); const last = host.querySelector(".fxed__ch:last-of-type select"); if (last) last.focus(); }, "fxed__addch"));
    bar.appendChild(textBtn("", t("FXED_CSV"), () => $("fxed-csv-input").click(), "fxed__csv"));
    host.appendChild(bar);
    $("fxed-foot").textContent = t("FXED_FOOT", { n: footprint(m) });
    $("fxed-foot").classList.toggle("fxed__foot--bad", footprint(m) > 512);
    renderWarnings();
  }

  // CSV: eine Zeile je Kanal. Spalten (Kopfzeile, beliebige Reihenfolge, ; oder , oder Tab): Attribut, Beschriftung, Bit, Standard, Bereiche.
  // Bereiche: "0 Aus; 10 Nebel" oder "0-9 Aus; 10-255 Nebel" oder "0=Aus; 10=Nebel". Ohne Kopfzeile gilt die Reihenfolge Attribut; Beschriftung; Bit; Standard; Bereiche.
  function parseCsv(text) {
    const lines = text.replace(/^﻿/, "").split(/\r?\n/).filter((l) => l.trim());
    if (!lines.length) return [];
    const delim = [";", "\t", ","].map((d) => [d, lines[0].split(d).length]).sort((a, b) => b[1] - a[1])[0][0];
    const split = (l) => {                                                 // mit Anfuehrungszeichen: "0 Aus; 10 Nebel" bleibt eine Zelle
      const cells = []; let cur = "", q = false;
      for (let i = 0; i < l.length; i++) {
        const ch = l[i];
        if (ch === '"') { if (q && l[i + 1] === '"') { cur += '"'; i++; } else q = !q; }
        else if (ch === delim && !q) { cells.push(cur.trim()); cur = ""; }
        else cur += ch;
      }
      cells.push(cur.trim());
      return cells;
    };
    const names = { attribute: /^(attr|attribut|attribute|kanal ?name|name)/i, label: /^(label|beschriftung|funktion|function|bezeichnung|beschreibung|description)/i, bits: /^(bit|bits|aufl)/i, default: /^(default|standard|std)/i, ranges: /^(bereiche|ranges|range|stufen|werte)/i };
    let head = split(lines[0]);
    const mapping = {};
    head.forEach((h, i) => { for (const [k, re] of Object.entries(names)) if (mapping[k] === undefined && re.test(h)) { mapping[k] = i; break; } });
    let body = lines.slice(1);
    if (mapping.attribute === undefined) { Object.assign(mapping, { attribute: 0, label: 1, bits: 2, default: 3, ranges: 4 }); body = lines; }
    const out = [];
    body.forEach((line) => {
      const c = split(line);
      const attr = (c[mapping.attribute] || "").trim();
      if (!attr) return;
      const bitsRaw = mapping.bits !== undefined ? parseInt(c[mapping.bits], 10) : 8;
      const ranges = [];
      String(mapping.ranges !== undefined ? c[mapping.ranges] || "" : "").split(/[;|]/).forEach((part) => {
        const m = part.trim().match(/^(\d{1,3})(?:\s*[-–]\s*\d{1,3})?\s*[=:]?\s*(.*)$/);
        if (m) ranges.push({ from: Math.min(255, Number(m[1])), name: m[2].trim() });
      });
      ranges.sort((a, b) => a.from - b.from);
      if (ranges.length && ranges[0].from !== 0) ranges.unshift({ from: 0, name: "" });
      out.push(newChannel(attr, mapping.label !== undefined ? c[mapping.label] : "", ranges, bitsRaw === 16 ? 16 : 8, mapping.default !== undefined ? (parseInt(c[mapping.default], 10) || 0) : 0));
    });
    return out;
  }

  // ------------------------------------------------------------------------------------------------------ Bild & 3D
  function thumbUrl() {
    if (E.thumb.kind === "new") return E.thumb.url;
    if (E.thumb.kind === "keep" && E.replaceId) return `/api/library/installed/${encodeURIComponent(E.replaceId)}/thumbnail?v=${Date.now()}`;
    if (E.thumb.kind === "copy") return `/api/library/installed/${encodeURIComponent(E.thumb.copy_from)}/thumbnail`;
    return "";
  }

  function readImage(file) {                                               // beliebiges Bild -> PNG, hoechstens 512 Pixel breit/hoch (wie die Vorschaubilder bei GDTF Share)
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        const scale = Math.min(1, 512 / Math.max(img.naturalWidth || 1, img.naturalHeight || 1));
        const c = document.createElement("canvas");
        c.width = Math.max(1, Math.round((img.naturalWidth || 1) * scale)); c.height = Math.max(1, Math.round((img.naturalHeight || 1) * scale));
        c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
        URL.revokeObjectURL(url);
        const data = c.toDataURL("image/png");
        resolve({ data: data.split(",")[1], url: data });
      };
      img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("image")); };
      img.src = url;
    });
  }

  const toBase64 = (buffer) => { let s = ""; const bytes = new Uint8Array(buffer); for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000)); return btoa(s); };

  function renderMedia() {
    const box = $("fxed-pane-media");
    box.textContent = "";
    const s = E.spec;
    // Profilbild
    const pic = el("section", "fxed__card");
    pic.appendChild(el("h3", "fxed__h", t("FXED_PICTURE")));
    pic.appendChild(el("p", "fxed__hint", t("FXED_PICTURE_HINT")));
    const row = el("div", "fxed__media");
    const preview = el("div", "fxed__preview");
    const url = thumbUrl();
    if (url) { const img = el("img"); img.alt = ""; img.src = url; preview.appendChild(img); } else preview.appendChild(el("span", "fxed__hint", t("FXED_NO_PICTURE")));
    row.appendChild(preview);
    const actions = el("div", "fxed__mediaactions");
    actions.appendChild(textBtn("plus", t("FXED_PICTURE_CHOOSE"), () => $("fxed-image-input").click()));
    actions.appendChild(textBtn("trash", t("FXED_REMOVE"), async () => {
      if (!(await confirmDelete("FXED_DEL_PIC_TITLE", "FXED_DEL_PIC_BODY", {}))) return;
      E.thumb = { kind: "none" }; renderMedia();
    }, E.thumb.kind === "none" ? "fxed__hidden" : ""));
    row.appendChild(actions);
    pic.appendChild(row);
    box.appendChild(pic);
    // 3D-Modell
    const m3 = el("section", "fxed__card");
    m3.appendChild(el("h3", "fxed__h", t("FXED_MODEL")));
    if (isMoving()) {
      m3.appendChild(el("p", "fxed__hint", t("FXED_MODEL_MOVER")));
    } else {
      m3.appendChild(el("p", "fxed__hint", t("FXED_MODEL_HINT")));
      const r2 = el("div", "fxed__media");
      const info = el("div", "fxed__modelinfo");
      const label = E.model.kind === "new" ? E.model.filename : E.model.kind === "keep" ? (E.model.file || t("FXED_MODEL_KEEP")) : t("FXED_NO_MODEL");
      info.appendChild(el("strong", "", label));
      r2.appendChild(info);
      const a2 = el("div", "fxed__mediaactions");
      a2.appendChild(textBtn("plus", t("FXED_MODEL_CHOOSE"), () => $("fxed-model-input").click()));
      a2.appendChild(textBtn("trash", t("FXED_REMOVE"), async () => {
        if (!(await confirmDelete("FXED_DEL_MODEL_TITLE", "FXED_DEL_MODEL_BODY", { name: label }))) return;
        E.model = { kind: "none" }; renderMedia();
      }, E.model.kind === "none" ? "fxed__hidden" : ""));
      r2.appendChild(a2);
      m3.appendChild(r2);
      if (E.model.kind !== "none") {
        const dims = el("div", "fxed__dims");
        [["length", "FXED_DIM_L"], ["width", "FXED_DIM_W"], ["height", "FXED_DIM_H"]].forEach(([key, lk]) => {
          const i = el("input", "settings__text-input fxed__num"); i.type = "number"; i.min = 0.01; i.step = "0.01"; i.value = E.model[key];
          i.addEventListener("input", () => { E.model[key] = i.value === "" ? "" : Number(i.value); });
          dims.appendChild(field(t(lk), i));
        });
        m3.appendChild(dims);
      }
    }
    box.appendChild(m3);
    void s;
  }

  // ------------------------------------------------------------------------------------------------------ Pruefen / Speichern
  function validate() {
    const q = (sel) => document.querySelector("#fxed-body " + sel);
    const s = E.spec;
    if (!s.manufacturer.trim()) return [t("FXED_E_MISSING", { f: t("FXED_MANUFACTURER") }), () => q('[data-fxed="manufacturer"]'), "general"];
    if (!s.name.trim()) return [t("FXED_E_MISSING", { f: t("FXED_NAME") }), () => q('[data-fxed="name"]'), "general"];
    for (let mi = 0; mi < s.modes.length; mi++) {
      const m = s.modes[mi];
      const seen = new Map();
      for (let ci = 0; ci < m.channels.length; ci++) {
        const ch = m.channels[ci];
        const attr = (ch.attribute || "").trim();
        const rowEl = () => document.querySelector(`#fxed-channels .fxed__ch[data-k="${ch._k}"]`);
        const hint = s.modes.length > 1 ? `${m.name}: ` : "";
        const go = () => { if (E.mode !== mi) { E.mode = mi; renderModes(); } };
        if (!ATTR_RE.test(attr)) { go(); return [hint + t("FXED_E_ATTR", { n: ci + 1 }), () => { const r = rowEl(); return r && (r.querySelector('input[data-fxed="attribute"]') || r.querySelector("select")); }, "channels"]; }
        if (seen.has(attr.toLowerCase())) { go(); return [hint + t("FXED_E_DUP", { n: ci + 1, m: seen.get(attr.toLowerCase()) + 1, a: attr }), () => { const r = rowEl(); return r && r.querySelector("select"); }, "channels"]; }
        seen.set(attr.toLowerCase(), ci);
        const d = ch.default;
        if (d === "" || !Number.isInteger(d) || d < 0 || d > 255) { go(); return [hint + t("FXED_E_DEFAULT", { n: ci + 1 }), () => { const r = rowEl(); return r && r.querySelector('[data-fxed="default"]'); }, "channels"]; }
        if (ch.ranges.length) {
          const starts = ch.ranges.map((x) => x.from);
          if (starts.some((v) => v === "" || !Number.isInteger(v) || v < 0 || v > 255) || new Set(starts).size !== starts.length || Math.min(...starts) !== 0) {
            go(); E.open.add(ch._k); renderChannels();
            return [hint + t("FXED_E_RANGE", { n: ci + 1 }), () => document.querySelector(`#fxed-channels .fxed__ch[data-k="${ch._k}"] + .fxed__rangeholder`), "channels"];
          }
        }
      }
    }
    return null;
  }

  function payload() {
    const s = E.spec;
    const out = {
      manufacturer: s.manufacturer.trim(), name: s.name.trim(), short_name: s.short_name.trim(), description: s.description.trim(), category: s.category, tags: s.tags, weight: s.weight === "" ? 0 : s.weight,
      thumbnail: E.thumb.kind === "new" ? { data: E.thumb.data } : E.thumb.kind === "keep" ? { keep: true } : E.thumb.kind === "copy" ? { copy_from: E.thumb.copy_from } : null,
      model: null,
      modes: s.modes.map((m) => ({
        name: (m.name || "").trim(),
        channels: m.channels.map((c) => {
          const o = { attribute: c.attribute.trim(), label: (c.label || "").trim(), bits: c.bits, default: c.default, ranges: c.ranges.map((r) => ({ from: r.from, name: (r.name || "").trim() })) };
          if (E.physical[o.attribute]) { if (c.physical_from !== undefined && c.physical_from !== "") o.physical_from = c.physical_from; if (c.physical_to !== undefined && c.physical_to !== "") o.physical_to = c.physical_to; }
          return o;
        }),
      })),
    };
    if (E.model.kind === "new") out.model = { filename: E.model.filename, data: E.model.data, length: E.model.length, width: E.model.width, height: E.model.height };
    else if (E.model.kind === "keep") out.model = { keep: true, length: E.model.length, width: E.model.width, height: E.model.height };
    return out;
  }

  const FIELD_TAB = { manufacturer: "general", name: "general", short_name: "general", description: "general", category: "general", tags: "general", weight: "general", thumbnail: "media", model: "media" };
  function serverError(data) {
    const code = data.error;
    const p = { n: data.n, a: data.attr, m: data.other, limit: data.limit, mb: data.limit_mb, name: data.name, f: t({ manufacturer: "FXED_MANUFACTURER", name: "FXED_NAME", short_name: "FXED_SHORT" }[data.field] || "FXED_NAME") };
    const map = { missing: "FXED_E_MISSING", bad_attribute: "FXED_E_ATTR", duplicate: "FXED_E_DUP", bad_default: "FXED_E_DEFAULT", bad_range: "FXED_E_RANGE", exists: "FXED_E_EXISTS" };
    const key = map[code] || ("FXED_S_" + code);
    const text = i18n(key);
    const message = text && text !== key ? t(key, p) : (data.message || t("FXED_E_GENERIC"));
    const tab = FIELD_TAB[data.field] || (data.field ? "channels" : E.tab);
    const sel = data.field && ["manufacturer", "name", "short_name", "weight"].includes(data.field) ? () => document.querySelector(`#fxed-body [data-fxed="${data.field}"]`) : null;
    setError(message, sel, tab);
  }

  async function save() {
    if (E.busy) return;
    const bad = validate();
    if (bad) { setError(bad[0], bad[1], bad[2]); return; }
    setError("");
    E.busy = true; $("fxed-save").disabled = true;
    try {
      const res = await fetch("/api/fixture-editor", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ spec: payload(), replace_id: E.replaceId }) });
      let data = {};
      try { data = await res.json(); } catch (e) { /* leer */ }
      if (!res.ok) { serverError(data); return; }
      const warn = warnings();
      Modal.close(MODAL, true);
      _showToast(t("FXED_SAVED", { name: data.name }), "ok", 3000, true);
      if (warn.length) _showToast(warn.join(" "), "warn", 9000, true);
      document.dispatchEvent(new CustomEvent("fixture-library-changed"));
    } catch (e) {
      setError(t("FXED_E_GENERIC"));
    } finally {
      E.busy = false; $("fxed-save").disabled = false;
    }
  }

  // ------------------------------------------------------------------------------------------------------ Oeffnen
  async function ensurePalette() {
    if (E.palette.length) return true;
    try {
      const data = await (await fetch("/api/fixture-editor/palette")).json();
      E.palette = data.palette || []; E.physical = data.physical || {};
      return E.palette.length > 0;
    } catch (e) { return false; }
  }

  async function openEditor(fixtureId, asCopy) {
    if (!(await ensurePalette())) { _showToast(t("FXED_E_GENERIC"), "warn", 4000, true); return; }
    if (!(window.FixtureEditor.types || []).length) {                      // Liste fuer "aus vorhandenem Scheinwerfer laden", falls die Bibliothek noch nicht geladen ist
      try { const d = await (await fetch("/api/library/installed")).json(); window.FixtureEditor.setTypes(d.items || []); } catch (e) { /* egal */ }
    }
    E.replaceId = ""; E.copyOf = ""; E.inUse = 0; E.usedModes = {}; E.footprints = {}; E.mode = 0; E.open.clear(); E.notes = null; E.tab = "general";
    E.thumb = { kind: "none" }; E.model = { kind: "none" };
    if (fixtureId) {
      let data = null;
      try { const res = await fetch("/api/fixture-editor/" + encodeURIComponent(fixtureId) + (asCopy ? "?copy=1" : "")); data = res.ok ? await res.json() : null; } catch (e) { /* unten */ }
      if (!data) { _showToast(t("FXED_E_GENERIC"), "warn", 4000, true); return; }
      const sp = data.spec;
      E.spec = adopt(sp);
      if (asCopy) {
        E.copyOf = fixtureId; E.notes = sp.notes || null;
        if (sp.thumbnail && sp.thumbnail.copy_from) E.thumb = { kind: "copy", copy_from: sp.thumbnail.copy_from };
      } else {
        E.replaceId = data.id; E.inUse = data.in_use || 0; E.usedModes = data.used_modes || {}; E.footprints = data.footprints || {};
        if (sp.thumbnail === true) E.thumb = { kind: "keep" };
        if (sp.model && sp.model.file) E.model = { kind: "keep", file: sp.model.file, length: sp.model.length, width: sp.model.width, height: sp.model.height };
      }
    } else {
      E.spec = adopt(blank());
    }
    $("fxed-title").textContent = t(E.replaceId ? "FXED_TITLE_EDIT" : "FXED_TITLE");
    setError("");
    renderGeneral(); renderModes(); showTab("general");
    E.snap = snapshot();
    Modal._guards[MODAL] = guardClose;
    Modal.open(MODAL);
    if (!E.replaceId && !E.copyOf) setTimeout(() => { const f = document.querySelector('#fxed-body [data-fxed="manufacturer"]'); if (f) f.focus(); }, 80);
  }

  function init() {
    if (!$("fxed-body")) return;
    $("fxed-save").addEventListener("click", save);
    document.querySelectorAll("#fxed-body [data-fxed-tab]").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.fxedTab)));
    $("fxed-csv-input").addEventListener("change", async (e) => {
      const file = e.target.files[0]; e.target.value = "";
      if (!file) return;
      const rows = parseCsv(await file.text());
      if (!rows.length) { setError(t("FXED_CSV_EMPTY")); return; }
      setError("");
      const m = mode();
      m.channels = m.channels.length === 1 && !m.channels[0].label && !m.channels[0].ranges.length && m.channels[0].attribute === "Dimmer" ? rows : m.channels.concat(rows);
      renderChannels();
      _showToast(t("FXED_CSV_DONE", { n: rows.length }), "ok", 2500, true);
    });
    $("fxed-image-input").addEventListener("change", async (e) => {
      const file = e.target.files[0]; e.target.value = "";
      if (!file) return;
      try { const img = await readImage(file); E.thumb = { kind: "new", data: img.data, url: img.url }; setError(""); renderMedia(); }
      catch (err) { setError(t("FXED_S_bad_image"), null, "media"); }
    });
    $("fxed-model-input").addEventListener("change", async (e) => {
      const file = e.target.files[0]; e.target.value = "";
      if (!file) return;
      if (!/\.(glb|3ds|stl|obj)$/i.test(file.name)) { setError(t("FXED_S_bad_model"), null, "media"); return; }
      if (file.size > 25 * 1024 * 1024) { setError(t("FXED_S_file_too_large", { mb: 25 }), null, "media"); return; }
      const prev = E.model.kind !== "none" ? E.model : { length: 0.25, width: 0.25, height: 0.3 };
      E.model = { kind: "new", filename: file.name, data: toBase64(await file.arrayBuffer()), length: prev.length, width: prev.width, height: prev.height };
      setError(""); renderMedia();
    });
    document.addEventListener("i18n-applied", () => { if (E.spec && Modal.isOpen(MODAL)) { $("fxed-title").textContent = t(E.replaceId ? "FXED_TITLE_EDIT" : "FXED_TITLE"); renderGeneral(); renderModes(); showTab(E.tab); } });
  }
  window.FixtureEditor = {
    open: (id) => openEditor(id, false), copy: (id) => openEditor(id, true), manufacturers: [], types: [],
    setTypes(items) { this.types = items.map((f) => ({ id: f.id, label: `${f.manufacturer} – ${f.name}${f.revision ? " (" + String(f.revision).replace(/_/g, " ") + ")" : ""}` })).sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: "base" })); },
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
