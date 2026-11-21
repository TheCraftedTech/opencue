# MIDI

Con el **MIDI** controla OpenCue desde un controlador, un teclado, pads o un software de música, y OpenCue también puede enviar MIDI. Una tecla, un fader, un potenciómetro o un cambio de programa activa un **comando de la línea de comandos**, igual que un atajo de teclado personalizado (véase *Atajos de teclado*), y además con faders.

La asignación pertenece al **programa**, no al show: se aplica a todos los shows y se guarda en la configuración de la aplicación. Se accede de cuatro maneras: el **icono MIDI** arriba a la derecha de la barra de herramientas, **Ajustes → Controles → MIDI**, **Controles → Asignación MIDI …** y, para teclas y faders de un panel, **Asignar MIDI …** en las propiedades del panel. El dispositivo MIDI está conectado al ordenador de la consola; editar la lista también funciona desde una tableta, el aprendizaje y el monitor solo en el ordenador de la consola.

---

## 1. ¿Qué es el MIDI? (brevemente)

El MIDI no envía sonido, sino pequeños **mensajes**. Se necesitan tres clases:

| Mensaje | Qué informa su dispositivo | En OpenCue |
|---|---|---|
| **Nota** | Una tecla (tecla de piano, pad) se pulsa o se suelta. Cada una tiene un número, p. ej. 60 = **Do4** (do central), y una **velocity** (0–127, con cuánta fuerza se golpeó). | Tipos **Tecla**, **Interruptor**, **Mantener**, o **Fader** (la velocity pasa a ser el valor) |
| **Controlador (CC)** | Un fader o potenciómetro. Cada uno tiene un número (0–127) y un valor 0–127. | Tipos **Fader** (faders, potenciómetros) o **Encoder** (potenciómetros sin fin) |
| **Cambio de programa** | Se elige un «programa» con un número. | Tipo **Tecla** (p. ej. programa 3 = `Go Cue 3`) |

Cada mensaje tiene además un **canal** (1–16) para que varios dispositivos compartan una línea. Si no lo sabe: déjelo en **Todos**.

---

## 2. Primeros pasos

1. Conecte el dispositivo MIDI por USB (Windows lo reconoce solo; los dispositivos compatibles con la clase estándar no necesitan controlador).
2. Haga clic en el **icono MIDI** arriba a la derecha (o **Controles → Asignación MIDI …**). Arriba se ve qué dispositivos se reconocen. El **monitor** de abajo muestra en directo todo lo que envía su dispositivo: pulse una tecla y mire: `Note On C4 (60) · 100`.
3. **Nueva asignación MIDI** → haga clic en el campo de señal de la fila → **pulse o mueva** algo en el dispositivo → **Aplicar**. La señal queda aprendida.
4. Introduzca a la derecha el **comando**, p. ej. `Go`. Listo: la tecla activa ahora `Go`. La fila se ilumina brevemente cuando se dispara.

La asignación se guarda de inmediato. El interruptor **MIDI activado** de arriba lo desactiva todo (OpenCue no escucha entonces ningún dispositivo).

**El icono de la barra de herramientas** muestra el estado: **verde** = un dispositivo está listo, **gris** = ningún dispositivo conectado, **amarillo** = un dispositivo no se puede abrir (normalmente lo retiene otro programa), **rojo y tachado** = el MIDI está desactivado. Un clic abre la asignación; la información sobre herramientas nombra los dispositivos reconocidos.

**Ajustes → Controles → MIDI** (como todos los ajustes con *Guardar*): usar MIDI, **qué dispositivos** se usan (cada dispositivo conectado tiene un interruptor; uno desmarcado nunca se abre), la **salida**, el **timecode (MTC)** y el **tempo desde el reloj MIDI** (sección 5b) y botones hacia la asignación.

En **Ajustes → Entradas y salidas → MIDI** ve los dispositivos reconocidos, si se están leyendo ahora mismo, la salida y cuántas asignaciones hay activas.

---

## 3. Los tipos

