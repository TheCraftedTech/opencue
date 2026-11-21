# REST-API

Met de **REST-API** kunnen andere programma's de status van OpenCue **lezen** en het **bedienen en bewerken** – scripts, een showcontroller, domotica, een webpagina voor de stagemanager, een tablet-app of uw eigen tool. Ze spreekt gewoon **HTTP** en antwoordt in **JSON**. Er is geen extra software nodig en ze werkt volledig offline binnen uw netwerk.

De toegang wordt beschermd door **tokens** die u in OpenCue aanmaakt. Elk token heeft zijn eigen **rechten**, zodat een tablet-app misschien alleen mag lezen terwijl een andere tool ook cues mag triggeren en een derde hele shows mag bouwen.

---

## 1. Het idee in één minuut

- De API staat onder **`/api/v1/`** op hetzelfde adres en dezelfde poort als OpenCue zelf (bijvoorbeeld `http://127.0.0.1:8000/api/v1/`).
- U **maakt een token** in *Instellingen → API* en stuurt het met elk verzoek mee.
- **Lees**verzoeken (`GET`) geven de status terug: projectoren, cuelijsten, cues, variabelen, effecten, het DMX-signaal, de tijdcode, de programmer.
- **Bedienings**verzoeken (`POST` / `PUT`) laten de show draaien: opdrachten, cues, tijdcode, blackout, audio, de programmer.
- **Bewerk**verzoeken wijzigen de show zelf: cuelijsten en cues, variabelen, effecten en effectscripts maken en wijzigen, projectoren patchen, showbestanden opslaan en laden, media uploaden.
- De eigen **knoppen, faders en schakelaars** van de console kunnen van buitenaf worden ingedrukt, verschoven en omgeschakeld.
- Alles wat een operator in het venster doet, verschijnt **meteen in alle open vensters** – ook wat de API wijzigt.
- Een **live-stroom** (`GET /events`) meldt wijzigingen op het moment dat ze gebeuren, zodat een dashboard niet steeds hoeft te vragen.
- Voor **hardware** (een ESP32 met joystick, draaiknoppen, knoppen, microfoon) is er een **WebSocket** (`/api/v1/ws`): joystick relatief of absoluut, waarden absoluut of relatief instellen, DMX en live waarden, tijdcode verzenden en ontvangen, audiowaarden en audiogegevens in beide richtingen (paragraaf 10). Voor eenvoudige apparaten zonder eigen interface zijn er **statusweergaven** als afbeelding of webpagina (paragraaf 11).
- Elke functie vraagt **één recht**. Een token zonder dat recht krijgt `403`. De bewerkrechten staan **standaard uit**.
- De API is een eigen, stabiele interface. De interne routes die het programmavenster gebruikt, maken er *geen* deel van uit.

---

## 2. Snel aan de slag

1. Open **Instellingen → REST-API** (ook mogelijk vanaf een aangemeld apparaat op afstand). Standaard is er **geen token** en antwoordt de API alleen op **deze computer**.
2. Klik op **Nieuw token**, geef het een naam, kies de rechten (of een voorinstelling) en klik op **Token aanmaken**. Een **nieuw token wordt meteen aangemaakt** (zonder *Opslaan*) en daarna getoond.
3. **Kopieer het token nu.** Het wordt maar één keer getoond; daarna zijn alleen de eerste tekens zichtbaar. Raakt het kwijt, maak dan een nieuw token of gebruik *Nieuw token genereren*.
4. Probeer het:

```
curl -H "Authorization: Bearer oc_xxxxxxxx" http://127.0.0.1:8000/api/v1/status
```

Het antwoord is een JSON-object met de shownaam, blackout, grand master, tijdcode en meer (zie paragraaf 6).

Het adres in de voorbeelden (`127.0.0.1:8000`) is de console zelf. Voor het adres vanaf andere apparaten zie paragraaf 8. Een pagina met elke route, doorzoekbaar en offline leesbaar, staat op `/api/v1/docs`.

---

## 3. Tokens en rechten

### Tokens beheren

In **Instellingen → REST-API** kunt u:

| Actie | Betekenis |
|---|---|
| **REST-API aan/uit** | De hoofdschakelaar. Staat hij uit, dan wordt elk verzoek beantwoord met `403 api_disabled`. |
| **Bereikbaar vanaf** | *Alleen deze computer* (standaard) of *Het netwerk*. Andere apparaten hebben ook **toegang op afstand** nodig; de pagina meldt het anders (met een link). Van buitenaf antwoordt de API `403 api_local_only` als *Alleen deze computer* is ingesteld. |
| **Webpagina's op andere adressen toestaan** | Browserpagina's die vanaf een ander adres zijn geopend, mogen de API aanroepen (CORS, paragraaf 8). Standaard aan. |
| **Statusweergaven (afbeelding / web)** | Schakelaar voor de weergaven van paragraaf 11. Standaard aan (elk vraagt een token). |
| **Nu verbonden (WebSocket)** | Lijst van de apparaten die nu via de WebSocket verbonden zijn (token, adres, wat ze ontvangen, joystick actief, berichten per seconde) – live, met **Verbinding verbreken**. |
| **Nieuw token** | Maakt een token. Een breed venster laat u de rechten in drie kolommen kiezen: *Lezen*, *Bedienen*, *De show bewerken*. |
| **Bewerken** | Naam en rechten wijzigen. |
| **Actief-schakelaar** | Zet één token uit en weer aan zonder het te verwijderen (`403 token_disabled` zolang het uit staat). |
| **Nieuw token genereren** (in *Bewerken*) | Vervangt het geheim. Het oude token werkt niet meer zodra u opslaat. |
| **Verwijderen** | Vraagt in een eigen venster (uit te zetten, zie *Standaardwaarden → Verwijderen*) en verwijdert het token daarna **meteen**. |
| **Laatst gebruikt** | Toont wanneer een token voor het laatst is gebruikt. |

Een **nieuw token** wordt meteen aangemaakt en getoond, een **verwijdering** geldt meteen na de vraag. Al het andere is een **concept** zoals in alle instellingen (schakelaar, bewerken, opnieuw genereren): gewijzigde rijen worden gemarkeerd en geteld, alleen **Opslaan** past alles toe (het venster blijft open), *Sluiten* verwerpt na een vraag. Tokens kunnen alleen op de consolecomputer zelf worden beheerd, niet vanaf apparaten op afstand.

Alleen een **hash** van het token wordt op schijf opgeslagen, nooit het token zelf.

### De rechten

**Lezen**

| Recht | Staat toe | Standaard |
|---|---|---|
| **Status** | Status: shownaam, blackout, grand master, tijdcode, selectie, programmer, audio-analyse, uitgangen, de live gebeurtenissenstroom | aan |
| **Showgegevens** | Projectoren, projectortypen, groepen, variabelen, effecten, effectscripts, showbestanden, cuelijsten en cues, media, indelingen | aan |
| **DMX-uitgang** | Actuele DMX-waarden en de live toestand van elke projector | aan |

**Bedienen**

| Recht | Staat toe | Standaard |
|---|---|---|
| **Consoleopdrachten** | Elke opdracht van de opdrachtregel uitvoeren (kan ook showgegevens wijzigen en verwijderen) – *kritiek* | aan |
| **Cuelijsten** | Go, Back, naar een cue springen, pauze, hervatten, stop, fader | aan |
| **Tijdcode** | Start, pauze, stop, zoeken, snelheid | aan |
| **Blackout en master** | Blackout schakelen, grand master instellen | aan |
| **Audio** | De audiobron openen / sluiten, haar instellingen wijzigen, het tempo tikken | aan |
| **Programmer en selectie** | Projectoren selecteren, waarden en variabelen live instellen, de programmer leegmaken | aan |
| **Console-knoppen, -faders, -schakelaars** | De eigen Knop-, Fader- en Schakelaar-panelen van de console indrukken, verschuiven en omschakelen (ze voeren de daarin ingestelde opdrachten uit) | aan |
| **DMX direct instellen** | DMX-kanalen schrijven – overschrijft de lopende show – *kritiek* | **uit** |

**De show bewerken**

| Recht | Staat toe | Standaard |
|---|---|---|
| **Cuelijsten en cues** | Cuelijsten en cues maken, wijzigen, kopiëren, hernummeren en verwijderen; de programmer als cue opslaan | **uit** |
| **Variabelen** | Variabelen en variabelegroepen maken, wijzigen en verwijderen | **uit** |
| **Effecten** | Effecten en effectgroepen maken, wijzigen en verwijderen; effecten op projectoren starten en stoppen | **uit** |
| **Effectscripts** | Effecttypen (scriptbestanden) controleren, opslaan en verwijderen | **uit** |
| **Patch en projectorgroepen** | Projectoren patchen, wijzigen en verwijderen; projectorgroepen beheren; GDTF-projectortypen installeren en verwijderen – *kritiek* | **uit** |
| **Showbestanden** | Showbestanden nieuw, laden, opslaan, hernoemen, kopiëren en verwijderen – *kritiek* | **uit** |
| **Media** | Video- en audiobestanden uploaden, hernoemen en verwijderen | **uit** |
| **Indelingen** | Een opgeslagen paneelindeling in het consolevenster tonen | **uit** |
| **DMX-uitgangen en taal** | Art-Net, sACN en USB-DMX schakelen, adressen, standaarduniversum en taal wijzigen – *kritiek* | **uit** |

