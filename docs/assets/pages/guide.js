/*
 * OpenCue website – pages/guide.js
 * Loads a guide (static/help/<name>.<lang>.md, the name comes from data-doc on #guide) from GitHub in the site's
 * language, renders it and builds the "On this page" list from its headings.
 */
(function () {
  "use strict";

  var box = document.getElementById("guide");
  var tocList = document.getElementById("guide-toc");
  var sourceLink = document.getElementById("guide-source");
  if (!box || !window.OCMarkdown) { return; }

  var cache = {};

  // reading order = order of the cards on the docs overview: [folder, text key, English title]
  var ORDER = [
    ["getting-started", "guide.start.t", "Getting started"],
    ["commands", "guide.cmd.t", "Command reference"],
    ["fixtures", "guide.fix.t", "Fixtures and patching"],
    ["effect-studio", "guide.fx.t", "Effect Studio guide"],
    ["remote", "guide.rem.t", "Remote control"],
    ["keyboard-shortcuts", "guide.keys.t", "Keyboard shortcuts"]
  ];

  // "Previous / Next" buttons below the guide, so the chapters can be read one after the other
  var nav = null;
  function buildNav() {
    var at = -1;
    ORDER.forEach(function (g, i) { if (g[0] === DOC) { at = i; } });
    if (at < 0 || !sourceLink || !sourceLink.parentNode) { return; }
    nav = document.createElement("nav");
    nav.className = "guide-nav";
    nav.setAttribute("aria-label", OC.t("guide.nav", "More guides"));
    nav.setAttribute("data-i18n-aria-label", "guide.nav");
    [[-1, "guide.prev", "Previous", "prev"], [1, "guide.next", "Next", "next"]].forEach(function (d) {
      var g = ORDER[at + d[0]];
      var a = document.createElement(g ? "a" : "span");
      a.className = "guide-nav-" + d[3];
      if (!g) { nav.appendChild(a); return; }
      a.href = OC.root + "guide/" + g[0] + "/";
      a.setAttribute("rel", d[3]);
      var dir = document.createElement("span");
      dir.className = "dir"; dir.setAttribute("data-i18n", d[1]); dir.setAttribute("data-en", d[2]);
      dir.textContent = OC.t(d[1], d[2]);
      var name = document.createElement("strong");
      name.setAttribute("data-i18n", g[1]); name.setAttribute("data-en", g[2]);
      name.textContent = OC.t(g[1], g[2]);
      a.appendChild(dir); a.appendChild(name);
      nav.appendChild(a);
    });
    sourceLink.parentNode.parentNode.insertBefore(nav, sourceLink.parentNode);
  }
  function labelNav() {
    if (!nav) { return; }
    nav.setAttribute("aria-label", OC.t("guide.nav", "More guides"));
    nav.querySelectorAll("[data-i18n]").forEach(function (el) { el.textContent = OC.t(el.getAttribute("data-i18n"), el.getAttribute("data-en")); });
  }

  var DOC = box.getAttribute("data-doc") || "effect-studio";

  function path(lang) { return "static/help/" + DOC + "." + lang + ".md"; }

  function showError(lang) {
    box.innerHTML = "";
    tocList.innerHTML = "";
    var p = document.createElement("p");
    p.className = "state error";
    p.textContent = OC.t("common.loadError", "Could not load this from GitHub right now.") + " ";
    var a = document.createElement("a");
    a.href = OC.blob(path(lang)); a.rel = "noopener";
    a.textContent = OC.t("guide.source", "View this guide on GitHub");
    p.appendChild(a);
    box.appendChild(p);
  }

  function show(text, lang) {
    var rendered = OCMarkdown.render(text, { base: "https://github.com/" + OC.repo + "/blob/main/static/help/" });
    box.innerHTML = rendered.html;
    if (OC.copyable) { OC.copyable(box); }
    tocList.innerHTML = "";
    rendered.headings.forEach(function (h) {
      if (h.level !== 2 && h.level !== 3) { return; }
      var li = document.createElement("li");
      if (h.level === 3) { li.className = "l3"; }
      var a = document.createElement("a");
      a.href = "#" + h.id;
      a.textContent = h.text;
      li.appendChild(a);
      tocList.appendChild(li);
    });
    // the first heading (# title) repeats the page title: hide it
    var first = box.firstElementChild;
    if (first && first.tagName === "H1") { first.remove(); }
    if (window.OCToc) { OCToc.init(document.querySelector(".toc")); }
    if (location.hash) {
      var target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (target) { target.scrollIntoView(); }
    }
    sourceLink.href = OC.blob(path(lang));
  }

  function load(lang) {
    sourceLink.href = OC.blob(path(lang));
    if (cache[lang]) { show(cache[lang], lang); return; }
    OC.fetchText(path(lang))
      .then(function (text) { cache[lang] = text; show(text, lang); })
      .catch(function () {
        // no translation of this guide yet: fall back to English
        if (lang !== "en") { load("en"); } else { showError(lang); }
      });
  }

  OC.whenReady(function () {
    buildNav();
    load(OC.lang());
    OC.onLang(function (lang) { labelNav(); load(lang); });
  });
})();
