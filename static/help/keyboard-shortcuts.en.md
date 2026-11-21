# Keyboard Shortcuts and Gestures

All keyboard shortcuts and touch gestures of OpenCue in one place. Inside the program the same list is available under **Help → Keyboard Shortcuts** and **Controls → Keyboard shortcuts ...** - and there you can also **change** the program's own shortcuts (section 11b).

On a Mac keyboard (or in a browser on one) `Cmd` works like `Ctrl`.

---

## 1. Overview

Most shortcuts are **global**: they work wherever the focus is, with one rule – **while you type in a text field, only a few shortcuts stay active**: `Ctrl+S`, `Ctrl+Shift+S`, `Ctrl+F`, `F1`, `F5`, `Ctrl+F5`, `F11` and `Ctrl+L`. Everything else (`Ctrl+N`, `Ctrl+O`, `Ctrl+Q`, `Ctrl+E`, arrow keys, `Ctrl+1–9`, scale, clipboard and undo shortcuts) stays quiet so that typing is never disturbed.

---

## 2. Showfile

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New showfile (asks first if there are unsaved changes) |
| `Ctrl+O` | Open a showfile (opens the file manager on *Shows*) |
| `Ctrl+M` | File manager (all files: shows, layouts, stages, models, media, effects ...) |
| `Ctrl+L` | **Lock screen** (menu *Controls → Lock screen*; needs *Settings → Security → Use lock mode*; at a remote device: log out; in operator mode: asks for the password to leave it) |
| `Ctrl+S` | Save the showfile **and** the layout of this console (a show without a name opens *Save As*) |
| `Ctrl+Shift+S` | Save the showfile under a new name |
| `Ctrl+Q` | Quit OpenCue (asks to save first) |

`Ctrl+S` also works while you type in a name field, for example in the *Save As* dialog.

---

## 3. View and interface

| Shortcut | Action |
|---|---|
| `?` | **Show / hide this overview of all keyboard shortcuts** (not while you type in a field or while another dialog is open) |
| `F1` | Open the **Guides** (all manuals inside the program, also offline). Inside them `Ctrl+F` searches, `Enter` / `Shift+Enter` jump to the next / previous match, `Esc` clears the search |
| `F5` | **Reload the layout**: the current layout is loaded again like a layout switch and **all panels are rebuilt** (helps if something - for example the 3D simulation - did not appear correctly after the start). With unsaved layout changes nothing is fetched from the file: the panels are only rebuilt and your changes stay. Also in *View → Reload layout* |
| `Ctrl+F5` | **Reload the whole interface** (like reloading a web page; the device gets its layout back afterwards). Also in *View → Reload interface* |
| `F11` | Fullscreen (console window, or the browser of this device) |
| `Ctrl +` / `Ctrl =` | Enlarge the interface (GUI scale, steps of 5 %) |
| `Ctrl -` | Shrink the interface |
| `Ctrl+0` | Reset the scale to 100 % |
| `Ctrl+Shift+L` | Switch language (one after the other: English, German, French, Dutch, Italian, Spanish) |
| `Ctrl+F` | Open / close the **command console**: command line with keypad and command keys in one window – also without these panels in the layout; the cursor is in the input at once |
| `Esc` | Close / cancel the topmost dialog, panel window or menu - one press closes **one** dialog (Settings ask first if there are changes) |

The GUI scale (50–200 %) is stored **per device**: a tablet can be large while the console stays small.

---

## 4. Layouts

| Shortcut | Action |
|---|---|
| `Ctrl+1` … `Ctrl+9` | Load layout 1 to 9 (favourites first, then A–Z) |
| `←` / `→` | Previous / next layout (not in text fields, dialogs, menus or edit mode) |
| Horizontal swipe | Previous / next layout on touch devices (*Settings → General → Switch layouts by swiping*, per device) |

Loading a layout discards unsaved changes of the current one. The order is the same as under **View → Layouts**.

---

