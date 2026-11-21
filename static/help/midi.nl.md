# MIDI

Met **MIDI** bedient u OpenCue vanaf een controller, keyboard, pads of muzieksoftware – en OpenCue kan zelf MIDI verzenden. Een toets, fader, draaiknop of programmawijziging activeert een **opdracht van de opdrachtregel**, net als een eigen toetsenbordsnelkoppeling (zie *Toetsenbordsnelkoppelingen*) – met daarbovenop faders.

De mapping hoort bij het **programma**, niet bij de show: ze geldt voor alle shows en wordt in de appconfiguratie opgeslagen. U bereikt haar op vier manieren: het **MIDI-pictogram** rechtsboven in de werkbalk, **Instellingen → Bedieningen → MIDI**, **Bedieningen → MIDI-mapping …** en – voor toetsen en faders van een paneel – **MIDI toewijzen …** in de eigenschappen van het paneel. Het MIDI-apparaat zit aan de consolecomputer; het bewerken van de lijst werkt ook vanaf een tablet, leren en de monitor alleen op de consolecomputer.

---

## 1. Wat is MIDI? (kort)

MIDI verstuurt geen geluid, maar kleine **berichten**. U hebt er drie soorten nodig:

| Bericht | Wat uw apparaat meldt | In OpenCue |
|---|---|---|
| **Noot** | Een toets (pianotoets, pad) wordt ingedrukt of losgelaten. Elke heeft een nummer, bijv. 60 = **C4** (middelste C), en een **velocity** (0–127, hoe hard hij is aangeslagen). | Typen **Toets**, **Schakelaar**, **Vasthouden** – of **Fader** (de velocity wordt de waarde) |
| **Controller (CC)** | Een fader of draaiknop. Elke heeft een nummer (0–127) en een waarde 0–127. | Typen **Fader** (faders, potmeters) of **Encoder** (eindeloze knoppen) |
| **Programmawijziging** | Een "programma" met een nummer wordt gekozen. | Type **Toets** (bijv. programma 3 = `Go Cue 3`) |

Elk bericht heeft ook een **kanaal** (1–16), zodat meerdere apparaten één lijn kunnen delen. Weet u het niet: laat het op **Alle** staan.

---

## 2. Eerste stappen

1. Sluit het MIDI-apparaat via USB aan (Windows herkent het vanzelf – class-compliant apparaten hebben geen stuurprogramma nodig).
2. Klik op het **MIDI-pictogram** rechtsboven (of **Bedieningen → MIDI-mapping …**). Bovenaan staat welke apparaten worden herkend. De **monitor** onderaan toont live alles wat uw apparaat verstuurt – druk op een toets en kijk: `Note On C4 (60) · 100`.
3. **Nieuwe MIDI-mapping** → klik op het signaalveld in de rij → **druk op of beweeg** iets op het apparaat → **Toepassen**. Het signaal is geleerd.
4. Voer rechts de **opdracht** in, bijv. `Go`. Klaar – de toets activeert nu `Go`. De rij licht kort op als hij afgaat.

De mapping wordt meteen opgeslagen. De schakelaar **MIDI aan** bovenaan zet alles uit (OpenCue luistert dan naar geen enkel apparaat).

**Het werkbalkpictogram** toont de status: **groen** = een apparaat is klaar, **grijs** = geen apparaat aangesloten, **geel** = een apparaat kan niet worden geopend (meestal houdt een ander programma het vast), **rood en doorgestreept** = MIDI is uit. Een klik opent de mapping; de tooltip noemt de herkende apparaten.

**Instellingen → Bedieningen → MIDI** (zoals alle instellingen met *Opslaan*): MIDI gebruiken, **welke apparaten** worden gebruikt (elk aangesloten apparaat heeft een schakelaar – een uitgevinkt apparaat wordt nooit geopend), de **uitgang**, **tijdcode (MTC)** en **tempo van de MIDI-klok** (paragraaf 5b) en knoppen naar de mapping.

Onder **Instellingen → Ingangen & uitgangen → MIDI** ziet u de herkende apparaten, of ze nu worden gelezen, de uitgang en hoeveel mappings actief zijn.

---

## 3. De typen

