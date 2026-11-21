# Audio: licht dat op muziek reageert

OpenCue kan naar muziek **luisteren** en lampen erop laten reageren: helderder met de bas, een flits bij elke kick, kleuren die op de beat veranderen, een chase die in de maat loopt. De analyse draait live op de console, heeft geen internet nodig en neemt slechts enkele procenten van één processorkern.

---

## 1. Het idee in één minuut

- Het **Audio-paneel** neemt een geluidsbron en analyseert die: luidheid, een spectrum, de slagen van **basdrum, snare en hi-hat**, het **tempo (BPM)** en de positie binnen de beat.
- De resultaten zijn voor effecten beschikbaar als **variabelen** (`a_level`, `a_bass`, `a_kick`, `a_beat_phase` ...). Een **audio-effect** is een gewoon effectscript dat ze leest. Het werkt zoals elk ander effect: wijs het in de programmer aan projectoren toe, sla het op in cues, fade het in en uit.
- 33 kant-en-klare audio-effecten worden met het programma meegeleverd. Ze dragen de tag **Audio** (automatisch gezet zodra een effect audiowaarden leest) – kies de tag in het venster voor het effecttype om ze te tonen.
- Zonder draaiende bron zijn alle audiowaarden `0`: een audio-effect blijft gewoon donker of op zijn ruststand.
- Cues kunnen ook **op de muziek** starten: de cuetrigger *Audio* (paragraaf 8).
- De eigen knoppen, faders en schakelaars van de console kunnen de muziek volgen (paragraaf 9) en de REST-API kan de audio lezen en bedienen (paragraaf 10).

---

## 2. Snel aan de slag

1. Voeg het paneel toe: **Bewerken → Paneel toevoegen…** → categorie *Media en tijd* → **Audio**.
2. Kies **Demobeat** in de bronnenlijst en druk op **Starten**. Een drumloop van 120 BPM wordt geanalyseerd – u ziet het spectrum, de lampjes *Kick / Snare / Hi-hat / Beat* flitsen en het tempo verschijnt.
3. Selecteer in de programmer enkele projectoren, open het tabblad **Effecten** en klik op **Effect toevoegen**, kies het effecttype **Kick Flash** (of *Bass Dimmer*, *Beat Chase* ... – tip: filter op de tag *Audio*) en maak het aan. De projectoren flitsen nu mee met de demobeat.
4. Zet de bron om naar uw echte muziek (volgende paragraaf).

Bestaande installaties krijgen de nieuwe effecten via het **Bestandsbeheer** (lijst *Effecten*) met **Standaardeffecten herstellen**. Dit maakt alleen *ontbrekende* bestanden aan en overschrijft nooit: hebt u eerder een oudere versie hersteld, verwijder dan eerst de oude `audio_*.fx`-bestanden in het bestandsbeheer en herstel daarna opnieuw.

---

## 3. De bron kiezen

De lijst toont alles wat Windows kent:

| Groep | Wat het is | Typisch gebruik |
|---|---|---|
| **Systeemgeluid** | Wat deze computer afspeelt via een luidspreker of koptelefoon ("loopback"). Eén item per uitvoerapparaat. | Muziek van dezelfde computer (dj-software, Spotify, browser). Geen kabel, geen microfoon. |
| **Ingangen** | Microfoons, lijningangen en USB-audio-interfaces. | Muziek van een mengpaneel of een telefoon: steek de kabel in de **lijningang** of de interface. Een laptop met één gecombineerde headsetaansluiting behandelt die als *microfoon*: het signaal is zwakker, verhoog de **ingangsversterking**. Een microfoon in de ruimte werkt ook, maar de muziek moet hard en duidelijk zijn. |
| **Test** | De demobeat. | Effecten uitproberen zonder muziek. |

Items met *(standaard)* zijn die welke Windows standaard gebruikt. **Opnieuw zoeken** (de knop met pijlen) zoekt opnieuw naar apparaten nadat u iets hebt aangesloten.

Druk op **Starten**. De bron blijft open tot u op **Stoppen** drukt; de volgende programmastart opent hem vanzelf weer. Kan een bron niet worden geopend, dan zegt het paneel waarom (in gebruik door een ander programma, geblokkeerd in de Windows-privacy-instellingen *Microfoon*, losgekoppeld).

---

## 4. Wat het paneel toont

