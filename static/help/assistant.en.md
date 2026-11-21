# AI assistant

The **AI assistant** is a chat with a language model that runs on **your own computer** (or another one in your network) through **Ollama**. Nothing is sent to the internet: OpenCue only talks to the server address you enter. The AI writes every answer **itself** - OpenCue does not make up answer texts.

> **Status today:** the **Chat** and the **Work** mode work. Work can **read** the show (fixtures with all details, groups, cue lists, effects, variables), **change fixtures** (brightness, colour, pan / tilt, zoom ... - after asking you) and has a calculator, random numbers and the time. The **Guide** explains the program from the manuals (without inventing anything) and offers buttons that open dialogs (see section 7).

---

## 1. Set up

1. Install **Ollama** (ollama.com) on this or another computer and download a model once, e.g. `ollama pull qwen2.5-coder:3b`. After that no internet is needed.
2. In OpenCue open **Settings -> AI assistant** and switch on the **master switch *Enable the AI assistant*** at the top - while it is off the rest of the page is locked.
3. Under **Connection** enter the **server address** (default `http://127.0.0.1:11434`) and click **Test connection**.
4. Choose the **default model** and click **Save** at the bottom right (the dialog stays open).
5. Use **Add Panel** to add the **AI Assistant** panel.

The page is organised in **Connection**, **Behaviour** (mode of new chats, chat names, function list), **Permissions** and **Advanced**. Under **Advanced** (collapsed) you find context size, temperature and waiting time. The first answer after a model is loaded takes longer - the waiting time is generous.
Under **Advanced** every value shows a **"Recommended: ..."**; the button **Set recommended values** (at the bottom of the settings) puts context (16384), temperature, longest answer, waiting time, chat names and the function list back. Server address, model and permissions stay untouched.

---

## 2. Writing

At the bottom is the input line: **[mode button] [text field] [microphone] [send]**. The microphone button (dictation, only at the console) is described under *Dictating* below.

- **Enter** sends, **Shift + Enter** starts a new line.
- While the AI works you see jumping dots, then the text word by word. The **send** button turns into a red **stop** button.
- Under every answer is a compact line: the **mode**, the total time of the question, tokens per second and the model.
- **Thinking steps:** models such as `qwen3` or `deepseek-r1` think first and answer afterwards. The thoughts sit in a collapsible block **above** the answer: while the model thinks it is open and grows; when the answer starts it folds up ("Thought for 12 s"), a click opens it again. Whether a model thinks is up to the model itself (there is no switch for it). Thinking counts towards the *Longest answer* - OpenCue adds 2500 tokens of room for it.
- **Scrolling:** when the history is at the very bottom it follows along while the AI writes. If you scroll up, **your position stays** - even while more is written below. The round down-arrow button at the bottom right of the history takes you back to the end (it lights up while something is still running below). When you send a message you jump down by yourself.
- Every message has a **copy** button when you hover over it; the text can also be selected.
- In Chat mode the AI gets the **whole chat so far** with every question. If it gets too long for the context window, the oldest messages drop out (everything stays saved). In Work mode it gets the current question with everything that happened for it, plus a **short summary** of the earlier questions. Results appear in it only for calculations ("and half of that?"); show data, the time and random numbers are fetched anew every time (otherwise small models copy old text answers and calculate from memory).

### Dictating (speech to text)

Click the **microphone** next to the text field: the field is replaced by an animation of moving **bars** that follow your voice, with the recording time. **Tick** = done, the recording is written down and the text is put into the field (it is **not** sent - read it, correct it, press send); a text already in the field is kept and the new words are added. **Cross** or `Esc` = discard. After 2 minutes the recording ends by itself.

- The **language** is the language of the interface (any of the six languages) - there is no separate setting. Technical words (cue, dimmer, gobo, blackout ...) are known to the recogniser.
- Recording uses the microphone of the **console** (so the button only appears there). Everything runs on this computer with *Whisper* (faster-whisper).
- The **speech model** is loaded once at the first dictation (internet needed, a progress bar shows it); afterwards dictation works offline. *Settings -> Dictation* offers **Fast** (Whisper base, about 145 MB) and **Accurate** (Whisper small, about 484 MB, better for German, takes a little longer), a **Load now** button, and the **microphone for dictation**. Writing down takes about as long as the recording or less, depending on the computer.
- Dictation has nothing to do with the **wake word** (*Settings -> Wake word*) - they are separate functions, each with its own microphone. An overview of all inputs and outputs in use is under *Settings -> Inputs & outputs*.

