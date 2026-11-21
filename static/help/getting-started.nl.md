# Aan de slag met OpenCue

OpenCue is een lichtbesturingsconsole voor je pc. Deze handleiding brengt je in ongeveer tien minuten van het installatieprogramma naar je eerste lichtcue – zonder aangesloten lampen, want de eerste stappen werken met de ingebouwde demoshow.

Alle handleidingen zitten ook in het programma, zelfs offline: **Help → Handleidingen** (of **F1**) opent ze met een zoekfunctie (`Ctrl+F` binnenin).

---

## 1. Wat je nodig hebt

- Een pc met **Windows 10 of 11** (64-bit). De **Microsoft Edge WebView2 Runtime** toont het venster van OpenCue; die hoort bij de huidige Windows, en het installatieprogramma installeert hem als hij ontbreekt (daarvoor is eenmalig internet nodig).
- Voor echte lampen: een DMX-verbinding – via het netwerk (**Art-Net** of **sACN**) of een **USB-DMX-interface** (Enttec DMX USB Pro en compatibele). Zonder hardware kun je toch alles programmeren en bekijken in de **3D-simulatie**.
- Geen account, geen licentiesleutel, geen internetverbinding tijdens het werken.

---

## 2. Installeren

1. Download `OpenCue-Setup-v<versie>.exe` van de Releases-pagina van het project en start hem.
2. De setup begint met een welkomstpagina waar je de **taal** kiest (Engels of Duits; dat is ook de taal van OpenCue zelf – andere talen kies je later in het menu *Taal*).
3. Klik je erdoorheen: **Licentie** (de GNU GPL, om te lezen), **Programmamap**, **Gegevensmap**, **Snelkoppelingen** (Startmenu, bureaublad), het overzicht, **Installeren**.
4. Rond af en start OpenCue.

De **gegevensmap** is waar je shows, lay-outs, projectoren en instellingen staan. De standaardlocatie (`%LOCALAPPDATA%\OpenCue`) is voor de meeste mensen prima; je kunt in de setup een andere kiezen en die later in OpenCue wijzigen onder *Instellingen → Opslag*.

Is OpenCue al geïnstalleerd, dan herkent de setup dat en biedt *Bijwerken*, *Opnieuw installeren* of *Verwijderen* aan – je gegevens blijven altijd staan. OpenCue controleert bij het starten ook op nieuwe versies (uit te schakelen in *Instellingen → Algemeen*) en biedt aan ze te installeren; *Help → Controleren op updates…* doet het op verzoek.

OpenCue vind je via de Windows-zoekfunctie (Windows-toets en typ « OpenCue »).

---

## 3. De eerste start

Bij een verse installatie opent OpenCue een kant-en-klare **demoshow** met de naam **Default_1**:

- vijf **Generic Dimmers** (“Dimmer 1” … “Dimmer 5”) in universum 1 op kanaal 1 tot 5,
- een cuelijst “Default” met twee cues (“Cue 1” en “Cue 2”, elk één seconde fade),
- een **lay-out** met de panelen die je als eerste nodig hebt: cuelijst, projectorlijst, projectorbediening, executor, opdrachtregel, opdrachtknoppen en numpad.

Bij de allereerste start opent een korte **welkomstdialoog**: taal, en dan – alleen als je wilt – het netwerk (Art-Net, toegang op afstand met je eigen wachtwoord, OSC). Hij kan niet worden gesloten, je klikt erdoorheen (of drukt op *Overslaan* op de eerste pagina). Er wordt niets ingeschakeld zonder jouw akkoord; schakel je iets in dat het netwerk gebruikt, dan kan Windows eenmalig vragen of OpenCue het mag gebruiken. Na een update toont **Help → Wat is er nieuw** de wijzigingen (opent één keer vanzelf).

In de 3D-simulatie bestaat nog geen podium – dat maak je aan als je het nodig hebt. De democbestanden zijn gewone bestanden: wijzig of verwijder ze naar believen.

---

## 4. De interface in een minuut

### Menu's (linksboven)

