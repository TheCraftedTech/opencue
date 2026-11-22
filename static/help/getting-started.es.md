# Primeros pasos con OpenCue

OpenCue es una consola de control de iluminación para tu PC. Esta guía te lleva del instalador a tu primera cue en unos diez minutos – sin luces conectadas, porque los primeros pasos usan el show de demostración incluido.

Todas las guías están también dentro del programa, incluso sin conexión: **Ayuda → Guías** (o **F1**) las abre con una búsqueda (`Ctrl+F` dentro).

---

## 1. Qué necesitas

- Un PC con **Windows 10 u 11** (64 bits). El **Microsoft Edge WebView2 Runtime** muestra la ventana de OpenCue; forma parte de los Windows actuales, y el instalador lo configura si falta (hace falta Internet una vez).
- Para luces reales: una conexión DMX – por red (**Art-Net** o **sACN**) o una **interfaz USB DMX** (Enttec DMX USB Pro y compatibles). Sin hardware puedes programar todo y verlo en la **simulación 3D**.
- Sin cuenta, sin clave de licencia, sin conexión a Internet mientras trabajas.

---

## 2. Instalación

1. Descarga `OpenCue-Setup-v<versión>.exe` de la página de versiones (Releases) del proyecto y ejecútalo.
2. La instalación empieza con una página de bienvenida donde eliges el **idioma** (inglés o alemán; es también el idioma del propio OpenCue – otros idiomas se eligen después en el menú *Idioma*).
3. Avanza: **Licencia** (la GNU GPL, para leer), **Carpeta del programa**, **Carpeta de datos**, **Accesos directos** (menú Inicio, escritorio), el resumen, **Instalar**.
4. Termina e inicia OpenCue.

La **carpeta de datos** es donde viven tus shows, disposiciones, proyectores y ajustes. La ubicación por defecto (`%LOCALAPPDATA%\OpenCue`) sirve para la mayoría; puedes elegir otra en la instalación y cambiarla después en OpenCue en *Ajustes → Almacenamiento*.

Si OpenCue ya está instalado, el instalador lo reconoce y ofrece *Actualizar*, *Reinstalar* o *Desinstalar* – tus datos siempre se conservan. OpenCue también busca versiones nuevas al iniciar (se puede desactivar en *Ajustes → General*) y ofrece instalarlas; *Ayuda → Buscar actualizaciones…* lo hace a petición. La ventana de actualización muestra las notas de la versión; tras una actualización se abre una vez una ventana **Novedades** con las novedades de cada versión que te saltaste (también en *Ayuda → Novedades*).

OpenCue se encuentra con la búsqueda de Windows (tecla Windows y escribe «OpenCue»).

---

## 3. El primer inicio

En una instalación nueva OpenCue abre un **show de demostración** ya preparado llamado **Default_1**:

- cinco **Generic Dimmers** («Dimmer 1» … «Dimmer 5») en el universo 1, canales 1 a 5,
- una lista de cues «Default» con dos cues («Cue 1» y «Cue 2», un segundo de fundido cada una),
- una **disposición** con los paneles que necesitas primero: lista de cues, lista de proyectores, control de proyectores, ejecutor, línea de comandos, botones de comando y teclado numérico.

En el primerísimo inicio se abre un breve **diálogo de bienvenida**: el idioma y luego – solo si quieres – la red (Art-Net, acceso remoto con tu propia contraseña, OSC). No se puede cerrar, se recorre (o se pulsa *Omitir* en la primera página). Nada se activa sin tu consentimiento; si activas algo que usa la red, Windows puede preguntar una vez si OpenCue puede usarla. Tras una actualización, **Ayuda → Novedades** lista los cambios (se abre una vez por sí sola).

En la simulación 3D todavía no existe ningún escenario – lo creas cuando lo necesites. Los archivos de demostración son archivos normales: cámbialos o bórralos como quieras.

---

## 4. La interfaz en un minuto

### Menús (arriba a la izquierda)

