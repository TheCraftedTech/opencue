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
3. Search, sort (name, newest, best rated), filter by **manufacturer files** / rating. Each card shows whether the file was uploaded **by the manufacturer** or **by a user**, how many modes it has (with channel counts) and how large it is.
4. Click **Details** to **look at a fixture before installing it**: the file is only loaded temporarily (not installed) and opens in the same detail view as installed types – with all channels, wheels and the 3D model. **Install** and **Back to search** are at the top. Or click **Install** right away.
5. The card then shows *Installed*. If a newer revision appears later, an **Update** button is offered.

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

### Many fixtures at once: a list from CSV or Excel

The *Add fixtures* dialog has **Advanced import ...** at the bottom (also in the menu **Library → Import fixture list**). With it you create a whole rig from a table:

1. **Choose file ...** - a `.csv` or Excel file (`.xlsx`). The **first row** holds the column titles. Only the **type** is needed; *name*, *mode*, *universe*, *address*, *number* (FID) and *count* are optional. **Download the current patch as CSV** gives you a template.
2. OpenCue **guesses the columns** (titles like *Name*, *Type*, *Device*, *Universe*, *Address*, *Count* ...); you can change every assignment. An address may also be `2.045` or `2/45` (universe 2, address 45). If the address is missing it continues behind the previous device of the same universe.
3. The **preview** shows every row - red with the reason when something is wrong (type unknown or ambiguous, mode unknown, does not fit the universe, number already used). **Type when the cell is empty** and **Universe when missing** fill gaps.
4. **Import** creates the fixtures. With problems, tick **Skip rows with problems** first. Nothing is created before that.

### The fixture list and the Fixtures tab

Two places show your fixtures:

- The **Fixture List** panel is the patch table: one row per fixture with FID, name, type, universe, address and channel count, plus the **Add Fixtures** button.
- The **Fixtures** tab of the **Fixture Control** panel shows the same fixtures as a grid of tiles (like on a lighting console) for quick selecting.

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

Select fixtures, then use the **Fixture Control** panel (often called “Programmer” on consoles). A panel can show everything (a sidebar with all categories) or one category only (*Panel Properties → View*).

| Category | Controls |
|---|---|
| **Fixtures** | The tile grid for selecting; switch **List / Layout** (see below) |
| **Dimmer** | Fader and quick buttons |
| **Position** | Switch **Coarse / Fine**. *Coarse*: pan/tilt faders, **Center / Home / Flip**, number fields in degrees. *Fine*: the fine channels (16-bit) as number fields; swipe a number field up or down to change it finely. Fixtures without fine channels act as 8-bit. |
| **Color** | **Fader** (HSV, CMY or RGB) or **Color Picker** (colour wheel) |
| **Beam** | Sub-pages **Shutter / Strobe** (open, closed, slow, fast, strobe, pulse …), **Gobo** (with picture thumbnails of the wheel), **Prism** |
| **Focus** | Focus and zoom |
| **DMX Direct** | Every channel of the mode as its own fader (by channel number, 0–255) |

Every channel the GDTF file describes gets a control, so you can reach even unusual functions (frost, iris, colour wheels, speeds).

**Aim at a point (3D):** if the fixtures are placed in the **3D Simulation**, the position pane offers *Set point in 3D simulation*: tap a target in the 3D view and the selected moving heads aim at it. In the focus pane, *Auto focus (3D)* and *Auto zoom (3D)…* set focus and zoom from the distance to that point.

### What the colour of the controls tells you

The controls always show what is currently being output (the same values as the DMX monitor) – also while a cue or effect runs. A thin coloured line next to a fixture or a category tab shows what **changed compared with the active cue** – operated by hand or by a *Clear* that made everything dark. *Store Cue* always stores the change compared with the cue that would play before it (also when inserting with `2.5`). After storing, the new cue is the active one and the lines disappear. With several cue lists the active cue of the most recently used list counts.

---

### Fixtures: list or layout

At the top of the **Fixtures** tab you switch between two views (like *Colour* between Fader / Picker / Wheel):

- **List:** the tiles ordered by groups and numbers.
- **Layout:** every fixture is a **square tile** on a grid. Arrange the fixtures the way they hang on stage and hit them faster. The tiles show the same as in the list (number, brightness, colour and beam preview).

In the layout:

- **Select** like in the list: click or a **swipe** (lasso) across the empty area.
- **Unlimited area:** it goes on in **every direction** (also left and up; positions may be negative). Move the view with the mouse wheel / scroll bars / swiping, **drag with the middle button**, or move to the edge while dragging a tile. **Ctrl + mouse wheel** zooms.
- **Show all:** the button at the top right zooms and centres so that **all fixtures** are in the middle.
- **Views (areas):** *Save view…* (right-click) stores the current centre and zoom under a name, for example "Stage left". A button appears at the top; a click jumps there, right-click on the button: overwrite, rename, delete. With many fixtures you do not have to keep everything in view at once.
- **Right-click** (touch: long press) on the free area or on a tile opens the menu: *Build mode*, *Show all*, *Save view…*, *Grid* (whole, half or quarter tile), *Tiles may overlap*, *Reset zoom*, *Rearrange all fixtures…*.
- **Build mode:** dragging moves a tile; with several selected they move together. Tiles snap to the grid; without *Overlap* they never cover each other, with *Overlap* you can put them into each other (the last moved lies on top) and stagger them closely with the fine grid (1/4). The empty area still selects by swipe. **Done** or **Esc** ends build mode.
- **Stored in the show:** the positions, the grid resolution, *Overlap* and the saved views. **On your device** (not in the show): the zoom, the last shown centre and the last used sub-view.

