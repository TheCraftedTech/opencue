# Effectenstudio – Handleiding

Een **effect** is een klein programma dat licht in de tijd verandert: een dimmer die pulseert, een kleur die door de regenboog loopt, een moving head die een cirkel beschrijft. U schrijft effecten in de **Effectenstudio** (paneel *Effectenstudio*) in een taal die op C++ of Arduino lijkt: met variabelen, `if`, `for`, `while` en uw eigen functies. U hoeft geen programmeur te zijn – de sjablonen onder **Nieuw...** werken meteen en zijn bedoeld om gelezen en aangepast te worden.

Deze handleiding is ook in de studio beschikbaar via de knop **Help**.

---

## 1. Het idee in één minuut

- Een **script** is een tekstbestand (`.fx`). Het beschrijft wat er in **één doorgang** gebeurt. Die doorgang heet `loop()` en loopt **`#RATE` keer per seconde** (1 tot 40, standaard 40).
- In elke doorgang berekent het script nieuwe **uitvoerwaarden**: `dimmer`, of `r`/`g`/`b`, of `pan`/`tilt`. Welke, bepaalt de **categorie** (`#CATEGORY`).
- Tussen twee doorgangen **blijft de uitvoer waar hij is**. Bij 10 doorgangen per seconde verandert de waarde dus tien keer per seconde – met opzet, zo bouwt u effecten met stappen.
- Het script loopt **voor elke projector afzonderlijk**. Elke projector kent zijn nummer (`index`) en het totaal (`count`); gebruik ze om golven en chases over meerdere projectoren te verdelen.
- Variabelen die u buiten `loop()` maakt, **houden hun waarde tussen doorgangen**: tellers, toestanden, timers.

```
#NAME Sine
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05

loop() {
  dimmer = 50 + 50 * sin(2 * PI * speed * elapsed);
}
```

Dat is een compleet effect: de dimmer zwaait tussen 0 en 100 % met `speed` golven per seconde.

---

## 2. Opdrachtenoverzicht (spiekbriefje)

Alle opdrachten in één oogopslag. De hoofdstukken hierna leggen ze met voorbeelden uit.

