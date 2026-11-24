# Simulazione 3D

Il pannello **Simulazione 3D** mostra il palco in 3D; ogni apparecchio si accende in tempo reale secondo i suoi valori DMX. Aggiungilo con **Aggiungi pannello**. Questa guida spiega i pulsanti, le impostazioni in **Stanza e luce** e cosa controllare quando l'immagine non è quella attesa (non tutti gli apparecchi illuminano il palco, mancano coni o ombre, è lento).

---

## 1. Il pannello

- Tre modalità in alto a sinistra: **Visualizza**, **Costruisci** (oggetti e modelli 3D) e **Apparecchi** (posizionare gli apparecchi, puntare le teste mobili).
- Pulsanti in alto a destra: visore VR (solo se il browser ne offre uno), condividere la camera tra dispositivi, **Stanza e luce** (ingranaggio), **Ferma / Avvia la simulazione 3D**, **Blackout** (lampadina), **Reimposta vista**, **Schermo intero**.
- In basso a sinistra: il pulsante della qualità mostra frequenza e risoluzione; un clic passa da Automatica → Bassa → Media → Alta.

## 2. Fermare e avviare la simulazione 3D

Il pulsante di pausa ferma completamente la simulazione: scena, contesto grafico e modelli vengono rimossi, nulla viene calcolato o disegnato e il resto di OpenCue non rallenta. Il pannello resta nel layout e mostra un pulsante di riproduzione; **Avvia** ricostruisce tutto. La scelta viene ricordata **per dispositivo** e vale per tutti i pannelli 3D di quel dispositivo. Se un pannello 3D è vuoto e indica che è fermo, premi il pulsante di riproduzione.

Dopo l'avvio, dopo il caricamento di uno show grande o dopo aver cambiato i limiti di luce, il pannello mostra per un attimo *Preparazione dell'illuminazione …*: la scheda grafica prepara i suoi programmi in background e il resto di OpenCue resta utilizzabile.

## 3. Stanza e luce

Apri la finestra con l'ingranaggio. Ha due parti.

**Per tutti i dispositivi** – vale per ogni dispositivo collegato allo show (console, iPad, accesso remoto): *Illuminazione* (luce di lavoro in modalità Costruisci, luce di sala), *Luce riflessa* (luce ambiente, riflessione delle pareti, irradiazione di colore), *Immagine* (riflessione degli oggetti, esposizione, **Foschia**) e *Griglia e assi nella vista*. **Foschia a 0 %** disattiva completamente la foschia: niente coni di luce e niente calcolo della foschia – è ciò che fa risparmiare più prestazioni.

**Solo questo dispositivo** – prestazioni e qualità. Valgono solo su questo dispositivo, ogni dispositivo può sceglierle diversamente:

| Impostazione | Significato |
|---|---|
| **Qualità** | Automatica (si adatta alla frequenza), Bassa, Media, Alta: risoluzione e dettaglio delle ombre. |
| **Luci massime** | Quanti apparecchi ricevono contemporaneamente una propria luce sulle superfici (predefinito 32). Vincono i più luminosi. |
| **Ombre massime** | Quante di queste luci proiettano ombre. 0 = quante ne consente la scheda grafica. |
| **Riflessi speculari massimi** | Riflessi su metallo e specchi. |
| **Max. coni di luce semplici** | Quanti coni di luce semplici vengono disegnati. 0 = tutti. Con un limite ogni apparecchio mantiene prima il suo primo cono, poi i più luminosi. |
| **Frequenza max.** | Limita quante volte al secondo l'immagine viene ridisegnata (ad es. 30). 0 = illimitata. |
| **Gli apparecchi proiettano ombre** | Gli involucri degli apparecchi proiettano ombre nei coni di luce (attivo per impostazione predefinita). |

La riga sotto le impostazioni mostra cosa vale ora (luci, ombre, apparecchi posizionati) e cosa consente la scheda grafica. **Reimposta limiti** ripristina i valori predefiniti.

## 4. Quando l'immagine non è quella attesa

- **Non tutti gli apparecchi illuminano il palco, alcuni non hanno ombra, solo alcuni mostrano un gobo.** Dipende dai limiti di questo dispositivo. Solo i *Luci massime* apparecchi più luminosi (predefinito 32) illuminano le superfici, solo *Ombre massime* di queste luci proiettano ombre (la scheda grafica fissa un limite massimo, indicato nella riga informativa) e un motivo di gobo o prisma compare sulle prime **3** luci di questo tipo; le altre mostrano luce aperta. Aumenta *Luci massime* e *Ombre massime* (0 = quante possibile) se vuoi vedere tutto – con molti apparecchi l'immagine diventa più lenta o ha un po' di ritardo.
- **Un apparecchio è acceso ma il suo cono manca.** Controlla la **Foschia** (0 % = nessun cono), *Max. coni di luce semplici*, il Blackout, il Grand Master, il dimmer dell'apparecchio e che la simulazione 3D non sia ferma.
- **L'immagine è scura.** La luce di lavoro esiste solo in modalità Costruisci; controlla il cursore *Esposizione*, il Blackout e il Grand Master.
- **La simulazione 3D è lenta.** Prova in quest'ordine: Foschia 0 % (se non ti serve), meno *Luci massime* / *Ombre massime*, *Max. coni di luce semplici* (ad es. 200), disattivare *Gli apparecchi proiettano ombre*, qualità Bassa o Automatica, una *Frequenza max.* di 30, oppure fermare la simulazione 3D finché non ti serve. I palchi con 100 o più apparecchi accesi insieme sono impegnativi; fino a circa 16 apparecchi accesi contemporaneamente bastano i valori predefiniti.
- **Un apparecchio non si muove in 3D.** Il suo tipo ha bisogno di un modello 3D con forcella / testa mobile e di canali Pan / Tilt; i tipi senza (pannelli LED, barre, blinder) restano fermi. L'apparecchio deve inoltre essere posizionato sul palco (modalità Apparecchi → *Posiziona tutti*).
- **Un cono di luce punta nella direzione sbagliata.** OpenCue inverte la direzione automaticamente quando un file GDTF fa puntare il fascio nell'involucro. Se un tipo è ancora sbagliato, annota il suo nome e segnalalo allo sviluppatore.
