# Own Fixtures (Editor)

The editor creates devices that have no suitable GDTF file – a fog machine, a plain dimmer, an RGB par, a moving head. The result is a **real GDTF file** (format GDTF 1.2, built like the files on GDTF Share). You do **not** need a GDTF Share account for this.

---

## 1. Opening it

**Library → Fixture Library… → "Own fixture…".** The window is as large as the library and has three tabs: **General**, **Modes & channels**, **Picture & 3D**.

- Change an own type later: click **Edit** in the list of installed types (only for types built with the editor, marked "Own · unverified").
- Use an existing type as a starting point (**load from another fixture**): in the editor, on the *General* tab at the top, the choice **"Start from an existing fixture"**, or on the card in the library **More → Edit a copy**. Carried over: master data, modes, channels, function names, ranges and the profile picture. **Not** carried over: wheels (gobos, colour wheels), the geometry and 3D parts; the editor tells you what was left out.

---

## 2. General

| Field | Meaning |
|---|---|
| Manufacturer, Name | Required. The file name becomes `Manufacturer@Name@Eigen.gdtf`. If the type already exists the editor says so. |
| Short name | Optional, 8 characters at most. |
| Category | Moving head, LED bar, par, dimmer, strobe, effect, other – or "Automatic" (detected from the channels). You can filter the library by category. |
| Weight, Description | Optional. |
| Tags | Type and press **Enter**. The library searches them too (e.g. "fog", "outdoor", "12 V"). |
| Template | New types only: fog machine, dimmer, RGB, RGB + dimmer, moving head. |

---

## 3. Modes & channels

A **mode** is one channel layout (many devices have several, e.g. "3 channel" and "8 channel"). **+ Mode (copy)** adds another one as a copy of the selected mode; change its name at the top right.

For each **channel**:

- **Attribute** – what the channel does. The list is sorted into intensity, colour, position, beam, effects (fog, haze, fan) and control. At the very bottom, separate: **Own name …** for anything not in the list (e.g. "Bubbles").
- **Label** – free text, e.g. "Fog output". It shows up in the DMX Direct detail panel.
- **8 / 16 bit** – a 16-bit channel uses two DMX addresses (coarse + fine).
- **Default value** (0–255) – the value the device has when it is not driven.
- **Ranges** – named steps, e.g. from 0 "Off", from 10 "Fog". The first range always starts at 0; every other ends just before the start of the next. For pan, tilt and zoom you also enter the angle range in degrees.

The arrows change the order; the DMX addresses are calculated from it (left of each row).

### CSV import

**Import CSV…** reads a channel list: one line per channel, with a header line. Columns (any order, separated by `;`, `,` or tab): `Attribute`, `Label`, `Bit`, `Default`, `Ranges`. Write ranges as `0 Off; 10 Fog` or `0-9 Off; 10-255 Fog` – if the cell contains the separator, put it in quotes:

```
Attribute;Label;Bit;Default;Ranges
Fog1;Fog output;8;0;"0 Off; 10 Fog"
Control1;Fan;8;0;"0-9 Off; 10-255 On"
```

---

## 4. Picture & 3D

- **Profile picture** – any image; it is written into the file as a PNG (512 pixels at most) and appears in the library.
- **3D model** – optionally a `.glb`, `.3ds`, `.stl` or `.obj` file (25 MB and 250,000 triangles at most; STL and OBJ are converted to GLB) for **fixed** devices; the size in metres sets how large it appears on the 3D stage. Moving heads (pan/tilt) get base, yoke and head as standard parts.

---

## 5. Passing the file on

Every card in the library has **More → Export file (.gdtf)** and **Show in folder** (only on the computer running the program). The file can be copied and added on another computer with **Import GDTF file…** – or opened in any other GDTF software. The editor's description is stored in it as an extra file; other programs ignore it.

---

## 6. Good to know

- Own types are **unverified**: check the channel layout on the real device.
- If you change a type the show uses, the changes apply immediately. If the **channel count of a mode in use** changes (or such a mode is deleted or renamed), the editor shows a **note** – it prevents nothing; check the DMX addresses afterwards.
- **Cancel asks first:** if you changed something, *Cancel*, the × and Escape open the "Unsaved changes" dialog (*Keep editing*, *Discard changes* or *Save*). Without changes the editor closes at once.
- **Deleting asks first:** a mode, channel, range, profile picture or 3D model is only removed after a confirmation.
- Grand master and blackout only act on the **dimmer** (or the colour when there is no dimmer channel) – a fog channel keeps running unaffected.
- You operate fog, haze and the like in the fixture control on the **DMX Direct** tab. Hovering the label, clicking the label or right-clicking a fader shows the channel's function names and ranges.
