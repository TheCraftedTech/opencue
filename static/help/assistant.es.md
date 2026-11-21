# Asistente de IA

El **asistente de IA** es un chat con un modelo de lenguaje que se ejecuta en **su propio ordenador** (o en otro de su red) mediante **Ollama**. No se envía nada a internet: OpenCue solo habla con la dirección de servidor que usted introduce. La IA escribe cada respuesta **por sí misma**; OpenCue no inventa textos de respuesta.

> **Estado actual:** el modo **Chat** y el modo **Trabajo** funcionan. Trabajo puede **leer** el show (proyectores con todos los detalles, grupos, listas de cues, efectos, variables), **cambiar proyectores** (brillo, color, pan / tilt, zoom ... – después de preguntarle) y dispone de una calculadora, números aleatorios y la hora. La **Guía** explica el programa a partir de los manuales (sin inventar nada) y ofrece botones que abren cuadros de diálogo (véase la sección 7).

---

## 1. Configuración

1. Instale **Ollama** (ollama.com) en este u otro ordenador y descargue un modelo una vez, p. ej. `ollama pull qwen2.5-coder:3b`. Después ya no hace falta internet.
2. En OpenCue abra **Ajustes -> Asistente de IA** y active arriba el **interruptor principal *Activar el asistente de IA*** – mientras está desactivado, el resto de la página está bloqueado.
3. En **Conexión** introduzca la **dirección del servidor** (por defecto `http://127.0.0.1:11434`) y haga clic en **Probar conexión**.
4. Elija el **modelo predeterminado** y haga clic en **Guardar** abajo a la derecha (el cuadro permanece abierto).
5. Con **Añadir panel** añada el panel **Asistente de IA**.

La página está organizada en **Conexión**, **Comportamiento** (modo de los chats nuevos, nombres de chat, lista de funciones), **Permisos** y **Avanzado**. En **Avanzado** (plegado) encuentra el tamaño de contexto, la temperatura y el tiempo de espera. La primera respuesta tras cargar un modelo tarda más: el tiempo de espera es generoso.
En **Avanzado** cada valor muestra un **«Recomendado: ...»**; el botón **Establecer valores recomendados** (al pie de los ajustes) restablece el contexto (16384), la temperatura, la respuesta más larga, el tiempo de espera, los nombres de chat y la lista de funciones. La dirección del servidor, el modelo y los permisos no se tocan.

---

## 2. Escribir

Abajo está la línea de entrada: **[botón de modo] [campo de texto] [micrófono] [enviar]**. El botón del micrófono (dictado, solo en la consola) se describe más abajo en *Dictar*.

- **Intro** envía, **Mayús + Intro** empieza una línea nueva.
- Mientras la IA trabaja ve puntos que saltan y después el texto palabra por palabra. El botón **enviar** se convierte en un botón rojo **detener**.
- Bajo cada respuesta hay una línea compacta: el **modo**, el tiempo total de la pregunta, los tokens por segundo y el modelo.
- **Pasos de razonamiento:** modelos como `qwen3` o `deepseek-r1` piensan primero y responden después. Los pensamientos están en un bloque plegable **encima** de la respuesta: mientras el modelo piensa está abierto y crece; cuando empieza la respuesta se pliega («Pensó durante 12 s»), un clic lo vuelve a abrir. Que un modelo piense o no depende del propio modelo (no hay interruptor). El razonamiento cuenta para la *Respuesta más larga*; OpenCue añade 2500 tokens de margen para ello.
- **Desplazamiento:** cuando el historial está al final del todo, sigue mientras la IA escribe. Si se desplaza hacia arriba, **su posición se mantiene**, incluso mientras se escribe más abajo. El botón redondo con flecha hacia abajo, abajo a la derecha del historial, le lleva de vuelta al final (se ilumina mientras algo sigue en marcha abajo). Al enviar un mensaje baja usted solo.
- Cada mensaje tiene un botón **copiar** al pasar el ratón por encima; el texto también se puede seleccionar.
- En el modo Chat la IA recibe con cada pregunta **todo el chat hasta ahora**. Si se hace demasiado largo para la ventana de contexto, los mensajes más antiguos se descartan (todo sigue guardado). En el modo Trabajo recibe la pregunta actual con todo lo ocurrido para ella, más un **breve resumen** de las preguntas anteriores. Los resultados solo aparecen en él para cálculos («¿y la mitad de eso?»); los datos del show, la hora y los números aleatorios se obtienen de nuevo cada vez (si no, los modelos pequeños copian respuestas antiguas y calculan de memoria).

