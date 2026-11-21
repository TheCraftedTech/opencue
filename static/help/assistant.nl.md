# AI-assistent

De **AI-assistent** is een chat met een taalmodel dat op **uw eigen computer** draait (of op een andere in uw netwerk) via **Ollama**. Er wordt niets naar internet verstuurd: OpenCue praat alleen met het serveradres dat u invoert. De AI schrijft elk antwoord **zelf** – OpenCue verzint geen antwoordteksten.

> **Stand van zaken:** de modus **Chat** en de modus **Werk** werken. Werk kan de show **lezen** (projectoren met alle details, groepen, cuelijsten, effecten, variabelen), **projectoren wijzigen** (helderheid, kleur, pan / tilt, zoom ... – nadat het u heeft gevraagd) en heeft een rekenmachine, willekeurige getallen en de tijd. De **Gids** legt het programma uit aan de hand van de handleidingen (zonder iets te verzinnen) en biedt knoppen die vensters openen (zie paragraaf 7).

---

## 1. Instellen

1. Installeer **Ollama** (ollama.com) op deze of een andere computer en download één keer een model, bijv. `ollama pull qwen2.5-coder:3b`. Daarna is geen internet meer nodig.
2. Open in OpenCue **Instellingen -> AI-assistent** en zet bovenaan de **hoofdschakelaar *AI-assistent inschakelen*** aan – zolang die uit staat, is de rest van de pagina vergrendeld.
3. Voer onder **Verbinding** het **serveradres** in (standaard `http://127.0.0.1:11434`) en klik op **Verbinding testen**.
4. Kies het **standaardmodel** en klik rechtsonder op **Opslaan** (het venster blijft open).
5. Voeg met **Paneel toevoegen** het paneel **AI-assistent** toe.

De pagina is ingedeeld in **Verbinding**, **Gedrag** (modus van nieuwe chats, chatnamen, functielijst), **Rechten** en **Geavanceerd**. Onder **Geavanceerd** (ingeklapt) vindt u contextgrootte, temperatuur en wachttijd. Het eerste antwoord nadat een model is geladen duurt langer – de wachttijd is ruim bemeten.
Onder **Geavanceerd** toont elke waarde een **"Aanbevolen: ..."**; de knop **Aanbevolen waarden instellen** (onderaan de instellingen) zet context (16384), temperatuur, langste antwoord, wachttijd, chatnamen en de functielijst terug. Serveradres, model en rechten blijven ongemoeid.

---

## 2. Schrijven

Onderaan staat de invoerregel: **[modusknop] [tekstveld] [microfoon] [verzenden]**. De microfoonknop (dictatie, alleen op de console) wordt hieronder beschreven onder *Dicteren*.

- **Enter** verstuurt, **Shift + Enter** begint een nieuwe regel.
- Terwijl de AI werkt, ziet u springende puntjes, daarna de tekst woord voor woord. De knop **verzenden** verandert in een rode knop **stoppen**.
- Onder elk antwoord staat een compacte regel: de **modus**, de totale tijd van de vraag, tokens per seconde en het model.
- **Denkstappen:** modellen als `qwen3` of `deepseek-r1` denken eerst en antwoorden daarna. De gedachten staan in een inklapbaar blok **boven** het antwoord: terwijl het model denkt, is het open en groeit het; als het antwoord begint, klapt het in ("Nagedacht gedurende 12 s"), een klik opent het weer. Of een model denkt, hangt van het model zelf af (er is geen schakelaar). Denken telt mee voor het *Langste antwoord* – OpenCue voegt er 2500 tokens ruimte voor toe.
- **Scrollen:** staat de geschiedenis helemaal onderaan, dan volgt ze mee terwijl de AI schrijft. Scrolt u omhoog, dan **blijft uw positie** – ook al wordt er verderop nog geschreven. De ronde knop met pijl omlaag rechtsonder in de geschiedenis brengt u terug naar het einde (hij licht op zolang er nog iets loopt). Als u een bericht verstuurt, springt u vanzelf naar beneden.
- Elk bericht heeft een knop **kopiëren** als u eroverheen beweegt; de tekst kan ook worden geselecteerd.
- In de modus Chat krijgt de AI bij elke vraag **de hele chat tot nu toe**. Wordt die te lang voor het contextvenster, dan vallen de oudste berichten eruit (alles blijft opgeslagen). In de modus Werk krijgt ze de huidige vraag met alles wat ervoor is gebeurd, plus een **korte samenvatting** van de eerdere vragen. Resultaten staan daarin alleen voor berekeningen ("en de helft daarvan?"); showgegevens, de tijd en willekeurige getallen worden elke keer opnieuw opgehaald (anders kopiëren kleine modellen oude antwoorden en rekenen ze uit het hoofd).

