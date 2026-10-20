# Fixtures and Patching

A **fixture** is a light you control: a dimmer, an LED par, a moving head. To control it, OpenCue needs to know **what kind of device it is** (its channels) and **where it listens** (its DMX address). Telling OpenCue both is called **patching**. This guide walks you through the fixture library, patching, groups and the programmer.

---

## 1. The idea in one minute

- A **fixture type** describes a device model: how many DMX channels it uses in which mode and what each channel does (dimmer, pan, tilt, colour, gobo …). OpenCue uses the standard format **GDTF** for this – a small file per device that the manufacturer publishes.
- A **fixture** in your show is one real device of such a type, with a **number** (FID), a **name**, a **universe** and a **start channel** (the DMX address you set on the device).
- The show stores the fixtures (type, mode, address, name, group). The GDTF files themselves live in the **fixture library** on your computer.
- Three **built-in** fixture types are always available, even without any GDTF file: **Generic Dimmer** (1 channel), **Generic RGBW LED Par** (4 channels) and **Generic Moving Head Spot 16ch** (16 channels, with fine pan/tilt). Perfect to try things out.

---

## 2. Getting fixture types: the fixture library

Open **Library → Fixture Library…**. The large dialog has these tabs:

| Tab | What it shows |
|---|---|
| **Installed** | Every GDTF file on this computer as a card: preview picture, name, manufacturer, type, modes, channel count, revision and *In use (N)* when the show uses it. |
| **In this show** | The types the loaded show uses, with count (“4× in the show”) and revision. If a type's file is not in the library, the tab shows *Built-in substitute* or *File missing*. View only. |
| **Online (GDTF Share)** | Search the official GDTF database (see below). |

On the *Installed* tab you can **search** by name or manufacturer and filter by **type** (Moving head, LED bar, PAR / wash, Dimmer, Strobe / blinder, Effect / fog, Other – derived from the real channels) and by **manufacturer**. Each tab keeps its own filters.

### Import a GDTF file you already have

Click **Import GDTF file…** or simply **drop the file** into the dialog. The file must be a valid GDTF file (at most 30 MB). Files are copied into the `fixtures` folder inside OpenCue's data folder (Settings → Storage shows where that is).

### Download from GDTF Share

GDTF Share (gdtf-share.com) is the official, free collection of GDTF files from manufacturers and users.

1. Open the tab **Online (GDTF Share)**.
2. **Sign in** with your GDTF Share account. A free account is required to download; there is a *Create a free account* link in the dialog. Your password is kept in memory for this session only – unless you tick *Stay signed in*, which stores it **encrypted on this computer**.
3. Search, sort (name, newest, best rated), filter by verified / rating, and click **Install**.
4. The card then shows *Installed*. If a newer revision appears later, an **Update** button is offered.

This is the only place where OpenCue uses the internet for fixtures; everything else works offline. OpenCue does not ship GDTF files from GDTF Share, because their terms do not allow redistribution – you download them yourself.

### Details of a fixture

Click a card to open its **details**:

- **Overview** – master data, optics per beam (beam type, lamp, power, luminous flux, colour temperature, beam and field angle), connectors, emitters.
- **3D preview** – the fixture as a 3D model. Drag to rotate, wheel or two fingers to zoom, right-drag to move, double-click to reset. Buttons *Angled / Front / Side / Top*, switches for the *light beam* and a *grid*, and **Pan / Tilt sliders** to move a moving head. Without a 3D file in the GDTF, OpenCue draws the basic shapes (cylinder, yoke, head …) with the given dimensions.
- **DMX channels** – the mode selector and a table of all channels with functions and value ranges.
- **Gobos & colors** – every wheel with its slots: gobo patterns as pictures, colour slots as swatches.

### Removing and updating

- **Uninstall** (asks a second time) removes a type from the library – but it is **refused while the show still uses it**.
- **Update** installs a newer revision. If the show uses the old one, the old revision stays installed.

---

## 3. Adding fixtures to the show (patching)

Fixtures are created in the **Fixture List** panel.

1. In the **Fixture List** panel click **Add Fixtures**.
2. **Fixture Type** – pick one with *Select Type…* (manufacturer → device → mode, plus a search) or one of the built-in generics.
3. **Mode** – the DMX mode of the device (it decides the channel count).
4. **Name** (optional) – for example “Head”; empty means the type name. With several fixtures OpenCue numbers the names.
5. **Quantity** – how many identical fixtures to add. They are placed **one after another** on consecutive addresses.
6. **Universe** and **Start Channel** – the address of the first one. This must match the address set on the device (display or DIP switches).
7. Click **Add Fixtures**.

The dialog warns you if the last fixture would end beyond channel **512** of a universe (“end address exceeds 512 … Reduce quantity or start address”). A universe holds 512 channels; use the next universe for more.

Each fixture gets a stable **FID** (fixture number) used by the command line (`Fixture 1 Thru 5`).

### The fixture list and the Fixtures tab