### Dictar (voz a texto)

Haga clic en el **micrófono** junto al campo de texto: el campo se sustituye por una animación de **barras** en movimiento que siguen su voz, con el tiempo de grabación. **Marca** = hecho, la grabación se transcribe y el texto se pone en el campo (**no** se envía; léalo, corríjalo, pulse enviar); un texto que ya estuviera en el campo se conserva y las palabras nuevas se añaden. **Cruz** o `Esc` = descartar. A los 2 minutos la grabación termina sola.

- El **idioma** es el de la interfaz (uno de los seis idiomas); no hay un ajuste aparte. Las palabras técnicas (cue, dimmer, gobo, blackout ...) las conoce el reconocedor.
- La grabación usa el micrófono de la **consola** (por eso el botón solo aparece allí). Todo se ejecuta en este ordenador con *Whisper* (faster-whisper).
- El **modelo de habla** se carga una vez en el primer dictado (hace falta internet, una barra de progreso lo muestra); después el dictado funciona sin conexión. *Ajustes -> Dictado* ofrece **Rápido** (Whisper base, unos 145 MB) y **Preciso** (Whisper small, unos 484 MB, mejor para alemán, algo más lento), un botón **Cargar ahora** y el **micrófono para el dictado**. La transcripción tarda más o menos lo que la grabación o menos, según el ordenador.
- El dictado no tiene nada que ver con la **palabra de activación** (*Ajustes -> Palabra de activación*): son funciones separadas, cada una con su propio micrófono. Un resumen de todas las entradas y salidas en uso está en *Ajustes -> Entradas y salidas*.

---

## 3. Los tres modos

El **botón de modo** cuadrado a la izquierda del campo de texto abre un pequeño menú:

| Modo | Para qué | Estado |
|---|---|---|
| **Chat** | Conversación normal con la IA. | listo |
| **Guía** | Explica el programa y le muestra dónde están las cosas (los botones abren cuadros de diálogo). | listo |
| **Trabajo** | La IA trabaja con funciones: calcular, leer el show, ajustar proyectores ... | en curso (la lectura y el cambio de proyectores están hechos) |

El modo pertenece al **chat** y se puede cambiar en cualquier momento en mitad de una conversación. El modo en que empiezan los **chats nuevos** se ajusta en *Ajustes -> Asistente de IA -> Modo de los chats nuevos*; cada chat recuerda también su propio modelo y modo (incluso tras un reinicio).

---

## 4. Trabajo: la IA con funciones

En el modo **Trabajo** la IA funciona como un **agente**: llama a **funciones**, lee los resultados, continúa con ellos y escribe ella misma la respuesta final. Cuando tiene que calcular, consulta la **calculadora** en lugar de adivinar de cabeza; cuando necesita algo del show, lo **lee**; cuando tiene que ajustar algo, llama a la **función de escritura** correspondiente – según sus **permisos** (sección 5), solo después de preguntarle. Hasta ahora existen estas funciones:

| Colección | Función | Qué hace |
|---|---|---|
| Lectura (`read_functions`) | `show_overview` | Nombre del show, blackout, master y solo los **recuentos** (proyectores, grupos, listas de cues, cues, efectos, variables), lista de cues activa |
| Lectura | `list_fixtures` | Los proyectores: número, nombre, tipo, dirección DMX, grupo, brillo actual (filtros: grupo, nombre) |
| Lectura | `read_fixtures` | Los **detalles** de los proyectores: modelo, fabricante, modo, dirección DMX, grupo y **todos** los valores actuales (brillo en %, color, pan / tilt, zoom ... y cada canal como valor DMX). Usted dice cuáles: `all`, un rango como `1-5`, números como `1, 3, 7` (también `1-3, 7`) o el nombre de un grupo (también «group Front»). Si un número que nombra no existe (`6, 11` con 10 proyectores), vuelven los existentes y una nota nombra el que falta; así la IA puede responder correctamente |
| Lectura | `list_groups` | Los grupos con los números de sus proyectores |
| Lectura | `read_dmx` | La **salida DMX** de un universo: solo los canales que no son 0 (`universe`, `first`, `last`) |
| Lectura | `list_cuelists` | Las listas de cues con número de cues, cue activo y fader |
| Biblioteca (`library_functions`) | `list_effects` | Los efectos con sus ajustes, y si están en marcha y en qué proyectores |
| Biblioteca | `list_variables` | Las variables (nombre, tipo como color o posición, grupo, valor) |
| Cambio (`control_functions`) | `set_fixtures` | **Cambia** valores de proyectores: `brightness` (0-100 %), `color` (un nombre como `red`, `#FF8000` o `255 128 0`), `pan` / `tilt` (grados o `50%`), `zoom`, `focus`, `gobo`, `prism`, `strobe` (cada uno 0-100 %) y con `channels` cualquier otro canal por su nombre en porcentaje (`{"Frost": 50}`). Elegidos como en `read_fixtures`; lo que no nombra se queda como está. Pasa por las mismas comprobaciones que la **línea de comandos** (el comando aparece en su historial). La **selección** en la interfaz permanece intacta: los valores van exactamente a estos proyectores (visibles en la lista de proyectores, el programador y los valores DMX) sin seleccionarlos; mientras tanto puede seguir trabajando con otros proyectores |
| Cambio | `set_blackout` | **Blackout** activado o desactivado (`enabled`): todo oscuro, los valores se conservan |
| Cambio | `set_master` | El **master** (brillo general) en porcentaje |
| Cambio | `timecode_control` | El reloj del **timecode**: `play`, `pause`, `stop`, `seek` (con `position`), `rate` (con `rate`) |
| Listas de cues (`cuelist_functions`) | `read_cuelist` | **Una** lista de cues con todos los cues: número, nombre, disparador, tiempos, cue activo, si está sonando |
| Listas de cues | `control_cuelist` | Reproduce una lista de cues: `go` (siguiente cue, o con `cue` un salto), `back`, `pause`, `resume`, `stop` |
| Listas de cues | `set_cuelist_fader` | El **fader** (mezcla) de una lista de cues en porcentaje |
| Looks (`look_functions`) | `apply_variable` | Pone una **variable** (color guardado, posición ...) en proyectores |
| Looks | `apply_effect` | Inicia un **efecto** en proyectores |
| Looks | `stop_effects` | Detiene todos los efectos en proyectores (los valores se quedan) |
| Looks | `release_fixtures` | Devuelve proyectores a **manual**: libera variables y efectos; opcionalmente solo `dimmer`, `color`, `position`, `zoom`, `focus`, `gobo` |
| Lectura | `read_selection` | Qué proyectores están **seleccionados** en la interfaz |
| Biblioteca | `list_showfiles` | Los **archivos de show** guardados y cuál está cargado |
| Selección y grupos (`group_functions`) | `select_fixtures` | **Selecciona** proyectores en la interfaz (o `none` borra la selección) |
| Selección y grupos | `create_group` | Crea un **grupo** a partir de proyectores (`name`, `fixtures`); la selección del usuario se mantiene |
| Selección y grupos | `delete_group` | **Crítica:** elimina un grupo (los proyectores se quedan) |
| Listas de cues | `store_cue` | **Guarda** los valores del programador como un cue nuevo (`cuelist`, `cue`, `name` opcional, `if_exists` = `merge` / `overwrite`) |
| Listas de cues | `delete_cue` | **Crítica:** elimina un cue de una lista |
| Patch (`patch_functions`) | `list_fixture_types` | Busca tipos en la **biblioteca de proyectores** (nombre, fabricante, modos con número de canales) |
| Patch | `add_fixtures` | **Hace patch** de proyectores nuevos: tipo, cantidad, universo, primera dirección, nombre, grupo; las direcciones solapadas se rechazan |
| Patch | `change_fixture` | Cambia **un** proyector: nombre, dirección, universo, grupo |
| Patch | `change_group` | Renombra un grupo y / o fija sus miembros |
| Patch | `delete_fixtures` | **Crítica:** elimina proyectores del show |
| Archivos de show (`showfile_functions`) | `save_show`, `save_show_as` | **Guarda** el show (con su nombre conocido / con uno nuevo; un nombre existente solo se reemplaza con `overwrite`) |
| Archivos de show | `rename_showfile` | Renombra un archivo de show guardado |
| Archivos de show | `load_show`, `new_show` | **Crítica:** carga otro show / inicia uno nuevo y reemplaza el que está en marcha. Los cambios sin guardar se rechazan; solo con su acuerdo (`discard_changes`) funciona igualmente |
| Archivos de show | `delete_showfile` | **Crítica:** elimina un archivo de show guardado (el cargado solo con `force`) |
| Variables (`variable_functions`) | `create_variable`, `change_variable` | Crea / cambia una **variable**: color (`color`), brillo / zoom / focus / gobo (`level`), posición (`pan`, `tilt`); todo lo que la usa la sigue de inmediato |
| Variables | `delete_variable` | **Crítica:** elimina una variable |
| Efectos (`effect_functions`) | `list_effect_types` | Los **tipos de efecto** con su categoría y sus ajustes con límites |
| Efectos | `create_effect`, `change_effect` | Crea un **efecto** a partir de un tipo con ajustes (`settings`) / lo cambia |
| Efectos | `delete_effect` | **Crítica:** elimina un efecto (se detiene en todas partes) |
| Editar cues (`cue_edit_functions`) | `set_cue` | Cambia las **propiedades** de un cue: nombre, fade, delay, disparador (`go` / `follow` / `timecode` / `audio` / `midi`), timecode, comando, move-in-black, número nuevo |
| Editar cues | `duplicate_cue`, `update_cue` | Copia un cue / lleva los valores del programador al **cue activo** (como el botón Update) |
| Gestionar listas de cues (`cuelist_manage_functions`) | `create_cuelist`, `rename_cuelist`, `duplicate_cuelist` | Crea una lista de cues / la renombra / la copia con todos sus cues |
| Gestionar listas de cues | `delete_cuelist` | **Crítica:** elimina una lista de cues con todos sus cues |
| Comando (`command_functions`) | `command_help` | La **sintaxis de la línea de comandos** de la guía (chuleta o un tema: `selection`, `values`, `color`, `channels`, `effects`, `combine`, `clear`, `cuelists`, `cues`); la IA la consulta antes de usar `run_command` |
| Comando | `run_command` | **Crítica:** ejecuta **cualquier comando de la línea de comandos** (también borrar y guardar cues); la IA se lo pregunta hasta que elija «Permitir siempre» |
| Ayudas (`helper_functions`) | `calculate` | Calcula una expresión con exactitud: `+ - * / // % ** ^`, paréntesis, `sqrt`, `sin`, `cos`, `tan`, `ln`, `log`, `exp`, `abs`, `round`, `floor`, `ceil`, `min`, `max`, `pi`, `e` ... (decimales con punto) |
| Ayudas | `random_number` | Números aleatorios o tiradas de dados (`min`, `max`, `count`, enteros o decimales) |
| Ayudas | `current_time` | Hora, fecha y día de la semana del ordenador |

