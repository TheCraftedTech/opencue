# API REST

Con la **API REST** otros programas pueden **leer** el estado de OpenCue y **controlarlo y editarlo**: scripts, un controlador de shows, domótica, una página web para el regidor, una aplicación de tableta o su propia herramienta. Habla **HTTP** sencillo y responde en **JSON**. No hace falta ningún software adicional y funciona por completo sin conexión dentro de su red.

El acceso está protegido por **tokens** que usted crea en OpenCue. Cada token tiene sus propios **permisos**, de modo que una aplicación de tableta solo puede leer, otra herramienta también puede disparar cues y una tercera puede construir shows enteros.

---

## 1. La idea en un minuto

- La API vive bajo **`/api/v1/`** en la misma dirección y puerto que el propio OpenCue (por ejemplo `http://127.0.0.1:8000/api/v1/`).
- Usted **crea un token** en *Ajustes → API* y lo envía con cada petición.
- Las peticiones de **lectura** (`GET`) devuelven el estado: proyectores, listas de cues, cues, variables, efectos, la señal DMX, el timecode, el programador.
- Las peticiones de **operación** (`POST` / `PUT`) hacen funcionar el show: comandos, cues, timecode, blackout, audio, el programador.
- Las peticiones de **edición** cambian el propio show: crear y cambiar listas de cues y cues, variables, efectos y scripts de efectos, hacer patch de proyectores, guardar y cargar archivos de show, subir medios.
- Los **botones, faders e interruptores** propios de la consola se pueden pulsar, mover y cambiar desde fuera.
- Todo lo que un operador hace en la ventana aparece **de inmediato en todas las ventanas abiertas**, también lo que cambia la API.
- Un **flujo en directo** (`GET /events`) informa de los cambios según ocurren, de modo que un panel de control no tiene que preguntar una y otra vez.
- Para **hardware** (un ESP32 con joystick, potenciómetros, botones, micrófono) hay un **WebSocket** (`/api/v1/ws`): joystick relativo o absoluto, valores absolutos o relativos, DMX y valores en directo, envío y recepción del timecode, valores de audio y datos de audio en ambas direcciones (sección 10). Para dispositivos sencillos sin interfaz propia hay **vistas de estado** como imagen o página web (sección 11).
- Cada función necesita **un permiso**. Un token sin él recibe `403`. Los permisos de edición están **desactivados por defecto**.
- La API es una interfaz propia y estable. Las rutas internas que usa la ventana del programa *no* forman parte de ella.

---

## 2. Inicio rápido

1. Abra **Ajustes → API REST** (también es posible desde un dispositivo remoto con sesión iniciada). Por defecto **no hay ningún token** y la API solo responde en **este ordenador**.
2. Haga clic en **Nuevo token**, póngale un nombre, elija los permisos (o un preajuste) y haga clic en **Crear token**. Un **token nuevo se crea de inmediato** (sin *Guardar*) y se muestra a continuación.
3. **Copie el token ahora.** Solo se muestra una vez; después solo se ven sus primeros caracteres. Si se pierde, cree uno nuevo o use *Generar nuevo token*.
4. Pruébelo:

```
curl -H "Authorization: Bearer oc_xxxxxxxx" http://127.0.0.1:8000/api/v1/status
```

La respuesta es un objeto JSON con el nombre del show, blackout, grand master, timecode y más (véase la sección 6).

La dirección de los ejemplos (`127.0.0.1:8000`) es la propia consola. Para la dirección desde otros dispositivos véase la sección 8. Una página con todas las rutas, con búsqueda y legible sin conexión, está en `/api/v1/docs`.

---

## 3. Tokens y permisos

### Gestionar los tokens

En **Ajustes → API REST** puede:

| Acción | Significado |
|---|---|
| **API REST activada/desactivada** | El interruptor principal. Desactivado, cada petición recibe la respuesta `403 api_disabled`. |
| **Accesible desde** | *Solo este ordenador* (por defecto) o *La red*. Los demás dispositivos también necesitan que el **acceso remoto** esté activado; si no, la página lo indica (con un enlace). Desde fuera, la API responde `403 api_local_only` cuando está en *Solo este ordenador*. |
| **Permitir páginas web de otras direcciones** | Las páginas del navegador abiertas desde otra dirección pueden llamar a la API (CORS, sección 8). Activado por defecto. |
| **Vistas de estado (imagen / web)** | Interruptor para las vistas de la sección 11. Activado por defecto (cada una necesita un token). |
| **Conectados ahora (WebSocket)** | Lista de los dispositivos conectados ahora mismo mediante el WebSocket (token, dirección, lo que reciben, joystick activo, mensajes por segundo), en directo, con **Desconectar**. |
| **Nuevo token** | Crea un token. Un cuadro amplio permite elegir los permisos en tres columnas: *Lectura*, *Operación*, *Editar el show*. |
| **Editar** | Cambiar nombre y permisos. |
| **Interruptor Activo** | Desactiva y vuelve a activar un token sin eliminarlo (`403 token_disabled` mientras está desactivado). |
| **Generar nuevo token** (en *Editar*) | Sustituye el secreto. El token antiguo deja de funcionar en cuanto guarda. |
| **Eliminar** | Pregunta en un cuadro propio (se puede desactivar, véase *Valores predeterminados → Eliminar*) y después elimina el token **de inmediato**. |
| **Último uso** | Muestra cuándo se usó un token por última vez. |

Un **token nuevo** se crea y se muestra de inmediato, una **eliminación** se aplica de inmediato tras la pregunta. Todo lo demás es un **borrador** como en todos los ajustes (interruptor, edición, regeneración): las filas cambiadas se marcan y cuentan, solo **Guardar** aplica todo (el cuadro permanece abierto), *Cerrar* descarta tras una pregunta. Los tokens solo se pueden gestionar en el propio ordenador de la consola, no desde dispositivos remotos.

En el disco solo se guarda un **hash** del token, nunca el token en sí.

### Los permisos

**Lectura**

| Permiso | Permite | Por defecto |
|---|---|---|
| **Estado** | Estado: nombre del show, blackout, grand master, timecode, selección, programador, análisis de audio, salidas, el flujo de eventos en directo | activado |
| **Datos del show** | Proyectores, tipos de proyector, grupos, variables, efectos, scripts de efectos, archivos de show, listas de cues y cues, medios, disposiciones | activado |
| **Salida DMX** | Valores DMX actuales y estado en directo de cada proyector | activado |

**Operación**

| Permiso | Permite | Por defecto |
|---|---|---|
| **Comandos de la consola** | Ejecutar cualquier comando de la línea de comandos (también puede cambiar y eliminar datos del show) – *crítico* | activado |
| **Listas de cues** | Go, Back, saltar a un cue, pausa, reanudar, parar, fader | activado |
| **Timecode** | Inicio, pausa, parada, búsqueda, velocidad | activado |
| **Blackout y master** | Cambiar el blackout, ajustar el grand master | activado |
| **Audio** | Abrir / cerrar la fuente de audio, cambiar sus ajustes, marcar el tempo | activado |
| **Programador y selección** | Seleccionar proyectores, ajustar valores y variables en directo, vaciar el programador | activado |
| **Botones, faders e interruptores de la consola** | Pulsar, mover y cambiar los paneles Botón, Fader e Interruptor propios de la consola (ejecutan los comandos configurados en ellos) | activado |
| **Ajustar DMX directamente** | Escribir canales DMX – prevalece sobre el show en marcha – *crítico* | **desactivado** |

**Editar el show**

| Permiso | Permite | Por defecto |
|---|---|---|
| **Listas de cues y cues** | Crear, cambiar, copiar, renumerar y eliminar listas de cues y cues; guardar el programador como cue | **desactivado** |
| **Variables** | Crear, cambiar y eliminar variables y grupos de variables | **desactivado** |
| **Efectos** | Crear, cambiar y eliminar efectos y grupos de efectos; iniciar y detener efectos en proyectores | **desactivado** |
| **Scripts de efectos** | Comprobar, guardar y eliminar tipos de efecto (archivos de script) | **desactivado** |
| **Patch y grupos de proyectores** | Hacer patch, cambiar y eliminar proyectores; gestionar grupos de proyectores; instalar y quitar tipos de proyector GDTF – *crítico* | **desactivado** |
| **Archivos de show** | Nuevo, cargar, guardar, renombrar, copiar y eliminar archivos de show – *crítico* | **desactivado** |
| **Medios** | Subir, renombrar y eliminar archivos de vídeo y audio | **desactivado** |
| **Disposiciones** | Mostrar una disposición de paneles guardada en la ventana de la consola | **desactivado** |
| **Salidas DMX e idioma** | Cambiar Art-Net, sACN y DMX USB, cambiar direcciones, universo predeterminado, idioma – *crítico* | **desactivado** |

**Preajustes** en el cuadro: *Solo lectura* (los tres permisos de lectura), *Operación* (lectura más listas de cues, timecode, blackout/master, audio, programador y los botones / faders / interruptores de la consola – sin comandos, sin DMX directo), *Editar show* (Operación más listas de cues y cues, variables, efectos), *Acceso completo* y *Predeterminado*.

---

## 4. Reglas para todas las peticiones

