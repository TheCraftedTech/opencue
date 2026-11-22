# Códigos de error y solución de problemas

Cuando algo va mal, OpenCue no desaparece sin más: muestra una pequeña **ventana de error** con una breve explicación y un **código de error** como `OC-1002`. El mismo código se escribe en el **archivo de registro**. Esta página explica cada código: qué significa y cómo solucionarlo.

Si no puede resolver un problema, copie los detalles (véase la sección 1) y envíelos con su consulta; el código nos indica de inmediato dónde mirar.

---

## 1. La ventana de error

La ventana tiene un titular, una breve explicación, el **CÓDIGO DE ERROR**, a veces un cuadro con detalles técnicos, y estos botones:

| Botón | Qué hace |
|---|---|
| **Copiar detalles** | Pone en el portapapeles todo lo necesario para un informe de error: código de error, versión de OpenCue, versiones de Windows y Python, el texto del error y las **últimas 40 líneas del registro**. Péguelo en un correo, una incidencia de GitHub o un chat con un asistente. (Atajo: **Ctrl+C**) |
| **Abrir carpeta de registros** | Abre en el Explorador la carpeta con los archivos de registro. |
| **Abrir archivo de registro** | Abre el registro actual (`opencue.log`) en su editor de texto. |
| **Cerrar** | Cierra la ventana (también **Esc** o la **×**). Si el error detuvo OpenCue, el programa termina después de cerrar la ventana. |

Puede mover la ventana por su barra de título. La ventana de error aparece en el idioma de OpenCue (en inglés si no se puede determinar); el texto copiado con *Copiar detalles* es siempre inglés, para que cualquiera pueda leer un informe.

---

## 2. Dónde están los archivos de registro

Cada inicio de OpenCue escribe un registro:

| Archivo | Contenido |
|---|---|
| `opencue.log` | El inicio **actual**: todo lo que OpenCue informa: mensajes, advertencias, errores con sus códigos y trazas de fallos. |
| `opencue.previous.log` | El registro del inicio **anterior**. Tras un fallo y un reinicio, la causa sigue aquí. |

Están en la carpeta `logs` dentro de la carpeta de datos de OpenCue, normalmente `%LOCALAPPDATA%\OpenCue\logs` (escríbalo en la barra de direcciones del Explorador). La ventana de error la abre por usted.

**Buscar en el registro:** los códigos se escriben como `OC-1234`. Busque `OC-` para encontrarlos todos, u `OC-3` para los pequeños problemas de una sola función (sección 5).

---

## 3. Problemas de inicio (OC-1xxx)

OpenCue comprueba estas cosas **antes** de que arranque cualquier otra. La ventana le dice qué va mal; después OpenCue se cierra.

### OC-1001 – OpenCue ya se está ejecutando

**Significado:** Por cada carpeta de datos solo puede ejecutarse un OpenCue a la vez. Un segundo se disputaría los mismos ajustes, puerto y salida DMX.

**Qué ocurre:** La ventana del OpenCue en marcha pasa al primer plano y aparece esta ventana. (Si el OpenCue en marcha es un **servidor sin ventana**, véase la guía *Opciones de inicio y modo servidor*: no aparece ningún error; su navegador se abre en su lugar en la consola en marcha.)

**Qué hacer:**
- Use la ventana que ha pasado al primer plano. Si no la ve, mire en sus **otras pantallas** y en la **barra de tareas**.
- ¿Acaba de cerrar OpenCue y aun así recibe esto? Puede necesitar unos segundos para cerrarse. Espere un momento y vuelva a iniciarlo.
- ¿No se ve nada en absoluto? Abra el **Administrador de tareas**, busque `OpenCue` (o `python`/`pythonw` si se inició desde el código fuente) y finalice el proceso sobrante.
- Avanzado: para un segundo OpenCue separado (por ejemplo para pruebas) ponga la variable de entorno `OPENCUE_DATA_DIR` en otra carpeta **y** déle otro puerto en su `app_config.json` (véase OC-1002).

### OC-1002 – El puerto de red ya está en uso

**Significado:** OpenCue tiene un pequeño servidor integrado con el que habla su ventana. Necesita un puerto de red libre (por defecto **8000**). Otro programa usa ese puerto. Sin esta comprobación, la ventana de OpenCue mostraría la página del *otro* programa.

**Qué hacer:**
1. Cierre el otro programa. Causas habituales: otro servidor web o herramienta de desarrollo, o un proceso OpenCue sobrante (véase OC-1001, Administrador de tareas).
2. Para averiguar quién usa el puerto, abra un símbolo del sistema y escriba `netstat -ano | findstr :8000` (con su número de puerto). La última columna es el ID del proceso; búsquelo en el Administrador de tareas (pestaña *Detalles*).
3. O deje que OpenCue use otro puerto: cierre OpenCue, abra en un editor de texto el archivo de ajustes indicado en la ventana (normalmente `%LOCALAPPDATA%\OpenCue\config\app_config.json`) y cambie `"server_port": 8000` por un número libre entre **1024 y 65535**, por ejemplo `8010`. Si falta la línea, añádala. Guarde y vuelva a iniciar OpenCue. (Cuando OpenCue está en marcha, puede cambiarlo en **Ajustes → Acceso remoto → Puerto HTTP**.)

