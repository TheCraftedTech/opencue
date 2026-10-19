/*
 * OpenCue website – theme.js
 * Dark or light. Dark is the default (like the program itself), whatever the system prefers.
 * The toggle in the header switches to light and back and remembers the choice
 * (localStorage, this browser only; no cookies).
 * ?theme=dark|light in the address forces a theme for this visit (handy for screenshots).
 * Loaded in <head> without defer so the saved theme is set before the first paint.
 */
(function () {
  "use strict";

  var root = document.documentElement;
  var KEY = "opencue-theme";

  function read() {
    try { return window.localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function write(value) {
    try { window.localStorage.setItem(KEY, value); } catch (e) { /* blocked: fine */ }
  }

  function effective() {
    return root.getAttribute("data-theme") || "dark";
  }

  var fromUrl = /[?&]theme=(dark|light)\b/.exec(window.location.search);
  var start = fromUrl ? fromUrl[1] : read();
  if (start === "dark" || start === "light") { root.setAttribute("data-theme", start); }

  // The button's label is translated in main.js (keys theme.toLight / theme.toDark).
  function labelButton(btn) {
    var key = effective() === "dark" ? "theme.toLight" : "theme.toDark";
    btn.setAttribute("data-i18n-aria-label", key);
    btn.setAttribute("data-i18n-title", key);
    document.dispatchEvent(new CustomEvent("opencue:relabel"));
  }

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("theme-toggle");
    if (!btn) { return; }
    labelButton(btn);
    btn.addEventListener("click", function () {
      var next = effective() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      write(next);
      labelButton(btn);
    });
  });
})();