- **Spectrum:** 32 balken van 30 Hz tot 16 kHz (lage tonen links). Het kader gloeit bij elke beat.
- **Lampjes:** *Kick*, *Snare*, *Hi-hat* lichten bij elke slag op; *Beat* bij elke tel van het tempo.
- **Niveau** met een *Overbelasting*-markering: licht op als het signaal clipt (te hard bij de ingang; verlaag het volume of de versterking).
- **Tempo:** de BPM in grote cijfers, een beat-led, een balk met de positie binnen de beat en een dunne balk voor hoe zeker de detectie is.

---

## 5. Tempo: automatisch, getikt of vast

- **Automatisch** detecteert het tempo uit de muziek (70 - 180 BPM). Het heeft een paar seconden en een vaste beat nodig; het volgt tempowisselingen.
- **Tap:** tik op de knop in de maat van de muziek (ook de opdracht `Tap`). Vanaf de tweede tik wordt het tempo uit uw tikken bepaald en begint de beat precies op de tik. Het tempo is dan *Handmatig*.
- **÷2 / ×2:** wanneer de detectie de helft of het dubbele van de snelheid vond (typisch bij zeer langzame of zeer snelle muziek).
- **Handmatig:** het tempo ligt vast; typ het in het veld. Met *Handmatig tempo: de beat volgt de muziek* past de beatpositie zich nog zachtjes aan de slagen aan. Zonder muziek loopt een vast tempo als een **metronoom** – effecten met `a_beat_phase` blijven in de maat lopen.
- **Automatisch** schakelt terug naar detectie.

Opdrachten: `Tap`, `BPM 128`, `BPM Auto`, `BPM Half`, `BPM Double`, `Audio Start`, `Audio Stop`, `Audio Demo`, `Audio Status`.

---

## 6. Instellingen

| Instelling | Wat ze doet |
|---|---|
| **Ingangsversterking** | Versterkt (×0,1 tot ×10) een zwak signaal, bijv. een microfoon. |
| **Automatische versterking** | De analyse meet zich af aan de luidste delen van de laatste seconden, zodat een zacht nummer werkt als een hard nummer. Zet haar uit voor een vaste schaal (dan werkt de versterking direct). |
| **Beatgevoeligheid** | Hoger: ook zachte slagen tellen (risico: valse slagen). Lager: alleen duidelijke slagen tellen. |
| **Afvlakking** | Hoe langzaam de niveaus en banden terugvallen. |
| **Tijdsverschuiving** | −100 tot +200 ms. Positief: het licht reageert **eerder** – gebruik dit als lampen of luidsprekers te laat zijn. |

De instellingen horen bij de console (niet bij een show of een paneel) en worden automatisch opgeslagen. Elk apparaat met een Audio-paneel toont en bedient dezelfde bron.

---

## 7. De kant-en-klare audio-effecten

