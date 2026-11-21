// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Windows-Teil der Einstellungen: Firewall-Regel (Einstellungen -> Fernzugriff -> "Windows-Firewall") und Start mit Windows (Einstellungen -> Allgemein -> Verhalten).
 * Server: app/system_routes.py (GET/POST /api/system*), app/firewall.py, app/autostart.py. Alles Aendernde nur an der Konsole selbst.
 * Aufruf: window.OCSystem.fillSettings(state) beim Oeffnen der Einstellungen, window.OCSystem.saveSettings() beim Speichern. */
(function () {
  "use strict";

  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    if (vars) for (const name of Object.keys(vars)) text = text.split("{" + name + "}").join(String(vars[name]));
    return text;
  };
  const $ = (id) => document.getElementById(id);
  const isLocal = () => !!(typeof client !== "undefined" && client.state && client.state.is_local);
  const toast = (text, kind) => { if (typeof _showToast === "function") _showToast(text, kind || "info", 5000); };
  async function api(method, url, body) {
    try {
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
      let data = {};
      try { data = await res.json(); } catch (e) { /* leere Antwort */ }
      return { ok: res.ok, status: res.status, data };
    } catch (e) {
      return { ok: false, status: 0, data: {} };
    }
  }

  let info = null;
  let autostartSaved = null;                                                  // {enabled, headless} wie zuletzt vom Server gelesen

  function renderFirewall() {
    const box = $("settings-firewall-section");
    if (!box || !info) return;
    box.hidden = !(info.firewall && info.firewall.available);
    const exists = !!(info.firewall && info.firewall.exists);
    $("settings-firewall-status").textContent = t(exists ? "SYS_FIREWALL_OK" : "SYS_FIREWALL_NONE") + (isLocal() ? "" : " " + t("SYS_FIREWALL_AT_CONSOLE"));
    $("settings-firewall-status").classList.toggle("sys__ok", exists);
    $("settings-firewall-add").hidden = exists;                                  // die Windows-Rueckfrage (UAC) erscheint am Hauptrechner (der Hinweis steht daneben)
    $("settings-firewall-remove").hidden = !exists;
    $("settings-admin-note").textContent = t(info.admin ? "SYS_ADMIN_YES" : "SYS_ADMIN_NO");
  }

  function renderAutostart() {
    const row = $("settings-autostart-section");
    if (!row || !info) return;
    const a = info.autostart || {};
    row.hidden = false;
    const usable = !!a.available;
    autostartSaved = { enabled: !!a.enabled, headless: !!a.headless };
    $("settings-autostart-enabled").checked = autostartSaved.enabled;
    $("settings-autostart-headless").checked = autostartSaved.headless;
    $("settings-autostart-enabled").disabled = !usable;
    $("settings-autostart-headless").disabled = !usable;
    $("settings-autostart-hint").textContent = t(usable ? "SYS_AUTOSTART_HINT" : "SYS_AUTOSTART_UNAVAILABLE");
  }

  async function fillSettings() {
    const res = await api("GET", "/api/system");
    if (!res.ok) return;
    info = res.data;
    renderFirewall();
    renderAutostart();
  }

  async function saveSettings() {
    if (!autostartSaved || !($("settings-autostart-enabled") && !$("settings-autostart-enabled").disabled)) return;
    const want = { enabled: $("settings-autostart-enabled").checked, headless: $("settings-autostart-headless").checked };
    if (want.enabled === autostartSaved.enabled && want.headless === autostartSaved.headless) return;
    const res = await api("POST", "/api/system/autostart", want);
    if (res.ok && res.data.autostart) { autostartSaved = { enabled: res.data.autostart.enabled, headless: res.data.autostart.headless }; if (info) info.autostart = res.data.autostart; }
    else toast(t("SYS_AUTOSTART_FAILED"), "error");
  }

  async function changeFirewall(enable) {
    const buttons = [$("settings-firewall-add"), $("settings-firewall-remove")];
    buttons.forEach((b) => { if (b) b.disabled = true; });
    $("settings-firewall-status").textContent = t("SYS_FIREWALL_WAIT");
    const res = await api("POST", "/api/system/firewall", { enabled: enable });
    buttons.forEach((b) => { if (b) b.disabled = false; });
    if (res.data && res.data.firewall && info) info.firewall = res.data.firewall;
    renderFirewall();
    if (res.data && res.data.cancelled) toast(t("SYS_FIREWALL_CANCELLED"), "warn");
    else if (res.data && res.data.ok) toast(t(enable ? "SYS_FIREWALL_ADDED" : "SYS_FIREWALL_REMOVED"), "info");
    else toast(t("SYS_FIREWALL_FAILED"), "error");
  }

  function bind() {
    const add = $("settings-firewall-add");
    if (add && !add.dataset.bound) {
      add.dataset.bound = "1";
      add.addEventListener("click", () => changeFirewall(true));
      $("settings-firewall-remove").addEventListener("click", () => changeFirewall(false));
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind); else bind();

  window.OCSystem = { fillSettings, saveSettings };
})();
