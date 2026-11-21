# Opdrachtregel – Opdrachtenreferentie

De **opdrachtregel** bedient OpenCue door te typen, naar de stijl van professionele lichtconsoles. Ze vult de bediening met muis en aanraking aan met korte opdrachten die u kunt typen, koppelen en in cues kunt opslaan. Ze is beschikbaar als paneel **Opdrachtregel** (*Bewerken → Paneel toevoegen…*); de panelen **Opdracht-numpad** en **Opdrachtknoppen** schrijven voor de bediening met aanraking in dezelfde invoerregel.

Elke opdracht wordt op de server uitgevoerd en het resultaat wordt aan **alle** verbonden apparaten gemeld: projectorlijst, cuelijst en programmer worden overal tegelijk bijgewerkt, niet alleen waar u typte.

> De opdrachtwoorden zijn Engels – zoals op lichtconsoles. Hoofdletters en kleine letters maken **niet** uit bij opdrachten, attributen en namen.

---

## 1. Het idee in één minuut

Elke opdracht volgt hetzelfde patroon: **wat** – **welke** – **waarde**.

| Actie / object | ID / bereik | Eigenschap / doel |
|---|---|---|
| `Fixture` | `1` | – |
| `At` | – | `80` |
| `Store` | `Cue 1.5` | – |
| `Cue` | `1` | `Fade 3` |
| `Cuelist` | `Show` | `Go` |

- De **actie of het object** komt altijd eerst (`Fixture`, `Group`, `At`, `Color`, `Pan`, `Zoom`, `Store`, `Cue`, `Go`, `Cuelist` …).
- De **ID of het bereik** zegt wat wordt bedoeld: een projectornummer (FID), een naam, een cuenummer, de naam van een cuelijst of een bereik (`1 Thru 10`).
- De **eigenschap of het doel** is de eigenlijke waarde: procent, graden, tijd, naam, kleur.
- Opdrachten **bouwen op elkaar voort**, zoals op een echte console: eerst selecteert u (`Fixture 1 Thru 4`), dan werkt een waardeopdracht (`At 80`) op precies die selectie. De selectie wordt **door alle apparaten gedeeld**: een klik in de projectorlijst op het ene scherm en een `Fixture`-opdracht op een ander werken op dezelfde selectie.
- Tekst met spaties (een cuenaam, een lijstnaam) gaat tussen dubbele aanhalingstekens: `Label Cue 1 "Intro scene"`. Een woord tussen aanhalingstekens is altijd een **naam**, nooit een opdrachtwoord, zodat ook een groep met de naam "Color" kan worden aangesproken.
- De invoer wordt gecontroleerd: ongeldige getallen (`Zoom abc`), onbekende attributen of namen en ontbrekende waarden geven een foutmelding **zonder iets te wijzigen**.

```
Fixture 1 Thru 4 At 80
Fixture 1 Thru 4 Color Red
Store Cue 1 "Opening"
Go
```

---

## 2. Projectoren en groepen selecteren

| Opdracht | Effect |
|---|---|
| `Fixture 1` | Selecteert projector FID 1 (vervangt de huidige selectie). |
| `Fixture 1 Thru 10` | Selecteert FID 1 tot 10. |
| `Fixture 1 + 3` | Selecteert FID 1 **en** 3 (combineer zo vaak u wilt met `+`). |
| `Fixture 1 Thru 5 + 10` | Selecteert FID 1–5 en ook 10. |
| `Fixture 1 Thru 10 - 5` | Selecteert FID 1–10 **zonder** 5 (een `-` met spaties verwijdert; meerdere mogelijk: `- 5 - 7 Thru 8`). |
| `Next` / `Previous` | Selecteert de **volgende / vorige projector** op FID (loopt rond; zonder selectie is `Next` = de eerste, `Previous` = de laatste). Loop projectoren een voor een af. |
| `Fixture "Head 2"` | Selecteert de projector(en) met deze **naam** (ook combineerbaar met `+`). |
| `Group 1` | Selecteert de 1e groep in de groepenlijst. |
| `Group 1 Thru 4` | Selecteert de projectoren van groepen 1 tot 4. |
| `Group Front` | Selecteert de groep met deze **naam** (`Group "Front Truss"` als hij spaties bevat). |

`Group N` betekent de **N-de gemaakte groep**. De naam is eenvoudiger en robuuster: `Group Front` werkt ongeacht de volgorde.

Een enkel woord mag zonder aanhalingstekens worden geschreven als het niet gelijk is aan een opdrachtwoord en de naam echt bestaat. Zet anders namen met spaties, komma's, puntkomma's of `+`, en namen die op een opdracht of een getal lijken, tussen `"…"`.

### Groepen maken, hernoemen, verwijderen

De **huidige selectie** kan als groep worden opgeslagen:

| Opdracht | Effect |
|---|---|
| `Store Group "Front"` | Maakt de groep van de huidige selectie. |
| `Store Group "Front" Merge` | Bestaat hij al: de selectie wordt **toegevoegd**. |
| `Store Group "Front" Overwrite` | Bestaat hij al: de leden worden **vervangen**. |
| `Label Group Front "Stage front"` | Hernoemt (`Set Group 2 Name "Stage front"` werkt ook, eveneens op nummer). |
| `Delete Group Front` | Verwijdert de groep (`Delete Group 2` op nummer) – de projectoren blijven. |

