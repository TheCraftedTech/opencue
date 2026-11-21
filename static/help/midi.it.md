# MIDI

Con il **MIDI** controllate OpenCue da un controller, una tastiera, dei pad o un software musicale – e OpenCue può inviare esso stesso MIDI. Un tasto, un fader, una manopola o un cambio di programma attiva un **comando della riga di comando**, proprio come una scorciatoia da tastiera personalizzata (vedi *Scorciatoie da tastiera*) – in più con i fader.

La mappatura appartiene al **programma**, non allo show: vale per tutti gli show ed è memorizzata nella configurazione dell'applicazione. La raggiungete in quattro modi: l'**icona MIDI** in alto a destra nella barra degli strumenti, **Impostazioni → Controlli → MIDI**, **Controlli → Mappatura MIDI …** e – per tasti e fader di un pannello – **Assegna MIDI …** nelle proprietà del pannello. Il dispositivo MIDI è collegato al computer della console; modificare l'elenco funziona anche da un tablet, l'apprendimento e il monitor solo sul computer della console.

---

## 1. Cos'è il MIDI? (in breve)

Il MIDI non invia suono, ma piccoli **messaggi**. Ne servono tre tipi:

| Messaggio | Cosa segnala il vostro dispositivo | In OpenCue |
|---|---|---|
| **Nota** | Un tasto (tasto di pianoforte, pad) viene premuto o rilasciato. Ognuno ha un numero, ad es. 60 = **Do4** (Do centrale), e una **velocity** (0–127, quanto forte è stato colpito). | Tipi **Tasto**, **Interruttore**, **Mantieni** – oppure **Fader** (la velocity diventa il valore) |
| **Controller (CC)** | Un fader o una manopola. Ognuno ha un numero (0–127) e un valore 0–127. | Tipi **Fader** (fader, potenziometri) o **Encoder** (manopole senza fine) |
| **Cambio di programma** | Viene scelto un «programma» con un numero. | Tipo **Tasto** (ad es. programma 3 = `Go Cue 3`) |

Ogni messaggio ha anche un **canale** (1–16) così più dispositivi possono condividere una linea. Se non lo sapete: lasciate su **Tutti**.

---

## 2. Primi passi

1. Collegate il dispositivo MIDI via USB (Windows lo riconosce da solo – i dispositivi class-compliant non richiedono driver).
2. Fate clic sull'**icona MIDI** in alto a destra (o **Controlli → Mappatura MIDI …**). In alto si vede quali dispositivi vengono riconosciuti. Il **monitor** in basso mostra in diretta tutto ciò che il vostro dispositivo invia – premete un tasto e guardate: `Note On C4 (60) · 100`.
3. **Nuova mappatura MIDI** → fate clic sul campo del segnale nella riga → **premete o muovete** qualcosa sul dispositivo → **Applica**. Il segnale è appreso.
4. Inserite a destra il **comando**, ad es. `Go`. Fatto – il tasto ora attiva `Go`. La riga si illumina brevemente quando scatta.

La mappatura viene salvata subito. L'interruttore **MIDI attivo** in alto disattiva tutto (OpenCue non ascolta allora nessun dispositivo).

**L'icona della barra degli strumenti** mostra lo stato: **verde** = un dispositivo è pronto, **grigio** = nessun dispositivo collegato, **giallo** = un dispositivo non si può aprire (di solito lo tiene un altro programma), **rosso e barrato** = il MIDI è disattivato. Un clic apre la mappatura; il tooltip nomina i dispositivi riconosciuti.

**Impostazioni → Controlli → MIDI** (come tutte le impostazioni con *Salva*): usare il MIDI, **quali dispositivi** vengono usati (ogni dispositivo collegato ha un interruttore – uno deselezionato non viene mai aperto), l'**uscita**, il **timecode (MTC)** e il **tempo dal clock MIDI** (sezione 5b) e pulsanti verso la mappatura.

In **Impostazioni → Ingressi e uscite → MIDI** vedete i dispositivi riconosciuti, se vengono letti in questo momento, l'uscita e quante mappature sono attive.

---

## 3. I tipi

