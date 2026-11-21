# Getting Started with OpenCue

OpenCue is a lighting control console for your PC. This guide takes you from the installer to your first light cue in about ten minutes – with no lights connected, because the first steps work with the built-in demo show.

All guides are also inside the program, even offline: **Help → Guides** (or **F1**) opens them with a search (`Ctrl+F` inside).

---

## 1. What you need

- A PC with **Windows 10 or 11** (64-bit). The **Microsoft Edge WebView2 Runtime** shows OpenCue's window; it is part of current Windows, and the installer sets it up if it is missing (internet needed once for that).
- For real lights: a DMX connection – via the network (**Art-Net** or **sACN**) or a **USB DMX interface** (Enttec DMX USB Pro and compatible). Without any hardware you can still program everything and watch it in the **3D simulation**.
- No account, no licence key, no internet connection while working.

---

## 2. Installing

1. Download `OpenCue-Setup-v<version>.exe` from the Releases page of the project and run it.
2. The setup starts with a welcome page where you choose the **language** (English or German; it is also the language of OpenCue itself - more languages can be chosen later in the *Language* menu).
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

A short **welcome dialog** opens at the very first start: language, then - only if you want - the network (Art-Net, remote access with your own password, OSC). It cannot be closed, you click through it (or press *Skip* on the first page). Nothing is switched on without your say-so; if you switch on something that uses the network, Windows may ask once whether OpenCue may use it. After an update **Help → What's new** lists the changes (it opens once by itself).

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

The toolbar shows the current **layout** and **stage**, the **showfile name** (click it to open the file manager), a pulsing **Blackout** button (bulb), the **timecode**, a DMX indicator, the number of connected **remote devices**, and the **Settings** button. When you move the mouse over an entry it lights up and a **tooltip** tells you what it is. What appears in the bar is up to you under *Settings → Toolbar & internet* (each entry on its own; only for this device; the gear is always visible).

**Operator mode in plain words** (*View → Operator mode ...*): you hand the console to someone who should only **operate** - push faders, press buttons, start cues - but not change anything. In operator mode menus, settings and rebuilding are locked, and **voice control is off** (the microphone stays closed). You only get out with the **password** (padlock at the bottom right or `Ctrl+L`). It needs the password from *Settings → Security*. **Lock screen** is something else (*Controls → Lock screen*, `Ctrl+L`): it darkens everything until the password is entered - nothing can be operated at all.

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
| **Timecode**, **Timeline editor**, **Video/Audio Player**, **Livestream / Camera** | Time and media (guide *Timeline editor and LTC*) |
| **Audio** | Live music analysis (spectrum, beat, tempo): lights and cues can react to music |
| **Simple control** | A simple control surface to hand over: pick lights by tile, **joystick**, brightness, colour field, zoom, gobos - see *Remote → Operator mode* |
| **Button**, **Fader**, **Toggle** | Own buttons, faders and on/off switches that run commands (or write them into the command line) |

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

For moving heads, **Position** has three views: **Coarse** (faders for pan and tilt), **Fine** (one swipe strip per axis: swipe up or down, the marks follow your finger - one step of the fine channel per 4 pixels) and **Joystick**. The joystick is a round knob with two axes, **relative**: the further you push it, the faster the fixture moves; the inner circle is very precise, the outside fast. When you let go the knob snaps back to the centre and the fixture stays where it is. It changes the coarse and the fine value, and several selected fixtures move by the same amount (their offsets stay). Mouse and touch both work.

### Step 3 – Store a cue

Click **Save Cue** in the Cue List panel. A dialog asks for the **position** (at the end, after a cue, or free), the **cue number** and an optional **name**. Click **Store**. Or type:

```
Store Cue 3 "Warm look"
```

If the number already exists you choose **Merge** (only the changed channels go in) or **Overwrite**.

### Step 4 – Play it

Press **Go** in the Cue List or Executor panel – or type `Go`. The look fades in over the cue's fade time. `Go Cue 3` jumps directly to a cue; **Back** goes one cue back; **Pause** and **Stop** control a running fade.

Use the **Executor fader** to mix between your manual values (0 %) and the cue (100 %). For a big show add **several Executor panels**, each bound to its own cue list (panel settings → list): every one has its own fader and Go / Pause / Back / Stop - together with the grand master (*Master*) they work as submasters.

### Step 5 – Save

Press `Ctrl+S`. This saves the **showfile** and your **layout**. Without saving, changes live only in memory; OpenCue asks before it closes.

---

## 6. Connecting real lights

1. Open **Settings → DMX output**.
2. For **Art-Net**: it is **off** on the first start (it sends into the network) - switch it on. **Find devices automatically** is on by default: OpenCue looks for Art-Net devices in the network (every few seconds) and sends to each of them directly, so a node you plug in simply works. **Scan network** lists what it found (name, address, universes); **Use** makes one device a fixed target. Switch the automatic mode off to type a fixed **Target IP** yourself (for example the Art-Net broadcast address) and, if needed, the **Bind IP** (which network card to use).
3. For **sACN (E1.31)**: switch it on. It is also off by default so that Windows does not show a firewall question on first start.
4. For **USB DMX** (Enttec DMX USB Pro or compatible): switch it on. The **COM port** stays on **Automatic (recommended)**: OpenCue recognises the adapter itself when you plug it in, connects, and connects again after you unplug and re-plug it (even on another USB port). Choose the **universe**; pick a COM port by hand only if you have several adapters.
5. If an interface does not start, use **Re-initialize DMX Interfaces** – no restart needed.

Then **patch** your fixtures (guide *Fixtures and Patching*): the universe and start channel must match the address set on each device.

The **DMX Monitor** panel shows exactly what is being sent. The **Blackout** button sets all brightness to 0 instantly; clicking it again brings the look back.

