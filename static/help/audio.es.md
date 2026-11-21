# Audio: luces que reaccionan a la música

OpenCue puede **escuchar** música y hacer que las luces reaccionen: más brillantes con los graves, un destello con cada bombo, colores que cambian con el ritmo, un chase que corre al compás. El análisis se ejecuta en directo en la consola, no necesita internet y ocupa solo unos pocos puntos porcentuales de un núcleo del procesador.

---

## 1. La idea en un minuto

- El **panel Audio** toma una fuente de sonido y la analiza: volumen, un espectro, los golpes de **bombo, caja y hi-hat**, el **tempo (BPM)** y la posición dentro del compás.
- Los resultados están disponibles para los efectos como **variables** (`a_level`, `a_bass`, `a_kick`, `a_beat_phase` ...). Un **efecto de audio** es un script de efecto normal que las lee. Funciona como cualquier otro efecto: asígnelo a proyectores en el programador, guárdelo en cues, haga que entre y salga con fundido.
- Con el programa se incluyen 33 efectos de audio ya hechos. Llevan la etiqueta **Audio** (se pone automáticamente en cuanto un efecto lee valores de audio); elija la etiqueta en el cuadro de diálogo del tipo de efecto para listarlos.
- Sin una fuente en marcha todos los valores de audio son `0`: un efecto de audio simplemente se queda oscuro o en su valor de reposo.
- Los cues también pueden arrancar **con la música**: el disparador de cue *Audio* (sección 8).
- Los botones, faders e interruptores propios de la consola pueden seguir la música (sección 9) y la API REST puede leer y controlar el audio (sección 10).

---

## 2. Inicio rápido

1. Añada el panel: **Editar → Añadir panel…** → categoría *Medios y tiempo* → **Audio**.
2. Elija **Ritmo de demostración** en la lista de fuentes y pulse **Iniciar**. Se analiza un bucle de batería a 120 BPM: verá el espectro, las luces *Bombo / Caja / Hi-hat / Ritmo* parpadear y aparece el tempo.
3. En el programador seleccione algunos proyectores, abra la pestaña **Efectos** y haga clic en **Añadir efecto**, elija el tipo de efecto **Kick Flash** (o *Bass Dimmer*, *Beat Chase* ... – consejo: filtre por la etiqueta *Audio*) y créelo. Los proyectores parpadean ahora con el ritmo de demostración.
4. Cambie la fuente a su música real (sección siguiente).

Las instalaciones existentes obtienen los nuevos efectos a través del **Gestor de archivos** (lista *Efectos*) con **Restaurar efectos predeterminados**. Esto solo crea los archivos *que faltan* y nunca sobrescribe: si ya restauró una versión anterior, elimine primero los archivos antiguos `audio_*.fx` en el gestor de archivos y restaure de nuevo.

---

## 3. Elegir la fuente

La lista muestra todo lo que Windows conoce:

| Grupo | Qué es | Uso típico |
|---|---|---|
| **Sonido del sistema** | Lo que este ordenador reproduce por un altavoz o auriculares («loopback»). Una entrada por dispositivo de salida. | Música del mismo ordenador (software de DJ, Spotify, navegador). Sin cable, sin micrófono. |
| **Entradas** | Micrófonos, tomas de línea e interfaces de audio USB. | Música de una mesa de mezclas o de un teléfono: conecte el cable a la **entrada de línea** o a la interfaz. Un portátil con una sola toma combinada de auriculares la trata como *micrófono*: la señal es más débil, suba la **ganancia de entrada**. Un micrófono en la sala también funciona, pero la música tiene que sonar fuerte y clara. |
| **Prueba** | El ritmo de demostración. | Probar efectos sin música. |

Las entradas marcadas *(predeterminado)* son las que Windows usa por defecto. **Buscar de nuevo** (el botón de flechas) vuelve a buscar dispositivos tras conectar algo.

Pulse **Iniciar**. La fuente permanece abierta hasta que pulse **Detener**; el siguiente inicio del programa la abre otra vez por sí solo. Si no se puede abrir una fuente, el panel dice por qué (la usa otro programa, bloqueada en los ajustes de privacidad de Windows *Micrófono*, desenchufada).

---

## 4. Qué muestra el panel

