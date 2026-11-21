// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Sicherungen der Show (Datei -> Sicherung wiederherstellen), Angebot nach einem Absturz und die Einstellungen dazu (Einstellungen -> Allgemein -> Sicherungen der Show).
 * Server: app/backups.py (GET/POST /api/backups*). Eine Sicherung wird als UNGESPEICHERTE Show geladen; die Show-Datei bleibt unveraendert.
 * Aufruf: window.OCBackups.open() | .onReady() (nach dem ersten Zustand: Angebot nach einem Absturz) | .fillSettings(state) | .saveSettings(). */
(function () {
  "use strict";

  const ROOT = '[data-modal-backdrop="backup-restore"]';
  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    if (vars) for (const name of Object.keys(vars)) text = text.split("{" + name + "}").join(String(vars[name]));
    return text;
  };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const toast = (text, kind) => { if (typeof _showToast === "function") _showToast(text, kind || "info", 4200); };
  async function api(method, url, body) {
    try {
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
      let data = {};
      try { data = await res.json(); } catch (e) { /* leere Antwort */ }
      return { ok: res.ok && data.ok !== false, status: res.status, data };
    } catch (e) {
      return { ok: false, status: 0, data: { message: String(e) } };
    }
  }
  function fmtTime(iso) {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso || "";
    const same = new Date().toDateString() === d.toDateString();
    const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    return same ? time : d.toLocaleDateString([], { day: "2-digit", month: "2-digit" }) + " " + time;
  }
  const fmtSize = (n) => (n >= 1048576 ? (n / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(n / 1024)) + " KB");

  // ------------------------------------------------------------------------------------------------ Dialog "Sicherung wiederherstellen"
  async function open() {
    Modal.open("backup-restore");
    await render();
  }

  async function render() {
    const root = document.querySelector(ROOT);
    if (!root) return;
    const list = root.querySelector("#backup-list");
    const empty = root.querySelector("#backup-empty");
    const dir = root.querySelector("#backup-dir");
    const res = await api("GET", "/api/backups");
    list.textContent = "";
    const items = (res.data && res.data.items) || [];
    empty.hidden = items.length > 0;
    if (dir) dir.textContent = (res.data && res.data.dir) || "";
    root.querySelector("#backup-now").hidden = false;
    root.querySelector("#backup-open-folder").hidden = false;
    for (const item of items) {
      const row = el("div", "bk__row");
      const name = el("div", "bk__name");
      name.append(el("span", "bk__title", item.name));
      const notes = [];
      if (item.original_path && item.original_exists && item.original_locked) notes.push(t("BACKUP_ORIGINAL_LOCKED"));
      if (item.original_path && !item.original_exists) notes.push(t("BACKUP_ORIGINAL_GONE"));
      if (notes.length) name.append(el("span", "bk__note", notes.join(" · ")));
      const reasonKey = "BACKUP_REASON_" + item.reason;
      const reason = t(reasonKey);
      row.append(name, el("div", "bk__cell", fmtTime(item.taken_at)), el("div", "bk__cell", reason === reasonKey ? item.reason : reason), el("div", "bk__cell bk__cell--size", fmtSize(item.size)));
      const acts = el("div", "bk__acts");
      {
        const restore = el("button", "modal__button modal__button--primary", t("BACKUP_RESTORE"));
        restore.type = "button";
        restore.addEventListener("click", () => restoreItem(item));
        const del = el("button", "modal__button", t("BACKUP_DELETE"));
        del.type = "button";
        del.addEventListener("click", async () => {
          if (typeof _askDelete === "function" && !(await _askDelete("files", { title: t("BACKUP_DELETE"), body: t("BACKUP_DELETE_CONFIRM"), confirmKey: "BACKUP_DELETE" }))) return;
          await api("POST", "/api/backups/delete", { id: item.id });
          render();
        });
        acts.append(restore, del);
      }
      row.append(acts);
      list.append(row);
    }
  }

  async function restoreItem(item) {
    const res = await api("POST", "/api/backups/restore", { id: item.id });
    if (!res.ok) { toast(t("BACKUP_RESTORE_FAILED", { error: (res.data && (res.data.message || res.data.error)) || res.status }), "error"); return; }
    Modal.close("backup-restore");
    Modal.close("backup-recovery");
    toast(t("BACKUP_RESTORED", { name: res.data.name || item.name, time: fmtTime(res.data.taken_at || item.taken_at) }), "warn");
    if (typeof _refreshShowfileStatus === "function") _refreshShowfileStatus(true);
  }

  /** Ordner der Sicherungen: am Hauptrechner der Windows-Explorer, sonst der OpenCue-Explorer. */
  function revealFolder() {
    if (window.OCFsBrowser) window.OCFsBrowser.reveal({ realUrl: "/api/backups/open-folder", path: "backups" });
  }

  // ------------------------------------------------------------------------------------------------ Angebot nach einem Absturz
  let offered = false;
  async function onReady() {
    if (offered) return;
    offered = true;
    const res = await api("GET", "/api/backups");
    const rec = res.data && res.data.recovery;
    if (!rec) return;
    const body = document.getElementById("backup-recovery-body");
    if (body) body.textContent = t("BACKUP_RECOVERY_BODY", { name: rec.name, time: fmtTime(rec.taken_at) });
    const go = document.getElementById("backup-recovery-restore");
    if (go) go.onclick = () => restoreItem(rec);
    Modal.open("backup-recovery");
  }

  // ------------------------------------------------------------------------------------------------ Einstellungen (Allgemein)
  const $ = (id) => document.getElementById(id);
  /** Sicherungen aus: Intervall und Anzahl abdunkeln und sperren (die Wiederherstellung vorhandener Sicherungen bleibt nutzbar). */
  function dimSettings() {
    const on = !!($("settings-backup-enabled") || {}).checked;
    ["settings-backup-interval", "settings-backup-keep"].forEach((id) => {
      const input = $(id);
      if (!input) return;
      input.disabled = !on;
      const field = input.closest(".settings-field");
      if (field) field.classList.toggle("settings-field--off", !on);
    });
  }
  function fillSettings(state) {
    const cfg = (state && state.backup_config) || { enabled: true, interval_min: 15, keep: 10 };
    const box = $("settings-backup-enabled");
    if (!box) return;
    box.checked = !!cfg.enabled;
    $("settings-backup-interval").value = cfg.interval_min;
    $("settings-backup-keep").value = cfg.keep;
    dimSettings();
    const section = $("settings-backup-section");
    if (section) section.hidden = false;                                       // auch am Fernzugriffs-Geraet einstellbar
  }
  function readSettings() {
    const box = $("settings-backup-enabled");
    if (!box) return null;
    return { enabled: box.checked, interval_min: parseInt($("settings-backup-interval").value, 10) || 15, keep: parseInt($("settings-backup-keep").value, 10) || 10 };
  }
  async function saveSettings() {
    const want = readSettings();
    if (!want) return;
    const cur = client.state && client.state.backup_config;
    if (cur && cur.enabled === want.enabled && cur.interval_min === want.interval_min && cur.keep === want.keep) return;
    const res = await api("POST", "/api/backups/config", want);
    if (res.ok && client.state) client.state.backup_config = res.data.config;
  }

  function bind() {
    const root = document.querySelector(ROOT);
    if (root && !root.dataset.bound) {
      root.dataset.bound = "1";
      root.querySelector("#backup-now").addEventListener("click", async () => {
        const res = await api("POST", "/api/backups/now");
        toast(t(res.ok ? "BACKUP_NOW_DONE" : "BACKUP_NOW_NOTHING"), res.ok ? "info" : "warn");
        render();
      });
      root.querySelector("#backup-open-folder").addEventListener("click", revealFolder);
    }
    const later = $("backup-recovery-later");
    if (later && !later.dataset.bound) {
      later.dataset.bound = "1";
      later.addEventListener("click", () => { Modal.close("backup-recovery"); api("POST", "/api/backups/dismiss-recovery"); });
      $("backup-recovery-all").addEventListener("click", () => { Modal.close("backup-recovery"); open(); });
    }
    const settingsBox = $("settings-backup-enabled");
    if (settingsBox && !settingsBox.dataset.dimBound) {
      settingsBox.dataset.dimBound = "1";
      settingsBox.addEventListener("change", dimSettings);
    }
    const settingsRestore = $("settings-backup-restore");
    if (settingsRestore && !settingsRestore.dataset.bound) {
      settingsRestore.dataset.bound = "1";
      settingsRestore.addEventListener("click", () => open());
    }
    const settingsFolder = $("settings-backup-folder");
    if (settingsFolder && !settingsFolder.dataset.bound) {
      settingsFolder.dataset.bound = "1";
      settingsFolder.addEventListener("click", revealFolder);
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind); else bind();

  window.OCBackups = { open, onReady, fillSettings, saveSettings, readSettings };
})();