| Menú | Contenido |
|---|---|
| **Archivo** | Nuevo / Abrir / Guardar / Guardar como (archivos de show), Cerrar sesión (solo dispositivos remotos), Salir |
| **Editar** | **Editar paneles** (modo edición), Deshacer / Rehacer, **Añadir panel…**, Añadir botón / fader, **Gestionar disposiciones…** |
| **Biblioteca** | **Biblioteca de proyectores…**, escenarios 3D, y el gestor de archivos lista *Shows*, *Disposiciones*, *Escenarios 3D*, *Efectos* |
| **Ver** | Pantalla completa, escala de la interfaz, disposiciones |
| **Idioma** | English / Deutsch / Français / Nederlands / Italiano / Español |
| **Ayuda** | Atajos de teclado, repositorio de GitHub, Novedades, Buscar actualizaciones…, Acerca de OpenCue |

### Barra de herramientas (arriba)

La barra muestra la **disposición** y el **escenario** actuales, el **nombre del archivo de show** (haz clic para abrir el gestor de archivos), un botón **Blackout** que parpadea (bombilla), el **timecode**, un indicador DMX, el número de **dispositivos remotos** conectados y el botón **Ajustes**. Al pasar el ratón sobre una entrada, se ilumina y un **texto emergente** dice qué es. Qué aparece en la barra lo decides tú en *Ajustes → Barra de herramientas e Internet* (cada entrada por separado; solo para este dispositivo; el engranaje siempre es visible).

**Modo operador en palabras sencillas** (*Ver → Modo operador ...*): entregas la consola a alguien que solo debe **manejarla** – mover faders, pulsar botones, lanzar cues – pero no cambiar nada. En modo operador los menús, los ajustes y la reconstrucción están bloqueados, y el **control por voz está apagado** (el micrófono permanece cerrado). Solo se sale con la **contraseña** (candado abajo a la derecha o `Ctrl+L`). Hace falta la contraseña de *Ajustes → Seguridad*. El **bloqueo de pantalla** es otra cosa (*Controles → Bloquear pantalla*, `Ctrl+L`): oscurece todo hasta introducir la contraseña – no se puede manejar nada.

### Paneles

Todo lo demás son **paneles** que colocas libremente. Los más importantes:

| Panel | Para qué sirve |
|---|---|
| **Lista de proyectores** | El patch: añadir, editar y borrar proyectores |
| **Control de proyectores** | Dimmer, posición, color, haz, foco y DMX directo para los proyectores seleccionados; también la cuadrícula de teselas para seleccionar |
| **Lista de cues** | Las cues de una lista: guardar, actualizar, editar, borrar, reproducir |
| **Ejecutor** | Reproducción con Go / Pause / Back / Stop y un fader de mezcla |
| **Línea de comandos**, **Teclado numérico de comandos**, **Botones de comando** | Escritura y entrada táctil de comandos |
| **Variables / Efectos** | Colores, posiciones, haces y efectos reutilizables |
| **Estudio de efectos** | Escribir tus propios efectos |
| **Monitor DMX** | Ver los valores que se envían |
| **Simulación 3D** | Ver tu escenario y tus luces en directo |
| **Timecode**, **Editor de línea de tiempo**, **Reproductor de vídeo/audio**, **Streaming en vivo / cámara** | Tiempo y medios (guía *Editor de línea de tiempo y LTC*) |
| **Audio** | Análisis musical en directo (espectro, beat, tempo): las luces y las cues pueden reaccionar a la música |
| **Control sencillo** | Una superficie de control sencilla para entregar: elegir luces por tesela, **joystick**, brillo, campo de color, zoom, gobos – ver *Acceso remoto → Modo operador* |
| **Botón**, **Fader**, **Interruptor** | Botones, faders e interruptores propios que ejecutan comandos (o los escriben en la línea de comandos) |

Añade paneles con **Editar → Añadir panel…**.

---

## 5. Tu primera cue

Puedes seguir esto con el show de demostración.

### Paso 1 – Seleccionar

Haz clic en proyectores en la pestaña **Proyectores** del panel Control de proyectores (o en la lista de proyectores) – o escribe en la línea de comandos:

```
Fixture 1 Thru 3
```

### Paso 2 – Crear un look

Usa el fader **Dimmer** – o escribe:

```
At 80
```

Elige un color si tus proyectores lo tienen (`Color Red`). Los proyectores modificados reciben una marca roja: ahora están en el **programmer**.

