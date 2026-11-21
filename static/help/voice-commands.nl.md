# Spraakopdrachten

Met **spraakopdrachten** bedient u OpenCue met uw stem: u zegt het **triggerwoord** (standaard "OpenCue") en direct daarna een **opdracht van de opdrachtregel** – OpenCue schrijft die op, zet hem om in de notatie van de opdrachtregel en **voert hem meteen uit**, precies zoals een getypte opdracht (hij staat ook in de opdrachtgeschiedenis, alle vensters volgen). Alles draait **offline** op de consolecomputer (na het eenmalig downloaden van de modellen), er is geen AI nodig.

U spreekt **Engels**: de opdrachten van de opdrachtregel (`Fixture`, `At`, `Color`, `Blackout`, `Go` …) zijn Engels en de spraakherkenning is ingesteld om Engelse woorden te schrijven.

---

## 1. Aanzetten

1. Het **microfoonsymbool** rechtsboven in de werkbalk is een **aan/uit-schakelaar**:
   - **groen** = de spraakbesturing luistert naar het triggerwoord,
   - **rood en doorgestreept** = uit,
   - **geel** = fout (microfoon onbereikbaar, model ontbreekt …; de aanwijzing staat in de tooltip).
2. Eenmalig worden twee modellen gedownload (elk maar één keer, daarna werkt alles zonder internet): het kleine **triggerwoordmodel** (41 MB: *Instellingen → Triggerwoord → Spraakmodel downloaden*, of al in het installatieprogramma) en het **spraakmodel** voor de opdrachten (*Instellingen → Dictatie → Nu laden*; het is hetzelfde als bij dictatie). Het spraakmodel *Nauwkeurig* (small) begrijpt veel beter dan *Snel* (base).
3. Microfoon, triggerwoord en gevoeligheid stelt u in onder *Instellingen → Triggerwoord*.

Het symbool bestaat op de consolecomputer en ook op apparaten op afstand (iPad): de schakelaar zet de spraakbesturing van de server aan of uit; de microfoon zelf zit altijd aan de hoofdcomputer.

---

## 2. Hoe te spreken

```
"OpenCue … Blackout on."
"OpenCue … Fixture five at seventy nine, color green."
"OpenCue … Fixtures one through five at full."
```

- Eerst het **triggerwoord**, daarna – in dezelfde adem of na een korte pauze (tot ongeveer 2 seconden) – de **opdracht**.
- Als de opdracht klaar is, **wacht dan ongeveer een seconde**: een korte pauze beëindigt de opname (maximaal 10 seconden).
- Onderaan in het midden van het scherm toont een bel de voortgang: **Luisteren …** → **Begrijpen …** → **de opdracht** met zijn resultaat (groen = gedaan, rood = fout of niets begrepen). Heeft OpenCue een woord gecorrigeerd, dan staat dat erachter ("gecorrigeerd: add → At").
- Spreek korte, duidelijke opdrachten. Stopwoorden ("uh", "please", "now", "set") en stotteren worden verwijderd.

---

## 3. Wat u kunt zeggen

U zegt de opdrachten zoals ze in de opdrachtregel staan (zie de handleiding *Opdrachtregel*). Getallen kunt u in woorden zeggen ("seventy nine") of als cijfers. Meerdere opdrachten in één adem worden gescheiden door **"then"**.

### Projectoren en helderheid kiezen

| U zegt | Wat wordt uitgevoerd |
|---|---|
| Fixture five | `Fixture 5` |
| Fixtures one through ten | `Fixture 1 Thru 10` |
| Fixture three and seven | `Fixture 3 + 7` |
| Fixture five at seventy nine | `Fixture 5 At 79` |
| Fixture five brightness fifty percent | `Fixture 5 At 50%` (ook *dimmer, intensity, level*) |
| Fixtures one through five at full / at half | `Fixture 1 Thru 5 At Full` / `… At Half` |
| Fixture five on / full | `Fixture 5 At Full` |
| Fixture five off / out | `Fixture 5 At 0` |
| Fixture five at seventy nine point five | `Fixture 5 At 79.5` |
| At at / Everything on / All lights on | `At At` – **alles aan** (100 % + wit): zonder selectie alle projectoren, met een selectie alleen die selectie. Zeg eerst "Clear" om zeker te zijn dat het alles is. |
| Fixtures one through ten minus five (ook *except / without*) | `Fixture 1 Thru 10 - 5` (zonder nr. 5) |
| Next fixture / Previous fixture | `Next` / `Previous` (selecteert het volgende / vorige projector) |
| Group front at full | `Group front At Full` |
| Group front truss at forty | `Group "front truss" At 40` (meerdere naamwoorden horen bij elkaar tussen aanhalingstekens) |
| Light / lamp / spot five | `Fixture 5` |

