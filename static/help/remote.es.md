# Acceso remoto (tableta y teléfono)

Con el **acceso remoto** manejas OpenCue desde un iPad, una tableta, un teléfono o cualquier otro ordenador de la **misma red** – mientras el ordenador consola sigue ejecutando el show y enviando el DMX. Recorre la sala y ajusta luces, lanza cues desde el escenario, o usa una tableta como segunda pantalla.

El acceso remoto está **desactivado por defecto**. Mientras esté desactivado, OpenCue no es accesible desde la red en absoluto (el puerto está realmente cerrado, no solo protegido con contraseña).

---

## 1. La idea en un minuto

- La **consola** es el ordenador donde OpenCue está instalado y funcionando. Hace todo el trabajo: contiene el show, calcula las cues y envía el DMX.
- Un **dispositivo remoto** es solo un navegador. Abre una dirección web de la consola, inicia sesión con la contraseña y muestra **la misma interfaz de OpenCue** – misma barra, mismos paneles, mismos derechos.
- Todo permanece sincronizado en directo: cuando seleccionas un proyector, mueves un fader o pulsas *Go* en un dispositivo, todos los demás lo muestran enseguida.
- No hace falta Internet. Todo ocurre dentro de tu red local.

---

## 2. Activarlo

1. En la consola abre **Ajustes** (barra de herramientas) → categoría **Acceso remoto**.
2. Activa el **interruptor principal del acceso remoto** arriba. **No hay contraseña por defecto:** la primera vez OpenCue pide la tuya – **«Elige una contraseña»**, introducida dos veces (al menos 4 caracteres; *Cancelar* vuelve a desactivar el acceso remoto). Después **HTTP** queda activado.
3. La **contraseña** se define y se cambia en **Ajustes → Seguridad** (botón *Definir o cambiar contraseña ...* en la sección Acceso remoto); esto también funciona desde un dispositivo remoto (su propio inicio de sesión se conserva; todos los demás dispositivos tienen que iniciar sesión de nuevo). Usa *Mostrar* para comprobar lo que escribiste. La misma contraseña protege el bloqueo de pantalla (sección 8). Se permite cualquier contraseña (al menos 4 caracteres) – la elección es tuya.
4. Opcionalmente cambia el **puerto HTTP** (1024–65535, por defecto 8000). Un puerto cambiado surte efecto tras reiniciar OpenCue.
   **HTTPS** es una sección propia más abajo con su propio interruptor y su propio **puerto HTTPS** (por defecto 8001, efecto inmediato): algunas funciones del navegador necesitan una **página segura (https)**: **mantener encendida la pantalla del iPad** (Ajustes → Más opciones → *Mantener la pantalla encendida*), el modo VR de la simulación 3D, y micrófono y cámara en el navegador. Abre por tanto la **dirección https://** en el iPad (confirma el certificado una vez); con `http://` solo funciona el ajuste del dispositivo «Bloqueo automático: Nunca». OpenCue crea el certificado él mismo; el navegador pide confirmarlo una vez en la primera visita. HTTP y HTTPS se activan y desactivan de forma independiente y cada uno tiene su propia dirección con su propio código QR.
   **Nombre de red:** la consola también es accesible como `opencue.local` (viene automáticamente con el acceso remoto; un pequeño interruptor en *Avanzado*), por ejemplo `http://opencue.local:8000` – la dirección es la misma en todas las redes. Si el nombre ya está ocupado (por ejemplo por una segunda consola), OpenCue usa `opencue-2.local` y así sucesivamente; los ajustes muestran cuál vale. iPad, iPhone, Mac y Windows 10/11 entienden el nombre por sí solos. Una app web instalada está ligada a su dirección: si cambias al nombre, instálala otra vez.
5. Haz clic en **Guardar** (el diálogo sigue abierto). No hace falta reiniciar. La primera vez Windows pregunta una vez por el cortafuegos – permite las **redes privadas**.

OpenCue escucha ahora en todas las direcciones de red de la consola. La página muestra:

| Elemento | Significado |
|---|---|
| **Estado** | «Accesible en la red» o «Solo local». |
| **Direcciones** | Cada dirección con la que se puede llegar a la consola, cada una con un botón **Copiar**. |
| **Código QR** | Para la dirección seleccionada – escanéalo con la cámara de un iPad o teléfono. Al conectar se pide la contraseña. |
| **Detectar direcciones de nuevo** | Tras cambiar de Wi-Fi o conectar un cable. |

Al desactivarlo de nuevo, los oyentes se cierran de inmediato.

> **Cortafuegos de Windows:** cuando el acceso remoto se activa por primera vez, Windows puede preguntar si OpenCue puede comunicarse en la red. Permítelo para tu red **privada**; si no, los demás dispositivos no pueden conectarse.

---

## 3. Conectar un dispositivo

1. Asegúrate de que el dispositivo está en la **misma red** (mismo Wi-Fi o LAN) que la consola.
2. Abre la dirección de la página de ajustes en el navegador del dispositivo – por ejemplo `http://192.168.1.20:8000/` – o escanea el código QR. La dirección redirige a la página remota `/remote/`.
3. Introduce la contraseña y toca **Iniciar sesión**.

**Recordar contraseña** (casilla en la página de inicio de sesión) guarda la contraseña solo en el navegador de **ese dispositivo** y rellena el campo la próxima vez. No hay inicio de sesión automático – sigues tocando *Iniciar sesión*. Desmarca la casilla para borrar al instante la contraseña guardada.

**Contraseña incorrecta:** los intentos erróneos repetidos bloquean el dispositivo durante un rato (protección contra fuerza bruta).

**Cerrar sesión:** *Archivo → Cerrar sesión* (solo se muestra en dispositivos remotos).

Si nada se conecta: comprueba que ambos dispositivos están en la misma red (las redes Wi-Fi de invitados suelen separar los dispositivos entre sí), que la dirección coincide con la de la página de ajustes y el cortafuegos (ver arriba).

---

## 4. Qué puede hacer un dispositivo remoto

- **Todo lo que puede la consola.** Tras iniciar sesión, un dispositivo remoto tiene los mismos derechos: programación, cues, efectos, archivos, ajustes, ajustes DMX y ajustes de acceso remoto. Eso incluye cosas con consecuencias – desactivar el acceso remoto (lo que deja fuera a ese dispositivo) o **cerrar OpenCue**, lo que detiene el programa para todos. Usa una contraseña que solo conozcan personas de confianza.
- **Disposición propia por dispositivo.** Cada dispositivo recuerda qué disposición usó y puede mostrar una distinta de la consola. Crea para la tableta una disposición con botones grandes (ver abajo). Si un dispositivo guarda una disposición que otro está mostrando, el otro la adopta – o, si tiene cambios propios sin guardar, ofrece *Aplicar* o *Mantener mi versión*.
- **Acceso completo a todos los ajustes, también desde el iPad.** Esto importa cuando OpenCue funciona sin ventana (*solo servidor*, icono de la bandeja): todos los ajustes – salida, seguridad y modo de bloqueo, API REST, asistente de IA, control por voz, copias de seguridad, iniciar con Windows, valores predeterminados, entradas / salidas ... – se pueden cambiar en el iPad y se aplican **al servidor**. El interruptor del micrófono del control por voz también está en el iPad. **Carpetas:** donde el ordenador principal abriría el Explorador de Windows, un dispositivo remoto recibe el **Explorador de OpenCue** – un diálogo grande para la carpeta de datos de OpenCue (shows, copias de seguridad, registros, proyectores ...): explorar, descargar (una carpeta como ZIP), subir, nueva carpeta, renombrar, duplicar, borrar. No puede salir de la carpeta de datos. El mismo diálogo (*Elegir carpeta...*) permite elegir una nueva ubicación de almacenamiento. El **aprendizaje / la monitorización MIDI**, la **entrada DMX** y la **regla del cortafuegos** (Windows pide permiso en el ordenador principal) también funcionan desde el iPad. Solo unas pocas cosas dependen **físicamente del ordenador principal**: su ventana (pantalla completa), el **bloqueo de pantalla** de la consola (desbloquéala allí), grabar la tecla de un **teclado concreto**, el **micrófono al dictar** y el verdadero Explorador de Windows.
- **Por dispositivo:** solo el **modo pantalla completa** (el de cada navegador) y la **escala de la interfaz**.
- **Los datos permanecen en la consola.** Guardar y cargar siempre pasan por la consola; shows, disposiciones y proyectores viven en el ordenador consola.

