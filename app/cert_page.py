# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
cert_page.py
Anleitungs-Seite "Zertifikat installieren" (GET /remote/zertifikat): eine Schritt-fuer-Schritt-Anleitung - oben ein Umschalter zwischen "iPad / iPhone" und "Android / Windows / macOS" - mit
Installieren UND Entfernen. Sie ist OEFFENTLICH (ohne Anmeldung) und laeuft ueber http - das Zertifikat der eigenen Stelle (app/https_cert.py) ist nichts Geheimes, und solange man ihm noch nicht
vertraut, kann man es nur so ohne Warnung laden. Die Sprache folgt dem Browser (Accept-Language, `?lang=xx` erzwingt eine), sonst der Sprache der Konsole. Die Haken bei den Schritten und die
gewaehlte Seite (iPad / andere) merkt sich die Seite im Speicher des Geraets (localStorage), damit man nach dem Wechsel in die Einstellungen weiss, wo man war; `?os=ios|other` waehlt sie vor.
"""

from __future__ import annotations

import html
import re
from typing import Optional

from app import https_cert, remote_pwa
from app.languages import LANGUAGES, tr
from app.state_manager import state

KEYS = (
    "CP_TITLE", "CP_LEAD", "CP_ORDER", "CP_TAB_IOS", "CP_TAB_OTHER", "CP_SAFARI_T", "CP_SAFARI_B", "CP_SETTINGS_NOTE",
    "CP_S1_T", "CP_S1_B", "CP_S2_T", "CP_S2_B", "CP_S3_T", "CP_S3_B", "CP_S4_T", "CP_S4_B", "CP_BTN_PROFILE", "CP_BTN_HTTPS", "CP_DONE",
    "CP_NO_CERT", "CP_HTTPS_OFF", "CP_AND_I", "CP_WIN_I", "CP_MAC_I", "CP_BTN_CRT", "CP_CHECK_T", "CP_CHECK_B", "CP_SAFE_T", "CP_SAFE_B", "CP_WHY_T", "CP_WHY_B",
    "CP_UN_T", "CP_UN_IOS", "CP_UN_AND", "CP_UN_WIN", "CP_UN_MAC", "CP_UN_AFTER",
)


def pick_language(accept_language: str, query: Optional[str]) -> str:
    """Sprache der Seite: ?lang=, dann die Reihenfolge der Browser-Sprachen, sonst die Sprache der Konsole."""
    known = {code for code, _name in LANGUAGES}
    if query and query.lower() in known:
        return query.lower()
    for part in (accept_language or "").split(","):
        code = re.split(r"[;\-_]", part.strip().lower())[0]
        if code in known:
            return code
    return state.language if state.language in known else "en"


def page(host: str, accept_language: str = "", query_lang: Optional[str] = None, query_os: Optional[str] = None) -> str:
    lang = pick_language(accept_language, query_lang)
    tokens = remote_pwa.resolved_tokens()
    colors = {
        "bg": tokens.get("bg", "#0a0a0b"), "surface": tokens.get("surface-1", "#151517"), "surface2": tokens.get("surface-2", "#1d1d20"),
        "border": tokens.get("border", "#323237"), "text": tokens.get("text-1", "#ededf0"), "muted": tokens.get("text-2", "#a2a2aa"),
        "accent": tokens.get("accent", "#ffb000"), "ink": tokens.get("accent-ink", "#1a1200"),
    }
    base = state.theme["base"]
    t = {key: tr(key, lang) for key in KEYS}
    name = re.sub(r":\d+$", "", host or "") or "opencue.local"
    https_url = f"https://{name}:{state.https_port}/remote/" if state.https_enabled else ""
    fingerprint = https_cert.ca_fingerprint()
    available = bool(fingerprint)
    touch = remote_pwa.icon_data_uri("apple-touch-icon.png")
    langs = "".join(f'<a href="?lang={code}"{" aria-current=true" if code == lang else ""}>{code.upper()}</a>' for code, _name in LANGUAGES)
    css = """
  * { box-sizing: border-box; }
  html, body { margin: 0; background: %(bg)s; color: %(text)s; font-family: -apple-system, "Segoe UI", system-ui, sans-serif; line-height: 1.5; }
  body { padding: max(16px, env(safe-area-inset-top)) max(16px, env(safe-area-inset-right)) max(24px, env(safe-area-inset-bottom)) max(16px, env(safe-area-inset-left)); }
  main { width: min(100%%, 38rem); margin: 0 auto; }
  header { display: flex; align-items: center; gap: 14px; margin: 8px 0 14px; }
  header img { width: 56px; height: 56px; border-radius: 13px; flex: none; }
  h1 { margin: 0; font-size: 1.35rem; line-height: 1.2; }
  .lead { color: %(muted)s; margin: 0 0 14px; }
  .tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; padding: 5px; margin: 0 0 16px; background: %(surface2)s; border: 1px solid %(border)s; border-radius: 14px; }
  .tabs button { min-height: 3rem; border: 0; border-radius: 10px; background: transparent; color: %(muted)s; font: inherit; font-weight: 600; cursor: pointer; padding: 0 8px; }
  .tabs button[aria-selected=true] { background: %(accent)s; color: %(ink)s; }
  .tabs button:focus-visible { outline: 2px solid %(text)s; outline-offset: 2px; }
  [data-panel][hidden] { display: none; }
  .order { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 18px; padding: 0; list-style: none; }
  .order li { padding: 6px 12px; border-radius: 999px; background: %(surface2)s; border: 1px solid %(border)s; font-size: .9rem; }
  .order b { color: %(accent)s; margin-right: 4px; }
  .step, .box { background: %(surface)s; border: 1px solid %(border)s; border-radius: 14px; padding: 16px 16px 18px; margin: 0 0 14px; }
  .banner { border-color: %(accent)s; }
  .step.done { opacity: .6; }
  .step h2 { margin: 0 0 6px; font-size: 1.05rem; display: flex; align-items: center; gap: 10px; }
  .num { flex: none; width: 1.9rem; height: 1.9rem; border-radius: 50%%; background: %(accent)s; color: %(ink)s; display: inline-flex; align-items: center; justify-content: center; font-weight: 700; }
  .step p, .box p { margin: 0 0 12px; color: %(muted)s; }
  .step p.note { font-size: .92rem; color: %(text)s; padding: 8px 12px; background: %(surface2)s; border-radius: 10px; }
  .btn { display: flex; align-items: center; justify-content: center; min-height: 3.2rem; padding: 0 18px; border-radius: 12px; background: %(accent)s; color: %(ink)s; font-weight: 700; font-size: 1.05rem; text-decoration: none; border: 0; text-align: center; }
  .btn.off { background: %(surface2)s; color: %(muted)s; pointer-events: none; }
  .btn:focus-visible, label:focus-within, a:focus-visible { outline: 2px solid %(accent)s; outline-offset: 2px; }
  .done-row { display: flex; align-items: center; gap: 10px; margin-top: 12px; color: %(text)s; min-height: 2.75rem; cursor: pointer; }
  .done-row input { width: 1.4rem; height: 1.4rem; accent-color: %(accent)s; flex: none; }
  .warn { color: #ff9d5c; }
  code { background: %(surface2)s; padding: 1px 6px; border-radius: 6px; font-size: .88em; word-break: break-all; }
  h3 { margin: 0 0 6px; font-size: .95rem; }
  .box h3.os { color: %(accent)s; }
  .langs { display: flex; gap: 6px; justify-content: center; margin: 18px 0 0; }
  .langs a { padding: 6px 10px; border-radius: 8px; border: 1px solid %(border)s; color: %(muted)s; text-decoration: none; font-size: .85rem; }
  .langs a[aria-current] { background: %(accent)s; color: %(ink)s; border-color: %(accent)s; }
""" % colors
    for key, value in colors.items():
        css = css.replace("%(" + key + ")s", value)
    css = css.replace("%%", "%")

    def esc(key: str) -> str:
        return html.escape(t[key])

    def step(n: int, title: str, body: str, extra: str = "", note: str = "") -> str:
        note_html = f'<p class="note">{html.escape(note)}</p>' if note else ""
        return (f'<section class="step" id="s{n}"><h2><span class="num">{n}</span>{html.escape(title)}</h2><p>{html.escape(body)}</p>{note_html}{extra}'
                f'<label class="done-row"><input type="checkbox" data-step="{n}"><span>{esc("CP_DONE")}</span></label></section>')

    profile_btn = (f'<a class="btn" href="/remote/opencue.mobileconfig">{esc("CP_BTN_PROFILE")}</a>' if available
                   else f'<a class="btn off">{esc("CP_BTN_PROFILE")}</a><p class="warn" style="margin:10px 0 0">{esc("CP_NO_CERT")}</p>')
    https_btn = (f'<a class="btn" href="{html.escape(https_url)}">{esc("CP_BTN_HTTPS")}</a><p style="margin:8px 0 0"><code>{html.escape(https_url)}</code></p>' if https_url
                 else f'<a class="btn off">{esc("CP_BTN_HTTPS")}</a><p class="warn" style="margin:10px 0 0">{esc("CP_HTTPS_OFF")}</p>')
    order = "".join(f'<li><b>{n}</b>{html.escape(label)}</li>' for n, label in enumerate(t["CP_ORDER"].split("|"), 1))
    crt_btn = f'<a class="btn" style="margin-top:10px" href="/remote/opencue-ca.crt">{esc("CP_BTN_CRT")}</a>' if available else ""
    check = html.escape(t["CP_CHECK_B"].replace("{fp}", "")) + (f"<br><code>{html.escape(fingerprint)}</code>" if fingerprint else "")
    initial = "other" if (query_os or "").lower() == "other" else ("ios" if (query_os or "").lower() == "ios" else "")
    script = """
(function () {
  var KEY = "opencue.certsteps", OSKEY = "opencue.certos", forced = "__OS__";
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { saved = {}; }
  [].forEach.call(document.querySelectorAll("input[data-step]"), function (box) {
    var n = box.getAttribute("data-step");
    box.checked = !!saved[n];
    box.closest(".step").classList.toggle("done", box.checked);
    box.addEventListener("change", function () {
      saved[n] = box.checked;
      box.closest(".step").classList.toggle("done", box.checked);
      try { localStorage.setItem(KEY, JSON.stringify(saved)); } catch (e) { /* privat */ }
    });
  });
  // iPad / iPhone oder Android / Windows / macOS: vorgewaehlt nach Geraet (iPadOS meldet sich wie ein Mac, hat aber Touch), gemerkt im Speicher des Geraets
  function detect() {
    var ua = navigator.userAgent || "";
    if (/iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)) return "ios";
    return "other";
  }
  var current = forced || (function () { try { return localStorage.getItem(OSKEY); } catch (e) { return ""; } })() || detect();
  function show(which) {
    current = which === "other" ? "other" : "ios";
    [].forEach.call(document.querySelectorAll("[data-panel]"), function (p) { p.hidden = p.getAttribute("data-panel") !== current; });
    [].forEach.call(document.querySelectorAll(".tabs button"), function (b) { b.setAttribute("aria-selected", b.getAttribute("data-tab") === current ? "true" : "false"); });
    try { localStorage.setItem(OSKEY, current); } catch (e) { /* privat */ }
  }
  [].forEach.call(document.querySelectorAll(".tabs button"), function (b) { b.addEventListener("click", function () { show(b.getAttribute("data-tab")); }); });
  show(current);
})();
""".replace("__OS__", initial)
    no_cert_note = "" if available else f'<p class="warn" style="margin:10px 0 14px">{esc("CP_NO_CERT")}</p>'
    return f"""<!doctype html>
