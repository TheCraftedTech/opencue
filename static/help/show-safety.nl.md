# Back-ups, vergrendelingen en veilig afsluiten

Je hebt de show vóór het evenement geprogrammeerd en slaat nu **bewust niet op** terwijl hij draait – niets mag per ongeluk worden overschreven. OpenCue beschermt je op vier manieren: **back-ups op de achtergrond**, **herstellen** na een crash, een **vergrendeling** voor afgeronde shows en een **voorzichtige afsluitdialoog**. Deze handleiding legt alle vier uit, en hoe je een probleem meldt.

---

## 1. Back-ups op de achtergrond

OpenCue schrijft regelmatig de **huidige staat van je show** – inclusief wijzigingen die je *niet* hebt opgeslagen – naar een verborgen map. Je ziet hem pas als je hem nodig hebt. Een back-up **vervangt nooit je showbestand**.

- **Wanneer:** standaard elke **15 minuten**, maar **alleen als** de show niet-opgeslagen wijzigingen heeft en er sinds de laatste back-up iets is veranderd. Niets veranderd = niets geschreven.
- **Ook:** wanneer je afsluit zonder op te slaan, wanneer opslaan mislukte (bijvoorbeeld omdat de show vergrendeld is), en vlak voordat je een andere show opent of start terwijl deze nog niet-opgeslagen wijzigingen heeft.
- **Hoeveel:** de nieuwste **10** per show blijven bewaard, in totaal hoogstens 100; oudere worden automatisch verwijderd.
- **Waar:** de map `backups` in de gegevensmap (`%LOCALAPPDATA%\OpenCue\backups`). Een back-up is een gewoon showbestand.

### Instellingen

**Instellingen → Algemeen → Showback-ups**:

| Instelling | Betekenis |
|---|---|
| **De show op de achtergrond back-uppen** | Schakelt de hele functie aan of uit (standaard: aan). |
| **Elke (minuten)** | Het interval, 1 tot 240 (standaard 15). |
| **Bewaren per show** | Hoeveel back-ups van één show worden bewaard, 1 tot 50 (standaard 10). |
| **Back-up herstellen...** / **Map openen** | Opent de herstel-dialoog (sectie 2) of de map in Verkenner. |

De instellingen gelden voor het hele programma en kunnen vanaf elk apparaat worden gewijzigd, ook vanaf een apparaat op afstand.

---

## 2. Een back-up herstellen

**Bestand → Back-up herstellen...** (of de knop in de instellingen) toont alle back-ups, nieuwste eerst: shownaam, tijd, reden (automatisch, bij afsluiten, handmatig, vóór een herstel, opslaan mislukt) en grootte.

- **Herstellen** laadt de back-up als een **niet-opgeslagen show**. Het showbestand op schijf blijft precies zoals het is, ook als het vergrendeld is. Sla daarna op met **Opslaan** (of **Showbestand opslaan als...**) als je tevreden bent.
- De staat die je daarvoor had, wordt eerst geback-upt – ook een herstel kan dus niets kwijtmaken.
- **Nu back-uppen** maakt direct een back-up; **Verwijderen** verwijdert er een. Alles hier werkt ook vanaf een apparaat op afstand (*Map openen* toont daar de OpenCue-verkenner).
- Shows, lay-outs, podia en instellingen worden **veilig** weggeschreven: eerst naar een naastgelegen bestand, dan verwisseld – een crash of stroomuitval midden in het opslaan kan het bestaande bestand niet vernietigen.

### Na een crash

Is OpenCue niet goed afgesloten (crash, stroomuitval, taak beëindigd), dan **biedt het bij de volgende start de laatste back-up van die sessie aan**: *“OpenCue is niet goed afgesloten … Herstellen?”* – **Herstellen**, **Alle back-ups tonen** of **Niet nu** (de back-ups blijven beschikbaar onder *Bestand → Back-up herstellen...*).

---

## 3. Een show vergrendelen

Een afgeronde show kan worden **vergrendeld** zodat niemand hem per ongeluk wijzigt. Klik in het **bestandsbeheer** (*Bestand → Bestandsbeheer...*, soort *Shows*) op het **slotsymbool** in de rij van de show; klik nogmaals om te ontgrendelen.

Een vergrendelde show:

- is in de lijst gemarkeerd als **Vergrendeld** en toont een klein **slot** naast de shownaam in de bovenbalk zolang hij geladen is,
- **kan niet worden overschreven, hernoemd of verwijderd** – opslaan toont *“Niet opgeslagen: … is vergrendeld”*,
- kan nog wel worden **geladen**, **gedupliceerd** (de kopie is niet vergrendeld) en onder **een andere naam** worden opgeslagen met *Showbestand opslaan als...*.

De vergrendeling beschermt tegen vergissingen, niet tegen kopiëren: het bestand zelf kan nog met elk ander programma worden gewijzigd.

---

## 4. Veilig afsluiten

**Bestand → Afsluiten** (of de sluitknop) vraagt: **Opslaan en afsluiten**, **Afsluiten zonder opslaan** of **Annuleren**.

Kan de show **niet worden opgeslagen** maar heeft hij wijzigingen – hij is vergrendeld, het bestand is schrijfbeveiligd, de map is niet beschrijfbaar of het laatste opslaan mislukte – dan verandert de dialoog:

- Een **oranje vak** bovenaan zegt *“Deze show kan niet worden opgeslagen”* en noemt de redenen. Het zegt ook of er een back-upkopie van je wijzigingen wordt bewaard.
- **Als kopie opslaan en afsluiten...** vervangt *Opslaan en afsluiten*: je kiest een nieuwe naam, de show wordt daar opgeslagen, daarna sluit OpenCue af.
- **Afsluiten zonder opslaan** vraagt **twee klikken**: de eerste maakt de knop rood (*“Klik nogmaals: afsluiten en de wijzigingen kwijtraken”*), pas de tweede sluit af.

Ook dan wordt bij het afsluiten een back-up van je wijzigingen geschreven (als back-ups aan staan), zodat *Bestand → Back-up herstellen...* ze nog kan terugbrengen.

---

## 5. Een probleem melden

- **Help → Logmap openen** opent de map met `opencue.log`.
- **Help → Probleem melden...** kopieert de **diagnose** (versie, systeem, de laatste logregels – zonder toegangstokens of wachtwoorden) naar het klembord en opent de meldpagina van het project in je browser. Beschrijf wat je deed, plak de diagnose.
- Fouten in de gebruikersinterface worden als **OC-3601** in het log geschreven; een back-up die niet kon worden geschreven als **OC-3701** (zie de handleiding *Foutcodes*).
