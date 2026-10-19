# Effect Studio – Guide

An **effect** is a small program that changes light over time: a dimmer that pulses, a color that walks through the rainbow, a moving head that travels a circle. You write effects in the **Effect Studio** (panel *Effect Studio*) in a language that looks like C++ or Arduino: with variables, `if`, `for`, `while` and your own functions. You do not have to be a programmer – the templates under **New...** run right away and are meant to be read and changed.

This guide is also available inside the studio via the **Help** button.

---

## 1. The idea in one minute

- A **script** is a text file (`.fx`). It describes what happens in **one pass**. That pass is called `loop()` and runs **`#RATE` times per second** (1 to 40, default 40).
- In every pass the script computes new **output values**: `dimmer`, or `r`/`g`/`b`, or `pan`/`tilt`. Which ones is decided by the **category** (`#CATEGORY`).
- Between two passes the **output stays where it is**. At 10 passes per second the value therefore changes ten times a second – on purpose, that is how you build stepped effects.
- The script runs **for every fixture on its own**. Each one knows its number (`index`) and the total (`count`); use them to spread waves and chases over several fixtures.
- Variables you create outside `loop()` **keep their value between passes**: counters, states, timers.

```
#NAME Sine
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05

loop() {
  dimmer = 50 + 50 * sin(2 * PI * speed * elapsed);
}
```

That is a complete effect: the dimmer swings between 0 and 100 % with `speed` waves per second.

---

## 2. Command overview (cheat sheet)

All commands at a glance. The chapters after this explain them with examples.

| Area | Commands |
|---|---|
| Header lines | `#NAME`, `#DESCRIPTION`, `#CATEGORY dimmer` / `color` / `position`, `#RATE 1` to `40`, `#VAR name Slider` / `NumberInput` / `ColorPicker` / `Internal ...` |
| Structure | `setup() { }` (once at start), `loop() { }` (`#RATE` times per second) |
| Types | `float` (`double`), `int` (`long`, `short`, `byte`), `bool` (`boolean`), `void`, `const` |
| Assigning | `x = 1;`, `x += 1;` (also `-=` `*=` `/=` `%=`), `x++;`, `x--;` |
| Branching | `if (...) { } else if (...) { } else { }`, `condition ? a : b` |
| Loops | `for (int i = 0; i < n; i++) { }`, `while (...) { }`, `do { } while (...);`, `break;`, `continue;` |
| Functions | `float name(float x) { return x * 2; }`, `void name() { }`, `return value;` |
| Calculating | `+ - * / %`, `== != < <= > >=`, `&& \|\| !` |
| Comments | `// to the end of the line`, `/* over several lines */` |
| Outputs | Dimmer: `dimmer` · Color: `r`, `g`, `b` or `hsv(h, s, v);` · Position: `pan`, `tilt` · Zoom: `zoom` · Focus: `focus` · Gobo: `gobo`, `gobo_spin`, `gobo2`, `gobo2_spin` |
| Time | `t` (shared system time), `elapsed` (since effect start), `dt`, `tick` (`loop_count`), `rate` |
| Fixtures | `index`, `count`, `phase` (= `index / count`), `slots`, `slots2` (number of gobos on wheel 1 and wheel 2) |
| Constants | `PI`, `TWO_PI`, `HALF_PI`, `E`, `true`, `false` |
| Math | `sin` `cos` `tan` `asin` `acos` `atan` `atan2` `sqrt` `pow` `exp` `log` `abs` `sign` `min` `max` `floor` `ceil` `round` `fract` `mod` |
| Helpers | `constrain(x, lo, hi)` `map(x, inMin, inMax, outMin, outMax)` `lerp(a, b, k)` `smoothstep(e0, e1, x)` `radians(d)` `degrees(r)` |
| Waveforms | `saw(x)` `tri(x)` `square(x)` `square(x, duty)` – each 0 to 1 per period |
| Random, color, gobo | `random()` `random(max)` `random(min, max)` · `hsv(h, s, v)` · `slot(n)` `slot(n, wheel)` |