---

## 3. The three modes

The square **mode button** at the left of the text field opens a small menu:

| Mode | What for | Status |
|---|---|---|
| **Chat** | Normal conversation with the AI. | ready |
| **Guide** | Explains the program and shows you where things are (buttons open dialogs). | ready |
| **Work** | The AI works with functions: calculate, read the show, set fixtures ... | in progress (reading and changing fixtures are done) |

The mode belongs to the **chat** and can be switched at any time in the middle of a conversation. Which mode **new chats** start in is set under *Settings -> AI assistant -> Mode of new chats*; every chat also remembers its own model and mode (also after a restart).

---

## 4. Work: the AI with functions

In **Work** mode the AI works like an **agent**: it calls **functions**, reads the results, continues with them and writes the final answer itself. When it has to calculate it asks the **calculator** instead of guessing in its head; when it needs something about the show it **reads** it; when it has to set something it calls the matching **write function** - depending on your **permissions** (section 5) only after asking you. These functions exist so far:

| Collection | Function | What it does |
|---|---|---|
| Read (`read_functions`) | `show_overview` | Show name, blackout, master and only the **counts** (fixtures, groups, cue lists, cues, effects, variables), active cue list |
| Read | `list_fixtures` | The fixtures: number, name, type, DMX address, group, current brightness (filters: group, name) |
| Read | `read_fixtures` | The **details** of fixtures: model, manufacturer, mode, DMX address, group and **all** current values (brightness in %, colour, pan / tilt, zoom ... and every channel as a DMX value). You say which: `all`, a range such as `1-5`, numbers such as `1, 3, 7` (also `1-3, 7`) or the name of a group (also "group Front"). If a number you name does not exist (`6, 11` with 10 fixtures), the existing ones come back and a note names the missing one - so the AI can answer correctly |
| Read | `list_groups` | The groups with the numbers of their fixtures |
| Read | `read_dmx` | The **DMX output** of a universe: only the channels that are not 0 (`universe`, `first`, `last`) |
| Read | `list_cuelists` | The cue lists with number of cues, active cue and fader |
| Library (`library_functions`) | `list_effects` | The effects with their settings - and whether they are running and on which fixtures |
| Library | `list_variables` | The variables (name, kind such as colour or position, group, value) |
| Change (`control_functions`) | `set_fixtures` | **Changes** values of fixtures: `brightness` (0-100 %), `color` (a name such as `red`, `#FF8000` or `255 128 0`), `pan` / `tilt` (degrees or `50%`), `zoom`, `focus`, `gobo`, `prism`, `strobe` (each 0-100 %) and with `channels` any other channel by its name in percent (`{"Frost": 50}`). Chosen like in `read_fixtures`; what you do not name stays as it is. It goes through the same checks as the **command line** (the command appears in its history). The **selection** in the interface stays untouched: the values go to exactly these fixtures (visible in the fixture list, the programmer and the DMX values) without selecting them - you can keep working with other fixtures in the meantime |
| Change | `set_blackout` | **Blackout** on or off (`enabled`): everything dark, the values are kept |
| Change | `set_master` | The **master** (overall brightness) in percent |
| Change | `timecode_control` | The **timecode** clock: `play`, `pause`, `stop`, `seek` (with `position`), `rate` (with `rate`) |
| Cue lists (`cuelist_functions`) | `read_cuelist` | **One** cue list with all cues: number, name, trigger, times, active cue, whether it plays |
| Cue lists | `control_cuelist` | Plays a cue list: `go` (next cue, or with `cue` a jump), `back`, `pause`, `resume`, `stop` |
| Cue lists | `set_cuelist_fader` | The **fader** (mix) of a cue list in percent |
| Looks (`look_functions`) | `apply_variable` | Puts a **variable** (saved colour, position ...) on fixtures |
| Looks | `apply_effect` | Starts an **effect** on fixtures |
| Looks | `stop_effects` | Stops all effects on fixtures (the values stay) |
| Looks | `release_fixtures` | Hands fixtures back to **manual**: releases variables and effects; optionally only `dimmer`, `color`, `position`, `zoom`, `focus`, `gobo` |
| Read | `read_selection` | Which fixtures are **selected** in the interface |
| Library | `list_showfiles` | The saved **showfiles** and which one is loaded |
| Selection & groups (`group_functions`) | `select_fixtures` | **Selects** fixtures in the interface (or `none` clears the selection) |
| Selection & groups | `create_group` | Creates a **group** from fixtures (`name`, `fixtures`); the user's selection stays |
| Selection & groups | `delete_group` | **Critical:** deletes a group (the fixtures stay) |
| Cue lists | `store_cue` | **Stores** the programmer values as a new cue (`cuelist`, `cue`, optional `name`, `if_exists` = `merge` / `overwrite`) |
| Cue lists | `delete_cue` | **Critical:** deletes a cue of a list |
| Patch (`patch_functions`) | `list_fixture_types` | Looks up types in the **fixture library** (name, manufacturer, modes with channel count) |
| Patch | `add_fixtures` | **Patches** new fixtures: type, quantity, universe, first address, name, group; overlapping addresses are refused |
| Patch | `change_fixture` | Changes **one** fixture: name, address, universe, group |
| Patch | `change_group` | Renames a group and / or sets its members |
| Patch | `delete_fixtures` | **Critical:** deletes fixtures from the show |
| Showfiles (`showfile_functions`) | `save_show`, `save_show_as` | **Saves** the show (under its known name / under a new one; an existing name is only replaced with `overwrite`) |
| Showfiles | `rename_showfile` | Renames a saved showfile |
| Showfiles | `load_show`, `new_show` | **Critical:** loads another show / starts a new one and replaces the running one. Unsaved changes are refused - only with your agreement (`discard_changes`) it works anyway |
| Showfiles | `delete_showfile` | **Critical:** deletes a saved showfile (the loaded one only with `force`) |
| Variables (`variable_functions`) | `create_variable`, `change_variable` | Creates / changes a **variable**: colour (`color`), brightness / zoom / focus / gobo (`level`), position (`pan`, `tilt`); everything that uses it follows at once |
| Variables | `delete_variable` | **Critical:** deletes a variable |
| Effects (`effect_functions`) | `list_effect_types` | The **effect types** with their category and their settings with limits |
| Effects | `create_effect`, `change_effect` | Creates an **effect** from a type with settings (`settings`) / changes it |
| Effects | `delete_effect` | **Critical:** deletes an effect (it stops everywhere) |
| Edit cues (`cue_edit_functions`) | `set_cue` | Changes the **properties** of a cue: name, fade, delay, trigger (`go` / `follow` / `timecode` / `audio` / `midi`), timecode, command, move-in-black, new number |
| Edit cues | `duplicate_cue`, `update_cue` | Copies a cue / takes the programmer values into the **active cue** (like the Update button) |
| Manage cue lists (`cuelist_manage_functions`) | `create_cuelist`, `rename_cuelist`, `duplicate_cuelist` | Creates a cue list / renames it / copies it with all its cues |
| Manage cue lists | `delete_cuelist` | **Critical:** deletes a cue list with all its cues |
| Command (`command_functions`) | `command_help` | The **syntax of the command line** from the guide (quick reference or a topic: `selection`, `values`, `color`, `channels`, `effects`, `combine`, `clear`, `cuelists`, `cues`) - the AI looks it up before it uses `run_command` |
| Command | `run_command` | **Critical:** runs **any command of the command line** (also deleting and storing cues) - the AI asks you until you choose "Always allow" |
| Helpers (`helper_functions`) | `calculate` | Calculates an expression exactly: `+ - * / // % ** ^`, parentheses, `sqrt`, `sin`, `cos`, `tan`, `ln`, `log`, `exp`, `abs`, `round`, `floor`, `ceil`, `min`, `max`, `pi`, `e` ... (decimals with a dot) |
| Helpers | `random_number` | Random numbers or dice rolls (`min`, `max`, `count`, whole numbers or decimals) |
| Helpers | `current_time` | Time, date and weekday of the computer |