La IA **no tiene que usar una función**: ante un saludo, un agradecimiento o una pregunta general responde simplemente con palabras. Solo los cálculos, los números aleatorios, la fecha y la hora, los datos del show y los cambios en el show pasan por una función, cada vez de nuevo, también en una pregunta de seguimiento.

Cada llamada aparece en el chat en un **bloque de funciones** bajo su pregunta: plegado ve el recuento, los nombres, el estado y el tiempo; un clic muestra cada función con su **entrada y resultado**. Si una llamada no funciona (p. ej. un cálculo no válido o un número de proyector que no existe), la IA puede leer el error – con lo que sí existe – y lo intenta de nuevo con valores corregidos. Cada valor que la IA da a `set_fixtures` se comprueba primero estrictamente (rangos numéricos, nombres de color, nombres de canal); el texto de la IA nunca se convierte en un comando arbitrario.

**Llamar usted mismo a las funciones:** también puede activar cualquier función **a mano**, sin que la IA diga nada. Escriba `/` y el nombre en el campo de texto; mientras escribe aparecen sugerencias (las flechas, **Tab** o un clic aceptan, **Intro** envía):

- `/read_fixtures {"fixtures":"6-8"}` – los valores como JSON, como los escribe la IA.
- `/read_fixtures 6-8` – si la función tiene exactamente un valor obligatorio, basta el valor solo. `/calculate 17*23` calcula.
- `/set_fixtures fixtures=1-3 brightness=50` – o como `nombre=valor`.
- `/help` lista todas las funciones con su tipo y sus valores.

