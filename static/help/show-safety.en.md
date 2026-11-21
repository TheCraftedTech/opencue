# Backups, Locks and Quitting Safely

You programmed the show before the event and now you **deliberately do not save** while it runs – nothing should be overwritten by accident. OpenCue protects you in four ways: **backups in the background**, **restoring** after a crash, a **lock** for finished shows, and a **careful quit dialog**. This guide explains all four, and how to report a problem.

---

## 1. Backups in the background

OpenCue regularly writes the **current state of your show** – including changes you have *not* saved – into a hidden folder. You never see it until you need it. A backup **never replaces your show file**.

- **When:** every **15 minutes** by default, but **only if** the show has unsaved changes and something changed since the last backup. Nothing changed = nothing written.
- **Also:** when you quit without saving, when saving failed (for example because the show is locked), and right before you open or start another show that still has unsaved changes.
- **How many:** the newest **10** per show are kept, at most 100 in total; older ones are deleted automatically.
- **Where:** the folder `backups` inside the data folder (`%LOCALAPPDATA%\OpenCue\backups`). A backup is an ordinary show file.

### Settings

**Settings → General → Show backups**:

| Setting | Meaning |
|---|---|
| **Back up the show in the background** | Switch the whole function on or off (default: on). |
| **Every (minutes)** | The interval, 1 to 240 (default 15). |
| **Keep per show** | How many backups of one show are kept, 1 to 50 (default 10). |
| **Restore backup...** / **Open folder** | Opens the restore dialog (section 2) or the folder in Explorer. |

The settings apply to the whole program and can be changed from any device, also from a remote device.

---

## 2. Restoring a backup

**File → Restore backup...** (or the button in the settings) lists all backups, newest first: show name, time, reason (automatic, on quit, manual, before a restore, saving failed) and size.

- **Restore** loads the backup as an **unsaved show**. The show file on disk stays exactly as it is, even if it is locked. Then **Save** (or **Save Showfile As...**) when you are happy.
- The state you had before is backed up first – a restore cannot lose anything either.
- **Back up now** makes a backup immediately; **Delete** removes one. Everything here also works from a remote device (*Open folder* shows the OpenCue Explorer there).
- Shows, layouts, stages and settings are written **safely**: first into a neighbouring file, then swapped in - a crash or power loss in the middle of saving cannot destroy the existing file.

### After a crash

If OpenCue was not closed properly (crash, power loss, task killed), it **offers the last backup of that session** at the next start: *"OpenCue was not closed properly … Restore it?"* – **Restore**, **Show all backups** or **Not now** (the backups stay available under *File → Restore backup...*).

---

## 3. Locking a show

A finished show can be **locked** so nobody changes it by accident. In the **file manager** (*File → File manager...*, kind *Shows*) click the **lock symbol** in the row of the show; click it again to unlock.

A locked show:

- is marked **Locked** in the list and shows a small **lock** next to the show name in the top bar while it is loaded,
- **cannot be saved over, renamed or deleted** – saving shows *"Not saved: … is locked"*,
- can still be **loaded**, **duplicated** (the copy is not locked) and saved under **another name** with *Save Showfile As...*.

The lock is a protection against slips, not against copying: the file itself can still be changed with any other program.

---

## 4. Quitting safely

**File → Exit** (or the close button) asks: **Save and quit**, **Quit without saving** or **Cancel**.

If the show **cannot be saved** but has changes – it is locked, the file is write-protected, the folder is not writable or the last save failed – the dialog changes:

- An **orange box** at the top says *"This show cannot be saved"* and names the reasons. It also tells you whether a backup copy of your changes is kept.
- **Save as a copy and quit...** replaces *Save and quit*: you choose a new name, the show is saved there, then OpenCue quits.
- **Quit without saving** needs **two clicks**: the first turns the button red (*"Click again: quit and lose the changes"*), only the second quits.

Even then a backup of your changes is written when quitting (if backups are on), so *File → Restore backup...* can still bring them back.

---

## 5. Reporting a problem

- **Help → Open log folder** opens the folder with `opencue.log`.
- **Help → Report a problem...** copies the **diagnostics** (version, system, the last log lines – without access tokens or passwords) to the clipboard and opens the project's report page in your browser. Describe what you did, paste the diagnostics.
- Errors in the user interface are written to the log as **OC-3601**; a backup that could not be written as **OC-3701** (see the guide *Error codes*).