- **Inicio de sesión:** envíe el token como `Authorization: Bearer oc_…`. La cabecera `X-API-Key: oc_…` también funciona.
- **Formato:** las peticiones con cuerpo usan JSON y `Content-Type: application/json`. Las respuestas son siempre JSON (salvo el flujo de eventos y las descargas de archivos).
- **Elegir cosas:**
  - un *proyector* por su **número (FID)**, su id o un nombre inequívoco; un *grupo* de proyectores por su nombre;
  - una *lista de cues* por su **nombre** o id; un *cue* por su **número** (por ejemplo `1.5`) o id;
  - una *variable*, un *efecto* o un *archivo de show* por su **nombre** (mayúsculas / minúsculas no importan) o id.
  - Los nombres con espacios deben codificarse como URL en la ruta (`Par%20links`).
- **Elegir varios proyectores** en un cuerpo: `"fixtures": [1, 2, "Front"]`, `"fixture": 3` y / o `"group": "Wash"`. En las llamadas del programador `"selection": true` significa los proyectores seleccionados en la consola, y una llamada sin ninguno de ellos usa la selección.
- **Porcentaje y bytes:** dimmer, posición y similares se dan en **porcentaje (0–100)**, los canales DMX en bruto en **0–255**, los colores como `"#rrggbb"`, `[r, g, b]` o `{"r": …, "g": …, "b": …}` (0–255).
- **Tiempos** en segundos; el timecode como segundos o texto (`00:01:04.300`).
- **Comprobaciones cuidadosas de la entrada:** un campo que no existe se rechaza (`422`), un valor o nombre incorrecto da `400`, un nombre ya ocupado da `409 duplicate`. No se adivina ni se ignora nada en silencio.
- **Comprobado antes de que cambie nada:** una llamada con un valor, nombre o proyector incorrecto se rechaza por completo; un cue con un proyector incorrecto no se guarda a medias.

### Errores

Los errores tienen siempre el mismo aspecto:

```json
{ "error": { "code": "not_found", "message": "No fixture '99' (use the fixture number, id or an unambiguous name)." } }
```

| HTTP | `code` | Significado |
|---|---|---|
| 400 | `bad_request` | La petición es incorrecta (un valor fuera de rango, un atributo desconocido, un comando vacío …) |
| 401 | `unauthorized` | Token ausente o no válido |
| 403 | `forbidden` | El token no tiene el permiso para esta función |
| 403 | `token_disabled` / `api_disabled` | El token o toda la API está desactivado |
| 404 | `not_found` | El proyector, la lista de cues, el cue, la variable, el efecto, el archivo de show … no existe |
| 409 | `duplicate` | El nombre está ocupado (lista de cues, variable, efecto, grupo …) |
| 409 | `cue_exists` | Existe un cue con este número – envíe `on_conflict` (`merge` / `overwrite`) |
| 409 | `address_conflict` | Las direcciones DMX se solapan con otro proyector – `allow_overlap: true` hace patch igualmente |
| 409 | `unsaved_changes` | El show tiene cambios sin guardar – guárdelo, o envíe `force: true` |
| 409 | `exists` / `in_use` / `never_saved` | Existe un archivo de show o script con ese nombre / el archivo de show es el cargado / el show aún no tiene archivo |
| 409 | `no_active_cue` / `programmer_empty` | *Update* sin cue activo o con un programador vacío |
| 409 | `audio_failed` | La fuente de audio no se pudo abrir (el motivo está en el mensaje) |
| 415 | `invalid_type` | Una subida de medios que no es un archivo de vídeo / audio admitido |
| 422 | `invalid` | Falta un campo, es desconocido o tiene un tipo incorrecto |
| 422 | `invalid_script` | Un script no compila o falla en su ejecución de prueba (con la línea) |
| 429 | `rate_limited` | Demasiados tokens incorrectos desde esta dirección – espere el tiempo indicado en `Retry-After` |

Un **comando de consola rechazado** (por ejemplo una errata) *no* es un error HTTP: la respuesta es `200` con `"success": false` y el mensaje de la línea de comandos.

---

## 5. Resumen de los puntos de acceso

Todas las rutas empiezan por `/api/v1`. El permiso de la columna de la derecha es lo que necesita el token. En las rutas `{list}` es una lista de cues, `{cue}` un cue, `{fixture}` un proyector, `{ref}` una variable / un efecto / un nombre.

### Lectura

| Método | Ruta | Devuelve | Permiso |
|---|---|---|---|
| GET | `/` | Índice: versión, enlaces, lo que este token puede hacer | Estado |
| GET | `/status` | Estado general: show, blackout, master, timecode, selección, lista de cues activa, salidas DMX, recuentos | Estado |
| GET | `/blackout` · `/master` · `/timecode` · `/selection` | Una parte del estado | Estado |
| GET | `/system` | Versión, idioma, salidas DMX (Art-Net, sACN, USB), universos, acceso remoto, carpeta de datos | Estado |
| GET | `/showfile` | Nombre del show cargado, si tiene cambios sin guardar y un archivo | Estado |
| GET | `/programmer` | Selección, los valores ajustados a mano (porcentaje, color + hex, canales en bruto), las variables que siguen, efectos en marcha | Estado |
| GET | `/audio` · `/audio/devices` | El análisis de audio en directo y los ajustes / cada entrada de audio | Estado |
| GET | `/system/usb-ports` · `/command/suggest?text=` | Puertos serie para DMX USB / completados para un comando (como Tab en la línea de comandos) | Estado |
| GET | `/events` | **Flujo en directo** de cambios (Server-Sent Events, sección 6) | Estado |
| GET | `/fixtures` | Todos los proyectores. Opcionales `?universe=`, `?group=`, `?include_state=true` | Datos del show |
| GET | `/fixtures/{fixture}` | Un proyector con cada canal (dirección, valor DMX actual) y su estado | Datos del show |
| GET | `/fixture-types` | La biblioteca de proyectores: id, nombre, fabricante, modos con número de canales (`?q=` filtra) | Datos del show |
| GET | `/groups` · `/variable-groups` · `/effect-groups` | Grupos de proyectores, grupos de variables, grupos de efectos | Datos del show |
| GET | `/variables` · `/variables/{ref}` | Todas las variables / una (con cuántas entradas de cue la usan) | Datos del show |
| GET | `/effects` · `/effects/{ref}` · `/effects/assignments` | Efectos / un efecto con la información de su tipo / qué efecto corre en qué proyector | Datos del show |
| GET | `/effect-scripts` · `/effect-scripts/{name}` | Todos los tipos de efecto (categoría, etiquetas, ajustes) / el texto fuente de uno | Datos del show |
| GET | `/cuelists` · `/cuelists/{list}` | Todas las listas de cues con cue activo, fader y estado de reproducción / una lista con todos sus cues | Datos del show |
| GET | `/cuelists/{list}/cues` | Los cues de una lista; `?detail=true` añade **lo que cambia cada cue** | Datos del show |
| GET | `/cuelists/{list}/cues/{cue}` | Un cue con todo detalle | Datos del show |
| GET | `/showfiles` | Nombres de archivos de show guardados (y el cargado) | Datos del show |
| GET | `/media` · `/media/{id}/file` | Los medios del show / descargar uno | Datos del show |
| GET | `/layouts` | Disposiciones guardadas de la consola | Datos del show |
| GET | `/widgets` | Los paneles Botón / Fader / Interruptor de la consola: comandos, límites y valor del fader, estado del interruptor | Datos del show |
| GET | `/dmx` · `/dmx/{universe}` | Los universos y sus valores (`?first=&last=`, `?nonzero=true`) | Salida DMX |
| GET | `/fixtures/state` | El estado en directo de **cada** proyector (lo que la consola emite ahora) | Salida DMX |

### Operación

