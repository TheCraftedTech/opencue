"""Erzeugt die Bilder des Installers (packaging/installer-img/*.bmp) aus dem Logo - nur Entwicklung, das Ergebnis liegt im Repository.

  wizard-<n>.bmp   grosses Bild links auf der Willkommens- und der Abschlussseite (164x314 bei 100 %, dazu 150 %, 200 %)
  small-<n>.bmp    kleines Bild oben rechts auf den uebrigen Seiten (55x55, dazu 150 %, 200 %)

Gerendert wird mit Chrome/Edge (wie make_icon.py); die Version steht NICHT auf den Bildern (die zeigt der Installer selbst im Text), damit sie nie veralten.
Aufruf (im Projektordner):  venv\\Scripts\\python.exe packaging\\make_installer_images.py
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
import zlib
from pathlib import Path

import websockets

HERE = Path(__file__).resolve().parent
OUT = HERE / "installer-img"
LAMP = (HERE / "icon-src" / "OpenCue-lamp.svg").as_posix()
CHROME = next((c for c in (os.environ.get("CHROME", ""), r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                           r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe") if c and Path(c).is_file()), None)
PORT = 9478
BACKGROUND = "#151517"

WIZARD = """<html><body style="margin:0;width:164px;height:314px;overflow:hidden;background:linear-gradient(180deg,#1d1d20 0%,#0e0e10 100%);font-family:Segoe UI,Arial,sans-serif">
<div style="position:absolute;left:0;top:0;width:4px;height:314px;background:#ffb000"></div>
<img src="file:///{lamp}" style="position:absolute;left:22px;top:46px;width:120px;height:120px;image-rendering:pixelated">
<div style="position:absolute;left:0;top:186px;width:164px;text-align:center;color:#fff;font-size:27px;font-weight:700;letter-spacing:.5px">Open<span style="color:#ffb000">Cue</span></div>
<div style="position:absolute;left:0;top:226px;width:164px;text-align:center;color:#9a9aa3;font-size:11px;line-height:1.5">DMX lighting<br>control console</div>
</body></html>"""
SMALL = """<html><body style="margin:0;width:55px;height:55px;overflow:hidden;background:{bg}"><img src="file:///{lamp}" style="width:55px;height:55px;image-rendering:pixelated"></body></html>"""


def png_to_bmp(png: bytes) -> bytes:
    """24-Bit-BMP aus einer (nicht interlaced) 8-Bit-RGB(A)-PNG - ohne Pillow."""
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    pos, data, header = 8, b"", None
    while pos < len(png):
        length, kind = struct.unpack(">I4s", png[pos:pos + 8])
        chunk = png[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", chunk)
        elif kind == b"IDAT":
            data += chunk
        pos += 12 + length
    width, height, depth, color, _c, _f, interlace = header
    assert depth == 8 and interlace == 0 and color in (2, 6), header
    bpp = 3 if color == 2 else 4
    raw = zlib.decompress(data)
    stride = width * bpp
    rows, prev = [], bytearray(stride)
    for y in range(height):
        f = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line)
        prev = line
    pad = (4 - (width * 3) % 4) % 4
    pixels = b""
    for line in reversed(rows):
        out = bytearray()
        for x in range(width):
            r, g, b = line[x * bpp], line[x * bpp + 1], line[x * bpp + 2]
            out += bytes((b, g, r))
        pixels += bytes(out) + b"\x00" * pad
    return b"BM" + struct.pack("<IHHI", 54 + len(pixels), 0, 0, 54) + struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0, len(pixels), 2835, 2835, 0, 0) + pixels


async def render(jobs):
    if not CHROME:
        sys.exit("Weder Chrome noch Edge gefunden (Umgebungsvariable CHROME setzen).")
    work = Path(tempfile.mkdtemp(prefix="oc-inst-img-"))
    proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", f"--remote-debugging-port={PORT}", f"--user-data-dir={work / 'p'}", "--allow-file-access-from-files", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        target = None
        for _ in range(80):
            try:
                target = next(x for x in json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json").read()) if x["type"] == "page")
                break
            except Exception:
                time.sleep(0.25)
        ws = await websockets.connect(target["webSocketDebuggerUrl"], max_size=80_000_000)
        seq = [0]

        async def cdp(method, **params):
            seq[0] += 1
            await ws.send(json.dumps({"id": seq[0], "method": method, "params": params}))
            while True:
                message = json.loads(await ws.recv())
                if message.get("id") == seq[0]:
                    return message.get("result", {})

        await cdp("Page.enable")
        results = {}
        page = work / "p.html"
        for name, html, w, h, scale in jobs:
            page.write_text(html, encoding="utf-8")
            await cdp("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=scale, mobile=False)
            await cdp("Page.navigate", url="file:///" + page.as_posix())
            await asyncio.sleep(0.8)
            shot = await cdp("Page.captureScreenshot", format="png")
            results[name] = base64.b64decode(shot["data"])
        return results
    finally:
        proc.terminate()


def main() -> None:
    jobs = []
    for pct, scale in ((100, 1), (150, 1.5), (200, 2)):
        jobs.append((f"wizard-{pct}", WIZARD.replace("{lamp}", LAMP), 164, 314, scale))
        jobs.append((f"small-{pct}", SMALL.replace("{lamp}", LAMP).replace("{bg}", BACKGROUND), 55, 55, scale))
    OUT.mkdir(exist_ok=True)
    for name, png in asyncio.run(render(jobs)).items():
        (OUT / f"{name}.bmp").write_bytes(png_to_bmp(png))
        print("geschrieben:", name)


if __name__ == "__main__":
    main()