| Effect | Categorie | Wat het doet |
|---|---|---|
| Band Bars | Dimmer | Elke projector toont één frequentieband: het eerste de lage, het laatste de hoge tonen (herhaalt bij meer dan 8 projectoren). |
| Bass Dimmer | Dimmer | De helderheid volgt de bas van de muziek. |
| Beat Chase | Dimmer | Een chase die bij elke beat (of elke n-de) een stap zet. |
| Beat Pulse | Dimmer | De helderheid pulseert in de maat van de muziek: helder op de beat, daarna zacht wegvallend. |
| Beat Strobe | Dimmer | Strobe in de maat van de muziek: meerdere flitsen per beat, vergrendeld op het tempo. |
| Beat Toggle | Dimmer | Schakelt bij elke beat (of elke n-de) tussen twee groepen, hard of overgefade (zacht). |
| Hi-Hat Sparkle | Dimmer | Bij elke hi-hat-slag fonkelen willekeurig gekozen projectoren. |
| Kick Chase | Dimmer | Een chase die bij elke basdrumslag een stap zet (in plaats van op de beat). |
| Kick Flash | Dimmer | Elke basdrumslag laat de lampen flitsen en uitdoven. |
| Level Dimmer | Dimmer | De helderheid volgt de totale luidheid. |
| Snare Flash | Dimmer | Elke snareslag (of klap) laat de lampen flitsen en uitdoven. |
| Beat Color | Kleur | De kleur verandert bij elke beat (of elke n-de) en is het helderst op de beat. |
| Beat Color Chase | Kleur | Een gekleurd licht (A) loopt over een achtergrondkleur (B), één stap per beat (of elke n-de). |
| Beat Color Fade | Kleur | Fadet tussen twee kleuren in de maat van de muziek. |
| Beat Color Strobe | Kleur | Een gekleurde strobe in de maat van de muziek: meerdere flitsen per beat, afwisselend tussen kleur A en B. |
| Color Blend | Kleur | Mengt van kleur A (zacht) naar kleur B (hard). |
| Color Hit | Kleur | De basiskleur flitst naar de flitskleur bij elke slag van de gekozen drum. |
| Hi-Hat Color Sparkle | Kleur | Bij elke hi-hat-slag flitsen willekeurig gekozen projectoren in een willekeurige kleur (binnen het kleurbereik). |
| Hue Drift | Kleur | De kleuren drijven door het kleurbereik, één volledige cyclus duurt `beats` beats. |
| Kick Color Flash | Kleur | De basiskleur flitst naar de flitskleur bij elke basdrumslag. |
| Spectrum Color | Kleur | De kleur wordt uit de muziek gemengd: bas = rood, middentonen = groen, hoge tonen = blauw. |
| Spectrum Hue | Kleur | De kleur volgt het geluid: basrijke muziek toont het begin van het kleurbereik, heldere klanken het einde. |
| Bass Tilt | Positie | De tilt volgt de bas: zacht = omlaag, sterke bas = omhoog (rond de basispositie). |
| Beat Circle | Positie | De koppen doorlopen een cirkel in de maat van de muziek: één ronde duurt `beats` beats. |
| Beat Fan | Positie | De projectoren waaieren uit en sluiten zich in de maat van de muziek. |
| Kick Tilt Punch | Positie | Bij elke basdrumslag geven de koppen een tilt-stoot en zakken terug naar de basispositie. |
| Level Spread | Positie | Hoe harder de muziek, hoe wijder de projectoren uitwaaieren (symmetrisch rond de basispositie). |
| Pan/Tilt Sway | Positie | De koppen bewegen in de maat van de muziek. |
| Snare Pan Snap | Positie | Bij elke snareslag springt elke kop naar de volgende van vier pan-posities. |
| Beat Zoom Pulse | Zoom | De zoom pulseert bij elke beat: hoog op de beat, daarna terugvallend naar laag. |
| Kick Zoom Punch | Zoom | De zoom stoot bij elke basdrumslag van laag naar hoog en valt terug. |
| Bass Focus | Focus | De focus volgt de bas van de muziek. |
| Beat Gobo Change | Gobo | De gobo verandert bij elke beat (of elke n-de). |

Bijna elk effect heeft opties om **animaties om te schakelen** en een **strobe** toe te voegen: *strobe* (flitsen per seconde, 0 = uit), *mode* (bijvoorbeeld allemaal samen / even-oneven afwisselend / willekeurig), *direction* (chase vooruit, achteruit, heen en weer, willekeurig), *every* (elke n-de beat schakelen), *soft* (harde schakeling of overfade). Het zijn gewone effecten: sla ze op in cues, varieer ze, kopieer ze.

---

## 8. Cuetrigger: Audio

Naast *Go*, *Follow*, *Tijdcode* en *MIDI* (handleiding *MIDI*) kan een cue de trigger **Audio** hebben: hij gaat dan vanzelf af **op de muziek**. Kies in het cuevenster de trigger *Audio*, kies **één bron** en zo nodig een waarde – in de cuelijst kunt u haar ook typen (`audio kick`, `audio beat 4`, `audio bass 70`) of de opdracht `Cue 2 Trigger Audio Beat 4` gebruiken.

| Bron | Waarde | De cue gaat af … |
|---|---|---|
| **Beat (tempo)**, **Kickdrum**, **Snare**, **Hi-hat** | elke n-de (1 tot 64, standaard 1) | … bij elke n-de beat / slag. |
| **Totaalniveau**, **Bas**, **Midden**, **Hoog** of een van de **acht banden** (met hun Hz-bereik in de lijst) | drempel in % (standaard 70) | … wanneer dit deel van het geluid **tot** de drempel stijgt van onderaf. |