| Método | Ruta | Cuerpo | Permiso |
|---|---|---|---|
| POST | `/command` | `{"command": "Fixture 1 At 80"}` | Comandos de la consola |
| POST | `/commands` | `{"commands": ["…", "…"], "stop_on_error": false}` – hasta 100 | Comandos de la consola |
| POST | `/cuelists/{list}/go` | `{"cue": "2"}` opcional (sin él: el siguiente cue) | Listas de cues |
| POST | `/cuelists/{list}/back` · `/pause` · `/resume` · `/stop` | – | Listas de cues |
| PUT | `/cuelists/{list}/fader` | `{"value": 70}` (porcentaje) | Listas de cues |
| PUT | `/timecode` | `{"action": "play" \| "pause" \| "stop" \| "seek" \| "rate", "position": …, "direction": 1, "rate": 1}` | Timecode |
| PUT | `/blackout` | `{"enabled": true}` (sin valor: alternar) | Blackout y master |
| PUT | `/master` | `{"value": 80}` (porcentaje) | Blackout y master |
| PUT | `/audio` | `{"running": true, "device": "demo", "settings": {"mode": "manual", "bpm": 128}}` – cada campo opcional | Audio |
| POST | `/audio/tap` | – (un toque del botón de tempo) | Audio |
| PUT | `/selection` | `{"fixtures": [1, 2], "mode": "set" \| "add" \| "remove" \| "clear"}` (también `group`) | Programador y selección |
| PUT | `/programmer/values` | `{"fixtures": [1, 2], "values": {"dimmer": 80, "color": "#ff0000"}}` | Programador y selección |
| POST | `/programmer/variables` | `{"variable": "Warm white", "fixtures": [1, 2]}` – aplica y enlaza una variable | Programador y selección |
| POST | `/widgets/{id}/press` | – (ejecuta el comando de un botón) | Botones, faders e interruptores de la consola |
| PUT | `/widgets/{id}/value` | `{"value": 70}` (fader; limitado a su mínimo / máximo, redondeado) | Botones, faders e interruptores de la consola |
| PUT | `/widgets/{id}/state` | `{"on": true}` (interruptor; sin valor se invierte) | Botones, faders e interruptores de la consola |
| POST | `/programmer/clear` | `{"fixtures": [1]}` olvida sus valores; `{"all": true}` = *Clear Clear*: todo oscuro | Programador y selección |
| PUT | `/dmx/{universe}/{channel}` | `{"value": 255}` o `{"percent": 100}` | Ajustar DMX directamente |
| PUT | `/dmx/{universe}` | `{"channels": {"1": 255, "2": 0}}` | Ajustar DMX directamente |
| PUT | `/fixtures/{fixture}/channels/{channel}` | `{"value": 128}` o `{"percent": 50}`; `{channel}` es el número de canal del proyector (1 = primero) o su nombre (`Dimmer`) | Ajustar DMX directamente |

### Editar: listas de cues y cues – permiso *Listas de cues y cues*

| Método | Ruta | Cuerpo | Qué hace |
|---|---|---|---|
| POST | `/cuelists` | `{"name": "Act 1"}` | Crea una lista de cues (201) |
| PUT | `/cuelists/{list}` | `{"name": "…", "active": true}` | Renombra; `active` la convierte en la lista que muestran los paneles de listas de cues |
| PUT | `/cuelists/order` | `{"order": ["Act 2", "Act 1"]}` | Orden de las listas |
| POST | `/cuelists/{list}/duplicate` | `{"name": "Copy"}` | Copia con todos los cues |
| DELETE | `/cuelists/{list}` | – | Elimina la lista |
| POST | `/cuelists/{list}/cues` | véase abajo | Crea un cue (201) |
| PUT | `/cuelists/{list}/cues/{cue}` | véase abajo | Cambia propiedades y / o contenido, renumera |
| DELETE | `/cuelists/{list}/cues/{cue}` | – | Elimina un cue |
| POST | `/cuelists/{list}/cues/delete` | `{"cues": ["1", "2.5"]}` | Elimina varios (todos o ninguno) |
| POST | `/cuelists/{list}/cues/{cue}/duplicate` | `{"number": 9, "name": "…"}` | Copia un cue |
| POST | `/cuelists/{list}/update-active` | `{"mode": "normal" \| "only"}` | Lleva el programador al cue activo (como *Update*) |

**Cuerpo del cue** (crear y cambiar; cada campo opcional al cambiar):

| Campo | Significado |
|---|---|
| `number` | Número del cue, se admiten decimales. Omitido al crear: el siguiente número libre. |
| `name`, `fade`, `delay` | Nombre y los tiempos generales en segundos |
| `trigger` | `go` · `follow` · `timecode` · `audio` · `midi` · `clock` |
| `timecode` | Para `timecode`: segundos o `1:04.300` |
| `audio` | Para `audio`: `{"source": "beat" \| "kick" \| "snare" \| "hat" \| "level" \| "bass" \| "mid" \| "high" \| "b1" … "b8", "value": 4}` (cada n-ésimo golpe, o un umbral en %) |
| `midi` | Para `midi`: `{"type": "note" \| "cc" \| "pc", "number": 60, "channel": 0, "value": 64}` – el cue se dispara cuando llega esta señal mientras es el siguiente cue de una lista en marcha; `channel` 0 = cualquiera (1–16 = un canal), `value` = el umbral de un `cc` (1–127) |
| `clock` | Para `clock`: `{"time": "19:30", "days": "Mon-Fri"}` (o `"days": [0,1,2,3,4]`, lunes = 0; vacío = todos los días) – el cue espera, como siguiente cue de una lista en marcha, esta hora del reloj de pared. |
| `mib`, `command` | Move in black (`Off` / `Auto` / `On`); comandos de consola que se ejecutan con el cue |
| `times` | Tiempos propios por grupo: `{"color": {"fade": 2, "delay": 0}, "position": {…}, "beam": {…}, "zoom": {…}}`; `null` = usar de nuevo el tiempo general |
| `effect_fade` | `{"in": 1, "out": 2}` |
| `changes` | Lo que cambia el cue (abajo) |
| `effects` | Los efectos que inicia el cue: `[{"fixtures": [2, 3], "effects": {"dimmer": "Strobe"}}]` (categoría → nombre del efecto) |
| `from_programmer` | *(crear)* guarda también lo que hay en el programador **y cada cambio de la imagen respecto al cue anterior** (como *Store Cue*; si nada cambió: `409 nothing_changed`); `clear_programmer` lo vacía después |
| `on_conflict` | *(crear / renumerar)* el número existe: `merge` (solo los atributos enviados se unen al cue existente) o `overwrite` |
| `content` | *(cambiar)* `merge` (por defecto) o `replace`: el contenido del cue es exactamente lo que se envía |

`changes` es una lista; cada entrada nombra proyectores y lo que reciben:

```json
{ "fixtures": [2, 3], "values": { "dimmer": 80, "color": "#00ff00", "pan": 40 }, "variables": { "color": "Warm white" } }
```

`values`: `dimmer`, `pan`, `tilt`, `strobe`, `gobo`, `gobo_spin`, `gobo2`, `gobo2_spin`, `prism`, `focus`, `zoom` en porcentaje, `color`, canales en bruto `ch<N>` (0–255). `variables` asocia un tipo (`dimmer`, `position`, `color`, `focus`, `zoom`, `gobo`) a una variable: el cue **se refiere entonces a la variable** (un marcador, resuelto en directo cuando el cue se ejecuta) en lugar de guardar el valor.

### Editar: variables – permiso *Variables*

| Método | Ruta | Cuerpo | Qué hace |
|---|---|---|---|
| POST | `/variables` | `{"name": "Warm white", "type": "color", "group": "Colours", "values": {"hex": "#ffb060"}}` | Crea |
| PUT | `/variables/{ref}` | `{"name": "…", "group": "…", "values": {…}}` | Cambia; el tipo no puede cambiar. Un valor nuevo llega al programador, a los cues en marcha y a **cada cue que usa la variable** |
| DELETE | `/variables/{ref}` | – | Elimina (los enlaces del programador se liberan) |
| POST · DELETE | `/variable-groups` · `/variable-groups/{name}` | `{"name": "Colours"}` | Crea / elimina un grupo (sus variables se quedan) |

`values` por tipo: `dimmer`, `focus`, `zoom`: `{"level": 0-100}` · `position`: `{"pan": 0-100, "tilt": 0-100}` · `color`: `{"r","g","b"}` o `{"hex": "#ff8000"}` · `gobo`: `{"level", "spin", "gobo2", "gobo2_spin"}`.

### Editar: efectos – permiso *Efectos*

| Método | Ruta | Cuerpo | Qué hace |
|---|---|---|---|
| POST | `/effects` | `{"script": "strobe", "name": "Blink", "group": "…", "params": {"rate_hz": 8}}` | Crea un efecto a partir de un tipo de efecto (`GET /effect-scripts`); `params` se comprueban frente a los límites del tipo |
| PUT | `/effects/{ref}` | `{"name", "group", "params"}` | Cambia (el tipo no puede cambiar) |
| DELETE | `/effects/{ref}` | – | Elimina; se detiene en todas partes |
| POST | `/effects/{ref}/assign` | `{"fixtures": [2, 3]}` (también `group`) | **Inicia** el efecto en proyectores (el orden reparte las ondas) |
| POST | `/effects/release` | `{"fixtures": [2], "categories": ["dimmer"]}` | **Detiene** efectos en proyectores (los valores se quedan) |
| POST · DELETE | `/effect-groups` · `/effect-groups/{name}` | `{"name": "…"}` | Crea / elimina un grupo |

### Editar: scripts de efectos – permiso *Scripts de efectos*

| Método | Ruta | Cuerpo | Qué hace |
|---|---|---|---|
| POST | `/effect-scripts/check` | `{"text": "…"}` | Compila y prueba un script sin guardarlo: `{ok, line, message}` |
| POST | `/effect-scripts/preview` | `{"text": "…", "count": 3, "duration": 4, "bpm": 120, "params": {…}}` | Simula las curvas sin proyectores |
| PUT | `/effect-scripts/{name}` | `{"text": "…", "overwrite": false}` | Guarda como archivo en la carpeta de efectos del usuario – **solo si compila y se ejecuta** (`422 invalid_script` con la línea). Un nombre existente necesita `overwrite` |
| DELETE | `/effect-scripts/{name}` | – | Elimina un script de la carpeta de usuario; los efectos de este tipo se detienen |

El lenguaje de script se describe en la guía *Estudio de efectos*.