**Voorinstellingen** in het venster: *Alleen lezen* (de drie leesrechten), *Bedienen* (lezen plus cuelijsten, tijdcode, blackout/master, audio, programmer en de knoppen / faders / schakelaars van de console – geen opdrachten, geen DMX direct), *Show bewerken* (Bedienen plus cuelijsten en cues, variabelen, effecten), *Volledige toegang* en *Standaard*.

---

## 4. Regels voor alle verzoeken

- **Aanmelden:** stuur het token als `Authorization: Bearer oc_…`. De header `X-API-Key: oc_…` werkt ook.
- **Formaat:** verzoeken met een body gebruiken JSON en `Content-Type: application/json`. Antwoorden zijn altijd JSON (behalve de gebeurtenissenstroom en bestandsdownloads).
- **Dingen kiezen:**
  - een *projector* op zijn **nummer (FID)**, zijn id of een ondubbelzinnige naam; een *groep* projectoren op zijn naam;
  - een *cuelijst* op zijn **naam** of id; een *cue* op zijn **nummer** (bijvoorbeeld `1.5`) of id;
  - een *variabele*, een *effect* of een *showbestand* op zijn **naam** (hoofdletters / kleine letters maken niet uit) of id.
  - Namen met spaties moeten in het pad als URL worden gecodeerd (`Par%20links`).
- **Meerdere projectoren kiezen** in een body: `"fixtures": [1, 2, "Front"]`, `"fixture": 3` en / of `"group": "Wash"`. Voor de programmer-aanroepen betekent `"selection": true` de op de console geselecteerde projectoren, en een aanroep zonder een van deze gebruikt de selectie.
- **Procent en bytes:** dimmer, positie en dergelijke worden in **procenten (0–100)** gegeven, ruwe DMX-kanalen in **0–255**, kleuren als `"#rrggbb"`, `[r, g, b]` of `{"r": …, "g": …, "b": …}` (0–255).
- **Tijden** in seconden; de tijdcode als seconden of tekst (`00:01:04.300`).
- **Zorgvuldige invoercontrole:** een veld dat niet bestaat wordt geweigerd (`422`), een verkeerde waarde of naam geeft `400`, een naam die al bezet is geeft `409 duplicate`. Er wordt niets geraden of stilzwijgend genegeerd.
- **Gecontroleerd voordat iets verandert:** een aanroep met een verkeerde waarde, naam of projector wordt als geheel geweigerd – een cue met één verkeerde projector wordt niet half opgeslagen.

### Fouten

Fouten zien er altijd hetzelfde uit:

```json
{ "error": { "code": "not_found", "message": "No fixture '99' (use the fixture number, id or an unambiguous name)." } }
```

| HTTP | `code` | Betekenis |
|---|---|---|
| 400 | `bad_request` | Het verzoek is fout (een waarde buiten het bereik, een onbekend attribuut, een lege opdracht …) |
| 401 | `unauthorized` | Token ontbreekt of is ongeldig |
| 403 | `forbidden` | Het token heeft het recht voor deze functie niet |
| 403 | `token_disabled` / `api_disabled` | Het token of de hele API staat uit |
| 404 | `not_found` | Projector, cuelijst, cue, variabele, effect, showbestand … bestaat niet |
| 409 | `duplicate` | De naam is bezet (cuelijst, variabele, effect, groep …) |
| 409 | `cue_exists` | Een cue met dit nummer bestaat – stuur `on_conflict` (`merge` / `overwrite`) |
| 409 | `address_conflict` | De DMX-adressen overlappen een andere projector – `allow_overlap: true` patcht toch |
| 409 | `unsaved_changes` | De show heeft niet-opgeslagen wijzigingen – sla hem op, of stuur `force: true` |
| 409 | `exists` / `in_use` / `never_saved` | Een showbestand of script met die naam bestaat / het showbestand is het geladen bestand / de show heeft nog geen bestand |
| 409 | `no_active_cue` / `programmer_empty` | *Update* zonder actieve cue of met een lege programmer |
| 409 | `audio_failed` | De audiobron kon niet worden geopend (de reden staat in het bericht) |
| 415 | `invalid_type` | Een media-upload die geen ondersteund video- / audiobestand is |
| 422 | `invalid` | Een veld ontbreekt, is onbekend of heeft een verkeerd type |
| 422 | `invalid_script` | Een script compileert niet of mislukt zijn proefrun (met de regel) |
| 429 | `rate_limited` | Te veel verkeerde tokens vanaf dit adres – wacht de tijd in `Retry-After` af |

Een **afgewezen consoleopdracht** (bijvoorbeeld een typfout) is *geen* HTTP-fout: het antwoord is `200` met `"success": false` en het bericht van de opdrachtregel.

---

## 5. Overzicht van de eindpunten

Alle paden beginnen met `/api/v1`. Het recht in de rechterkolom is wat het token nodig heeft. In de paden is `{list}` een cuelijst, `{cue}` een cue, `{fixture}` een projector, `{ref}` een variabele / effect / naam.

### Lezen

| Methode | Pad | Geeft terug | Recht |
|---|---|---|---|
| GET | `/` | Index: versie, links, wat dit token mag | Status |
| GET | `/status` | Totale status: show, blackout, master, tijdcode, selectie, actieve cuelijst, DMX-uitgangen, aantallen | Status |
| GET | `/blackout` · `/master` · `/timecode` · `/selection` | Eén deel van de status | Status |
| GET | `/system` | Versie, taal, DMX-uitgangen (Art-Net, sACN, USB), universa, toegang op afstand, gegevensmap | Status |
| GET | `/showfile` | Naam van de geladen show, of hij niet-opgeslagen wijzigingen en een bestand heeft | Status |
| GET | `/programmer` | Selectie, de met de hand ingestelde waarden (procent, kleur + hex, ruwe kanalen), de variabelen die ze volgen, lopende effecten | Status |
| GET | `/audio` · `/audio/devices` | De live audio-analyse en de instellingen / elke audio-ingang | Status |
| GET | `/system/usb-ports` · `/command/suggest?text=` | Seriële poorten voor USB-DMX / aanvullingen voor een opdracht (zoals Tab in de opdrachtregel) | Status |
| GET | `/events` | **Live-stroom** van wijzigingen (Server-Sent Events, paragraaf 6) | Status |
| GET | `/fixtures` | Alle projectoren. Optioneel `?universe=`, `?group=`, `?include_state=true` | Showgegevens |
| GET | `/fixtures/{fixture}` | Eén projector met elk kanaal (adres, actuele DMX-waarde) en zijn toestand | Showgegevens |
| GET | `/fixture-types` | De projectorbibliotheek: id, naam, fabrikant, modi met aantal kanalen (`?q=` filtert) | Showgegevens |
| GET | `/groups` · `/variable-groups` · `/effect-groups` | Projectorgroepen, variabelegroepen, effectgroepen | Showgegevens |
| GET | `/variables` · `/variables/{ref}` | Alle variabelen / één (met hoeveel cue-items hem gebruiken) | Showgegevens |
| GET | `/effects` · `/effects/{ref}` · `/effects/assignments` | Effecten / één effect met zijn typegegevens / welk effect op welke projector loopt | Showgegevens |
| GET | `/effect-scripts` · `/effect-scripts/{name}` | Alle effecttypen (categorie, tags, instellingen) / de brontekst van één type | Showgegevens |
| GET | `/cuelists` · `/cuelists/{list}` | Alle cuelijsten met actieve cue, fader en afspeelstatus / één lijst met al zijn cues | Showgegevens |
| GET | `/cuelists/{list}/cues` | De cues van een lijst; `?detail=true` voegt **toe wat elke cue wijzigt** | Showgegevens |
| GET | `/cuelists/{list}/cues/{cue}` | Eén cue in alle details | Showgegevens |
| GET | `/showfiles` | Namen van opgeslagen showbestanden (en het geladen bestand) | Showgegevens |
| GET | `/media` · `/media/{id}/file` | De media van de show / er een downloaden | Showgegevens |
| GET | `/layouts` | Opgeslagen indelingen van de console | Showgegevens |
| GET | `/widgets` | De Knop-/Fader-/Schakelaar-panelen van de console: opdrachten, faderlimieten en waarde, schakelaarstatus | Showgegevens |
| GET | `/dmx` · `/dmx/{universe}` | De universa en hun waarden (`?first=&last=`, `?nonzero=true`) | DMX-uitgang |
| GET | `/fixtures/state` | De live toestand van **elke** projector (wat de console nu uitvoert) | DMX-uitgang |

### Bedienen