The AI **does not have to use a function**: for a greeting, thanks or a general question it simply answers in words. Only calculations, random numbers, date and time, show data and changes to the show go through a function - every time anew, also for a follow-up.

Every call appears in the chat in a **function block** under your question: collapsed you see the count, names, status and time; a click shows each function with its **input and result**. If a call does not work (e.g. an invalid calculation or a fixture number that does not exist), the AI gets to read the error - with what does exist - and tries again with corrected values. Every value the AI gives for `set_fixtures` is checked strictly first (number ranges, colour names, channel names); text from the AI never becomes an arbitrary command.

**Calling functions yourself:** You can also trigger any function **by hand** - without the AI saying anything. Type `/` and the name in the text field; suggestions appear while you type (arrow keys, **Tab** or a click accept, **Enter** sends):

- `/read_fixtures {"fixtures":"6-8"}` - the values as JSON, the way the AI writes them.
- `/read_fixtures 6-8` - if the function has exactly one required value, the value alone is enough. `/calculate 17*23` calculates.
- `/set_fixtures fixtures=1-3 brightness=50` - or as `name=value`.
- `/help` lists all functions with their kind and values.

The result appears in the chat already unfolded (input and result as JSON). **No model is asked** and the AI does not see these calls later. Because you act yourself, the **permissions** do not apply here - even a write function runs without a question, also when it is set to "Never allow" for the AI. A mistake (unknown function, wrong way of writing the values) appears as a failed call with an explanation. A message that merely starts with `/` without being a function name (e.g. `/etc/hosts show`) goes to the AI as usual.

