// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/**
 * Einheitlicher Tooltip fuer alles, was eine Benennung hat (Maus):
 * - Quelle ist das title-Attribut; ein Symbol-Knopf ohne title (und ohne sichtbaren Text) nimmt sein aria-label.
 * - Erscheint nach kurzer Zeit (schneller als der Browser-Tooltip), ist kurz und verschwindet beim Wegfahren, Klicken, Scrollen oder Tippen.
 * - Waehrend der Tooltip-Zeit wird das title-Attribut zurueckgehalten (data-oc-title), damit nicht zusaetzlich der Browser-Tooltip erscheint;
 *   beim Verlassen kommt es unveraendert zurueck (Skripte, die .title lesen oder setzen, merken nichts).
 * - Nur mit echter Maus (hover: hover); Touch-Geraete haben keinen Mauszeiger.
 */
(() => {
  "use strict";

  const DELAY_MS = 350;
  if (!window.matchMedia || !window.matchMedia("(hover: hover)").matches) return;

  let tip = null;
  let timer = 0;
  let current = null;                                   // Element, ueber dem die Maus gerade steht
  let held = null;                                      // Element, dessen title gerade zurueckgehalten wird

  function textOf(el) {
    const title = el.getAttribute("title") || el.getAttribute("data-oc-title") || "";
    if (title.trim()) return title.trim();
    if (el.matches("button, [role=button], a") && !(el.textContent || "").trim()) return (el.getAttribute("aria-label") || "").trim();
    return "";
  }

  function find(start) {
    for (let el = start; el && el.nodeType === 1 && el !== document.body; el = el.parentElement) {
      if (el.closest(".oc-tip")) return null;
      if (textOf(el)) return el;
    }
    return null;
  }

  function release() {
    if (held && held.hasAttribute("data-oc-title")) {
      if (!held.getAttribute("title")) held.setAttribute("title", held.getAttribute("data-oc-title"));
      held.removeAttribute("data-oc-title");
    }
    held = null;
  }

  function hide() {
    clearTimeout(timer);
    timer = 0;
    if (tip) tip.classList.remove("oc-tip--on");
    release();
    current = null;
  }

  function show(el) {
    const text = textOf(el);
    if (!text || !el.isConnected) return;
    if (el.getAttribute("title")) { el.setAttribute("data-oc-title", el.getAttribute("title")); el.removeAttribute("title"); held = el; }        // ein Skript hat den title inzwischen neu gesetzt
    if (!tip) {
      tip = document.createElement("div");
      tip.className = "oc-tip";
      tip.setAttribute("role", "tooltip");
      document.body.appendChild(tip);
    }
    tip.textContent = text;
    tip.style.left = "0px";
    tip.style.top = "0px";
    tip.classList.add("oc-tip--on");
    const r = el.getBoundingClientRect();
    const w = tip.offsetWidth;
    const h = tip.offsetHeight;
    const gap = 8;
    let left = r.left + r.width / 2 - w / 2;
    left = Math.max(6, Math.min(left, window.innerWidth - w - 6));
    let top = r.bottom + gap;
    if (top + h > window.innerHeight - 6) top = Math.max(6, r.top - h - gap);          // unten kein Platz: darueber
    tip.style.left = Math.round(left) + "px";
    tip.style.top = Math.round(top) + "px";
  }

  document.addEventListener("mouseover", (event) => {
    if (event.pointerType === "touch") return;
    const el = find(event.target);
    if (el === current) return;
    hide();
    if (!el) return;
    current = el;
    if (el.getAttribute("title")) {                      // den Browser-Tooltip unterdruecken, solange unserer an der Reihe ist
      el.setAttribute("data-oc-title", el.getAttribute("title"));
      el.removeAttribute("title");
      held = el;
    }
    timer = setTimeout(() => show(el), DELAY_MS);
  }, true);

  document.addEventListener("mouseout", (event) => {
    if (!current) return;
    const to = event.relatedTarget;
    if (to && current.contains(to)) return;
    hide();
  }, true);

  ["mousedown", "keydown", "wheel", "scroll", "blur", "dragstart"].forEach((name) => document.addEventListener(name, () => { if (current) hide(); }, true));
  window.addEventListener("blur", hide);
  window.OCTooltip = { hide, DELAY_MS };
})();