| Methode | Pad | Body | Recht |
|---|---|---|---|
| POST | `/command` | `{"command": "Fixture 1 At 80"}` | Consoleopdrachten |
| POST | `/commands` | `{"commands": ["…", "…"], "stop_on_error": false}` – tot 100 | Consoleopdrachten |
| POST | `/cuelists/{list}/go` | optioneel `{"cue": "2"}` (zonder: de volgende cue) | Cuelijsten |
| POST | `/cuelists/{list}/back` · `/pause` · `/resume` · `/stop` | – | Cuelijsten |
| PUT | `/cuelists/{list}/fader` | `{"value": 70}` (procent) | Cuelijsten |
| PUT | `/timecode` | `{"action": "play" \| "pause" \| "stop" \| "seek" \| "rate", "position": …, "direction": 1, "rate": 1}` | Tijdcode |
| PUT | `/blackout` | `{"enabled": true}` (zonder waarde: omschakelen) | Blackout en master |
| PUT | `/master` | `{"value": 80}` (procent) | Blackout en master |
| PUT | `/audio` | `{"running": true, "device": "demo", "settings": {"mode": "manual", "bpm": 128}}` – elk veld optioneel | Audio |
| POST | `/audio/tap` | – (één tik van de tempoknop) | Audio |
| PUT | `/selection` | `{"fixtures": [1, 2], "mode": "set" \| "add" \| "remove" \| "clear"}` (ook `group`) | Programmer en selectie |
| PUT | `/programmer/values` | `{"fixtures": [1, 2], "values": {"dimmer": 80, "color": "#ff0000"}}` | Programmer en selectie |
| POST | `/programmer/variables` | `{"variable": "Warm white", "fixtures": [1, 2]}` – past een variabele toe en koppelt hem | Programmer en selectie |
| POST | `/widgets/{id}/press` | – (voert de opdracht van een knop uit) | Console-knoppen, -faders, -schakelaars |
| PUT | `/widgets/{id}/value` | `{"value": 70}` (fader; begrensd tot zijn minimum / maximum, afgerond) | Console-knoppen, -faders, -schakelaars |
| PUT | `/widgets/{id}/state` | `{"on": true}` (schakelaar; zonder waarde klapt hij om) | Console-knoppen, -faders, -schakelaars |
| POST | `/programmer/clear` | `{"fixtures": [1]}` vergeet hun waarden; `{"all": true}` = *Clear Clear*: alles donker | Programmer en selectie |
| PUT | `/dmx/{universe}/{channel}` | `{"value": 255}` of `{"percent": 100}` | DMX direct instellen |
| PUT | `/dmx/{universe}` | `{"channels": {"1": 255, "2": 0}}` | DMX direct instellen |
| PUT | `/fixtures/{fixture}/channels/{channel}` | `{"value": 128}` of `{"percent": 50}`; `{channel}` is het kanaalnummer van de projector (1 = eerste) of zijn naam (`Dimmer`) | DMX direct instellen |

### Bewerken: cuelijsten en cues – recht *Cuelijsten en cues*

| Methode | Pad | Body | Wat het doet |
|---|---|---|---|
| POST | `/cuelists` | `{"name": "Act 1"}` | Maakt een cuelijst (201) |
| PUT | `/cuelists/{list}` | `{"name": "…", "active": true}` | Hernoemt; `active` maakt hem de lijst die cuelijstpanelen tonen |
| PUT | `/cuelists/order` | `{"order": ["Act 2", "Act 1"]}` | Volgorde van de lijsten |
| POST | `/cuelists/{list}/duplicate` | `{"name": "Copy"}` | Kopie met alle cues |
| DELETE | `/cuelists/{list}` | – | Verwijdert de lijst |
| POST | `/cuelists/{list}/cues` | zie hieronder | Maakt een cue (201) |
| PUT | `/cuelists/{list}/cues/{cue}` | zie hieronder | Wijzigt eigenschappen en / of inhoud, hernummert |
| DELETE | `/cuelists/{list}/cues/{cue}` | – | Verwijdert een cue |
| POST | `/cuelists/{list}/cues/delete` | `{"cues": ["1", "2.5"]}` | Verwijdert er meerdere (alle of geen) |
| POST | `/cuelists/{list}/cues/{cue}/duplicate` | `{"number": 9, "name": "…"}` | Kopieert een cue |
| POST | `/cuelists/{list}/update-active` | `{"mode": "normal" \| "only"}` | Neemt de programmer over in de actieve cue (zoals *Update*) |

**Cue-body** (aanmaken en wijzigen; elk veld optioneel bij wijzigen):

| Veld | Betekenis |
|---|---|
| `number` | Cuenummer, decimalen toegestaan. Weggelaten bij aanmaken: het volgende vrije nummer. |
| `name`, `fade`, `delay` | Naam en de algemene tijden in seconden |
| `trigger` | `go` · `follow` · `timecode` · `audio` · `midi` · `clock` |
| `timecode` | Voor `timecode`: seconden of `1:04.300` |
| `audio` | Voor `audio`: `{"source": "beat" \| "kick" \| "snare" \| "hat" \| "level" \| "bass" \| "mid" \| "high" \| "b1" … "b8", "value": 4}` (elke n-de slag, of een drempel in %) |
| `midi` | Voor `midi`: `{"type": "note" \| "cc" \| "pc", "number": 60, "channel": 0, "value": 64}` – de cue gaat af als dit signaal binnenkomt terwijl hij de volgende cue van een lopende lijst is; `channel` 0 = elk (1–16 = één kanaal), `value` = de drempel van een `cc` (1–127) |
| `clock` | Voor `clock`: `{"time": "19:30", "days": "Mon-Fri"}` (of `"days": [0,1,2,3,4]`, maandag = 0; leeg = elke dag) – de cue wacht als volgende cue van een lopende lijst op dit tijdstip van de wandklok. |
| `mib`, `command` | Move in black (`Off` / `Auto` / `On`); consoleopdrachten die met de cue lopen |
| `times` | Eigen tijden per groep: `{"color": {"fade": 2, "delay": 0}, "position": {…}, "beam": {…}, "zoom": {…}}`; `null` = weer de algemene tijd gebruiken |
| `effect_fade` | `{"in": 1, "out": 2}` |
| `changes` | Wat de cue wijzigt (hieronder) |
| `effects` | De effecten die de cue start: `[{"fixtures": [2, 3], "effects": {"dimmer": "Strobe"}}]` (categorie → effectnaam) |
| `from_programmer` | *(aanmaken)* slaat ook op wat in de programmer staat **en elke wijziging van het beeld ten opzichte van de cue ervoor** (zoals *Store Cue*; is er niets gewijzigd: `409 nothing_changed`); `clear_programmer` leegt hem daarna |
| `on_conflict` | *(aanmaken / hernummeren)* het nummer bestaat: `merge` (alleen de verstuurde attributen voegen zich bij de bestaande cue) of `overwrite` |
| `content` | *(wijzigen)* `merge` (standaard) of `replace`: de inhoud van de cue is precies wat wordt verstuurd |

`changes` is een lijst; elk item noemt projectoren en wat ze krijgen:

```json
{ "fixtures": [2, 3], "values": { "dimmer": 80, "color": "#00ff00", "pan": 40 }, "variables": { "color": "Warm white" } }
```

`values`: `dimmer`, `pan`, `tilt`, `strobe`, `gobo`, `gobo_spin`, `gobo2`, `gobo2_spin`, `prism`, `focus`, `zoom` in procenten, `color`, ruwe kanalen `ch<N>` (0–255). `variables` koppelt een type (`dimmer`, `position`, `color`, `focus`, `zoom`, `gobo`) aan een variabele: de cue **verwijst dan naar de variabele** (een plaatshouder, live opgelost als de cue loopt) in plaats van de waarde op te slaan.

### Bewerken: variabelen – recht *Variabelen*

| Methode | Pad | Body | Wat het doet |
|---|---|---|---|
| POST | `/variables` | `{"name": "Warm white", "type": "color", "group": "Colours", "values": {"hex": "#ffb060"}}` | Maakt aan |
| PUT | `/variables/{ref}` | `{"name": "…", "group": "…", "values": {…}}` | Wijzigt; het type kan niet veranderen. Een nieuwe waarde bereikt de programmer, lopende cues en **elke cue die de variabele gebruikt** |
| DELETE | `/variables/{ref}` | – | Verwijdert (koppelingen van de programmer worden vrijgegeven) |
| POST · DELETE | `/variable-groups` · `/variable-groups/{name}` | `{"name": "Colours"}` | Maakt / verwijdert een groep (zijn variabelen blijven) |

`values` per type: `dimmer`, `focus`, `zoom`: `{"level": 0-100}` · `position`: `{"pan": 0-100, "tilt": 0-100}` · `color`: `{"r","g","b"}` of `{"hex": "#ff8000"}` · `gobo`: `{"level", "spin", "gobo2", "gobo2_spin"}`.

### Bewerken: effecten – recht *Effecten*

| Methode | Pad | Body | Wat het doet |
|---|---|---|---|
| POST | `/effects` | `{"script": "strobe", "name": "Blink", "group": "…", "params": {"rate_hz": 8}}` | Maakt een effect van een effecttype (`GET /effect-scripts`); `params` worden getoetst aan de grenzen van het type |
| PUT | `/effects/{ref}` | `{"name", "group", "params"}` | Wijzigt (het type kan niet veranderen) |
| DELETE | `/effects/{ref}` | – | Verwijdert; het stopt overal |
| POST | `/effects/{ref}/assign` | `{"fixtures": [2, 3]}` (ook `group`) | **Start** het effect op projectoren (de volgorde verdeelt golven) |
| POST | `/effects/release` | `{"fixtures": [2], "categories": ["dimmer"]}` | **Stopt** effecten op projectoren (de waarden blijven) |
| POST · DELETE | `/effect-groups` · `/effect-groups/{name}` | `{"name": "…"}` | Maakt / verwijdert een groep |

### Bewerken: effectscripts – recht *Effectscripts*

| Methode | Pad | Body | Wat het doet |
|---|---|---|---|
| POST | `/effect-scripts/check` | `{"text": "…"}` | Compileert en test een script zonder op te slaan: `{ok, line, message}` |
| POST | `/effect-scripts/preview` | `{"text": "…", "count": 3, "duration": 4, "bpm": 120, "params": {…}}` | Simuleert de curven zonder projectoren |
| PUT | `/effect-scripts/{name}` | `{"text": "…", "overwrite": false}` | Slaat op als bestand in de effectenmap van de gebruiker – **alleen als het compileert en draait** (`422 invalid_script` met de regel). Een bestaande naam vraagt `overwrite` |
| DELETE | `/effect-scripts/{name}` | – | Verwijdert een script uit de gebruikersmap; effecten van dit type stoppen |

