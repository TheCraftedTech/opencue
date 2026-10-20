# Command Line – Command Reference

The **command line** controls OpenCue by typing, in the style of professional lighting consoles (dot2 / MA Lighting). It complements mouse and touch operation with short commands that you can type, chain and store inside cues. It is available as the panel **Command Line** (*Edit → Add Panel…*); the panels **Command Numpad** and **Command Buttons** write into the same input line for touch operation.

Every command is executed on the server and the result is reported to **all** connected devices: fixture list, cue list and programmer update everywhere at once, not only where you typed.

> The command words are English – as on dot2 and MA Lighting. Upper and lower case do **not** matter for commands, attributes and names.

---

## 1. The idea in one minute

Every command follows the same pattern: **what** – **which** – **value**.

| Action / object | ID / range | Property / target |
|---|---|---|
| `Fixture` | `1` | – |
| `At` | – | `80` |
| `Store` | `Cue 1.5` | – |
| `Cue` | `1` | `Fade 3` |
| `Cuelist` | `Show` | `Go` |

- The **action or object** always comes first (`Fixture`, `Group`, `At`, `Color`, `Pan`, `Zoom`, `Store`, `Cue`, `Go`, `Cuelist` …).
- The **ID or range** says what is affected: a fixture number (FID), a name, a cue number, a cue list name, or a range (`1 Thru 10`).
- The **property or target** is the actual value: percent, degrees, time, name, colour.
- Commands **build on each other**, as on a real console: first you select (`Fixture 1 Thru 4`), then a value command (`At 80`) acts on exactly that selection. The selection is **shared by all devices**: a click in the fixture list on one screen and a `Fixture` command on another work on the same selection.
- Text with spaces (a cue name, a list name) goes in double quotes: `Label Cue 1 "Intro scene"`. A word in quotes is always a **name**, never a command word, so a group called "Color" can be addressed too.
- Input is validated: invalid numbers (`Zoom abc`), unknown attributes or names and missing values give an error message **without changing anything**.

```
Fixture 1 Thru 4 At 80
Fixture 1 Thru 4 Color Red
Store Cue 1 "Opening"
Go
```

---

## 2. Selecting fixtures and groups

| Command | Effect |
|---|---|
| `Fixture 1` | Selects fixture FID 1 (replaces the current selection). |
| `Fixture 1 Thru 10` | Selects FID 1 to 10. |
| `Fixture 1 + 3` | Selects FID 1 **and** 3 (combine as often as you like with `+`). |
| `Fixture 1 Thru 5 + 10` | Selects FID 1–5 and also 10. |
| `Fixture "Head 2"` | Selects the fixture(s) with this **name** (also combinable with `+`). |
| `Group 1` | Selects the 1st group in the group list. |
| `Group 1 Thru 4` | Selects the fixtures of groups 1 to 4. |
| `Group Front` | Selects the group with this **name** (`Group "Front Truss"` when it contains spaces). |

`Group N` means the **N-th group created**. The name is simpler and more robust: `Group Front` works regardless of the order.

A single word may be written without quotes if it does not equal a command word and the name really exists. Otherwise put names with spaces, commas, semicolons or `+`, and names that look like a command or a number, in `"…"`.

### Creating, renaming, deleting groups

The **current selection** can be stored as a group:

| Command | Effect |
|---|---|
| `Store Group "Front"` | Creates the group from the current selection. |
| `Store Group "Front" Merge` | If it exists: the selection is **added**. |
| `Store Group "Front" Overwrite` | If it exists: the members are **replaced**. |
| `Label Group Front "Stage front"` | Renames (`Set Group 2 Name "Stage front"` works too, also by number). |
| `Delete Group Front` | Deletes the group (`Delete Group 2` by number) – the fixtures stay. |

Without a selection `Store Group` reports an error. An existing name (case-insensitive) is never overwritten silently. A fixture belongs to at most one group.

---

## 3. Setting values: At / Full

Acts on the **currently selected** fixtures (dimmer channel).

| Command | Effect |
|---|---|
| `At 80` | Dimmer to 80 % (`At 80%` works too). |
| `At Full` | Dimmer to 100 %. |
| `At At` | Same as `At Full` (the dot2 short form – “At” twice). |
| `Full` | Short form without leading “At” – also 100 %. |
| `At 0` | Dimmer to 0 % (off). |
| `At +10` / `At -10` | Raises / lowers the current dimmer value by 10 percentage points. |

