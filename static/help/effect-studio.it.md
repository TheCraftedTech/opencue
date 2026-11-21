# Studio effetti – Guida

Un **effetto** è un piccolo programma che cambia la luce nel tempo: un dimmer che pulsa, un colore che percorre l'arcobaleno, una testa mobile che descrive un cerchio. Gli effetti si scrivono nello **Studio effetti** (pannello *Studio effetti*) in un linguaggio che assomiglia a C++ o Arduino: con variabili, `if`, `for`, `while` e funzioni proprie. Non serve essere programmatori – i modelli sotto **Nuovo...** funzionano subito e sono fatti per essere letti e modificati.

Questa guida è disponibile anche nello studio con il pulsante **Aiuto**.

---

## 1. L'idea in un minuto

- Uno **script** è un file di testo (`.fx`). Descrive cosa succede in **un solo passaggio**. Quel passaggio si chiama `loop()` e viene eseguito **`#RATE` volte al secondo** (da 1 a 40, predefinito 40).
- A ogni passaggio lo script calcola nuovi **valori di uscita**: `dimmer`, oppure `r`/`g`/`b`, oppure `pan`/`tilt`. Quali, lo decide la **categoria** (`#CATEGORY`).
- Tra due passaggi l'**uscita resta dov'è**. A 10 passaggi al secondo il valore cambia quindi dieci volte al secondo – di proposito, è così che si costruiscono effetti a gradini.
- Lo script gira **per ogni apparecchio per conto suo**. Ognuno conosce il proprio numero (`index`) e il totale (`count`); usateli per distribuire onde e chase su più apparecchi.
- Le variabili create fuori da `loop()` **mantengono il loro valore tra un passaggio e l'altro**: contatori, stati, timer.

```
#NAME Sine
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05

loop() {
  dimmer = 50 + 50 * sin(2 * PI * speed * elapsed);
}
```

Questo è un effetto completo: il dimmer oscilla tra 0 e 100 % con `speed` onde al secondo.

---

## 2. Panoramica dei comandi (promemoria)

Tutti i comandi a colpo d'occhio. I capitoli successivi li spiegano con esempi.

| Area | Comandi |
|---|---|
| Righe di intestazione | `#NAME`, `#DESCRIPTION`, `#CATEGORY dimmer` / `color` / `position`, `#RATE 1` a `40`, `#VAR name Slider` / `NumberInput` / `ColorPicker` / `Internal ...` |
| Struttura | `setup() { }` (una volta all'inizio), `loop() { }` (`#RATE` volte al secondo) |
| Tipi | `float` (`double`), `int` (`long`, `short`, `byte`), `bool` (`boolean`), `void`, `const` |
| Assegnazione | `x = 1;`, `x += 1;` (anche `-=` `*=` `/=` `%=`), `x++;`, `x--;` |
| Diramazione | `if (...) { } else if (...) { } else { }`, `condition ? a : b` |
| Cicli | `for (int i = 0; i < n; i++) { }`, `while (...) { }`, `do { } while (...);`, `break;`, `continue;` |
| Funzioni | `float name(float x) { return x * 2; }`, `void name() { }`, `return value;` |
| Calcolo | `+ - * / %`, `== != < <= > >=`, `&& \|\| !` |
| Commenti | `// fino a fine riga`, `/* su più righe */` |
| Uscite | Dimmer: `dimmer` · Colore: `r`, `g`, `b` o `hsv(h, s, v);` · Posizione: `pan`, `tilt` · Zoom: `zoom` · Focus: `focus` · Gobo: `gobo`, `gobo_spin`, `gobo2`, `gobo2_spin` |
| Tempo | `t` (tempo di sistema condiviso), `elapsed` (dall'avvio dell'effetto), `dt`, `tick` (`loop_count`), `rate` |
| Apparecchi | `index`, `count`, `phase` (= `index / count`), `slots`, `slots2` (numero di gobo sulla ruota 1 e sulla ruota 2) |
| Costanti | `PI`, `TWO_PI`, `HALF_PI`, `E`, `true`, `false` |
| Matematica | `sin` `cos` `tan` `asin` `acos` `atan` `atan2` `sqrt` `pow` `exp` `log` `abs` `sign` `min` `max` `floor` `ceil` `round` `fract` `mod` |
| Aiuti | `constrain(x, lo, hi)` `map(x, inMin, inMax, outMin, outMax)` `lerp(a, b, k)` `smoothstep(e0, e1, x)` `radians(d)` `degrees(r)` |
| Forme d'onda | `saw(x)` `tri(x)` `square(x)` `square(x, duty)` – ciascuna da 0 a 1 per periodo |
| Casuale, colore, gobo | `random()` `random(max)` `random(min, max)` · `hsv(h, s, v)` · `slot(n)` `slot(n, wheel)` |

---

## 3. Usare lo studio

| Area | Cosa fa |
|---|---|
| **Apri...** | Finestra con tutti gli effetti, **preferiti per primi** (ricerca, categoria, cicli al secondo, origine; gli effetti inclusi portano il distintivo **Predefinito**). L'elenco scorre. Fate clic su una riga per aprirla, la **stella** rende un effetto preferito (vale per tutti i dispositivi), il cestino lo elimina dalla cartella utente. In fondo: **Ripristina effetti predefiniti**. |
| **Nuovo...** | Finestra: prima la **categoria** (dimmer, colore, posizione, zoom, focus, gobo) o **File vuoto**, poi un **modello** (*Vuoto* è preselezionato), poi i **cicli al secondo**. *File vuoto* crea un editor completamente vuoto senza righe di intestazione. **Crea** carica il risultato nell'editor – nulla viene salvato finché non lo dite. |
| **Salva** | Salva nel file dell'effetto. Un nuovo effetto chiede un nome di file. Un punto accanto al nome indica modifiche non salvate. Tastiera: **Ctrl+S** nel testo (salva l'effetto, non lo show). |
| **Salva come...** | Un nuovo nome di file. Se esiste già, lo studio chiede se sovrascriverlo. |
| **Elimina** | Elimina l'effetto caricato (solo nella cartella utente; viene chiesto prima). Poi l'editor è vuoto. Se il pulsante è grigio, un suggerimento dice perché (non ancora salvato, o non nella cartella utente). |
| **Aiuto** | Apre questa guida. Il promemoria (capitolo 2) elenca tutti i comandi. |
| **Anteprima** | Mostra o nasconde l'anteprima a destra. |
| **Barra di stato** | Verde = a posto. Rosso = errore con numero di riga. A destra: riga e colonna del cursore. |

