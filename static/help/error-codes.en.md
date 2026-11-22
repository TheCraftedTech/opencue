# Error Codes and Troubleshooting

When something goes wrong, OpenCue does not just disappear: it shows a small **error window** with a short explanation and an **error code** like `OC-1002`. The same code is written to the **log file**. This page explains every code: what it means and how to fix it.

If you cannot solve a problem, copy the details (see section 1) and send them with your question – the code tells us immediately where to look.

---

## 1. The error window

The window has a headline, a short explanation, the **ERROR CODE**, sometimes a box with technical details, and these buttons:

| Button | What it does |
|---|---|
| **Copy details** | Puts everything needed for a bug report into the clipboard: error code, OpenCue version, Windows and Python version, the error text and the **last 40 lines of the log**. Paste it into an e-mail, a GitHub issue or a chat with an assistant. (Shortcut: **Ctrl+C**) |
| **Open log folder** | Opens the folder with the log files in Explorer. |
| **Open log file** | Opens the current log (`opencue.log`) in your text editor. |
| **Close** | Closes the window (also **Esc** or the **×**). If the error stopped OpenCue, the program ends after you close the window. |

You can move the window by its title bar. The error window appears in the language of OpenCue (English if that cannot be determined); the text copied with *Copy details* is always English, so that a report can be read by anyone.

---

## 2. Where the log files are

Every start of OpenCue writes a log:

| File | Content |
|---|---|
| `opencue.log` | The **current** start: everything OpenCue reports – messages, warnings, errors with their codes, and crash traces. |
| `opencue.previous.log` | The log of the **start before**. After a crash and a restart the cause is still here. |

They are in the folder `logs` inside the OpenCue data folder – normally `%LOCALAPPDATA%\OpenCue\logs` (type this into the Explorer address bar). The error window opens it for you.

**Searching the log:** codes are written as `OC-1234`. Search for `OC-` to find all of them, or `OC-3` for the small problems of a single function (section 5).

---

## 3. Start problems (OC-1xxx)

OpenCue checks these things **before** anything else starts. The window tells you what is wrong; OpenCue then closes.

### OC-1001 – OpenCue is already running

**Meaning:** Only one OpenCue can run at a time per data folder. A second one would fight for the same settings, port and DMX output.

**What happens:** The window of the running OpenCue is brought to the front and this window appears. (If the running OpenCue is a **server without a window**, see the guide *Startup Options and Server Mode*, no error appears: your browser opens on the running console instead.)

**What to do:**
- Use the window that came to the front. If you cannot see it, look on your **other screens** and in the **taskbar**.
- Just closed OpenCue and still get this? It may need a few seconds to shut down. Wait a moment and start again.
- Nothing visible at all? Open the **Task Manager**, look for `OpenCue` (or `python`/`pythonw` when started from source) and end the leftover process.
- Advanced: for a second, separate OpenCue (for example for testing) set the environment variable `OPENCUE_DATA_DIR` to a different folder **and** give it a different port in its `app_config.json` (see OC-1002).
- **Starting right after closing:** OpenCue now waits (up to about 25 seconds) until the old one has finished closing and then starts by itself. You only see this message if the old one does not finish.

### OC-1002 – Network port is already in use

**Meaning:** OpenCue has a small built-in server that its window talks to. It needs a free network port (default **8000**). Another program is using that port. Without this check, the OpenCue window would show the *other* program's page.

**What to do:**
1. Close the other program. Common causes: another web server or development tool, or a leftover OpenCue process (see OC-1001, Task Manager).
2. To find out who uses the port, open a command prompt and type `netstat -ano | findstr :8000` (use your port number). The last column is the process ID; look it up in the Task Manager (*Details* tab).
3. Or let OpenCue use another port: close OpenCue, open the settings file named in the window (normally `%LOCALAPPDATA%\OpenCue\config\app_config.json`) in a text editor and change `"server_port": 8000` to a free number between **1024 and 65535**, for example `8010`. If the line is missing, add it. Save and start OpenCue again. (When OpenCue runs, you can change it in **Settings → Remote access → HTTP port** instead.)

### OC-1003 – Microsoft Edge WebView2 Runtime not found

**Meaning:** OpenCue shows its window with the free **Microsoft Edge WebView2 Runtime**. Windows 11 has it; Windows 10 usually has it through Edge or Office, but not always.

**What to do:** Click **Open download page**, install the *Evergreen* runtime from Microsoft and start OpenCue again. If you are sure the runtime is installed, click **Start anyway**. The OpenCue installer downloads the runtime automatically when it is missing and there is internet.

### OC-1004 – The data folder cannot be used

**Meaning:** OpenCue stores settings, shows, layouts and logs in its **data folder** (normally `%LOCALAPPDATA%\OpenCue`) and cannot create or write to it. The line below the explanation shows the technical reason.

**What to do:** Check that the folder exists and that your Windows account may write there; that the drive is not full, not read-only and (for a network or USB drive) connected; that no antivirus or "controlled folder access" blocks OpenCue. If a custom data folder was chosen during installation, make sure that drive is available. A folder name that is really an existing **file** also causes this.

---

## 4. Unexpected errors (OC-2xxx)

These are errors OpenCue did not expect – usually a bug. **Please copy the details and report them.** The error text and the log show where it happened.

### OC-2001 – OpenCue could not start