De scripttaal wordt beschreven in de handleiding *Effectenstudio*.

### Bewerken: patch en projectorgroepen – recht *Patch en projectorgroepen*

| Methode | Pad | Body | Wat het doet |
|---|---|---|---|
| POST | `/fixtures` | `{"type": "Generic RGBW LED Par", "mode": "…", "name": "Par", "quantity": 4, "universe": 1, "address": 11, "group": "Wash"}` | Patcht een of meer projectoren achter elkaar. De adressen worden gecontroleerd (ze moeten in 512 passen en mogen niet overlappen – `allow_overlap: true` forceert) |
| PUT | `/fixtures/{fixture}` | `{"name", "universe", "address", "sort_index", "group", "allow_overlap"}` | Wijzigt; `"group": ""` haalt hem uit zijn groep |
| DELETE | `/fixtures/{fixture}` · POST `/fixtures/delete` | `{"fixtures": [1, 2]}` | Verwijdert (cues behouden hun items voor de ontbrekende projector, zoals in het venster) |
| POST | `/groups` | `{"name": "Wash", "fixtures": [2, 3]}` | Maakt een projectorgroep |
| POST | `/fixture-types` | het ruwe `.gdtf`-bestand; header `X-Filename` (URL-gecodeerd) | Installeert een projectortype (tot 30 MB; gecontroleerd vóór de installatie) |
| DELETE | `/fixture-types/{id}` | – | Verwijdert een geïnstalleerd type (`409 in_use` zolang de show het gebruikt) |
| PUT · DELETE | `/groups/{name}` | `{"name": "…", "fixtures": […]}` | Hernoemt / stelt de leden in (vervangt de lijst) / verwijdert (de projectoren blijven) |

### Bewerken: showbestanden – recht *Showbestanden*

| Methode | Pad | Body | Wat het doet |
|---|---|---|---|
| POST | `/showfile/new` | `{"force": false}` | Start een nieuwe, lege show |
| POST | `/showfile/save` | – | Slaat op onder de huidige naam (`409 never_saved` als er nog geen bestand is) |
| POST | `/showfile/save-as` | `{"name": "Concert", "overwrite": false}` | Slaat op onder een naam (tekens die in bestandsnamen niet zijn toegestaan, worden verwijderd) |
| POST | `/showfile/load` | `{"name": "Concert", "force": false}` | Laadt een opgeslagen show – vervangt de lopende |
| POST | `/showfiles/{name}/rename` | `{"new_name": "…", "overwrite": false}` | Hernoemt een opgeslagen bestand |
| POST | `/showfiles/{name}/duplicate` | – | Kopieert een opgeslagen bestand |
| DELETE | `/showfiles/{name}` | `?force=true` voor het geladen bestand | Verwijdert een opgeslagen bestand |

**Nieuw** en **Laden** vervangen de lopende show. Bij niet-opgeslagen wijzigingen worden ze geweigerd met `409 unsaved_changes` tot u eerst opslaat of `"force": true` stuurt.

### Bewerken: media – recht *Media*

| Methode | Pad | Body | Wat het doet |
|---|---|---|---|
| POST | `/media` | het ruwe bestand; header `X-Filename` (URL-gecodeerd) | Uploadt een video- / audiobestand (tot 1 GB; hetzelfde bestand twee keer is één item) |
| PUT | `/media/{id}` | `{"name": "…"}` | Hernoemt |
| DELETE | `/media/{id}` | – | Haalt uit de show en verwijdert de kopie |

### Bewerken: indelingen en instellingen – rechten *Indelingen* en *DMX-uitgangen en taal*

| Methode | Pad | Body | Wat het doet |
|---|---|---|---|
| POST | `/layouts/{filename}/load` | – | Toont een opgeslagen indeling (`Name.json` zoals in `GET /layouts`) in het consolevenster; niet-opgeslagen indelingswijzigingen gaan daar verloren |
| PUT | `/system` | `{"artnet": {"enabled": true, "ip": "2.255.255.255", "bind_ip": ""}, "sacn": {"enabled": true}, "enttec": {"enabled": false, "port": "COM3", "universe": 1}, "default_universe": 1, "language": "de"}` – elk veld optioneel | Schakelt de DMX-uitgangen en wijzigt taal / standaarduniversum; het antwoord is `GET /system` |
| POST | `/system/dmx/reinitialize` | – | Herstart de DMX-uitgangen zonder het programma te herstarten |

### Documentatie (geen token)

| Methode | Pad | Geeft terug |
|---|---|---|
| GET | `/docs` | Een leesbaar, doorzoekbaar overzicht van alle routes (werkt offline) |
| GET | `/openapi.json` | De machineleesbare beschrijving (OpenAPI 3.1); elke route noemt zijn recht als `x-capability` |

---

## 6. Voorbeelden met echte antwoorden

### Status

```
GET /api/v1/status
```

```json
{
  "app": { "name": "OpenCue", "version": "1.0.0" },
  "show": { "name": "Concert", "unsaved_changes": true },
  "blackout": false,
  "grand_master": 100.0,
  "timecode": { "running": false, "direction": 1, "rate": 1.0, "position_ms": 0.0, "position": "00:00:00.000" },
  "selection": { "fixture_ids": ["228a68e5-…"], "fids": [2] },
  "active_cuelist": { "id": "7e5d274f-…", "name": "Show" },
  "dmx": { "universes": [1], "artnet": true, "sacn": false, "usb": false },
  "counts": { "fixtures": 2, "groups": 1, "variables": 0, "effects": 0, "cuelists": 1, "cues": 2 }
}
```

### Welke projectoren zitten in de show, en welke kleur hebben ze?

```
GET /api/v1/fixtures?include_state=true
GET /api/v1/fixtures/state
```

```json
{
  "fixtures": [
    { "id": "9ea4feaa-…", "fid": 1, "name": "Front", "state": { "dimmer": 80.0 } },
    { "id": "228a68e5-…", "fid": 2, "name": "Par left",
      "state": { "dimmer": 100.0, "color": { "r": 255, "g": 0, "b": 0, "hex": "#ff0000" } } }
  ]
}
```

`state` bevat precies wat de console nu uitvoert, gelezen uit de DMX-buffer: `dimmer`, `pan`, `tilt`, `zoom`, `focus` … in procenten en `color` als r/g/b. Attributen die een projector niet heeft, ontbreken. (Bij grand master 0 of blackout kan de dimmer niet worden gereconstrueerd en blijft weg.)

### Eén projector met alle kanalen

```
GET /api/v1/fixtures/2
```

```json
{
  "id": "228a68e5-…", "fid": 2, "name": "Par left", "type": "Generic RGBW LED Par", "manufacturer": "Generic",
  "universe": 1, "start_channel": 11, "end_channel": 14, "channel_count": 4, "mode": "default", "group": "Wash",
  "channels": [
    { "channel": 1, "name": "ColorAdd_R", "address": 11, "value": 255 },
    { "channel": 2, "name": "ColorAdd_G", "address": 12, "value": 0 },
    { "channel": 3, "name": "ColorAdd_B", "address": 13, "value": 0 },
    { "channel": 4, "name": "ColorAdd_W", "address": 14, "value": 0 }
  ],
  "state": { "color": { "r": 255, "g": 0, "b": 0, "hex": "#ff0000" } }
}
```

### Wat wijzigt een cue?

```
GET /api/v1/cuelists/Show/cues/1
```

```json
{
  "id": "700571ee-…", "number": 1, "name": "Auf", "active": false,
  "trigger": "go", "timecode_ms": null, "timecode": null, "audio": null, "midi": null, "clock": null,
  "fade": 2.0, "delay": 0.0,
  "times": { "color": { "fade": null, "delay": null }, "position": { "fade": null, "delay": null },
             "beam": { "fade": null, "delay": null }, "zoom": { "fade": null, "delay": null } },
  "effect_fade": { "in": 0.0, "out": 0.0 }, "mib": "Off", "command": "", "fixture_count": 2,
  "changes": [
    { "fixture_id": "9ea4feaa-…", "fid": 1, "name": "Front", "values": { "dimmer": 50 }, "variables": {} },
    { "fixture_id": "228a68e5-…", "fid": 2, "name": "Par left",
      "values": { "dimmer": 100, "color": { "r": 255, "g": 0, "b": 0, "hex": "#ff0000" } }, "variables": {} }
  ],
  "effects": [],
  "cuelist": { "id": "7e5d274f-…", "name": "Show" }
}
```

- `fade` / `delay` zijn de algemene tijden; `times` bevat de optionele tijden per attribuutgroep (`null` = gebruikt de algemene tijd).
- `changes[].values` zijn de vaste waarden die in de cue zijn opgeslagen. `variables` toont de variabelen (plaatshouders) waarnaar de cue verwijst, op type en naam – een variabele wordt live opgelost als de cue loopt.
- `effects` toont de effecten die de cue start, per projector.
- Alle cues van een lijst tegelijk met hun details: `GET /api/v1/cuelists/Show/cues?detail=true`.

### Het DMX-signaal

```
GET /api/v1/dmx/1?first=1&last=14
GET /api/v1/dmx/1?nonzero=true
```

```json
{ "universe": 1, "first": 1, "last": 14, "values": [0,0,0,0,0,0,0,0,0,0,255,0,0,0] }
{ "universe": 1, "first": 1, "last": 512, "channels": { "11": 255 } }
```

### Een consoleopdracht uitvoeren

```
POST /api/v1/command
{ "command": "Fixture 1 Thru 4 At 80" }
```