Values are limited to 0–100 %. `At +` / `At -` refers to the value last set in the programmer for each fixture (or to the DMX value currently being output if nothing was programmed yet).

Affected fixtures get a red status marker in the fixture list – they are now “in the programmer” and can be stored with `Store Cue`.

### Master (overall brightness)

`Master` (short `GrandMaster`) scales the output of **all** dimmer channels in percent. The default is 100 %. The value stays until you change it and is saved with the showfile.

| Command | Effect |
|---|---|
| `Master 80` / `Master At 80` | Overall brightness 80 % (the word `At` is optional). |
| `Master Full` | 100 %. |
| `Master -10` / `Master +10` | Lower / raise by 10 percentage points. |

The master only scales dimmer channels; colours and pan/tilt stay unchanged. (The **fader of a cue list** is something different – see chapter 10.)

### Blackout

`Blackout` turns the **brightness of all fixtures to 0** and restores it at the next `Blackout`. It is a toggle, independent of the master.

| Command | Effect |
|---|---|
| `Blackout` | Toggle. |
| `Blackout On` / `Blackout Off` | Switch on / off (`1`/`0`, `True`/`False` also work). |

**Blackout has priority over everything** – faders, commands, cues, fades and running effects: while it is active the brightness of every fixture stays at 0, in the DMX output **and** in the 3D simulation. The values are kept: you can change brightness normally during a blackout, and after `Blackout Off` the **last set** state appears. Fixtures **without** a dimmer channel (pure RGB) are darkened through their colour. A pulsing bulb button in the toolbar shows an active blackout; clicking it toggles. The state applies to all devices but is **not** saved in the show.

### Timecode: `Timecode` / `TC`

The global timecode (the internal clock) can also be controlled by command – for example in a cue's **CMD** field (`Timecode Play` starts the clock when the cue fires).

| Command | Effect |
|---|---|
| `Timecode` | Shows the state (time, running/stopped, speed). |
| `Timecode At 4.3` | Jumps to 4.3 s (also `00:00:04.300`, `1:04.300`; at most 100 h). |
| `Timecode At 4.3 Play` | Jumps and starts (`Reverse` starts backwards). |
| `Timecode +5` / `Timecode -2` | Relative: 5 s forward / 2 s back. |
| `Timecode Play` / `Reverse` | Run forward / backward. |
| `Timecode Pause` | Pause. |
| `Timecode Stop` (`Reset`) | Stop and set to 00:00:00.000. |
| `Timecode Rate 2` | Speed (0.1 … 8; `0.5x` works too). |

Jumping does not fire timecode cues; only forward running does.

---

## 4. Colour and position: Color / RGB / Pan / Tilt

These also act on the **currently selected** fixtures.

| Command | Effect |
|---|---|
| `Color Red` | Sets the colour to red (named colour, list below). |
| `Color #FF8000` | Colour as hex (`#F80` short form works too). |
| `Color 255 128 0` | Colour as three values 0–255 (red / green / blue). |
| `RGB 255 0 0` | Same (dot2 notation). |
| `Pan 180` | Moves pan to 180°. |
| `Tilt -45` | Moves tilt to -45°. |
| `Pan 50%` | Pan in percent of the range (0–100 %; 50 % = centre). |
| `Pan +10%` / `Tilt -5%` | Relative to the current value, in percent of the range. |
| `Pan +15` / `Tilt -15` | Relative in degrees (with sign). |

**Named colours:** `Red`, `Green`, `Blue`, `White`, `Black`, `Yellow`, `Cyan`, `Magenta`, `Orange`, `Pink`, `Purple`, `Amber`, `Lime`, `Teal`, `Violet`, `LightBlue`, `Warm`, `Cool`.

**Degrees for pan/tilt:** OpenCue reads the real movement range (physical range) from the fixture's GDTF profile, so different fixtures may stand slightly differently at the same degree value. If the profile has no range, the default applies: **pan -270° to +270°, tilt -135° to +135°**.

---

## 5. Beam attributes and channels: Zoom, Gobo, CH …

Besides brightness, colour and position, **every channel** of a fixture can be set – in two ways: by **attribute name** (percent, same logic as the faders in the programmer) or directly by **channel number** or **name** (like “DMX direct”).

### Attributes in percent