Zonder selectie meldt `Store Group` een fout. Een bestaande naam (hoofdletterongevoelig) wordt nooit stilzwijgend overschreven. Een projector hoort bij hoogstens één groep.

---

## 3. Waarden instellen: At / Full

Werkt op de **momenteel geselecteerde** projectoren (dimmerkanaal).

| Opdracht | Effect |
|---|---|
| `At 80` | Dimmer op 80 % (`At 80%` werkt ook). |
| `At Full` | Dimmer op 100 %. |
| `At At` | **Alles aan**: dimmer 100 % **en kleur wit** (projectoren zonder kleur krijgen alleen de dimmer). **Zonder selectie geldt het voor ALLE projectoren** (de selectie blijft leeg) – het tegenovergestelde van `Clear Clear`. Met een selectie wordt alleen die selectie aangezet. Ook mogelijk: `Fixture 5 At At`, `At At Color Red` (alles aan, rood). |
| `Zero` | Selectie op 0 % (zoals `At 0`). |
| `Full` | Korte vorm zonder voorafgaand "At" – ook 100 %. |
| `At 0` | Dimmer op 0 % (uit). |
| `At +10` / `At -10` | Verhoogt / verlaagt de huidige dimmerwaarde met 10 procentpunten. |

Waarden worden beperkt tot 0–100 %. `At +` / `At -` verwijst naar de laatst in de programmer ingestelde waarde per projector (of naar de DMX-waarde die nu wordt uitgevoerd als er nog niets is geprogrammeerd).

Betrokken projectoren krijgen een rode statusmarkering in de projectorlijst – ze zijn nu "in de programmer" en kunnen met `Store Cue` worden opgeslagen.

### Master (totale helderheid)

`Master` (kort `GrandMaster`) schaalt de uitvoer van **alle** dimmerkanalen in procenten. De standaard is 100 %. De waarde blijft tot u hem wijzigt en wordt met het showbestand opgeslagen.

| Opdracht | Effect |
|---|---|
| `Master 80` / `Master At 80` | Totale helderheid 80 % (het woord `At` is optioneel). |
| `Master Full` | 100 %. |
| `Master -10` / `Master +10` | Met 10 procentpunten verlagen / verhogen. |

De master schaalt alleen dimmerkanalen; kleuren en pan/tilt blijven ongewijzigd. (De **fader van een cuelijst** is iets anders – zie hoofdstuk 10.)

### Blackout

`Blackout` zet de **helderheid van alle projectoren op 0** en herstelt haar bij de volgende `Blackout`. Het is een schakelaar, onafhankelijk van de master.

| Opdracht | Effect |
|---|---|
| `Blackout` | Omschakelen. |
| `Blackout On` / `Blackout Off` | Aan- / uitzetten (`1`/`0`, `True`/`False` werken ook). |

**Blackout heeft voorrang op alles** – faders, opdrachten, cues, overgangen en lopende effecten: zolang hij actief is, blijft de helderheid van elke projector op 0, in de DMX-uitvoer **en** in de 3D-simulatie. De waarden blijven behouden: tijdens een blackout kunt u de helderheid gewoon wijzigen, en na `Blackout Off` verschijnt de **laatst ingestelde** toestand. Projectoren **zonder** dimmerkanaal (zuiver RGB) worden via hun kleur verduisterd. Een pulserende gloeilampknop in de werkbalk toont een actieve blackout; klikken schakelt om. De toestand geldt voor alle apparaten maar wordt **niet** in de show opgeslagen.

### Tijdcode: `Timecode` / `TC`

De globale tijdcode (de interne klok) kan ook met een opdracht worden bediend – bijvoorbeeld in het veld **CMD** van een cue (`Timecode Play` start de klok wanneer de cue afgaat).

| Opdracht | Effect |
|---|---|
| `Timecode` | Toont de status (tijd, loopt/stilstaand, snelheid). |
| `Timecode At 4.3` | Springt naar 4,3 s (ook `00:00:04.300`, `1:04.300`; hoogstens 100 u). |
| `Timecode At 4.3 Play` | Springt en start (`Reverse` start achteruit). |
| `Timecode +5` / `Timecode -2` | Relatief: 5 s vooruit / 2 s terug. |
| `Timecode Play` / `Reverse` | Vooruit / achteruit lopen. |
| `Timecode Pause` | Pauze. |
| `Timecode Stop` (`Reset`) | Stoppen en op 00:00:00.000 zetten. |
| `Timecode Rate 2` | Snelheid (0,1 … 8; `0.5x` werkt ook). |

Springen laat tijdcodecues niet afgaan; alleen vooruit lopen doet dat.

### Audio en tempo: `Tap` / `BPM` / `Audio`

Bedient het *Audio*-paneel (zie de handleiding *Audio*) – ook bruikbaar in het veld **CMD** van een cue.

| Opdracht | Betekenis |
|---|---|
| `Tap` | Het tempo tikken: vanaf de tweede tik wordt het tempo uit uw tikken bepaald (handmatig) en begint de beat op de tik. |
| `BPM` | Toont het tempo en de modus. |
| `BPM 128` | Vast tempo (30 … 300). |
| `BPM Auto` | Terug naar automatische detectie. |
| `BPM Half` / `BPM Double` | Het tempo halveren / verdubbelen (als de detectie het dubbele / de helft vond). |
| `Audio Start` / `Audio Stop` | De gekozen bron openen / sluiten. |
| `Audio Demo` | De demobeat starten. |
| `Audio` (`Audio Status`) | Toont of audio loopt, het tempo en het niveau. |

