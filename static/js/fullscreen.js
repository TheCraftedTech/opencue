/* Vollbild fuer Panels (Video/Audio-Player, Livestream, Timecode).
 * Das echte Vollbild (Fullscreen API) gibt es nicht ueberall: auf iPad/iPhone nicht fuer beliebige Elemente und in einer als PWA installierten
 * App gar nicht. Deshalb ist das Vollbild hier ein EIGENES: das Panel-Element wird in die Seite verschoben und legt sich ueber die ganze
 * Oberflaeche (Menueleiste, andere Panels) - Dialoge (z. B. "Programm beenden"), Menues und Meldungen liegen weiterhin davor. Wo das echte
 * Vollbild moeglich ist (Desktop-Fenster, normaler Browser), wird es zusaetzlich angefordert.
 * Beenden: Knopf/Doppelklick des Panels, Escape (oder Escape des echten Vollbilds). Wird das Panel entfernt, endet das Vollbild von selbst.
 * Laeuft nach app.js, vor den Panel-Dateien. */
const OCFullscreen = (() => {
  const ua = navigator.userAgent || "";
  const ios = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const standalone = (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) || navigator.standalone === true;
  let nativeEnabled = !ios && !standalone;
  const active = new Set();

  const nativeElement = () => document.fullscreenElement || document.webkitFullscreenElement || null;
  const isFull = (wrap) => wrap.classList.contains("oc-fs");
  const mediaStates = (wrap) => [...wrap.querySelectorAll("video, audio")].map((m) => [m, !m.paused]);

  /** Ein Medium pausiert, sobald sein Element aus der Seite genommen wird - nach dem Verschieben wieder starten, was lief. */
  function resume(states) {
    states.forEach(([media, wasPlaying]) => {
      if (!wasPlaying) return;
      const promise = media.play();
      if (promise && promise.catch) promise.catch(() => { /* Browser verlangt erst eine Bedienung */ });
    });
  }

  function announce(wrap, on) {
    wrap.dispatchEvent(new CustomEvent("ocfullscreen", { detail: on }));
  }

  function enter(wrap) {
    if (isFull(wrap) || !wrap.parentNode) return;
    const states = mediaStates(wrap);
    const panel = wrap.closest("[data-panel-id]");
    const placeholder = document.createComment("oc-fullscreen");
    wrap.parentNode.insertBefore(placeholder, wrap);
    wrap._ocFs = { placeholder, panel };
    if (panel) panel._ocFsWrap = wrap;
    document.body.appendChild(wrap);
    wrap.classList.add("oc-fs");
    document.documentElement.classList.add("oc-fs-active");
    active.add(wrap);
    resume(states);
    if (nativeEnabled) {
      const request = wrap.requestFullscreen || wrap.webkitRequestFullscreen;
      if (request) {
        try {
          const promise = request.call(wrap);
          if (promise && promise.catch) promise.catch(() => { /* nicht erlaubt: das eigene Vollbild genuegt */ });
        } catch (err) { /* dito */ }
      }
    }
    announce(wrap, true);
  }

  function exit(wrap) {
    if (!isFull(wrap)) return;
    const info = wrap._ocFs;
    if (nativeElement() === wrap) {
      try { (document.exitFullscreen || document.webkitExitFullscreen).call(document); } catch (err) { /* schon beendet */ }
    }
    const states = mediaStates(wrap);
    wrap._ocFs = null;
    wrap.classList.remove("oc-fs");
    active.delete(wrap);
    if (info && info.panel) delete info.panel._ocFsWrap;
    if (info && info.placeholder.isConnected) info.placeholder.parentNode.insertBefore(wrap, info.placeholder);
    else wrap.remove();                                          // das Panel gibt es nicht mehr
    if (info) info.placeholder.remove();
    if (!active.size) document.documentElement.classList.remove("oc-fs-active");
    if (overlayHost === wrap) releaseOverlays();
    resume(states);
    announce(wrap, false);
  }

  // Ein offener Dialog bekommt Escape zuerst: schon in der Fangphase merken, ob beim Tastendruck einer offen war (die Dialog-Handler schliessen ihn,
  // bevor dieser hier drankommt).
  let dialogWasOpen = false;
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") dialogWasOpen = (typeof Modal !== "undefined" && Modal._stack.length > 0) || !!document.querySelector(".fx-panel-modal-backdrop, .fx-library-backdrop");
  }, true);
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || dialogWasOpen || event.defaultPrevented || !active.size) return;
    exit([...active].pop());
  });
  // Im ECHTEN Vollbild (Fullscreen API) zeigt der Browser nur das Vollbild-Element und seine Kinder: alles andere - auch Dialoge mit hohem z-index - liegt darunter und waere unsichtbar
  // (z. B. die Rueckfrage "Zuruecksetzen" oder "Programm beenden"). Darum ziehen Dialoge, Meldungen und spaeter geoeffnete Overlays solange ins Vollbild-Element um und gehen danach zurueck.
  // Reihenfolge der Ebenen bleibt: Panels < Vollbild < Menues/Dialoge < Meldungen (z-index in style.css/modern.css).
  const OVERLAYS = ".modal-backdrop, .fx-panel-modal-backdrop, .fx-library-backdrop, #toast-container";
  const adopted = [];
  let overlayHost = null;
  let overlayObserver = null;
  const adopt = (node, host) => {
    if (!node || node === host || node.contains(host) || host.contains(node)) return;
    adopted.push({ node, parent: node.parentNode, next: node.nextSibling });
    host.appendChild(node);
  };
  function hostOverlays(host) {
    overlayHost = host;
    document.querySelectorAll(OVERLAYS).forEach((node) => { if (node.parentNode === document.body) adopt(node, host); });
    overlayObserver = new MutationObserver((records) => {
      records.forEach((record) => record.addedNodes.forEach((node) => {
        if (node.nodeType !== 1 || node.parentNode !== document.body || node === host || /^(SCRIPT|STYLE|LINK|TEMPLATE)$/.test(node.tagName) || node.hasAttribute("data-panel-id")) return;
        adopt(node, host);
      }));
    });
    overlayObserver.observe(document.body, { childList: true });
  }
  function releaseOverlays() {
    if (overlayObserver) overlayObserver.disconnect();
    overlayObserver = null;
    overlayHost = null;
    adopted.reverse().forEach(({ node, parent, next }) => {
      if (!node.isConnected) return;                                   // vom Besitzer schon entfernt (z. B. ein Menue)
      if (parent && parent.isConnected) parent.insertBefore(node, next && next.parentNode === parent ? next : null);
      else document.body.appendChild(node);
    });
    adopted.length = 0;
  }
  const syncOverlays = () => {
    const element = nativeElement();
    if (element && active.has(element)) {
      if (overlayHost !== element) { releaseOverlays(); hostOverlays(element); }
    } else if (overlayHost) {
      releaseOverlays();
    }
  };
  const onNativeChange = () => {
    syncOverlays();
    if (!nativeElement()) [...active].forEach(exit);
  };
  document.addEventListener("fullscreenchange", onNativeChange);
  document.addEventListener("webkitfullscreenchange", onNativeChange);
  setInterval(() => {
    active.forEach((wrap) => { if (wrap._ocFs && !wrap._ocFs.placeholder.isConnected) exit(wrap); });
  }, 1000);

  return {
    isFull,
    enter,
    exit,
    toggle(wrap) { if (isFull(wrap)) exit(wrap); else enter(wrap); },
    /** Das Panel-Element eines Inhalts - auch waehrend das Vollbild den Inhalt aus dem Panel herausgenommen hat. */
    panelOf(wrap) { return wrap.closest("[data-panel-id]") || (wrap._ocFs && wrap._ocFs.panel) || null; },
    /** Wie panelEl.querySelector(selector), findet den Inhalt aber auch im Vollbild. */
    query(panelEl, selector) {
      const found = panelEl.querySelector(selector);
      return found || (panelEl._ocFsWrap && panelEl._ocFsWrap.matches(selector) ? panelEl._ocFsWrap : null);
    },
    get native() { return nativeEnabled; },
    /** Nur fuer Tests/Sonderfaelle: das echte Vollbild zusaetzlich anfordern oder nicht. */
    setNative(on) { nativeEnabled = !!on; },
    get ios() { return ios; },
    get standalone() { return standalone; },
  };
})();
window.OCFullscreen = OCFullscreen;