| Command | Effect |
|---|---|
| `Zoom 50` | Zoom to 50 % (also `Zoom Full`, `Zoom Half`, `Zoom Min`, `Zoom 50%`). |
| `Focus 25` | Focus. |
| `Gobo 40` / `Gobo2 40` | Gobo wheel 1 / 2 (selection; number = percent of the channel). |
| `GoboSpin 30` / `Gobo2Spin 30` | Rotation / position of the gobo wheel. |
| `Prism 100` | Prism. |
| `Strobe 0` (`Shutter 0`) | Shutter / strobe. |
| `Zoom +10` / `Zoom -20` | Relative to the current value (percentage points). |

All values run 0–100 and are stored like the faders: `Store Cue` takes them over. If a fixture lacks the channel (a pure dimmer has no zoom) it is skipped and the feedback says so: `OK: Zoom 50 applied to 3 fixtures (Zoom not available on 1 of 3 fixtures)`. If **none** of the selected fixtures has the channel it is an error and nothing changes.

### Channels by number: `CH` / `Channel`

| Command | Effect |
|---|---|
| `CH6 128` | Channel 6 **of the fixture** (1 = first channel) to DMX value 128. |
| `Channel 6 128` | Same, written with a space (`CH 6 128` also works). |
| `CH6 50%` | With `%`: percent instead of DMX value (50 % = 128). |
| `CH6 +20` | Relative: 20 DMX steps more (`-20` less). |
| `CH6 Full` | 255 (also `Half` = 50 %, `Min` = 0). |

The channel number refers to the **order in the fixture's mode** (visible in the *DMX direct* tab of the programmer), not to the DMX address: `Fixture 5 Thru 8 CH6 255` sets the 6th channel of each selected fixture wherever it is patched. The value is **0–255** as in DMX direct.

### Channels by name

Every GDTF channel name of the fixture can be used directly as a clause (value in **percent**):

```
Fixture 1 Frost 50        Iris 30        Cyan 100
Channel Frost1 50         CH Frost 50
```

The name may be shortened as long as it stays unambiguous (`Frost` for `Frost1`); common short names are built in (`Cyan`, `Magenta`, `Yellow` for CMY channels, `Red`/`Green`/`Blue` for RGB channels, `Intensity` for the dimmer). The autocomplete shows which names a fixture has (chapter 14).

Channels with their own attribute (dimmer, pan, tilt, zoom, focus, gobo wheel, prism, shutter) are stored as that attribute; all others (frost, iris, colour wheel, fine channels …) as raw channel values. `Store Cue` takes over both.

---

## 6. Variables, effects, manual

Variables (presets) and effects can be applied to the **current selection** – alone or as a clause behind a selection like any other attribute.

| Command | Effect |
|---|---|
| `Variable "Warm White"` | Applies the variable **and links it**: the fixtures follow it until a value, an effect or a cue takes over the attribute (change the variable and the fixtures change with it). Short forms: `Var`, `Preset`. |
| `Effect Rainbow` | Assigns the effect (the category follows from the effect). Several fixtures run with a phase offset as in the dropdown. |
| `Effect Off` | Ends **all** effects of the selection; `Effect Off color position` only the named categories. |
| `Manual` | Back to **manual**: releases the variable link **and** the effect for all categories; the last output values stay. |
| `Manual color` | Only that category (`dimmer`, `color`, `position`, `zoom`, `focus`, `gobo`, several in a row, or `all`). |

Variable and effect names are unique in OpenCue and case-insensitive. With spaces either in `"…"` or simply one after another (`Variable warm white`). An unknown name gives an error with the list of existing ones. The autocomplete suggests variables (with their type) and effects (with their category).

```
Fixture 1 Thru 4 Variable "Warm White" Variable Wide Effect Wave
Group Front Manual color
Effect Off
```

---

## 7. Combined commands

Selection and value/attribute commands can be combined in **one line** – equivalent to two commands in a row, but faster to type:

```
Fixture 1 At 80
Fixture 1 Thru 5 At Full
Fixture 1 + 3 At 50
Fixture 1 Thru 10 Color Blue
Fixture 1 Pan 90 Tilt 45
Fixture 1 Thru 4 At 80 Zoom 30 Gobo 40 Frost 0
Group Front At 100 Color Warm
Fixture "Head 2" CH6 128
```

Several attribute clauses may follow each other directly (`Fixture 1 At 80 Color Red` sets dimmer AND colour in one go). If one clause contains an error (typo in the attribute, invalid number, a channel no fixture has), **neither** the selection **nor** any value changes.

---

