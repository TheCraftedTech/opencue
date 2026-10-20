/*
 * OpenCue website – demo/ui.js
 * Builds the live demo window: menubar, 3D stage, cue list, executor, fixture control (programmer),
 * presets and effects. Layout, labels and behaviour follow the program's own panels (see static/css/style.css
 * and modern.css), with a stage and a presets panel added so everything can be operated by clicking.
 *
 *   var demo = OCDemo.mount(document.getElementById("demo"));
 *   demo.api.pars() / .brightness() / .movers() / .storeCue() / .play() / .effect()   // used by the guided tour
 */
(function (g) {
  "use strict";

  var D = g.OCDemo = g.OCDemo || {};

  // text for the current site language; English text is the fallback
  function T(key, en) { return g.OC ? g.OC.t(key, en) : en; }

  function pad2(n) { return (n < 10 ? "0" : "") + n; }
  function clock() { var d = new Date(); return pad2(d.getHours()) + ":" + pad2(d.getMinutes()) + ":" + pad2(d.getSeconds()); }
  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }

  var ICON_BULB = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/><path class="slash" d="M4 4l16 16"/></svg>';
  var ICON_HEART = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20.8 5.6a5 5 0 0 0-7.1 0L12 7.3l-1.7-1.7a5 5 0 0 0-7.1 7.1L12 21.5l8.8-8.8a5 5 0 0 0 0-7.1z"/></svg>';

  var TEMPLATE =
    '<div class="dm-window" role="group" aria-label="Interactive OpenCue demo" data-dkt-aria-label="demo.aria">' +
      '<div class="dm-menubar">' +
        '<div class="dm-brand"><img class="dm-logo" src="__ROOT__assets/logo-mark.svg" alt=""><span>OPENCUE</span></div>' +
        '<button class="dm-menu" type="button" data-dk="demo.m.file">File</button>' +
        '<button class="dm-menu" type="button" data-dk="demo.m.edit">Edit</button>' +
        '<button class="dm-menu" type="button" data-dk="demo.m.library">Library</button>' +
        '<button class="dm-menu" type="button" data-dk="demo.m.view">View</button>' +
        '<button class="dm-menu" type="button" data-dk="demo.m.language">Language</button>' +
        '<button class="dm-menu" type="button" data-dk="demo.m.help">Help</button>' +
        '<div class="dm-showinfo"><span class="dm-lbl" data-dk="demo.m.show">Show</span><span class="dm-showname">Demo_1</span></div>' +
        '<span class="dm-spacer"></span>' +
        '<span class="dm-clock" id="dm-clock">00:00:00</span>' +
        '<button class="dm-icon" id="dm-fs" type="button" title="Fullscreen" aria-label="Fullscreen" data-dkt="demo.fullscreen"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg></button>' +
        '<button class="dm-icon dm-blackout" id="dm-blackout" type="button" aria-pressed="false" title="Blackout" aria-label="Blackout" data-dkt="demo.blackout">' + ICON_BULB + '</button>' +
        '<span class="dm-icon dm-heart" title="DMX output (simulated)" data-dkt="demo.dmx" role="img" aria-label="DMX output (simulated)">' + ICON_HEART + '</span>' +
      '</div>' +
      '<div class="dm-workspace">' +

        '<section class="dm-panel dm-stage-p" aria-labelledby="dm-h-stage">' +
          '<h3 class="dm-panel-h" id="dm-h-stage" data-dk="demo.p.stage">3D Simulation</h3>' +
          '<div class="dm-panel-c dm-stage-c" id="dm-stage-c">' +
            '<canvas id="dm-canvas" role="img" aria-label="Stage with the lights of the demo show" data-dkt-aria-label="demo.stage.alt"></canvas>' +
            '<p class="dm-stage-hint" id="dm-stage-hint" data-dk="demo.stage.hint">Simplified stage view while the 3D scene loads …</p>' +
          '</div>' +
        '</section>' +

        '<section class="dm-panel dm-cues-p" aria-labelledby="dm-h-cues">' +
          '<h3 class="dm-panel-h" id="dm-h-cues" data-dk="demo.p.cues">Cue List</h3>' +
          '<div class="dm-panel-c">' +
            '<div class="dm-cuebar">' +
              '<select class="dm-select" disabled aria-label="Cue list" data-dkt-aria-label="demo.cl.list"><option>Default</option></select>' +
              '<button class="dm-btn" type="button" data-act="save" data-dk="demo.cl.save">Save Cue</button>' +
              '<button class="dm-btn" type="button" data-act="update" data-dk="demo.cl.update">Update</button>' +
              '<button class="dm-btn" type="button" data-act="delete" data-dk="demo.cl.delete">Delete</button>' +
              '<span class="spacer"></span>' +
              '<button class="dm-btn go" type="button" data-act="go" data-dk="demo.go">Go</button>' +
            '</div>' +
            '<div class="dm-table" id="dm-cuetable" role="table" aria-label="Cues" data-dkt-aria-label="demo.cl.table"></div>' +
            '<div class="dm-nextcue" id="dm-nextcue"></div>' +
          '</div>' +
        '</section>' +

        '<section class="dm-panel dm-exec-p" aria-labelledby="dm-h-exec">' +
          '<h3 class="dm-panel-h" id="dm-h-exec" data-dk="demo.p.exec">Executor</h3>' +
          '<div class="dm-panel-c dm-exec-c">' +
            '<div class="dm-exec-name">Default</div>' +
            '<div class="dm-exec-cue" id="dm-exec-cue"></div>' +
            '<div class="dm-exec-fader" id="dm-exec-fader"></div>' +
            '<div class="dm-exec-btns">' +
              '<button class="dm-btn go" type="button" data-exec="go"><span class="prog"></span><span class="lbl" data-dk="demo.go">Go</span></button>' +
              '<button class="dm-btn" type="button" data-exec="pause" id="dm-pause" data-dk="demo.pause">Pause</button>' +
              '<button class="dm-btn" type="button" data-exec="back" data-dk="demo.back">Back</button>' +
              '<button class="dm-btn" type="button" data-exec="stop" data-dk="demo.stop">Stop</button>' +
            '</div>' +
          '</div>' +
        '</section>' +

        '<section class="dm-panel dm-prog-p" aria-labelledby="dm-h-prog">' +
          '<h3 class="dm-panel-h" id="dm-h-prog" data-dk="demo.p.prog">Fixture Control</h3>' +
          '<div class="dm-panel-c dm-prog-c">' +
            '<div class="dm-sheet" id="dm-sheet"></div>' +
            '<div class="dm-controls" id="dm-controls"></div>' +
          '</div>' +
        '</section>' +

        '<section class="dm-panel dm-pres-p" aria-labelledby="dm-h-pres">' +
          '<h3 class="dm-panel-h" id="dm-h-pres" data-dk="demo.p.pres">Groups and Presets</h3>' +
          '<div class="dm-panel-c dm-pres-c" id="dm-pres"></div>' +
        '</section>' +

        '<section class="dm-panel dm-fx-p" aria-labelledby="dm-h-fx">' +
          '<h3 class="dm-panel-h" id="dm-h-fx" data-dk="demo.p.fx">Effects</h3>' +
          '<div class="dm-panel-c dm-fx-c" id="dm-fx"></div>' +
        '</section>' +

      '</div>' +
      '<div class="dm-toast" id="dm-toast" role="status" aria-live="polite"></div>' +
    '</div>';

  // ---------------------------------------------------------------------------------------------------

  D.mount = function (root, optionalShow) {
    var show = optionalShow || new D.Show();
    var siteRoot = (g.OC && g.OC.root) || (g.OCBoot && g.OCBoot.root) || "";
    root.innerHTML = TEMPLATE.replace("__ROOT__", siteRoot);

    var $ = function (sel) { return root.querySelector(sel); };
    var win = $(".dm-window");
    var toastEl = $("#dm-toast");

    // ---- translation: static text carries data-dk / data-dkt-*, text built here carries data-lk (+ data-len)
    var EN = {};
    function capture() {
      root.querySelectorAll("[data-dk]").forEach(function (e) { EN[e.getAttribute("data-dk")] = e.textContent; });
      root.querySelectorAll("[data-dkt-aria-label]").forEach(function (e) { EN[e.getAttribute("data-dkt-aria-label")] = e.getAttribute("aria-label"); });
      root.querySelectorAll("[data-dkt]").forEach(function (e) { EN[e.getAttribute("data-dkt")] = e.getAttribute("title"); });
    }
    function tr(key) { return T(key, EN[key]); }
    function lbl(el, key, en) { el.setAttribute("data-lk", key); el.setAttribute("data-len", en); el.textContent = T(key, en); return el; }
    function relabel() {
      root.querySelectorAll("[data-dk]").forEach(function (e) { e.textContent = tr(e.getAttribute("data-dk")); });
      root.querySelectorAll("[data-dkt-aria-label]").forEach(function (e) { e.setAttribute("aria-label", tr(e.getAttribute("data-dkt-aria-label"))); });
      root.querySelectorAll("[data-dkt]").forEach(function (e) { var s = tr(e.getAttribute("data-dkt")); e.setAttribute("title", s); e.setAttribute("aria-label", s); });
      root.querySelectorAll("[data-lk]").forEach(function (e) { e.textContent = T(e.getAttribute("data-lk"), e.getAttribute("data-len")); });
    }

    // ---- toast
    var toastTimer = null;
    function toast(msg) {
      toastEl.textContent = msg;
      toastEl.classList.add("on");
      clearTimeout(toastTimer);
      toastTimer = setTimeout(function () { toastEl.classList.remove("on"); }, 3400);
    }

    // ---- dialogs
    function dialog(opts) {
      var back = document.createElement("div");
      back.className = "dm-modal";
      var box = document.createElement("div");
      box.className = "dm-dialog"; box.setAttribute("role", "dialog"); box.setAttribute("aria-modal", "true");
      var h = document.createElement("h3"); h.textContent = opts.title; box.appendChild(h);
      var body = document.createElement("div"); body.className = "body"; box.appendChild(body);
      var inputs = [];
      (opts.fields || []).forEach(function (f) {
        var label = document.createElement("label"); label.textContent = f.label;
        var inp = document.createElement("input"); inp.type = "text"; inp.value = f.value; inp.autocomplete = "off"; inp.spellcheck = false;
        if (f.numeric) { inp.inputMode = "decimal"; }
        label.appendChild(inp); body.appendChild(label); inputs.push(inp);
      });
      if (opts.text) { var p = document.createElement("p"); p.textContent = opts.text; body.appendChild(p); }
      var hint = document.createElement("div"); hint.className = "hint"; body.appendChild(hint);
      var foot = document.createElement("div"); foot.className = "foot"; box.appendChild(foot);
      var cancel = document.createElement("button"); cancel.type = "button"; cancel.className = "dm-btn"; cancel.textContent = T("demo.cancel", "Cancel");
      var ok = document.createElement("button"); ok.type = "button"; ok.className = "dm-btn primary"; ok.textContent = opts.okLabel;
      foot.appendChild(cancel); foot.appendChild(ok);
      back.appendChild(box); win.appendChild(back);

      var previous = document.activeElement;
      function close() { back.remove(); if (previous && previous.focus) { try { previous.focus({ preventScroll: true }); } catch (e) { previous.focus(); } } }
      function submit() {
        var values = inputs.map(function (i) { return i.value.trim(); });
        var err = opts.validate ? opts.validate(values) : "";
        if (err) { hint.textContent = err; hint.className = "hint err"; return; }
        close(); opts.onOk(values);
      }
      cancel.addEventListener("click", close);
      ok.addEventListener("click", submit);
      back.addEventListener("mousedown", function (e) { if (e.target === back) { close(); } });
      box.addEventListener("keydown", function (e) {
        if (e.key === "Escape") { e.preventDefault(); close(); }
        else if (e.key === "Enter") { e.preventDefault(); submit(); }
        else if (e.key === "Tab") {
          var items = [].concat(inputs, [cancel, ok]);
          var idx = items.indexOf(document.activeElement);
          if (e.shiftKey && idx <= 0) { e.preventDefault(); items[items.length - 1].focus(); }
          else if (!e.shiftKey && idx === items.length - 1) { e.preventDefault(); items[0].focus(); }
        }
      });
      (inputs[0] || ok).focus();
      if (inputs[0]) { inputs[0].select(); }
    }

    // ---- vertical faders -----------------------------------------------------------------------

    function makeFader(spec) {
      var wrap = document.createElement("div");
      wrap.className = "vfader" + (spec.cls ? " " + spec.cls : "");
      var track = document.createElement("div");
      track.className = "vfader__track"; track.tabIndex = 0;
      track.setAttribute("role", "slider"); track.setAttribute("aria-orientation", "vertical");
      track.setAttribute("aria-valuemin", "0"); track.setAttribute("aria-valuemax", "100");
      var fill = document.createElement("div"); fill.className = "vfader__fill";
      var thumb = document.createElement("div"); thumb.className = "vfader__thumb";
      track.appendChild(fill); track.appendChild(thumb);
      var label = document.createElement("div"); label.className = "vfader__label";
      wrap.appendChild(track); wrap.appendChild(label);

      var api = { el: wrap, spec: spec, value: null };
      api.setLabel = function () { var s = T(spec.labelKey, spec.label); label.textContent = s; track.setAttribute("aria-label", s); };
      api.update = function () {
        var v = spec.get();
        var off = v === null;
        wrap.classList.toggle("vfader--off", off);
        if (off) { thumb.textContent = "–"; fill.style.height = "0%"; thumb.style.setProperty("--fv", "0%"); track.setAttribute("aria-disabled", "true"); api.value = null; return; }
        var r = Math.round(v);
        if (r === api.value) { return; }
        api.value = r;
        fill.style.height = r + "%"; thumb.style.setProperty("--fv", r + "%"); thumb.textContent = String(r);
        track.setAttribute("aria-valuenow", String(r)); track.removeAttribute("aria-disabled");
      };
      function fromPointer(e) {
        var rect = track.getBoundingClientRect();
        spec.set(clamp(100 * (1 - (e.clientY - rect.top) / rect.height), 0, 100));
        api.update();
      }
      track.addEventListener("pointerdown", function (e) {
        if (spec.get() === null) { return; }
        track.setPointerCapture(e.pointerId); fromPointer(e); e.preventDefault();
      });
      track.addEventListener("pointermove", function (e) { if (track.hasPointerCapture(e.pointerId)) { fromPointer(e); } });
      track.addEventListener("keydown", function (e) {
        var v = spec.get(); if (v === null) { return; }
        var step = e.shiftKey ? 10 : 1, nv = null;
        if (e.key === "ArrowUp" || e.key === "ArrowRight") { nv = v + step; }
        else if (e.key === "ArrowDown" || e.key === "ArrowLeft") { nv = v - step; }
        else if (e.key === "PageUp") { nv = v + 10; } else if (e.key === "PageDown") { nv = v - 10; }
        else if (e.key === "Home") { nv = 0; } else if (e.key === "End") { nv = 100; }
        if (nv !== null) { e.preventDefault(); spec.set(clamp(nv, 0, 100)); api.update(); }
      });
      api.setLabel();
      return api;
    }

    // ---- programmer: tiles, lasso, faders -------------------------------------------------------

    var sheet = $("#dm-sheet");
    var tiles = {};
    var TYPE_LABEL = { par: ["demo.t.par", "RGBW Par"], mh: ["demo.t.mh", "Moving Head"] };

    function buildSheet() {
      sheet.innerHTML = "";
      ["par", "mh"].forEach(function (type) {
        var list = show.fixtures.filter(function (f) { return f.type === type; });
        if (!list.length) { return; }
        var group = document.createElement("div"); group.className = "dm-group";
        var head = document.createElement("button"); head.type = "button"; head.className = "dm-group-h";
        var name = lbl(document.createElement("span"), TYPE_LABEL[type][0], TYPE_LABEL[type][1]);
        var count = document.createElement("span"); count.className = "count"; count.textContent = String(list.length);
        head.appendChild(name); head.appendChild(count);
        head.addEventListener("click", function () { show.select(list.map(function (f) { return f.fid; }), "replace"); });
        group.appendChild(head);
        var wrap = document.createElement("div"); wrap.className = "dm-tiles";
        list.forEach(function (f) {
          var b = document.createElement("button");
          b.type = "button"; b.className = "dm-tile"; b.setAttribute("data-fid", String(f.fid)); b.setAttribute("aria-pressed", "false");
          b.setAttribute("aria-label", f.name);
          var bar = document.createElement("span"); bar.className = "bar";
          var id = document.createElement("span"); id.className = "id"; id.textContent = String(f.fid);
          var mark = document.createElement("i"); mark.textContent = "•"; mark.hidden = true; id.appendChild(mark);
          var col = document.createElement("span"); col.className = "col";
          var pct = document.createElement("span"); pct.className = "pct"; pct.textContent = "0%";
          b.appendChild(bar); b.appendChild(id); b.appendChild(col); b.appendChild(pct);
          wrap.appendChild(b);
          tiles[f.fid] = { el: b, bar: bar, col: col, pct: pct, mark: mark };
        });
        group.appendChild(wrap);
        sheet.appendChild(group);
      });
    }

    function paintSelection() {
      Object.keys(tiles).forEach(function (fid) {
        var on = show.selection.indexOf(Number(fid)) >= 0;
        tiles[fid].el.classList.toggle("sel", on);
        tiles[fid].el.setAttribute("aria-pressed", on ? "true" : "false");
      });
    }

    // click = toggle, drag = lasso (Shift/Ctrl adds), click on empty space = deselect
    var drag = null, lasso = null;
    function tileUnder(target) { return target.closest ? target.closest(".dm-tile") : null; }
    sheet.addEventListener("pointerdown", function (e) {
      if (e.button !== 0) { return; }
      var tile = tileUnder(e.target);
      drag = { x: e.clientX, y: e.clientY, fid: tile ? Number(tile.getAttribute("data-fid")) : null, on: false, id: e.pointerId };
      try { sheet.setPointerCapture(e.pointerId); } catch (err) { /* ignore */ }
    });
    function hits(rect) {
      var out = [];
      Object.keys(tiles).forEach(function (fid) {
        var r = tiles[fid].el.getBoundingClientRect();
        var x = r.left < rect.right && r.right > rect.left && r.top < rect.bottom && r.bottom > rect.top;
        tiles[fid].el.classList.toggle("prev", x);
        if (x) { out.push(Number(fid)); }
      });
      return out;
    }
    sheet.addEventListener("pointermove", function (e) {
      if (!drag || e.pointerId !== drag.id) { return; }
      var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (!drag.on && Math.sqrt(dx * dx + dy * dy) > 5) {
        drag.on = true;
        lasso = document.createElement("div"); lasso.className = "dm-lasso"; document.body.appendChild(lasso);
      }
      if (drag.on) {
        var rect = { left: Math.min(drag.x, e.clientX), top: Math.min(drag.y, e.clientY), right: Math.max(drag.x, e.clientX), bottom: Math.max(drag.y, e.clientY) };
        lasso.style.left = rect.left + "px"; lasso.style.top = rect.top + "px";
        lasso.style.width = (rect.right - rect.left) + "px"; lasso.style.height = (rect.bottom - rect.top) + "px";
        hits(rect);
      }
    });
    function endDrag(e, cancelled) {
      if (!drag || (e && e.pointerId !== drag.id)) { return; }
      var d = drag; drag = null;
      if (d.on) {
        var rect = lasso.getBoundingClientRect();
        var ids = cancelled ? [] : hits({ left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom });
        lasso.remove(); lasso = null;
        Object.keys(tiles).forEach(function (fid) { tiles[fid].el.classList.remove("prev"); });
        if (!cancelled) { show.select(ids, e && (e.shiftKey || e.ctrlKey || e.metaKey) ? "add" : "replace"); }
      } else if (!cancelled) {
        if (d.fid !== null) { show.select([d.fid], "toggle"); }
        else { show.clearSelection(); }
      }
    }
    sheet.addEventListener("pointerup", function (e) { endDrag(e, false); });
    sheet.addEventListener("pointercancel", function (e) { endDrag(e, true); });
    sheet.addEventListener("click", function (e) {                      // keyboard (Enter/Space) only: mouse is handled above
      if (e.detail !== 0) { return; }
      var tile = tileUnder(e.target);
      if (tile) { show.select([Number(tile.getAttribute("data-fid"))], "toggle"); }
    });

    var controls = $("#dm-controls");
    var faders = [];
    function addFaderGroup(titleKey, title, specs) {
      var grp = document.createElement("div"); grp.className = "dm-fgroup";
      var h = lbl(document.createElement("div"), titleKey, title); h.className = "dm-fgroup-h";
      var body = document.createElement("div"); body.className = "dm-fgroup-b";
      specs.forEach(function (s) {
        var key = s.key;
        var f = makeFader({
          cls: s.cls, label: s.label, labelKey: s.labelKey,
          get: function () { return show.selectionHas(key) ? show.selectionValue(key) : null; },
          set: function (v) { show.setProgrammer(key, v); }
        });
        faders.push(f); body.appendChild(f.el);
      });
      grp.appendChild(h); grp.appendChild(body); controls.appendChild(grp);
    }
    addFaderGroup("demo.f.dimmer", "Dimmer", [{ key: "dimmer", cls: "vfader--neutral", label: "Dimmer", labelKey: "demo.f.dimmer" }]);
    addFaderGroup("demo.f.color", "Color", [
      { key: "r", cls: "vfader--red", label: "Red", labelKey: "demo.f.red" },
      { key: "g", cls: "vfader--green", label: "Green", labelKey: "demo.f.green" },
      { key: "b", cls: "vfader--blue", label: "Blue", labelKey: "demo.f.blue" }]);
    addFaderGroup("demo.f.position", "Position", [
      { key: "pan", cls: "vfader--neutral", label: "Pan", labelKey: "demo.f.pan" },
      { key: "tilt", cls: "vfader--neutral", label: "Tilt", labelKey: "demo.f.tilt" }]);

    var hintEl = document.createElement("p"); hintEl.className = "dm-prog-hint"; hintEl.id = "dm-prog-hint";
    lbl(hintEl, "demo.prog.hint", "Click the tiles to select fixtures – then use the faders.");
    controls.appendChild(hintEl);

    // ---- presets: groups, colours, positions ---------------------------------------------------

    var presBox = $("#dm-pres");
    var chipEls = [], posBtns = [];

    function needSelection() {
      if (show.selection.length) { return false; }
      toast(T("demo.select.first", "Select fixtures first – click the tiles in Fixture Control."));
      return true;
    }
    function section(key, en) {
      var wrap = document.createElement("div"); wrap.className = "dm-pre-sec";
      var h = lbl(document.createElement("div"), key, en); h.className = "dm-fgroup-h";
      var body = document.createElement("div"); body.className = "dm-pre-body";
      wrap.appendChild(h); wrap.appendChild(body); presBox.appendChild(wrap);
      return body;
    }
    function button(parent, key, en, onClick) {
      var b = document.createElement("button"); b.type = "button"; b.className = "dm-btn";
      lbl(b, key, en); b.addEventListener("click", onClick); parent.appendChild(b); return b;
    }

    function buildPresets() {
      presBox.innerHTML = "";
      var groups = section("demo.pre.groups", "Groups");
      [["demo.g.pars", "Pars", [1, 2, 3, 4]], ["demo.g.movers", "Movers", [5, 6]], ["demo.g.all", "All", [1, 2, 3, 4, 5, 6]]].forEach(function (gr) {
        button(groups, gr[0], gr[1], function () { show.select(gr[2], "replace"); });
      });
      button(groups, "demo.g.none", "None", function () { show.clearSelection(); });

      var colors = section("demo.pre.colors", "Colors");
      colors.classList.add("chips");
      D.Show.COLORS.forEach(function (c) {
        var b = document.createElement("button"); b.type = "button"; b.className = "dm-chip";
        b.style.background = "rgb(" + Math.round(c.rgb[0] * 2.55) + "," + Math.round(c.rgb[1] * 2.55) + "," + Math.round(c.rgb[2] * 2.55) + ")";
        b.setAttribute("data-color", c.id); b.setAttribute("title", c.id); b.setAttribute("aria-label", c.id);
        b.addEventListener("click", function () { if (!needSelection()) { show.setColor(c.id); } });
        colors.appendChild(b); chipEls.push(b);
      });

      var positions = section("demo.pre.positions", "Positions (moving heads)");
      [["center", "demo.pos.center", "Center"], ["left", "demo.pos.left", "Left"], ["right", "demo.pos.right", "Right"],
       ["cross", "demo.pos.cross", "Cross"], ["audience", "demo.pos.audience", "Audience"]].forEach(function (p) {
        posBtns.push(button(positions, p[1], p[2], function () {
          if (needSelection()) { return; }
          if (!show.applyPosition(p[0])) { toast(T("demo.fx.needsMh", "This needs moving heads – select fixture 5 or 6.")); }
        }));
      });

      var foot = document.createElement("div"); foot.className = "dm-pre-foot";
      var clear = button(foot, "demo.clear", "Clear manual values", function () { clearAll(); });
      clear.classList.add("clear");
      presBox.appendChild(foot);
    }

    function clearAll() {
      var had = show.selection.length || show.hasProgrammer() || Object.keys(show.fx).length;
      show.clearSelection(); show.clearProgrammer(); show.clearEffects();
      toast(had ? T("demo.cleared", "Cleared: selection, manual values and effects are released.") : T("demo.cleared.none", "Nothing to clear."));
    }

    // ---- effects panel -------------------------------------------------------------------------

    var fxBox = $("#dm-fx");
    var fxTiles = {};
    var FX_NAME = { rainbow: "Rainbow", chase: "Chase", pulse: "Pulse", fire: "Fire", circle: "Circle" };
    var FX_CAT = { color: "Color", dimmer: "Dimmer", position: "Position" };
    function buildEffects() {
      fxBox.innerHTML = "";
      D.Show.EFFECTS.forEach(function (eff) {
        var b = document.createElement("button"); b.type = "button"; b.className = "dm-fxtile"; b.setAttribute("aria-pressed", "false");
        var n = lbl(document.createElement("span"), "demo.fx." + eff.id, FX_NAME[eff.id]); n.className = "n";
        var c = lbl(document.createElement("span"), "demo.fxc." + eff.cat, FX_CAT[eff.cat]); c.className = "c";
        b.appendChild(n); b.appendChild(c);
        b.addEventListener("click", function () {
          if (needSelection()) { return; }
          if (show.toggleEffect(eff.id) === 0) { toast(T("demo.fx.needsMh", "This needs moving heads – select fixture 5 or 6.")); }
        });
        fxBox.appendChild(b); fxTiles[eff.id] = b;
      });
      var off = button(fxBox, "demo.fx.off", "Clear effects", function () { show.clearEffects(); });
      off.id = "dm-fx-off";
    }
    function paintEffects() {
      Object.keys(fxTiles).forEach(function (id) {
        var on = show.effectOn(id);
        fxTiles[id].classList.toggle("on", on);
        fxTiles[id].setAttribute("aria-pressed", on ? "true" : "false");
      });
    }

    // ---- executor ------------------------------------------------------------------------------

    var execFader = makeFader({
      cls: "", label: "Mix", labelKey: "demo.ex.mix",
      get: function () { return show.mix; },
      set: function (v) { show.setMix(v); }
    });
    $("#dm-exec-fader").appendChild(execFader.el);
    var goProg = $('[data-exec="go"] .prog');
    var pauseBtn = $("#dm-pause");

    function paintExecutor() {
      var cue = show.activeCue();
      $("#dm-exec-cue").textContent = cue
        ? T("demo.ex.active", "Active: {cue}").replace("{cue}", "Cue " + D.fmtNum(cue.number))
        : T("demo.ex.none", "No active cue");
      pauseBtn.textContent = show.paused ? T("demo.resume", "Resume") : T("demo.pause", "Pause");
    }

    // playback: same effects as the program's Go / Back / Pause / Stop
    function go(idx) {
      var cue = idx === undefined ? show.goNext() : show.goIndex(idx);
      if (!cue) { toast(T("demo.cl.nonext", "No further cue")); return null; }
      if (show.hasProgrammer()) { toast(T("demo.override", "Manual values still override the cue. Press Clear to release them.")); }
      return cue;
    }
    function back() { if (!show.back()) { toast(T("demo.cl.noprev", "No previous cue")); } }

    root.querySelectorAll("[data-exec]").forEach(function (b) {
      b.addEventListener("click", function () {
        var what = b.getAttribute("data-exec");
        if (what === "go") { go(); }
        else if (what === "back") { back(); }
        else if (what === "pause") { if (!show.pause()) { toast(T("demo.nopause", "Nothing to pause – no fade is running.")); } }
        else if (what === "stop") { show.stop(); }
      });
    });

    // ---- cue list ------------------------------------------------------------------------------

    var table = $("#dm-cuetable");
    var selectedCue = -1;
    var rowEls = [];

    var lastTap = { idx: -1, t: 0 };

    function renderCues() {
      table.innerHTML = "";
      rowEls = [];
      var head = document.createElement("div"); head.className = "dm-row head"; head.setAttribute("role", "row");
      [["", ""], ["demo.cl.num", "Cue #"], ["demo.cl.name", "Name"], ["demo.cl.fade", "Fade"], ["demo.cl.delay", "Delay"], ["demo.cl.trigger", "Trigger"]].forEach(function (c, i) {
        var d = document.createElement("div"); d.setAttribute("role", "columnheader");
        if (c[0]) { d.textContent = T(c[0], c[1]); }
        if (i === 1 || i === 3 || i === 4) { d.className = i === 1 ? "num" : "fade"; }
        head.appendChild(d);
      });
      table.appendChild(head);

      if (!show.cues.length) {
        var empty = document.createElement("div"); empty.className = "dm-empty";
        empty.textContent = T("demo.cl.empty", "No cues yet. Program some values and click 'Save Cue'.");
        table.appendChild(empty);
      }
      var next = show.nextIdx();
      show.cues.forEach(function (cue, idx) {
        var row = document.createElement("div");
        row.className = "dm-row" + (idx === show.activeIdx ? " is-active" : "") + (idx === next ? " is-next" : "") + (idx === selectedCue ? " is-selected" : "");
        row.setAttribute("role", "row"); row.tabIndex = 0; row.setAttribute("data-idx", String(idx));
        var cells = [
          ['<span class="dm-dot"></span><span class="dm-progress"><i></i></span>', "status"],
          [D.fmtNum(cue.number), "num"], [cue.name, "name"], [cue.fade.toFixed(1), "fade"], [(cue.delay || 0).toFixed(1), "fade"], [cue.trigger, "trig"]
        ];
        cells.forEach(function (c, i) {
          var d = document.createElement("div"); d.className = c[1]; d.setAttribute("role", "cell");
          if (i === 0) { d.innerHTML = c[0]; d.style.padding = "0 0 0 .5rem"; } else { d.textContent = c[0]; }
          row.appendChild(d);
        });
        // click selects; a second click or tap on the same cue within 450 ms plays it (a real dblclick does not
        // fire reliably on touch screens, and the rows are rebuilt on every click)
        row.addEventListener("click", function () {
          var now = Date.now();
          if (lastTap.idx === idx && now - lastTap.t < 450) { lastTap.idx = -1; go(idx); return; }
          lastTap = { idx: idx, t: now };
          selectedCue = idx; renderCues();
        });
        row.addEventListener("keydown", function (e) {
          if (e.key === "Enter") { e.preventDefault(); go(idx); }
          else if (e.key === " ") { e.preventDefault(); selectedCue = idx; renderCues(); }
        });
        table.appendChild(row);
        rowEls.push(row);
      });
      var nx = show.cues[next];
      $("#dm-nextcue").textContent = nx
        ? T("demo.cl.next", "Next cue: {cue}").replace("{cue}", "Cue " + D.fmtNum(nx.number) + " – " + nx.name)
        : T("demo.cl.nonext", "No further cue");
      paintExecutor();
    }

    function selectedCueNumber() { return selectedCue >= 0 && show.cues[selectedCue] ? show.cues[selectedCue].number : null; }

    function saveCue(number, name) {
      var res = show.store(number, name);
      toast(T(res.created ? "demo.cl.stored" : "demo.cl.updated", res.created ? "Cue {n} stored." : "Cue {n} updated.").replace("{n}", D.fmtNum(number)));
      return res;
    }

    root.querySelector('[data-act="go"]').addEventListener("click", function () { go(); });
    root.querySelector('[data-act="update"]').addEventListener("click", function () {
      var cue = show.updateActive();
      toast(cue ? T("demo.cl.updated", "Cue {n} updated.").replace("{n}", D.fmtNum(cue.number)) : T("demo.cl.noactive", "No active cue to update – play a cue first."));
    });
    root.querySelector('[data-act="save"]').addEventListener("click", function () {
      var n = show.nextFreeNumber();
      dialog({
        title: T("demo.cl.saveTitle", "Save cue"),
        okLabel: T("demo.cl.save", "Save Cue"),
        fields: [
          { label: T("demo.cl.saveNum", "Cue number"), value: String(n), numeric: true },
          { label: T("demo.cl.saveName", "Name"), value: "Cue " + n }
        ],
        validate: function (v) {
          var num = Number(v[0]);
          if (!v[0] || !isFinite(num) || num <= 0) { return T("demo.cl.badNum", "Please enter a cue number greater than 0."); }
          return "";
        },
        onOk: function (v) { saveCue(Number(v[0]), v[1]); }
      });
    });
    root.querySelector('[data-act="delete"]').addEventListener("click", function () {
      var num = selectedCueNumber();
      if (num === null) { toast(T("demo.cl.pick", "Select a cue in the list first.")); return; }
      dialog({
        title: T("demo.cl.delTitle", "Delete cue"),
        okLabel: T("demo.cl.delete", "Delete"),
        text: T("demo.cl.delBody", "Delete cue {n} from the list?").replace("{n}", D.fmtNum(num)),
        onOk: function () { selectedCue = -1; show.deleteCue(num); }
      });
    });

    // ---- menubar -------------------------------------------------------------------------------

    root.querySelectorAll(".dm-menu").forEach(function (b) {
      b.addEventListener("click", function () { toast(T("demo.menuHint", "The menus belong to the real program – this demo shows its panels.")); });
    });
    var fsBtn = $("#dm-fs");
    if (D.fs && D.fs.enabled()) { fsBtn.addEventListener("click", function () { D.fs.toggle(win); }); }
    else { fsBtn.hidden = true; }
    var blackoutBtn = $("#dm-blackout");
    blackoutBtn.addEventListener("click", function () { show.setBlackout(); });

    // ---- stage (simplified canvas first, the real 3D scene as soon as it has loaded) -----------

    var canvas2d = $("#dm-canvas");
    var stage = new D.Stage(canvas2d, show, { selection: true });
    var stageHint = $("#dm-stage-hint");
    var quality = (/[?&]quality=(low|high)\b/.exec(location.search) || [])[1];

    function upgradeTo3D() {
      if (!g.OCBoot || (/[?&]3d=0\b/.test(location.search))) { return; }
      g.OCBoot.loadScripts(["assets/vendor/three/three-lite.js", "assets/demo/stage3d.js"]).then(function () {
        if (!D.Stage3D || !D.Stage3D.supported()) { return; }
        var s3 = new D.Stage3D($("#dm-stage-c"), show, { ui: true, quality: quality, onSlow: function () { toast(T("demo.slow", "Your device is a bit slow – the 3D view switched to a lighter mode.")); } });
        canvas2d.style.display = "none";
        if (stageHint) { stageHint.style.display = "none"; }
        stage = s3;
      }).catch(function (e) { if (g.console) { console.warn("3D stage not available, keeping the simplified view:", e); } });
    }

    var clockEl = $("#dm-clock");
    var lastUi = 0, visible = true;
    if (g.IntersectionObserver) { new g.IntersectionObserver(function (en) { visible = en[0].isIntersecting; }).observe(win); }

    function updateUi(out) {
      // tiles show what the fixture really outputs, faders show the selection's values
      for (var i = 0; i < out.length; i++) {
        var o = out[i], tl = tiles[o.fid];
        if (!tl) { continue; }
        var lvl = o.level;
        tl.bar.style.transform = "scaleY(" + lvl.toFixed(3) + ")";
        tl.col.style.background = lvl > 0.01
          ? "rgb(" + Math.round(o.r * 255 * (0.25 + 0.75 * lvl)) + "," + Math.round(o.g * 255 * (0.25 + 0.75 * lvl)) + "," + Math.round(o.b * 255 * (0.25 + 0.75 * lvl)) + ")"
          : "#111";
        var p = Math.round(lvl * 100);
        tl.pct.textContent = p + "%";
        tl.el.classList.toggle("live", p > 0);
        tl.mark.hidden = !show.programmer[o.fid];
      }
      faders.forEach(function (f) { f.update(); });
      execFader.update();

      var prog = show.fadeProgress();
      var activeRow = rowEls[show.activeIdx];
      rowEls.forEach(function (r) { var pb = r.querySelector(".dm-progress"); if (pb) { pb.classList.remove("on"); } });
      if (activeRow && prog !== null) {
        var pb = activeRow.querySelector(".dm-progress");
        pb.classList.add("on"); pb.firstChild.style.width = (prog * 100).toFixed(1) + "%";
      }
      goProg.style.transform = prog !== null && show.activeIdx >= 0 ? "scaleX(" + prog.toFixed(3) + ")" : "scaleX(0)";
      clockEl.textContent = clock();

      var hasSel = show.selection.length > 0;
      hintEl.hidden = hasSel;
      controls.classList.toggle("is-idle", !hasSel);
    }

    function frame(now) {
      if (visible && !document.hidden) {
        show.tick(now);
        var out = show.output(now);
        stage.render(out);
        if (now - lastUi > 80) { lastUi = now; updateUi(out); }
      }
      g.requestAnimationFrame(frame);
    }

    // ---- wiring --------------------------------------------------------------------------------

    show.on("selection", function () { paintSelection(); });
    show.on("fx", paintEffects);
    show.on("cues", renderCues);
    show.on("active", function () { renderCues(); });
    show.on("blackout", function (on) { blackoutBtn.setAttribute("aria-pressed", on ? "true" : "false"); });

    capture();
    buildSheet();
    buildPresets();
    buildEffects();
    renderCues();
    paintSelection();
    paintEffects();
    relabel();

    if (g.OC && g.OC.onLang) {
      g.OC.onLang(function () {
        relabel();
        faders.forEach(function (f) { f.setLabel(); });
        execFader.setLabel();
        renderCues(); paintExecutor();
      });
    }

    g.requestAnimationFrame(frame);
    upgradeTo3D();

    // actions the guided tour (pages/demo.js) triggers: the same things a visitor would click
    var api = {
      pars: function () { show.select([1, 2, 3, 4], "replace"); },
      brightness: function () {
        if (!show.selection.length) { api.pars(); }
        show.setProgrammer("dimmer", 80); show.setColor("magenta");
      },
      movers: function () {
        show.select([5, 6], "replace");
        show.setProgrammer("dimmer", 100); show.setColor("white");
        show.applyPosition("cross");
      },
      storeCue: function () {
        var res = saveCue(show.nextFreeNumber(), T("demo.tour.cueName", "My look"));
        selectedCue = show.cueByNumber(res.cue.number); renderCues();
        return res.cue.number;
      },
      play: function () {
        show.clearSelection(); show.clearProgrammer();
        go(show.cueByNumber(2) >= 0 ? show.cueByNumber(2) : 0);
      },
      effect: function () {
        show.select([1, 2, 3, 4], "replace");
        if (!show.effectOn("rainbow")) { show.toggleEffect("rainbow"); }
      },
      clear: clearAll
    };

    return { show: show, api: api, toast: toast, fullscreen: function () { if (D.fs && D.fs.enabled()) { D.fs.toggle(win); } }, get stage() { return stage; } };
  };
})(window);
