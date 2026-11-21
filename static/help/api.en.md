# REST API

With the **REST API** other programs can **read** the state of OpenCue and **control and edit** it – scripts, a show controller, home automation, a stage-manager web page, a tablet app or your own tool. It speaks plain **HTTP** and answers in **JSON**. No extra software is needed, and it works completely offline inside your network.

Access is protected by **tokens** that you create in OpenCue. Every token has its own **permissions**, so a tablet app may only read while another tool may also trigger cues and a third one may build whole shows.

---

## 1. The idea in one minute

- The API lives under **`/api/v1/`** on the same address and port as OpenCue itself (for example `http://127.0.0.1:8000/api/v1/`).
- You **create a token** in *Settings → API* and send it with every request.
- **Read** requests (`GET`) return the state: fixtures, cue lists, cues, variables, effects, the DMX signal, the timecode, the programmer.
- **Operate** requests (`POST` / `PUT`) run the show: commands, cues, timecode, blackout, audio, the programmer.
- **Edit** requests change the show itself: create and change cue lists and cues, variables, effects and effect scripts, patch fixtures, save and load showfiles, upload media.
- The console's own **buttons, faders and toggles** can be pressed, moved and switched from outside.
- Everything an operator does in the window shows up **at once in all open windows** – also what the API changes.
- A **live stream** (`GET /events`) reports changes as they happen, so a dashboard does not have to ask over and over.
- For **hardware** (an ESP32 with joystick, knobs, buttons, microphone) there is a **WebSocket** (`/api/v1/ws`): joystick relative or absolute, set values absolute or relative, DMX and live values, send and receive the timecode, audio values and audio data in both directions (section 10). For simple devices without an interface of their own there are **status views** as an image or a web page (section 11).
- Every function needs **one permission**. A token without it gets `403`. The edit permissions are **off by default**.
- The API is its own, stable interface. The internal routes the program window uses are *not* part of it.

---

## 2. Quick start

1. Open **Settings → REST API** (also possible from a logged-in remote device). By default there is **no token** and the API only answers on **this computer**.
2. Click **New token**, give it a name, choose the permissions (or a preset) and click **Create token**. A **new token is created at once** (without *Save*) and shown right after.
3. **Copy the token now.** It is shown only once; afterwards only its first characters are visible. If it gets lost, create a new one or use *Generate new token*.
4. Try it:

```
curl -H "Authorization: Bearer oc_xxxxxxxx" http://127.0.0.1:8000/api/v1/status
```

The answer is a JSON object with the show name, blackout, grand master, timecode and more (see section 6).

The address in the examples (`127.0.0.1:8000`) is the console itself. For the address of other devices see section 8. A page with every route, searchable and readable offline, is at `/api/v1/docs`.

---

## 3. Tokens and permissions

### Managing tokens

In **Settings → REST API** you can:

| Action | Meaning |
|---|---|
| **REST API on/off** | The main switch. When off, every request is answered with `403 api_disabled`. |
| **Reachable from** | *This computer only* (default) or *The network*. Other devices also need **remote access** to be on; the page tells you otherwise (with a link). From outside, the API answers `403 api_local_only` when set to *This computer only*. |
| **Allow web pages on other addresses** | Browser pages opened from another address may call the API (CORS, section 8). On by default. |
| **Status views (image / web)** | Switch for the views of section 11. On by default (each needs a token). |
| **Connected now (WebSocket)** | List of the devices that are connected through the WebSocket right now (token, address, what they receive, joystick active, messages per second) – live, with **Disconnect**. |
| **New token** | Creates a token. A wide dialog lets you pick the permissions in three columns: *Read*, *Operate*, *Edit the show*. |
| **Edit** | Change name and permissions. |
| **Active switch** | Switches one token off and on again without deleting it (`403 token_disabled` while off). |
| **Generate new token** (in *Edit*) | Replaces the secret. The old token stops working as soon as you save. |
| **Delete** | Asks in a dialog of its own (can be switched off, see *Defaults → Deleting*) and then deletes the token **at once**. |
| **Last used** | Shows when a token was used the last time. |

A **new token** is created and shown at once, a **delete** applies at once after the question. Everything else is a **draft** like in all settings (switch, edit, regenerate): changed rows are marked and counted, only **Save** applies everything (the dialog stays open), *Close* discards after a question. Tokens can only be managed at the console computer itself, not from remote devices.

Only a **hash** of the token is stored on disk, never the token itself.

### The permissions

**Read**

| Permission | Allows | Default |
|---|---|---|
| **Status** | State: show name, blackout, grand master, timecode, selection, programmer, audio analysis, outputs, the live event stream | on |
| **Show data** | Fixtures, fixture types, groups, variables, effects, effect scripts, showfiles, cue lists and cues, media, layouts | on |
| **DMX output** | Current DMX values and the live state of each fixture | on |

**Operate**

| Permission | Allows | Default |
|---|---|---|
| **Console commands** | Run any command of the command line (can also change and delete show data) – *critical* | on |
| **Cue lists** | Go, Back, jump to a cue, pause, resume, stop, fader | on |
| **Timecode** | Start, pause, stop, seek, speed | on |
| **Blackout and master** | Switch blackout, set grand master | on |
| **Audio** | Open / close the audio source, change its settings, tap the tempo | on |
| **Programmer and selection** | Select fixtures, set values and variables live, clear the programmer | on |
| **Console buttons, faders, toggles** | Press, move and switch the console's own Button, Fader and Toggle panels (they run the commands set up in them) | on |
| **Set DMX directly** | Write DMX channels – overrides the running show – *critical* | **off** |

**Edit the show**

| Permission | Allows | Default |
|---|---|---|
| **Cue lists and cues** | Create, change, copy, renumber and delete cue lists and cues; store the programmer as a cue | **off** |
| **Variables** | Create, change and delete variables and variable groups | **off** |
| **Effects** | Create, change and delete effects and effect groups; start and stop effects on fixtures | **off** |
| **Effect scripts** | Check, save and delete effect types (script files) | **off** |
| **Patch and fixture groups** | Patch, change and delete fixtures; manage fixture groups; install and remove GDTF fixture types – *critical* | **off** |
| **Showfiles** | New, load, save, rename, copy and delete showfiles – *critical* | **off** |
| **Media** | Upload, rename and delete video and audio files | **off** |
| **Layouts** | Show a saved panel layout in the console window | **off** |
| **DMX outputs and language** | Switch Art-Net, sACN and USB DMX, change addresses, default universe, language – *critical* | **off** |