### Editar: patch y grupos de proyectores – permiso *Patch y grupos de proyectores*

| Método | Ruta | Cuerpo | Qué hace |
|---|---|---|---|
| POST | `/fixtures` | `{"type": "Generic RGBW LED Par", "mode": "…", "name": "Par", "quantity": 4, "universe": 1, "address": 11, "group": "Wash"}` | Hace patch de uno o más proyectores uno tras otro. Las direcciones se comprueban (deben caber en 512 y no solaparse – `allow_overlap: true` lo fuerza) |
| PUT | `/fixtures/{fixture}` | `{"name", "universe", "address", "sort_index", "group", "allow_overlap"}` | Cambia; `"group": ""` lo saca de su grupo |
| DELETE | `/fixtures/{fixture}` · POST `/fixtures/delete` | `{"fixtures": [1, 2]}` | Elimina (los cues conservan sus entradas del proyector que falta, como en la ventana) |
| POST | `/groups` | `{"name": "Wash", "fixtures": [2, 3]}` | Crea un grupo de proyectores |
| POST | `/fixture-types` | el archivo `.gdtf` en bruto; cabecera `X-Filename` (codificada como URL) | Instala un tipo de proyector (hasta 30 MB; se comprueba antes de instalarlo) |
| DELETE | `/fixture-types/{id}` | – | Quita un tipo instalado (`409 in_use` mientras el show lo use) |
| PUT · DELETE | `/groups/{name}` | `{"name": "…", "fixtures": […]}` | Renombra / fija los miembros (sustituye la lista) / elimina (los proyectores se quedan) |

### Editar: archivos de show – permiso *Archivos de show*

| Método | Ruta | Cuerpo | Qué hace |
|---|---|---|---|
| POST | `/showfile/new` | `{"force": false}` | Inicia un show nuevo y vacío |
| POST | `/showfile/save` | – | Guarda con el nombre actual (`409 never_saved` si aún no tiene archivo) |
| POST | `/showfile/save-as` | `{"name": "Concert", "overwrite": false}` | Guarda con un nombre (los caracteres no permitidos en nombres de archivo se eliminan) |
| POST | `/showfile/load` | `{"name": "Concert", "force": false}` | Carga un show guardado – sustituye el que está en marcha |
| POST | `/showfiles/{name}/rename` | `{"new_name": "…", "overwrite": false}` | Renombra un archivo guardado |
| POST | `/showfiles/{name}/duplicate` | – | Copia un archivo guardado |
| DELETE | `/showfiles/{name}` | `?force=true` para el cargado | Elimina un archivo guardado |

**Nuevo** y **Cargar** sustituyen el show en marcha. Con cambios sin guardar se rechazan con `409 unsaved_changes` hasta que guarde antes o envíe `"force": true`.

### Editar: medios – permiso *Medios*

| Método | Ruta | Cuerpo | Qué hace |
|---|---|---|---|
| POST | `/media` | el archivo en bruto; cabecera `X-Filename` (codificada como URL) | Sube un archivo de vídeo / audio (hasta 1 GB; el mismo archivo dos veces es una sola entrada) |
| PUT | `/media/{id}` | `{"name": "…"}` | Renombra |
| DELETE | `/media/{id}` | – | Quita del show y elimina la copia |

### Editar: disposiciones y ajustes – permisos *Disposiciones* y *Salidas DMX e idioma*

| Método | Ruta | Cuerpo | Qué hace |
|---|---|---|---|
| POST | `/layouts/{filename}/load` | – | Muestra una disposición guardada (`Name.json` como en `GET /layouts`) en la ventana de la consola; los cambios de disposición sin guardar allí se pierden |
| PUT | `/system` | `{"artnet": {"enabled": true, "ip": "2.255.255.255", "bind_ip": ""}, "sacn": {"enabled": true}, "enttec": {"enabled": false, "port": "COM3", "universe": 1}, "default_universe": 1, "language": "de"}` – cada campo opcional | Cambia las salidas DMX y el idioma / universo predeterminado; la respuesta es `GET /system` |
| POST | `/system/dmx/reinitialize` | – | Reinicia las salidas DMX sin reiniciar el programa |

### Documentación (sin token)

| Método | Ruta | Devuelve |
|---|---|---|
| GET | `/docs` | Un resumen legible y con búsqueda de todas las rutas (funciona sin conexión) |
| GET | `/openapi.json` | La descripción legible por máquina (OpenAPI 3.1); cada ruta indica su permiso como `x-capability` |

---

## 6. Ejemplos con respuestas reales

### Estado

```
GET /api/v1/status
```

```json
{
  "app": { "name": "OpenCue", "version": "1.0.0" },
  "show": { "name": "Concert", "unsaved_changes": true },
  "blackout": false,
  "grand_master": 100.0,
  "timecode": { "running": false, "direction": 1, "rate": 1.0, "position_ms": 0.0, "position": "00:00:00.000" },
  "selection": { "fixture_ids": ["228a68e5-…"], "fids": [2] },
  "active_cuelist": { "id": "7e5d274f-…", "name": "Show" },
  "dmx": { "universes": [1], "artnet": true, "sacn": false, "usb": false },
  "counts": { "fixtures": 2, "groups": 1, "variables": 0, "effects": 0, "cuelists": 1, "cues": 2 }
}
```

### ¿Qué proyectores hay en el show y de qué color son?

```
GET /api/v1/fixtures?include_state=true
GET /api/v1/fixtures/state
```

```json
{
  "fixtures": [
    { "id": "9ea4feaa-…", "fid": 1, "name": "Front", "state": { "dimmer": 80.0 } },
    { "id": "228a68e5-…", "fid": 2, "name": "Par left",
      "state": { "dimmer": 100.0, "color": { "r": 255, "g": 0, "b": 0, "hex": "#ff0000" } } }
  ]
}
```

`state` contiene exactamente lo que la consola emite en este momento, leído del búfer DMX: `dimmer`, `pan`, `tilt`, `zoom`, `focus` … en porcentaje y `color` como r/g/b. Los atributos que un proyector no tiene faltan. (Con grand master 0 o en blackout el dimmer no se puede reconstruir y se omite.)

### Un proyector con todos los canales

```
GET /api/v1/fixtures/2
```

```json
{
  "id": "228a68e5-…", "fid": 2, "name": "Par left", "type": "Generic RGBW LED Par", "manufacturer": "Generic",
  "universe": 1, "start_channel": 11, "end_channel": 14, "channel_count": 4, "mode": "default", "group": "Wash",
  "channels": [
    { "channel": 1, "name": "ColorAdd_R", "address": 11, "value": 255 },
    { "channel": 2, "name": "ColorAdd_G", "address": 12, "value": 0 },
    { "channel": 3, "name": "ColorAdd_B", "address": 13, "value": 0 },
    { "channel": 4, "name": "ColorAdd_W", "address": 14, "value": 0 }
  ],
  "state": { "color": { "r": 255, "g": 0, "b": 0, "hex": "#ff0000" } }
}
```

### ¿Qué cambia un cue?

```
GET /api/v1/cuelists/Show/cues/1
```

```json
{
  "id": "700571ee-…", "number": 1, "name": "Auf", "active": false,
  "trigger": "go", "timecode_ms": null, "timecode": null, "audio": null, "midi": null, "clock": null,
  "fade": 2.0, "delay": 0.0,
  "times": { "color": { "fade": null, "delay": null }, "position": { "fade": null, "delay": null },
             "beam": { "fade": null, "delay": null }, "zoom": { "fade": null, "delay": null } },
  "effect_fade": { "in": 0.0, "out": 0.0 }, "mib": "Off", "command": "", "fixture_count": 2,
  "changes": [
    { "fixture_id": "9ea4feaa-…", "fid": 1, "name": "Front", "values": { "dimmer": 50 }, "variables": {} },
    { "fixture_id": "228a68e5-…", "fid": 2, "name": "Par left",
      "values": { "dimmer": 100, "color": { "r": 255, "g": 0, "b": 0, "hex": "#ff0000" } }, "variables": {} }
  ],
  "effects": [],
  "cuelist": { "id": "7e5d274f-…", "name": "Show" }
}
```

- `fade` / `delay` son los tiempos generales; `times` contiene los tiempos opcionales por grupo de atributos (`null` = usa el tiempo general).
- `changes[].values` son los valores fijos guardados en el cue. `variables` lista las variables (marcadores) a las que el cue se refiere, por tipo y nombre; una variable se resuelve en directo cuando el cue se ejecuta.
- `effects` lista los efectos que el cue inicia, por proyector.
- Todos los cues de una lista de una vez con sus detalles: `GET /api/v1/cuelists/Show/cues?detail=true`.

### La señal DMX

```
GET /api/v1/dmx/1?first=1&last=14
GET /api/v1/dmx/1?nonzero=true
```

```json
{ "universe": 1, "first": 1, "last": 14, "values": [0,0,0,0,0,0,0,0,0,0,255,0,0,0] }
{ "universe": 1, "first": 1, "last": 512, "channels": { "11": 255 } }
```

### Ejecutar un comando de consola

```
POST /api/v1/command
{ "command": "Fixture 1 Thru 4 At 80" }
```