| Tipo | Efecto | Ejemplo |
|---|---|---|
| **Tecla** | El comando se ejecuta cuando se pulsa la tecla. | Pad 1 → `Go`; Pad 2 → `Back`; Pad 3 → `Clear` |
| **Interruptor** | Cada pulsación alterna entre el **comando** y el **comando de apagado** (vacío = el mismo comando las dos veces). | `Blackout` (alterna por sí solo); o `Effect Rainbow` / `Effect Off` |
| **Mantener** | El **comando** se ejecuta al pulsar, el **comando de liberación** al soltar («flash»). | `Group front At Full` / `Group front At 0` |
| **Fader** | El comando recibe el valor como `{value}`, escalado al rango **Desde … Hasta** (también **Invertir**). | Fader → `Master {value}` (0–100); Fader → `Cuelist main Fader {value}` |
| **Encoder** | Para **potenciómetros sin fin**: cada paso se ejecuta como `{delta}` (con signo, multiplicado por **Paso**). El tipo de encoder (habitual / bit de signo / centro 64) se ajusta en la fila. | Potenciómetro → `Pan {delta}` (seleccione antes proyectores) |

**Marcadores en el comando:** `{value}` (valor del fader en el rango Desde–Hasta), `{delta}` (pasos del encoder, p. ej. `+1` / `-2`), `{velocity}` (velocity 0–127), `{note}` y `{number}` (número de nota / controlador / programa), `{channel}`, `{raw}` (valor en bruto 0–127).

**Start / Stop / Continue (transporte):** también puede elegir *Start*, *Stop* y *Continue* del software de música como señal (tipo en el cuadro de aprendizaje; no tienen canal ni número). Ejemplo: Start → `Timecode Play`, Stop → `Timecode Stop`.

**Pickup:** un **fader** sin motor suele estar en una posición distinta del valor del programa. Con **Pickup** el fader solo toma el control una vez que ha alcanzado o cruzado el valor actual: sin saltos al tocarlo por primera vez. Si el valor se cambió mientras tanto en otro sitio, tiene que alcanzarlo de nuevo. Funciona para `Master {value}`, `Fader {value}`, `Cuelist <nombre> Fader {value}` y el brillo o un atributo de haz de un proyector, grupo o de la selección (`Fixture 5 At {value}`, `Group front At {value}`, `At {value}`, `Zoom {value}`); los demás comandos toman el control de inmediato.

**Más tipos:** *Doble clic* (el comando se ejecuta en la segunda pulsación dentro de 0,4 s) y *Pulsación larga* (se ejecuta cuando la tecla se mantiene el tiempo ajustado, p. ej. 600 ms; soltar antes cancela). Para los faders elige una **curva**: *Lineal*, *Inicio lento* (valores finos abajo) o *Inicio rápido*. El **aftertouch** (presión sobre una tecla mantenida) y la **presión de canal** también se pueden asignar como faders. **Un fader, varios comandos:** sepárelos con punto y coma, p. ej. `Master {value}; Group front At {value}`.

**Retorno al dispositivo (LEDs, faders motorizados):** en la fila elija en **Retorno** un estado de la consola: *Blackout*, *Master*, *Selección presente*, *Cue activo*, *Timecode en marcha* o *Fader de lista de cues*. OpenCue lo envía como nota / controlador / pitch bend **con el mismo número y canal** que la señal a la salida que tiene el mismo nombre que el dispositivo: en un controlador de pads se enciende el LED, un fader motorizado se mueve. Para los estados de encendido/apagado ajusta **LED encendido / LED apagado** (la velocity; en pads con colores es el color). Solo se envía cuando el valor cambia, y tras conectar un dispositivo se vuelve a enviar todo.

Más ejemplos:

| Dispositivo | Asignación |
|---|---|
| Cambio de programa (p. ej. en un teclado) | Tecla, comando `Go Cue {number}` – el programa 5 salta al cue 5 |
| Tecla con velocity | Fader (fuente Nota), comando `Group front At {value}`, Desde 0 Hasta 100 – cuanto más fuerte, más brillante |
| Rueda de pitch bend | Fader, comando `Master {value}` |
| Banco de faders | una fila por fader (CC 1…8): `Fixture 1 At {value}`, `Fixture 2 At {value}` … |

Disparo: una tecla se dispara al **pulsar**. Un CC usado como tecla (los pads de muchos controladores) se dispara con un valor **de 64 o más**. Un fader envía como máximo **unos 40 comandos por segundo** (los movimientos rápidos se fusionan, el último valor llega siempre).

---

