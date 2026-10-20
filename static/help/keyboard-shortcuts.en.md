# Keyboard Shortcuts and Gestures

All keyboard shortcuts and touch gestures of OpenCue in one place. Inside the program the same list is available under **Help → Keyboard Shortcuts**.

On a Mac keyboard (or in a browser on one) `Cmd` works like `Ctrl`.

---

## 1. Overview

Most shortcuts are **global**: they work wherever the focus is, with one rule – **while you type in a text field, only three shortcuts stay active**: `Ctrl+S`, `Ctrl+Shift+S` and `F11`. Everything else (`Ctrl+N`, `Ctrl+O`, `Ctrl+Q`, `Ctrl+E`, arrow keys, `Ctrl+1–9`, scale, clipboard and undo shortcuts) stays quiet so that typing is never disturbed.

---

## 2. Showfile

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New showfile (asks first if there are unsaved changes) |
| `Ctrl+O` | Open a showfile (opens the file manager on *Shows*) |
| `Ctrl+S` | Save the showfile **and** the layout of this console (a show without a name opens *Save As*) |
| `Ctrl+Shift+S` | Save the showfile under a new name |
| `Ctrl+Q` | Quit OpenCue (asks to save first) |

`Ctrl+S` also works while you type in a name field, for example in the *Save As* dialog.

---

## 3. View and interface

| Shortcut | Action |
|---|---|
| `F11` | Fullscreen (console window, or the browser of this device) |
| `Ctrl +` / `Ctrl =` | Enlarge the interface (GUI scale, steps of 5 %) |
| `Ctrl -` | Shrink the interface |
| `Ctrl+0` | Reset the scale to 100 % |
| `Ctrl+Shift+L` | Switch language (English ⇄ German) |
| `Esc` | Close the topmost dialog or menu |

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

Undo and redo for panels only work **in edit mode**; outside it the shortcuts do nothing.

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
| `Esc` | Close the suggestion list |

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

## 11. Cheat sheet

```
Ctrl+N  New show           Ctrl+O  Open show          Ctrl+S  Save          Ctrl+Shift+S  Save as
Ctrl+E  Edit panels        Ctrl+Z / Ctrl+Y  Undo / Redo (edit mode)
Ctrl+C / X / V  Copy / cut / paste panels (edit mode)
Ctrl+1…9  Load layout      ← / →  Previous / next layout
Ctrl +  Ctrl -  Ctrl+0     GUI scale larger / smaller / 100 %
Ctrl+Shift+L  Language     F11  Fullscreen      Ctrl+Q  Quit      Esc  Close dialog
```
