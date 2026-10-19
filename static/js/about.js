/* "Ueber OpenCue" (Hilfe-Menue): Version, Lizenz (GPL-3.0-or-later), Quellcode-Link, Drittanbieter-Komponenten mit Lizenztexten.
 * Daten kommen von /api/about* (app/about.py, app/version.py); Aufruf: window.OCAbout.open(). */
(function () {
  "use strict";
  const ROOT = '[data-modal-backdrop="about"]';
  const t = (key, fallback) => { try { const v = typeof i18n === "function" ? i18n(key) : ""; return v && v !== key ? v : fallback; } catch (err) { return fallback; } };
  const $ = (selector) => document.querySelector(ROOT + " " + selector);
  const $$ = (selector) => [...document.querySelectorAll(ROOT + " " + selector)];
  let info = null;
  let licenseLoaded = false;
  let bound = false;

  function showTab(name) {
    $$("[data-about-tab]").forEach((b) => { const on = b.dataset.aboutTab === name; b.classList.toggle("about__tab--on", on); b.setAttribute("aria-selected", String(on)); });
    $$("[data-about-pane]").forEach((p) => { p.hidden = p.dataset.aboutPane !== name; });
    if (name === "license" && !licenseLoaded) loadLicense();
  }

  async function loadLicense() {
    const box = $("#about-license-text");
    box.textContent = t("ABOUT_LOADING", "Loading ...");
    try {
      const res = await fetch("/api/about/license", { cache: "no-store" });
      box.textContent = res.ok ? await res.text() : t("ABOUT_LOAD_FAILED", "Could not load.");
      licenseLoaded = res.ok;
    } catch (err) {
      box.textContent = t("ABOUT_LOAD_FAILED", "Could not load.");
    }
  }

  async function showComponent(item, row) {
    $$(".about__item").forEach((r) => r.classList.toggle("about__item--on", r === row));
    const box = $("#about-component-text");
    box.hidden = false;
    if (!item.has_text) { box.textContent = t("ABOUT_NO_TEXT", "No license text is bundled for this component."); return; }
    box.textContent = t("ABOUT_LOADING", "Loading ...");
    try {
      const res = await fetch("/api/about/component?name=" + encodeURIComponent(item.name), { cache: "no-store" });
      box.textContent = res.ok ? await res.text() : t("ABOUT_LOAD_FAILED", "Could not load.");
      box.scrollTop = 0;
    } catch (err) {
      box.textContent = t("ABOUT_LOAD_FAILED", "Could not load.");
    }
  }

  function fill() {
    $("#about-name").textContent = info.name;
    $("#about-version").textContent = info.label;
    $("#about-desc").textContent = info.description;
    $("#about-copyright").textContent = info.copyright;
    $("#about-fact-version").textContent = info.label + (info.frozen ? "" : " (source)");
    $("#about-fact-license").textContent = info.license + " (" + info.license_id + ")";
    $("#about-fact-data").textContent = info.data_dir;
    $("#about-fact-runtime").textContent = "Python " + info.python;
    const list = $("#about-components");
    list.textContent = "";
    $("#about-component-text").hidden = true;
    (info.components || []).forEach((item) => {
      const row = document.createElement("li");
      row.className = "about__item" + (item.has_text ? "" : " about__item--none");
      row.title = item.purpose || "";
      [item.name, item.version, item.license].forEach((text) => { const cell = document.createElement("span"); cell.textContent = text; row.appendChild(cell); });
      row.addEventListener("click", () => showComponent(item, row));
      list.appendChild(row);
    });
  }

  async function openLink(target) {
    try {
      const res = await fetch("/api/about/open", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target }) });
      const data = await res.json();
      if (data && data.ok && !data.opened && data.url) window.open(data.url, "_blank", "noopener");       // entferntes Geraet: im eigenen Browser
    } catch (err) { /* offline: nichts zu oeffnen */ }
  }

  function bind() {
    if (bound) return;
    bound = true;
    $$("[data-about-tab]").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.aboutTab)));
    $$("[data-about-open]").forEach((b) => b.addEventListener("click", () => openLink(b.dataset.aboutOpen)));
    $$("[data-about-updates]").forEach((b) => b.addEventListener("click", () => { Modal.close("about"); if (window.OCUpdate) window.OCUpdate.checkNow(true); }));
  }

  async function open() {
    bind();
    showTab("about");
    try {
      const res = await fetch("/api/about", { cache: "no-store" });
      info = await res.json();
      fill();
    } catch (err) {
      $("#about-desc").textContent = t("ABOUT_LOAD_FAILED", "Could not load.");
    }
    Modal.open("about");
  }

  window.OCAbout = { open };
})();