Two places show your fixtures:

- The **Fixture List** panel is the patch table: one row per fixture with FID, name, type, universe, address and channel count, plus the **Add Fixtures** button.
- The **Fixtures** tab of the **Fixture Control** panel shows the same fixtures as a grid of tiles (like dot2) for quick selecting.

| Action | How |
|---|---|
| Select | Click / tap a row or tile |
| Select several | In the tile grid, drag a **lasso** over the tiles (mouse and touch) |
| Edit one fixture | Right-click / long-press → **Edit fixture…** |
| Delete | Select, press `Delete` or use the context menu (asks for confirmation) |

### Edit fixture

One dialog changes everything: **Name**, **Universe**, **Start Channel**, **Group** and a free **Sort index**.

- The sort index decides where the tile appears. Empty means the FID; a number (decimals allowed, for example 2.5) places it accordingly.
- A fixture belongs to at most **one group**.
- With **several fixtures selected** the menu also offers *Move N fixtures to group…*.

Changing the address changes where OpenCue sends the data – so do it when you move a device to another address.

---

## 4. Groups

Groups are purely organisational: sorting and selecting several fixtures with one click or command. They are stored with the show.

- **Create:** in the **Fixtures** tab of the Fixture Control panel, right-click / long-press on the empty area → *Add new group…* and enter a name (names are unique, case-insensitive).
- **Fill:** the *Group* dropdown in *Edit fixture…*, or *Move N fixtures to group…* for a selection.
- **Select:** click the group, or use the command line: `Group Front`, `Group 1 Thru 4`.
- **From a selection:** `Store Group "Front"` stores the current selection as a group (see *Command Reference*).

---

## 5. Controlling fixtures: the Fixture Control panel

Select fixtures, then use the **Fixture Control** panel (called “Programmer” in dot2 terms). A panel can show everything (a sidebar with all categories) or one category only (*Panel Properties → View*).

| Category | Controls |
|---|---|
| **Fixtures** | The tile grid for selecting |
| **Dimmer** | Fader and quick buttons |
| **Position** | Switch **Coarse / Fine**. *Coarse*: pan/tilt faders, **Center / Home / Flip**, number fields in degrees. *Fine*: the fine channels (16-bit) as number fields; swipe a number field up or down to change it finely. Fixtures without fine channels act as 8-bit. |
| **Color** | **Fader** (HSV, CMY or RGB) or **Color Picker** (colour wheel) |
| **Beam** | Sub-pages **Shutter / Strobe** (open, closed, slow, fast, strobe, pulse …), **Gobo** (with picture thumbnails of the wheel), **Prism** |
| **Focus** | Focus and zoom |
| **DMX Direct** | Every channel of the mode as its own fader (by channel number, 0–255) |

Every channel the GDTF file describes gets a control, so you can reach even unusual functions (frost, iris, colour wheels, speeds).

**Aim at a point (3D):** if the fixtures are placed in the **3D Simulation**, the position pane offers *Set point in 3D simulation*: tap a target in the 3D view and the selected moving heads aim at it. In the focus pane, *Auto focus (3D)* and *Auto zoom (3D)…* set focus and zoom from the distance to that point.

### What the colour of the controls tells you

The controls always show what is currently being output (the same values as the DMX monitor) – also while a cue or effect runs. A thin coloured line next to a fixture or a category tab appears **only after you operated that category by hand**: those are your *programmer values* that are not yet stored. They disappear after *Store Cue* or *Clear*.

---

## 6. Variables and effects (presets)

The panel **Variables / Effects** holds reusable values: a colour “Warm White”, a position “Front”, a beam “Wide”. A variable is a **live reference**: apply it to fixtures and they follow it; change the variable later and all fixtures using it change with it – including cues that use it. Effects are small programs that change values over time; see the guide *Effect Studio*.

---

## 7. Fixtures and the show file

- A showfile stores the fixtures **with** their type, mode, address and group, plus the cues, effects, variables and presets.
- The GDTF files are **not** inside the show – but when you **export a show** (file manager → export), the GDTF files and effect scripts the show uses are packed into the ZIP, so you can open the show on another computer without installing anything. On import, a local file of the same name is never replaced.
- If a show uses a fixture type whose file is missing, OpenCue uses a built-in substitute so the show still works; the tab *In this show* shows this as *Built-in substitute* or *File missing*.

---

## 8. Quick tips

- **Start with a generic:** add a few *Generic Dimmer* fixtures to learn the programmer, cues and the command line before you look for real GDTF files.
- **Match addresses:** the start channel in OpenCue must equal the address on the device. Moving heads usually need a channel block (for example 16 channels), so the next fixture starts 16 channels later – OpenCue calculates that for you when you add a quantity.
- **Several modes:** many devices offer several modes (for example 8-bit and 16-bit). Pick the mode the device is actually set to.
- **Missing a device?** Search GDTF Share by manufacturer; if the model is not there, start from the closest one or use *Generic* and set up your own cues.
