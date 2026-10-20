/*
 * OpenCue website – pages/changelog.js
 * Loads CHANGELOG.md from the repository (GitHub raw) and shows every "## vX.Y.Z — date" section as a card.
 */
(function () {
  "use strict";

  var box = document.getElementById("releases");
  if (!box || !window.OCMarkdown) { return; }

  var SOURCE = "CHANGELOG.md";

  function showError() {
    box.innerHTML = "";
    var p = document.createElement("p");
    p.className = "state error";
    var msg = document.createElement("span");
    msg.textContent = OC.t("common.loadError", "Could not load this from GitHub right now.") + " ";
    var a = document.createElement("a");
    a.href = OC.blob(SOURCE); a.rel = "noopener";
    a.textContent = OC.t("cl.github", "View on GitHub");
    p.appendChild(msg); p.appendChild(a);
    box.appendChild(p);
  }

  // "## v1.0.0 — 2026-10-19" -> { version, date, body }
  function splitReleases(text) {
    var parts = text.split(/^##\s+/m).slice(1);
    return parts.map(function (part) {
      var nl = part.indexOf("\n");
      var title = (nl < 0 ? part : part.slice(0, nl)).trim();
      var body = nl < 0 ? "" : part.slice(nl + 1);
      var m = /^(v?\d[^\s—–-]*(?:-[\w.]+)?)\s*(?:[—–-]\s*(.+))?$/.exec(title);
      return { version: m ? m[1] : title, date: m && m[2] ? m[2].trim() : "", body: body };
    });
  }

  function render(text) {
    var releases = splitReleases(text);
    if (!releases.length) { showError(); return; }
    box.innerHTML = "";
    releases.forEach(function (rel, index) {
      var article = document.createElement("article");
      article.className = "release" + (index === 0 ? " latest" : "");
      article.id = rel.version.replace(/[^\w.-]/g, "");

      var head = document.createElement("div");
      head.className = "release-head";
      var h2 = document.createElement("h2");
      h2.textContent = rel.version;
      head.appendChild(h2);
      if (rel.date) {
        var time = document.createElement("time");
        time.textContent = rel.date;
        head.appendChild(time);
      }
      if (index === 0) {
        var badge = document.createElement("span");
        badge.className = "badge";
        badge.setAttribute("data-i18n", "cl.latest");
        badge.setAttribute("data-en", "Latest");
        badge.textContent = OC.t("cl.latest", "Latest");
        head.appendChild(badge);
      }
      var spacer = document.createElement("span");
      spacer.className = "spacer";
      head.appendChild(spacer);
      var plain = rel.version.replace(/^v/i, "");
      if (/^\d/.test(plain)) {
        // leads to the thank-you page, which fetches exactly this version (hidden again if GitHub has no installer for it)
        var dl = document.createElement("a");
        dl.className = "btn small primary release-dl";
        dl.href = OC.root + "download/thanks/?v=" + encodeURIComponent(plain);
        dl.setAttribute("data-version-dl", plain);
        dl.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" aria-hidden="true"><path d="M12 3v13M6 11l6 6 6-6M4 21h16"/></svg><span data-i18n="cl.download" data-en="Download">' + OC.t("cl.download", "Download") + "</span>";
        head.appendChild(dl);
      }
      var link = document.createElement("a");
      link.className = "btn small";
      link.rel = "noopener";
      link.href = "https://github.com/" + OC.repo + "/releases/tag/" + encodeURIComponent(rel.version);
      link.setAttribute("data-i18n", "cl.releasePage");
      link.setAttribute("data-en", "Release page");
      link.textContent = OC.t("cl.releasePage", "Release page");
      head.appendChild(link);
      article.appendChild(head);

      var prose = document.createElement("div");
      prose.className = "prose wide";
      prose.innerHTML = OCMarkdown.render(rel.body, { base: "https://github.com/" + OC.repo + "/blob/main/" }).html;
      article.appendChild(prose);
      if (OC.copyable) { OC.copyable(prose); }
      box.appendChild(article);
    });
  }

  // once GitHub's list of installers is known, drop the download button of versions that have none
  OC.whenReady(function () {
    OC.onReleases(function (list) {
      var have = {};
      list.forEach(function (r) { have[r.version] = true; });
      document.querySelectorAll("[data-version-dl]").forEach(function (a) {
        a.hidden = !have[a.getAttribute("data-version-dl")];
      });
    });
  });

  OC.whenReady(function () {
    OC.fetchText(SOURCE)
      .then(render)
      .catch(showError);
  });
})();
