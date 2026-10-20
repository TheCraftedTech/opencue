# Getting Started with OpenCue

OpenCue is a lighting control console for your PC. This guide takes you from the installer to your first light cue in about ten minutes – with no lights connected, because the first steps work with the built-in demo show.

---

## 1. What you need

- A PC with **Windows 10 or 11** (64-bit). The **Microsoft Edge WebView2 Runtime** shows OpenCue's window; it is part of current Windows, and the installer sets it up if it is missing (internet needed once for that).
- For real lights: a DMX connection – via the network (**Art-Net** or **sACN**) or a **USB DMX interface** (Enttec DMX USB Pro and compatible). Without any hardware you can still program everything and watch it in the **3D simulation**.
- No account, no licence key, no internet connection while working.

---

## 2. Installing

1. Download `OpenCue-Setup-v<version>.exe` from the Releases page of the project and run it.
2. The setup starts with a welcome page where you choose the **language** (English or German; it is also the language of OpenCue itself).
3. Click through: **License** (the GNU GPL, to read), **Program folder**, **Data folder**, **Shortcuts** (Start menu, desktop), the summary, **Install**.
4. Finish and start OpenCue.

The **data folder** is where your shows, layouts, fixtures and settings live. The default (`%LOCALAPPDATA%\OpenCue`) is fine for most people; you can choose another location in the setup and change it later in OpenCue under *Settings → Storage*.

If OpenCue is already installed, the setup recognises that and offers *Update*, *Reinstall* or *Uninstall* – your data always stays. OpenCue also checks for new versions at start (switchable in *Settings → General*) and offers to install them; *Help → Check for Updates…* does it on demand.

OpenCue can be found through the Windows search (press the Windows key and type “OpenCue”).

---

## 3. The first start

On a fresh installation OpenCue opens a ready-made **demo show** named **Default_1**:

- five **Generic Dimmers** (“Dimmer 1” … “Dimmer 5”) in universe 1 on channels 1 to 5,
- a cue list “Default” with two cues (“Cue 1” and “Cue 2”, one second fade each),
- a **layout** with the panels you need first: cue list, fixture list, fixture control, executor, command line, command buttons and numpad.

No stage exists in the 3D simulation yet – you create one when you need it. The demo files are normal files: change or delete them as you like.

---

## 4. The interface in a minute

### Menus (top left)

| Menu | What it contains |
|---|---|
| **File** | New / Open / Save / Save As (showfiles), Sign out (remote devices only), Exit |
| **Edit** | **Edit Panels** (edit mode), Undo / Redo, **Add Panel…**, Add Button / Add Fader, **Manage Layouts…** |
| **Library** | **Fixture Library…**, 3D stages, and the file manager lists *Shows*, *Layouts*, *3D stages*, *Effects* |
| **View** | Fullscreen, GUI scale, Layouts |
| **Language** | English / Deutsch |
| **Help** | Keyboard Shortcuts, GitHub repository, Check for Updates…, About OpenCue |

### Toolbar (top)

The toolbar shows the current **layout** and **stage**, the **showfile name** (click it to open the file manager), a pulsing **Blackout** button (bulb), the **timecode**, a DMX indicator, the number of connected **remote devices**, and the **Settings** button.

### Panels

Everything else is **panels** that you place freely. The most important ones:

| Panel | Purpose |
|---|---|
| **Fixture List** | The patch: add, edit and delete fixtures |
| **Fixture Control** | Dimmer, position, colour, beam, focus and DMX direct for the selected fixtures; also the tile grid for selecting |
| **Cue List** | The cues of a list: store, update, edit, delete, play |
| **Executor** | Playback with Go / Pause / Back / Stop and a mix fader |
| **Command Line**, **Command Numpad**, **Command Buttons** | Typing and touch input for commands |
| **Variables / Effects** | Reusable colours, positions, beams and effects |
| **Effect Studio** | Write your own effects |
| **DMX Monitor** | See the values that are being sent |
| **3D Simulation** | See your stage and lights live |
| **Timecode**, **Video/Audio Player**, **Livestream / Camera** | Time and media |
| **Button**, **Fader** | Own buttons and faders that run commands |

Add panels with **Edit → Add Panel…**.

---

## 5. Your first cue

You can follow this with the demo show.

### Step 1 – Select