```json
{ "command": "Fixture 1 Thru 4 At 80", "success": true, "message": "OK: 4 fixtures selected; At 80 applied" }
```

Funcionan todos los comandos de la línea de comandos, también encadenados con `;` (véase la guía *Referencia de comandos*).

### Disparar un cue

```
POST /api/v1/cuelists/Show/go            { "cue": "2" }
```

```json
{ "cuelist": { "id": "7e5d274f-…", "name": "Show" }, "command": "Cuelist \"Show\" Go Cue 2", "success": true, "message": "OK: Go Cue 2 [Show]" }
```

Sin cuerpo `go` inicia el siguiente cue. Nota: una lista de cues cuyo **nombre contiene unas comillas** no se puede direccionar así; renómbrela.

### Timecode

```
PUT /api/v1/timecode   { "action": "seek", "position": "1:04.300" }
PUT /api/v1/timecode   { "action": "play", "position": 10 }
GET /api/v1/timecode
```

```json
{ "running": false, "direction": 1, "rate": 1.0, "position_ms": 64300.0, "position": "00:01:04.300" }
```

`position` es un número en **segundos** o un texto como `1:04.300` o `00:00:04.300`. `play` puede empezar desde una `position` y correr hacia atrás con `"direction": -1`; `rate` es la velocidad entre 0,1 y 8. Saltar con `seek` no dispara los cues de timecode.

### Ajustar canales DMX

```
PUT /api/v1/dmx/1/200                      { "value": 255 }
PUT /api/v1/dmx/1                          { "channels": { "201": 10, "202": 20 } }
PUT /api/v1/fixtures/Front/channels/Dimmer { "percent": 50 }
```

```json
{ "universe": 1, "channel": 1, "value": 128, "fixture": { "fid": 1, "name": "Front" }, "channel_of_fixture": 1 }
```

Un canal que pertenece a un **proyector** se ajusta como el fader *DMX directo* del programador: se convierte en un valor manual que los cues en marcha ya no mezclan. Los demás canales se escriben directamente en la salida. Este permiso está **desactivado por defecto**.

### Audio: leer y controlar

```
GET  /api/v1/audio/devices                    -> { "devices": [ { "id": "demo", "kind": "demo", "name": "Demo beat" }, ... ] }
PUT  /api/v1/audio    { "device": "demo" }    open that source (`running` false closes it)
PUT  /api/v1/audio    { "settings": { "mode": "manual", "bpm": 128, "sensitivity": 0.7 } }
POST /api/v1/audio/tap                        tap the tempo (about 4 taps in a row set it, the tempo switches to manual)
GET  /api/v1/audio                            level, bands, kick / snare / hat, bpm, beat_phase ... and the settings
```

`PUT /audio` aplica primero los `settings`, después abre (`running: true`, o un `device`) o cierra (`running: false`) la fuente, y responde como `GET /audio`. Si la fuente no se puede abrir la respuesta es `409 audio_failed` con el motivo. Ajustes: `gain`, `auto_gain`, `sensitivity`, `smoothing`, `latency_ms`, `mode` (`auto` | `manual`), `bpm` (tempo manual), `phase_follow`, `demo_bpm`, `autostart`; las claves desconocidas se ignoran y los números se limitan a su rango.

### Construir un cue

```
POST /api/v1/cuelists/Show/cues
{
  "number": 3, "name": "Blue wash", "fade": 3,
  "changes": [
    { "group": "Wash", "values": { "dimmer": 80, "color": "#0000ff" } },
    { "fixtures": [1], "values": { "dimmer": 20 } }
  ],
  "effects": [ { "fixtures": [2, 3], "effects": { "dimmer": "Blink" } } ]
}
```

```json
{ "status": "created", "cuelist": { "id": "7e5d274f-…", "name": "Show" },
  "cue": { "id": "5c0b…", "number": 3, "name": "Blue wash", "fade": 3.0, "changes": [ … ], "effects": [ … ], … } }
```

La respuesta es el cue completo tal como lo mostraría `GET …/cues/3`. Si el cue 3 existe recibe `409 cue_exists`; envíe `"on_conflict": "merge"` para añadirle los atributos enviados, o `"overwrite"` para sustituir su contenido (estado `merged` / `overwritten`).

Lo mismo desde el programador, como *Store Cue*:

```
PUT  /api/v1/programmer/values   { "fixtures": [2, 3], "values": { "color": "#ff8000", "dimmer": 100 } }
POST /api/v1/cuelists/Show/cues  { "number": 4, "name": "Orange", "from_programmer": true, "clear_programmer": true }
```

### Cambiar y eliminar cues

```
PUT    /api/v1/cuelists/Show/cues/3   { "name": "Deep blue", "fade": 5, "times": { "color": { "fade": 8 } } }
PUT    /api/v1/cuelists/Show/cues/3   { "changes": [ { "fixtures": [1], "values": { "dimmer": 0 } } ] }                       (adds to the content)
PUT    /api/v1/cuelists/Show/cues/3   { "content": "replace", "changes": [ { "fixtures": [1], "values": { "dimmer": 0 } } ] } (content = exactly this)
PUT    /api/v1/cuelists/Show/cues/3   { "number": 2.5 }                                                                          (renumber)
DELETE /api/v1/cuelists/Show/cues/3
```

Solo cambia lo que usted envía. Un cambio en un cue que está en marcha surte efecto con su siguiente *Go*.

### Variables y efectos

```
POST /api/v1/variables  { "name": "Warm white", "type": "color", "values": { "hex": "#ffb060" } }
PUT  /api/v1/variables/Warm white   { "values": { "hex": "#ffa040" } }      -> every cue that uses it is warmer now
POST /api/v1/effects    { "script": "strobe", "name": "Blink", "params": { "rate_hz": 8 } }
POST /api/v1/effects/Blink/assign   { "fixtures": [2, 3] }                  -> it runs now
POST /api/v1/effects/release        { "fixtures": [2, 3] }                  -> stop it
```

`GET /api/v1/effect-scripts` lista los tipos de efecto con sus ajustes (`variables`: nombre, tipo, límites, valor por defecto, etiquetas en ambos idiomas).

### Escribir su propio tipo de efecto

```
POST /api/v1/effect-scripts/check   { "text": "…" }                  -> { "ok": false, "line": 3, "message": "…" }
PUT  /api/v1/effect-scripts/my_wave { "text": "…", "overwrite": true }
POST /api/v1/effects                { "script": "my_wave" }
```

Un script solo se guarda cuando compila y se ejecuta. El lenguaje está documentado en la guía *Estudio de efectos*.

### Hacer patch de proyectores

```
GET  /api/v1/fixture-types?q=par
POST /api/v1/fixtures  { "type": "Generic RGBW LED Par", "quantity": 4, "name": "Par", "universe": 1, "address": 11, "group": "Wash" }
```

```json
{ "created": [ { "fid": 4, "name": "Par 1", "universe": 1, "start_channel": 11, "end_channel": 14, … },
               { "fid": 5, "name": "Par 2", "universe": 1, "start_channel": 15, … }, … ] }
```

Las direcciones que se solapan con otros proyectores se rechazan (`409 address_conflict`); `"allow_overlap": true` hace patch igualmente.

### El programador

```
GET  /api/v1/programmer
PUT  /api/v1/selection            { "group": "Wash" }
PUT  /api/v1/programmer/values    { "values": { "dimmer": 100, "color": [255, 0, 0] } }       (without fixtures: the selection)
POST /api/v1/programmer/variables { "variable": "Warm white" }
POST /api/v1/programmer/clear     { "fixtures": [2] }          forget their values (the output stays)
POST /api/v1/programmer/clear     { "all": true }              Clear Clear: every fixture dark, effects end
```

Los valores ajustados así se comportan como los faders de la ventana del programador: la salida cambia de inmediato, cuentan como tocados y el siguiente *Store Cue* los toma.

### Valores relativos (empujar en lugar de fijar)

```
curl -X PUT -H "Authorization: Bearer oc_xxxxxxxx" -H "Content-Type: application/json" \
  -d '{"group": "Front", "mode": "relative", "values": {"pan": 2.5, "dimmer": -10}}' \
  http://127.0.0.1:8000/api/v1/programmer/values
```

Con `"mode": "relative"` los números son **cambios en puntos porcentuales** (−100 a 100); cada proyector parte de su propio valor y se limita en 0 / 100 %. Los colores y los canales en bruto solo existen como valores absolutos. Para secuencias rápidas de cambios (potenciómetros, joystick) es mejor el WebSocket (sección 10).

### Archivos de show

```
POST /api/v1/showfile/save-as  { "name": "Concert" }
POST /api/v1/showfile/load     { "name": "Concert", "force": false }
POST /api/v1/showfile/new      { "force": true }
```

Sin `force`, *load* y *new* se detienen con `409 unsaved_changes` cuando el show en marcha tiene cambios sin guardar. `GET /api/v1/showfile` indica si los tiene.

### Botones, faders e interruptores de la consola

```
GET /api/v1/widgets
POST /api/v1/widgets/b1/press
PUT  /api/v1/widgets/f1/value   { "value": 70 }
PUT  /api/v1/widgets/t1/state   { "on": true }
```

