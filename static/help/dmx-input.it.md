# Ingresso DMX (ricevere Art-Net e sACN)

OpenCue non può solo inviare DMX ma anche **riceverlo dalla rete** – da una consolle luci, da un programma (per esempio un visualizzatore o un controller di show) o da un dispositivo. I valori ricevuti possono essere **inoltrati e miscelati** nell'uscita o usati come **trigger**.

Aprilo con **Controlli → Ingresso DMX…** (si può modificare anche da un tablet).

---

## 1. Attivarlo

- Attiva **Ricevi DMX** (spento è il valore predefinito – il DMX non ha password, chiunque nella rete può inviare).
- **Protocolli:** Art-Net (UDP 6454) e/o sACN / E1.31 (UDP 5568, multicast). Universo Art-Net = *indirizzo di porta* (esattamente come lo invia OpenCue: universo 1 = indirizzo di porta 1).
- **Mittenti consentiti:** vuoto = chiunque; altrimenti indirizzi IP o i loro inizi (p. es. `192.168.1.`).
- **Scheda di rete:** serve solo se il computer ne ha diverse e l'ingresso deve ascoltare su una precisa.
- **Sorgente scomparsa dopo:** tanto tempo senza pacchetti, poi OpenCue rilascia i valori della sorgente (sACN: subito con “stream terminato”).

**Sorgenti viste** mostra dal vivo tutto ciò che viene inviato: protocollo, universo, mittente, pacchetti al secondo e quanti canali non sono a zero. **Vedi** mostra i 512 canali come griglia; **Inoltra** crea subito un'assegnazione.

---

## 2. Inoltrare / miscelare (sorgente → uscita)

Un'**assegnazione** miscela un *universo di ingresso* in un *universo di uscita* di OpenCue:

| Modalità | Significato |
|---|---|
| **Vince il più alto** (HTP) | Per canale conta il valore maggiore tra OpenCue e l'ingresso. Il valore predefinito, sicuro per miscelare. |
| **Sostituisci** | Conta l'ingresso finché la sorgente c'è (zeri inclusi). Eventualmente solo per un intervallo di canali. |

- Più sorgenti per lo stesso universo: **vince il più alto**. Con sACN contano solo le sorgenti con la **priorità** più alta.
- Se l'universo di uscita **non ha apparecchi**, viene comunque emesso – ne risulta un **inoltro puro** (p. es. Art-Net → sACN o → un adattatore USB).
- L'ingresso sta **sopra a tutto** (programmer, cue, effetti). I valori dentro OpenCue restano invariati; la miscelazione avviene solo nell'**uscita**.
- I pacchetti propri vengono riconosciuti e ignorati – un inoltro non crea un anello di retroazione.
- Gira nel **processo di uscita DMX**: l'inoltro continua invariato anche se il programma principale si blocca. Se quel processo fallisce e l'uscita gira nel programma principale come ripiego, trigger e visualizzazione continuano a funzionare ma la miscelazione no (la finestra lo dice).

---

## 3. Trigger (canale → comando)

Un **trigger** esegue un comando della riga di comando quando un canale cambia:

- **Pulsante:** quando il valore supera la **soglia** viene eseguito il primo comando (p. es. `Go`); quando scende di nuovo sotto, il secondo (facoltativo, p. es. `Blackout Off`).
- **Fader:** ogni nuovo valore viene eseguito come comando; `{value}` rappresenta il valore scalato all'**intervallo** (predefinito 0–100), p. es. `Master {value}`.
- **Impara:** clicca su **Impara** e muovi un canale sulla consolle – protocollo, universo e canale vengono compilati.
- Il primo valore visto viene solo memorizzato, non si attiva nulla (nessun salto alla connessione). I comandi dei fader vengono eseguiti al massimo 20 volte al secondo; l'ultimo valore arriva sempre.

Esempi: canale 1 = `Go` (pulsante), canale 2 = `Blackout` (pulsante), canale 3 = `Master {value}` (fader), canale 10 = `Goto Cue 5`.

**Ultimi trigger** mostra cosa è stato attivato.

---

## 4. Da sapere

- L'ingresso appartiene alla **configurazione dell'app** (non allo show) e vale per questo computer.
- Perché una consolle raggiunga OpenCue deve inviare all'indirizzo IP del computer o in broadcast; il firewall di Windows deve consentire UDP 6454 / 5568 per OpenCue – la finestra mostra se la regola esiste e la crea con un clic (Windows chiede il permesso sul computer principale).
- **Annunciarsi come dispositivo Art-Net:** OpenCue risponde alla ricerca (ArtPoll) degli altri dispositivi e compare nel loro elenco di dispositivi Art-Net – una consolle può sceglierlo come destinazione senza digitare l'indirizzo IP.
- Una panoramica di tutti gli ingressi e le uscite è in **Impostazioni → Panoramica**.