```json
{ "command": "Fixture 1 Thru 4 At 80", "success": true, "message": "OK: 4 fixtures selected; At 80 applied" }
```

Alle opdrachten van de opdrachtregel werken, ook gekoppeld met `;` (zie de handleiding *Opdrachtenreferentie*).

### Een cue triggeren

```
POST /api/v1/cuelists/Show/go            { "cue": "2" }
```

```json
{ "cuelist": { "id": "7e5d274f-…", "name": "Show" }, "command": "Cuelist \"Show\" Go Cue 2", "success": true, "message": "OK: Go Cue 2 [Show]" }
```

Zonder body start `go` de volgende cue. Let op: een cuelijst waarvan de **naam een aanhalingsteken bevat**, kan op deze manier niet worden aangesproken; hernoem hem.

### Tijdcode

```
PUT /api/v1/timecode   { "action": "seek", "position": "1:04.300" }
PUT /api/v1/timecode   { "action": "play", "position": 10 }
GET /api/v1/timecode
```

```json
{ "running": false, "direction": 1, "rate": 1.0, "position_ms": 64300.0, "position": "00:01:04.300" }
```

`position` is een getal in **seconden** of tekst zoals `1:04.300` of `00:00:04.300`. `play` mag vanaf een `position` starten en met `"direction": -1` achteruit lopen; `rate` is de snelheid tussen 0,1 en 8. Springen met `seek` laat tijdcodecues niet afgaan.

### DMX-kanalen instellen

```
PUT /api/v1/dmx/1/200                      { "value": 255 }
PUT /api/v1/dmx/1                          { "channels": { "201": 10, "202": 20 } }
PUT /api/v1/fixtures/Front/channels/Dimmer { "percent": 50 }
```

```json
{ "universe": 1, "channel": 1, "value": 128, "fixture": { "fid": 1, "name": "Front" }, "channel_of_fixture": 1 }
```

Een kanaal dat bij een **projector** hoort, wordt ingesteld zoals de *DMX direct*-fader van de programmer: het wordt een handmatige waarde die lopende cues niet meer mengen. Andere kanalen worden rechtstreeks naar de uitvoer geschreven. Dit recht staat **standaard uit**.

### Audio: lezen en bedienen

```
GET  /api/v1/audio/devices                    -> { "devices": [ { "id": "demo", "kind": "demo", "name": "Demo beat" }, ... ] }
PUT  /api/v1/audio    { "device": "demo" }    open that source (`running` false closes it)
PUT  /api/v1/audio    { "settings": { "mode": "manual", "bpm": 128, "sensitivity": 0.7 } }
POST /api/v1/audio/tap                        tap the tempo (about 4 taps in a row set it, the tempo switches to manual)
GET  /api/v1/audio                            level, bands, kick / snare / hat, bpm, beat_phase ... and the settings
```

`PUT /audio` past eerst de `settings` toe, opent dan (`running: true`, of een `device`) of sluit (`running: false`) de bron en antwoordt zoals `GET /audio`. Kan de bron niet worden geopend, dan is het antwoord `409 audio_failed` met de reden. Instellingen: `gain`, `auto_gain`, `sensitivity`, `smoothing`, `latency_ms`, `mode` (`auto` | `manual`), `bpm` (handmatig tempo), `phase_follow`, `demo_bpm`, `autostart`; onbekende sleutels worden genegeerd en getallen worden tot hun bereik begrensd.

### Een cue bouwen

```
POST /api/v1/cuelists/Show/cues
{
  "number": 3, "name": "Blue wash", "fade": 3,
  "changes": [
    { "group": "Wash", "values": { "dimmer": 80, "color": "#0000ff" } },
    { "fixtures": [1], "values": { "dimmer": 20 } }
  ],
  "effects": [ { "fixtures": [2, 3], "effects": { "dimmer": "Blink" } } ]
}
```

```json
{ "status": "created", "cuelist": { "id": "7e5d274f-…", "name": "Show" },
  "cue": { "id": "5c0b…", "number": 3, "name": "Blue wash", "fade": 3.0, "changes": [ … ], "effects": [ … ], … } }
```

Het antwoord is de hele cue zoals `GET …/cues/3` hem zou tonen. Bestaat cue 3 al, dan krijgt u `409 cue_exists`; stuur `"on_conflict": "merge"` om de verstuurde attributen eraan toe te voegen, of `"overwrite"` om zijn inhoud te vervangen (status `merged` / `overwritten`).

Hetzelfde vanuit de programmer, zoals *Store Cue*:

```
PUT  /api/v1/programmer/values   { "fixtures": [2, 3], "values": { "color": "#ff8000", "dimmer": 100 } }
POST /api/v1/cuelists/Show/cues  { "number": 4, "name": "Orange", "from_programmer": true, "clear_programmer": true }
```

### Cues wijzigen en verwijderen

```
PUT    /api/v1/cuelists/Show/cues/3   { "name": "Deep blue", "fade": 5, "times": { "color": { "fade": 8 } } }
PUT    /api/v1/cuelists/Show/cues/3   { "changes": [ { "fixtures": [1], "values": { "dimmer": 0 } } ] }                       (adds to the content)
PUT    /api/v1/cuelists/Show/cues/3   { "content": "replace", "changes": [ { "fixtures": [1], "values": { "dimmer": 0 } } ] } (content = exactly this)
PUT    /api/v1/cuelists/Show/cues/3   { "number": 2.5 }                                                                          (renumber)
DELETE /api/v1/cuelists/Show/cues/3
```

Alleen wat u verstuurt, verandert. Een wijziging aan een cue die loopt, werkt bij zijn volgende *Go*.

### Variabelen en effecten

```
POST /api/v1/variables  { "name": "Warm white", "type": "color", "values": { "hex": "#ffb060" } }
PUT  /api/v1/variables/Warm white   { "values": { "hex": "#ffa040" } }      -> every cue that uses it is warmer now
POST /api/v1/effects    { "script": "strobe", "name": "Blink", "params": { "rate_hz": 8 } }
POST /api/v1/effects/Blink/assign   { "fixtures": [2, 3] }                  -> it runs now
POST /api/v1/effects/release        { "fixtures": [2, 3] }                  -> stop it
```

`GET /api/v1/effect-scripts` toont de effecttypen met hun instellingen (`variables`: naam, soort, grenzen, standaard, labels in beide talen).

### Uw eigen effecttype schrijven

```
POST /api/v1/effect-scripts/check   { "text": "…" }                  -> { "ok": false, "line": 3, "message": "…" }
PUT  /api/v1/effect-scripts/my_wave { "text": "…", "overwrite": true }
POST /api/v1/effects                { "script": "my_wave" }
```

Een script wordt alleen opgeslagen als het compileert en draait. De taal is gedocumenteerd in de handleiding *Effectenstudio*.

### Projectoren patchen

```
GET  /api/v1/fixture-types?q=par
POST /api/v1/fixtures  { "type": "Generic RGBW LED Par", "quantity": 4, "name": "Par", "universe": 1, "address": 11, "group": "Wash" }
```

```json
{ "created": [ { "fid": 4, "name": "Par 1", "universe": 1, "start_channel": 11, "end_channel": 14, … },
               { "fid": 5, "name": "Par 2", "universe": 1, "start_channel": 15, … }, … ] }
```

Adressen die andere projectoren overlappen, worden geweigerd (`409 address_conflict`); `"allow_overlap": true` patcht toch.

### De programmer

```
GET  /api/v1/programmer
PUT  /api/v1/selection            { "group": "Wash" }
PUT  /api/v1/programmer/values    { "values": { "dimmer": 100, "color": [255, 0, 0] } }       (without fixtures: the selection)
POST /api/v1/programmer/variables { "variable": "Warm white" }
POST /api/v1/programmer/clear     { "fixtures": [2] }          forget their values (the output stays)
POST /api/v1/programmer/clear     { "all": true }              Clear Clear: every fixture dark, effects end
```

Zo ingestelde waarden gedragen zich als de faders van het programmervenster: de uitvoer verandert meteen, ze tellen als aangeraakt en de volgende *Store Cue* neemt ze over.

### Relatieve waarden (bijsturen in plaats van instellen)

```
curl -X PUT -H "Authorization: Bearer oc_xxxxxxxx" -H "Content-Type: application/json" \
  -d '{"group": "Front", "mode": "relative", "values": {"pan": 2.5, "dimmer": -10}}' \
  http://127.0.0.1:8000/api/v1/programmer/values
```

Met `"mode": "relative"` zijn de getallen **wijzigingen in procentpunten** (−100 tot 100); elke projector begint bij zijn eigen waarde en wordt bij 0 / 100 % begrensd. Kleuren en ruwe kanalen bestaan alleen als absolute waarden. Voor snelle reeksen wijzigingen (draaiknoppen, joystick) is de WebSocket (paragraaf 10) beter.

### Showbestanden

```
POST /api/v1/showfile/save-as  { "name": "Concert" }
POST /api/v1/showfile/load     { "name": "Concert", "force": false }
POST /api/v1/showfile/new      { "force": true }
```

Zonder `force` stoppen *load* en *new* met `409 unsaved_changes` als de lopende show niet-opgeslagen wijzigingen heeft. `GET /api/v1/showfile` meldt of dat zo is.

### Knoppen, faders en schakelaars van de console

```
GET /api/v1/widgets
POST /api/v1/widgets/b1/press
PUT  /api/v1/widgets/f1/value   { "value": 70 }
PUT  /api/v1/widgets/t1/state   { "on": true }
```

