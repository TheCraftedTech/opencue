# Third-party notices

OpenCue v1.0.0 is free software under the **GNU General Public License v3.0 or later** (see `LICENSE`). Copyright (C) 2026 Samuel Zenker. It ships with and uses the following components; their licence texts are in the `licenses` folder.

| Component | Version | Licence | Used for | Homepage |
|---|---|---|---|---|
| fastapi | 0.141.1 | MIT | Web framework (server) | https://github.com/fastapi/fastapi |
| starlette | 1.7.0 | BSD-3-Clause | Web toolkit used by FastAPI | https://github.com/Kludex/starlette |
| pydantic | 2.13.5 | MIT | Data validation (FastAPI) | https://github.com/pydantic/pydantic |
| pydantic_core | 2.46.5 | MIT | Core of pydantic | https://github.com/pydantic |
| annotated-types | 0.8.0 | MIT | pydantic | https://github.com/annotated-types/annotated-types |
| annotated-doc | 0.0.5 | MIT | FastAPI | https://github.com/fastapi/annotated-doc |
| typing_extensions | 4.16.0 | PSF-2.0 | Typing backports | https://github.com/python/typing_extensions |
| typing-inspection | 0.4.4 | MIT | pydantic | https://github.com/pydantic/typing-inspection |
| anyio | 4.15.1 | MIT | Async foundation |  |
| idna | 3.20 | BSD-3-Clause | Domain names | https://github.com/kjd/idna |
| uvicorn | 0.53.0 | BSD-3-Clause | HTTP/WebSocket server | https://uvicorn.dev/ |
| click | 8.5.0 | BSD-3-Clause | uvicorn | https://github.com/pallets/click/ |
| h11 | 0.16.0 | MIT License | HTTP (uvicorn) | https://github.com/python-hyper/h11 |
| httptools | 0.8.0 | MIT | HTTP (uvicorn) | https://github.com/MagicStack/httptools |
| websockets | 17.1 | BSD-3-Clause | WebSocket (uvicorn) | https://github.com/python-websockets/websockets |
| python-dotenv | 1.2.3 | BSD-3-Clause | uvicorn (optional) | https://github.com/theskumar/python-dotenv |
| PyYAML | 6.0.3 | MIT License | uvicorn (optional) | https://pyyaml.org/ |
| Jinja2 | 3.1.6 | BSD License | HTML templates | https://github.com/pallets/jinja/ |
| MarkupSafe | 3.0.3 | BSD-3-Clause | Jinja2 | https://github.com/pallets/markupsafe/ |
| pywebview | 6.2.1 | BSD License | Application window (WebView2) | https://pywebview.flowrl.com/ |
| pythonnet | 3.1.0 | MIT | pywebview: .NET bridge | https://pythonnet.github.io/ |
| clr_loader | 0.3.1 | see licence file | pythonnet |  |
| cffi | 2.1.1 | MIT-0 | clr_loader |  |
| pycparser | 3.0 | BSD-3-Clause | cffi | https://github.com/eliben/pycparser |
| proxy_tools | 0.1.0 | MIT License | pywebview | http://github.com/jtushman/proxy_tools |
| bottle | 0.13.4 | MIT License | pywebview | https://github.com/bottlepy/bottle |
| sacn | 1.11.0 | MIT License | sACN output | https://www.github.com/Hundemeier/sacn |
| stupidArtnet | 1.6.0 | MIT License | Art-Net output | https://github.com/cpvalente/stupidArtnet |
| pyserial | 3.5 | BSD License | USB DMX (Enttec) | https://github.com/pyserial/pyserial |
| pygdtf | 1.4.5 | see licence file | Reading GDTF fixture files | https://github.com/open-stage/python-gdtf.git |
| assimp_py | 1.2.0 | see licence file | 3D models inside GDTF files (Assimp) | https://github.com/ranjian0/assimp_py |
| segno | 1.6.6 | BSD License | QR codes (remote access) | https://github.com/heuer/segno/ |
| FFmpeg | 8.1 (gyan.dev essentials build) | GPL-3.0 (build with --enable-gpl --enable-version3) | Camera capture on the main device (separate program, ffmpeg/ffmpeg.exe) | https://ffmpeg.org/ |
| three.js | r186 | MIT | 3D simulation and fixture model viewer (static/vendor/three) | https://threejs.org/ |
| Python | 3.13.9 | PSF-2.0 | Runtime bundled by PyInstaller | https://www.python.org/ |
| Microsoft Edge WebView2 | Runtime installed separately | Microsoft software licence terms | Renders the application window | https://developer.microsoft.com/microsoft-edge/webview2/ |
| GDTF Share (online service) | online | Terms and Conditions of GDTF Share; files belong to their uploaders | Optional download of fixture files by the user - no GDTF files are bundled | https://gdtf-share.com/landing/pages/termsAndConditions.php |

Source code of FFmpeg: https://ffmpeg.org/download.html (version of the bundled build: run `ffmpeg -version`); the build comes from https://www.gyan.dev/ffmpeg/builds/ .
The PyInstaller bootloader is GPL v2 or later with the special exception that allows distributing the bundled program under any licence.

Source code of OpenCue: https://github.com/TheCraftedTech/opencue