### OSC versturen: `Osc`

`Osc /address [value ...]` verstuurt een OSC-bericht naar het doel dat onder **Bedieningen → OSC ...** (*Versturen naar*) is ingesteld: `Osc /opencue/go`, `Osc /light/1 0.5 hello`. Waarden zijn getallen (gehele getallen gaan als integers), `true` / `false` of tekst. Zonder doel meldt de opdracht dat. Zie de handleiding *Planning, tijdstip en OSC*.

### MIDI versturen: `Midi`

Verstuurt MIDI naar de gekozen uitgang (zie de handleiding *MIDI*): `Midi Note 60 [velocity] [Ch 2] [Len 0.5]` speelt een noot en zet hem weer uit, `Midi On 60` / `Midi Off 60` afzonderlijk, `Midi CC 7 100` stelt een controller in, `Midi PC 3` een programmawijziging, `Midi Panic` zet alle noten uit.

---

## 4. Kleur en positie: Color / RGB / Pan / Tilt

Ook deze werken op de **momenteel geselecteerde** projectoren.

| Opdracht | Effect |
|---|---|
| `Color Red` | Zet de kleur op rood (benoemde kleur, lijst hieronder). |
| `Color #FF8000` | Kleur als hex (de korte vorm `#F80` werkt ook). |
| `Color 255 128 0` | Kleur als drie waarden 0–255 (rood / groen / blauw). |
| `RGB 255 0 0` | Hetzelfde (consolenotatie). |
| `Pan 180` | Beweegt pan naar 180°. |
| `Tilt -45` | Beweegt tilt naar -45°. |
| `Pan 50%` | Pan in procent van het bereik (0–100 %; 50 % = midden). |
| `Pan +10%` / `Tilt -5%` | Relatief ten opzichte van de huidige waarde, in procent van het bereik. |
| `Pan +15` / `Tilt -15` | Relatief in graden (met teken). |

**Benoemde kleuren:** `Red`, `Green`, `Blue`, `White`, `Black`, `Yellow`, `Cyan`, `Magenta`, `Orange`, `Pink`, `Purple`, `Amber`, `Lime`, `Teal`, `Violet`, `LightBlue`, `Warm`, `Cool`.

**Graden voor pan/tilt:** OpenCue leest het echte bewegingsbereik (fysiek bereik) uit het GDTF-profiel van de projector, dus verschillende projectoren kunnen bij dezelfde gradenwaarde iets anders staan. Heeft het profiel geen bereik, dan geldt de standaard: **pan -270° tot +270°, tilt -135° tot +135°**.

---

## 5. Bundelattributen en kanalen: Zoom, Gobo, CH …

Naast helderheid, kleur en positie kan **elk kanaal** van een projector worden ingesteld – op twee manieren: op **attribuutnaam** (procent, dezelfde logica als de faders in de programmer) of rechtstreeks op **kanaalnummer** of **naam** (zoals "DMX direct").

### Attributen in procenten

| Opdracht | Effect |
|---|---|
| `Zoom 50` | Zoom op 50 % (ook `Zoom Full`, `Zoom Half`, `Zoom Min`, `Zoom 50%`). |
| `Focus 25` | Focus. |
| `Gobo 40` / `Gobo2 40` | Goborad 1 / 2 (selectie; getal = procent van het kanaal). |
| `GoboSpin 30` / `Gobo2Spin 30` | Rotatie / positie van het goborad. |
| `Prism 100` | Prisma. |
| `Strobe 0` (`Shutter 0`) | Shutter / strobe. |
| `Zoom +10` / `Zoom -20` | Relatief ten opzichte van de huidige waarde (procentpunten). |

Alle waarden lopen van 0–100 en worden opgeslagen zoals de faders: `Store Cue` neemt ze over. Ontbreekt het kanaal bij een projector (een zuivere dimmer heeft geen zoom), dan wordt hij overgeslagen en de terugmelding zegt dat: `OK: Zoom 50 applied to 3 fixtures (Zoom not available on 1 of 3 fixtures)`. Heeft **geen enkele** geselecteerde projector het kanaal, dan is het een fout en verandert er niets.

### Kanalen op nummer: `CH` / `Channel`

| Opdracht | Effect |
|---|---|
| `CH6 128` | Kanaal 6 **van de projector** (1 = eerste kanaal) op DMX-waarde 128. |
| `Channel 6 128` | Hetzelfde, met een spatie geschreven (`CH 6 128` werkt ook). |
| `CH6 50%` | Met `%`: procent in plaats van DMX-waarde (50 % = 128). |
| `CH6 +20` | Relatief: 20 DMX-stappen meer (`-20` minder). |
| `CH6 Full` | 255 (ook `Half` = 50 %, `Min` = 0). |

Het kanaalnummer verwijst naar de **volgorde in de modus van de projector** (zichtbaar in het tabblad *DMX direct* van de programmer), niet naar het DMX-adres: `Fixture 5 Thru 8 CH6 255` stelt het 6e kanaal van elke geselecteerde projector in, waar hij ook is gepatcht. De waarde is **0–255** zoals in DMX direct.

### Kanalen op naam