---

## 3. Using the studio

| Area | What it does |
|---|---|
| **Open...** | Dialog with all effects, **favorites first** (search, category, loops per second, origin; bundled effects carry the badge **Default**). The list scrolls. Click a row to open it, the **star** makes an effect a favorite (applies to all devices), the trash can deletes it from the user folder. At the bottom: **Restore default effects**. |
| **New...** | Dialog: first the **category** (dimmer, color, position, zoom, focus, gobo) or **Empty file**, then a **template** (*Empty* is preselected), then the **loops per second**. *Empty file* creates a completely empty editor without header lines. **Create** loads the result into the editor – nothing is saved until you say so. |
| **Save** | Saves to the effect's file. A new effect asks for a file name. A dot next to the name shows unsaved changes. Keyboard: **Ctrl+S** in the text (saves the effect, not the show). |
| **Save as...** | A new file name. If it already exists, the studio asks whether to overwrite it. |
| **Delete** | Deletes the loaded effect (user folder only; you are asked first). Afterwards the editor is empty. If the button is grey, a hint says why (not saved yet, or not in the user folder). |
| **Help** | Opens this guide. The cheat sheet (chapter 2) lists all commands. |
| **Preview** | Shows or hides the preview on the right. |
| **Status bar** | Green = fine. Red = error with line number. On the right: line and column of the caret. |

The editor **colors** keywords, types, numbers, comments, functions, system variables, outputs and your sliders (`#VAR`). **Enter** keeps the indentation of the line (two more spaces after `{`), **Tab** inserts two spaces.

### The preview

The preview runs your script **without any fixtures** while you type – with exactly the loops per second you chose with `#RATE` – and draws the result:

- **Dimmer:** one curve per fixture, 0 to 100 %.
- **Color:** R/G/B as curves and a **color strip** per fixture below.
- **Position:** pan and tilt as curves and the **path** in the pan/tilt field.

Default: **1 fixture, 2 seconds**. At the top you set the number of fixtures (1 to 16) and the duration (1 to 20 s); several fixtures show how `index`, `count` and `phase` offset the waves. Below are **sliders for your `#VAR` parameters** – drag one and the curve follows at once. At a low rate (up to 20 loops per second) the preview draws steps, up to 10 additionally the single points.

If the script has an error, the preview stays as the **last good state, faded**, the error line is marked red and the status bar names the line and the message.

---

## 4. Your first effect

1. **New...** → category **Dimmer** → template **Sine** → **Create**.
2. The preview shows two waves in two seconds (`speed` is 1).
3. Move `speed` to 2: twice as fast. Set 3 fixtures in the preview and move `spread` to 0.33: the waves are offset against each other.
4. Change `0.5 + 0.5 * sin(...)` in the text and watch the curve.
5. **Save** (Ctrl+S), enter a file name. The effect now appears in the programmer's effect list.

---

## 5. Structure of a script

A script has three parts:

```
#NAME My effect                            // 1. Header lines (start with #)
#CATEGORY dimmer
#RATE 25
#VAR speed Slider 1 0.1 8 0.1

float level = 0;                           // 2. Variables and functions (optional)

setup() {                                  //    setup(): once when the effect starts (optional)
  level = 50;
}

loop() {                                   // 3. loop(): required, runs #RATE times per second
  dimmer = level;
}
```

### Header lines

| Line | Meaning |
|---|---|
| `#NAME text` | Display name in the program. Without it the file name is used. |
| `#DESCRIPTION text` | Short description (shown in the effect picker and the Open dialog). |
| `#CATEGORY dimmer` / `color` / `position` | **Required.** What the effect controls. |
| `#RATE n` | How often `loop()` runs per second: a whole number from **1 to 40**. Default 40 – the DMX output rate. |
| `#VAR ...` | A **slider** (see section 9) or an internal variable. |

---

## 6. Time and rate

