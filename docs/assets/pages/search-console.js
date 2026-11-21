/*
 * OpenCue website – pages/search-console.js
 * Helper page for the site owner (not linked, "noindex"): lists every page, image, logo and icon of the site with buttons that copy the public
 * address. The data comes from <script type="application/json" id="gsc-data">, written by tools/website/build_seo.py.
 */
(function () {
  "use strict";

  var node = document.getElementById("gsc-data");
  if (!node) { return; }
  var D = JSON.parse(node.textContent);
  var $ = function (s) { return document.querySelector(s); };
  var here = new URL("../", location.href).href;           // the site root as served right now (local test or live)

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function local(path) { return here + path; }

  function copy(text, btn) {
    function ok() {
      if (!btn) { return; }
      var old = btn.textContent;
      btn.textContent = "Kopiert ✓"; btn.classList.add("done");
      setTimeout(function () { btn.textContent = old; btn.classList.remove("done"); }, 1400);
    }
    function fallback() {
      var t = document.createElement("textarea");
      t.value = text; t.style.cssText = "position:fixed;opacity:0";
      document.body.appendChild(t); t.select();
      try { document.execCommand("copy"); ok(); } catch (e) { window.prompt("Zum Kopieren Strg+C:", text); }
      t.remove();
    }
    if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(text).then(ok, fallback); } else { fallback(); }
  }

  function btn(label, cls, fn) {
    var b = document.createElement("button");
    b.type = "button"; b.className = "gsc-btn" + (cls ? " " + cls : ""); b.textContent = label; b.onclick = function () { fn(b); };
    return b;
  }

  function fmt(bytes) { return bytes > 1048576 ? (bytes / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(bytes / 1024)) + " KB"; }

  // ---- Zaehler und Kopfbereich
  $("#gsc-gen").textContent = D.generated;
  ["np", "ni", "nl", "no"].forEach(function (k, i) { var el = $("#gsc-" + k); if (el) { el.textContent = [D.pages.length, D.images.length, D.icons.length, D.og.length][i]; } });
  $("#gsc-sitemap").textContent = D.sitemap; $("#gsc-robots").textContent = D.robots; $("#gsc-root-robots").textContent = D.rootRobots;
  $("#gsc-sitemap-open").href = D.sitemap; $("#gsc-robots-open").href = D.robots;
  $("#gsc-sitemap-copy").onclick = function () { copy(D.sitemap, this); };
  $("#gsc-robots-copy").onclick = function () { copy(D.robots, this); };
  $("#gsc-root-copy").onclick = function () { copy(D.rootRobots, this); };
  $("#gsc-pages-copy").onclick = function () { copy(D.pages.map(function (p) { return p.url; }).join("\n"), this); };
  $("#gsc-icons-copy").onclick = function () { copy(D.icons.map(function (p) { return p.url; }).join("\n"), this); };
  $("#gsc-imgs-copy").onclick = function () { copy(D.images.map(function (p) { return p.url; }).join("\n"), this); };
  $("#gsc-og-copy").onclick = function () { copy(D.og.map(function (p) { return p.url; }).join("\n"), this); };

  // ---- Seiten
  var tb = $("#gsc-pages tbody");
  D.pages.forEach(function (p) {
    var tr = document.createElement("tr");
    tr.innerHTML = '<td><span class="gsc-mono">' + esc(p.url) + "</span><small>" + esc(p.title) + "</small></td><td>" + p.n + "</td><td>" + esc(p.lastmod) + '</td><td class="gsc-act"></td>';
    var act = tr.querySelector(".gsc-act");
    act.appendChild(btn("Adresse kopieren", "pri", function (b) { copy(p.url, b); }));
    if (p.desc) { act.appendChild(btn("Beschreibung", "", function (b) { copy(p.desc, b); })); }
    var a = document.createElement("a"); a.href = p.url; a.target = "_blank"; a.rel = "noopener"; a.textContent = "Live öffnen"; act.appendChild(a);
    tb.appendChild(tr);
  });

  // ---- Bildkarten (Logos/Icons, Bilder, Vorschaubilder)
  function card(it, opts) {
    var d = document.createElement("div");
    d.className = "gsc-card";
    var meta = [];
    if (it.w && it.h) { meta.push(it.w + " × " + it.h + " px"); }
    if (it.bytes) { meta.push(fmt(it.bytes)); }
    d.innerHTML = '<div class="gsc-th' + (opts.dark ? " dark" : "") + '"><img loading="lazy" src="' + esc(local(it.path)) + '" alt=""></div><div class="gsc-b"><div class="gsc-n">' + esc(it.name) + "</div>" +
      (it.note ? '<div class="gsc-alt">' + esc(it.note) + "</div>" : "") + (it.alt ? '<div class="gsc-alt">' + esc(it.alt) + "</div>" : "") +
      (meta.length ? '<div class="gsc-pg">' + esc(meta.join(" · ")) + "</div>" : "") +
      (it.pages && it.pages.length ? '<div class="gsc-pg">auf: ' + it.pages.map(function (p) { return p === "" ? "Startseite" : "/" + p; }).map(esc).join(", ") + "</div>" : "") +
      '<div class="gsc-bt"></div></div>';
    var bt = d.querySelector(".gsc-bt");
    bt.appendChild(btn("Adresse kopieren", "pri", function (b) { copy(it.url, b); }));
    if (it.alt) { bt.appendChild(btn("Beschreibung", "", function (b) { copy(it.alt, b); })); }
    var a = document.createElement("a"); a.href = it.url; a.target = "_blank"; a.rel = "noopener"; a.textContent = "Live öffnen"; bt.appendChild(a);
    return d;
  }
  D.icons.forEach(function (it) { $("#gsc-icons").appendChild(card(it, { dark: true })); });
  D.og.forEach(function (it) { $("#gsc-og").appendChild(card(it, {})); });

  var grid = $("#gsc-imgs");
  function render() {
    var q = $("#gsc-q").value.toLowerCase(), n = 0;
    grid.innerHTML = "";
    D.images.forEach(function (it) { if (!q || (it.name + " " + (it.alt || "")).toLowerCase().indexOf(q) >= 0) { grid.appendChild(card(it, {})); n++; } });
    $("#gsc-imgs-n").textContent = n + " von " + D.images.length;
  }
  $("#gsc-q").oninput = render;
  render();
})();