### Dicteren (spraak naar tekst)

Klik op de **microfoon** naast het tekstveld: het veld wordt vervangen door een animatie van bewegende **balken** die uw stem volgen, met de opnametijd. **Vinkje** = klaar, de opname wordt opgeschreven en de tekst wordt in het veld gezet (hij wordt **niet** verzonden – lees hem, corrigeer hem, druk op verzenden); een tekst die al in het veld staat blijft behouden en de nieuwe woorden worden toegevoegd. **Kruisje** of `Esc` = weggooien. Na 2 minuten eindigt de opname vanzelf.

- De **taal** is de taal van de interface (een van de zes talen) – daarvoor is geen aparte instelling. Vakwoorden (cue, dimmer, gobo, blackout ...) zijn bij de herkenner bekend.
- Opnemen gebruikt de microfoon van de **console** (de knop verschijnt dus alleen daar). Alles draait op deze computer met *Whisper* (faster-whisper).
- Het **spraakmodel** wordt één keer bij de eerste dictatie geladen (internet nodig, een voortgangsbalk toont het); daarna werkt dicteren offline. *Instellingen -> Dictatie* biedt **Snel** (Whisper base, ongeveer 145 MB) en **Nauwkeurig** (Whisper small, ongeveer 484 MB, beter voor Duits, duurt iets langer), een knop **Nu laden** en de **microfoon voor dictatie**. Het opschrijven duurt ongeveer even lang als de opname of korter, afhankelijk van de computer.
- Dictatie heeft niets te maken met het **triggerwoord** (*Instellingen -> Triggerwoord*) – het zijn aparte functies, elk met zijn eigen microfoon. Een overzicht van alle gebruikte ingangen en uitgangen staat onder *Instellingen -> Ingangen & uitgangen*.

---

## 3. De drie modi

De vierkante **modusknop** links van het tekstveld opent een klein menu:

| Modus | Waarvoor | Status |
|---|---|---|
| **Chat** | Gewoon gesprek met de AI. | klaar |
| **Gids** | Legt het programma uit en laat zien waar dingen staan (knoppen openen vensters). | klaar |
| **Werk** | De AI werkt met functies: rekenen, de show lezen, projectoren instellen ... | in uitvoering (lezen en wijzigen van projectoren zijn klaar) |

De modus hoort bij de **chat** en kan op elk moment midden in een gesprek worden gewisseld. In welke modus **nieuwe chats** starten, stelt u in onder *Instellingen -> AI-assistent -> Modus van nieuwe chats*; elke chat onthoudt ook zijn eigen model en modus (ook na een herstart).

---

## 4. Werk: de AI met functies

In de modus **Werk** werkt de AI als een **agent**: ze roept **functies** aan, leest de resultaten, gaat daarmee verder en schrijft het eindantwoord zelf. Moet ze rekenen, dan vraagt ze het aan de **rekenmachine** in plaats van uit het hoofd te raden; heeft ze iets over de show nodig, dan **leest** ze het; moet ze iets instellen, dan roept ze de passende **schrijffunctie** aan – afhankelijk van uw **rechten** (paragraaf 5) pas nadat ze het u heeft gevraagd. Deze functies bestaan tot nu toe:

| Verzameling | Functie | Wat ze doet |
|---|---|---|
| Lezen (`read_functions`) | `show_overview` | Shownaam, blackout, master en alleen de **aantallen** (projectoren, groepen, cuelijsten, cues, effecten, variabelen), actieve cuelijst |
| Lezen | `list_fixtures` | De projectoren: nummer, naam, type, DMX-adres, groep, huidige helderheid (filters: groep, naam) |
| Lezen | `read_fixtures` | De **details** van projectoren: model, fabrikant, modus, DMX-adres, groep en **alle** huidige waarden (helderheid in %, kleur, pan / tilt, zoom ... en elk kanaal als DMX-waarde). U zegt welke: `all`, een bereik zoals `1-5`, nummers zoals `1, 3, 7` (ook `1-3, 7`) of de naam van een groep (ook "group Front"). Bestaat een genoemd nummer niet (`6, 11` bij 10 projectoren), dan komen de bestaande terug en een opmerking noemt het ontbrekende – zo kan de AI correct antwoorden |
| Lezen | `list_groups` | De groepen met de nummers van hun projectoren |
| Lezen | `read_dmx` | De **DMX-uitvoer** van een universum: alleen de kanalen die niet 0 zijn (`universe`, `first`, `last`) |
| Lezen | `list_cuelists` | De cuelijsten met aantal cues, actieve cue en fader |
| Bibliotheek (`library_functions`) | `list_effects` | De effecten met hun instellingen – en of ze lopen en op welke projectoren |
| Bibliotheek | `list_variables` | De variabelen (naam, soort zoals kleur of positie, groep, waarde) |
| Wijzigen (`control_functions`) | `set_fixtures` | **Wijzigt** waarden van projectoren: `brightness` (0-100 %), `color` (een naam zoals `red`, `#FF8000` of `255 128 0`), `pan` / `tilt` (graden of `50%`), `zoom`, `focus`, `gobo`, `prism`, `strobe` (elk 0-100 %) en met `channels` elk ander kanaal op naam in procenten (`{"Frost": 50}`). Gekozen zoals in `read_fixtures`; wat u niet noemt, blijft zoals het is. Ze doorloopt dezelfde controles als de **opdrachtregel** (de opdracht verschijnt in de geschiedenis daarvan). De **selectie** in de interface blijft onaangeroerd: de waarden gaan naar precies deze projectoren (zichtbaar in de projectorlijst, de programmer en de DMX-waarden) zonder ze te selecteren – u kunt intussen met andere projectoren blijven werken |
| Wijzigen | `set_blackout` | **Blackout** aan of uit (`enabled`): alles donker, de waarden blijven bewaard |
| Wijzigen | `set_master` | De **master** (totale helderheid) in procenten |
| Wijzigen | `timecode_control` | De **tijdcode**-klok: `play`, `pause`, `stop`, `seek` (met `position`), `rate` (met `rate`) |
| Cuelijsten (`cuelist_functions`) | `read_cuelist` | **Eén** cuelijst met alle cues: nummer, naam, trigger, tijden, actieve cue, of ze speelt |
| Cuelijsten | `control_cuelist` | Speelt een cuelijst af: `go` (volgende cue, of met `cue` een sprong), `back`, `pause`, `resume`, `stop` |
| Cuelijsten | `set_cuelist_fader` | De **fader** (mix) van een cuelijst in procenten |
| Looks (`look_functions`) | `apply_variable` | Zet een **variabele** (opgeslagen kleur, positie ...) op projectoren |
| Looks | `apply_effect` | Start een **effect** op projectoren |
| Looks | `stop_effects` | Stopt alle effecten op projectoren (de waarden blijven) |
| Looks | `release_fixtures` | Geeft projectoren terug aan **handmatig**: geeft variabelen en effecten vrij; eventueel alleen `dimmer`, `color`, `position`, `zoom`, `focus`, `gobo` |
| Lezen | `read_selection` | Welke projectoren in de interface zijn **geselecteerd** |
| Bibliotheek | `list_showfiles` | De opgeslagen **showbestanden** en welke is geladen |
| Selectie en groepen (`group_functions`) | `select_fixtures` | **Selecteert** projectoren in de interface (of `none` wist de selectie) |
| Selectie en groepen | `create_group` | Maakt een **groep** van projectoren (`name`, `fixtures`); de selectie van de gebruiker blijft |
| Selectie en groepen | `delete_group` | **Kritiek:** verwijdert een groep (de projectoren blijven) |
| Cuelijsten | `store_cue` | **Slaat** de programmerwaarden op als nieuwe cue (`cuelist`, `cue`, optioneel `name`, `if_exists` = `merge` / `overwrite`) |
| Cuelijsten | `delete_cue` | **Kritiek:** verwijdert een cue van een lijst |
| Patch (`patch_functions`) | `list_fixture_types` | Zoekt typen op in de **projectorbibliotheek** (naam, fabrikant, modi met aantal kanalen) |
| Patch | `add_fixtures` | **Patcht** nieuwe projectoren: type, aantal, universum, eerste adres, naam, groep; overlappende adressen worden geweigerd |
| Patch | `change_fixture` | Wijzigt **één** projector: naam, adres, universum, groep |
| Patch | `change_group` | Hernoemt een groep en / of bepaalt de leden |
| Patch | `delete_fixtures` | **Kritiek:** verwijdert projectoren uit de show |
| Showbestanden (`showfile_functions`) | `save_show`, `save_show_as` | **Slaat** de show op (onder zijn bekende naam / onder een nieuwe; een bestaande naam wordt alleen met `overwrite` vervangen) |
| Showbestanden | `rename_showfile` | Hernoemt een opgeslagen showbestand |
| Showbestanden | `load_show`, `new_show` | **Kritiek:** laadt een andere show / start een nieuwe en vervangt de lopende. Niet-opgeslagen wijzigingen worden geweigerd – alleen met uw instemming (`discard_changes`) lukt het toch |
| Showbestanden | `delete_showfile` | **Kritiek:** verwijdert een opgeslagen showbestand (het geladen alleen met `force`) |
| Variabelen (`variable_functions`) | `create_variable`, `change_variable` | Maakt / wijzigt een **variabele**: kleur (`color`), helderheid / zoom / focus / gobo (`level`), positie (`pan`, `tilt`); alles wat hem gebruikt, volgt meteen |
| Variabelen | `delete_variable` | **Kritiek:** verwijdert een variabele |
| Effecten (`effect_functions`) | `list_effect_types` | De **effecttypen** met hun categorie en hun instellingen met grenzen |
| Effecten | `create_effect`, `change_effect` | Maakt een **effect** van een type met instellingen (`settings`) / wijzigt het |
| Effecten | `delete_effect` | **Kritiek:** verwijdert een effect (het stopt overal) |
| Cues bewerken (`cue_edit_functions`) | `set_cue` | Wijzigt de **eigenschappen** van een cue: naam, fade, delay, trigger (`go` / `follow` / `timecode` / `audio` / `midi`), tijdcode, opdracht, move-in-black, nieuw nummer |
| Cues bewerken | `duplicate_cue`, `update_cue` | Kopieert een cue / neemt de programmerwaarden over in de **actieve cue** (zoals de knop Update) |
| Cuelijsten beheren (`cuelist_manage_functions`) | `create_cuelist`, `rename_cuelist`, `duplicate_cuelist` | Maakt een cuelijst / hernoemt hem / kopieert hem met al zijn cues |
| Cuelijsten beheren | `delete_cuelist` | **Kritiek:** verwijdert een cuelijst met al zijn cues |
| Opdracht (`command_functions`) | `command_help` | De **syntaxis van de opdrachtregel** uit de handleiding (spiekbriefje of een onderwerp: `selection`, `values`, `color`, `channels`, `effects`, `combine`, `clear`, `cuelists`, `cues`) – de AI zoekt het op voordat ze `run_command` gebruikt |
| Opdracht | `run_command` | **Kritiek:** voert **elke opdracht van de opdrachtregel** uit (ook cues verwijderen en opslaan) – de AI vraagt het u tot u "Altijd toestaan" kiest |
| Hulpjes (`helper_functions`) | `calculate` | Berekent een uitdrukking exact: `+ - * / // % ** ^`, haakjes, `sqrt`, `sin`, `cos`, `tan`, `ln`, `log`, `exp`, `abs`, `round`, `floor`, `ceil`, `min`, `max`, `pi`, `e` ... (decimalen met een punt) |
| Hulpjes | `random_number` | Willekeurige getallen of dobbelstenen (`min`, `max`, `count`, gehele getallen of decimalen) |
| Hulpjes | `current_time` | Tijd, datum en weekdag van de computer |