Elke GDTF-kanaalnaam van de projector kan rechtstreeks als clausule worden gebruikt (waarde in **procenten**):

```
Fixture 1 Frost 50        Iris 30        Cyan 100
Channel Frost1 50         CH Frost 50
```

De naam mag worden ingekort zolang hij ondubbelzinnig blijft (`Frost` voor `Frost1`); gangbare korte namen zijn ingebouwd (`Cyan`, `Magenta`, `Yellow` voor CMY-kanalen, `Red`/`Green`/`Blue` voor RGB-kanalen, `Intensity` voor de dimmer). De automatische aanvulling toont welke namen een projector heeft (hoofdstuk 14).

Kanalen met een eigen attribuut (dimmer, pan, tilt, zoom, focus, goborad, prisma, shutter) worden als dat attribuut opgeslagen; alle andere (frost, iris, kleurenwiel, fijne kanalen …) als ruwe kanaalwaarden. `Store Cue` neemt beide over.

---

## 6. Variabelen, effecten, handmatig

Variabelen (presets) en effecten kunnen op de **huidige selectie** worden toegepast – alleen of als clausule achter een selectie, zoals elk ander attribuut.

| Opdracht | Effect |
|---|---|
| `Variable "Warm White"` | Past de variabele toe **en koppelt hem**: de projectoren volgen hem tot een waarde, een effect of een cue het attribuut overneemt (wijzig de variabele en de projectoren veranderen mee). Korte vormen: `Var`, `Preset`. |
| `Effect Rainbow` | Wijst het effect toe (de categorie volgt uit het effect). Meerdere projectoren lopen met een fase-verschuiving zoals in het keuzemenu. |
| `Effect Off` | Beëindigt **alle** effecten van de selectie; `Effect Off color position` alleen de genoemde categorieën. |
| `Manual` | Terug naar **handmatig**: geeft de variabelekoppeling **en** het effect voor alle categorieën vrij; de laatste uitvoerwaarden blijven. |
| `Manual color` | Alleen die categorie (`dimmer`, `color`, `position`, `zoom`, `focus`, `gobo`, meerdere achter elkaar, of `all`). |

Namen van variabelen en effecten zijn uniek in OpenCue en hoofdletterongevoelig. Met spaties ofwel tussen `"…"` ofwel gewoon achter elkaar (`Variable warm white`). Een onbekende naam geeft een fout met de lijst van bestaande. De automatische aanvulling stelt variabelen (met hun type) en effecten (met hun categorie) voor.

```
Fixture 1 Thru 4 Variable "Warm White" Variable Wide Effect Wave
Group Front Manual color
Effect Off
```

---

## 7. Gecombineerde opdrachten

Selectie- en waarde-/attribuutopdrachten kunnen in **één regel** worden gecombineerd – gelijkwaardig aan twee opdrachten achter elkaar, maar sneller te typen:

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

Meerdere attribuutclausules mogen direct op elkaar volgen (`Fixture 1 At 80 Color Red` stelt dimmer EN kleur in één keer in). Bevat één clausule een fout (typfout in het attribuut, ongeldig getal, een kanaal dat geen enkele projector heeft), dan verandert **noch** de selectie **noch** een waarde.

---

## 8. Gekoppelde opdrachten (komma of puntkomma)

Meerdere complete opdrachten kunnen in **één** regel worden gekoppeld, gescheiden door een komma of puntkomma. Ze worden na elkaar uitgevoerd:

```
Fixture 1 At 100, Fixture 2 At 50
Fixture 1 Color Red; Fixture 2 Color Blue; Fixture 3 At 0
```

Mislukt één deel, dan worden de andere toch uitgevoerd; het logboek toont alle deelresultaten in één regel, gescheiden door `|`. Komma's en puntkomma's **binnen aanhalingstekens** (bijvoorbeeld in een cuenaam) worden correct genegeerd: `Label Cue 1 "Act 1, scene 2"` wordt niet gesplitst.

---

## 9. Clear: `Clear` tegenover `Clear Clear`

| Invoer | Effect |
|---|---|
| `Clear` | Geeft alleen de huidige selectie vrij. Geprogrammeerde waarden blijven. |
| `Clear Clear` | **Volledige reset:** zet **alle** projectoren volledig terug – dimmer, kleur en pan/tilt (zoals ingesteld onder *Instellingen → Standaardwaarden → Clear Clear*: standaard dimmer 0 %, kleur wit, pan/tilt 0°; projectoren zonder dimmerkanaal blijven zwart), zoom, focus, goborad 1 en 2 met rotatie, prisma, strobe **en elk ander kanaal van de projector** (frost, iris, kleurenwiel, snelheid, fijne kanalen …) op 0. Beëindigt alle effecten, leegt de programmer en geeft de selectie vrij. |
| `Clear` twee keer **binnen 1,0 seconde** | Hetzelfde als `Clear Clear` – snel twee keer `Clear` typen activeert de volledige reset. |
| `Clear` … (meer dan 1,0 s) … `Clear` | Twee onafhankelijke acties "selectie vrijgeven" – **geen** reset. |

---

## 10. Cuelijsten: op naam selecteren, Go, fader, beheren

