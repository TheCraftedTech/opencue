/*
 * OpenCue website – pages/thanks.js
 * The page every download button leads to. It shows a short loading animation, starts the installer download
 * (the direct link comes from the GitHub release data main.js has loaded) and then says thank you.
 * If no release information arrives, it points to the releases page instead of waiting forever.
 */
(function () {
  "use strict";

  var root = document.getElementById("thanks");
  var title = document.getElementById("thanks-title");
  var lead = document.getElementById("thanks-lead");
  var file = document.getElementById("thanks-file");
  var fallbackText = document.getElementById("thanks-fallback-text");
  var manual = document.getElementById("thanks-manual");
  if (!root) { return; }

  // ?v=1.0.0 asks for one particular version (from the changelog or the version list); without it: the newest
  var wanted = ((/[?&]v=v?([\w.\-]+)/.exec(window.location.search)) || [])[1] || "";
  if (wanted) {
    manual.removeAttribute("data-direct");
    manual.href = "https://github.com/" + OC.repo + "/releases/tag/v" + wanted;
    file.removeAttribute("data-filename");
  }

  var state = "loading";            // loading -> done | failed
  var release = null;

  function render() {
    if (state === "done") {
      title.textContent = OC.t("thanks.title.done", "Thank you for downloading OpenCue!");
      lead.textContent = OC.t("thanks.lead.done", "The installer {file} is on its way. Open it when the download has finished and follow the setup.").replace("{file}", release.file);
      fallbackText.textContent = OC.t("thanks.fallback.done", "Download did not start?");
      file.hidden = false;
    } else if (state === "failed") {
      title.textContent = OC.t("thanks.title.failed", "Your download is one click away");
      lead.textContent = OC.t("thanks.lead.failed", "We could not look up the newest version just now. The releases page on GitHub has the installer.");
      fallbackText.textContent = OC.t("thanks.fallback.failed", "Open the releases page:");
    } else {
      title.textContent = OC.t("thanks.title.loading", "Preparing your download …");
      lead.textContent = OC.t("thanks.lead.loading", "OpenCue is free – the installer starts in a moment.");
      fallbackText.textContent = OC.t("thanks.fallback.loading", "Nothing happening?");
    }
    root.classList.toggle("done", state === "done");
  }

  function start(rel) {
    if (release) { return; }
    release = rel;
    if (wanted) { manual.href = rel.url; file.textContent = rel.file; }
    setTimeout(function () {
      var a = document.createElement("a");
      a.href = rel.url; a.download = rel.file; a.rel = "noopener";
      document.body.appendChild(a); a.click(); a.remove();
      state = "done";
      render();
    }, 1500);
  }

  OC.whenReady(function () {
    render();
    OC.onLang(render);
    if (wanted) {
      OC.onReleases(function (list) {
        for (var i = 0; i < list.length; i++) { if (list[i].version === wanted) { start(list[i]); return; } }
        if (!release) { state = "failed"; render(); }
      });
    } else {
      OC.onRelease(start);
    }
    setTimeout(function () {
      if (!release) { state = "failed"; render(); }
    }, 6000);
  });
})();