| Menu | Inhoud |
|---|---|
| **Bestand** | Nieuw / Openen / Opslaan / Opslaan als (showbestanden), Afmelden (alleen apparaten op afstand), Afsluiten |
| **Bewerken** | **Panelen bewerken** (bewerkmodus), Ongedaan maken / Opnieuw uitvoeren, **Paneel toevoegen…**, Knop / Fader toevoegen, **Lay-outs beheren…** |
| **Bibliotheek** | **Projectorbibliotheek…**, 3D-podia, en het bestandsbeheer toont *Shows*, *Lay-outs*, *3D-podia*, *Effecten* |
| **Weergave** | Volledig scherm, GUI-schaal, Lay-outs |
| **Taal** | English / Deutsch / Français / Nederlands / Italiano / Español |
| **Help** | Toetsenbordsnelkoppelingen, GitHub-repository, Controleren op updates…, Over OpenCue |

### Werkbalk (boven)

De werkbalk toont de huidige **lay-out** en het **podium**, de **showbestandsnaam** (klik erop om het bestandsbeheer te openen), een pulserende **Blackout**-knop (gloeilamp), de **timecode**, een DMX-indicator, het aantal verbonden **apparaten op afstand** en de knop **Instellingen**. Beweeg je de muis over een onderdeel, dan licht het op en een **tooltip** zegt wat het is. Wat er in de balk staat bepaal je zelf onder *Instellingen → Werkbalk en internet* (elk onderdeel apart; alleen voor dit apparaat; het tandwiel is altijd zichtbaar).

**Operatormodus in gewone woorden** (*Weergave → Operatormodus ...*): je geeft de console aan iemand die alleen mag **bedienen** – faders schuiven, knoppen indrukken, cues starten – maar niets mag wijzigen. In operatormodus zijn menu's, instellingen en ombouwen vergrendeld, en is **spraakbesturing uit** (de microfoon blijft dicht). Eruit komt alleen met het **wachtwoord** (hangslot rechtsonder of `Ctrl+L`). Daarvoor is het wachtwoord uit *Instellingen → Beveiliging* nodig. **Scherm vergrendelen** is iets anders (*Bedieningen → Scherm vergrendelen*, `Ctrl+L`): het verduistert alles tot het wachtwoord is ingevoerd – er is dan niets meer te bedienen.

### Panelen

Al het andere zijn **panelen** die je vrij plaatst. De belangrijkste:

| Paneel | Doel |
|---|---|
| **Projectorlijst** | De patch: projectoren toevoegen, bewerken en verwijderen |
| **Projectorbediening** | Dimmer, positie, kleur, bundel, focus en DMX direct voor de geselecteerde projectoren; ook het tegelraster om te selecteren |
| **Cuelijst** | De cues van een lijst: opslaan, bijwerken, bewerken, verwijderen, afspelen |
| **Executor** | Afspelen met Go / Pause / Back / Stop en een mixfader |
| **Opdrachtregel**, **Opdracht-numpad**, **Opdrachtknoppen** | Typen en aanraakinvoer voor opdrachten |
| **Variabelen/effecten** | Herbruikbare kleuren, posities, bundels en effecten |
| **Effectenstudio** | Eigen effecten schrijven |
| **DMX-monitor** | De verzonden waarden zien |
| **3D-simulatie** | Je podium en lampen live zien |
| **Timecode**, **Tijdlijn-editor**, **Video/audiospeler**, **Livestream/camera** | Tijd en media (handleiding *Tijdlijn-editor en LTC*) |
| **Audio** | Live muziekanalyse (spectrum, beat, tempo): lampen en cues kunnen op muziek reageren |
| **Eenvoudige bediening** | Een eenvoudig bedieningsvlak om uit te lenen: lampen kiezen per tegel, **joystick**, helderheid, kleurveld, zoom, gobo's – zie *Toegang op afstand → Operatormodus* |
| **Knop**, **Fader**, **Schakelaar** | Eigen knoppen, faders en aan/uit-schakelaars die opdrachten uitvoeren (of ze in de opdrachtregel schrijven) |

Panelen voeg je toe met **Bewerken → Paneel toevoegen…**.

---

## 5. Je eerste cue

Je kunt dit volgen met de demoshow.

### Stap 1 – Selecteren

Klik op projectoren op het tabblad **Projectoren** van het paneel Projectorbediening (of in de projectorlijst) – of typ in de opdrachtregel:

```
Fixture 1 Thru 3
```

### Stap 2 – Een look maken

Gebruik de **Dimmer**-fader – of typ:

```
At 80
```

Kies een kleur als je projectoren die hebben (`Color Red`). Gewijzigde projectoren krijgen een rode markering: ze zitten nu in de **programmer**.

