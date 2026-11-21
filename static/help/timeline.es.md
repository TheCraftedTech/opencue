# Editor de línea de tiempo y LTC

Con el **editor de línea de tiempo** coloca cues y comandos gráficamente sobre un eje de tiempo, con las formas de onda de sus canciones debajo. Con el **LTC**, OpenCue va al compás de una fuente externa (un reproductor, un software de DJ o de shows, una consola) o envía él mismo un reloj a otros dispositivos. Todo se basa en el **timecode global**.

---

## 1. La idea en un minuto

- OpenCue tiene **un solo** reloj, el **timecode** (panel *Timecode*, indicador arriba en la barra de herramientas). Corre, se detiene, salta, en todos los dispositivos a la vez.
- En ciertos momentos de este reloj ocurren cosas: arranca un **cue** con el disparador *Timecode*, se ejecuta un **comando** de una pista de comandos, un **reproductor** inicia su canción (*hora de inicio*). Esto solo ocurre cuando el reloj **atraviesa** ese momento **hacia delante**; los saltos y la marcha atrás no disparan nada.
- El reloj puede estar dirigido por **tres fuentes**: este ordenador (usted pulsa Inicio), el **timecode MIDI** (*Ajustes → MIDI*) o el **LTC** (*Ajustes → Timecode*). Dirige quien esté primero.
- El **editor de línea de tiempo** muestra todo esto en un eje de tiempo y permite colocarlo y moverlo cómodamente, en lugar de escribir cada hora en el cuadro de diálogo del cue.

---

## 2. Abrir el editor de línea de tiempo

- Como panel en la disposición: *Editar → Añadir panel → Medios → **Editor de línea de tiempo*** (mejor ancho).
- Brevemente como ventana: *Ver → Abrir panel como ventana → **Editor de línea de tiempo*** (allí se listan todos los paneles, por ejemplo también **Control sencillo**).

---

## 3. Qué aspecto tiene

- **Regla** arriba: un clic o arrastre salta a ese momento.
- **Una pista por lista de cues**: cada cue con el disparador *Timecode* es un **marcador** con número y nombre. El nombre de la lista a la izquierda la selecciona (para la bandeja y «Poner cue aquí»).
- **Pistas de comandos** (rojas / rosas): comandos de la línea de comandos en ciertos momentos; véase la sección 6.
- **Pistas de audio** abajo: **automáticas** para cada canción que un reproductor reproduce junto con el timecode, con una **forma de onda** y finas líneas en cada marcador: se ve si algo cae exactamente en el tiempo (sección 5).
- **Bandeja** al final del todo: los **cues sin hora** de la lista seleccionada.
- El **cabezal** amarillo es el timecode global.

---

## 4. Editar marcadores y avanzar

| Acción | Cómo |
|---|---|
| **Mover** un marcador | arrastrarlo hacia un lado con el ratón o el dedo; se ajusta a la **cuadrícula** (mantenga **Mayús** = sin cuadrícula) |
| **Mover con precisión** un marcador | hacer clic en el marcador y luego `←` / `→` (un paso de cuadrícula; `Mayús` = diez veces más) |
| Poner un cue **sin hora** en la línea de tiempo | arrastrarlo desde la **bandeja** a la pista, o seleccionar la ficha y pulsar **Poner cue aquí** |
| **Cuadrícula** | *desactivada*, 10 ms, fotograma (25 fps), 0,1 s, 1 s |
| **Zoom** | teclas `+` / `−`, Ctrl + rueda del ratón, **dos dedos** (iPad); *Mostrar todo* (`F`) |
| **Seguir** | la vista se desplaza junto con el cabezal |

El **avance y retroceso** funciona de todas las formas:

| Tecla / botón | Efecto |
|---|---|
| **Arrastrar** la regla o la forma de onda | salta allí de forma continua (el sonido sigue) |
| Botones **±5 s** | cinco segundos atrás / adelante (los clics rápidos se suman) |
| Botones **marcador anterior / siguiente** (`[` / `]`) | salta al siguiente cue u hora de comando |
| `←` / `→` (foco en el panel) | 1 s; con `Mayús` 10 s; con `Alt` un fotograma (40 ms) |
| `Inicio` / `Fin` | al principio / al final de los marcadores |
| `Espacio`, `L`, `K`, `J` | reproducir / pausa · adelante · pausa · reproducir **hacia atrás** |
| Botón **Invertir** | reproduce el timecode hacia atrás (no dispara cues ni comandos) |

---

## 5. Audio: automáticamente desde los reproductores

No tiene que elegir una canción en la línea de tiempo. La línea de tiempo mira por sí misma **qué se reproduce junto con el timecode**:

- Cada **reproductor** en modo **Timecode** con un medio elegido y su **hora de inicio** aparece como pista de audio: con nombre, **forma de onda** y un **marcador de inicio** (símbolo de nota) en la hora de inicio. También aparecen un reproductor en **otro dispositivo** (por ejemplo en el ordenador principal mientras trabaja en el iPad) y las **pantallas de la simulación 3D**.
- **Arrastrar el marcador de inicio** (o hacer doble clic en él y escribir la hora) cambia la **hora de inicio del reproductor**: la canción empieza entonces a la nueva hora.
- **Añadir audio ...** crea un **audio propio** de esta línea de tiempo (va sincronizado con el timecode) por si aún no hay ningún reproductor configurado. El botón del altavoz solo silencia estos audios propios. En el iPad el navegador necesita un toque en el panel antes de permitir el sonido.
- OpenCue calcula la **forma de onda** una vez con el *ffmpeg* incluido (un valor cada 10 ms) y la recuerda. Si falta ffmpeg, la pista lo indica.
- Con el **LTC** ocurre lo mismo: los reproductores siguen el timecode sin importar quién lo dirija, así que las pistas de audio siempre muestran qué corre a qué hora.

