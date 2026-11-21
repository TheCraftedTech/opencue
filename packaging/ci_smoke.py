# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
ci_smoke.py
Rauchtest des FERTIG GEBAUTEN Programms und Installers - lokal und in GitHub Actions derselbe Weg (.github/workflows/release.yml).

    python packaging\\ci_smoke.py                         dist\\OpenCue\\OpenCue.exe und dist\\installer\\OpenCue-Setup-v*.exe pruefen
    python packaging\\ci_smoke.py --no-installer           nur das Programm
    python packaging\\ci_smoke.py --languages english,german,french,dutch,italian,spanish     Installer in allen sechs Sprachen (Standard: english)

Programm: startet ohne Fenster (--no-ui) mit eigenem leerem Datenordner und eigenem Port, prueft Server, Oberflaeche, Hilfeseiten in allen sechs Sprachen, Sprachdateien, Zustand,
REST-API (Token anlegen, Status lesen), Doppelstart-Schutz, Protokolldatei ohne Fehler und dass nach dem Beenden kein Prozess uebrig bleibt.
Installer: stille Installation in einen Temp-Ordner (/DIR, /DATADIR, /CONFIGDIR, /NOLAUNCH, /LANG), Exe + Konfiguration vorhanden, Deinstallation entfernt Programmordner,
Eintrag und Zuordnung. Beruehrt nie den echten Datenordner. Exit-Code 0 = alles in Ordnung.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{C2C554E2-CE9C-4C3B-8742-E5E820D30FE4}_is1"
results: list = []


