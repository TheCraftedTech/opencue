// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Einstellungen -> Kategorie "REST-API": Hauptschalter, Reichweite (nur dieser PC / im Netzwerk), Tokens anlegen, bearbeiten, neu erzeugen und loeschen (Berechtigungen je Token in
 * einem breiten Dialog). Wie alle anderen Seiten arbeitet die Seite mit einem ENTWURF: Schalter UND Token-Aenderungen (auch Loeschen) werden erst mit "Speichern" uebernommen, in
 * einem Rutsch ueber /api/apikeys/apply (app/api_v1.py, nur an der Konsole selbst). Geaenderte Zeilen markiert und zaehlt settings_tracker.js (Anbieter "api").
 * Das Token im Klartext sieht man nur einmal, direkt nach dem Speichern (neu angelegte oder neu erzeugte Tokens). Klassisches Skript. */
(function () {
  "use strict";
  const DIALOG = "api-token";
  const CRITICAL = new Set(["write.dmx", "write.command", "write.showfile", "write.patch", "write.settings"]);            // mit Warnhinweis
  const t = (key, fallback) => { try { const v = typeof i18n === "function" ? i18n(key) : ""; return v && v !== key ? v : fallback; } catch (err) { return fallback; } };
  const capKey = (id) => "API_CAP_" + id.replace(/\./g, "_").toUpperCase();
  const clone = (value) => JSON.parse(JSON.stringify(value));
  let saved = { enabled: true, cors: true, network: false, tokens: [], capabilities: [], presets: {} };       // Stand des Servers
  let draft = null;                                                                                             // Entwurf dieser Sitzung des Dialogs (null = noch nicht geladen)
  let backdrop = null;
  let bound = false;
  let tempCounter = 0;
  const rowOf = {};

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  const toast = (message, type) => { if (typeof _showToast === "function") _showToast(message, type || "info", 3500); };
  const baseUrl = () => location.origin + "/api/v1";
  const touch = () => { if (window.OCSettings) window.OCSettings.touch(); };

  async function api(method, path, body) {
    const res = await fetch(path, { method, cache: "no-store", headers: body !== undefined ? { "Content-Type": "application/json" } : {}, body: body !== undefined ? JSON.stringify(body) : undefined });
    let json = null;
    try { json = await res.json(); } catch (err) { /* keine JSON-Antwort */ }
    if (!res.ok) throw new Error((json && json.error && json.error.message) || ("HTTP " + res.status));
    return json;
  }

  async function copy(text) {
    const ok = typeof _copyText === "function" ? await _copyText(text) : false;
    toast(ok ? t("SETTINGS_REMOTE_COPIED", "Copied") : t("SETTINGS_REMOTE_COPY_FAILED", "Copying is not possible"), ok ? "info" : "error");
  }

  function copyRow(label, value) {
    const field = el("div", "settings-field");
    field.appendChild(el("label", "", label));
    const wrap = el("div", "modal__field");
    const input = el("input");
    input.type = "text";
    input.readOnly = true;
    input.value = value;
    input.className = "api-readonly";
    const button = el("button", "modal__button", t("SETTINGS_REMOTE_COPY", "Copy"));
    button.type = "button";
    button.addEventListener("click", () => copy(value));
    wrap.append(input, button);
    field.appendChild(wrap);
    return field;
  }

  function permsLabel(caps) {
    const set = new Set(caps);
    const same = (list) => list.length === set.size && list.every((c) => set.has(c));
    const presets = saved.presets || {};
    if (!set.size) return t("API_PERMS_NONE", "No permissions");
    if (presets.full && same(presets.full)) return t("API_PERMS_FULL", "Full access");
    if (presets.edit && same(presets.edit)) return t("API_PERMS_EDIT", "Edit show");
    if (presets.operate && same(presets.operate)) return t("API_PERMS_OPERATE", "Operate");
    if (presets.read && same(presets.read)) return t("API_PERMS_READ", "Read only");
    return t("API_PERMS_CUSTOM", "Custom ({n}/{total})").replace("{n}", String(set.size)).replace("{total}", String(saved.capabilities.length));
  }

  function when(seconds) {
    if (!seconds) return t("API_NEVER", "never");
    try { return new Date(seconds * 1000).toLocaleString(); } catch (err) { return String(seconds); }
  }

  function askSure(title, body, confirmKey) {
    return _askLayoutConfirm({ title, body, confirmKey });
  }

  // ------------------------------------------------------------------------------------------------ Entwurf <-> Server
  const savedToken = (id) => saved.tokens.find((x) => x.id === id);
  const sameCaps = (a, b) => a.length === b.length && a.every((c) => b.includes(c));

  /** Was am Token gegenueber dem Gespeicherten anders ist: "new" | "deleted" | "regenerate" | "changed" | "" */
  function tokenState(token) {
    if (token.isNew) return "new";
    if (token.deleted) return "deleted";
    if (token.regenerate) return "regenerate";
    const was = savedToken(token.id);
    if (!was) return "";
    return was.name !== token.name || !sameCaps(was.capabilities, token.capabilities) || !!was.enabled !== !!token.enabled ? "changed" : "";
  }

  function changes() {
    if (!draft) return [];
    const out = [];
    [["enabled", "API_ENABLE_LABEL"], ["network", "API_REACH"], ["cors", "API_CORS"], ["views", "API_VIEWS"]].forEach(([key, labelKey]) => {
      const was = key === "views" ? saved[key] !== false : saved[key];
      if (draft[key] === was || !rowOf[key] || !rowOf[key].isConnected) return;
      out.push({ key: "api:" + key, label: t(labelKey, key), row: rowOf[key], revert: () => { draft[key] = was; render(); } });
    });
    draft.tokens.forEach((token) => {
      const state = tokenState(token);
      const row = rowOf["tok:" + token.id];
      if (!state || !row || !row.isConnected) return;
      out.push({ key: "api:token:" + token.id, label: token.name + " (" + t("API_STATE_" + state.toUpperCase(), state) + ")", row,
        revert: () => {
          if (token.isNew) draft.tokens = draft.tokens.filter((x) => x !== token);
          else Object.assign(token, clone(savedToken(token.id)), { deleted: false, regenerate: false });
          render();
        } });
    });
    return out;
  }

  async function reset() {
    if (!draft) await refresh();
    if (!draft) return;
    draft.enabled = true; draft.cors = true; draft.network = false; draft.views = true;                  // Werkseinstellung; die Tokens selbst bleiben (loeschen geht nur einzeln)
    render();
  }

  async function refresh() {
    try {
      const data = await api("GET", "/api/apikeys");
      const keepDraft = draft && changes().length > 0;
      saved = data;
      if (!keepDraft) draft = clone({ enabled: saved.enabled, cors: saved.cors, network: !!saved.network, views: saved.views !== false, tokens: saved.tokens });
    } catch (err) { toast(err.message, "error"); }
    render();
  }

  /** "Speichern" des Einstellungsdialogs: alle Aenderungen in einem Rutsch an den Server. */
  async function commit() {
    if (!draft) return;
    const body = { create: [], update: [], regenerate: [], delete: [] };
    ["enabled", "cors", "network", "views"].forEach((key) => { if (draft[key] !== (key === "views" ? saved[key] !== false : saved[key])) body[key] = draft[key]; });
    draft.tokens.forEach((token) => {
      const state = tokenState(token);
      if (state === "new") body.create.push({ temp_id: token.id, name: token.name, capabilities: token.capabilities, enabled: token.enabled });
      else if (state === "deleted") body.delete.push(token.id);
      else if (state === "regenerate" || state === "changed") {
        const was = savedToken(token.id) || {};
        body.update.push({ id: token.id, name: token.name, capabilities: token.capabilities, enabled: token.enabled });
        if (state === "regenerate") body.regenerate.push(token.id);
        void was;
      }
    });
    if (!changes().length) return;
    try {
      const result = await api("POST", "/api/apikeys/apply", body);
      saved = Object.assign({}, saved, result.snapshot);
      draft = clone({ enabled: saved.enabled, cors: saved.cors, network: !!saved.network, views: saved.views !== false, tokens: saved.tokens });
      render();
      if (result.secrets && result.secrets.length) showSecrets(result.secrets);
    } catch (err) {
      toast(err.message, "error");
    }
  }

  // ------------------------------------------------------------------------------------------------ Kategorie
  function root() { return document.getElementById("settings-api-root"); }

  function toggleRow(id, label, checked, onChange, hint, rowKey, master) {
    const field = el("div", "settings-field" + (master ? " settings-master" : ""));
    field.appendChild(el("label", "", label));
    const toggle = el("label", "toggle-switch");
    const box = el("input");
    box.type = "checkbox";
    box.id = id;
    box.checked = !!checked;
    box.addEventListener("change", () => { onChange(box.checked); touch(); });
    toggle.append(box, el("span", "toggle-switch__track"));
    field.appendChild(toggle);
    if (rowKey) rowOf[rowKey] = field;
    return field;
  }

  function render() {
    const host = root();
    if (!host || !draft) return;
    host.textContent = "";
    Object.keys(rowOf).forEach((k) => delete rowOf[k]);

    // ---- Hauptschalter + Reichweite
    const main = el("div", "settings-section");
    main.appendChild(toggleRow("settings-api-enabled", t("API_ENABLE_LABEL", "REST API"), draft.enabled, (on) => { draft.enabled = on; }, "", "enabled", true));
    main.appendChild(el("p", "settings-field-hint settings-keep", t("API_HINT", "Other programs control OpenCue with tokens.")));

    const reach = el("div", "settings-field");
    reach.appendChild(el("label", "", t("API_REACH", "Reachable from")));
    const select = el("select");
    select.id = "settings-api-reach";
    [["local", t("API_REACH_LOCAL", "This computer only")], ["network", t("API_REACH_NETWORK", "The network")]].forEach(([value, label]) => { const o = el("option", "", label); o.value = value; select.appendChild(o); });
    select.value = draft.network ? "network" : "local";
    select.addEventListener("change", () => { draft.network = select.value === "network"; syncReachHint(); touch(); });
    reach.appendChild(select);
    rowOf.network = reach;
    main.appendChild(reach);
    const reachHint = el("p", "settings-field-hint api-reach-hint");
    const goRemote = el("button", "modal__button--link", t("API_GO_REMOTE", "Open remote access"));
    goRemote.type = "button";
    goRemote.addEventListener("click", () => { const b = document.querySelector('.modal--settings [data-settings-category="remote"]'); if (b) b.click(); });
    reachHint.append(el("span", "", ""), goRemote);
    main.appendChild(reachHint);
    function syncReachHint() {
      const rs = typeof client !== "undefined" && client.state ? client.state.remote : null;
      const remoteOn = !!(rs && (rs.enabled || rs.https_enabled));
      const needs = draft.network && !remoteOn;
      reachHint.hidden = !needs;
      reachHint.firstChild.textContent = t("API_REACH_NEEDS_REMOTE", "Other computers can only get through when remote access is on.") + " ";
    }
    syncReachHint();

    main.appendChild(toggleRow("settings-api-cors", t("API_CORS", "Allow web pages on other addresses"), draft.cors, (on) => { draft.cors = on; }, "", "cors", false));
    main.appendChild(toggleRow("settings-api-views", t("API_VIEWS", "Status views (images / web pages)"), draft.views, (on) => { draft.views = on; }, "", "views", false));
    main.appendChild(el("p", "settings-field-hint", t("API_VIEWS_HINT", "Small read-only displays for simple devices (ESP32 display, wall tablet): /api/v1/views/status.png, dmx, timecode ...")));
    main.appendChild(copyRow(t("API_BASE_URL", "Address of the API"), baseUrl()));
    const rs = typeof client !== "undefined" && client.state ? client.state.remote : null;
    const netUrls = draft.network && rs && rs.listening_on_network ? [...(rs.urls || []), ...(rs.https_urls || [])] : [];          // so erreichen andere Geraete die API (Name, IP-Adressen)
    netUrls.forEach((url) => main.appendChild(copyRow(t("API_NET_URL", "Address in the network"), url + "/api/v1")));
    main.appendChild(copyRow(t("API_DOCS_URL", "Documentation"), baseUrl() + "/docs"));
    main.appendChild(copyRow(t("API_VIEWS_URL", "Status views"), baseUrl() + "/views"));
    const example = el("details", "settings-advanced settings-keep");
    example.appendChild(el("summary", "", t("API_EXAMPLE", "Example")));
    example.appendChild(el("pre", "api-example", 'curl -H "Authorization: Bearer <token>" ' + baseUrl() + "/status\n" +
      'curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d \'{"command":"Fixture 1 At 80"}\' ' + baseUrl() + "/command"));
    main.appendChild(example);
    host.appendChild(main);

    // ---- Tokens
    const tokens = el("div", "settings-section");
    const head = el("div", "settings-section__head");
    head.appendChild(el("div", "settings-section__title", t("API_TOKENS", "Tokens")));
    const add = el("button", "modal__button modal__button--primary", t("API_NEW", "New token"));
    add.type = "button";
    add.id = "settings-api-new";
    add.addEventListener("click", () => openDialog(null));
    head.appendChild(add);
    tokens.appendChild(head);
    if (!draft.tokens.length) tokens.appendChild(el("p", "settings-field-hint", t("API_NONE", "No tokens yet. Create one to use the API.")));
    draft.tokens.forEach((token) => tokens.appendChild(tokenRow(token)));
    host.appendChild(tokens);

    // ---- Wer ist gerade verbunden (WebSocket-Strom), live
    const conns = el("div", "settings-section api-conns");
    const connHead = el("div", "settings-section__head");
    connHead.appendChild(el("div", "settings-section__title", t("API_CONNS", "Connected now")));
    const connCount = el("span", "api-conns__count");
    connCount.id = "settings-api-conns-count";
    connHead.appendChild(connCount);
    conns.appendChild(connHead);
    const connList = el("div", "api-conn-list");
    connList.id = "settings-api-conns";
    conns.appendChild(connList);
    host.appendChild(conns);
    paintConns();
    if (window.OCSettings) window.OCSettings.bindMasters(host);
    touch();
  }

  function tokenRow(token) {
    const state = tokenState(token);
    const row = el("div", "api-token" + (token.deleted ? " api-token--deleted" : "") + (token.enabled === false ? " api-token--off" : "") + (state === "changed" || state === "regenerate" ? " api-token--changed" : ""));
    rowOf["tok:" + token.id] = row;
    const nameBox = el("div", "api-token__name");
    nameBox.appendChild(el("span", "api-token__title", token.name));
    const sub = (token.hint || "oc_") + "…  ·  " + t("API_LAST_USED", "last used") + ": " + when(token.last_used) + (state === "regenerate" ? "  ·  " + t("API_STATE_REGENERATE", "new token") : "");
    nameBox.appendChild(el("span", "api-token__key", sub));
    row.appendChild(nameBox);
    row.appendChild(el("span", "api-token__perms", permsLabel(token.capabilities)));
    const sw = el("label", "toggle-switch");
    sw.title = t("API_TOKEN_ACTIVE", "Token on / off");
    const box = el("input");
    box.type = "checkbox";
    box.checked = token.enabled !== false;
    box.disabled = !!token.deleted;
    box.addEventListener("change", () => { token.enabled = box.checked; render(); });
    sw.append(box, el("span", "toggle-switch__track"));
    row.appendChild(sw);
    const actions = el("div", "api-token__actions");
    if (token.deleted) {
      const undo = el("button", "modal__button", t("API_RESTORE", "Keep"));
      undo.type = "button";
      undo.addEventListener("click", () => { token.deleted = false; render(); });
      actions.appendChild(undo);
    } else {
      const edit = el("button", "modal__button", t("EDIT", "Edit"));
      edit.type = "button";
      edit.addEventListener("click", () => openDialog(token));
      const del = el("button", "modal__button api-danger", t("API_DELETE", "Delete"));
      del.type = "button";
      del.addEventListener("click", async () => {
        const ok = await _askDelete("other", { title: t("API_DELETE_TITLE", "Delete token?"), body: t("API_DELETE_BODY", "The token \"{name}\" stops working at once.").replace("{name}", token.name), confirmKey: "API_DELETE" });
        if (!ok) return;
        try {                                                                                        // Sicherheitsdialog (oder abgeschaltet) -> sofort loeschen, kein Umweg ueber "Speichern"
          await api("DELETE", "/api/apikeys/" + token.id);
          saved.tokens = saved.tokens.filter((x) => x.id !== token.id);
          draft.tokens = draft.tokens.filter((x) => x.id !== token.id);
          render();
        } catch (err) { toast(err.message, "error"); }
      });
      actions.append(edit, del);
    }
    row.appendChild(actions);
    return row;
  }

  // ------------------------------------------------------------------------------------------------ Verbundene Geraete (live)
  let connTimer = 0;
  const seconds = (n) => (n >= 3600 ? Math.floor(n / 3600) + " h " + Math.floor((n % 3600) / 60) + " min" : n >= 60 ? Math.floor(n / 60) + " min " + (n % 60) + " s" : n + " s");

  async function paintConns() {
    const list = document.getElementById("settings-api-conns");
    if (!list) return;
    let data = null;
    try { data = await api("GET", "/api/apikeys/connections"); } catch (err) { data = null; }
    const target = document.getElementById("settings-api-conns");
    if (!target) return;
    target.textContent = "";
    const rows = (data && data.connections) || [];
    const count = document.getElementById("settings-api-conns-count");
    if (count) count.textContent = data ? rows.length + " / " + data.max + (data.event_streams ? " · " + t("API_CONN_STREAMS", "{n} event stream(s)").replace("{n}", String(data.event_streams)) : "") : "";
    if (!rows.length) { target.appendChild(el("p", "settings-field-hint", t("API_CONNS_NONE", "No device is connected through the WebSocket right now."))); return; }
    rows.forEach((c) => {
      const row = el("div", "api-conn");
      const who = el("div", "api-token__name");
      who.append(el("span", "api-token__title", c.token), el("span", "api-token__key", c.ip));
      const what = [];
      if (c.topics.length) what.push(t("API_CONN_TOPICS", "receives") + ": " + c.topics.join(", "));
      if (c.sticks.length) what.push(t("API_CONN_STICK", "joystick active"));
      if (c.audio_in) what.push(t("API_CONN_AUDIO", "sends audio") + " (" + c.audio_in + " Hz)");
      row.append(who, el("span", "api-token__perms", what.join(" · ") || "-"), el("span", "api-token__used", c.messages_per_second + " " + t("API_CONN_RATE", "msg/s") + " · " + seconds(c.seconds)));
      const kick = el("button", "modal__button api-danger", t("API_CONN_KICK", "Disconnect"));
      kick.type = "button";
      kick.addEventListener("click", async () => { try { await api("POST", "/api/apikeys/connections/" + c.id + "/close"); } catch (err) { /* schon weg */ } paintConns(); });
      row.appendChild(kick);
      target.appendChild(row);
    });
  }
  function watchConns() {
    clearInterval(connTimer);
    connTimer = setInterval(() => { const r = root(); if (!r || !r.offsetParent) { clearInterval(connTimer); return; } paintConns(); }, 2000);        // nur solange die Seite sichtbar ist
  }

  // ------------------------------------------------------------------------------------------------ Dialog
  function ensureDialog() {
    if (backdrop) return backdrop;
    backdrop = el("div", "modal-backdrop modal-backdrop--stacked");
    backdrop.dataset.modalBackdrop = DIALOG;
    backdrop.setAttribute("aria-hidden", "true");
    backdrop.innerHTML =
      '<div class="modal modal--l modal--api-token" role="dialog" aria-modal="true" aria-labelledby="api-token-title">' +
      '<div class="modal__header"><span id="api-token-title"></span><button type="button" class="modal__close" data-modal-close="' + DIALOG + '" aria-label="Close">&times;</button></div>' +
      '<div class="modal__body api-dialog__body"></div><div class="modal__footer"></div></div>';
    document.body.appendChild(backdrop);
    return backdrop;
  }

  const part = (selector) => ensureDialog().querySelector(selector);

  function footer(buttons) {
    const box = part(".modal__footer");
    box.textContent = "";
    buttons.forEach((b) => box.appendChild(b));
  }

  function button(label, cls, onClick) {
    const b = el("button", "modal__button" + (cls ? " " + cls : ""), label);
    b.type = "button";
    b.addEventListener("click", onClick);
    return b;
  }

  // Die Berechtigungen in vier Spalten: Lesen, Bedienen, Show bearbeiten, System (kritisch)
  const CAP_COLUMNS = [
    ["API_GROUP_READ", "Read", ["read.status", "read.show", "read.dmx"]],
    ["API_GROUP_WRITE", "Operate", ["write.command", "write.cue", "write.timecode", "write.blackout", "write.audio", "write.programmer", "write.widgets"]],
    ["API_GROUP_EDIT", "Edit the show", ["write.show", "write.variables", "write.effects", "write.scripts", "write.media", "write.layout"]],
    ["API_GROUP_CRITICAL", "System", ["write.patch", "write.dmx", "write.showfile", "write.settings"]],
  ];

  /** Formular: Name, Voreinstellungen und die Berechtigungen. Neues Token: wird SOFORT angelegt und gleich angezeigt. Bearbeiten: nur der ENTWURF (gespeichert wird mit "Speichern" der Einstellungen). */
  function openDialog(token) {
    ensureDialog();
    const editing = !!token;
    part("#api-token-title").textContent = editing ? t("API_DLG_EDIT", "Edit API token") : t("API_DLG_NEW", "New API token");
    const body = part(".api-dialog__body");
    body.textContent = "";
    const chosen = new Set(editing ? token.capabilities : saved.capabilities.filter((c) => c.default).map((c) => c.id));

    const top = el("div", "api-dialog__top");
    const nameField = el("div", "api-dialog__name");
    nameField.appendChild(el("label", "", t("API_NAME", "Name")));
    const name = el("input");
    name.type = "text";
    name.id = "api-token-name";
    name.maxLength = 60;
    name.value = editing ? token.name : "";
    name.placeholder = t("API_NAME_PH", "e.g. Stage manager tablet");
    nameField.appendChild(name);
    top.appendChild(nameField);

    const presetRow = el("div", "api-presets");
    presetRow.appendChild(el("span", "api-presets__label", t("API_PRESETS", "Presets")));
    const switches = new Map();
    const sync = () => {
      switches.forEach((box, id) => { box.checked = chosen.has(id); });
      presetButtons.forEach(([list, b]) => { const on = list.length === chosen.size && list.every((c) => chosen.has(c)); b.classList.toggle("api-preset--on", on); });
    };
    const defaults = saved.capabilities.filter((c) => c.default).map((c) => c.id);
    const presetButtons = [
      [saved.presets.read || [], t("API_PRESET_READ", "Read only")],
      [saved.presets.operate || [], t("API_PRESET_OPERATE_SHORT", "Operate")],
      [saved.presets.edit || [], t("API_PRESET_EDIT_SHORT", "Edit show")],
      [saved.presets.full || [], t("API_PRESET_FULL", "Full access")],
      [defaults, t("API_PRESET_DEFAULT", "Default")],
    ].map(([list, label]) => {
      const b = button(label, "api-preset", () => { chosen.clear(); list.forEach((c) => chosen.add(c)); sync(); });
      presetRow.appendChild(b);
      return [list, b];
    });
    top.appendChild(presetRow);
    body.appendChild(top);

    const grid = el("div", "api-caps");
    CAP_COLUMNS.forEach(([key, fallback, ids]) => {
      const column = el("div", "api-caps__col");
      column.appendChild(el("div", "api-caps__title", t(key, fallback)));
      ids.map((id) => saved.capabilities.find((c) => c.id === id)).filter(Boolean).forEach((cap) => {
        const row = el("label", "api-cap");
        const desc = t(capKey(cap.id) + "_DESC", "");
        row.title = desc;
        const sw = el("span", "toggle-switch");
        const box = el("input");
        box.type = "checkbox";
        box.addEventListener("change", () => { if (box.checked) chosen.add(cap.id); else chosen.delete(cap.id); sync(); });
        switches.set(cap.id, box);
        sw.append(box, el("span", "toggle-switch__track"));
        const text = el("span", "api-cap__text");
        const title = el("span", "api-cap__title", t(capKey(cap.id), cap.id));
        if (CRITICAL.has(cap.id)) title.appendChild(el("span", "api-cap__crit", t("API_CRITICAL", "critical")));
        text.append(title, el("span", "api-cap__desc", desc));
        row.append(sw, text);
        column.appendChild(row);
      });
      grid.appendChild(column);
    });
    body.appendChild(grid);
    body.appendChild(el("p", "api-dialog__note", editing ? t("API_EDIT_NOTE", "Changes apply when you press Save in the settings.") : t("API_CREATE_NOTE", "The token is created at once and shown right after - copy it then.")));
    sync();

    const buttons = [button(t("CANCEL", "Cancel"), "", () => Modal.close(DIALOG))];
    if (editing) {
      const regenerate = el("button", "modal__button api-danger", token.regenerate ? t("API_REGENERATE_UNDO", "Keep the current token") : t("API_REGENERATE", "Generate new token"));
      regenerate.type = "button";
      regenerate.addEventListener("click", async () => {
        if (!token.regenerate && !(await askSure(t("API_REGENERATE_TITLE", "Generate a new token?"), t("API_REGENERATE_BODY", "The old token of \"{name}\" stops working as soon as you save.").replace("{name}", token.name), "API_REGENERATE"))) return;
        token.regenerate = !token.regenerate;
        Modal.close(DIALOG);
        render();
      });
      buttons.unshift(regenerate);
    }
    const ok = button(editing ? t("API_APPLY", "OK") : t("API_CREATE", "Create token"), "modal__button--primary", async () => {
      const cleanName = name.value.trim();
      if (editing) {
        token.name = cleanName || token.name;
        token.capabilities = [...chosen];
        Modal.close(DIALOG);
        render();
        return;
      }
      ok.disabled = true;
      try {
        const made = await api("POST", "/api/apikeys", { name: cleanName || t("API_DEFAULT_NAME", "Token"), capabilities: [...chosen] });
        saved.tokens = [...saved.tokens, made.record];                              // gespeichert und angezeigt: kein "Speichern" noetig
        if (draft) draft.tokens.push(clone(made.record));
        Modal.close(DIALOG);
        render();
        setTimeout(() => showSecrets([{ name: made.record.name, token: made.token }]), 120);
      } catch (err) {
        ok.disabled = false;
        toast(err.message, "error");
      }
    });
    buttons.push(ok);
    footer(buttons);
    Modal.open(DIALOG);
    name.focus();
  }

  /** Die Tokens im Klartext - nur dieses eine Mal, direkt nach dem Speichern. */
  function showSecrets(list) {
    ensureDialog();
    part("#api-token-title").textContent = list.length === 1 ? t("API_CREATED_TITLE", "Your new token") : t("API_CREATED_TITLE_N", "Your new tokens");
    const body = part(".api-dialog__body");
    body.textContent = "";
    body.appendChild(el("p", "api-warning", t("API_CREATED_WARN", "Copy the token now. It is shown only once - afterwards only its first characters are visible.")));
    list.forEach((item) => {
      const field = el("div", "settings-field");
      field.appendChild(el("label", "", item.name));
      const wrap = el("div", "modal__field");
      const input = el("input");
      input.type = "text";
      input.readOnly = true;
      input.value = item.token;
      input.className = "api-readonly api-secret";
      input.addEventListener("focus", () => input.select());
      wrap.append(input, button(t("SETTINGS_REMOTE_COPY", "Copy"), "modal__button--primary", () => copy(item.token)));
      field.appendChild(wrap);
      body.appendChild(field);
    });
    footer([button(t("API_DONE", "Done"), "modal__button--primary", () => Modal.close(DIALOG))]);
    Modal.open(DIALOG);
  }

  function bind() {
    if (bound) return;
    bound = true;
    document.addEventListener("settings-category-shown", (e) => { if (e.detail && e.detail.category === "api") { refresh(); watchConns(); } });
    document.addEventListener("settings-opened", () => { draft = null; });
    document.addEventListener("settings-cancelled", () => { draft = null; if (root() && root().offsetParent) refresh(); });
    document.addEventListener("settings-saved", commit);
    const register = () => { if (window.OCSettings) window.OCSettings.register({ id: "api", category: "api", changes, reset }); else setTimeout(register, 50); };
    register();
  }

  bind();
  window.OCApiSettings = { refresh, openDialog };
})();
