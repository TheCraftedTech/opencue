# Startopties en servermodus

OpenCue kan met opties worden gestart – in een snelkoppeling, een batchbestand, de Taakplanner of een terminal. Deze handleiding somt ze op, legt de **servermodus zonder venster** (`--no-ui`) uit, **Starten met Windows**, wat **beheerdersrechten** wel en niet veranderen en de regel voor de **Windows Firewall**.

---

## 1. De opties

Zet ze achter het programma: `OpenCue.exe --no-ui --open-browser` (vanuit de broncode: `python main.py ...`). In een snelkoppeling: *Eigenschappen → Doel*, na de afsluitende aanhalingstekens van het pad.

| Optie | Wat het doet |
|---|---|
| `--no-ui` of `--server-only` | Starten **zonder programmavenster** (paragraaf 2). Impliceert `--no-splash`. |
| `--open-browser` | Met `--no-ui`: opent bij het starten de standaardbrowser op de console. |
| `SHOWFILE` of `--show BESTAND` | Laadt deze show in plaats van de laatste. Een showbestand als eerste parameter werkt als een start met dubbelklik; dit geldt ook voor een `.ocshow`-bestand (exportpakket). Draait OpenCue al, dan neemt het draaiende programma het bestand over (en vraagt eerst wat er met niet-opgeslagen wijzigingen moet gebeuren). |
| `--new-show` | Start met een **lege show** in plaats van de laatste. Er wordt niets verwijderd; de "laatst gebruikte" show blijft zoals hij was. |
| `--port N` | Serverpoort **alleen voor deze keer** (1–65535). De opgeslagen instelling verandert niet. |
| `--remote` | Zet **netwerktoegang** aan (zoals in *Instellingen → Toegang op afstand*) – deze instelling wordt **opgeslagen**. |
| `--data-dir MAP` | Gebruikt een andere **gegevensmap** voor deze keer (draagbaar gebruik, tests). Gelijk aan de variabele `OPENCUE_DATA_DIR`. |
| `--fullscreen` | Start het programmavenster op volledig scherm. |
| `--priority normal`, `above` of `high` | Procesprioriteit; standaard `above` (boven normaal), zie paragraaf 5. |
| `--no-splash` | Geen opstartscherm (ook: `OPENCUE_NO_SPLASH=1`). |
| `--version`, `--help` | Toont de versie of de lijst met opties. |

Het gebouwde programma heeft geen eigen console: `--help` en `--version` schrijven naar de console waaruit het is gestart (cmd, PowerShell).

---

## 2. Servermodus zonder venster (`--no-ui`)

OpenCue start zoals gewoonlijk – DMX-uitvoer, cues, effecten, MIDI, toegang op afstand, de REST-API – maar er opent **geen programmavenster**. U bedient het vanuit

- **een browser op deze computer:** `http://127.0.0.1:8000` (de poort uit *Instellingen → Toegang op afstand*, of `--port`) – precies dezelfde console als in het venster, of
- **een tablet of telefoon** via het netwerk (zet **Toegang op afstand** aan in de instellingen of start één keer met `--remote`).

Een **pictogram in het systeemvak** van de taakbalk laat zien dat OpenCue draait: **klik** erop om de console in uw browser te openen; **rechtsklik** voor het menu *OpenCue in de browser openen*, *Logmap openen* en *OpenCue afsluiten*. Heeft de show niet-opgeslagen wijzigingen, dan vraagt afsluiten één keer om bevestiging (er wordt in elk geval een reservekopie opgeslagen).

Het menu toont bovenaan de **naam van de show**, de waarschuwing **⚠ Niet-opgeslagen wijzigingen** als die er zijn (de tooltip van het pictogram ook) en de **adressen** waarop de console bereikbaar is (met toegang op afstand aan ook die in het netwerk) – een klik opent er een in de browser.