`GET /widgets` toont de panelen met hun `id`, `label`, opdracht en de huidige waarde (faders) of status (schakelaars). Indrukken, verschuiven of omschakelen voert de in het paneel ingestelde opdracht uit – dezelfde die een operator triggert – en de panelen op elk apparaat volgen (een ingedrukte knop pulseert, faders en schakelaars met dezelfde opdracht bewegen mee). Een faderwaarde wordt tot zijn minimum / maximum begrensd. Een paneel zonder opdracht antwoordt `409 no_command` (een schakelaar zonder opdrachten schakelt alleen om). De panelen zijn die van de indeling van de **console**; apparaten op afstand hebben eigen indelingen.

### Uitgangen en indelingen

```
PUT  /api/v1/system   { "artnet": { "ip": "192.168.1.255" }, "sacn": { "enabled": false } }
POST /api/v1/layouts/Concert.json/load
POST /api/v1/fixture-types   (raw .gdtf file, header X-Filename: my_fixture.gdtf)
```

### Een medium uploaden

```
curl -X POST -H "Authorization: Bearer oc_xxxxxxxx" -H "Content-Type: application/octet-stream" \
     -H "X-Filename: intro.mp4" --data-binary @intro.mp4 http://127.0.0.1:8000/api/v1/media
```

### Live-gebeurtenissen (stroom)

```
curl -N -H "Authorization: Bearer oc_xxxxxxxx" "http://127.0.0.1:8000/api/v1/events?events=cue,blackout,command"
```

```
event: hello
data: {"app": "OpenCue", "events": ["blackout", "cue", "command"]}

event: cue
data: {"cuelists": [{"id": "7e5d…", "name": "Show", "active_cue": {"id": "700…", "number": 2, "name": "Blue", …}}]}

event: command
data: {"command": "Fixture 1 At 10", "success": true, "message": "OK: …", "time": "21:14:03"}
```

De verbinding blijft open. Eerst komen `hello` en één bericht per soort met de **huidige toestand**, daarna elke wijziging. Soorten: `cue` (actieve cue van een lijst gewijzigd), `cuelists` (lijsten / cues toegevoegd, verwijderd, hernoemd), `blackout`, `master`, `timecode` (gestart, gestopt, snelheid), `selection`, `effects`, `fixtures`, `variables`, `show` (naam / niet-opgeslagen wijzigingen), `command` (een consoleopdracht liep, van waar ook), `audio` (bron geopend / gesloten, tempo, signaal aanwezig). Alleen op verzoek (`?events=beat,hit`): `beat` (elke beat, met het tempo) en `hit` (elke slag van basdrum / snare / hi-hat: `{"drum": "kick", "strength": 0.9}`). `?events=` beperkt de stroom. Wijzigingen worden binnen ongeveer 0,1 s opgemerkt. Elke 15 s komt een commentaarregel (`: keep-alive`); er lopen hoogstens 20 stromen tegelijk. Vraagt het recht *Status*.

In een browser kan `EventSource` geen headers versturen: gebruik dan `?access_token=<token>`, of `fetch()` met een header en lees de stroom. Het token verschijnt dan in het adres, geef zo'n pagina dus een eigen token met alleen *Status*.

---

## 7. Kleine programma's

Python, met de bibliotheek `requests` (elke HTTP-bibliotheek werkt):

```python
import requests

BASE = "http://127.0.0.1:8000/api/v1"
HEAD = {"Authorization": "Bearer oc_xxxxxxxx"}

# What is the colour of every fixture?
for fx in requests.get(f"{BASE}/fixtures/state", headers=HEAD).json()["fixtures"]:
    color = fx["state"].get("color")
    print(fx["fid"], fx["name"], color["hex"] if color else "-")

# Dim the front lights, then start the next cue
requests.post(f"{BASE}/command", headers=HEAD, json={"command": "Fixture 1 At 30"})
requests.post(f"{BASE}/cuelists/Show/go", headers=HEAD)
```

Een kleine show bouwen (vraagt de bewerkrechten):

```python
requests.post(f"{BASE}/fixtures", headers=HEAD, json={"type": "Generic RGBW LED Par", "quantity": 4, "name": "Par", "address": 1, "group": "Wash"})
requests.post(f"{BASE}/variables", headers=HEAD, json={"name": "Warm", "type": "color", "values": {"hex": "#ffb060"}})
requests.post(f"{BASE}/cuelists", headers=HEAD, json={"name": "Show"})
requests.post(f"{BASE}/cuelists/Show/cues", headers=HEAD, json={
    "number": 1, "name": "Warm", "fade": 3,
    "changes": [{"group": "Wash", "values": {"dimmer": 80}, "variables": {"color": "Warm"}}]})
requests.post(f"{BASE}/showfile/save-as", headers=HEAD, json={"name": "From the API"})
```

Een webpagina die de actieve cue live toont (JavaScript in de browser; de pagina mag van elk adres komen, zie paragraaf 8):

```javascript
const res = await fetch("http://192.168.1.20:8000/api/v1/events?events=cue", { headers: { Authorization: "Bearer oc_xxxxxxxx" } });
const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
for (;;) {
  const { value, done } = await reader.read();
  if (done) break;
  console.log(value);          // "event: cue\ndata: {...}\n\n"
}
```

---

## 8. Andere apparaten en beveiliging

- **Vanaf een andere computer of tablet** is de API bereikbaar zodra **Toegang via HTTP toestaan** (Instellingen → Toegang op afstand) aan staat. Gebruik het adres van de console (op die pagina getoond) in plaats van `127.0.0.1`, bijvoorbeeld `http://192.168.1.20:8000/api/v1/status`. Staat toegang op afstand uit, dan is de poort voor het netwerk gesloten. Het **token vervangt daar het wachtwoord** – aanmelden is niet nodig.
- Tokens geven echte controle over de lampen. Geef elk programma zijn **eigen token met alleen de rechten die het nodig heeft** en verwijder tokens die u niet meer gebruikt.
- De **bewerkrechten staan standaard uit** en kunnen showgegevens wijzigen of vernietigen: *Patch*, *Showbestanden* en *Consoleopdrachten* zijn als **kritiek** gemarkeerd. *Laden* en *Nieuw* weigeren niet-opgeslagen wijzigingen weg te gooien zonder `force`.
- Het verkeer is gewoon HTTP binnen uw netwerk. Stel de poort niet bloot aan internet.
- **Webpagina's op andere adressen** (uw eigen dashboard, een webtool in de browser) mogen de API rechtstreeks aanroepen: de antwoorden dragen de headers voor toegang tussen herkomsten (CORS) en het preflight-verzoek van de browser (`OPTIONS`, dat geen token kan dragen) wordt beantwoord. De pagina heeft nog steeds een token in de `Authorization`-header nodig en moet het token voor zichzelf houden (zet geen krachtig token in een openbare webpagina). Zet het uit in *Instellingen → API → Webpagina's op andere adressen toestaan* als u het niet nodig hebt; browsers blokkeren zulke pagina's dan weer (programma's en scripts worden niet geraakt).
- De API wijzigt de show **in het geheugen**, zoals het venster. Er wordt niets op schijf bewaard tot de show wordt opgeslagen (`POST /showfile/save`, of *Opslaan* in het venster).

---

## 9. Als iets niet werkt

| Probleem | Controleer |
|---|---|
| `401 unauthorized` | Header geschreven als `Authorization: Bearer oc_…` met het volledige token? Token verwijderd of opnieuw gegenereerd? |
| `403 forbidden` | Het token mist dit recht – open het token in *Instellingen → API* en zet het aan (het bericht noemt het). |
| `403 api_disabled` | De hoofdschakelaar in *Instellingen → API* staat uit. |
| `403 remote access disabled` | U roept aan vanaf een ander apparaat terwijl *Toegang via HTTP toestaan* uit staat. |
| `404 not_found` | Controleer het projectornummer, de naam van de cuelijst (precies) en het cuenummer. |
| `409 duplicate` | De naam is bezet (hoofdletters / kleine letters maken niet uit). Kies een andere naam of wijzig de bestaande met `PUT`. |
| `409 cue_exists` | Een cue met dit nummer staat in de lijst: `on_conflict` of `PUT`. |
| `409 unsaved_changes` | Sla eerst op (`POST /showfile/save`) of stuur `force: true`. |
| `409 no_command` / `409 wrong_type` | Een paneel heeft geen opdracht ingesteld / u drukte op een fader, verschoof een knop … (zie `GET /widgets` voor het type). |
| `422` | Een veld dat niet bestaat (typfout?) of een verkeerd type – het bericht noemt het veld. |
| `422 invalid_script` | Het script bevat een fout – het bericht noemt de regel. `POST /effect-scripts/check` test zonder op te slaan. |
| `200` maar `"success": false` | De opdracht is afgewezen – lees `message`. |
| `429` | Te veel verkeerde tokens vanaf dit adres. Wacht `Retry-After` seconden. |
| Browserpagina: "geblokkeerd door CORS" | *Instellingen → API → Webpagina's op andere adressen toestaan* staat uit, of het verzoek heeft geen token (het foutantwoord van de API draagt de headers, dus de echte reden is zichtbaar). |
| Helemaal geen antwoord | Draait OpenCue en is de poort goed (Instellingen → Toegang op afstand toont hem)? |

---

## 10. Hardware en snelle bediening: de WebSocket-stroom

