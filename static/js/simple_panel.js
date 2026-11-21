// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Panel "Einfache Steuerung" (Typ simple): die schlichte Schwester der Scheinwerfersteuerung - zum Weitergeben an jemanden, der nur bedienen soll (zusammen mit dem Bedienmodus, kiosk.js).
 * Es nutzt die ganze Flaeche des Panels mit festen, prozentualen Feldern (die Bedienelemente scrollen nicht):
 *
 *   breit:  | Auswahl (38 %)            | BLACKOUT (immer, ganz oben, unabhaengig von der Auswahl)  |
 *           | jeder Scheinwerfer eine   | Helligkeit (Fader) | Farbe (Farbfeld)  | Position (Joystick) |
 *           | Kachel, nach Gruppen      | Zoom (Fader)       | Gobos                                    |
 *           |                           | Looks (Regenbogen, Kreis, Puls, Blitz, Aus)                   |
 *   schmal (unter ~720 px Breite): Kompaktmodus - ein Reiter je Bereich (Lichter | Helligkeit | Farbe | Bewegen | Strahl | Looks), Blackout bleibt immer sichtbar.
 *
 *  - Jedes Bedienelement sagt, was es ist (Fader, Farbfeld, Joystick ...): Fader haben einen sichtbaren Griff und eine Skala, der Joystick Pfeile und eine Mitte, das Farbfeld ein Fadenkreuz.
 *  - Auswahl: Kacheln mit Nummer, Name, Farbe und Helligkeit des Geraets (live); Gruppen als Abschnitte (Klick auf den Gruppennamen waehlt die Gruppe), der Rest nach Typ. Die Auswahl
 *    ist die des Programmers (WS `set_selection`) - sie gilt in allen Panels. Gruppen anlegen oder aendern gibt es hier bewusst nicht.
 *  - Was ein gewaehlter Scheinwerfer nicht kann, ist abgedunkelt UND nicht bedienbar (Felder bleiben an ihrem Platz; Looks einzeln: Regenbogen braucht Farbe, Kreis Pan/Tilt, Puls/Blitz Helligkeit).
 *  - Reaktion sofort: jede Bedienung zeigt sich im Panel ohne auf den Server zu warten (Blackout, Fader, Farbe ...); Live-Werte aus dem DMX-Puffer kommen erst nach einer kurzen Pause wieder an.
 * Werte gehen als `set_fixture_values` (abstrakt: dimmer / color / pan / tilt / zoom, 0-255) bzw. `set_fixture_raw_channel` (Gobo) an den Server und landen im Programmer
 * (als Cue speicherbar); Looks als `simple_look`. Faehigkeiten der Auswahl: GET /api/simple/caps (app/simple_caps.py). Klassisches Skript, laeuft nach app.js. */