De AI **hoeft geen functie te gebruiken**: bij een groet, een bedankje of een algemene vraag antwoordt ze gewoon in woorden. Alleen berekeningen, willekeurige getallen, datum en tijd, showgegevens en wijzigingen aan de show gaan via een functie – elke keer opnieuw, ook bij een vervolgvraag.

Elke aanroep verschijnt in de chat in een **functieblok** onder uw vraag: ingeklapt ziet u het aantal, de namen, de status en de tijd; een klik toont elke functie met haar **invoer en resultaat**. Werkt een aanroep niet (bijv. een ongeldige berekening of een projectornummer dat niet bestaat), dan mag de AI de fout lezen – met wat er wel bestaat – en probeert ze het opnieuw met gecorrigeerde waarden. Elke waarde die de AI voor `set_fixtures` opgeeft, wordt eerst streng gecontroleerd (getalbereiken, kleurnamen, kanaalnamen); tekst van de AI wordt nooit een willekeurige opdracht.

**Zelf functies aanroepen:** u kunt elke functie ook **met de hand** activeren – zonder dat de AI iets zegt. Typ `/` en de naam in het tekstveld; terwijl u typt verschijnen suggesties (pijltoetsen, **Tab** of een klik accepteren, **Enter** verstuurt):

- `/read_fixtures {"fixtures":"6-8"}` – de waarden als JSON, zoals de AI ze schrijft.
- `/read_fixtures 6-8` – heeft de functie precies één verplichte waarde, dan volstaat de waarde alleen. `/calculate 17*23` rekent.
- `/set_fixtures fixtures=1-3 brightness=50` – of als `naam=waarde`.
- `/help` toont alle functies met hun soort en waarden.