An unexpected error stopped OpenCue while it was starting. Restart once. If it comes back: copy the details and report it. As a workaround, a damaged settings file can be the cause: close OpenCue, rename `config\app_config.json` in the data folder to `app_config.old.json` and start again (OpenCue then starts with default settings; your shows and layouts are separate files and stay).

### OC-2002 – A background task failed

Something went wrong in a background task, for example audio analysis, MIDI or network. **OpenCue keeps running.** The window appears only for the *first* such error per start (all of them are in the log). If anything behaves strangely, save your show and restart OpenCue. Please report it with the copied details.

### OC-2003 – The OpenCue server stopped

The built-in server stopped unexpectedly or could not start, so the window cannot work. OpenCue closes after the window and releases DMX output and cameras first. Restart OpenCue. If it happens again, report it; check OC-1002 as well (a port problem can also end here).

### OC-2004 – OpenCue stopped unexpectedly

An unexpected error occurred while OpenCue was running and the program has to close. **Unsaved changes may be lost.** Restart OpenCue and report the error with the copied details. Tip: save your show regularly (**Ctrl+S**) during long sessions.

---

## 5. Problems of a single function (OC-3xxx, log only)

These do **not** open a window and OpenCue keeps running. They appear as the first thing in a **log line** (for example `... [DMX] OC-3103 USB DMX: COM3 ...`) and often as a message in the matching settings page. Search the log for `OC-3`.

| Code | Meaning | What to do |
|---|---|---|
| **OC-3001** | The settings file `app_config.json` could not be read. OpenCue used the automatic backup (`.bak`) or, if that was damaged too, the default settings. The damaged file is kept next to it as `.corrupt`. | Check your settings. To keep older settings, copy values from the `.corrupt` file into the new `app_config.json` (close OpenCue first). |
| **OC-3101** | An error occurred in the DMX output thread. | Check the DMX settings (Settings → DMX output) and the network or USB connection. Report it if it repeats. |
| **OC-3102** | The Art-Net output could not be set up (again) with the current settings. | Check the target and bind IP address in the DMX settings. The network adapter must exist and be connected. |
| **OC-3103** | The USB DMX interface was unplugged or reported a send error. | Plug it in again and press *Refresh Ports* in the DMX settings. Try another USB port or cable; check that no other program uses the port. |
| **OC-3104** | An error occurred in the clock of the DMX output (it sends the frames to Art-Net, sACN and USB). | OpenCue keeps running and the clock continues with the next frame. Report it if it repeats (Help → Report a problem). |
| **OC-3105** | The **separate DMX output process** (a second OpenCue process in the Task Manager) ended or could not be started. | OpenCue restarts it automatically (output is back in under a second). If it dies five times in a minute or does not start at all, the output continues inside the main program - without the separation, but without an outage. Check your antivirus (it must allow `OpenCue.exe` to start a second process); report it if it repeats. |
| **OC-3201** | The audio analysis could not open its input or source (device busy, removed or blocked by Windows privacy settings). | Choose another source in the Audio panel. Close programs that use the device exclusively. For a microphone allow access in Windows *Settings → Privacy → Microphone*. |
| **OC-3202** | Voice control could not open the selected microphone (OpenCue tries several times). | Choose the microphone again in Settings → Wake word; close other programs that hold it; check the Windows microphone privacy setting. |
| **OC-3301** | A MIDI device could not be opened. Under Windows most devices can be used by **one program** at a time. | Close the other program (music software, DAW) or switch the device off there. Unplug and re-plug the device. |
| **OC-3401** | The name `opencue.local` could not be announced on the network (mDNS). Remote devices can still use the IP address. | Use the address with the IP number shown in the Remote access settings. Check that the network allows multicast and that the Windows firewall allows OpenCue on private networks. |
| **OC-3402** | OpenCue could not listen on a network address for remote devices. | Another program may use that port, or the address is gone (changed Wi-Fi). Switch remote access off and on again in Settings → Remote access, or choose another port. |
| **OC-3501** | The update could not be downloaded or its checksum did not match. | Check the internet connection and try again later, or download the installer from the release page. |
| **OC-3502** | The downloaded update setup could not be started. | Download the installer from the release page and run it yourself. |
| **OC-3601** | The user interface reported a JavaScript error. The log line shows the message, the file and line and which device it happened on (the console or a remote device). Often nothing is visible; sometimes a panel stays empty. | Reload the window (or the page on the remote device). If it happens again, report it with *Help → Report a problem* – the line is part of the details. |
| **OC-3701** | A background backup of the show could not be written (disk full, folder not writable, or protected by a virus scanner). The show itself is not affected. | Free some disk space or choose another data folder (*Settings → General → Data folder & file management*). *File → Restore backup* shows which backups exist; the folder is `backups` inside the data folder. |
| **OC-3801** | OSC could not listen on its UDP port (another program uses it). | Choose another port in **Controls → OSC ...** or close the other program. |

---

## 6. Reporting a problem

1. Easiest: **Help → Report a problem...** copies the details into the clipboard and opens the report page. (In the error window: **Copy details**.) **Help → Open log folder** opens the folder with `opencue.log`.
2. On the **Issues** page of the OpenCue project on GitHub describe what you did before the error.
3. Paste the copied text. It contains no show data, only the technical information described in section 1.

Please do not send passwords or access keys; if you pasted log lines from a settings screen, remove them first.
