# Audio: luci che reagiscono alla musica

OpenCue può **ascoltare** la musica e far reagire le luci: più luminose con i bassi, un flash a ogni cassa, colori che cambiano a tempo, un chase che corre a ritmo. L'analisi gira in diretta sulla console, non richiede internet e impegna solo pochi punti percentuali di un core del processore.

---

## 1. L'idea in un minuto

- Il **pannello Audio** prende una sorgente sonora e la analizza: volume, uno spettro, i colpi di **cassa, rullante e hi-hat**, il **tempo (BPM)** e la posizione all'interno del battito.
- I risultati sono disponibili agli effetti come **variabili** (`a_level`, `a_bass`, `a_kick`, `a_beat_phase` ...). Un **effetto audio** è un normale script di effetto che le legge. Funziona come ogni altro effetto: assegnatelo agli apparecchi nel programmer, salvatelo nei cue, fatelo entrare e uscire in dissolvenza.
- Con il programma sono forniti 33 effetti audio già pronti. Portano il tag **Audio** (assegnato automaticamente non appena un effetto legge valori audio) – scegliete il tag nella finestra del tipo di effetto per elencarli.
- Senza una sorgente attiva tutti i valori audio sono `0`: un effetto audio resta semplicemente buio o al suo valore di riposo.
- I cue possono partire anche **sulla musica**: il trigger di cue *Audio* (sezione 8).
- I pulsanti, i fader e gli interruttori propri della console possono seguire la musica (sezione 9), e l'API REST può leggere e controllare l'audio (sezione 10).

---

## 2. Avvio rapido

1. Aggiungete il pannello: **Modifica → Aggiungi pannello…** → categoria *Media e tempo* → **Audio**.
2. Scegliete **Battito demo** nell'elenco delle sorgenti e premete **Avvia**. Viene analizzato un loop di batteria a 120 BPM – vedete lo spettro, le spie *Cassa / Rullante / Hi-hat / Battito* lampeggiare e compare il tempo.
3. Nel programmer selezionate alcuni apparecchi, aprite la scheda **Effetti** e fate clic su **Aggiungi effetto**, scegliete il tipo di effetto **Kick Flash** (o *Bass Dimmer*, *Beat Chase* ... – suggerimento: filtrate per il tag *Audio*) e createlo. Gli apparecchi ora lampeggiano con il battito demo.
4. Passate la sorgente alla vostra musica reale (sezione successiva).

Le installazioni esistenti ottengono i nuovi effetti tramite il **Gestore file** (elenco *Effetti*) con **Ripristina effetti predefiniti**. Questo crea solo i file *mancanti* e non sovrascrive mai: se avete già ripristinato una versione più vecchia, eliminate prima i vecchi file `audio_*.fx` nel gestore file, poi ripristinate di nuovo.

---

## 3. Scegliere la sorgente

L'elenco mostra tutto ciò che Windows conosce:

| Gruppo | Cos'è | Uso tipico |
|---|---|---|
| **Audio di sistema** | Ciò che questo computer riproduce su un altoparlante o sulle cuffie («loopback»). Una voce per dispositivo di uscita. | Musica dallo stesso computer (software DJ, Spotify, browser). Nessun cavo, nessun microfono. |
| **Ingressi** | Microfoni, prese line-in e interfacce audio USB. | Musica da un mixer o da un telefono: collegate il cavo all'**ingresso linea** o all'interfaccia. Un portatile con una sola presa cuffie/microfono combinata la tratta come *microfono*: il segnale è più debole, aumentate il **guadagno di ingresso**. Funziona anche un microfono nella sala, ma la musica deve essere forte e chiara. |
| **Prova** | Il battito demo. | Provare gli effetti senza musica. |

Le voci contrassegnate *(predefinito)* sono quelle che Windows usa di default. **Cerca di nuovo** (il pulsante con le frecce) cerca di nuovo i dispositivi dopo aver collegato qualcosa.

Premete **Avvia**. La sorgente resta aperta finché non premete **Interrompi**; il successivo avvio del programma la riapre da sola. Se una sorgente non si può aprire, il pannello dice perché (usata da un altro programma, bloccata nelle impostazioni di privacy di Windows *Microfono*, scollegata).

---

## 4. Cosa mostra il pannello

