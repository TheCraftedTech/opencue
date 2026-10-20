/*
 * OpenCue website – pages/demo.js
 * Mounts the live demo into the page.
 */
(function () {
  "use strict";

  var host = document.getElementById("demo");
  if (!host || !window.OCDemo) { return; }

  OC.whenReady(function () {
    host.innerHTML = "";
    OCDemo.mount(host);
  });
})();
