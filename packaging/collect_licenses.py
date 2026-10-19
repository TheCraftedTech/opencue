"""Sammelt die Lizenztexte aller Pakete, die in den PyInstaller-Build wandern, nach packaging/third_party/ (nur Entwicklung; das Ergebnis wird mit ausgeliefert).

Erzeugt:
  packaging/third_party/components.json            Liste fuer den Ueber-Dialog (Name, Version, Lizenz, Zweck, Webseite, Lizenzdateien) - gelesen von app/about.py
  packaging/third_party/THIRD_PARTY_NOTICES.md     dieselbe Liste als Tabelle (liegt im Build neben der Lizenz)
  packaging/third_party/licenses/<Name>/<Datei>    die Lizenztexte (aus den installierten Paketen, aus packaging/license-extra/ fuer Pakete ohne Lizenzdatei,
                                                   dazu ffmpeg, three.js und Python)

Aufruf (im Projektordner, mit dem venv, in dem auch gebaut wird):  venv\\Scripts\\python.exe packaging\\collect_licenses.py
Die Paketliste unten muss zu requirements.txt + deren Abhaengigkeiten passen. Der Ordner third_party wird bei jedem Lauf neu angelegt.
"""
from __future__ import annotations

import importlib.metadata as md
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "third_party"
EXTRA = HERE / "license-extra"
sys.path.insert(0, str(ROOT))
from app import version  # noqa: E402

# (Paket, wofuer) - alles, was zur Laufzeit im Build steckt. Nicht dabei: watchfiles (wird ausgeschlossen), pyinstaller selbst (Bootloader: GPL mit Ausnahme, erlaubt jede Lizenz).
PACKAGES = [
    ("fastapi", "Web framework (server)"), ("starlette", "Web toolkit used by FastAPI"), ("pydantic", "Data validation (FastAPI)"), ("pydantic_core", "Core of pydantic"),
    ("annotated-types", "pydantic"), ("annotated-doc", "FastAPI"), ("typing_extensions", "Typing backports"), ("typing-inspection", "pydantic"), ("anyio", "Async foundation"), ("idna", "Domain names"),
    ("uvicorn", "HTTP/WebSocket server"), ("click", "uvicorn"), ("h11", "HTTP (uvicorn)"), ("httptools", "HTTP (uvicorn)"), ("websockets", "WebSocket (uvicorn)"),
    ("python-dotenv", "uvicorn (optional)"), ("PyYAML", "uvicorn (optional)"),
    ("Jinja2", "HTML templates"), ("MarkupSafe", "Jinja2"),
    ("pywebview", "Application window (WebView2)"), ("pythonnet", "pywebview: .NET bridge"), ("clr_loader", "pythonnet"), ("cffi", "clr_loader"), ("pycparser", "cffi"),
    ("proxy_tools", "pywebview"), ("bottle", "pywebview"),
    ("sacn", "sACN output"), ("stupidArtnet", "Art-Net output"), ("pyserial", "USB DMX (Enttec)"), ("pygdtf", "Reading GDTF fixture files"),
    ("assimp_py", "3D models inside GDTF files (Assimp)"), ("segno", "QR codes (remote access)"),
]
LICENSE_FILE = re.compile(r"(licen[sc]e|copying|notice|authors)", re.IGNORECASE)


def dist_files(dist: md.Distribution) -> list[tuple[str, Path]]:
    found = []
    for f in dist.files or []:
        parts = f.parts
        in_info = len(parts) >= 2 and parts[0].endswith(".dist-info")
        if in_info and LICENSE_FILE.search(parts[-1]) and parts[-1] != "RECORD" and not parts[-1].endswith((".pyc", ".json")):
            path = Path(dist.locate_file(f))
            if path.is_file():
                found.append(("/".join(parts[1:]), path))
    return found