| Type | Effect | Voorbeeld |
|---|---|---|
| **Toets** | De opdracht loopt wanneer de toets wordt ingedrukt. | Pad 1 → `Go`; Pad 2 → `Back`; Pad 3 → `Clear` |
| **Schakelaar** | Elke druk wisselt tussen de **opdracht** en de **uit-opdracht** (leeg = beide keren dezelfde opdracht). | `Blackout` (schakelt vanzelf om); of `Effect Rainbow` / `Effect Off` |
| **Vasthouden** | De **opdracht** loopt bij indrukken, de **loslaatopdracht** bij loslaten ("flash"). | `Group front At Full` / `Group front At 0` |
| **Fader** | De opdracht krijgt de waarde als `{value}`, geschaald naar het bereik **Van … Tot** (ook **Omkeren**). | Fader → `Master {value}` (0–100); Fader → `Cuelist main Fader {value}` |
| **Encoder** | Voor **eindeloze knoppen**: elke stap loopt als `{delta}` (met teken, maal **Stap**). Het encodertype (gebruikelijk / tekenbit / midden 64) stelt u in de rij in. | Knop → `Pan {delta}` (selecteer eerst projectoren) |

**Plaatshouders in de opdracht:** `{value}` (faderwaarde in het bereik Van–Tot), `{delta}` (encoderstappen, bijv. `+1` / `-2`), `{velocity}` (velocity 0–127), `{note}` en `{number}` (noot- / controller- / programmanummer), `{channel}`, `{raw}` (ruwe waarde 0–127).

**Start / Stop / Continue (transport):** u kunt ook *Start*, *Stop* en *Continue* van de muzieksoftware als signaal kiezen (type in het leervenster; ze hebben geen kanaal en geen nummer). Voorbeeld: Start → `Timecode Play`, Stop → `Timecode Stop`.

**Pickup:** een **fader** zonder motor staat vaak anders dan de waarde in het programma. Met **Pickup** neemt de fader pas over als hij de huidige waarde heeft bereikt of gepasseerd – geen sprong bij de eerste aanraking. Is de waarde intussen elders gewijzigd, dan moet hij haar opnieuw inhalen. Dit werkt voor `Master {value}`, `Fader {value}`, `Cuelist <naam> Fader {value}` en de helderheid of een bundelattribuut van een projector, groep of de selectie (`Fixture 5 At {value}`, `Group front At {value}`, `At {value}`, `Zoom {value}`); andere opdrachten nemen meteen over.

**Meer typen:** *Dubbelklik* (de opdracht loopt bij de tweede druk binnen 0,4 s) en *Lang indrukken* (ze loopt als de toets de ingestelde tijd wordt vastgehouden – bijv. 600 ms; eerder loslaten annuleert). Voor faders kiest u een **curve**: *Lineair*, *Langzame start* (fijne waarden onderaan) of *Snelle start*. **Aftertouch** (druk op een ingedrukt gehouden toets) en **kanaaldruk** kunnen ook als faders worden toegewezen. **Eén fader, meerdere opdrachten:** scheid ze met een puntkomma, bijv. `Master {value}; Group front At {value}`.

**Terugkoppeling naar het apparaat (leds, motorfaders):** kies in de rij onder **Feedback** een status van de console: *Blackout*, *Master*, *Selectie aanwezig*, *Cue actief*, *Tijdcode loopt* of *Cuelijstfader*. OpenCue verstuurt die als noot / controller / pitch bend **met hetzelfde nummer en kanaal** als het signaal naar de uitgang die dezelfde naam heeft als het apparaat – op een padcontroller licht de led op, een motorfader beweegt mee. Voor aan/uit-statussen stelt u **LED aan / LED uit** in (de velocity; op pads met kleuren is dat de kleur). Het wordt alleen verstuurd als de waarde verandert, en nadat een apparaat is aangesloten wordt alles opnieuw verstuurd.

Meer voorbeelden:

| Apparaat | Mapping |
|---|---|
| Programmawijziging (bijv. op een keyboard) | Toets, opdracht `Go Cue {number}` – programma 5 springt naar cue 5 |
| Toets met velocity | Fader (bron Noot), opdracht `Group front At {value}`, Van 0 Tot 100 – hoe harder, hoe helderder |
| Pitchbendwiel | Fader, opdracht `Master {value}` |
| Faderbank | één rij per fader (CC 1…8): `Fixture 1 At {value}`, `Fixture 2 At {value}` … |

Triggers: een toets gaat af bij **indrukken**. Een CC die als toets wordt gebruikt (de pads van veel controllers) gaat af bij een waarde **van 64 of meer**. Een fader verstuurt hoogstens **ongeveer 40 opdrachten per seconde** (snelle bewegingen worden samengevoegd, de laatste waarde komt altijd aan).

---

## 3b. Rijen kopiëren, exporteren, importeren, vanuit een paneel