Voor **hardware** (ESP32, Arduino, Raspberry Pi, een zelfgebouwd bureau) en elke toepassing die **veel kleine waarden snel verstuurt of ontvangt**, is er naast de HTTP-routes een **WebSocket**: `ws://<console>:8000/api/v1/ws`. Eén verbinding blijft open en beide kanten sturen kleine **JSON-berichten** (tekstframes) – zonder de kosten van een nieuw HTTP-verzoek per waarde. Er is geen extra recht nodig: elk bericht vraagt **hetzelfde recht als de bijbehorende HTTP-route** (tabel hieronder). Met de voorinstelling *Bedienen* werkt alles behalve ruwe DMX.

### Verbinden en aanmelden

Het token kan op drie manieren worden verstuurd (microcontrollers vinden het adres het gemakkelijkst):

1. in het adres: `ws://opencue.local:8000/api/v1/ws?access_token=oc_xxxxxxxx`
2. in de header: `Authorization: Bearer oc_xxxxxxxx` (of `X-API-Key`)
3. als **eerste bericht** binnen 5 s: `{"op": "auth", "token": "oc_xxxxxxxx"}`

Daarna stuurt OpenCue `{"op": "hello", ...}` met de toegestane rechten, bewerkingen, onderwerpen en limieten. Fouten sluiten de verbinding met een code: `4401` (token ontbreekt / fout), `4403` (API uit, alleen deze pc, toegang op afstand uit, token uitgeschakeld), `4429` (te veel mislukte pogingen / te veel verbindingen). Dezelfde regels als voor HTTP gelden: *REST-API aan*, *Bereikbaar vanaf*, uitsluiting na mislukte pogingen. Er zijn hoogstens 10 verbindingen tegelijk open.

Elk bericht is een JSON-object met `"op"`. Een optionele **`"id"`** (elk getal of elke tekst) komt terug in het antwoord: `{"op": "ack", "id": 7, ...}` bij succes, `{"op": "error", "id": 7, "code": "...", "message": "..."}` bij een fout. Zonder `id` worden alleen fouten beantwoord. Een foutief bericht beëindigt de verbinding nooit.

### Berichten van de hardware

| `op` | Recht | Wat het doet |
|---|---|---|
| `joystick` | Programmer | Een joystick – zie hieronder |
| `set` | Programmer | Waarden instellen, **absoluut** of **relatief** – zie hieronder |
| `select` | Programmer | De selectie wijzigen: `{"op":"select","mode":"set","fixtures":[1,2]}` (`mode`: `set`, `add`, `remove`, `clear`) |
| `cmd` | Opdrachten | Consoleopdracht: `{"op":"cmd","line":"Cuelist Main Go"}` (antwoord: `success`, `message`) |
| `cue` | Cues | `{"op":"cue","list":"Main","action":"go"}`; `action`: `go` (met `"cue": 5` springt hij), `back`, `pause`, `resume`, `stop`, `fader` (met `"value"`) |
| `master`, `blackout` | Blackout / Master | `{"op":"master","value":70}`, `{"op":"blackout","on":true}` |
| `dmx` | DMX-kanalen | `{"op":"dmx","universe":1,"channels":{"1":255,"2":0}}` – ruwe kanaalwaarden zoals `PUT /dmx/{universe}` |
| `tap` | Audio | Het tempo tikken (een knop op de ESP32) |
| `timecode` | Tijdcode | De tijdcode bedienen: `{"op":"timecode","action":"play"}` (ook `pause`, `stop`, `seek`, `rate`) – of `{"op":"timecode","action":"sync","position":12345,"running":true}`: OpenCue **volgt** een externe klok (positie in ms of `"0:12.345"`; afwijkingen onder 60 ms worden niet gecorrigeerd zodat de klok niet jittert; een sprong verplaatst hem zonder cues te laten afgaan) |
| `audio_in` | Audio | Audio **in** – zie hieronder |
| `subscribe`, `unsubscribe` | per onderwerp | **Abonneren** op live waarden – zie hieronder |
| `ping` | – | Antwoord `{"op":"pong","t":<uw t>,"server_ms":...}`: de rondreistijd meten, klokken vergelijken |

Doelen (`set`, `joystick`, `select`) heten zoals in de HTTP-routes: `"fixtures": [1, 2, "Front 3"]`, `"fixture": 5`, `"group": "Front"` en / of `"selection": true` (de selectie van de console). Zonder een van deze wordt de selectie gebruikt.

### Waarden instellen: absoluut en relatief

```json
{"op": "set", "fixtures": [1, 2], "values": {"dimmer": 80, "pan": 25, "color": "#ff8800"}}
{"op": "set", "group": "Front", "mode": "relative", "values": {"pan": 2.5, "dimmer": -10}}
```

- **absoluut** (standaard): de waarden zijn de nieuwe waarden – procent 0–100, kleur als `#rrggbb` / `[r,g,b]`, ruwe kanalen als `ch<N>` (0–255).
- **relatief** (`"mode": "relative"`): de getallen zijn **wijzigingen in procentpunten** (−100 tot 100); elke projector begint bij **zijn eigen** waarde en wordt bij 0 / 100 % begrensd. Dat past bij draaiknoppen en "een beetje verder"-knoppen. Kleuren en ruwe kanalen kunnen niet relatief zijn.

HTTP heeft hetzelfde: `PUT /programmer/values` met `"mode": "relative"`. Pan en tilt worden met de volledige **16-bitresolutie** (grof en fijn) ingesteld.

### Joystick

```json
{"op": "joystick", "selection": true, "x": 0.35, "y": -0.8}
```

`x` en `y` lopen van −1 tot 1 (rechts / omhoog positief). Standaard stuurt hij pan (`x`) en tilt (`y`) van de geselecteerde projectoren aan; `"axes": {"x": "pan", "y": "zoom"}` wijst elk attribuut toe (`dimmer`, `zoom`, `focus`, `strobe`, `gobo`, `prism` ...). Twee modi (`"mode"`):

- **`rate`** (standaard, **relatief**): de uitslag bepaalt de **snelheid**, niet de positie – zoals de joystick in de programmer. Kleine uitslagen zijn zeer nauwkeurig (dicht bij het midden ongeveer 1° per seconde), grote snel (helemaal buiten loopt het hele bereik in enkele seconden door); de curve is exponentieel. OpenCue integreert de beweging **zelf op 40 Hz** uit de laatst gemelde uitslag – het apparaat hoeft alleen wijzigingen en de huidige waarde elke 20–50 ms te sturen; wifi-jitter maakt de beweging niet schokkerig. Meerdere geselecteerde projectoren bewegen evenveel vanaf **hun** beginwaarde; aan het einde van het bereik stoppen ze. Bij `x = y = 0` (of binnen de dode zone) is de stok losgelaten: **de projectoren blijven waar ze zijn**.
- **`position`** (**absoluut**): de uitslag is de positie – `x = −1` is pan 0 %, `x = 1` pan 100 %. Niet nuttig voor een veerbelaste stok, wel voor een encoder of een schuif.

Meer velden: `stick` (een naam als een apparaat meerdere stokken heeft; standaard `main`, tot 4), `speed` (factor 0,05–4 voor de snelheid, standaard 1), `deadzone` (0–0,5, standaard 0,04), `timeout_ms` (100–5000, standaard 500), `invert_y`, `release: true` (meteen loslaten). De doelen worden vastgelegd als de stok voor het eerst wordt aangeraakt en bewaard tot hij wordt losgelaten.

**Dodemansschakelaar:** komt er langer dan `timeout_ms` geen bericht (kabel eruit, wifi weg, apparaat hangt), dan stopt de stok en meldt OpenCue `{"op":"joystick","stick":"main","state":"timeout"}`. Valt de verbinding weg, dan blijven alle projectoren waar ze zijn.

### Abonneren op live waarden

`{"op":"subscribe","topic":"<topic>","hz":30}` – `hz` is de hoogste frequentie (1–60, standaard 30). OpenCue stuurt alleen wat **gewijzigd** is. `unsubscribe` met `"topic"` beëindigt het abonnement.

| `topic` | Recht | Berichten |
|---|---|---|
| `audio` | Status | `{"op":"audio","t":ms,"running":true,"v":{"a_level":0.62,"a_bass":0.9,"a_bpm":124,...}}` – de audiovariabelen van de audio-analyse; `"keys": ["a_level","a_bass"]` beperkt ze |
| `dmx` | DMX | `"universes": [1]` (tot 8): eerst `{"op":"dmx","universe":1,"full":true,"values":[512 numbers]}`, daarna alleen `{"op":"dmx","universe":1,"changes":{"17":255}}` (kanaal → waarde) |
| `fixtures` | DMX | `{"op":"fixtures","values":{"3":{"pan":12.5,"tilt":50,"dimmer":100,"color":{...}}}}` – live waarden per projector**nummer**, alleen de gewijzigde |
| `timecode` | Status | `{"op":"timecode","ms":83400,"text":"00:01:23.400","running":true,"direction":1,"rate":1}` – terwijl de klok loopt bij elke tik (tot 60 Hz), anders alleen bij een wijziging (start, stop, sprong, snelheid) |
| `events` | Status | zoals `GET /events`: `{"op":"event","event":"cue","data":{...}}`; `"events": ["cue","blackout"]` kiest (standaard: de standaardsoorten; `beat` en `hit` alleen op verzoek). De huidige toestand komt eerst |

### Audio in: een microfoon op de ESP32

Met de audiobron **"Netwerk (API-stroom)"** analyseert OpenCue audio die een apparaat verstuurt – niveau, banden, kick / snare / hi-hat, tempo en beat bestaan dan als `a_`-variabelen voor **effecten, cuetriggers en het Audio-paneel** zoals gewoonlijk.