### OC-1003 – No se encuentra Microsoft Edge WebView2 Runtime

**Significado:** OpenCue muestra su ventana con el **Microsoft Edge WebView2 Runtime** gratuito. Windows 11 lo tiene; Windows 10 suele tenerlo a través de Edge u Office, pero no siempre.

**Qué hacer:** Haga clic en **Abrir la página de descarga**, instale el runtime *Evergreen* de Microsoft y vuelva a iniciar OpenCue. Si está seguro de que el runtime está instalado, haga clic en **Iniciar de todos modos**. El instalador de OpenCue descarga el runtime automáticamente cuando falta y hay internet.

### OC-1004 – No se puede usar la carpeta de datos

**Significado:** OpenCue guarda ajustes, shows, disposiciones y registros en su **carpeta de datos** (normalmente `%LOCALAPPDATA%\OpenCue`) y no puede crearla ni escribir en ella. La línea bajo la explicación muestra el motivo técnico.

**Qué hacer:** Compruebe que la carpeta existe y que su cuenta de Windows puede escribir en ella; que la unidad no está llena, no es de solo lectura y (si es una unidad de red o USB) está conectada; que ningún antivirus ni el «acceso controlado a carpetas» bloquea OpenCue. Si durante la instalación se eligió una carpeta de datos propia, asegúrese de que esa unidad está disponible. Un nombre de carpeta que en realidad es un **archivo** existente también causa esto.

---

## 4. Errores inesperados (OC-2xxx)

Son errores que OpenCue no esperaba, normalmente un fallo del programa. **Copie los detalles y comuníquelos.** El texto del error y el registro muestran dónde ocurrió.

### OC-2001 – OpenCue no pudo iniciarse

Un error inesperado detuvo OpenCue mientras arrancaba. Reinícielo una vez. Si vuelve a ocurrir: copie los detalles y comuníquelo. Como solución provisional, la causa puede ser un archivo de ajustes dañado: cierre OpenCue, renombre `config\app_config.json` de la carpeta de datos a `app_config.old.json` y vuelva a iniciar (OpenCue arranca entonces con los ajustes predeterminados; sus shows y disposiciones son archivos aparte y se conservan).

### OC-2002 – Falló una tarea en segundo plano

Algo fue mal en una tarea en segundo plano, por ejemplo el análisis de audio, el MIDI o la red. **OpenCue sigue funcionando.** La ventana aparece solo para el *primer* error de este tipo en cada inicio (todos están en el registro). Si algo se comporta de forma extraña, guarde su show y reinicie OpenCue. Comuníquelo con los detalles copiados.

### OC-2003 – El servidor de OpenCue se detuvo

El servidor integrado se detuvo inesperadamente o no pudo iniciarse, por lo que la ventana no puede funcionar. OpenCue se cierra después de la ventana y antes libera la salida DMX y las cámaras. Reinicie OpenCue. Si vuelve a ocurrir, comuníquelo; compruebe también OC-1002 (un problema de puerto también puede acabar aquí).

### OC-2004 – OpenCue se detuvo inesperadamente

Se produjo un error inesperado mientras OpenCue funcionaba y el programa tiene que cerrarse. **Los cambios sin guardar pueden perderse.** Reinicie OpenCue y comunique el error con los detalles copiados. Consejo: guarde su show con regularidad (**Ctrl+S**) durante las sesiones largas.

---

## 5. Problemas de una sola función (OC-3xxx, solo registro)

Estos **no** abren una ventana y OpenCue sigue funcionando. Aparecen al principio de una **línea del registro** (por ejemplo `... [DMX] OC-3103 USB DMX: COM3 ...`) y a menudo como mensaje en la página de ajustes correspondiente. Busque `OC-3` en el registro.