Het resultaat verschijnt al uitgeklapt in de chat (invoer en resultaat als JSON). **Er wordt geen model gevraagd** en de AI ziet deze aanroepen later niet. Omdat u zelf handelt, gelden de **rechten** hier niet – zelfs een schrijffunctie wordt zonder vraag uitgevoerd, ook als ze voor de AI op "Nooit toestaan" staat. Een fout (onbekende functie, verkeerde schrijfwijze van de waarden) verschijnt als mislukte aanroep met een uitleg. Een bericht dat alleen met `/` begint zonder een functienaam te zijn (bijv. `/etc/hosts show`) gaat zoals gewoonlijk naar de AI.

**Functielijst** (*Instellingen -> AI-assistent -> Werkmodus*):

- **Gangbare functies meteen, de rest op verzoek** (standaard, aanbevolen): de AI ziet de ongeveer 17 gangbare functies (projectoren lezen en instellen, blackout, master, een cuelijst afspelen, variabelen en effecten toepassen, opdrachtregel, rekenmachine ...) direct en een **verzamelfunctie** voor al het andere (patchen, showbestanden, variabelen / effecten / cues bewerken ...): het aanroepen van een verzamelfunctie geeft haar de functies van die verzameling vanaf de volgende stap. De prompt blijft klein – belangrijk, want alle 56 functies tegelijk zijn ongeveer twee keer zo groot als het contextvenster van een klein model aankan.
- **Alles tegelijk**: de AI ziet meteen alle 56 functies. Alleen voor grote modellen met een groot contextvenster (verhoog *Instellingen -> AI-assistent -> Geavanceerd -> Contextgrootte*).
- **Alles op verzoek**: de AI ziet alleen de 14 verzamelfuncties (`read_functions`, `library_functions`, `cuelist_functions`, `look_functions`, `group_functions`, `command_functions`, `control_functions`, `helper_functions`, `patch_functions`, `showfile_functions`, `variable_functions`, `effect_functions`, `cue_edit_functions`, `cuelist_manage_functions`). De kleinste prompt, maar kleine modellen zijn er trager mee en kiezen vaker de verkeerde verzameling.