### ¿Quién está conectado?

Un icono de la barra de herramientas muestra **cuántos dispositivos remotos están conectados**. Haz clic para ver la dirección IP, el dispositivo y el tiempo de conexión de cada uno – y para **desconectar** (*Expulsar*) un dispositivo. Un dispositivo desconectado ve un aviso y debe recargar la página para iniciar sesión de nuevo.

---

## 5. Instalar como aplicación (iPad / iPhone / Android)

La página remota es una **app web**. En el dispositivo puedes añadirla a la pantalla de inicio:

- **iPad / iPhone (Safari):** botón Compartir → **Añadir a pantalla de inicio**.
- **Android (Chrome):** menú → **Instalar aplicación** / **Añadir a la pantalla de inicio**.

Después se abre a pantalla completa sin barras del navegador, con los colores de tu tema actual.

**Icono:** la app recibe el icono de OpenCue y el nombre «OpenCue» – también por HTTPS. (El icono está incrustado en la página; si no, iOS no lo descarga con un certificado autocreado y muestra solo una letra gris.) Si el icono sigue sin cambiar, elimina la app de la pantalla de inicio y añádela de nuevo – iOS recuerda el icono antiguo.

**Página sin conexión y elección de servidor (página segura, HTTPS):** cuando no se puede alcanzar el servidor, la app muestra «**Servidor no accesible**» en lugar de una página de error. Allí puedes **Recargar**, o introducir una nueva **dirección o IP**, el **puerto** y **HTTPS** activado / desactivado en **Otro servidor** y **Conectar** – si el ordenador tiene una nueva dirección IP no hace falta reinstalar la app. Las direcciones usadas recientemente aparecen debajo para tocarlas. Si la conexión se pierde (Wi-Fi caído, OpenCue cerrado), aparece el aviso «Restableciendo la conexión»; tras 3 segundos con el botón «**Elegir otro servidor (7 s)**» cuyo número **cuenta atrás**; al llegar a 0 la página sin conexión se abre sola y vuelve a cargar OpenCue en cuanto el servidor responde. Esto también vale cuando hay Wi-Fi pero el ordenador no responde – entonces la página sin conexión aparece tras **unos 1,5 segundos** en lugar de una pantalla blanca y desaparece de inmediato cuando el servidor responde. Si la abres a propósito con el botón, se queda. Consejo: el nombre `opencue.local` encuentra el ordenador incluso cuando cambia la IP.

**Importante en el iPad – instala el certificado una vez:** con un certificado autocreado, iOS solo conoce la excepción «continuar a pesar de la advertencia» **dentro de la pestaña de Safari**. Una app de la pantalla de inicio se queda entonces **en blanco**, y el service worker (página sin conexión) no está permitido. Por eso OpenCue crea su propia autoridad de certificación («OpenCue Local CA») que firma el certificado https. La instalas **una vez** en el dispositivo:

Los pasos son una **página guía** en el servidor: *Ajustes → Acceso remoto → Certificado para iPad y navegadores* muestra su dirección y un código QR (escanéalo con la cámara del iPad). La página se abre por **http://** sin inicio de sesión y sigue el idioma del dispositivo. Arriba eliges entre **iPad / iPhone** y **Android · Windows · macOS**. Para el iPad hay cuatro pasos con un recordatorio: **Descargar → Instalar → Confiar → Abrir https**; puedes marcar los pasos terminados (la página los recuerda). **Importante: abre la página en Safari** – el perfil no se puede instalar desde la app de la pantalla de inicio, desde Chrome ni desde el navegador dentro de otra app. «Ajustes» significa la **app Ajustes del iPad**, no un ajuste de Safari. Al final de cada página se indica cómo **quitar de nuevo el certificado** (iPad: Ajustes → General → VPN y gestión de dispositivos → «OpenCue» → Eliminar perfil). En OpenCue lo mismo está en *Ajustes → Acceso remoto → Certificado para iPad y navegadores* (versión corta para instalar y quitar). (El acceso por HTTP debe estar activado para esto.)