Para cabezas móviles, **Posición** tiene tres vistas: **Gruesa** (faders de pan y tilt), **Fina** (una tira por eje que se desliza: desliza arriba o abajo, las marcas siguen tu dedo – un paso del canal fino cada 4 píxeles) y **Joystick**. El joystick es un mando redondo de dos ejes, **relativo**: cuanto más lo empujas, más rápido se mueve el proyector; el círculo interior es muy preciso, el exterior rápido. Al soltarlo, el mando vuelve al centro y el proyector se queda donde está. Cambia el valor grueso y el fino, y varios proyectores seleccionados se mueven la misma cantidad (sus diferencias se mantienen). Funcionan ratón y táctil.

### Paso 3 – Guardar una cue

Haz clic en **Guardar cue** en el panel Lista de cues. Un diálogo pide la **posición** (al final, tras una cue o libre), el **número de cue** y un **nombre** opcional. Haz clic en **Guardar**. O escribe:

```
Store Cue 3 "Warm look"
```

Si el número ya existe, eliges **Combinar** (solo entran los canales cambiados) o **Sobrescribir**.

### Paso 4 – Reproducirla

Pulsa **Go** en el panel Lista de cues o Ejecutor – o escribe `Go`. El look entra con un fundido durante el tiempo de fundido de la cue. `Go Cue 3` salta directamente a una cue; **Back** retrocede una cue; **Pause** y **Stop** controlan un fundido en curso.

Usa el **fader del ejecutor** para mezclar entre tus valores manuales (0 %) y la cue (100 %). Para un show grande añade **varios paneles Ejecutor**, cada uno ligado a su propia lista de cues (ajustes del panel → lista): cada uno tiene su fader y sus Go / Pause / Back / Stop – junto con el grand master (*Master*) funcionan como submasters.

### Paso 5 – Guardar

Pulsa `Ctrl+S`. Esto guarda el **archivo de show** y tu **disposición**. Sin guardar, los cambios viven solo en memoria; OpenCue pregunta antes de cerrarse.

---

## 6. Conectar luces reales

1. Abre **Ajustes → Salida DMX**.
2. Para **Art-Net**: en el primer inicio está **apagado** (envía a la red) – actívalo. **Buscar dispositivos automáticamente** está activado por defecto: OpenCue busca dispositivos Art-Net en la red (cada pocos segundos) y envía a cada uno directamente, de modo que un nodo que conectes simplemente funciona. **Analizar la red** lista lo que encontró (nombre, dirección, universos); **Usar** convierte un dispositivo en destino fijo. Desactiva el modo automático para escribir tú una **IP de destino** fija (por ejemplo la dirección de difusión Art-Net) y, si hace falta, la **IP de enlace** (qué tarjeta de red usar).
3. Para **sACN (E1.31)**: actívalo. También está apagado por defecto para que Windows no muestre una pregunta del cortafuegos en el primer inicio.
4. Para **USB DMX** (Enttec DMX USB Pro o compatible): actívalo. El **puerto COM** se queda en **Automático (recomendado)**: OpenCue reconoce el adaptador por sí mismo al conectarlo, se conecta y se vuelve a conectar tras desenchufarlo y enchufarlo (incluso en otro puerto USB). Elige el **universo**; elige un puerto COM a mano solo si tienes varios adaptadores.
5. Si una interfaz no arranca, usa **Reinicializar interfaces DMX** – sin reiniciar.

Después haz el **patch** de tus proyectores (guía *Proyectores y patch*): el universo y el canal inicial deben coincidir con la dirección ajustada en cada dispositivo.

El panel **Monitor DMX** muestra exactamente lo que se envía. El botón **Blackout** pone todo el brillo a 0 al instante; al pulsarlo de nuevo vuelve el look.

---

## 7. Hacer tuya la interfaz