`GET /widgets` lista los paneles con su `id`, `label`, comando y el valor actual (faders) o el estado (interruptores). Pulsar, mover o cambiar ejecuta el comando configurado en el panel – el mismo que dispara un operador – y los paneles de cada dispositivo lo siguen (un botón pulsado late, los faders e interruptores con el mismo comando se mueven también). El valor de un fader se limita a su mínimo / máximo. Un panel sin comando responde `409 no_command` (un interruptor sin comandos simplemente cambia). Los paneles son los de la disposición de la **consola**; los dispositivos remotos tienen disposiciones propias.

### Salidas y disposiciones

```
PUT  /api/v1/system   { "artnet": { "ip": "192.168.1.255" }, "sacn": { "enabled": false } }
POST /api/v1/layouts/Concert.json/load
POST /api/v1/fixture-types   (raw .gdtf file, header X-Filename: my_fixture.gdtf)
```

### Subir un medio

```
curl -X POST -H "Authorization: Bearer oc_xxxxxxxx" -H "Content-Type: application/octet-stream" \
     -H "X-Filename: intro.mp4" --data-binary @intro.mp4 http://127.0.0.1:8000/api/v1/media
```

### Eventos en directo (flujo)

```
curl -N -H "Authorization: Bearer oc_xxxxxxxx" "http://127.0.0.1:8000/api/v1/events?events=cue,blackout,command"
```

```
event: hello
data: {"app": "OpenCue", "events": ["blackout", "cue", "command"]}

event: cue
data: {"cuelists": [{"id": "7e5d…", "name": "Show", "active_cue": {"id": "700…", "number": 2, "name": "Blue", …}}]}

event: command
data: {"command": "Fixture 1 At 10", "success": true, "message": "OK: …", "time": "21:14:03"}
```

La conexión permanece abierta. Llegan primero `hello` y un mensaje por tipo con el **estado actual**, después cada cambio. Tipos: `cue` (cambió el cue activo de una lista), `cuelists` (se añadieron, quitaron o renombraron listas / cues), `blackout`, `master`, `timecode` (iniciado, detenido, velocidad), `selection`, `effects`, `fixtures`, `variables`, `show` (nombre / cambios sin guardar), `command` (se ejecutó un comando de consola, desde donde sea), `audio` (fuente abierta / cerrada, tempo, señal presente). Solo bajo petición (`?events=beat,hit`): `beat` (cada pulso, con el tempo) y `hit` (cada golpe de bombo / caja / hi-hat: `{"drum": "kick", "strength": 0.9}`). `?events=` limita el flujo. Los cambios se detectan en unos 0,1 s. Cada 15 s llega una línea de comentario (`: keep-alive`); como máximo corren 20 flujos a la vez. Necesita el permiso *Estado*.

En un navegador `EventSource` no puede enviar cabeceras: use en su lugar `?access_token=<token>`, o `fetch()` con una cabecera y lea el flujo. El token aparece entonces en la dirección, así que dé a una página así su propio token con solo *Estado*.

---

## 7. Programas pequeños

Python, con la biblioteca `requests` (sirve cualquier biblioteca HTTP):

```python
import requests

BASE = "http://127.0.0.1:8000/api/v1"
HEAD = {"Authorization": "Bearer oc_xxxxxxxx"}

# What is the colour of every fixture?
for fx in requests.get(f"{BASE}/fixtures/state", headers=HEAD).json()["fixtures"]:
    color = fx["state"].get("color")
    print(fx["fid"], fx["name"], color["hex"] if color else "-")

# Dim the front lights, then start the next cue
requests.post(f"{BASE}/command", headers=HEAD, json={"command": "Fixture 1 At 30"})
requests.post(f"{BASE}/cuelists/Show/go", headers=HEAD)
```

Construir un show pequeño (necesita los permisos de edición):

```python
requests.post(f"{BASE}/fixtures", headers=HEAD, json={"type": "Generic RGBW LED Par", "quantity": 4, "name": "Par", "address": 1, "group": "Wash"})
requests.post(f"{BASE}/variables", headers=HEAD, json={"name": "Warm", "type": "color", "values": {"hex": "#ffb060"}})
requests.post(f"{BASE}/cuelists", headers=HEAD, json={"name": "Show"})
requests.post(f"{BASE}/cuelists/Show/cues", headers=HEAD, json={
    "number": 1, "name": "Warm", "fade": 3,
    "changes": [{"group": "Wash", "values": {"dimmer": 80}, "variables": {"color": "Warm"}}]})
requests.post(f"{BASE}/showfile/save-as", headers=HEAD, json={"name": "From the API"})
```

Una página web que muestra el cue activo en directo (JavaScript en el navegador; la página puede venir de cualquier dirección, véase la sección 8):

```javascript
const res = await fetch("http://192.168.1.20:8000/api/v1/events?events=cue", { headers: { Authorization: "Bearer oc_xxxxxxxx" } });
const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
for (;;) {
  const { value, done } = await reader.read();
  if (done) break;
  console.log(value);          // "event: cue\ndata: {...}\n\n"
}
```

---

## 8. Otros dispositivos y seguridad

- **Desde otro ordenador o tableta** la API es accesible en cuanto **Permitir el acceso por HTTP** (Ajustes → Acceso remoto) está activado. Use la dirección de la consola (mostrada en esa página) en lugar de `127.0.0.1`, por ejemplo `http://192.168.1.20:8000/api/v1/status`. Con el acceso remoto desactivado el puerto está cerrado a la red. El **token sustituye a la contraseña** allí; no hace falta iniciar sesión.
- Los tokens dan un control real sobre las luces. Dé a cada programa su **propio token con solo los permisos que necesita** y elimine los tokens que ya no use.
- Los **permisos de edición están desactivados por defecto** y pueden cambiar o destruir datos del show: *Patch*, *Archivos de show* y *Comandos de la consola* están marcados como **críticos**. *Cargar* y *Nuevo* se niegan a tirar cambios sin guardar sin `force`.
- El tráfico es HTTP sencillo dentro de su red. No exponga el puerto a internet.
- Las **páginas web de otras direcciones** (su propio panel de control, una herramienta web en el navegador) pueden llamar directamente a la API: las respuestas llevan las cabeceras de acceso entre orígenes (CORS) y se responde a la petición previa del navegador (`OPTIONS`, que no puede llevar token). La página sigue necesitando un token en la cabecera `Authorization`, y debe guardar el token para sí (no ponga un token potente en una página web pública). Desactívelo en *Ajustes → API → Permitir páginas web de otras direcciones* si no lo necesita; los navegadores bloquean entonces de nuevo esas páginas (los programas y scripts no se ven afectados).
- La API cambia el show **en memoria**, como la ventana. No se guarda nada en disco hasta que se guarda el show (`POST /showfile/save`, o *Guardar* en la ventana).

---

## 9. Cuando algo no funciona

| Problema | Compruebe |
|---|---|
| `401 unauthorized` | ¿Cabecera escrita `Authorization: Bearer oc_…` con el token completo? ¿Token eliminado o regenerado? |
| `403 forbidden` | Al token le falta este permiso: abra el token en *Ajustes → API* y actívelo (el mensaje lo nombra). |
| `403 api_disabled` | El interruptor principal de *Ajustes → API* está desactivado. |
| `403 remote access disabled` | Llama desde otro dispositivo mientras *Permitir el acceso por HTTP* está desactivado. |
| `404 not_found` | Compruebe el número de proyector, el nombre de la lista de cues (exactamente) y el número de cue. |
| `409 duplicate` | El nombre está ocupado (mayúsculas / minúsculas no importan). Elija otro nombre o cambie el existente con `PUT`. |
| `409 cue_exists` | Hay un cue con este número en la lista: `on_conflict` o `PUT`. |
| `409 unsaved_changes` | Guarde antes (`POST /showfile/save`) o envíe `force: true`. |
| `409 no_command` / `409 wrong_type` | Un panel no tiene comando configurado / pulsó un fader, movió un botón … (véase `GET /widgets` para el tipo). |
| `422` | Un campo que no existe (¿errata?) o un tipo incorrecto: el mensaje nombra el campo. |
| `422 invalid_script` | El script tiene un error: el mensaje nombra la línea. `POST /effect-scripts/check` prueba sin guardar. |
| `200` pero `"success": false` | El comando fue rechazado: lea `message`. |
| `429` | Demasiados tokens incorrectos desde esta dirección. Espere `Retry-After` segundos. |
| Página del navegador: «bloqueado por CORS» | *Ajustes → API → Permitir páginas web de otras direcciones* está desactivado, o la petición no tiene token (la respuesta de error de la API lleva las cabeceras, de modo que el motivo real es visible). |
| Ninguna respuesta | ¿Está OpenCue en marcha y es correcto el puerto (Ajustes → Acceso remoto lo muestra)? |

---

## 10. Hardware y control rápido: el flujo WebSocket

