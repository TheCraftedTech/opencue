# Opciones de inicio y modo servidor

OpenCue se puede iniciar con opciones: en un acceso directo, un archivo por lotes, el Programador de tareas o un terminal. Esta guía las enumera, explica el **modo servidor sin ventana** (`--no-ui`), **Iniciar con Windows**, qué cambian (y qué no) los **derechos de administrador** y la regla del **Firewall de Windows**.

---

## 1. Las opciones

Póngalas detrás del programa: `OpenCue.exe --no-ui --open-browser` (desde el código fuente: `python main.py ...`). En un acceso directo: *Propiedades → Destino*, después de las comillas de cierre de la ruta.

| Opción | Qué hace |
|---|---|
| `--no-ui` o `--server-only` | Inicia **sin ventana del programa** (sección 2). Implica `--no-splash`. |
| `--open-browser` | Con `--no-ui`: abre al iniciar el navegador predeterminado en la consola. |
| `SHOWFILE` o `--show ARCHIVO` | Carga este show en lugar del último. Un archivo de show como primer parámetro funciona como un inicio con doble clic; esto incluye un archivo `.ocshow` (paquete de exportación). Si OpenCue ya se está ejecutando, el programa en marcha toma el archivo (y antes pregunta por los cambios sin guardar). |
| `--new-show` | Inicia con un **show vacío** en lugar del último. No se borra nada; el show «usado por última vez» queda como estaba. |
| `--port N` | Puerto del servidor **solo para esta ejecución** (1–65535). El ajuste guardado no cambia. |
| `--remote` | Activa el **acceso por red** (como en *Ajustes → Acceso remoto*); este ajuste **se guarda**. |
| `--data-dir CARPETA` | Usa otra **carpeta de datos** para esta ejecución (uso portátil, pruebas). Igual que la variable `OPENCUE_DATA_DIR`. |
| `--fullscreen` | Inicia la ventana del programa a pantalla completa. |
| `--priority normal`, `above` o `high` | Prioridad del proceso; por defecto `above` (superior a la normal), véase la sección 5. |
| `--no-splash` | Sin pantalla de inicio (también: `OPENCUE_NO_SPLASH=1`). |
| `--version`, `--help` | Muestra la versión o la lista de opciones. |

El programa compilado no tiene consola propia: `--help` y `--version` escriben en la consola desde la que se inició (cmd, PowerShell).

---

## 2. Modo servidor sin ventana (`--no-ui`)

OpenCue arranca como de costumbre – salida DMX, cues, efectos, MIDI, acceso remoto, la API REST – pero **no se abre ninguna ventana del programa**. Se maneja desde

- **un navegador de este ordenador:** `http://127.0.0.1:8000` (el puerto de *Ajustes → Acceso remoto*, o `--port`): exactamente la misma consola que en la ventana, o
- **una tableta o un teléfono** por la red (active el **Acceso remoto** en los ajustes o inicie una vez con `--remote`).

Un **icono en el área de notificación** de la barra de tareas muestra que OpenCue está en marcha: un **clic** abre la consola en su navegador; el **clic derecho** abre el menú *Abrir OpenCue en el navegador*, *Abrir carpeta de registros* y *Salir de OpenCue*. Si el show tiene cambios sin guardar, al salir se pregunta una vez (en cualquier caso se guarda una copia de seguridad).

El menú muestra arriba el **nombre del show**, el aviso **⚠ Cambios sin guardar** cuando los hay (también la información sobre herramientas del icono) y las **direcciones** en las que se puede acceder a la consola (con el acceso remoto activado, también las de la red); un clic abre una en el navegador.

Otras formas de salir: **Archivo → Salir** en el navegador, **Ctrl+C** si se inició desde un terminal, y cerrar sesión o apagar Windows (OpenCue intenta entonces cerrarse limpiamente, con la copia de seguridad habitual).

**Iniciar OpenCue una segunda vez** mientras el servidor está en marcha no muestra ningún error: simplemente abre su navegador en la consola en ejecución.

Lo que **puede no funcionar** sin la ventana: lo que necesita la propia ventana nativa del programa, por ejemplo el selector de archivos para *vincular* un archivo de vídeo o audio, o el cambio a pantalla completa de la ventana. Todo lo demás está disponible en el navegador.

Consejo: para un PC de escenario que solo emite DMX, active *Iniciar OpenCue al iniciar sesión en Windows* + *Iniciar sin ventana* (sección 3).

---

## 3. Iniciar con Windows

**Ajustes → General → Comportamiento:**

- **Iniciar OpenCue al iniciar sesión en Windows** – una entrada para **su usuario de Windows** (no se necesitan derechos de administrador; se elimina desactivando la opción).
- **Iniciar sin ventana (solo servidor)** – inicia con `--no-ui`.

Esto está disponible en el **programa instalado**, no al iniciar desde el código fuente. (Un show exportado con la extensión `.ocshow` siempre se abre en OpenCue con un doble clic; no hay interruptor para ello.) La entrada apunta al archivo del programa: si mueve o reinstala OpenCue en otro sitio, desactive y vuelva a activar la opción.

---

## 4. Derechos de administrador y el firewall

**¿Se ejecuta OpenCue como administrador?** El registro (`opencue.log`, primeras líneas) y los detalles de un informe de error indican *«Administrator: yes»* o *«no»*. Si es así, OpenCue también escribe una nota en el registro.

**No lo necesita – y no debería usarlo:** Windows bloquea **arrastrar archivos desde el Explorador** a un programa que se ejecuta como administrador, y un servidor web con derechos de administrador es un objetivo mayor. Los derechos de administrador ayudan en **una** cosa: crear la **regla del Firewall de Windows**.

**Regla de firewall:** sin ella, Windows pregunta la primera vez que OpenCue usa la red; una pregunta sin responder o rechazada bloquea las tabletas, el sACN y el nombre de red `opencue.local`. **Ajustes → Acceso remoto → Firewall de Windows → Permitir OpenCue en el firewall** crea una regla para exactamente este programa, **de entrada, solo en redes privadas y de dominio** (nunca en las públicas). Windows pide permiso **una sola vez** (aviso de administrador): solo este pequeño comando se inicia con derechos elevados, OpenCue en sí sigue ejecutándose con normalidad. *Quitar la regla de firewall* la elimina de nuevo. La línea de estado muestra si la regla existe.

---

## 5. Prioridad y temporización exacta

Al iniciar, OpenCue pone la **prioridad del proceso** en *superior a la normal* y la **resolución del temporizador en 1 ms** (Windows normalmente marca cada 15,6 ms). Ambas mantienen fluidos los bucles de 40 Hz de cues, efectos y DMX cuando el ordenador está ocupado; no se necesitan derechos de administrador. `--priority high` la sube aún más (para un PC que no hace nada más), `--priority normal` la desactiva.

---

## 6. Ejemplos

- Servidor en un PC de escenario, se abre el navegador: `OpenCue.exe --no-ui --open-browser`
- Abrir un show desde *Abrir con* del Explorador: `OpenCue.exe "D:\Shows\Concert.json"`
- Iniciar vacío sin tocar el último show: `OpenCue.exe --new-show`
- Probar en otro puerto con datos propios: `OpenCue.exe --port 8080 --data-dir D:\OpenCueTest`
