/*
 * OpenCue website – pages/guide-search.js
 * Search on the docs overview: finds guides by title and, once the field is used, searches the full text of all guides
 * (static/help/<name>.<lang>.md, loaded from GitHub like the guide pages themselves) section by section and links to the heading.
 */
(function () {
  "use strict";

  var input = document.getElementById("doc-q");
  var status = document.getElementById("doc-status");
  var results = document.getElementById("doc-results");
  var groups = document.getElementById("doc-groups");
  if (!input || !results || !groups || !window.OCMarkdown) { return; }

  var index = {};          // lang -> [{slug, title, heading, id, text}]
  var loading = {};        // lang -> promise
  var timer = null;

  function slugs() {
    return [].map.call(groups.querySelectorAll("a.doc-card"), function (a) {
      var m = /guide\/([^\/]+)\/?$/.exec(a.getAttribute("href") || "");
      return { slug: m ? m[1] : "", card: a };
    }).filter(function (x) { return x.slug; });
  }

  function plain(s) {
    return s.replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1").replace(/[`*_>|]/g, " ").replace(/^\s*[-+]\s+/, "").replace(/\s+/g, " ").trim();
  }

  function build(slug, title, text) {
    var rendered = OCMarkdown.render(text, { base: "" });
    var heads = rendered.headings || [];
    var out = [], cur = { heading: "", id: "", lines: [] }, j = 0, fence = false;
    function flush() { if (cur.lines.length || cur.heading) { out.push({ slug: slug, title: title, heading: cur.heading, id: cur.id, text: cur.lines.join(" ") }); } }
    text.split(/\r?\n/).forEach(function (line) {
      if (/^\s*(```|~~~)/.test(line)) { fence = !fence; return; }
      var m = !fence && /^(#{1,6})\s+(.*)$/.exec(line);
      if (m) {
        flush();
        var name = plain(m[2]);
        var k = j;
        for (var t = j; t < Math.min(heads.length, j + 4); t++) { if (plain(heads[t].text || "") === name) { k = t; break; } }
        var h = heads[k];
        cur = { heading: m[1].length === 1 ? "" : name, id: m[1].length === 1 ? "" : (h ? h.id : ""), lines: [] };
        j = k + 1;
        return;
      }
      var p = plain(line);
      if (p && !/^[-:\s]+$/.test(p)) { cur.lines.push(p); }          // table separator lines (---|---) carry no text
    });
    flush();
    return out;
  }

  function load(lang) {
    if (loading[lang]) { return loading[lang]; }
    var list = slugs();
    loading[lang] = Promise.all(list.map(function (x) {
      var title = x.card.querySelector("h3") ? x.card.querySelector("h3").textContent : x.slug;
      function get(l) { return OC.fetchText("static/help/" + x.slug + "." + l + ".md"); }
      return get(lang).catch(function () { return lang === "en" ? "" : get("en"); }).catch(function () { return ""; })
        .then(function (text) { return text ? build(x.slug, title, text) : []; });
    })).then(function (all) {
      index[lang] = [].concat.apply([], all);
      return index[lang];
    });
    return loading[lang];
  }

  function esc(s) { return s.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  function mark(text, words) {
    var safe = esc(text);
    words.forEach(function (w) {
      var re = new RegExp("(" + esc(w).replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig");
      safe = safe.replace(re, "<mark>$1</mark>");
    });
    return safe;
  }

  function snippet(text, words) {
    var low = text.toLowerCase(), at = -1;
    for (var i = 0; i < words.length; i++) { var p = low.indexOf(words[i]); if (p >= 0 && (at < 0 || p < at)) { at = p; } }
    if (at < 0) { return text.slice(0, 140); }
    var from = Math.max(0, at - 60), to = Math.min(text.length, at + 110);
    return (from > 0 ? "… " : "") + text.slice(from, to) + (to < text.length ? " …" : "");
  }

  function search() {
    var q = input.value.trim().toLowerCase();
    if (!q) {
      results.hidden = true; results.innerHTML = ""; groups.hidden = false; status.textContent = "";
      return;
    }
    var words = q.split(/\s+/).filter(Boolean);
    groups.hidden = true; results.hidden = false;
    var lang = OC.lang();

    // 1) guides whose title / short text match
    var html = "", n = 0;
    var cards = slugs().filter(function (x) {
      var t = (x.card.textContent || "").toLowerCase();
      return words.every(function (w) { return t.indexOf(w) >= 0; });
    });
    if (cards.length) {
      html += '<h2 class="doc-group">' + esc(OC.t("guide.search.guides", "Guides")) + '</h2><div class="cards doc-cards">' +
        cards.map(function (x) { return x.card.outerHTML; }).join("") + "</div>";
      n += cards.length;
    }

    function finish(hits) {
      if (hits && hits.length) {
        html += '<h2 class="doc-group">' + esc(OC.t("guide.search.texts", "In the texts")) + '</h2><div class="doc-hits">' + hits.map(function (h) {
          var href = OC.root + "guide/" + h.slug + "/" + (h.id ? "#" + h.id : "");
          return '<a class="doc-hit" href="' + esc(href) + '"><small>' + esc(h.title) + (h.heading ? " › " + esc(h.heading) : "") + "</small><span>" +
            mark(snippet(h.text || h.heading, words), words) + "</span></a>";
        }).join("") + "</div>";
        n += hits.length;
      }
      results.innerHTML = html;
      status.textContent = n ? OC.t("guide.search.found", "Results:") + " " + n : OC.t("guide.search.none", "Nothing found.");
    }

    var ready = index[lang];
    if (!ready) {
      status.textContent = OC.t("guide.search.loading", "Searching all guides …");
      finish(null);
      load(lang).then(function () { if (input.value.trim().toLowerCase() === q) { search(); } });
      return;
    }
    var scored = [];
    ready.forEach(function (s) {
      var hay = (s.heading + " " + s.text).toLowerCase();
      if (!words.every(function (w) { return hay.indexOf(w) >= 0; })) { return; }
      var hl = s.heading.toLowerCase(), score = 0;
      words.forEach(function (w) { if (hl.indexOf(w) >= 0) { score += 5; } score += Math.min(5, hay.split(w).length - 1); });
      scored.push({ s: s, score: score });
    });
    scored.sort(function (a, b) { return b.score - a.score; });
    finish(scored.slice(0, 40).map(function (x) { return x.s; }));
  }

  function labels() {
    input.setAttribute("placeholder", OC.t("guide.search.ph", "Search the guides …"));
    input.setAttribute("aria-label", OC.t("guide.search.label", "Search the guides"));
  }

  input.addEventListener("input", function () { clearTimeout(timer); timer = setTimeout(search, 160); });
  input.addEventListener("focus", function () { load(OC.lang()); });
  input.addEventListener("keydown", function (e) { if (e.key === "Escape") { input.value = ""; search(); } });

  OC.whenReady(function () {
    labels();
    OC.onLang(function () { labels(); if (input.value.trim()) { search(); } });
  });
})();