A partir de entonces https funciona sin advertencia, la app se abre, el service worker y la página sin conexión funcionan – también cuando el ordenador recibe una **nueva dirección IP** (OpenCue solo vuelve a emitir el certificado del servidor, la autoridad permanece). La autoridad solo puede avalar nombres locales (`.local`, `localhost`) y direcciones privadas. Android / Windows / macOS: instala el archivo de certificado (`opencue-ca.crt`) y configúralo como autoridad de confianza. Si borras la carpeta `https` de la carpeta de datos, se crea una nueva autoridad – vuelve a instalar el perfil en los dispositivos.

**Limitación:** las apps web instalables y la página sin conexión necesitan una conexión segura (HTTPS, en el iPad con el certificado instalado). Con `http://` simple la app de la pantalla de inicio funciona, pero no hay página sin conexión y el dispositivo debe alcanzar la consola para mostrar algo.

---

## 6. Consejos para una buena disposición de tableta

- Crea una **disposición aparte** para la tableta (*Editar → Gestionar disposiciones…*): un **Ejecutor** grande, la **Lista de cues**, algunos paneles **Botón** o **Fader** y la categoría del **Control de proyectores** que más necesites. Los dispositivos remotos cargan su propia disposición, así que la disposición de la consola se queda como está.
- Para el táctil usa los paneles **Teclado numérico de comandos** y **Botones de comando** en vez de escribir con el teclado en pantalla.
- Aumenta la **escala de la interfaz** en la tableta (`Ctrl +` o *Ver → Escala de la interfaz…*) – vale solo para ese dispositivo.
- Las disposiciones se pueden cambiar **deslizando** en horizontal si *Ajustes → General → Cambiar de disposición deslizando* está activado (por dispositivo).
- Las listas de cues con disparadores de timecode siguen funcionando en la consola aunque un dispositivo se desconecte – el show no depende de la tableta.

---

## 7. Seguridad y buenas prácticas

- Usa el acceso remoto solo en redes de confianza (tu propio router, una red de show dedicada). La conexión **no está cifrada** (HTTP simple); cualquiera en la red podría leer el tráfico.
- Elige una contraseña que no uses en otro sitio – se guarda en la configuración de la aplicación en la consola y, si marcas *Recordar contraseña*, en el navegador de ese dispositivo.
- Desactiva el acceso remoto cuando no lo necesites.
- La salida DMX funciona siempre en la consola – aunque todos los dispositivos remotos se desconecten, las luces se quedan como están.

## 8. Bloqueo: bloqueo de pantalla y cierre de sesión

**Ajustes → Seguridad** contiene el **modo de bloqueo** (desactivado por defecto, pide la contraseña):

- **En la consola:** el **candado** de la barra superior, **Ctrl+L** (modificable en *Controles → Atajos de teclado*) o **Controles → Bloquear** bloquea OpenCue. Una consola bloqueada muestra solo una ventana oscura de contraseña – el resto de la interfaz está oculto, el teclado no hace nada, y la consola ya no acepta cambios desde esta ventana (ni siquiera sorteando la interfaz). Recargar **no** desbloquea. **El show sigue:** cues, efectos, MIDI, OSC, la programación y los dispositivos remotos funcionan como antes. Cinco contraseñas erróneas seguidas pausan el desbloqueo durante un minuto. La contraseña nunca sale de la consola mientras está bloqueada. Reiniciar OpenCue desbloquea.
- **En un dispositivo remoto:** el candado **cierra la sesión del dispositivo**: la sesión termina, la *contraseña recordada* de ese dispositivo se borra, y la página muestra de nuevo el inicio de sesión con el campo de contraseña vacío. Los dispositivos remotos no pueden cambiar la contraseña ni el modo de bloqueo.
- **Bloquear automáticamente tras ...** (1 a 60 minutos sin ninguna entrada; desactivado por defecto): la consola se bloquea sola, los dispositivos remotos cierran sesión. Cuidado con una tableta que solo muestra: deja el ajuste desactivado para esas.

