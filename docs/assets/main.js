/*
 * OpenCue website – main.js (loaded on every page by boot.js, after locales/de.js)
 *
 *  1. Header and footer: built here from ONE definition, so every page shares them.
 *  2. Links written as href="@features/" are turned into <site root>features/ (the root comes from boot.js).
 *  3. Language: English is the page's own text; German comes from locales/de.js (window.OC_DE).
 *     Choice: ?lang=de|en, else the saved choice, else the first browser language we translate.
 *     The saved choice lives in localStorage (this browser only; no cookies).
 *  4. Newest release: read from the GitHub API (the repository is hosted there anyway), cached for an
 *     hour. Buttons marked data-download switch from the releases page to the installer's direct link.
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
  var RELEASE_API = "https://api.github.com/repos/" + REPO + "/releases/latest";
  var RELEASES_API = "https://api.github.com/repos/" + REPO + "/releases?per_page=30";
  var DOWNLOAD_PREFIX = "https://github.com/" + REPO + "/releases/download/";
  var CACHE_KEY = "opencue-latest-release-2";
  var LIST_KEY = "opencue-releases";
  var CACHE_MS = 60 * 60 * 1000;

  var DE = window.OC_DE || {};
  var EN = {};               // English texts, collected from the page itself
  var current = "en";
  var listeners = [];

  // English texts for the generated header/footer (German: locales/de.js)
  var CHROME_EN = {
    "nav.features": "Features", "nav.demo": "Live demo", "nav.download": "Download",
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
    "foot.issues": "Report a problem",
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

  var NAV = [
    { id: "features",  href: "features/",  key: "nav.features" },
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
          '<nav id="site-nav" class="nav" aria-label="Main" data-i18n-aria-label="nav.label">' + links + "</nav>" +
          '<div class="tools">' +
            '<div class="lang" role="group" aria-label="Language" data-i18n-aria-label="lang.label">' +
              '<button type="button" data-lang="en" lang="en" aria-pressed="true">EN</button>' +
              '<button type="button" data-lang="de" lang="de" aria-pressed="false">DE</button>' +
            "</div>" +
            '<button type="button" class="icon-btn theme-btn" id="theme-toggle">' +
              '<svg class="ico-sun" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/></svg>' +
              '<svg class="ico-moon" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>' +
            "</button>" +
          "</div>" +
          '<button type="button" class="icon-btn menu-btn" aria-expanded="false" aria-controls="site-nav" aria-label="' + CHROME_EN["nav.menu"] + '" data-i18n-aria-label="nav.menu">' +
            '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true"><path d="M3 6h18M3 12h18M3 18h18"/></svg>' +
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
            "</ul></nav>" +
            '<div class="foot-col"><h2 data-i18n="foot.privacyTitle">' + CHROME_EN["foot.privacyTitle"] + '</h2><p data-i18n="foot.privacy">' + CHROME_EN["foot.privacy"] + "</p></div>" +
          "</div>" +
          '<div class="foot-bottom"><span data-i18n="foot.copy">' + CHROME_EN["foot.copy"] + '</span><span><span data-i18n="foot.latest">' + CHROME_EN["foot.latest"] + '</span> <span data-version>–</span></span></div>' +
        "</div>";
    }

    var menuBtn = document.querySelector(".menu-btn");
    var nav = document.getElementById("site-nav");
    if (menuBtn && nav) {
      menuBtn.addEventListener("click", function () {
        var open = nav.classList.toggle("open");
        menuBtn.setAttribute("aria-expanded", open ? "true" : "false");
      });
      nav.addEventListener("click", function (e) {
        if (e.target.tagName === "A") { nav.classList.remove("open"); menuBtn.setAttribute("aria-expanded", "false"); }
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && nav.classList.contains("open")) { nav.classList.remove("open"); menuBtn.setAttribute("aria-expanded", "false"); menuBtn.focus(); }
      });
    }

    var themeBtn = document.getElementById("theme-toggle");
    if (themeBtn) { themeBtn.addEventListener("click", function () { OCBoot.theme.toggle(); labelTheme(); }); }
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
    if (current === "de" && DE[key] !== undefined) { return DE[key]; }
    if (EN[key] !== undefined) { return EN[key]; }
    return fallback !== undefined ? fallback : key;
  }

  function applyLanguage(lang) {
    current = lang === "de" ? "de" : "en";
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
    document.querySelectorAll(".lang button").forEach(function (btn) {
      btn.setAttribute("aria-pressed", btn.getAttribute("data-lang") === current ? "true" : "false");
    });
    labelTheme();
    labelCopyButtons();
    listeners.forEach(function (fn) { try { fn(current); } catch (e) { /* a page script failed: keep going */ } });
  }

  function initialLanguage() {
    var fromUrl = /[?&]lang=(de|en)\b/.exec(window.location.search);
    if (fromUrl) { return fromUrl[1]; }
    var saved = store("opencue-lang");
    if (saved === "de" || saved === "en") { return saved; }
    // first browser language we have a translation for (e.g. ["fr-CH", "de-AT", "en"] -> de)
    var langs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || "en"];
    for (var i = 0; i < langs.length; i++) {
      var code = String(langs[i]).slice(0, 2).toLowerCase();
      if (code === "de" || code === "en") { return code; }
    }
    return "en";
  }

  // ------------------------------------------------------------------ newest release

  var releaseCallbacks = [];
  var releaseData = null;

  function showRelease(rel) {
    releaseData = rel;
    document.querySelectorAll("[data-direct]").forEach(function (a) { a.setAttribute("href", rel.url); });
    document.querySelectorAll("[data-version]").forEach(function (el) { el.textContent = "v" + rel.version; });
    document.querySelectorAll("[data-filename]").forEach(function (el) { el.textContent = rel.file; });
    document.querySelectorAll("[data-release-size]").forEach(function (el) { el.textContent = rel.size ? (rel.size / 1048576).toFixed(1) + " MB" : "–"; });
    document.querySelectorAll("[data-release-date]").forEach(function (el) { el.textContent = rel.date ? rel.date.slice(0, 10) : "–"; });
    releaseCallbacks.forEach(function (fn) { try { fn(rel); } catch (e) { /* ignore */ } });
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

  function readCache() {
    try {
      var cached = JSON.parse(store(CACHE_KEY) || "null");
      // only a complete entry counts: an older or damaged one (no size or date) is fetched again
      if (cached && cached.rel && String(cached.rel.url).indexOf(DOWNLOAD_PREFIX) === 0 && cached.rel.size && cached.rel.date) { return cached; }
    } catch (e) { /* damaged cache: ignore */ }
    return null;
  }

  function loadRelease() {
    var cached = readCache();
    if (cached) { showRelease(cached.rel); }
    if (cached && Date.now() - cached.time < CACHE_MS) { return; }
    if (!window.fetch) { return; }
    window.fetch(RELEASE_API, { headers: { "Accept": "application/vnd.github+json" } })
      .then(function (response) { return response.ok ? response.json() : Promise.reject(new Error("HTTP " + response.status)); })
      .then(function (json) {
        var rel = parseRelease(json);
        if (!rel) { loadList(); return; }
        showRelease(rel);
        store(CACHE_KEY, JSON.stringify({ time: Date.now(), rel: rel }));
      })
      .catch(function () { loadList(); /* the list is a second source; offline or rate limited: the buttons stay links to the releases page */ });
  }

  // All published installers (newest first), for the version list and the per-release download buttons.
  // Same idea as the newest-release lookup: GitHub API, cached for an hour, nothing else leaves the page.
  var listCallbacks = [];
  var listData = null;

  function showList(list) {
    listData = list;
    // the list carries the same data: use it if the newest-release lookup failed or came back incomplete
    if (list.length && (!releaseData || !releaseData.size || !releaseData.date)) { showRelease(list[0]); }
    listCallbacks.forEach(function (fn) { try { fn(list); } catch (e) { /* ignore */ } });
  }

  function parseList(json) {
    var out = [];
    (Array.isArray(json) ? json : []).forEach(function (r) {
      if (r.draft || r.prerelease) { return; }
      var rel = parseRelease(r);
      if (rel) { rel.tag = String(r.tag_name || ""); out.push(rel); }
    });
    return out;
  }

  function loadList() {
    try {
      var cached = JSON.parse(store(LIST_KEY) || "null");
      if (cached && Array.isArray(cached.list)) {
        showList(cached.list);
        if (Date.now() - cached.time < CACHE_MS) { return; }
      }
    } catch (e) { /* damaged cache: ignore */ }
    if (!window.fetch) { return; }
    window.fetch(RELEASES_API, { headers: { "Accept": "application/vnd.github+json" } })
      .then(function (response) { return response.ok ? response.json() : Promise.reject(new Error("HTTP " + response.status)); })
      .then(function (json) {
        var list = parseList(json);
        if (!list.length) { return; }
        showList(list);
        store(LIST_KEY, JSON.stringify({ time: Date.now(), list: list }));
      })
      .catch(function () { /* offline or rate limited: pages fall back to the releases page */ });
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

    var targetVisible = false;
    if (fab && target && "IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) { targetVisible = entries[0].isIntersecting; update(); }).observe(target);
    }

    var ticking = false;
    function update() {
      ticking = false;
      var max = document.documentElement.scrollHeight - window.innerHeight;
      var y = window.pageYOffset || document.documentElement.scrollTop || 0;
      bar.style.transform = "scaleX(" + (max > 0 ? Math.min(1, y / max) : 0) + ")";
      if (fab) { fab.classList.toggle("show", y > Math.max(500, window.innerHeight * .8) && !targetVisible); }
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
    loadRelease();
    if (PAGE === "changelog" || PAGE === "download") { loadList(); }
    makeCopyable();
    setupReveal();
    setupScrollAids();
    document.querySelectorAll(".lang button").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var lang = btn.getAttribute("data-lang");
        applyLanguage(lang);
        store("opencue-lang", lang);
      });
    });
    var lang = initialLanguage();
    if (lang !== "en") { applyLanguage(lang); } else { labelTheme(); }
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
    onRelease: function (fn) { releaseCallbacks.push(fn); if (releaseData) { fn(releaseData); } },
    onReleases: function (fn) { listCallbacks.push(fn); if (listData) { fn(listData); } },
    root: ROOT,
    repo: REPO,
    raw: function (path) { return "https://raw.githubusercontent.com/" + REPO + "/main/" + path; },
    blob: function (path) { return "https://github.com/" + REPO + "/blob/main/" + path; }
  };

  OCBoot.onDom(init);
})();
