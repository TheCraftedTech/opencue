"""Erzeugt packaging/OpenCue.ico aus den Pixel-Logos in packaging/icon-src/ (nur fuer die Entwicklung, gehoert nicht ins Programm).

Die Groessen 256 / 128 / 64 zeigen das ganze Logo mit Schrift (OpenCue-full.svg), die kleinen 48 / 32 / 24 / 16 nur die Lampe (OpenCue-lamp.svg) - die Schrift waere dort
nicht lesbar. Gerendert wird mit dem installierten Chrome (headless, ueber das DevTools-Protokoll, Paket `websockets` aus dem venv), gepackt wird die .ico von Hand
(PNG-komprimierte Eintraege, ab Windows Vista ueblich) - es wird kein Pillow gebraucht.

Aufruf (im Projektordner):  venv\\Scripts\\python.exe packaging\\make_icon.py
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets

HERE = Path(__file__).resolve().parent
SOURCES = {"full": HERE / "icon-src" / "OpenCue-full.svg", "lamp": HERE / "icon-src" / "OpenCue-lamp.svg"}
SIZES = [(256, "full"), (128, "full"), (64, "full"), (48, "lamp"), (32, "lamp"), (24, "lamp"), (16, "lamp")]
CHROME_CANDIDATES = [
    os.environ.get("CHROME", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
PORT = 9477


async def render() -> dict[int, bytes]:
    chrome = next((c for c in CHROME_CANDIDATES if c and Path(c).is_file()), None)
    if not chrome:
        sys.exit("Weder Chrome noch Edge gefunden (Umgebungsvariable CHROME auf die exe setzen).")
    work = Path(tempfile.mkdtemp(prefix="oc-icon-"))
    proc = subprocess.Popen([chrome, "--headless=new", "--disable-gpu", "--no-first-run", f"--remote-debugging-port={PORT}", f"--user-data-dir={work / 'profile'}",
                             "--allow-file-access-from-files", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        target = None
        for _ in range(80):
            try:
                target = next(x for x in json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json").read()) if x["type"] == "page")
                break
            except Exception:
                time.sleep(0.25)
        if target is None:
            sys.exit("Browser startete nicht.")
        ws = await websockets.connect(target["webSocketDebuggerUrl"], max_size=80_000_000)
        seq = [0]

        async def cdp(method: str, **params):
            seq[0] += 1
            await ws.send(json.dumps({"id": seq[0], "method": method, "params": params}))
            while True:
                message = json.loads(await ws.recv())
                if message.get("id") == seq[0]:
                    return message.get("result", {})

        await cdp("Page.enable")
        images: dict[int, bytes] = {}
        page = work / "page.html"
        for size, kind in SIZES:
            src = SOURCES[kind].as_posix()
            page.write_text(f'<html><body style="margin:0;background:transparent;overflow:hidden"><img src="file:///{src}" style="display:block;width:{size}px;height:{size}px"></body></html>', encoding="utf-8")
            await cdp("Emulation.setDeviceMetricsOverride", width=size, height=size, deviceScaleFactor=1, mobile=False)
            await cdp("Emulation.setDefaultBackgroundColorOverride", color={"r": 0, "g": 0, "b": 0, "a": 0})
            await cdp("Page.navigate", url="file:///" + page.as_posix())
            await asyncio.sleep(0.8)
            shot = await cdp("Page.captureScreenshot", format="png")
            images[size] = base64.b64decode(shot["data"])
        return images
    finally:
        proc.terminate()


def pack_ico(images: dict[int, bytes]) -> bytes:
    sizes = sorted(images, reverse=True)
    header = struct.pack("<HHH", 0, 1, len(sizes))
    entries = b""
    offset = 6 + 16 * len(sizes)
    data = b""
    for size in sizes:
        png = images[size]
        w, h = struct.unpack(">II", png[16:24])
        assert (w, h) == (size, size), (size, w, h)
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(png), offset)
        data += png
        offset += len(png)
    return header + entries + data


def main() -> None:
    images = asyncio.run(render())
    target = HERE / "OpenCue.ico"
    target.write_bytes(pack_ico(images))
    print(f"{target} geschrieben: {', '.join(str(s) for s in sorted(images, reverse=True))} px")


if __name__ == "__main__":
    main()
