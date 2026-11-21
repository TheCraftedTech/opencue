# Riga di comando – Riferimento dei comandi

La **riga di comando** controlla OpenCue digitando, nello stile delle console luci professionali. Integra l'uso con mouse e touch con brevi comandi che potete digitare, concatenare e memorizzare nei cue. È disponibile come pannello **Riga di comando** (*Modifica → Aggiungi pannello…*); i pannelli **Tastierino numerico comandi** e **Pulsanti comando** scrivono nella stessa riga di input per l'uso touch.

Ogni comando viene eseguito sul server e il risultato viene segnalato a **tutti** i dispositivi connessi: elenco apparecchi, lista di cue e programmer si aggiornano ovunque contemporaneamente, non solo dove avete digitato.

> Le parole di comando sono in inglese – come sulle console luci. Maiuscole e minuscole **non** contano per comandi, attributi e nomi.

---

## 1. L'idea in un minuto

Ogni comando segue lo stesso schema: **cosa** – **quale** – **valore**.

| Azione / oggetto | ID / intervallo | Proprietà / destinazione |
|---|---|---|
| `Fixture` | `1` | – |
| `At` | – | `80` |
| `Store` | `Cue 1.5` | – |
| `Cue` | `1` | `Fade 3` |
| `Cuelist` | `Show` | `Go` |

- L'**azione o l'oggetto** viene sempre per primo (`Fixture`, `Group`, `At`, `Color`, `Pan`, `Zoom`, `Store`, `Cue`, `Go`, `Cuelist` …).
- L'**ID o l'intervallo** dice cosa è interessato: un numero di apparecchio (FID), un nome, un numero di cue, il nome di una lista di cue o un intervallo (`1 Thru 10`).
- La **proprietà o la destinazione** è il valore vero e proprio: percentuale, gradi, tempo, nome, colore.
- I comandi **si basano l'uno sull'altro**, come su una vera console: prima si seleziona (`Fixture 1 Thru 4`), poi un comando di valore (`At 80`) agisce esattamente su quella selezione. La selezione è **condivisa da tutti i dispositivi**: un clic nell'elenco apparecchi su uno schermo e un comando `Fixture` su un altro agiscono sulla stessa selezione.
- Il testo con spazi (un nome di cue, un nome di lista) va tra virgolette doppie: `Label Cue 1 "Intro scene"`. Una parola tra virgolette è sempre un **nome**, mai una parola di comando, così si può indirizzare anche un gruppo chiamato «Color».
- L'input viene validato: numeri non validi (`Zoom abc`), attributi o nomi sconosciuti e valori mancanti danno un messaggio di errore **senza modificare nulla**.

```
Fixture 1 Thru 4 At 80
Fixture 1 Thru 4 Color Red
Store Cue 1 "Opening"
Go
```

---

## 2. Selezionare apparecchi e gruppi

| Comando | Effetto |
|---|---|
| `Fixture 1` | Seleziona l'apparecchio FID 1 (sostituisce la selezione attuale). |
| `Fixture 1 Thru 10` | Seleziona i FID da 1 a 10. |
| `Fixture 1 + 3` | Seleziona i FID 1 **e** 3 (combinate quanto volete con `+`). |
| `Fixture 1 Thru 5 + 10` | Seleziona i FID 1–5 e anche 10. |
| `Fixture 1 Thru 10 - 5` | Seleziona i FID 1–10 **senza** 5 (un `-` con spazi rimuove; ne sono ammessi più d'uno: `- 5 - 7 Thru 8`). |
| `Next` / `Previous` | Seleziona l'**apparecchio successivo / precedente** per FID (ricomincia da capo; senza selezione `Next` = il primo, `Previous` = l'ultimo). Scorrete gli apparecchi uno a uno. |
| `Fixture "Head 2"` | Seleziona l'apparecchio / gli apparecchi con questo **nome** (combinabile anche con `+`). |
| `Group 1` | Seleziona il 1° gruppo nell'elenco dei gruppi. |
| `Group 1 Thru 4` | Seleziona gli apparecchi dei gruppi da 1 a 4. |
| `Group Front` | Seleziona il gruppo con questo **nome** (`Group "Front Truss"` quando contiene spazi). |

`Group N` indica l'**N-esimo gruppo creato**. Il nome è più semplice e robusto: `Group Front` funziona a prescindere dall'ordine.

Una singola parola può essere scritta senza virgolette se non coincide con una parola di comando e il nome esiste davvero. Altrimenti mettete tra `"…"` i nomi con spazi, virgole, punti e virgola o `+`, e i nomi che sembrano un comando o un numero.

### Creare, rinominare, eliminare gruppi

La **selezione attuale** può essere memorizzata come gruppo:

| Comando | Effetto |
|---|---|
| `Store Group "Front"` | Crea il gruppo dalla selezione attuale. |
| `Store Group "Front" Merge` | Se esiste: la selezione viene **aggiunta**. |
| `Store Group "Front" Overwrite` | Se esiste: i membri vengono **sostituiti**. |
| `Label Group Front "Stage front"` | Rinomina (funziona anche `Set Group 2 Name "Stage front"`, anche per numero). |
| `Delete Group Front` | Elimina il gruppo (`Delete Group 2` per numero) – gli apparecchi restano. |

Senza selezione `Store Group` segnala un errore. Un nome esistente (senza distinzione tra maiuscole e minuscole) non viene mai sovrascritto in silenzio. Un apparecchio appartiene al massimo a un gruppo.