| Tipo | Effetto | Esempio |
|---|---|---|
| **Tasto** | Il comando viene eseguito quando il tasto viene premuto. | Pad 1 → `Go`; Pad 2 → `Back`; Pad 3 → `Clear` |
| **Interruttore** | Ogni pressione commuta tra il **comando** e il **comando di spegnimento** (vuoto = lo stesso comando entrambe le volte). | `Blackout` (commuta da solo); oppure `Effect Rainbow` / `Effect Off` |
| **Mantieni** | Il **comando** viene eseguito alla pressione, il **comando di rilascio** al rilascio («flash»). | `Group front At Full` / `Group front At 0` |
| **Fader** | Il comando riceve il valore come `{value}`, scalato nell'intervallo **Da … A** (anche **Inverti**). | Fader → `Master {value}` (0–100); Fader → `Cuelist main Fader {value}` |
| **Encoder** | Per **manopole senza fine**: ogni passo viene eseguito come `{delta}` (con segno, moltiplicato per **Passo**). Il tipo di encoder (normale / bit di segno / centro 64) si imposta nella riga. | Manopola → `Pan {delta}` (selezionate prima degli apparecchi) |

**Segnaposto nel comando:** `{value}` (valore del fader nell'intervallo Da–A), `{delta}` (passi dell'encoder, ad es. `+1` / `-2`), `{velocity}` (velocity 0–127), `{note}` e `{number}` (numero di nota / controller / programma), `{channel}`, `{raw}` (valore grezzo 0–127).

**Start / Stop / Continue (transport):** potete anche scegliere *Start*, *Stop* e *Continue* del software musicale come segnale (tipo nella finestra di apprendimento; non hanno né canale né numero). Esempio: Start → `Timecode Play`, Stop → `Timecode Stop`.

**Pickup:** un **fader** senza motore spesso sta in una posizione diversa dal valore nel programma. Con **Pickup** il fader subentra solo dopo aver raggiunto o superato il valore attuale – nessun salto al primo contatto. Se nel frattempo il valore è stato cambiato altrove, deve raggiungerlo di nuovo. Funziona per `Master {value}`, `Fader {value}`, `Cuelist <nome> Fader {value}` e per la luminosità o un attributo del fascio di un apparecchio, di un gruppo o della selezione (`Fixture 5 At {value}`, `Group front At {value}`, `At {value}`, `Zoom {value}`); gli altri comandi subentrano subito.

**Altri tipi:** *Doppio clic* (il comando viene eseguito alla seconda pressione entro 0,4 s) e *Pressione lunga* (viene eseguito quando il tasto è tenuto premuto per il tempo impostato – ad es. 600 ms; rilasciare prima annulla). Per i fader scegliete una **curva**: *Lineare*, *Partenza lenta* (valori fini in basso) o *Partenza rapida*. Anche l'**aftertouch** (pressione su un tasto tenuto premuto) e la **pressione di canale** possono essere mappati come fader. **Un fader, più comandi:** separateli con un punto e virgola, ad es. `Master {value}; Group front At {value}`.

**Feedback verso il dispositivo (LED, fader motorizzati):** nella riga scegliete sotto **Feedback** uno stato della console: *Blackout*, *Master*, *Selezione presente*, *Cue attivo*, *Timecode in corso* o *Fader lista di cue*. OpenCue lo invia come nota / controller / pitch bend **con lo stesso numero e canale** del segnale all'uscita che ha lo stesso nome del dispositivo – su un controller a pad il LED si accende, un fader motorizzato si muove insieme. Per gli stati acceso/spento impostate **LED acceso / LED spento** (la velocity; sui pad con colori è il colore). Viene inviato solo quando il valore cambia, e dopo il collegamento di un dispositivo viene reinviato tutto.

Altri esempi:

| Dispositivo | Mappatura |
|---|---|
| Cambio di programma (ad es. su una tastiera) | Tasto, comando `Go Cue {number}` – il programma 5 salta al cue 5 |
| Tasto con velocity | Fader (sorgente Nota), comando `Group front At {value}`, Da 0 A 100 – più forte si colpisce, più luminoso |
| Rotella pitch bend | Fader, comando `Master {value}` |
| Banco di fader | una riga per fader (CC 1…8): `Fixture 1 At {value}`, `Fixture 2 At {value}` … |

