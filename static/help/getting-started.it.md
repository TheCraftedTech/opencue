# Primi passi con OpenCue

OpenCue è una console di controllo luci per il tuo PC. Questa guida ti porta dall'installatore alla tua prima cue in circa dieci minuti – senza luci collegate, perché i primi passi usano lo show dimostrativo incluso.

Tutte le guide sono anche nel programma, persino offline: **Aiuto → Guide** (oppure **F1**) le apre con una ricerca (`Ctrl+F` all'interno).

---

## 1. Cosa ti serve

- Un PC con **Windows 10 o 11** (64 bit). Il **Microsoft Edge WebView2 Runtime** mostra la finestra di OpenCue; fa parte dei Windows attuali, e l'installatore lo configura se manca (serve Internet una volta).
- Per luci reali: un collegamento DMX – tramite rete (**Art-Net** o **sACN**) o un'**interfaccia USB DMX** (Enttec DMX USB Pro e compatibili). Senza hardware puoi comunque programmare tutto e guardarlo nella **simulazione 3D**.
- Nessun account, nessuna chiave di licenza, nessuna connessione Internet mentre lavori.

---

## 2. Installazione

1. Scarica `OpenCue-Setup-v<versione>.exe` dalla pagina delle release del progetto ed eseguilo.
2. L'installazione inizia con una pagina di benvenuto in cui scegli la **lingua** (inglese o tedesco; è anche la lingua di OpenCue stesso – altre lingue si scelgono poi nel menu *Lingua*).
3. Prosegui: **Licenza** (la GNU GPL, da leggere), **Cartella del programma**, **Cartella dei dati**, **Collegamenti** (menu Start, desktop), il riepilogo, **Installa**.
4. Concludi e avvia OpenCue.

La **cartella dei dati** è dove stanno i tuoi show, i layout, gli apparecchi e le impostazioni. Il percorso predefinito (`%LOCALAPPDATA%\OpenCue`) va bene per la maggior parte delle persone; puoi sceglierne un altro nell'installazione e cambiarlo in seguito in OpenCue in *Impostazioni → Archiviazione*.

Se OpenCue è già installato, l'installatore lo riconosce e offre *Aggiorna*, *Reinstalla* o *Disinstalla* – i tuoi dati restano sempre. OpenCue controlla anche all'avvio se ci sono nuove versioni (si può disattivare in *Impostazioni → Generale*) e propone di installarle; *Aiuto → Verifica aggiornamenti…* lo fa su richiesta. La finestra di aggiornamento mostra le note di rilascio; dopo un aggiornamento si apre una volta la finestra **Novità** con le novità di ogni versione saltata (anche in *Aiuto → Novità*).

OpenCue si trova con la ricerca di Windows (tasto Windows, poi scrivi “OpenCue”).

---

## 3. Il primo avvio

In una nuova installazione OpenCue apre uno **show dimostrativo** pronto, chiamato **Default_1**:

- cinque **Generic Dimmer** (“Dimmer 1” … “Dimmer 5”) nell'universo 1 sui canali da 1 a 5,
- una lista di cue “Default” con due cue (“Cue 1” e “Cue 2”, un secondo di dissolvenza ciascuna),
- un **layout** con i pannelli che servono per primi: lista cue, elenco apparecchi, controllo apparecchi, executor, riga di comando, pulsanti di comando e tastierino numerico.

Al primissimo avvio si apre una breve **finestra di benvenuto**: la lingua, poi – solo se vuoi – la rete (Art-Net, accesso remoto con una tua password, OSC). Non si può chiudere, la si scorre (o si preme *Salta* nella prima pagina). Niente viene attivato senza il tuo consenso; se attivi qualcosa che usa la rete, Windows può chiedere una volta se OpenCue può usarla. Dopo un aggiornamento **Aiuto → Novità** elenca le modifiche (si apre una volta da sola).

Nella simulazione 3D non esiste ancora nessun palco – lo crei quando ti serve. I file dimostrativi sono file normali: modificali o eliminali come vuoi.

---

## 4. L'interfaccia in un minuto

### Menu (in alto a sinistra)

| Menu | Contenuto |
|---|---|
| **File** | Nuovo / Apri / Salva / Salva con nome (file show), Esci dall'account (solo dispositivi remoti), Esci |
| **Modifica** | **Modifica pannelli** (modalità modifica), Annulla / Ripeti, **Aggiungi pannello…**, Aggiungi pulsante / fader, **Gestisci layout…** |
| **Libreria** | **Libreria apparecchi…**, palchi 3D, e il gestore file elenca *Show*, *Layout*, *Palchi 3D*, *Effetti* |
| **Visualizza** | Schermo intero, scala dell'interfaccia, layout |
| **Lingua** | English / Deutsch / Français / Nederlands / Italiano / Español |
| **Aiuto** | Scorciatoie da tastiera, repository GitHub, Novità, Verifica aggiornamenti…, Informazioni su OpenCue |

### Barra degli strumenti (in alto)

La barra mostra il **layout** e il **palco** attuali, il **nome del file show** (clicca per aprire il gestore file), un pulsante **Blackout** pulsante (lampadina), il **timecode**, un indicatore DMX, il numero di **dispositivi remoti** collegati e il pulsante **Impostazioni**. Passando il mouse su una voce, questa si illumina e un **suggerimento** dice cos'è. Cosa compare nella barra lo decidi tu in *Impostazioni → Barra e Internet* (ogni voce a sé; solo per questo dispositivo; l'ingranaggio è sempre visibile).