Cue-opdrachten werken op de **actieve cuelijst** (keuzemenu in het cuelijstpaneel). Met `Cuelist` (gelijkwaardig: `QList`, `Q-List`, `CL`, `List`, `Exec`) kunt u elke lijst **op naam** aanspreken – hoofdletterongevoelig; namen zijn uniek in OpenCue, dus het is altijd duidelijk. Zoals overal: **eerst de categorie, dan de naam** – een kale lijstnaam (`Show Go`) is geen opdracht.

| Opdracht | Effect |
|---|---|
| `Cuelist Show` | Maakt "Show" de **actieve** lijst. |
| `Cuelist "Cue List 1"` | Naam met spaties (ook zonder aanhalingstekens als hij ondubbelzinnig is: `Cuelist Cue List 1`). |
| `Cuelist 2` | De 2e lijst in de volgorde van het keuzemenu (zoals `Exec 2`). |
| `Cuelist Show Go` | Zet lijst "Show" één stap verder – **zonder** de actieve lijst te wijzigen. |
| `QList Show Go` | Hetzelfde met de categorie `QList`. |

### Lijsten maken, hernoemen, dupliceren, verwijderen

| Opdracht | Effect |
|---|---|
| `Cuelist New "Act 1"` | Maakt een nieuwe lijst (namen zijn uniek; zonder naam: `Cue List 1`, `Cue List 2` …). Was er geen, dan wordt hij actief. |
| `Cuelist Show Rename "Act 1"` | Hernoemt (een al gebruikte naam wordt geweigerd). |
| `Cuelist Show Duplicate` | Kopieert met alle cues, nieuwe ID's, naam `Show (copy)`; met een naam: `Duplicate "Backup"`. |
| `Cuelist Show Delete` | Verwijdert de lijst (`Delete Cuelist Show` werkt ook) – **zonder** bevestiging; een lopende overgang eindigt. |

Een lijst met de naam "New" bereikt u tussen aanhalingstekens: `Cuelist "New" Go`. Na de lijstnaam mag elke cue-opdracht volgen; hij geldt dan voor precies die lijst en de terugmelding noemt haar tussen haakjes (`OK: Go Cue 1 [Show]`).

### Afspelen

| Opdracht | Effect |
|---|---|
| `Go` | Volgende cue (aan het einde van de lijst springt Go naar de eerste cue, zoals de knop). |
| `Go Cue 3` / `Go 3` | Springt rechtstreeks naar cue 3 (zachte overgang met zijn fadetijd). |
| `Goto Cue 3` | Hetzelfde als `Go Cue 3`. |
| `Back` / `Go Back` | Vorige cue. |
| `Pause` / `Resume` | De lopende overgang pauzeren / voortzetten. |
| `Stop` | De overgang afbreken (waarden blijven); beëindigt ook alle lopende effecten. |
| `Fader 50` | De **fader** van de lijst (mix tussen handmatige waarde en cue, zoals de executorfader) op 50 %. Ook `Fader Full`, `Fader +10`, `Fader At 30`. |
| `Off` / `Off Exec 1` / `Off Cuelist Show` | Zet de actieve-cuetoestand van de actieve / de 1e / de genoemde lijst terug. (Executors zijn nog geen aparte objecten; `Exec N` betekent de N-de lijst. `Off` laat de laatste DMX-waarden niet uitfaden.) |

```
Cuelist Show Go                Go Cue 3
Cuelist "Encore" Goto Cue 1    QList "Encore" Fader 40
Cuelist Show Fader +10         Cuelist 2 Back
```

---

## 11. Cues beheren

Alle cue-opdrachten werken op de **actieve cuelijst** – of, met een voorafgaande `Cuelist <name>`, op de genoemde lijst.

| Opdracht | Effect |
|---|---|
| `Store Cue 1` | Slaat een nieuwe cue op met **elke wijziging ten opzichte van de cue ervoor** (zie hieronder) – ook een *Clear* die alles donker maakte. Waarden die u expliciet hebt aangeraakt, zijn altijd inbegrepen. |
| `Store Cue 1.5` | Decimale getallen maken het later invoegen tussen bestaande cues mogelijk. "Ervoor" is dan cue 1 (de cue met het eerstvolgende kleinere nummer), welke cue er nu ook actief is. |
| `Store Cue 1.5 CueOnly` | Bij invoegen in het midden behoudt de **volgende cue** zijn vorige uiterlijk: waarden die de nieuwe cue wijzigt en die de volgende cue zelf niet instelt, worden daar met de oude toestand vastgelegd. Zonder `CueOnly` erft de volgende cue ze via tracking. |
| `Store Cue 4 "Intro"` | Met een naam (anders heet de cue "Cue 4"). |
| `Store Cue 3 Merge` | Bestaat cue 3: alleen wat in het beeld verschilt ten opzichte van **deze cue** komt erin, de rest blijft. Zonder `Merge`/`Overwrite` meldt `Store Cue 3` een fout in plaats van een dubbel nummer te maken. |
| `Store Cue 3 Overwrite` | Bestaat cue 3: zijn inhoud wordt volledig vervangen door de wijzigingen ten opzichte van de cue ervoor (naam, tijden, trigger blijven). |
| `Store Cue 6 Absolute` | De cue speelt later **precies de toestand af die u bij het opslaan zag** (alle projectoren, alle kanalen). Werkt ook met een lege programmer: de huidige toestand wordt als momentopname opgeslagen. `Relative` (standaard) speelt alleen uw wijzigingen af. |
| `Update` | Neemt alles wat in het beeld verschilt van de **actieve** cue over in die cue (alleen gewijzigde kanalen). Zonder toevoeging geldt de standaard uit *Instellingen → Standaardwaarden → Nieuwe cues → Update* ("Elke keer vragen" werkt voor de opdracht als tracking). |
| `Update Tracking` | Volgende cues die deze waarden zelf niet instellen, nemen ze bij het afspelen over. |
| `Update CueOnly` | Zoals `Update Tracking`, maar de volgende cue behoudt zijn vorige uiterlijk. |
| `Delete Cue 3` | Verwijdert cue 3. Met een bereik: `Delete Cue 3 Thru 5`. |
| `Move Cue 1 At 5` | Hernummert cue 1 naar 5 (de lijst sorteert opnieuw). Bestaat het doelnummer, dan wordt een fout gemeld. |
| `Label Cue 1 "Intro"` / `Set Cue 1 Name "Intro"` | Hernoemt cue 1. |