El resultado aparece en el chat ya desplegado (entrada y resultado como JSON). **No se consulta ningún modelo** y la IA no ve estas llamadas más tarde. Como actúa usted mismo, los **permisos** no se aplican aquí: incluso una función de escritura se ejecuta sin preguntar, también cuando para la IA está en «No permitir nunca». Un error (función desconocida, forma incorrecta de escribir los valores) aparece como llamada fallida con una explicación. Un mensaje que simplemente empieza por `/` sin ser un nombre de función (p. ej. `/etc/hosts show`) va a la IA como de costumbre.

**Lista de funciones** (*Ajustes -> Asistente de IA -> Modo trabajo*):

- **Las funciones habituales de inmediato, el resto bajo demanda** (por defecto, recomendado): la IA ve enseguida las unas 17 funciones habituales (leer y ajustar proyectores, blackout, master, reproducir una lista de cues, aplicar variables y efectos, línea de comandos, calculadora ...) y una **función de colección** para todo lo demás (patch, archivos de show, editar variables / efectos / cues ...): llamar a una le da las funciones de esa colección desde el paso siguiente. El prompt se mantiene pequeño – importante, porque las 56 funciones a la vez son aproximadamente el doble de lo que cabe en la ventana de contexto de un modelo pequeño.
- **Todas a la vez**: la IA ve de inmediato las 56 funciones. Solo para modelos grandes con una gran ventana de contexto (suba *Ajustes -> Asistente de IA -> Avanzado -> Tamaño del contexto*).
- **Todo bajo demanda**: la IA solo ve las 14 funciones de colección (`read_functions`, `library_functions`, `cuelist_functions`, `look_functions`, `group_functions`, `command_functions`, `control_functions`, `helper_functions`, `patch_functions`, `showfile_functions`, `variable_functions`, `effect_functions`, `cue_edit_functions`, `cuelist_manage_functions`). El prompt más pequeño, pero los modelos pequeños son más lentos así y eligen más a menudo la colección equivocada.

**Protección contra bucles sin fin:** la misma llamada con los mismos valores se ejecuta como máximo **3 veces** por pregunta, como máximo **30** llamadas en total. Después la IA se detiene y escribe su respuesta con lo que tiene hasta ese momento (aparece una nota en el chat).