Para **hardware** (ESP32, Arduino, Raspberry Pi, una mesa casera) y cualquier aplicación que envíe o reciba **muchos valores pequeños con rapidez**, hay un **WebSocket** junto a las rutas HTTP: `ws://<consola>:8000/api/v1/ws`. Una conexión permanece abierta y ambos lados envían pequeños **mensajes JSON** (tramas de texto), sin el coste de una nueva petición HTTP por valor. No necesita ningún permiso adicional: cada mensaje necesita **el mismo permiso que la ruta HTTP correspondiente** (tabla abajo). Con el preajuste *Operación* todo funciona salvo el DMX en bruto.

### Conectar e iniciar sesión

El token se puede enviar de tres maneras (los microcontroladores encuentran la dirección más fácil):

1. en la dirección: `ws://opencue.local:8000/api/v1/ws?access_token=oc_xxxxxxxx`
2. en la cabecera: `Authorization: Bearer oc_xxxxxxxx` (o `X-API-Key`)
3. como **primer mensaje** en 5 s: `{"op": "auth", "token": "oc_xxxxxxxx"}`

Después OpenCue envía `{"op": "hello", ...}` con los permisos, operaciones, temas y límites permitidos. Los errores cierran la conexión con un código: `4401` (token ausente / incorrecto), `4403` (API desactivada, solo este PC, acceso remoto desactivado, token desactivado), `4429` (demasiados intentos fallidos / demasiadas conexiones). Se aplican las mismas reglas que en HTTP: *API REST activada*, *Accesible desde*, bloqueo tras intentos fallidos. Como máximo hay 10 conexiones abiertas a la vez.

Cada mensaje es un objeto JSON con `"op"`. Un **`"id"`** opcional (cualquier número o texto) vuelve en la respuesta: `{"op": "ack", "id": 7, ...}` si hay éxito, `{"op": "error", "id": 7, "code": "...", "message": "..."}` si hay error. Sin `id` solo se responden los errores. Un mensaje defectuoso nunca termina la conexión.

### Mensajes del hardware

| `op` | Permiso | Qué hace |
|---|---|---|
| `joystick` | Programador | Un joystick – véase abajo |
| `set` | Programador | Ajustar valores, **absolutos** o **relativos** – véase abajo |
| `select` | Programador | Cambiar la selección: `{"op":"select","mode":"set","fixtures":[1,2]}` (`mode`: `set`, `add`, `remove`, `clear`) |
| `cmd` | Comandos | Comando de consola: `{"op":"cmd","line":"Cuelist Main Go"}` (respuesta: `success`, `message`) |
| `cue` | Cues | `{"op":"cue","list":"Main","action":"go"}`; `action`: `go` (con `"cue": 5` salta), `back`, `pause`, `resume`, `stop`, `fader` (con `"value"`) |
| `master`, `blackout` | Blackout / Master | `{"op":"master","value":70}`, `{"op":"blackout","on":true}` |
| `dmx` | Canales DMX | `{"op":"dmx","universe":1,"channels":{"1":255,"2":0}}` – valores de canal en bruto como `PUT /dmx/{universe}` |
| `tap` | Audio | Marcar el tempo (un botón en el ESP32) |
| `timecode` | Timecode | Controlar el timecode: `{"op":"timecode","action":"play"}` (también `pause`, `stop`, `seek`, `rate`) – o `{"op":"timecode","action":"sync","position":12345,"running":true}`: OpenCue **sigue** un reloj externo (posición en ms o `"0:12.345"`; las desviaciones inferiores a 60 ms no se corrigen para que el reloj no tiemble; un salto lo mueve sin disparar cues) |
| `audio_in` | Audio | Audio **de entrada** – véase abajo |
| `subscribe`, `unsubscribe` | por tema | **Suscribirse** a valores en directo – véase abajo |
| `ping` | – | Respuesta `{"op":"pong","t":<su t>,"server_ms":...}`: medir el tiempo de ida y vuelta, comparar relojes |

Los destinos (`set`, `joystick`, `select`) se llaman como en las rutas HTTP: `"fixtures": [1, 2, "Front 3"]`, `"fixture": 5`, `"group": "Front"` y / o `"selection": true` (la selección de la consola). Sin ninguno de ellos se usa la selección.

### Ajustar valores: absolutos y relativos

```json
{"op": "set", "fixtures": [1, 2], "values": {"dimmer": 80, "pan": 25, "color": "#ff8800"}}
{"op": "set", "group": "Front", "mode": "relative", "values": {"pan": 2.5, "dimmer": -10}}
```

- **absoluto** (por defecto): los valores son los nuevos valores – porcentaje 0–100, color como `#rrggbb` / `[r,g,b]`, canales en bruto como `ch<N>` (0–255).
- **relativo** (`"mode": "relative"`): los números son **cambios en puntos porcentuales** (−100 a 100); cada proyector parte de **su propio** valor y se limita en 0 / 100 %. Eso es lo adecuado para potenciómetros giratorios y botones de «un poco más». Los colores y los canales en bruto no pueden ser relativos.

HTTP tiene lo mismo: `PUT /programmer/values` con `"mode": "relative"`. Pan y tilt se ajustan con la **resolución completa de 16 bits** (grueso y fino).

### Joystick

```json
{"op": "joystick", "selection": true, "x": 0.35, "y": -0.8}
```

`x` e `y` van de −1 a 1 (derecha / arriba positivo). Por defecto controla pan (`x`) y tilt (`y`) de los proyectores seleccionados; `"axes": {"x": "pan", "y": "zoom"}` asigna cualquier atributo (`dimmer`, `zoom`, `focus`, `strobe`, `gobo`, `prism` ...). Dos modos (`"mode"`):

- **`rate`** (por defecto, **relativo**): la deflexión fija la **velocidad**, no la posición – como el joystick del programador. Las deflexiones pequeñas son muy precisas (cerca del centro unos 1° por segundo), las grandes rápidas (en el extremo exterior todo el rango pasa en pocos segundos); la curva es exponencial. OpenCue integra el movimiento **por sí mismo a 40 Hz** a partir de la última deflexión comunicada – el dispositivo solo tiene que enviar los cambios y el valor actual cada 20–50 ms; el jitter del WLAN no hace que el movimiento sea brusco. Varios proyectores seleccionados se mueven la misma cantidad desde **su** valor inicial; al final del rango se detienen. Con `x = y = 0` (o dentro de la zona muerta) la palanca está suelta: **los proyectores se quedan donde están**.
- **`position`** (**absoluto**): la deflexión es la posición – `x = −1` es pan 0 %, `x = 1` pan 100 %. No es útil para una palanca con muelle, pero sí para un encoder o un deslizador.

Más campos: `stick` (un nombre cuando un dispositivo tiene varias palancas; por defecto `main`, hasta 4), `speed` (factor 0,05–4 para la velocidad, por defecto 1), `deadzone` (0–0,5, por defecto 0,04), `timeout_ms` (100–5000, por defecto 500), `invert_y`, `release: true` (soltar de inmediato). Los destinos se fijan cuando la palanca se toca por primera vez y se mantienen hasta que se suelta.

**Hombre muerto:** si no llega ningún mensaje durante más de `timeout_ms` (cable desenchufado, WLAN caído, dispositivo colgado) la palanca se detiene y OpenCue informa `{"op":"joystick","stick":"main","state":"timeout"}`. Si la conexión se cae, todos los proyectores se quedan donde están.

### Suscribirse a valores en directo

`{"op":"subscribe","topic":"<topic>","hz":30}` – `hz` es la frecuencia máxima (1–60, por defecto 30). OpenCue solo envía lo que **cambió**. `unsubscribe` con `"topic"` termina la suscripción.

| `topic` | Permiso | Mensajes |
|---|---|---|
| `audio` | Estado | `{"op":"audio","t":ms,"running":true,"v":{"a_level":0.62,"a_bass":0.9,"a_bpm":124,...}}` – las variables de audio del análisis de audio; `"keys": ["a_level","a_bass"]` las limita |
| `dmx` | DMX | `"universes": [1]` (hasta 8): primero `{"op":"dmx","universe":1,"full":true,"values":[512 numbers]}`, después solo `{"op":"dmx","universe":1,"changes":{"17":255}}` (canal → valor) |
| `fixtures` | DMX | `{"op":"fixtures","values":{"3":{"pan":12.5,"tilt":50,"dimmer":100,"color":{...}}}}` – valores en directo por **número** de proyector, solo los que cambiaron |
| `timecode` | Estado | `{"op":"timecode","ms":83400,"text":"00:01:23.400","running":true,"direction":1,"rate":1}` – mientras el reloj corre con cada tic (hasta 60 Hz), si no solo con un cambio (inicio, parada, salto, velocidad) |
| `events` | Estado | como `GET /events`: `{"op":"event","event":"cue","data":{...}}`; `"events": ["cue","blackout"]` elige (por defecto: los tipos estándar; `beat` y `hit` solo bajo petición). Primero llega el estado actual |

### Audio de entrada: un micrófono en el ESP32

Con la fuente de audio **«Red (flujo API)»** OpenCue analiza el audio que envía un dispositivo – nivel, bandas, bombo / caja / hi-hat, tempo y pulso existen entonces como variables `a_` para **efectos, disparadores de cue y el panel Audio** como de costumbre.