- **Kopiëren** (pictogram naast de prullenbak): dupliceert een rij met type en opdracht, het signaal blijft leeg – handig voor een reeks vergelijkbare faders (fader 1 … 8).
- **Exporteren / Importeren** (onderaan het venster): slaat de mapping op als bestand (`opencue-midi-mapping.json`) of leest zo'n bestand. Bij het importeren worden de rijen **toegevoegd** – er wordt niets vervangen.
- **Sjabloon …** (onderaan het venster): maakt een **reeks** rijen – *Faderbank* (projectoren 1...8), *Cuepads*, *Transporttoetsen* (Go, Back, Pause, Blackout), *Master & blackout* – en laat u dan **de bedieningen na elkaar indrukken of bewegen** ("Signaal 2 van 8", *Overslaan* gaat verder, Annuleren beëindigt de reeks). Zo wijst u elke controller toe zonder nummers te kennen.
- Een **zoekveld** boven de lijst (signaal, opdracht, apparaat) en de **pijlen** op elke rij (omhoog / omlaag; uitgeschakeld tijdens zoeken).
- **Naar deze cue springen met een MIDI-toets …** in het venster van een **cue** (*Cue bewerken*): maakt een mapping `Cuelist "<lijst>" Go Cue <nummer>` en leert het signaal – de cue start dan bij een toetsdruk, **op elk moment** (een vrije "sprong"-toets). Voor een cue die binnen een reeks op zijn signaal wacht, zie de cuetrigger **MIDI** (paragraaf 5c).
- **MIDI toewijzen …** in de eigenschappen van een **knop, schakelaar of fader**: maakt een mapping met de opdracht van het paneel (schakelaar: aan- en uit-opdracht, fader: met Van/Tot) en leert meteen het signaal. De mapping blijft ook als u het paneel verwijdert.

---

## 4. Geldt voor, Uitvoeren, Geschiedenis

- **Signaal leren → Geldt voor:** *Alle apparaten* (elk apparaat dat dit signaal verstuurt, activeert) of *Alleen dit apparaat* (bijv. als twee controllers dezelfde nummers sturen).
- **Uitvoeren** uit: de opdracht wordt alleen **in de opdrachtregel geschreven**, niet uitgevoerd (om hem te controleren of aan te vullen).
- **In geschiedenis:** de opdracht verschijnt in de geschiedenis van de opdrachtregel (alle vensters zien hem).
- Er is geen controle op dubbele signalen: twee rijen met hetzelfde signaal gaan **allebei** af (het leervenster waarschuwt u).

**Veiligheid:** `Delete …` en opdrachten die `Overwrite` bevatten worden **nooit via MIDI uitgevoerd** (een per ongeluk aangeslagen toets mag geen gegevens vernietigen). `Clear Clear` is toegestaan.

---

## 5. OpenCue verstuurt MIDI: de opdracht `Midi`

De opdracht `Midi` verstuurt naar de **uitgang** (gekozen bovenaan het venster; **Automatisch** neemt het eerste echte apparaat, anders de Windows-synthesizer "Microsoft GS Wavetable Synth" – zo hoort u meteen iets):

| Opdracht | Effect |
|---|---|
| `Midi Note 60` | Speelt noot C4 (60), velocity 100, na 0,3 s weer uit |
| `Midi Note 60 90 Ch 2 Len 1` | Noot 60, velocity 90, kanaal 2, gedurende 1 seconde |
| `Midi On 60 100` / `Midi Off 60` | Noot aan / uit afzonderlijk (blijft tot u `Off` verstuurt) |
| `Midi CC 7 100` | Controller 7 op waarde 100 |
| `Midi PC 3` | Programmawijziging 3 |
| `Midi MSC Go 5 List 2` | Verstuurt **MIDI Show Control** (`Go`, `Stop`, `Resume`, `AllOff`, `Restore` ...; optioneel `List <n>`, `Device <0-127>`) |
| `Midi Panic` | All notes off (alle kanalen) |

Te combineren met knoppen, toetsenbordsnelkoppelingen, cueopdrachten of **spraakbesturing** ("OpenCue, MIDI note sixty") – bijv. een cue die een geluid in uw muzieksoftware activeert. Ook via de **REST-API**: `POST /api/v1/command` met `Midi Note 60`; `GET /api/v1/midi` geeft apparaten en status terug.

---

## 5b. Tijd en tempo van de muzieksoftware (MTC en MIDI-klok)

Twee schakelaars onder **Instellingen → Bedieningen → MIDI** laten OpenCue muzieksoftware (DAW) of een ander apparaat volgen. Beide reageren **alleen op het passende formaat en alleen als er echt iets geldigs binnenkomt** – anders gebeurt er niets. Zolang er een aan staat, blijven de gebruikte apparaten open.

