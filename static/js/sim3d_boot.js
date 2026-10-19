/* Startskript des Panels "3D-Simulation": registriert den Panel-Typ sofort (klassisches Skript) und laedt das eigentliche Panel (ES-Modul sim3d.js mit three.js)
 * im Hintergrund. Ohne diesen Umweg koennte der erste Snapshot die Panels aufbauen, bevor das Modul fertig geladen ist - das Panel bliebe dann leer. */
(function () {
  "use strict";
  /** Registratur "Anleuchten": jede 3D-Simulation meldet sich mit {root, aim, placedCount, canAim} an. Die Scheinwerfersteuerung (app.js) zeigt ihre Knoepfe ("Punkt in 3D-Simulation setzen",
   *  Auto-Fokus/-Zoom) nur, wenn eine angemeldete Simulation im Layout steht und Scheinwerfer auf der Buehne platziert sind; jede Aenderung kommt als Ereignis "sim-aim-changed". */
  const instances = new Set();
  const registry = {
    register(inst) { instances.add(inst); registry.notify(); return () => { instances.delete(inst); registry.notify(); }; },
    notify() { document.dispatchEvent(new CustomEvent("sim-aim-changed")); },
    active() { return [...instances].find((i) => i.root.isConnected && i.placedCount() > 0) || null; },
    available() { return !!registry.active(); },
    get armed() { const a = registry.active(); return !!a && a.aim.armed; },
    arm(on) { instances.forEach((i) => { if (i.aim.armed) i.aim.arm(false); }); const a = registry.active(); if (a && on) a.aim.arm(true); },
    /** Wie viele der Scheinwerfer `ids` zielen koennen (Moving Head mit 3D-Modell auf der Buehne). */
    aimable(ids) { const a = registry.active(); return a ? ids.filter((id) => a.canAim(id)).length : 0; },
    /** Auto-Fokus / Auto-Zoom (Radius in m) fuer `ids`; Rueckgabe {done, skipped, miss} oder null ohne Simulation. */
    auto(kind, ids, radius) { const a = registry.active(); return a ? a.aim.auto(kind, ids, radius) : null; },
    /** Moegliche Radien des Lichtkreises fuer `ids` (siehe sim3d_aim.js zoomInfo). */
    zoomInfo(ids) { const a = registry.active(); return a ? a.aim.zoomInfo(ids) : null; },
    get radius() { const a = registry.active(); return a ? a.aim.prefs.radius : 0.5; },
    set radius(value) { const a = registry.active(); if (a) a.aim.setRadius(value); },
  };
  window.OCSimAim = registry;
  let real = null;
  const loading = import("/static/js/sim3d.js").then((module) => { real = module.plugin; return real; }).catch((error) => {
    console.error("3D-Simulation konnte nicht geladen werden:", error);
    return null;
  });
  window.__panelPlugins.register({
    type: "sim3d",
    buildContent(panel) {
      const host = document.createElement("div");
      host.style.cssText = "display:contents";
      loading.then((plugin) => { if (plugin) host.appendChild(plugin.buildContent(panel)); });
      return host;
    },
    onMessage(panelEl, messageType, payload) { if (real && real.onMessage) real.onMessage(panelEl, messageType, payload); },
  });
})();