**Modalità operatore in parole semplici** (*Visualizza → Modalità operatore ...*): affidi la console a qualcuno che deve solo **usarla** – muovere fader, premere pulsanti, avviare cue – ma non modificare nulla. In modalità operatore menu, impostazioni e ricostruzione sono bloccati, e il **controllo vocale è spento** (il microfono resta chiuso). Se ne esce solo con la **password** (lucchetto in basso a destra o `Ctrl+L`). Serve la password di *Impostazioni → Sicurezza*. Il **blocco schermo** è un'altra cosa (*Controlli → Blocca schermo*, `Ctrl+L`): oscura tutto finché non si inserisce la password – non si può più usare nulla.

### Pannelli

Tutto il resto sono **pannelli** che disponi liberamente. I più importanti:

| Pannello | Scopo |
|---|---|
| **Elenco apparecchi** | Il patch: aggiungere, modificare ed eliminare apparecchi |
| **Controllo apparecchi** | Dimmer, posizione, colore, fascio, focus e DMX diretto per gli apparecchi selezionati; anche la griglia di tessere per selezionare |
| **Lista cue** | Le cue di una lista: salvare, aggiornare, modificare, eliminare, riprodurre |
| **Executor** | Riproduzione con Go / Pause / Back / Stop e un fader di mix |
| **Riga di comando**, **Tastierino numerico comandi**, **Pulsanti comando** | Digitazione e input touch per i comandi |
| **Variabili / Effetti** | Colori, posizioni, fasci ed effetti riutilizzabili |
| **Studio effetti** | Scrivere effetti propri |
| **Monitor DMX** | Vedere i valori inviati |
| **Simulazione 3D** | Vedere palco e luci dal vivo |
| **Timecode**, **Editor timeline**, **Lettore video/audio**, **Streaming live / telecamera** | Tempo e media (guida *Editor timeline e LTC*) |
| **Audio** | Analisi musicale dal vivo (spettro, beat, tempo): luci e cue possono reagire alla musica |
| **Controllo semplice** | Una superficie di controllo semplice da consegnare: scegliere le luci per tessera, **joystick**, luminosità, campo colore, zoom, gobo – vedi *Accesso remoto → Modalità operatore* |
| **Pulsante**, **Fader**, **Interruttore** | Pulsanti, fader e interruttori on/off propri che eseguono comandi (o li scrivono nella riga di comando) |

Aggiungi pannelli con **Modifica → Aggiungi pannello…**.

---

## 5. La tua prima cue

Puoi seguire questo con lo show dimostrativo.

### Passo 1 – Selezionare