## 5. Panel edit mode

Edit mode (**Edit → Edit Panels**) lets you move, resize and configure panels.

| Shortcut | Action |
|---|---|
| `Ctrl+E` | Switch edit mode on / off |
| Click on a panel | Marks it (thin accent frame) |
| `Shift`/`Ctrl` + click | Add a panel to / remove it from the marking |
| Click on empty workspace | Clears the marking |
| `Ctrl+C` / `Ctrl+X` / `Ctrl+V` | Copy / cut / paste the marked panels (the clipboard survives a layout change) |
| `Ctrl+Z` | Undo the last panel change |
| `Ctrl+Y` or `Ctrl+Shift+Z` | Redo |
| Right-click → *Duplicate* | Copies the marked (or clicked) panels with a small offset |

In **edit mode**, `Ctrl+Z` / `Ctrl+Y` apply to the arrangement of the panels. **Outside** it they undo changes to the **content of the show** (see *Undo and redo* below).

Leaving edit mode with unsaved changes asks: **Save**, **Discard changes** (reloads the saved layout) or **Keep editing**.

---

## 6. Fixture list and programmer

| Action | How |
|---|---|
| Select a fixture | Click / tap its tile |
| Select several | **Lasso**: drag a frame over the tiles (mouse and touch); the lasso stays inside its own panel |
| Delete the selected fixtures | `Delete` or `Backspace` (asks for confirmation) |
| Change a Pan/Tilt value finely | **Swipe** up/down on the number field (coarse: 2 px per step, fine: 4 px per fine step); tap it to type |
| Open the context menu | Right-click (mouse) or long-press (touch) on a fixture or on empty space |

---

## 7. Command line

| Key | Effect |
|---|---|
| `Enter` | Execute the command |
| `↑` / `↓` | Older / newer command from the history (down returns to your draft) |
| `Tab` | Take the first suggestion; each further `Tab` moves to the next |
| `Shift+Tab` | Move through the suggestions backwards |
| `Esc` | Close the suggestion list (in the command console: close the console) |

Details about the commands: *Command Reference*.

---

## 8. Effect Studio

| Shortcut | Action |
|---|---|
| `Ctrl+S` | Save the effect (**not** the show) while the cursor is in the script |
| `Tab` | Inserts two spaces |
| `Enter` | New line with the indentation of the previous one (two more spaces after `{`) |

---

## 9. 3D simulation – build mode

These shortcuts only act in the 3D simulation while you are building (modes *Build* / *Fixtures*), not in *View* mode.