Trigger: un tasto scatta alla **pressione**. Un CC usato come tasto (i pad di molti controller) scatta a un valore **di 64 o più**. Un fader invia al massimo **circa 40 comandi al secondo** (i movimenti veloci vengono uniti, l'ultimo valore arriva sempre).

---

## 3b. Copiare righe, esportare, importare, da un pannello

- **Copia** (icona accanto al cestino): duplica una riga con tipo e comando, il segnale resta vuoto – comodo per una serie di fader simili (fader 1 … 8).
- **Esporta / Importa** (in fondo alla finestra): salva la mappatura in un file (`opencue-midi-mapping.json`) o legge un tale file. All'importazione le righe vengono **aggiunte** – nulla viene sostituito.
- **Modello …** (in fondo alla finestra): crea una **serie** di righe – *Banco di fader* (apparecchi 1...8), *Pad cue*, *Tasti transport* (Go, Back, Pause, Blackout), *Master e blackout* – e poi vi lascia **premere o muovere i controlli uno dopo l'altro** («Segnale 2 di 8», *Salta* prosegue, Annulla termina la serie). Così mappate qualsiasi controller senza conoscere i numeri.
- Un **campo di ricerca** sopra l'elenco (segnale, comando, dispositivo) e le **frecce** su ogni riga (sposta su / giù; disattivate durante una ricerca).
- **Salta a questa cue con un tasto MIDI …** nella finestra di un **cue** (*Modifica cue*): crea una mappatura `Cuelist "<lista>" Go Cue <numero>` e apprende il segnale – il cue parte allora alla pressione di un tasto, **in qualsiasi momento** (un tasto di «salto» libero). Per un cue che aspetta il suo segnale all'interno di una sequenza vedi il trigger di cue **MIDI** (sezione 5c).
- **Assegna MIDI …** nelle proprietà di un **pulsante, interruttore o fader**: crea una mappatura con il comando del pannello (interruttore: comando di accensione e spegnimento, fader: con Da/A) e apprende subito il segnale. La mappatura resta anche se eliminate il pannello.

---

## 4. Si applica a, Esegui, Cronologia

- **Impara segnale → Si applica a:** *Tutti i dispositivi* (qualsiasi dispositivo che invia questo segnale attiva) oppure *Solo questo dispositivo* (ad es. quando due controller inviano gli stessi numeri).
- **Esegui** disattivato: il comando viene solo **scritto nella riga di comando**, non eseguito (per controllarlo o completarlo).
- **Nella cronologia:** il comando compare nella cronologia della riga di comando (tutte le finestre lo vedono).
- Non c'è un controllo dei segnali duplicati: due righe con lo stesso segnale scattano **entrambe** (la finestra di apprendimento vi avvisa).

**Sicurezza:** `Delete …` e i comandi che contengono `Overwrite` **non vengono mai eseguiti via MIDI** (un tasto colpito per sbaglio non deve distruggere dati). `Clear Clear` è consentito.

---

## 5. OpenCue invia MIDI: il comando `Midi`

Il comando `Midi` invia all'**uscita** (scelta in alto nella finestra; **Automatica** prende il primo dispositivo reale, altrimenti il sintetizzatore Windows «Microsoft GS Wavetable Synth» – così sentite subito qualcosa):

| Comando | Effetto |
|---|---|
| `Midi Note 60` | Suona la nota Do4 (60), velocity 100, spenta dopo 0,3 s |
| `Midi Note 60 90 Ch 2 Len 1` | Nota 60, velocity 90, canale 2, per 1 secondo |
| `Midi On 60 100` / `Midi Off 60` | Nota accesa / spenta singolarmente (resta finché non inviate `Off`) |
| `Midi CC 7 100` | Controller 7 al valore 100 |
| `Midi PC 3` | Cambio di programma 3 |
| `Midi MSC Go 5 List 2` | Invia **MIDI Show Control** (`Go`, `Stop`, `Resume`, `AllOff`, `Restore` ...; facoltativi `List <n>`, `Device <0-127>`) |
| `Midi Panic` | All notes off (tutti i canali) |

Si può combinare con pulsanti, scorciatoie da tastiera, comandi dei cue o il **controllo vocale** («OpenCue, MIDI note sixty») – ad es. un cue che attiva un suono nel vostro software musicale. Anche tramite l'**API REST**: `POST /api/v1/command` con `Midi Note 60`; `GET /api/v1/midi` restituisce dispositivi e stato.

---

## 5b. Tempo e ritmo dal software musicale (MTC e clock MIDI)

Due interruttori in **Impostazioni → Controlli → MIDI** fanno seguire a OpenCue un software musicale (DAW) o un altro dispositivo. Entrambi reagiscono **solo al formato corrispondente e solo quando arriva davvero qualcosa di valido** – altrimenti non succede nulla. Finché uno è attivo, i dispositivi in uso restano aperti.

**Timecode dal MIDI (MTC).** Se il software invia *MIDI Timecode* (MTC, 24 / 25 / 29,97 / 30 fotogrammi al secondo), il **timecode globale** scorre al passo con quell'ora: i cue con il trigger «Timecode», il lettore timecode e i pannelli seguono. Viene preso solo un **flusso senza lacune e plausibile** (tre gruppi concordanti, valori nell'intervallo valido); rumore, marcia indietro e segnali estranei vengono ignorati. Se il vostro clock deriva di più di 0,1 s, viene rimesso all'ora giusta. **Se il flusso si ferma** (software fermato, cavo staccato), il timecode si ferma. Se il software salta a una posizione da fermo (*full frame*), anche il timecode salta. Un timecode avviato a mano **non** viene fermato quando l'MTC manca; mentre l'MTC scorre, l'MTC ha la priorità. Le impostazioni mostrano l'ora ricevuta e la frequenza fotogrammi.

