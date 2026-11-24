# Projectoren en patchen

Een **projector** is een lamp die u bedient: een dimmer, een LED-par, een moving head. Om hem te bedienen moet OpenCue weten **wat voor apparaat het is** (zijn kanalen) en **waar hij luistert** (zijn DMX-adres). OpenCue beide vertellen heet **patchen**. Deze handleiding leidt u door de projectorbibliotheek, het patchen, groepen en de programmer.

---

## 1. Het idee in één minuut

- Een **projectortype** beschrijft een apparaatmodel: hoeveel DMX-kanalen het in welke modus gebruikt en wat elk kanaal doet (dimmer, pan, tilt, kleur, gobo …). OpenCue gebruikt hiervoor het standaardformaat **GDTF** – een klein bestand per apparaat dat de fabrikant publiceert.
- Een **projector** in uw show is één echt apparaat van zo'n type, met een **nummer** (FID), een **naam**, een **universum** en een **startkanaal** (het DMX-adres dat u op het apparaat instelt).
- De show slaat de projectoren op (type, modus, adres, naam, groep). De GDTF-bestanden zelf staan in de **projectorbibliotheek** op uw computer.
- Drie **ingebouwde** projectortypen zijn altijd beschikbaar, ook zonder GDTF-bestand: **Generic Dimmer** (1 kanaal), **Generic RGBW LED Par** (4 kanalen) en **Generic Moving Head Spot 16ch** (16 kanalen, met fijne pan/tilt). Perfect om dingen uit te proberen.

---

## 2. Projectortypen krijgen: de bibliotheek

Open **Bibliotheek → Projectorbibliotheek…**. Het grote venster heeft deze tabbladen:

| Tabblad | Wat het toont |
|---|---|
| **Geïnstalleerd** | Elk GDTF-bestand op deze computer als kaart: voorbeeldafbeelding, naam, fabrikant, type, modi, aantal kanalen, revisie en *In gebruik (N)* als de show het gebruikt. |
| **In deze show** | De typen die de geladen show gebruikt, met aantal ("4× in de show") en revisie. Ontbreekt het bestand van een type in de bibliotheek, dan toont het tabblad *Ingebouwde vervanging* of *Bestand ontbreekt*. Alleen bekijken. |
| **Online (GDTF Share)** | Zoek in de officiële GDTF-database (zie hieronder). |

Op het tabblad *Geïnstalleerd* kunt u **zoeken** op naam of fabrikant en filteren op **type** (moving head, LED-bar, PAR / wash, dimmer, strobe / blinder, effect / rook, overig – afgeleid van de echte kanalen) en op **fabrikant**. Elk tabblad houdt zijn eigen filters.

### Een GDTF-bestand importeren dat u al hebt

Klik op **GDTF-bestand importeren…** of **sleep het bestand** gewoon in het venster. Het bestand moet een geldig GDTF-bestand zijn (maximaal 30 MB). Bestanden worden gekopieerd naar de map `fixtures` in de gegevensmap van OpenCue (Instellingen → Opslag toont waar die is).

### Downloaden van GDTF Share

GDTF Share (gdtf-share.com) is de officiële, gratis verzameling GDTF-bestanden van fabrikanten en gebruikers.

1. Open het tabblad **Online (GDTF Share)**.
2. **Meld u aan** met uw GDTF Share-account. Om te downloaden is een gratis account nodig; in het venster staat een link *Gratis account aanmaken*. Uw wachtwoord wordt alleen voor deze sessie in het geheugen bewaard – tenzij u *Aangemeld blijven* aanvinkt, waarmee het **versleuteld op deze computer** wordt opgeslagen.
3. Zoek, sorteer (naam, nieuwste, best beoordeeld), filter op **bestanden van fabrikanten** / beoordeling. Elke kaart toont of het bestand **door de fabrikant** of **door een gebruiker** is geüpload, hoeveel modi het heeft (met aantallen kanalen) en hoe groot het is.
4. Klik op **Details** om **een projector te bekijken voordat u hem installeert**: het bestand wordt alleen tijdelijk geladen (niet geïnstalleerd) en opent in dezelfde detailweergave als geïnstalleerde typen – met alle kanalen, wielen en het 3D-model. **Installeren** en **Terug naar zoeken** staan bovenaan. Of klik meteen op **Installeren**.
5. De kaart toont dan *Geïnstalleerd*. Verschijnt later een nieuwere revisie, dan wordt een knop **Bijwerken** aangeboden.