- **Espectro:** 32 barras de 30 Hz a 16 kHz (los tonos graves a la izquierda). El marco brilla en cada pulso.
- **Luces:** *Bombo*, *Caja*, *Hi-hat* se encienden en cada golpe; *Ritmo* en cada pulso del tempo.
- **Nivel** con una marca de *Saturación*: se enciende cuando la señal satura (demasiado fuerte en la entrada; baje el volumen o la ganancia).
- **Tempo:** los BPM en cifras grandes, un LED de pulso, una barra con la posición dentro del pulso y una barra fina que indica cuán segura es la detección.

---

## 5. Tempo: automático, marcado o fijo

- **Automático** detecta el tempo a partir de la música (70 - 180 BPM). Necesita unos segundos y un ritmo constante; sigue los cambios de tempo.
- **Tap:** golpee el botón al compás de la música (también el comando `Tap`). A partir del segundo golpe el tempo se fija con sus golpes y el pulso empieza exactamente en el golpe. El tempo es entonces *Manual*.
- **÷2 / ×2:** cuando la detección encontró la mitad o el doble de la velocidad (típico de música muy lenta o muy rápida).
- **Manual:** el tempo es fijo; escríbalo en el campo. Con *Tempo manual: el pulso sigue la música* la posición del pulso aún se ajusta suavemente a los golpes. Sin ninguna música, un tempo fijo funciona como un **metrónomo**: los efectos con `a_beat_phase` siguen al compás.
- **Automático** vuelve a la detección.

Comandos: `Tap`, `BPM 128`, `BPM Auto`, `BPM Half`, `BPM Double`, `Audio Start`, `Audio Stop`, `Audio Demo`, `Audio Status`.

---

## 6. Ajustes

| Ajuste | Qué hace |
|---|---|
| **Ganancia de entrada** | Amplifica (×0,1 a ×10) una señal débil, p. ej. un micrófono. |
| **Ganancia automática** | El análisis se mide frente a las partes más fuertes de los últimos segundos, de modo que una canción suave funciona como una fuerte. Desactívela para una escala fija (entonces la ganancia actúa directamente). |
| **Sensibilidad al ritmo** | Más alta: cuentan incluso los golpes suaves (riesgo: golpes falsos). Más baja: solo cuentan los golpes claros. |
| **Suavizado** | Con qué lentitud caen de nuevo los niveles y las bandas. |
| **Desfase de sincronización** | de −100 a +200 ms. Positivo: las luces reaccionan **antes**; úselo cuando las luces o los altavoces llegan tarde. |

Los ajustes pertenecen a la consola (no a un show ni a un panel) y se guardan automáticamente. Cada dispositivo con un panel Audio muestra y controla la misma fuente.

---

## 7. Los efectos de audio ya hechos