**The most important rule:** `loop()` runs exactly `#RATE` times per second – no matter how fast the computer is. So you can **think in exact seconds**.

| Name | Meaning |
|---|---|
| `elapsed` | **Seconds since the effect started** on this fixture. Starts at 0. Exactly `tick / rate`. This is how you program "in second 3 this should happen". |
| `t` | Shared system time in seconds. The same for **all** effects – effects that compute with `t` stay **in sync** with each other even when they were started at different times. |
| `tick` | Number of the pass, starts at 0. |
| `rate` | Passes per second (the value of `#RATE`). |
| `dt` | Time between two passes in seconds (`1 / rate`). |

Which rate should I choose?

- **40** (default): smoothest curves – for waves, circles, crossfades.
- **10 to 25**: enough for color changes and effects that are stepped anyway.
- **1 to 5**: step effects (one step per second, "click-click" chases), cheap to compute.

**The "speed" convention:** the bundled effects and all templates have a slider `speed` with default **1**: that is **one period per second**. `sin(2 * PI * speed * elapsed)` is one wave per second at `speed = 1`.

### In second X ...

```
#NAME Sequence
#CATEGORY dimmer
#RATE 20
#VAR length Slider 8 2 30 1       // length of the sequence in seconds

loop() {
  float s = elapsed % length;     // time within the sequence; jumps back to 0 after "length" seconds
  if (s < 2) {
    dimmer = map(s, 0, 2, 0, 100);                 // seconds 0 to 2: fade in
  } else if (s < 5) {
    dimmer = 100;                                  // seconds 2 to 5: full
  } else {
    dimmer = 100 * (1 - (s - 5) / (length - 5));   // then fade out
  }
}
```

---

## 7. The language

Everything is a **number**. The types are `float` (decimal, also `double`), `int` (whole number, also `long`, `short`, `byte`) and `bool` (0 or 1, also `boolean`). `true` and `false` are 1 and 0.

### Variables

```
float x = 1.5;          // decimal number (dot, not comma)
int n = 3;              // whole number: assigning truncates (7.9 becomes 7)
bool on = true;         // 0 or 1: any value other than 0 becomes 1
const float K = 0.25;   // constant, cannot be changed
float a = 1, b2 = 2;    // several in one line
```

- Variables created **outside** functions are **global** and **keep their value** from pass to pass. Their initial value applies when the effect starts (to reset them later, write `setup()`).
- Variables created **inside** `{ }` are **local**: they last until the closing brace and start fresh in every pass.
- Assigning to an **undeclared** variable (`counter = counter + 1;`) creates a global `float` automatically – that is how older scripts worked. Better: declare it.
- The names `t`, `elapsed`, `dt`, `tick`, `rate`, `index`, `count`, `phase`, `dimmer`, `r`, `g`, `b`, `pan`, `tilt`, `PI` and all keywords and function names are taken.

### Calculating and comparing

| Symbol | Meaning |
|---|---|
| `+ - * /` | Basic arithmetic. Division by 0 gives 0. |
| `%` | Remainder (also for decimals): `5.5 % 2` is 1.5. |
| `== != < <= > >=` | Comparisons; result 1 (true) or 0 (false). |
| `&& \|\| !` | And, or, not. Conditions are true when they are not 0. |
| `condition ? a : b` | Choice: `a` if the condition is true, otherwise `b`. |
| `= += -= *= /= %=` | Assignment; `x += 2;` is `x = x + 2;`. |
| `x++;` `x--;` | Increase / decrease by 1. |

### Branching and repeating

```
if (x > 10) {                 // if ...
  dimmer = 100;
} else if (x > 5) {           // else if ...
  dimmer = 50;
} else {                      // else
  dimmer = 0;
}

for (int i = 0; i < 5; i++) { // count i from 0 to 4
  total += i;
}

while (n > 0) { n--; }        // as long as n is greater than 0

do { n++; } while (n < 3);    // run at least once

break;                        // leave the loop at once
continue;                     // jump to the next loop pass
```

