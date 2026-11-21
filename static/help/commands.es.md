# Línea de comandos – Referencia de comandos

La **línea de comandos** controla OpenCue escribiendo, al estilo de las consolas de iluminación profesionales. Complementa el manejo con ratón y táctil con comandos cortos que puede escribir, encadenar y guardar dentro de cues. Está disponible como panel **Línea de comandos** (*Editar → Añadir panel…*); los paneles **Teclado numérico de comandos** y **Botones de comando** escriben en la misma línea de entrada para el manejo táctil.

Cada comando se ejecuta en el servidor y el resultado se comunica a **todos** los dispositivos conectados: la lista de proyectores, la lista de cues y el programador se actualizan en todas partes a la vez, no solo donde usted escribió.

> Las palabras de comando están en inglés, como en las consolas de iluminación. Las mayúsculas y minúsculas **no** importan en comandos, atributos y nombres.

---

## 1. La idea en un minuto

Cada comando sigue el mismo patrón: **qué** – **cuál** – **valor**.

| Acción / objeto | ID / rango | Propiedad / destino |
|---|---|---|
| `Fixture` | `1` | – |
| `At` | – | `80` |
| `Store` | `Cue 1.5` | – |
| `Cue` | `1` | `Fade 3` |
| `Cuelist` | `Show` | `Go` |

- La **acción o el objeto** va siempre primero (`Fixture`, `Group`, `At`, `Color`, `Pan`, `Zoom`, `Store`, `Cue`, `Go`, `Cuelist` …).
- El **ID o rango** indica qué se ve afectado: un número de proyector (FID), un nombre, un número de cue, el nombre de una lista de cues o un rango (`1 Thru 10`).
- La **propiedad o destino** es el valor propiamente dicho: porcentaje, grados, tiempo, nombre, color.
- Los comandos **se apoyan unos en otros**, como en una consola real: primero se selecciona (`Fixture 1 Thru 4`), después un comando de valor (`At 80`) actúa exactamente sobre esa selección. La selección es **compartida por todos los dispositivos**: un clic en la lista de proyectores en una pantalla y un comando `Fixture` en otra actúan sobre la misma selección.
- El texto con espacios (un nombre de cue, un nombre de lista) va entre comillas dobles: `Label Cue 1 "Intro scene"`. Una palabra entre comillas es siempre un **nombre**, nunca una palabra de comando, de modo que también se puede direccionar un grupo llamado «Color».
- La entrada se valida: números no válidos (`Zoom abc`), atributos o nombres desconocidos y valores que faltan dan un mensaje de error **sin cambiar nada**.

```
Fixture 1 Thru 4 At 80
Fixture 1 Thru 4 Color Red
Store Cue 1 "Opening"
Go
```

---

## 2. Seleccionar proyectores y grupos

| Comando | Efecto |
|---|---|
| `Fixture 1` | Selecciona el proyector FID 1 (sustituye la selección actual). |
| `Fixture 1 Thru 10` | Selecciona los FID 1 a 10. |
| `Fixture 1 + 3` | Selecciona los FID 1 **y** 3 (combine tantos como quiera con `+`). |
| `Fixture 1 Thru 5 + 10` | Selecciona los FID 1–5 y también 10. |
| `Fixture 1 Thru 10 - 5` | Selecciona los FID 1–10 **sin** 5 (un `-` con espacios quita; se permiten varios: `- 5 - 7 Thru 8`). |
| `Next` / `Previous` | Selecciona el **proyector siguiente / anterior** por FID (da la vuelta; sin selección `Next` = el primero, `Previous` = el último). Recorra los proyectores uno por uno. |
| `Fixture "Head 2"` | Selecciona el/los proyectores con este **nombre** (también combinable con `+`). |
| `Group 1` | Selecciona el 1.er grupo de la lista de grupos. |
| `Group 1 Thru 4` | Selecciona los proyectores de los grupos 1 a 4. |
| `Group Front` | Selecciona el grupo con este **nombre** (`Group "Front Truss"` cuando contiene espacios). |

`Group N` significa el **N-ésimo grupo creado**. El nombre es más sencillo y robusto: `Group Front` funciona sea cual sea el orden.

Una palabra suelta se puede escribir sin comillas si no coincide con una palabra de comando y el nombre existe de verdad. En caso contrario ponga entre `"…"` los nombres con espacios, comas, puntos y comas o `+`, y los nombres que parecen un comando o un número.

### Crear, renombrar, eliminar grupos

La **selección actual** se puede guardar como grupo:

| Comando | Efecto |
|---|---|
| `Store Group "Front"` | Crea el grupo a partir de la selección actual. |
| `Store Group "Front" Merge` | Si existe: la selección se **añade**. |
| `Store Group "Front" Overwrite` | Si existe: los miembros se **sustituyen**. |
| `Label Group Front "Stage front"` | Renombra (también funciona `Set Group 2 Name "Stage front"`, también por número). |
| `Delete Group Front` | Elimina el grupo (`Delete Group 2` por número); los proyectores se quedan. |