### Kleuren

| U zegt | Wat wordt uitgevoerd |
|---|---|
| Fixture five color green | `Fixture 5 Color Green` |
| Fixture five green | `Fixture 5 Color Green` (het woord "color" wordt toegevoegd) |
| Fixture five warm white / cool white / light blue | `Fixture 5 Color Warm` / `Cool` / `Lightblue` |
| RGB two fifty five zero zero | `RGB 255 0 0` |
| Color two fifty five one twenty eight zero | `Color 255 128 0` ("one twenty eight" = 128 na *color / rgb / bpm*) |

Kleuren zoals in de opdrachtregel: red, green, blue, white, black, yellow, cyan, magenta, orange, pink, purple, amber, lime, teal, violet, light blue, warm, cool.

### Positie en bundel

| U zegt | Wat wordt uitgevoerd |
|---|---|
| Pan ninety / Pan fifty percent | `Pan 90` / `Pan 50%` |
| Tilt minus forty five / Pan plus fifteen | `Tilt -45` / `Pan +15` (een teken = relatief) |
| Fixture five home / center | `Fixture 5 Pan 50% Tilt 50%` |
| Zoom half / full / minimum / fifty | `Zoom Half` / `Zoom Full` / `Zoom Min` / `Zoom 50` |
| Focus twenty five | `Focus 25` |
| Gobo forty / gobo spin thirty | `Gobo 40` / `GoboSpin 30` |
| Prism one hundred | `Prism 100` |
| Strobe zero / shutter ten | `Strobe 0` / `Strobe 10` |
| Channel six one hundred twenty eight | `Channel 6 128` (kanaal 6 van de projector op DMX 128) |

### Master en blackout

| U zegt | Wat wordt uitgevoerd |
|---|---|
| Blackout | `Blackout` (omschakelen) |
| Blackout on / Blackout off | `Blackout On` / `Blackout Off` |
| Master eighty / Master full / Master minus ten | `Master 80` / `Master Full` / `Master -10` |

### Cuelijsten

| U zegt | Wat wordt uitgevoerd |
|---|---|
| Go / Next cue | `Go` |
| Back / Go back / Previous cue | `Back` |
| Pause / Resume / Stop | `Pause` / `Resume` / `Stop` |
| Go to cue five | `Go Cue 5` (ook *goto cue five*) |
| Cue list main go | `Cuelist main Go` |
| Cue list front of house back | `Cuelist "front of house" Back` |
| Cuelist two go | `Cuelist 2 Go` |
| Cuelist main fader eighty / Fader fifty | `Cuelist main Fader 80` / `Fader 50` |
| Cue five fade three / Cue five delay one point five | `Cue 5 Fade 3` / `Cue 5 Delay 1.5` |
| Store cue five (merge) | `Store Cue 5` (`Merge`) |
| Update / Clear | `Update` / `Clear` |

### Tijdcode en audio

| U zegt | Wat wordt uitgevoerd |
|---|---|
| Timecode play / pause / stop / reset / reverse | `Timecode Play` / `Pause` / `Stop` / `Reset` / `Reverse` |
| Timecode rate two | `Timecode Rate 2` |
| Tap | `Tap` (het tempo tikken) |
| BPM one twenty eight / BPM auto / BPM half | `BPM 128` / `BPM Auto` / `BPM Half` (ook *beats per minute*) |
| Audio start / stop / demo | `Audio Start` / `Stop` / `Demo` |

### Effecten, variabelen, programmer

| U zegt | Wat wordt uitgevoerd |
|---|---|
| Effect rainbow / Effect off | `Effect rainbow` / `Effect Off` |
| Variable warm white | `Variable "warm white"` |
| Manual / Manual color | `Manual` / `Manual Color` |

### Meerdere opdrachten

"Fixture one at full **then** fixture two at zero" → `Fixture 1 At Full; Fixture 2 At 0`.

---

## 4. Wat automatisch wordt gecorrigeerd

Whisper schrijft soms woorden die hetzelfde klinken maar in de opdracht geen zin hebben ("add" in plaats van "at", "true" in plaats van "thru"). OpenCue controleert **op welke plek in de opdracht** het woord staat en zet het passende opdrachtwoord in – alleen waar het past:

