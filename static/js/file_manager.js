/* Dateimanager: ein grosser Dialog fuer alle Dateiarten (Shows, Layouts, 3D-Buehnen, Effekte, Scheinwerfer-Dateien) mit Seitenleiste, Suche, Mehrfachauswahl,
 * Oeffnen/Umbenennen/Duplizieren/Loeschen, Download (ein Eintrag, Auswahl oder alles als ZIP), Upload (Dateien, Ordner, ZIP-Pakete) und dem Export-Dialog fuer die geladene Show.
 * Schnittstelle: app/file_manager.py (/api/files/...). Oeffnen/Umbenennen/Duplizieren/Loeschen rufen die bestehenden Schnittstellen der Dateiarten auf (/api/layouts*,
 * /api/sim-stage*, /api/showfiles*, /api/effects, /api/library/installed), damit deren Besonderheiten (geladene Show, aktives Layout, aktive Buehne) erhalten bleiben.
 * Downloads: im Programmfenster oeffnet der Server den Standard-Browser mit der Adresse (gewoehnlicher Browser-Download); auf entfernten Geraeten laedt der Browser selbst.
 * Namens-, Rueckfrage- und Toast-Dialoge sind die der Layouts (app.js). Klassisches Skript, laeuft nach app.js.
 * Er ersetzt die frueheren Einzel-Dialoge (Showfiles/Layouts/Buehnen verwalten, Show oeffnen): Menues, Toolbar-Chips und Strg+O oeffnen ihn mit der passenden Art
 * (data-action="file-manager" + data-fm-kind). Oben zeigt er den geladenen Stand der Art (Name, ungespeichert) mit Neu/Speichern/Speichern unter; bei Scheinwerfern fuehrt
 * ein Knopf in die Scheinwerferbibliothek. app.js/sim3d_stages.js melden Aenderungen ueber OCFileManager.changed(kind). */