Sin selección `Store Group` informa de un error. Un nombre existente (sin distinguir mayúsculas) nunca se sobrescribe en silencio. Un proyector pertenece como máximo a un grupo.

---

## 3. Ajustar valores: At / Full

Actúa sobre los proyectores **seleccionados en ese momento** (canal de dimmer).

| Comando | Efecto |
|---|---|
| `At 80` | Dimmer al 80 % (también funciona `At 80%`). |
| `At Full` | Dimmer al 100 %. |
| `At At` | **Todo encendido**: dimmer 100 % **y color blanco** (los proyectores sin color solo reciben el dimmer). **Sin selección afecta a TODOS los proyectores** (la selección queda vacía), lo contrario de `Clear Clear`. Con una selección solo se enciende esa selección. También posible: `Fixture 5 At At`, `At At Color Red` (todo encendido, rojo). |
| `Zero` | Selección al 0 % (igual que `At 0`). |
| `Full` | Forma corta sin «At» delante; también 100 %. |
| `At 0` | Dimmer al 0 % (apagado). |
| `At +10` / `At -10` | Sube / baja el valor actual del dimmer en 10 puntos porcentuales. |

Los valores se limitan a 0–100 %. `At +` / `At -` se refiere al último valor ajustado en el programador para cada proyector (o al valor DMX que se está emitiendo si aún no se ha programado nada).

Los proyectores afectados reciben una marca de estado roja en la lista de proyectores: ahora están «en el programador» y se pueden guardar con `Store Cue`.

### Master (brillo general)

`Master` (abreviado `GrandMaster`) escala la salida de **todos** los canales de dimmer en porcentaje. El valor por defecto es 100 %. El valor permanece hasta que lo cambie y se guarda con el archivo de show.

| Comando | Efecto |
|---|---|
| `Master 80` / `Master At 80` | Brillo general 80 % (la palabra `At` es opcional). |
| `Master Full` | 100 %. |
| `Master -10` / `Master +10` | Baja / sube 10 puntos porcentuales. |

El master solo escala canales de dimmer; los colores y el pan/tilt permanecen sin cambios. (El **fader de una lista de cues** es otra cosa; véase el capítulo 10.)

### Blackout

`Blackout` pone el **brillo de todos los proyectores a 0** y lo restablece con el siguiente `Blackout`. Es un interruptor, independiente del master.

| Comando | Efecto |
|---|---|
| `Blackout` | Alternar. |
| `Blackout On` / `Blackout Off` | Activar / desactivar (también funcionan `1`/`0`, `True`/`False`). |

**El blackout tiene prioridad sobre todo**: faders, comandos, cues, transiciones y efectos en marcha. Mientras está activo, el brillo de cada proyector permanece en 0, en la salida DMX **y** en la simulación 3D. Los valores se conservan: durante un blackout puede cambiar el brillo con normalidad y, tras `Blackout Off`, aparece el estado **ajustado por última vez**. Los proyectores **sin** canal de dimmer (RGB puro) se oscurecen mediante su color. Un botón de bombilla que pulsa en la barra de herramientas muestra un blackout activo; un clic lo alterna. El estado se aplica a todos los dispositivos pero **no** se guarda en el show.

### Timecode: `Timecode` / `TC`

El timecode global (el reloj interno) también se puede controlar por comando, por ejemplo en el campo **CMD** de un cue (`Timecode Play` inicia el reloj cuando el cue se dispara).

| Comando | Efecto |
|---|---|
| `Timecode` | Muestra el estado (hora, en marcha/parado, velocidad). |
| `Timecode At 4.3` | Salta a 4,3 s (también `00:00:04.300`, `1:04.300`; como máximo 100 h). |
| `Timecode At 4.3 Play` | Salta e inicia (`Reverse` inicia hacia atrás). |
| `Timecode +5` / `Timecode -2` | Relativo: 5 s hacia delante / 2 s hacia atrás. |
| `Timecode Play` / `Reverse` | Correr hacia delante / hacia atrás. |
| `Timecode Pause` | Pausa. |
| `Timecode Stop` (`Reset`) | Detener y poner a 00:00:00.000. |
| `Timecode Rate 2` | Velocidad (0,1 … 8; también funciona `0.5x`). |

Un salto no dispara los cues de timecode; solo lo hace la marcha hacia delante.

### Audio y tempo: `Tap` / `BPM` / `Audio`

Controla el panel *Audio* (véase la guía *Audio*); también utilizable en el campo **CMD** de un cue.