Dit is de enige plek waar OpenCue internet gebruikt voor projectoren; al het andere werkt offline. OpenCue levert geen GDTF-bestanden van GDTF Share mee, omdat hun voorwaarden herdistributie niet toestaan – u downloadt ze zelf.

### Details van een projector

Klik op een kaart om zijn **details** te openen:

- **Overzicht** – stamgegevens, optiek per bundel (bundeltype, lamp, vermogen, lichtstroom, kleurtemperatuur, bundel- en veldhoek), connectoren, emitters.
- **3D-voorbeeld** – de projector als 3D-model. Slepen om te draaien, wiel of twee vingers om te zoomen, met rechts slepen om te verplaatsen, dubbelklikken om te resetten. Knoppen *Schuin / Voor / Zij / Boven*, schakelaars voor de *lichtbundel* en een *raster*, en **Pan / Tilt-schuiven** om een moving head te bewegen. Zonder 3D-bestand in de GDTF tekent OpenCue de basisvormen (cilinder, beugel, kop …) met de opgegeven afmetingen.
- **DMX-kanalen** – de modusselector en een tabel van alle kanalen met functies en waardebereiken.
- **Gobo's en kleuren** – elk wiel met zijn slots: gobopatronen als afbeeldingen, kleurslots als kleurvlakken.

### Verwijderen en bijwerken

- **Verwijderen** (vraagt een tweede keer) haalt een type uit de bibliotheek – maar het wordt **geweigerd zolang de show het nog gebruikt**.
- **Bijwerken** installeert een nieuwere revisie. Gebruikt de show de oude, dan blijft de oude revisie geïnstalleerd.

---

## 3. Projectoren aan de show toevoegen (patchen)

Projectoren worden gemaakt in het paneel **Projectorlijst**.

1. Klik in het paneel **Projectorlijst** op **Projectoren toevoegen**.
2. **Projectortype** – kies er een met *Type selecteren...* (fabrikant → apparaat → modus, plus zoeken) of een van de ingebouwde generieke.
3. **Modus** – de DMX-modus van het apparaat (die bepaalt het aantal kanalen).
4. **Naam** (optioneel) – bijvoorbeeld "Kop"; leeg betekent de typenaam. Bij meerdere projectoren nummert OpenCue de namen.
5. **Aantal** – hoeveel identieke projectoren u toevoegt. Ze worden **achter elkaar** op opeenvolgende adressen geplaatst.
6. **Universum** en **Startkanaal** – het adres van de eerste. Dit moet overeenkomen met het adres dat op het apparaat is ingesteld (display of DIP-schakelaars).
7. Klik op **Projectoren toevoegen**.

Het venster waarschuwt u als de laatste projector voorbij kanaal **512** van een universum zou eindigen ("eindadres overschrijdt 512 … Verminder het aantal of het startadres"). Een universum bevat 512 kanalen; gebruik voor meer het volgende universum.

Elke projector krijgt een vaste **FID** (projectornummer) die de opdrachtregel gebruikt (`Fixture 1 Thru 5`).

### Veel projectoren tegelijk: een lijst uit CSV of Excel

Het venster *Projectoren toevoegen* heeft onderaan **Geavanceerd importeren...** (ook in het menu **Bibliotheek → Projectorlijst importeren**). Daarmee maakt u een hele opstelling uit een tabel:

1. **Bestand kiezen ...** – een `.csv`- of Excelbestand (`.xlsx`). De **eerste rij** bevat de kolomtitels. Alleen het **type** is nodig; *naam*, *modus*, *universum*, *adres*, *nummer* (FID) en *aantal* zijn optioneel. **De huidige patch downloaden als CSV** geeft u een sjabloon.
2. OpenCue **raadt de kolommen** (titels als *Name*, *Type*, *Device*, *Universe*, *Address*, *Count* ...); u kunt elke toewijzing wijzigen. Een adres mag ook `2.045` of `2/45` zijn (universum 2, adres 45). Ontbreekt het adres, dan gaat het verder achter het vorige apparaat van hetzelfde universum.
3. De **voorvertoning** toont elke rij – rood met de reden als er iets niet klopt (type onbekend of dubbelzinnig, modus onbekend, past niet in het universum, nummer al gebruikt). **Type wanneer de cel leeg is** en **Universum wanneer ontbrekend** vullen gaten op.
4. **Importeren** maakt de projectoren aan. Bij problemen vinkt u eerst **Rijen met problemen overslaan** aan. Daarvoor wordt niets aangemaakt.

### De projectorlijst en het tabblad Projectoren

Twee plekken tonen uw projectoren:

- Het paneel **Projectorlijst** is de patchtabel: één rij per projector met FID, naam, type, universum, adres en aantal kanalen, plus de knop **Projectoren toevoegen**.
- Het tabblad **Projectoren** van het paneel **Projectorbediening** toont dezelfde projectoren als raster van tegels (zoals op een lichtconsole) voor snel selecteren.

| Actie | Hoe |
|---|---|
| Selecteren | Op een rij of tegel klikken / tikken |
| Meerdere selecteren | In het tegelraster een **lasso** over de tegels slepen (muis en aanraking) |
| Eén projector bewerken | Rechtsklik / lang drukken → **Projector bewerken…** |
| Verwijderen | Selecteren, `Delete` drukken of het contextmenu gebruiken (vraagt om bevestiging) |

### Projector bewerken

Eén venster wijzigt alles: **Naam**, **Universum**, **Startkanaal**, **Groep** en een vrije **Sorteerindex**.

- De sorteerindex bepaalt waar de tegel verschijnt. Leeg betekent de FID; een getal (decimalen toegestaan, bijvoorbeeld 2,5) plaatst hem dienovereenkomstig.
- Een projector hoort bij hoogstens **één groep**.
- Met **meerdere projectoren geselecteerd** biedt het menu ook *N projectoren naar groep verplaatsen…*.

Het adres wijzigen verandert waarheen OpenCue de gegevens stuurt – doe dat dus als u een apparaat naar een ander adres verplaatst.

---

## 4. Groepen

Groepen zijn puur organisatorisch: meerdere projectoren met één klik of opdracht sorteren en selecteren. Ze worden met de show opgeslagen.

- **Aanmaken:** in het tabblad **Projectoren** van het paneel Projectorbediening, rechtsklik / lang drukken op het lege gebied → *Nieuwe groep toevoegen…* en voer een naam in (namen zijn uniek, hoofdletterongevoelig).
- **Vullen:** het keuzemenu *Groep* in *Projector bewerken…*, of *N projectoren naar groep verplaatsen…* voor een selectie.
- **Selecteren:** klik op de groep, of gebruik de opdrachtregel: `Group Front`, `Group 1 Thru 4`.
- **Uit een selectie:** `Store Group "Front"` slaat de huidige selectie op als groep (zie *Opdrachtenreferentie*).

---

## 5. Projectoren bedienen: het paneel Projectorbediening

Selecteer projectoren en gebruik dan het paneel **Projectorbediening** (op consoles vaak "Programmer" genoemd). Een paneel kan alles tonen (een zijbalk met alle categorieën) of één categorie (*Paneeleigenschappen → Weergave*).