L'editor **colora** parole chiave, tipi, numeri, commenti, funzioni, variabili di sistema, uscite e i vostri cursori (`#VAR`). **Invio** mantiene il rientro della riga (due spazi in più dopo `{`), **Tab** inserisce due spazi.

### L'anteprima

L'anteprima esegue il vostro script **senza alcun apparecchio** mentre scrivete – esattamente con i cicli al secondo scelti con `#RATE` – e disegna il risultato:

- **Dimmer:** una curva per apparecchio, da 0 a 100 %.
- **Colore:** R/G/B come curve e sotto una **striscia di colore** per apparecchio.
- **Posizione:** pan e tilt come curve e il **percorso** nel campo pan/tilt.

Predefinito: **1 apparecchio, 2 secondi**. In alto impostate il numero di apparecchi (da 1 a 16) e la durata (da 1 a 20 s); più apparecchi mostrano come `index`, `count` e `phase` sfasano le onde. Sotto ci sono **cursori per i vostri parametri `#VAR`** – trascinatene uno e la curva segue subito. A una frequenza bassa (fino a 20 cicli al secondo) l'anteprima disegna gradini, fino a 10 in più i singoli punti.

Se lo script contiene un errore, l'anteprima resta sull'**ultimo stato buono, attenuato**, la riga dell'errore è segnata in rosso e la barra di stato nomina la riga e il messaggio.

---

## 4. Il vostro primo effetto

1. **Nuovo...** → categoria **Dimmer** → modello **Sine** → **Crea**.
2. L'anteprima mostra due onde in due secondi (`speed` è 1).
3. Portate `speed` a 2: il doppio più veloce. Impostate 3 apparecchi nell'anteprima e portate `spread` a 0,33: le onde sono sfasate tra loro.
4. Cambiate `0.5 + 0.5 * sin(...)` nel testo e guardate la curva.
5. **Salva** (Ctrl+S), inserite un nome di file. L'effetto compare ora nell'elenco degli effetti del programmer.

---

## 5. Struttura di uno script

Uno script ha tre parti:

```
#NAME My effect                            // 1. Header lines (start with #)
#CATEGORY dimmer
#RATE 25
#VAR speed Slider 1 0.1 8 0.1

float level = 0;                           // 2. Variables and functions (optional)

setup() {                                  //    setup(): once when the effect starts (optional)
  level = 50;
}

loop() {                                   // 3. loop(): required, runs #RATE times per second
  dimmer = level;
}
```

### Righe di intestazione