| Gebied | Opdrachten |
|---|---|
| Kopregels | `#NAME`, `#DESCRIPTION`, `#CATEGORY dimmer` / `color` / `position`, `#RATE 1` tot `40`, `#VAR name Slider` / `NumberInput` / `ColorPicker` / `Internal ...` |
| Structuur | `setup() { }` (één keer aan het begin), `loop() { }` (`#RATE` keer per seconde) |
| Typen | `float` (`double`), `int` (`long`, `short`, `byte`), `bool` (`boolean`), `void`, `const` |
| Toewijzen | `x = 1;`, `x += 1;` (ook `-=` `*=` `/=` `%=`), `x++;`, `x--;` |
| Vertakken | `if (...) { } else if (...) { } else { }`, `condition ? a : b` |
| Lussen | `for (int i = 0; i < n; i++) { }`, `while (...) { }`, `do { } while (...);`, `break;`, `continue;` |
| Functies | `float name(float x) { return x * 2; }`, `void name() { }`, `return value;` |
| Rekenen | `+ - * / %`, `== != < <= > >=`, `&& \|\| !` |
| Commentaar | `// tot het einde van de regel`, `/* over meerdere regels */` |
| Uitvoer | Dimmer: `dimmer` · Kleur: `r`, `g`, `b` of `hsv(h, s, v);` · Positie: `pan`, `tilt` · Zoom: `zoom` · Focus: `focus` · Gobo: `gobo`, `gobo_spin`, `gobo2`, `gobo2_spin` |
| Tijd | `t` (gedeelde systeemtijd), `elapsed` (sinds de start van het effect), `dt`, `tick` (`loop_count`), `rate` |
| Projectoren | `index`, `count`, `phase` (= `index / count`), `slots`, `slots2` (aantal gobo's op wiel 1 en wiel 2) |
| Constanten | `PI`, `TWO_PI`, `HALF_PI`, `E`, `true`, `false` |
| Wiskunde | `sin` `cos` `tan` `asin` `acos` `atan` `atan2` `sqrt` `pow` `exp` `log` `abs` `sign` `min` `max` `floor` `ceil` `round` `fract` `mod` |
| Hulpjes | `constrain(x, lo, hi)` `map(x, inMin, inMax, outMin, outMax)` `lerp(a, b, k)` `smoothstep(e0, e1, x)` `radians(d)` `degrees(r)` |
| Golfvormen | `saw(x)` `tri(x)` `square(x)` `square(x, duty)` – elk 0 tot 1 per periode |
| Willekeurig, kleur, gobo | `random()` `random(max)` `random(min, max)` · `hsv(h, s, v)` · `slot(n)` `slot(n, wheel)` |

---

## 3. De studio gebruiken

| Gebied | Wat het doet |
|---|---|
| **Openen...** | Venster met alle effecten, **favorieten eerst** (zoeken, categorie, lussen per seconde, herkomst; meegeleverde effecten dragen het label **Standaard**). De lijst scrolt. Klik op een rij om hem te openen, de **ster** maakt een effect tot favoriet (geldt voor alle apparaten), de prullenbak verwijdert het uit de gebruikersmap. Onderaan: **Standaardeffecten herstellen**. |
| **Nieuw...** | Venster: eerst de **categorie** (dimmer, kleur, positie, zoom, focus, gobo) of **Leeg bestand**, dan een **sjabloon** (*Leeg* is voorgeselecteerd), dan de **lussen per seconde**. *Leeg bestand* maakt een volledig lege editor zonder kopregels. **Aanmaken** laadt het resultaat in de editor – er wordt niets opgeslagen tot u het zegt. |
| **Opslaan** | Slaat op in het bestand van het effect. Een nieuw effect vraagt om een bestandsnaam. Een punt naast de naam toont niet-opgeslagen wijzigingen. Toetsenbord: **Ctrl+S** in de tekst (slaat het effect op, niet de show). |
| **Opslaan als...** | Een nieuwe bestandsnaam. Bestaat die al, dan vraagt de studio of hij moet worden overschreven. |
| **Verwijderen** | Verwijdert het geladen effect (alleen in de gebruikersmap; er wordt eerst gevraagd). Daarna is de editor leeg. Is de knop grijs, dan zegt een aanwijzing waarom (nog niet opgeslagen, of niet in de gebruikersmap). |
| **Help** | Opent deze handleiding. Het spiekbriefje (hoofdstuk 2) toont alle opdrachten. |
| **Voorbeeld** | Toont of verbergt de voorvertoning rechts. |
| **Statusbalk** | Groen = in orde. Rood = fout met regelnummer. Rechts: regel en kolom van de cursor. |

De editor **kleurt** sleutelwoorden, typen, getallen, commentaar, functies, systeemvariabelen, uitvoer en uw schuiven (`#VAR`). **Enter** behoudt de inspringing van de regel (twee spaties extra na `{`), **Tab** voegt twee spaties in.

### De voorvertoning

De voorvertoning laat uw script **zonder projectoren** lopen terwijl u typt – precies met de lussen per seconde die u met `#RATE` koos – en tekent het resultaat:

- **Dimmer:** één curve per projector, 0 tot 100 %.
- **Kleur:** R/G/B als curven en eronder een **kleurstrook** per projector.
- **Positie:** pan en tilt als curven en het **pad** in het pan/tilt-veld.

Standaard: **1 projector, 2 seconden**. Bovenaan stelt u het aantal projectoren (1 tot 16) en de duur (1 tot 20 s) in; meerdere projectoren tonen hoe `index`, `count` en `phase` de golven verschuiven. Eronder staan **schuiven voor uw `#VAR`-parameters** – sleep er een en de curve volgt meteen. Bij een lage snelheid (tot 20 lussen per seconde) tekent de voorvertoning stappen, tot 10 bovendien de afzonderlijke punten.

Bevat het script een fout, dan blijft de voorvertoning in de **laatste goede toestand, vervaagd**, de foutregel is rood gemarkeerd en de statusbalk noemt de regel en het bericht.

---

## 4. Uw eerste effect

1. **Nieuw...** → categorie **Dimmer** → sjabloon **Sine** → **Aanmaken**.
2. De voorvertoning toont twee golven in twee seconden (`speed` is 1).
3. Zet `speed` op 2: twee keer zo snel. Stel in de voorvertoning 3 projectoren in en zet `spread` op 0,33: de golven zijn ten opzichte van elkaar verschoven.
4. Wijzig `0.5 + 0.5 * sin(...)` in de tekst en kijk naar de curve.
5. **Opslaan** (Ctrl+S), voer een bestandsnaam in. Het effect verschijnt nu in de effectenlijst van de programmer.

---

## 5. Structuur van een script

Een script heeft drie delen:

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

### Kopregels

| Regel | Betekenis |
|---|---|
| `#NAME text` | Weergavenaam in het programma. Zonder wordt de bestandsnaam gebruikt. |
| `#CATEGORY dimmer` / `color` / `position` | **Verplicht.** Wat het effect aanstuurt. |
| `#RATE n` | Hoe vaak `loop()` per seconde loopt: een geheel getal van **1 tot 40**. Standaard 40 – de snelheid van de DMX-uitvoer. |
| `#DESCRIPTION text` | Een korte beschrijving (ook `#DESCRIPTION en ...` en `#DESCRIPTION de ...` voor één tekst per taal; het programma toont die van de interfacetaal). |
| `#INFO name en Label \| Hint` | Geeft de schuif `name` een **label** en een **muisaanwijzing** in een taal (`en` of `de`), bijvoorbeeld `#INFO speed de Tempo \| Wie schnell der Effekt läuft`. Zonder `#INFO` gebruikt het programma zijn ingebouwde woordenlijst van de gebruikelijke namen (`speed`, `size`, `low`, `high`, `strobe` ...) en ten slotte de variabelenaam zelf. |
| `#TAGS a, b, c` | Trefwoorden om te zoeken en te filteren in het venster voor het effecttype (bijvoorbeeld `strobe, flash, toggle`; maximaal 8, kleine letters). Een script dat audiovariabelen leest, krijgt automatisch de tag `audio` – die schrijft u niet. De meegeleverde effecten dragen `basic` (voor beginners, 19 ervan) of `advanced` (alle andere) als eerste tag; het venster toont ze als "Basis" / "Geavanceerd" – gebruik ze ook voor uw eigen effecten. |
| `#VAR ...` | Een **schuif** (zie paragraaf 9) of een interne variabele. |

---

## 6. Tijd en snelheid

**De belangrijkste regel:** `loop()` loopt precies `#RATE` keer per seconde – ongeacht hoe snel de computer is. U kunt dus **in exacte seconden denken**.

| Naam | Betekenis |
|---|---|
| `elapsed` | **Seconden sinds het effect startte** op deze projector. Begint bij 0. Precies `tick / rate`. Zo programmeert u "in seconde 3 moet dit gebeuren". |
| `t` | Gedeelde systeemtijd in seconden. Dezelfde voor **alle** effecten – effecten die met `t` rekenen blijven **synchroon** met elkaar, ook als ze op verschillende momenten zijn gestart. |
| `tick` | Nummer van de doorgang, begint bij 0. |
| `rate` | Doorgangen per seconde (de waarde van `#RATE`). |
| `dt` | Tijd tussen twee doorgangen in seconden (`1 / rate`). |

Welke snelheid kies ik?

- **40** (standaard): de vloeiendste curven – voor golven, cirkels, overgangen.
- **10 tot 25**: genoeg voor kleurwisselingen en effecten die toch in stappen gaan.
- **1 tot 5**: stapeffecten (één stap per seconde, "klik-klik"-chases), goedkoop te berekenen.

**De "speed"-afspraak:** de meegeleverde effecten en alle sjablonen hebben een schuif `speed` met standaard **1**: dat is **één periode per seconde**. `sin(2 * PI * speed * elapsed)` is één golf per seconde bij `speed = 1`.

### In seconde X ...

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

## 7. De taal

Alles is een **getal**. De typen zijn `float` (decimaal, ook `double`), `int` (geheel getal, ook `long`, `short`, `byte`) en `bool` (0 of 1, ook `boolean`). `true` en `false` zijn 1 en 0.

### Variabelen

```
float x = 1.5;          // decimal number (dot, not comma)
int n = 3;              // whole number: assigning truncates (7.9 becomes 7)
bool on = true;         // 0 or 1: any value other than 0 becomes 1
const float K = 0.25;   // constant, cannot be changed
float a = 1, b2 = 2;    // several in one line
```

- Variabelen die **buiten** functies worden gemaakt, zijn **globaal** en **houden hun waarde** van doorgang tot doorgang. Hun beginwaarde geldt als het effect start (om ze later te resetten, schrijft u `setup()`).
- Variabelen die **binnen** `{ }` worden gemaakt, zijn **lokaal**: ze duren tot de sluitende accolade en beginnen in elke doorgang opnieuw.
- Toewijzen aan een **niet-gedeclareerde** variabele (`counter = counter + 1;`) maakt automatisch een globale `float` – zo werkten oudere scripts. Beter: declareer haar.
- De namen `t`, `elapsed`, `dt`, `tick`, `rate`, `index`, `count`, `phase`, `dimmer`, `r`, `g`, `b`, `pan`, `tilt`, `PI` en alle sleutelwoorden en functienamen zijn bezet.

### Rekenen en vergelijken

| Symbool | Betekenis |
|---|---|
| `+ - * /` | Basisrekenen. Delen door 0 geeft 0. |
| `%` | Rest (ook voor decimalen): `5.5 % 2` is 1,5. |
| `== != < <= > >=` | Vergelijkingen; resultaat 1 (waar) of 0 (onwaar). |
| `&& \|\| !` | En, of, niet. Voorwaarden zijn waar als ze niet 0 zijn. |
| `condition ? a : b` | Keuze: `a` als de voorwaarde waar is, anders `b`. |
| `= += -= *= /= %=` | Toewijzing; `x += 2;` is `x = x + 2;`. |
| `x++;` `x--;` | Met 1 verhogen / verlagen. |

### Vertakken en herhalen

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

Accolades `{ }` zijn optioneel bij één enkele instructie (`if (a) b = 1;`), maar duidelijker met. Er is geen `switch` – gebruik `if` / `else if`.

### Uw eigen functies

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

Functies mogen voor of na de plek staan waar ze worden aangeroepen en mogen zichzelf aanroepen (recursie, beperkt). Parameters zijn lokaal; globale variabelen en uitvoer (`dimmer` ...) zijn overal bereikbaar.

### Commentaar

```
// rest of the line is a comment
/* several
   lines */
```

### Grenzen

- Een doorgang mag hoogstens **60.000 lusiteraties en functieaanroepen** doen; een eindeloze lus stopt met het bericht "endless loop?".
- Een effect dat **een fout geeft of meer dan 50 ms per doorgang nodig heeft**, wordt uitgeschakeld ("rust") zodat het de andere niet ophoudt. Sla het script opnieuw op en het loopt weer.
- Er zijn alleen getallen: geen tekst, lijsten (arrays) of pointers.

---

## 8. Uitvoer per categorie

Het script schrijft zijn resultaat in variabelen die bij de categorie passen:

| `#CATEGORY` | Uitvoer | Bereik |
|---|---|---|
| `dimmer` | `dimmer` | 0 tot 100 (%) |
| `color` | `r`, `g`, `b` | 0 tot 255 |
| `position` | `pan`, `tilt` | 0 tot 100 (%), 50 is het midden. Heeft de projector fijne kanalen (16 bit), dan worden decimalen gebruikt: `pan = 33.3333;` is nauwkeuriger dan `pan = 33;` |
| `zoom` | `zoom` | 0 tot 100 (%) – de uiteinden van het zoomkanaal (breed/smal, afhankelijk van de projector) |
| `focus` | `focus` | 0 tot 100 (%) – de uiteinden van het focuskanaal (dichtbij/ver) |
| `gobo` | `gobo` | 0 tot 100 (%) – de positie van het gobokanaal van wiel 1; kies gobo's het best met `slot(n)` (zie hieronder) |
| `gobo` | `gobo_spin` | 0 tot 100 (%) – rotatie of schudden van wiel 1 (het bereik bepaalt richting en snelheid, afhankelijk van de projector) |
| `gobo` | `gobo2` | 0 tot 100 (%) – goborad 2 (alleen projectoren met een tweede wiel), kies gobo's met `slot(n, 2)` |
| `gobo` | `gobo2_spin` | 0 tot 100 (%) – rotatie van wiel 2 |

Waarden buiten het bereik worden begrensd. **Een effect stuurt alleen de uitvoer aan die zijn script ergens toewijst** (`hsv()` telt als `r`, `g`, `b`; bij kleur altijd alle drie). Schrijft een script alleen `pan`, dan blijft `tilt` met rust: het kanaal volgt het effect niet en in de programmer is alleen de Pan-fader vergrendeld – u kunt Tilt met de hand blijven instellen. Wordt een uitvoer in één doorgang niet bereikt (bijv. de toewijzing zit in een `if`), dan staat hij voor die doorgang op 0 (`pan`/`tilt`: midden, 50). Ontbreekt het kanaal bij de projector, dan wordt de uitvoer stilzwijgend genegeerd. Uitvoer van een andere categorie wordt genegeerd. Met `hsv(h, s, v);` stelt u `r`, `g`, `b` in uit tint, verzadiging en waarde (elk 0 tot 1) in één stap.

Let op: uitvoer geldt alleen voor **de huidige doorgang** – om een waarde te onthouden, maakt u een eigen variabele (`float level = 0;` ... `dimmer = level;`).

---

## 9. Schuiven: `#VAR`

```
#VAR <name> <type> <default> [min max step]
```

| Type | Standaard | Bediening |
|---|---|---|
| `Slider` | getal, plus `min max step` | schuif |
| `NumberInput` | getal, plus `min max step` | getalveld |
| `ColorPicker` | hexkleur, bijv. `#ff8800` | kleurkiezer; in het script als `name_r`, `name_g`, `name_b` (0 tot 255) |
| `Internal` | getal | geen bediening – een globale variabele met een beginwaarde (zoals `float name = 0;`) |

```
#VAR speed Slider 1 0.05 8 0.05          // periods per second
#VAR size Slider 100 0 100 1             // strength in %
#VAR color ColorPicker #00aaff           // color_r, color_g, color_b
```

De schuiven verschijnen in het venster **Effect aanmaken/bewerken** en in de voorvertoning van de studio. In het script zijn ze **alleen-lezen**.

---

## 10. Systeemvariabelen

| Naam | Betekenis |
|---|---|
| `t` | Gedeelde systeemtijd in seconden (houdt effecten synchroon). |
| `elapsed` | Seconden sinds dit effect op deze projector startte. |
| `dt` | Seconden tussen twee doorgangen (`1 / rate`). |
| `tick` | Nummer van de doorgang (0, 1, 2 ...). Ook `loop_count`. |
| `rate` | Doorgangen per seconde. |
| `index` | Nummer van deze projector in de selectievolgorde van de programmer (0, 1, 2 ...). |
| `count` | Aantal projectoren waarop het effect loopt. |
| `phase` | `index / count`: gelijkmatige verschuiving over de selectie (0 tot bijna 1). |
| `slots` | Aantal vaste gobo's op wiel 1 (alleen in de categorie `gobo`, anders 0). De voorvertoning gebruikt 8 gobo's. |
| `slots2` | Hetzelfde voor wiel 2 (0 als de projector maar één wiel heeft). |

De selectievolgorde is de volgorde waarin u de projectoren koos.

### Audiovariabelen (`a_...`)

Effecten kunnen op muziek reageren. Het **Audio**-paneel analyseert het geluid (zie de handleiding *Audio*); deze variabelen bevatten het resultaat. Alle beginnen met `a_`, zodat ze nooit botsen met uw eigen namen. Zonder draaiende audiobron zijn ze allemaal `0`. Een script dat er een leest, is een **audio-effect** (gemarkeerd in de lijst en in de studio; de voorvertoning laat dan een voorbeeldbeat van 120 BPM lopen).

| Naam | Betekenis |
|---|---|
| `a_active` | `1` zolang er geluid binnenkomt, anders `0`. |
| `a_level` | Totale luidheid 0 tot 1 (relatief aan de luidste delen van de laatste seconden). |
| `a_bass`, `a_mid`, `a_high` | Bas (tot 150 Hz), midden (150 Hz tot 2,5 kHz) en hoog (boven 2,5 kHz), 0 tot 1. |
| `a_b1` ... `a_b8` | De acht banden afzonderlijk (20-60, 60-150, 150-400, 400-1k, 1k-2,5k, 2,5k-5k, 5k-10k, 10k-20k Hz), 0 tot 1. |
| `a_kick`, `a_snare`, `a_hat` | Slagen van de basdrum, snare (of klap) en hi-hat: springt bij elke slag naar 0,45 - 1 en dooft in ongeveer 0,15 s uit (hi-hat 0,07 s). |
| `a_beat` | Hetzelfde soort puls bij elke beat van het gedetecteerde tempo. |
| `a_beat_phase` | Positie binnen de beat, 0 tot 1, gelijkmatig stijgend van de ene beat naar de volgende: ideaal voor tempo-synchrone golven. |
| `a_beat_count` | Nummer van de beat; telt bij elke beat met 1 op. |
| `a_bpm` | Gedetecteerd (of ingesteld) tempo in beats per minuut; `0` zolang onbekend. |
| `a_conf` | Hoe zeker de tempodetectie is, 0 tot 1. |

```
#CATEGORY dimmer
#RATE 40
loop() {
  dimmer = lerp(5, 100, a_kick);                              // flash on every bass drum
}
```

Tip: een doorgang ziet alleen de toestand op zijn eigen moment. Een puls (`a_kick`) lezen is altijd veilig omdat hij uitdooft; om op het *moment* van een slag te reageren, onthoudt u de laatste waarde in een globale variabele en vergelijkt u (zie het effect *Audio: Hi-Hat Sparkle*). Gebruik `#RATE 40` voor audio-effecten zodat ze pittig blijven.

---

## 11. Functies

| Functie | Betekenis |
|---|---|
| `sin(x)`, `cos(x)`, `tan(x)` | Hoek in radialen (hele cirkel = `2 * PI`). |
| `asin(x)`, `acos(x)`, `atan(x)`, `atan2(y, x)` | Inverse functies. |
| `sqrt(x)`, `pow(x, y)`, `exp(x)`, `log(x)` | Wortel, macht, e-functie, natuurlijke logaritme. Ongeldige invoer geeft 0. |
| `abs(x)`, `sign(x)` | Absolute waarde; teken (-1, 0, 1). |
| `min(a, b)`, `max(a, b)` | Kleinere / grotere waarde. |
| `floor(x)`, `ceil(x)`, `round(x)` | Naar beneden afronden, naar boven afronden, afronden. |
| `fract(x)` | Breukdeel: `fract(2.25)` is 0,25. Handig voor "positie binnen de periode". |
| `mod(a, b)` | Rest die nooit negatief is (anders dan `%` bij negatieve getallen). |
| `constrain(x, low, high)` | Begrenst `x` tot het bereik. |
| `map(x, inMin, inMax, outMin, outMax)` | Zet `x` van het ene bereik om naar het andere (zoals in Arduino). |
| `lerp(a, b, k)` | Lineair van `a` naar `b`: `a + (b - a) * k`. |
| `smoothstep(e0, e1, x)` | Zachte overgang van 0 naar 1 tussen `e0` en `e1`. |
| `saw(x)`, `tri(x)`, `square(x)`, `square(x, duty)` | Golfvormen met 0 tot 1 per periode van `x`: zaagtand, driehoek, blokgolf (`duty` = aandeel "aan", standaard 0,5). |
| `radians(d)`, `degrees(r)` | Graden ↔ radialen. |
| `random()`, `random(max)`, `random(min, max)` | Willekeurig getal (0 tot 1, 0 tot `max`, `min` tot `max`). Elke projector heeft zijn eigen **reproduceerbare** reeks. |
| `hsv(h, s, v)` | Stelt `r`, `g`, `b` in uit tint `h` (0 tot 1, loopt rond), verzadiging `s` en waarde `v` (0 tot 1). |
| `slot(n)` | De waarde (in %) van de n-de gobo van wiel 1; `slot(0)` is de eerste (meestal open). Alleen in de categorie `gobo`; de lijst komt uit het projectorbestand, zonder gegevens geeft `slot()` 0. |
| `slot(n, wheel)` | Zoals `slot(n)`, maar voor wiel `wheel` (1 of 2): `gobo2 = slot(3, 2);` |

Constanten: `PI`, `TWO_PI`, `HALF_PI`, `E`, `true`, `false`.

---

## 12. Voorbeelden

### Pulse (dimmer)

Hard aan en uit; `duty` is het aandeel van de periode waarin het licht aan is.

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

Eén licht loopt over alle geselecteerde projectoren.

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

### Willekeurige kleur (kleur)

Wisselt `speed` keer per seconde naar een willekeurige tint. De globale variabele `hue` onthoudt hem.

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

### Vier posities (positie, toestandsmachine)

De kop springt elke `interval` seconden naar de volgende van vier hoeken. De toestand zit in `step`.

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

### Harmonischen (dimmer, lus)

Telt meerdere golven op met een `for`-lus (hoe hoger, hoe zachter).

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

### Zoom die ademt (zoom)

De zoom zwaait tussen `low` en `high` (0 en 100 zijn de uiteinden van het zoomkanaal).

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

### Gobowissel (gobo)

Loopt de gobo's van de projector na elkaar af. `slots` is hun aantal, `slot(n)` de waarde van de n-de (0 = de eerste, meestal open). Elke projector heeft andere gobo's – het effect vraagt het dus aan de projector in plaats van percentages te raden.

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

### Gobo met rotatie en tweede wiel (gobo)

De uitvoer `gobo`, `gobo_spin`, `gobo2` en `gobo2_spin` kan afzonderlijk worden gebruikt. Dit voorbeeld loopt wiel 1 af, laat wiel 2 met een verschuiving volgen en laat de gekozen gobo roteren:

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

### Tweekleurige loper (kleur)

Alle projectoren tonen kleur A, één of twee lopen in kleur B door de rij (selectievolgorde). `direction` bepaalt de richting – dit is de meegeleverde *Color Runner* in verkorte vorm:

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

### Uw eigen functie (dimmer)

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

## 13. Fouten en controleren

De studio controleert terwijl u typt. Typische berichten (altijd met een regelnummer):

| Bericht | Oorzaak |
|---|---|
| `Unbekannte Variable 'x'` | Naam nooit gedeclareerd of toegewezen (typfout?). |
| `Unbekannte Funktion 'foo()'` | De functie bestaat niet. |
| `sin() erwartet 1 Argument(e)` | Verkeerd aantal argumenten. |
| `';' erwartet, gefunden '}'` | Er ontbreekt een puntkomma (het bericht wijst vaak naar de regel erna). |
| `Ausdruck erwartet, gefunden ';'` | Er ontbreekt een waarde, bijv. `dimmer = 1 +;`. |
| `'speed' ist ein Regler (#VAR) ...` | Schuiven zijn alleen-lezen; maak een eigen variabele. |
| `'b' ist eine Ausgabe des Effekts ...` | `dimmer`, `r`, `g`, `b`, `pan`, `tilt` en de systeemnamen zijn bezet. |
| `'break' ist nur in einer Schleife erlaubt` | `break` / `continue` buiten `for` / `while`. |
| `#RATE erwartet eine ganze Zahl von 1 bis 40` | Ongeldige snelheid. |
| `#CATEGORY fehlt` | De kop heeft geen categorie. |
| `loop() erwartet` | Het script heeft geen functie `loop()`. |
| `Zu viele Schritte in einem Durchlauf ... Endlosschleife?` | Een lus eindigt nooit (runtimefout, verschijnt in de voorvertoning). |

(De berichten worden in het Duits getoond, ongeacht de interfacetaal.)

**Opslaan** slaat ook scripts met fouten op, zodat u kunt blijven werken. Een foutief script wordt niet uitgevoerd; lopende effecten houden de **laatste goede versie**.

Wordt een script opgeslagen terwijl effecten lopen, dan nemen ze de nieuwe code bij de volgende doorgang over. Hun **geheugen** (globale variabelen, tellers, toestand) blijft behouden; nieuw toegevoegde variabelen beginnen met hun beginwaarde.

---

## 14. Hoe effecten in het programma werken

- **Script en effect:** het script (`.fx`) is het bestand. Een **effect** (in de effectenlijst van de programmer) is een **definitie**: een naam, een script en waarden voor zijn schuiven. Meerdere effecten kunnen hetzelfde script met verschillende schuifwaarden gebruiken. Als u er een maakt, toont het venster de beschrijving van het script en zijn lussen per seconde.
- **Toepassen:** in de programmer wijst u per **categorie** (dimmer, kleur, positie, zoom, focus, gobo) een effect toe aan de geselecteerde projectoren: de rij **Variabele:/Effect** in de bijbehorende programmerweergave (focus en zoom in de focusweergave, gobo in het gobotabblad van het bundelgebied; terwijl een effect loopt, is de bijbehorende fader vergrendeld). De selectievolgorde bepaalt `index` en daarmee de verdeling over de projectoren. Een effect stuurt alleen de kanalen van zijn categorie aan.
- **In cues:** een cue slaat de effecttoewijzingen op (met de selectievolgorde) en start ze bij het afspelen; de tijden voor **effect-fade-in** en **-fade-out** van de cue laten de amplitude van / naar de vorige waarde overvloeien. Zet een cue een vaste waarde voor een categorie, dan eindigt het lopende effect daar en fadet de cue vanaf de laatste uitvoer van het effect.
- **Sync:** effecten die `t` gebruiken (of `phase`/`index` samen met `t`) lopen gelijk met elkaar. Met `elapsed` begint elk effect bij zijn start van voren af aan – goed voor reeksen "vanaf nu".
- **Toestand:** elk effect heeft zijn **eigen geheugen** per projector en categorie. Het begint opnieuw als het effect opnieuw wordt toegewezen.
- **Bestanden:** scripts staan in de map `effects/` van de gegevensmap. De studio, het **bestandsbeheer** (soort *Effecten*: hernoemen, dupliceren, downloaden, uploaden) en het **exporteren** van de show (gebruikte scripts gaan in het pakket) werken met dezelfde bestanden. De meegeleverde effecten worden bij de eerste start gekopieerd; **Standaardeffecten herstellen** (in het venster Openen of het bestandsbeheer) maakt ontbrekende opnieuw aan en overschrijft **nooit** iets.
- **De show slaat de definities op** (naam, scriptnaam, schuifwaarden), niet de scripttekst. Ontbreekt het script, dan verliezen de definities hun effect en werken ze weer als het terugkomt; een cue met een ontbrekend effect laat het kanaal ongewijzigd.

### Beperkingen nu

- Er zijn zes categorieën (dimmer, kleur, positie, zoom, focus, gobo). Meer (prisma, strobe, ruwe DMX-waarden) zijn voorbereid maar nog niet ingebouwd.
- Zoom en focus gebruiken het eigen kanaal van de projector en dat moet bestaan; gobo's hangen af van het projectorbestand. De voorvertoning toont alleen de waarden voor gobo's, niet het beeld.
- Eén effect stuurt één categorie per projector aan; twee categorieën tegelijk vragen twee effecten.
- De snelheid is hoogstens 40 per seconde omdat de DMX-uitvoer niet sneller verstuurt.