| Gehoord / geschreven | Wordt | Wanneer |
|---|---|---|
| add, ad, it, app | At | na een getal, vóór een getal ("fixture 5 **add** 70") |
| true, threw, till, through, until, to, too, drew, grew, crew, throw … | Thru | tussen twee getallen ("fixtures 1 **true** 5") |
| **2** (Whisper hoort "thru" als het getal *two*) | Thru | in een selectie precies tussen twee getallen ("fixtures one **two** five" = `Fixture 1 Thru 5`; ook "fixture 1-5" en "1, 2, 5") |
| eight (8) | At | in een selectie tussen twee getallen ("fixture 5 **eight** 70") |
| halve, calf | Half | altijd; "fixture 3 half" = `Fixture 3 At Half` |
| chanel, clair, stroke, pawn, tell, fate, delight … | Channel, Clear, Strobe, Pan, Tilt, Fade, Delay | afhankelijk van de positie (vóór een getal, of altijd) |
| oh | 0 | waar een getal moet staan ("at oh", "master oh") |
| picture, pitcher, fix sure, fixer | Fixture | altijd ("**picture** one to four") |
| for, to, too, won, ate, tree | 4, 2, 2, 1, 8, 3 | alleen waar een getal moet staan ("fixture **for** at fifty" → Fixture 4 At 50) |
| collar, caller | Color | altijd |
| pen, ban, pun | Pan | vóór een getal |
| till, tilted | Tilt | vóór een getal ("**till** minus ten") |
| queue, q, cute, cube, key | Cue | vóór een getal ("go **key** five") |
| fool | Full | altijd |
| of, own | Off, On | na Blackout |
| prison, prisms | Prism | altijd |
| strove | Strobe | altijd |
| paws, pours | Pause | altijd |
| affect, effects | Effect | altijd |
| tab | Tap | altijd |
| read, grin, grain, blew, wait … | Red, Green, Blue, White | na "color" of als kleurnaam |
| black out, black art, blackouts | Blackout | altijd |
| time code, cue list, grand master, go bo, b p m | Timecode, Cuelist, Master, Gobo, BPM | uitdrukkingen van meerdere woorden |

Verder:

- **Getalwoorden** → cijfers ("twenty one", "one hundred and five", "two point five", "minus ten percent").
- **Klankvergelijking:** een onbekend woord dat staat waar een bepaald opdrachtwoord moet staan en hetzelfde klinkt, wordt dat woord.
- **Kleine spelfouten** in sleutelwoorden → het dichtstbijzijnde opdrachtwoord ("blakout" → Blackout).
- **Varianten van het triggerwoord** ("open queue", "open Q", "OpenCue") worden aan het begin verwijderd, ook alles wat vóór het triggerwoord is gezegd.
- **Namen** (na *group, cuelist, effect, variable*) blijven zoals gesproken.
- **Procent** na Master, Fader, BPM en cuenummers wordt weggelaten ("master eighty percent" → `Master 80`), omdat de opdrachtregel daar geen procent kent.
- Inleidend gepraat vóór de opdracht ("set", "please", alles wat niet wordt begrepen) wordt weggelaten; de opdracht moet met een opdrachtwoord beginnen.

---

## 5. Wat niet met spraak werkt

In de **operatormodus** op de console (*Weergave → Operatormodus ...*) is de spraakbesturing **uitgeschakeld**, zodat op deze pc alleen mogelijk is wat het bedieningsoppervlak biedt; na het verlaten loopt ze weer als ze aan stond.

Voor de veiligheid voert spraakbesturing **nooit iets uit dat verwijdert of overschrijft**: `Delete …`, `Clear Clear`, `Overwrite`. De bel zegt dan "Niet met spraak". Typ deze opdrachten of gebruik de interface.

---

## 6. Als het niet werkt

| Weergave | Wat te doen |
|---|---|
| Microfoon geel | Lees de tooltip; *Instellingen → Triggerwoord* (juiste microfoon?) |
| "Spraakmodel ontbreekt" | *Instellingen → Dictatie → Nu laden* (en voor het triggerwoord: *Instellingen → Triggerwoord → Spraakmodel downloaden*) |
| "Niets begrepen" | Dichter bij de microfoon, duidelijker spreken, de opdracht direct na het triggerwoord zeggen |
| "Geen opdracht herkend" | De tekst begint niet met een opdrachtwoord – de bel toont wat is begrepen; spreek precies zoals in de opdrachtregel |
| Opdracht rood (✗) | De opdrachtregel zegt wat niet klopt (bijvoorbeeld de projector bestaat niet, "deze cuelijst heeft geen cues") |
| Het triggerwoord wordt niet herkend | Verhoog *Instellingen → Triggerwoord → Gevoeligheid* |
| Een woord wordt steeds verkeerd geschreven | Noteer wat Whisper schrijft (de tekst staat in het logboek) – de tabel met correcties is gemakkelijk uit te breiden |

Het triggerwoord wordt herkend door een klein offline model, de opdracht erna wordt door Whisper opgeschreven (ongeveer 1–3 seconden op een gewone computer). Harde muziek of lawaai in de ruimte verslechtert de herkenning – een microfoon dicht bij de mond helpt meer dan wat ook.