| Comando | Significado |
|---|---|
| `Tap` | Marcar el tempo: a partir del segundo golpe el tempo se fija con sus golpes (manual) y el pulso empieza en el golpe. |
| `BPM` | Muestra el tempo y el modo. |
| `BPM 128` | Tempo fijo (30 … 300). |
| `BPM Auto` | Vuelve a la detección automática. |
| `BPM Half` / `BPM Double` | Divide por dos / duplica el tempo (cuando la detección encontró el doble / la mitad). |
| `Audio Start` / `Audio Stop` | Abre la fuente elegida / la cierra. |
| `Audio Demo` | Inicia el ritmo de demostración. |
| `Audio` (`Audio Status`) | Muestra si el audio está en marcha, el tempo y el nivel. |

### Enviar OSC: `Osc`

`Osc /address [value ...]` envía un mensaje OSC al destino ajustado en **Controles → OSC ...** (*Enviar a*): `Osc /opencue/go`, `Osc /light/1 0.5 hello`. Los valores son números (los enteros se envían como enteros), `true` / `false` o texto. Sin destino, el comando lo indica. Véase la guía *Programación, hora del día y OSC*.

### Enviar MIDI: `Midi`

Envía MIDI a la salida elegida (véase la guía *MIDI*): `Midi Note 60 [velocity] [Ch 2] [Len 0.5]` toca una nota y la apaga de nuevo, `Midi On 60` / `Midi Off 60` por separado, `Midi CC 7 100` ajusta un controlador, `Midi PC 3` un cambio de programa, `Midi Panic` apaga todas las notas.

---

## 4. Color y posición: Color / RGB / Pan / Tilt

También actúan sobre los proyectores **seleccionados en ese momento**.

| Comando | Efecto |
|---|---|
| `Color Red` | Ajusta el color a rojo (color con nombre, lista abajo). |
| `Color #FF8000` | Color en hexadecimal (también funciona la forma corta `#F80`). |
| `Color 255 128 0` | Color como tres valores 0–255 (rojo / verde / azul). |
| `RGB 255 0 0` | Lo mismo (notación de consola). |
| `Pan 180` | Mueve el pan a 180°. |
| `Tilt -45` | Mueve el tilt a -45°. |
| `Pan 50%` | Pan en porcentaje del rango (0–100 %; 50 % = centro). |
| `Pan +10%` / `Tilt -5%` | Relativo al valor actual, en porcentaje del rango. |
| `Pan +15` / `Tilt -15` | Relativo en grados (con signo). |

**Colores con nombre:** `Red`, `Green`, `Blue`, `White`, `Black`, `Yellow`, `Cyan`, `Magenta`, `Orange`, `Pink`, `Purple`, `Amber`, `Lime`, `Teal`, `Violet`, `LightBlue`, `Warm`, `Cool`.

**Grados para pan/tilt:** OpenCue lee el rango real de movimiento (rango físico) del perfil GDTF del proyector, por lo que proyectores distintos pueden quedar algo diferentes con el mismo valor en grados. Si el perfil no tiene rango, se aplica el predeterminado: **pan de -270° a +270°, tilt de -135° a +135°**.

---

## 5. Atributos de haz y canales: Zoom, Gobo, CH …

Además del brillo, el color y la posición se puede ajustar **cada canal** de un proyector, de dos maneras: por **nombre de atributo** (porcentaje, la misma lógica que los faders del programador) o directamente por **número de canal** o **nombre** (como «DMX directo»).

### Atributos en porcentaje

| Comando | Efecto |
|---|---|
| `Zoom 50` | Zoom al 50 % (también `Zoom Full`, `Zoom Half`, `Zoom Min`, `Zoom 50%`). |
| `Focus 25` | Foco. |
| `Gobo 40` / `Gobo2 40` | Rueda de gobos 1 / 2 (selección; número = porcentaje del canal). |
| `GoboSpin 30` / `Gobo2Spin 30` | Rotación / posición de la rueda de gobos. |
| `Prism 100` | Prisma. |
| `Strobe 0` (`Shutter 0`) | Shutter / estroboscopio. |
| `Zoom +10` / `Zoom -20` | Relativo al valor actual (puntos porcentuales). |

Todos los valores van de 0 a 100 y se guardan como los faders: `Store Cue` los toma. Si a un proyector le falta el canal (un dimmer puro no tiene zoom) se omite y el retorno lo dice: `OK: Zoom 50 applied to 3 fixtures (Zoom not available on 1 of 3 fixtures)`. Si **ninguno** de los proyectores seleccionados tiene el canal, es un error y no cambia nada.

### Canales por número: `CH` / `Channel`

| Comando | Efecto |
|---|---|
| `CH6 128` | Canal 6 **del proyector** (1 = primer canal) al valor DMX 128. |
| `Channel 6 128` | Lo mismo, escrito con un espacio (también funciona `CH 6 128`). |
| `CH6 50%` | Con `%`: porcentaje en lugar de valor DMX (50 % = 128). |
| `CH6 +20` | Relativo: 20 pasos DMX más (`-20` menos). |
| `CH6 Full` | 255 (también `Half` = 50 %, `Min` = 0). |