(function () {
  "use strict";
  const t = (key, vars) => {
    let s = i18n(key);
    if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
    return s;
  };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const MODAL = "file-manager";
  const EXPORT_MODAL = "file-export";
  const KINDS = ["shows", "layouts", "stages", "effects", "themes", "fixtures"];
  const KIND_UI = {
    shows: { icon: "cuelist", label: "FM_KIND_SHOWS", hint: "FM_HINT_SHOWS", detail: "FM_DETAIL_SHOWS", accept: ".json,.zip" },
    layouts: { icon: "panel", label: "FM_KIND_LAYOUTS", hint: "FM_HINT_LAYOUTS", detail: "FM_DETAIL_LAYOUTS", accept: ".json,.zip" },
    stages: { icon: "stage", label: "FM_KIND_STAGES", hint: "FM_HINT_STAGES", detail: "FM_DETAIL_STAGES", accept: ".json,.zip" },
    effects: { icon: "fx", label: "FM_KIND_EFFECTS", hint: "FM_HINT_EFFECTS", detail: "FM_DETAIL_EFFECTS", accept: ".fx,.zip" },
    themes: { icon: "palette", label: "FM_KIND_THEMES", hint: "FM_HINT_THEMES", detail: "FM_DETAIL_THEMES", accept: ".json,.zip" },
    fixtures: { icon: "fixture", label: "FM_KIND_FIXTURES", hint: "FM_HINT_FIXTURES", detail: "FM_DETAIL_FIXTURES", accept: ".gdtf,.zip" },
  };
  const EXT = { shows: ".json", layouts: ".json", stages: ".json", effects: ".fx", themes: ".json", fixtures: ".gdtf" };
  /** Anzeigename einer Zeile: die eingebauten Farbprofile (Dunkel/Hell) sind uebersetzt. */
  const rowName = (row) => (row.name_key ? t(row.name_key) : row.name);
  /** Vorschau-Farben eines Farbprofils (Hintergrund, Panel, Text, Akzent): geaenderte Werte des Profils, sonst die der Basis (theme.css). */
  const THEME_BASE_SWATCH = { dark: { bg: "#0a0a0b", "surface-1": "#151517", "text-1": "#ededf0", accent: "#ffb000" }, light: { bg: "#e8eaee", "surface-1": "#ffffff", "text-1": "#16181d", accent: "#a35f00" } };
  function themeSwatches(theme) {
    const base = THEME_BASE_SWATCH[theme && theme.base === "light" ? "light" : "dark"];
    const tokens = (theme && theme.tokens) || {};
    return ["bg", "surface-1", "text-1", "accent"].map((key) => tokens[key] || base[key]);
  }
  const state = { kind: "shows", rows: [], path: "", counts: {}, selected: new Set(), query: "", sort: { key: "name", dir: 1 }, loading: false };
  let seq = 0;
  let built = false;

  const style = document.createElement("style");
  style.textContent = `
    .modal--files { width: min(82rem, 96vw); height: min(50rem, 92vh); display: flex; flex-direction: column; }
    .modal--files .modal__body { flex: 1 1 auto; min-height: 0; padding: 0; display: flex; flex-direction: row; overflow: hidden; }
    .fm { display: flex; width: 100%; min-height: 0; }
    .fm__side { flex: 0 0 15rem; display: flex; flex-direction: column; gap: 0.2rem; padding: 0.6rem; border-right: 1px solid var(--border-color); background: var(--dialog-header-bg); overflow: auto; }
    .fm__kind { display: flex; align-items: center; gap: 0.55rem; padding: 0.55rem 0.6rem; border: 1px solid transparent; border-radius: var(--base-radius, 3px); background: transparent; color: var(--text-main); font: inherit; text-align: left; cursor: pointer; }
    .fm__kind:hover { border-color: var(--border-color); }
    .fm__kind--active { background: var(--accent-soft, rgba(255, 176, 0, 0.14)); border-color: var(--accent-color, #ffb000); }
    .fm__kind .ico { width: 1.15em; height: 1.15em; flex: 0 0 auto; color: var(--secondary-text); }
    .fm__kind--active .ico { color: var(--accent-color, #ffb000); }
    .fm__kind-name { flex: 1 1 auto; font-weight: 600; }
    .fm__kind-count { font-size: 0.72rem; color: var(--secondary-text); font-variant-numeric: tabular-nums; }
    .fm__side-sep { height: 1px; background: var(--border-color); margin: 0.5rem 0; }
    .fm__side-btn { display: flex; align-items: center; gap: 0.5rem; justify-content: flex-start; width: 100%; }
    .fm__side-btn .ico, .fm__bar .modal__button .ico { width: 1.05em; height: 1.05em; }
    .fm__main { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; }
    .fm__bar { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; padding: 0.6rem 0.8rem; border-bottom: 1px solid var(--border-color); }
    .fm__title { display: flex; flex-direction: column; margin-right: auto; min-width: 12rem; }
    .fm__title-name { font-weight: 700; font-size: 1rem; }
    .fm__title-path { font-size: 0.68rem; color: var(--secondary-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 34rem; }
    .fm__search { width: 14rem; max-width: 40vw; }
    .fm__bar .modal__button { display: inline-flex; align-items: center; gap: 0.4rem; }
    .fm__current { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 0.8rem; padding: 0.5rem 0.8rem; border-bottom: 1px solid var(--border-color); background: var(--dialog-header-bg); }
    .fm__current[hidden] { display: none; }
    .fm__current-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--secondary-text); }
    .fm__current-name { font-weight: 700; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .fm__current-state { font-size: 0.78rem; color: var(--ok, #3fb950); }
    .fm__current--dirty .fm__current-state { color: var(--warn, #f0b429); }
    .fm__current-info { font-size: 0.78rem; color: var(--secondary-text); flex: 1 1 18rem; }
    .fm__current-acts { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-left: auto; }
    .fm__current-acts .modal__button { display: inline-flex; align-items: center; gap: 0.4rem; }
    .fm__current-acts .ico { width: 1.05em; height: 1.05em; }
    .fm__head, .fm__row { display: grid; grid-template-columns: 2rem minmax(10rem, 1fr) 12rem 6rem 10rem 11.5rem; align-items: center; gap: 0.4rem; padding: 0 0.8rem; }
    .fm__head { padding-top: 0.35rem; padding-bottom: 0.35rem; border-bottom: 1px solid var(--border-color); font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--secondary-text); }
    .fm__head button { background: transparent; border: 0; color: inherit; font: inherit; text-transform: inherit; letter-spacing: inherit; text-align: left; cursor: pointer; padding: 0.2rem 0; }
    .fm__head button:hover { color: var(--text-main); }
    .fm__list { flex: 1 1 auto; min-height: 0; overflow: auto; }
    .fm__row { min-height: 2.9rem; border-bottom: 1px solid var(--border-color); }
    .fm__row:hover { background: rgba(255, 255, 255, 0.03); }
    .fm__row--selected { background: var(--accent-soft, rgba(255, 176, 0, 0.14)); }
    .fm__row--active .fm__name { color: var(--accent-color, #ffb000); }
    .fm__name { display: flex; align-items: center; gap: 0.4rem; min-width: 0; font-weight: 600; }
    .fm__name-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .fm__file { font-size: 0.66rem; font-weight: 400; color: var(--secondary-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .fm__cell { font-size: 0.78rem; color: var(--secondary-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-variant-numeric: tabular-nums; }
    .fm__badge { flex: 0 0 auto; font-size: 0.62rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; padding: 0.1rem 0.4rem; border-radius: 99px; border: 1px solid var(--border-color); color: var(--secondary-text); }
    .fm__badge--active { color: var(--ok, #3fb950); border-color: var(--ok, #3fb950); }
    .fm__swatches { display: inline-flex; flex: 0 0 auto; border: 1px solid var(--border-color); border-radius: 99px; overflow: hidden; }
    .fm__swatch { width: 0.9rem; height: 0.9rem; }
    .fm__badge--warn { color: var(--warn, #f0b429); border-color: var(--warn, #f0b429); }
    .fm__badge--error { color: var(--error, #e5484d); border-color: var(--error, #e5484d); }
    .fm__acts { display: flex; justify-content: flex-end; gap: 0.1rem; }
    .fm__act { display: inline-flex; align-items: center; justify-content: center; width: 2.3rem; height: 2.3rem; background: transparent; border: 1px solid transparent; border-radius: var(--base-radius, 3px); color: var(--secondary-text); cursor: pointer; }
    .fm__act:hover { border-color: var(--border-color); color: var(--text-main); }
    .fm__act--danger:hover { color: var(--error, #e5484d); }
    .fm__act--on { color: var(--accent-color, #ffb000); }
    .fm__act .ico { width: 1.05em; height: 1.05em; }
    .fm__empty { padding: 2.5rem 1rem; text-align: center; color: var(--secondary-text); }
    .fm__foot { display: flex; align-items: center; gap: 0.6rem; padding: 0.5rem 0.8rem; border-top: 1px solid var(--border-color); min-height: 3.2rem; }
    .fm__foot-info { margin-right: auto; font-size: 0.78rem; color: var(--secondary-text); }
    .fm__foot .modal__button { display: inline-flex; align-items: center; gap: 0.4rem; }
    .fm__foot .ico { width: 1.05em; height: 1.05em; }
    .fm__dropzone { outline: 2px dashed var(--accent-color, #ffb000); outline-offset: -6px; }
    .modal--fmexport { width: min(38rem, 94vw); display: flex; flex-direction: column; max-height: min(52rem, 94vh); }
    .modal--fmexport .modal__body { flex: 1 1 auto; min-height: 0; overflow: auto; }
    .fmx__intro { margin: 0 0 0.7rem; font-size: 0.82rem; color: var(--secondary-text); }
    .fmx__cat { border-bottom: 1px solid var(--border-color); }
    .fmx__head { display: flex; gap: 0.6rem; align-items: center; padding: 0.55rem 0.2rem; }
    .fmx__expand { flex: 0 0 auto; width: 2rem; height: 2rem; display: inline-flex; align-items: center; justify-content: center; background: transparent; border: 1px solid transparent; border-radius: var(--base-radius, 3px); color: var(--secondary-text); cursor: pointer; }
    .fmx__expand:hover:not(:disabled) { border-color: var(--border-color); color: var(--text-main); }
    .fmx__expand:disabled { opacity: 0.25; cursor: default; }
    .fmx__expand .ico { width: 1em; height: 1em; transition: transform 0.15s; }
    .fmx__expand--open .ico { transform: rotate(90deg); }
    .fmx__items { margin: 0 0 0.5rem 2.6rem; border-left: 2px solid var(--border-color); max-height: 14rem; overflow: auto; }
    .fmx__row { display: flex; gap: 0.8rem; align-items: center; padding: 0.35rem 0.6rem; cursor: pointer; }
    .fmx__row:hover { background: rgba(255, 255, 255, 0.03); }
    .fmx__row-name { font-size: 0.85rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .fmx__item { display: flex; gap: 0.8rem; align-items: center; padding: 0.55rem 0.2rem; border-bottom: 1px solid var(--border-color); cursor: pointer; }
    .fmx__text { flex: 1 1 auto; min-width: 0; }
    .fmx__switch { position: relative; flex: 0 0 auto; width: 2.6rem; height: 1.45rem; margin: 0; appearance: none; -webkit-appearance: none; border-radius: 99px; border: 1px solid var(--border-color); background: var(--dialog-header-bg); cursor: pointer; transition: background 0.15s, border-color 0.15s; }
    .fmx__switch::after { content: ""; position: absolute; top: 50%; left: 0.18rem; width: 1rem; height: 1rem; border-radius: 50%; background: var(--secondary-text); transform: translateY(-50%); transition: left 0.15s, background 0.15s; }
    .fmx__switch:checked { background: var(--accent-soft, rgba(255, 176, 0, 0.25)); border-color: var(--accent-color, #ffb000); }
    .fmx__switch:checked::after { left: calc(100% - 1.18rem); background: var(--accent-color, #ffb000); }
    .fmx__switch:disabled { cursor: default; }
    .fmx__item-name { font-weight: 600; }
    .fmx__item-detail { font-size: 0.74rem; color: var(--secondary-text); }
    .fmx__item--off { opacity: 0.5; }
    .fmx__note { margin-top: 0.7rem; font-size: 0.74rem; color: var(--secondary-text); }
    .fmx__note--warn { color: var(--warn, #f0b429); }
    @media (max-width: 760px) { .modal--files .modal__body { flex-direction: column; } .fm__side { flex: 0 0 auto; flex-direction: row; flex-wrap: wrap; border-right: 0; border-bottom: 1px solid var(--border-color); }
      .fm__head, .fm__row { grid-template-columns: 2rem minmax(8rem, 1fr) 11.5rem; } .fm__head > :nth-child(3), .fm__head > :nth-child(4), .fm__head > :nth-child(5), .fm__row > :nth-child(3), .fm__row > :nth-child(4), .fm__row > :nth-child(5) { display: none; } }
  `;
  document.head.appendChild(style);

  // ------------------------------------------------------------------------------------------ Hilfen
  async function call(method, url, body, raw) {
    try {
      const options = { method, headers: {} };
      if (raw !== undefined) { options.body = raw; options.headers["Content-Type"] = "application/octet-stream"; }
      else if (body !== undefined) { options.body = JSON.stringify(body); options.headers["Content-Type"] = "application/json"; }
      const res = await fetch(url, options);
      return { ok: res.ok, status: res.status, data: await res.json().catch(() => ({})) };
    } catch (err) {
      return { ok: false, status: 0, data: { error: "network" } };
    }
  }
  const fmtSize = (bytes) => {
    if (!bytes) return "–";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(bytes < 10240 ? 1 : 0) + " KB";
    if (bytes < 1024 * 1024 * 1024) return (bytes / 1048576).toFixed(bytes < 10485760 ? 1 : 0) + " MB";
    return (bytes / 1073741824).toFixed(1) + " GB";
  };
  const fmtDate = (seconds) => (seconds ? new Date(seconds * 1000).toLocaleString([], { dateStyle: "short", timeStyle: "short" }) : "–");
  const stem = (filename) => String(filename || "").replace(/\.[^.]+$/, "");
  const toast = (text, type) => _showToast(text, type || "success", type === "error" ? 5000 : 3000);
  function failToast(result, fallbackKey) {
    const data = result && result.data ? result.data : {};
    toast(data.message || t(fallbackKey || "FM_ERR_GENERIC"), "error");
  }
  const confirmBox = (title, body, confirmKey) => _askLayoutConfirm({ title, body, confirmKey });

  // ------------------------------------------------------------------------------------------ Laden
  async function load(kind, keepSelection) {
    const mine = ++seq;
    state.loading = true;
    const result = await call("GET", "/api/files/" + kind);
    if (mine !== seq) return;
    state.loading = false;
    if (!result.ok) { state.rows = []; state.path = ""; failToast(result); render(); return; }
    state.rows = result.data.rows || [];
    state.path = result.data.path || "";
    state.counts[kind] = state.rows.length;
    if (!keepSelection) state.selected.clear();
    else for (const id of [...state.selected]) if (!state.rows.some((r) => r.id === id)) state.selected.delete(id);
    render();
  }
  async function loadCounts() {
    await Promise.all(KINDS.map(async (kind) => {
      if (kind === state.kind) return;
      const result = await call("GET", "/api/files/" + kind);
      if (result.ok) state.counts[kind] = (result.data.rows || []).length;
    }));
    renderSide();
  }
  function reload() { return load(state.kind, true).then(loadCounts); }
  function selectKind(kind) {
    state.kind = kind;
    state.query = "";
    state.selected.clear();
    state.sort = { key: kind === "shows" ? "modified" : "name", dir: kind === "shows" ? -1 : 1 };
    state.rows = [];
    render();
    load(kind);
  }

  // ------------------------------------------------------------------------------------------ Download
  function downloadUrl(kind, ids) {
    const params = new URLSearchParams({ kind });
    for (const id of ids || []) params.append("id", id);
    return "/api/files/download?" + params.toString();
  }
  /** Im Programmfenster: der Server oeffnet den Standard-Browser; sonst laedt dieser Browser selbst (Adresse mit Sitzung/Cookie). */
  async function startDownload(url) {
    const result = await call("POST", "/api/files/open-download", { url });
    if (result.ok && result.data.opened) { toast(t("FM_DL_STARTED")); return; }
    const link = el("a");
    link.href = url;
    link.download = "";
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  // ------------------------------------------------------------------------------------------ Aktionen je Art
  function openRow(row) {
    if (state.kind === "shows") {
      _guardUnsavedChanges(() => { client.send("load_show", { path: row.path }); Modal.close(MODAL); toast(t("FM_OPENED", { name: row.name })); });
    } else if (state.kind === "layouts") {
      _loadLayoutByFilename(row.id, row.name).then(() => { toast(t("FM_OPENED", { name: row.name })); reload(); });
    } else if (state.kind === "themes") {
      client.send("set_theme", row.theme);                                  // anwenden und speichern wie ein Klick auf ein Profil in den Einstellungen
      toast(t("FM_OPENED", { name: rowName(row) }));
    } else if (state.kind === "stages") {
      (async () => {
        const dirty = window.OCSimStages && window.OCSimStages.current && window.OCSimStages.current.dirty;
        if (dirty && !(await confirmBox(t("SIMSTAGE_REPLACE_TITLE"), t("SIMSTAGE_REPLACE_BODY", { name: window.OCSimStages.current.name }), "SIMSTAGE_REPLACE_CONFIRM"))) return;
        const result = await call("POST", "/api/sim-stage/load", { filename: row.id });
        if (!result.ok) { failToast(result); return; }
        toast(t("FM_OPENED", { name: row.name }));
        reload();
      })();
    }
  }
  /** Umbenennen. Ein Name, den es schon gibt, wird nie uebernommen (kein Ueberschreiben): der Dialog fragt mit Hinweis erneut. */
  async function renameRow(row) {
    if (row.builtin) return;
    const current = state.kind === "effects" ? stem(row.id) : row.name;
    let value = current;
    let note = "";
    for (;;) {
      const name = await _askLayoutName({ title: t("FM_RENAME_TITLE"), confirmKey: "FM_RENAME_CONFIRM", value, labelKey: "FM_NAME_LABEL", note });
      if (!name || name === current) return;
      const taken = state.rows.some((r) => r.id !== row.id && (r.name.toLowerCase() === name.toLowerCase() || (r.name_key && t(r.name_key).toLowerCase() === name.toLowerCase())));
      let result = null;
      if (!taken) {
        if (state.kind === "shows") result = await call("POST", "/api/showfiles/rename", { path: row.path, new_name: name });
        else if (state.kind === "layouts") result = await call("POST", "/api/layouts/rename", { filename: row.id, new_name: name });
        else if (state.kind === "stages") result = await call("POST", "/api/sim-stage/rename", { filename: row.id, new_name: name });
        else if (state.kind === "themes") { client.send("rename_theme_profile", { name: row.name, new_name: name }); result = { ok: true, data: {} }; }
        else result = await call("POST", "/api/files/effects/rename", { id: row.id, new_name: name });
      }
      if (result && result.ok) {
        toast(t("FM_RENAMED", { name }));
        if (state.kind === "shows") _refreshShowfileStatus(true);           // war es die geladene Show: Name in der Menueleiste
        if (state.kind === "layouts" && result.data.filename) {            // dieses Geraet merkt sich sein Layout ueber den Dateinamen
          let remembered = null;
          try { remembered = localStorage.getItem(DEVICE_LAYOUT_KEY); } catch (error) { /* privates Fenster */ }
          if (remembered === row.id) _rememberDeviceLayout(result.data.filename);
          _refreshLayoutStatus();
          _refreshLayoutsSubmenu();
        }
        reload();
        return;
      }
      if (taken || (result.status === 409 && result.data.error !== "in_use")) { value = name; note = t("FM_NAME_TAKEN", { name }); continue; }
      failToast(result, result.data && result.data.error === "in_use" ? "FM_ERR_IN_USE" : "FM_ERR_GENERIC");
      return;
    }
  }
  async function duplicateRow(row) {
    let result;
    if (state.kind === "shows") result = await call("POST", "/api/showfiles/duplicate", { path: row.path });
    else if (state.kind === "layouts") result = await call("POST", "/api/layouts/duplicate", { filename: row.id });
    else if (state.kind === "stages") result = await call("POST", "/api/sim-stage/duplicate", { filename: row.id });
    else if (state.kind === "themes") {
      if (row.builtin) {                                                     // eingebaut: als eigenes Profil anlegen (freier Name "<Name> 2", "<Name> 3" ...)
        let copy = `${rowName(row)} 2`;
        for (let n = 3; state.rows.some((r) => r.name.toLowerCase() === copy.toLowerCase()); n++) copy = `${rowName(row)} ${n}`;
        client.send("save_theme_profile", { name: copy, theme: row.theme });
        toast(t("FM_DUPLICATED", { name: copy }));
      } else {
        client.send("duplicate_theme_profile", { name: row.name });
        toast(t("FM_DUPLICATED", { name: row.name }));
      }
      setTimeout(reload, 300);                                              // die Antwort kommt als theme_profiles_changed; changed() frischt die Liste ebenfalls auf
      return;
    }
    else result = await call("POST", "/api/files/effects/duplicate", { id: row.id });
    if (!result.ok) { failToast(result); return; }
    toast(t("FM_DUPLICATED", { name: result.data.name || row.name }));
    reload();
  }
  async function deleteOne(row) {
    if (state.kind === "shows") return call("POST", "/api/showfiles/delete", { path: row.path });
    if (state.kind === "layouts") return { ok: await _deleteLayoutAndSwitch(row.id), data: {} };         // war es das geladene, wechselt die Oberflaeche auf ein anderes
    if (state.kind === "stages") return call("POST", "/api/sim-stage/delete", { filename: row.id });
    if (state.kind === "themes") { client.send("delete_theme_profile", { name: row.name }); return { ok: true, data: {} }; }
    if (state.kind === "effects") return call("DELETE", "/api/effects/" + encodeURIComponent(stem(row.id)));
    return call("DELETE", "/api/library/installed/" + encodeURIComponent(stem(row.id)));
  }
  async function deleteRows(rows) {
    rows = rows.filter((r) => !r.builtin);                                  // eingebaute Farbprofile lassen sich nicht loeschen
    if (!rows.length) return;
    let body = rows.length === 1
      ? t(state.kind === "fixtures" ? "FM_DELETE_FIXTURE_BODY" : "FM_DELETE_BODY", { name: rows[0].name })
      : t("FM_DELETE_MANY_BODY", { n: rows.length });
    if (state.kind === "shows" && rows.some((r) => r.active)) body += " " + t("SHOWFILE_DELETE_LOADED_NOTE");
    if (!(await confirmBox(t("FM_DELETE_TITLE"), body, "FM_DELETE_CONFIRM"))) return;
    let failed = 0;
    let freedMedia = 0;
    for (const row of rows) {
      const result = await deleteOne(row);
      if (!result.ok) { failed++; failToast(result); }
      else if (result.data && result.data.media_deleted) freedMedia += result.data.media_deleted;
    }
    if (freedMedia) toast(t("SHOWFILE_MEDIA_DELETED", { n: freedMedia }));
    if (state.kind === "shows") _refreshShowfileStatus(true);
    if (failed < rows.length) toast(t("FM_DELETED", { n: rows.length - failed }));
    state.selected.clear();
    reload();
  }
  async function toggleFavorite(row) {
    await call("POST", state.kind === "effects" ? "/api/files/effects/favorite" : "/api/layouts/favorite", state.kind === "effects" ? { id: row.id } : { filename: row.id });
    reload();
  }

  // ------------------------------------------------------------------------------------------ Upload
  async function uploadOne(kind, file, relativeName) {
    const name = relativeName || file.name;
    const result = await call("POST", "/api/files/" + kind + "/upload?filename=" + encodeURIComponent(file.name), undefined, await file.arrayBuffer());
    if (!result.ok) { toast(t("FM_UPLOAD_FAILED", { name, message: (result.data && result.data.message) || t("FM_ERR_GENERIC") }), "error"); return { failed: true }; }
    return { ok: true, data: result.data };
  }
  function importSummary(data) {
    const parts = [];
    for (const [kind, n] of Object.entries(data.imported || {})) parts.push(`${n} ${kindLabel(kind)}`);
    const skipped = Object.values(data.skipped || {}).reduce((a, b) => a + b, 0);
    let text = parts.length ? t("FM_IMPORT_DONE", { summary: parts.join(", ") }) : t("FM_IMPORT_NOTHING");
    if (skipped) text += " – " + t("FM_IMPORT_SKIPPED", { n: skipped });
    if ((data.copies || []).length) text += " – " + t("FM_IMPORT_COPIES", { list: data.copies.map((c) => `${c.from} → ${c.to}`).join(", ") });
    if ((data.errors || []).length) text += " – " + t("FM_IMPORT_ERRORS", { n: data.errors.length });
    return text;
  }
  /** Meldung zu einer einzelnen hochgeladenen Datei: neu, schon vorhanden (gleicher Inhalt) oder als Kopie unter freiem Namen. */
  function singleSummary(file, data) {
    if (data.status === "identical") return t("FM_UPLOAD_IDENTICAL", { name: data.name || file.name });
    if (data.status === "copy") return t("FM_UPLOAD_COPY", { name: data.original, copy: data.name });
    return t("FM_UPLOADED", { name: data.name || file.name });
  }
  function kindLabel(kind) {
    return KIND_UI[kind] ? t(KIND_UI[kind].label) : kind === "media" ? t("FM_KIND_MEDIA") : kind === "streams" ? t("FM_KIND_STREAMS") : kind;
  }
  async function uploadFiles(files, fromFolder) {
    const wanted = [...files].filter((f) => {
      const lower = f.name.toLowerCase();
      return lower.endsWith(".zip") || lower.endsWith(EXT[state.kind]);
    });
    if (!wanted.length) { toast(t("FM_UPLOAD_NONE", { ext: EXT[state.kind] }), "error"); return; }
    let ok = 0, skipped = 0, failed = 0;
    for (const file of wanted) {
      const result = await uploadOne(state.kind, file, fromFolder && file.webkitRelativePath ? file.webkitRelativePath : file.name);
      if (!result.ok) { failed++; continue; }
      if (result.data.status === "identical") skipped++; else ok++;
      if (result.data.imported) toast(importSummary(result.data));
      else if (wanted.length === 1 && !fromFolder) toast(singleSummary(file, result.data));
    }
    if (wanted.length > 1 || fromFolder) toast(t("FM_UPLOAD_DONE", { ok, skipped, failed }), failed ? "error" : "success");
    reload();
  }

  // ------------------------------------------------------------------------------------------ Show importieren (JSON oder Export-Paket als ZIP)
  /** Waehlt eine Show-Datei (.json) oder ein Export-Paket (.zip), liest sie ein und bietet an, die Show zu oeffnen. */
  function importShow() {
    if (typeof _closeAllMenus === "function") _closeAllMenus();
    let input = document.getElementById("fm-import-input");
    if (!input) {
      input = el("input");
      input.type = "file";
      input.id = "fm-import-input";
      input.accept = ".json,.zip,application/json,application/zip";
      input.hidden = true;
      document.body.appendChild(input);
    }
    input.value = "";
    input.onchange = async () => {
      const file = input.files && input.files[0];
      input.value = "";
      if (!file) return;
      const result = await uploadOne("shows", file);
      if (!result.ok) return;
      const data = result.data;
      toast(data.imported || data.skipped ? importSummary(data) : singleSummary(file, data));
      const showId = data.imported ? data.show : data.id;
      if (!Modal.isOpen(MODAL)) open("shows"); else selectKind("shows");
      if (!showId) return;
      await waitForRows();
      const row = state.rows.find((r) => r.id === showId);
      if (row && await confirmBox(t("FM_IMPORTED_TITLE"), t("FM_IMPORTED_OPEN", { name: row.name }), "FM_OPEN")) openRow(row);
    };
    input.click();
  }
  function waitForRows() {
    return new Promise((resolve) => { const started = Date.now(); const timer = setInterval(() => { if (!state.loading || Date.now() - started > 4000) { clearInterval(timer); setTimeout(resolve, 50); } }, 60); });
  }

  // ------------------------------------------------------------------------------------------ Geladener Stand der Art (Name, ungespeichert, Neu/Speichern/Speichern unter)
  function currentInfo() {
    const kind = state.kind;
    const stateText = (named, dirty) => (dirty ? "\u25CF " + t("LAYOUT_DIRTY") : named ? "\u2713 " + t("LAYOUT_CLEAN") : "");
    if (kind === "shows") {
      const name = client.state && client.state.showfile_name;
      const named = !!name && name !== "Untitled";
      return { name: named ? name : t("SHOWFILE_UNTITLED"), dirty: !!_isDirty, text: stateText(named, !!_isDirty) };
    }
    if (kind === "layouts") {
      const named = !!_layoutState.name;
      return { name: named ? _layoutState.name : t("LAYOUT_NONE"), dirty: !!_layoutState.dirty, text: stateText(named, !!_layoutState.dirty) };
    }
    if (kind === "stages") {
      const c = window.OCSimStages && window.OCSimStages.current;
      const named = !!(c && c.filename);
      return { name: c && c.name ? c.name : "\u2013", dirty: !!(c && c.dirty), text: stateText(named, !!(c && c.dirty)) };
    }
    if (kind === "themes") {
      const active = state.rows.find((r) => r.active);
      return { name: active ? rowName(active) : t("THEME_BASE_CUSTOM"), dirty: false, text: active ? "\u2713 " + t("FM_THEME_APPLIED") : t("FM_THEME_UNSAVED") };
    }
    return null;
  }
  const CURRENT_ACTIONS = {
    shows: {
      create: () => _guardUnsavedChanges(() => Modal.open("new-show-confirm")),
      save: () => _saveShowDirect(),
      saveAs: () => _openSaveAsModal(),
    },
    layouts: {
      create: () => _layoutNewFlow(),
      save: () => _saveLayoutDirect(),
      saveAs: () => _saveLayoutWithPrompt(),
    },
    stages: {
      create: () => window.OCSimStages.newStage(),
      save: () => window.OCSimStages.save(false),
      saveAs: () => window.OCSimStages.save(true),
    },
    themes: {                                    // nur "Speichern unter": das aktive Design als Farbprofil (Datei) ablegen
      saveAs: async () => {
        let value = "";
        let note = "";
        for (;;) {
          const name = await _askLayoutName({ title: t("FM_THEME_SAVE_TITLE"), confirmKey: "FM_SAVE", value, labelKey: "FM_NAME_LABEL", note });
          if (!name) return;
          if (state.rows.some((r) => r.name.toLowerCase() === name.toLowerCase() || (r.name_key && t(r.name_key).toLowerCase() === name.toLowerCase()))) { value = name; note = t("FM_NAME_TAKEN", { name }); continue; }
          client.send("save_theme_profile", { name, theme: client.state && client.state.theme });
          toast(t("FM_THEME_SAVED", { name }));
          setTimeout(reload, 300);
          return;
        }
      },
    },
  };
  function renderCurrent() {
    const box = document.getElementById("fm-current");
    if (!box) return;
    box.textContent = "";
    const kind = state.kind;
    if (kind === "fixtures") {
      box.hidden = false;
      box.classList.remove("fm__current--dirty");
      const open = el("button", "modal__button");
      open.type = "button";
      open.id = "fm-open-fixlib";
      open.dataset.action = "fixture-library";         // die Scheinwerferbibliothek reagiert selbst auf dieses Attribut
      open.append(Icons.svg("fixture"), el("span", "", t("FM_OPEN_FIXLIB")));
      const acts = el("div", "fm__current-acts");
      acts.appendChild(open);
      box.append(el("span", "fm__current-info", t("FM_FIXLIB_INFO")), acts);
      return;
    }
    if (kind === "effects") {
      box.hidden = false;
      box.classList.remove("fm__current--dirty");
      const restore = el("button", "modal__button");
      restore.type = "button";
      restore.id = "fm-restore-fx";
      restore.append(Icons.svg("refresh"), el("span", "", t("FM_RESTORE_FX")));
      restore.addEventListener("click", restoreDefaultEffects);
      const acts = el("div", "fm__current-acts");
      acts.appendChild(restore);
      box.append(el("span", "fm__current-info", t("FM_RESTORE_FX_INFO")), acts);
      return;
    }
    const info = currentInfo();
    box.hidden = !info;
    if (!info) return;
    box.classList.toggle("fm__current--dirty", info.dirty);
    const actions = CURRENT_ACTIONS[kind];
    const button = (id, icon, key, handler, primary) => {
      const b = el("button", "modal__button" + (primary ? " modal__button--primary" : ""));
      b.type = "button";
      b.id = id;
      b.append(Icons.svg(icon), el("span", "", t(key)));
      b.addEventListener("click", handler);
      return b;
    };
    const acts = el("div", "fm__current-acts");
    if (actions.create) acts.appendChild(button("fm-cur-new", "plus", "FM_NEW", actions.create));
    if (actions.save) acts.appendChild(button("fm-cur-save", "save", "FM_SAVE", actions.save, info.dirty));
    acts.appendChild(button("fm-cur-saveas", "copy", "FM_SAVE_AS", actions.saveAs));
    const name = el("span", "fm__current-name", info.name);
    name.id = "fm-cur-name";
    const stateEl = el("span", "fm__current-state", info.text);
    stateEl.id = "fm-cur-state";
    box.append(el("span", "fm__current-label", t("FM_CURRENT")), name, stateEl, acts);
  }
  /** Mitgelieferte Effekte, die fehlen, wieder anlegen; vorhandene (auch geaenderte) bleiben unveraendert. */
  async function restoreDefaultEffects() {
    const result = await call("POST", "/api/files/effects/restore-defaults");
    if (!result.ok) { failToast(result); return; }
    const { restored = [], modified = [] } = result.data;
    if (restored.length) toast(t("FM_RESTORED", { n: restored.length, list: restored.join(", ") }));
    else toast(t("FM_RESTORE_NONE"));
    if (modified.length) toast(t("FM_RESTORE_MODIFIED", { n: modified.length, list: modified.join(", ") }));
    reload();
  }
  let changeTimer = 0;
  /** app.js/sim3d_stages.js: geladener Stand oder Dateien dieser Art haben sich geaendert - offener Dialog frischt Kopfzeile und Liste auf. */
  function changed(kind) {
    if (!built || !Modal.isOpen(MODAL)) return;
    renderCurrent();
    if (kind && kind !== state.kind) return;
    clearTimeout(changeTimer);
    changeTimer = setTimeout(() => { if (Modal.isOpen(MODAL)) load(state.kind, true).then(loadCounts); }, 200);
  }

  // ------------------------------------------------------------------------------------------ Darstellung
  function visibleRows() {
    const q = state.query.trim().toLowerCase();
    let rows = state.rows.filter((r) => !q || r.name.toLowerCase().includes(q) || r.id.toLowerCase().includes(q));
    const { key, dir } = state.sort;
    rows = rows.slice().sort((a, b) => {
      if (!!a.builtin !== !!b.builtin) return a.builtin ? -1 : 1;           // eingebaute Farbprofile bleiben oben
      let x = a[key], y = b[key];
      if (typeof x === "string" || typeof y === "string") return dir * String(x ?? "").localeCompare(String(y ?? ""), undefined, { sensitivity: "base", numeric: true });
      return dir * ((x ?? 0) - (y ?? 0));
    });
    return rows;
  }
  function detailText(row) {
    const kind = state.kind;
    if (kind === "layouts") return t("FM_PANELS", { n: row.detail });
    if (kind === "stages") return t("FM_OBJECTS", { n: row.detail });
    if (kind === "themes") return t(row.detail === "light" ? "THEME_BASE_LIGHT" : "THEME_BASE_DARK");
    if (kind === "fixtures") { const [category, modes] = String(row.detail).split(" · "); return `${category} · ${t("FM_MODES", { n: modes })}`; }
    return row.detail || "";
  }
  function badges(row) {
    const out = [];
    const add = (text, cls) => out.push(el("span", "fm__badge" + (cls ? " fm__badge--" + cls : ""), text));
    if (state.kind === "shows" && row.active) add(row.dirty ? t("FM_BADGE_DIRTY") : t("FM_BADGE_LOADED"), row.dirty ? "warn" : "active");
    else if ((state.kind === "layouts" || state.kind === "stages") && row.active) add(t("FM_BADGE_ACTIVE"), "active");
    if (state.kind === "themes") {
      const swatches = el("span", "fm__swatches");
      swatches.title = rowName(row);
      for (const color of themeSwatches(row.theme)) { const dot = el("span", "fm__swatch"); dot.style.background = color; swatches.appendChild(dot); }
      out.push(swatches);
      if (row.builtin) add(t("THEME_PROFILE_BUILTIN"));
      if (row.active) add(t("FM_BADGE_ACTIVE"), "active");
    }
    if (state.kind === "effects" && row.default) add(t("FXS_BADGE_DEFAULT"));
    if (state.kind === "effects" && row.in_use) add(t("FM_BADGE_IN_USE", { n: row.in_use }), "active");
    if (state.kind === "fixtures" && row.in_use) add(t("FM_BADGE_IN_USE", { n: row.in_use }), "active");
    if ((state.kind === "effects" && row.ok === false) || (state.kind === "fixtures" && row.error)) add(t("FM_BADGE_ERROR"), "error");
    return out;
  }
  function actionButton(icon, tipKey, handler, extra) {
    const b = el("button", "fm__act" + (extra ? " " + extra : ""));
    b.type = "button";
    b.title = t(tipKey);
    b.setAttribute("aria-label", t(tipKey));
    b.appendChild(Icons.svg(icon));
    b.addEventListener("click", (e) => { e.stopPropagation(); handler(); });
    return b;
  }
  function renderSide() {
    const side = document.getElementById("fm-side");
    if (!side) return;
    side.textContent = "";
    for (const kind of KINDS) {
      const ui = KIND_UI[kind];
      const button = el("button", "fm__kind" + (kind === state.kind ? " fm__kind--active" : ""));
      button.type = "button";
      button.dataset.kind = kind;
      button.append(Icons.svg(ui.icon), el("span", "fm__kind-name", t(ui.label)), el("span", "fm__kind-count", state.counts[kind] === undefined ? "" : String(state.counts[kind])));
      button.title = t(ui.hint);
      button.addEventListener("click", () => selectKind(kind));
      side.appendChild(button);
    }
    side.appendChild(el("div", "fm__side-sep"));
    const exportButton = el("button", "modal__button fm__side-btn");
    exportButton.type = "button";
    exportButton.id = "fm-export-open";
    exportButton.append(Icons.svg("upload"), el("span", "", t("FM_EXPORT_SHOW")));
    exportButton.title = t("FM_EXPORT_SHOW_TIP");
    exportButton.addEventListener("click", openExport);
    const importButton = el("button", "modal__button fm__side-btn");
    importButton.type = "button";
    importButton.id = "fm-import-open";
    importButton.append(Icons.svg("download"), el("span", "", t("FM_IMPORT_SHOW")));
    importButton.title = t("FM_IMPORT_SHOW_TIP");
    importButton.addEventListener("click", importShow);
    const backup = el("button", "modal__button fm__side-btn");
    backup.type = "button";
    backup.id = "fm-backup";
    backup.append(Icons.svg("download"), el("span", "", t("FM_BACKUP")));
    backup.title = t("FM_BACKUP_TIP");
    backup.addEventListener("click", () => startDownload("/api/files/download?kinds=" + KINDS.join(",")));
    side.append(importButton, exportButton, backup);
  }
  function renderHead() {
    const head = document.getElementById("fm-head");
    head.textContent = "";
    const all = el("input");
    all.type = "checkbox";
    all.id = "fm-select-all";
    all.title = t("FM_SELECT_ALL");
    const rows = visibleRows();
    all.checked = rows.length > 0 && rows.every((r) => state.selected.has(r.id));
    all.addEventListener("change", () => { for (const r of visibleRows()) { if (all.checked) state.selected.add(r.id); else state.selected.delete(r.id); } renderList(); renderFoot(); });
    head.appendChild(all);
    const column = (key, labelKey) => {
      const b = el("button", "", t(labelKey) + (state.sort.key === key ? (state.sort.dir > 0 ? " ▲" : " ▼") : ""));
      b.type = "button";
      b.dataset.sort = key;
      b.addEventListener("click", () => { state.sort = { key, dir: state.sort.key === key ? -state.sort.dir : 1 }; renderHead(); renderList(); });
      return b;
    };
    head.append(column("name", "FM_COL_NAME"), column("detail", KIND_UI[state.kind].detail), column("size", "FM_COL_SIZE"), column("modified", "FM_COL_MODIFIED"), el("span"));
  }
  function renderList() {
    const list = document.getElementById("fm-list");
    list.textContent = "";
    const rows = visibleRows();
    if (!rows.length) { list.appendChild(el("div", "fm__empty", state.loading ? t("FM_LOADING") : state.query ? t("FM_NO_MATCH") : t("FM_EMPTY"))); return; }
    for (const row of rows) {
      const node = el("div", "fm__row" + (state.selected.has(row.id) ? " fm__row--selected" : "") + (row.active ? " fm__row--active" : ""));
      node.dataset.id = row.id;
      const check = el("input");
      check.type = "checkbox";
      check.disabled = !!row.builtin;                                     // eingebaute Farbprofile: nichts auszuwaehlen (kein Loeschen/Herunterladen)
      check.checked = state.selected.has(row.id);
      check.addEventListener("change", () => { if (check.checked) state.selected.add(row.id); else state.selected.delete(row.id); node.classList.toggle("fm__row--selected", check.checked); renderFoot(); renderHead(); });
      const name = el("div", "fm__name");
      const text = el("span", "fm__name-text", rowName(row));
      const titleBox = el("div", "", "");
      titleBox.style.cssText = "display:flex;flex-direction:column;min-width:0;";
      titleBox.append(text);
      if (!row.builtin && stem(row.id) !== row.name) titleBox.append(el("span", "fm__file", row.id));
      name.append(titleBox, ...badges(row));
      const acts = el("div", "fm__acts");
      if (state.kind === "layouts") acts.appendChild(actionButton("star", row.favorite ? "LAYOUT_UNFAVORITE" : "LAYOUT_FAVORITE", () => toggleFavorite(row), row.favorite ? "fm__act--on" : ""));
      if (state.kind === "effects") acts.appendChild(actionButton("star", row.favorite ? "FXS_UNFAVORITE" : "FXS_FAVORITE", () => toggleFavorite(row), row.favorite ? "fm__act--on" : ""));
      if (["shows", "layouts", "stages", "themes"].includes(state.kind)) acts.appendChild(actionButton("play", "FM_OPEN", () => openRow(row)));
      if (state.kind !== "fixtures" && !row.builtin) acts.appendChild(actionButton("edit", "FM_RENAME", () => renameRow(row)));
      if (state.kind !== "fixtures") acts.appendChild(actionButton("copy", "FM_DUPLICATE", () => duplicateRow(row)));
      if (!row.builtin) acts.appendChild(actionButton("download", "FM_DOWNLOAD_ONE", () => startDownload(downloadUrl(state.kind, [row.id]))));
      if (!row.builtin) acts.appendChild(actionButton("trash", "FM_DELETE", () => deleteRows([row]), "fm__act--danger"));
      node.append(check, name, el("div", "fm__cell", detailText(row)), el("div", "fm__cell", fmtSize(row.size)), el("div", "fm__cell", fmtDate(row.modified)), acts);
      if (["shows", "layouts", "stages", "themes"].includes(state.kind)) node.addEventListener("dblclick", () => openRow(row));
      list.appendChild(node);
    }
  }
  function renderFoot() {
    const info = document.getElementById("fm-foot-info");
    const n = state.selected.size;
    info.textContent = n ? t("FM_SELECTED", { n }) : t("FM_COUNT", { n: state.rows.length });
    const dl = document.getElementById("fm-dl-selected");
    const del = document.getElementById("fm-del-selected");
    dl.disabled = del.disabled = n === 0;
  }
  function render() {
    if (!built) return;
    document.getElementById("fm-title-name").textContent = t(KIND_UI[state.kind].label);
    const path = document.getElementById("fm-title-path");
    path.textContent = state.path;
    path.title = state.path;
    const search = document.getElementById("fm-search");
    search.placeholder = t("FM_SEARCH");
    if (search.value !== state.query) search.value = state.query;
    document.getElementById("fm-file-input").accept = KIND_UI[state.kind].accept;
    renderSide();
    renderCurrent();
    renderHead();
    renderList();
    renderFoot();
  }

  // ------------------------------------------------------------------------------------------ Aufbau
  function build() {
    if (built) return;
    const root = document.getElementById("fm-root");
    if (!root) return;
    root.textContent = "";
    root.classList.add("fm");
    const side = el("div", "fm__side");
    side.id = "fm-side";
    const main = el("div", "fm__main");

    const bar = el("div", "fm__bar");
    const titleBox = el("div", "fm__title");
    const titleName = el("span", "fm__title-name");
    titleName.id = "fm-title-name";
    const titlePath = el("span", "fm__title-path");
    titlePath.id = "fm-title-path";
    titleBox.append(titleName, titlePath);
    const search = el("input", "modal__input fm__search");
    search.type = "search";
    search.id = "fm-search";
    search.addEventListener("input", () => { state.query = search.value; renderHead(); renderList(); });
    const fileInput = el("input");
    fileInput.type = "file";
    fileInput.multiple = true;
    fileInput.hidden = true;
    fileInput.id = "fm-file-input";
    fileInput.addEventListener("change", () => { const files = [...fileInput.files]; fileInput.value = ""; uploadFiles(files, false); });
    const folderInput = el("input");
    folderInput.type = "file";
    folderInput.multiple = true;
    folderInput.hidden = true;
    folderInput.id = "fm-folder-input";
    folderInput.setAttribute("webkitdirectory", "");
    folderInput.addEventListener("change", () => { const files = [...folderInput.files]; folderInput.value = ""; uploadFiles(files, true); });
    const button = (id, icon, key, handler, iconOnly) => {
      const b = el("button", "modal__button");
      b.type = "button";
      b.id = id;
      b.append(Icons.svg(icon), el("span", "", iconOnly ? "" : t(key)));
      if (iconOnly) b.title = t(key);
      b.dataset.i18nKey = key;
      b.addEventListener("click", handler);
      return b;
    };
    bar.append(titleBox, search,
      button("fm-upload", "upload", "FM_UPLOAD", () => fileInput.click()),
      button("fm-upload-folder", "folder", "FM_UPLOAD_FOLDER", () => folderInput.click()),
      button("fm-dl-all", "download", "FM_DOWNLOAD_ALL", () => startDownload(downloadUrl(state.kind, []))),
      button("fm-refresh", "refresh", "FM_REFRESH", reload, true), fileInput, folderInput);
    const current = el("div", "fm__current");
    current.id = "fm-current";
    const head = el("div", "fm__head");
    head.id = "fm-head";
    const list = el("div", "fm__list");
    list.id = "fm-list";
    const foot = el("div", "fm__foot");
    const info = el("span", "fm__foot-info");
    info.id = "fm-foot-info";
    const dl = button("fm-dl-selected", "download", "FM_DOWNLOAD_SELECTED", () => startDownload(downloadUrl(state.kind, [...state.selected])));
    const del = button("fm-del-selected", "trash", "FM_DELETE_SELECTED", () => deleteRows(state.rows.filter((r) => state.selected.has(r.id))));
    foot.append(info, dl, del);
    main.append(bar, current, head, list, foot);
    root.append(side, main);
    // Dateien auf den Dialog ziehen = Upload in die gewaehlte Art
    for (const type of ["dragenter", "dragover"]) main.addEventListener(type, (e) => { if (e.dataTransfer && [...e.dataTransfer.types].includes("Files")) { e.preventDefault(); main.classList.add("fm__dropzone"); } });
    for (const type of ["dragleave", "drop"]) main.addEventListener(type, () => main.classList.remove("fm__dropzone"));
    main.addEventListener("drop", (e) => { if (e.dataTransfer && e.dataTransfer.files.length) { e.preventDefault(); uploadFiles(e.dataTransfer.files, false); } });
    built = true;
  }
  function open(kind) {
    if (typeof _closeAllMenus === "function") _closeAllMenus();
    build();
    if (kind && KINDS.includes(kind)) state.kind = kind;
    Modal.open(MODAL);
    state.query = "";
    render();
    load(state.kind).then(loadCounts);
  }

  // ------------------------------------------------------------------------------------------ Export-Dialog fuer die geladene Show
  // Jede Kategorie hat einen Hauptschalter (an = alle Eintraege, aus = keiner) und laesst sich aufklappen: dort ist jeder Eintrag einzeln waehlbar.
  let exportInfo = null;
  function exportCategories(info) {
    const media = info.media.map((m) => ({ id: m.id, name: m.name, detail: fmtSize(m.size), present: m.present }));
    return [
      { key: "fixtures", label: "FM_EXPORT_FIXTURES", param: "fixture", on: true, items: info.fixtures.map((f) => ({ id: f.id, name: f.name, detail: t("FM_EXPORT_FIXTURE_D", { n: f.count, size: fmtSize(f.size) }), present: f.present })) },
      { key: "effects", label: "FM_EXPORT_EFFECTS", param: "effect", on: true, items: info.effects.map((e) => ({ id: e.name, name: e.name, detail: "", present: e.present })) },
      { key: "stage", label: "FM_EXPORT_STAGE", param: "stage", on: true, single: info.stage ? { detail: t("FM_EXPORT_STAGE_D", { n: info.stage.objects }) } : null },
      { key: "media", label: "FM_EXPORT_MEDIA", param: "media", on: true, items: media },
      { key: "layouts", label: "FM_EXPORT_LAYOUTS", param: "layout", on: false, items: info.layouts.map((l) => ({ id: l.id, name: l.name, detail: "", present: true })) },
      { key: "streams", label: "FM_EXPORT_STREAMS", param: "stream", on: false, items: info.streams.map((x) => ({ id: x.id, name: x.name, detail: x.url, present: true })) },
    ];
  }
  function switchBox(extra) {
    const box = el("input", "fmx__switch");
    box.type = "checkbox";
    box.setAttribute("role", "switch");
    for (const [k, v] of Object.entries(extra || {})) box.dataset[k] = v;
    return box;
  }
  function buildExportCategory(cat) {
    const wrap = el("div", "fmx__cat");
    const head = el("div", "fmx__head");
    const items = cat.items || [];
    const available = cat.single ? true : items.length > 0;
    const chooseable = items.filter((i) => i.present);
    const master = switchBox({ key: cat.key });
    master.disabled = !available || (!cat.single && !chooseable.length);
    master.checked = !master.disabled && cat.on;
    const toggle = el("button", "fmx__expand");
    toggle.type = "button";
    toggle.disabled = !items.length;
    toggle.title = t("FM_EXPORT_EXPAND");
    toggle.appendChild(Icons.svg("chevron-right"));
    const text = el("div", "fmx__text");
    const summary = el("div", "fmx__item-detail");
    text.append(el("div", "fmx__item-name", t(cat.label)), summary);
    head.append(toggle, text, master);
    wrap.appendChild(head);
    const list = el("div", "fmx__items");
    list.hidden = true;
    const boxes = [];
    for (const item of items) {
      const row = el("label", "fmx__row" + (item.present ? "" : " fmx__item--off"));
      const box = switchBox({ param: cat.param, id: item.id });
      box.checked = master.checked && item.present;
      box.disabled = !item.present;
      boxes.push(box);
      const label = el("div", "fmx__text");
      label.append(el("div", "fmx__row-name", item.name), el("div", "fmx__item-detail", item.present ? item.detail : t("FM_EXPORT_MISSING")));
      row.append(label, box);
      list.appendChild(row);
      box.addEventListener("change", () => { master.checked = boxes.some((b) => b.checked); refresh(); });
    }
    const refresh = () => {
      if (cat.single) summary.textContent = cat.single ? cat.single.detail : t("FM_EXPORT_NONE");
      else if (!items.length) summary.textContent = t("FM_EXPORT_NONE");
      else summary.textContent = t("FM_EXPORT_SELECTED", { n: boxes.filter((b) => b.checked).length, m: items.length });
    };
    master.addEventListener("change", () => { boxes.forEach((b) => { if (!b.disabled) b.checked = master.checked; }); refresh(); });
    toggle.addEventListener("click", () => { list.hidden = !list.hidden; toggle.classList.toggle("fmx__expand--open", !list.hidden); });
    if (cat.single === null) summary.textContent = t("FM_EXPORT_NONE"); else refresh();
    wrap.appendChild(list);
    return wrap;
  }
  async function openExport() {
    if (typeof _closeAllMenus === "function") _closeAllMenus();
    const result = await call("GET", "/api/files/export-show/info");
    if (!result.ok) { failToast(result); return; }
    exportInfo = result.data;
    const body = document.getElementById("fm-export-body");
    body.textContent = "";
    body.appendChild(el("p", "fmx__intro", t("FM_EXPORT_INTRO", { name: exportInfo.show })));
    for (const cat of exportCategories(exportInfo)) body.appendChild(buildExportCategory(cat));
    if (exportInfo.dirty) body.appendChild(el("p", "fmx__note fmx__note--warn", t("FM_EXPORT_DIRTY")));
    Modal.open(EXPORT_MODAL);
  }
  function runExport() {
    const params = new URLSearchParams();
    document.querySelectorAll("#fm-export-body input[data-param]").forEach((box) => { if (box.checked) params.append(box.dataset.param, box.dataset.id); });
    const stage = document.querySelector('#fm-export-body input[data-key="stage"]');
    if (stage && stage.checked) params.set("stage", "1");
    Modal.close(EXPORT_MODAL);
    startDownload("/api/files/export-show?" + params.toString());
  }

  // ------------------------------------------------------------------------------------------ Anschluss
  document.addEventListener("click", (e) => {
    const opener = e.target.closest('[data-action="file-manager"]');
    if (opener) open(opener.dataset.fmKind);
    else if (e.target.closest("#fm-open-fixlib")) Modal.close(MODAL);
    else if (e.target.closest('[data-action="export-show"]')) openExport();
    else if (e.target.closest('[data-action="import-show"]')) importShow();
    else if (e.target.closest("#fm-export-go")) runExport();
  });
  document.addEventListener("keydown", (e) => {        // Toolbar-Name der Show ist ein Pseudo-Knopf (span role=button)
    if ((e.key === "Enter" || e.key === " ") && e.target.matches && e.target.matches('[role="button"][data-action="file-manager"]')) {
      e.preventDefault();
      open(e.target.dataset.fmKind);
    }
  });
  document.addEventListener("i18n-applied", () => {
    if (!built) return;
    for (const b of document.querySelectorAll("#fm-root .modal__button[data-i18n-key]")) { if (b.lastChild.textContent) b.lastChild.textContent = t(b.dataset.i18nKey); else b.title = t(b.dataset.i18nKey); }
    if (Modal.isOpen(MODAL)) render();
  });
  window.OCFileManager = { open, openExport, importShow, reload, changed, get state() { return state; } };
})();