| Categorie | Bediening |
|---|---|
| **Projectoren** | Het tegelraster om te selecteren; schakel **Lijst / Layout** (zie hieronder) |
| **Dimmer** | Fader en snelknoppen |
| **Positie** | Schakel **Grof / Fijn**. *Grof*: pan/tilt-faders, **Midden / Thuispositie / Spiegelen**, getalvelden in graden. *Fijn*: de fijne kanalen (16 bit) als getalvelden; veeg een getalveld omhoog of omlaag om het fijn te wijzigen. Projectoren zonder fijne kanalen werken als 8 bit. |
| **Kleur** | **Fader** (HSV, CMY of RGB) of **Kleurkiezer** (kleurenwiel) |
| **Bundel** | Subpagina's **Shutter/stroboscoop** (open, dicht, langzaam, snel, strobe, puls …), **Gobo** (met miniaturen van het wiel), **Prisma** |
| **Focus** | Focus en zoom |
| **DMX direct** | Elk kanaal van de modus als eigen fader (op kanaalnummer, 0–255) |

Elk kanaal dat het GDTF-bestand beschrijft krijgt een bediening, zodat u ook ongebruikelijke functies bereikt (frost, iris, kleurenwielen, snelheden).

**Op een punt richten (3D):** staan de projectoren in de **3D-simulatie**, dan biedt het positiepaneel *Punt instellen in 3D-simulatie*: tik op een doel in de 3D-weergave en de geselecteerde moving heads richten erop. In het focuspaneel stellen *Automatische focus (3D)* en *Automatische zoom (3D)…* focus en zoom in naar de afstand tot dat punt.

### Wat de kleur van de bediening u vertelt

De bediening toont altijd wat op dit moment wordt uitgevoerd (dezelfde waarden als de DMX-monitor) – ook terwijl een cue of effect loopt. Een dun gekleurd streepje naast een projector of een categorietabblad toont wat **is gewijzigd ten opzichte van de actieve cue** – met de hand bediend of door een *Clear* die alles donker maakte. *Store Cue* slaat altijd de wijziging op ten opzichte van de cue die ervoor zou spelen (ook bij invoegen met `2.5`). Na het opslaan is de nieuwe cue de actieve en verdwijnen de streepjes. Bij meerdere cuelijsten telt de actieve cue van de laatst gebruikte lijst.

---

### Projectoren: lijst of layout

Bovenaan het tabblad **Projectoren** schakelt u tussen twee weergaven (zoals *Kleur* tussen Fader / Kiezer / Wiel):

- **Lijst:** de tegels geordend op groepen en nummers.
- **Layout:** elke projector is een **vierkante tegel** op een raster. Rangschik de projectoren zoals ze op het podium hangen en bereik ze sneller. De tegels tonen hetzelfde als in de lijst (nummer, helderheid, voorbeeld van kleur en bundel).

In de layout:

- **Selecteren** zoals in de lijst: klik of een **veeg** (lasso) over het lege gebied.
- **Onbeperkt gebied:** het gaat door in **elke richting** (ook naar links en omhoog; posities mogen negatief zijn). Verplaats de weergave met het muiswiel / schuifbalken / vegen, **sleep met de middelste knop**, of ga naar de rand terwijl u een tegel sleept. **Ctrl + muiswiel** zoomt.
- **Alles weergeven:** de knop rechtsboven zoomt en centreert zo dat **alle projectoren** in het midden staan.
- **Weergaven (gebieden):** *Weergave opslaan…* (rechtsklik) slaat het huidige midden en de zoom onder een naam op, bijvoorbeeld "Podium links". Bovenaan verschijnt een knop; een klik springt erheen, rechtsklik op de knop: overschrijven, hernoemen, verwijderen. Bij veel projectoren hoeft u niet alles tegelijk in beeld te houden.
- **Rechtsklik** (aanraking: lang drukken) op het vrije gebied of op een tegel opent het menu: *Bouwmodus*, *Alles weergeven*, *Weergave opslaan…*, *Raster* (hele, halve of kwarttegel), *Tegels mogen overlappen*, *Zoom resetten*, *Alle projectoren opnieuw rangschikken…*.
- **Bouwmodus:** slepen verplaatst een tegel; zijn er meerdere geselecteerd, dan verplaatsen ze samen. Tegels klikken vast op het raster; zonder *Overlappen* bedekken ze elkaar nooit, met *Overlappen* kunt u ze in elkaar schuiven (de laatst verplaatste ligt bovenop) en dicht verspringen met het fijne raster (1/4). Het lege gebied selecteert nog steeds door te vegen. **Klaar** of **Esc** beëindigt de bouwmodus.
- **In de show opgeslagen:** de posities, de rasterresolutie, *Overlappen* en de opgeslagen weergaven. **Op uw apparaat** (niet in de show): de zoom, het laatst getoonde midden en de laatst gebruikte subweergave.

