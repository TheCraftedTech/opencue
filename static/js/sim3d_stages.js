/* Buehnen der 3D-Simulation: Toolbar-Chip "Stage <Name> *" (oeffnet den Dateimanager, Art 3D-Buehnen: static/js/file_manager.js) und die gemeinsame Schnittstelle fuer das Panel (window.OCSimStages: aktueller Stand, speichern, verwerfen, Ereignis "sim-stage" bei Aenderungen).
 * Die aktive Buehne liegt auf dem Server (app/sim_stages.py); app.js meldet jede Aenderung als Ereignis "sim-stage-changed". Namens-, Rueckfrage- und Toast-Dialoge
 * sind die der Layouts (app.js). Klassisches Skript, laeuft nach app.js. */
(function () {
  "use strict";
  const t = (key, vars) => {
    let s = i18n(key);
    if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
    return s;
  };
  const stem = (filename) => String(filename || "").replace(/\.json$/i, "");
  let current = null;                    // letzter bekannter Stand der aktiven Buehne ({name, filename, dirty, state, count, revision, objects?})

  async function call(method, url, body) {
    try {
      const res = await fetch(url, { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
      return { ok: res.ok, status: res.status, data: await res.json().catch(() => ({})) };
    } catch (err) {
      return { ok: false, status: 0, data: { error: "network" } };
    }
  }
  function fail(result) {
    const key = { invalid_name: "SIMSTAGE_ERR_NAME", not_found: "SIMSTAGE_ERR_NOT_FOUND", too_big: "SIMSTAGE_ERR_TOO_BIG", network: "SIMSTAGE_ERR_NETWORK" }[result.data && result.data.error];
    _showToast(t(key || "SIMSTAGE_ERR_GENERIC"), "error", 4500);
  }

  // ------------------------------------------------------------------------------------------ Stand und Toolbar-Chip
  function paintChip() {
    const chip = document.getElementById("toolbar-stage-chip");
    if (!chip || !current) return;
    const empty = !current.filename && !(current.count > 0) && !current.dirty;           // noch keine Buehne angelegt (leere, ungespeicherte Arbeitsflaeche): wie beim Layout nur "—"
    document.getElementById("toolbar-stage-name").textContent = empty ? "—" : (current.name || "—");
    document.getElementById("toolbar-stage-dirty").hidden = !current.dirty;
    chip.classList.toggle("menubar__layout-chip--dirty", !!current.dirty);
    chip.title = current.dirty ? t("SIMSTAGE_CHIP_DIRTY") : t("SIMSTAGE_CHIP_TIP");
  }
  function setCurrent(payload) {
    current = { ...(current || {}), ...payload };
    paintChip();
    _notifyFileManager("stages");
  }
  async function refresh() {
    const result = await call("GET", "/api/sim-stage");
    if (result.ok) {
      setCurrent(result.data);
      document.dispatchEvent(new CustomEvent("sim-stage", { detail: { kind: "resync", stage: current } }));
    }
    return current;
  }
  document.addEventListener("sim-stage-changed", (e) => {
    const payload = e.detail || {};
    setCurrent(payload);
    document.dispatchEvent(new CustomEvent("sim-stage", { detail: { kind: "changed", stage: current, source: payload.source || null } }));
  });
  document.addEventListener("sim-stage-resync", () => { refresh(); });
  document.addEventListener("i18n-applied", () => { paintChip(); });

  // ------------------------------------------------------------------------------------------ Aktionen
  async function confirmReplace() {
    if (!current || !current.dirty) return true;
    return _askLayoutConfirm({ title: t("SIMSTAGE_REPLACE_TITLE"), body: t("SIMSTAGE_REPLACE_BODY", { name: current.name }), confirmKey: "SIMSTAGE_REPLACE_CONFIRM" });
  }

  /** In die Datei der aktiven Buehne speichern; hat sie noch keine (oder fehlt sie), wird nach dem Namen gefragt. forceAsk = "Speichern unter". true = gespeichert. */
  async function save(forceAsk) {
    await refresh();
    let name = current && current.filename && current.state !== "missing" && !forceAsk ? stem(current.filename) : null;
    if (!name) {
      name = await _askLayoutName({ title: t("SIMSTAGE_SAVE_TITLE"), confirmKey: "SIMSTAGE_SAVE_CONFIRM", value: current ? current.name : "", labelKey: "SIMSTAGE_NAME_LABEL" });
      if (!name) return false;
    }
    const sameFile = !!(current && current.filename && !forceAsk && stem(current.filename) === name);
    let result = await call("POST", "/api/sim-stage/save", { name, overwrite: sameFile });
    if (!result.ok && result.status === 409) {
      if (!(await _askLayoutConfirm({ title: t("SIMSTAGE_EXISTS_TITLE"), body: t("SIMSTAGE_EXISTS_BODY", { name }), confirmKey: "LAYOUT_OVERWRITE" }))) return false;
      result = await call("POST", "/api/sim-stage/save", { name, overwrite: true });
    }
    if (!result.ok) { fail(result); return false; }
    _showToast(t("SIMSTAGE_SAVED", { name: result.data.name }), "success", 3000);
    return true;
  }

  async function discard() {
    const result = await call("POST", "/api/sim-stage/discard", {});
    if (!result.ok) fail(result);
    return result.ok;
  }

  async function newStage() {
    if (!(await confirmReplace())) return;
    const result = await call("POST", "/api/sim-stage/new", {});          // ohne Namensabfrage: "Bühne N" entsteht sofort als Datei und steht gleich in der Liste (Umbenennen geht spaeter)
    if (!result.ok) { fail(result); return; }
    _showToast(t("SIMSTAGE_CREATED", { name: result.data.name }), "success", 3000);
  }

  window.OCSimStages = {
    get current() { return current; },
    refresh, save, discard, newStage, confirmReplace,
    open() { window.OCFileManager.open("stages"); },
    /** Das Panel meldet eine Aenderung der Arbeitskopie (Objektliste); source = Kennung des Panels (sein Echo ignoriert es). */
    async push(objects, source) {
      const result = await call("POST", "/api/sim-stage/objects", { objects, source });
      if (result.ok) setCurrent(result.data);
      return result.ok;
    },
  };
  refresh();
})();