**Tijdcode van MIDI (MTC).** Verstuurt de software *MIDI Timecode* (MTC, 24 / 25 / 29,97 / 30 frames per seconde), dan loopt de **globale tijdcode** gelijk met die tijd: cues met de trigger "Tijdcode", de tijdcodespeler en de panelen volgen. Alleen een **gatloze, plausibele stroom** wordt overgenomen (drie overeenkomende groepen, waarden in het geldige bereik); ruis, achteruit lopen en vreemde signalen worden genegeerd. Wijkt uw eigen klok meer dan 0,1 s af, dan wordt hij op de juiste tijd gezet. **Stopt de stroom** (software gestopt, kabel eruit), dan stopt de tijdcode. Springt de software in stilstand naar een positie (*full frame*), dan springt de tijdcode ook. Een tijdcode die u met de hand startte wordt **niet** gestopt als MTC ontbreekt; zolang MTC loopt, heeft MTC voorrang. De instellingen tonen de ontvangen tijd en de framesnelheid.

**Verzenden: OpenCue als tijdbron.** *Tijdcode versturen (MTC)* verstuurt de globale tijdcode als MIDI Timecode (framesnelheid 24 / 25 / 29,97 / 30; nauwkeurig getimede kwartframes, een full-framebericht bij sprongen) naar de gekozen uitgang. *MIDI-klok versturen* verstuurt *Start* / *Stop* en de klok op het tempo van het Audio-paneel terwijl de tijdcode loopt.

**Showcontrol ontvangen (MSC).** Met *Showbesturing ontvangen* en een **apparaat-ID** (0-127, 127 = alle) sturen GO, STOP, RESUME, ALL_OFF en RESTORE (ook met cue- en lijstnummer) de cuelijsten aan – bijv. vanuit een showprogramma of console. De opdracht `Midi MSC ...` verstuurt ze.

**Tempo van de MIDI-klok.** Een **stabiele MIDI-klok** (24 pulsen per kwartnoot, 30 tot 300 BPM) stelt het tempo in als vast tempo van het Audio-paneel (zoals de opdracht `BPM 128`) en volgt tempowisselingen. Wijs *Start*, *Stop* en *Continue* als signalen toe (zie boven).

Om het zonder software uit te proberen: een MIDI-tijdcodegenerator (er zijn gratis programma's en webpagina's) verstuurt via een virtuele MIDI-poort (onder Windows bijv. *loopMIDI*) – beide kanten kiezen dezelfde poort.

---

## 5c. Cuetrigger: MIDI

Naast *Go*, *Follow*, *Tijdcode* en *Audio* kan een cue de trigger **MIDI** hebben: hij wacht dan op **één MIDI-signaal** en gaat af als het binnenkomt – een **reeks die u speelt met een keyboard, een pad of een voetcontroller**. Kies in het cuevenster (*Cue bewerken*) de trigger *MIDI* en kies dan het **signaal** (of druk op **Signaal leren** en sla de toets aan – het wordt voor u ingevuld; leren werkt op de consolecomputer). In de cuelijst kunt u het ook in de triggercel typen (`midi note c4`, `midi cc 20 64`, `midi pc 5 ch 2`) of de opdracht `Cue 3 Trigger Midi Note 60` gebruiken (zie *Opdrachtregel*).

| Signaal | De cue gaat af … |
|---|---|
| **Noot** (toets / pad), nummer 0–127 | … wanneer de toets wordt ingedrukt (Note On; loslaten doet niets). |
| **Controller (CC)**, nummer 0–127, drempel 1–127 (standaard 64) | … wanneer de controllerwaarde van onderaf **tot** de drempel stijgt. Een pad dat als CC (127) wordt verstuurd gaat meteen af; een fader gaat af als hij voorbij de drempel wordt geduwd, en opnieuw nadat hij eronder is teruggetrokken en weer omhoog geduwd. |
| **Programmawijziging**, nummer 0–127 | … wanneer dit programma op het apparaat wordt gekozen. |

Elk signaal kan tot één **kanaal** (1–16) worden beperkt; *Alle* accepteert alle kanalen en alle apparaten.