1. Abra la fuente: elija *Red (flujo API)* en el panel Audio, o `PUT /audio` con `{"device": "network"}`, o hágalo con el mensaje del paso 2 (`"open": true`).
2. `{"op":"audio_in","rate":16000,"open":true}` – anuncia PCM (`rate` 8000–48000 Hz, **16 bits con signo little endian, mono**).
3. Envíe después **tramas binarias** (WebSocket binario) con las muestras, p. ej. 20 ms cada vez (640 bytes a 16 kHz). Como máximo 64 KB por trama.

Si la fuente no está abierta OpenCue responde (como máximo una vez por segundo) con el error `audio_source`. Sin datos el análisis sigue funcionando sobre silencio.

### Límites y protección

**La salida DMX siempre tiene prioridad**: corre en su propio hilo (prioridad algo mayor) y el flujo está limitado, de modo que el hardware nunca puede ralentizar la consola. Como máximo 300 mensajes por segundo por conexión (ráfagas de hasta 600) y 1200 en total; los demás reciben `rate_limited` y se descartan; mensajes de texto de hasta 8 KB, tramas binarias de hasta 64 KB; 10 conexiones; un joystick cambia como máximo a 40 Hz. Una conexión que no inicia sesión se cierra a los 5 s.

### Ejemplo: ESP32 con un joystick (Arduino)

```cpp
#include <WiFi.h>
#include <WebSocketsClient.h>          // Bibliothek "WebSockets" von Markus Sattler (arduinoWebSockets)

const char* WIFI_SSID = "MeinWLAN";
const char* WIFI_PASS = "geheim";
const char* TOKEN     = "oc_xxxxxxxx";      // Token mit "Programmer" (write.programmer)
const int PIN_X = 34, PIN_Y = 35;           // die beiden Achsen des Joysticks (ADC)

WebSocketsClient ws;
int centerX = 2048, centerY = 2048;

float norm(int raw, int center) {           // 0..4095 -> -1..1
  float f = (raw - center) / 2048.0f;
  return f < -1 ? -1 : (f > 1 ? 1 : f);
}

void onEvent(WStype_t type, uint8_t* payload, size_t length) {
  if (type == WStype_CONNECTED) Serial.println("OpenCue verbunden");
  if (type == WStype_TEXT)      Serial.printf("%s\n", payload);       // hello, Fehler, Rueckmeldungen
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) delay(200);
  delay(300);
  centerX = analogRead(PIN_X);              // Ruhelage beim Start merken
  centerY = analogRead(PIN_Y);
  String path = String("/api/v1/ws?access_token=") + TOKEN;
  ws.begin("opencue.local", 8000, path);    // oder die IP-Adresse der Konsole
  ws.onEvent(onEvent);
  ws.setReconnectInterval(2000);
  ws.enableHeartbeat(15000, 3000, 2);
}

void loop() {
  ws.loop();
  static uint32_t last = 0;
  if (ws.isConnected() && millis() - last >= 20) {      // 50 Mal pro Sekunde
    last = millis();
    float x = norm(analogRead(PIN_X), centerX);
    float y = -norm(analogRead(PIN_Y), centerY);        // nach oben = Tilt mehr
    char msg[128];
    snprintf(msg, sizeof msg, "{\"op\":\"joystick\",\"selection\":true,\"x\":%.3f,\"y\":%.3f}", x, y);
    ws.sendTXT(msg);
  }
}
```

El dispositivo sigue enviando `x = 0, y = 0` en reposo; eso no hace daño (la palanca cuenta como suelta). La selección de la consola decide qué se mueve; con `"fixtures": [1, 2]` o `"group"` en lugar de `"selection": true` el destino es fijo.

### Ejemplo: Python

```python
import asyncio, json, websockets            # pip install websockets

async def main():
    async with websockets.connect("ws://127.0.0.1:8000/api/v1/ws?access_token=oc_xxxxxxxx") as ws:
        print(json.loads(await ws.recv()))                           # hello
        await ws.send(json.dumps({"op": "set", "fixtures": [1, 2], "values": {"dimmer": 80}}))
        await ws.send(json.dumps({"op": "subscribe", "topic": "audio", "hz": 30, "keys": ["a_level", "a_bass"]}))
        async for text in ws:
            frame = json.loads(text)
            if frame["op"] == "audio":
                print(frame["v"])

asyncio.run(main())
```

Una referencia de todos los mensajes también está en la página `/api/v1/docs`.

---

## 11. Vistas de estado: imágenes y páginas web para dispositivos sencillos

Para dispositivos que solo pueden **obtener una imagen** o mostrar una **página sencilla** – un ESP32 con pantalla, una tableta vieja como pantalla de pared, una pestaña del navegador en el monitor del vestíbulo – hay **vistas de estado**. Son **de solo lectura** (sin manejo), no necesitan **ninguna biblioteca** en el dispositivo y OpenCue las genera por sí mismo: el contenido es el mismo como imagen o como página.

| Vista | Muestra | Permiso |
|---|---|---|
| `status` | show, blackout, master, timecode, el cue activo de cada lista, tempo | Estado |
| `timecode` | el reloj, grande, «en marcha / parado» | Estado |
| `dmx` | los 512 canales de un universo como cuadrícula (`?universe=1`), brillo = valor | DMX |
| `cue` | el cue activo de una lista (`?list=Main`) y el siguiente | Estado |
| `audio` | nivel, las ocho bandas, tempo | Estado |

Cada vista existe en varias formas (`GET /api/v1/views/<name>…`):

| Dirección | Resultado |
|---|---|
| `/views/status` | **página web** que se actualiza sola (`?refresh=2` segundos); sin JavaScript mediante meta refresh |
| `/views/status.png` | **imagen PNG** (`?w=320&h=240&theme=dark`; tamaño de 64×48 a 800×600; `theme`: `dark` o `light`) |
| `/views/status.bmp` | **BMP** de 24 bits – cualquier decodificador pequeño lo entiende |
| `/views/status.rgb565` | **píxeles en bruto**, 16 bits cada uno (5-6-5, primero el byte alto); el tamaño está en las cabeceras `X-Width` / `X-Height`: entréguelos directamente a un TFT (no hace falta decodificador) |
| `/views/status.json` | el modelo de visualización (partes: título, filas, barras, cuadrícula) – para quien quiera dibujar por sí mismo |
| `/views` | lista de todas las vistas con sus parámetros |

Inicie sesión como de costumbre. Un navegador o un dispositivo que no pueda enviar una cabecera añade el token (`access_token`, también funciona `token`; los espacios y comillas que se hayan arrastrado al copiar no importan). El mensaje indica si el token **falta** o es **no válido / eliminado**; la consola registra cada inicio de sesión rechazado. Si la primera carga de `opencue.local` se queda colgada (Windows a veces resuelve lentamente los nombres `.local` la primera vez), use la **dirección IP**, que figura en *Ajustes → API REST* (para copiar): `…/views/status?access_token=oc_xxxxxxxx` (el token pasa entonces a formar parte de la dirección; cree para ello un token aparte **con solo «Estado» y «DMX»**). El interruptor **Vistas de estado** en *Ajustes → API REST* lo desactiva todo (respuesta `403 views_disabled`).

**Color:** `?color=green` (o `amber`, `red`, `blue`, `cyan`, `white`, `magenta`, `violet`, `orange`, `yellow`, o `#rrggbb`) cambia el color de resalte; el monitor DMX es **verde** por defecto.

**Los errores son visibles:** si algo va mal (token incorrecto, vistas desactivadas, sin permiso) vuelve una **imagen** (`.png` / `.bmp` / `.rgb565`) con el código de estado correcto (401, 403 ...) **como imagen con el mensaje**; una pantalla simplemente la muestra («TOKEN MISSING OR WRONG», «STATUS VIEWS ARE OFF» ...); la **página web** muestra una página con el mensaje y se recarga cada 5 s. Si no se puede acceder a OpenCue después de abrir la página, la página muestra arriba **«Sin conexión con OpenCue»** y atenúa la última imagen hasta que vuelva a funcionar. `.json` conserva el mensaje de error JSON.

**La salida DMX siempre tiene prioridad:** las imágenes se recalculan como máximo cada 0,4 s por vista y tamaño (muchos dispositivos comparten una imagen), en un hilo en segundo plano, y nunca más de cuatro a la vez. Una imagen de 320×240 cuesta unos 6 ms. El hilo de salida DMX corre además con una prioridad algo mayor.

### ESP32 con un TFT: una imagen cada dos segundos

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <TFT_eSPI.h>                       // 320 x 240 display

TFT_eSPI tft;
uint16_t frame[320 * 240];                  // 150 KB: on an ESP32 without PSRAM ask for 160 x 120 instead

void loop() {
  HTTPClient http;
  http.begin("http://opencue.local:8000/api/v1/views/status.rgb565?w=320&h=240&access_token=oc_xxxxxxxx");
  if (http.GET() == 200) {
    WiFiClient* s = http.getStreamPtr();
    s->readBytes((uint8_t*)frame, sizeof frame);
    tft.setSwapBytes(true);
    tft.pushImage(0, 0, 320, 240, frame);
  }
  http.end();
  delay(2000);
}
```

Para dispositivos con poca memoria: elija un tamaño menor (`w=160&h=120`) o pase el flujo a la pantalla línea por línea.