---

## 6. Pistas de comandos

Una **pista de comandos** ejecuta **comandos de la línea de comandos** en momentos del timecode, con independencia de los cues, por ejemplo `Blackout Off` a 1:30, `Cuelist Show Go` a 2:00 o `Effect Off` en el estribillo. Pertenece al **show** (se guarda y se exporta con él).

- **Nueva pista de comandos**: botón **+**. Puede haber varias (por ejemplo «Luz», «Humo», «Vídeo»); un doble clic en el nombre la renombra, la **×** la elimina (hacer clic dos veces).
- **Añadir un comando**: el botón **Comando aquí** (o `C`) coloca un comando en el momento actual de la pista seleccionada; o **haga doble clic** en la pista en ese punto.
- Una pequeña ventana pide la **hora** y el **comando**; `Intro` acepta. Cada marcador se puede **arrastrar**, mover con las teclas de flecha, editar de nuevo con un **doble clic** y eliminar con `Supr`.
- El **servidor** ejecuta el comando cuando el timecode **atraviesa** su momento **hacia delante**, exactamente igual que los cues (también con LTC / timecode MIDI). Aparece en el historial de comandos. Un salto lo omite.
- En el **modo operador** las pistas de comandos no se pueden cambiar; se ejecutan como de costumbre.

---

## 7. Colocar cues con la música (grabación)

Como en una consola, pero en gráfico:

1. Cree sus cues (lista de cues); su hora puede estar aún vacía. Aparecen en la **bandeja**.
2. Configure un **reproductor** con su canción (modo Timecode, hora de inicio 0); la forma de onda aparece sola.
3. Elija la lista de cues y el primer cue de la bandeja.
4. Inicie la reproducción (Espacio) y pulse **Poner cue aquí** (o `Intro`) en cada entrada: el cue seleccionado recibe la **hora actual** y a continuación se selecciona el **siguiente** cue.
5. Después retoque con calma: arrastre los marcadores sobre la forma de onda y deje que se ajusten.

Consejo: con *cuadrícula 1 s* o *fotograma* los marcadores caen en tiempos redondos; con *desactivada*, en el milisegundo exacto.

---

## 8. LTC: el timecode como señal de audio

El **LTC** (Linear Timecode) es una señal audible (suena como ruido) que lleva la hora. Va en un canal (normalmente el izquierdo) y la música en el otro. *Ajustes → Timecode* muestra arriba **quién dirige actualmente el reloj** (este ordenador, el timecode MIDI o el LTC) y tiene dos áreas:

**Entrada: leer el timecode (Seguir LTC)**

1. Active **Seguir LTC** y elija la **entrada de audio** (entrada de línea, interfaz USB o el *sonido del sistema* de un dispositivo de salida). Para probar existe la **señal de prueba** (25 fotogramas/s, no hace falta ningún dispositivo).
2. Elija el **canal** (izquierdo / derecho / mezcla) y **Guardar**. Debajo verá en directo **«Señal encontrada: 00:01:12:05 · 25 fps»** y una barra de nivel.
3. En cuanto llega una señal válida, el **timecode global corre con ella**. Todos los cues, comandos y reproductores siguen. Una **pausa o parada de la fuente** detiene también aquí el timecode; un **salto** de la fuente se sigue.
4. Se reconocen **24, 25, 29,97 (drop frame) y 30 fotogramas por segundo**.
5. Para tocar usted mismo, desactive de nuevo **Seguir LTC**.

**Salida: enviar timecode (Enviar LTC)**

OpenCue pasa a ser el reloj de otros dispositivos: al iniciar el timecode (por ejemplo Reproducir en el panel *Timecode*), el **LTC sale por una salida de audio**; un reproductor, una consola o una grabadora puede ir al compás.

1. Active **Enviar LTC** y elija la **salida de audio** y el **canal** (*ambos*, *solo izquierdo* o *solo derecho*; use un canal si el otro lleva música).
2. Ajuste la **velocidad de fotogramas** (24 / 25 / 29,97 drop frame / 30) y el **nivel** (fuerte pero sin saturar; muchos dispositivos esperan nivel de línea) y **Guardar**.
3. Se envía **solo mientras el timecode avanza hacia delante**; si está parado o va hacia atrás, la salida queda en silencio. Si salta, la señal empieza de inmediato en la nueva hora.
4. Si OpenCue mismo sigue una fuente LTC o MIDI, el reloj también se retransmite.

**Si no llega nada:** compruebe la barra de nivel (¿demasiado baja?), el canal (izquierdo / derecho) y si la entrada la usa otro programa.

---

## 9. Notas

- Una **fuente LTC o MIDI dirige** el reloj: Inicio / Parada en el panel Timecode quedan anulados por la fuente mientras esta funciona.
- Las horas pertenecen a los **cues**, las **pistas de comandos** y los **reproductores** del show y se guardan con él; el editor de línea de tiempo es solo la herramienta para ello.
- *Ajustes → Entradas y salidas* muestra en el grupo **Timecode**, de un vistazo: quién dirige el reloj, lectura / envío de LTC, timecode MIDI.
- Más sobre las fuentes: guía **MIDI** (timecode MIDI), guía **Acceso remoto** (iPad), panel **Timecode** (inicio, pausa, salto, velocidad), **reproductor** (hora de inicio).