## 3b. Copiar filas, exportar, importar, desde un panel

- **Copiar** (icono junto a la papelera): duplica una fila con tipo y comando, la señal queda vacía; práctico para una serie de faders parecidos (fader 1 … 8).
- **Exportar / Importar** (al pie del cuadro): guarda la asignación como archivo (`opencue-midi-mapping.json`) o lee un archivo así. Al importar las filas se **añaden**; no se sustituye nada.
- **Plantilla …** (al pie del cuadro): crea una **serie** de filas – *Banco de faders* (proyectores 1...8), *Pads de cue*, *Teclas de transporte* (Go, Back, Pause, Blackout), *Master y blackout* – y luego le deja **pulsar o mover los controles uno tras otro** («Señal 2 de 8», *Omitir* continúa, Cancelar termina la serie). Así asigna cualquier controlador sin conocer los números.
- Un **campo de búsqueda** sobre la lista (señal, comando, dispositivo) y las **flechas** de cada fila (subir / bajar; desactivadas durante una búsqueda).
- **Saltar a este cue con una tecla MIDI …** en el cuadro de un **cue** (*Editar cue*): crea una asignación `Cuelist "<lista>" Go Cue <número>` y aprende la señal; el cue arranca entonces al pulsar una tecla, **en cualquier momento** (una tecla de «salto» libre). Para un cue que espera su señal dentro de una secuencia véase el disparador de cue **MIDI** (sección 5c).
- **Asignar MIDI …** en las propiedades de un **botón, interruptor o fader**: crea una asignación con el comando del panel (interruptor: comando de encendido y apagado, fader: con Desde/Hasta) y aprende enseguida la señal. La asignación permanece aunque elimine el panel.

---

## 4. Se aplica a, Ejecutar, Historial

- **Aprender señal → Se aplica a:** *Todos los dispositivos* (cualquier dispositivo que envíe esta señal dispara) o *Solo este dispositivo* (p. ej. cuando dos controladores envían los mismos números).
- **Ejecutar** desactivado: el comando solo se **escribe en la línea de comandos**, no se ejecuta (para comprobarlo o completarlo).
- **En el historial:** el comando aparece en el historial de la línea de comandos (todas las ventanas lo ven).
- No hay comprobación de señales duplicadas: dos filas con la misma señal se disparan **ambas** (el cuadro de aprendizaje le avisa).

**Seguridad:** `Delete …` y los comandos que contienen `Overwrite` **nunca se ejecutan por MIDI** (una tecla golpeada sin querer no debe destruir datos). `Clear Clear` está permitido.

---

## 5. OpenCue envía MIDI: el comando `Midi`

El comando `Midi` envía a la **salida** (elegida arriba en el cuadro; **Automática** toma el primer dispositivo real, si no el sintetizador de Windows «Microsoft GS Wavetable Synth», de modo que se oye algo enseguida):

| Comando | Efecto |
|---|---|
| `Midi Note 60` | Toca la nota Do4 (60), velocity 100, se apaga tras 0,3 s |
| `Midi Note 60 90 Ch 2 Len 1` | Nota 60, velocity 90, canal 2, durante 1 segundo |
| `Midi On 60 100` / `Midi Off 60` | Nota encendida / apagada por separado (permanece hasta que envíe `Off`) |
| `Midi CC 7 100` | Controlador 7 al valor 100 |
| `Midi PC 3` | Cambio de programa 3 |
| `Midi MSC Go 5 List 2` | Envía **MIDI Show Control** (`Go`, `Stop`, `Resume`, `AllOff`, `Restore` ...; opcionales `List <n>`, `Device <0-127>`) |
| `Midi Panic` | All notes off (todos los canales) |

Se puede combinar con botones, atajos de teclado, comandos de cue o el **control por voz** («OpenCue, MIDI note sixty»), p. ej. un cue que dispara un sonido en su software de música. También mediante la **API REST**: `POST /api/v1/command` con `Midi Note 60`; `GET /api/v1/midi` devuelve dispositivos y estado.

---

## 5b. Tiempo y tempo desde el software de música (MTC y reloj MIDI)

Dos interruptores en **Ajustes → Controles → MIDI** hacen que OpenCue siga un software de música (DAW) u otro dispositivo. Ambos reaccionan **solo al formato correspondiente y solo cuando llega de verdad algo válido**; si no, no pasa nada. Mientras uno está activado, los dispositivos en uso permanecen abiertos.

