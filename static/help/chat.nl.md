# Chat en notities

Het paneel **Chat en notities** is een kleine messenger en een notitieboek in één. U kunt **chatten met de andere apparaten** die met OpenCue verbonden zijn – de console, een iPad, een telefoon – en **notities en checklists** bijhouden voor de show: een takenlijst voor de deuren opengaan, een memo over de patch, het plan voor de toegift.

Alles wordt **op de server** opgeslagen (de computer waarop OpenCue draait). Elk apparaat ziet dezelfde chats en notities, en ze zijn morgen er nog.

---

## 1. Het paneel openen

*Bewerken → **Paneel toevoegen** → Podium en assistent → **Chat en notities*** (op een tablet op dezelfde manier). U kunt het paneel meerdere keren toevoegen en vrij indelen; alle tonen dezelfde chats en notities.

Links staat de **lijst** met chats en notities. De eerste knop in de kop verbergt de lijst; in een smal paneel schuift ze over de inhoud. De knop **+** maakt een **nieuwe chat** of een **nieuwe notitie**. Onder de lijst ziet u **uw naam**.

---

## 2. Chatten met andere apparaten

- Klik op een chat, typ, verstuur met **Enter** – **Shift + Enter** begint een nieuwe regel.
- Elk bericht toont wie het schreef en wanneer. Uw eigen berichten staan rechts.
- **Uw naam** (linksonder, klik om te wijzigen) kiest u per apparaat, bijvoorbeeld "Mengpaneel" of "iPad podium". Hij wordt op dat apparaat onthouden. Zolang u er geen kiest, heet de console "Console" en een tablet "Afstandsbediening" met een nummer.
- Nieuwe berichten verschijnen **direct** op elk apparaat. Is de chat op een apparaat niet geopend, dan verschijnt in de lijst een kleine **stip** en een korte melding.
- Zolang iemand typt, ziet u onder de berichten **“Naam is aan het typen”**. In een notitie staat **“Naam bewerkt de notitie”** zolang iemand anders erin werkt.
- Beweeg de muis over een bericht (op een touchscreen zijn de knoppen altijd zichtbaar) voor **Kopiëren** en **Verwijderen**. Verwijderen haalt het bericht van alle apparaten.
- Dubbelklik op de titel (of gebruik het potlood) om een chat te **hernoemen**; de prullenbak verwijdert de hele chat na bevestiging.
- **Vet**, *cursief*, `code`, ++onderstreept++ en links werken in berichten zoals in notities (paragraaf 4).

---

## 3. Notities en checklists

Een notitie is een tekst in **Markdown** – maar u hoeft Markdown niet te kennen: de **werkbalk** doet het voor u.

| Knop | Wat hij doet |
|---|---|
| **B**, *I*, U, S | vet, cursief, onderstreept, doorgehaald (ook **Ctrl+B / I / U**) |
| H | kop – nogmaals klikken voor een kleinere |
| lijstknoppen | lijst met opsommingstekens, genummerde lijst, **checklist**, citaat, code |

- **Bewerken / Weergave** (rechtsboven): *Weergave* toont de opgemaakte notitie. In de weergave kunt u **selectievakjes direct aanvinken** – ideaal voor een checklist die u tijdens de show afwerkt. Een dubbelklik in de weergave start het bewerken.
- **Enter** in een lijst zet haar voort met het volgende punt; **Enter** op een leeg punt beëindigt de lijst. **Tab / Shift + Tab** laten punten inspringen of terugkomen.
- In de lijst toont een notitie hoeveel taken klaar zijn, bijvoorbeeld "3/5".
- Notities worden **automatisch opgeslagen**, kort nadat u stopt met typen ("Opgeslagen" naast de knoppen).

---

## 4. Markdown in één oogopslag

| U typt | U krijgt |
|---|---|
| `**vet**` | **vet** |
| `*cursief*` | *cursief* |
| `++onderstreept++` | onderstreept |
| `~~doorgehaald~~` | doorgehaald |
| `# Kop`, `## Kleiner` | koppen |
| `- punt` | lijst met opsommingstekens (twee spaties inspringen voor een sublijst) |
| `1. punt` | genummerde lijst |
| `- [ ] taak` / `- [x] klaar` | selectievakje |
| `> citaat` | citaat |
| `` `code` `` | code |
| `---` | horizontale lijn |
| `[tekst](https://...)` | link |

---

## 5. Goed om te weten

- Chats en notities horen bij het **programma, niet bij een show**: ze blijven staan als u een andere show laadt.
- Het zijn bestanden in de gegevensmap (`notebook`); kopieer de map om ze naar een andere computer mee te nemen.
- **Als bestand opslaan:** de downloadknop in de kop slaat de geopende chat of notitie op als **Markdown-bestand** (`.md`): een notitie als haar tekst, een chat als gespreksverloop per dag.
- **Back-up en meenemen:** *Bestandsbeheer → Alles back-uppen* neemt alle chats en notities mee. Bij *Show exporteren...* kun je ze aan het pakket toevoegen (standaard uit, elk item apart). Bij het inlezen wordt niets overschreven – een afwijkend item komt als kopie erbij.
- **Vanuit programma's en apparaten:** scripts en hardware (bijvoorbeeld een ESP32) kunnen chats en notities via de REST-API lezen en schrijven – rechten *Chats en notities lezen* en *Chats en notities schrijven* (zie de handleiding REST-API, sectie 6).
- **Meerdere personen in dezelfde notitie:** de laatst opgeslagen versie geldt. Typen twee personen op hetzelfde moment, dan krijgt u een melding. Gebruik aparte notities of wissel af.
- Grenzen: 300 chats en notities, 4000 tekens per bericht, 100 000 per notitie; van een chat blijven de laatste 5000 berichten bewaard.
- Iedereen die met OpenCue verbonden is, kan alles lezen en schrijven – de chat is **niet privé**. Zet er geen wachtwoorden in.
- Er verlaat niets uw netwerk.