Click fixtures in the **Fixtures** tab of the Fixture Control panel (or in the fixture list) – or type in the command line:

```
Fixture 1 Thru 3
```

### Step 2 – Set a look

Use the **Dimmer** fader – or type:

```
At 80
```

Choose a colour if your fixtures have one (`Color Red`). Changed fixtures get a red marker: they are now in the **programmer**.

### Step 3 – Store a cue

Click **Save Cue** in the Cue List panel. A dialog asks for the **position** (at the end, after a cue, or free), the **cue number** and an optional **name**. Click **Store**. Or type:

```
Store Cue 3 "Warm look"
```

If the number already exists you choose **Merge** (only the changed channels go in) or **Overwrite**.

### Step 4 – Play it

Press **Go** in the Cue List or Executor panel – or type `Go`. The look fades in over the cue's fade time. `Go Cue 3` jumps directly to a cue; **Back** goes one cue back; **Pause** and **Stop** control a running fade.

Use the **Executor fader** to mix between your manual values (0 %) and the cue (100 %).

### Step 5 – Save

Press `Ctrl+S`. This saves the **showfile** and your **layout**. Without saving, changes live only in memory; OpenCue asks before it closes.

---

## 6. Connecting real lights

1. Open **Settings → DMX / Network**.
2. For **Art-Net**: it is on by default; set the **Target IP** (the default is the Art-Net broadcast address) and, if needed, the **Bind IP** (which network card to use).
3. For **sACN (E1.31)**: switch it on. It is off by default so that Windows does not show a firewall question on first start.
4. For **USB DMX** (Enttec DMX USB Pro or compatible): switch it on, choose the **COM port** and the **universe**. The connection is re-established after unplugging.
5. If an interface does not start, use **Re-initialize DMX Interfaces** – no restart needed.

Then **patch** your fixtures (guide *Fixtures and Patching*): the universe and start channel must match the address set on each device.

The **DMX Monitor** panel shows exactly what is being sent. The **Blackout** button sets all brightness to 0 instantly; clicking it again brings the look back.

---

## 7. Making the interface yours

- **Edit mode** (**Edit → Edit Panels**, `Ctrl+E`): move and resize panels, change their properties and colours, copy and paste them.
- **Layouts** are files. Build several (for example a small one for programming and a big one for playback) and switch with `Ctrl+1` … `Ctrl+9` or **View → Layouts**. Save with `Ctrl+S` or in the file manager.
- **Themes** (colour profiles): *Settings → Colors* – dark, light, or your own.
- **GUI scale** (`Ctrl +` / `Ctrl -`): makes everything larger for touch screens; it is stored per device.
- **Language:** *Language* menu or `Ctrl+Shift+L`.

---

## 8. What to explore next

| Topic | Where |
|---|---|
| Fixtures, GDTF library, patching, groups | *Fixtures and Patching* |
| All typed commands | *Command Reference* |
| Own effects with a small scripting language | *Effect Studio* |
| Tablet and phone as remote control | *Remote Control* |
| Every shortcut and gesture | *Keyboard Shortcuts* (also **Help → Keyboard Shortcuts**) |
| Stage in 3D, aiming moving heads at a point | Panel **3D Simulation** (add it via *Add Panel*; modes View / Build / Fixtures) |
| Cues that start at a time | **Timecode** panel and cue trigger *Timecode* |
| Files: shows, layouts, stages, effects | **Library → Shows… / Layouts… / 3D stages… / Effects…** (the file manager, with import and export as ZIP) |

---

## 9. Where your data is and how to back it up

Your data is plain files in the data folder (`%LOCALAPPDATA%\OpenCue` by default):

| Folder | Content |
|---|---|
| `showfiles` | Shows (fixtures, groups, cues, presets, effects) |
| `layouts` | Panel layouts |
| `themes` | Colour profiles |
| `fixtures` | GDTF fixture files |
| `effects` | Effect scripts (`.fx`) |
| `stages` | 3D stages |
| `media` | Videos and audio of your shows |
| `config` | Settings (`app_config.json`) |

To back up, copy the folder – or use the file manager's **export** (a show as a ZIP including the fixtures and effects it needs), which also lets you move a show to another computer.

Uninstalling OpenCue asks whether to delete this data too; the default is **No**.
