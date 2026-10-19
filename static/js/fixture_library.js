/* Scheinwerfer-Bibliothek: Dialog zum Verwalten der installierten GDTF-Dateien und zum Suchen/Installieren aus GDTF Share.
 * Laeuft nach app.js (nutzt dessen globale Helfer Modal, translator, _showToast, _closeAllMenus). Alle Daten kommen von
 * /api/library/*; Texte aus fremden Quellen (Namen, Hersteller) werden nur als textContent gesetzt, nie als HTML. */
(function () {
  "use strict";

  const MODAL = "fixture-library";
  const PAGE = 48;
  const CATS = ["moving_head", "led_bar", "par", "dimmer", "strobe", "effect", "other"];
  const CAT_KEY = {
    moving_head: "FXLIB_CAT_MOVING_HEAD", led_bar: "FXLIB_CAT_LED_BAR", par: "FXLIB_CAT_PAR", dimmer: "FXLIB_CAT_DIMMER",
    strobe: "FXLIB_CAT_STROBE", effect: "FXLIB_CAT_EFFECT", other: "FXLIB_CAT_OTHER",
  };
  // Symbole fuer Eintraege ohne Vorschaubild (feste, eigene Zeichenketten - kein fremder Inhalt)
  const ICONS = {
    moving_head: '<path d="M4 21V11a8 8 0 0 1 16 0v10"/><circle cx="12" cy="12" r="3.6"/><path d="M12 15.6V19"/>',
    led_bar: '<rect x="2.5" y="8.5" width="19" height="7" rx="1.5"/><circle cx="6.5" cy="12" r="1" fill="currentColor"/><circle cx="10.5" cy="12" r="1" fill="currentColor"/><circle cx="14.5" cy="12" r="1" fill="currentColor"/><circle cx="18" cy="12" r="1" fill="currentColor"/>',
    par: '<path d="M8 4h8l3.5 12h-15z"/><path d="M6 20h12"/><path d="M9.5 9h5"/>',
    dimmer: '<circle cx="12" cy="12" r="8"/><path d="M12 12l4-4"/><path d="M12 4v1.5M4 12h1.5M20 12h-1.5"/>',
    strobe: '<path d="M13 2.5L5 14h6l-1 7.5L19 10h-6z"/>',
    effect: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18"/>',
    other: '<rect x="5" y="5" width="14" height="14" rx="2"/><path d="M9 12h6"/>',
  };

  const t = (key, vars) => {
    let s = i18n(key);
    if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
    return s;
  };
  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const S = {
    tab: "installed",
    installed: [],
    show: { items: [], name: "", saved: false },        // Scheinwerfertypen der geladenen Show (Tab 'In dieser Show')
    path: "",
    f: { installed: { q: "", cat: "", mfr: "" }, show: { q: "", cat: "", mfr: "" }, online: { q: "", cat: "", mfr: "", sort: "name", verified: false, verifiedFirst: false, minRating: 0 } },   // Filter je Registerkarte
    updates: {},                       // installierte Datei -> neuere Revision bei GDTF Share (nur wenn die Liste geladen ist)
    pendingUninstall: null,
    pendingTimer: null,
    online: { status: null, items: [], total: 0, manufacturers: [], listTotal: 0, loading: false, seq: 0, error: "", busy: new Set() },
  };

  // ---------------------------------------------------------------------------------------------------- Aufrufe
  function errorText(code, data) {
    if (code === "rate_limited") return t("FXLIB_ERR_RATE", { s: (data && data.retry_after) || 10 });
    const map = {
      auth: "FXLIB_ERR_AUTH", network: "FXLIB_ERR_NETWORK", bad_response: "FXLIB_ERR_BAD", invalid_file: "FXLIB_ERR_INVALID_FILE",
      too_large: "FXLIB_ERR_TOO_LARGE", in_use: "FXLIB_ERR_IN_USE", not_found: "FXLIB_ERR_NOT_FOUND", invalid: "FXLIB_ERR_GENERIC",
    };
    return t(map[code] || "FXLIB_ERR_GENERIC");
  }

  async function api(method, url, body, headers) {
    const options = { method, headers: { ...(headers || {}) } };
    if (body !== undefined) {
      if (body instanceof Blob || body instanceof ArrayBuffer) options.body = body;
      else { options.body = JSON.stringify(body); options.headers["Content-Type"] = "application/json"; }
    }
    let res;
    try { res = await fetch(url, options); } catch { return { ok: false, status: 0, data: { error: "network" } }; }
    let data = {};
    try { data = await res.json(); } catch { /* leere/ungueltige Antwort */ }
    return { ok: res.ok, status: res.status, data };
  }

  // ------------------------------------------------------------------------------- Popover (Konto-Menue, Versionen)
  let popClose = null;
  function closePopover() { if (popClose) { const fn = popClose; popClose = null; fn(); } }

  /** Kleine Auswahlliste unter einem Knopf. rows: {label, sub, badges:[{text, cls}], danger, disabled, id, onClick} oder {separator:true}. */
  function popover(anchor, rows) {
    closePopover();
    const pop = el("div", "fxlib-pop");
    pop.setAttribute("role", "menu");
    rows.forEach((row) => {
      if (row.separator) { pop.appendChild(el("div", "fxlib-pop__sep")); return; }
      const item = el("button", "fxlib-pop__item" + (row.danger ? " fxlib-pop__item--danger" : ""));
      item.type = "button";
      item.setAttribute("role", "menuitem");
      if (row.id) item.id = row.id;
      if (row.disabled) item.disabled = true;
      const main = el("span", "fxlib-pop__main", row.label);
      (row.badges || []).forEach((b) => main.appendChild(tag(b.text, b.cls, b.icon)));
      item.appendChild(main);
      if (row.sub) item.appendChild(el("span", "fxlib-pop__sub", row.sub));
      item.addEventListener("click", () => { closePopover(); if (row.onClick) row.onClick(); });
      pop.appendChild(item);
    });
    document.body.appendChild(pop);
    const r = anchor.getBoundingClientRect();
    const box = pop.getBoundingClientRect();
    let left = Math.min(Math.max(4, r.left), window.innerWidth - box.width - 4);
    let top = r.bottom + 4;
    if (top + box.height > window.innerHeight - 4) top = Math.max(4, r.top - box.height - 4);
    pop.style.left = left + "px";
    pop.style.top = top + "px";
    anchor.setAttribute("aria-expanded", "true");
    const outside = (e) => { if (!pop.contains(e.target) && !anchor.contains(e.target)) closePopover(); };
    const onKey = (e) => { if (e.key === "Escape") { e.preventDefault(); e.stopImmediatePropagation(); closePopover(); } };
    document.addEventListener("pointerdown", outside, true);
    document.addEventListener("keydown", onKey, true);
    window.addEventListener("resize", closePopover);
    pop.addEventListener("wheel", (e) => e.stopPropagation(), { passive: true });
    popClose = () => {
      document.removeEventListener("pointerdown", outside, true);
      document.removeEventListener("keydown", onKey, true);
      window.removeEventListener("resize", closePopover);
      anchor.setAttribute("aria-expanded", "false");
      pop.remove();
    };
    const first = pop.querySelector("button:not(:disabled)");
    if (first) first.focus({ preventScroll: true });
  }

  /** 'Nach oben'-Knopf: erscheint, sobald der Bereich ein Stueck gescrollt ist. getScroller liefert den gerade sichtbaren Scroll-Bereich. */
  function wireTop(button, scrollers, getScroller) {
    const update = () => { const s = getScroller(); button.hidden = !s || s.scrollTop < 300; };
    scrollers.forEach((s) => s.addEventListener("scroll", update, { passive: true }));
    button.addEventListener("click", () => { const s = getScroller(); if (s) s.scrollTo({ top: 0, behavior: "smooth" }); });
    return update;
  }
  let updateTop = () => {};
  let updateDetTop = () => {};

  // ------------------------------------------------------------------------------------------------------ Karten
  function thumb(category, url) {
    const box = el("div", "fxlib-card__thumb");
    const icon = () => {
      box.textContent = "";
      const ns = "http://www.w3.org/2000/svg";
      const svg = document.createElementNS(ns, "svg");
      svg.setAttribute("viewBox", "0 0 24 24");
      svg.setAttribute("class", "fxlib-card__icon");
      svg.setAttribute("aria-hidden", "true");
      svg.innerHTML = ICONS[category] || ICONS.other;     // feste Zeichenketten aus ICONS
      box.appendChild(svg);
    };
    if (url) {
      const img = new Image();
      img.alt = "";
      img.loading = "lazy";
      img.draggable = false;
      img.addEventListener("error", icon);
      img.src = url;
      box.appendChild(img);
    } else {
      icon();
    }
    return box;
  }

  /** Schild (kleine Pille); icon = optionaler Name aus Icons (immer SVG, nie Unicode-Symbole). */
  function tag(text, cls, icon) {
    const node = el("span", "fxlib-tag" + (cls ? " fxlib-tag--" + cls : ""));
    if (icon) node.appendChild(Icons.svg(icon, icon === "star" ? "ico--star" : ""));
    node.appendChild(document.createTextNode(text));
    return node;
  }

  function card(opts) {
    const node = el("div", "fxlib-card");
    node.dataset.id = opts.id;
    node.appendChild(thumb(opts.category, opts.thumb));
    const info = el("div", "fxlib-card__info");
    info.appendChild(el("div", "fxlib-card__name", opts.name));
    info.appendChild(el("div", "fxlib-card__mfr", opts.manufacturer || "—"));
    const tags = el("div", "fxlib-card__tags");
    opts.tags.forEach((x) => tags.appendChild(x));
    info.appendChild(tags);
    node.appendChild(info);
    const actions = el("div", "fxlib-card__actions");
    opts.actions.forEach((x) => actions.appendChild(x));
    node.appendChild(actions);
    return node;
  }

  function button(label, cls, onClick, disabled, title, icon) {
    const b = el("button", "modal__button " + (cls || ""));
    if (icon) { b.classList.add("modal__button--icon"); b.appendChild(Icons.svg(icon)); }
    if (label) b.appendChild(el("span", "", label));
    b.type = "button";
    if (disabled) b.disabled = true;
    if (title) b.title = title;
    b.addEventListener("click", onClick);
    return b;
  }

  // ---------------------------------------------------------------------------------------------- installiert
  const F = () => S.f[S.tab];
  const tokens = () => F().q.trim().toLowerCase().split(/\s+/).filter(Boolean);

  function filteredInstalled() {
    const words = tokens();
    return S.installed.filter((f) => {
      if (F().cat && f.category !== F().cat) return false;
      if (F().mfr && f.manufacturer !== F().mfr) return false;
      const hay = `${f.name} ${f.manufacturer} ${f.revision}`.toLowerCase();
      return words.every((w) => hay.includes(w));
    });
  }

  function filteredShow() {
    const words = tokens();
    return S.show.items.filter((f) => {
      if (F().cat && f.category !== F().cat) return false;
      if (F().mfr && f.manufacturer !== F().mfr) return false;
      return words.every((w) => `${f.name} ${f.manufacturer} ${f.revision}`.toLowerCase().includes(w));
    });
  }

  function clearPending() {
    S.pendingUninstall = null;
    if (S.pendingTimer) { clearTimeout(S.pendingTimer); S.pendingTimer = null; }
  }

  function installedCard(f) {
    const maxCh = f.modes.reduce((m, x) => Math.max(m, x.channel_count || 0), 0);
    const tags = [tag(t(CAT_KEY[f.category] || CAT_KEY.other), "cat")];
    tags.push(tag(t("FXLIB_MODES", { n: f.modes.length })));
    if (maxCh) tags.push(tag(t("FXLIB_CHANNELS", { n: maxCh })));
    if (f.revision) tags.push(tag(t("FXLIB_REV", { rev: f.revision.replace(/_/g, " ") })));
    if (f.in_use) tags.push(tag(t("FXLIB_IN_USE", { n: f.in_use }), "use"));
    if (f.error) tags.push(tag(t("FXLIB_BROKEN"), "bad"));
    const upd = S.updates[f.id];
    if (upd) tags.push(tag(t("FXLIB_UPDATE_AVAILABLE", { rev: String(upd.revision).replace(/_/g, " ") }), "use"));
    const actions = [button(t("FXLIB_DETAILS"), "", () => openDetails(f.id))];
    if (f.in_use && !upd) actions.push(button(t("FXLIB_USED_NOTE"), "", () => setTab("show")));      // springt zum Tab 'In dieser Show'
    if (upd) {
      const busy = S.online.busy.has(String(upd.rid));
      actions.push(button(busy ? t("FXLIB_INSTALLING") : t("FXLIB_UPDATE"), "modal__button--primary", () => installOnline({ rid: upd.rid, name: f.name, revision: upd.revision }, { replace: f.id }), busy));
    }
    if (S.pendingUninstall === f.id) {
      actions.push(button(t("FXLIB_UNINSTALL_CONFIRM"), "modal__button--danger", () => doUninstall(f.id)));
      actions.push(button(t("CANCEL"), "", () => { clearPending(); renderInstalled(); }));
    } else {
      actions.push(button(t("FXLIB_UNINSTALL"), "", () => {
        clearPending();
        S.pendingUninstall = f.id;
        S.pendingTimer = setTimeout(() => { clearPending(); renderInstalled(); }, 6000);
        renderInstalled();
      }, false, f.in_use ? t("FXLIB_UNINSTALL_IN_USE_TIP") : ""));
    }
    const node = card({
      id: f.id, name: f.name, manufacturer: f.manufacturer, category: f.category, tags, actions,
      thumb: f.has_thumbnail ? `/api/library/installed/${encodeURIComponent(f.id)}/thumbnail?v=${f.installed_at}` : "",
    });
    // Tippen auf Bild oder Text oeffnet die Details (die Knoepfe rechts unten behalten ihre eigene Aktion)
    [node.querySelector(".fxlib-card__thumb"), node.querySelector(".fxlib-card__info")].forEach((part) => {
      part.classList.add("fxlib-card__open");
      part.setAttribute("role", "button");
      part.tabIndex = 0;
      part.addEventListener("click", () => openDetails(f.id));
      part.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openDetails(f.id); } });
    });
    return node;
  }

  // ------------------------------------------------------------------------------------------------ In dieser Show
  /** Karte eines Scheinwerfertyps der Show: nur ansehen (Details); Typen kommen und gehen ueber das Scheinwerferlisten-Panel. */
  function showCard(f) {
    const tags = [];
    if (f.category) tags.push(tag(t(CAT_KEY[f.category] || CAT_KEY.other), "cat"));
    tags.push(tag(t("FXLIB_SHOW_COUNT", { n: f.count }), "use"));
    if (f.revision) tags.push(tag(t("FXLIB_REV", { rev: f.revision.replace(/_/g, " ") })));
    const sourceKey = { show: "FXLIB_SHOW_SRC_SHOW", library: "FXLIB_SHOW_SRC_LIBRARY", builtin: "FXLIB_SHOW_SRC_BUILTIN", missing: "FXLIB_SHOW_SRC_MISSING" }[f.source];
    tags.push(tag(t(sourceKey), f.source === "show" ? "cat" : f.source === "missing" ? "bad" : "use", f.source === "show" ? "check" : ""));
    if (f.library === "different") tags.push(tag(t("FXLIB_SHOW_LIB_DIFFERENT"), "use"));
    if (f.library === "removed" && f.source === "show") tags.push(tag(t("FXLIB_SHOW_LIB_REMOVED"), "use"));
    if (f.others && f.others.length && f.library !== "different") tags.push(tag(t("FXLIB_SHOW_LIB_OTHER", { rev: f.others.join(", ").replace(/_/g, " ") }), "use"));
    const canOpen = f.source === "show" || f.source === "library";
    const actions = canOpen ? [button(t("FXLIB_DETAILS"), "", () => openDetails(f.id, "show"))] : [];
    const node = card({
      id: f.id, name: f.name, manufacturer: f.manufacturer, category: f.category, tags, actions,
      thumb: f.has_thumbnail ? `/api/library/installed/${encodeURIComponent(f.id)}/thumbnail?scope=show&v=${f.size}` : "",
    });
    if (canOpen) {
      [node.querySelector(".fxlib-card__thumb"), node.querySelector(".fxlib-card__info")].forEach((part) => {
        part.classList.add("fxlib-card__open");
        part.setAttribute("role", "button");
        part.tabIndex = 0;
        part.addEventListener("click", () => openDetails(f.id, "show"));
        part.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openDetails(f.id, "show"); } });
      });
    }
    return node;
  }

  function renderShow() {
    const grid = $("fxlib-show-grid");
    if (!grid) return;
    grid.textContent = "";
    $("fxlib-tab-show").textContent = t("FXLIB_TAB_SHOW", { n: S.show.items.length });
    $("fxlib-show-hint").textContent = S.show.items.length ? t("FXLIB_SHOW_HINT", { name: S.show.name || "" }) : "";
    const rows = filteredShow();
    if (!rows.length) {
      const box = el("div", "fxlib__empty");
      box.appendChild(el("p", "", t(S.show.items.length ? "FXLIB_EMPTY_FILTER" : "FXLIB_SHOW_EMPTY")));
      if (S.show.items.length && filtersActive()) box.appendChild(button(t("FXLIB_RESET_FILTERS"), "", resetFilters));
      grid.appendChild(box);
      return;
    }
    rows.forEach((f) => grid.appendChild(showCard(f)));
  }

  async function loadShow() {
    const res = await api("GET", "/api/library/show");
    if (!res.ok) return;
    S.show = { items: res.data.items || [], name: res.data.show_name || "", saved: !!res.data.saved };
    if (S.tab === "show") buildManufacturers(S.show.items.map((f) => f.manufacturer));
    renderShow();
  }

  // ------------------------------------------------------------------------------------------------ Details
  const DET = { scope: "library", data: null, mode: 0, open: new Set(), tab: "overview", viewer: null, model: null, modelId: "", pan: 0, tilt: 0, beam: true, grid: true };
  const TABS = [["overview", "info", "FXDET_TAB_OVERVIEW"], ["model", "cube", "FXDET_TAB_MODEL"], ["channels", "fader", "FXDET_TAB_CHANNELS"], ["wheels", "wheel", "FXDET_TAB_WHEELS"]];
  const WHEEL_KEY = { gobo: "FXDET_WHEEL_GOBO", color: "FXDET_WHEEL_COLOR", prism: "FXDET_WHEEL_PRISM" };

  const fmtRange = (from, to) => (from === null || to === null || from === undefined || to === undefined) ? "\u2014" : (from === to ? String(from) : `${from}\u2013${to}`);
  const fmtPhys = (a, b) => (a === null || b === null || a === undefined || b === undefined || (a === 0 && b === 0)) ? "" : (a === b ? String(a) : `${a} \u2026 ${b}`);

  function fact(label, value, wide) {
    if (value === "" || value === null || value === undefined) return null;
    const box = el("div", "fxdet__fact" + (wide ? " fxdet__fact--wide" : ""));
    box.appendChild(el("dt", "", label));
    box.appendChild(el("dd", "", String(value)));
    return box;
  }

  function renderTabs() {
    const bar = $("fxdet-tabs");
    bar.textContent = "";
    TABS.forEach(([name, icon, key]) => {
      const b = el("button", "fxdet__tab");
      b.type = "button";
      b.dataset.tab = name;
      b.setAttribute("role", "tab");
      b.setAttribute("aria-selected", DET.tab === name ? "true" : "false");
      b.appendChild(Icons.svg(icon));
      b.appendChild(el("span", "", t(key)));
      b.addEventListener("click", () => setDetTab(name));
      bar.appendChild(b);
    });
  }

  function destroyViewer() {
    if (DET.viewer) { DET.viewer.destroy(); DET.viewer = null; }
  }

  function setDetTab(name) {
    DET.tab = name;
    document.querySelectorAll("#fxdet-scroll .fxdet__pane").forEach((pane) => { pane.hidden = pane.dataset.pane !== name; });
    document.querySelectorAll("#fxdet-tabs .fxdet__tab").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === name ? "true" : "false"));
    const scroller = $("fxdet-scroll");
    if (scroller) scroller.scrollTop = 0;
    if (name === "model") showModel(); else destroyViewer();
    updateDetTop();
  }

  const infoRow = (label, value) => (value === "" || value === null || value === undefined || value === 0 ? null : [label, String(value)]);

  function infoCard(title, rows, extra) {
    const box = el("section", "fxdet__card");
    box.appendChild(el("h4", "", title));
    const list = el("dl", "fxdet__kv");
    rows.filter(Boolean).forEach(([k, v]) => { list.appendChild(el("dt", "", k)); list.appendChild(el("dd", "", v)); });
    if (list.children.length) box.appendChild(list);
    if (extra) box.appendChild(extra);
    return box;
  }

  function renderOverview() {
    const d = DET.data;
    $("fxdet-title").textContent = d.manufacturer ? `${d.name} \u2013 ${d.manufacturer}` : d.name;
    const thumbBox = $("fxdet-thumb");
    thumbBox.textContent = "";
    thumbBox.appendChild(thumb(d.category, d.has_thumbnail ? `/api/library/installed/${encodeURIComponent(d.id)}/thumbnail${scopeQuery(true)}` : ""));
    const facts = $("fxdet-facts");
    facts.textContent = "";
    const rev = d.revisions.length ? d.revisions[d.revisions.length - 1] : null;
    const p = d.physical || {};
    const kb = d.size >= 1048576 ? `${(d.size / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(d.size / 1024))} KB`;
    [
      fact(t("FXDET_MFR"), d.manufacturer), fact(t("FXDET_NAME"), d.name), fact(t("FXDET_LONG"), d.long_name !== d.name ? d.long_name : ""),
      fact(t("FXDET_SHORT"), d.short_name), fact(t("FXDET_TYPE"), t(CAT_KEY[d.category] || CAT_KEY.other)),
      fact(t("FXDET_VERSION"), d.data_version ? `GDTF ${d.data_version}` : ""),
      fact(t("FXDET_REVISION"), rev ? [rev.text, rev.date.slice(0, 10)].filter(Boolean).join(" \u00B7 ") : ""),
      fact(t("FXDET_WEIGHT"), p.weight ? `${p.weight} kg` : ""),
      fact(t("FXDET_TEMP"), (p.temp_low !== null && p.temp_low !== undefined && p.temp_high) ? `${p.temp_low} \u2026 ${p.temp_high} \u00B0C` : ""),
      fact(t("FXDET_MODES"), d.modes.length), fact(t("FXDET_SIZE"), kb), fact(t("FXDET_DESC"), d.description, true),
    ].filter(Boolean).forEach((node) => facts.appendChild(node));

    // Karten: Optik/Strahl, Anschluesse, Emitter, Modelle
    const cards = $("fxdet-cards");
    cards.textContent = "";
    const s = d.structure || {};
    (s.beams || []).forEach((b, i) => {
      cards.appendChild(infoCard((s.beams.length > 1 ? `${t("FXDET_OPTICS")} ${i + 1}` : t("FXDET_OPTICS")) + (b.name ? ` (${b.name})` : ""), [
        infoRow(t("FXDET_BEAM_KIND"), b.type), infoRow(t("FXDET_LAMP"), b.lamp), infoRow(t("FXDET_POWER"), b.power ? `${b.power} W` : ""),
        infoRow(t("FXDET_FLUX"), b.flux ? `${b.flux} lm` : ""), infoRow(t("FXDET_CCT"), b.temperature ? `${b.temperature} K` : ""),
        infoRow(t("FXDET_BEAM_ANGLE"), b.angle ? `${b.angle}\u00B0` : ""), infoRow(t("FXDET_FIELD_ANGLE"), b.field ? `${b.field}\u00B0` : ""),
        infoRow(t("FXDET_THROW"), b.throw_ratio ? b.throw_ratio : ""),
      ]));
    });
    if ((s.connectors || []).length) cards.appendChild(infoCard(t("FXDET_CONNECTORS"), s.connectors.map((c) => infoRow(c.name || "\u2014", c.type || ""))));
    if ((s.emitters || []).length) {
      const row = el("div", "fxdet__emitters");
      s.emitters.forEach((e) => {
        const chip = el("span", "fxdet__emitter");
        const dot = el("span", "fxdet__dot");
        if (e.color) dot.style.background = `rgb(${e.color.join(",")})`;
        chip.append(dot, el("span", "", e.wavelength ? `${e.name} \u00B7 ${Math.round(e.wavelength)} nm` : e.name));
        row.appendChild(chip);
      });
      cards.appendChild(infoCard(t("FXDET_EMITTERS"), [], row));
    }
    const m = s.models || {};
    cards.appendChild(infoCard(t("FXDET_MODELS"), [
      infoRow(t("FXDET_MODELS_FILES"), m.files), infoRow(t("FXDET_MODELS_PRIMS"), m.primitives), infoRow(t("FXDET_GEOMETRIES"), d.geometries),
      infoRow(t("FXDET_MODELS_READER"), m.reader === false ? t("FXDET_MODELS_NO_READER") : ""),
    ]));
  }

  function renderWheels() {
    const box = $("fxdet-wheels");
    box.textContent = "";
    const d = DET.data;
    const wheels = (d.structure && d.structure.wheels) || [];
    if (!wheels.length) { box.appendChild(el("p", "fxdet__empty", t("FXDET_NO_WHEELS"))); return; }
    wheels.forEach((wheel) => {
      const section = el("section", "fxdet__wheel");
      const head = el("h4", "fxdet__wheel-head");
      head.appendChild(el("span", "", wheel.name || t("FXDET_WHEELS")));
      head.appendChild(el("span", "fxdet__badge", t(WHEEL_KEY[wheel.kind] || WHEEL_KEY.color)));
      head.appendChild(el("span", "fxdet__muted", t("FXDET_WHEEL_SLOTS", { n: wheel.slots.length })));
      section.appendChild(head);
      const grid = el("div", "fxdet__slots");
      wheel.slots.forEach((slot, index) => {
        const tile = el("div", "fxdet__slot");
        const face = el("div", "fxdet__slot-face");
        if (slot.image) {
          const img = document.createElement("img");
          img.alt = slot.name || "";
          img.loading = "lazy";
          img.decoding = "async";
          img.src = `/api/library/installed/${encodeURIComponent(d.id)}/asset?path=${encodeURIComponent(slot.image)}${scopeQuery(false)}`;
          face.classList.add("fxdet__slot-face--gobo");
          face.appendChild(img);
        } else if (slot.facets) {
          face.classList.add("fxdet__slot-face--prism");
          face.appendChild(Icons.svg("wheel"));
        } else if (slot.color) {
          face.style.background = `rgb(${slot.color.join(",")})`;
        } else {
          face.classList.add("fxdet__slot-face--open");
        }
        tile.appendChild(face);
        tile.appendChild(el("div", "fxdet__slot-name", slot.name || `#${index + 1}`));
        if (slot.facets) tile.appendChild(el("div", "fxdet__muted", t("FXDET_FACETS", { n: slot.facets })));
        grid.appendChild(tile);
      });
      section.appendChild(grid);
      box.appendChild(section);
    });
  }

  // ---- 3D-Vorschau
  const modelStatus = (text) => { const node = $("fxdet-model-status"); node.textContent = text; node.hidden = !text; };

  function renderModelControls() {
    const bar = $("fxdet-viewctl");
    bar.textContent = "";
    const viewer = DET.viewer;
    if (!viewer) return;
    const views = el("div", "fxdet__btns");
    [["iso", "FXDET3D_VIEW_ISO"], ["front", "FXDET3D_VIEW_FRONT"], ["side", "FXDET3D_VIEW_SIDE"], ["top", "FXDET3D_VIEW_TOP"]].forEach(([name, key]) => {
      const b = el("button", "modal__button", t(key));
      b.type = "button";
      b.dataset.view = name;
      b.addEventListener("click", () => { if (name === "iso") viewer.resetView(); else viewer.view(name); });
      views.appendChild(b);
    });
    bar.appendChild(views);
    const toggles = el("div", "fxdet__btns");
    [["beam", "FXDET3D_BEAM"], ["grid", "FXDET3D_GRID"]].forEach(([name, key]) => {
      const label = el("label", "fxdet__check");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = DET[name];
      input.dataset.toggle = name;
      input.addEventListener("change", () => { DET[name] = input.checked; if (name === "beam") viewer.setBeam(input.checked); else viewer.setGrid(input.checked); });
      label.append(input, el("span", "", t(key)));
      toggles.appendChild(label);
    });
    bar.appendChild(toggles);
    const axes = viewer.axes || {};
    [["pan", "FXDET3D_PAN"], ["tilt", "FXDET3D_TILT"]].forEach(([name, key]) => {
      if (!axes[name]) return;
      const row = el("label", "fxdet__slider");
      row.appendChild(el("span", "fxdet__slider-label", t(key)));
      const input = document.createElement("input");
      input.type = "range";
      input.dataset.axis = name;
      input.min = String(Math.round(Math.min(axes[name].min, axes[name].max)));
      input.max = String(Math.round(Math.max(axes[name].min, axes[name].max)));
      input.step = "1";
      input.value = String(Math.min(Math.max(DET[name], Number(input.min)), Number(input.max)));
      const value = el("span", "fxdet__slider-value", `${input.value}\u00B0`);
      input.addEventListener("input", () => {
        DET[name] = Number(input.value);
        value.textContent = `${input.value}\u00B0`;
        viewer.setAngles(DET.pan, DET.tilt);
      });
      row.append(input, value);
      bar.appendChild(row);
    });
  }

  async function showModel() {
    const host = $("fxdet-viewer");
    const id = DET.data.id;
    destroyViewer();
    $("fxdet-viewctl").textContent = "";
    $("fxdet-model-info").textContent = "";
    if (DET.modelId !== id || !DET.model) {
      modelStatus(t("FXDET3D_LOADING"));
      const res = await api("GET", `/api/library/installed/${encodeURIComponent(id)}/model${scopeQuery(true)}`);
      if (DET.tab !== "model" || !DET.data || DET.data.id !== id) return;       // inzwischen woanders
      if (!res.ok) { modelStatus(t("FXDET3D_ERR")); return; }
      DET.model = res.data;
      DET.modelId = id;
      DET.pan = DET.tilt = 0;
    }
    const model = DET.model;
    if (!model.available) { modelStatus(t(model.reader === false ? "FXDET3D_NO_READER" : "FXDET3D_NONE")); return; }
    let viewer = null;
    try { viewer = window.OCModelViewer ? window.OCModelViewer.create(host, model, { beam: DET.beam, grid: DET.grid }) : null; } catch (err) { console.error(err); }
    if (!viewer) { modelStatus(t("FXDET3D_NO_WEBGL")); return; }
    modelStatus("");
    DET.viewer = viewer;
    viewer.setAngles(DET.pan, DET.tilt);
    renderModelControls();
    const st = model.stats || {};
    $("fxdet-model-info").textContent = [
      t(model.source === "files" ? "FXDET3D_FROM_FILES" : model.source === "primitives" ? "FXDET3D_FROM_PRIMS" : "FXDET3D_FROM_MIXED"),
      t("FXDET3D_STATS", { n: st.triangles || 0 }), t("FXDET3D_HINT"),
      ...(model.notes && model.notes.length ? [t("FXDET3D_NOTES", { n: model.notes.length })] : []),
    ].join(" \u00B7 ");
  }

  function renderDetails() {
    const d = DET.data;
    if (!d) return;
    renderTabs();
    renderOverview();
    renderWheels();
    // Modus-Auswahl
    const select = $("fxdet-mode");
    select.textContent = "";
    d.modes.forEach((m, i) => { const o = el("option", "", `${m.name} (${m.channel_count})`); o.value = String(i); select.appendChild(o); });
    select.value = String(DET.mode);
    renderModeChannels();
    if (DET.viewer) renderModelControls();
  }

  function renderModeChannels() {
    const d = DET.data;
    const mode = d.modes[DET.mode];
    const body = $("fxdet-channels");
    body.textContent = "";
    $("fxdet-modeinfo").textContent = mode ? [t("FXDET_CH_COUNT", { n: mode.channel_count }), mode.description].filter(Boolean).join(" \u00B7 ") : "";
    $("fxdet-error").hidden = !d.truncated;
    $("fxdet-error").textContent = d.truncated ? t("FXDET_TRUNC") : "";
    if (!mode || !mode.channels.length) {
      const tr = el("tr");
      const td = el("td", "fxdet__empty", t("FXDET_NO_CHANNELS"));
      td.colSpan = 5;
      tr.appendChild(td);
      body.appendChild(tr);
      return;
    }
    mode.channels.forEach((ch, index) => {
      const key = `${DET.mode}:${index}`;
      const open = DET.open.has(key);
      const row = el("tr", "fxdet__row" + (open ? " fxdet__row--open" : ""));
      row.tabIndex = 0;
      row.setAttribute("role", "button");
      row.setAttribute("aria-expanded", open ? "true" : "false");
      const dmx = el("td", "", ch.offset.join(" + "));
      if (ch.bytes > 1) dmx.appendChild(el("span", "fxdet__bit", t("FXDET_BIT", { n: ch.bytes * 8 })));
      const attr = el("td");
      attr.appendChild(el("div", "", ch.pretty && ch.pretty !== ch.attribute ? `${ch.attribute} (${ch.pretty})` : ch.attribute));
      attr.appendChild(el("div", "fxdet__muted", [ch.feature, ch.geometry].filter(Boolean).join(" \u00B7 ")));
      const max = Math.pow(256, ch.bytes) - 1;
      const def = el("td", "", ch.default === null || ch.default === undefined ? "\u2014" : `${ch.default} / ${max}`);
      const funcs = el("td", "", String(ch.functions.length));
      const chevron = el("td");
      chevron.appendChild(Icons.svg(open ? "chevron-up" : "chevron-down"));
      row.append(dmx, attr, def, funcs, chevron);
      const toggle = () => { if (DET.open.has(key)) DET.open.delete(key); else DET.open.add(key); renderModeChannels(); };
      row.addEventListener("click", toggle);
      row.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
      body.appendChild(row);
      if (open) body.appendChild(detailSubRow(ch, max));
    });
  }

  function detailSubRow(ch, max) {
    const tr = el("tr", "fxdet__sub");
    const td = el("td");
    td.colSpan = 5;
    const inner = el("div", "fxdet__sub-inner");
    const table = el("table", "fxdet__fn");
    const head = el("tr");
    [t("FXDET_FUNC_NAME"), t("FXDET_FUNC_RANGE", { max }), t("FXDET_FUNC_PHYS"), t("FXDET_COL_DEFAULT")].forEach((h) => head.appendChild(el("th", "", h)));
    const thead = el("thead");
    thead.appendChild(head);
    table.appendChild(thead);
    const tbody = el("tbody");
    ch.functions.forEach((fn) => {
      const tr2 = el("tr");
      tr2.appendChild(el("td", "", fn.name || fn.attribute));
      tr2.appendChild(el("td", "", fmtRange(fn.from, fn.to)));
      tr2.appendChild(el("td", "", fmtPhys(fn.physical_from, fn.physical_to)));
      tr2.appendChild(el("td", "", fn.default === null || fn.default === undefined ? "" : String(fn.default)));
      tbody.appendChild(tr2);
      if (fn.sets && fn.sets.length > 1 || (fn.sets && fn.sets.length === 1 && fn.sets[0].name)) {
        const trs = el("tr");
        const tds = el("td");
        tds.colSpan = 4;
        const ul = el("ul", "fxdet__sets");
        fn.sets.forEach((cs) => ul.appendChild(el("li", "", `${fmtRange(cs.from, cs.to)}  ${cs.name || "\u2014"}`)));
        if (fn.sets_truncated) ul.appendChild(el("li", "", "\u2026"));
        tds.appendChild(ul);
        trs.appendChild(tds);
        tbody.appendChild(trs);
      }
    });
    table.appendChild(tbody);
    inner.appendChild(table);
    if (ch.functions_truncated) inner.appendChild(el("div", "fxdet__muted", t("FXDET_TRUNC")));
    td.appendChild(inner);
    tr.appendChild(td);
    return tr;
  }

  const scopeQuery = (first) => (DET.scope === "show" ? `${first ? "?" : "&"}scope=show` : "");

  async function openDetails(id, scope) {
    DET.scope = scope === "show" ? "show" : "library";
    const res = await api("GET", `/api/library/installed/${encodeURIComponent(id)}/details${scopeQuery(true)}`);
    if (!res.ok) { _showToast(t("FXDET_ERR"), "warn", 4000, true); return; }
    destroyViewer();
    DET.data = res.data;
    DET.mode = 0;
    DET.open = new Set();
    DET.tab = "overview";
    DET.model = null;
    DET.modelId = "";
    Modal._hooks["fixture-library-detail"] = destroyViewer;               // beim Schliessen die Grafikkarte freigeben
    Modal.open("fixture-library-detail");
    renderDetails();
    setDetTab("overview");
  }

  function renderInstalled() {
    const grid = $("fxlib-installed-grid");
    if (!grid) return;
    grid.textContent = "";
    const rows = filteredInstalled();
    $("fxlib-installed-path").textContent = S.path ? t("FXLIB_INSTALLED_PATH", { path: S.path }) : "";
    $("fxlib-tab-installed").textContent = t("FXLIB_TAB_INSTALLED", { n: S.installed.length });
    $("fxlib-tab-show").textContent = t("FXLIB_TAB_SHOW", { n: S.show.items.length });
    if (!rows.length) {
      grid.appendChild(emptyState(false));
      return;
    }
    rows.forEach((f) => grid.appendChild(installedCard(f)));
  }

  async function loadInstalled() {
    const res = await api("GET", "/api/library/installed");
    if (!res.ok) return;
    S.installed = res.data.items || [];
    S.updates = res.data.updates || {};
    S.path = res.data.path || "";
    if (S.pendingUninstall && !S.installed.some((f) => f.id === S.pendingUninstall)) clearPending();
    if (S.tab === "installed") buildManufacturers(S.installed.map((f) => f.manufacturer));
    renderInstalled();
  }

  async function doUninstall(id) {
    clearPending();
    const res = await api("DELETE", `/api/library/installed/${encodeURIComponent(id)}`);
    if (res.ok) {
      _showToast("FXLIB_UNINSTALLED", "ok", 2500);
      if (res.data.used) _showToast("FXLIB_SHOW_KEEPS_COPY", "info", 6000);       // benutzt: die Show behaelt ihre eigene Kopie
    } else _showToast(errorText(res.data.error), "warn", 4500, true);
    await loadInstalled();
    loadShow();
  }

  // ------------------------------------------------------------------------------------------------ Filterleiste
  function buildManufacturers(names) {
    const select = $("fxlib-mfr");
    const unique = [...new Set(names.filter(Boolean))].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
    if (F().mfr && !unique.includes(F().mfr)) F().mfr = "";
    select.textContent = "";
    const all = el("option", "", t("FXLIB_MFR_ALL"));
    all.value = "";
    select.appendChild(all);
    unique.forEach((name) => { const o = el("option", "", name); o.value = name; select.appendChild(o); });
    select.value = F().mfr;
  }

  function buildCategories() {
    const row = $("fxlib-cats");
    row.textContent = "";
    [["", t("FXLIB_CAT_ALL")], ...CATS.map((c) => [c, t(CAT_KEY[c])])].forEach(([value, label]) => {
      const b = el("button", "fxlib-chip" + (F().cat === value ? " fxlib-chip--on" : ""), label);
      b.type = "button";
      b.dataset.cat = value;
      b.setAttribute("aria-pressed", F().cat === value ? "true" : "false");
      row.appendChild(b);
    });
  }

  let searchTimer = null;
  function filtersChanged(immediate) {
    if (S.tab === "installed") { clearPending(); renderInstalled(); return; }
    if (S.tab === "show") { renderShow(); return; }
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(() => searchOnline(false), immediate ? 0 : 300);
  }

  // ----------------------------------------------------------------------------------------------------- online
  function showOnlineView() {
    const logged = !!(S.online.status && S.online.status.logged_in);
    $("fxlib-login").hidden = logged;
    $("fxlib-online-body").hidden = !logged;
    $("fxlib-session").hidden = !logged;
    if (logged) $("fxlib-session-user").textContent = S.online.status.user;
    $("fxlib-account").title = logged ? t("FXLIB_LOGGED_AS", { user: S.online.status.user }) : "";
    $("fxlib-verified").hidden = !(logged && S.online.hasVerified);
    $("fxlib-verified").classList.toggle("fxlib-chip--on", !!F().verified);
    $("fxlib-verified").setAttribute("aria-pressed", F().verified ? "true" : "false");
    const first = $("fxlib-verified-first");                                  // 'Verifizierte zuerst' ist ueberfluessig, wenn nur verifizierte gezeigt werden
    first.hidden = !(logged && S.online.hasVerified) || !!F().verified;
    first.classList.toggle("fxlib-chip--on", !!F().verifiedFirst);
    first.setAttribute("aria-pressed", F().verifiedFirst ? "true" : "false");
    const ratingBox = $("fxlib-rating-box");
    ratingBox.hidden = !(logged && S.online.hasRating);
    const select = $("fxlib-rating");
    if (!select.options.length || select.dataset.lang !== translator.language) {
      select.textContent = "";
      [0, 1, 2, 3, 4].forEach((n) => { const o = el("option", "", n === 0 ? t("FXLIB_RATING_ALL") : n === 1 ? t("FXLIB_RATING_ONE") : t("FXLIB_RATING_MIN", { n })); o.value = String(n); select.appendChild(o); });
      select.dataset.lang = translator.language;
    }
    select.value = String(F().minRating || 0);
    const st = S.online.status || {};
    $("fxlib-remember-row").hidden = !st.remember_available;
    if (!logged && st.remembered_user && !$("fxlib-user").value) $("fxlib-user").value = st.remembered_user;
    if (!logged) $("fxlib-remember").checked = !!st.remembered;
    $("fxlib-filters").hidden = !logged && S.tab === "online";
  }

  async function loadOnlineStatus() {
    const res = await api("GET", "/api/library/online/status");
    S.online.status = res.ok ? res.data : { logged_in: false };
    if (!S.online.status.logged_in && S.online.status.remembered) {
      // "Angemeldet bleiben": mit den gespeicherten Zugangsdaten still wieder anmelden
      const back = await api("POST", "/api/library/online/resume");
      if (back.ok) S.online.status = back.data;
      else {
        const again = await api("GET", "/api/library/online/status");
        S.online.status = again.ok ? again.data : { logged_in: false };
        const msg = $("fxlib-login-error");
        msg.textContent = errorText(back.data.error);
        msg.hidden = false;
      }
    }
    showOnlineView();
    if (S.online.status.logged_in) searchOnline(false);
  }

  const day = (text) => String(text || "").slice(0, 10);

  function verifiedTag(flag) {
    if (flag === true) return tag(t("FXLIB_VERIFIED"), "ok", "check");
    if (flag === false && S.online.hasVerified) return tag(t("FXLIB_UNVERIFIED"));
    return null;
  }

  function onlineCard(item) {
    const versions = item.versions || [];
    const tags = [tag(t(CAT_KEY[item.category] || CAT_KEY.other), "cat")];
    if (item.revision) tags.push(tag(t("FXLIB_REV", { rev: String(item.revision).replace(/_/g, " ") })));
    const vt = verifiedTag(item.verified);
    if (vt) tags.push(vt);
    if (item.creator) tags.push(tag(t("FXLIB_BY", { name: item.creator })));
    if (item.modified || item.created) tags.push(tag(day(item.modified || item.created)));
    if (item.rating) tags.push(tag(String(Math.round(item.rating * 10) / 10), "", "star"));
    if (versions.length > 1) tags.push(tag(t("FXLIB_VERSION_COUNT", { n: versions.length })));
    const installedVersion = item.installed_version;
    if (item.installed) tags.push(tag(t("FXLIB_INSTALLED_TAG"), "ok"));
    else if (installedVersion) tags.push(tag(t("FXLIB_INSTALLED_REV", { rev: String(installedVersion.revision).replace(/_/g, " ") }), "use"));
    else if (item.same_fixture_installed) tags.push(tag(t("FXLIB_OTHER_REV"), "use"));
    const busy = versions.some((v) => S.online.busy.has(String(v.rid))) || S.online.busy.has(String(item.rid));
    const group = el("div", "fxlib-split");
    if (item.installed) {
      const done = button(t("FXLIB_INSTALLED_TAG"), "", () => {}, true, "", "check");
      group.appendChild(done);
    } else if (item.update_available && installedVersion) {
      group.appendChild(button(busy ? t("FXLIB_INSTALLING") : t("FXLIB_UPDATE"), "modal__button--primary", () => installOnline(item, { replace: installedVersion.id }), busy));
    } else {
      group.appendChild(button(busy ? t("FXLIB_INSTALLING") : t("FXLIB_INSTALL"), "modal__button--primary", () => installOnline(item), busy));
    }
    if (versions.length > 1) {
      const arrow = button("", "fxlib-split__arrow" + (item.installed ? "" : " modal__button--primary"), () => openVersions(arrow, item, installedVersion), busy, t("FXLIB_VERSIONS"), "chevron-down");
      arrow.setAttribute("aria-haspopup", "menu");
      arrow.setAttribute("aria-expanded", "false");
      arrow.setAttribute("aria-label", t("FXLIB_VERSIONS"));
      group.appendChild(arrow);
    }
    return card({ id: String(item.rid), name: item.name, manufacturer: item.manufacturer, category: item.category, tags, actions: [group], thumb: "" });
  }

  /** Aufklappliste mit allen Versionen (Revisionen) eines Geraets: neueste zuerst; eine davon waehlen und installieren. */
  function openVersions(anchor, item, installedVersion) {
    const rows = item.versions.map((v, index) => {
      const badges = [];
      if (index === 0) badges.push({ text: t("FXLIB_LATEST"), cls: "cat" });
      if (v.installed) badges.push({ text: t("FXLIB_INSTALLED_TAG"), cls: "ok" });
      if (v.verified === true) badges.push({ text: t("FXLIB_VERIFIED"), cls: "ok", icon: "check" });
      return {
        label: t("FXLIB_REV", { rev: String(v.revision || "?").replace(/_/g, " ") }), badges, disabled: v.installed,
        sub: [day(v.modified), v.creator ? t("FXLIB_BY", { name: v.creator }) : "", v.version ? `GDTF ${v.version}` : ""].filter(Boolean).join(" \u00B7 "),
        onClick: () => installOnline({ ...item, rid: v.rid, revision: v.revision }, installedVersion && !v.installed ? { replace: installedVersion.id } : {}),
      };
    });
    popover(anchor, rows);
  }

  function renderOnline() {
    const grid = $("fxlib-online-grid");
    grid.textContent = "";
    const o = S.online;
    $("fxlib-online-count").textContent = o.error ? "" : t("FXLIB_ONLINE_COUNT", { shown: o.items.length, total: o.total });
    $("fxlib-online-error").textContent = o.error;
    $("fxlib-online-error").hidden = !o.error;
    if (!o.items.length && !o.loading && !o.error) grid.appendChild(emptyState(true));
    o.items.forEach((item) => grid.appendChild(onlineCard(item)));
    const more = $("fxlib-online-more");
    const all = o.items.length >= o.total;
    more.hidden = all;
    more.disabled = o.loading;
    more.textContent = o.loading ? t("FXLIB_LOADING") : t("FXLIB_MORE");
    const end = $("fxlib-online-end");
    end.hidden = !(all && o.total > PAGE && !o.loading);
    end.textContent = t("FXLIB_ALL_LOADED", { n: o.total });
  }

  function filtersActive() { const f = F(); return !!(f.q || f.cat || f.mfr || f.verified || f.minRating); }

  /** Leere Liste: Hinweis, bei aktiven Filtern mit 'Filter zuruecksetzen'. */
  function emptyState(online) {
    const box = el("div", "fxlib__empty");
    const installedEmpty = !online && !S.installed.length;
    box.appendChild(el("p", "", t(installedEmpty ? "FXLIB_EMPTY_INSTALLED" : "FXLIB_EMPTY_FILTER")));
    if (filtersActive()) box.appendChild(button(t("FXLIB_RESET_FILTERS"), "", resetFilters));
    return box;
  }

  function resetFilters() {
    const f = F();
    f.q = ""; f.cat = ""; f.mfr = ""; f.verified = false; f.minRating = 0;
    $("fxlib-search").value = "";
    buildCategories();
    if (S.tab === "installed") buildManufacturers(S.installed.map((x) => x.manufacturer)); else buildManufacturers(S.online.manufacturers);
    showOnlineView();
    filtersChanged(true);
  }

  async function searchOnline(append, keepRange, refresh) {
    const o = S.online;
    const seq = ++o.seq;
    o.loading = true;
    o.error = "";
    const offset = append ? o.items.length : 0;
    const limit = keepRange ? Math.min(200, Math.max(PAGE, o.items.length)) : PAGE;
    renderOnline();
    const params = new URLSearchParams({ q: F().q, category: F().cat, manufacturer: F().mfr, offset: String(offset), limit: String(limit),
                                         sort: F().sort || "name", verified: F().verified ? "1" : "0",
                                         verified_first: F().verifiedFirst && !F().verified ? "1" : "0", min_rating: String(F().minRating || 0) });
    if (refresh) params.set("refresh", "1");
    const res = await api("GET", "/api/library/online/search?" + params);
    if (seq !== o.seq) return;                     // eine neuere Suche ist unterwegs
    o.loading = false;
    if (!res.ok) {
      if (res.data.error === "auth") { o.status = null; S.online.status = { logged_in: false }; showOnlineView(); }
      o.error = errorText(res.data.error, res.data) + (res.data.error === "network" && res.data.message ? " " + res.data.message : "");
      o.items = append ? o.items : [];
      renderOnline();
      return;
    }
    o.items = append ? o.items.concat(res.data.items) : res.data.items;
    o.total = res.data.total;
    o.listTotal = res.data.list_total;
    o.manufacturers = res.data.manufacturers || [];
    const hadVerified = o.hasVerified;
    const hadRating = o.hasRating;
    o.hasVerified = !!res.data.has_verified;
    o.hasRating = !!res.data.has_rating;
    if (S.tab === "online") buildManufacturers(o.manufacturers);
    if (hadVerified !== o.hasVerified || hadRating !== o.hasRating) showOnlineView();
    renderOnline();
    if (refresh) {
      if (res.data.refresh_throttled) _showToast(t("FXLIB_REFRESH_THROTTLED", { s: res.data.list_age || 0 }), "warn", 3500, true);
      else _showToast(t("FXLIB_REFRESHED", { n: res.data.list_total }), "ok", 2500, true);
    }
    updateTop();
  }

  async function installOnline(item, opts) {
    const key = String(item.rid);
    if (S.online.busy.has(key)) return;
    S.online.busy.add(key);
    renderOnline();
    renderInstalled();
    const body = { rid: item.rid };
    if (opts && opts.replace) body.replace = opts.replace;
    const res = await api("POST", "/api/library/online/install", body);
    S.online.busy.delete(key);
    if (res.ok) {
      const key2 = res.data.removed_old ? "FXLIB_UPDATED_OK" : (res.data.replaced ? "FXLIB_REPLACED_OK" : "FXLIB_INSTALLED_OK");
      _showToast(t(key2, { name: res.data.name || item.name, rev: String(item.revision || "").replace(/_/g, " ") }), "ok", 3000, true);
      if (res.data.kept_old === "in_use") _showToast(t("FXLIB_OLD_KEPT"), "warn", 4500, true);
      if (res.data.pinned_old || res.data.pinned) _showToast(t("FXLIB_SHOW_KEEPS_COPY"), "info", 6500, true);
      await loadInstalled();
      if (S.tab === "online" && S.online.status && S.online.status.logged_in) await searchOnline(false, true);
    } else {
      if (res.data.error === "auth") { S.online.status = { logged_in: false }; showOnlineView(); }
      _showToast(errorText(res.data.error, res.data), "warn", 4500, true);
      renderOnline();
      renderInstalled();
    }
  }

  async function doLogin(event) {
    event.preventDefault();
    const user = $("fxlib-user").value.trim();
    const password = $("fxlib-pass").value;
    const msg = $("fxlib-login-error");
    msg.hidden = true;
    const submit = $("fxlib-login-submit");
    submit.disabled = true;
    const res = await api("POST", "/api/library/online/login", { user, password, remember: $("fxlib-remember").checked });
    submit.disabled = false;
    if (!res.ok) {
      msg.textContent = errorText(res.data.error, res.data);
      msg.hidden = false;
      return;
    }
    $("fxlib-pass").value = "";
    try { localStorage.setItem("opencue.fxlib.user", user); } catch { /* ohne Speicher: kein Vorausfuellen */ }
    S.online.status = res.data;
    showOnlineView();
    searchOnline(false);
  }

  async function doLogout() {
    await api("POST", "/api/library/online/logout");
    S.online.status = { logged_in: false };
    S.online.items = [];
    S.online.total = 0;
    S.online.manufacturers = [];
    S.updates = {};
    renderOnline();
    renderInstalled();
    showOnlineView();
  }

  /** Konto-Menue: Profil im Web, Liste aktualisieren, Abmelden. */
  function openAccountMenu() {
    const st = S.online.status || {};
    popover($("fxlib-account"), [
      { label: t("FXLIB_LOGGED_AS", { user: st.user || "" }), disabled: true, id: "fxlib-menu-user" },
      { separator: true },
      { label: t("FXLIB_REFRESH"), id: "fxlib-menu-refresh", sub: st.list_age !== null && st.list_age !== undefined ? t("FXLIB_LIST_AGE", { s: st.list_age }) : "", onClick: () => searchOnline(false, false, true) },
      { label: t("FXLIB_PROFILE"), id: "fxlib-menu-profile", sub: t("FXLIB_PROFILE_TIP"), onClick: () => window.open(st.base || "https://gdtf-share.com", "_blank", "noopener") },
      { separator: true },
      { label: t("FXLIB_LOGOUT"), id: "fxlib-menu-logout", danger: true, sub: t("FXLIB_LOGOUT_TIP"), onClick: doLogout },
    ]);
  }

  // ------------------------------------------------------------------------------------------------------ Import
  async function importFiles(files) {
    for (const file of files) {
      if (!/\.gdtf$/i.test(file.name)) { _showToast(t("FXLIB_ERR_INVALID_FILE"), "warn", 4000, true); continue; }
      if (file.size > 30 * 1024 * 1024) { _showToast(t("FXLIB_ERR_TOO_LARGE"), "warn", 4000, true); continue; }
      const res = await api("POST", "/api/library/import", await file.arrayBuffer(), { "X-Filename": encodeURIComponent(file.name), "Content-Type": "application/octet-stream" });
      if (res.ok) _showToast(t(res.data.replaced ? "FXLIB_REPLACED_OK" : "FXLIB_INSTALLED_OK", { name: res.data.name || file.name }), "ok", 3000, true);
      else _showToast(errorText(res.data.error), "warn", 4500, true);
    }
    await loadInstalled();
    if (S.tab === "online" && S.online.status && S.online.status.logged_in) searchOnline(false, true);
  }

  // ------------------------------------------------------------------------------------------------------- Tabs
  function setTab(tab) {
    S.tab = tab;
    $("fxlib-search").value = F().q;
    buildCategories();
    document.querySelectorAll("[data-fxlib-tab]").forEach((b) => {
      const on = b.dataset.fxlibTab === tab;
      b.classList.toggle("fxlib__tab--active", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    closePopover();
    $("fxlib-view-installed").hidden = tab !== "installed";
    $("fxlib-view-show").hidden = tab !== "show";
    $("fxlib-view-online").hidden = tab !== "online";
    updateTop();
    if (tab === "installed") {
      $("fxlib-filters").hidden = false;
      buildManufacturers(S.installed.map((f) => f.manufacturer));
      renderInstalled();
    } else if (tab === "show") {
      $("fxlib-filters").hidden = false;
      buildManufacturers(S.show.items.map((f) => f.manufacturer));
      renderShow();
      loadShow();
    } else {
      buildManufacturers(S.online.manufacturers);
      showOnlineView();
      loadOnlineStatus();
    }
  }

  function open() {
    if (typeof _closeAllMenus === "function") _closeAllMenus();
    clearPending();
    buildCategories();
    Modal.open(MODAL);
    setTab("installed");
    loadInstalled();
    loadShow();
    try { const u = localStorage.getItem("opencue.fxlib.user"); if (u && !$("fxlib-user").value) $("fxlib-user").value = u; } catch { /* egal */ }
  }

  function init() {
    if (!$("fxlib-installed-grid")) return;
    document.addEventListener("click", (e) => { if (e.target.closest('[data-action="fixture-library"]')) open(); });
    document.querySelectorAll("[data-fxlib-tab]").forEach((b) => b.addEventListener("click", () => setTab(b.dataset.fxlibTab)));
    $("fxlib-search").addEventListener("input", (e) => { F().q = e.target.value; filtersChanged(false); });
    $("fxlib-mfr").addEventListener("change", (e) => { F().mfr = e.target.value; filtersChanged(true); });
    $("fxlib-cats").addEventListener("click", (e) => {
      const chip = e.target.closest("[data-cat]");
      if (!chip) return;
      F().cat = chip.dataset.cat;
      buildCategories();
      filtersChanged(true);
    });
    $("fxdet-mode").addEventListener("change", (e) => { DET.mode = Number(e.target.value) || 0; renderModeChannels(); });
    $("fxlib-import").addEventListener("click", () => $("fxlib-import-input").click());
    $("fxlib-import-input").addEventListener("change", (e) => { const files = [...e.target.files]; e.target.value = ""; importFiles(files); });
    $("fxlib-login").addEventListener("submit", doLogin);
    $("fxlib-account").addEventListener("click", () => { if (popClose) closePopover(); else openAccountMenu(); });
    $("fxlib-sort").addEventListener("change", (e) => { S.f.online.sort = e.target.value; filtersChanged(true); });
    $("fxlib-verified").addEventListener("click", () => { S.f.online.verified = !S.f.online.verified; showOnlineView(); filtersChanged(true); });
    $("fxlib-verified-first").addEventListener("click", () => { S.f.online.verifiedFirst = !S.f.online.verifiedFirst; showOnlineView(); filtersChanged(true); });
    $("fxlib-rating").addEventListener("change", (e) => { S.f.online.minRating = Number(e.target.value) || 0; filtersChanged(true); });
    $("fxlib-online-more").addEventListener("click", () => searchOnline(true));
    // Nach oben: je Bereich (installiert / online / Details) ein runder Knopf, sobald gescrollt wurde
    const scrollers = [$("fxlib-view-installed"), $("fxlib-view-online")];
    updateTop = wireTop($("fxlib-top"), scrollers, () => scrollers.find((s) => !s.hidden));
    const detScroll = $("fxdet-scroll");
    updateDetTop = wireTop($("fxdet-top"), [detScroll], () => detScroll);
    const dialog = document.querySelector('[data-modal-backdrop="fixture-library"] .modal');
    ["dragenter", "dragover"].forEach((name) => dialog.addEventListener(name, (e) => { e.preventDefault(); dialog.classList.add("modal--drop"); }));
    ["dragleave", "drop"].forEach((name) => dialog.addEventListener(name, (e) => { if (name === "drop" || e.target === dialog) dialog.classList.remove("modal--drop"); }));
    dialog.addEventListener("drop", (e) => { e.preventDefault(); importFiles([...(e.dataTransfer?.files || [])]); });
    // Aenderungen von aussen (anderer Client, Import): Liste neu laden
    document.addEventListener("fixture-library-changed", () => {
      if (!Modal.isOpen(MODAL)) return;
      loadInstalled();
      loadShow();
      if (S.tab === "online" && S.online.status && S.online.status.logged_in) searchOnline(false, true);
    });
    // Sprachwechsel (translator.apply): dynamisch erzeugte Texte neu aufbauen
    const relabel = () => {
      if (!Modal.isOpen(MODAL)) return;
      buildCategories();
      buildManufacturers(S.tab === "installed" ? S.installed.map((f) => f.manufacturer) : S.tab === "show" ? S.show.items.map((f) => f.manufacturer) : S.online.manufacturers);
      renderInstalled();
      renderShow();
      if (S.tab === "online") { renderOnline(); showOnlineView(); }
    };
    const relabelDetails = () => { if (Modal.isOpen("fixture-library-detail") && DET.data) renderDetails(); };
    window.FixtureLibrary = { open, relabel: () => { relabel(); relabelDetails(); }, showDetails: openDetails, state: S };
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