**Hoe een cue wordt opgeslagen.** Een cue bevat alleen wat hij ten opzichte van de cue ervoor wijzigt (tracking). Bij het opslaan zoekt OpenCue dus de cue die **vóór** de nieuwe zou spelen – die met het eerstvolgende kleinere nummer, ook voor `1.5` midden in de lijst –, leest zijn toestand en slaat precies de verschillen met het beeld dat u nu ziet op. Dat omvat een *Clear*: die maakt alles donker en is dus een grote wijziging. Is er geen cue ervoor (de eerste van de lijst), dan krijgt hij alleen de waarden die u expliciet hebt aangeraakt. Is er niets gewijzigd, dan zegt `Store Cue` dat en maakt geen cue aan (behalve met `Absolute`).

**De weergave "gewijzigd".** De rode markering in de projectorlijst en de puntjes op de tabbladen tonen hetzelfde: wat nu verschilt van de **actieve cue** (naast wat u met de hand hebt bediend). Bij meerdere lijsten telt de actieve cue van de **laatst gebruikte** lijst (Go, Back, sprong, selecteren, opslaan). Terwijl die lijst overgaat, blijft de weergave zoals ze is; met een executorfader onder 100 % is ze leeg (de uitvoer wordt met opzet gemengd). Het is alleen een weergave – wat wordt opgeslagen is altijd de wijziging ten opzichte van de cue ervoor.

**Na het opslaan** is de opgeslagen cue de **actieve cue** van de lijst (het beeld komt ermee overeen); de volgende `Go` start dus de cue erna. De programmer wordt voor de opgeslagen projectoren geleegd (de rode markering verdwijnt). Nieuwe cues krijgen standaard `Fade = 0.0 s` (harde omschakeling).

**Relatief en absoluut:** elke cue **slaat altijd beide** op in het showbestand: de *wijzigingen* (wat u aanraakte) en de *volledige toestand* van alle projectoren op het moment van opslaan (dimmer, kleur, positie, gobo, zoom, focus en elk ander kanaal; variabelen blijven plaatshouders). Het **afspelen** bepaalt wat er bij Go gebeurt:

- **Relatief** (tracking, standaard): alleen de opgeslagen wijzigingen worden ingesteld, al het andere blijft zoals de vorige cue het achterliet.
- **Absoluut**: elke projector wordt precies op de opgeslagen toestand gezet – cue 6 ziet er dus precies uit zoals bij het opslaan, ook als u eerst cues 1-5 doorliep. Effecten die de cue niet heeft, eindigen ook op alle projectoren.

De standaard voor nieuwe cues stelt u in onder *Instellingen → Standaardwaarden → Nieuwe cues* (daar ook trigger, delay, fadetijd, effect-fade in/uit, MIB en wat *Update* doet). `Store Cue 6` zonder toevoeging neemt altijd deze standaarden; wat u expliciet opgeeft (`Absolute`, `Relative`) wint. In het opslagvenster kunt u het voor één cue wijzigen, later in het bewerkvenster, door dubbelklikken op de kolom **Afspelen** of met de opdracht `Cue 6 Mode Absolute` / `Cue 6 Mode Relative`. Omdat de toestand altijd wordt opgeslagen, kan elke cue op elk moment worden omgeschakeld. Onder *Standaardwaarden → Programmastart* stelt u ook in hoe OpenCue na het starten staat (grand master uit de show of een vaste waarde, blackout aan/uit) en het niveau van de executorfader voor nieuwe lijsten. Oudere cues zonder opgeslagen toestand gedragen zich, als absoluut, als de tracking van de lijst tot die cue.

**Effecten** zijn altijd een complete toestand: een cue onthoudt alle effecten die liepen toen hij werd opgeslagen. `Update` neemt dat ook over – een effect dat u hebt gestopt, valt uit de cue.

### Cues in de lijst bewerken (muis en aanraking)