**Timecode desde MIDI (MTC).** Si el software envía *MIDI Timecode* (MTC, 24 / 25 / 29,97 / 30 fotogramas por segundo), el **timecode global** corre al compás de ese tiempo: los cues con el disparador «Timecode», el reproductor de timecode y los paneles lo siguen. Solo se acepta un **flujo sin huecos y verosímil** (tres grupos coincidentes, valores en el rango válido); el ruido, la marcha atrás y las señales ajenas se ignoran. Si su propio reloj se desvía más de 0,1 s, se ajusta a la hora correcta. **Si el flujo se detiene** (software parado, cable desenchufado), el timecode se detiene. Si el software salta a una posición estando parado (*full frame*), el timecode también salta. Un timecode que inició a mano **no** se detiene cuando falta el MTC; mientras el MTC corre, el MTC tiene prioridad. Los ajustes muestran la hora recibida y la velocidad de fotogramas.

**Envío: OpenCue como fuente de tiempo.** *Enviar Timecode (MTC)* envía el timecode global como MIDI Timecode (velocidad 24 / 25 / 29,97 / 30; cuartos de fotograma con temporización precisa, un mensaje full frame en los saltos) a la salida elegida. *Enviar MIDI clock* envía *Start* / *Stop* y el reloj al tempo del panel Audio mientras el timecode corre.

**Recibir show control (MSC).** Con *Recibir control de show* y un **ID de dispositivo** (0-127, 127 = todos), GO, STOP, RESUME, ALL_OFF y RESTORE (también con número de cue y de lista) controlan las listas de cues, p. ej. desde un programa de shows o una consola. El comando `Midi MSC ...` los envía.

**Tempo desde el reloj MIDI.** Un **reloj MIDI estable** (24 pulsos por negra, 30 a 300 BPM) fija el tempo como tempo fijo del panel Audio (como el comando `BPM 128`) y sigue los cambios de tempo. Asigne *Start*, *Stop* y *Continue* como señales (véase arriba).

Para probarlo sin software: un generador de timecode MIDI (hay programas y páginas web gratuitos) envía por un puerto MIDI virtual (en Windows p. ej. *loopMIDI*); ambos lados eligen el mismo puerto.

---

## 5c. Disparador de cue: MIDI

Además de *Go*, *Follow*, *Timecode* y *Audio*, un cue puede tener el disparador **MIDI**: espera entonces **una señal MIDI** y se dispara cuando llega: una **secuencia que toca con un teclado, un pad o un pedal**. En el cuadro del cue (*Editar cue*) elija el disparador *MIDI* y después escoja la **señal** (o pulse **Aprender señal** y golpee la tecla; se rellena por usted; el aprendizaje funciona en el ordenador de la consola). En la lista de cues también puede escribirla en la celda del disparador (`midi note c4`, `midi cc 20 64`, `midi pc 5 ch 2`) o usar el comando `Cue 3 Trigger Midi Note 60` (véase *Línea de comandos*).

| Señal | El cue se dispara … |
|---|---|
| **Nota** (tecla / pad), número 0–127 | … cuando se pulsa la tecla (Note On; soltarla no hace nada). |
| **Controlador (CC)**, número 0–127, umbral 1–127 (por defecto 64) | … cuando el valor del controlador **alcanza** el umbral subiendo desde abajo. Un pad enviado como CC (127) se dispara de inmediato; un fader se dispara cuando se empuja más allá del umbral, y otra vez después de haberlo bajado por debajo y subido de nuevo. |
| **Cambio de programa**, número 0–127 | … cuando se elige este programa en el dispositivo. |

Cada señal se puede limitar a un **canal** (1–16); *Cualquiera* acepta todos los canales y todos los dispositivos.