El número de canal se refiere al **orden en el modo del proyector** (visible en la pestaña *DMX directo* del programador), no a la dirección DMX: `Fixture 5 Thru 8 CH6 255` ajusta el 6.º canal de cada proyector seleccionado esté donde esté patcheado. El valor es **0–255** como en DMX directo.

### Canales por nombre

Cada nombre de canal GDTF del proyector se puede usar directamente como cláusula (valor en **porcentaje**):

```
Fixture 1 Frost 50        Iris 30        Cyan 100
Channel Frost1 50         CH Frost 50
```

El nombre se puede abreviar mientras siga siendo inequívoco (`Frost` por `Frost1`); hay nombres cortos habituales integrados (`Cyan`, `Magenta`, `Yellow` para canales CMY, `Red`/`Green`/`Blue` para canales RGB, `Intensity` para el dimmer). El autocompletado muestra qué nombres tiene un proyector (capítulo 14).

Los canales con atributo propio (dimmer, pan, tilt, zoom, foco, rueda de gobos, prisma, shutter) se guardan como ese atributo; todos los demás (frost, iris, rueda de color, canales finos …) como valores de canal en bruto. `Store Cue` toma ambos.

---

## 6. Variables, efectos, manual

Las variables (presets) y los efectos se pueden aplicar a la **selección actual**, solos o como cláusula tras una selección como cualquier otro atributo.

| Comando | Efecto |
|---|---|
| `Variable "Warm White"` | Aplica la variable **y la enlaza**: los proyectores la siguen hasta que un valor, un efecto o un cue toma el atributo (cambie la variable y los proyectores cambian con ella). Formas cortas: `Var`, `Preset`. |
| `Effect Rainbow` | Asigna el efecto (la categoría se deduce del efecto). Varios proyectores funcionan con un desfase de fase como en la lista desplegable. |
| `Effect Off` | Termina **todos** los efectos de la selección; `Effect Off color position` solo las categorías nombradas. |
| `Manual` | Vuelve a **manual**: libera el enlace de variable **y** el efecto de todas las categorías; los últimos valores de salida permanecen. |
| `Manual color` | Solo esa categoría (`dimmer`, `color`, `position`, `zoom`, `focus`, `gobo`, varias seguidas, o `all`). |

Los nombres de variables y efectos son únicos en OpenCue y no distinguen mayúsculas. Con espacios, o bien entre `"…"` o simplemente uno tras otro (`Variable warm white`). Un nombre desconocido da un error con la lista de los existentes. El autocompletado sugiere variables (con su tipo) y efectos (con su categoría).

```
Fixture 1 Thru 4 Variable "Warm White" Variable Wide Effect Wave
Group Front Manual color
Effect Off
```

---

## 7. Comandos combinados

Los comandos de selección y de valor/atributo se pueden combinar en **una sola línea**, equivalente a dos comandos seguidos pero más rápido de escribir:

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

Varias cláusulas de atributo pueden seguirse directamente (`Fixture 1 At 80 Color Red` ajusta dimmer Y color de una vez). Si una cláusula contiene un error (errata en el atributo, número no válido, un canal que ningún proyector tiene), **ni** la selección **ni** ningún valor cambia.

---

## 8. Comandos encadenados (coma o punto y coma)

Varios comandos completos se pueden encadenar en **una** línea, separados por coma o punto y coma. Se ejecutan uno tras otro:

```
Fixture 1 At 100, Fixture 2 At 50
Fixture 1 Color Red; Fixture 2 Color Blue; Fixture 3 At 0
```

Si una parte falla, las demás se ejecutan igualmente; el registro muestra todos los resultados parciales en una línea separados por `|`. Las comas y los puntos y comas **entre comillas** (por ejemplo en un nombre de cue) se ignoran correctamente: `Label Cue 1 "Act 1, scene 2"` no se divide.

---

## 9. Clear: `Clear` frente a `Clear Clear`

| Entrada | Efecto |
|---|---|
| `Clear` | Solo libera la selección actual. Los valores programados permanecen. |
| `Clear Clear` | **Restablecimiento completo:** devuelve **todos** los proyectores por completo: dimmer, color y pan/tilt (según *Ajustes → Valores predeterminados → Clear Clear*: por defecto dimmer 0 %, color blanco, pan/tilt 0°; los proyectores sin canal de dimmer quedan negros), zoom, foco, ruedas de gobos 1 y 2 con rotación, prisma, estroboscopio **y todos los demás canales del proyector** (frost, iris, rueda de color, velocidad, canales finos …) a 0. Termina todos los efectos, vacía el programador y libera la selección. |
| `Clear` dos veces **en 1,0 segundo** | Igual que `Clear Clear`: escribir `Clear` dos veces rápidamente activa el restablecimiento completo. |
| `Clear` … (más de 1,0 s) … `Clear` | Dos acciones independientes «liberar selección»; **ningún** restablecimiento. |

---

## 10. Listas de cues: seleccionar por nombre, Go, fader, gestionar

