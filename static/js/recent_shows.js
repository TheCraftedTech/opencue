// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Datei-Menue -> "Zuletzt benutzt" (Untermenue mit den zuletzt benutzten Shows) und "Show von aussen oeffnen" (Doppelklick auf eine .ocshow-Datei, zweiter Programmstart mit einer Datei).
 * Server: GET /api/showfiles/recent, POST /api/showfiles/recent/clear (app/server.py), Liste `recent_shows` in der app_config; Ereignis `open_show_request` (nur an die Konsole, app/remote.py).
 * Das Oeffnen laeuft wie im Dateimanager: bei ungespeicherten Aenderungen kommt zuerst die Frage, dann `load_show`. */
(function () {
  "use strict";

  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    if (vars) for (const name of Object.keys(vars)) text = text.split("{" + name + "}").join(String(vars[name]));
    return text;
  };
  const toast = (text, kind) => { if (typeof _showToast === "function") _showToast(text, kind || "info", 3500); };
  const isLocal = () => !!(typeof client !== "undefined" && client.state && client.state.is_local);

  function openShow(path, name) {
    const run = () => { client.send("load_show", { path }); toast(t("RECENT_OPENED", { name })); };
    if (typeof _guardUnsavedChanges === "function") _guardUnsavedChanges(run); else run();
  }

  async function refresh() {
    const menu = document.getElementById("recent-submenu");
    if (!menu) return;
    let items = [];
    try { items = (await (await fetch("/api/showfiles/recent")).json()).items || []; } catch (e) { items = []; }
    const signature = JSON.stringify([items.map((i) => [i.path, i.current]), t("RECENT_EMPTY"), isLocal()]);
    if (menu.dataset.signature === signature && menu.childElementCount) return;          // unveraendert: nichts neu bauen (ein Tipp darf nicht verschluckt werden)
    menu.dataset.signature = signature;
    menu.textContent = "";
    if (!items.length) {
      const empty = document.createElement("li");
      empty.className = "menu__item menu__item--empty";
      empty.textContent = t("RECENT_EMPTY");
      menu.appendChild(empty);
      return;
    }
    items.forEach((item) => {
      const li = document.createElement("li");
      li.className = "menu__item" + (item.current ? " menu__item--active" : "");
      li.dataset.recentPath = item.path;
      li.title = item.path;
      li.textContent = item.name;
      li.addEventListener("click", (e) => {
        e.stopPropagation();
        if (typeof _closeAllMenus === "function") _closeAllMenus();
        openShow(item.path, item.name);
      });
      menu.appendChild(li);
    });
    {
      const sep = document.createElement("li");
      sep.className = "menu__separator";
      sep.setAttribute("role", "separator");
      const clear = document.createElement("li");
      clear.className = "menu__item";
      clear.dataset.action = "recent-clear";
      clear.textContent = t("RECENT_CLEAR");
      clear.addEventListener("click", async (e) => {
        e.stopPropagation();
        if (typeof _closeAllMenus === "function") _closeAllMenus();
        try { await fetch("/api/showfiles/recent/clear", { method: "POST" }); } catch (err) { /* offline */ }
        menu.dataset.signature = "";
        refresh();
      });
      menu.append(sep, clear);
    }
  }

  function bind() {
    const file = document.querySelector('[data-menu="file"]');
    if (!file || file.dataset.recentBound) return;
    file.dataset.recentBound = "1";
    const trigger = file.querySelector(".menu__trigger");
    if (trigger) { trigger.addEventListener("click", refresh); trigger.addEventListener("mouseenter", refresh); }
    refresh();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind); else bind();
  document.addEventListener("i18n-applied", () => { const m = document.getElementById("recent-submenu"); if (m) { m.dataset.signature = ""; refresh(); } });

  // Eine Show-Datei von aussen (Doppelklick / zweiter Start): nur die Konsole fragt und oeffnet
  document.addEventListener("open-show-request", (e) => {
    const p = e.detail || {};
    if (!p.path || !isLocal()) return;
    openShow(p.path, p.name || "");
  });

  window.OCRecentShows = { refresh, openShow };
})();