## 8. Chained commands (comma or semicolon)

Several complete commands can be chained in **one** line, separated by comma or semicolon. They run one after the other:

```
Fixture 1 At 100, Fixture 2 At 50
Fixture 1 Color Red; Fixture 2 Color Blue; Fixture 3 At 0
```

If one part fails, the others still run; the log shows all partial results in one line separated by `|`. Commas and semicolons **inside quotes** (for example in a cue name) are ignored correctly: `Label Cue 1 "Act 1, scene 2"` is not split.

---

## 9. Clear: `Clear` vs. `Clear Clear`

| Input | Effect |
|---|---|
| `Clear` | Only releases the current selection. Programmed values stay. |
| `Clear Clear` | **Full reset:** sets **all** fixtures back completely – dimmer, colour (black), pan/tilt (0°), zoom, focus, gobo wheels 1 and 2 with rotation, prism, strobe **and every other channel of the fixture** (frost, iris, colour wheel, speed, fine channels …) to 0. Ends all effects, empties the programmer and releases the selection. |
| `Clear` twice **within 1.0 second** | Same as `Clear Clear` – quickly typing `Clear` twice triggers the full reset. |
| `Clear` … (more than 1.0 s) … `Clear` | Two independent “release selection” actions – **no** reset. |

---

## 10. Cue lists: select by name, Go, fader, manage

Cue commands act on the **active cue list** (dropdown in the cue list panel). With `Cuelist` (equivalent: `QList`, `Q-List`, `CL`, `List`, `Exec`) you can address any list **by name** – case-insensitive; names are unique in OpenCue, so it is always clear. As everywhere: **category first, then name** – a bare list name (`Show Go`) is not a command.

| Command | Effect |
|---|---|
| `Cuelist Show` | Makes “Show” the **active** list. |
| `Cuelist "Cue List 1"` | Name with spaces (without quotes too, if unambiguous: `Cuelist Cue List 1`). |
| `Cuelist 2` | The 2nd list in the order of the dropdown (like `Exec 2`). |
| `Cuelist Show Go` | Advances list “Show” by one step – **without** changing the active list. |
| `QList Show Go` | The same with the category `QList`. |

### Creating, renaming, duplicating, deleting lists

| Command | Effect |
|---|---|
| `Cuelist New "Act 1"` | Creates a new list (names are unique; without a name: `Cue List 1`, `Cue List 2` …). If there was none, it becomes active. |
| `Cuelist Show Rename "Act 1"` | Renames (a name already in use is rejected). |
| `Cuelist Show Duplicate` | Copies with all cues, new IDs, name `Show (copy)`; with a name: `Duplicate "Backup"`. |
| `Cuelist Show Delete` | Deletes the list (`Delete Cuelist Show` works too) – **without** a confirmation; a running fade ends. |

A list named “New” is reached in quotes: `Cuelist "New" Go`. Any cue command may follow the list name; it then applies to exactly that list, and the feedback names it in brackets (`OK: Go Cue 1 [Show]`).

### Playback

| Command | Effect |
|---|---|
| `Go` | Next cue (at the end of the list Go jumps to the first cue, like the button). |
| `Go Cue 3` / `Go 3` | Jumps directly to cue 3 (soft fade with its fade time). |
| `Goto Cue 3` | Same as `Go Cue 3`. |
| `Back` / `Go Back` | Previous cue. |
| `Pause` / `Resume` | Pause / continue the running fade. |
| `Stop` | Abort the fade (values stay); also ends all running effects. |
| `Fader 50` | The list's **fader** (mix between manual value and cue, like the executor fader) to 50 %. Also `Fader Full`, `Fader +10`, `Fader At 30`. |
| `Off` / `Off Exec 1` / `Off Cuelist Show` | Resets the active-cue state of the active / the 1st / the named list. (Executors are not separate objects yet; `Exec N` means the N-th list. `Off` does not fade out the last DMX values.) |

```
Cuelist Show Go                Go Cue 3
Cuelist "Encore" Goto Cue 1    QList "Encore" Fader 40
Cuelist Show Fader +10         Cuelist 2 Back
```

---

## 11. Managing cues

All cue commands act on the **active cue list** – or, with a leading `Cuelist <name>`, on the named list.