1. Open de bron: kies *Netwerk (API-stroom)* in het Audio-paneel, of `PUT /audio` met `{"device": "network"}`, of doe het met het bericht van stap 2 (`"open": true`).
2. `{"op":"audio_in","rate":16000,"open":true}` – kondigt PCM aan (`rate` 8000–48000 Hz, **16 bit signed little endian, mono**).
3. Stuur daarna **binaire frames** (WebSocket binair) met de samples, bijv. 20 ms per keer (640 bytes bij 16 kHz). Hoogstens 64 KB per frame.

Is de bron niet open, dan antwoordt OpenCue (hoogstens één keer per seconde) met de fout `audio_source`. Zonder gegevens blijft de analyse op stilte doorlopen.

### Grenzen en bescherming

**De DMX-uitvoer heeft altijd voorrang**: ze draait in een eigen thread (iets hogere prioriteit) en de stroom is beperkt – hardware kan de console dus nooit vertragen. Hoogstens 300 berichten per seconde per verbinding (pieken tot 600) en 1200 in totaal – meer krijgt `rate_limited` en wordt weggegooid; tekstberichten tot 8 KB, binaire frames tot 64 KB; 10 verbindingen; een joystick verandert hoogstens met 40 Hz. Een verbinding die zich niet aanmeldt, wordt na 5 s gesloten.

### Voorbeeld: ESP32 met een joystick (Arduino)

```cpp
#include <WiFi.h>
#include <WebSocketsClient.h>          // Bibliothek "WebSockets" von Markus Sattler (arduinoWebSockets)

const char* WIFI_SSID = "MeinWLAN";
const char* WIFI_PASS = "geheim";
const char* TOKEN     = "oc_xxxxxxxx";      // Token mit "Programmer" (write.programmer)
const int PIN_X = 34, PIN_Y = 35;           // die beiden Achsen des Joysticks (ADC)

WebSocketsClient ws;
int centerX = 2048, centerY = 2048;

float norm(int raw, int center) {           // 0..4095 -> -1..1
  float f = (raw - center) / 2048.0f;
  return f < -1 ? -1 : (f > 1 ? 1 : f);
}

void onEvent(WStype_t type, uint8_t* payload, size_t length) {
  if (type == WStype_CONNECTED) Serial.println("OpenCue verbunden");
  if (type == WStype_TEXT)      Serial.printf("%s\n", payload);       // hello, Fehler, Rueckmeldungen
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) delay(200);
  delay(300);
  centerX = analogRead(PIN_X);              // Ruhelage beim Start merken
  centerY = analogRead(PIN_Y);
  String path = String("/api/v1/ws?access_token=") + TOKEN;
  ws.begin("opencue.local", 8000, path);    // oder die IP-Adresse der Konsole
  ws.onEvent(onEvent);
  ws.setReconnectInterval(2000);
  ws.enableHeartbeat(15000, 3000, 2);
}

void loop() {
  ws.loop();
  static uint32_t last = 0;
  if (ws.isConnected() && millis() - last >= 20) {      // 50 Mal pro Sekunde
    last = millis();
    float x = norm(analogRead(PIN_X), centerX);
    float y = -norm(analogRead(PIN_Y), centerY);        // nach oben = Tilt mehr
    char msg[128];
    snprintf(msg, sizeof msg, "{\"op\":\"joystick\",\"selection\":true,\"x\":%.3f,\"y\":%.3f}", x, y);
    ws.sendTXT(msg);
  }
}
```

Het apparaat blijft in rust `x = 0, y = 0` sturen – dat schaadt niet (de stok telt als losgelaten). De selectie op de console bepaalt wat beweegt; met `"fixtures": [1, 2]` of `"group"` in plaats van `"selection": true` ligt het doel vast.

### Voorbeeld: Python

```python
import asyncio, json, websockets            # pip install websockets

async def main():
    async with websockets.connect("ws://127.0.0.1:8000/api/v1/ws?access_token=oc_xxxxxxxx") as ws:
        print(json.loads(await ws.recv()))                           # hello
        await ws.send(json.dumps({"op": "set", "fixtures": [1, 2], "values": {"dimmer": 80}}))
        await ws.send(json.dumps({"op": "subscribe", "topic": "audio", "hz": 30, "keys": ["a_level", "a_bass"]}))
        async for text in ws:
            frame = json.loads(text)
            if frame["op"] == "audio":
                print(frame["v"])

asyncio.run(main())
```

Een referentie van alle berichten staat ook op de pagina `/api/v1/docs`.

---

## 11. Statusweergaven: afbeeldingen en webpagina's voor eenvoudige apparaten

Voor apparaten die alleen **een afbeelding kunnen ophalen** of een **gewone pagina** kunnen tonen – een ESP32 met een display, een oude tablet als wandscherm, een browsertabblad op de foyermonitor – zijn er **statusweergaven**. Ze zijn **alleen-lezen** (geen bediening), hebben **geen bibliotheek** op het apparaat nodig en OpenCue rendert ze zelf: de inhoud is hetzelfde als afbeelding of als pagina.

| Weergave | Toont | Recht |
|---|---|---|
| `status` | show, blackout, master, tijdcode, de actieve cue van elke lijst, tempo | Status |
| `timecode` | de klok, groot, "loopt / stilstaand" | Status |
| `dmx` | de 512 kanalen van een universum als raster (`?universe=1`), helderheid = waarde | DMX |
| `cue` | de actieve cue van een lijst (`?list=Main`) en de volgende | Status |
| `audio` | niveau, de acht banden, tempo | Status |

Elke weergave bestaat in meerdere vormen (`GET /api/v1/views/<name>…`):

| Adres | Resultaat |
|---|---|
| `/views/status` | **webpagina** die zichzelf ververst (`?refresh=2` seconden); zonder JavaScript via meta refresh |
| `/views/status.png` | **PNG-afbeelding** (`?w=320&h=240&theme=dark`; grootte 64×48 tot 800×600; `theme`: `dark` of `light`) |
| `/views/status.bmp` | 24-bits **BMP** – elke kleine decoder begrijpt het |
| `/views/status.rgb565` | **ruwe pixels**, elk 16 bit (5-6-5, hoge byte eerst); de grootte staat in de headers `X-Width` / `X-Height`: geef ze rechtstreeks aan een TFT (geen decoder nodig) |
| `/views/status.json` | het weergavemodel (onderdelen: titel, rijen, balken, raster) – voor wie zelf wil tekenen |
| `/views` | lijst van alle weergaven met hun parameters |

Meld u aan zoals gewoonlijk. Een browser of apparaat dat geen header kan versturen, voegt het token toe (`access_token`, `token` werkt ook; spaties en aanhalingstekens die bij het kopiëren zijn meegenomen, maken niet uit). Het bericht zegt of het token **ontbreekt** of **ongeldig / verwijderd** is; de console logt elke geweigerde aanmelding. Blijft het eerste laden van `opencue.local` hangen (Windows lost `.local`-namen de eerste keer soms langzaam op), gebruik dan het **IP-adres** – dat staat in *Instellingen → REST-API* (om te kopiëren): `…/views/status?access_token=oc_xxxxxxxx` (het token is dan deel van het adres – maak daarvoor een apart token **met alleen "Status" en "DMX"**). De schakelaar **Statusweergaven** in *Instellingen → REST-API* zet alles uit (antwoord `403 views_disabled`).

**Kleur:** `?color=green` (of `amber`, `red`, `blue`, `cyan`, `white`, `magenta`, `violet`, `orange`, `yellow`, of `#rrggbb`) wijzigt de accentkleur; de DMX-monitor is standaard **groen**.

**Fouten zijn zichtbaar:** is er iets mis (verkeerd token, weergaven uit, geen recht), dan komt er een **afbeelding** (`.png` / `.bmp` / `.rgb565`) terug met de juiste statuscode (401, 403 ...) **als beeld met het bericht** – een display toont het gewoon ("TOKEN MISSING OR WRONG", "STATUS VIEWS ARE OFF" ...); de **webpagina** toont een pagina met het bericht en herlaadt elke 5 s. Is OpenCue na het openen van de pagina niet meer bereikbaar, dan toont de pagina bovenaan **"Geen verbinding met OpenCue"** en dimt het laatste beeld tot het weer werkt. `.json` behoudt het JSON-foutbericht.

**De DMX-uitvoer heeft altijd voorrang:** afbeeldingen worden hoogstens elke 0,4 s per weergave en grootte opnieuw berekend (veel apparaten delen één afbeelding), in een achtergrondthread, en nooit meer dan vier tegelijk. Een afbeelding van 320×240 kost ongeveer 6 ms. De DMX-uitvoerthread draait bovendien met een iets hogere prioriteit.

### ESP32 met een TFT: om de twee seconden een afbeelding

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <TFT_eSPI.h>                       // 320 x 240 display

TFT_eSPI tft;
uint16_t frame[320 * 240];                  // 150 KB: on an ESP32 without PSRAM ask for 160 x 120 instead

void loop() {
  HTTPClient http;
  http.begin("http://opencue.local:8000/api/v1/views/status.rgb565?w=320&h=240&access_token=oc_xxxxxxxx");
  if (http.GET() == 200) {
    WiFiClient* s = http.getStreamPtr();
    s->readBytes((uint8_t*)frame, sizeof frame);
    tft.setSwapBytes(true);
    tft.pushImage(0, 0, 320, 240, frame);
  }
  http.end();
  delay(2000);
}
```

Voor apparaten met weinig geheugen: kies een kleinere afmeting (`w=160&h=120`) of geef de stroom regel voor regel aan het display door.