Braces `{ }` are optional for a single statement (`if (a) b = 1;`), but clearer with them. There is no `switch` – use `if` / `else if`.

### Your own functions

```
float wave(float x) {                     // return type, name, parameters
  return 0.5 + 0.5 * sin(2 * PI * x);     // return hands the value back
}

void setBright(float v) {                 // void: returns nothing
  dimmer = v;
}

loop() {
  setBright(100 * wave(speed * elapsed));
}
```

Functions may stand before or after the place where they are called, and may call themselves (recursion, limited). Parameters are local; global variables and outputs (`dimmer` ...) are reachable everywhere.

### Comments

```
// rest of the line is a comment
/* several
   lines */
```

### Limits

- One pass may do at most **60,000 loop iterations and function calls**; an endless loop stops with the message "endless loop?".
- An effect that **throws an error or needs more than 50 ms per pass** is switched off ("rests") so it cannot hold up the others. Save the script again and it runs again.
- There are only numbers: no text, lists (arrays) or pointers.

---

## 8. Outputs per category

The script writes its result into variables that fit the category:

| `#CATEGORY` | Outputs | Range |
|---|---|---|
| `dimmer` | `dimmer` | 0 to 100 (%) |
| `color` | `r`, `g`, `b` | 0 to 255 |
| `position` | `pan`, `tilt` | 0 to 100 (%), 50 is the centre. If the fixture has fine channels (16 bit), decimals are used: `pan = 33.3333;` is more precise than `pan = 33;` |
| `zoom` | `zoom` | 0 to 100 (%) – the ends of the zoom channel (wide/narrow, depending on the fixture) |
| `focus` | `focus` | 0 to 100 (%) – the ends of the focus channel (near/far) |
| `gobo` | `gobo` | 0 to 100 (%) – the position of the gobo channel of wheel 1; pick gobos best with `slot(n)` (see below) |
| `gobo` | `gobo_spin` | 0 to 100 (%) – rotation or shake of wheel 1 (the range sets direction and speed, depending on the fixture) |
| `gobo` | `gobo2` | 0 to 100 (%) – gobo wheel 2 (fixtures with a second wheel only), pick gobos with `slot(n, 2)` |
| `gobo` | `gobo2_spin` | 0 to 100 (%) – rotation of wheel 2 |

Values outside the range are clamped. **An effect drives only the outputs its script assigns somewhere** (`hsv()` counts as `r`, `g`, `b`; for color always all three). If a script writes only `pan`, `tilt` is left alone: the channel does not follow the effect, and in the programmer only the Pan fader is locked - you can keep setting Tilt by hand. If an output is not reached in one pass (e.g. the assignment sits in an `if`), it stands at 0 for that pass (`pan`/`tilt`: center, 50). If the fixture lacks the channel, the output is silently ignored. Outputs of another category are ignored. With `hsv(h, s, v);` you set `r`, `g`, `b` from hue, saturation and value (each 0 to 1) in one step.

Note: outputs only apply to **the current pass** – to remember a value, create your own variable (`float level = 0;` ... `dimmer = level;`).

---

## 9. Sliders: `#VAR`

```
#VAR <name> <type> <default> [min max step]
```

| Type | Default | Control |
|---|---|---|
| `Slider` | number, plus `min max step` | slider |
| `NumberInput` | number, plus `min max step` | number field |
| `ColorPicker` | hex color, e.g. `#ff8800` | color picker; in the script as `name_r`, `name_g`, `name_b` (0 to 255) |
| `Internal` | number | no control – a global variable with an initial value (like `float name = 0;`) |

```
#VAR speed Slider 1 0.05 8 0.05          // periods per second
#VAR size Slider 100 0 100 1             // strength in %
#VAR color ColorPicker #00aaff           // color_r, color_g, color_b
```

The sliders appear in the **Create / edit effect** dialog and in the studio preview. In the script they are **read-only**.

---

## 10. System variables

