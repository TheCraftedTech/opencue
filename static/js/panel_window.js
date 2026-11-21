// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Panel als Fenster: jedes Panel laesst sich ohne Platz im Layout kurz als Fenster oeffnen (Ansicht -> Panel als Fenster). Strg+F (Ansicht -> Befehlszeile als Fenster)
 * oeffnet die BEFEHLS-KONSOLE: Befehlszeile oben, darunter Ziffernblock und Befehlstasten - zum schnellen Tippen per Hand oder Tastatur.
 * Jedes Fenster hat dieselbe feste Groesse und Lage (mittig, siehe .panelwin in style.css), egal welches Panel darin steht.
 * Das Fenster baut die Panels genau wie im Layout (Plugin buildContent) mit ihren Standard-Einstellungen; sie empfangen alle Live-Nachrichten wie Panels im Layout
 * (app.js schickt sie an jedes Element mit data-panel-type). Nichts davon wird gespeichert. Ausgenommen sind Knopf, Fader und Schalter: sie leben von ihrer Einrichtung
 * im Layout. Es ist immer nur ein Fenster offen.
 * Schliessen: X, Esc (wenn kein Dialog darueber liegt), Klick neben das Fenster, Strg+F (bei der Konsole). Der getippte Text bleibt im gemeinsamen Befehlspuffer.
 * Klassisches Skript, nach app.js. */