- **Modo edición** (**Editar → Editar paneles**, `Ctrl+E`): mover y cambiar el tamaño de los paneles (se puede muy pequeño, el contenido entonces se desplaza), cambiar sus propiedades y colores, copiarlos y pegarlos. Un **clic derecho en el espacio de trabajo vacío** añade un panel, botón, interruptor o fader en el punto del clic. La casilla **Editar → Guías** activa o desactiva las guías de alineación al mover (mantén `Alt`: desactivadas un momento).
- Las **disposiciones** son archivos. Crea varias (por ejemplo una pequeña para programar y una grande para reproducir) y cambia con `Ctrl+1` … `Ctrl+9` o **Ver → Disposiciones**. Guarda con `Ctrl+S` o en el gestor de archivos.
- **Temas** (perfiles de color): *Ajustes → Apariencia* – oscuro, claro o el tuyo.
- **Escala de la interfaz** (`Ctrl +` / `Ctrl -`): agranda todo para pantallas táctiles; se guarda por dispositivo.
- **Idioma:** menú *Idioma* (English, Deutsch, Français, Nederlands, Italiano, Español) o `Ctrl+Mayús+L`. Las guías existen en los seis idiomas.

### Los ajustes de un vistazo

El engranaje (**Ajustes**) abre un diálogo con las categorías a la izquierda, agrupadas por tarea. Las categorías importantes empiezan con un **gran interruptor de encendido/apagado**: cuando está apagado, todo lo de debajo queda atenuado y bloqueado. Nada se aplica antes de pulsar **Guardar** (el diálogo sigue abierto); **Cerrar** pregunta si hay cambios sin guardar. El campo **Buscar en los ajustes ...** también encuentra ajustes en categorías que nunca has abierto y lista los resultados en **todas las categorías** (*ajuste - categoría / sección*); un clic salta a la fila. La pequeña **(i)** tras un ajuste muestra su explicación; el **botón (i) junto al campo de búsqueda** muestra u oculta todas las explicaciones (se recuerda por dispositivo).

**Copia de seguridad de los ajustes:** al final de *General*, **Exportar ajustes** guarda todos los ajustes como archivo (`opencue-settings.json`), **Importar ajustes ...** lee uno. Los valores importados aparecen como **cambios** (marcados y contados) – solo **Guardar** los aplica, **Cerrar** los descarta. No se incluyen contraseñas ni claves de acceso, valores propios del dispositivo o del ordenador (escala, carpeta de datos, micrófonos, dispositivos MIDI) ni las asignaciones de teclado y MIDI – esas tienen su propia exportación.

| Grupo | Categoría | Para qué |
|---|---|---|
| Programa | **General** | Lo básico: idioma, escala de la interfaz, cambiar de disposición deslizando, iniciar con Windows, actualizaciones, copias de seguridad de shows, carpeta de datos, copia de los ajustes |
| Programa | **Apariencia** | Colores, temas, valores por defecto para paneles nuevos |
| Salida | **Salida DMX** | Art-Net, sACN, USB DMX – cada uno con su interruptor, **todo está apagado en el primer inicio** |
| Red | **Acceso remoto** | Tableta / teléfono como mando a distancia: interruptor principal, HTTP / HTTPS, contraseña, direcciones y códigos QR, nombre de red `opencue.local` |
| Red | **API REST** | Otros programas controlan OpenCue: interruptor, *Accesible desde* (solo este ordenador / la red), tokens |
| Controles | **Teclado** | Ver los atajos de teclado, **asignación de teclas personalizada** (guía *Atajos de teclado*) |
| Controles | **MIDI** | Usar MIDI, elegir dispositivos, salida, timecode / tempo desde MIDI, **asignación MIDI** (guía *MIDI*) |
| Voz y audio | **Palabra de activación** | Control por voz con su propio micrófono: palabra de activación + comando en inglés, p. ej. «OpenCue, blackout on» (guía *Comandos de voz*); encendido/apagado con el símbolo del micrófono arriba a la derecha |
| Voz y audio | **Dictado** | Micrófono y modelo de voz para dictar en el chat de IA |
| Asistente | **Asistente de IA** | Interruptor principal, conexión con Ollama, comportamiento, permisos |
| Avanzado | **Más opciones** | **Interruptores rápidos** (control por voz, MIDI, blackout, deshacer incluyendo Go – actúan de inmediato, incluso con su botón oculto en la barra), **Mantener la pantalla encendida** (ordenador y tabletas; en el iPad solo en una página segura, https), qué aparece arriba a la derecha de la barra (cada entrada por separado, por dispositivo) y la **conexión a Internet** (botón *Probar conexión*) |
| Avanzado | **Valores predeterminados** | Valores por defecto para cues nuevas, estado base tras *Clear Clear*, valores iniciales y **Borrado**: una confirmación antes de borrar por categoría (cues, proyectores, biblioteca, archivos, otros) – activada por defecto |
| Avanzado | **Entradas y salidas** | Solo visualización: cada conexión, para qué sirve y **hasta dónde llega** (*solo este PC*, *red local*, *Internet*), con un enlace al ajuste correspondiente |