| Command | Effect |
|---|---|
| `Store Cue 1` | Stores the values currently set in the programmer (red / “touched”) as a new cue. |
| `Store Cue 1.5` | Decimal numbers allow inserting between existing cues later. |
| `Store Cue 4 "Intro"` | With a name (otherwise the cue is called “Cue 4”). |
| `Store Cue 3 Merge` | If cue 3 exists: only the changed channels go into it, the rest stays. Without `Merge`/`Overwrite`, `Store Cue 3` reports an error instead of creating a duplicate number. |
| `Store Cue 3 Overwrite` | If cue 3 exists: its content is replaced completely by the programmer (name, times, trigger stay). |
| `Update` | Takes the programmer values into the **active** cue (changed channels only). Following cues that do not set these values themselves take them over when played (tracking). |
| `Update CueOnly` | Like `Update`, but the following cue keeps its previous look. |
| `Delete Cue 3` | Deletes cue 3. With a range: `Delete Cue 3 Thru 5`. |
| `Move Cue 1 At 5` | Renumbers cue 1 to 5 (the list re-sorts). If the target number exists, an error is reported. |
| `Label Cue 1 "Intro"` / `Set Cue 1 Name "Intro"` | Renames cue 1. |

After a successful `Store Cue` the programmer is cleared for the stored fixtures (the red marker disappears). New cues get `Fade = 0.0 s` (hard switch) by default.

### Cue properties: `Cue <number> <property> <value>`

Everything in the edit dialog (and in the columns of the cue list) can be set by command. Instead of a number a range also works: `Cue 1 Thru 5 Fade 2` changes cues 1 to 5.

| Command | Effect |
|---|---|
| `Cue 1 Fade 3` / `Cue 1 Delay 1.5` | General (dimmer) times in seconds. |
| `Cue 1 Color Fade 2` / `Color Delay` | Own time for colour (`Colour` works too). |
| `Cue 1 Pos Fade 4` / `Pos Delay` | Own time for position (`Position Fade` works too). |
| `Cue 1 Beam Fade 0` / `Beam Delay` | Own time for beam (gobo, prism, strobe, focus …). |
| `Cue 1 Zoom Fade 2` / `Zoom Delay 1` | Own time for zoom. |
| `Cue 1 Color Fade -` | A `-` (or `default`) resets the group to the general time. |
| `Cue 1 FX In 2` / `FX Out 1` | Fade effects in/out in seconds (`Effect In` / `Effect Out` work too). |
| `Cue 1 Trigger Go` / `Follow` | Trigger of the cue. |
| `Cue 1 Trigger Timecode 00:01:30` | Trigger by the global timecode (time as with `Timecode At`). |
| `Cue 1 MIB Auto` (`Off` / `On`) | Move In Black. |
| `Cue 1 Cmd "Fixture 1 At 0; Go"` | Command(s) the cue runs when it fires (chapter 12). |
| `Cue 1 Name "Intro"` | Name. |

---

## 12. CMD: attaching commands to a cue

Every cue has an optional text field **CMD** (right-click → Edit → section “MIB & CMD”, double-click in the column of the cue list, or by command `Cue 3 Cmd "…"`). If it contains a command, OpenCue runs it **automatically** when the cue is triggered (by `Go`, an automatic `Follow`, or the context menu “Fade here”) – before the actual fade begins.

Several commands are separated by **comma or semicolon**:

```
Fixture 1 At 0
Fixture 3 Thru 6 Color Blue
Fixture 1 At 0; Fixture 2 Zoom 30; Cuelist Encore Go
```

The result appears in the same shared command history as a typed command, so it stays visible that a cue triggered an action. The field takes up to 200 characters. CMD may contain **any** command from this reference, including chained and combined ones – a cue can start another list with `Cuelist Encore Go`. Recursive `Go Cue` calls are possible, but OpenCue does not detect endless loops between chained CMD cues.

---

## 13. Feedback in the log

Every executed command produces one line in the log area of the panel, with a timestamp:

```
[20:45:01] OpenCue> Fixture 1 Thru 10
           OK: 10 fixtures selected
[20:45:07] OpenCue> At 80
           OK: At 80 applied to 10 fixtures
[20:45:12] OpenCue> Store Cue 1
           OK: Cue 1 stored
```

Faulty commands are marked **red**:

```
[20:46:40] OpenCue> At 80
           At: no fixtures selected
[20:46:55] OpenCue> Go Cue 99
           Cue 99 not found
[20:47:02] OpenCue> Fixture 1 Colr Red
           Unknown attribute: Colr
```

