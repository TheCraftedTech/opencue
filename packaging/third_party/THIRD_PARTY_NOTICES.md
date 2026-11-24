# Third-party notices

OpenCue v2.3.0 is free software under the **GNU General Public License v3.0 or later** (see `LICENSE`). Copyright (C) 2026 Samuel Zenker. It ships with and uses the following components; their licence texts are in the `licenses` folder.

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
| zeroconf | 0.153.0 | LGPL-2.1-or-later | Network name opencue.local (mDNS) | https://github.com/python-zeroconf/python-zeroconf |
| ifaddr | 0.2.0 | MIT License | zeroconf | https://github.com/pydron/ifaddr |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | Self-signed https certificate | https://github.com/pyca/cryptography |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | Audio analysis (spectrum, beat detection) | https://numpy.org |
| PyAudioWPatch | 0.2.12.9 | Apache Software License | Audio capture (PortAudio, WASAPI) | https://github.com/s0d3s/PyAudioWPatch/ |
| python-rtmidi | 1.5.8 | MIT License | MIDI input and output (RtMidi) | https://github.com/SpotlightKid/python-rtmidi |
| vosk | 0.3.45 | Apache Software License | Offline speech recognition (wake word) | https://github.com/alphacep/vosk-api |
| requests | 2.34.2 | Apache Software License | vosk | https://github.com/psf/requests |
| urllib3 | 2.8.0 | MIT | requests |  |
| certifi | 2026.10.23 | Mozilla Public License 2.0 (MPL 2.0) | requests | https://github.com/certifi/python-certifi |
| charset-normalizer | 3.5.2 | MIT | requests |  |
| tqdm | 4.70.1 | MPL-2.0 AND MIT | vosk | https://tqdm.github.io |
| colorama | 0.4.6 | BSD License | tqdm | https://github.com/tartley/colorama |
| srt | 3.5.3 | MIT License | vosk | https://github.com/cdown/srt |
| faster-whisper | 1.2.1 | MIT License | Offline dictation: speech to text (Whisper) | https://github.com/SYSTRAN/faster-whisper |
| ctranslate2 | 4.8.5 | MIT | Inference engine of faster-whisper | https://github.com/OpenNMT/CTranslate2 |
| onnxruntime | 1.31.1 | MIT License | Voice activity detection (faster-whisper) | https://onnxruntime.ai |
| tokenizers | 0.23.3 | Apache Software License | Text tokenizer of the Whisper model | https://github.com/huggingface/tokenizers |
| huggingface_hub | 2.4.0 | Apache Software License | Downloads the Whisper model once | https://github.com/huggingface/huggingface_hub |
| filelock | 4.2.7 | MIT | huggingface_hub | https://github.com/tox-dev/filelock |
| fsspec | 2026.9.0 | BSD-3-Clause | huggingface_hub | https://github.com/fsspec/filesystem_spec |
| httpx2 | 2.16.0 | BSD-3-Clause | huggingface_hub | https://github.com/pydantic/httpx2 |
| httpcore2 | 2.16.0 | BSD-3-Clause | httpx2 | https://github.com/pydantic/httpx2 |
| truststore | 0.10.5 | MIT | httpx2 | https://github.com/sethmlarson/truststore |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | huggingface_hub | https://github.com/pypa/packaging |
| protobuf | 7.36.2 | 3-Clause BSD License | onnxruntime | https://developers.google.com/protocol-buffers/ |
| flatbuffers | 25.12.19 | Apache Software License | onnxruntime | https://github.com/google/flatbuffers |
| FFmpeg | 8.1 (gyan.dev essentials build) | GPL-3.0 (build with --enable-gpl --enable-version3) | Camera capture on the main device (separate program, ffmpeg/ffmpeg.exe) | https://ffmpeg.org/ |
| three.js | r186 | MIT | 3D simulation and fixture model viewer (static/vendor/three) | https://threejs.org/ |
| Python | 3.13.9 | PSF-2.0 | Runtime bundled by PyInstaller | https://www.python.org/ |
| Vosk speech model (small, English) | 0.15 | Apache-2.0 | Wake word recognition, offline (downloaded once on request into the data folder: voice/vosk-model-small-en-us-0.15) | https://alphacephei.com/vosk/models |
| Whisper speech models (base, small; CTranslate2 conversion) | 1.2 | MIT | Offline dictation (loaded once from Hugging Face into the data folder: models/whisper) | https://huggingface.co/Systran |
| Inter (font) | 4 (Fontsource 5.2.5, variable) | OFL-1.1 | User interface font (static/fonts) | https://rsms.me/inter/ |
| JetBrains Mono (font) | 2 (Fontsource 5.2.5, variable) | OFL-1.1 | Monospace font for values and the command line (static/fonts) | https://www.jetbrains.com/lp/mono/ |
| Microsoft Edge WebView2 | Runtime installed separately | Microsoft software licence terms | Renders the application window | https://developer.microsoft.com/microsoft-edge/webview2/ |
| GDTF Share (online service) | online | Terms and Conditions of GDTF Share; files belong to their uploaders | Optional download of fixture files by the user - no GDTF files are bundled | https://gdtf-share.com/landing/pages/termsAndConditions.php |

Source code of FFmpeg: https://ffmpeg.org/download.html (version of the bundled build: run `ffmpeg -version`); the build comes from https://www.gyan.dev/ffmpeg/builds/ .
The PyAV wheel (av, used by faster-whisper for audio decoding) includes FFmpeg shared libraries under the LGPL v2.1 or later; they stay separate files next to the program and can be replaced. Source code: https://ffmpeg.org/download.html .
The PyInstaller bootloader is GPL v2 or later with the special exception that allows distributing the bundled program under any licence.

Source code of OpenCue: https://github.com/TheCraftedTech/opencue
