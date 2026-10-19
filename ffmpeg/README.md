# ffmpeg (bundled, separate program)

OpenCue uses `ffmpeg.exe` only for cameras on the main device (Livestream panel). It is started as a **separate process** and never linked into OpenCue.

| | |
|---|---|
| Build | FFmpeg 8.1 "essentials" build from https://www.gyan.dev/ffmpeg/builds/ (64-bit, static) |
| Licence | **GNU GPL v3** (`--enable-gpl --enable-version3`, includes x264/x265), full text in `LICENSE.txt` |
| Source code | https://ffmpeg.org/download.html (FFmpeg 8.1) – the corresponding source of the build is available from the same sources |
| Upgrade | replace `ffmpeg.exe` here by a newer build and update the version line above and in `packaging/third_party` (run `packaging/collect_licenses.py`) |

Search order (`app/host_cameras.py`): environment variable `OPENCUE_FFMPEG`, `ffmpeg/ffmpeg.exe` in the program folder, next to `OpenCue.exe`, the data folder, then the `PATH`.
