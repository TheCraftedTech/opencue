# Comandi vocali

Con i **comandi vocali** controllate OpenCue con la voce: dite la **parola di attivazione** (predefinita «OpenCue») e subito dopo un **comando della riga di comando** – OpenCue lo trascrive, lo converte nella notazione della riga di comando e lo **esegue subito**, esattamente come un comando digitato (compare anche nella cronologia dei comandi, tutte le finestre seguono). Tutto funziona **offline** sul computer della console (dopo il download una tantum dei modelli), non serve alcuna IA.

Si parla in **inglese**: i comandi della riga di comando (`Fixture`, `At`, `Color`, `Blackout`, `Go` …) sono in inglese, e il riconoscimento vocale è impostato per scrivere parole inglesi.

---

## 1. Attivarlo

1. L'**icona del microfono** in alto a destra nella barra degli strumenti è un **interruttore on/off**:
   - **verde** = il controllo vocale ascolta la parola di attivazione,
   - **rosso e barrato** = spento,
   - **giallo** = errore (microfono irraggiungibile, modello mancante …; il suggerimento è nel tooltip).
2. Una volta vengono scaricati due modelli (ciascuno una sola volta, poi tutto funziona senza internet): il piccolo **modello della parola di attivazione** (41 MB: *Impostazioni → Parola di attivazione → Scarica il modello vocale*, oppure già nell'installatore) e il **modello vocale** per i comandi (*Impostazioni → Dettatura → Carica ora*; è lo stesso della dettatura). Il modello vocale *Accurato* (small) capisce molto meglio di *Veloce* (base).
3. Microfono, parola di attivazione e sensibilità si impostano in *Impostazioni → Parola di attivazione*.

L'icona esiste sul computer della console e anche sui dispositivi remoti (iPad): l'interruttore attiva o disattiva il controllo vocale del server; il microfono stesso è sempre collegato al computer principale.

---

## 2. Come parlare

```
"OpenCue … Blackout on."
"OpenCue … Fixture five at seventy nine, color green."
"OpenCue … Fixtures one through five at full."
```

- Prima la **parola di attivazione**, poi – nello stesso respiro o dopo una breve pausa (fino a circa 2 secondi) – il **comando**.
- Quando il comando è finito, **aspettate circa un secondo**: una breve pausa termina la registrazione (al massimo 10 secondi).
- In basso al centro dello schermo un fumetto mostra l'avanzamento: **In ascolto …** → **Comprensione …** → **il comando** con il suo risultato (verde = fatto, rosso = errore o nulla di compreso). Se OpenCue ha corretto una parola, viene mostrato dopo («corretto: add → At»).
- Parlate con comandi brevi e chiari. Le parole di riempimento («uh», «please», «now», «set») e le balbuzie vengono rimosse.

---

## 3. Cosa si può dire

Dite i comandi come sono scritti nella riga di comando (vedi la guida *Riga di comando*). I numeri si possono dire a parole («seventy nine») o in cifre. Più comandi in un solo respiro si separano con **«then»**.

### Selezionare apparecchi e luminosità

| Dite | Cosa viene eseguito |
|---|---|
| Fixture five | `Fixture 5` |
| Fixtures one through ten | `Fixture 1 Thru 10` |
| Fixture three and seven | `Fixture 3 + 7` |
| Fixture five at seventy nine | `Fixture 5 At 79` |
| Fixture five brightness fifty percent | `Fixture 5 At 50%` (anche *dimmer, intensity, level*) |
| Fixtures one through five at full / at half | `Fixture 1 Thru 5 At Full` / `… At Half` |
| Fixture five on / full | `Fixture 5 At Full` |
| Fixture five off / out | `Fixture 5 At 0` |
| Fixture five at seventy nine point five | `Fixture 5 At 79.5` |
| At at / Everything on / All lights on | `At At` – **tutto acceso** (100 % + bianco): senza selezione tutti gli apparecchi, con una selezione solo quella selezione. Dite prima «Clear» per essere sicuri che sia tutto. |
| Fixtures one through ten minus five (anche *except / without*) | `Fixture 1 Thru 10 - 5` (senza il n. 5) |
| Next fixture / Previous fixture | `Next` / `Previous` (seleziona l'apparecchio successivo / precedente) |
| Group front at full | `Group front At Full` |
| Group front truss at forty | `Group "front truss" At 40` (più parole di un nome stanno insieme tra virgolette) |
| Light / lamp / spot five | `Fixture 5` |

### Colori

| Dite | Cosa viene eseguito |
|---|---|
| Fixture five color green | `Fixture 5 Color Green` |
| Fixture five green | `Fixture 5 Color Green` (la parola «color» viene aggiunta) |
| Fixture five warm white / cool white / light blue | `Fixture 5 Color Warm` / `Cool` / `Lightblue` |
| RGB two fifty five zero zero | `RGB 255 0 0` |
| Color two fifty five one twenty eight zero | `Color 255 128 0` («one twenty eight» = 128 dopo *color / rgb / bpm*) |

Colori come nella riga di comando: red, green, blue, white, black, yellow, cyan, magenta, orange, pink, purple, amber, lime, teal, violet, light blue, warm, cool.

### Posizione e fascio

| Dite | Cosa viene eseguito |
|---|---|
| Pan ninety / Pan fifty percent | `Pan 90` / `Pan 50%` |
| Tilt minus forty five / Pan plus fifteen | `Tilt -45` / `Pan +15` (un segno = relativo) |
| Fixture five home / center | `Fixture 5 Pan 50% Tilt 50%` |
| Zoom half / full / minimum / fifty | `Zoom Half` / `Zoom Full` / `Zoom Min` / `Zoom 50` |
| Focus twenty five | `Focus 25` |
| Gobo forty / gobo spin thirty | `Gobo 40` / `GoboSpin 30` |
| Prism one hundred | `Prism 100` |
| Strobe zero / shutter ten | `Strobe 0` / `Strobe 10` |
| Channel six one hundred twenty eight | `Channel 6 128` (canale 6 dell'apparecchio a DMX 128) |

### Master e blackout

| Dite | Cosa viene eseguito |
|---|---|
| Blackout | `Blackout` (commuta) |
| Blackout on / Blackout off | `Blackout On` / `Blackout Off` |
| Master eighty / Master full / Master minus ten | `Master 80` / `Master Full` / `Master -10` |

### Liste di cue

| Dite | Cosa viene eseguito |
|---|---|
| Go / Next cue | `Go` |
| Back / Go back / Previous cue | `Back` |
| Pause / Resume / Stop | `Pause` / `Resume` / `Stop` |
| Go to cue five | `Go Cue 5` (anche *goto cue five*) |
| Cue list main go | `Cuelist main Go` |
| Cue list front of house back | `Cuelist "front of house" Back` |
| Cuelist two go | `Cuelist 2 Go` |
| Cuelist main fader eighty / Fader fifty | `Cuelist main Fader 80` / `Fader 50` |
| Cue five fade three / Cue five delay one point five | `Cue 5 Fade 3` / `Cue 5 Delay 1.5` |
| Store cue five (merge) | `Store Cue 5` (`Merge`) |
| Update / Clear | `Update` / `Clear` |

### Timecode e audio

| Dite | Cosa viene eseguito |
|---|---|
| Timecode play / pause / stop / reset / reverse | `Timecode Play` / `Pause` / `Stop` / `Reset` / `Reverse` |
| Timecode rate two | `Timecode Rate 2` |
| Tap | `Tap` (battere il tempo) |
| BPM one twenty eight / BPM auto / BPM half | `BPM 128` / `BPM Auto` / `BPM Half` (anche *beats per minute*) |
| Audio start / stop / demo | `Audio Start` / `Stop` / `Demo` |

### Effetti, variabili, programmer

| Dite | Cosa viene eseguito |
|---|---|
| Effect rainbow / Effect off | `Effect rainbow` / `Effect Off` |
| Variable warm white | `Variable "warm white"` |
| Manual / Manual color | `Manual` / `Manual Color` |

### Più comandi

«Fixture one at full **then** fixture two at zero» → `Fixture 1 At Full; Fixture 2 At 0`.

---

## 4. Cosa viene corretto automaticamente

Whisper a volte scrive parole che suonano uguali ma non hanno senso nel comando («add» invece di «at», «true» invece di «thru»). OpenCue controlla **in quale posizione del comando** si trova la parola e inserisce la parola di comando adatta – solo dove calza:

| Sentito / scritto | Diventa | Quando |
|---|---|---|
| add, ad, it, app | At | dopo un numero, prima di un numero («fixture 5 **add** 70») |
| true, threw, till, through, until, to, too, drew, grew, crew, throw … | Thru | tra due numeri («fixtures 1 **true** 5») |
| **2** (Whisper sente «thru» come il numero *two*) | Thru | in una selezione esattamente tra due numeri («fixtures one **two** five» = `Fixture 1 Thru 5`; anche «fixture 1-5» e «1, 2, 5») |
| eight (8) | At | in una selezione tra due numeri («fixture 5 **eight** 70») |
| halve, calf | Half | sempre; «fixture 3 half» = `Fixture 3 At Half` |
| chanel, clair, stroke, pawn, tell, fate, delight … | Channel, Clear, Strobe, Pan, Tilt, Fade, Delay | a seconda della posizione (prima di un numero, o sempre) |
| oh | 0 | dove deve stare un numero («at oh», «master oh») |
| picture, pitcher, fix sure, fixer | Fixture | sempre («**picture** one to four») |
| for, to, too, won, ate, tree | 4, 2, 2, 1, 8, 3 | solo dove deve stare un numero («fixture **for** at fifty» → Fixture 4 At 50) |
| collar, caller | Color | sempre |
| pen, ban, pun | Pan | prima di un numero |
| till, tilted | Tilt | prima di un numero («**till** minus ten») |
| queue, q, cute, cube, key | Cue | prima di un numero («go **key** five») |
| fool | Full | sempre |
| of, own | Off, On | dopo Blackout |
| prison, prisms | Prism | sempre |
| strove | Strobe | sempre |
| paws, pours | Pause | sempre |
| affect, effects | Effect | sempre |
| tab | Tap | sempre |
| read, grin, grain, blew, wait … | Red, Green, Blue, White | dopo «color» o come nome di colore |
| black out, black art, blackouts | Blackout | sempre |
| time code, cue list, grand master, go bo, b p m | Timecode, Cuelist, Master, Gobo, BPM | espressioni di più parole |

Inoltre:

- **Numeri a parole** → cifre («twenty one», «one hundred and five», «two point five», «minus ten percent»).
- **Confronto fonetico:** una parola sconosciuta che si trova dove deve stare una determinata parola di comando e suona uguale diventa quella parola.
- **Piccoli errori di ortografia** delle parole chiave → la parola di comando più vicina («blakout» → Blackout).
- **Varianti della parola di attivazione** («open queue», «open Q», «OpenCue») vengono rimosse all'inizio, così come tutto ciò che è stato detto prima della parola di attivazione.
- **I nomi** (dopo *group, cuelist, effect, variable*) restano come pronunciati.
- **La percentuale** dopo Master, Fader, BPM e numeri di cue viene tralasciata («master eighty percent» → `Master 80`), perché la riga di comando lì non conosce la percentuale.
- Le chiacchiere introduttive prima del comando («set», «please», tutto ciò che non è compreso) vengono tralasciate; il comando deve iniziare con una parola di comando.

---

## 5. Cosa non funziona a voce

In **modalità operatore** sulla console (*Visualizza → Modalità operatore ...*) il controllo vocale è **disattivato**, così che su questo PC sia possibile solo ciò che offre la superficie di controllo; dopo l'uscita riprende a funzionare se era attivo.

Per sicurezza il controllo vocale **non esegue mai nulla che elimini o sovrascriva**: `Delete …`, `Clear Clear`, `Overwrite`. Il fumetto dice allora «Non a voce». Digitate questi comandi o usate l'interfaccia.

---

## 6. Quando non funziona

| Visualizzazione | Cosa fare |
|---|---|
| Microfono giallo | Leggete il tooltip; *Impostazioni → Parola di attivazione* (microfono giusto?) |
| «Modello vocale mancante» | *Impostazioni → Dettatura → Carica ora* (e per la parola di attivazione: *Impostazioni → Parola di attivazione → Scarica il modello vocale*) |
| «Nulla di compreso» | Più vicini al microfono, parlate più chiaramente, dite il comando subito dopo la parola di attivazione |
| «Nessun comando riconosciuto» | Il testo non inizia con una parola di comando – il fumetto mostra ciò che è stato compreso; parlate esattamente come nella riga di comando |
| Comando rosso (✗) | La riga di comando dice cosa non va (ad esempio l'apparecchio non esiste, «questa lista di cue non ha cue») |
| La parola di attivazione non viene riconosciuta | Aumentate *Impostazioni → Parola di attivazione → Sensibilità* |
| Una parola viene sempre scritta male | Annotate cosa scrive Whisper (il testo è nel registro) – la tabella delle correzioni è facile da estendere |

La parola di attivazione viene riconosciuta da un piccolo modello offline, il comando che segue viene trascritto da Whisper (circa 1–3 secondi su un computer normale). Musica alta o rumore nella stanza peggiorano il riconoscimento – un microfono vicino alla bocca aiuta più di ogni altra cosa.