**Function list** (*Settings -> AI assistant -> Work mode*):

- **Common functions at once, the rest on demand** (default, recommended): the AI sees the roughly 17 common functions (read and set fixtures, blackout, master, play a cue list, apply variables and effects, command line, calculator ...) right away and a **collection function** for everything else (patching, showfiles, editing variables / effects / cues ...): calling one gives it the functions of that collection from the next step. The prompt stays small - important, because all 56 functions at once are about twice as large as the context window of a small model holds.
- **All at once**: the AI sees all 56 functions right away. Only for large models with a big context window (raise *Settings -> AI assistant -> Advanced -> Context size*).
- **Everything on demand**: the AI sees only the 14 collection functions (`read_functions`, `library_functions`, `cuelist_functions`, `look_functions`, `group_functions`, `command_functions`, `control_functions`, `helper_functions`, `patch_functions`, `showfile_functions`, `variable_functions`, `effect_functions`, `cue_edit_functions`, `cuelist_manage_functions`). The smallest prompt, but small models are slower with it and more often pick the wrong collection.

**Protection against endless loops:** the same call with the same values runs at most **3 times** per question, at most **30** calls in total. After that the AI is stopped and writes its answer from what it has so far (a note appears in the chat).

**Important for the model:** it must be able to **call functions** (e.g. `qwen2.5-coder`, `qwen3`, `llama3.1`). Small models (3B) still occasionally make something up or skip a function; the bigger the model, the more reliable - a model such as `qwen3:4b` or `llama3.1:8b` is worth it if your computer can run it. A plain chat model reports in Work mode that it cannot call functions; in Chat mode it works normally.

---

## 5. Permissions: what the AI may do on its own

Every function belongs to a **kind**, and for every kind you set what the AI may do (*Settings -> AI assistant -> Permissions*):

| Kind | Examples | Default |
|---|---|---|
| **Read functions** | `show_overview`, `list_fixtures`, `read_fixtures`, `list_groups`, `read_dmx`, `list_cuelists`, `read_cuelist`, `read_selection`, `list_effects`, `list_effect_types`, `list_showfiles`, `list_fixture_types`, `list_variables` - they only look at the show | **Always allow** |
| **Write functions** | `set_fixtures`, `set_blackout`, `set_master`, `timecode_control`, `control_cuelist`, `set_cuelist_fader`, `apply_variable`, `apply_effect`, `stop_effects`, `release_fixtures`, `select_fixtures`, `create_group`, `store_cue` and everything for patching, saving, editing variables, effects, cues and cue lists (`add_fixtures`, `save_show`, `create_variable`, `create_effect`, `set_cue`, `create_cuelist` ...) - they change the show | **Ask every time** |
| **Critical functions** | `run_command` (any command of the command line), **all delete functions** (`delete_cue`, `delete_group`, `delete_fixtures`, `delete_variable`, `delete_effect`, `delete_cuelist`, `delete_showfile`) and `load_show` and `new_show` (they replace the running show) | **Ask every time** |
| Helper functions | `calculate`, `random_number`, `current_time`, `command_help` - no effect on the show | always allowed, not adjustable |

