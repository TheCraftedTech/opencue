/*
 * OpenCue website – main.js (loaded on every page by boot.js, after locales/de.js)
 *
 *  1. Header and footer: built here from ONE definition, so every page shares them.
 *  2. Links written as href="@features/" are turned into <site root>features/ (the root comes from boot.js).
 *  3. Language: English is the page's own text; every other language is a dictionary file locales/<code>.js (en, de, fr, nl, it, es).
 *     boot.js picks the language first (?lang=xx, else the saved choice, else the first browser language we translate) and loads
 *     only that dictionary; the language menu in the header loads another one when it is chosen. The choice is saved in
 *     localStorage (this browser only; no cookies).
 *  4. Newest release: read from the GitHub API (the repository is hosted there anyway), cached, but always
 *     checked again (ETag), so a new release shows up at once. Buttons marked data-download switch from the releases page to the installer's direct link.
 *
 * Public helpers for page scripts: window.OC = { t, lang, onLang, whenReady, onRelease, root, raw, blob, … }.
 */
(function () {
  "use strict";

  var html = document.documentElement;
  var ROOT = OCBoot.root;
  var PAGE = html.getAttribute("data-page") || "";
  var META = OCBoot.page;                    // title and description keys: meta.title.<id> / meta.desc.<id>
  var META_TITLE = "meta.title." + META;
  var META_DESC = "meta.desc." + META;

  var REPO = "TheCraftedTech/opencue";
  var RELEASES_API = "https://api.github.com/repos/" + REPO + "/releases?per_page=30";
  var DOWNLOAD_PREFIX = "https://github.com/" + REPO + "/releases/download/";
  var LIST_KEY = "opencue-releases-3";
  var FRESH_MS = 30 * 1000;                 // a cached list younger than this is used as is; older ones are checked against GitHub (ETag, free when unchanged)

  var LOCALES = window.OC_LOCALES = window.OC_LOCALES || {};     // dictionaries per language (assets/locales/<code>.js), loaded on demand
  var EN = {};               // English texts, collected from the page itself
  var current = "en";
  var listeners = [];

  // English texts for the generated header/footer (other languages: locales/<code>.js)
  var CHROME_EN = {
    "nav.home": "Home", "nav.features": "Features", "nav.panels": "Panels", "nav.demo": "Live demo", "nav.download": "Download",
    "nav.guide": "Docs", "nav.changelog": "Changelog",
    "nav.menu": "Menu", "fab.download": "Download", "nav.label": "Main", "lang.label": "Language",
    "theme.toLight": "Switch to light theme", "theme.toDark": "Switch to dark theme",
    "skip": "Skip to content",
    "foot.copy": "OpenCue · GPL-3.0-or-later",
    "foot.tag": "Open-source DMX lighting console for Windows. Free, offline, no account.",
    "foot.project": "Project", "foot.privacyTitle": "Privacy",
    "foot.privacy": "No cookies, no analytics and no third-party scripts. This site only asks GitHub for release information and documentation.",
    "foot.latest": "Latest version",
    "foot.label": "Project links",
    "foot.source": "Source code", "foot.releases": "Releases", "foot.license": "License",
    "foot.issues": "Report a problem", "foot.codesigning": "Code Signing Policy",
    "copy": "Copy", "copied": "Copied"
  };

  // ------------------------------------------------------------------ small helpers

  function store(key, value) {
    try {
      if (value === undefined) { return window.localStorage.getItem(key); }
      window.localStorage.setItem(key, value);
    } catch (e) { /* storage blocked: the page still works */ }
    return null;
  }

  function url(path) { return ROOT + path; }

  // ------------------------------------------------------------------ header and footer

  // the languages of the site, with their own names (shown in the language menu)
  var LANGUAGES = [
    { code: "en", name: "English" }, { code: "de", name: "Deutsch" }, { code: "fr", name: "Français" },
    { code: "nl", name: "Nederlands" }, { code: "it", name: "Italiano" }, { code: "es", name: "Español" }
  ];
  var LANGUAGE_CODES = LANGUAGES.map(function (l) { return l.code; });

  var SVG_ATTR = ' viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true"';

  // desktop: a button with the current language that opens a list
  function langDropdown() {
    var items = LANGUAGES.map(function (l) {
      return '<li role="none"><button type="button" role="menuitemradio" aria-checked="false" data-lang="' + l.code + '" lang="' + l.code + '">' +
        '<span class="lang-name">' + l.name + '</span><span class="lang-code">' + l.code.toUpperCase() + "</span></button></li>";
    }).join("");
    return '<div class="lang">' +
      '<button type="button" class="lang-btn" id="lang-btn" aria-haspopup="true" aria-expanded="false" aria-controls="lang-menu" aria-label="' + CHROME_EN["lang.label"] + '" data-i18n-aria-label="lang.label">' +
        '<svg width="16" height="16"' + SVG_ATTR + '><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/></svg>' +
        '<span class="lang-cur">EN</span>' +
        '<svg class="chev" width="14" height="14"' + SVG_ATTR + '><path d="M6 9l6 6 6-6"/></svg>' +
      "</button>" +
      '<ul class="lang-menu" id="lang-menu" role="menu" hidden>' + items + "</ul>" +
    "</div>";
  }

  // phone: the same choice as a block of buttons at the end of the opened menu
  function langChips() {
    var chips = LANGUAGES.map(function (l) {
      return '<button type="button" data-lang="' + l.code + '" lang="' + l.code + '" aria-pressed="false">' + l.name + "</button>";
    }).join("");
    return '<div class="nav-extra"><p class="nav-extra-title" data-i18n="lang.label">' + CHROME_EN["lang.label"] + "</p>" +
      '<div class="lang-chips" role="group" aria-label="' + CHROME_EN["lang.label"] + '" data-i18n-aria-label="lang.label">' + chips + "</div></div>";
  }

  var NAV = [
    { id: "home",      href: "",           key: "nav.home" },
    { id: "features",  href: "features/",  key: "nav.features" },
    { id: "panels",    href: "panels/",    key: "nav.panels" },
    { id: "demo",      href: "demo/",      key: "nav.demo" },
    { id: "download",  href: "download/",  key: "nav.download" },
    { id: "guide",     href: "guide/",     key: "nav.guide" },
    { id: "changelog", href: "changelog/", key: "nav.changelog" }
  ];

  function renderChrome() {
    var skip = document.createElement("a");
    skip.className = "skip"; skip.href = "#main"; skip.setAttribute("data-i18n", "skip"); skip.textContent = CHROME_EN["skip"];
    document.body.insertBefore(skip, document.body.firstChild);

    var links = NAV.map(function (n) {
      var cur = n.id === PAGE ? ' aria-current="page"' : "";
      var cls = n.id === "download" ? ' class="nav-cta"' : "";
      return '<a href="' + url(n.href) + '"' + cls + cur + ' data-i18n="' + n.key + '">' + CHROME_EN[n.key] + "</a>";
    }).join("");

    var header = document.getElementById("site-header");
    if (header) {
      header.className = "site-header";
      header.innerHTML =
        '<div class="wrap bar">' +
          '<a class="brand" href="' + url("") + '" aria-label="OpenCue">' +
            '<img src="' + url("assets/logo-mark.svg") + '" width="36" height="36" alt="">' +
            '<span class="brand-name">Open<span>Cue</span></span>' +
          "</a>" +
          '<nav id="site-nav" class="nav" aria-label="Main" data-i18n-aria-label="nav.label">' + links + langChips() + "</nav>" +
          '<div class="tools">' +
            langDropdown() +
            '<button type="button" class="icon-btn theme-btn" id="theme-toggle">' +
              '<svg class="ico-sun" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/></svg>' +
              '<svg class="ico-moon" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>' +
            "</button>" +
          "</div>" +
          '<button type="button" class="icon-btn menu-btn" aria-expanded="false" aria-controls="site-nav" aria-label="' + CHROME_EN["nav.menu"] + '" data-i18n-aria-label="nav.menu">' +
            '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true"><path class="ico-burger" d="M3 6h18M3 12h18M3 18h18"/><path class="ico-x" d="M5 5l14 14M19 5L5 19"/></svg>' +
          "</button>" +
        "</div>";
    }

    var footer = document.getElementById("site-footer");
    if (footer) {
      footer.className = "site-footer";
      var base = "https://github.com/" + REPO;
      // the page navigation lives in the header; the footer is only for the project itself
      footer.innerHTML =
        '<div class="wrap">' +
          '<div class="foot">' +
            '<div class="foot-about">' +
              '<a class="foot-brand" href="' + url("") + '"><img src="' + url("assets/logo-mark.svg") + '" width="40" height="40" alt=""><span>Open<span>Cue</span></span></a>' +
              '<p data-i18n="foot.tag">' + CHROME_EN["foot.tag"] + "</p>" +
            "</div>" +
            '<nav class="foot-col" aria-labelledby="foot-project"><h2 id="foot-project" data-i18n="foot.project">' + CHROME_EN["foot.project"] + "</h2><ul>" +
              '<li><a href="' + base + '" rel="noopener" data-i18n="foot.source">' + CHROME_EN["foot.source"] + "</a></li>" +
              '<li><a href="' + base + '/releases" rel="noopener" data-i18n="foot.releases">' + CHROME_EN["foot.releases"] + "</a></li>" +
              '<li><a href="' + base + '/issues" rel="noopener" data-i18n="foot.issues">' + CHROME_EN["foot.issues"] + "</a></li>" +
              '<li><a href="' + base + '/blob/main/LICENSE" rel="noopener" data-i18n="foot.license">' + CHROME_EN["foot.license"] + "</a></li>" +
              '<li><a href="' + url("code-signing/") + '" data-i18n="foot.codesigning">' + CHROME_EN["foot.codesigning"] + "</a></li>" +
            "</ul></nav>" +
            '<div class="foot-col"><h2 data-i18n="foot.privacyTitle">' + CHROME_EN["foot.privacyTitle"] + '</h2><p data-i18n="foot.privacy">' + CHROME_EN["foot.privacy"] + "</p></div>" +
          "</div>" +
          '<div class="foot-bottom"><span data-i18n="foot.copy">' + CHROME_EN["foot.copy"] + '</span><span><span data-i18n="foot.latest">' + CHROME_EN["foot.latest"] + '</span> <span data-version>–</span></span></div>' +
        "</div>";
    }

    var backdrop = document.createElement("div");
    backdrop.className = "nav-backdrop";
    document.body.appendChild(backdrop);
    setupMenus();

    var themeBtn = document.getElementById("theme-toggle");
    if (themeBtn) { themeBtn.addEventListener("click", function () { OCBoot.theme.toggle(); labelTheme(); }); }
  }

  // phone menu (burger) and language menu (dropdown): open/close, outside click, Escape, arrow keys
  function setupMenus() {
    var menuBtn = document.querySelector(".menu-btn");
    var nav = document.getElementById("site-nav");
    var backdrop = document.querySelector(".nav-backdrop");
    var langBtn = document.getElementById("lang-btn");
    var langMenu = document.getElementById("lang-menu");

    function setMenu(open, focusCurrent) {
      if (!langBtn || !langMenu) { return; }
      langMenu.hidden = !open;
      langBtn.setAttribute("aria-expanded", open ? "true" : "false");
      if (open && focusCurrent) { (langMenu.querySelector('[aria-checked="true"]') || langMenu.querySelector("button")).focus(); }
    }
    function setNav(open) {
      if (!menuBtn || !nav) { return; }
      nav.classList.toggle("open", open);
      html.classList.toggle("nav-open", open);
      menuBtn.setAttribute("aria-expanded", open ? "true" : "false");
      if (open) { setMenu(false); }
    }

    if (menuBtn && nav) {
      menuBtn.addEventListener("click", function () { setNav(!nav.classList.contains("open")); });
      nav.addEventListener("click", function (e) { if (e.target.closest("a")) { setNav(false); } });
      if (backdrop) { backdrop.addEventListener("click", function () { setNav(false); }); }
    }
    if (langBtn && langMenu) {
      langBtn.addEventListener("click", function () { setMenu(langMenu.hidden, true); });
      langBtn.addEventListener("keydown", function (e) {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); setMenu(true, true); }
      });
      langMenu.addEventListener("keydown", function (e) {
        var items = Array.prototype.slice.call(langMenu.querySelectorAll("button"));
        var i = items.indexOf(document.activeElement);
        if (e.key === "ArrowDown") { e.preventDefault(); items[(i + 1) % items.length].focus(); }
        else if (e.key === "ArrowUp") { e.preventDefault(); items[(i - 1 + items.length) % items.length].focus(); }
        else if (e.key === "Home") { e.preventDefault(); items[0].focus(); }
        else if (e.key === "End") { e.preventDefault(); items[items.length - 1].focus(); }
        else if (e.key === "Tab") { setMenu(false); }
      });
    }

    document.addEventListener("click", function (e) {
      var choice = e.target.closest(".lang-menu [data-lang], .lang-chips [data-lang]");
      if (choice) {
        setLanguage(choice.getAttribute("data-lang"));
        setMenu(false);
        if (choice.closest(".lang-chips")) { setNav(false); } else if (langBtn) { langBtn.focus(); }
        return;
      }
      if (langMenu && !langMenu.hidden && !e.target.closest(".lang")) { setMenu(false); }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") { return; }
      if (langMenu && !langMenu.hidden) { setMenu(false); if (langBtn) { langBtn.focus(); } }
      else if (nav && nav.classList.contains("open")) { setNav(false); if (menuBtn) { menuBtn.focus(); } }
    });
    if (window.matchMedia) {         // back to a wide window: the phone menu closes by itself
      var wide = window.matchMedia("(min-width: 66.0625rem)");
      var onWide = function (m) { if (m.matches) { setNav(false); } };
      if (wide.addEventListener) { wide.addEventListener("change", onWide); } else if (wide.addListener) { wide.addListener(onWide); }
    }
  }

  // in page text, href="@features/" means "<site root>features/"
  // (images use data-src="@assets/img/…": src is set here, so the browser never asks for a wrong address first)
  function resolveSiteLinks() {
    document.querySelectorAll('a[href^="@"]').forEach(function (a) { a.setAttribute("href", ROOT + a.getAttribute("href").slice(1)); });
    document.querySelectorAll('img[data-src^="@"]').forEach(function (img) { img.setAttribute("src", ROOT + img.getAttribute("data-src").slice(1)); });
  }

  function labelTheme() {
    var btn = document.getElementById("theme-toggle");
    if (!btn) { return; }
    var label = t(OCBoot.theme.current() === "dark" ? "theme.toLight" : "theme.toDark");
    btn.setAttribute("aria-label", label); btn.setAttribute("title", label);
  }

  // ------------------------------------------------------------------ language

  var ATTRS = ["aria-label", "alt", "title", "placeholder"];

  function collectEnglish() {
    Object.keys(CHROME_EN).forEach(function (key) { EN[key] = CHROME_EN[key]; });
    EN[META_TITLE] = document.title;
    var meta = document.querySelector('meta[name="description"]');
    EN[META_DESC] = meta ? meta.getAttribute("content") : "";

    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var key = el.getAttribute("data-i18n");
      if (EN[key] === undefined) { EN[key] = el.textContent; }
    });
    ATTRS.forEach(function (attr) {
      document.querySelectorAll("[data-i18n-" + attr + "]").forEach(function (el) {
        var key = el.getAttribute("data-i18n-" + attr);
        if (EN[key] === undefined) { EN[key] = el.getAttribute(attr); }
      });
    });
  }

  // t(key) for page texts; t(key, englishFallback) for texts that only exist in a script
  function t(key, fallback) {
    var dict = LOCALES[current];
    if (current !== "en" && dict && dict[key] !== undefined) { return dict[key]; }
    if (EN[key] !== undefined) { return EN[key]; }
    return fallback !== undefined ? fallback : key;
  }

  // shows which language is active: the code in the dropdown button, the tick in the list, the pressed chip in the phone menu
  function markLanguage() {
    var name = current;
    LANGUAGES.forEach(function (l) { if (l.code === current) { name = l.name; } });
    document.querySelectorAll(".lang-cur").forEach(function (el) { el.textContent = current.toUpperCase(); });
    var btn = document.getElementById("lang-btn");
    if (btn) { btn.setAttribute("aria-label", t("lang.label") + ": " + name); }
    document.querySelectorAll(".lang-menu [data-lang]").forEach(function (b) { b.setAttribute("aria-checked", b.getAttribute("data-lang") === current ? "true" : "false"); });
    document.querySelectorAll(".lang-chips [data-lang]").forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-lang") === current ? "true" : "false"); });
  }

  // loads the dictionary if needed, remembers the choice, switches the page
  function setLanguage(code) {
    if (LANGUAGE_CODES.indexOf(code) < 0) { return; }
    store(OCBoot.languageKey, code);
    OCBoot.loadLocale(code).then(function () { applyLanguage(code); }, function () { /* dictionary not reachable: stay in the current language */ });
  }

  function applyLanguage(lang) {
    current = LANGUAGE_CODES.indexOf(lang) >= 0 && (lang === "en" || LOCALES[lang]) ? lang : "en";
    html.lang = current;
    document.title = t(META_TITLE);
    var meta = document.querySelector('meta[name="description"]');
    if (meta) { meta.setAttribute("content", t(META_DESC)); }

    // elements that scripts create later carry their English text in data-en (static ones were collected from the page)
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      el.textContent = t(el.getAttribute("data-i18n"), el.getAttribute("data-en") || undefined);
    });
    ATTRS.forEach(function (attr) {
      document.querySelectorAll("[data-i18n-" + attr + "]").forEach(function (el) {
        el.setAttribute(attr, t(el.getAttribute("data-i18n-" + attr)));
      });
    });
    markLanguage();
    labelTheme();
    labelCopyButtons();
    listeners.forEach(function (fn) { try { fn(current); } catch (e) { /* a page script failed: keep going */ } });
  }

  function initialLanguage() { return OCBoot.language; }     // chosen in boot.js, whose dictionary is already loaded

  // ------------------------------------------------------------------ releases (one source: the list of published installers)
  //
  // The list (newest first) also gives "the newest release": the download button and the version list can never disagree.
  // Cached copy: shown at once (no empty buttons), then ALWAYS checked against GitHub in the background - unless it is
  // younger than FRESH_MS. The check is a conditional request (ETag): an unchanged answer (304) costs no API quota.
  // Pages that START a download (pages/thanks.js) wait for the checked ("fresh") answer; callbacks get (data, fresh).

  var releaseCallbacks = [];
  var releaseData = null;
  var releaseFresh = false;
  var listCallbacks = [];
  var listData = null;
  var listFresh = false;

  function showRelease(rel, fresh) {
    releaseData = rel;
    releaseFresh = !!fresh;
    document.querySelectorAll("[data-direct]").forEach(function (a) { a.setAttribute("href", rel.url); });
    document.querySelectorAll("[data-version]").forEach(function (el) { el.textContent = "v" + rel.version; });
    document.querySelectorAll("[data-filename]").forEach(function (el) { el.textContent = rel.file; });
    document.querySelectorAll("[data-release-size]").forEach(function (el) { el.textContent = rel.size ? (rel.size / 1048576).toFixed(1) + " MB" : "–"; });
    document.querySelectorAll("[data-release-date]").forEach(function (el) { el.textContent = rel.date ? rel.date.slice(0, 10) : "–"; });
    releaseCallbacks.forEach(function (fn) { try { fn(rel, releaseFresh); } catch (e) { /* ignore */ } });
  }

  function showList(list, fresh) {
    listData = list;
    listFresh = !!fresh;
    if (list.length) { showRelease(list[0], fresh); }
    listCallbacks.forEach(function (fn) { try { fn(list, listFresh); } catch (e) { /* ignore */ } });
  }

  // GitHub release JSON -> { version, url, file, size, date } or null (only accepts this repository's installer)
  function parseRelease(json) {
    var assets = json && json.assets ? json.assets : [];
    for (var i = 0; i < assets.length; i++) {
      var a = assets[i];
      if (/^OpenCue-Setup.*\.exe$/i.test(a.name || "") && String(a.browser_download_url || "").indexOf(DOWNLOAD_PREFIX) === 0) {
        return {
          version: String(json.tag_name || "").replace(/^v/i, ""),
          url: a.browser_download_url, file: a.name,
          size: Number(a.size) || 0, date: String(json.published_at || "")
        };
      }
    }
    return null;
  }

  function parseList(json) {
    var out = [];
    (Array.isArray(json) ? json : []).forEach(function (r) {
      if (r.draft || r.prerelease) { return; }
      var rel = parseRelease(r);
      if (rel && rel.size && rel.date) { rel.tag = String(r.tag_name || ""); out.push(rel); }
    });
    return out;
  }

  function readCache() {
    try {
      var cached = JSON.parse(store(LIST_KEY) || "null");
      // only a complete entry counts (every item with installer link, size and date)
      if (cached && Array.isArray(cached.list) && cached.list.length && cached.list.every(function (r) {
        return r && String(r.url).indexOf(DOWNLOAD_PREFIX) === 0 && r.size && r.date;
      })) { return cached; }
    } catch (e) { /* damaged cache: ignore */ }
    return null;
  }

  function forgetOldCaches() {
    // earlier versions of this script kept two separate caches (newest release and list) that could disagree
    ["opencue-latest-release-2", "opencue-latest-release-3", "opencue-releases", "opencue-releases-2"].forEach(function (k) {
      try { window.localStorage.removeItem(k); } catch (e) { /* blocked: fine */ }
    });
  }

  function loadReleases() {
    forgetOldCaches();
    var cached = readCache();
    var young = !!cached && Date.now() - cached.time < FRESH_MS;
    if (cached) { showList(cached.list, young); }
    if (young || !window.fetch) { return; }

    function request(useEtag) {
      var headers = { "Accept": "application/vnd.github+json" };
      if (useEtag && cached && cached.etag) { headers["If-None-Match"] = cached.etag; }
      return window.fetch(RELEASES_API, { headers: headers }).then(function (response) {
        if (response.status === 304 && cached) { return { list: cached.list, etag: cached.etag || "" }; }
        if (!response.ok) { return Promise.reject(new Error("HTTP " + response.status)); }
        var etag = response.headers.get("ETag") || "";
        return response.json().then(function (json) { return { list: parseList(json), etag: etag }; });
      });
    }

    request(true)
      .catch(function (err) {
        // a conditional request needs a preflight; if that is blocked somewhere, ask once more without it
        return cached && cached.etag ? request(false) : Promise.reject(err);
      })
      .then(function (res) {
        if (!res.list.length) { return; }
        store(LIST_KEY, JSON.stringify({ time: Date.now(), etag: res.etag, list: res.list }));
        showList(res.list, true);
      })
      .catch(function () { /* offline or rate limited: what was cached stays; without a cache the buttons stay links to the releases page */ });
  }

  // ------------------------------------------------------------------ scroll reveal and copy buttons

  function setupReveal() {
    if (!("IntersectionObserver" in window)) { return; }
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) { return; }
    var items = document.querySelectorAll("[data-reveal]");
    if (!items.length) { return; }
    html.classList.add("js-reveal");
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
    }, { rootMargin: "0px 0px -6% 0px", threshold: 0.04 });
    items.forEach(function (el) { io.observe(el); });
  }

  var COPY_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true"><rect x="9" y="9" width="12" height="12"/><path d="M5 15V5h10"/></svg>';

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) { return navigator.clipboard.writeText(text); }
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      ta.remove();
      if (ok) { resolve(); } else { reject(new Error("copy failed")); }
    });
  }

  // gives every .code-block a header bar with a "Copy" button (also for blocks that scripts add later)
  function makeCopyable(root) {
    (root || document).querySelectorAll(".code-block").forEach(function (block) {
      if (block.querySelector(".copy-btn")) { return; }
      var bar = block.querySelector(".cb-bar");
      if (!bar) {
        bar = document.createElement("div");
        bar.className = "cb-bar";
        bar.innerHTML = '<span class="cb-name"><i></i><span>' + (block.getAttribute("data-label") || "") + "</span></span>";
        block.insertBefore(bar, block.firstChild);
      }
      var btn = document.createElement("button");
      btn.type = "button"; btn.className = "copy-btn";
      btn.innerHTML = COPY_ICON + '<span class="copy-label">' + t("copy") + "</span>";
      btn.addEventListener("click", function () {
        var pre = block.querySelector("pre");
        copyText(pre ? pre.innerText.replace(/\n$/, "") : "").then(function () {
          btn.classList.add("done");
          btn.querySelector(".copy-label").textContent = t("copied");
          setTimeout(function () { btn.classList.remove("done"); btn.querySelector(".copy-label").textContent = t("copy"); }, 1800);
        }).catch(function () { /* clipboard blocked: nothing to do */ });
      });
      bar.appendChild(btn);
    });
  }

  function labelCopyButtons() {
    document.querySelectorAll(".copy-btn").forEach(function (btn) {
      btn.querySelector(".copy-label").textContent = t(btn.classList.contains("done") ? "copied" : "copy");
    });
  }

  // ------------------------------------------------------------------ project text files

  // Text files of the project (guides in static/help, CHANGELOG.md): GitHub first, so the site always shows the newest
  // text; if GitHub cannot be reached, the same file relative to this site (<site root>/../<path>). That second
  // address only exists where the whole repository is served - e.g. locally from the repository folder; GitHub Pages
  // publishes only docs/, so there the fallback finds nothing and the page shows its normal error message.
  function fetchText(path) {
    var sources = ["https://raw.githubusercontent.com/" + REPO + "/main/" + path, ROOT + "../" + path];
    function get(src) {
      return window.fetch(src).then(function (r) { return r.ok ? r.text() : Promise.reject(new Error("HTTP " + r.status)); })
        .then(function (text) { return /^\s*<(!doctype|html)/i.test(text) ? Promise.reject(new Error("not a text file")) : text; });
    }
    return sources.reduce(function (chain, src) { return chain.catch(function () { return get(src); }); }, Promise.reject(new Error("start")));
  }

  // ------------------------------------------------------------------ scroll aids
  // A thin progress line, and a "Download" pill that shows up once the visitor has scrolled past the first screen
  // (on the home page it jumps to the download band, elsewhere to the download page). Not shown where it would be redundant.

  function setupScrollAids() {
    var line = document.createElement("div");
    line.className = "scroll-progress"; line.setAttribute("aria-hidden", "true");
    line.innerHTML = "<i></i>";
    document.body.appendChild(line);
    var bar = line.firstChild;

    var skip = PAGE === "demo" || PAGE === "download" || PAGE === "e404";
    var target = document.getElementById("download");
    var fab = null;
    if (!skip) {
      fab = document.createElement("a");
      fab.className = "fab-dl";
      fab.href = target ? "#download" : url("download/");
      fab.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="square" aria-hidden="true"><path d="M12 3v13M6 11l6 6 6-6M4 21h16"/></svg><span data-i18n="fab.download">' + CHROME_EN["fab.download"] + "</span>";
      document.body.appendChild(fab);
    }

    // the pill steps aside while the download band or the footer is on screen
    var hidden = {};
    if (fab && "IntersectionObserver" in window) {
      var seen = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) { hidden[e.target.id] = e.isIntersecting; });
        update();
      });
      [target, document.getElementById("site-footer")].forEach(function (el) { if (el) { seen.observe(el); } });
    }

    var ticking = false;
    function update() {
      ticking = false;
      var max = document.documentElement.scrollHeight - window.innerHeight;
      var y = window.pageYOffset || document.documentElement.scrollTop || 0;
      bar.style.transform = "scaleX(" + (max > 0 ? Math.min(1, y / max) : 0) + ")";
      if (fab) { fab.classList.toggle("show", y > Math.max(500, window.innerHeight * .8) && !hidden.download && !hidden["site-footer"]); }
    }
    window.addEventListener("scroll", function () { if (!ticking) { ticking = true; window.requestAnimationFrame(update); } }, { passive: true });
    window.addEventListener("resize", update);
    update();
  }

  // ------------------------------------------------------------------ start

  var isReady = false;
  var readyFns = [];

  function init() {
    renderChrome();
    resolveSiteLinks();
    // every download button leads to the thank-you page, which starts the actual download (pages/thanks.js)
    document.querySelectorAll("[data-download]").forEach(function (a) { a.setAttribute("href", url("download/thanks/")); a.removeAttribute("rel"); });
    collectEnglish();
    loadReleases();
    makeCopyable();
    setupReveal();
    setupScrollAids();
    var lang = initialLanguage();
    if (lang !== "en") { applyLanguage(lang); } else { labelTheme(); markLanguage(); }
    isReady = true;
    document.dispatchEvent(new CustomEvent("opencue:ready"));
    readyFns.splice(0).forEach(function (fn) { try { fn(); } catch (e) { console.error(e); } });
  }

  window.OC = {
    // run fn once the header/footer exist and the language is set (immediately if that already happened)
    copyable: makeCopyable,
    whenReady: function (fn) { if (isReady) { fn(); } else { readyFns.push(fn); } },
    t: t,
    lang: function () { return current; },
    onLang: function (fn) { listeners.push(fn); },
    onRelease: function (fn) { releaseCallbacks.push(fn); if (releaseData) { fn(releaseData, releaseFresh); } },
    onReleases: function (fn) { listCallbacks.push(fn); if (listData) { fn(listData, listFresh); } },
    root: ROOT,
    repo: REPO,
    fetchText: fetchText,
    raw: function (path) { return "https://raw.githubusercontent.com/" + REPO + "/main/" + path; },
    blob: function (path) { return "https://github.com/" + REPO + "/blob/main/" + path; }
  };

  OCBoot.onDom(init);
})();