**En el primer inicio nada sale del ordenador:** el acceso remoto, Art-Net, sACN y la API REST hacia fuera están apagados. Solo está activa la comprobación de actualizaciones (se puede desactivar); necesita Internet. Si Internet funciona en el navegador pero no en OpenCue (cortafuegos, antivirus, red de empresa), *General → Conexión a Internet → Probar conexión* muestra **qué** lo impide.

---

## 8. Qué explorar después

| Tema | Dónde |
|---|---|
| Proyectores, biblioteca GDTF, patch, grupos | *Proyectores y patch* |
| Todos los comandos escritos | *Referencia de comandos* |
| Efectos propios con un pequeño lenguaje de scripts | *Estudio de efectos* |
| Tableta y teléfono como mando a distancia | *Acceso remoto* |
| Cada atajo y gesto | *Atajos de teclado* (también **Ayuda → Atajos de teclado**) |
| Escenario en 3D, apuntar cabezas móviles a un punto | Panel **Simulación 3D** (añádelo con *Añadir panel*; modos Vista / Construcción / Proyectores) |
| Modelos 3D propios (STL u OBJ) en el escenario | Simulación 3D → **Construcción** → **Modelo 3D …** (importar o elegir de la biblioteca; la unidad del archivo mm/cm/m/pulgadas fija el tamaño original). **Importar varios archivos a la vez** (selecciónalos en el diálogo de archivos o arrástralos desde el Explorador al escenario en modo *Construcción*): se colocan uno junto a otro alrededor del centro de la vista y se seleccionan juntos. Se gestionan en el gestor de archivos en **Modelos 3D** |
| Usar un panel brevemente sin ponerlo en la disposición | **Ver → Abrir panel como ventana**; línea de comandos con teclado numérico y teclas: **Ctrl+F** (consola de comandos) |
| Cues que arrancan a una hora | Panel **Timecode** y disparador de cue *Timecode* |
| Luces y cues que reaccionan a la música | Panel **Audio**, efectos con la etiqueta *Audio*, disparador de cue *Audio* (guía *Audio*) |
| Cues que esperan una tecla, pad o fader de un dispositivo MIDI | disparador de cue *MIDI* (guía *MIDI*, sección 5c) |
| Controlar OpenCue desde otros programas | **API REST** (Ajustes → API; guía *API REST*) |
| Archivos: shows, disposiciones, escenarios, modelos 3D, efectos | **Biblioteca → Shows… / Disposiciones… / Escenarios 3D… / Efectos…** (el gestor de archivos, con importación y exportación como ZIP; el paquete de exportación de un show también puede incluir los modelos 3D de su escenario) |

---

## 9. Dónde están tus datos y cómo hacer copias de seguridad

Tus datos son archivos sencillos en la carpeta de datos (`%LOCALAPPDATA%\OpenCue` por defecto):

| Carpeta | Contenido |
|---|---|
| `showfiles` | Shows (proyectores, grupos, cues, presets, efectos) |
| `layouts` | Disposiciones de paneles |
| `themes` | Perfiles de color |
| `fixtures` | Archivos de proyectores GDTF |
| `effects` | Scripts de efectos (`.fx`) |
| `stages` | Escenarios 3D |
| `media` | Vídeos y audio de tus shows |
| `config` | Ajustes (`app_config.json`, incl. la fuente de audio elegida) y los tokens de API (`api_tokens.json`, solo hashes) |

Para hacer una copia de seguridad, copia la carpeta – o usa la **exportación** del gestor de archivos (un show como ZIP con los proyectores y efectos que necesita), que también permite llevar un show a otro ordenador.

Al desinstalar OpenCue se pregunta si también se borran estos datos; la respuesta por defecto es **No**.