| Name | Meaning |
|---|---|
| `t` | Shared system time in seconds (keeps effects in sync). |
| `elapsed` | Seconds since this effect started on this fixture. |
| `dt` | Seconds between two passes (`1 / rate`). |
| `tick` | Number of the pass (0, 1, 2 ...). Also `loop_count`. |
| `rate` | Passes per second. |
| `index` | Number of this fixture in the programmer's selection order (0, 1, 2 ...). |
| `count` | Number of fixtures the effect runs on. |
| `phase` | `index / count`: even offset across the selection (0 to almost 1). |
| `slots` | Number of fixed gobos on wheel 1 (only in the `gobo` category, otherwise 0). The preview uses 8 gobos. |
| `slots2` | The same for wheel 2 (0 if the fixture has only one wheel). |

The selection order is the order in which you picked the fixtures.

---

## 11. Functions

| Function | Meaning |
|---|---|
| `sin(x)`, `cos(x)`, `tan(x)` | Angle in radians (full circle = `2 * PI`). |
| `asin(x)`, `acos(x)`, `atan(x)`, `atan2(y, x)` | Inverse functions. |
| `sqrt(x)`, `pow(x, y)`, `exp(x)`, `log(x)` | Root, power, e-function, natural logarithm. Invalid input gives 0. |
| `abs(x)`, `sign(x)` | Absolute value; sign (-1, 0, 1). |
| `min(a, b)`, `max(a, b)` | Smaller / larger value. |
| `floor(x)`, `ceil(x)`, `round(x)` | Round down, round up, round. |
| `fract(x)` | Fractional part: `fract(2.25)` is 0.25. Useful for "position within the period". |
| `mod(a, b)` | Remainder that is never negative (unlike `%` for negative numbers). |
| `constrain(x, low, high)` | Limits `x` to the range. |
| `map(x, inMin, inMax, outMin, outMax)` | Converts `x` from one range to another (as in Arduino). |
| `lerp(a, b, k)` | Linear from `a` to `b`: `a + (b - a) * k`. |
| `smoothstep(e0, e1, x)` | Soft transition from 0 to 1 between `e0` and `e1`. |
| `saw(x)`, `tri(x)`, `square(x)`, `square(x, duty)` | Waveforms with 0 to 1 per period of `x`: sawtooth, triangle, square (`duty` = share "on", default 0.5). |
| `radians(d)`, `degrees(r)` | Degrees ↔ radians. |
| `random()`, `random(max)`, `random(min, max)` | Random number (0 to 1, 0 to `max`, `min` to `max`). Every fixture has its own **reproducible** sequence. |
| `hsv(h, s, v)` | Sets `r`, `g`, `b` from hue `h` (0 to 1, wraps around), saturation `s` and value `v` (0 to 1). |
| `slot(n)` | The value (in %) of the n-th gobo of wheel 1; `slot(0)` is the first (usually open). Only in the `gobo` category; the list comes from the fixture file, without data `slot()` returns 0. |
| `slot(n, wheel)` | Like `slot(n)`, but for wheel `wheel` (1 or 2): `gobo2 = slot(3, 2);` |

Constants: `PI`, `TWO_PI`, `HALF_PI`, `E`, `true`, `false`.

---

## 12. Examples

### Pulse (dimmer)

Hard on and off; `duty` is the share of the period in which the light is on.

```
#NAME Pulse
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR duty Slider 0.25 0.05 1 0.05
#VAR spread Slider 0 0 1 0.05

loop() {
  float p = fract(speed * elapsed + index * spread);
  dimmer = p < duty ? 100 : 0;
}
```

### Chase (dimmer)

One light travels across all selected fixtures.

```
#NAME Chase
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.1 8 0.1
#VAR width Slider 1 0.5 8 0.5

loop() {
  float pos = fract(speed * elapsed) * count;   // current step (decimal)
  float d = abs(index - pos);
  if (d > count / 2) d = count - d;             // distance on the circle
  dimmer = d < width ? 100 : 0;
}
```