| Efecto | Categoría | Qué hace |
|---|---|---|
| Band Bars | Dimmer | Cada proyector muestra una banda de frecuencias: el primero los graves, el último los agudos (se repite con más de 8 proyectores). |
| Bass Dimmer | Dimmer | El brillo sigue los graves de la música. |
| Beat Chase | Dimmer | Un chase que avanza en cada pulso (o cada n-ésimo). |
| Beat Pulse | Dimmer | El brillo pulsa al compás de la música: brillante en el pulso y luego se desvanece suavemente. |
| Beat Strobe | Dimmer | Estroboscopio al compás de la música: varios destellos por pulso, anclados al tempo. |
| Beat Toggle | Dimmer | Alterna entre dos grupos en cada pulso (o cada n-ésimo), de forma seca o con fundido cruzado (suave). |
| Hi-Hat Sparkle | Dimmer | En cada golpe de hi-hat centellean proyectores elegidos al azar. |
| Kick Chase | Dimmer | Un chase que avanza en cada golpe de bombo (en lugar de en el pulso). |
| Kick Flash | Dimmer | Cada golpe de bombo hace destellar las luces, que luego se apagan. |
| Level Dimmer | Dimmer | El brillo sigue el volumen general. |
| Snare Flash | Dimmer | Cada golpe de caja (o palmada) hace destellar las luces, que luego se apagan. |
| Beat Color | Color | El color cambia en cada pulso (o cada n-ésimo) y es más brillante en el pulso. |
| Beat Color Chase | Color | Una luz de color (A) recorre un color de fondo (B), un paso por pulso (o cada n-ésimo). |
| Beat Color Fade | Color | Funde entre dos colores al compás de la música. |
| Beat Color Strobe | Color | Un estroboscopio de color al compás de la música: varios destellos por pulso, alternando entre los colores A y B. |
| Color Blend | Color | Mezcla del color A (suave) al color B (fuerte). |
| Color Hit | Color | El color base destella al color de destello en cada golpe del tambor elegido. |
| Hi-Hat Color Sparkle | Color | En cada golpe de hi-hat destellan proyectores elegidos al azar en un color aleatorio (dentro del rango de colores). |
| Hue Drift | Color | Los colores derivan por el rango de colores; un ciclo completo dura `beats` pulsos. |
| Kick Color Flash | Color | El color base destella al color de destello en cada golpe de bombo. |
| Spectrum Color | Color | El color se mezcla a partir de la música: graves = rojo, medios = verde, agudos = azul. |
| Spectrum Hue | Color | El color sigue el sonido: la música con muchos graves muestra el principio del rango de colores y los sonidos brillantes su final. |
| Bass Tilt | Posición | El tilt sigue los graves: suave = abajo, graves fuertes = arriba (alrededor de la posición base). |
| Beat Circle | Posición | Las cabezas recorren un círculo al compás de la música: una vuelta dura `beats` pulsos. |
| Beat Fan | Posición | Los proyectores se abren en abanico y se cierran al compás de la música. |
| Kick Tilt Punch | Posición | En cada golpe de bombo las cabezas dan un golpe de tilt y vuelven a la posición base. |
| Level Spread | Posición | Cuanto más fuerte suena la música, más se abren en abanico los proyectores (simétricamente alrededor de la posición base). |
| Pan/Tilt Sway | Posición | Las cabezas se mueven al compás de la música. |
| Snare Pan Snap | Posición | En cada golpe de caja cada cabeza salta a la siguiente de cuatro posiciones de pan. |
| Beat Zoom Pulse | Zoom | El zoom pulsa en cada pulso: alto en el pulso y luego cae de nuevo a bajo. |
| Kick Zoom Punch | Zoom | El zoom da un golpe de bajo a alto en cada golpe de bombo y vuelve a caer. |
| Bass Focus | Foco | El foco sigue los graves de la música. |
| Beat Gobo Change | Gobo | El gobo cambia en cada pulso (o cada n-ésimo). |

Casi todos los efectos tienen opciones para **alternar animaciones** y añadir un **estroboscopio**: *strobe* (destellos por segundo, 0 = apagado), *mode* (por ejemplo todos juntos / pares-impares alternando / aleatorio), *direction* (chase hacia delante, hacia atrás, de ida y vuelta, aleatorio), *every* (cambiar cada n-ésimo pulso), *soft* (cambio seco o fundido cruzado). Son efectos normales: guárdelos en cues, varíelos, cópielos.

---

## 8. Disparador de cue: Audio

Además de *Go*, *Follow*, *Timecode* y *MIDI* (guía *MIDI*), un cue puede tener el disparador **Audio**: se dispara entonces solo **con la música**. En el cuadro de diálogo del cue elija el disparador *Audio*, escoja **una fuente** y, si hace falta, un valor; en la lista de cues también puede escribirlo (`audio kick`, `audio beat 4`, `audio bass 70`) o usar el comando `Cue 2 Trigger Audio Beat 4`.

| Fuente | Valor | El cue se dispara … |
|---|---|---|
| **Ritmo (tempo)**, **Bombo**, **Caja**, **Hi-hat** | cada n-ésimo (1 a 64, por defecto 1) | … en cada n-ésimo pulso / golpe. |
| **Nivel general**, **Graves**, **Medios**, **Agudos** o una de las **ocho bandas** (con su rango en Hz en la lista) | umbral en % (por defecto 70) | … cuando esta parte del sonido **alcanza** el umbral subiendo desde abajo. |