Andere manieren om af te sluiten: **Bestand → Afsluiten** in de browser, **Ctrl+C** als het vanuit een terminal is gestart, en afmelden of afsluiten van Windows (OpenCue probeert dan netjes af te sluiten, met de gebruikelijke reservekopie).

**OpenCue een tweede keer starten** terwijl de server draait, geeft geen foutmelding: het opent gewoon uw browser op de draaiende console.

Wat **niet kan werken** zonder het venster: dingen waarvoor het eigen programmavenster nodig is – bijvoorbeeld de bestandskiezer om een video- of audiobestand te *koppelen*, of de schakelaar voor volledig scherm van het venster. Al het andere is beschikbaar in de browser.

Tip: voor een podium-pc die alleen DMX uitvoert, zet u *OpenCue starten wanneer ik me aanmeld bij Windows* + *Starten zonder venster* aan (paragraaf 3).

---

## 3. Starten met Windows

**Instellingen → Algemeen → Gedrag:**

- **OpenCue starten wanneer ik me aanmeld bij Windows** – een vermelding voor **uw Windows-gebruiker** (geen beheerdersrechten nodig; verwijder haar door de optie uit te zetten).
- **Starten zonder venster (alleen server)** – start met `--no-ui`.

Dit is beschikbaar in het **geïnstalleerde programma**, niet bij starten vanuit de broncode. (Een geëxporteerde show met de extensie `.ocshow` opent daar altijd met een dubbelklik in OpenCue – daar is geen schakelaar voor.) De vermelding verwijst naar het programmabestand: verplaatst of herinstalleert u OpenCue elders, zet de optie dan uit en weer aan.

---

## 4. Beheerdersrechten en de firewall

**Draait OpenCue als beheerder?** Het logboek (`opencue.log`, eerste regels) en de details van een foutrapport vermelden *"Administrator: yes"* of *"no"*. Is dat zo, dan schrijft OpenCue ook een opmerking in het logboek.

**U hebt het niet nodig – en moet het niet gebruiken:** Windows blokkeert het **slepen van bestanden uit Verkenner** naar een programma dat als beheerder draait, en een webserver met beheerdersrechten is een groter doelwit. Beheerdersrechten helpen bij **één** ding: het maken van de **Windows Firewall-regel**.

**Firewallregel:** zonder die regel vraagt Windows het de eerste keer dat OpenCue het netwerk gebruikt; een onbeantwoorde of geweigerde vraag blokkeert tablets, sACN en de netwerknaam `opencue.local`. **Instellingen → Toegang op afstand → Windows Firewall → OpenCue toestaan in de firewall** maakt een regel voor precies dit programma, **inkomend, alleen in privé- en domeinnetwerken** (nooit in openbare). Windows vraagt **één keer** toestemming (beheerdersmelding) – alleen dit ene kleine commando wordt met verhoogde rechten gestart, OpenCue zelf blijft gewoon draaien. *De firewallregel verwijderen* verwijdert haar weer. De statusregel toont of de regel bestaat.

---

## 5. Prioriteit en nauwkeurige timing

Bij het starten zet OpenCue de **procesprioriteit** op *boven normaal* en de **timerresolutie op 1 ms** (Windows tikt normaal elke 15,6 ms). Beide houden de 40 Hz-lussen van cues, effecten en DMX soepel als de computer het druk heeft – geen beheerdersrechten nodig. `--priority high` verhoogt het verder (voor een pc die niets anders doet), `--priority normal` schakelt het uit.

---

## 6. Voorbeelden

- Server op een podium-pc, browser opent: `OpenCue.exe --no-ui --open-browser`
- Een show openen via *Openen met* in Verkenner: `OpenCue.exe "D:\Shows\Concert.json"`
- Leeg starten zonder de laatste show aan te raken: `OpenCue.exe --new-show`
- Testen op een andere poort met eigen gegevens: `OpenCue.exe --port 8080 --data-dir D:\OpenCueTest`