### Random color (color)

Switches `speed` times per second to a random hue. The global variable `hue` remembers it.

```
#NAME Random color
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.1 8 0.1

float hue = 0;

loop() {
  if (tick % max(1, round(rate / speed)) == 0) {
    hue = random();
  }
  hsv(hue, 1, 1);
}
```

### Four positions (position, state machine)

The head jumps to the next of four corners every `interval` seconds. The state lives in `step`.

```
#NAME Four positions
#CATEGORY position
#RATE 10
#VAR interval Slider 1 0.2 10 0.1

int step = 0;
float start = 0;

loop() {
  if (elapsed - start >= interval) {
    step = (step + 1) % 4;
    start = elapsed;
  }
  pan = (step == 0 || step == 3) ? 20 : 80;
  tilt = (step < 2) ? 20 : 80;
}
```

### Harmonics (dimmer, loop)

Adds several waves with a `for` loop (the higher, the quieter).

```
#NAME Harmonics
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.1 4 0.1
#VAR harmonics Slider 3 1 8 1

loop() {
  float sum = 0;
  float norm = 0;
  for (int k = 1; k <= harmonics; k++) {
    sum += sin(2 * PI * k * speed * elapsed) / k;
    norm += 1.0 / k;
  }
  dimmer = 50 + 50 * sum / norm;
}
```

### Zoom breathing (zoom)

The zoom swings between `low` and `high` (0 and 100 are the ends of the zoom channel).

```
#NAME Zoom breathing
#CATEGORY zoom
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR low Slider 20 0 100 1
#VAR high Slider 80 0 100 1

loop() {
  float k = 0.5 + 0.5 * sin(2 * PI * speed * elapsed);
  zoom = lerp(low, high, k);
}
```

### Gobo change (gobo)

Steps through the fixture's gobos in turn. `slots` is their number, `slot(n)` the value of the n-th (0 = first, usually open). Every fixture has different gobos – so the effect asks the fixture instead of guessing percentages.

```
#NAME Gobo change
#CATEGORY gobo
#RATE 20
#VAR speed Slider 0.5 0.05 8 0.05
#VAR first Slider 0 0 20 1

loop() {
  float n = max(1, slots - first);
  gobo = slot(first + mod(floor(speed * elapsed), n));
}
```

### Gobo with rotation and second wheel (gobo)

The outputs `gobo`, `gobo_spin`, `gobo2` and `gobo2_spin` can be used individually. This example steps through wheel 1, lets wheel 2 follow with an offset and rotates the chosen gobo:

```
#NAME Two wheels
#CATEGORY gobo
#RATE 20
#VAR speed Slider 0.5 0.05 8 0.05

loop() {
  float n  = max(1, slots);
  float n2 = max(1, slots2);
  gobo  = slot(mod(floor(speed * elapsed), n));
  gobo2 = slot(mod(floor(speed * elapsed) + 1, n2), 2);
  gobo_spin = 70;                    // rotation of wheel 1 (set only if wanted)
}
```

### Two-color runner (color)

All fixtures show color A, one or two run through the row in color B (selection order). `direction` sets the direction - this is the bundled *Color Runner* in short form:

```
#NAME Color runner
#CATEGORY color
#RATE 40
#VAR speed Slider 0.5 0.05 4 0.05
#VAR width Slider 1.5 0.5 8 0.5
#VAR direction Slider 1 0 1 1
#VAR color_a ColorPicker #ffcc00
#VAR color_b ColorPicker #ff0000

loop() {
  float run = fract(speed * t);
  if (direction < 0.5) run = 1 - run;
  float d = abs(index - run * count);
  if (d > count / 2) d = count - d;
  float k = d < width ? 1 : 0;
  r = lerp(color_a_r, color_b_r, k);
  g = lerp(color_a_g, color_b_g, k);
  b = lerp(color_a_b, color_b_b, k);
}
```

### Your own function (dimmer)

