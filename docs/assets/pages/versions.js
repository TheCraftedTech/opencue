/*
 * OpenCue website – pages/versions.js
 * Download page: lists every published installer (GitHub releases, via main.js) with date, size and a download button.
 * Each button leads to the thank-you page for exactly that version.
 */
(function () {
  "use strict";

  var box = document.getElementById("versions-list");
  if (!box) { return; }

  function render(list) {
    box.innerHTML = "";
    list.forEach(function (rel, index) {
      var row = document.createElement("div");
      row.className = "ver-row" + (index === 0 ? " latest" : "");

      var name = document.createElement("div");
      name.className = "ver-name";
      var h3 = document.createElement("h3");
      h3.textContent = "v" + rel.version;
      name.appendChild(h3);
      if (index === 0) {
        var badge = document.createElement("span");
        badge.className = "badge";
        badge.setAttribute("data-i18n", "cl.latest");
        badge.setAttribute("data-en", "Latest");
        badge.textContent = OC.t("cl.latest", "Latest");
        name.appendChild(badge);
      }
      row.appendChild(name);

      var meta = document.createElement("div");
      meta.className = "ver-meta";
      meta.textContent = [rel.date ? rel.date.slice(0, 10) : "", rel.size ? (rel.size / 1048576).toFixed(1) + " MB" : ""].filter(Boolean).join(" · ");
      row.appendChild(meta);

      var actions = document.createElement("div");
      actions.className = "ver-actions";
      var notes = document.createElement("a");
      notes.className = "btn small";
      notes.href = OC.root + "changelog/#" + encodeURIComponent("v" + rel.version);
      notes.setAttribute("data-i18n", "ver.notes");
      notes.setAttribute("data-en", "What's new");
      notes.textContent = OC.t("ver.notes", "What's new");
      var dl = document.createElement("a");
      dl.className = "btn small" + (index === 0 ? " primary" : "");
      dl.href = OC.root + "download/thanks/?v=" + encodeURIComponent(rel.version);
      dl.setAttribute("data-i18n", "cl.download");
      dl.setAttribute("data-en", "Download");
      dl.textContent = OC.t("cl.download", "Download");
      actions.appendChild(notes); actions.appendChild(dl);
      row.appendChild(actions);
      box.appendChild(row);
    });
  }

  OC.whenReady(function () {
    OC.onReleases(render);
    setTimeout(function () {
      if (box.querySelector(".ver-row")) { return; }
      box.innerHTML = "";
      var p = document.createElement("p");
      p.className = "state";
      var a = document.createElement("a");
      a.href = "https://github.com/" + OC.repo + "/releases"; a.rel = "noopener";
      a.textContent = OC.t("ver.github", "All releases on GitHub");
      p.appendChild(document.createTextNode(OC.t("common.loadError", "Could not load this from GitHub right now.") + " "));
      p.appendChild(a);
      box.appendChild(p);
    }, 7000);
  });
})();