**Invio: OpenCue come sorgente del tempo.** *Invia Timecode (MTC)* invia il timecode globale come MIDI Timecode (frequenza 24 / 25 / 29,97 / 30; quarti di fotogramma temporizzati con precisione, un messaggio full frame nei salti) all'uscita scelta. *Invia MIDI clock* invia *Start* / *Stop* e il clock al tempo del pannello Audio mentre il timecode scorre.

**Ricevere lo show control (MSC).** Con *Ricevi controllo show* e un **ID dispositivo** (0-127, 127 = tutti), GO, STOP, RESUME, ALL_OFF e RESTORE (anche con numero di cue e di lista) controllano le liste di cue – ad es. da un programma di show o da una console. Il comando `Midi MSC ...` li invia.

**Tempo dal clock MIDI.** Un **clock MIDI stabile** (24 impulsi per quarto, da 30 a 300 BPM) imposta il tempo come tempo fisso del pannello Audio (come il comando `BPM 128`) e segue i cambi di tempo. Mappate *Start*, *Stop* e *Continue* come segnali (vedi sopra).

Per provare senza software: un generatore di timecode MIDI (esistono programmi e pagine web gratuiti) invia tramite una porta MIDI virtuale (su Windows ad es. *loopMIDI*) – entrambe le parti scelgono la stessa porta.

---

## 5c. Trigger di cue: MIDI