- **Eén cel:** dubbelklik op een cel (naam, trigger, tijden, MIB, CMD …) om haar rechtstreeks in de lijst te bewerken. Het bewerkvenster (rechtsklik → *Bewerken*) blijft voor alles tegelijk.
- **Meerdere cues tegelijk:** sleep met de muis een **rechthoek** over de cellen (bij aanraking: kort ingedrukt houden, dan slepen). **Alleen de cellen binnen de rechthoek** worden geselecteerd, niet de hele rij. Een **dubbelklik** op een geselecteerde cel wijzigt dan **alle geselecteerde cellen van die kolom** tegelijk – bijvoorbeeld de fadetijd van meerdere cues op 1 zetten. Hetzelfde werkt voor hele rijen die met `Ctrl`-klik of `Shift`-klik zijn geselecteerd. Een gewone klik selecteert weer een hele rij. Het cuenummer wordt altijd één voor één gewijzigd (nummers zijn uniek).
- **Triggers met symbolen:** Go, Follow, Tijdcode, Audio, MIDI en Tijdstip hebben elk een symbool – in de lijst en als rij knoppen in het bewerkvenster (met een korte opmerking over wanneer de cue start).
- **Verplaatsen:** wijzig het cuenummer – de cue verhuist naar zijn nieuwe plek.
- **Kopiëren:** selecteer cues → **Kopiëren** (of rechtsklik → *Kopiëren …*). Kies de lijst en het nummer van de eerste kopie; de andere behouden de afstand van de originelen. Nummers die al bestaan worden nooit overschreven – dan wordt er niets gekopieerd en noemt OpenCue de bezette nummers.
- **Ongedaan maken:** `Ctrl+Z` / `Ctrl+Y` maken wijzigingen aan cues ongedaan en opnieuw (zie *Toetsenbordsnelkoppelingen*).

### Cue-eigenschappen: `Cue <number> <property> <value>`

Alles in het bewerkvenster (en in de kolommen van de cuelijst) kan met een opdracht worden ingesteld. In plaats van een nummer werkt ook een bereik: `Cue 1 Thru 5 Fade 2` wijzigt cues 1 tot 5.

| Opdracht | Effect |
|---|---|
| `Cue 1 Fade 3` / `Cue 1 Delay 1.5` | Algemene (dimmer)tijden in seconden. |
| `Cue 1 Color Fade 2` / `Color Delay` | Eigen tijd voor kleur (`Colour` werkt ook). |
| `Cue 1 Pos Fade 4` / `Pos Delay` | Eigen tijd voor positie (`Position Fade` werkt ook). |
| `Cue 1 Beam Fade 0` / `Beam Delay` | Eigen tijd voor bundel (gobo, prisma, strobe, focus …). |
| `Cue 1 Zoom Fade 2` / `Zoom Delay 1` | Eigen tijd voor zoom. |
| `Cue 1 Color Fade -` | Een `-` (of `default`) zet de groep terug op de algemene tijd. |
| `Cue 1 FX In 2` / `FX Out 1` | Effecten in/uit faden in seconden (`Effect In` / `Effect Out` werken ook). |
| `Cue 1 Trigger Go` / `Follow` | Trigger van de cue. |
| `Cue 1 Trigger Timecode 00:01:30` | Trigger door de globale tijdcode (tijd zoals bij `Timecode At`). |
| `Cue 2 Trigger Audio Beat 4` | Trigger door de muziek: gaat bij elke 4e beat af zodra hij de volgende cue is (het Audio-paneel moet draaien). Bronnen: `Beat`, `Kick`, `Snare`, `Hat` (het getal = elke n-de, standaard 1) en `Level`, `Bass`, `Mid`, `High`, `B1` … `B8` (het getal = drempel in %, standaard 70). |
| `Cue 2 Trigger Audio Kick` | Gaat af bij de volgende basdrumslag. |
| `Cue 2 Trigger Audio Bass 80` | Gaat af als de bas 80 % bereikt. |
| `Cue 3 Trigger Midi Note 60` | Trigger door een MIDI-signaal: gaat af als deze toets wordt ingedrukt, zodra de cue de volgende cue van een lopende lijst is. `Note` neemt een getal (0–127) of een notennaam (`Note C4`), `CC <number> [threshold]` gaat af als een controller de drempel bereikt (standaard 64), `PC <number>` bij een programmawijziging. Voeg `Ch <1-16>` toe voor één kanaal (standaard: elk). Voorbeelden: `Cue 3 Trigger Midi Note C4 Ch 2`, `Cue 4 Trigger Midi CC 20 100`, `Cue 5 Trigger Midi PC 3`. MIDI moet aan staan (handleiding *MIDI*, paragraaf 5c). |
| `Cue 3 Trigger Clock 19:30 Mon-Fri` | Trigger door de **klok**: zodra de cue de volgende cue van een lopende lijst is, wacht hij op dit tijdstip (en deze dagen: `Mon-Fri`, `Sat,Sun`, `weekdays`, `weekend`, `daily` – zonder dagen: elke dag; seconden toegestaan: `19:30:15`). Zie de handleiding *Planning, tijdstip en OSC*. (`Trigger Time` blijft de tijdcodetrigger.) |
| `Cue 1 MIB Auto` (`Off` / `On`) | Move In Black. |
| `Cue 1 Mode Absolute` (`Relative`) | Afspelen: precies de opgeslagen toestand of alleen de wijzigingen (zie boven). |
| `Cue 1 Cmd "Fixture 1 At 0; Go"` | Opdracht(en) die de cue uitvoert als hij afgaat (hoofdstuk 12). |
| `Cue 1 Name "Intro"` | Naam. |

---

## 12. CMD: opdrachten aan een cue koppelen

