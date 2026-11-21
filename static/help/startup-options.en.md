# Startup Options and Server Mode

OpenCue can be started with options – in a shortcut, a batch file, the Task Scheduler or a terminal. This guide lists them, explains the **server mode without a window** (`--no-ui`), **Start with Windows**, what **administrator rights** do (and do not) change, and the **Windows Firewall** rule.

---

## 1. The options

Put them behind the program: `OpenCue.exe --no-ui --open-browser` (from source: `python main.py ...`). In a shortcut: *Properties → Target*, after the closing quote of the path.

| Option | What it does |
|---|---|
| `--no-ui` or `--server-only` | Start **without a program window** (section 2). Implies `--no-splash`. |
| `--open-browser` | With `--no-ui`: open the default browser on the console at start. |
| `SHOWFILE` or `--show FILE` | Load this show instead of the last one. A show file as the first parameter works like a double-click start; this includes an `.ocshow` file (export package). If OpenCue is already running, the running program takes the file over (and asks first about unsaved changes). |
| `--new-show` | Start with an **empty show** instead of the last one. Nothing is deleted; the "last used" show stays as it was. |
| `--port N` | Server port **for this run only** (1–65535). The saved setting does not change. |
| `--remote` | Switch **network access** on (as in *Settings → Remote access*) – this one is **saved**. |
| `--data-dir FOLDER` | Use another **data folder** for this run (portable use, tests). Same as the variable `OPENCUE_DATA_DIR`. |
| `--fullscreen` | Start the program window in full screen. |
| `--priority normal`, `above` or `high` | Process priority; default `above` (above normal), see section 5. |
| `--no-splash` | No start screen (also: `OPENCUE_NO_SPLASH=1`). |
| `--version`, `--help` | Print the version or the list of options. |

The built program has no console of its own: `--help` and `--version` write to the console they were started from (cmd, PowerShell).

---

## 2. Server mode without a window (`--no-ui`)

OpenCue starts as usual – DMX output, cues, effects, MIDI, remote access, the REST API – but **no program window opens**. You control it from

- **a browser on this computer:** `http://127.0.0.1:8000` (the port from *Settings → Remote access*, or `--port`) – exactly the same console as in the window, or
- **a tablet or phone** over the network (switch on **Remote access** in the settings or start once with `--remote`).

A **symbol in the notification area** of the taskbar shows that OpenCue is running: **click** it to open the console in your browser; **right-click** for the menu *Open OpenCue in the browser*, *Open log folder* and *Quit OpenCue*. If the show has unsaved changes, quitting asks once (a backup copy is saved in any case).

The menu shows the **name of the show** at the top, the warning **⚠ Unsaved changes** when there are some (so does the tooltip of the icon) and the **addresses** the console can be reached at (with remote access on, also those in the network) - a click opens one in the browser.

Other ways to quit: **File → Exit** in the browser, **Ctrl+C** if it was started from a terminal, and Windows signing out or shutting down (OpenCue then tries to quit cleanly, with the usual backup).

**Starting OpenCue a second time** while the server runs does not show an error: it simply opens your browser on the running console.

What **may not work** without the window: things that need the native program window itself – for example the file picker for *linking* a video or audio file, or the full-screen toggle of the window. Everything else is available in the browser.

Tip: for a stage PC that only outputs DMX, switch on *Start with Windows* + *Start without a window* (section 3).

---

## 3. Start with Windows

**Settings → General → Behaviour:**

- **Start OpenCue when I sign in to Windows** – an entry for **your Windows user** (no administrator rights needed; remove it by switching it off).
- **Start without a window (server only)** – starts with `--no-ui`.

This is available in the **installed program**, not when started from the source code. (An exported show with the extension `.ocshow` always opens in OpenCue with a double-click there - there is no switch for it.) The entry points to the program file: if you move or reinstall OpenCue elsewhere, switch it off and on again.

---

## 4. Administrator rights and the firewall

**Does OpenCue run as administrator?** The log (`opencue.log`, first lines) and the details of an error report say *"Administrator: yes"* or *"no"*. If it does, OpenCue also writes a note to the log.

**You do not need it – and should not use it:** Windows blocks **dragging files from Explorer** into a program that runs as administrator, and a web server with administrator rights is a bigger target. Administrator rights help with **one** thing: creating the **Windows Firewall rule**.

**Firewall rule:** without it Windows asks the first time OpenCue uses the network; an unanswered or refused question blocks tablets, sACN and the network name `opencue.local`. **Settings → Remote access → Windows Firewall → Allow OpenCue in the firewall** creates a rule for exactly this program, **inbound, only in private and domain networks** (never in public ones). Windows asks for permission **once** (administrator prompt) – only this one small command is started with elevated rights, OpenCue itself keeps running normally. *Remove the firewall rule* deletes it again. The status line shows whether the rule exists.

---

## 5. Priority and exact timing

At start OpenCue sets the **process priority** to *above normal* and the **timer resolution to 1 ms** (Windows normally ticks every 15.6 ms). Both keep the 40 Hz loops of cues, effects and DMX smooth when the computer is busy – no administrator rights needed. `--priority high` raises it further (for a PC that does nothing else), `--priority normal` switches it off.

---

## 6. Examples

- Server on a stage PC, browser opens: `OpenCue.exe --no-ui --open-browser`
- Open a show from Explorer's *Open with*: `OpenCue.exe "D:\Shows\Concert.json"`
- Start empty without touching the last show: `OpenCue.exe --new-show`
- Test on another port with its own data: `OpenCue.exe --port 8080 --data-dir D:\OpenCueTest`