**Onthouden weergaven:** overal waar een paneel tussen weergaven wisselt, onthoudt uw apparaat de laatste en herstelt die de volgende keer: in Projectorbediening (Lijst / Layout, Fader / Kiezer / Wiel, Strobe / Gobo / Prisma, Grof / Fijn), in *Variabelen/effecten* (variabelen of effecten, typefilter, sortering), in de *Effectenstudio* (voorvertoning aan / uit), in de *3D-simulatie* (Weergave / Bouwen / Projectoren) en in de effectkiezer (categorie en tags zoals *Basis*).

## 6. Variabelen en effecten (presets)

Het paneel **Variabelen/effecten** bevat herbruikbare waarden: een kleur "Warm wit", een positie "Voor", een bundel "Breed". Een variabele is een **levende verwijzing**: pas hem toe op projectoren en ze volgen hem; wijzig de variabele later en alle projectoren die hem gebruiken veranderen mee – ook cues die hem gebruiken. Effecten zijn kleine programma's die waarden in de tijd veranderen; zie de handleiding *Effectenstudio*.

---

## 7. Projectoren en het showbestand

- Een showbestand slaat de projectoren **met** hun type, modus, adres en groep op, plus de cues, effecten, variabelen en presets.
- De GDTF-bestanden staan **niet** in de show – maar als u **een show exporteert** (bestandsbeheer → exporteren), worden de GDTF-bestanden en effectscripts die de show gebruikt in de ZIP gepakt, zodat u de show op een andere computer kunt openen zonder iets te installeren. Bij importeren wordt een lokaal bestand met dezelfde naam nooit vervangen.
- **Afdrukken / PDF** (menu Bestand): documentatie van de show voor technici – **patchlijst**, **DMX-kanaalkaart** (welke projector welke kanalen van elk universum bezet, overlappingen in rood), **groepen**, **plattegrond (bovenaanzicht)** van de projectoren (uit het 3D-podium, anders uit de layoutweergave) en **cuelijsten**. Het venster toont naast de keuzes een **voorvertoning** van de PDF (die volgt elke wijziging van de keuzes en het papierformaat; op kleine schermen vervalt de voorvertoning). Lange namen worden in de tabellen en in de plattegrond **afgebroken** (een zeer lange naam zonder spaties wordt gesplitst). In de plattegrond draagt elke projector zijn nummer, en een lijst onder de plattegrond vertelt welk nummer welke projector is; namen van podiumobjecten staan binnen hun vorm. *Opslaan als PDF* downloadt het bestand, *Openen om af te drukken* toont het in de PDF-viewer (druk daar af met Ctrl+P).
- **Showbestand `.ocshow`:** *Bestand → Show exporteren* schrijft een `.ocshow`-bestand (een ZIP met de show en zijn bestanden). Een **dubbelklik** opent het in OpenCue (het installatieprogramma stelt dit in; voor de uitgepakte versie gebruikt u *Instellingen → Algemeen → .ocshow-bestanden met OpenCue openen*). Draait OpenCue al, dan neemt het het bestand over en vraagt eerst wat er met niet-opgeslagen wijzigingen moet gebeuren. **Bestand → Recent openen** toont de laatste shows.
- **3D-podium als JSON:** schakel in het 3D-paneel (modus *Bouwen* of *Projectoren*) de zijbalk van **Hulpmiddelen** naar **JSON** (schakelaar onder de knop Opslaan; hij blijft bovenaan de zijbalk staan als u scrolt). De hulpmiddelen (lichamen toevoegen, lijst, eigenschappen) worden vervangen door de tekst van het podium (ruimte, objecten, projectorposities; meters, graden, Z omhoog; projectoren met hun nummer); podiumnaam, ongedaan maken en **Opslaan** blijven hetzelfde, **Hulpmiddelen** brengt de normale weergave terug. **De breedte van de zijbalk kan worden gewijzigd:** sleep zijn linkerrand (dubbelklik = standaardbreedte); de breedte wordt onthouden als aandeel van het paneel (hoogstens driekwart), zodat ze proportioneel blijft op volledig scherm. Wijzigingen worden gecontroleerd en **live toegepast** (een syntaxisfout noemt de regel en verandert niets); wat u in de 3D-weergave verplaatst, verschijnt in de tekst. *Opslaan* slaat het podium op, *JSON sluiten* brengt de zijbalk terug. Dezelfde tekst is als venster beschikbaar onder *Bibliotheek → 3D-podium bewerken als JSON* (met *Controleren* en *Toepassen*).
- **MVR-import (podium en projectoren):** *Bibliotheek → MVR-scène importeren…* leest een **.mvr**-bestand uit een podium- of lichtontwerpprogramma (Vectorworks, Capture, Depence …). Kies het bestand (of sleep het op het venster): OpenCue toont wat erin zit - podiumonderdelen, projectoren en hun typen - en u beslist: **3D-podium** *vervangen* (standaard; een eerder opgeslagen podiumbestand blijft ongemoeid op de schijf), *aanvullen* of *niet wijzigen*, en of de **projectoren worden gepatcht**. De projectoren krijgen type, modus, DMX-adres en nummer uit het bestand en staan met positie en draaiing in het 3D-podium (een al bezet nummer of een ontbrekend adres wordt vervangen door een vrij exemplaar - de opmerkingen vertellen het u). De GDTF-bestanden gaan naar de projectorbibliotheek (er wordt niets overschreven). De podiumonderdelen (vloer, truss, decor, schermen …) worden **3D-modellen** (binaire STL, onder *Bibliotheek → 3D-modellen…*) en podiumobjecten die u net als alle andere kunt verplaatsen, draaien en schalen; een onderdeel dat vaak voorkomt (een symbool in het bestand) deelt één model. Een scène met meer dan 200 onderdelen wordt per laag samengevoegd zodat ze op een podium past. Het nieuwe podium is pas opgeslagen als u de show opslaat. De kleuren van de materialen blijven behouden (per vlak) en gespiegelde onderdelen blijven gespiegeld. Een voortgangsbalk toont de import - grote ledprojectorbestanden hebben elk enkele seconden nodig, één keer per type, en worden daarna onthouden. Het venster opent ook via de kleine knop *MVR-scène importeren…* in het 3D-paneel (modus *Bouwen* en *Projectoren*). Niet overgenomen: richtpunten en beeldtexturen.
- Gebruikt een show een projectortype waarvan het bestand ontbreekt, dan gebruikt OpenCue een ingebouwde vervanging zodat de show toch werkt; het tabblad *In deze show* toont dit als *Ingebouwde vervanging* of *Bestand ontbreekt*.

---

## 8. Snelle tips

- **Begin met een generiek type:** voeg een paar *Generic Dimmer*-projectoren toe om de programmer, cues en de opdrachtregel te leren voordat u echte GDTF-bestanden zoekt.
- **Laat adressen overeenkomen:** het startkanaal in OpenCue moet gelijk zijn aan het adres op het apparaat. Moving heads hebben meestal een kanaalblok nodig (bijvoorbeeld 16 kanalen), dus de volgende projector begint 16 kanalen later – OpenCue berekent dat voor u als u een aantal toevoegt.
- **Meerdere modi:** veel apparaten bieden meerdere modi (bijvoorbeeld 8 bit en 16 bit). Kies de modus waarop het apparaat echt is ingesteld.
- **Ontbreekt een apparaat?** Zoek op GDTF Share op fabrikant; staat het model er niet, begin dan met het dichtstbijzijnde of gebruik *Generic* en maak uw eigen cues.
