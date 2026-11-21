// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Oberflaechenzustand der KONSOLE in der app_config.json (Server: app/ui_store.py). Laeuft als allererstes Skript im <head> (nur wenn der Server den Stand mitgibt, also nicht auf
 * externen Geraeten): spielt den gespeicherten Stand in den localStorage zurueck, BEVOR irgendein anderes Skript ihn liest, und meldet danach jede Aenderung eines Eintrags
 * "opencue.*" an den Server. Der localStorage bleibt der schnelle Speicher; der Server verhindert, dass der Zustand verloren geht (WebView-Speicher geleert, Datenordner gewechselt). */
(function () {
  "use strict";
  const PREFIX = "opencue.";
  const MAX_VALUE = 60000;
  const server = window.__OC_UI_STORE__;
  if (!server || typeof server !== "object") return;
  let ls;
  try { ls = window.localStorage; void ls.length; } catch (error) { return; }       // gesperrter Speicher: nichts zu spiegeln
  const nativeSet = Storage.prototype.setItem;
  const nativeRemove = Storage.prototype.removeItem;
  const pendingSet = {};
  const pendingRemove = new Set();
  let timer = 0;

  // 1) Stand des Servers gilt; was nur hier liegt (z. B. von einer frueheren Version), wandert zum Server
  try {
    for (const key of Object.keys(server)) {
      if (typeof server[key] === "string" && ls.getItem(key) !== server[key]) nativeSet.call(ls, key, server[key]);
    }
    for (let i = 0; i < ls.length; i++) {
      const key = ls.key(i);
      if (key && key.indexOf(PREFIX) === 0 && !(key in server)) {
        const value = ls.getItem(key);
        if (value !== null && value.length <= MAX_VALUE) pendingSet[key] = value;
      }
    }
  } catch (error) { /* egal */ }

  function flush() {
    timer = 0;
    const body = { set: { ...pendingSet }, remove: [...pendingRemove] };
    for (const key of Object.keys(pendingSet)) delete pendingSet[key];
    pendingRemove.clear();
    if (!Object.keys(body.set).length && !body.remove.length) return;
    try {
      const text = JSON.stringify(body);
      fetch("/api/uistore", { method: "POST", headers: { "Content-Type": "application/json" }, body: text, keepalive: text.length < 60000 }).catch(() => null);      // keepalive hat ein Limit von 64 KB
    } catch (error) { /* Server nicht erreichbar */ }
  }
  function queue() { if (!timer) timer = setTimeout(flush, 800); }

  // 2) jede Aenderung der eigenen Eintraege weitermelden
  Storage.prototype.setItem = function (key, value) {
    nativeSet.call(this, key, value);
    if (this === window.localStorage && typeof key === "string" && key.indexOf(PREFIX) === 0) {
      const text = String(value);
      if (text.length <= MAX_VALUE) { pendingSet[key] = text; pendingRemove.delete(key); queue(); }
    }
  };
  Storage.prototype.removeItem = function (key) {
    nativeRemove.call(this, key);
    if (this === window.localStorage && typeof key === "string" && key.indexOf(PREFIX) === 0) { delete pendingSet[key]; pendingRemove.add(key); queue(); }
  };
  window.addEventListener("pagehide", flush);
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") flush(); });
  if (Object.keys(pendingSet).length) queue();
})();
