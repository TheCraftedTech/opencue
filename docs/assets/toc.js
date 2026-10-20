/*
 * OpenCue website – toc.js
 * Highlights the entry of the "On this page" list (.toc) that belongs to the section in view.
 * Static pages get it automatically; pages that build their list from loaded text call OCToc.init(listEl)
 * after they filled it.
 */
(function (g) {
  "use strict";

  var observer = null;

  function init(toc) {
    if (!toc || !("IntersectionObserver" in g)) { return; }
    var links = Array.prototype.slice.call(toc.querySelectorAll('a[href^="#"]'));
    var targets = [];
    links.forEach(function (a) {
      var el = document.getElementById(decodeURIComponent(a.getAttribute("href").slice(1)));
      if (el) { targets.push({ link: a, el: el }); }
    });
    if (!targets.length) { return; }

    if (observer) { observer.disconnect(); }
    var visible = {};
    observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) { visible[entry.target.id] = entry.isIntersecting; });
      var active = null;
      for (var i = 0; i < targets.length; i++) {
        if (visible[targets[i].el.id]) { active = targets[i]; break; }
      }
      if (!active) { return; }
      links.forEach(function (a) { a.classList.toggle("on", a === active.link); });
    }, { rootMargin: "-130px 0px -60% 0px", threshold: 0 });
    targets.forEach(function (tg) { observer.observe(tg.el); });
  }

  g.OCToc = { init: init };

  g.OC.whenReady(function () { init(document.querySelector(".toc")); });
})(window);