- **Spettro:** 32 barre da 30 Hz a 16 kHz (i toni bassi a sinistra). La cornice si illumina a ogni battito.
- **Spie:** *Cassa*, *Rullante*, *Hi-hat* si accendono a ogni colpo; *Battito* a ogni battito del tempo.
- **Livello** con un indicatore *Sovraccarico*: si accende quando il segnale va in clipping (troppo forte all'ingresso; abbassate il volume o il guadagno).
- **Tempo:** i BPM in grandi cifre, un LED del battito, una barra che mostra la posizione nel battito e una barra sottile per l'affidabilità del rilevamento.

---

## 5. Tempo: automatico, battuto o fisso

- **Automatico** rileva il tempo dalla musica (70 - 180 BPM). Servono alcuni secondi e un ritmo costante; segue i cambi di tempo.
- **Tap:** battete sul pulsante a tempo con la musica (anche il comando `Tap`). Dal secondo colpo il tempo viene impostato dai vostri colpi e il battito parte esattamente sul colpo. Il tempo è allora *Manuale*.
- **÷2 / ×2:** quando il rilevamento ha trovato la metà o il doppio della velocità (tipico per musica molto lenta o molto veloce).
- **Manuale:** il tempo è fisso; digitatelo nel campo. Con *Tempo manuale: il battito segue la musica* la posizione del battito si adegua ancora dolcemente ai colpi. Senza alcuna musica un tempo fisso gira come un **metronomo** – gli effetti con `a_beat_phase` continuano a girare a tempo.
- **Automatico** torna al rilevamento.

Comandi: `Tap`, `BPM 128`, `BPM Auto`, `BPM Half`, `BPM Double`, `Audio Start`, `Audio Stop`, `Audio Demo`, `Audio Status`.

---

## 6. Impostazioni

| Impostazione | Cosa fa |
|---|---|
| **Guadagno di ingresso** | Amplifica (×0,1 a ×10) un segnale debole, ad es. un microfono. |
| **Guadagno automatico** | L'analisi si misura sulle parti più forti degli ultimi secondi, così un brano silenzioso funziona come uno forte. Disattivatelo per una scala fissa (allora il guadagno agisce direttamente). |
| **Sensibilità al battito** | Più alta: contano anche i colpi leggeri (rischio: falsi colpi). Più bassa: contano solo i colpi netti. |
| **Levigatura** | Quanto lentamente i livelli e le bande ricadono. |
| **Offset di sincronizzazione** | da −100 a +200 ms. Positivo: le luci reagiscono **prima** – usatelo quando le luci o gli altoparlanti sono in ritardo. |

Le impostazioni appartengono alla console (non a uno show né a un pannello) e vengono salvate automaticamente. Ogni dispositivo con un pannello Audio mostra e controlla la stessa sorgente.

---

## 7. Gli effetti audio già pronti

| Effetto | Categoria | Cosa fa |
|---|---|---|
| Band Bars | Dimmer | Ogni apparecchio mostra una banda di frequenza: il primo i bassi, l'ultimo gli alti (si ripete con più di 8 apparecchi). |
| Bass Dimmer | Dimmer | La luminosità segue i bassi della musica. |
| Beat Chase | Dimmer | Un chase che avanza a ogni battito (o a ogni n-esimo). |
| Beat Pulse | Dimmer | La luminosità pulsa a tempo con la musica: luminosa sul battito, poi si spegne dolcemente. |
| Beat Strobe | Dimmer | Strobo a tempo con la musica: più lampi per battito, agganciati al tempo. |
| Beat Toggle | Dimmer | Commuta tra due gruppi a ogni battito (o a ogni n-esimo), netto o in dissolvenza incrociata (morbido). |
| Hi-Hat Sparkle | Dimmer | A ogni colpo di hi-hat scintillano apparecchi scelti a caso. |
| Kick Chase | Dimmer | Un chase che avanza a ogni colpo di cassa (invece che al battito). |
| Kick Flash | Dimmer | Ogni colpo di cassa fa lampeggiare le luci, che poi si spengono. |
| Level Dimmer | Dimmer | La luminosità segue il volume complessivo. |
| Snare Flash | Dimmer | Ogni colpo di rullante (o battito di mani) fa lampeggiare le luci, che poi si spengono. |
| Beat Color | Colore | Il colore cambia a ogni battito (o a ogni n-esimo) ed è più luminoso sul battito. |
| Beat Color Chase | Colore | Una luce colorata (A) corre su un colore di fondo (B), un passo per battito (o per n-esimo). |
| Beat Color Fade | Colore | Dissolve tra due colori a tempo con la musica. |
| Beat Color Strobe | Colore | Uno strobo colorato a tempo con la musica: più lampi per battito, alternando tra il colore A e B. |
| Color Blend | Colore | Sfuma dal colore A (piano) al colore B (forte). |
| Color Hit | Colore | Il colore di base lampeggia nel colore del flash a ogni colpo del tamburo scelto. |
| Hi-Hat Color Sparkle | Colore | A ogni colpo di hi-hat apparecchi scelti a caso lampeggiano in un colore casuale (entro la gamma di colori). |
| Hue Drift | Colore | I colori scorrono lungo la gamma di colori, un ciclo completo dura `beats` battiti. |
| Kick Color Flash | Colore | Il colore di base lampeggia nel colore del flash a ogni colpo di cassa. |
| Spectrum Color | Colore | Il colore si mescola dalla musica: bassi = rosso, medi = verde, alti = blu. |
| Spectrum Hue | Colore | Il colore segue il suono: la musica ricca di bassi mostra l'inizio della gamma di colori, i suoni brillanti la fine. |
| Bass Tilt | Posizione | Il tilt segue i bassi: piano = giù, bassi forti = su (attorno alla posizione di base). |
| Beat Circle | Posizione | Le teste descrivono un cerchio a tempo con la musica: un giro dura `beats` battiti. |
| Beat Fan | Posizione | Gli apparecchi si aprono a ventaglio e si richiudono a tempo con la musica. |
| Kick Tilt Punch | Posizione | A ogni colpo di cassa le teste danno uno scatto in tilt e tornano alla posizione di base. |
| Level Spread | Posizione | Più la musica è forte, più gli apparecchi si aprono a ventaglio (simmetricamente attorno alla posizione di base). |
| Pan/Tilt Sway | Posizione | Le teste si muovono a tempo con la musica. |
| Snare Pan Snap | Posizione | A ogni colpo di rullante ogni testa scatta alla successiva di quattro posizioni di pan. |
| Beat Zoom Pulse | Zoom | Lo zoom pulsa a ogni battito: alto sul battito, poi ricade in basso. |
| Kick Zoom Punch | Zoom | Lo zoom scatta da basso ad alto a ogni colpo di cassa e ricade. |
| Bass Focus | Focus | Il fuoco segue i bassi della musica. |
| Beat Gobo Change | Gobo | Il gobo cambia a ogni battito (o a ogni n-esimo). |

Quasi ogni effetto ha opzioni per **attivare/disattivare le animazioni** e aggiungere uno **strobo**: *strobe* (lampi al secondo, 0 = spento), *mode* (ad esempio tutti insieme / pari-dispari alternati / casuale), *direction* (chase avanti, indietro, avanti e indietro, casuale), *every* (commutare a ogni n-esimo battito), *soft* (commutazione netta o dissolvenza incrociata). Sono effetti normali: salvateli nei cue, variateli, copiateli.

---

## 8. Trigger di cue: Audio

Oltre a *Go*, *Follow*, *Timecode* e *MIDI* (guida *MIDI*) un cue può avere il trigger **Audio**: scatta allora da solo **sulla musica**. Nella finestra del cue scegliete il trigger *Audio*, selezionate **una sorgente** e, se serve, un valore – nella lista dei cue potete anche digitarlo (`audio kick`, `audio beat 4`, `audio bass 70`) o usare il comando `Cue 2 Trigger Audio Beat 4`.

| Sorgente | Valore | Il cue scatta … |
|---|---|---|
| **Battito (tempo)**, **Cassa**, **Rullante**, **Hi-hat** | ogni n-esimo (da 1 a 64, predefinito 1) | … a ogni n-esimo battito / colpo. |
| **Livello generale**, **Bassi**, **Medi**, **Alti** o una delle **otto bande** (con il loro intervallo in Hz nell'elenco) | soglia in % (predefinita 70) | … quando questa parte del suono **raggiunge** la soglia salendo dal basso. |

Come funziona:
- Il cue scatta quando è il **cue successivo** di una lista in esecuzione: avviate prima la lista con *Go*, poi il successivo cue audio aspetta il suo evento. Dopo che è scattato, il cue seguente (se ha anch'esso il trigger *Audio*) aspetta a sua volta – così potete concatenare un'intera sequenza alla musica.
- Il contatore (*ogni n-esimo*) riparte da 0 ogni volta che diventa attivo un nuovo cue.
- Con una soglia il cue scatta una volta quando il livello la raggiunge; viene riarmato solo dopo che il livello è sceso nettamente sotto (circa l'80 % della soglia). Se il livello è già sopra quando il cue diventa il successivo, aspetta la salita seguente.
- Dopo un trigger c'è una breve pausa (0,25 s), così un colpo non avvia mai due cue.
- Il **pannello Audio deve essere in esecuzione** (una sorgente avviata); senza suono non scatta nulla. Il trigger funziona per ogni lista di cue indipendentemente.

---

## 9. Pulsanti, fader e interruttori che reagiscono alla musica

I pannelli **Pulsante**, **Fader** e **Interruttore** propri della console possono usare la musica come *segnale* – in *Segue lo stato di* (un fader si muove con la musica, un interruttore commuta con il segnale) e nelle **condizioni delle regole** (colore, testo o comando quando …). I segnali sono nel gruppo **Audio**:

| Segnale | Significato |
|---|---|
| **Segnale audio presente** | attivo finché una sorgente è aperta e qualcosa viene riprodotto |
| **Livello generale**, **bassi**, **medi**, **alti** | 0–100 % |
| **Cassa**, **rullante**, **hi-hat**, **battito** (impulso) | saltano al 100 % a ogni colpo e si spengono |
| **Tempo (BPM)** | il tempo rilevato o impostato |

Esempi: un fader che segue i bassi come misuratore di livello; un pulsante che si illumina di rosso quando il tempo è tra 120 e 130 BPM; un interruttore che mostra se arriva musica. La sorgente audio gira sulla console; a un pannello basta essere sullo schermo di un dispositivo qualsiasi – le misure vengono inviate a un dispositivo esattamente finché un tale pannello (o il pannello *Audio*) vi è aperto.

## 10. L'audio tramite l'API

L'API REST può leggere l'analisi (`GET /api/v1/audio`), aprire e chiudere la sorgente, modificare le impostazioni e battere il tempo (`PUT /api/v1/audio`, `POST /api/v1/audio/tap`, permesso *Audio*), e il **flusso di eventi in diretta** (`GET /api/v1/events?events=audio,beat,hit`) segnala la sorgente, ogni battito e ogni colpo di tamburo nel momento in cui accadono. Vedi la guida *API REST*.

## 11. Scrivere un proprio effetto audio

Aprite lo **Studio effetti**, create un effetto e leggete le variabili audio – vedi la guida *Studio effetti*, sezione *Variabili audio*. Un primo esempio:

```
#NAME My Flash
#CATEGORY dimmer
#RATE 40
#VAR peak Slider 100 0 100 1

loop() {
  dimmer = peak * a_kick;
}
```

L'anteprima dello studio riproduce un battito di esempio (120 BPM) così vedete subito come si comporta la curva.

---

## 12. Quando qualcosa non funziona

| Problema | Controllare |
|---|---|
| La sorgente non si può aprire | Un altro programma la usa in modo esclusivo; il microfono è bloccato nelle impostazioni di privacy di Windows (*Impostazioni → Privacy → Microfono*); il dispositivo è scollegato. |
| Il pannello non mostra nulla / tutto piatto | La sorgente è *avviata*? Il misuratore di volume di Windows si muove? Aumentate il **guadagno di ingresso**. Per *Audio di sistema* il programma deve davvero riprodurre su quel dispositivo di uscita. |
| *Sovraccarico* è acceso | Il segnale è troppo forte: abbassate il volume alla sorgente o il guadagno di ingresso. |
| I BPM saltano o sono la metà / il doppio | Premete **÷2 / ×2**, battete il tempo o fissatelo con *Manuale*. La musica senza ritmo costante (classica, parlato) non ha un tempo rilevabile. |
| Le luci reagiscono troppo tardi | Usate l'**Offset di sincronizzazione** (valori positivi). |
| Un effetto audio resta buio | Nessuna sorgente attiva, o la sensibilità è troppo bassa per la musica; alzate il cursore *gain* dell'effetto. |