| Riga | Significato |
|---|---|
| `#NAME text` | Nome visualizzato nel programma. Senza di essa si usa il nome del file. |
| `#CATEGORY dimmer` / `color` / `position` | **Obbligatoria.** Cosa controlla l'effetto. |
| `#RATE n` | Quante volte al secondo viene eseguito `loop()`: un numero intero da **1 a 40**. Predefinito 40 – la frequenza dell'uscita DMX. |
| `#DESCRIPTION text` | Una breve descrizione (anche `#DESCRIPTION en ...` e `#DESCRIPTION de ...` per un testo per lingua; il programma mostra quello della lingua dell'interfaccia). |
| `#INFO name en Label \| Hint` | Dà al cursore `name` un'**etichetta** e un **suggerimento al passaggio del mouse** in una lingua (`en` o `de`), ad esempio `#INFO speed de Tempo \| Wie schnell der Effekt läuft`. Senza `#INFO` il programma usa il proprio glossario integrato dei nomi comuni (`speed`, `size`, `low`, `high`, `strobe` ...) e infine il nome della variabile stessa. |
| `#TAGS a, b, c` | Parole chiave per cercare e filtrare nella finestra del tipo di effetto (ad esempio `strobe, flash, toggle`; fino a 8, minuscole). Uno script che legge variabili audio riceve automaticamente il tag `audio` – non lo scrivete voi. Gli effetti inclusi portano `basic` (per principianti, 19 di essi) o `advanced` (tutti gli altri) come primo tag; la finestra li mostra come «Base» / «Avanzato» – usateli anche per i vostri effetti. |
| `#VAR ...` | Un **cursore** (vedi la sezione 9) o una variabile interna. |

---

## 6. Tempo e frequenza

**La regola più importante:** `loop()` viene eseguito esattamente `#RATE` volte al secondo – indipendentemente da quanto è veloce il computer. Potete quindi **pensare in secondi esatti**.

| Nome | Significato |
|---|---|
| `elapsed` | **Secondi dall'avvio dell'effetto** su questo apparecchio. Parte da 0. Esattamente `tick / rate`. Così programmate «al secondo 3 deve succedere questo». |
| `t` | Tempo di sistema condiviso in secondi. Lo stesso per **tutti** gli effetti – gli effetti che calcolano con `t` restano **sincronizzati** tra loro anche se sono stati avviati in momenti diversi. |
| `tick` | Numero del passaggio, parte da 0. |
| `rate` | Passaggi al secondo (il valore di `#RATE`). |
| `dt` | Tempo tra due passaggi in secondi (`1 / rate`). |

Quale frequenza scegliere?

- **40** (predefinita): le curve più fluide – per onde, cerchi, dissolvenze incrociate.
- **Da 10 a 25**: sufficiente per cambi di colore ed effetti che comunque vanno a gradini.
- **Da 1 a 5**: effetti a passi (un passo al secondo, chase «clic-clic»), poco costosi da calcolare.

**La convenzione «speed»:** gli effetti inclusi e tutti i modelli hanno un cursore `speed` con valore predefinito **1**: è **un periodo al secondo**. `sin(2 * PI * speed * elapsed)` è un'onda al secondo con `speed = 1`.

### Al secondo X ...

```
#NAME Sequence
#CATEGORY dimmer
#RATE 20
#VAR length Slider 8 2 30 1       // length of the sequence in seconds

loop() {
  float s = elapsed % length;     // time within the sequence; jumps back to 0 after "length" seconds
  if (s < 2) {
    dimmer = map(s, 0, 2, 0, 100);                 // seconds 0 to 2: fade in
  } else if (s < 5) {
    dimmer = 100;                                  // seconds 2 to 5: full
  } else {
    dimmer = 100 * (1 - (s - 5) / (length - 5));   // then fade out
  }
}
```

---

## 7. Il linguaggio

Tutto è un **numero**. I tipi sono `float` (decimale, anche `double`), `int` (numero intero, anche `long`, `short`, `byte`) e `bool` (0 o 1, anche `boolean`). `true` e `false` sono 1 e 0.

### Variabili

```
float x = 1.5;          // decimal number (dot, not comma)
int n = 3;              // whole number: assigning truncates (7.9 becomes 7)
bool on = true;         // 0 or 1: any value other than 0 becomes 1
const float K = 0.25;   // constant, cannot be changed
float a = 1, b2 = 2;    // several in one line
```

- Le variabili create **fuori** dalle funzioni sono **globali** e **mantengono il loro valore** da un passaggio all'altro. Il loro valore iniziale vale all'avvio dell'effetto (per reimpostarle in seguito scrivete `setup()`).
- Le variabili create **dentro** `{ }` sono **locali**: durano fino alla graffa di chiusura e ripartono da zero a ogni passaggio.
- Assegnare a una variabile **non dichiarata** (`counter = counter + 1;`) crea automaticamente un `float` globale – così funzionavano gli script più vecchi. Meglio dichiararla.
- I nomi `t`, `elapsed`, `dt`, `tick`, `rate`, `index`, `count`, `phase`, `dimmer`, `r`, `g`, `b`, `pan`, `tilt`, `PI` e tutte le parole chiave e i nomi di funzione sono occupati.

### Calcolare e confrontare

| Simbolo | Significato |
|---|---|
| `+ - * /` | Aritmetica di base. La divisione per 0 dà 0. |
| `%` | Resto (anche per decimali): `5.5 % 2` è 1,5. |
| `== != < <= > >=` | Confronti; risultato 1 (vero) o 0 (falso). |
| `&& \|\| !` | E, o, non. Le condizioni sono vere quando non sono 0. |
| `condition ? a : b` | Scelta: `a` se la condizione è vera, altrimenti `b`. |
| `= += -= *= /= %=` | Assegnazione; `x += 2;` è `x = x + 2;`. |
| `x++;` `x--;` | Aumenta / diminuisce di 1. |

### Diramazione e ripetizione

```
if (x > 10) {                 // if ...
  dimmer = 100;
} else if (x > 5) {           // else if ...
  dimmer = 50;
} else {                      // else
  dimmer = 0;
}

for (int i = 0; i < 5; i++) { // count i from 0 to 4
  total += i;
}

while (n > 0) { n--; }        // as long as n is greater than 0

do { n++; } while (n < 3);    // run at least once

break;                        // leave the loop at once
continue;                     // jump to the next loop pass
```

Le graffe `{ }` sono facoltative per una singola istruzione (`if (a) b = 1;`), ma più chiare con esse. Non c'è `switch` – usate `if` / `else if`.

### Funzioni proprie

```
float wave(float x) {                     // return type, name, parameters
  return 0.5 + 0.5 * sin(2 * PI * x);     // return hands the value back
}

void setBright(float v) {                 // void: returns nothing
  dimmer = v;
}

loop() {
  setBright(100 * wave(speed * elapsed));
}
```

Le funzioni possono stare prima o dopo il punto in cui vengono chiamate e possono chiamare se stesse (ricorsione, limitata). I parametri sono locali; le variabili globali e le uscite (`dimmer` ...) sono raggiungibili ovunque.

### Commenti

```
// rest of the line is a comment
/* several
   lines */
```

### Limiti

- Un passaggio può eseguire al massimo **60.000 iterazioni di ciclo e chiamate di funzione**; un ciclo infinito si ferma con il messaggio «endless loop?».
- Un effetto che **provoca un errore o richiede più di 50 ms per passaggio** viene spento («a riposo») per non trattenere gli altri. Salvate di nuovo lo script e riparte.
- Esistono solo numeri: niente testo, liste (array) o puntatori.

---

## 8. Uscite per categoria

Lo script scrive il suo risultato in variabili adatte alla categoria:

| `#CATEGORY` | Uscite | Intervallo |
|---|---|---|
| `dimmer` | `dimmer` | da 0 a 100 (%) |
| `color` | `r`, `g`, `b` | da 0 a 255 |
| `position` | `pan`, `tilt` | da 0 a 100 (%), 50 è il centro. Se l'apparecchio ha canali fini (16 bit), si usano i decimali: `pan = 33.3333;` è più preciso di `pan = 33;` |
| `zoom` | `zoom` | da 0 a 100 (%) – gli estremi del canale zoom (largo/stretto, a seconda dell'apparecchio) |
| `focus` | `focus` | da 0 a 100 (%) – gli estremi del canale focus (vicino/lontano) |
| `gobo` | `gobo` | da 0 a 100 (%) – la posizione del canale gobo della ruota 1; scegliete i gobo meglio con `slot(n)` (vedi sotto) |
| `gobo` | `gobo_spin` | da 0 a 100 (%) – rotazione o scuotimento della ruota 1 (l'intervallo stabilisce direzione e velocità, a seconda dell'apparecchio) |
| `gobo` | `gobo2` | da 0 a 100 (%) – ruota gobo 2 (solo apparecchi con una seconda ruota), scegliete i gobo con `slot(n, 2)` |
| `gobo` | `gobo2_spin` | da 0 a 100 (%) – rotazione della ruota 2 |

I valori fuori intervallo vengono limitati. **Un effetto pilota solo le uscite che il suo script assegna da qualche parte** (`hsv()` conta come `r`, `g`, `b`; per il colore sempre tutte e tre). Se uno script scrive solo `pan`, `tilt` viene lasciato in pace: il canale non segue l'effetto, e nel programmer è bloccato solo il fader Pan – potete continuare a impostare Tilt a mano. Se un'uscita non viene raggiunta in un passaggio (ad es. l'assegnazione sta in un `if`), per quel passaggio vale 0 (`pan`/`tilt`: centro, 50). Se l'apparecchio non ha il canale, l'uscita viene ignorata in silenzio. Le uscite di un'altra categoria vengono ignorate. Con `hsv(h, s, v);` impostate `r`, `g`, `b` da tinta, saturazione e valore (ciascuno da 0 a 1) in un solo passo.

Nota: le uscite valgono solo per **il passaggio attuale** – per ricordare un valore, create una variabile propria (`float level = 0;` ... `dimmer = level;`).

---

## 9. Cursori: `#VAR`

```
#VAR <name> <type> <default> [min max step]
```

| Tipo | Predefinito | Controllo |
|---|---|---|
| `Slider` | numero, più `min max step` | cursore |
| `NumberInput` | numero, più `min max step` | campo numerico |
| `ColorPicker` | colore esadecimale, ad es. `#ff8800` | selettore colore; nello script come `name_r`, `name_g`, `name_b` (da 0 a 255) |
| `Internal` | numero | nessun controllo – una variabile globale con un valore iniziale (come `float name = 0;`) |

```
#VAR speed Slider 1 0.05 8 0.05          // periods per second
#VAR size Slider 100 0 100 1             // strength in %
#VAR color ColorPicker #00aaff           // color_r, color_g, color_b
```

I cursori compaiono nella finestra **Crea / Modifica effetto** e nell'anteprima dello studio. Nello script sono di **sola lettura**.

---

## 10. Variabili di sistema

| Nome | Significato |
|---|---|
| `t` | Tempo di sistema condiviso in secondi (mantiene gli effetti sincronizzati). |
| `elapsed` | Secondi dall'avvio di questo effetto su questo apparecchio. |
| `dt` | Secondi tra due passaggi (`1 / rate`). |
| `tick` | Numero del passaggio (0, 1, 2 ...). Anche `loop_count`. |
| `rate` | Passaggi al secondo. |
| `index` | Numero di questo apparecchio nell'ordine di selezione del programmer (0, 1, 2 ...). |
| `count` | Numero di apparecchi su cui gira l'effetto. |
| `phase` | `index / count`: sfasamento uniforme sulla selezione (da 0 a quasi 1). |
| `slots` | Numero di gobo fissi sulla ruota 1 (solo nella categoria `gobo`, altrimenti 0). L'anteprima usa 8 gobo. |
| `slots2` | Lo stesso per la ruota 2 (0 se l'apparecchio ha una sola ruota). |

L'ordine di selezione è l'ordine in cui avete scelto gli apparecchi.

### Variabili audio (`a_...`)

Gli effetti possono reagire alla musica. Il pannello **Audio** analizza il suono (vedi la guida *Audio*); queste variabili contengono il risultato. Tutte iniziano con `a_`, così non entrano mai in conflitto con i vostri nomi. Senza una sorgente audio attiva sono tutte `0`. Uno script che ne legge una è un **effetto audio** (contrassegnato nell'elenco e nello studio; l'anteprima fa allora girare un battito di esempio a 120 BPM).

| Nome | Significato |
|---|---|
| `a_active` | `1` finché arriva suono, altrimenti `0`. |
| `a_level` | Volume complessivo da 0 a 1 (relativo alle parti più forti degli ultimi secondi). |
| `a_bass`, `a_mid`, `a_high` | Bassi (fino a 150 Hz), medi (da 150 Hz a 2,5 kHz) e alti (oltre 2,5 kHz), da 0 a 1. |
| `a_b1` ... `a_b8` | Le otto bande una per una (20-60, 60-150, 150-400, 400-1k, 1k-2,5k, 2,5k-5k, 5k-10k, 10k-20k Hz), da 0 a 1. |
| `a_kick`, `a_snare`, `a_hat` | Colpi di cassa, rullante (o battito di mani) e hi-hat: salta a 0,45 - 1 a ogni colpo e si spegne in circa 0,15 s (hi-hat 0,07 s). |
| `a_beat` | Lo stesso tipo di impulso a ogni battito del tempo rilevato. |
| `a_beat_phase` | Posizione nel battito, da 0 a 1, crescente in modo uniforme da un battito al successivo: ideale per onde sincrone con il tempo. |
| `a_beat_count` | Numero del battito; aumenta di 1 a ogni battito. |
| `a_bpm` | Tempo rilevato (o impostato) in battiti al minuto; `0` finché è sconosciuto. |
| `a_conf` | Quanto è sicuro il rilevamento del tempo, da 0 a 1. |

```
#CATEGORY dimmer
#RATE 40
loop() {
  dimmer = lerp(5, 100, a_kick);                              // flash on every bass drum
}
```

Suggerimento: un passaggio vede solo lo stato nel proprio istante. Leggere un impulso (`a_kick`) è sempre sicuro perché si spegne; per reagire al *momento* di un colpo, ricordate l'ultimo valore in una variabile globale e confrontate (vedi l'effetto *Audio: Hi-Hat Sparkle*). Usate `#RATE 40` per gli effetti audio così restano scattanti.

---

## 11. Funzioni

| Funzione | Significato |
|---|---|
| `sin(x)`, `cos(x)`, `tan(x)` | Angolo in radianti (cerchio completo = `2 * PI`). |
| `asin(x)`, `acos(x)`, `atan(x)`, `atan2(y, x)` | Funzioni inverse. |
| `sqrt(x)`, `pow(x, y)`, `exp(x)`, `log(x)` | Radice, potenza, funzione esponenziale, logaritmo naturale. Un input non valido dà 0. |
| `abs(x)`, `sign(x)` | Valore assoluto; segno (-1, 0, 1). |
| `min(a, b)`, `max(a, b)` | Valore minore / maggiore. |
| `floor(x)`, `ceil(x)`, `round(x)` | Arrotonda per difetto, per eccesso, arrotonda. |
| `fract(x)` | Parte frazionaria: `fract(2.25)` è 0,25. Utile per «posizione nel periodo». |
| `mod(a, b)` | Resto che non è mai negativo (diversamente da `%` per numeri negativi). |
| `constrain(x, low, high)` | Limita `x` all'intervallo. |
| `map(x, inMin, inMax, outMin, outMax)` | Converte `x` da un intervallo a un altro (come in Arduino). |
| `lerp(a, b, k)` | Lineare da `a` a `b`: `a + (b - a) * k`. |
| `smoothstep(e0, e1, x)` | Transizione morbida da 0 a 1 tra `e0` e `e1`. |
| `saw(x)`, `tri(x)`, `square(x)`, `square(x, duty)` | Forme d'onda da 0 a 1 per periodo di `x`: dente di sega, triangolo, quadra (`duty` = quota «acceso», predefinita 0,5). |
| `radians(d)`, `degrees(r)` | Gradi ↔ radianti. |
| `random()`, `random(max)`, `random(min, max)` | Numero casuale (da 0 a 1, da 0 a `max`, da `min` a `max`). Ogni apparecchio ha la propria sequenza **riproducibile**. |
| `hsv(h, s, v)` | Imposta `r`, `g`, `b` da tinta `h` (da 0 a 1, ciclica), saturazione `s` e valore `v` (da 0 a 1). |
| `slot(n)` | Il valore (in %) dell'n-esimo gobo della ruota 1; `slot(0)` è il primo (di solito aperto). Solo nella categoria `gobo`; l'elenco proviene dal file dell'apparecchio, senza dati `slot()` restituisce 0. |
| `slot(n, wheel)` | Come `slot(n)`, ma per la ruota `wheel` (1 o 2): `gobo2 = slot(3, 2);` |

Costanti: `PI`, `TWO_PI`, `HALF_PI`, `E`, `true`, `false`.

---

## 12. Esempi

### Pulse (dimmer)

Acceso e spento netti; `duty` è la quota del periodo in cui la luce è accesa.

```
#NAME Pulse
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR duty Slider 0.25 0.05 1 0.05
#VAR spread Slider 0 0 1 0.05

loop() {
  float p = fract(speed * elapsed + index * spread);
  dimmer = p < duty ? 100 : 0;
}
```

### Chase (dimmer)

Una luce percorre tutti gli apparecchi selezionati.

```
#NAME Chase
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.1 8 0.1
#VAR width Slider 1 0.5 8 0.5

loop() {
  float pos = fract(speed * elapsed) * count;   // current step (decimal)
  float d = abs(index - pos);
  if (d > count / 2) d = count - d;             // distance on the circle
  dimmer = d < width ? 100 : 0;
}
```

### Colore casuale (colore)

Passa `speed` volte al secondo a una tinta casuale. La variabile globale `hue` la ricorda.

```
#NAME Random color
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.1 8 0.1

float hue = 0;

loop() {
  if (tick % max(1, round(rate / speed)) == 0) {
    hue = random();
  }
  hsv(hue, 1, 1);
}
```

### Quattro posizioni (posizione, macchina a stati)

La testa salta al successivo di quattro angoli ogni `interval` secondi. Lo stato sta in `step`.

```
#NAME Four positions
#CATEGORY position
#RATE 10
#VAR interval Slider 1 0.2 10 0.1

int step = 0;
float start = 0;

loop() {
  if (elapsed - start >= interval) {
    step = (step + 1) % 4;
    start = elapsed;
  }
  pan = (step == 0 || step == 3) ? 20 : 80;
  tilt = (step < 2) ? 20 : 80;
}
```

### Armoniche (dimmer, ciclo)

Somma più onde con un ciclo `for` (più è alta, più è silenziosa).

```
#NAME Harmonics
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.1 4 0.1
#VAR harmonics Slider 3 1 8 1

loop() {
  float sum = 0;
  float norm = 0;
  for (int k = 1; k <= harmonics; k++) {
    sum += sin(2 * PI * k * speed * elapsed) / k;
    norm += 1.0 / k;
  }
  dimmer = 50 + 50 * sum / norm;
}
```

### Zoom che respira (zoom)

Lo zoom oscilla tra `low` e `high` (0 e 100 sono gli estremi del canale zoom).

```
#NAME Zoom breathing
#CATEGORY zoom
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR low Slider 20 0 100 1
#VAR high Slider 80 0 100 1

loop() {
  float k = 0.5 + 0.5 * sin(2 * PI * speed * elapsed);
  zoom = lerp(low, high, k);
}
```

### Cambio di gobo (gobo)

Percorre a turno i gobo dell'apparecchio. `slots` è il loro numero, `slot(n)` il valore dell'n-esimo (0 = il primo, di solito aperto). Ogni apparecchio ha gobo diversi – quindi l'effetto lo chiede all'apparecchio invece di indovinare le percentuali.

```
#NAME Gobo change
#CATEGORY gobo
#RATE 20
#VAR speed Slider 0.5 0.05 8 0.05
#VAR first Slider 0 0 20 1

loop() {
  float n = max(1, slots - first);
  gobo = slot(first + mod(floor(speed * elapsed), n));
}
```

### Gobo con rotazione e seconda ruota (gobo)

Le uscite `gobo`, `gobo_spin`, `gobo2` e `gobo2_spin` si possono usare singolarmente. Questo esempio percorre la ruota 1, fa seguire la ruota 2 con uno scostamento e fa ruotare il gobo scelto:

```
#NAME Two wheels
#CATEGORY gobo
#RATE 20
#VAR speed Slider 0.5 0.05 8 0.05

loop() {
  float n  = max(1, slots);
  float n2 = max(1, slots2);
  gobo  = slot(mod(floor(speed * elapsed), n));
  gobo2 = slot(mod(floor(speed * elapsed) + 1, n2), 2);
  gobo_spin = 70;                    // rotation of wheel 1 (set only if wanted)
}
```

### Corridore bicolore (colore)

Tutti gli apparecchi mostrano il colore A, uno o due percorrono la fila nel colore B (ordine di selezione). `direction` imposta la direzione – è il *Color Runner* incluso in versione breve:

```
#NAME Color runner
#CATEGORY color
#RATE 40
#VAR speed Slider 0.5 0.05 4 0.05
#VAR width Slider 1.5 0.5 8 0.5
#VAR direction Slider 1 0 1 1
#VAR color_a ColorPicker #ffcc00
#VAR color_b ColorPicker #ff0000

loop() {
  float run = fract(speed * t);
  if (direction < 0.5) run = 1 - run;
  float d = abs(index - run * count);
  if (d > count / 2) d = count - d;
  float k = d < width ? 1 : 0;
  r = lerp(color_a_r, color_b_r, k);
  g = lerp(color_a_g, color_b_g, k);
  b = lerp(color_a_b, color_b_b, k);
}
```

### Una funzione propria (dimmer)

```
#NAME Triangle with function
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.1 8 0.1

float triangle(float x) {
  return 1 - abs(2 * fract(x) - 1);
}

loop() {
  dimmer = 100 * triangle(speed * elapsed + phase);
}
```

---

## 13. Errori e controllo

Lo studio controlla mentre scrivete. Messaggi tipici (sempre con un numero di riga):

| Messaggio | Causa |
|---|---|
| `Unbekannte Variable 'x'` | Nome mai dichiarato o assegnato (errore di battitura?). |
| `Unbekannte Funktion 'foo()'` | La funzione non esiste. |
| `sin() erwartet 1 Argument(e)` | Numero di argomenti sbagliato. |
| `';' erwartet, gefunden '}'` | Manca un punto e virgola (il messaggio spesso indica la riga dopo). |
| `Ausdruck erwartet, gefunden ';'` | Manca un valore, ad es. `dimmer = 1 +;`. |
| `'speed' ist ein Regler (#VAR) ...` | I cursori sono di sola lettura; create una variabile propria. |
| `'b' ist eine Ausgabe des Effekts ...` | `dimmer`, `r`, `g`, `b`, `pan`, `tilt` e i nomi di sistema sono occupati. |
| `'break' ist nur in einer Schleife erlaubt` | `break` / `continue` fuori da `for` / `while`. |
| `#RATE erwartet eine ganze Zahl von 1 bis 40` | Frequenza non valida. |
| `#CATEGORY fehlt` | L'intestazione non ha una categoria. |
| `loop() erwartet` | Lo script non ha la funzione `loop()`. |
| `Zu viele Schritte in einem Durchlauf ... Endlosschleife?` | Un ciclo non finisce mai (errore di esecuzione, compare nell'anteprima). |

(I messaggi vengono mostrati in tedesco qualunque sia la lingua dell'interfaccia.)

**Salva** salva anche gli script con errori così potete continuare a lavorare. Uno script difettoso non viene eseguito; gli effetti in esecuzione mantengono l'**ultima versione buona**.

Se uno script viene salvato mentre gli effetti sono in esecuzione, essi prendono il nuovo codice al passaggio successivo. La loro **memoria** (variabili globali, contatori, stato) viene conservata; le variabili appena aggiunte partono dal loro valore iniziale.

---

## 14. Come funzionano gli effetti nel programma

- **Script ed effetto:** lo script (`.fx`) è il file. Un **effetto** (nell'elenco degli effetti del programmer) è una **definizione**: un nome, uno script e valori per i suoi cursori. Più effetti possono usare lo stesso script con valori di cursore diversi. Quando ne create uno, la finestra mostra la descrizione dello script e i suoi cicli al secondo.
- **Applicare:** nel programmer assegnate un effetto per **categoria** (dimmer, colore, posizione, zoom, focus, gobo) agli apparecchi selezionati: la riga **Variabile:/Effetto** nella vista del programmer corrispondente (focus e zoom nella vista focus, gobo nella scheda gobo dell'area fascio; mentre un effetto è in esecuzione, il fader corrispondente è bloccato). L'ordine di selezione determina `index` e con esso la distribuzione sugli apparecchi. Un effetto controlla solo i canali della sua categoria.
- **Nei cue:** un cue memorizza le assegnazioni degli effetti (con l'ordine di selezione) e le avvia alla riproduzione; i tempi di **dissolvenza in entrata** e **in uscita dell'effetto** del cue sfumano l'ampiezza da / verso il valore precedente. Se un cue imposta un valore fisso per una categoria, l'effetto in esecuzione termina lì e il cue sfuma dall'ultima uscita dell'effetto.
- **Sincronizzazione:** gli effetti che usano `t` (o `phase`/`index` insieme a `t`) vanno a tempo tra loro. Con `elapsed` ogni effetto riparte dall'inizio quando parte – giusto per sequenze «da ora».
- **Stato:** ogni effetto ha la **propria memoria** per apparecchio e categoria. Riparte da zero quando l'effetto viene assegnato di nuovo.
- **File:** gli script si trovano nella cartella `effects/` della cartella dati. Lo studio, il **gestore file** (tipo *Effetti*: rinomina, duplica, scarica, carica) e l'**esportazione** dello show (gli script usati vanno nel pacchetto) lavorano con gli stessi file. Gli effetti inclusi vengono copiati al primo avvio; **Ripristina effetti predefiniti** (nella finestra Apri o nel gestore file) ricrea quelli mancanti e non sovrascrive **mai** nulla.
- **Lo show memorizza le definizioni** (nome, nome dello script, valori dei cursori), non il testo dello script. Se lo script manca, le definizioni perdono il loro effetto e funzionano di nuovo quando torna; un cue con un effetto mancante lascia il canale invariato.

### Limiti attuali

- Ci sono sei categorie (dimmer, colore, posizione, zoom, focus, gobo). Altre (prisma, strobo, valori DMX grezzi) sono predisposte ma non ancora integrate.
- Zoom e focus usano il canale proprio dell'apparecchio e questo deve esistere; i gobo dipendono dal file dell'apparecchio. L'anteprima mostra solo i valori per i gobo, non l'immagine.
- Un effetto controlla una categoria per apparecchio; due categorie insieme richiedono due effetti.
- La frequenza è al massimo di 40 al secondo perché l'uscita DMX non invia più velocemente.
