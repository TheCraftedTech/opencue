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
    window.fetch(OC.raw(path(lang)))
      .then(function (r) { return r.ok ? r.text() : Promise.reject(new Error("HTTP " + r.status)); })
      .then(function (text) { cache[lang] = text; show(text, lang); })
      .catch(function () {
        // no translation of this guide yet: fall back to English
        if (lang !== "en") { load("en"); } else { showError(lang); }
      });
  }

  OC.whenReady(function () {
    load(OC.lang());
    OC.onLang(function (lang) { load(lang); });
  });
})();