| Shortcut | Action |
|---|---|
| `Ctrl+C` / `Ctrl+X` / `Ctrl+V` | Copy / cut / paste objects |
| `Ctrl+D` | Duplicate the selected object (press again to repeat the offset) |
| `Delete` / `Backspace` | Delete the selected object (asks for confirmation); in fixture mode: remove the fixture from the stage |
| `Esc` | Clear the selection |
| `Shift` + click | Add / remove an object to the selection |
| Arrow keys | Move the selection (with `Shift` five times as far); while something is selected the arrows do not switch layouts |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` or `Ctrl+Shift+Z` | Redo |

Fixtures exist only once on a stage, so in fixture mode copy, cut and duplicate are switched off.

While you are aiming (*Set point in 3D simulation* in the fixture control), `Esc` ends aiming.

---

## 10. Touch gestures

| Gesture | Same as |
|---|---|
| Long-press | Right-click (context menu) |
| Long-press on an element with a tooltip | Shows the tooltip |
| Double-tap | Double-click |
| Horizontal swipe (if enabled) | Previous / next layout |
| Swipe on a Pan/Tilt number field | Change the value (coarse / fine) |

Panel handles and toolbar buttons have a touch target of at least 44 × 44 px. The layout swipe is recognised by the direction of the first movement (at most 25° from horizontal, at least 40 % of the width) and never starts on elements with their own drag function (faders, lasso tiles, swipe number fields, input fields, the colour wheel, column and panel handles). Vertical scrolling stays scrolling.

---

## 11. Custom keyboard shortcuts

A key or key combination of your own can trigger a **command-line command** - for example `Ctrl+H` for `Blackout` or the space bar for `Cuelist Main Go`. Open the list with **Controls → Custom keyboard shortcuts ...** or with the button at the bottom of the *Keyboard Shortcuts* dialog.

**One key for the next cue:** under *Quick start* at the top of the dialog click **Next cue (Go)** (or *Previous cue*, *Pause*, *Blackout*): a new row with the command `Go` appears, then click its key field and press the key - for example the space bar or a key of a second keyboard / number pad (choose *Only this keyboard* in the *Set key* dialog). `Go` starts the next cue of the active cue list; `Cuelist Main Go` always that list.

Each row has, from left to right:

| Field | Meaning |
|---|---|
| **On** | Turns the row on or off without deleting it. |
| **Key** | Shows the key or combination. Clicking it or the **keyboard button** next to it opens the **Set key** dialog: you have **10 seconds** to press the key or combination (for example `Ctrl` and `H` together) - everything from the first press until all keys are released is recorded. `Esc` cancels, the button next to the field records again. Below you choose what it applies to: **All keyboards** or **Only this keyboard**. A row only gets its key through this dialog. |
| **Command** | The command as you would type it into the command line. |
| **Run** | On: the command runs at once. Off: it is only **written** into the command line (you confirm it yourself). |
| **In history** | On: the command appears in the command-line history. |
| Trash can | Deletes the row (after a confirmation). |

**New key combination** at the bottom adds as many empty rows as you like (no recording). Changes apply immediately and on every device with a keyboard attached (also an iPad).

**Back up and share:** At the bottom of the dialog **Export ...** saves the mapping as a file (`opencue-keyboard-mapping.json`), **Import ...** reads such a file. The rows are **added**; keys that the program or another row already uses are skipped (the message gives the number).

**Good to know**

- Combinations the program or the browser already uses (`Ctrl+S`, `Ctrl+1...9`, `Left`/`Right`, `F5` ...) are refused while recording; each combination can only be used once.
- While **typing in an input field** only combinations with `Ctrl` apply. With a dialog open, plain keys do nothing, and with the *Custom keyboard shortcuts* dialog open nothing triggers.
- The command runs when the key is **pressed** (not on release). A held key triggers it only **once**.
- A combination may have **several main keys**, e.g. `Ctrl+H+J`: it applies as soon as all are pressed (the order does not matter). If `Ctrl+H` exists as well, that shorter combination waits a moment to see whether `J` is added.
- If a combination is already used by the program or the browser (also as part of a longer one, e.g. `Ctrl+S+J`), OpenCue does not accept it and shows a message at the top of the dialog.
- Keys are stored independently of the keyboard layout (the `Z` key stays the key at that position). The number pad is called `Num1` ... `Num9`.

**Key of a specific keyboard (e.g. macro pad, Windows only)**

In the **Set key** dialog (keyboard button of a row) you press the key on the keyboard you want. At the console on Windows OpenCue detects **which** keyboard it comes from (the name appears below the field), and you choose **All keyboards** or **Only this keyboard**. On a tablet or without Windows the browser records and it always applies to "All keyboards". A key applies either to all keyboards or to specific ones - not both at once. A row set to "only this keyboard" triggers only when the key is pressed on exactly that keyboard - even when OpenCue is not in the foreground. The row shows the keyboard below the key.

- This works **at the console itself** on Windows only, not from a tablet.
- OpenCue **only listens while** there is at least one enabled row for a specific keyboard (or while recording). It only evaluates the keyboards that are in the list; everything else is discarded at once and never stored.
- Windows only reports the key, it does **not block** it: the key still reaches the active program as well (for example as a character in a text field). For a macro pad, choose keys that otherwise do nothing - such as `F13` to `F24` or the number pad.
- Some keyboards report as several devices (for example keys and media keys separately). OpenCue detects that on its own while recording.
- Two different keyboards may assign the same key differently. A duplicate report of the same key press (within 80 ms) triggers only once.

## 11b. Change the program's own shortcuts

The shortcuts the program already has (`Ctrl+S`, `F11`, `Ctrl+E` ...) can be moved to other keys or switched off. Open **Controls → Keyboard shortcuts ...** and click **Edit shortcuts** at the bottom:

1. Every changeable row shows a dashed frame around its key. **Click the key**, press the new combination and **release** it - it is set at once (the key shows *Press keys ...* while you hold it). `Esc` cancels.
2. The **cross** next to a row turns that shortcut **off**, the **arrow** restores its standard key. **Restore all standard keys** resets everything. **Done** leaves the edit mode.
3. Changed keys are shown in the accent colour here, in the menus (for example *File → Save Showfile*) and in the *Custom keyboard shortcuts* dialog, which refuses keys that are taken.

OpenCue refuses a combination that is already used (by another shortcut, by a custom key command, or by the browser / Windows - for example `Ctrl+W`). A program shortcut has **one main key plus Ctrl, Alt or Shift**; a single letter or number is refused because it would block typing - function keys (`F1` ... `F24`) work alone. The change applies to **all devices** of the console.

Not changeable (they depend on the situation): `Esc`, `Ctrl+C / X / V` for panels, `Ctrl+1 ... 9` for layouts, the arrow keys and the 3D editing keys.

---

## Undo and redo (content of the show)

Outside panel edit mode, `Ctrl+Z` and `Ctrl+Y` (or `Ctrl+Shift+Z`) – and *Edit → Undo / Redo* – undo and redo everything that is **saved in the show file**, and the operating before it:

- **cues and cue lists:** store, update, change times / triggers / names (also several at once), copy, delete, create, rename, reorder and delete lists;
- **variables** and their groups, **fixture groups**, the **patch** (add, delete, re-address, rename, arrange fixtures), **effects** (definitions and groups), the **schedule** and **timeline command tracks**;
- the **selection** of fixtures;
- **programmer values** (colour, position, brightness, beam …) – one fader drag or one command such as `At 80` is **one** step; the DMX state of the affected fixtures goes back too;
- **running effects:** applying or deselecting an effect on fixtures;
- the **executor fader** of a cue list (one drag = one step).

A short message names what was undone. Quick changes of the same kind (for example a swipe on a time or a fader drag) count as **one** step; the history keeps the last 100 steps. Starting a new show (*New*, *Open*) clears it.

**Go and Back (switch):** whether **Go / Back / Jump** (and a `Go` typed as a command) are undone too – then `Ctrl+Z` jumps back to the previous cue. Default: **off**, so you never take back a cue by accident during a performance. The switch is an icon (undo arrow with a small play triangle) in the toolbar **and** under *Settings → More options → Quick switches* – there it works even when the icon is hidden in the toolbar.

**Not included:** settings, Go through MIDI / OSC / timecode and changes made through the REST interface. In an open dialog and in text fields the shortcuts do nothing. You can rebind the keys under *Keyboard shortcuts → Edit shortcuts*.

## 12. Cheat sheet

```
Ctrl+N  New show           Ctrl+O  Open show          Ctrl+S  Save          Ctrl+Shift+S  Save as
Ctrl+E  Edit panels        Ctrl+Z / Ctrl+Y  Undo / Redo (panels in edit mode, otherwise show content)
Ctrl+C / X / V  Copy / cut / paste panels (edit mode)
Ctrl+1…9  Load layout      ← / →  Previous / next layout
Ctrl +  Ctrl -  Ctrl+0     GUI scale larger / smaller / 100 %
Ctrl+Shift+L  Language     F11  Fullscreen      Ctrl+Q  Quit      Esc  Close dialog
Ctrl+F  Command console (command line + keypad + keys)
```