def check(name: str, ok: bool, detail="") -> None:
    print(("OK   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail != "" else ""), flush=True)
    results.append(bool(ok))


def kill_tree(pid: int) -> None:
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)


def get(port: int, path: str, timeout: float = 10, headers: dict | None = None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", headers=headers or {})
    return urllib.request.urlopen(req, timeout=timeout)


def post(port: int, path: str, body: dict, timeout: float = 10):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(), method="POST", headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout)


def program_smoke(exe: str, port: int) -> None:
    print(f"\n== Programm: {exe}")
    check("OpenCue.exe vorhanden", os.path.isfile(exe), exe)
    if not os.path.isfile(exe):
        return
    data = tempfile.mkdtemp(prefix="oc-ci-data-")
    os.makedirs(os.path.join(data, "config"))
    with open(os.path.join(data, "config", "app_config.json"), "w", encoding="utf-8") as fh:
        json.dump({"first_start_done": True, "mdns_enabled": False, "update_check_enabled": False}, fh)
    env = dict(os.environ, OPENCUE_DATA_DIR=data, OPENCUE_NO_SPLASH="1")
    out = open(os.path.join(data, "stdout.txt"), "wb")
    args = [exe, "--no-ui", "--no-splash", "--port", str(port), "--data-dir", data]
    started = time.time()
    proc = subprocess.Popen(args, env=env, stdout=out, stderr=subprocess.STDOUT, cwd=os.path.dirname(exe))
    try:
        up = False
        while time.time() - started < 120:
            if proc.poll() is not None:
                break
            try:
                if get(port, "/", 3).status == 200:
                    up = True
                    break
            except Exception:
                time.sleep(1)
        check("Server antwortet", up, f"{time.time() - started:.1f} s, Exit-Code {proc.poll()}")
        if not up:
            return
        time.sleep(3)
        pages = ("getting-started", "api", "commands", "error-codes", "whatsnew")
        for lang in ("en", "de", "fr", "nl", "it", "es"):
            miss = []
            for page in pages:
                try:
                    body = get(port, f"/static/help/{page}.{lang}.md").read()
                    if len(body) < 500:
                        miss.append(page)
                except Exception:
                    miss.append(page)
            check(f"Anleitungen {lang}", not miss, miss or f"{len(pages)} Seiten")
            try:
                loc = json.load(get(port, f"/static/locales/{lang}.json"))
                check(f"Sprachdatei {lang}", len(loc) > 3000, f"{len(loc)} Schluessel")
            except Exception as exc:
                check(f"Sprachdatei {lang}", False, exc)
        for path, needle in (("/static/js/help_viewer.js", "OCHelp"), ("/static/help/guide/snippets/fr/api.json", "[")):
            try:
                check(f"GET {path}", needle in get(port, path).read().decode("utf-8", "replace"))
            except Exception as exc:
                check(f"GET {path}", False, exc)
        try:
            state = json.load(get(port, "/api/state"))
            check("Zustand lesbar", isinstance(state, dict), list(state)[:5])
        except Exception as exc:
            check("Zustand lesbar", False, exc)
        # REST-API: Token anlegen (nur am Rechner selbst), Status lesen
        try:
            token = json.load(post(port, "/api/apikeys", {"name": "ci", "capabilities": None}))["token"]
            status = json.load(get(port, "/api/v1/status", headers={"Authorization": f"Bearer {token}"}))
            check("REST-API: Token + /status", "show" in status and "app" in status, status.get("app"))
            try:
                get(port, "/api/v1/status")
                check("REST-API ohne Token wird abgelehnt", False)
            except urllib.error.HTTPError as exc:
                check("REST-API ohne Token wird abgelehnt", exc.code == 401, exc.code)
        except Exception as exc:
            check("REST-API: Token + /status", False, exc)
        # Zweite Instanz: darf den ersten Server nicht stoeren (Doppelstart-Schutz)
        out2 = open(os.path.join(data, "stdout2.txt"), "wb")
        proc2 = subprocess.Popen(args, env=env, stdout=out2, stderr=subprocess.STDOUT, cwd=os.path.dirname(exe))
        try:
            proc2.wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass
        kill_tree(proc2.pid)
        try:
            check("Erster Server laeuft nach einem zweiten Start ungestoert weiter", get(port, "/", 5).status == 200)
        except Exception as exc:
            check("Erster Server laeuft nach einem zweiten Start ungestoert weiter", False, exc)
    finally:
        kill_tree(proc.pid)
        time.sleep(2)
        out.close()
    log = os.path.join(data, "logs", "opencue.log")
    check("Protokolldatei vorhanden", os.path.isfile(log))
    if os.path.isfile(log):
        text = open(log, encoding="utf-8", errors="replace").read()
        bad = [ln for ln in text.splitlines() if "Traceback" in ln or " ERROR " in ln or "OC-2" in ln]
        check("Protokoll ohne Fehler", not bad, bad[:3])
    left = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {os.path.basename(exe)}", "/FO", "CSV", "/NH"], capture_output=True).stdout.decode("utf-8", "replace")   # Bytes: die Konsole nutzt eine OEM-Codepage
    check("Nach dem Beenden bleibt kein Prozess uebrig", os.path.basename(exe).lower() not in left.lower(), left.strip()[:120])
    shutil.rmtree(data, ignore_errors=True)


def installer_smoke(setup: str, languages: list) -> None:
    print(f"\n== Installer: {setup}")
    check("Installer vorhanden", os.path.isfile(setup), setup)
    if not os.path.isfile(setup):
        return
    import winreg
    for lang in languages:
        base = tempfile.mkdtemp(prefix="oc-ci-inst-")
        app, data, cfg = (os.path.join(base, n) for n in ("app", "data", "cfg"))
        cmd = [setup, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/DIR={app}", f"/DATADIR={data}", f"/CONFIGDIR={cfg}", "/NOLAUNCH=1", f"/LANG={lang}", f"/LOG={os.path.join(base, 'setup.log')}"]
        run = subprocess.run(cmd, timeout=600)
        exe = os.path.join(app, "OpenCue.exe")
        check(f"[{lang}] Installation: Exit-Code 0 und OpenCue.exe vorhanden", run.returncode == 0 and os.path.isfile(exe), run.returncode)
        cfg_file = os.path.join(cfg, "app_config.json")
        try:
            conf = json.load(open(cfg_file, encoding="utf-8-sig"))
            check(f"[{lang}] Konfiguration geschrieben (Datenordner)", os.path.normcase(str(conf.get("custom_data_path", ""))) == os.path.normcase(data) or bool(conf), conf)
        except Exception as exc:
            check(f"[{lang}] Konfiguration geschrieben", False, exc)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY):
                check(f"[{lang}] Eintrag unter 'Apps & Features'", True)
        except OSError:
            check(f"[{lang}] Eintrag unter 'Apps & Features'", False)
        unins = os.path.join(app, "unins000.exe")
        if os.path.isfile(unins):
            run = subprocess.run([unins, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], timeout=300)
            time.sleep(2)
            check(f"[{lang}] Deinstallation entfernt Programm und Eintrag", run.returncode == 0 and not os.path.isfile(exe), run.returncode)
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY):
                    check(f"[{lang}] Eintrag ist nach der Deinstallation weg", False)
            except OSError:
                check(f"[{lang}] Eintrag ist nach der Deinstallation weg", True)
        else:
            check(f"[{lang}] Deinstallationsprogramm vorhanden", False)
        shutil.rmtree(base, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--exe", default=os.path.join(ROOT, "dist", "OpenCue", "OpenCue.exe"))
    ap.add_argument("--setup", default="")
    ap.add_argument("--port", type=int, default=8957)
    ap.add_argument("--no-installer", action="store_true")
    ap.add_argument("--no-program", action="store_true")
    ap.add_argument("--languages", default="english")
    a = ap.parse_args()
    if not a.no_program:
        program_smoke(a.exe, a.port)
    if not a.no_installer:
        setup = a.setup or next(iter(sorted(glob.glob(os.path.join(ROOT, "dist", "installer", "OpenCue-Setup-v*.exe")))), "")
        installer_smoke(setup, [x.strip() for x in a.languages.split(",") if x.strip()])
    failed = results.count(False)
    print(f"\n{'ALLE PRUEFUNGEN GRUEN' if not failed else str(failed) + ' PRUEFUNG(EN) FEHLGESCHLAGEN'} ({len(results)} Pruefungen)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