Hoe het werkt:
- Net als de audiotrigger gaat de cue af als hij de **volgende cue** van een lopende lijst is: start eerst de lijst met *Go*, dan wacht de volgende MIDI-cue op zijn signaal. Daarna wacht de volgende cue (als die ook een MIDI-trigger heeft) op zijn beurt – zo kunt u een hele reeks aan toetsen of pads koppelen.
- Een korte pauze van 0,25 s na elke trigger voorkomt dat één slag twee cues start.
- **MIDI moet aan staan** (*Instellingen → MIDI → MIDI gebruiken*, of de schakelaar bovenaan het mappingvenster). OpenCue opent de MIDI-apparaten zelf zodra een cue een MIDI-trigger heeft – daarvoor hebt u geen mappingrij nodig – en geeft ze weer vrij als geen cue MIDI meer nodig heeft. Apparaten die u onder *Instellingen → MIDI* hebt uitgevinkt, blijven gesloten.
- De trigger werkt voor elke cuelijst afzonderlijk en ook vanuit het gezichtspunt van apparaten op afstand: het signaal komt van de MIDI-apparaten van de **consolecomputer**.
- **Verschil met de mapping** (paragraaf 3): een mappingrij voert een opdracht **op elk moment** uit (bijv. `Go`, of `Cuelist "Main" Go Cue 5` = daarheen springen). De cuetrigger is onderdeel van de **cue zelf** en telt alleen terwijl de cue de volgende is. Beide kunnen samen worden gebruikt; een signaal dat door beide wordt gebruikt, doet beide.

---

## 6. Als het niet werkt

| Probleem | Oplossing |
|---|---|
| Apparaat niet herkend | Een andere USB-kabel/-poort; **Instellingen → Ingangen & uitgangen** ververst de apparaten om de paar seconden; veel apparaten hebben na het aansluiten even tijd nodig. |
| "in gebruik?" bij het apparaat | **Een ander programma** (muzieksoftware, de editor van de fabrikant) heeft het apparaat geopend – onder Windows kan meestal maar **één** programma het lezen. Sluit het andere programma en zet dan **MIDI aan** uit en weer aan. |
| Monitor toont niets | De monitor loopt alleen terwijl het venster open is. Staat **MIDI aan** aan? |
| Een cue met de trigger **MIDI** gaat nooit af | Hij gaat alleen af als hij de **volgende cue** van een **lopende** lijst is (start de lijst eerst met *Go*). *MIDI aan* moet aan staan, het apparaat mag niet zijn uitgevinkt in *Instellingen → MIDI*, en nummer, kanaal en type moeten overeenkomen met wat de monitor toont als u de toets indrukt (gebruik *Signaal leren* in het cuevenster). |
| Toets activeert niets | Controleer kanaal / apparaat onder "Geldt voor"; test de opdracht met de hand in de opdrachtregel; licht de rij op in het venster? (dan komt het signaal aan en is de opdracht het probleem). |
| Fader springt | Zet **Pickup** aan in de rij (master en fader): de fader neemt pas over als hij de huidige waarde heeft bereikt. |
| Muzieksoftware en OpenCue moeten verbinden | Windows heeft daarvoor een **virtuele MIDI-poort** nodig (gratis, bijv. *loopMIDI*). Die verschijnt dan als ingang/uitgang in beide programma's. |

---

## 7. Beperkingen

- **Tablets:** de iPad (Safari) kan geen MIDI in de browser. MIDI-apparaten horen bij de consolecomputer; u kunt de mapping vanaf elk apparaat bewerken.
- **Meerdere programma's:** onder Windows leest meestal maar **één** programma een MIDI-apparaat (zie "in gebruik?"). Nieuwere Windows-versies (*Windows MIDI Services*) kunnen dat veranderen – OpenCue opent apparaten alleen als dat nodig is en geeft ze vrij met **MIDI aan** uit.
- **Netwerk-MIDI en virtuele poorten** worden door het besturingssysteem ingesteld (bijv. *loopMIDI*, *rtpMIDI*); ze verschijnen dan als elk apparaat.
- **Controllerprofielen:** in plaats van vaste profielen voor afzonderlijke modellen zijn er **sjablonen met een leerreeks** – ze werken met elke controller. Ledkleuren (velocities) verschillen per apparaat; ze worden onder feedback ingesteld als *LED aan / LED uit*.
- **Meerdere mappings om tussen te wisselen** (bijv. "podium" en "repetitie"): als bestanden via **Exporteren / Importeren** in het venster; er is geen aparte schakelaar.
- Pitchbend, aftertouch en kanaaldruk worden als faders beoordeeld; er is geen songpositie en er zijn geen MIDI-gebeurtenissen in de WebSocket-stroom van de API.
- Nog niet met alle apparaten geprobeerd: faders, encoders, pads en feedback zijn met kunstmatige berichten getest – de **monitor** in het venster toont wat uw apparaat echt verstuurt.