Cómo funciona:
- El cue se dispara cuando es el **siguiente cue** de una lista en marcha: primero inicie la lista con *Go*; después el siguiente cue de audio espera su evento. Una vez disparado, el cue que sigue (si también tiene el disparador *Audio*) espera a su vez: así puede encadenar toda una secuencia a la música.
- El contador (*cada n-ésimo*) empieza en 0 cada vez que un cue nuevo pasa a estar activo.
- Con un umbral el cue se dispara una vez cuando el nivel lo alcanza; solo se rearma después de que el nivel haya caído claramente por debajo (aproximadamente el 80 % del umbral). Si el nivel ya está por encima cuando el cue pasa a ser el siguiente, espera a la siguiente subida.
- Tras un disparo hay una breve pausa (0,25 s), de modo que un golpe nunca inicia dos cues.
- El **panel Audio debe estar en marcha** (una fuente iniciada); sin sonido no se dispara nada. El disparador funciona para cada lista de cues por separado.

---

## 9. Botones, faders e interruptores que reaccionan a la música

Los paneles **Botón**, **Fader** e **Interruptor** propios de la consola pueden usar la música como *señal*: en *Sigue el estado de* (un fader se mueve con la música, un interruptor cambia con la señal) y en las **condiciones de las reglas** (color, texto o comando cuando …). Las señales están en el grupo **Audio**:

| Señal | Significado |
|---|---|
| **Hay señal de audio presente** | activa mientras hay una fuente abierta y suena algo |
| **Nivel general**, **graves**, **medios**, **agudos** | 0–100 % |
| **Bombo**, **caja**, **hi-hat**, **pulso** (impulso) | saltan al 100 % en cada golpe y se desvanecen |
| **Tempo (BPM)** | el tempo detectado o fijado |

Ejemplos: un fader que sigue los graves como medidor de nivel; un botón que se ilumina en rojo cuando el tempo está entre 120 y 130 BPM; un interruptor que muestra si entra música. La fuente de audio se ejecuta en la consola; a un panel le basta con estar en la pantalla de cualquier dispositivo: las mediciones se envían a un dispositivo exactamente mientras allí haya abierto un panel así (o el panel *Audio*).

## 10. El audio mediante la API

La API REST puede leer el análisis (`GET /api/v1/audio`), abrir y cerrar la fuente, cambiar los ajustes y marcar el tempo (`PUT /api/v1/audio`, `POST /api/v1/audio/tap`, permiso *Audio*), y el **flujo de eventos en directo** (`GET /api/v1/events?events=audio,beat,hit`) informa de la fuente, cada pulso y cada golpe de tambor en el momento en que ocurren. Véase la guía *API REST*.

## 11. Escribir su propio efecto de audio

Abra el **Estudio de efectos**, cree un efecto y lea las variables de audio; véase la guía *Estudio de efectos*, sección *Variables de audio*. Un primer ejemplo:

```
#NAME My Flash
#CATEGORY dimmer
#RATE 40
#VAR peak Slider 100 0 100 1

loop() {
  dimmer = peak * a_kick;
}
```

La vista previa del estudio reproduce un ritmo de ejemplo (120 BPM) para que vea enseguida cómo se comporta la curva.

---

## 12. Cuando algo no funciona

| Problema | Compruebe |
|---|---|
| No se puede abrir la fuente | Otro programa la usa en exclusiva; el micrófono está bloqueado en los ajustes de privacidad de Windows (*Configuración → Privacidad → Micrófono*); el dispositivo está desenchufado. |
| El panel no muestra nada / todo plano | ¿Está la fuente *iniciada*? ¿Se mueve el medidor de volumen de Windows? Suba la **ganancia de entrada**. Para *Sonido del sistema* el programa debe reproducir realmente en ese dispositivo de salida. |
| *Saturación* está encendida | La señal es demasiado fuerte: baje el volumen en la fuente o la ganancia de entrada. |
| Los BPM saltan o son la mitad / el doble | Pulse **÷2 / ×2**, marque el tempo o fíjelo con *Manual*. La música sin ritmo constante (clásica, voz) no tiene un tempo detectable. |
| Las luces reaccionan demasiado tarde | Use el **Desfase de sincronización** (valores positivos). |
| Un efecto de audio se queda oscuro | No hay fuente en marcha, o la sensibilidad es demasiado baja para la música; suba el control deslizante *gain* del efecto. |