Bij moving heads heeft **Positie** drie weergaven: **Grof** (faders voor pan en tilt), **Fijn** (één veegstrook per as: veeg omhoog of omlaag, de markeringen volgen je vinger – één stap van het fijne kanaal per 4 pixels) en **Joystick**. De joystick is een ronde knop met twee assen, **relatief**: hoe verder je duwt, hoe sneller de projector beweegt; de binnenste cirkel is heel nauwkeurig, de buitenkant snel. Laat je los, dan springt de knop terug naar het midden en blijft de projector waar hij is. Hij wijzigt de grove en de fijne waarde, en meerdere geselecteerde projectoren bewegen met hetzelfde bedrag (hun verschillen blijven). Muis en aanraking werken allebei.

### Stap 3 – Een cue opslaan

Klik op **Cue opslaan** in het paneel Cuelijst. Een dialoog vraagt om de **positie** (aan het einde, na een cue of vrij), het **cuenummer** en een optionele **naam**. Klik op **Opslaan**. Of typ:

```
Store Cue 3 "Warm look"
```

Bestaat het nummer al, dan kies je **Samenvoegen** (alleen de gewijzigde kanalen gaan erin) of **Overschrijven**.

### Stap 4 – Afspelen

Druk op **Go** in het paneel Cuelijst of Executor – of typ `Go`. De look komt in over de fadetijd van de cue. `Go Cue 3` springt direct naar een cue; **Back** gaat een cue terug; **Pause** en **Stop** bedienen een lopende fade.

Gebruik de **Executor-fader** om te mixen tussen je handmatige waarden (0 %) en de cue (100 %). Voor een grote show voeg je **meerdere Executor-panelen** toe, elk gekoppeld aan een eigen cuelijst (paneelinstellingen → lijst): elk heeft zijn eigen fader en Go / Pause / Back / Stop – samen met de grandmaster (*Master*) werken ze als submasters.

### Stap 5 – Opslaan

Druk op `Ctrl+S`. Dit slaat het **showbestand** en je **lay-out** op. Zonder opslaan leven wijzigingen alleen in het geheugen; OpenCue vraagt voor het afsluit.

---

## 6. Echte lampen aansluiten

1. Open **Instellingen → DMX-uitgang**.
2. Voor **Art-Net**: het staat bij de eerste start **uit** (het zendt in het netwerk) – schakel het in. **Apparaten automatisch zoeken** staat standaard aan: OpenCue zoekt Art-Net-apparaten in het netwerk (om de paar seconden) en zendt direct naar elk ervan, dus een node die je aansluit werkt gewoon. **Netwerk scannen** toont wat het vond (naam, adres, universa); **Gebruiken** maakt van een apparaat een vast doel. Schakel de automatische modus uit om zelf een vast **doel-IP** in te typen (bijvoorbeeld het Art-Net-broadcastadres) en zo nodig het **bind-IP** (welke netwerkkaart te gebruiken).
3. Voor **sACN (E1.31)**: schakel het in. Ook dit staat standaard uit, zodat Windows bij de eerste start geen firewallvraag toont.
4. Voor **USB-DMX** (Enttec DMX USB Pro of compatibel): schakel het in. De **COM-poort** blijft op **Automatisch (aanbevolen)**: OpenCue herkent de adapter zelf als je hem aansluit, verbindt, en verbindt opnieuw nadat je hem loskoppelt en weer aansluit (ook op een andere USB-poort). Kies het **universum**; kies alleen met de hand een COM-poort als je meerdere adapters hebt.
5. Start een interface niet, gebruik dan **DMX-interfaces opnieuw initialiseren** – geen herstart nodig.

**Patch** daarna je projectoren (handleiding *Projectoren en patchen*): universum en startkanaal moeten overeenkomen met het adres dat op elk apparaat is ingesteld.

Het paneel **DMX-monitor** toont precies wat wordt verzonden. De knop **Blackout** zet alle helderheid direct op 0; nogmaals klikken brengt de look terug.

---

## 7. De interface naar je hand zetten