Los comandos de cue actúan sobre la **lista de cues activa** (lista desplegable del panel de la lista de cues). Con `Cuelist` (equivalentes: `QList`, `Q-List`, `CL`, `List`, `Exec`) puede direccionar cualquier lista **por nombre**, sin distinguir mayúsculas; los nombres son únicos en OpenCue, así que siempre está claro. Como en todas partes: **primero la categoría, luego el nombre**; un nombre de lista suelto (`Show Go`) no es un comando.

| Comando | Efecto |
|---|---|
| `Cuelist Show` | Convierte «Show» en la lista **activa**. |
| `Cuelist "Cue List 1"` | Nombre con espacios (también sin comillas, si es inequívoco: `Cuelist Cue List 1`). |
| `Cuelist 2` | La 2.ª lista en el orden de la lista desplegable (como `Exec 2`). |
| `Cuelist Show Go` | Avanza la lista «Show» un paso, **sin** cambiar la lista activa. |
| `QList Show Go` | Lo mismo con la categoría `QList`. |

### Crear, renombrar, duplicar, eliminar listas

| Comando | Efecto |
|---|---|
| `Cuelist New "Act 1"` | Crea una lista nueva (los nombres son únicos; sin nombre: `Cue List 1`, `Cue List 2` …). Si no había ninguna, pasa a ser la activa. |
| `Cuelist Show Rename "Act 1"` | Renombra (un nombre ya usado se rechaza). |
| `Cuelist Show Duplicate` | Copia con todos los cues, nuevos ID, nombre `Show (copy)`; con un nombre: `Duplicate "Backup"`. |
| `Cuelist Show Delete` | Elimina la lista (también funciona `Delete Cuelist Show`), **sin** confirmación; una transición en curso termina. |

Una lista llamada «New» se alcanza entre comillas: `Cuelist "New" Go`. Tras el nombre de la lista puede seguir cualquier comando de cue; se aplica entonces exactamente a esa lista y el retorno la nombra entre corchetes (`OK: Go Cue 1 [Show]`).

### Reproducción

| Comando | Efecto |
|---|---|
| `Go` | Siguiente cue (al final de la lista Go salta al primer cue, como el botón). |
| `Go Cue 3` / `Go 3` | Salta directamente al cue 3 (transición suave con su tiempo de fade). |
| `Goto Cue 3` | Igual que `Go Cue 3`. |
| `Back` / `Go Back` | Cue anterior. |
| `Pause` / `Resume` | Pausa / continúa la transición en curso. |
| `Stop` | Aborta la transición (los valores permanecen); también termina todos los efectos en marcha. |
| `Fader 50` | El **fader** de la lista (mezcla entre valor manual y cue, como el fader del ejecutor) al 50 %. También `Fader Full`, `Fader +10`, `Fader At 30`. |
| `Off` / `Off Exec 1` / `Off Cuelist Show` | Restablece el estado de cue activo de la lista activa / la 1.ª / la nombrada. (Los ejecutores aún no son objetos separados; `Exec N` significa la N-ésima lista. `Off` no desvanece los últimos valores DMX.) |

```
Cuelist Show Go                Go Cue 3
Cuelist "Encore" Goto Cue 1    QList "Encore" Fader 40
Cuelist Show Fader +10         Cuelist 2 Back
```

---

## 11. Gestionar cues

Todos los comandos de cue actúan sobre la **lista de cues activa** o, con un `Cuelist <name>` delante, sobre la lista nombrada.

| Comando | Efecto |
|---|---|
| `Store Cue 1` | Guarda un cue nuevo con **cada cambio respecto al cue anterior** (véase abajo), incluido un *Clear* que lo dejó todo oscuro. Los valores que tocó explícitamente siempre se incluyen. |
| `Store Cue 1.5` | Los números decimales permiten insertar más tarde entre cues existentes. «Antes» es entonces el cue 1 (el cue con el siguiente número menor), sea cual sea el cue activo ahora. |
| `Store Cue 1.5 CueOnly` | Al insertar en medio, el **cue siguiente** conserva su aspecto anterior: los valores que el cue nuevo cambia y que el cue siguiente no fija por sí mismo se fijan allí con el estado antiguo. Sin `CueOnly` el cue siguiente los hereda por tracking. |
| `Store Cue 4 "Intro"` | Con un nombre (si no el cue se llama «Cue 4»). |
| `Store Cue 3 Merge` | Si el cue 3 existe: solo entra lo que difiere en la imagen respecto a **este cue**, el resto permanece. Sin `Merge`/`Overwrite`, `Store Cue 3` informa de un error en lugar de crear un número duplicado. |
| `Store Cue 3 Overwrite` | Si el cue 3 existe: su contenido se sustituye por completo por los cambios respecto al cue anterior (nombre, tiempos, disparador permanecen). |
| `Store Cue 6 Absolute` | El cue reproducirá después **exactamente el estado que vio al guardar** (todos los proyectores, todos los canales). También funciona con un programador vacío: el estado actual se guarda como instantánea. `Relative` (por defecto) reproduce solo sus cambios. |
| `Update` | Lleva al cue **activo** todo lo que en la imagen difiere de ese cue (solo los canales cambiados). Sin complemento se aplica el valor predeterminado de *Ajustes → Valores predeterminados → Nuevos cues → Update* («Preguntar cada vez» actúa como tracking para el comando). |
| `Update Tracking` | Los cues siguientes que no fijan por sí mismos estos valores los toman al reproducirse. |
| `Update CueOnly` | Como `Update Tracking`, pero el cue siguiente conserva su aspecto anterior. |
| `Delete Cue 3` | Elimina el cue 3. Con un rango: `Delete Cue 3 Thru 5`. |
| `Move Cue 1 At 5` | Renumera el cue 1 a 5 (la lista se reordena). Si el número de destino existe, se informa de un error. |
| `Label Cue 1 "Intro"` / `Set Cue 1 Name "Intro"` | Renombra el cue 1. |