def license_name(meta) -> str:
    expression = meta.get("License-Expression")
    if expression:
        return expression
    classifiers = [c.split("::")[-1].strip() for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
    if classifiers:
        return ", ".join(classifiers)
    text = (meta.get("License") or "").strip().splitlines()
    return text[0][:60] if text else "see licence file"


def homepage(meta) -> str:
    for line in meta.get_all("Project-URL") or []:
        name, _, url = line.partition(",")
        if name.strip().lower() in ("homepage", "home", "source", "repository", "github"):
            return url.strip()
    return (meta.get("Home-page") or "").strip()


def copy_into(folder_name: str, sources: list[Path]) -> list[str]:
    """Kopiert Lizenzdateien nach licenses/<folder_name>/ und liefert die relativen Namen (fuer components.json)."""
    names = []
    for path in sources:
        target = OUT / "licenses" / folder_name / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        names.append(f"{folder_name}/{path.name}")
    return names


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "licenses").mkdir(parents=True)
    components = []
    missing = []
    for name, purpose in PACKAGES:
        try:
            dist = md.distribution(name)
        except md.PackageNotFoundError:
            missing.append(name)
            continue
        display = dist.metadata["Name"]
        sources = [path for _, path in dist_files(dist)]
        if not sources:
            fallback = EXTRA / f"{name}.txt"
            if fallback.is_file():
                sources = [fallback]
            else:
                print("WARNUNG: keine Lizenzdatei fuer", name, "- Text in packaging/license-extra/%s.txt anlegen" % name)
        components.append({"name": display, "version": dist.version, "license": license_name(dist.metadata), "purpose": purpose, "url": homepage(dist.metadata), "files": copy_into(display, sources)})

    # weitere mitgelieferte Komponenten (keine Python-Pakete)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    extras = [
        ("FFmpeg", "8.1 (gyan.dev essentials build)", "GPL-3.0 (build with --enable-gpl --enable-version3)", "Camera capture on the main device (separate program, ffmpeg/ffmpeg.exe)", "https://ffmpeg.org/",
         [ROOT / "ffmpeg" / "LICENSE.txt"]),
        ("three.js", "r186", "MIT", "3D simulation and fixture model viewer (static/vendor/three)", "https://threejs.org/", [ROOT / "static" / "vendor" / "three" / "LICENSE"]),
        ("Python", sys.version.split()[0], "PSF-2.0", "Runtime bundled by PyInstaller", "https://www.python.org/", [python_license] if python_license.is_file() else []),
        ("Microsoft Edge WebView2", "Runtime installed separately", "Microsoft software licence terms", "Renders the application window", version.WEBVIEW2_URL, []),
        ("GDTF Share (online service)", "online", "Terms and Conditions of GDTF Share; files belong to their uploaders", "Optional download of fixture files by the user - no GDTF files are bundled", "https://gdtf-share.com/landing/pages/termsAndConditions.php",
         [EXTRA / "gdtf-share.txt"]),
    ]
    for name, ver, lic, purpose, url, sources in extras:
        sources = [p for p in sources if p.is_file()]
        components.append({"name": name, "version": ver, "license": lic, "purpose": purpose, "url": url, "files": copy_into(name, sources)})

    (OUT / "components.json").write_text(json.dumps(components, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Third-party notices", "",
        f"{version.APP_NAME} {version.APP_VERSION_LABEL} is free software under the **{version.APP_LICENSE_NAME}** (see `LICENSE`). {version.APP_COPYRIGHT}. "
        "It ships with and uses the following components; their licence texts are in the `licenses` folder.", "",
        "| Component | Version | Licence | Used for | Homepage |", "|---|---|---|---|---|",
    ]
    lines += [f"| {c['name']} | {c['version']} | {c['license']} | {c['purpose']} | {c['url']} |" for c in components]
    lines += [
        "", "Source code of FFmpeg: https://ffmpeg.org/download.html (version of the bundled build: run `ffmpeg -version`); the build comes from https://www.gyan.dev/ffmpeg/builds/ .",
        "The PyInstaller bootloader is GPL v2 or later with the special exception that allows distributing the bundled program under any licence.", "",
        f"Source code of {version.APP_NAME}: {version.SOURCE_URL}", "",
    ]
    (OUT / "THIRD_PARTY_NOTICES.md").write_text("\n".join(lines), encoding="utf-8")
    with_text = sum(1 for c in components if c["files"])
    print(f"{len(components)} Komponenten, {with_text} mit Lizenztext -> {OUT}")
    if missing:
        print("Nicht installiert (uebersprungen):", ", ".join(missing))


if __name__ == "__main__":
    main()