- **Bewerkmodus** (**Bewerken → Panelen bewerken**, `Ctrl+E`): panelen verplaatsen en vergroten of verkleinen (heel klein kan, de inhoud scrolt dan), hun eigenschappen en kleuren wijzigen, kopiëren en plakken. **Rechtsklikken op de lege werkruimte** voegt een paneel, knop, schakelaar of fader toe op de plek van de klik. Het vinkje **Bewerken → Hulplijnen** zet de uitlijnhulplijnen tijdens het verplaatsen aan of uit (houd `Alt` ingedrukt: kortstondig uit).
- **Lay-outs** zijn bestanden. Bouw er meerdere (bijvoorbeeld een kleine om te programmeren en een grote om af te spelen) en wissel met `Ctrl+1` … `Ctrl+9` of **Weergave → Lay-outs**. Opslaan met `Ctrl+S` of in het bestandsbeheer.
- **Thema's** (kleurprofielen): *Instellingen → Weergave* – donker, licht of je eigen.
- **GUI-schaal** (`Ctrl +` / `Ctrl -`): maakt alles groter voor aanraakschermen; wordt per apparaat bewaard.
- **Taal:** menu *Taal* (English, Deutsch, Français, Nederlands, Italiano, Español) of `Ctrl+Shift+L`. De handleidingen zijn beschikbaar in alle zes de talen.

### Instellingen in één oogopslag

Het tandwiel (**Instellingen**) opent een dialoog met links categorieën, gegroepeerd per taak. Belangrijke categorieën beginnen met een **grote aan/uit-schakelaar**: staat die uit, dan is alles eronder gedimd en vergrendeld. Niets wordt toegepast voordat je op **Opslaan** klikt (de dialoog blijft open); **Sluiten** vraagt het bij niet-opgeslagen wijzigingen. Het veld **Instellingen zoeken ...** vindt ook instellingen in categorieën die je nooit hebt geopend en toont de treffers over **alle categorieën** (*instelling - categorie / sectie*); een klik springt naar de rij. De kleine **(i)** achter een instelling toont de uitleg; de **(i)-knop naast het zoekveld** toont of verbergt alle uitleg (per apparaat onthouden).

**Instellingen veiligstellen:** onderaan *Algemeen* slaat **Instellingen exporteren** alle instellingen op als bestand (`opencue-settings.json`), **Instellingen importeren ...** leest er een terug. Geïmporteerde waarden verschijnen als **wijzigingen** (gemarkeerd en geteld) – alleen **Opslaan** past ze toe, **Sluiten** verwerpt ze. Niet inbegrepen zijn wachtwoorden en toegangssleutels, apparaat- of computerspecifieke waarden (schaal, gegevensmap, microfoons, MIDI-apparaten) en de toetsenbord- en MIDI-toewijzingen – die hebben hun eigen export.

| Groep | Categorie | Waarvoor |
|---|---|---|
| Programma | **Algemeen** | De basis: taal, GUI-schaal, lay-out wisselen door vegen, starten met Windows, updates, showback-ups, gegevensmap, instellingen veiligstellen |
| Programma | **Weergave** | Kleuren, thema's, standaardwaarden voor nieuwe panelen |
| Uitgang | **DMX-uitgang** | Art-Net, sACN, USB-DMX – elk met een eigen schakelaar, **alles staat bij de eerste start uit** |
| Netwerk | **Toegang op afstand** | Tablet / telefoon als afstandsbediening: hoofdschakelaar, HTTP / HTTPS, wachtwoord, adressen en QR-codes, netwerknaam `opencue.local` |
| Netwerk | **REST API** | Andere programma's besturen OpenCue: schakelaar, *Bereikbaar vanaf* (alleen deze computer / het netwerk), tokens |
| Bedieningen | **Toetsenbord** | De sneltoetsen bekijken, **eigen toetstoewijzing** (handleiding *Toetsenbordsnelkoppelingen*) |
| Bedieningen | **MIDI** | MIDI gebruiken, apparaten en uitgang kiezen, timecode / tempo uit MIDI, **MIDI-toewijzing** (handleiding *MIDI*) |
| Spraak en audio | **Triggerwoord** | Spraakbesturing met een eigen microfoon: triggerwoord + Engelse opdracht, bijv. “OpenCue, blackout on” (handleiding *Spraakopdrachten*); aan/uit met het microfoonsymbool rechtsboven |
| Spraak en audio | **Dictatie** | Microfoon en spraakmodel om te dicteren in de AI-chat |
| Assistent | **AI-assistent** | Hoofdschakelaar, verbinding met Ollama, gedrag, rechten |
| Geavanceerd | **Meer opties** | **Snelschakelaars** (spraakbesturing, MIDI, blackout, ongedaan maken inclusief Go – ze werken meteen, ook als hun knop in de werkbalk is verborgen), **Scherm wakker houden** (computer en tablets; op de iPad alleen op een beveiligde pagina, https), wat rechtsboven in de balk staat (elk onderdeel apart, per apparaat) en de **internetverbinding** (knop *Verbinding testen*) |
| Geavanceerd | **Standaardwaarden** | Standaarden voor nieuwe cues, basisstaat na *Clear Clear*, beginwaarden en **Verwijderen**: een bevestiging voor het verwijderen per categorie (cues, projectoren, bibliotheek, bestanden, overig) – standaard aan |
| Geavanceerd | **Ingangen & uitgangen** | Alleen weergave: elke verbinding, waarvoor ze dient en **hoe ver ze reikt** (*alleen deze pc*, *lokaal netwerk*, *internet*), met een link naar de bijbehorende instelling |