**Cómo se guarda un cue.** Un cue solo contiene lo que cambia respecto al cue anterior (tracking). Al guardar, OpenCue busca por tanto el cue que se reproduciría **antes** del nuevo (el que tiene el siguiente número menor, también para `1.5` en medio de la lista), lee su estado y guarda exactamente las diferencias con la imagen que ve ahora. Eso incluye un *Clear*: lo deja todo oscuro y es, por tanto, un cambio grande. Si no hay un cue anterior (el primero de la lista), solo recibe los valores que tocó explícitamente. Si nada cambió, `Store Cue` lo dice y no crea ningún cue (salvo con `Absolute`).

**La indicación «cambiado».** La marca roja de la lista de proyectores y los puntos de las pestañas muestran lo mismo: lo que ahora difiere del **cue activo** (además de lo que manejó a mano). Con varias listas cuenta el cue activo de la lista **usada más recientemente** (Go, Back, salto, selección, guardado). Mientras esa lista hace una transición, la indicación se queda como está; con un fader de ejecutor por debajo del 100 % está vacía (la salida se mezcla a propósito). Es solo una indicación: lo que se guarda es siempre el cambio respecto al cue anterior.

**Tras guardar**, el cue guardado es el **cue activo** de la lista (la imagen coincide con él); el siguiente `Go` inicia por tanto el cue que le sigue. El programador se vacía para los proyectores guardados (la marca roja desaparece). Los cues nuevos reciben por defecto `Fade = 0.0 s` (cambio seco).

**Relativo y absoluto:** cada cue **guarda siempre ambos** en el archivo de show: los *cambios* (lo que tocó) y el *estado completo* de todos los proyectores en el momento de guardar (dimmer, color, posición, gobo, zoom, foco y cada otro canal; las variables siguen siendo marcadores). La **reproducción** decide qué ocurre con Go:

- **Relativo** (tracking, por defecto): solo se ajustan los cambios guardados, todo lo demás queda como lo dejó el cue anterior.
- **Absoluto**: cada proyector se ajusta exactamente al estado guardado; así el cue 6 se ve exactamente como al guardarlo, aunque antes haya pasado por los cues 1-5. También terminan en todos los proyectores los efectos que el cue no tiene.

El valor por defecto para los cues nuevos se ajusta en *Ajustes → Valores predeterminados → Nuevos cues* (allí también disparador, delay, tiempo de fade, entrada/salida de efectos, MIB y qué hace *Update*). `Store Cue 6` sin complemento toma siempre estos valores por defecto; lo que indique explícitamente (`Absolute`, `Relative`) prevalece. En el cuadro de guardado puede cambiarlo para un solo cue, más tarde en el cuadro de edición, haciendo doble clic en la columna **Reproducción** o con el comando `Cue 6 Mode Absolute` / `Cue 6 Mode Relative`. Como el estado se guarda siempre, cualquier cue se puede cambiar en cualquier momento. En *Valores predeterminados → Inicio del programa* ajusta también cómo se encuentra OpenCue tras iniciarse (grand master del show o un valor fijo, blackout activado/desactivado) y el nivel del fader de ejecutor para las listas nuevas. Los cues antiguos sin estado guardado se comportan, siendo absolutos, como el tracking de la lista hasta ese cue.

**Los efectos** son siempre un estado completo: un cue recuerda todos los efectos que estaban en marcha cuando se guardó. `Update` también lo toma: un efecto que haya detenido sale del cue.

### Editar cues en la lista (ratón y táctil)