## 9. Control sencillo y modo operador (para entregar la consola a otra persona)

- El **panel «Control sencillo»** (*Editar → Añadir panel → Entrada*) es el hermano sencillo del panel *Control de proyectores* y usa **todo el panel** con campos fijos en porcentaje: a la izquierda (38 %) **cada proyector tiene su propia tesela** (número, nombre, color y brillo en directo), ordenadas por **grupos** (tocar el nombre del grupo = seleccionar todo el grupo; el resto ordenado por tipo; *Todos* / *Ninguno* arriba); a la derecha **brillo** (fader grande, *Off* / *Full*), **color** (campo de color – tono de izquierda a derecha, más blanco hacia arriba – más botones de color), **movimiento** (**joystick** de muelle: empuja – cuanto más lejos, más rápido; suelta = parar; *Centro*), **zoom**, **gobos** como imágenes, un gran botón **Blackout** y los **looks**: *Arcoíris*, *Círculo* (pan / tilt), *Pulso*, *Estrobo* – efectos estándar ya preparados sin ningún ajuste (tocar otra vez = apagado, *Looks off* quita todo; el efecto se añade automáticamente al show la primera vez). Un control que las luces seleccionadas no tienen se queda en su sitio pero atenuado. En un **panel estrecho** (menos de unos 720 px) pasa a un **modo compacto** con una pestaña por área (*Luces | Brillo | Color | Movimiento | Haz | Looks*; Blackout sigue visible). Nada aquí cambia grupos ni el show; selección, valores y efectos son los de todo el programa (programmer, cues, estudio de efectos). Crea una disposición con solo este panel (o unos pocos más) para la persona que debe manejar.
- El **modo operador** (*Ver → Modo operador ...* o el botón joystick de la barra superior; pide la contraseña, *Ajustes → Seguridad*): este dispositivo **solo puede manejar** lo que hay en pantalla – sin menús, sin barra superior, sin ajustes ni otros diálogos, sin atajos de teclado (escribir en un campo de texto sigue funcionando), sin mover ni reconstruir paneles, sin cambiar de disposición ni de show. Se sale con el pequeño **candado abajo a la derecha** y la contraseña, o con **Ctrl+L**. Solo se inicia desde el menú o el botón (sin atajo de teclado). Los **comandos** (línea de comandos, teclas, widgets) el servidor los ejecuta en modo operador solo si **manejan**; todo lo que cambia el show (*Store, Update, Delete, Move, Label, Set*, tiempos de cue, crear / renombrar / borrar listas de cues) se rechaza – también dentro de una cadena de comandos. **En la consola el control por voz está apagado en modo operador** (el micrófono permanece cerrado) y vuelve después si está activado. El **servidor lo impone**: desde un dispositivo en modo operador solo se aceptan mensajes de manejo (seleccionar, fijar valores, cues, presets, timecode, línea de comandos ...); los mensajes de programación, disposición, show y ajustes se descartan y las peticiones de escritura reciben la respuesta `423`. Recargar no sale del modo. Funciona en la consola y en cada dispositivo remoto por su cuenta (entrega un iPad con la app en modo operador); reiniciar OpenCue lo termina. Cinco contraseñas erróneas seguidas pausan la salida durante un minuto.
- **Bueno saber:** la línea de comandos, si la pones en esa disposición, puede ejecutar cualquier comando – déjala fuera de una disposición para invitados. Las teclas de un teclado adicional dedicado (*Atajos de teclado personalizados*, específicos del dispositivo) y los controladores MIDI / OSC siguen funcionando: pertenecen al show, no a la pantalla.