(function () {
  "use strict";
  const EXCLUDED = new Set(["button", "fader", "toggle"]);
  const CONSOLE = "command";                                                  // Strg+F: Befehlszeile + Ziffernblock + Befehlstasten
  const CONSOLE_PARTS = [["command_line", "cmd"], ["command_numpad", "num"], ["command_buttons", "keys"]];
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  let current = null;                    // {type, backdrop, root, returnFocus}

  /** Panel-Typen, die sich als Fenster oeffnen lassen (vom Server, wie im Dialog "Panel hinzufuegen"). */
  function types() {
    const infos = (typeof client !== "undefined" && client.state && client.state.panel_types) || [];
    return infos.filter((info) => !EXCLUDED.has(info.type) && window.__panelPlugins.has(info.type));
  }
  const infoOf = (type) => types().find((item) => item.type === type) || null;

  function close() {
    if (!current) return;
    const { backdrop, returnFocus } = current;
    current = null;
    backdrop.remove();                   // Listener der Plugins melden sich ueber _panelGone selbst ab
    document.dispatchEvent(new CustomEvent("panels-rendered"));
    if (returnFocus && returnFocus.isConnected && typeof returnFocus.focus === "function") returnFocus.focus({ preventScroll: true });
  }

  /** Ein Panel wie im Layout (ohne Kopfzeile, Rahmen und Ziehgriffe). */
  function panelSection(info, area) {
    const panel = { id: "win-" + info.type, type: info.type, title: "", show_header: false, panel_scale: 1, module_config: JSON.parse(JSON.stringify(info.default_module_config || {})) };
    const section = el("section", "panel panelwin__panel");
    section.dataset.panelId = panel.id;
    section.dataset.panelType = info.type;
    section.dataset.moduleConfig = JSON.stringify(panel.module_config);
    section.dataset.panelScale = "1";
    section.dataset.showHeader = "false";
    if (area) section.style.gridArea = area;
    const content = el("div", "panel__content");
    content.appendChild(buildPanelContent(panel));
    section.appendChild(content);
    return section;
  }

  function open(type) {
    const isConsole = type === CONSOLE;
    const info = isConsole ? infoOf("command_line") : infoOf(type);
    if (!info) return false;
    if (current && current.type === type) { focusInside(); return true; }
    const returnFocus = current ? current.returnFocus : document.activeElement;
    close();
    const backdrop = el("div", "panelwin-backdrop");
    const win = el("div", "panelwin");
    win.setAttribute("role", "dialog");
    win.setAttribute("aria-modal", "true");
    win.dataset.panelwinType = type;
    const head = el("div", "panelwin__head");
    const icon = Icons.svg(info.icon || "panel");
    icon.classList.add("panelwin__icon");
    const titleKey = isConsole ? "PANELWIN_CONSOLE" : info.name;
    const title = el("span", "panelwin__title", i18n(titleKey));
    title.dataset.i18n = titleKey;
    const shut = el("button", "modal__close panelwin__close", "×");
    shut.type = "button";
    shut.title = i18n("PANELWIN_CLOSE");
    shut.dataset.i18nTitle = "PANELWIN_CLOSE";
    shut.setAttribute("aria-label", i18n("PANELWIN_CLOSE"));
    shut.addEventListener("click", close);
    head.append(icon, title, shut);

    let body;
    if (isConsole) {
      body = el("div", "panelwin__console");
      CONSOLE_PARTS.forEach(([partType, area]) => { const part = infoOf(partType); if (part) body.appendChild(panelSection(part, area)); });
    } else {
      body = panelSection(info);
    }
    win.append(head, body);
    backdrop.appendChild(win);
    backdrop.addEventListener("mousedown", (e) => { if (e.target === backdrop) close(); });
    document.body.appendChild(backdrop);
    current = { type, backdrop, root: body, returnFocus };
    refreshActivePanels();                                           // wie neue Panels im Layout: sofort mit dem aktuellen Stand fuellen
    document.dispatchEvent(new CustomEvent("panels-rendered"));
    requestAnimationFrame(focusInside);
    return true;
  }

  /** Fokus ins Fenster: bei der Befehlszeile direkt ins Eingabefeld (sofort tippen). */
  function focusInside() {
    if (!current) return;
    const input = current.root.querySelector(".cmdline-input");
    if (input) { input.focus(); const n = input.value.length; try { input.setSelectionRange(n, n); } catch (err) { /* kein Textfeld */ } return; }
    const win = current.backdrop.querySelector(".panelwin");
    if (win) { win.tabIndex = -1; win.focus({ preventScroll: true }); }
  }

  function toggle(type) {
    if (current && current.type === type) { close(); return false; }
    return open(type);
  }

  // Esc schliesst das Fenster - aber erst, wenn darueber nichts mehr offen ist (Dialog, Bibliothek, Menue). Eine offene Vorschlagsliste verschwindet mit dem Fenster.
  document.addEventListener("keydown", (e) => {
    if (!current || e.key !== "Escape") return;
    if (typeof Modal !== "undefined" && Modal._stack.length) return;
    if (document.querySelector(".fx-panel-modal-backdrop, .fx-library-backdrop, .menu--open")) return;
    if (current.root.contains(document.activeElement) && document.activeElement.matches("select")) return;
    e.preventDefault();
    e.stopPropagation();
    close();
  }, true);

  // ---- Menue "Ansicht": Befehls-Konsole + Untermenue "Panel als Fenster"
  function fillSubmenu() {
    const submenu = document.getElementById("panelwin-submenu");
    if (!submenu) return;
    const list = types().map((info) => ({ ...info, label: i18n(info.name) })).sort((a, b) => a.label.localeCompare(b.label));
    const signature = JSON.stringify(list.map((info) => [info.type, info.label]));
    if (submenu.dataset.signature === signature && submenu.childElementCount) return;
    submenu.dataset.signature = signature;
    submenu.textContent = "";
    list.forEach((info) => {
      const li = el("li", "menu__item menu__item--icon");
      li.dataset.action = "open-panel-window";
      li.dataset.panelType = info.type;
      const icon = Icons.svg(info.icon || "panel");
      icon.classList.add("menu__icon");
      const label = el("span", "", info.label);
      label.dataset.i18n = info.name;
      li.append(icon, label);
      submenu.appendChild(li);
    });
  }
  document.addEventListener("click", (e) => {
    const item = e.target.closest("[data-action='open-panel-window'], [data-action='open-command-window']");
    if (!item) return;
    if (item.dataset.action === "open-command-window") open(CONSOLE);
    else if (item.dataset.panelType) open(item.dataset.panelType);
  });
  const hookMenu = () => {
    const view = document.querySelector('[data-menu="view"]');
    if (view) view.addEventListener("pointerenter", fillSubmenu);
    const item = document.getElementById("panelwin-menu-item");
    if (item) { item.addEventListener("pointerenter", fillSubmenu); item.addEventListener("click", fillSubmenu); }
    const trigger = view && view.querySelector(".menu__trigger");
    if (trigger) trigger.addEventListener("click", fillSubmenu);
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hookMenu); else hookMenu();
  document.addEventListener("i18n-applied", () => { const submenu = document.getElementById("panelwin-submenu"); if (submenu) submenu.dataset.signature = ""; });

  window.OCPanelWindow = { open, close, toggle, isOpen: () => !!current, type: () => (current ? current.type : null), types, CONSOLE };
})();
