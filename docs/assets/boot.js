/*
 * OpenCue website – boot.js
 * The ONLY file every page points to (with one relative path, e.g. <script src="../assets/boot.js">).
 * Everything else is found from here, so no other path in any HTML file has to be right:
 *
 *   - ROOT      the absolute address of the site's root folder, worked out from where this very file was loaded
 *               (https://thecraftedtech.github.io/opencue/ when published, file:///…/docs/ when opened from disk)
 *   - PRODUCTION  the published address, stored once here (the static canonical links in the pages use the same address)
 *   - PAGES     which style sheets and scripts each page needs
 *   - links     in the page text, a link written as href="@features/" means "<ROOT>features/" (see main.js)
 *
 * Moving a page into another folder only means changing the relative path to this file.
 * Also here, because it must run before the first paint: the theme (dark is the default).
 *
 * Page ids: <html data-page="…"> (and data-meta="…" when a page needs its own id, e.g. the effect guide).
 */
(function (g) {
  "use strict";

  var doc = document, html = doc.documentElement;
  var me = doc.currentScript;

  // boot.js lives in <ROOT>assets/, so the root is its parent folder
  var ROOT = new URL("../", me.src).href;
  var PRODUCTION = "https://thecraftedtech.github.io/opencue/";
  var PAGE = html.getAttribute("data-meta") || html.getAttribute("data-page") || "e404";

  // style sheets and scripts per page, relative to ROOT; "*" is loaded everywhere (scripts run in the order listed)
  var PAGES = {
    "*":              { css: ["assets/style.css"], js: ["assets/main.js"] },        // the dictionary of the chosen language is put in front (see "language" below)
    "home":           { js: ["assets/demo/show.js", "assets/demo/stage.js", "assets/pages/home.js"] },
    "features":       {},
    "panels":         {},
    "code-signing":   {},
    "download":       { js: ["assets/pages/versions.js"] },
    "download-thanks": { js: ["assets/pages/thanks.js"] },
    "changelog":      { js: ["assets/md.js", "assets/pages/changelog.js"] },
    "guide":          { js: ["assets/md.js", "assets/pages/guide-search.js"] },
    "guide-effects":  { js: ["assets/md.js", "assets/toc.js", "assets/pages/guide.js"] },
    "guide-start": { js: ["assets/md.js", "assets/toc.js", "assets/pages/guide.js"] },
    "guide-cmd": { js: ["assets/md.js", "assets/toc.js", "assets/pages/guide.js"] },
    "guide-fix": { js: ["assets/md.js", "assets/toc.js", "assets/pages/guide.js"] },
    "guide-rem": { js: ["assets/md.js", "assets/toc.js", "assets/pages/guide.js"] },
    "guide-keys": { js: ["assets/md.js", "assets/toc.js", "assets/pages/guide.js"] },
    "guide-doc": { js: ["assets/md.js", "assets/toc.js", "assets/pages/guide.js"] },          // every other guide page (guide-<name>): same scripts
    "demo":           { css: ["assets/demo.css"], js: ["assets/demo/show.js", "assets/demo/stage.js", "assets/demo/ui.js", "assets/pages/demo.js"] },
    "gsc":            {},          // google-search-console/ (helper page for the owner, noindex)
    "e404":           {}
  };

  function url(path) { return ROOT + path; }

  // ---------------------------------------------------------------- head: meta, icons, canonical, style sheets
  function addMeta(name, content) {
    var m = doc.createElement("meta"); m.name = name; m.content = content; doc.head.appendChild(m);
  }
  function addLink(attrs) {
    var l = doc.createElement("link");
    Object.keys(attrs).forEach(function (k) { l.setAttribute(k, attrs[k]); });
    doc.head.appendChild(l);
  }

  addMeta("color-scheme", "dark light");
  // canonical address, Open Graph, icons and theme colour are written statically into each page's <head> (crawlers
  // and link previews do not run scripts); only pages without them (thank-you page, 404) get icons from here
  if (!doc.head.querySelector('link[rel="icon"]')) {
    addMeta("theme-color", "#0a0a0b");
    addLink({ rel: "icon", href: url("assets/logo-mark.svg"), type: "image/svg+xml" });
    addLink({ rel: "icon", href: url("assets/icon-192.png"), sizes: "192x192", type: "image/png" });
    addLink({ rel: "apple-touch-icon", href: url("assets/apple-touch-icon.png") });
  }

  var common = PAGES["*"], mine = PAGES[PAGE] || (PAGE.indexOf("guide-") === 0 ? PAGES["guide-doc"] : {});
  (common.css || []).concat(mine.css || []).forEach(function (c) { addLink({ rel: "stylesheet", href: url(c) }); });

  // ---------------------------------------------------------------- theme (before first paint)
  var THEME_KEY = "opencue-theme";
  function readTheme() { try { return g.localStorage.getItem(THEME_KEY); } catch (e) { return null; } }
  function writeTheme(v) { try { g.localStorage.setItem(THEME_KEY, v); } catch (e) { /* blocked: fine */ } }
  var fromUrl = /[?&]theme=(dark|light)\b/.exec(location.search);
  var start = fromUrl ? fromUrl[1] : readTheme();
  if (start === "dark" || start === "light") { html.setAttribute("data-theme", start); }
  var theme = {
    current: function () { return html.getAttribute("data-theme") || "dark"; },
    toggle: function () {
      var next = theme.current() === "dark" ? "light" : "dark";
      html.setAttribute("data-theme", next);
      writeTheme(next);
      doc.dispatchEvent(new CustomEvent("opencue:theme", { detail: next }));
      return next;
    }
  };

  // ---------------------------------------------------------------- language
  // Chosen here, before anything else is loaded, so the dictionary of that language arrives together with main.js and the first
  // paint is already in the right language. Order: ?lang=xx, the saved choice, the first browser language we translate, English.
  // English is the page's own text; every other language is a dictionary file assets/locales/<code>.js (window.OC_LOCALES.<code>).
  var LANGUAGES = ["en", "de", "fr", "nl", "it", "es"];
  var LANG_KEY = "opencue-lang";
  function chooseLanguage() {
    var fromUrl = /[?&]lang=([a-z]{2})\b/.exec(location.search);
    if (fromUrl && LANGUAGES.indexOf(fromUrl[1]) >= 0) { return fromUrl[1]; }
    var saved = null;
    try { saved = g.localStorage.getItem(LANG_KEY); } catch (e) { /* blocked: fine */ }
    if (LANGUAGES.indexOf(saved) >= 0) { return saved; }
    var list = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || "en"];
    for (var i = 0; i < list.length; i++) {
      var code = String(list[i]).slice(0, 2).toLowerCase();
      if (LANGUAGES.indexOf(code) >= 0) { return code; }
    }
    return "en";
  }
  var language = chooseLanguage();
  g.OC_LOCALES = g.OC_LOCALES || {};
  html.lang = language;

  // ---------------------------------------------------------------- scripts
  // loads scripts in parallel but runs them in the given order; resolves when the last one has run
  function loadScripts(list) {
    return new Promise(function (resolve, reject) {
      if (!list.length) { resolve(); return; }
      var left = list.length;
      list.forEach(function (path) {
        var s = doc.createElement("script");
        s.src = /^https?:|^file:/.test(path) ? path : url(path);
        s.async = false;
        s.onload = function () { left -= 1; if (!left) { resolve(); } };
        s.onerror = function () { reject(new Error("Could not load " + path)); };
        doc.head.appendChild(s);
      });
    });
  }

  // ---------------------------------------------------------------- DOM ready (scripts may arrive before or after it)
  var domReady = doc.readyState !== "loading";
  var domFns = [];
  if (!domReady) {
    doc.addEventListener("DOMContentLoaded", function () {
      domReady = true; api.domReady = true;
      domFns.splice(0).forEach(function (fn) { fn(); });
    });
  }

  var api = g.OCBoot = {
    root: ROOT, production: PRODUCTION, page: PAGE, theme: theme,
    url: url, loadScripts: loadScripts, domReady: domReady,
    language: language, languages: LANGUAGES, languageKey: LANG_KEY,
    // makes sure the dictionary of `code` is there (English needs none); resolves when it is
    loadLocale: function (code) {
      if (code === "en" || g.OC_LOCALES[code] || LANGUAGES.indexOf(code) < 0) { return Promise.resolve(); }
      return loadScripts(["assets/locales/" + code + ".js"]);
    },
    onDom: function (fn) { if (domReady) { fn(); } else { domFns.push(fn); } }
  };

  var dictionary = language === "en" ? [] : ["assets/locales/" + language + ".js"];
  loadScripts(dictionary.concat(common.js || [], mine.js || [])).catch(function (e) {
    if (g.console) { console.error(e); }
  });
})(window);