**Importante para el modelo:** tiene que poder **llamar a funciones** (p. ej. `qwen2.5-coder`, `qwen3`, `llama3.1`). Los modelos pequeños (3B) todavía inventan alguna cosa de vez en cuando o se saltan una función; cuanto mayor es el modelo, más fiable: un modelo como `qwen3:4b` o `llama3.1:8b` merece la pena si su ordenador puede con él. Un modelo de chat sin más indica en el modo Trabajo que no puede llamar a funciones; en el modo Chat funciona con normalidad.

---

## 5. Permisos: lo que la IA puede hacer por sí sola

Cada función pertenece a un **tipo**, y para cada tipo usted ajusta lo que la IA puede hacer (*Ajustes -> Asistente de IA -> Permisos*):

| Tipo | Ejemplos | Por defecto |
|---|---|---|
| **Funciones de lectura** | `show_overview`, `list_fixtures`, `read_fixtures`, `list_groups`, `read_dmx`, `list_cuelists`, `read_cuelist`, `read_selection`, `list_effects`, `list_effect_types`, `list_showfiles`, `list_fixture_types`, `list_variables` – solo miran el show | **Permitir siempre** |
| **Funciones de escritura** | `set_fixtures`, `set_blackout`, `set_master`, `timecode_control`, `control_cuelist`, `set_cuelist_fader`, `apply_variable`, `apply_effect`, `stop_effects`, `release_fixtures`, `select_fixtures`, `create_group`, `store_cue` y todo lo de patch, guardado, edición de variables, efectos, cues y listas de cues (`add_fixtures`, `save_show`, `create_variable`, `create_effect`, `set_cue`, `create_cuelist` ...) – cambian el show | **Preguntar cada vez** |
| **Funciones críticas** | `run_command` (cualquier comando de la línea de comandos), **todas las funciones de eliminación** (`delete_cue`, `delete_group`, `delete_fixtures`, `delete_variable`, `delete_effect`, `delete_cuelist`, `delete_showfile`) y `load_show` y `new_show` (reemplazan el show en marcha) | **Preguntar cada vez** |
| Funciones de ayuda | `calculate`, `random_number`, `current_time`, `command_help` – sin efecto en el show | siempre permitidas, no ajustables |

Para cada uno de los tres tipos elige **Permitir siempre**, **Preguntar cada vez** o **No permitir nunca**. Bajo cada opción ve qué funciones le pertenecen.

**La pregunta:** cuando un tipo está en *Preguntar cada vez*, la IA hace una pausa antes de ejecutar la función y aparece en el bloque de funciones una **tarjeta** con la función y sus valores (y el tipo, p. ej. «Cambia el show»). Tiene tres botones:

- **Permitir una vez** – la función se ejecuta ahora; la próxima vez vuelve a preguntar.
- **Permitir siempre** – la función se ejecuta ahora y a partir de ahora **siempre sin preguntar** (también en otros chats). Esto se aplica exactamente a esta función y aparece en *Ajustes -> Asistente de IA -> Permisos -> Funciones siempre permitidas*; **Quitar** hace que vuelva a preguntar. Este botón solo existe en el **ordenador de la consola** (no en tabletas / dispositivos remotos); se aplica a **todos** los tipos, también a las funciones críticas.
- **No permitir** – la función no se ejecuta. Se informa a la IA y esta le dice que no lo hizo.

La pregunta aparece en **todos** los dispositivos que muestran este chat; *Permitir una vez* y *No permitir* funcionan desde cualquiera de ellos. También permanece tras recargar la página. Si nadie responde, cuenta como «no» tras 10 minutos; *Detener* termina la pregunta de inmediato.

Cuando un tipo está en **No permitir nunca**, la IA ni siquiera pregunta: la función no se ejecuta, la IA recibe la nota sobre el ajuste y se lo dice.

