"""Erzeugt aus app/version.py die Dateien, die der Build braucht (nie von Hand aendern - bei jeder neuen Version neu erzeugen, das Build-Skript macht es selbst):

  packaging/version_info.txt   Windows-Versionsresource der OpenCue.exe (Rechtsklick -> Eigenschaften -> Details): Firma, Beschreibung, Version, Copyright (Englisch)
  packaging/version.iss        dieselben Angaben fuer den Inno-Setup-Installer (packaging/OpenCue.iss)

Aufruf (im Projektordner):  venv\\Scripts\\python.exe packaging\\make_version_info.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from app import version  # noqa: E402


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("'", "\\'")


def main() -> None:
    major, minor, patch, build = version.version_tuple()
    dotted = f"{major}.{minor}.{patch}.{build}"
    comments = f"{version.APP_LICENSE_NAME}. Source code: {version.SOURCE_URL}"
    info = f"""# UTF-8
# Erzeugt von packaging/make_version_info.py aus app/version.py - nicht von Hand aendern.
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, {build}),
    prodvers=({major}, {minor}, {patch}, {build}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', '{esc(version.APP_COMPANY)}'),
        StringStruct('FileDescription', '{esc(version.APP_DESCRIPTION)}'),
        StringStruct('FileVersion', '{dotted}'),
        StringStruct('InternalName', '{esc(version.APP_NAME)}'),
        StringStruct('LegalCopyright', '{esc(version.APP_COPYRIGHT)}'),
        StringStruct('OriginalFilename', '{esc(version.APP_EXE_NAME)}'),
        StringStruct('ProductName', '{esc(version.APP_NAME)}'),
        StringStruct('ProductVersion', '{esc(version.APP_VERSION_LABEL)}'),
        StringStruct('Comments', '{esc(comments)}')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    (HERE / "version_info.txt").write_text(info, encoding="utf-8")
    iss = f"""; Erzeugt von packaging/make_version_info.py aus app/version.py - nicht von Hand aendern.
#define AppName "{version.APP_NAME}"
#define AppVersion "{version.APP_VERSION}"
#define AppVersionLabel "{version.APP_VERSION_LABEL}"
#define AppVersionNumeric "{dotted}"
#define AppPublisher "{version.APP_COMPANY}"
#define AppURL "{version.WEBSITE_URL}"
#define AppExeName "{version.APP_EXE_NAME}"
#define AppDescription "{version.APP_DESCRIPTION}"
#define AppCopyright "{version.APP_COPYRIGHT}"
"""
    (HERE / "version.iss").write_text(iss, encoding="utf-8")
    print(f"{version.APP_NAME} {version.APP_VERSION_LABEL} ({dotted}) -> version_info.txt, version.iss")


if __name__ == "__main__":
    main()
