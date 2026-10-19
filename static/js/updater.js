/* Update-Hinweis: beim Programmstart (Hauptgeraet) und ueber Hilfe -> "Nach Updates suchen". Daten kommen von /api/update/* (app/about.py, app/updater.py).
 *   - Beim Start fragt die Seite das (im Hintergrund ermittelte) Ergebnis ab; gibt es eine neue Version, die nicht uebersprungen wurde, erscheint der Dialog:
 *     "Jetzt installieren" (laedt das Setup, merkt es vor und beendet OpenCue ueber den normalen Beenden-Dialog; das Setup startet danach und oeffnet OpenCue wieder),
 *     "Spaeter erinnern" (beim naechsten Start wieder), "Diese Version nicht mehr anzeigen" (bis es eine neuere gibt).
 *   - Fernbediente Geraete (/remote/) bekommen keinen Hinweis und koennen nichts installieren.
 * Aufruf: window.OCUpdate.checkNow(true) = manuelle Pruefung mit Rueckmeldung. */
(function () {
  "use strict";
  const ROOT = '[data-modal-backdrop="update"]';
  const t = (key, fallback) => { try { const v = typeof i18n === "function" ? i18n(key) : ""; return v && v !== key ? v : fallback; } catch (err) { return fallback; } };
  const $ = (selector) => document.querySelector(ROOT + " " + selector);
  const fill = (text, values) => Object.keys(values || {}).reduce((s, k) => s.split("{" + k + "}").join(String(values[k])), text);
  const isRemote = () => location.pathname.startsWith("/remote");
  let current = null;                  // letztes Ergebnis
  let shownOnStart = false;
  let polling = 0;
  let bound = false;

  async function api(method, path, body) {
    const res = await fetch(path, { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined, cache: "no-store" });
    return res.json();
  }

  function show(parts) {
    const set = (id, text) => { const el = $("#" + id); el.textContent = text || ""; el.hidden = !text; };
    set("update-headline", parts.headline);
    set("update-sub", parts.sub);
    set("update-notes", parts.notes);
    set("update-error", parts.error);
    $("#update-progress").hidden = !parts.progress;
    const on = (id, visible, label) => { const b = $("#" + id); b.hidden = !visible; b.disabled = false; if (label) b.textContent = label; };
    on("update-install", !!parts.install);
    on("update-skip", !!parts.skip);
    on("update-later", !!parts.later);
    on("update-page", !!parts.page);
    on("update-close", !!parts.close);
    Modal.open("update");
  }

  function dialogFor(info, manual) {
    if (info.state === "available") {
      show({
        headline: fill(t("UPDATE_AVAILABLE", "OpenCue {latest} is available"), { latest: info.latest }),
        sub: fill(t("UPDATE_YOU_HAVE", "You are using {version}."), { version: info.version || info.current }) + (info.can_install ? "" : " " + t("UPDATE_MAIN_DEVICE_ONLY", "Install it on the computer that runs OpenCue.")),
        notes: (info.notes || "").trim(), install: info.can_install, skip: true, later: true, page: true,
      });
    } else if (manual) {
      const text = info.state === "current" ? fill(t("UPDATE_CURRENT", "OpenCue {version} is up to date."), { version: info.current })
        : info.state === "none" ? t("UPDATE_NONE", "No release has been published yet.")
        : info.error === "rate_limit" ? t("UPDATE_RATE_LIMIT", "GitHub is limiting requests right now. Try again later.")
        : t("UPDATE_OFFLINE", "Could not check for updates. Is this computer online?");
      show({ headline: text, close: true, page: info.state === "error" });
    }
  }

  async function checkNow(manual) {
    if (isRemote() && !manual) return;
    if (manual) show({ headline: t("UPDATE_CHECKING", "Checking for updates ..."), close: true });
    try {
      current = await api("POST", "/api/update/check");
    } catch (err) {
      current = { state: "error", error: "network" };
    }
    if (manual && !(current.state === "available")) { dialogFor(current, true); return; }
    if (current.state === "available") dialogFor(current, manual);
  }

  /** Beim Start: Ergebnis der Hintergrund-Pruefung abholen (bis zu ~40 s warten, solange sie noch laeuft). */
  async function startupCheck() {
    if (isRemote() || shownOnStart) return;
    try {
      const info = await api("GET", "/api/update/status");
      if (info.enabled === false) return;
      if (info.state === "unknown" && polling < 14) { polling += 1; setTimeout(startupCheck, 3000); return; }
      if (info.state === "available" && !info.skipped) { shownOnStart = true; current = info; dialogFor(info, false); }
    } catch (err) { /* offline / Server noch nicht bereit */ }
  }

  async function install() {
    const info = current;
    const button = $("#update-install");
    button.disabled = true;
    $("#update-skip").hidden = true;
    $("#update-later").hidden = true;
    $("#update-error").hidden = true;
    $("#update-progress").hidden = false;
    const started = await api("POST", "/api/update/download");
    if (!started.ok) { fail(started.error); return; }
    for (;;) {
      await new Promise((r) => setTimeout(r, 500));
      const p = await api("GET", "/api/update/progress");
      if (p.state === "downloading") {
        const pct = p.total ? Math.round((p.done / p.total) * 100) : 0;
        $("#update-bar-fill").style.width = pct + "%";
        $("#update-progress-text").textContent = fill(t("UPDATE_DOWNLOADING", "Downloading {done} of {total} MB"), { done: (p.done / 1048576).toFixed(1), total: (p.total / 1048576).toFixed(1) });
      } else if (p.state === "ready") {
        $("#update-bar-fill").style.width = "100%";
        $("#update-progress-text").textContent = p.verified ? t("UPDATE_VERIFIED", "Download complete and verified.") : t("UPDATE_DONE", "Download complete.");
        const armed = await api("POST", "/api/update/arm");
        if (!armed.ok) { fail("network"); return; }
        Modal.close("update");
        client.send("exit_app", {});                       // der normale Beenden-Dialog (Speichern?) - danach startet das Setup
        return;
      } else if (p.state === "error") { fail(p.error); return; }
    }
  }

  function fail(code) {
    const map = { checksum: t("UPDATE_ERR_CHECKSUM", "The download is damaged (checksum does not match). Nothing was installed."), main_device_only: t("UPDATE_MAIN_DEVICE_ONLY", "Install it on the computer that runs OpenCue."), too_big: t("UPDATE_ERR_CHECKSUM", "The download is damaged (checksum does not match). Nothing was installed.") };
    const el = $("#update-error");
    el.textContent = map[code] || t("UPDATE_ERR_NETWORK", "The download failed. Check the connection or use the release page.");
    el.hidden = false;
    $("#update-progress").hidden = true;
    const button = $("#update-install");
    button.disabled = false;
    button.hidden = false;
    $("#update-page").hidden = false;
    $("#update-close").hidden = false;
  }

  function bind() {
    if (bound) return;
    bound = true;
    $("#update-install").addEventListener("click", install);
    $("#update-later").addEventListener("click", () => Modal.close("update"));
    $("#update-close").addEventListener("click", () => Modal.close("update"));
    $("#update-skip").addEventListener("click", async () => {
      if (current && current.latest) await api("POST", "/api/update/skip", { version: current.latest });
      Modal.close("update");
    });
    $("#update-page").addEventListener("click", async () => {
      const res = await api("POST", "/api/about/open", { target: "releases" });
      if (res && res.ok && !res.opened && res.url) window.open(res.url, "_blank", "noopener");
    });
  }

  function init() {
    bind();
    setTimeout(startupCheck, 2500);                 // die Oberflaeche ist dann aufgebaut; die Hintergrund-Pruefung des Servers laeuft ca. 4 s nach dem Start
  }
  window.OCUpdate = { checkNow, startupCheck, install };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