**Bij de eerste start verlaat niets de computer:** toegang op afstand, Art-Net, sACN en de REST API naar buiten zijn uit. Alleen de updatecontrole staat aan (uit te schakelen); die heeft internet nodig. Werkt internet in de browser maar niet in OpenCue (firewall, antivirus, bedrijfsnetwerk), dan toont *Algemeen → Internetverbinding → Verbinding testen* **wat** in de weg zit.

---

## 8. Wat je daarna kunt verkennen

| Onderwerp | Waar |
|---|---|
| Projectoren, GDTF-bibliotheek, patchen, groepen | *Projectoren en patchen* |
| Alle getypte opdrachten | *Opdrachtenreferentie* |
| Eigen effecten met een kleine scripttaal | *Effectenstudio* |
| Tablet en telefoon als afstandsbediening | *Toegang op afstand* |
| Elke sneltoets en elk gebaar | *Toetsenbordsnelkoppelingen* (ook **Help → Toetsenbordsnelkoppelingen**) |
| Podium in 3D, moving heads op een punt richten | Paneel **3D-simulatie** (voeg het toe via *Paneel toevoegen*; modi Weergave / Bouwen / Projectoren) |
| Eigen 3D-modellen (STL of OBJ) op het podium | 3D-simulatie → **Bouwen** → **3D-model …** (importeren of uit de bibliotheek kiezen; de bestandseenheid mm/cm/m/inch bepaalt de oorspronkelijke grootte). **Meerdere bestanden tegelijk importeren** (selecteer ze in het bestandsdialoogvenster of sleep ze vanuit Verkenner op het podium in de modus *Bouwen*): ze worden naast elkaar rond het midden van het beeld geplaatst en samen geselecteerd. Beheerd in het bestandsbeheer onder **3D-modellen** |
| Een paneel kort gebruiken zonder het in de lay-out te zetten | **Weergave → Paneel als venster openen**; opdrachtregel met numpad en toetsen: **Ctrl+F** (opdrachtconsole) |
| Cues die op een tijdstip starten | Paneel **Timecode** en cuetrigger *Timecode* |
| Lampen en cues die op muziek reageren | Paneel **Audio**, effecten met het label *Audio*, cuetrigger *Audio* (handleiding *Audio*) |
| Cues die wachten op een toets, pad of fader van een MIDI-apparaat | cuetrigger *MIDI* (handleiding *MIDI*, sectie 5c) |
| OpenCue vanuit andere programma's besturen | **REST API** (Instellingen → API; handleiding *REST API*) |
| Bestanden: shows, lay-outs, podia, 3D-modellen, effecten | **Bibliotheek → Shows… / Lay-outs… / 3D-podia… / Effecten…** (het bestandsbeheer, met import en export als ZIP; het exportpakket van een show kan ook de 3D-modellen van zijn podium bevatten) |

---

## 9. Waar je gegevens staan en hoe je ze back-upt

Je gegevens zijn gewone bestanden in de gegevensmap (standaard `%LOCALAPPDATA%\OpenCue`):

| Map | Inhoud |
|---|---|
| `showfiles` | Shows (projectoren, groepen, cues, presets, effecten) |
| `layouts` | Paneel-lay-outs |
| `themes` | Kleurprofielen |
| `fixtures` | GDTF-projectorbestanden |
| `effects` | Effectscripts (`.fx`) |
| `stages` | 3D-podia |
| `media` | Video's en audio van je shows |
| `config` | Instellingen (`app_config.json`, incl. de gekozen audiobron) en de API-tokens (`api_tokens.json`, alleen hashes) |

Voor een back-up kopieer je de map – of gebruik je de **export** van het bestandsbeheer (een show als ZIP inclusief de projectoren en effecten die hij nodig heeft), waarmee je een show ook naar een andere computer verplaatst.

Bij het verwijderen van OpenCue wordt gevraagd of deze gegevens ook moeten worden gewist; de standaardkeuze is **Nee**.