```
#NAME Triangle with function
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.1 8 0.1

float triangle(float x) {
  return 1 - abs(2 * fract(x) - 1);
}

loop() {
  dimmer = 100 * triangle(speed * elapsed + phase);
}
```

---

## 13. Errors and checking

The studio checks while you type. Typical messages (always with a line number):

| Message | Cause |
|---|---|
| `Unbekannte Variable 'x'` | Name never declared or assigned (typo?). |
| `Unbekannte Funktion 'foo()'` | The function does not exist. |
| `sin() erwartet 1 Argument(e)` | Wrong number of arguments. |
| `';' erwartet, gefunden '}'` | A semicolon is missing (the message often points to the line after). |
| `Ausdruck erwartet, gefunden ';'` | A value is missing, e.g. `dimmer = 1 +;`. |
| `'speed' ist ein Regler (#VAR) ...` | Sliders are read-only; create your own variable. |
| `'b' ist eine Ausgabe des Effekts ...` | `dimmer`, `r`, `g`, `b`, `pan`, `tilt` and the system names are taken. |
| `'break' ist nur in einer Schleife erlaubt` | `break` / `continue` outside `for` / `while`. |
| `#RATE erwartet eine ganze Zahl von 1 bis 40` | Invalid rate. |
| `#CATEGORY fehlt` | The header has no category. |
| `loop() erwartet` | The script has no `loop()` function. |
| `Zu viele Schritte in einem Durchlauf ... Endlosschleife?` | A loop never ends (runtime error, shows in the preview). |

(The messages are shown in German whatever the interface language.)

**Save** also saves scripts with errors so you can keep working. A faulty script is not executed; running effects keep the **last good version**.

If a script is saved while effects are running, they take the new code on the next pass. Their **memory** (global variables, counters, state) is kept; newly added variables start with their initial value.

---

## 14. How effects work in the program

- **Script and effect:** the script (`.fx`) is the file. An **effect** (in the programmer's effect list) is a **definition**: a name, a script and values for its sliders. Several effects can use the same script with different slider values. When you create one, the dialog shows the script's description and its loops per second.
- **Applying:** in the programmer you assign an effect per **category** (dimmer, color, position, zoom, focus, gobo) to the selected fixtures: the **Variable:/Effect** row in the matching programmer view (focus and zoom in the focus view, gobo in the gobo tab of the beam area; while an effect runs, the matching fader is locked). The selection order determines `index` and with it the spread across the fixtures. An effect only controls the channels of its category.
- **In cues:** a cue stores the effect assignments (with the selection order) and starts them when played; the cue's **effect fade-in** and **fade-out** times blend the amplitude from / to the previous value. If a cue sets a fixed value for a category, the running effect ends there and the cue fades from the effect's last output.
- **Sync:** effects that use `t` (or `phase`/`index` together with `t`) run in step with each other. With `elapsed`, every effect starts from the beginning when it starts – right for sequences "from now".
- **State:** every effect has its **own memory** per fixture and category. It starts fresh when the effect is assigned again.
- **Files:** scripts live in the `effects/` folder of the data folder. The studio, the **file manager** (kind *Effects*: rename, duplicate, download, upload) and the show **export** (used scripts go into the package) work with the same files. The bundled effects are copied on first start; **Restore default effects** (in the Open dialog or the file manager) recreates missing ones and **never** overwrites anything.
- **The show stores the definitions** (name, script name, slider values), not the script text. If the script is missing the definitions lose their effect and work again when it returns; a cue with a missing effect leaves the channel unchanged.

### Limits today

- There are six categories (dimmer, color, position, zoom, focus, gobo). More (prism, strobe, raw DMX values) are prepared but not built in yet.
- Zoom and focus use the fixture's own channel and must exist; gobos depend on the fixture file. The preview shows only the values for gobos, not the picture.
- One effect controls one category per fixture; two categories at once need two effects.
- The rate is at most 40 per second because the DMX output does not send faster.