Elke cue heeft een optioneel tekstveld **CMD** (rechtsklik → Bewerken → sectie "MIB en CMD", dubbelklik in de kolom van de cuelijst, of met de opdracht `Cue 3 Cmd "…"`). Bevat het een opdracht, dan voert OpenCue die **automatisch** uit wanneer de cue wordt getriggerd (door `Go`, een automatische `Follow` of het contextmenu "Hierheen faden") – voordat de eigenlijke overgang begint.

Meerdere opdrachten worden gescheiden door een **komma of puntkomma**:

```
Fixture 1 At 0
Fixture 3 Thru 6 Color Blue
Fixture 1 At 0; Fixture 2 Zoom 30; Cuelist Encore Go
```

Het resultaat verschijnt in dezelfde gedeelde opdrachtgeschiedenis als een getypte opdracht, zodat zichtbaar blijft dat een cue een actie heeft getriggerd. Het veld neemt tot 200 tekens. CMD mag **elke** opdracht uit deze referentie bevatten, ook gekoppelde en gecombineerde – een cue kan een andere lijst starten met `Cuelist Encore Go`. Recursieve `Go Cue`-aanroepen zijn mogelijk, maar OpenCue herkent geen eindeloze lussen tussen gekoppelde CMD-cues.

---

## 13. Terugmelding in het logboek

Elke uitgevoerde opdracht levert één regel op in het logboekgebied van het paneel, met een tijdstempel:

```
[20:45:01] OpenCue> Fixture 1 Thru 10
           OK: 10 fixtures selected
[20:45:07] OpenCue> At 80
           OK: At 80 applied to 10 fixtures
[20:45:12] OpenCue> Store Cue 1
           OK: Cue 1 stored
```

Foutieve opdrachten worden **rood** gemarkeerd:

```
[20:46:40] OpenCue> At 80
           At: no fixtures selected
[20:46:55] OpenCue> Go Cue 99
           Cue 99 not found
[20:47:02] OpenCue> Fixture 1 Colr Red
           Unknown attribute: Colr
```

Gekoppelde opdrachten geven **één** regel met alle deelresultaten gescheiden door `|`. Het logboek is identiek op **alle** verbonden apparaten – elke opdracht, waar hij ook is getypt (of door het CMD van een cue is uitgevoerd), verschijnt in elk geopend opdrachtregelpaneel. Logtekst kan worden geselecteerd en gekopieerd.

---

## 14. Toetsenbord en automatische aanvulling

| Toets | Effect |
|---|---|
| `Enter` | Voert de opdracht uit en leegt de invoer. |
| `Pijl omhoog` | Vorige (oudere) opdracht. |
| `Pijl omlaag` | Volgende (nieuwere) opdracht, of terug naar het concept dat u was begonnen. |
| `Tab` | Neemt het eerste voorstel over; elke volgende `Tab` gaat naar het volgende. |
| `Shift` + `Tab` | Zoals `Tab`, achteruit. |
| `Esc` | Sluit de voorstellenlijst. |

**Automatische aanvulling:** tijdens het typen (en bij klikken in het veld) verschijnt boven de invoer een lijst met passende vervolgen. Aan het begin van een regel toont ze **alleen de categorieën** (`Fixture`, `Group`, `Cuelist`, `Cue`, `Go` …) – namen en waarden komen daarna. De lijst kent de **huidige toestand**, niet alleen de opdrachtwoorden:

- na `Fixture ` de nummers (met de apparaatnaam) en de namen,
- na `Group ` de groepen; na `Cuelist ` de cuelijsten (namen met spaties worden automatisch tussen `"…"` gezet),
- na een projectorselectie de attributen en precies de **kanalen die deze projectoren hebben** (`Frost1`, `Iris`, `ColorSub_C` … met het kanaalnummer als aanwijzing),
- na `Go `, `Cue `, `Delete Cue ` de cues van de (genoemde) lijst met hun namen, daarna de eigenschappen (`Fade`, `Color Fade`, `FX In`, `Trigger` …),
- na `Color ` de kleurnamen, na `Zoom ` waarden (`Full`, `Half`, `Min`),
- na `Variable ` / `Effect ` de variabelen (met type) en effecten (met categorie); na `Manual ` de categorieën; na `Store ` / `Delete ` / `Label ` `Cue` en `Group`; na `Cuelist ` eerst `New`; na `Blackout ` `On` / `Off`.

Cursieve regels zijn **aanwijzingen** over de verwachte waarde (`<0-100> | +<n> | -<n> (%)`, `<0-255> (DMX) | <0-100>%`) en kunnen niet worden ingevoegd. De lijst verwijst altijd naar de **laatste deelopdracht** (na de laatste komma/puntkomma). Een klik op een item voegt het ook in. De hele grammatica zit in de server; de interface toont alleen wat de server voorstelt, dus voorstellen wijken nooit af van de echte parser.

Een kleine **schakelaar** helemaal rechts van de invoerregel zet voorstellen aan en uit (opgeslagen in de appconfiguratie, geldt voor alle apparaten).

In *Paneeleigenschappen → Moduleinstellingen* kunt u ook de tekst-, succes- en foutkleuren van het logboek wijzigen.

---

## 15. Snelle referentie

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
Cue 1 FX In 2  Cue 1 Trigger Follow   Cue 1 Trigger Timecode 00:01:30   Cue 3 Trigger Midi Note 60   Cue 1 MIB Auto   Cue 1 Cmd "Fixture 1 At 0; Go"

Timecode Play    Timecode At 4.3    Timecode Stop
```