---

## 3. Impostare valori: At / Full

Agisce sugli apparecchi **attualmente selezionati** (canale dimmer).

| Comando | Effetto |
|---|---|
| `At 80` | Dimmer all'80 % (funziona anche `At 80%`). |
| `At Full` | Dimmer al 100 %. |
| `At At` | **Tutto acceso**: dimmer 100 % **e colore bianco** (gli apparecchi senza colore ricevono solo il dimmer). **Senza selezione riguarda TUTTI gli apparecchi** (la selezione resta vuota) – l'opposto di `Clear Clear`. Con una selezione si accende solo quella selezione. Possibile anche: `Fixture 5 At At`, `At At Color Red` (tutto acceso, rosso). |
| `Zero` | Selezione allo 0 % (come `At 0`). |
| `Full` | Forma breve senza «At» davanti – anch'essa 100 %. |
| `At 0` | Dimmer allo 0 % (spento). |
| `At +10` / `At -10` | Aumenta / diminuisce il valore attuale del dimmer di 10 punti percentuali. |

I valori sono limitati a 0–100 %. `At +` / `At -` si riferisce all'ultimo valore impostato nel programmer per ogni apparecchio (o al valore DMX attualmente emesso se non è ancora stato programmato nulla).

Gli apparecchi interessati ricevono un indicatore di stato rosso nell'elenco apparecchi – sono ora «nel programmer» e possono essere memorizzati con `Store Cue`.

### Master (luminosità complessiva)

`Master` (in breve `GrandMaster`) scala l'uscita di **tutti** i canali dimmer in percentuale. Il valore predefinito è 100 %. Il valore resta finché non lo cambiate ed è salvato con il file show.

| Comando | Effetto |
|---|---|
| `Master 80` / `Master At 80` | Luminosità complessiva 80 % (la parola `At` è facoltativa). |
| `Master Full` | 100 %. |
| `Master -10` / `Master +10` | Diminuisce / aumenta di 10 punti percentuali. |