Cómo funciona:
- Como el disparador de audio, el cue se dispara cuando es el **siguiente cue** de una lista en marcha: primero inicie la lista con *Go*; después el siguiente cue MIDI espera su señal. A continuación el siguiente cue (si también tiene un disparador MIDI) espera a su vez: puede encadenar toda una secuencia a teclas o pads.
- Una breve pausa de 0,25 s tras cada disparo evita que un golpe inicie dos cues.
- El **MIDI debe estar activado** (*Ajustes → MIDI → Usar MIDI*, o el interruptor de arriba en el cuadro de asignación). OpenCue abre por sí mismo los dispositivos MIDI en cuanto algún cue tiene un disparador MIDI (para eso no necesita una fila de asignación) y los libera cuando ningún cue necesita ya el MIDI. Los dispositivos que haya desmarcado en *Ajustes → MIDI* permanecen cerrados.
- El disparador funciona para cada lista de cues por separado y también desde el punto de vista de los dispositivos remotos: la señal procede de los dispositivos MIDI del **ordenador de la consola**.
- **Diferencia con la asignación** (sección 3): una fila de asignación ejecuta un comando **en cualquier momento** (p. ej. `Go`, o `Cuelist "Main" Go Cue 5` = saltar allí). El disparador de cue forma parte del **propio cue** y solo cuenta mientras el cue es el siguiente en la cola. Ambos se pueden usar juntos; una señal usada por los dos hace las dos cosas.

---

## 6. Cuando no funciona

| Problema | Solución |
|---|---|
| Dispositivo no reconocido | Otro cable/puerto USB; **Ajustes → Entradas y salidas** actualiza los dispositivos cada pocos segundos; muchos dispositivos necesitan un momento tras conectarlos. |
| «¿en uso?» en el dispositivo | **Otro programa** (software de música, el editor del fabricante) ha abierto el dispositivo; en Windows normalmente solo **un** programa puede leerlo. Cierre el otro programa y después desactive y vuelva a activar **MIDI activado**. |
| El monitor no muestra nada | El monitor solo funciona mientras el cuadro está abierto. ¿Está activado **MIDI activado**? |
| Un cue con el disparador **MIDI** nunca se dispara | Solo se dispara cuando es el **siguiente cue** de una lista **en marcha** (inicie antes la lista con *Go*). *MIDI activado* debe estar activo, el dispositivo no debe estar desmarcado en *Ajustes → MIDI*, y el número, el canal y el tipo deben coincidir con lo que muestra el monitor al pulsar la tecla (use *Aprender señal* en el cuadro del cue). |
| Una tecla no dispara nada | Compruebe canal / dispositivo en «Se aplica a»; pruebe el comando a mano en la línea de comandos; ¿se ilumina la fila en el cuadro? (entonces la señal llega y el problema es el comando). |
| El fader salta | Active **Pickup** en la fila (master y fader): el fader solo toma el control una vez que ha alcanzado el valor actual. |
| El software de música y OpenCue deben conectarse | Windows necesita para ello un **puerto MIDI virtual** (gratuito, p. ej. *loopMIDI*). Aparece entonces como entrada/salida en ambos programas. |

---

## 7. Límites

- **Tabletas:** el iPad (Safari) no puede hacer MIDI en el navegador. Los dispositivos MIDI pertenecen al ordenador de la consola; puede editar la asignación desde cualquier dispositivo.
- **Varios programas:** en Windows normalmente solo **un** programa lee un dispositivo MIDI (véase «¿en uso?»). Las versiones más recientes de Windows (*Windows MIDI Services*) pueden cambiarlo; OpenCue solo abre dispositivos cuando hace falta y los libera con **MIDI activado** desactivado.
- **El MIDI de red y los puertos virtuales** los configura el sistema operativo (p. ej. *loopMIDI*, *rtpMIDI*); aparecen entonces como cualquier dispositivo.
- **Perfiles de controlador:** en lugar de perfiles fijos para modelos concretos hay **plantillas con una serie de aprendizaje**; funcionan con cualquier controlador. Los colores de los LED (velocities) difieren según el dispositivo; se ajustan en el retorno como *LED encendido / LED apagado*.
- **Varias asignaciones entre las que alternar** (p. ej. «escenario» y «ensayo»): como archivos mediante **Exportar / Importar** en el cuadro; no hay un interruptor aparte.
- El pitch bend, el aftertouch y la presión de canal se evalúan como faders; no hay posición de canción y no hay eventos MIDI en el flujo WebSocket de la API.
- Aún no probado con todos los dispositivos: faders, encoders, pads y retorno se han probado con mensajes artificiales; el **monitor** del cuadro muestra lo que su dispositivo envía realmente.
