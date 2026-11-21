// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Gemerkter Ansichtszustand je Panel (window.OCViewState): welche Unteransicht / welcher Umschalter zuletzt benutzt wurde (Liste oder Layout, Variablen oder Effekte, Filter, Sortierung,
 * Vorschau an/aus, Modus der 3D-Simulation, Zoom ...). Gehoert dem GERAET (localStorage), nie der Show: ein iPad und die Konsole duerfen verschieden eingestellt sein.
 * Schluessel: Panel-Id (data-panel-id des Panels) + Name der Einstellung. Ohne Panel-Id (z. B. Dialoge) nimmt man scope = "global".
 *   OCViewState.get(scope, key, fallback)      OCViewState.set(scope, key, value)      OCViewState.scopeOf(element)  ->  Panel-Id oder null
 * Alles ist gegen gesperrten Speicher (privates Fenster) abgesichert: dann gilt einfach die Standardansicht. */
(function () {
  "use strict";
  const STORE = "opencue.viewState";
  function read() {
    try { const v = JSON.parse(localStorage.getItem(STORE) || "{}"); return v && typeof v === "object" ? v : {}; } catch (error) { return {}; }
  }
  function get(scope, key, fallback) {
    const map = read()[scope];
    return map && Object.prototype.hasOwnProperty.call(map, key) ? map[key] : fallback;
  }
  function set(scope, key, value) {
    if (!scope) return;
    const all = read();
    const map = all[scope] || (all[scope] = {});
    if (value === undefined || value === null) delete map[key]; else map[key] = value;
    try { localStorage.setItem(STORE, JSON.stringify(all)); } catch (error) { /* privates Fenster */ }
  }
  function scopeOf(el) {
    const panel = el && el.closest ? el.closest("[data-panel-id]") : null;
    return panel ? panel.dataset.panelId : null;
  }
  /** Scrollposition eines Bereichs je Panel merken und beim naechsten Mal (auch nach einem Neustart) wiederherstellen. `key` benennt den Bereich im Panel.
   *  Der Inhalt baut sich oft erst nach dem Anlegen auf: das Wiederherstellen versucht es einige Bilder lang, bis der Bereich hoch genug ist; waehrend dessen und kurz nach
   *  jedem Neuaufbau des Inhalts (der die Position von selbst zuruecksetzt) wird nichts gespeichert. */
  function keepScroll(el, key) {
    if (!el || el._keepScroll) return;
    el._keepScroll = true;
    const name = "scroll:" + key;
    let scope = null;
    let restoring = true;
    let lastMutation = 0;
    let timer = 0;
    new MutationObserver(() => { lastMutation = performance.now(); }).observe(el, { childList: true, subtree: true });
    let frames = 0;
    const restore = () => {
      scope = scope || scopeOf(el);
      if (!scope) { if (++frames < 90) requestAnimationFrame(restore); else restoring = false; return; }       // noch nicht in einem Panel eingehaengt
      const saved = get(scope, name, null);
      if (!Array.isArray(saved) || (!saved[0] && !saved[1])) { restoring = false; return; }
      el.scrollTop = saved[0] || 0;
      el.scrollLeft = saved[1] || 0;
      const reached = Math.abs(el.scrollTop - (saved[0] || 0)) < 2 && Math.abs(el.scrollLeft - (saved[1] || 0)) < 2;
      if (!reached && ++frames < 180) requestAnimationFrame(restore);
      else setTimeout(() => { restoring = false; }, 200);
    };
    requestAnimationFrame(restore);
    el.addEventListener("scroll", () => {
      if (restoring || performance.now() - lastMutation < 250) return;
      clearTimeout(timer);
      timer = setTimeout(() => {
        scope = scope || scopeOf(el);
        if (scope) set(scope, name, el.scrollTop || el.scrollLeft ? [Math.round(el.scrollTop), Math.round(el.scrollLeft)] : null);
      }, 300);
    }, { passive: true });
  }
  window.OCViewState = { get, set, scopeOf, keepScroll };
})();