**Presets** in the dialog: *Read only* (the three reading permissions), *Operate* (reading plus cue lists, timecode, blackout/master, audio, programmer and the console's buttons / faders / toggles – no commands, no direct DMX), *Edit show* (Operate plus cue lists and cues, variables, effects), *Full access* and *Default*.

---

## 4. Rules for all requests

- **Sign-in:** send the token as `Authorization: Bearer oc_…`. The header `X-API-Key: oc_…` works as well.
- **Format:** requests with a body use JSON and `Content-Type: application/json`. Answers are always JSON (except the event stream and file downloads).
- **Choosing things:**
  - a *fixture* by its **number (FID)**, its id or an unambiguous name; a *group* of fixtures by its name;
  - a *cue list* by its **name** or id; a *cue* by its **number** (for example `1.5`) or id;
  - a *variable*, an *effect* or a *showfile* by its **name** (upper / lower case does not matter) or id.
  - Names with spaces must be URL-encoded in the path (`Par%20links`).
- **Choosing several fixtures** in a body: `"fixtures": [1, 2, "Front"]`, `"fixture": 3` and / or `"group": "Wash"`. For the programmer calls `"selection": true` means the fixtures selected on the console, and a call without any of them uses the selection.
- **Percent and bytes:** dimmer, position and the like are given in **percent (0–100)**, raw DMX channels in **0–255**, colours as `"#rrggbb"`, `[r, g, b]` or `{"r": …, "g": …, "b": …}` (0–255).
- **Times** in seconds; the timecode as seconds or text (`00:01:04.300`).
- **Careful input checks:** a field that does not exist is rejected (`422`), a wrong value or name is `400`, a name that is already taken is `409 duplicate`. Nothing is guessed or ignored silently.
- **Checked before anything changes:** a call with a wrong value, name or fixture is refused as a whole – a cue with one wrong fixture is not stored half.

### Errors

Errors always look the same:

```json
{ "error": { "code": "not_found", "message": "No fixture '99' (use the fixture number, id or an unambiguous name)." } }
```

| HTTP | `code` | Meaning |
|---|---|---|
| 400 | `bad_request` | The request is wrong (a value out of range, an unknown attribute, an empty command …) |
| 401 | `unauthorized` | Token missing or invalid |
| 403 | `forbidden` | The token does not have the permission for this function |
| 403 | `token_disabled` / `api_disabled` | The token or the whole API is switched off |
| 404 | `not_found` | Fixture, cue list, cue, variable, effect, showfile … does not exist |
| 409 | `duplicate` | The name is taken (cue list, variable, effect, group …) |
| 409 | `cue_exists` | A cue with this number exists – send `on_conflict` (`merge` / `overwrite`) |
| 409 | `address_conflict` | The DMX addresses overlap another fixture – `allow_overlap: true` patches anyway |
| 409 | `unsaved_changes` | The show has unsaved changes – save it, or send `force: true` |
| 409 | `exists` / `in_use` / `never_saved` | A showfile or script of that name exists / the showfile is the loaded one / the show has no file yet |
| 409 | `no_active_cue` / `programmer_empty` | *Update* without an active cue or an empty programmer |
| 409 | `audio_failed` | The audio source could not be opened (the reason is in the message) |
| 415 | `invalid_type` | A media upload that is no supported video / audio file |
| 422 | `invalid` | A field is missing, unknown or has a wrong type |
| 422 | `invalid_script` | A script does not compile or fails its test run (with the line) |
| 429 | `rate_limited` | Too many wrong tokens from this address – wait for the time in `Retry-After` |

A **console command that is rejected** (for example a typo) is *not* an HTTP error: the answer is `200` with `"success": false` and the message of the command line.

---

## 5. Endpoint overview

All paths start with `/api/v1`. The permission in the right column is what the token needs. In the paths `{list}` is a cue list, `{cue}` a cue, `{fixture}` a fixture, `{ref}` a variable / effect / name.

### Read

| Method | Path | Returns | Permission |
|---|---|---|---|
| GET | `/` | Index: version, links, what this token may do | Status |
| GET | `/status` | Overall state: show, blackout, master, timecode, selection, active cue list, DMX outputs, counts | Status |
| GET | `/blackout` · `/master` · `/timecode` · `/selection` | One part of the state | Status |
| GET | `/system` | Version, language, DMX outputs (Art-Net, sACN, USB), universes, remote access, data folder | Status |
| GET | `/showfile` | Name of the loaded show, whether it has unsaved changes and a file | Status |
| GET | `/programmer` | Selection, the values set by hand (percent, colour + hex, raw channels), the variables they follow, running effects | Status |
| GET | `/audio` · `/audio/devices` | The live audio analysis and the settings / every audio input | Status |
| GET | `/system/usb-ports` · `/command/suggest?text=` | Serial ports for USB DMX / completions for a command (like Tab in the command line) | Status |
| GET | `/events` | **Live stream** of changes (Server-Sent Events, section 6) | Status |
| GET | `/fixtures` | All fixtures. Optional `?universe=`, `?group=`, `?include_state=true` | Show data |
| GET | `/fixtures/{fixture}` | One fixture with every channel (address, current DMX value) and its state | Show data |
| GET | `/fixture-types` | The fixture library: id, name, manufacturer, modes with channel count (`?q=` filters) | Show data |
| GET | `/groups` · `/variable-groups` · `/effect-groups` | Fixture groups, variable groups, effect groups | Show data |
| GET | `/variables` · `/variables/{ref}` | All variables / one (with how many cue entries use it) | Show data |
| GET | `/effects` · `/effects/{ref}` · `/effects/assignments` | Effects / one effect with its type info / which effect runs on which fixture | Show data |
| GET | `/effect-scripts` · `/effect-scripts/{name}` | All effect types (category, tags, settings) / the source text of one | Show data |
| GET | `/cuelists` · `/cuelists/{list}` | All cue lists with active cue, fader and playback state / one list with all its cues | Show data |
| GET | `/cuelists/{list}/cues` | The cues of a list; `?detail=true` adds **what each cue changes** | Show data |
| GET | `/cuelists/{list}/cues/{cue}` | One cue in full detail | Show data |
| GET | `/showfiles` | Saved showfile names (and the loaded one) | Show data |
| GET | `/media` · `/media/{id}/file` | The media of the show / download one | Show data |
| GET | `/layouts` | Saved layouts of the console | Show data |
| GET | `/widgets` | The console's Button / Fader / Toggle panels: commands, fader limits and value, toggle state | Show data |
| GET | `/dmx` · `/dmx/{universe}` | The universes and their values (`?first=&last=`, `?nonzero=true`) | DMX output |
| GET | `/fixtures/state` | The live state of **every** fixture (what the console outputs right now) | DMX output |

### Operate

| Method | Path | Body | Permission |
|---|---|---|---|
| POST | `/command` | `{"command": "Fixture 1 At 80"}` | Console commands |
| POST | `/commands` | `{"commands": ["…", "…"], "stop_on_error": false}` – up to 100 | Console commands |
| POST | `/cuelists/{list}/go` | optional `{"cue": "2"}` (without: the next cue) | Cue lists |
| POST | `/cuelists/{list}/back` · `/pause` · `/resume` · `/stop` | – | Cue lists |
| PUT | `/cuelists/{list}/fader` | `{"value": 70}` (percent) | Cue lists |
| PUT | `/timecode` | `{"action": "play" \| "pause" \| "stop" \| "seek" \| "rate", "position": …, "direction": 1, "rate": 1}` | Timecode |
| PUT | `/blackout` | `{"enabled": true}` (without a value: toggle) | Blackout and master |
| PUT | `/master` | `{"value": 80}` (percent) | Blackout and master |
| PUT | `/audio` | `{"running": true, "device": "demo", "settings": {"mode": "manual", "bpm": 128}}` – every field optional | Audio |
| POST | `/audio/tap` | – (one tap of the tempo button) | Audio |
| PUT | `/selection` | `{"fixtures": [1, 2], "mode": "set" \| "add" \| "remove" \| "clear"}` (also `group`) | Programmer and selection |
| PUT | `/programmer/values` | `{"fixtures": [1, 2], "values": {"dimmer": 80, "color": "#ff0000"}}` | Programmer and selection |
| POST | `/programmer/variables` | `{"variable": "Warm white", "fixtures": [1, 2]}` – applies and links a variable | Programmer and selection |
| POST | `/widgets/{id}/press` | – (runs the command of a button) | Console buttons, faders, toggles |
| PUT | `/widgets/{id}/value` | `{"value": 70}` (fader; limited to its minimum / maximum, rounded) | Console buttons, faders, toggles |
| PUT | `/widgets/{id}/state` | `{"on": true}` (toggle; without a value it flips) | Console buttons, faders, toggles |
| POST | `/programmer/clear` | `{"fixtures": [1]}` forgets their values; `{"all": true}` = *Clear Clear*: everything dark | Programmer and selection |
| PUT | `/dmx/{universe}/{channel}` | `{"value": 255}` or `{"percent": 100}` | Set DMX directly |
| PUT | `/dmx/{universe}` | `{"channels": {"1": 255, "2": 0}}` | Set DMX directly |
| PUT | `/fixtures/{fixture}/channels/{channel}` | `{"value": 128}` or `{"percent": 50}`; `{channel}` is the channel number of the fixture (1 = first) or its name (`Dimmer`) | Set DMX directly |

### Edit: cue lists and cues – permission *Cue lists and cues*

| Method | Path | Body | What it does |
|---|---|---|---|
| POST | `/cuelists` | `{"name": "Act 1"}` | Create a cue list (201) |
| PUT | `/cuelists/{list}` | `{"name": "…", "active": true}` | Rename; `active` makes it the list that cue list panels show |
| PUT | `/cuelists/order` | `{"order": ["Act 2", "Act 1"]}` | Order of the lists |
| POST | `/cuelists/{list}/duplicate` | `{"name": "Copy"}` | Copy with all cues |
| DELETE | `/cuelists/{list}` | – | Delete the list |
| POST | `/cuelists/{list}/cues` | see below | Create a cue (201) |
| PUT | `/cuelists/{list}/cues/{cue}` | see below | Change properties and / or content, renumber |
| DELETE | `/cuelists/{list}/cues/{cue}` | – | Delete a cue |
| POST | `/cuelists/{list}/cues/delete` | `{"cues": ["1", "2.5"]}` | Delete several (all or none) |
| POST | `/cuelists/{list}/cues/{cue}/duplicate` | `{"number": 9, "name": "…"}` | Copy a cue |
| POST | `/cuelists/{list}/update-active` | `{"mode": "normal" \| "only"}` | Take the programmer into the active cue (like *Update*) |

**Cue body** (create and change; every field optional when changing):

| Field | Meaning |
|---|---|
| `number` | Cue number, decimals allowed. Left out when creating: the next free number. |
| `name`, `fade`, `delay` | Name and the general times in seconds |
| `trigger` | `go` · `follow` · `timecode` · `audio` · `midi` · `clock` |
| `timecode` | For `timecode`: seconds or `1:04.300` |
| `audio` | For `audio`: `{"source": "beat" \| "kick" \| "snare" \| "hat" \| "level" \| "bass" \| "mid" \| "high" \| "b1" … "b8", "value": 4}` (every n-th hit, or a threshold in %) |
| `midi` | For `midi`: `{"type": "note" \| "cc" \| "pc", "number": 60, "channel": 0, "value": 64}` – the cue fires when this signal arrives while it is the next cue of a running list; `channel` 0 = any (1–16 = one channel), `value` = the threshold of a `cc` (1–127) |
| `clock` | For `clock`: `{"time": "19:30", "days": "Mon-Fri"}` (or `"days": [0,1,2,3,4]`, Monday = 0; empty = every day) - the cue waits as the next cue of a running list for this time of the wall clock. |
| `mib`, `command` | Move in black (`Off` / `Auto` / `On`); console commands that run with the cue |
| `times` | Own times per group: `{"color": {"fade": 2, "delay": 0}, "position": {…}, "beam": {…}, "zoom": {…}}`; `null` = use the general time again |
| `effect_fade` | `{"in": 1, "out": 2}` |
| `changes` | What the cue changes (below) |
| `effects` | The effects the cue starts: `[{"fixtures": [2, 3], "effects": {"dimmer": "Strobe"}}]` (category → effect name) |
| `from_programmer` | *(create)* also store what is in the programmer **and every change of the picture compared with the cue before** (like *Store Cue*; if nothing changed: `409 nothing_changed`); `clear_programmer` empties it afterwards |
| `on_conflict` | *(create / renumber)* the number exists: `merge` (only the sent attributes join the existing cue) or `overwrite` |
| `content` | *(change)* `merge` (default) or `replace`: the content of the cue is exactly what is sent |

`changes` is a list; each entry names fixtures and what they get:

```json
{ "fixtures": [2, 3], "values": { "dimmer": 80, "color": "#00ff00", "pan": 40 }, "variables": { "color": "Warm white" } }
```

`values`: `dimmer`, `pan`, `tilt`, `strobe`, `gobo`, `gobo_spin`, `gobo2`, `gobo2_spin`, `prism`, `focus`, `zoom` in percent, `color`, raw channels `ch<N>` (0–255). `variables` maps a type (`dimmer`, `position`, `color`, `focus`, `zoom`, `gobo`) to a variable: the cue then **refers to the variable** (a placeholder, resolved live when the cue runs) instead of storing the value.

### Edit: variables – permission *Variables*

| Method | Path | Body | What it does |
|---|---|---|---|
| POST | `/variables` | `{"name": "Warm white", "type": "color", "group": "Colours", "values": {"hex": "#ffb060"}}` | Create |
| PUT | `/variables/{ref}` | `{"name": "…", "group": "…", "values": {…}}` | Change; the type cannot change. A new value reaches the programmer, running cues and **every cue that uses the variable** |
| DELETE | `/variables/{ref}` | – | Delete (programmer links are released) |
| POST · DELETE | `/variable-groups` · `/variable-groups/{name}` | `{"name": "Colours"}` | Create / delete a group (its variables stay) |

`values` by type: `dimmer`, `focus`, `zoom`: `{"level": 0-100}` · `position`: `{"pan": 0-100, "tilt": 0-100}` · `color`: `{"r","g","b"}` or `{"hex": "#ff8000"}` · `gobo`: `{"level", "spin", "gobo2", "gobo2_spin"}`.

### Edit: effects – permission *Effects*

| Method | Path | Body | What it does |
|---|---|---|---|
| POST | `/effects` | `{"script": "strobe", "name": "Blink", "group": "…", "params": {"rate_hz": 8}}` | Create an effect from an effect type (`GET /effect-scripts`); `params` are checked against the limits of the type |
| PUT | `/effects/{ref}` | `{"name", "group", "params"}` | Change (the type cannot change) |
| DELETE | `/effects/{ref}` | – | Delete; it stops everywhere |
| POST | `/effects/{ref}/assign` | `{"fixtures": [2, 3]}` (also `group`) | **Start** the effect on fixtures (the order spreads waves) |
| POST | `/effects/release` | `{"fixtures": [2], "categories": ["dimmer"]}` | **Stop** effects on fixtures (the values stay) |
| POST · DELETE | `/effect-groups` · `/effect-groups/{name}` | `{"name": "…"}` | Create / delete a group |

### Edit: effect scripts – permission *Effect scripts*

| Method | Path | Body | What it does |
|---|---|---|---|
| POST | `/effect-scripts/check` | `{"text": "…"}` | Compile and test-run a script without saving: `{ok, line, message}` |
| POST | `/effect-scripts/preview` | `{"text": "…", "count": 3, "duration": 4, "bpm": 120, "params": {…}}` | Simulate the curves without fixtures |
| PUT | `/effect-scripts/{name}` | `{"text": "…", "overwrite": false}` | Save as file in the user's effect folder – **only if it compiles and runs** (`422 invalid_script` with the line). An existing name needs `overwrite` |
| DELETE | `/effect-scripts/{name}` | – | Delete a script of the user folder; effects of this type stop |

The script language is described in the *Effect Studio* guide.

### Edit: patch and fixture groups – permission *Patch and fixture groups*

| Method | Path | Body | What it does |
|---|---|---|---|
| POST | `/fixtures` | `{"type": "Generic RGBW LED Par", "mode": "…", "name": "Par", "quantity": 4, "universe": 1, "address": 11, "group": "Wash"}` | Patch one or more fixtures one after the other. The addresses are checked (they must fit into 512 and not overlap – `allow_overlap: true` overrides) |
| PUT | `/fixtures/{fixture}` | `{"name", "universe", "address", "sort_index", "group", "allow_overlap"}` | Change; `"group": ""` takes it out of its group |
| DELETE | `/fixtures/{fixture}` · POST `/fixtures/delete` | `{"fixtures": [1, 2]}` | Delete (cues keep their entries for the missing fixture, like in the window) |
| POST | `/groups` | `{"name": "Wash", "fixtures": [2, 3]}` | Create a fixture group |
| POST | `/fixture-types` | the raw `.gdtf` file; header `X-Filename` (URL-encoded) | Install a fixture type (up to 30 MB; checked before it is installed) |
| DELETE | `/fixture-types/{id}` | – | Remove an installed type (`409 in_use` while the show uses it) |
| PUT · DELETE | `/groups/{name}` | `{"name": "…", "fixtures": […]}` | Rename / set the members (replaces the list) / delete (the fixtures stay) |

### Edit: showfiles – permission *Showfiles*

| Method | Path | Body | What it does |
|---|---|---|---|
| POST | `/showfile/new` | `{"force": false}` | Start a new, empty show |
| POST | `/showfile/save` | – | Save under the current name (`409 never_saved` if it has no file yet) |
| POST | `/showfile/save-as` | `{"name": "Concert", "overwrite": false}` | Save under a name (characters that are not allowed in file names are removed) |
| POST | `/showfile/load` | `{"name": "Concert", "force": false}` | Load a saved show – replaces the running one |
| POST | `/showfiles/{name}/rename` | `{"new_name": "…", "overwrite": false}` | Rename a saved file |
| POST | `/showfiles/{name}/duplicate` | – | Copy a saved file |
| DELETE | `/showfiles/{name}` | `?force=true` for the loaded one | Delete a saved file |

**New** and **Load** replace the running show. With unsaved changes they are refused with `409 unsaved_changes` until you save first or send `"force": true`.

### Edit: media – permission *Media*

| Method | Path | Body | What it does |
|---|---|---|---|
| POST | `/media` | the raw file; header `X-Filename` (URL-encoded) | Upload a video / audio file (up to 1 GB; the same file twice is one entry) |
| PUT | `/media/{id}` | `{"name": "…"}` | Rename |
| DELETE | `/media/{id}` | – | Remove from the show and delete the copy |

### Edit: layouts and settings – permissions *Layouts* and *DMX outputs and language*

| Method | Path | Body | What it does |
|---|---|---|---|
| POST | `/layouts/{filename}/load` | – | Show a saved layout (`Name.json` as in `GET /layouts`) in the console window; unsaved layout changes there are lost |
| PUT | `/system` | `{"artnet": {"enabled": true, "ip": "2.255.255.255", "bind_ip": ""}, "sacn": {"enabled": true}, "enttec": {"enabled": false, "port": "COM3", "universe": 1}, "default_universe": 1, "language": "de"}` – every field optional | Switch the DMX outputs and change language / default universe; the answer is `GET /system` |
| POST | `/system/dmx/reinitialize` | – | Restart the DMX outputs without restarting the program |

### Documentation (no token)

| Method | Path | Returns |
|---|---|---|
| GET | `/docs` | A readable, searchable overview of all routes (works offline) |
| GET | `/openapi.json` | The machine-readable description (OpenAPI 3.1); every route lists its permission as `x-capability` |

---

## 6. Examples with real answers

### State

```
GET /api/v1/status
```

```json
{
  "app": { "name": "OpenCue", "version": "1.0.0" },
  "show": { "name": "Concert", "unsaved_changes": true },
  "blackout": false,
  "grand_master": 100.0,
  "timecode": { "running": false, "direction": 1, "rate": 1.0, "position_ms": 0.0, "position": "00:00:00.000" },
  "selection": { "fixture_ids": ["228a68e5-…"], "fids": [2] },
  "active_cuelist": { "id": "7e5d274f-…", "name": "Show" },
  "dmx": { "universes": [1], "artnet": true, "sacn": false, "usb": false },
  "counts": { "fixtures": 2, "groups": 1, "variables": 0, "effects": 0, "cuelists": 1, "cues": 2 }
}
```

### Which fixtures are in the show, and what colour do they have?

```
GET /api/v1/fixtures?include_state=true
GET /api/v1/fixtures/state
```

```json
{
  "fixtures": [
    { "id": "9ea4feaa-…", "fid": 1, "name": "Front", "state": { "dimmer": 80.0 } },
    { "id": "228a68e5-…", "fid": 2, "name": "Par left",
      "state": { "dimmer": 100.0, "color": { "r": 255, "g": 0, "b": 0, "hex": "#ff0000" } } }
  ]
}
```

`state` contains exactly what the console currently outputs, read from the DMX buffer: `dimmer`, `pan`, `tilt`, `zoom`, `focus` … in percent and `color` as r/g/b. Attributes a fixture does not have are missing. (At grand master 0 or blackout the dimmer cannot be reconstructed and is left out.)

### One fixture with all channels

```
GET /api/v1/fixtures/2
```

```json
{
  "id": "228a68e5-…", "fid": 2, "name": "Par left", "type": "Generic RGBW LED Par", "manufacturer": "Generic",
  "universe": 1, "start_channel": 11, "end_channel": 14, "channel_count": 4, "mode": "default", "group": "Wash",
  "channels": [
    { "channel": 1, "name": "ColorAdd_R", "address": 11, "value": 255 },
    { "channel": 2, "name": "ColorAdd_G", "address": 12, "value": 0 },
    { "channel": 3, "name": "ColorAdd_B", "address": 13, "value": 0 },
    { "channel": 4, "name": "ColorAdd_W", "address": 14, "value": 0 }
  ],
  "state": { "color": { "r": 255, "g": 0, "b": 0, "hex": "#ff0000" } }
}
```

### What does a cue change?

```
GET /api/v1/cuelists/Show/cues/1
```

```json
{
  "id": "700571ee-…", "number": 1, "name": "Auf", "active": false,
  "trigger": "go", "timecode_ms": null, "timecode": null, "audio": null, "midi": null, "clock": null,
  "fade": 2.0, "delay": 0.0,
  "times": { "color": { "fade": null, "delay": null }, "position": { "fade": null, "delay": null },
             "beam": { "fade": null, "delay": null }, "zoom": { "fade": null, "delay": null } },
  "effect_fade": { "in": 0.0, "out": 0.0 }, "mib": "Off", "command": "", "fixture_count": 2,
  "changes": [
    { "fixture_id": "9ea4feaa-…", "fid": 1, "name": "Front", "values": { "dimmer": 50 }, "variables": {} },
    { "fixture_id": "228a68e5-…", "fid": 2, "name": "Par left",
      "values": { "dimmer": 100, "color": { "r": 255, "g": 0, "b": 0, "hex": "#ff0000" } }, "variables": {} }
  ],
  "effects": [],
  "cuelist": { "id": "7e5d274f-…", "name": "Show" }
}
```

- `fade` / `delay` are the general times; `times` holds the optional times per attribute group (`null` = uses the general time).
- `changes[].values` are the fixed values stored in the cue. `variables` lists the variables (placeholders) the cue refers to, by type and name – a variable is resolved live when the cue runs.
- `effects` lists the effects the cue starts, per fixture.
- All cues of a list at once with their details: `GET /api/v1/cuelists/Show/cues?detail=true`.

### The DMX signal

```
GET /api/v1/dmx/1?first=1&last=14
GET /api/v1/dmx/1?nonzero=true
```

```json
{ "universe": 1, "first": 1, "last": 14, "values": [0,0,0,0,0,0,0,0,0,0,255,0,0,0] }
{ "universe": 1, "first": 1, "last": 512, "channels": { "11": 255 } }
```

### Run a console command

```
POST /api/v1/command
{ "command": "Fixture 1 Thru 4 At 80" }
```

```json
{ "command": "Fixture 1 Thru 4 At 80", "success": true, "message": "OK: 4 fixtures selected; At 80 applied" }
```

All commands of the command line work, also chained with `;` (see the *Command reference* guide).

### Trigger a cue

```
POST /api/v1/cuelists/Show/go            { "cue": "2" }
```

```json
{ "cuelist": { "id": "7e5d274f-…", "name": "Show" }, "command": "Cuelist \"Show\" Go Cue 2", "success": true, "message": "OK: Go Cue 2 [Show]" }
```

Without a body `go` starts the next cue. Note: a cue list whose **name contains a quotation mark** cannot be addressed this way; rename it.

### Timecode

```
PUT /api/v1/timecode   { "action": "seek", "position": "1:04.300" }
PUT /api/v1/timecode   { "action": "play", "position": 10 }
GET /api/v1/timecode
```

```json
{ "running": false, "direction": 1, "rate": 1.0, "position_ms": 64300.0, "position": "00:01:04.300" }
```

`position` is a number in **seconds** or text such as `1:04.300` or `00:00:04.300`. `play` may start from a `position` and run backwards with `"direction": -1`; `rate` is the speed between 0.1 and 8. Jumping with `seek` does not fire timecode cues.

### Set DMX channels

```
PUT /api/v1/dmx/1/200                      { "value": 255 }
PUT /api/v1/dmx/1                          { "channels": { "201": 10, "202": 20 } }
PUT /api/v1/fixtures/Front/channels/Dimmer { "percent": 50 }
```

```json
{ "universe": 1, "channel": 1, "value": 128, "fixture": { "fid": 1, "name": "Front" }, "channel_of_fixture": 1 }
```

A channel that belongs to a **fixture** is set like the *DMX direct* fader of the programmer: it becomes a manual value that running cues no longer mix. Other channels are written straight to the output. This permission is **off by default**.

### Audio: read and control

```
GET  /api/v1/audio/devices                    -> { "devices": [ { "id": "demo", "kind": "demo", "name": "Demo beat" }, ... ] }
PUT  /api/v1/audio    { "device": "demo" }    open that source (`running` false closes it)
PUT  /api/v1/audio    { "settings": { "mode": "manual", "bpm": 128, "sensitivity": 0.7 } }
POST /api/v1/audio/tap                        tap the tempo (about 4 taps in a row set it, the tempo switches to manual)
GET  /api/v1/audio                            level, bands, kick / snare / hat, bpm, beat_phase ... and the settings
```

`PUT /audio` applies the `settings` first, then opens (`running: true`, or a `device`) or closes (`running: false`) the source, and answers like `GET /audio`. If the source cannot be opened the answer is `409 audio_failed` with the reason. Settings: `gain`, `auto_gain`, `sensitivity`, `smoothing`, `latency_ms`, `mode` (`auto` | `manual`), `bpm` (manual tempo), `phase_follow`, `demo_bpm`, `autostart`; unknown keys are ignored and numbers are limited to their range.

### Build a cue

```
POST /api/v1/cuelists/Show/cues
{
  "number": 3, "name": "Blue wash", "fade": 3,
  "changes": [
    { "group": "Wash", "values": { "dimmer": 80, "color": "#0000ff" } },
    { "fixtures": [1], "values": { "dimmer": 20 } }
  ],
  "effects": [ { "fixtures": [2, 3], "effects": { "dimmer": "Blink" } } ]
}
```

```json
{ "status": "created", "cuelist": { "id": "7e5d274f-…", "name": "Show" },
  "cue": { "id": "5c0b…", "number": 3, "name": "Blue wash", "fade": 3.0, "changes": [ … ], "effects": [ … ], … } }
```

The answer is the whole cue as `GET …/cues/3` would show it. If cue 3 exists you get `409 cue_exists`; send `"on_conflict": "merge"` to add the sent attributes to it, or `"overwrite"` to replace its content (status `merged` / `overwritten`).

The same from the programmer, like *Store Cue*:

```
PUT  /api/v1/programmer/values   { "fixtures": [2, 3], "values": { "color": "#ff8000", "dimmer": 100 } }
POST /api/v1/cuelists/Show/cues  { "number": 4, "name": "Orange", "from_programmer": true, "clear_programmer": true }
```

### Change and delete cues

```
PUT    /api/v1/cuelists/Show/cues/3   { "name": "Deep blue", "fade": 5, "times": { "color": { "fade": 8 } } }
PUT    /api/v1/cuelists/Show/cues/3   { "changes": [ { "fixtures": [1], "values": { "dimmer": 0 } } ] }                       (adds to the content)
PUT    /api/v1/cuelists/Show/cues/3   { "content": "replace", "changes": [ { "fixtures": [1], "values": { "dimmer": 0 } } ] } (content = exactly this)
PUT    /api/v1/cuelists/Show/cues/3   { "number": 2.5 }                                                                          (renumber)
DELETE /api/v1/cuelists/Show/cues/3
```

Only what you send changes. A change to a cue that is running takes effect with its next *Go*.

### Variables and effects

```
POST /api/v1/variables  { "name": "Warm white", "type": "color", "values": { "hex": "#ffb060" } }
PUT  /api/v1/variables/Warm white   { "values": { "hex": "#ffa040" } }      -> every cue that uses it is warmer now
POST /api/v1/effects    { "script": "strobe", "name": "Blink", "params": { "rate_hz": 8 } }
POST /api/v1/effects/Blink/assign   { "fixtures": [2, 3] }                  -> it runs now
POST /api/v1/effects/release        { "fixtures": [2, 3] }                  -> stop it
```

`GET /api/v1/effect-scripts` lists the effect types with their settings (`variables`: name, kind, limits, default, labels in both languages).

### Write your own effect type

```
POST /api/v1/effect-scripts/check   { "text": "…" }                  -> { "ok": false, "line": 3, "message": "…" }
PUT  /api/v1/effect-scripts/my_wave { "text": "…", "overwrite": true }
POST /api/v1/effects                { "script": "my_wave" }
```

A script is saved only when it compiles and runs. The language is documented in the *Effect Studio* guide.

### Patch fixtures

```
GET  /api/v1/fixture-types?q=par
POST /api/v1/fixtures  { "type": "Generic RGBW LED Par", "quantity": 4, "name": "Par", "universe": 1, "address": 11, "group": "Wash" }
```

```json
{ "created": [ { "fid": 4, "name": "Par 1", "universe": 1, "start_channel": 11, "end_channel": 14, … },
               { "fid": 5, "name": "Par 2", "universe": 1, "start_channel": 15, … }, … ] }
```

Addresses that overlap other fixtures are refused (`409 address_conflict`); `"allow_overlap": true` patches anyway.

### The programmer

```
GET  /api/v1/programmer
PUT  /api/v1/selection            { "group": "Wash" }
PUT  /api/v1/programmer/values    { "values": { "dimmer": 100, "color": [255, 0, 0] } }       (without fixtures: the selection)
POST /api/v1/programmer/variables { "variable": "Warm white" }
POST /api/v1/programmer/clear     { "fixtures": [2] }          forget their values (the output stays)
POST /api/v1/programmer/clear     { "all": true }              Clear Clear: every fixture dark, effects end
```

Values set this way behave like the faders of the programmer window: the output changes at once, they count as touched, and the next *Store Cue* takes them.

### Relative values (nudge instead of set)

```
curl -X PUT -H "Authorization: Bearer oc_xxxxxxxx" -H "Content-Type: application/json" \
  -d '{"group": "Front", "mode": "relative", "values": {"pan": 2.5, "dimmer": -10}}' \
  http://127.0.0.1:8000/api/v1/programmer/values
```

With `"mode": "relative"` the numbers are **changes in percent points** (−100 to 100); every fixture starts from its own value and is limited at 0 / 100 %. Colours and raw channels exist only as absolute values. For fast sequences of changes (knobs, joystick) the WebSocket (section 10) is better.

### Showfiles

```
POST /api/v1/showfile/save-as  { "name": "Concert" }
POST /api/v1/showfile/load     { "name": "Concert", "force": false }
POST /api/v1/showfile/new      { "force": true }
```

Without `force`, *load* and *new* stop with `409 unsaved_changes` when the running show has unsaved changes. `GET /api/v1/showfile` tells whether it has.

### Buttons, faders and toggles of the console

```
GET /api/v1/widgets
POST /api/v1/widgets/b1/press
PUT  /api/v1/widgets/f1/value   { "value": 70 }
PUT  /api/v1/widgets/t1/state   { "on": true }
```

`GET /widgets` lists the panels with their `id`, `label`, command and the current value (faders) or state (toggles). Pressing, moving or switching runs the command that is set up in the panel – the same one an operator triggers – and the panels on every device follow (a pressed button pulses, faders and toggles with the same command move along). A fader value is limited to its minimum / maximum. A panel without a command answers `409 no_command` (a toggle without commands just switches). The panels are those of the **console's** layout; remote devices have layouts of their own.

### Outputs and layouts

```
PUT  /api/v1/system   { "artnet": { "ip": "192.168.1.255" }, "sacn": { "enabled": false } }
POST /api/v1/layouts/Concert.json/load
POST /api/v1/fixture-types   (raw .gdtf file, header X-Filename: my_fixture.gdtf)
```

### Upload a medium

```
curl -X POST -H "Authorization: Bearer oc_xxxxxxxx" -H "Content-Type: application/octet-stream" \
     -H "X-Filename: intro.mp4" --data-binary @intro.mp4 http://127.0.0.1:8000/api/v1/media
```

### Live events (stream)

```
curl -N -H "Authorization: Bearer oc_xxxxxxxx" "http://127.0.0.1:8000/api/v1/events?events=cue,blackout,command"
```

```
event: hello
data: {"app": "OpenCue", "events": ["blackout", "cue", "command"]}

event: cue
data: {"cuelists": [{"id": "7e5d…", "name": "Show", "active_cue": {"id": "700…", "number": 2, "name": "Blue", …}}]}

event: command
data: {"command": "Fixture 1 At 10", "success": true, "message": "OK: …", "time": "21:14:03"}
```

The connection stays open. First come `hello` and one message per kind with the **current state**, then every change. Kinds: `cue` (active cue of a list changed), `cuelists` (lists / cues were added, removed, renamed), `blackout`, `master`, `timecode` (started, stopped, speed), `selection`, `effects`, `fixtures`, `variables`, `show` (name / unsaved changes), `command` (a console command ran, from anywhere), `audio` (source opened / closed, tempo, signal present). On request only (`?events=beat,hit`): `beat` (every beat, with the tempo) and `hit` (every bass drum / snare / hi-hat hit: `{"drum": "kick", "strength": 0.9}`). `?events=` limits the stream. Changes are noticed within about 0.1 s. A comment line (`: keep-alive`) arrives every 15 s; at most 20 streams run at once. Needs the permission *Status*.

In a browser, `EventSource` cannot send headers: use `?access_token=<token>` instead, or `fetch()` with a header and read the stream. The token then appears in the address, so give such a page its own token with only *Status*.

---

## 7. Small programs

Python, with the library `requests` (any HTTP library works):

```python
import requests

BASE = "http://127.0.0.1:8000/api/v1"
HEAD = {"Authorization": "Bearer oc_xxxxxxxx"}

# What is the colour of every fixture?
for fx in requests.get(f"{BASE}/fixtures/state", headers=HEAD).json()["fixtures"]:
    color = fx["state"].get("color")
    print(fx["fid"], fx["name"], color["hex"] if color else "-")

# Dim the front lights, then start the next cue
requests.post(f"{BASE}/command", headers=HEAD, json={"command": "Fixture 1 At 30"})
requests.post(f"{BASE}/cuelists/Show/go", headers=HEAD)
```

Build a small show (needs the edit permissions):

```python
requests.post(f"{BASE}/fixtures", headers=HEAD, json={"type": "Generic RGBW LED Par", "quantity": 4, "name": "Par", "address": 1, "group": "Wash"})
requests.post(f"{BASE}/variables", headers=HEAD, json={"name": "Warm", "type": "color", "values": {"hex": "#ffb060"}})
requests.post(f"{BASE}/cuelists", headers=HEAD, json={"name": "Show"})
requests.post(f"{BASE}/cuelists/Show/cues", headers=HEAD, json={
    "number": 1, "name": "Warm", "fade": 3,
    "changes": [{"group": "Wash", "values": {"dimmer": 80}, "variables": {"color": "Warm"}}]})
requests.post(f"{BASE}/showfile/save-as", headers=HEAD, json={"name": "From the API"})
```

A web page that shows the active cue live (JavaScript in the browser; the page may come from any address, see section 8):

```javascript
const res = await fetch("http://192.168.1.20:8000/api/v1/events?events=cue", { headers: { Authorization: "Bearer oc_xxxxxxxx" } });
const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
for (;;) {
  const { value, done } = await reader.read();
  if (done) break;
  console.log(value);          // "event: cue\ndata: {...}\n\n"
}
```

---

## 8. Other devices and security

- **From another computer or tablet** the API is reachable as soon as **Allow access over HTTP** (Settings → Remote) is switched on. Use the address of the console (shown on that page) instead of `127.0.0.1`, for example `http://192.168.1.20:8000/api/v1/status`. With remote access off the port is closed to the network. The **token replaces the password** there – no login is needed.
- Tokens grant real control over the lights. Give each program its **own token with only the permissions it needs** and delete tokens you no longer use.
- The **edit permissions are off by default** and can change or destroy show data: *Patch*, *Showfiles* and *Console commands* are marked **critical**. *Load* and *New* refuse to throw away unsaved changes without `force`.
- The traffic is plain HTTP inside your network. Do not expose the port to the internet.
- **Web pages on other addresses** (your own dashboard, a web tool in the browser) may call the API directly: the answers carry the headers for cross-origin access (CORS), and the browser's preflight request (`OPTIONS`, which cannot carry a token) is answered. The page still needs a token in the `Authorization` header, and the page must keep the token to itself (do not put a powerful token into a public web page). Switch it off in *Settings → API → Allow web pages on other addresses* if you do not need it; then browsers block such pages again (programs and scripts are not affected).
- The API changes the show **in memory**, like the window. Nothing is stored on disk until the show is saved (`POST /showfile/save`, or *Save* in the window).

---

## 9. When something does not work

| Problem | Check |
|---|---|
| `401 unauthorized` | Header spelled `Authorization: Bearer oc_…` with the complete token? Token deleted or regenerated? |
| `403 forbidden` | The token lacks this permission – open the token in *Settings → API* and switch it on (the message names it). |
| `403 api_disabled` | The main switch in *Settings → API* is off. |
| `403 remote access disabled` | You call from another device while *Allow access over HTTP* is off. |
| `404 not_found` | Check the fixture number, the cue list name (exactly) and the cue number. |
| `409 duplicate` | The name is taken (upper / lower case does not matter). Choose another name or change the existing one with `PUT`. |
| `409 cue_exists` | A cue with this number is in the list: `on_conflict` or `PUT` it. |
| `409 unsaved_changes` | Save first (`POST /showfile/save`) or send `force: true`. |
| `409 no_command` / `409 wrong_type` | A panel has no command set / you pressed a fader, moved a button … (see `GET /widgets` for the type). |
| `422` | A field that does not exist (a typo?) or a wrong type – the message names the field. |
| `422 invalid_script` | The script has an error – the message names the line. `POST /effect-scripts/check` tests without saving. |
| `200` but `"success": false` | The command was rejected – read `message`. |
| `429` | Too many wrong tokens from this address. Wait for `Retry-After` seconds. |
| Browser page: "blocked by CORS" | *Settings → API → Allow web pages on other addresses* is off, or the request has no token (the error answer of the API carries the headers, so the real reason is visible). |
| No answer at all | Is OpenCue running, and is the port right (Settings → Remote shows it)? |

---

## 10. Hardware and fast control: the WebSocket stream

For **hardware** (ESP32, Arduino, Raspberry Pi, a home-built desk) and every application that sends or receives **many small values quickly**, there is a **WebSocket** next to the HTTP routes: `ws://<console>:8000/api/v1/ws`. One connection stays open and both sides send small **JSON messages** (text frames) – without the cost of a new HTTP request per value. It needs no extra permission: every message needs **the same permission as the matching HTTP route** (table below). With the preset *Operate* everything works except raw DMX.

### Connect and log in

The token can be sent in one of three ways (microcontrollers find the address the easiest):

1. in the address: `ws://opencue.local:8000/api/v1/ws?access_token=oc_xxxxxxxx`
2. in the header: `Authorization: Bearer oc_xxxxxxxx` (or `X-API-Key`)
3. as the **first message** within 5 s: `{"op": "auth", "token": "oc_xxxxxxxx"}`

Then OpenCue sends `{"op": "hello", ...}` with the allowed permissions, operations, topics and limits. Errors close the connection with a code: `4401` (token missing / wrong), `4403` (API off, this PC only, remote access off, token switched off), `4429` (too many failed attempts / too many connections). The same rules as for HTTP apply: *REST API on*, *Reachable from*, lock-out after failed attempts. At most 10 connections are open at the same time.

Every message is a JSON object with `"op"`. An optional **`"id"`** (any number or text) comes back in the answer: `{"op": "ack", "id": 7, ...}` on success, `{"op": "error", "id": 7, "code": "...", "message": "..."}` on an error. Without an `id` only errors are answered. A faulty message never ends the connection.

### Messages from the hardware

| `op` | Permission | What it does |
|---|---|---|
| `joystick` | Programmer | A joystick – see below |
| `set` | Programmer | Set values, **absolute** or **relative** – see below |
| `select` | Programmer | Change the selection: `{"op":"select","mode":"set","fixtures":[1,2]}` (`mode`: `set`, `add`, `remove`, `clear`) |
| `cmd` | Commands | Console command: `{"op":"cmd","line":"Cuelist Main Go"}` (answer: `success`, `message`) |
| `cue` | Cues | `{"op":"cue","list":"Main","action":"go"}`; `action`: `go` (with `"cue": 5` it jumps), `back`, `pause`, `resume`, `stop`, `fader` (with `"value"`) |
| `master`, `blackout` | Blackout / Master | `{"op":"master","value":70}`, `{"op":"blackout","on":true}` |
| `dmx` | DMX channels | `{"op":"dmx","universe":1,"channels":{"1":255,"2":0}}` – raw channel values like `PUT /dmx/{universe}` |
| `tap` | Audio | Tap the tempo (a button on the ESP32) |
| `timecode` | Timecode | Control the timecode: `{"op":"timecode","action":"play"}` (also `pause`, `stop`, `seek`, `rate`) – or `{"op":"timecode","action":"sync","position":12345,"running":true}`: OpenCue **follows** an outside clock (position in ms or `"0:12.345"`; deviations under 60 ms are not corrected so the clock does not jitter; a jump moves it without firing cues) |
| `audio_in` | Audio | Audio **in** – see below |
| `subscribe`, `unsubscribe` | per topic | **Subscribe** to live values – see below |
| `ping` | – | Answer `{"op":"pong","t":<your t>,"server_ms":...}`: measure the round trip, compare clocks |

Targets (`set`, `joystick`, `select`) are named like in the HTTP routes: `"fixtures": [1, 2, "Front 3"]`, `"fixture": 5`, `"group": "Front"` and / or `"selection": true` (the selection of the console). Without any of them the selection is used.

### Setting values: absolute and relative

```json
{"op": "set", "fixtures": [1, 2], "values": {"dimmer": 80, "pan": 25, "color": "#ff8800"}}
{"op": "set", "group": "Front", "mode": "relative", "values": {"pan": 2.5, "dimmer": -10}}
```

- **absolute** (default): the values are the new values – percent 0–100, colour as `#rrggbb` / `[r,g,b]`, raw channels as `ch<N>` (0–255).
- **relative** (`"mode": "relative"`): the numbers are **changes in percent points** (−100 to 100); every fixture starts from **its own** value and is limited at 0 / 100 %. That is right for rotary knobs and "a bit further" buttons. Colours and raw channels cannot be relative.

HTTP has the same: `PUT /programmer/values` with `"mode": "relative"`. Pan and tilt are set with the full **16 bit resolution** (coarse and fine).

### Joystick

```json
{"op": "joystick", "selection": true, "x": 0.35, "y": -0.8}
```

`x` and `y` range from −1 to 1 (right / up positive). By default it drives pan (`x`) and tilt (`y`) of the selected fixtures; `"axes": {"x": "pan", "y": "zoom"}` assigns any attribute (`dimmer`, `zoom`, `focus`, `strobe`, `gobo`, `prism` ...). Two modes (`"mode"`):

- **`rate`** (default, **relative**): the deflection sets the **speed**, not the position – like the joystick in the programmer. Small deflections are very precise (close to the centre about 1° per second), large ones fast (at the very outside the whole range passes in a few seconds); the curve is exponential. OpenCue integrates the movement **itself at 40 Hz** from the last reported deflection – the device only has to send changes and the current value every 20–50 ms; WLAN jitter does not make the movement jerky. Several selected fixtures move by the same amount from **their** start value; at the end of the range they stop. With `x = y = 0` (or inside the dead zone) the stick is released: **the fixtures stay where they are**.
- **`position`** (**absolute**): the deflection is the position – `x = −1` is pan 0 %, `x = 1` pan 100 %. Not useful for a spring-loaded stick, but for an encoder or a slider.

More fields: `stick` (a name when a device has several sticks; default `main`, up to 4), `speed` (factor 0.05–4 for the speed, default 1), `deadzone` (0–0.5, default 0.04), `timeout_ms` (100–5000, default 500), `invert_y`, `release: true` (let go at once). The targets are fixed when the stick is first touched and kept until it is released.

**Dead-man switch:** if no message arrives for longer than `timeout_ms` (cable pulled, WLAN gone, device hangs) the stick stops and OpenCue reports `{"op":"joystick","stick":"main","state":"timeout"}`. If the connection drops, all fixtures stay where they are.

### Subscribing to live values

`{"op":"subscribe","topic":"<topic>","hz":30}` – `hz` is the highest rate (1–60, default 30). OpenCue only sends what **changed**. `unsubscribe` with `"topic"` ends the subscription.

| `topic` | Permission | Messages |
|---|---|---|
| `audio` | Status | `{"op":"audio","t":ms,"running":true,"v":{"a_level":0.62,"a_bass":0.9,"a_bpm":124,...}}` – the audio variables of the audio analysis; `"keys": ["a_level","a_bass"]` limits them |
| `dmx` | DMX | `"universes": [1]` (up to 8): first `{"op":"dmx","universe":1,"full":true,"values":[512 numbers]}`, then only `{"op":"dmx","universe":1,"changes":{"17":255}}` (channel → value) |
| `fixtures` | DMX | `{"op":"fixtures","values":{"3":{"pan":12.5,"tilt":50,"dimmer":100,"color":{...}}}}` – live values per fixture **number**, only the changed ones |
| `timecode` | Status | `{"op":"timecode","ms":83400,"text":"00:01:23.400","running":true,"direction":1,"rate":1}` – while the clock runs with every tick (up to 60 Hz), otherwise only on a change (start, stop, jump, rate) |
| `events` | Status | like `GET /events`: `{"op":"event","event":"cue","data":{...}}`; `"events": ["cue","blackout"]` chooses (default: the standard kinds; `beat` and `hit` only on request). The current state comes first |

### Audio in: a microphone on the ESP32

With the audio source **"Network (API stream)"** OpenCue analyses audio that a device sends – level, bands, kick / snare / hi-hat, tempo and beat then exist as `a_` variables for **effects, cue triggers and the Audio panel** as usual.

1. Open the source: choose *Network (API stream)* in the Audio panel, or `PUT /audio` with `{"device": "network"}`, or do it with the message of step 2 (`"open": true`).
2. `{"op":"audio_in","rate":16000,"open":true}` – announces PCM (`rate` 8000–48000 Hz, **16 bit signed little endian, mono**).
3. Then send **binary frames** (WebSocket binary) with the samples, e.g. 20 ms at a time (640 bytes at 16 kHz). At most 64 KB per frame.

If the source is not open OpenCue answers (at most once a second) with the error `audio_source`. Without data the analysis keeps running on silence.

### Limits and protection

**DMX output always has priority**: it runs in its own thread (slightly higher priority), and the stream is limited – so hardware can never slow the console down. At most 300 messages per second per connection (bursts up to 600) and 1200 in total – more get `rate_limited` and are dropped; text messages up to 8 KB, binary frames up to 64 KB; 10 connections; a joystick changes at most at 40 Hz. A connection that does not log in is closed after 5 s.

### Example: ESP32 with a joystick (Arduino)

```cpp
#include <WiFi.h>
#include <WebSocketsClient.h>          // Bibliothek "WebSockets" von Markus Sattler (arduinoWebSockets)

const char* WIFI_SSID = "MeinWLAN";
const char* WIFI_PASS = "geheim";
const char* TOKEN     = "oc_xxxxxxxx";      // Token mit "Programmer" (write.programmer)
const int PIN_X = 34, PIN_Y = 35;           // die beiden Achsen des Joysticks (ADC)

WebSocketsClient ws;
int centerX = 2048, centerY = 2048;

float norm(int raw, int center) {           // 0..4095 -> -1..1
  float f = (raw - center) / 2048.0f;
  return f < -1 ? -1 : (f > 1 ? 1 : f);
}

void onEvent(WStype_t type, uint8_t* payload, size_t length) {
  if (type == WStype_CONNECTED) Serial.println("OpenCue verbunden");
  if (type == WStype_TEXT)      Serial.printf("%s\n", payload);       // hello, Fehler, Rueckmeldungen
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) delay(200);
  delay(300);
  centerX = analogRead(PIN_X);              // Ruhelage beim Start merken
  centerY = analogRead(PIN_Y);
  String path = String("/api/v1/ws?access_token=") + TOKEN;
  ws.begin("opencue.local", 8000, path);    // oder die IP-Adresse der Konsole
  ws.onEvent(onEvent);
  ws.setReconnectInterval(2000);
  ws.enableHeartbeat(15000, 3000, 2);
}

void loop() {
  ws.loop();
  static uint32_t last = 0;
  if (ws.isConnected() && millis() - last >= 20) {      // 50 Mal pro Sekunde
    last = millis();
    float x = norm(analogRead(PIN_X), centerX);
    float y = -norm(analogRead(PIN_Y), centerY);        // nach oben = Tilt mehr
    char msg[128];
    snprintf(msg, sizeof msg, "{\"op\":\"joystick\",\"selection\":true,\"x\":%.3f,\"y\":%.3f}", x, y);
    ws.sendTXT(msg);
  }
}
```

The device keeps sending `x = 0, y = 0` at rest – that does no harm (the stick counts as released). The selection on the console decides what moves; with `"fixtures": [1, 2]` or `"group"` instead of `"selection": true` the target is fixed.

### Example: Python

```python
import asyncio, json, websockets            # pip install websockets

async def main():
    async with websockets.connect("ws://127.0.0.1:8000/api/v1/ws?access_token=oc_xxxxxxxx") as ws:
        print(json.loads(await ws.recv()))                           # hello
        await ws.send(json.dumps({"op": "set", "fixtures": [1, 2], "values": {"dimmer": 80}}))
        await ws.send(json.dumps({"op": "subscribe", "topic": "audio", "hz": 30, "keys": ["a_level", "a_bass"]}))
        async for text in ws:
            frame = json.loads(text)
            if frame["op"] == "audio":
                print(frame["v"])

asyncio.run(main())
```

A reference of all messages is also on the page `/api/v1/docs`.

---

## 11. Status views: images and web pages for simple devices

For devices that can only **fetch a picture** or show a **plain page** – an ESP32 with a display, an old tablet as a wall display, a browser tab on the foyer monitor – there are **status views**. They are **read-only** (no operation), need **no library** on the device and OpenCue renders them itself: the content is the same whether as an image or as a page.

| View | Shows | Permission |
|---|---|---|
| `status` | show, blackout, master, timecode, the active cue of every list, tempo | Status |
| `timecode` | the clock, big, "running / stopped" | Status |
| `dmx` | the 512 channels of a universe as a grid (`?universe=1`), brightness = value | DMX |
| `cue` | the active cue of a list (`?list=Main`) and the next one | Status |
| `audio` | level, the eight bands, tempo | Status |

Every view comes in several forms (`GET /api/v1/views/<name>…`):

| Address | Result |
|---|---|
| `/views/status` | **web page** that refreshes itself (`?refresh=2` seconds); without JavaScript by meta refresh |
| `/views/status.png` | **PNG image** (`?w=320&h=240&theme=dark`; size 64×48 to 800×600; `theme`: `dark` or `light`) |
| `/views/status.bmp` | 24 bit **BMP** – any small decoder understands it |
| `/views/status.rgb565` | **raw pixels**, 16 bit each (5-6-5, high byte first); the size is in the headers `X-Width` / `X-Height`: hand it straight to a TFT (no decoder needed) |
| `/views/status.json` | the display model (parts: title, rows, bars, grid) – for those who want to draw themselves |
| `/views` | list of all views with their parameters |

Log in as usual. A browser or a device that cannot send a header appends the token (`access_token`, `token` works too; spaces and quotes taken along when copying do not matter). The message says whether the token is **missing** or **invalid / deleted**; the console logs every rejected login. If the first load of `opencue.local` hangs (Windows sometimes resolves `.local` names slowly the first time), use the **IP address** – it is listed in *Settings → REST API* (to copy): `…/views/status?access_token=oc_xxxxxxxx` (the token is then part of the address – create a separate token **with only "Status" and "DMX"** for that). The switch **Status views** in *Settings → REST API* turns everything off (answer `403 views_disabled`).

**Colour:** `?color=green` (or `amber`, `red`, `blue`, `cyan`, `white`, `magenta`, `violet`, `orange`, `yellow`, or `#rrggbb`) changes the highlight colour; the DMX monitor is **green** by default.

**Errors are visible:** if something is wrong (wrong token, views off, no permission) an **image** (`.png` / `.bmp` / `.rgb565`) comes back with the right status code (401, 403 ...) **as a picture with the message** – a display simply shows it ("TOKEN MISSING OR WRONG", "STATUS VIEWS ARE OFF" ...); the **web page** shows a page with the message and reloads every 5 s. If OpenCue cannot be reached after the page was opened, the page shows **"No connection to OpenCue"** at the top and dims the last picture until it works again. `.json` keeps the JSON error message.

**DMX output always has priority:** pictures are recomputed at most every 0.4 s per view and size (many devices share one picture), in a background thread, and never more than four at the same time. A 320×240 picture costs about 6 ms. The DMX output thread additionally runs at a slightly higher priority.

### ESP32 with a TFT: a picture every two seconds

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <TFT_eSPI.h>                       // 320 x 240 display

TFT_eSPI tft;
uint16_t frame[320 * 240];                  // 150 KB: on an ESP32 without PSRAM ask for 160 x 120 instead

void loop() {
  HTTPClient http;
  http.begin("http://opencue.local:8000/api/v1/views/status.rgb565?w=320&h=240&access_token=oc_xxxxxxxx");
  if (http.GET() == 200) {
    WiFiClient* s = http.getStreamPtr();
    s->readBytes((uint8_t*)frame, sizeof frame);
    tft.setSwapBytes(true);
    tft.pushImage(0, 0, 320, 240, frame);
  }
  http.end();
  delay(2000);
}
```

For devices with little memory: choose a smaller size (`w=160&h=120`) or hand the stream to the display line by line.