Hoe het werkt:
- De cue gaat af als hij de **volgende cue** van een lopende lijst is: start eerst de lijst met *Go*, dan wacht de volgende audiocue op zijn gebeurtenis. Nadat hij is afgegaan, wacht de cue erna (als die ook de trigger *Audio* heeft) op zijn beurt – zo kunt u een hele reeks aan de muziek koppelen.
- De teller (*elke n-de*) begint op 0 wanneer een nieuwe cue actief wordt.
- Met een drempel gaat de cue één keer af als het niveau die bereikt; hij wordt pas weer scherpgesteld nadat het niveau duidelijk eronder is gevallen (ongeveer 80 % van de drempel). Is het niveau al hoger wanneer de cue de volgende wordt, dan wacht hij op de volgende stijging.
- Na een trigger is er een korte pauze (0,25 s), zodat één slag nooit twee cues start.
- Het **Audio-paneel moet draaien** (een bron gestart); zonder geluid gaat niets af. De trigger werkt voor elke cuelijst afzonderlijk.

---

## 9. Knoppen, faders en schakelaars die op de muziek reageren

De eigen **Knop**-, **Fader**- en **Schakelaar**-panelen van de console kunnen de muziek als *signaal* gebruiken – in *Volgt de status van* (een fader beweegt met de muziek, een schakelaar schakelt met het signaal) en in de **voorwaarden van regels** (kleur, tekst of opdracht wanneer …). De signalen staan in de groep **Audio**:

| Signaal | Betekenis |
|---|---|
| **Audiosignaal aanwezig** | aan zolang een bron open is en er iets wordt afgespeeld |
| **Totaalniveau**, **bas**, **midden**, **hoog** | 0–100 % |
| **Kickdrum**, **snare**, **hi-hat**, **beat** (puls) | springen bij elke slag naar 100 % en doven uit |
| **Tempo (BPM)** | het gedetecteerde of ingestelde tempo |

Voorbeelden: een fader die de bas volgt als niveaumeter; een knop die rood oplicht als het tempo tussen 120 en 130 BPM ligt; een schakelaar die toont of er muziek binnenkomt. De audiobron draait op de console; een paneel hoeft alleen op het scherm van een willekeurig apparaat te staan – de metingen worden precies zolang naar een apparaat verstuurd als zo'n paneel (of het *Audio*-paneel) daar open is.

## 10. Audio via de API

De REST-API kan de analyse lezen (`GET /api/v1/audio`), de bron openen en sluiten, de instellingen wijzigen en het tempo tikken (`PUT /api/v1/audio`, `POST /api/v1/audio/tap`, recht *Audio*), en de **live gebeurtenissenstroom** (`GET /api/v1/events?events=audio,beat,hit`) meldt de bron, elke beat en elke drumslag op het moment dat ze gebeuren. Zie de handleiding *REST-API*.

## 11. Uw eigen audio-effect schrijven

Open de **Effectenstudio**, maak een effect en lees de audiovariabelen – zie de handleiding *Effectenstudio*, paragraaf *Audiovariabelen*. Een eerste voorbeeld:

```
#NAME My Flash
#CATEGORY dimmer
#RATE 40
#VAR peak Slider 100 0 100 1

loop() {
  dimmer = peak * a_kick;
}
```

De voorvertoning van de studio speelt een voorbeeldbeat (120 BPM), zodat u meteen ziet hoe de curve zich gedraagt.

---

## 12. Als iets niet werkt

| Probleem | Controleer |
|---|---|
| De bron kan niet worden geopend | Een ander programma gebruikt hem exclusief; de microfoon is geblokkeerd in de Windows-privacy-instellingen (*Instellingen → Privacy → Microfoon*); het apparaat is losgekoppeld. |
| Het paneel toont niets / alles vlak | Is de bron *gestart*? Beweegt de volumemeter van Windows? Verhoog de **ingangsversterking**. Bij *Systeemgeluid* moet het programma echt naar dat uitvoerapparaat afspelen. |
| *Overbelasting* brandt | Het signaal is te hard: verlaag het volume bij de bron of de ingangsversterking. |
| BPM springt of is de helft / het dubbele | Druk op **÷2 / ×2**, tik het tempo of leg het vast met *Handmatig*. Muziek zonder vaste beat (klassiek, spraak) heeft geen detecteerbaar tempo. |
| Lampen reageren te laat | Gebruik de **Tijdsverschuiving** (positieve waarden). |
| Een audio-effect blijft donker | Geen bron actief, of de gevoeligheid is te laag voor de muziek; verhoog de *gain*-schuif van het effect. |