---

## 6. Chats

- Cada chat es un **archivo propio** (carpeta `chats` de la carpeta de datos) y se conserva al salir; todos los dispositivos y paneles muestran los mismos chats.
- **+** crea un chat nuevo; el primero se crea solo cuando envía.
- Un **doble clic** en el título lo renombra. Hasta que la IA da un título, se muestra el comienzo de la primera pregunta.
- **Títulos automáticos:** la IA da ella misma un título breve al chat (2-5 palabras; una petición extra, pequeña, al modelo) – **tras la segunda respuesta**, para tener más contexto (las dos primeras preguntas y respuestas entran en la petición). Si en **un minuto** no llega una segunda pregunta, el chat se nombra a partir de la primera. Hasta entonces se muestra el comienzo de la primera pregunta. Un chat que usted mismo haya renombrado nunca se renombra. Para desactivarlo: *Ajustes -> Asistente de IA -> Modelo -> Nombrar los chat automáticamente*.
- En la cabecera elige el **modelo de este chat** – se puede cambiar en cualquier momento, el historial se mantiene.
- Cada fila de la **lista de chats** tiene un **menú de tres puntos** (también con clic derecho): **Renombrar** (directamente en la lista), **Duplicar** (una copia con todo el historial, titulada «... (copia)») y **Eliminar chat** (tras una confirmación). El símbolo antes del título muestra el modo del chat. **Mientras la IA escribe** en un chat, se mueven unos puntitos tras el título; así ve en cuál de varios chats está trabajando. Cuando una respuesta está **terminada y el chat no está abierto**, aparece allí un **punto amarillo** («respuesta nueva»). Desaparece en cuanto abre el chat, en todos los dispositivos.
- La **lista de chats se puede plegar y desplegar** (primer botón de la cabecera); el estado se recuerda para cada panel. En paneles estrechos la lista se superpone al historial.

## 7. Guía: explica el programa y le muestra dónde están las cosas

En el modo **Guía** (icono: señal indicadora) la IA responde a preguntas como *«¿Dónde están los perfiles de color?»*, *«¿Cómo creo un cue?»* o *«¿Qué es un grupo de proyectores?»* – y puede ofrecerle **botones** que abren el cuadro de diálogo adecuado.

- **La IA no inventa nada.** Recibe muy poco en su prompt (cómo está organizado el programa) y obtiene cada detalle con la función **`find_help`**: OpenCue elige los fragmentos adecuados entre muchos pequeños fragmentos de texto y se los entrega a la IA con la instrucción de **responder solo a partir de ellos**. Si no coincide nada, la función lo dice explícitamente; la IA debe entonces admitir que no lo sabe en lugar de adivinar.
- **Fuentes:** los fragmentos son archivos JSON en la carpeta `static/help/guide/snippets/<idioma>/` (un archivo por página de manual, unos 400 por idioma). Su texto está tomado **palabra por palabra de los manuales**. Puede editar o acortar fragmentos a mano o añadir `keywords`; `synonyms.json` enlaza palabras (p. ej. «Gestor de archivos» <-> «file manager»).
- **Abrir cuadros de diálogo:** la función **`show_dialog`** pone bajo la respuesta un botón como **«Abrir: Gestor de archivos»**. La IA nunca hace clic por sí misma: **usted decide** si lo pulsa. El clic equivale al del elemento de menú; no se guarda ni se elimina nada. Se ofrecen los cuadros importantes (Ajustes con sus categorías, gestor de archivos para shows / disposiciones / escenarios / efectos, biblioteca de proyectores, abrir / guardar / importar / exportar show, Añadir panel, modo de edición, atajos, idioma ...); la lista está en `static/help/guide/targets.json`.
- **`list_help_topics`** muestra de qué puede hablarle la guía.
- La guía no cambia **nada** en su show; solo tiene estas tres funciones (todas permitidas sin preguntar).