Clicca sugli apparecchi nella scheda **Apparecchi** del pannello Controllo apparecchi (o nell'elenco apparecchi) – oppure scrivi nella riga di comando:

```
Fixture 1 Thru 3
```

### Passo 2 – Creare un look

Usa il fader **Dimmer** – oppure scrivi:

```
At 80
```

Scegli un colore se i tuoi apparecchi ne hanno uno (`Color Red`). Gli apparecchi modificati ricevono un segno rosso: ora sono nel **programmer**.

Per le teste mobili, **Posizione** ha tre viste: **Grossolana** (fader per pan e tilt), **Fine** (una striscia da scorrere per asse: scorri su o giù, i segni seguono il dito – un passo del canale fine ogni 4 pixel) e **Joystick**. Il joystick è una manopola rotonda a due assi, **relativa**: più la spingi, più veloce si muove l'apparecchio; il cerchio interno è molto preciso, l'esterno veloce. Quando lasci, la manopola torna al centro e l'apparecchio resta dov'è. Modifica il valore grossolano e quello fine, e più apparecchi selezionati si muovono della stessa quantità (le loro differenze restano). Funzionano mouse e touch.

### Passo 3 – Salvare una cue

Clicca su **Salva cue** nel pannello Lista cue. Una finestra chiede la **posizione** (alla fine, dopo una cue o libera), il **numero della cue** e un **nome** facoltativo. Clicca su **Salva**. Oppure scrivi:

```
Store Cue 3 "Warm look"
```

Se il numero esiste già, scegli **Unisci** (entrano solo i canali modificati) o **Sovrascrivi**.

### Passo 4 – Riprodurla

Premi **Go** nel pannello Lista cue o Executor – oppure scrivi `Go`. Il look entra in dissolvenza per il tempo di dissolvenza della cue. `Go Cue 3` salta direttamente a una cue; **Back** torna indietro di una cue; **Pause** e **Stop** controllano una dissolvenza in corso.

Usa il **fader dell'executor** per mixare tra i tuoi valori manuali (0 %) e la cue (100 %). Per uno show grande aggiungi **più pannelli Executor**, ciascuno legato a una propria lista cue (impostazioni del pannello → lista): ognuno ha il suo fader e i suoi Go / Pause / Back / Stop – insieme al grand master (*Master*) funzionano come submaster.

### Passo 5 – Salvare

Premi `Ctrl+S`. Questo salva il **file show** e il tuo **layout**. Senza salvare, le modifiche vivono solo in memoria; OpenCue chiede prima di chiudersi.

---

## 6. Collegare luci reali

1. Apri **Impostazioni → Uscita DMX**.
2. Per **Art-Net**: al primo avvio è **spento** (invia nella rete) – attivalo. **Trova dispositivi automaticamente** è attivo per impostazione predefinita: OpenCue cerca dispositivi Art-Net nella rete (ogni pochi secondi) e invia a ciascuno direttamente, quindi un nodo che colleghi funziona e basta. **Scansiona la rete** elenca ciò che ha trovato (nome, indirizzo, universi); **Usa** rende un dispositivo una destinazione fissa. Disattiva la modalità automatica per scrivere tu un **IP di destinazione** fisso (per esempio l'indirizzo broadcast Art-Net) e, se serve, l'**IP di binding** (quale scheda di rete usare).
3. Per **sACN (E1.31)**: attivalo. Anche questo è spento per impostazione predefinita, così Windows non mostra una domanda del firewall al primo avvio.
4. Per **USB DMX** (Enttec DMX USB Pro o compatibile): attivalo. La **porta COM** resta su **Automatica (consigliato)**: OpenCue riconosce da solo l'adattatore quando lo colleghi, si connette, e si riconnette dopo che lo scolleghi e ricolleghi (anche su un'altra porta USB). Scegli l'**universo**; scegli una porta COM a mano solo se hai più adattatori.
5. Se un'interfaccia non parte, usa **Reinizializza interfacce DMX** – non serve riavviare.

Poi fai il **patch** degli apparecchi (guida *Apparecchi e patch*): universo e canale iniziale devono corrispondere all'indirizzo impostato su ogni dispositivo.

Il pannello **Monitor DMX** mostra esattamente cosa viene inviato. Il pulsante **Blackout** porta subito tutta la luminosità a 0; cliccando di nuovo torna il look.

---

## 7. Personalizzare l'interfaccia

- **Modalità modifica** (**Modifica → Modifica pannelli**, `Ctrl+E`): spostare e ridimensionare i pannelli (anche molto piccoli, il contenuto allora scorre), cambiarne proprietà e colori, copiarli e incollarli. Un **clic destro sull'area di lavoro vuota** aggiunge un pannello, pulsante, interruttore o fader nel punto del clic. La spunta **Modifica → Guide** attiva o disattiva le guide di allineamento durante lo spostamento (tieni premuto `Alt`: spente per un attimo).
- I **layout** sono file. Creane diversi (per esempio uno piccolo per programmare e uno grande per la riproduzione) e passa dall'uno all'altro con `Ctrl+1` … `Ctrl+9` o **Visualizza → Layout**. Salva con `Ctrl+S` o nel gestore file. Crea un nuovo layout vuoto con **Modifica → Nuovo layout…**.
- **Temi** (profili di colore): *Impostazioni → Aspetto* – scuro, chiaro o il tuo.
- **Scala dell'interfaccia** (`Ctrl +` / `Ctrl -`): ingrandisce tutto per gli schermi touch; viene memorizzata per dispositivo.
- **Lingua:** menu *Lingua* (English, Deutsch, Français, Nederlands, Italiano, Español) o `Ctrl+Maiusc+L`. Le guide sono disponibili in tutte e sei le lingue.

### Le impostazioni a colpo d'occhio

L'ingranaggio (**Impostazioni**) apre una finestra con le categorie a sinistra, raggruppate per compito. Le categorie importanti iniziano con un **grande interruttore on/off**: quando è spento, tutto ciò che segue è attenuato e bloccato. Niente viene applicato prima di cliccare su **Salva** (la finestra resta aperta); **Chiudi** chiede conferma se ci sono modifiche non salvate. Il campo **Cerca nelle impostazioni ...** trova anche impostazioni in categorie che non hai mai aperto e mostra i risultati in **tutte le categorie** (*impostazione - categoria / sezione*); un clic salta alla riga. La piccola **(i)** dietro un'impostazione mostra la sua spiegazione; il **pulsante (i) accanto al campo di ricerca** mostra o nasconde tutte le spiegazioni (ricordato per dispositivo).

**Salvare le impostazioni:** in fondo a *Generale*, **Esporta impostazioni** salva tutte le impostazioni in un file (`opencue-settings.json`), **Importa impostazioni ...** ne rilegge uno. I valori importati compaiono come **modifiche** (evidenziate e contate) – solo **Salva** li applica, **Chiudi** li scarta. Non sono incluse password e chiavi di accesso, valori specifici del dispositivo o del computer (scala, cartella dei dati, microfoni, dispositivi MIDI) e le assegnazioni di tastiera e MIDI – hanno una propria esportazione.

| Gruppo | Categoria | A cosa serve |
|---|---|---|
| Programma | **Generale** | Le basi: lingua, scala dell'interfaccia, cambio layout con scorrimento, avvio con Windows, aggiornamenti, backup degli show, cartella dei dati, salvataggio impostazioni |
| Programma | **Aspetto** | Colori, temi, valori predefiniti per i nuovi pannelli |
| Uscita | **Uscita DMX** | Art-Net, sACN, USB DMX – ciascuno con il proprio interruttore, **tutto è spento al primo avvio** |
| Rete | **Accesso remoto** | Tablet / telefono come telecomando: interruttore principale, HTTP / HTTPS, password, indirizzi e codici QR, nome di rete `opencue.local` |
| Rete | **API REST** | Altri programmi controllano OpenCue: interruttore, *Raggiungibile da* (solo questo computer / la rete), token |
| Controlli | **Tastiera** | Vedere le scorciatoie, **assegnazione tasti personalizzata** (guida *Scorciatoie da tastiera*) |
| Controlli | **MIDI** | Usare il MIDI, scegliere dispositivi, uscita, timecode / tempo dal MIDI, **assegnazione MIDI** (guida *MIDI*) |
| Voce e audio | **Parola di attivazione** | Controllo vocale con un microfono proprio: parola di attivazione + comando in inglese, p. es. “OpenCue, blackout on” (guida *Comandi vocali*); on/off con il simbolo del microfono in alto a destra |
| Voce e audio | **Dettatura** | Microfono e modello vocale per dettare nella chat IA |
| Assistente | **Assistente IA** | Interruttore principale, connessione a Ollama, comportamento, permessi |
| Avanzate | **Altre opzioni** | **Interruttori rapidi** (controllo vocale, MIDI, blackout, annulla incluso Go – agiscono subito, anche se il loro pulsante è nascosto nella barra), **Mantieni lo schermo acceso** (computer e tablet; su iPad solo su una pagina sicura, https), cosa compare in alto a destra nella barra (ogni voce a sé, per dispositivo) e la **connessione Internet** (pulsante *Testa connessione*) |
| Avanzate | **Predefiniti** | Valori predefiniti per le nuove cue, stato di base dopo *Clear Clear*, valori iniziali ed **Eliminazione**: una conferma prima di eliminare per categoria (cue, apparecchi, libreria, file, altro) – attiva per impostazione predefinita |
| Avanzate | **Ingressi e uscite** | Solo visualizzazione: ogni connessione, a cosa serve e **fin dove arriva** (*solo questo PC*, *rete locale*, *Internet*), con un link all'impostazione corrispondente |

**Al primo avvio nulla lascia il computer:** accesso remoto, Art-Net, sACN e l'API REST verso l'esterno sono spenti. È attiva solo la verifica degli aggiornamenti (si può disattivare); richiede Internet. Se Internet funziona nel browser ma non in OpenCue (firewall, antivirus, rete aziendale), *Generale → Connessione Internet → Testa connessione* mostra **cosa** ostacola.

---

## 8. Cosa esplorare dopo

| Argomento | Dove |
|---|---|
| Apparecchi, libreria GDTF, patch, gruppi | *Apparecchi e patch* |
| Tutti i comandi digitati | *Riferimento dei comandi* |
| Effetti propri con un piccolo linguaggio di script | *Studio effetti* |
| Tablet e telefono come telecomando | *Accesso remoto* |
| Ogni scorciatoia e gesto | *Scorciatoie da tastiera* (anche **Aiuto → Scorciatoie da tastiera**) |
| Palco in 3D, puntare teste mobili su un punto | Pannello **Simulazione 3D** (aggiungilo con *Aggiungi pannello*; modalità Vista / Costruzione / Apparecchi) |
| Modelli 3D propri (STL o OBJ) sul palco | Simulazione 3D → **Costruzione** → **Modello 3D …** (importare o scegliere dalla libreria; l'unità del file mm/cm/m/pollici determina la dimensione originale). **Importare più file insieme** (selezionali nella finestra dei file o trascinali da Esplora risorse sul palco in modalità *Costruzione*): vengono posti uno accanto all'altro intorno al centro della vista e selezionati insieme. Gestiti nel gestore file in **Modelli 3D** |
| Usare brevemente un pannello senza metterlo nel layout | **Visualizza → Apri pannello come finestra**; riga di comando con tastierino e tasti: **Ctrl+F** (console di comando) |
| Cue che partono a un'ora | Pannello **Timecode** e trigger di cue *Timecode* |
| Luci e cue che reagiscono alla musica | Pannello **Audio**, effetti con l'etichetta *Audio*, trigger di cue *Audio* (guida *Audio*) |
| Cue che aspettano un tasto, pad o fader di un dispositivo MIDI | trigger di cue *MIDI* (guida *MIDI*, sezione 5c) |
| Controllare OpenCue da altri programmi | **API REST** (Impostazioni → API; guida *API REST*) |
| File: show, layout, palchi, modelli 3D, effetti | **Libreria → Show… / Layout… / Palchi 3D… / Effetti…** (il gestore file, con importazione ed esportazione come ZIP; il pacchetto di esportazione di uno show può includere anche i modelli 3D del suo palco) |

---

## 9. Dove sono i tuoi dati e come fare il backup

I tuoi dati sono semplici file nella cartella dei dati (`%LOCALAPPDATA%\OpenCue` per impostazione predefinita):

| Cartella | Contenuto |
|---|---|
| `showfiles` | Show (apparecchi, gruppi, cue, preset, effetti) |
| `layouts` | Layout dei pannelli |
| `themes` | Profili di colore |
| `fixtures` | File di apparecchi GDTF |
| `effects` | Script di effetti (`.fx`) |
| `stages` | Palchi 3D |
| `media` | Video e audio dei tuoi show |
| `config` | Impostazioni (`app_config.json`, inclusa la sorgente audio scelta) e i token API (`api_tokens.json`, solo hash) |

Per il backup copia la cartella – oppure usa l'**esportazione** del gestore file (uno show come ZIP con gli apparecchi e gli effetti di cui ha bisogno), che permette anche di spostare uno show su un altro computer.

Nel **gestore file** gli elenchi *Modelli 3D*, *Media*, *Effetti* e *Apparecchi* hanno un selettore **Elenco | Gruppi** (OpenCue ricorda la tua scelta). *Gruppi* mostra prima i gruppi: effetti per tipo (Dimmer, Colore, Posizione, Gobo, Zoom, Fuoco), media per genere (Audio, Immagine, Video), apparecchi per marca e modelli 3D per **show** in cui sono usati (un modello usato in due show è in entrambi i gruppi; l'elenco lo mostra una volta). Un clic apre un gruppo, *Tutti i gruppi* riporta indietro. **Elimina non usati** (elenco *Modelli 3D*) rimuove ogni modello 3D che non è su alcun palco – né quello caricato né uno salvato – così i vecchi import non si accumulano.

La disinstallazione di OpenCue chiede se eliminare anche questi dati; la risposta predefinita è **No**.