**Bescherming tegen eindeloze lussen:** dezelfde aanroep met dezelfde waarden wordt hoogstens **3 keer** per vraag uitgevoerd, in totaal hoogstens **30** aanroepen. Daarna wordt de AI gestopt en schrijft ze haar antwoord uit wat ze tot dan toe heeft (er verschijnt een opmerking in de chat).

**Belangrijk voor het model:** het moet **functies kunnen aanroepen** (bijv. `qwen2.5-coder`, `qwen3`, `llama3.1`). Kleine modellen (3B) verzinnen af en toe nog iets of slaan een functie over; hoe groter het model, hoe betrouwbaarder – een model als `qwen3:4b` of `llama3.1:8b` is de moeite waard als uw computer het aankan. Een gewoon chatmodel meldt in de modus Werk dat het geen functies kan aanroepen; in de modus Chat werkt het normaal.

---

## 5. Rechten: wat de AI zelf mag doen

Elke functie hoort bij een **soort**, en voor elke soort stelt u in wat de AI mag doen (*Instellingen -> AI-assistent -> Rechten*):

| Soort | Voorbeelden | Standaard |
|---|---|---|
| **Leesfuncties** | `show_overview`, `list_fixtures`, `read_fixtures`, `list_groups`, `read_dmx`, `list_cuelists`, `read_cuelist`, `read_selection`, `list_effects`, `list_effect_types`, `list_showfiles`, `list_fixture_types`, `list_variables` – ze kijken alleen naar de show | **Altijd toestaan** |
| **Schrijffuncties** | `set_fixtures`, `set_blackout`, `set_master`, `timecode_control`, `control_cuelist`, `set_cuelist_fader`, `apply_variable`, `apply_effect`, `stop_effects`, `release_fixtures`, `select_fixtures`, `create_group`, `store_cue` en alles voor patchen, opslaan, bewerken van variabelen, effecten, cues en cuelijsten (`add_fixtures`, `save_show`, `create_variable`, `create_effect`, `set_cue`, `create_cuelist` ...) – ze wijzigen de show | **Elke keer vragen** |
| **Kritieke functies** | `run_command` (elke opdracht van de opdrachtregel), **alle verwijderfuncties** (`delete_cue`, `delete_group`, `delete_fixtures`, `delete_variable`, `delete_effect`, `delete_cuelist`, `delete_showfile`) en `load_show` en `new_show` (ze vervangen de lopende show) | **Elke keer vragen** |
| Hulpfuncties | `calculate`, `random_number`, `current_time`, `command_help` – geen effect op de show | altijd toegestaan, niet instelbaar |

Voor elk van de drie soorten kiest u **Altijd toestaan**, **Elke keer vragen** of **Nooit toestaan**. Onder elke keuze ziet u welke functies erbij horen.

**De vraag:** staat een soort op *Elke keer vragen*, dan pauzeert de AI voordat ze de functie uitvoert en verschijnt in het functieblok een **kaart** met de functie en haar waarden (en de soort, bijv. "Wijzigt de show"). Ze heeft drie knoppen:

- **Eenmalig toestaan** – de functie wordt nu uitgevoerd; de volgende keer vraagt ze opnieuw.
- **Altijd toestaan** – de functie wordt nu uitgevoerd en voortaan **altijd zonder te vragen** (ook in andere chats). Dit geldt voor precies deze ene functie en staat onder *Instellingen -> AI-assistent -> Rechten -> Altijd toegestane functies*; **Verwijderen** laat haar weer vragen. Deze knop bestaat alleen op de **consolecomputer** (niet op tablets / apparaten op afstand); hij geldt voor **alle** soorten, ook kritieke functies.
- **Niet toestaan** – de functie wordt niet uitgevoerd. De AI wordt ingelicht en vertelt u dat ze het niet heeft gedaan.

De vraag verschijnt op **alle** apparaten die deze chat tonen; *Eenmalig toestaan* en *Niet toestaan* werken vanaf elk ervan. Ze blijft ook staan nadat de pagina is herladen. Antwoordt niemand, dan geldt het na 10 minuten als "nee"; *Stoppen* beëindigt de vraag meteen.

Staat een soort op **Nooit toestaan**, dan vraagt de AI zelfs niet: de functie wordt niet uitgevoerd, de AI krijgt de opmerking over de instelling en vertelt het u.

