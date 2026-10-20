/*
 * OpenCue website – pages/home.js
 * The hero stage on the home page: a small self-running show that types real console commands and plays
 * them on the stage. It starts with the light-weight canvas view and switches to the real 3D stage as soon as
 * that has loaded (wide screens, no "save data", WebGL available). With "reduce motion" it shows one still look.
 */
(function () {
  "use strict";

  var box = document.getElementById("hero-box");
  var canvas = document.getElementById("hero-stage");
  var cmdEl = document.getElementById("hero-cmd");
  if (!box || !canvas || !window.OCDemo) { return; }

  var show = new OCDemo.Show();
  var stage = new OCDemo.Stage(canvas, show, { selection: false, labels: false });
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---- upgrade to the real 3D stage on capable screens
  var wide = window.matchMedia && window.matchMedia("(min-width: 900px)").matches;
  var saver = navigator.connection && navigator.connection.saveData;
  var quality = (/[?&]quality=(low|high)\b/.exec(location.search) || [])[1];
  if (wide && !saver && !/[?&]3d=0\b/.test(location.search)) {
    OCBoot.loadScripts(["assets/vendor/three/three-lite.js", "assets/demo/stage3d.js"]).then(function () {
      if (!OCDemo.Stage3D || !OCDemo.Stage3D.supported()) { return; }
      var s3 = new OCDemo.Stage3D(box, show, { ui: false, selection: false, pick: false, zoom: false, sway: !reduce, quality: quality });
      canvas.style.display = "none";
      stage.stop();
      s3.canvas.classList.add("hero-3d");
      stage = s3;
      if (reduce) { runFor(1600); } else { runLoop(); }
    }).catch(function () { /* keep the canvas view */ });
  }

  // the 3D stage is driven from here (the canvas view has its own loop)
  function runLoop() {
    function frame() {
      var now = show.now();
      show.tick(now);
      stage.render(show.output(now));
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  // "reduce motion": a short burst of frames so the lights settle, then a still picture
  function runFor(ms) {
    var end = performance.now() + ms;
    (function frame() {
      var now = show.now();
      show.tick(now);
      stage.render(show.output(now));
      if (performance.now() < end) { requestAnimationFrame(frame); }
    })();
  }

  if (reduce) {
    show._applyCue(show.cues[2], true);          // Magenta cross, no animation
    show.activeIdx = 2;
    cmdEl.textContent = "Go Cue 3";
    stage.render(show.output(show.now()));
    return;
  }

  var scenes = [
    { cmd: "Go Cue 2", run: function () { show.goIndex(1); } },
    { cmd: "Go Cue 3", run: function () { show.goIndex(2); } },
    { cmd: "Fixture 1 Thru 4 At 90 Color Amber", run: function () {
        show.select([1, 2, 3, 4], "replace");
        show.setProgrammer("dimmer", 90); show.setColor("amber");
      } },
    { cmd: "Clear", run: function () { show.clearProgrammer(); show.clearSelection(); } },
    { cmd: "Go Cue 4", run: function () { show.goIndex(3); } },
    { cmd: "Go Cue 1", run: function () { show.goIndex(0); } }
  ];

  var index = 0;
  var timer = null;

  function typeText(text, done) {
    var i = 0;
    cmdEl.textContent = "";
    (function step() {
      if (i <= text.length) {
        cmdEl.textContent = text.slice(0, i);
        i += 1;
        timer = setTimeout(step, 38 + Math.random() * 30);
      } else { done(); }
    })();
  }

  function next() {
    var scene = scenes[index % scenes.length];
    index += 1;
    typeText(scene.cmd, function () {
      timer = setTimeout(function () {
        scene.run();
        timer = setTimeout(next, scene.cmd === "Clear" ? 1100 : 3400);
      }, 380);
    });
  }

  stage.start();                       // canvas view runs its own loop; the 3D stage is driven by runLoop()
  show.goIndex(0);
  timer = setTimeout(next, 900);

  // do not run the script while the tab is hidden
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) { clearTimeout(timer); }
    else { timer = setTimeout(next, 600); }
  });
})();