---

## 7. Making the interface yours

- **Edit mode** (**Edit → Edit Panels**, `Ctrl+E`): move and resize panels (very small is possible, the content then scrolls), change their properties and colours, copy and paste them. **Right-click on the empty workspace** adds a panel, button, toggle or fader at the click position. The tick **Edit → Guides** switches the alignment guides on or off while moving (hold `Alt`: off briefly).
- **Layouts** are files. Build several (for example a small one for programming and a big one for playback) and switch with `Ctrl+1` … `Ctrl+9` or **View → Layouts**. Save with `Ctrl+S` or in the file manager.
- **Themes** (colour profiles): *Settings → Appearance* – dark, light, or your own.
- **GUI scale** (`Ctrl +` / `Ctrl -`): makes everything larger for touch screens; it is stored per device.
- **Language:** *Language* menu (English, Deutsch, Français, Nederlands, Italiano, Español) or `Ctrl+Shift+L`. The guides are available in all six languages.

### Settings at a glance

The gear (**Settings**) opens a dialog with categories on the left, grouped by task. Important categories begin with a **big on/off switch**: when it is off, everything below is dimmed and locked. Nothing applies before you click **Save** (the dialog stays open); **Close** asks when there are unsaved changes. The field **Search settings ...** also finds settings in categories you have never opened and lists the hits across **all categories** (*setting - category / section*); a click jumps to the row. The small **(i)** behind a setting shows its explanation; the **(i) button next to the search field** shows or hides all explanations (remembered per device).

**Back up settings:** At the bottom of *General*, **Export settings** saves all settings as a file (`opencue-settings.json`), **Import settings ...** reads one back. Imported values show up as **changes** (marked and counted) - only **Save** applies them, **Close** discards them. Not included are passwords and access keys, device- or computer-specific values (scale, data folder, microphones, MIDI devices) and the keyboard and MIDI mappings - those have their own export.

| Group | Category | What for |
|---|---|---|
| Program | **General** | The basics: language, GUI scale, switching layouts by swiping, start with Windows, updates, show backups, data folder, back up settings |
| Program | **Appearance** | Colours, themes, defaults for new panels |
| Output | **DMX output** | Art-Net, sACN, USB DMX - each with its own switch, **everything is off on the first start** |
| Network | **Remote access** | Tablet / phone as a remote control: master switch, HTTP / HTTPS, password, addresses and QR codes, network name `opencue.local` |
| Network | **REST API** | Other programs control OpenCue: switch, *Reachable from* (this computer only / the network), tokens |
| Controls | **Keyboard** | Look at the keyboard shortcuts, **custom key mapping** (guide *Keyboard shortcuts*) |
| Controls | **MIDI** | Use MIDI, choose devices, output, timecode / tempo from MIDI, **MIDI mapping** (guide *MIDI*) |
| Speech & audio | **Wake word** | Voice control with its own microphone: wake word + English command, e.g. "OpenCue, blackout on" (guide *Voice commands*); on/off with the microphone symbol at the top right |
| Speech & audio | **Dictation** | Microphone and speech model for dictating in the AI chat |
| Assistant | **AI assistant** | Master switch, connection to Ollama, behaviour, permissions |
| Advanced | **More options** | **Quick switches** (voice control, MIDI, blackout, undo including Go – they act immediately, even when their button is hidden in the toolbar), **Keep the screen awake** (computer and tablets; on the iPad only on a secure page, https), what appears at the top right of the bar (each entry on its own, per device) and the **internet connection** (button *Test connection*) |
| Advanced | **Defaults** | Defaults for new cues, base state after *Clear Clear*, start values and **Deleting**: a confirmation before deleting per category (cues, fixtures, library, files, other) – on by default |
| Advanced | **Inputs & outputs** | Display only: every connection, what it is for and **how far it reaches** (*this PC only*, *local network*, *Internet*), with a link to the matching setting |

**Nothing leaves the computer on the first start:** remote access, Art-Net, sACN and the REST API towards the outside are off. Only the update check is on (it can be switched off); it needs the internet. If the internet works in the browser but not in OpenCue (firewall, antivirus, company network), *General -> Internet connection -> Test connection* shows **what** is in the way.

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
| Own 3D models (STL or OBJ) on the stage | 3D Simulation → **Build** → **3D model …** (import or pick from the library; the file unit mm/cm/m/inch sets the original size). **Import several files at once** (select them in the file dialog or drag them from Explorer onto the stage in *Build* mode): they are placed next to each other around the middle of the view and selected together. Managed in the file manager under **3D models** |
| Use a panel briefly without putting it in the layout | **View → Open Panel as Window**; command line with keypad and keys: **Ctrl+F** (command console) |
| Cues that start at a time | **Timecode** panel and cue trigger *Timecode* |
| Lights and cues that react to music | **Audio** panel, effects with the tag *Audio*, cue trigger *Audio* (guide *Audio*) |
| Cues that wait for a key, pad or fader of a MIDI device | cue trigger *MIDI* (guide *MIDI*, section 5c) |
| Control OpenCue from other programs | **REST API** (Settings → API; guide *REST API*) |
| Files: shows, layouts, stages, 3D models, effects | **Library → Shows… / Layouts… / 3D stages… / Effects…** (the file manager, with import and export as ZIP; a show's export package can also include the 3D models of its stage) |

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
| `config` | Settings (`app_config.json`, incl. the chosen audio source) and the API tokens (`api_tokens.json`, only hashes) |

To back up, copy the folder – or use the file manager's **export** (a show as a ZIP including the fixtures and effects it needs), which also lets you move a show to another computer.

Uninstalling OpenCue asks whether to delete this data too; the default is **No**.