---

## 6. Chats

- Elke chat is een **eigen bestand** (map `chats` in de gegevensmap) en blijft na het afsluiten bewaard; alle apparaten en panelen tonen dezelfde chats.
- **+** maakt een nieuwe chat; de eerste wordt vanzelf gemaakt als u verstuurt.
- **Dubbelklikken** op de titel hernoemt hem. Zolang de AI geen titel heeft gegeven, wordt het begin van de eerste vraag getoond.
- **Automatische titels:** de AI geeft de chat zelf een korte titel (2-5 woorden; één extra, klein verzoek aan het model) – **na het tweede antwoord**, zodat ze meer context heeft (de eerste twee vragen en antwoorden gaan in het verzoek). Komt er binnen **een minuut** geen tweede vraag, dan wordt de chat naar de eerste genoemd. Tot dan wordt het begin van de eerste vraag getoond. Een chat die u zelf hebt hernoemd, wordt nooit hernoemd. Uitzetten: *Instellingen -> AI-assistent -> Model -> Chats automatisch benoemen*.
- In de kop kiest u het **model van deze chat** – op elk moment te wijzigen, de geschiedenis blijft.
- Elke rij van de **chatlijst** heeft een **menu met drie puntjes** (ook bij rechtsklik): **Naam wijzigen** (direct in de lijst), **Dupliceren** (een kopie met de hele geschiedenis, getiteld "... (kopie)") en **Chat verwijderen** (na bevestiging). Het symbool voor de titel toont de modus van de chat. **Terwijl de AI schrijft** in een chat, bewegen kleine puntjes achter de titel – zo ziet u in welke van meerdere chats ze werkt. Is een antwoord **klaar en de chat niet open**, dan verschijnt daar een **gele stip** ("nieuw antwoord"). Die verdwijnt zodra u de chat opent – op alle apparaten.
- De **chatlijst kan worden in- en uitgeklapt** (eerste knop in de kop); de status wordt per paneel onthouden. In smalle panelen ligt de lijst over de geschiedenis.

## 7. Gids: legt het programma uit en laat zien waar dingen staan

In de modus **Gids** (pictogram: wegwijzer) beantwoordt de AI vragen als *"Waar staan de kleurprofielen?"*, *"Hoe maak ik een cue?"* of *"Wat is een projectorgroep?"* – en kan u **knoppen** aanbieden die het juiste venster openen.

- **De AI verzint niets.** Ze krijgt in haar prompt maar weinig mee (hoe het programma is opgebouwd) en haalt elk detail op met de functie **`find_help`**: OpenCue kiest de passende stukken uit vele kleine tekstfragmenten en geeft ze aan de AI met de opdracht om **alleen daaruit te antwoorden**. Past er niets, dan zegt de functie dat uitdrukkelijk – de AI moet dan toegeven dat ze het niet weet in plaats van te raden.
- **Bronnen:** de fragmenten zijn JSON-bestanden in de map `static/help/guide/snippets/<taal>/` (één bestand per handleidingpagina, ongeveer 400 per taal). Hun tekst is **woord voor woord uit de handleidingen** overgenomen. U mag fragmenten met de hand bewerken of inkorten of `keywords` toevoegen; `synonyms.json` koppelt woorden (bijv. "Bestandsbeheer" <-> "file manager").
- **Vensters openen:** de functie **`show_dialog`** zet onder het antwoord een knop als **"Openen: Bestandsbeheer"**. De AI klikt zelf nooit – **u beslist** of u erop drukt. De klik is hetzelfde als op het menu-item; er wordt niets opgeslagen of verwijderd. De belangrijke vensters worden aangeboden (Instellingen met hun categorieën, bestandsbeheer voor shows / indelingen / podia / effecten, projectorbibliotheek, show openen / opslaan / importeren / exporteren, Paneel toevoegen, bewerkmodus, sneltoetsen, taal ...); de lijst staat in `static/help/guide/targets.json`.
- **`list_help_topics`** toont waarover de gids u kan vertellen.
- De gids wijzigt **niets** in uw show; ze heeft alleen deze drie functies (allemaal zonder vragen toegestaan).