| Código | Significado | Qué hacer |
|---|---|---|
| **OC-3001** | No se pudo leer el archivo de ajustes `app_config.json`. OpenCue usó la copia de seguridad automática (`.bak`) o, si también estaba dañada, los ajustes predeterminados. El archivo dañado se conserva al lado como `.corrupt`. | Compruebe sus ajustes. Para conservar ajustes antiguos, copie valores del archivo `.corrupt` al nuevo `app_config.json` (cierre antes OpenCue). |
| **OC-3101** | Se produjo un error en el hilo de salida DMX. | Compruebe los ajustes DMX (Ajustes → Salida DMX) y la conexión de red o USB. Comuníquelo si se repite. |
| **OC-3102** | La salida Art-Net no pudo configurarse (de nuevo) con los ajustes actuales. | Compruebe el destino y la dirección IP de enlace en los ajustes DMX. El adaptador de red debe existir y estar conectado. |
| **OC-3103** | La interfaz DMX USB se desenchufó o informó de un error de envío. | Vuelva a enchufarla y pulse *Actualizar puertos* en los ajustes DMX. Pruebe otro puerto USB u otro cable; compruebe que ningún otro programa usa el puerto. |
| **OC-3104** | Se produjo un error en el reloj de la salida DMX (que envía los fotogramas a Art-Net, sACN y USB). | OpenCue sigue funcionando y el reloj continúa con el siguiente fotograma. Comuníquelo si se repite (Ayuda → Informar de un problema). |
| **OC-3105** | El **proceso de salida DMX separado** (un segundo proceso OpenCue en el Administrador de tareas) terminó o no pudo iniciarse. | OpenCue lo reinicia automáticamente (la salida vuelve en menos de un segundo). Si muere cinco veces en un minuto o no arranca en absoluto, la salida continúa dentro del programa principal: sin la separación, pero sin interrupción. Compruebe su antivirus (debe permitir que `OpenCue.exe` inicie un segundo proceso); comuníquelo si se repite. |
| **OC-3201** | El análisis de audio no pudo abrir su entrada o fuente (dispositivo ocupado, retirado o bloqueado por los ajustes de privacidad de Windows). | Elija otra fuente en el panel Audio. Cierre los programas que usan el dispositivo en exclusiva. Para un micrófono permita el acceso en *Configuración de Windows → Privacidad → Micrófono*. |
| **OC-3202** | El control por voz no pudo abrir el micrófono seleccionado (OpenCue lo intenta varias veces). | Vuelva a elegir el micrófono en Ajustes → Palabra de activación; cierre otros programas que lo retengan; compruebe el ajuste de privacidad del micrófono de Windows. |
| **OC-3301** | No se pudo abrir un dispositivo MIDI. En Windows la mayoría de los dispositivos pueden ser usados por **un solo programa** a la vez. | Cierre el otro programa (software musical, DAW) o desactive allí el dispositivo. Desenchufe y vuelva a enchufar el dispositivo. |
| **OC-3401** | El nombre `opencue.local` no pudo anunciarse en la red (mDNS). Los dispositivos remotos aún pueden usar la dirección IP. | Use la dirección con el número IP que se muestra en los ajustes de Acceso remoto. Compruebe que la red permite multicast y que el firewall de Windows permite OpenCue en redes privadas. |
| **OC-3402** | OpenCue no pudo escuchar en una dirección de red para dispositivos remotos. | Puede que otro programa use ese puerto, o que la dirección haya desaparecido (Wi-Fi cambiada). Desactive y vuelva a activar el acceso remoto en Ajustes → Acceso remoto, o elija otro puerto. |
| **OC-3501** | La actualización no pudo descargarse o su suma de comprobación no coincidía. | Compruebe la conexión a internet y vuelva a intentarlo más tarde, o descargue el instalador desde la página de versiones. |
| **OC-3502** | El instalador de la actualización descargado no pudo iniciarse. | Descargue el instalador desde la página de versiones y ejecútelo usted mismo. |
| **OC-3601** | La interfaz de usuario informó de un error de JavaScript. La línea del registro muestra el mensaje, el archivo y la línea y en qué dispositivo ocurrió (la consola o un dispositivo remoto). A menudo no se ve nada; a veces un panel se queda vacío. | Recargue la ventana (o la página en el dispositivo remoto). Si vuelve a ocurrir, comuníquelo con *Ayuda → Informar de un problema*: la línea forma parte de los detalles. |
| **OC-3701** | No se pudo escribir una copia de seguridad en segundo plano del show (disco lleno, carpeta no escribible o protegida por un antivirus). El show en sí no se ve afectado. | Libere espacio en disco o elija otra carpeta de datos (*Ajustes → General → Carpeta de datos y gestión de archivos*). *Archivo → Restaurar copia de seguridad* muestra qué copias existen; la carpeta es `backups` dentro de la carpeta de datos. |
| **OC-3801** | OSC no pudo escuchar en su puerto UDP (otro programa lo usa). | Elija otro puerto en **Controles → OSC ...** o cierre el otro programa. |

---

## 6. Comunicar un problema

1. Lo más fácil: **Ayuda → Informar de un problema...** copia los detalles al portapapeles y abre la página de informes. (En la ventana de error: **Copiar detalles**.) **Ayuda → Abrir carpeta de registros** abre la carpeta con `opencue.log`.
2. En la página **Issues** del proyecto OpenCue en GitHub describa lo que hizo antes del error.
3. Pegue el texto copiado. No contiene datos del show, solo la información técnica descrita en la sección 1.

No envíe contraseñas ni claves de acceso; si pegó líneas del registro de una pantalla de ajustes, elimínelas antes.