For each of the three kinds you choose **Always allow**, **Ask every time** or **Never allow**. Under every choice you see which functions belong to it.

**The question:** when a kind is set to *Ask every time*, the AI pauses before it runs the function and a **card** appears in the function block with the function and its values (and the kind, e.g. "Changes the show"). It has three buttons:

- **Allow once** - the function runs now; next time it asks again.
- **Always allow** - the function runs now and from now on **always without asking** (also in other chats). This applies to exactly this one function and is listed under *Settings -> AI assistant -> Permissions -> Always allowed functions*; **Remove** makes it ask again. This button only exists at the **console computer** (not on tablets / remote devices); it applies to **all** kinds, also critical functions.
- **Don't allow** - the function does not run. The AI is told and tells you that it did not do it.

The question appears on **all** devices that show this chat; *Allow once* and *Don't allow* work from any of them. It also stays after the page is reloaded. If nobody answers, it counts as "no" after 10 minutes; *Stop* ends the question at once.

When a kind is set to **Never allow**, the AI does not even ask: the function does not run, the AI gets the note about the setting and tells you.

---

## 6. Chats

- Every chat is its **own file** (folder `chats` in the data folder) and is kept after quitting; all devices and panels show the same chats.
- **+** creates a new chat; the first one is created by itself when you send.
- **Double click** on the title renames it. Until the AI gives a title, the start of the first question is shown.
- **Automatic titles:** the AI gives the chat a short title itself (2-5 words; one extra, tiny request to the model) - **after the second answer**, so it has more context (the first two questions and answers go into the request). If no second question comes within **one minute**, the chat is named after the first. Until then the start of the first question is shown. A chat you renamed yourself is never renamed. Turn it off: *Settings -> AI assistant -> Model -> Name chats automatically*.
- In the header you choose the **model of this chat** - changeable at any time, the history stays.
- Every row of the **chat list** has a **three-dot menu** (also on right click): **Rename** (right in the list), **Duplicate** (a copy with the whole history, titled "... (copy)") and **Delete chat** (after a confirmation). The symbol before the title shows the chat's mode. **While the AI is writing** in a chat, small dots move behind the title - so you see in which of several chats it is working. When an answer is **finished and the chat is not open**, a **yellow dot** ("new answer") appears there. It disappears as soon as you open the chat - on all devices.
- The **chat list can be collapsed and expanded** (first button in the header); the state is remembered for every panel. In narrow panels the list lies over the history.


## 7. Guide: explains the program and shows you where things are

In **Guide** mode (icon: signpost) the AI answers questions like *"Where are the colour profiles?"*, *"How do I create a cue?"* or *"What is a fixture group?"* - and can offer you **buttons** that open the right dialog.

- **The AI invents nothing.** It gets only a little in its prompt (how the program is laid out) and fetches every detail with the function **`find_help`**: OpenCue picks the matching pieces out of many small text snippets and hands them to the AI with the instruction to **answer only from them**. If nothing matches, the function says so explicitly - the AI is then to admit it does not know instead of guessing.
- **Sources:** the snippets are JSON files in the folder `static/help/guide/snippets/<language>/` (one file per manual page, about 400 per language). Their text is taken **word for word from the manuals**. You may edit or shorten snippets by hand or add `keywords`; `synonyms.json` links words (e.g. "Dateimanager" <-> "file manager").
- **Opening dialogs:** the function **`show_dialog`** puts a button like **"Open: File manager"** under the answer. The AI never clicks itself - **you decide** whether to press it. The click is the same as on the menu item; nothing is saved or deleted. The important dialogs are offered (Settings with their categories, file manager for shows / layouts / stages / effects, fixture library, open / save / import / export show, Add panel, edit mode, shortcuts, language ...); the list is in `static/help/guide/targets.json`.
- **`list_help_topics`** shows what the guide can tell you about.
- The guide changes **nothing** in your show; it has only these three functions (all allowed without asking).
