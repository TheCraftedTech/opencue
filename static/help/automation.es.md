# Programación, hora del día y OSC

Tres formas de poner cosas en marcha **sin pulsar Go**: una **programación** que ejecuta comandos a una hora determinada, cues que **esperan una hora** y mensajes **OSC** de otros programas y dispositivos. Los tres están en el menú **Controles**.

---

## 1. Programación: comandos a una hora determinada

**Controles → Programación...** lista comandos que OpenCue ejecuta por sí mismo: para la iluminación de una fachada, «apertura de puertas a las 19:00», un descanso, «iniciar la lista de cues a las 18:55».

- **Nueva entrada** añade una fila. Cada fila tiene: el interruptor **activado / desactivado**, la **hora** (`19:00` o `19:00:30`), la **repetición** (**Todos los días** – el valor por defecto, no hace falta fecha; **En días de la semana** – después haga clic en los botones de los días, lun–vie viene preseleccionado; **Una vez, en una fecha** – la entrada se ejecuta **una vez** ese día y se desactiva sola), un **nombre** y el **comando** – cualquier comando de la línea de comandos, por ejemplo `Cuelist Main Go`, `Blackout Off` o `Master 60` (véase la guía *Línea de comandos*).
- **siguiente: ...** muestra cuándo se ejecutará la entrada la próxima vez. **Ejecutar ahora** ejecuta el comando al instante, para probar. El botón de papelera elimina la entrada: OpenCue pregunta antes (una fila nueva y vacía desaparece sin preguntar). El comando puede contener varios comandos separados por `,` o `;` (`Blackout Off; Cuelist Main Go`).
- El reloj del título es el del ordenador de la consola. Una entrada se dispara **una vez** a su hora, también pasada la medianoche. Si el ordenador estaba suspendido, solo cuentan las horas del **último minuto**: nada se «pone al día».
- La programación **pertenece al show**: se guarda en el archivo del show, forma parte de las copias de seguridad y cambiarla marca el show como sin guardar. Cada ejecución aparece en el historial de comandos y como un mensaje breve.

---

## 2. Un cue que espera una hora

En el cuadro de diálogo del cue elija el disparador **Hora del día** (o escriba `clock 19:30` / `clock 20:00 sat,sun` en la celda del disparador, o use el comando `Cue 3 Trigger Clock 19:30 Mon-Fri`). El cue se comporta entonces como los demás disparadores (audio, MIDI, timecode): cuando es el **siguiente cue de una lista en marcha**, se dispara en cuanto el **reloj alcanza esa hora** en uno de los días elegidos. Si su hora ya ha pasado cuando se convierte en el siguiente cue, espera a la siguiente ocasión; no se dispara de inmediato.

Uso típico: *Cue 1 (Go, luces de sala) – Cue 2 (Hora del día 19:30, inicio del espectáculo) – Cue 3 (Follow)*. La programación puede iniciar la lista a las 18:55; el cue de reloj espera entonces a las 19:30.

---

## 3. OSC

**OSC (Open Sound Control)** es un protocolo de red que hablan muchas aplicaciones y dispositivos: **TouchOSC** (faders y botones en tableta / teléfono), **QLab**, **Ableton**, controladores de show. Con él, otro software controla OpenCue y OpenCue puede enviar mensajes.

**Controles → OSC ...** (el interruptor y el puerto también están en **Ajustes → OSC**; ambos cambian el mismo ajuste):

1. Active **Recibir OSC**. Se muestran el **puerto UDP** (por defecto `9000`) y las direcciones de este ordenador; introdúzcalos en la otra aplicación (`192.168.1.20:9000`). Está **desactivado** hasta que lo active; Windows puede preguntar una vez por el firewall (*Ajustes → Acceso remoto → Firewall de Windows* lo configura).
2. Las **direcciones integradas** funcionan al instante: `/opencue/go`, `/opencue/back`, `/opencue/pause`, `/opencue/resume`, `/opencue/stop`, `/opencue/blackout` (1 = activado, 0 = desactivado, sin valor = alternar), `/opencue/master` y `/opencue/fader` (valor de 0 a 1), `/opencue/cue/<número>` (saltar a ese cue). Un botón que envía 1 al pulsar y 0 al soltar se gestiona correctamente: solo cuenta la pulsación.
3. **Sus direcciones**: **Nueva asignación** – la **dirección** (`/my/button1`, se permiten `*` y `?`), el **comando** y cuándo se ejecuta: **solo al pulsar** (valor mayor que 0) o **con cada mensaje** (para faders). En el comando, `{value}` es el primer valor del mensaje **convertido a un rango** (por defecto 0..1 pasa a 0..100): `Master {value}` con un fader. **Aprender** toma la dirección del siguiente mensaje que llegue: pulse el botón en la otra aplicación. *En el historial* muestra el comando en el historial de comandos (un flujo de fader lo inundaría). El botón de papelera elimina la asignación: OpenCue pregunta antes. Aquí también se pueden encadenar los comandos (`Blackout On, Cuelist Main Stop`).
4. El **monitor** de abajo muestra cada mensaje entrante y en qué quedó (*integrada*, *asignación*, *sin asignación*, *bloqueado*).
5. **Direcciones integradas** (desplegar): desactivarlas todas, cambiar el **prefijo** (`/opencue/go` pasa a ser, por ejemplo, `/light/go` si otro programa ya usa `/opencue`) y desactivar direcciones **individuales**.
6. **Enviar a** fija el destino de los mensajes propios de OpenCue: **Enviar mensaje de prueba** o el comando `Osc /address 0.5` (véase *Línea de comandos*).
7. **Devolver el estado (retorno)**: OpenCue informa de su estado **por sí mismo** al destino (y, si *También a cada remitente* está activado, a cada dispositivo que le haya enviado un mensaje en la última hora, en el puerto del destino). Eso es lo que necesitan las pantallas y las luces de botón de TouchOSC. Solo se envían los **cambios**, más todo de golpe al activarlo, cuando aparece un dispositivo nuevo y con **Enviar todo ahora**. Se informa de (bajo el mismo prefijo que las direcciones integradas): `/opencue/cuelist` (nombre de la lista activa), `/opencue/cue` (número del cue activo, `-1` = ninguno), `/opencue/cuename`, `/opencue/state` (`running`, `paused`, `stopped`, `done` o `idle`), `/opencue/fader` y `/opencue/master` (0 a 1), `/opencue/blackout` (1 / 0) y `/opencue/cue/<número>` = `1` para el cue activo y `0` cuando termina (la luz de un botón de cue). En **Qué se informa** se pueden desactivar mensajes individuales. Está **desactivado** hasta que lo active.

**Seguridad:** OSC **no tiene contraseña**: cualquiera en la red puede enviar. Por eso está desactivado por defecto; **Remitentes permitidos** lo limita a direcciones (`192.168.1.` = toda la subred, o una dirección concreta); y una avalancha de mensajes se frena (300 mensajes por segundo). `/opencue/cmd "<comando>"` podría ejecutar **cualquier** comando (también *Delete*), por lo que solo funciona si activa **Permitir cualquier comando**.

---

## 4. DMX plug and play

(También en la guía *Primeros pasos*, sección 6.) **Art-Net: Ajustes → Salida DMX → Buscar dispositivos automáticamente** busca dispositivos en la red y envía a cada uno de ellos. **Escanear red** los lista. **DMX USB**: deje el puerto COM en **Automática**: conecte el adaptador y se conecta, también tras desenchufarlo y volverlo a enchufar.