Il master scala solo i canali dimmer; colori e pan/tilt restano invariati. (Il **fader di una lista di cue** è un'altra cosa – vedi il capitolo 10.)

### Blackout

`Blackout` porta la **luminosità di tutti gli apparecchi a 0** e la ripristina al successivo `Blackout`. È un interruttore, indipendente dal master.

| Comando | Effetto |
|---|---|
| `Blackout` | Commuta. |
| `Blackout On` / `Blackout Off` | Attiva / disattiva (funzionano anche `1`/`0`, `True`/`False`). |

**Il blackout ha la priorità su tutto** – fader, comandi, cue, dissolvenze ed effetti in esecuzione: finché è attivo la luminosità di ogni apparecchio resta a 0, nell'uscita DMX **e** nella simulazione 3D. I valori vengono conservati: durante un blackout potete cambiare normalmente la luminosità, e dopo `Blackout Off` compare l'ultimo stato **impostato**. Gli apparecchi **senza** canale dimmer (RGB puro) vengono oscurati tramite il colore. Un pulsante a lampadina pulsante nella barra degli strumenti mostra un blackout attivo; un clic commuta. Lo stato vale per tutti i dispositivi ma **non** viene salvato nello show.

### Timecode: `Timecode` / `TC`

Il timecode globale (il clock interno) può essere controllato anche da comando – ad esempio nel campo **CMD** di un cue (`Timecode Play` avvia il clock quando il cue scatta).

| Comando | Effetto |
|---|---|
| `Timecode` | Mostra lo stato (ora, in esecuzione/fermo, velocità). |
| `Timecode At 4.3` | Salta a 4,3 s (anche `00:00:04.300`, `1:04.300`; al massimo 100 h). |
| `Timecode At 4.3 Play` | Salta e avvia (`Reverse` avvia all'indietro). |
| `Timecode +5` / `Timecode -2` | Relativo: 5 s in avanti / 2 s indietro. |
| `Timecode Play` / `Reverse` | Scorre in avanti / all'indietro. |
| `Timecode Pause` | Pausa. |
| `Timecode Stop` (`Reset`) | Ferma e imposta a 00:00:00.000. |
| `Timecode Rate 2` | Velocità (0,1 … 8; funziona anche `0.5x`). |

Un salto non fa scattare i cue a timecode; lo fa solo la marcia in avanti.

### Audio e tempo: `Tap` / `BPM` / `Audio`

Controlla il pannello *Audio* (vedi la guida *Audio*) – utilizzabile anche nel campo **CMD** di un cue.

| Comando | Significato |
|---|---|
| `Tap` | Battere il tempo: dal secondo colpo il tempo viene impostato dai vostri colpi (manuale) e il battito parte sul colpo. |
| `BPM` | Mostra il tempo e la modalità. |
| `BPM 128` | Tempo fisso (30 … 300). |
| `BPM Auto` | Torna al rilevamento automatico. |
| `BPM Half` / `BPM Double` | Dimezza / raddoppia il tempo (quando il rilevamento ha trovato il doppio / la metà). |
| `Audio Start` / `Audio Stop` | Apre la sorgente scelta / la chiude. |
| `Audio Demo` | Avvia il battito demo. |
| `Audio` (`Audio Status`) | Mostra se l'audio è in esecuzione, il tempo e il livello. |

### Inviare OSC: `Osc`

`Osc /address [value ...]` invia un messaggio OSC alla destinazione impostata in **Controlli → OSC ...** (*Invia a*): `Osc /opencue/go`, `Osc /light/1 0.5 hello`. I valori sono numeri (gli interi partono come interi), `true` / `false` o testo. Senza destinazione il comando lo segnala. Vedi la guida *Pianificazione, ora del giorno e OSC*.

### Inviare MIDI: `Midi`

Invia MIDI all'uscita scelta (vedi la guida *MIDI*): `Midi Note 60 [velocity] [Ch 2] [Len 0.5]` suona una nota e la spegne di nuovo, `Midi On 60` / `Midi Off 60` singolarmente, `Midi CC 7 100` imposta un controller, `Midi PC 3` un cambio di programma, `Midi Panic` spegne tutte le note.

---

## 4. Colore e posizione: Color / RGB / Pan / Tilt

Agiscono anch'essi sugli apparecchi **attualmente selezionati**.

| Comando | Effetto |
|---|---|
| `Color Red` | Imposta il colore su rosso (colore con nome, elenco sotto). |
| `Color #FF8000` | Colore in esadecimale (funziona anche la forma breve `#F80`). |
| `Color 255 128 0` | Colore come tre valori 0–255 (rosso / verde / blu). |
| `RGB 255 0 0` | Lo stesso (notazione da console). |
| `Pan 180` | Muove il pan a 180°. |
| `Tilt -45` | Muove il tilt a -45°. |
| `Pan 50%` | Pan in percentuale dell'intervallo (0–100 %; 50 % = centro). |
| `Pan +10%` / `Tilt -5%` | Relativo al valore attuale, in percentuale dell'intervallo. |
| `Pan +15` / `Tilt -15` | Relativo in gradi (con segno). |

**Colori con nome:** `Red`, `Green`, `Blue`, `White`, `Black`, `Yellow`, `Cyan`, `Magenta`, `Orange`, `Pink`, `Purple`, `Amber`, `Lime`, `Teal`, `Violet`, `LightBlue`, `Warm`, `Cool`.

**Gradi per pan/tilt:** OpenCue legge il vero intervallo di movimento (intervallo fisico) dal profilo GDTF dell'apparecchio, quindi apparecchi diversi possono posizionarsi in modo leggermente diverso allo stesso valore in gradi. Se il profilo non ha un intervallo, vale il predefinito: **pan da -270° a +270°, tilt da -135° a +135°**.

---

## 5. Attributi del fascio e canali: Zoom, Gobo, CH …

Oltre a luminosità, colore e posizione si può impostare **ogni canale** di un apparecchio – in due modi: per **nome dell'attributo** (percentuale, stessa logica dei fader nel programmer) o direttamente per **numero di canale** o **nome** (come «DMX diretto»).

### Attributi in percentuale

| Comando | Effetto |
|---|---|
| `Zoom 50` | Zoom al 50 % (anche `Zoom Full`, `Zoom Half`, `Zoom Min`, `Zoom 50%`). |
| `Focus 25` | Focus. |
| `Gobo 40` / `Gobo2 40` | Ruota gobo 1 / 2 (selezione; numero = percentuale del canale). |
| `GoboSpin 30` / `Gobo2Spin 30` | Rotazione / posizione della ruota gobo. |
| `Prism 100` | Prisma. |
| `Strobe 0` (`Shutter 0`) | Shutter / strobo. |
| `Zoom +10` / `Zoom -20` | Relativo al valore attuale (punti percentuali). |

Tutti i valori vanno da 0 a 100 e vengono memorizzati come i fader: `Store Cue` li riprende. Se un apparecchio non ha il canale (un dimmer puro non ha zoom) viene saltato e il feedback lo dice: `OK: Zoom 50 applied to 3 fixtures (Zoom not available on 1 of 3 fixtures)`. Se **nessuno** degli apparecchi selezionati ha il canale è un errore e non cambia nulla.

### Canali per numero: `CH` / `Channel`

| Comando | Effetto |
|---|---|
| `CH6 128` | Canale 6 **dell'apparecchio** (1 = primo canale) al valore DMX 128. |
| `Channel 6 128` | Lo stesso, scritto con uno spazio (funziona anche `CH 6 128`). |
| `CH6 50%` | Con `%`: percentuale invece del valore DMX (50 % = 128). |
| `CH6 +20` | Relativo: 20 passi DMX in più (`-20` in meno). |
| `CH6 Full` | 255 (anche `Half` = 50 %, `Min` = 0). |

Il numero di canale si riferisce all'**ordine nella modalità dell'apparecchio** (visibile nella scheda *DMX diretto* del programmer), non all'indirizzo DMX: `Fixture 5 Thru 8 CH6 255` imposta il 6° canale di ogni apparecchio selezionato ovunque sia patchato. Il valore è **0–255** come in DMX diretto.

### Canali per nome

Ogni nome di canale GDTF dell'apparecchio può essere usato direttamente come clausola (valore in **percentuale**):

```
Fixture 1 Frost 50        Iris 30        Cyan 100
Channel Frost1 50         CH Frost 50
```

Il nome può essere abbreviato finché resta non ambiguo (`Frost` per `Frost1`); sono integrati nomi brevi comuni (`Cyan`, `Magenta`, `Yellow` per i canali CMY, `Red`/`Green`/`Blue` per i canali RGB, `Intensity` per il dimmer). Il completamento automatico mostra quali nomi ha un apparecchio (capitolo 14).

I canali con un proprio attributo (dimmer, pan, tilt, zoom, focus, ruota gobo, prisma, shutter) vengono memorizzati come quell'attributo; tutti gli altri (frost, iride, ruota colori, canali fini …) come valori di canale grezzi. `Store Cue` riprende entrambi.

---

## 6. Variabili, effetti, manuale

Variabili (preset) ed effetti possono essere applicati alla **selezione attuale** – da soli o come clausola dopo una selezione come qualsiasi altro attributo.

| Comando | Effetto |
|---|---|
| `Variable "Warm White"` | Applica la variabile **e la collega**: gli apparecchi la seguono finché un valore, un effetto o un cue non prende l'attributo (cambiate la variabile e gli apparecchi cambiano con essa). Forme brevi: `Var`, `Preset`. |
| `Effect Rainbow` | Assegna l'effetto (la categoria deriva dall'effetto). Più apparecchi girano con uno sfasamento come nel menu a discesa. |
| `Effect Off` | Termina **tutti** gli effetti della selezione; `Effect Off color position` solo le categorie nominate. |
| `Manual` | Torna al **manuale**: rilascia il collegamento della variabile **e** l'effetto per tutte le categorie; gli ultimi valori di uscita restano. |
| `Manual color` | Solo quella categoria (`dimmer`, `color`, `position`, `zoom`, `focus`, `gobo`, più di una di seguito, oppure `all`). |

I nomi di variabili ed effetti sono univoci in OpenCue e senza distinzione tra maiuscole e minuscole. Con spazi o tra `"…"` o semplicemente uno dopo l'altro (`Variable warm white`). Un nome sconosciuto dà un errore con l'elenco di quelli esistenti. Il completamento automatico suggerisce variabili (con il loro tipo) ed effetti (con la loro categoria).

```
Fixture 1 Thru 4 Variable "Warm White" Variable Wide Effect Wave
Group Front Manual color
Effect Off
```

---

## 7. Comandi combinati

I comandi di selezione e di valore/attributo si possono combinare in **una sola riga** – equivalente a due comandi di seguito, ma più veloce da digitare:

```
Fixture 1 At 80
Fixture 1 Thru 5 At Full
Fixture 1 + 3 At 50
Fixture 1 Thru 10 Color Blue
Fixture 1 Pan 90 Tilt 45
Fixture 1 Thru 4 At 80 Zoom 30 Gobo 40 Frost 0
Group Front At 100 Color Warm
Fixture "Head 2" CH6 128
```

Più clausole di attributo possono seguirsi direttamente (`Fixture 1 At 80 Color Red` imposta dimmer E colore in un colpo). Se una clausola contiene un errore (errore di battitura nell'attributo, numero non valido, un canale che nessun apparecchio ha), **né** la selezione **né** alcun valore cambia.

---

## 8. Comandi concatenati (virgola o punto e virgola)

Più comandi completi si possono concatenare in **una** riga, separati da virgola o punto e virgola. Vengono eseguiti uno dopo l'altro:

```
Fixture 1 At 100, Fixture 2 At 50
Fixture 1 Color Red; Fixture 2 Color Blue; Fixture 3 At 0
```

Se una parte fallisce, le altre vengono comunque eseguite; il registro mostra tutti i risultati parziali in una riga separati da `|`. Virgole e punti e virgola **tra virgolette** (ad esempio in un nome di cue) vengono ignorati correttamente: `Label Cue 1 "Act 1, scene 2"` non viene diviso.

---

## 9. Clear: `Clear` contro `Clear Clear`

| Input | Effetto |
|---|---|
| `Clear` | Rilascia solo la selezione attuale. I valori programmati restano. |
| `Clear Clear` | **Reset completo:** riporta **tutti** gli apparecchi completamente indietro – dimmer, colore e pan/tilt (come impostato in *Impostazioni → Predefiniti → Clear Clear*: di default dimmer 0 %, colore bianco, pan/tilt 0°; gli apparecchi senza canale dimmer restano neri), zoom, focus, ruote gobo 1 e 2 con rotazione, prisma, strobo **e ogni altro canale dell'apparecchio** (frost, iride, ruota colori, velocità, canali fini …) a 0. Termina tutti gli effetti, svuota il programmer e rilascia la selezione. |
| `Clear` due volte **entro 1,0 secondo** | Come `Clear Clear` – digitare rapidamente `Clear` due volte attiva il reset completo. |
| `Clear` … (più di 1,0 s) … `Clear` | Due azioni indipendenti «rilascia selezione» – **nessun** reset. |

---

## 10. Liste di cue: selezionare per nome, Go, fader, gestire

I comandi dei cue agiscono sulla **lista di cue attiva** (menu a discesa nel pannello della lista di cue). Con `Cuelist` (equivalenti: `QList`, `Q-List`, `CL`, `List`, `Exec`) potete indirizzare qualsiasi lista **per nome** – senza distinzione tra maiuscole e minuscole; i nomi sono univoci in OpenCue, quindi è sempre chiaro. Come ovunque: **prima la categoria, poi il nome** – un semplice nome di lista (`Show Go`) non è un comando.

| Comando | Effetto |
|---|---|
| `Cuelist Show` | Rende «Show» la lista **attiva**. |
| `Cuelist "Cue List 1"` | Nome con spazi (anche senza virgolette, se non ambiguo: `Cuelist Cue List 1`). |
| `Cuelist 2` | La 2ª lista nell'ordine del menu a discesa (come `Exec 2`). |
| `Cuelist Show Go` | Avanza la lista «Show» di un passo – **senza** cambiare la lista attiva. |
| `QList Show Go` | Lo stesso con la categoria `QList`. |

### Creare, rinominare, duplicare, eliminare liste

| Comando | Effetto |
|---|---|
| `Cuelist New "Act 1"` | Crea una nuova lista (i nomi sono univoci; senza nome: `Cue List 1`, `Cue List 2` …). Se non ce n'era nessuna, diventa attiva. |
| `Cuelist Show Rename "Act 1"` | Rinomina (un nome già in uso viene rifiutato). |
| `Cuelist Show Duplicate` | Copia con tutti i cue, nuovi ID, nome `Show (copy)`; con un nome: `Duplicate "Backup"`. |
| `Cuelist Show Delete` | Elimina la lista (funziona anche `Delete Cuelist Show`) – **senza** conferma; una dissolvenza in corso termina. |

Una lista chiamata «New» si raggiunge tra virgolette: `Cuelist "New" Go`. Dopo il nome della lista può seguire qualsiasi comando di cue; si applica allora esattamente a quella lista, e il feedback la nomina tra parentesi (`OK: Go Cue 1 [Show]`).

### Riproduzione

| Comando | Effetto |
|---|---|
| `Go` | Cue successivo (alla fine della lista Go salta al primo cue, come il pulsante). |
| `Go Cue 3` / `Go 3` | Salta direttamente al cue 3 (dissolvenza morbida con il suo tempo di fade). |
| `Goto Cue 3` | Come `Go Cue 3`. |
| `Back` / `Go Back` | Cue precedente. |
| `Pause` / `Resume` | Mette in pausa / riprende la dissolvenza in corso. |
| `Stop` | Interrompe la dissolvenza (i valori restano); termina anche tutti gli effetti in esecuzione. |
| `Fader 50` | Il **fader** della lista (mix tra valore manuale e cue, come il fader executor) al 50 %. Anche `Fader Full`, `Fader +10`, `Fader At 30`. |
| `Off` / `Off Exec 1` / `Off Cuelist Show` | Reimposta lo stato di cue attivo della lista attiva / della 1ª / di quella nominata. (Gli executor non sono ancora oggetti separati; `Exec N` indica la N-esima lista. `Off` non fa sfumare gli ultimi valori DMX.) |

```
Cuelist Show Go                Go Cue 3
Cuelist "Encore" Goto Cue 1    QList "Encore" Fader 40
Cuelist Show Fader +10         Cuelist 2 Back
```

---

## 11. Gestire i cue

Tutti i comandi dei cue agiscono sulla **lista di cue attiva** – o, con un `Cuelist <name>` iniziale, sulla lista nominata.

| Comando | Effetto |
|---|---|
| `Store Cue 1` | Memorizza un nuovo cue con **ogni modifica rispetto al cue precedente** (vedi sotto) – anche un *Clear* che ha reso tutto buio. I valori che avete toccato esplicitamente sono sempre inclusi. |
| `Store Cue 1.5` | I numeri decimali permettono di inserire in seguito tra cue esistenti. «Prima» è allora il cue 1 (il cue con il numero immediatamente minore), qualunque cue sia attivo in questo momento. |
| `Store Cue 1.5 CueOnly` | Inserendo nel mezzo, il **cue successivo** mantiene il suo aspetto precedente: i valori che il nuovo cue modifica e che il cue successivo non imposta da sé vengono lì fissati con lo stato precedente. Senza `CueOnly` il cue successivo li eredita per tracking. |
| `Store Cue 4 "Intro"` | Con un nome (altrimenti il cue si chiama «Cue 4»). |
| `Store Cue 3 Merge` | Se il cue 3 esiste: vi entra solo ciò che differisce nell'immagine rispetto a **questo cue**, il resto resta. Senza `Merge`/`Overwrite`, `Store Cue 3` segnala un errore invece di creare un numero doppio. |
| `Store Cue 3 Overwrite` | Se il cue 3 esiste: il suo contenuto viene sostituito completamente dalle modifiche rispetto al cue precedente (nome, tempi, trigger restano). |
| `Store Cue 6 Absolute` | Il cue riproduce poi **esattamente lo stato che avete visto alla memorizzazione** (tutti gli apparecchi, tutti i canali). Funziona anche con un programmer vuoto: lo stato attuale viene memorizzato come istantanea. `Relative` (predefinito) riproduce solo le vostre modifiche. |
| `Update` | Porta nel cue **attivo** tutto ciò che nell'immagine differisce da quel cue (solo i canali modificati). Senza aggiunta vale il predefinito di *Impostazioni → Predefiniti → Nuovi cue → Update* («Chiedi ogni volta» agisce come tracking per il comando). |
| `Update Tracking` | I cue successivi che non impostano da sé questi valori li riprendono alla riproduzione. |
| `Update CueOnly` | Come `Update Tracking`, ma il cue successivo mantiene il suo aspetto precedente. |
| `Delete Cue 3` | Elimina il cue 3. Con un intervallo: `Delete Cue 3 Thru 5`. |
| `Move Cue 1 At 5` | Rinumera il cue 1 in 5 (la lista si riordina). Se il numero di destinazione esiste, viene segnalato un errore. |
| `Label Cue 1 "Intro"` / `Set Cue 1 Name "Intro"` | Rinomina il cue 1. |

**Come viene memorizzato un cue.** Un cue contiene solo ciò che modifica rispetto al cue precedente (tracking). Alla memorizzazione OpenCue cerca quindi il cue che verrebbe riprodotto **prima** del nuovo – quello con il numero immediatamente minore, anche per `1.5` in mezzo alla lista –, legge il suo stato e memorizza esattamente le differenze rispetto all'immagine che vedete ora. Ciò include un *Clear*: rende tutto buio ed è quindi una grande modifica. Se non c'è un cue prima (il primo della lista), riceve solo i valori che avete toccato esplicitamente. Se nulla è cambiato, `Store Cue` lo dice e non crea alcun cue (tranne con `Absolute`).

**La visualizzazione «modificato».** L'indicatore rosso nell'elenco apparecchi e i puntini sulle schede mostrano la stessa cosa: ciò che ora differisce dal **cue attivo** (oltre a ciò che avete operato a mano). Con più liste conta il cue attivo della lista **usata più di recente** (Go, Back, salto, selezione, memorizzazione). Mentre quella lista sfuma, la visualizzazione resta com'è; con un fader executor sotto il 100 % è vuota (l'uscita è mescolata di proposito). È solo una visualizzazione – ciò che viene memorizzato è sempre la modifica rispetto al cue precedente.

**Dopo la memorizzazione** il cue memorizzato è il **cue attivo** della lista (l'immagine corrisponde ad esso); il successivo `Go` avvia quindi il cue dopo di esso. Il programmer viene svuotato per gli apparecchi memorizzati (l'indicatore rosso scompare). I nuovi cue ricevono di default `Fade = 0.0 s` (commutazione netta).

**Relativo e assoluto:** ogni cue **memorizza sempre entrambi** nel file show: le *modifiche* (ciò che avete toccato) e lo *stato completo* di tutti gli apparecchi al momento della memorizzazione (dimmer, colore, posizione, gobo, zoom, focus e ogni altro canale; le variabili restano segnaposto). La **riproduzione** decide cosa succede al Go:

- **Relativo** (tracking, predefinito): vengono impostate solo le modifiche memorizzate, tutto il resto resta come lo ha lasciato il cue precedente.
- **Assoluto**: ogni apparecchio viene impostato esattamente sullo stato memorizzato – così il cue 6 appare esattamente come alla memorizzazione, anche se prima avete attraversato i cue 1-5. Anche gli effetti che il cue non ha terminano su tutti gli apparecchi.

Il predefinito per i nuovi cue si imposta in *Impostazioni → Predefiniti → Nuovi cue* (lì anche trigger, delay, tempo di fade, dissolvenza in entrata/uscita degli effetti, MIB e cosa fa *Update*). `Store Cue 6` senza aggiunta prende sempre questi predefiniti; ciò che indicate esplicitamente (`Absolute`, `Relative`) prevale. Nella finestra di memorizzazione potete cambiarlo per un singolo cue, più tardi nella finestra di modifica, con un doppio clic sulla colonna **Riproduzione** o con il comando `Cue 6 Mode Absolute` / `Cue 6 Mode Relative`. Poiché lo stato viene sempre memorizzato, ogni cue può essere commutato in qualsiasi momento. In *Predefiniti → Avvio del programma* impostate anche come si trova OpenCue dopo l'avvio (grand master dallo show o un valore fisso, blackout acceso/spento) e il livello del fader executor per le nuove liste. I cue più vecchi senza stato memorizzato si comportano, se assoluti, come il tracking della lista fino a quel cue.

**Gli effetti** sono sempre uno stato completo: un cue ricorda tutti gli effetti che erano in esecuzione quando è stato memorizzato. `Update` riprende anche questo – un effetto che avete fermato esce dal cue.

### Modificare i cue nella lista (mouse e touch)

- **Una singola cella:** fate doppio clic su una cella (nome, trigger, tempi, MIB, CMD …) per modificarla direttamente nella lista. La finestra di modifica (clic destro → *Modifica*) resta per tutto in una volta.
- **Più cue insieme:** trascinate un **rettangolo** sulle celle con il mouse (su touch: tenete premuto brevemente, poi trascinate). Vengono selezionate **solo le celle all'interno del rettangolo**, non l'intera riga. Un **doppio clic** su una cella selezionata modifica allora **tutte le celle selezionate di quella colonna** insieme – ad esempio impostare il tempo di fade di più cue a 1. Lo stesso vale per intere righe selezionate con `Ctrl`-clic o `Maiusc`-clic. Un semplice clic seleziona di nuovo un'intera riga. Il numero del cue si modifica sempre uno alla volta (i numeri sono univoci).
- **Trigger con simboli:** Go, Follow, Timecode, Audio, MIDI e Ora del giorno hanno ciascuno un simbolo – nella lista e come fila di pulsanti nella finestra di modifica (con una breve nota su quando il cue parte).
- **Spostare:** cambiate il numero del cue – il cue si sposta al suo nuovo posto.
- **Copiare:** selezionate dei cue → **Copia** (o clic destro → *Copia …*). Scegliete la lista e il numero della prima copia; le altre mantengono la spaziatura degli originali. I numeri già esistenti non vengono mai sovrascritti – allora non viene copiato nulla e OpenCue nomina i numeri occupati.
- **Annulla:** `Ctrl+Z` / `Ctrl+Y` annullano e ripetono le modifiche ai cue (vedi *Scorciatoie da tastiera*).

### Proprietà dei cue: `Cue <number> <property> <value>`

Tutto ciò che sta nella finestra di modifica (e nelle colonne della lista di cue) si può impostare da comando. Al posto di un numero funziona anche un intervallo: `Cue 1 Thru 5 Fade 2` modifica i cue da 1 a 5.

| Comando | Effetto |
|---|---|
| `Cue 1 Fade 3` / `Cue 1 Delay 1.5` | Tempi generali (dimmer) in secondi. |
| `Cue 1 Color Fade 2` / `Color Delay` | Tempo proprio per il colore (funziona anche `Colour`). |
| `Cue 1 Pos Fade 4` / `Pos Delay` | Tempo proprio per la posizione (funziona anche `Position Fade`). |
| `Cue 1 Beam Fade 0` / `Beam Delay` | Tempo proprio per il fascio (gobo, prisma, strobo, focus …). |
| `Cue 1 Zoom Fade 2` / `Zoom Delay 1` | Tempo proprio per lo zoom. |
| `Cue 1 Color Fade -` | Un `-` (o `default`) riporta il gruppo al tempo generale. |
| `Cue 1 FX In 2` / `FX Out 1` | Dissolvenza degli effetti in entrata/uscita in secondi (funzionano anche `Effect In` / `Effect Out`). |
| `Cue 1 Trigger Go` / `Follow` | Trigger del cue. |
| `Cue 1 Trigger Timecode 00:01:30` | Trigger dal timecode globale (ora come con `Timecode At`). |
| `Cue 2 Trigger Audio Beat 4` | Trigger dalla musica: scatta a ogni 4° battito una volta che è il cue successivo (il pannello Audio deve essere in esecuzione). Sorgenti: `Beat`, `Kick`, `Snare`, `Hat` (il numero = ogni n-esimo, predefinito 1) e `Level`, `Bass`, `Mid`, `High`, `B1` … `B8` (il numero = soglia in %, predefinita 70). |
| `Cue 2 Trigger Audio Kick` | Scatta al prossimo colpo di cassa. |
| `Cue 2 Trigger Audio Bass 80` | Scatta quando i bassi raggiungono l'80 %. |
| `Cue 3 Trigger Midi Note 60` | Trigger da un segnale MIDI: scatta quando questo tasto viene premuto, una volta che il cue è il cue successivo di una lista in esecuzione. `Note` prende un numero (0–127) o un nome di nota (`Note C4`), `CC <number> [threshold]` scatta quando un controller sale alla soglia (predefinita 64), `PC <number>` a un cambio di programma. Aggiungete `Ch <1-16>` per un solo canale (predefinito: qualsiasi). Esempi: `Cue 3 Trigger Midi Note C4 Ch 2`, `Cue 4 Trigger Midi CC 20 100`, `Cue 5 Trigger Midi PC 3`. Il MIDI deve essere attivo (guida *MIDI*, sezione 5c). |
| `Cue 3 Trigger Clock 19:30 Mon-Fri` | Trigger dall'**orologio**: una volta che il cue è il cue successivo di una lista in esecuzione aspetta questa ora del giorno (e questi giorni: `Mon-Fri`, `Sat,Sun`, `weekdays`, `weekend`, `daily` – senza giorni: ogni giorno; i secondi sono ammessi: `19:30:15`). Vedi la guida *Pianificazione, ora del giorno e OSC*. (`Trigger Time` resta il trigger timecode.) |
| `Cue 1 MIB Auto` (`Off` / `On`) | Move In Black. |
| `Cue 1 Mode Absolute` (`Relative`) | Riproduzione: esattamente lo stato memorizzato o solo le modifiche (vedi sopra). |
| `Cue 1 Cmd "Fixture 1 At 0; Go"` | Comando/i che il cue esegue quando scatta (capitolo 12). |
| `Cue 1 Name "Intro"` | Nome. |

---

## 12. CMD: collegare comandi a un cue

Ogni cue ha un campo di testo facoltativo **CMD** (clic destro → Modifica → sezione «MIB e CMD», doppio clic nella colonna della lista di cue, o con il comando `Cue 3 Cmd "…"`). Se contiene un comando, OpenCue lo esegue **automaticamente** quando il cue viene attivato (da `Go`, da un `Follow` automatico o dal menu contestuale «Dissolvi qui») – prima che inizi la vera e propria dissolvenza.

Più comandi si separano con **virgola o punto e virgola**:

```
Fixture 1 At 0
Fixture 3 Thru 6 Color Blue
Fixture 1 At 0; Fixture 2 Zoom 30; Cuelist Encore Go
```

Il risultato compare nella stessa cronologia comandi condivisa di un comando digitato, così resta visibile che un cue ha attivato un'azione. Il campo accetta fino a 200 caratteri. CMD può contenere **qualsiasi** comando di questo riferimento, anche concatenato e combinato – un cue può avviare un'altra lista con `Cuelist Encore Go`. Le chiamate ricorsive `Go Cue` sono possibili, ma OpenCue non rileva cicli infiniti tra cue CMD concatenati.

---

## 13. Feedback nel registro

Ogni comando eseguito produce una riga nell'area del registro del pannello, con un'indicazione oraria:

```
[20:45:01] OpenCue> Fixture 1 Thru 10
           OK: 10 fixtures selected
[20:45:07] OpenCue> At 80
           OK: At 80 applied to 10 fixtures
[20:45:12] OpenCue> Store Cue 1
           OK: Cue 1 stored
```

I comandi errati sono contrassegnati in **rosso**:

```
[20:46:40] OpenCue> At 80
           At: no fixtures selected
[20:46:55] OpenCue> Go Cue 99
           Cue 99 not found
[20:47:02] OpenCue> Fixture 1 Colr Red
           Unknown attribute: Colr
```

I comandi concatenati danno **una** riga con tutti i risultati parziali separati da `|`. Il registro è identico su **tutti** i dispositivi connessi – ogni comando, ovunque sia stato digitato (o eseguito dal CMD di un cue), compare in ogni pannello riga di comando aperto. Il testo del registro si può selezionare e copiare.

---

## 14. Tastiera e completamento automatico

| Tasto | Effetto |
|---|---|
| `Invio` | Esegue il comando e svuota l'input. |
| `Freccia su` | Comando precedente (più vecchio). |
| `Freccia giù` | Comando successivo (più recente), oppure torna alla bozza che avevate iniziato. |
| `Tab` | Prende il primo suggerimento; ogni `Tab` successivo passa al successivo. |
| `Maiusc` + `Tab` | Come `Tab`, all'indietro. |
| `Esc` | Chiude l'elenco dei suggerimenti. |

**Completamento automatico:** mentre scrivete (e quando fate clic nel campo) sopra l'input compare un elenco di continuazioni adatte. All'inizio di una riga mostra **solo le categorie** (`Fixture`, `Group`, `Cuelist`, `Cue`, `Go` …) – nomi e valori vengono dopo. L'elenco conosce lo **stato attuale**, non solo le parole di comando:

- dopo `Fixture ` i numeri (con il nome del dispositivo) e i nomi,
- dopo `Group ` i gruppi; dopo `Cuelist ` le liste di cue (i nomi con spazi vengono messi automaticamente tra `"…"`),
- dopo una selezione di apparecchi gli attributi ed esattamente i **canali che questi apparecchi hanno** (`Frost1`, `Iris`, `ColorSub_C` … con il numero di canale come suggerimento),
- dopo `Go `, `Cue `, `Delete Cue ` i cue della lista (nominata) con i loro nomi, poi le proprietà (`Fade`, `Color Fade`, `FX In`, `Trigger` …),
- dopo `Color ` i nomi dei colori, dopo `Zoom ` valori (`Full`, `Half`, `Min`),
- dopo `Variable ` / `Effect ` le variabili (con tipo) e gli effetti (con categoria); dopo `Manual ` le categorie; dopo `Store ` / `Delete ` / `Label ` `Cue` e `Group`; dopo `Cuelist ` prima `New`; dopo `Blackout ` `On` / `Off`.

Le righe in corsivo sono **suggerimenti** sul valore atteso (`<0-100> | +<n> | -<n> (%)`, `<0-255> (DMX) | <0-100>%`) e non si possono inserire. L'elenco si riferisce sempre all'**ultimo comando parziale** (dopo l'ultima virgola/punto e virgola). Anche un clic su una voce la inserisce. L'intera grammatica sta nel server; l'interfaccia mostra solo ciò che il server suggerisce, perciò i suggerimenti non differiscono mai dal vero parser.

Un piccolo **interruttore** all'estrema destra della riga di input attiva e disattiva i suggerimenti (memorizzato nella configurazione dell'applicazione, vale per tutti i dispositivi).

In *Proprietà pannello → Impostazioni del modulo* potete anche cambiare i colori del testo, del successo e dell'errore del registro.

---

## 15. Promemoria

```
Fixture 1                       Fixture 1 Thru 10          Fixture 1 + 3
Fixture "Head 2"                Group 1                    Group Front

At 80          At Full          At At          Full        At 0     At +10     At -10
Master 80      Master Full      Master -10

Color Red      Color #FF8000    Color 255 128 0            RGB 255 0 0
Pan 180   Tilt -45   Pan 50%    Pan +10%                   Pan +15

Zoom 50   Focus 25   Gobo 40   Gobo2 40   GoboSpin 30   Prism 100   Strobe 0
CH6 128   CH6 50%    Channel 6 +20   Frost 50   Channel Frost1 50   Cyan 100

Fixture 1 At 80 Color Red Zoom 30          Group Front At 100, Fixture 5 At 0

Blackout       Blackout On       Blackout Off

Variable "Warm White"   Effect Wave   Effect Off   Effect Off color   Manual   Manual color

Store Group "Front"   Store Group "Front" Merge   Delete Group Front   Label Group Front "New"

Clear          Clear Clear

Go    Back    Go Cue 3    Goto Cue 3    Pause    Resume    Stop    Fader 50
Cuelist New "Act 1"    Cuelist Show Rename "Act 2"    Cuelist Show Duplicate    Cuelist Show Delete
Cuelist Show    Cuelist Show Go    QList "Encore" Fader 40    Cuelist 2 Back    Off    Off Cuelist Show

Store Cue 1    Store Cue 1.5    Store Cue 4 "Intro"    Store Cue 3 Merge    Update    Update CueOnly
Delete Cue 3   Delete Cue 3 Thru 5    Move Cue 1 At 5    Label Cue 1 "Intro"
Cue 1 Fade 3   Cue 1 Delay 1.5   Cue 1 Thru 5 Fade 2   Cue 1 Color Fade 2   Cue 1 Pos Delay 1
Cue 1 FX In 2  Cue 1 Trigger Follow   Cue 1 Trigger Timecode 00:01:30   Cue 3 Trigger Midi Note 60   Cue 1 MIB Auto   Cue 1 Cmd "Fixture 1 At 0; Go"

Timecode Play    Timecode At 4.3    Timecode Stop
```