Oltre a *Go*, *Follow*, *Timecode* e *Audio* un cue può avere il trigger **MIDI**: aspetta allora **un segnale MIDI** e scatta quando arriva – una **sequenza che suonate con una tastiera, un pad o un pedale**. Nella finestra del cue (*Modifica cue*) scegliete il trigger *MIDI*, poi selezionate il **segnale** (oppure premete **Impara segnale** e colpite il tasto – viene compilato per voi; l'apprendimento funziona sul computer della console). Nella lista dei cue potete anche digitarlo nella cella del trigger (`midi note c4`, `midi cc 20 64`, `midi pc 5 ch 2`) o usare il comando `Cue 3 Trigger Midi Note 60` (vedi *Riga di comando*).

| Segnale | Il cue scatta … |
|---|---|
| **Nota** (tasto / pad), numero 0–127 | … quando il tasto viene premuto (Note On; il rilascio non fa nulla). |
| **Controller (CC)**, numero 0–127, soglia 1–127 (predefinita 64) | … quando il valore del controller **raggiunge** la soglia salendo dal basso. Un pad inviato come CC (127) scatta subito; un fader scatta quando viene spinto oltre la soglia, e di nuovo dopo che è stato riportato sotto e spinto di nuovo su. |
| **Cambio di programma**, numero 0–127 | … quando questo programma viene scelto sul dispositivo. |

Ogni segnale può essere limitato a un **canale** (1–16); *Qualsiasi* accetta tutti i canali e tutti i dispositivi.

Come funziona:
- Come il trigger audio, il cue scatta quando è il **cue successivo** di una lista in esecuzione: avviate prima la lista con *Go*, poi il successivo cue MIDI aspetta il suo segnale. In seguito il cue successivo (se ha anch'esso un trigger MIDI) aspetta a sua volta – potete concatenare un'intera sequenza a tasti o pad.
- Una breve pausa di 0,25 s dopo ogni trigger evita che un colpo avvii due cue.
- Il **MIDI deve essere attivo** (*Impostazioni → MIDI → Usa MIDI*, o l'interruttore in alto nella finestra della mappatura). OpenCue apre da solo i dispositivi MIDI non appena un cue ha un trigger MIDI – per questo non serve una riga di mappatura – e li rilascia quando nessun cue ha più bisogno del MIDI. I dispositivi deselezionati in *Impostazioni → MIDI* restano chiusi.
- Il trigger funziona per ogni lista di cue indipendentemente, e anche dal punto di vista dei dispositivi remoti: il segnale proviene dai dispositivi MIDI del **computer della console**.
- **Differenza rispetto alla mappatura** (sezione 3): una riga di mappatura esegue un comando **in qualsiasi momento** (ad es. `Go`, o `Cuelist "Main" Go Cue 5` = saltare lì). Il trigger di cue fa parte del **cue stesso** e conta solo mentre il cue è il successivo in coda. Entrambi si possono usare insieme; un segnale usato da entrambi fa entrambe le cose.

---

## 6. Quando non funziona

| Problema | Soluzione |
|---|---|
| Dispositivo non riconosciuto | Un altro cavo/porta USB; **Impostazioni → Ingressi e uscite** aggiorna i dispositivi ogni pochi secondi; molti dispositivi hanno bisogno di un attimo dopo il collegamento. |
| «in uso?» sul dispositivo | **Un altro programma** (software musicale, l'editor del produttore) ha aperto il dispositivo – su Windows di solito **un solo** programma può leggerlo. Chiudete l'altro programma, poi disattivate e riattivate **MIDI attivo**. |
| Il monitor non mostra nulla | Il monitor funziona solo mentre la finestra è aperta. **MIDI attivo** è attivato? |
| Un cue con il trigger **MIDI** non scatta mai | Scatta solo quando è il **cue successivo** di una lista **in esecuzione** (avviate prima la lista con *Go*). *MIDI attivo* deve essere attivo, il dispositivo non deve essere deselezionato in *Impostazioni → MIDI*, e numero, canale e tipo devono corrispondere a ciò che il monitor mostra quando premete il tasto (usate *Impara segnale* nella finestra del cue). |
| Un tasto non attiva nulla | Controllate canale / dispositivo in «Si applica a»; provate il comando a mano nella riga di comando; la riga si illumina nella finestra? (allora il segnale arriva e il problema è il comando). |
| Il fader salta | Attivate **Pickup** nella riga (master e fader): il fader subentra solo dopo aver raggiunto il valore attuale. |
| Il software musicale e OpenCue devono connettersi | Windows ha bisogno di una **porta MIDI virtuale** (gratuita, ad es. *loopMIDI*). Compare poi come ingresso/uscita in entrambi i programmi. |

---

## 7. Limiti

- **Tablet:** l'iPad (Safari) non sa fare MIDI nel browser. I dispositivi MIDI appartengono al computer della console; potete modificare la mappatura da qualsiasi dispositivo.
- **Più programmi:** su Windows di solito **un solo** programma legge un dispositivo MIDI (vedi «in uso?»). Le versioni più recenti di Windows (*Windows MIDI Services*) potrebbero cambiarlo – OpenCue apre i dispositivi solo quando serve e li rilascia con **MIDI attivo** disattivato.
- **MIDI di rete e porte virtuali** sono configurati dal sistema operativo (ad es. *loopMIDI*, *rtpMIDI*); compaiono poi come qualsiasi dispositivo.
- **Profili di controller:** invece di profili fissi per singoli modelli ci sono **modelli con una serie di apprendimento** – funzionano con ogni controller. I colori dei LED (velocity) differiscono da dispositivo a dispositivo; si impostano sotto il feedback come *LED acceso / LED spento*.
- **Più mappature tra cui commutare** (ad es. «palco» e «prove»): come file tramite **Esporta / Importa** nella finestra; non c'è un interruttore separato.
- Pitch bend, aftertouch e pressione di canale vengono valutati come fader; non c'è la posizione del brano e non ci sono eventi MIDI nel flusso WebSocket dell'API.
- Non ancora provato con tutti i dispositivi: fader, encoder, pad e feedback sono testati con messaggi artificiali – il **monitor** nella finestra mostra cosa il vostro dispositivo invia davvero.