Chained commands give **one** line with all partial results separated by `|`. The log is identical on **all** connected devices – every command, wherever it was typed (or run by a cue's CMD), appears in every open command line panel. Log text can be selected and copied.

---

## 14. Keyboard and autocomplete

| Key | Effect |
|---|---|
| `Enter` | Executes the command and clears the input. |
| `Arrow up` | Previous (older) command. |
| `Arrow down` | Next (newer) command, or back to the draft you had started. |
| `Tab` | Takes the first suggestion; each further `Tab` moves to the next. |
| `Shift` + `Tab` | Like `Tab`, backwards. |
| `Esc` | Closes the suggestion list. |

**Autocomplete:** while typing (and when clicking into the field) a list of fitting continuations appears above the input. At the start of a line it shows **only the categories** (`Fixture`, `Group`, `Cuelist`, `Cue`, `Go` …) – names and values come afterwards. The list knows the **current state**, not just the command words:

- after `Fixture ` the numbers (with the device name) and the names,
- after `Group ` the groups; after `Cuelist ` the cue lists (names with spaces are put in `"…"` automatically),
- after a fixture selection the attributes and exactly the **channels these fixtures have** (`Frost1`, `Iris`, `ColorSub_C` … with the channel number as hint),
- after `Go `, `Cue `, `Delete Cue ` the cues of the (named) list with their names, then the properties (`Fade`, `Color Fade`, `FX In`, `Trigger` …),
- after `Color ` the colour names, after `Zoom ` values (`Full`, `Half`, `Min`),
- after `Variable ` / `Effect ` the variables (with type) and effects (with category); after `Manual ` the categories; after `Store ` / `Delete ` / `Label ` `Cue` and `Group`; after `Cuelist ` first `New`; after `Blackout ` `On` / `Off`.

Italic lines are **hints** about the expected value (`<0-100> | +<n> | -<n> (%)`, `<0-255> (DMX) | <0-100>%`) and cannot be inserted. The list always refers to the **last partial command** (after the last comma/semicolon). A click on an entry inserts it as well. The whole grammar lives in the server; the interface only shows what the server suggests, so suggestions never differ from the real parser.

A small **switch** at the far right of the input line turns suggestions on and off (stored in the app configuration, applies to all devices).

In *Panel Properties → Module Settings* you can also change the text, success and error colours of the log.

---

## 15. Quick reference

```
Fixture 1                       Fixture 1 Thru 10          Fixture 1 + 3
Fixture "Head 2"                Group 1                    Group Front

At 80          At Full          At At          Full        At 0     At +10     At -10
Master 80      Master Full      Master -10

Color Red      Color #FF8000    Color 255 128 0            RGB 255 0 0
Pan 180   Tilt -45   Pan 50%    Pan +10%                   Pan +15

Zoom 50   Focus 25   Gobo 40   Gobo2 40   GoboSpin 30   Prism 100   Strobe 0
CH6 128   CH6 50%    Channel 6 +20   Frost 50   Channel Frost1 50   Cyan 100

Fixture 1 At 80 Color Red Zoom 30          Group Front At 100, Fixture 5 At 0

Blackout       Blackout On       Blackout Off

Variable "Warm White"   Effect Wave   Effect Off   Effect Off color   Manual   Manual color

Store Group "Front"   Store Group "Front" Merge   Delete Group Front   Label Group Front "New"

Clear          Clear Clear

Go    Back    Go Cue 3    Goto Cue 3    Pause    Resume    Stop    Fader 50
Cuelist New "Act 1"    Cuelist Show Rename "Act 2"    Cuelist Show Duplicate    Cuelist Show Delete
Cuelist Show    Cuelist Show Go    QList "Encore" Fader 40    Cuelist 2 Back    Off    Off Cuelist Show

Store Cue 1    Store Cue 1.5    Store Cue 4 "Intro"    Store Cue 3 Merge    Update    Update CueOnly
Delete Cue 3   Delete Cue 3 Thru 5    Move Cue 1 At 5    Label Cue 1 "Intro"
Cue 1 Fade 3   Cue 1 Delay 1.5   Cue 1 Thru 5 Fade 2   Cue 1 Color Fade 2   Cue 1 Pos Delay 1
Cue 1 FX In 2  Cue 1 Trigger Follow   Cue 1 Trigger Timecode 00:01:30   Cue 1 MIB Auto   Cue 1 Cmd "Fixture 1 At 0; Go"

Timecode Play    Timecode At 4.3    Timecode Stop
```