- **Una sola celda:** haga doble clic en una celda (nombre, disparador, tiempos, MIB, CMD …) para editarla directamente en la lista. El cuadro de edición (clic derecho → *Editar*) sigue para todo a la vez.
- **Varios cues a la vez:** arrastre un **rectángulo** sobre las celdas con el ratón (en táctil: mantenga brevemente, después arrastre). Se seleccionan **solo las celdas dentro del rectángulo**, no la fila entera. Un **doble clic** en una celda seleccionada cambia entonces **todas las celdas seleccionadas de esa columna** a la vez, por ejemplo poner el tiempo de fade de varios cues a 1. Lo mismo funciona con filas enteras seleccionadas con `Ctrl`-clic o `Mayús`-clic. Un clic simple vuelve a seleccionar una fila entera. El número de cue se cambia siempre de uno en uno (los números son únicos).
- **Disparadores con símbolos:** Go, Follow, Timecode, Audio, MIDI y Hora del día tienen cada uno un símbolo, en la lista y como fila de botones en el cuadro de edición (con una breve nota sobre cuándo arranca el cue).
- **Mover:** cambie el número del cue; el cue se traslada a su nuevo lugar.
- **Copiar:** seleccione cues → **Copiar** (o clic derecho → *Copiar …*). Elija la lista y el número de la primera copia; las demás conservan el espaciado de los originales. Los números que ya existen nunca se sobrescriben; entonces no se copia nada y OpenCue nombra los números ocupados.
- **Deshacer:** `Ctrl+Z` / `Ctrl+Y` deshacen y rehacen cambios en cues (véase *Atajos de teclado*).

### Propiedades de los cues: `Cue <number> <property> <value>`

Todo lo que está en el cuadro de edición (y en las columnas de la lista de cues) se puede ajustar por comando. En lugar de un número también funciona un rango: `Cue 1 Thru 5 Fade 2` cambia los cues 1 a 5.

| Comando | Efecto |
|---|---|
| `Cue 1 Fade 3` / `Cue 1 Delay 1.5` | Tiempos generales (dimmer) en segundos. |
| `Cue 1 Color Fade 2` / `Color Delay` | Tiempo propio para el color (también funciona `Colour`). |
| `Cue 1 Pos Fade 4` / `Pos Delay` | Tiempo propio para la posición (también funciona `Position Fade`). |
| `Cue 1 Beam Fade 0` / `Beam Delay` | Tiempo propio para el haz (gobo, prisma, estroboscopio, foco …). |
| `Cue 1 Zoom Fade 2` / `Zoom Delay 1` | Tiempo propio para el zoom. |
| `Cue 1 Color Fade -` | Un `-` (o `default`) devuelve el grupo al tiempo general. |
| `Cue 1 FX In 2` / `FX Out 1` | Entrada/salida de los efectos en segundos (también funcionan `Effect In` / `Effect Out`). |
| `Cue 1 Trigger Go` / `Follow` | Disparador del cue. |
| `Cue 1 Trigger Timecode 00:01:30` | Disparo por el timecode global (hora como con `Timecode At`). |
| `Cue 2 Trigger Audio Beat 4` | Disparo por la música: se dispara en cada 4.º pulso una vez que es el siguiente cue (el panel Audio debe estar en marcha). Fuentes: `Beat`, `Kick`, `Snare`, `Hat` (el número = cada n-ésimo, por defecto 1) y `Level`, `Bass`, `Mid`, `High`, `B1` … `B8` (el número = umbral en %, por defecto 70). |
| `Cue 2 Trigger Audio Kick` | Se dispara con el siguiente golpe de bombo. |
| `Cue 2 Trigger Audio Bass 80` | Se dispara cuando los graves alcanzan el 80 %. |
| `Cue 3 Trigger Midi Note 60` | Disparo por una señal MIDI: se dispara cuando se pulsa esta tecla, una vez que el cue es el siguiente cue de una lista en marcha. `Note` toma un número (0–127) o un nombre de nota (`Note C4`), `CC <number> [threshold]` se dispara cuando un controlador sube hasta el umbral (por defecto 64), `PC <number>` con un cambio de programa. Añada `Ch <1-16>` para un solo canal (por defecto: cualquiera). Ejemplos: `Cue 3 Trigger Midi Note C4 Ch 2`, `Cue 4 Trigger Midi CC 20 100`, `Cue 5 Trigger Midi PC 3`. El MIDI debe estar activado (guía *MIDI*, sección 5c). |
| `Cue 3 Trigger Clock 19:30 Mon-Fri` | Disparo por el **reloj**: una vez que el cue es el siguiente cue de una lista en marcha, espera a esta hora del día (y a estos días: `Mon-Fri`, `Sat,Sun`, `weekdays`, `weekend`, `daily`; sin días: todos los días; se permiten segundos: `19:30:15`). Véase la guía *Programación, hora del día y OSC*. (`Trigger Time` sigue siendo el disparador de timecode.) |
| `Cue 1 MIB Auto` (`Off` / `On`) | Move In Black. |
| `Cue 1 Mode Absolute` (`Relative`) | Reproducción: exactamente el estado guardado o solo los cambios (véase arriba). |
| `Cue 1 Cmd "Fixture 1 At 0; Go"` | Comando(s) que el cue ejecuta al dispararse (capítulo 12). |
| `Cue 1 Name "Intro"` | Nombre. |

---

