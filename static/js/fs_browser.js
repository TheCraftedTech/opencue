// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* OpenCue-Explorer (Dialog "fs-browser"; app/fs_browser.py, /api/fs/*): ein eigener Datei-Dialog fuer Fernzugriffs-Geraete (iPad, Handy), wo am Hauptrechner der Windows-Explorer aufgeht.
 *   OCFsBrowser.open({area, path, title})     Dateien im Datenordner ("data") bzw. Protokoll-Ordner ("logs"): oeffnen, herunterladen (Ordner als ZIP), hochladen, neuer Ordner, umbenennen, duplizieren, loeschen
 *   OCFsBrowser.pickFolder({start, title})    einen Ordner des Rechners aussuchen (nur Ordner, keine Dateien) -> Promise<Pfad | null>
 *   OCFsBrowser.reveal({realUrl, area, path, title})   am Hauptrechner: der echte Explorer (POST realUrl), sonst dieser Dialog
 */
(function () {
  "use strict";

  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    if (vars) for (const name of Object.keys(vars)) text = text.split("{" + name + "}").join(String(vars[name]));
    return text;
  };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const $ = (id) => document.getElementById(id);
  const MODAL = "fs-browser";
  const HAS_ICONS = typeof Icons !== "undefined";                      // Icons ist eine globale const (nicht an window)
  const isLocal = () => !!(typeof client !== "undefined" && client.state && client.state.is_local);

  let mode = "browse";                                  // "browse" | "pick"
  let area = "data";
  let cwd = "";                                         // browse: relativ zum Bereich; pick: absoluter Pfad ("" = Laufwerke)
  let data = null;                                      // letzte Antwort des Servers
  let busy = false;
  let pickFinish = null;

  async function api(method, url, body) {
    try {
      const res = await fetch(url, { method, headers: body === undefined ? {} : { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
      let json = {};
      try { json = await res.json(); } catch (e) { /* leer */ }
      return { ok: res.ok && json.ok !== false, data: json, status: res.status };
    } catch (e) { return { ok: false, data: { error: "network" }, status: 0 }; }
  }

  const fmtSize = (n) => {
    if (n < 1024) return n + " B";
    if (n < 1048576) return (n / 1024).toFixed(1) + " KB";
    if (n < 1073741824) return (n / 1048576).toFixed(1) + " MB";
    return (n / 1073741824).toFixed(2) + " GB";
  };
  const fmtDate = (s) => { try { return new Date(s * 1000).toLocaleString(); } catch (e) { return ""; } };
  const join = (a, b) => (a ? a + "/" : "") + b;
  const errorText = (res) => {
    const code = (res.data && res.data.error) || "";
    const key = { exists: "FS_ERR_EXISTS", bad_name: "FS_ERR_NAME", outside: "FS_ERR_OUTSIDE", bad_path: "FS_ERR_OUTSIDE", too_large: "FS_ERR_TOO_LARGE", not_found: "FS_ERR_NOT_FOUND", root: "FS_ERR_ROOT", unreadable: "FS_ERR_UNREADABLE" }[code];
    return t(key || "FS_ERR_GENERIC", { detail: (res.data && res.data.detail) || code });
  };
  const toast = (text, kind) => { if (typeof _showToast === "function") _showToast(text, kind || "info", 4000); };

  // ------------------------------------------------------------------------------------------------ Aufbau (einmal)
  function buildOnce() {
    const body = $("fs-body");
    if (!body || body.dataset.built) return;
    body.dataset.built = "1";
    const bar = el("div", "fsb__bar");
    const mk = (id, icon, key, handler) => {
      const b = el("button", "modal__button fsb__btn"); b.type = "button"; b.id = id; b.title = t(key);
      if (HAS_ICONS) b.appendChild(Icons.svg(icon));
      b.appendChild(el("span", "", t(key))); b.dataset.i18nKey = key;
      b.addEventListener("click", handler);
      return b;
    };
    bar.append(mk("fs-up", "arrow-up", "FS_UP", goUp), mk("fs-refresh", "refresh", "FS_REFRESH", () => load(cwd)),
               mk("fs-mkdir", "plus", "FS_NEW_FOLDER", newFolder), mk("fs-upload", "upload", "FS_UPLOAD", () => $("fs-file").click()),
               mk("fs-home", "folder", "FS_PICK_HOME", () => { if (data && data.home) load(data.home); }), mk("fs-data", "folder", "FS_PICK_DATA", () => { if (data && data.data) load(data.data); }));
    const file = el("input"); file.type = "file"; file.multiple = true; file.id = "fs-file"; file.hidden = true;
    file.addEventListener("change", () => { upload([...file.files]); file.value = ""; });
    const crumbs = el("div", "fsb__crumbs"); crumbs.id = "fs-crumbs";
    const note = el("p", "fsb__note"); note.id = "fs-note";
    const list = el("div", "fsb__list"); list.id = "fs-list";
    body.append(bar, file, crumbs, note, list);
    // Dateien auf den Dialog ziehen (Computer): hochladen
    list.addEventListener("dragover", (e) => { if (mode === "browse" && e.dataTransfer && [...e.dataTransfer.types].includes("Files")) { e.preventDefault(); list.classList.add("fsb__list--drop"); } });
    list.addEventListener("dragleave", () => list.classList.remove("fsb__list--drop"));
    list.addEventListener("drop", (e) => { list.classList.remove("fsb__list--drop"); if (mode === "browse" && e.dataTransfer && e.dataTransfer.files.length) { e.preventDefault(); upload([...e.dataTransfer.files]); } });
  }

  function relabel() {
    document.querySelectorAll("#fs-body [data-i18n-key]").forEach((b) => { const s = b.querySelector("span"); if (s) s.textContent = t(b.dataset.i18nKey); b.title = t(b.dataset.i18nKey); });
  }

  // ------------------------------------------------------------------------------------------------ Laden und Anzeigen
  async function load(path) {
    if (busy) return;
    busy = true;
    const res = mode === "pick"
      ? await api("GET", "/api/fs/dirs?path=" + encodeURIComponent(path || ""))
      : await api("GET", "/api/fs/list?area=" + encodeURIComponent(area) + "&path=" + encodeURIComponent(path || ""));
    busy = false;
    if (!res.ok) {
      toast(errorText(res), "error");
      if (data == null) paint();                                         // erster Aufruf: wenigstens den leeren Dialog zeigen
      return;
    }
    data = res.data;
    cwd = mode === "pick" ? data.path : data.path;
    paint();
  }

  function paint() {
    const pick = mode === "pick";
    $("fs-mkdir").hidden = pick;
    $("fs-upload").hidden = pick;
    $("fs-home").hidden = !pick;
    $("fs-data").hidden = !pick;
    $("fs-up").disabled = pick ? !(data && (data.path || "")) : !cwd;
    $("fs-use").hidden = !pick;
    $("fs-use").disabled = !(pick && data && data.path);
    $("fs-note").textContent = pick ? (data && data.path ? "" : t("FS_PICK_NONE")) : t("FS_AREA_NOTE", { path: (data && data.root) || "" });
    $("fs-note").hidden = !$("fs-note").textContent;
    // Pfad-Leiste
    const crumbs = $("fs-crumbs");
    crumbs.textContent = "";
    const add = (label, target) => {
      const b = el("button", "fsb__crumb", label); b.type = "button";
      b.addEventListener("click", () => load(target));
      if (crumbs.children.length) crumbs.appendChild(el("span", "fsb__sep", "/"));
      crumbs.appendChild(b);
    };
    if (pick) {
      add(t("FS_PICK_DRIVES"), "");
      if (data && data.path) {
        const norm = data.path.replace(/\\/g, "/");
        const parts = norm.split("/").filter(Boolean);
        let acc = "";
        parts.forEach((p, i) => { acc = i === 0 ? p + "\\" : acc.replace(/[\\/]+$/, "") + "\\" + p; add(p, acc); });
      }
    } else {
      add(area === "logs" ? t("FS_ROOT_LOGS") : t("FS_ROOT_DATA"), "");
      ((data && data.crumbs) || []).forEach((c) => add(c.name, c.path));
    }
    // Liste
    const list = $("fs-list");
    list.textContent = "";
    const rows = (data && data.rows) || [];
    if (!rows.length) { list.appendChild(el("p", "fsb__empty", t(pick ? "FS_EMPTY_DIRS" : "FS_EMPTY"))); return; }
    if (!pick) {
      const head = el("div", "fsb__row fsb__row--head");
      head.append(el("span", "", t("FS_COL_NAME")), el("span", "fsb__size", t("FS_COL_SIZE")), el("span", "fsb__date", t("FS_COL_DATE")), el("span", ""));
      list.appendChild(head);
    }
    rows.forEach((r) => list.appendChild(pick ? pickRow(r) : fileRow(r)));
  }

  function nameCell(name, isDir, onOpen) {
    const cell = el("button", "fsb__name" + (isDir ? " fsb__name--dir" : "")); cell.type = "button";
    if (HAS_ICONS) cell.appendChild(Icons.svg(isDir ? "folder" : "attach"));
    cell.appendChild(el("span", "", name));
    if (onOpen) cell.addEventListener("click", onOpen);
    else cell.disabled = true;
    return cell;
  }

  function pickRow(r) {
    const row = el("div", "fsb__row fsb__row--pick");
    row.append(nameCell(r.name, true, () => load(r.path)));
    return row;
  }

  function fileRow(r) {
    const row = el("div", "fsb__row");
    const rel = join(cwd, r.name);
    row.append(nameCell(r.name, r.dir, r.dir ? () => load(rel) : null), el("span", "fsb__size", r.dir ? "" : fmtSize(r.size)), el("span", "fsb__date", fmtDate(r.mtime)));
    const acts = el("span", "fsb__acts");
    const act = (icon, key, handler, danger) => {
      const b = el("button", "fsb__act" + (danger ? " fsb__act--danger" : "")); b.type = "button"; b.title = t(key); b.setAttribute("aria-label", t(key));
      if (HAS_ICONS) b.appendChild(Icons.svg(icon)); else b.textContent = t(key);
      b.addEventListener("click", handler);
      return b;
    };
    acts.append(act("download", r.dir ? "FS_DOWNLOAD_ZIP" : "FS_DOWNLOAD", () => download(rel)),
                act("edit", "FS_RENAME", () => rename(r)), act("copy", "FS_DUPLICATE", () => duplicate(r)), act("trash", "FS_DELETE", () => remove(r), true));
    row.appendChild(acts);
    return row;
  }

  // ------------------------------------------------------------------------------------------------ Aktionen
  function goUp() {
    if (mode === "pick") { load(data && data.parent != null ? data.parent : ""); return; }
    const parts = cwd.split("/").filter(Boolean);
    parts.pop();
    load(parts.join("/"));
  }

  async function op(body, okText) {
    const res = await api("POST", "/api/fs/op", { area, ...body });
    if (!res.ok) { toast(errorText(res), "error"); return false; }
    if (okText) toast(okText, "info");
    await load(cwd);
    return true;
  }

  async function newFolder() {
    const name = await _askLayoutName({ title: t("FS_NEW_FOLDER"), confirmKey: "FS_CREATE", labelText: t("FS_NAME_LABEL") });
    if (name) await op({ op: "mkdir", path: cwd, name });
  }

  async function rename(r) {
    const name = await _askLayoutName({ title: t("FS_RENAME"), confirmKey: "FS_RENAME", value: r.name, labelText: t("FS_NAME_LABEL") });
    if (name && name !== r.name) await op({ op: "rename", path: join(cwd, r.name), name });
  }

  async function duplicate(r) {
    if (await op({ op: "duplicate", path: join(cwd, r.name) }, t("FS_DUPLICATED", { name: r.name }))) { /* Liste ist neu geladen */ }
  }

  async function remove(r) {
    if (typeof _askDelete === "function" && !(await _askDelete("files", { title: t("FS_DELETE"), body: t(r.dir ? "FS_DELETE_BODY_DIR" : "FS_DELETE_BODY", { name: r.name }), confirmKey: "FS_DELETE" }))) return;
    await op({ op: "delete", path: join(cwd, r.name) });
  }

  function download(rel) {
    const a = document.createElement("a");
    a.href = "/api/fs/download?area=" + encodeURIComponent(area) + "&path=" + encodeURIComponent(rel);
    a.download = "";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  async function upload(files) {
    if (!files.length) return;
    let done = 0;
    for (const f of files) {
      toast(t("FS_UPLOADING", { name: f.name }), "info");
      try {
        const res = await fetch("/api/fs/upload?area=" + encodeURIComponent(area) + "&path=" + encodeURIComponent(cwd) + "&name=" + encodeURIComponent(f.name), { method: "POST", body: f });
        let json = {};
        try { json = await res.json(); } catch (e) { /* leer */ }
        if (res.ok && json.ok !== false) done += 1; else toast(errorText({ data: json }), "error");
      } catch (e) { toast(t("FS_ERR_GENERIC", { detail: "network" }), "error"); }
    }
    if (done) toast(t("FS_UPLOADED", { n: done }), "info");
    await load(cwd);
  }

  // ------------------------------------------------------------------------------------------------ Oeffentlich
  function show(newMode, title) {
    buildOnce();
    relabel();
    mode = newMode;
    data = null;
    $("fs-title").textContent = title;
    $("fs-body").dataset.mode = newMode;
    $("fs-list").textContent = "";
    $("fs-list").appendChild(el("p", "fsb__empty", "..."));
    paint();
  }

  /** Dateien im Datenordner bzw. Protokoll-Ordner anzeigen und verwalten. */
  function open(opts) {
    const o = opts || {};
    area = o.area === "logs" ? "logs" : "data";
    cwd = o.path || "";
    show("browse", o.title || t("FS_TITLE"));
    load(cwd);
    return _modalResult(MODAL, null, () => {});
  }

  /** Einen Ordner aussuchen: gibt den absoluten Pfad zurueck oder null (Abbruch). */
  function pickFolder(opts) {
    const o = opts || {};
    show("pick", o.title || t("FS_TITLE_PICK"));
    const start = String(o.start || "").trim();
    load(/^[A-Za-z]:[\\/]|^\//.test(start) ? start : "");
    return _modalResult(MODAL, null, (finish, listen) => {
      listen($("fs-use"), "click", () => { if (data && data.path) finish(data.path); });
    });
  }

  /** Am Hauptrechner der echte Explorer (POST realUrl), an jedem anderen Geraet dieser Dialog. */
  async function reveal(opts) {
    const o = opts || {};
    if (isLocal() && o.realUrl) {
      const res = await api("POST", o.realUrl);
      if (res.ok) return;
    }
    open(o);
  }

  document.addEventListener("i18n-applied", relabel);
  window.OCFsBrowser = { open, pickFolder, reveal };
})();