(function () {
  "use strict";

  const t = (key) => (window.__panelAPI && window.__panelAPI.i18n ? window.__panelAPI.i18n(key) : key);
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const send = (type, payload) => { if (window.__panelAPI && window.__panelAPI.sendToServer) window.__panelAPI.sendToServer(type, payload); };
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const toByte = (pct) => Math.round(clamp(pct, 0, 100) * 2.55);
  const SWATCHES = [["#ffffff", "SP_C_WHITE"], ["#ffc58f", "SP_C_WARM"], ["#ff0000", "SP_C_RED"], ["#ff7a00", "SP_C_ORANGE"], ["#ffd400", "SP_C_YELLOW"], ["#22cc22", "SP_C_GREEN"],
    ["#00d4d4", "SP_C_CYAN"], ["#1a3cff", "SP_C_BLUE"], ["#8a2be2", "SP_C_VIOLET"], ["#ff3fa4", "SP_C_PINK"]];
  /** Looks: Standard-Effekte (defaults/effects); need = was die Auswahl koennen muss. */
  const LOOKS = [
    { id: "rainbow", cat: "color", key: "SP_L_RAINBOW", need: "color", css: "linear-gradient(90deg, #f00, #ff0, #0f0, #0ff, #00f, #f0f)" },
    { id: "circle", cat: "position", key: "SP_L_CIRCLE", need: "move", css: "" },
    { id: "pulse", cat: "dimmer", key: "SP_L_PULSE", need: "dimmer", css: "" },
    { id: "strobe", cat: "dimmer", key: "SP_L_STROBE", need: "dimmer", css: "" },
  ];
  const JOY = { dead: 0.05, k: 5, vmax: 0.45, ms: 33 };                       // wie der Joystick der Scheinwerfersteuerung: je Sekunde bis zu 45 % des Bereichs ganz aussen
  const speedOf = (r) => (r <= JOY.dead ? 0 : JOY.vmax * (Math.exp(JOY.k * Math.min(1, (r - JOY.dead) / (1 - JOY.dead))) - 1) / (Math.exp(JOY.k) - 1));
  const COMPACT_BELOW = 720;                                                   // schmaler als das (px): Reiter statt alles auf einmal
  const HOLD_MS = 900;                                                         // so lange nach einer eigenen Bedienung ignoriert das Panel Live-Werte (sonst springt der Griff kurz zurueck)
  const TABS = [["sel", "SP_TAB_SELECT"], ["dim", "SP_TAB_DIMMER"], ["col", "SP_TAB_COLOR"], ["pos", "SP_TAB_MOVE"], ["beam", "SP_TAB_BEAM"], ["look", "SP_TAB_LOOKS"]];

  const hsvToRgb = (h, s, v) => {
    const c = v * s; const x = c * (1 - Math.abs(((h / 60) % 2) - 1)); const m = v - c;
    const [r, g, b] = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
    return { r: Math.round((r + m) * 255), g: Math.round((g + m) * 255), b: Math.round((b + m) * 255) };
  };
  const hexToRgb = (hex) => ({ r: parseInt(hex.slice(1, 3), 16), g: parseInt(hex.slice(3, 5), 16), b: parseInt(hex.slice(5, 7), 16) });
  const css = (c) => `rgb(${c.r}, ${c.g}, ${c.b})`;
  const views = new Set();

  function selected() { return ((typeof client !== "undefined" && client.state && client.state.selected_fixture_ids) || []).slice(); }
  function fixturesMap() { return (typeof client !== "undefined" && client.state && client.state.fixtures) || {}; }
  function groupsMap() { return (typeof client !== "undefined" && client.state && client.state.groups) || {}; }
  const liveOf = (id) => (window.__fixturesLive || {})[id];
  function typeName(fx) {                                                       // lesbarer Typname fuer Abschnitte ohne Gruppe
    return String(fx.fixture_type || "").split("@").slice(-2, -1)[0] || String(fx.fixture_type || "").replace(/^__generic_/, "").replace(/_/g, " ");
  }

  /** Fader mit sichtbarem Griff und Skala (senkrecht oder waagerecht). Rueckgabe { root, set(pct), onInput(fn(pct, ende)) }. */
  function makeFader(vertical, label) {
    const root = el("div", "smp__fader " + (vertical ? "smp__fader--v" : "smp__fader--h"));
    root.setAttribute("role", "slider"); root.setAttribute("aria-label", label); root.setAttribute("aria-valuemin", "0"); root.setAttribute("aria-valuemax", "100");
    root.tabIndex = 0;
    const scale = el("div", "smp__fader-scale");
    (vertical ? [100, 75, 50, 25, 0] : [0, 25, 50, 75, 100]).forEach((n) => scale.appendChild(el("span", "", String(n))));
    const track = el("div", "smp__fader-track");
    const fill = el("div", "smp__fader-fill");
    const handle = el("div", "smp__fader-handle");
    const value = el("span", "smp__fader-value", "0");
    handle.append(el("span", "smp__fader-grip"), value, el("span", "smp__fader-grip"));
    track.append(fill, handle);
    root.append(scale, track);
    let pct = 0;
    let handler = null;
    let dragging = false;
    const set = (v) => {
      pct = clamp(v, 0, 100);
      if (vertical) { fill.style.height = pct + "%"; handle.style.bottom = pct + "%"; } else { fill.style.width = pct + "%"; handle.style.left = pct + "%"; }
      value.textContent = Math.round(pct) + (vertical ? "" : "");
      root.setAttribute("aria-valuenow", String(Math.round(pct)));
    };
    const from = (e) => { const r = track.getBoundingClientRect(); return vertical ? (1 - (e.clientY - r.top) / r.height) * 100 : ((e.clientX - r.left) / r.width) * 100; };
    root.addEventListener("pointerdown", (e) => { root.setPointerCapture(e.pointerId); dragging = true; set(from(e)); if (handler) handler(pct, false); });
    root.addEventListener("pointermove", (e) => { if (dragging) { set(from(e)); if (handler) handler(pct, false); } });
    const end = (e) => { if (!dragging) return; dragging = false; if (root.hasPointerCapture(e.pointerId)) root.releasePointerCapture(e.pointerId); if (handler) handler(pct, true); };
    root.addEventListener("pointerup", end);
    root.addEventListener("pointercancel", end);
    root.addEventListener("keydown", (e) => {                                   // Tastatur: Pfeile +/- 5 %
      const step = e.key === "ArrowUp" || e.key === "ArrowRight" ? 5 : e.key === "ArrowDown" || e.key === "ArrowLeft" ? -5 : 0;
      if (step) { e.preventDefault(); set(pct + step); if (handler) handler(pct, true); }
    });
    return { root, set, get value() { return pct; }, get dragging() { return dragging; }, onInput(fn) { handler = fn; } };
  }

  function buildPanel(panel) {
    const mc = (panel && panel.module_config) || {};
    const root = el("div", "smp");
    const view = { root, caps: null, capsKey: "", pan16: 32768, tilt16: 32768, color: { r: 255, g: 255, b: 255 }, dimmer: 100, mc, tab: "sel", looksOn: new Set(), holdUntil: 0 };
    const hold = () => { view.holdUntil = performance.now() + HOLD_MS; };

    // ================================================================= Auswahl (links)
    const sel = el("section", "smp__area smp__sel");
    sel.dataset.tab = "sel";
    const selHead = el("div", "smp__sel-head");
    const btnAll = el("button", "smp__chip", t("SP_ALL")); btnAll.type = "button";
    const btnNone = el("button", "smp__chip", t("SP_NONE")); btnNone.type = "button";
    selHead.append(btnAll, btnNone);
    const selHint = el("div", "smp__sel-hint", t("SP_SELECT_HINT"));              // freundlicher Hinweis (kein Fehler): solange nichts gewaehlt ist
    const selList = el("div", "smp__sel-list");
    sel.append(selHead, selHint, selList);

    // ================================================================= Bedienfelder (rechts)
    const box = (area, tab, titleKey, kindKey) => {
      const b = el("section", "smp__area smp__box smp__box--" + area); b.dataset.tab = tab; b.dataset.area = area;
      if (titleKey) { const head = el("div", "smp__head"); head.append(el("span", "smp__label", t(titleKey)), el("span", "smp__kind", t(kindKey))); b.appendChild(head); }
      return b;
    };

    const dimBox = box("dim", "dim", "SP_DIMMER", "SP_K_FADER");
    const dimFader = makeFader(true, t("SP_DIMMER"));
    const dimBtns = el("div", "smp__row");
    const btnOff = el("button", "smp__btn", t("SP_OFF")); btnOff.type = "button";
    const btnFull = el("button", "smp__btn smp__btn--accent", t("SP_FULL")); btnFull.type = "button";
    dimBtns.append(btnOff, btnFull);
    dimBox.append(dimFader.root, dimBtns);

    const colBox = box("col", "col", "SP_COLOR", "SP_K_FIELD");
    const field = el("div", "smp__field");
    const fieldDot = el("div", "smp__field-dot");
    field.appendChild(fieldDot);
    const sw = el("div", "smp__swatches");
    SWATCHES.forEach(([hex, key]) => {
      const b = el("button", "smp__swatch"); b.type = "button"; b.style.background = hex; b.title = t(key); b.setAttribute("aria-label", t(key)); b.dataset.hex = hex;
      sw.appendChild(b);
    });
    colBox.append(field, sw);

    const posBox = box("pos", "pos", "SP_MOVE", "SP_K_JOY");
    const padWrap = el("div", "smp__pad-wrap");
    const pad = el("div", "smp__pad");
    pad.setAttribute("role", "application"); pad.setAttribute("aria-label", t("SP_MOVE"));
    [["up", "▲"], ["down", "▼"], ["left", "◀"], ["right", "▶"]].forEach(([dir, glyph]) => pad.appendChild(el("span", "smp__pad-mark smp__pad-mark--" + dir, glyph)));
    pad.append(el("span", "smp__pad-cross smp__pad-cross--h"), el("span", "smp__pad-cross smp__pad-cross--v"));
    const knob = el("div", "smp__knob");
    pad.appendChild(knob);
    padWrap.appendChild(pad);
    const btnCenter = el("button", "smp__btn smp__btn--center"); btnCenter.type = "button";
    btnCenter.append(el("span", "smp__center-icon", "⊕"), el("span", "", t("SP_CENTER")));
    posBox.append(padWrap, btnCenter);

    const zoomBox = box("zoom", "beam", "SP_ZOOM", "SP_K_FADER");
    const zoomFader = makeFader(false, t("SP_ZOOM"));
    zoomFader.set(50);
    zoomBox.appendChild(zoomFader.root);

    const goboBox = box("gobo", "beam", "SP_GOBO", "SP_K_TAP");
    const goboStrip = el("div", "smp__gobos");
    goboBox.appendChild(goboStrip);

    const blackBox = box("black", "dim", "", "");
    const btnBlack = el("button", "smp__blackout"); btnBlack.type = "button";
    const blackText = el("span", "smp__blackout-text", t("SP_BLACKOUT"));
    const blackSub = el("span", "smp__blackout-sub", t("SP_BLACKOUT_HINT"));
    btnBlack.append(blackText, blackSub);
    blackBox.appendChild(btnBlack);

    const lookBox = box("look", "look", "SP_LOOKS", "SP_K_TAP");
    const lookGrid = el("div", "smp__looks");
    LOOKS.forEach((look) => {
      const b = el("button", "smp__look"); b.type = "button"; b.dataset.look = look.id;
      const dot = el("span", "smp__look-dot"); if (look.css) dot.style.background = look.css;
      b.append(dot, el("span", "smp__look-name", t(look.key)));
      lookGrid.appendChild(b);
    });
    const btnLooksOff = el("button", "smp__look smp__look--off"); btnLooksOff.type = "button";
    btnLooksOff.append(el("span", "smp__look-dot"), el("span", "smp__look-name", t("SP_L_OFF")));
    lookGrid.appendChild(btnLooksOff);
    lookBox.appendChild(lookGrid);

    const ctl = el("div", "smp__ctl");
    ctl.append(blackBox, dimBox, colBox, posBox, zoomBox, goboBox, lookBox);
    const empty = el("div", "smp__empty", t("SP_EMPTY"));
    ctl.appendChild(empty);

    // Kompaktmodus: Reiterleiste
    const tabs = el("div", "smp__tabs");
    TABS.forEach(([id, key]) => { const b = el("button", "smp__tab", t(key)); b.type = "button"; b.dataset.tab = id; tabs.appendChild(b); });
    const tabBlack = el("button", "smp__tab smp__tab--black", t("SP_BLACKOUT")); tabBlack.type = "button";
    tabs.appendChild(tabBlack);
    const main = el("div", "smp__main");
    main.append(sel, ctl);
    root.append(tabs, main);

    // ================================================================= Auswahl
    const setSelection = (ids) => {
      if (client.state) client.state.selected_fixture_ids = ids;
      send("set_selection", { ids });
      refresh();
    };
    const tileById = new Map();
    function buildSelection() {
      selList.textContent = "";
      tileById.clear();
      const fixtures = fixturesMap();
      const sorted = Object.values(fixtures).sort((a, b) => (a.fid || 0) - (b.fid || 0));
      if (!sorted.length) { selList.appendChild(el("div", "smp__hint", t("SP_NO_FIXTURES"))); return; }
      const section = (title, ids) => {
        const wrap = el("div", "smp__group");
        const head = el("button", "smp__group-head", title); head.type = "button"; head.title = t("SP_SELECT_GROUP");
        head.addEventListener("click", () => {
          const now = new Set(selected());
          const allIn = ids.every((id) => now.has(id));
          setSelection(allIn ? [...now].filter((id) => !ids.includes(id)) : [...new Set([...now, ...ids])]);
        });
        const grid = el("div", "smp__tiles");
        ids.forEach((id) => {
          const fx = fixtures[id];
          if (!fx) return;
          const tile = el("button", "smp__tile"); tile.type = "button"; tile.dataset.id = id;
          const swatch = el("span", "smp__tile-swatch");
          const num = el("span", "smp__tile-num", String(fx.fid || ""));
          const name = el("span", "smp__tile-name", fx.name || "");
          const pct = el("span", "smp__tile-pct", "");
          tile.append(num, swatch, name, pct);
          tile.addEventListener("click", () => {
            const now = new Set(selected());
            if (now.has(id)) now.delete(id); else now.add(id);
            setSelection([...now]);
          });
          grid.appendChild(tile);
          if (!tileById.has(id)) tileById.set(id, []);
          tileById.get(id).push({ tile, swatch, pct });
        });
        wrap.append(head, grid);
        selList.appendChild(wrap);
      };
      const inGroup = new Set();
      Object.entries(groupsMap()).forEach(([name, ids]) => {
        const valid = (ids || []).filter((id) => fixtures[id]).sort((a, b) => (fixtures[a].fid || 0) - (fixtures[b].fid || 0));
        if (!valid.length) return;
        valid.forEach((id) => inGroup.add(id));
        section(name, valid);
      });
      const rest = {};
      sorted.filter((f) => !inGroup.has(f.id)).forEach((f) => { (rest[typeName(f)] = rest[typeName(f)] || []).push(f.id); });
      Object.entries(rest).forEach(([name, ids]) => section(name, ids));
      paintSelection();
    }
    function paintSelection() {
      const now = new Set(selected());
      tileById.forEach((list, id) => list.forEach((x) => x.tile.classList.toggle("smp__tile--on", now.has(id))));
      selList.querySelectorAll(".smp__group").forEach((g) => {
        const ids = [...g.querySelectorAll(".smp__tile")].map((x) => x.dataset.id);
        g.querySelector(".smp__group-head").classList.toggle("smp__group-head--on", ids.length > 0 && ids.every((id) => now.has(id)));
      });
    }
    function paintTiles() {                                                 // Farbe und Helligkeit jedes Geraets auf seiner Kachel
      tileById.forEach((list, id) => {
        const live = liveOf(id) || {};
        const dim = Number.isFinite(live.dimmer) ? live.dimmer : null;
        const color = live.color && Number.isFinite(live.color.r) ? live.color : null;
        list.forEach((x) => {
          x.swatch.style.background = color ? css(color) : "";
          x.swatch.style.opacity = dim === null ? "0.35" : String(0.25 + 0.75 * clamp(dim, 0, 100) / 100);
          x.pct.textContent = dim === null ? "" : Math.round(dim) + "%";
        });
      });
    }
    btnAll.addEventListener("click", () => setSelection(Object.keys(fixturesMap())));
    btnNone.addEventListener("click", () => setSelection([]));

    // ================================================================= Faehigkeiten
    async function loadCaps() {
      const ids = selected();
      const key = ids.join(",");
      if (key === view.capsKey) return;
      view.capsKey = key;
      if (!ids.length) { view.caps = null; paintCaps(); return; }
      try {
        const res = await fetch("/api/simple/caps?ids=" + encodeURIComponent(key));
        const data = await res.json();
        if (view.capsKey !== key) return;
        view.caps = data.ok ? data : null;
        const first = ids.map(liveOf).find(Boolean);                       // Startwerte: der erste gewaehlte Scheinwerfer
        if (first) {
          if (Number.isFinite(first.pan)) view.pan16 = clamp(first.pan * 655.35, 0, 65535);
          if (Number.isFinite(first.tilt)) view.tilt16 = clamp(first.tilt * 655.35, 0, 65535);
          if (Number.isFinite(first.dimmer)) { view.dimmer = first.dimmer; paintDimmer(); }
        }
      } catch (err) { view.caps = null; }
      paintCaps();
    }
    /** Bereich bedienbar machen / sperren: abgedunkelt UND alle Knoepfe / Fader darin ausser Funktion. */
    const enable = (b, ok) => {
      b.classList.toggle("smp__box--off", !ok);
      b.querySelectorAll("button, input").forEach((n) => { n.disabled = !ok; });
      b.querySelectorAll(".smp__fader").forEach((n) => { n.tabIndex = ok ? 0 : -1; n.setAttribute("aria-disabled", ok ? "false" : "true"); });
    };
    function paintCaps() {
      const c = view.caps;
      const has = !!c;
      empty.hidden = has;
      selHint.hidden = has;
      ctl.classList.toggle("smp__ctl--empty", !has);
      const canMove = has && (c.pan || c.tilt);
      enable(dimBox, has && (c.dimmer || c.color !== "none"));
      enable(colBox, has && c.color !== "none");
      enable(posBox, canMove);
      enable(zoomBox, has && c.zoom);
      enable(goboBox, has && !!(c.gobo && c.gobo.slots && c.gobo.slots.length));
      enable(lookBox, has);
      const can = { color: has && c.color !== "none", move: canMove, dimmer: has && c.dimmer };           // Looks einzeln: nur, was die Auswahl wirklich kann
      lookGrid.querySelectorAll(".smp__look[data-look]").forEach((b) => {
        const look = LOOKS.find((l) => l.id === b.dataset.look);
        const ok = has && !!can[look.need];
        b.disabled = !ok;
        b.classList.toggle("smp__look--na", !ok);
      });
      goboStrip.textContent = "";
      if (has && c.gobo && c.gobo.slots) {
        c.gobo.slots.forEach((slot) => {
          const b = el("button", "smp__gobo"); b.type = "button"; b.title = slot.name;
          if (slot.image) { const img = document.createElement("img"); img.src = slot.image; img.alt = slot.name; img.draggable = false; b.appendChild(img); }
          else b.appendChild(el("span", "", slot.name.slice(0, 3)));
          b.addEventListener("click", () => {
            const ids = selected().filter((id) => c.gobo.ids.includes(id));
            if (ids.length) send("set_fixture_raw_channel", { ids, channel_offset: c.gobo.channel_offset, value: slot.value });
            goboStrip.querySelectorAll(".smp__gobo").forEach((x) => x.classList.toggle("smp__gobo--on", x === b));
          });
          goboStrip.appendChild(b);
        });
      }
    }

    // ================================================================= Werte senden
    let lastSend = 0;
    let pending = null;
    const flush = () => { if (pending) { const p = pending; pending = null; lastSend = performance.now(); send("set_fixture_values", p); } };
    const push = (values, now) => {
      const ids = selected();
      if (!ids.length) return;
      hold();
      pending = Object.assign(pending || {}, values, { ids });
      if (now || performance.now() - lastSend >= JOY.ms) flush();
      else setTimeout(flush, JOY.ms);
    };
    function paintDimmer() {
      if (!dimFader.dragging) dimFader.set(view.dimmer);
      fieldDot.style.background = css(view.color);
    }
    const setDimmer = (pct, now) => { view.dimmer = clamp(pct, 0, 100); dimFader.set(view.dimmer); fieldDot.style.background = css(view.color); push({ dimmer: toByte(view.dimmer) }, now); };
    const setColor = (rgb, now) => { view.color = rgb; fieldDot.style.background = css(rgb); push({ color: rgb }, now); };

    dimFader.onInput((pct, ended) => setDimmer(pct, ended));
    btnOff.addEventListener("click", () => setDimmer(0, true));
    btnFull.addEventListener("click", () => setDimmer(100, true));

    const colorFrom = (e) => {
      const r = field.getBoundingClientRect();
      const x = clamp((e.clientX - r.left) / r.width, 0, 1); const y = clamp((e.clientY - r.top) / r.height, 0, 1);
      fieldDot.style.left = x * 100 + "%"; fieldDot.style.top = y * 100 + "%";
      return hsvToRgb(x * 359.9, clamp(y / 0.85, 0, 1), 1);                       // oben Weiss, unten satte Farbe
    };
    field.addEventListener("pointerdown", (e) => { field.setPointerCapture(e.pointerId); setColor(colorFrom(e)); });
    field.addEventListener("pointermove", (e) => { if (field.hasPointerCapture(e.pointerId)) setColor(colorFrom(e)); });
    field.addEventListener("pointerup", (e) => { if (field.hasPointerCapture(e.pointerId)) { field.releasePointerCapture(e.pointerId); flush(); } });
    sw.addEventListener("click", (e) => { const b = e.target.closest(".smp__swatch"); if (b) setColor(hexToRgb(b.dataset.hex), true); });

    zoomFader.onInput((pct, ended) => push({ zoom: toByte(pct) }, ended));

    // Joystick: Federstick, Geschwindigkeit nach Auslenkung
    let joyTimer = 0;
    const joyVec = { x: 0, y: 0 };
    const joyStop = () => { clearInterval(joyTimer); joyTimer = 0; joyVec.x = joyVec.y = 0; knob.style.transform = "translate(-50%, -50%)"; knob.classList.remove("smp__knob--held"); };
    const joyTick = () => {
      const dt = JOY.ms / 1000;
      const r = Math.hypot(joyVec.x, joyVec.y);
      if (r <= JOY.dead) return;
      const v = speedOf(Math.min(1, r)) / r;
      view.pan16 = clamp(view.pan16 + joyVec.x * v * dt * 65535, 0, 65535);
      view.tilt16 = clamp(view.tilt16 - joyVec.y * v * dt * 65535, 0, 65535);          // Stick nach oben = Tilt hoch
      push({ pan: Math.round(view.pan16 / 257), tilt: Math.round(view.tilt16 / 257), pan16: Math.round(view.pan16), tilt16: Math.round(view.tilt16) }, true);
    };
    const joyFrom = (e) => {
      const r = pad.getBoundingClientRect();
      let x = ((e.clientX - r.left) / r.width - 0.5) * 2; let y = ((e.clientY - r.top) / r.height - 0.5) * 2;
      const len = Math.hypot(x, y);
      if (len > 1) { x /= len; y /= len; }
      joyVec.x = x; joyVec.y = y;
      knob.style.transform = `translate(calc(-50% + ${x * 42}%), calc(-50% + ${y * 42}%))`;
    };
    pad.addEventListener("pointerdown", (e) => { pad.setPointerCapture(e.pointerId); knob.classList.add("smp__knob--held"); joyFrom(e); if (!joyTimer) joyTimer = setInterval(joyTick, JOY.ms); });
    pad.addEventListener("pointermove", (e) => { if (pad.hasPointerCapture(e.pointerId)) joyFrom(e); });
    const joyEnd = (e) => { if (pad.hasPointerCapture(e.pointerId)) pad.releasePointerCapture(e.pointerId); joyStop(); };
    pad.addEventListener("pointerup", joyEnd);
    pad.addEventListener("pointercancel", joyEnd);
    btnCenter.addEventListener("click", () => { view.pan16 = view.tilt16 = 32768; push({ pan: 128, tilt: 128, pan16: 32768, tilt16: 32768 }, true); });

    // Blackout: sofort sichtbar (die Rueckmeldung des Servers bestaetigt nur)
    const paintBlackout = () => {
      const on = !!window.__blackout;
      btnBlack.classList.toggle("smp__blackout--on", on);
      tabBlack.classList.toggle("smp__tab--on", on);
      blackText.textContent = t(on ? "SP_BLACKOUT_ON" : "SP_BLACKOUT");
      blackSub.textContent = t(on ? "SP_BLACKOUT_HINT_ON" : "SP_BLACKOUT_HINT");
    };
    const toggleBlackout = () => {
      window.__blackout = !window.__blackout;                                 // optimistisch: sofort anzeigen
      paintBlackout();
      send("set_blackout", { enabled: window.__blackout });
      if (window.__syncBlackout) window.__syncBlackout();
    };
    btnBlack.addEventListener("click", toggleBlackout);
    tabBlack.addEventListener("click", toggleBlackout);
    view.paintBlackout = paintBlackout;

    // Looks (Standard-Effekte, der Server legt sie bei Bedarf in der Show an)
    const runLook = (id, on) => send("simple_look", { look: id, on });
    function paintLooks() { lookGrid.querySelectorAll(".smp__look[data-look]").forEach((b) => b.classList.toggle("smp__look--on", view.looksOn.has(b.dataset.look))); }
    lookGrid.addEventListener("click", (e) => {
      const b = e.target.closest(".smp__look");
      if (!b || b.disabled || !selected().length) return;
      if (b.classList.contains("smp__look--off")) { send("run_command", { command: "Effect Off", log_to_history: false }); view.looksOn.clear(); paintLooks(); return; }
      const look = LOOKS.find((l) => l.id === b.dataset.look);
      if (!look) return;
      if (view.looksOn.has(look.id)) { runLook(look.id, false); view.looksOn.delete(look.id); }
      else { LOOKS.filter((l) => l.cat === look.cat).forEach((l) => view.looksOn.delete(l.id)); runLook(look.id, true); view.looksOn.add(look.id); }
      paintLooks();
    });

    // ================================================================= Kompaktmodus (Reiter)
    function setTab(id) { view.tab = id; root.dataset.tab = id; tabs.querySelectorAll(".smp__tab[data-tab]").forEach((b) => b.classList.toggle("smp__tab--active", b.dataset.tab === id)); }
    tabs.addEventListener("click", (e) => { const b = e.target.closest(".smp__tab[data-tab]"); if (b) setTab(b.dataset.tab); });
    const sizeCheck = () => {
      const w = root.clientWidth;
      const compact = w > 0 && w < COMPACT_BELOW;
      root.classList.toggle("smp--compact", compact);
      empty.textContent = t("SP_EMPTY_COMPACT");                              // nur im Kompaktmodus sichtbar (andere Reiter als "Lichter"): nennt den Reiter
    };
    if (typeof ResizeObserver !== "undefined") { const ro = new ResizeObserver(sizeCheck); ro.observe(root); }
    setTab("sel");

    // ================================================================= Nachfuehren
    function refresh() { paintSelection(); loadCaps(); paintLooks(); }
    view.refresh = refresh;
    view.rebuild = () => { buildSelection(); refresh(); paintTiles(); };
    view.live = () => {                                                      // Live-Werte aus dem DMX-Puffer (nach einer kurzen Pause seit der letzten eigenen Bedienung)
      paintTiles();
      paintBlackout();
      const live = selected().map(liveOf).find(Boolean);
      if (!live || joyTimer || pending || performance.now() < view.holdUntil || dimFader.dragging) return;
      if (live.color && Number.isFinite(live.color.r)) { view.color = { r: live.color.r, g: live.color.g, b: live.color.b }; fieldDot.style.background = css(view.color); }
      if (Number.isFinite(live.dimmer)) { view.dimmer = live.dimmer; dimFader.set(view.dimmer); }
    };
    view.timer = setInterval(() => { if (!root.isConnected) { clearInterval(view.timer); joyStop(); views.delete(view); return; } view.live(); }, 250);
    views.add(view);
    dimFader.set(view.dimmer);
    buildSelection();
    paintCaps();
    paintBlackout();
    loadCaps();
    sizeCheck();
    return root;
  }

  // Live-Werte und Blackout sofort darstellen (statt auf den Takt zu warten)
  let liveScheduled = false;
  document.addEventListener("fixtures-live-values", () => {
    if (liveScheduled) return;
    liveScheduled = true;
    requestAnimationFrame(() => { liveScheduled = false; views.forEach((v) => { if (v.root.isConnected) v.live(); }); });
  });
  let wrapped = false;
  const wrapBlackout = () => {
    if (wrapped || typeof window.__syncBlackout !== "function") return;
    wrapped = true;
    const original = window.__syncBlackout;
    window.__syncBlackout = function () { const r = original.apply(this, arguments); views.forEach((v) => v.paintBlackout && v.paintBlackout()); return r; };
  };

  window.__panelPlugins.register({
    type: "simple",
    buildContent(panel) { wrapBlackout(); return buildPanel(panel); },
    onMessage(panelEl, type) {
      views.forEach((v) => {
        if (!panelEl.contains(v.root)) return;
        if (type === "selection_changed") v.refresh();
        else if (type === "fixtures_changed" || type === "fixture_groups_changed") v.rebuild();
      });
    },
    onModuleConfigChanged(panelEl, mc) { views.forEach((v) => { if (panelEl.contains(v.root)) { v.mc = mc || {}; v.rebuild(); } }); },
  });
  if (typeof PANEL_TITLE_KEYS !== "undefined") PANEL_TITLE_KEYS.simple = "PANEL_SIMPLE";
})();