**Remembered views:** wherever a panel switches between views, your device remembers the last one and restores it next time: in Fixture Control (List / Layout, Fader / Picker / Wheel, Strobe / Gobo / Prism, Coarse / Fine), in *Variables and Effects* (variables or effects, type filter, sorting), in the *Effect Studio* (preview on / off), in the *3D Simulation* (View / Build / Fixtures) and in the effect picker (category and tags such as *Basic*).

## 6. Variables and effects (presets)

The panel **Variables / Effects** holds reusable values: a colour “Warm White”, a position “Front”, a beam “Wide”. A variable is a **live reference**: apply it to fixtures and they follow it; change the variable later and all fixtures using it change with it – including cues that use it. Effects are small programs that change values over time; see the guide *Effect Studio*.

---

## 7. Fixtures and the show file

- A showfile stores the fixtures **with** their type, mode, address and group, plus the cues, effects, variables and presets.
- The GDTF files are **not** inside the show – but when you **export a show** (file manager → export), the GDTF files and effect scripts the show uses are packed into the ZIP, so you can open the show on another computer without installing anything. On import, a local file of the same name is never replaced.
- **Print / PDF** (File menu): documentation of the show for technicians - **patch list**, **DMX channel map** (which fixture occupies which channels of each universe, overlaps in red), **groups**, **plan (top view)** of the fixtures (from the 3D stage, otherwise from the layout view) and **cue lists**. The dialog shows a **preview** of the PDF next to the choices (it follows every change of the choices and the paper size; on small screens the preview is left out). Long names are **wrapped** in the tables and in the plan (an unbroken very long name is split). In the plan every fixture carries its number, and a list under the plan tells which number is which fixture; names of stage objects stand inside their shape. *Save as PDF* downloads the file, *Open to print* shows it in the PDF viewer (print there with Ctrl+P).
- **Show file `.ocshow`:** *File → Export show* writes an `.ocshow` file (a ZIP with the show and its files). A **double-click** opens it in OpenCue (the installer sets this up; for the unpacked version use *Settings → General → Open .ocshow files with OpenCue*). If OpenCue is already running it takes the file over and asks first about unsaved changes. **File → Open Recent** lists the latest shows.
- **3D stage as JSON:** in the 3D panel (*Build* or *Fixtures* mode) switch the side bar from **Tools** to **JSON** (toggle below the Save button; it stays at the top of the side bar when you scroll). The tools (add bodies, list, properties) are replaced by the text of the stage (room, objects, fixture positions; metres, degrees, Z up; fixtures by their number); stage name, undo and **Save** stay the same, **Tools** brings the normal view back. **The width of the side bar can be changed:** drag its left edge (double-click = standard width); the width is remembered as a share of the panel (at most three quarters), so it stays proportional in full screen. Changes are checked and **applied live** (a syntax error names the line and changes nothing); what you move in the 3D view shows up in the text. *Save* saves the stage, *Close JSON* brings the side bar back. The same text is available as a dialog under *Library → Edit 3D stage as JSON* (with *Check* and *Apply*).
- **MVR import (stage and fixtures):** *Library → Import MVR scene…* reads an **.mvr** file from a stage or lighting design program (Vectorworks, Capture, Depence …). Choose the file (or drop it on the dialog): OpenCue shows what is inside - stage parts, fixtures and their types - and you decide: **3D stage** *replace* (the default; a stage file you saved earlier stays untouched on disk), *add* or *leave alone*, and whether to **patch the fixtures**. The fixtures get type, mode, DMX address and number from the file and are placed in the 3D stage with their position and rotation (a number that is already used, or a missing address, is replaced by a free one - the notes tell you). The GDTF files go into the fixture library (nothing is overwritten). The stage parts (floor, truss, set pieces, screens …) become **3D models** (binary STL, listed under *Library → 3D models…*) and stage objects that you can move, rotate and resize like any other; a part that occurs many times (a symbol in the file) shares one model. A scene with more than 200 parts is combined per layer so that it fits on a stage. The new stage is not saved until you save the show. The colours of the materials are kept (per surface) and mirrored parts stay mirrored. A progress bar shows the import - big LED fixture files take a few seconds each, once per type, and are remembered afterwards. The dialog also opens from the small *Import MVR scene…* button in the 3D panel (*Build* and *Fixtures* mode). Not imported: focus points and image textures.
- If a show uses a fixture type whose file is missing, OpenCue uses a built-in substitute so the show still works; the tab *In this show* shows this as *Built-in substitute* or *File missing*.

---

## 8. Quick tips

- **Start with a generic:** add a few *Generic Dimmer* fixtures to learn the programmer, cues and the command line before you look for real GDTF files.
- **Match addresses:** the start channel in OpenCue must equal the address on the device. Moving heads usually need a channel block (for example 16 channels), so the next fixture starts 16 channels later – OpenCue calculates that for you when you add a quantity.
- **Several modes:** many devices offer several modes (for example 8-bit and 16-bit). Pick the mode the device is actually set to.
- **Missing a device?** Search GDTF Share by manufacturer; if the model is not there, start from the closest one or use *Generic* and set up your own cues.