<html lang="{lang}" data-theme="{base}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="{base}">
<meta name="theme-color" content="{remote_pwa.theme_color()}">
<link rel="apple-touch-icon" sizes="180x180" href="{touch}">
<title>OpenCue</title>
<style>{css}</style></head><body><main>
<header><img src="{touch}" alt="" width="56" height="56"><h1>{esc("CP_TITLE")}</h1></header>
<p class="lead">{esc("CP_LEAD")}</p>
<div class="tabs" role="tablist"><button type="button" role="tab" data-tab="ios" aria-selected="true">{esc("CP_TAB_IOS")}</button><button type="button" role="tab" data-tab="other" aria-selected="false">{esc("CP_TAB_OTHER")}</button></div>

<div data-panel="ios">
<section class="box banner"><h3>{esc("CP_SAFARI_T")}</h3><p style="margin:0">{esc("CP_SAFARI_B")}</p></section>
<ol class="order" aria-label="{html.escape(t["CP_ORDER"].replace("|", " - "))}">{order}</ol>
{step(1, t["CP_S1_T"], t["CP_S1_B"], profile_btn)}
{step(2, t["CP_S2_T"], t["CP_S2_B"], "", t["CP_SETTINGS_NOTE"])}
{step(3, t["CP_S3_T"], t["CP_S3_B"], "", t["CP_SETTINGS_NOTE"])}
{step(4, t["CP_S4_T"], t["CP_S4_B"], https_btn)}
<section class="box"><h3>{esc("CP_UN_T")}</h3><p>{esc("CP_UN_IOS")}</p><p style="margin:0">{esc("CP_UN_AFTER")}</p></section>
</div>

<div data-panel="other" hidden>
<section class="box"><h3 class="os">Android</h3><p>{esc("CP_AND_I")}</p><p style="margin:0">{esc("CP_UN_AND")}</p></section>
<section class="box"><h3 class="os">Windows</h3><p>{esc("CP_WIN_I")}</p><p style="margin:0">{esc("CP_UN_WIN")}</p></section>
<section class="box"><h3 class="os">macOS</h3><p>{esc("CP_MAC_I")}</p><p style="margin:0">{esc("CP_UN_MAC")}</p></section>
{crt_btn}{no_cert_note}
</div>

<section class="box"><h3>{esc("CP_CHECK_T")}</h3><p style="margin:0">{check}</p></section>
<section class="box"><h3>{esc("CP_WHY_T")}</h3><p style="margin:0">{esc("CP_WHY_B")}</p></section>
<section class="box"><h3>{esc("CP_SAFE_T")}</h3><p style="margin:0">{esc("CP_SAFE_B")}</p></section>
<nav class="langs" aria-label="Language">{langs}</nav>
</main><script>{script}</script></body></html>"""