## 12. CMD: asociar comandos a un cue

Cada cue tiene un campo de texto opcional **CMD** (clic derecho → Editar → sección «MIB y CMD», doble clic en la columna de la lista de cues, o con el comando `Cue 3 Cmd "…"`). Si contiene un comando, OpenCue lo ejecuta **automáticamente** cuando se dispara el cue (por `Go`, un `Follow` automático o el menú contextual «Transición aquí»), antes de que empiece la transición propiamente dicha.

Varios comandos se separan por **coma o punto y coma**:

```
Fixture 1 At 0
Fixture 3 Thru 6 Color Blue
Fixture 1 At 0; Fixture 2 Zoom 30; Cuelist Encore Go
```

El resultado aparece en el mismo historial de comandos compartido que un comando escrito, de modo que sigue siendo visible que un cue disparó una acción. El campo admite hasta 200 caracteres. CMD puede contener **cualquier** comando de esta referencia, también encadenados y combinados: un cue puede iniciar otra lista con `Cuelist Encore Go`. Las llamadas recursivas `Go Cue` son posibles, pero OpenCue no detecta bucles infinitos entre cues CMD encadenados.

---

## 13. Retorno en el registro

Cada comando ejecutado produce una línea en el área de registro del panel, con una marca de hora:

```
[20:45:01] OpenCue> Fixture 1 Thru 10
           OK: 10 fixtures selected
[20:45:07] OpenCue> At 80
           OK: At 80 applied to 10 fixtures
[20:45:12] OpenCue> Store Cue 1
           OK: Cue 1 stored
```

Los comandos erróneos se marcan en **rojo**:

```
[20:46:40] OpenCue> At 80
           At: no fixtures selected
[20:46:55] OpenCue> Go Cue 99
           Cue 99 not found
[20:47:02] OpenCue> Fixture 1 Colr Red
           Unknown attribute: Colr
```

Los comandos encadenados dan **una** línea con todos los resultados parciales separados por `|`. El registro es idéntico en **todos** los dispositivos conectados: cada comando, se haya escrito donde se haya escrito (o lo haya ejecutado el CMD de un cue), aparece en cada panel de línea de comandos abierto. El texto del registro se puede seleccionar y copiar.

---

## 14. Teclado y autocompletado

| Tecla | Efecto |
|---|---|
| `Intro` | Ejecuta el comando y vacía la entrada. |
| `Flecha arriba` | Comando anterior (más antiguo). |
| `Flecha abajo` | Comando siguiente (más reciente), o vuelta al borrador que había empezado. |
| `Tab` | Toma la primera sugerencia; cada `Tab` siguiente pasa a la siguiente. |
| `Mayús` + `Tab` | Como `Tab`, hacia atrás. |
| `Esc` | Cierra la lista de sugerencias. |

**Autocompletado:** mientras escribe (y al hacer clic en el campo) aparece sobre la entrada una lista de continuaciones adecuadas. Al principio de una línea muestra **solo las categorías** (`Fixture`, `Group`, `Cuelist`, `Cue`, `Go` …); los nombres y valores vienen después. La lista conoce el **estado actual**, no solo las palabras de comando:

- tras `Fixture ` los números (con el nombre del dispositivo) y los nombres,
- tras `Group ` los grupos; tras `Cuelist ` las listas de cues (los nombres con espacios se ponen automáticamente entre `"…"`),
- tras una selección de proyectores los atributos y exactamente los **canales que esos proyectores tienen** (`Frost1`, `Iris`, `ColorSub_C` … con el número de canal como indicación),
- tras `Go `, `Cue `, `Delete Cue ` los cues de la lista (nombrada) con sus nombres, después las propiedades (`Fade`, `Color Fade`, `FX In`, `Trigger` …),
- tras `Color ` los nombres de color, tras `Zoom ` valores (`Full`, `Half`, `Min`),
- tras `Variable ` / `Effect ` las variables (con tipo) y los efectos (con categoría); tras `Manual ` las categorías; tras `Store ` / `Delete ` / `Label ` `Cue` y `Group`; tras `Cuelist ` primero `New`; tras `Blackout ` `On` / `Off`.

Las líneas en cursiva son **indicaciones** sobre el valor esperado (`<0-100> | +<n> | -<n> (%)`, `<0-255> (DMX) | <0-100>%`) y no se pueden insertar. La lista se refiere siempre al **último comando parcial** (tras la última coma/punto y coma). Un clic en una entrada también la inserta. Toda la gramática está en el servidor; la interfaz solo muestra lo que el servidor sugiere, de modo que las sugerencias nunca difieren del analizador real.

Un pequeño **interruptor** en el extremo derecho de la línea de entrada activa y desactiva las sugerencias (guardado en la configuración de la aplicación, se aplica a todos los dispositivos).

En *Propiedades del panel → Ajustes del módulo* también puede cambiar los colores del texto, del éxito y del error del registro.

---

## 15. Chuleta

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
