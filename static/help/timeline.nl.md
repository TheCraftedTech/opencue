# Tijdlijn-editor en LTC

Met de **tijdlijn-editor** plaatst u cues en opdrachten grafisch op een tijdas – met de golfvormen van uw nummers eronder. Met **LTC** loopt OpenCue synchroon met een externe bron (een speler, dj- of showsoftware, een console) of stuurt het zelf een klok naar andere apparaten. Alles is gebouwd op de **globale tijdcode**.

---

## 1. Het idee in één minuut

- OpenCue heeft **één** klok, de **tijdcode** (paneel *Tijdcode*, weergave bovenaan de werkbalk). Ze loopt, stopt, springt – op alle apparaten tegelijk.
- Op bepaalde tijdstippen van deze klok gebeurt er iets: een **cue** met de trigger *Tijdcode* start, een **opdracht** van een opdrachtspoor wordt uitgevoerd, een **mediaspeler** start zijn nummer (*starttijd*). Dat gebeurt alleen als de klok **voorwaarts door** dat tijdstip loopt – springen en achteruit lopen triggeren niets.
- De klok kan door **drie bronnen** worden aangestuurd: deze computer (u drukt op Start), **MIDI-tijdcode** (*Instellingen → MIDI*) of **LTC** (*Instellingen → Tijdcode*). Wie er het eerst is, stuurt.
- De **tijdlijn-editor** toont dit alles op een tijdas en laat u het gemakkelijk plaatsen en verplaatsen – in plaats van elke tijd in het cuevenster te typen.

---

## 2. De tijdlijn-editor openen

- Als paneel in de indeling: *Bewerken → Paneel toevoegen → Media → **Tijdlijn-editor*** (het best breed).
- Kort als venster: *Weergave → Paneel als venster openen → **Tijdlijn-editor*** (alle panelen staan daar, bijvoorbeeld ook **Eenvoudige bediening**).

---

## 3. Hoe het eruitziet

- **Liniaal** bovenaan: klikken of slepen springt naar dat tijdstip.
- **Eén spoor per cuelijst**: elke cue met de trigger *Tijdcode* is een **markering** met nummer en naam. De lijstnaam links selecteert hem (voor de lade en "Cue hier zetten").
- **Opdrachtsporen** (rood / roze): opdrachten van de opdrachtregel op bepaalde tijdstippen – zie paragraaf 6.
- **Audiosporen** onderaan: **vanzelf** voor elk nummer dat een mediaspeler met de tijdcode meespeelt, met een **golfvorm** en dunne lijnen bij elke markering – u ziet of iets precies op de tel valt (paragraaf 5).
- **Lade** helemaal onderaan: de **cues zonder tijd** van de gekozen lijst.
- De gele **afspeelkop** is de globale tijdcode.

---

## 4. Markeringen bewerken en spoelen

| Actie | Hoe |
|---|---|
| Een markering **verplaatsen** | zijwaarts slepen met muis of vinger; hij klikt vast op het **raster** (houd **Shift** ingedrukt = geen raster) |
| Een markering **fijn verplaatsen** | op de markering klikken, dan `←` / `→` (één rasterstap; `Shift` = tien keer zoveel) |
| Een cue **zonder tijd** op de tijdlijn zetten | uit de **lade** op het spoor slepen – of de chip selecteren en op **Cue hier zetten** drukken |
| **Raster** | *uit*, 10 ms, frame (25 fps), 0,1 s, 1 s |
| **Zoomen** | toetsen `+` / `−`, Ctrl + muiswiel, **twee vingers** (iPad); *Alles tonen* (`F`) |
| **Volgen** | de weergave scrolt mee met de afspeelkop |

**Spoelen** kan op alle manieren:

| Toets / knop | Effect |
|---|---|
| De liniaal of de golfvorm **slepen** | springt continu daarheen (het geluid volgt) |
| Knoppen **±5 s** | vijf seconden terug / vooruit (snel klikken telt op) |
| Knoppen **vorige / volgende markering** (`[` / `]`) | springt naar de volgende cue- of opdrachttijd |
| `←` / `→` (focus in het paneel) | 1 s; met `Shift` 10 s; met `Alt` één frame (40 ms) |
| `Home` / `End` | naar het begin / het einde van de markeringen |
| `Spatie`, `L`, `K`, `J` | afspelen / pauze · vooruit · pauze · **achteruit** afspelen |
| Knop **Omkeren** | speelt de tijdcode achteruit af (triggert geen cues en opdrachten) |

---

## 5. Audio: vanzelf uit de mediaspelers

U hoeft in de tijdlijn geen nummer te kiezen. De tijdlijn kijkt zelf naar **wat met de tijdcode wordt meegespeeld**:

- Elke **mediaspeler** in de modus **Tijdcode** met een gekozen medium en zijn **starttijd** verschijnt als audiospoor: met naam, **golfvorm** en een **startmarkering** (notensymbool) op de starttijd. Een speler op **een ander apparaat** (bijvoorbeeld op de hoofdcomputer terwijl u op de iPad werkt) en de **schermen van de 3D-simulatie** verschijnen ook.
- Het **slepen van de startmarkering** (of er dubbel op klikken en de tijd typen) wijzigt de **starttijd van de mediaspeler** – het nummer begint dan op het nieuwe tijdstip.
- **Geluid toevoegen ...** maakt een **eigen geluid** van deze tijdlijn (het loopt synchroon met de tijdcode) voor het geval er nog geen mediaspeler is ingesteld. De luidsprekerknop dempt alleen deze eigen geluiden. Op de iPad heeft de browser een aanraking van het paneel nodig voordat geluid is toegestaan.
- OpenCue berekent de **golfvorm** één keer met de meegeleverde *ffmpeg* (een waarde per 10 ms) en onthoudt haar. Ontbreekt ffmpeg, dan meldt het spoor dat.
- Met **LTC** geldt hetzelfde: de mediaspelers volgen de tijdcode, wie hem ook aanstuurt – de audiosporen tonen dus altijd wat op welk tijdstip loopt.

---

## 6. Opdrachtsporen

Een **opdrachtspoor** voert **opdrachten van de opdrachtregel** uit op tijdstippen van de tijdcode – los van de cues, bijvoorbeeld `Blackout Off` om 1:30, `Cuelist Show Go` om 2:00 of `Effect Off` bij het refrein. Het hoort bij de **show** (opgeslagen en geëxporteerd met de show).

- **Nieuw opdrachtspoor**: knop **+**. Er kunnen er meerdere zijn (bijvoorbeeld "Licht", "Rook", "Video"); dubbelklikken op de naam hernoemt, de **×** verwijdert (twee keer klikken).
- **Een opdracht toevoegen**: de knop **Opdracht hier** (of `C`) zet een opdracht op het huidige tijdstip op het gekozen spoor – of **dubbelklik** op het spoor op die plek.
- Een klein venster vraagt om **tijd** en **opdracht**; `Enter` bevestigt. Elke markering kan worden **gesleept**, met de pijltoetsen verplaatst, met een **dubbelklik** opnieuw bewerkt en met `Del` verwijderd.
- De **server** voert de opdracht uit als de tijdcode **voorwaarts door** zijn tijdstip loopt – precies zoals cues (ook met LTC / MIDI-tijdcode). Hij verschijnt in de opdrachtgeschiedenis. Een sprong slaat hem over.
- In de **operatormodus** kunnen opdrachtsporen niet worden gewijzigd; ze lopen gewoon door.

---

## 7. Cues zetten met de muziek (opnemen)

Net als op een console, maar grafisch:

1. Maak uw cues (cuelijst) – hun tijd mag nog leeg zijn. Ze verschijnen in de **lade**.
2. Stel een **mediaspeler** in met uw nummer (modus Tijdcode, starttijd 0) – de golfvorm verschijnt vanzelf.
3. Kies de cuelijst en de eerste cue in de lade.
4. Start het afspelen (Spatie) en druk bij elke inzet op **Cue hier zetten** (of `Enter`): de gekozen cue krijgt de **huidige tijd**, daarna wordt de **volgende** cue gekozen.
5. Werk daarna rustig bij: sleep markeringen op de golfvorm en laat ze vastklikken.

Tip: met *raster 1 s* of *frame* landen de markeringen op ronde tijden, met *uit* op de exacte milliseconde.

---

## 8. LTC: tijdcode als audiosignaal

**LTC** (Linear Timecode) is een hoorbaar signaal – het klinkt als ruis – dat de tijd draagt. Het zit op één kanaal (meestal links), de muziek op het andere. *Instellingen → Tijdcode* toont bovenaan **wie de klok momenteel aanstuurt** (deze computer, MIDI-tijdcode of LTC) en heeft twee gebieden:

**Ingang: tijdcode lezen (LTC volgen)**

1. Zet **LTC volgen** aan, kies de **audio-ingang** (lijningang, USB-interface of het *systeemgeluid* van een uitvoerapparaat). Om te proberen is er het **testsignaal** (25 frames/s, geen apparaat nodig).
2. Kies het **kanaal** (links / rechts / mix), **Opslaan**. Eronder ziet u live **"Signaal gevonden: 00:01:12:05 · 25 fps"** en een niveaubalk.
3. Zodra een geldig signaal binnenkomt, **loopt de globale tijdcode mee**. Alle cues, opdrachten en mediaspelers volgen. **Pauze of stop van de bron** stopt hier de tijdcode ook, een **sprong** van de bron wordt gevolgd.
4. **24, 25, 29,97 (drop frame) en 30 frames per seconde** worden herkend.
5. Om zelf te spelen, zet u **LTC volgen** weer uit.

**Uitgang: tijdcode verzenden (LTC zenden)**

OpenCue wordt de klok voor andere apparaten: als u de tijdcode start (bijvoorbeeld Afspelen in het paneel *Tijdcode*), komt er **LTC uit een audio-uitgang** – een speler, console of recorder kan meelopen.

1. Zet **LTC zenden** aan, kies de **audio-uitgang** en het **kanaal** (*beide*, *alleen links* of *alleen rechts* – gebruik één kanaal als het andere muziek draagt).
2. Stel de **framesnelheid** (24 / 25 / 29,97 drop frame / 30) en het **niveau** in (sterk maar niet clippend; veel apparaten verwachten lijnniveau), **Opslaan**.
3. Het wordt **alleen verzonden terwijl de tijdcode vooruit loopt**; staat hij stil of loopt hij achteruit, dan is de uitgang stil. Springt u, dan begint het signaal meteen op het nieuwe tijdstip.
4. Volgt OpenCue zelf een LTC- of MIDI-bron, dan wordt de klok ook doorgegeven.

**Komt er niets binnen:** controleer de niveaubalk (te zacht?), het kanaal (links / rechts), of de ingang door een ander programma wordt gebruikt.

---

## 9. Opmerkingen

- Een **LTC- of MIDI-bron stuurt** de klok aan: Start / Stop in het tijdcodepaneel worden door de bron overstemd zolang die loopt.
- De tijden horen bij de **cues**, de **opdrachtsporen** en de **mediaspelers** van de show en worden ermee opgeslagen; de tijdlijn-editor is slechts het gereedschap ervoor.
- *Instellingen → Ingangen & uitgangen* toont in de groep **Tijdcode** in één oogopslag: wie de klok aanstuurt, LTC lezen / zenden, MIDI-tijdcode.
- Meer over de bronnen: handleiding **MIDI** (MIDI-tijdcode), handleiding **Toegang op afstand** (iPad), paneel **Tijdcode** (start, pauze, sprong, snelheid), **mediaspeler** (starttijd).
