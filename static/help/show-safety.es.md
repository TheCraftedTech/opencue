# Copias de seguridad, bloqueos y cierre seguro

Programaste el show antes del evento y ahora **no guardas a propósito** mientras funciona – nada debe sobrescribirse por accidente. OpenCue te protege de cuatro maneras: **copias de seguridad en segundo plano**, **restauración** tras un fallo, un **bloqueo** para shows terminados y un **diálogo de cierre cuidadoso**. Esta guía explica las cuatro, y cómo informar de un problema.

---

## 1. Copias de seguridad en segundo plano

OpenCue escribe regularmente el **estado actual de tu show** – incluidos los cambios que *no* has guardado – en una carpeta oculta. No la ves hasta que la necesitas. Una copia **nunca sustituye tu archivo de show**.

- **Cuándo:** cada **15 minutos** por defecto, pero **solo si** el show tiene cambios sin guardar y algo cambió desde la última copia. Nada cambiado = nada escrito.
- **También:** al salir sin guardar, cuando falló el guardado (por ejemplo porque el show está bloqueado), y justo antes de abrir o iniciar otro show mientras este aún tiene cambios sin guardar.
- **Cuántas:** se conservan las **10** más recientes por show, como máximo 100 en total; las más antiguas se borran automáticamente.
- **Dónde:** la carpeta `backups` dentro de la carpeta de datos (`%LOCALAPPDATA%\OpenCue\backups`). Una copia es un archivo de show normal.

### Ajustes

**Ajustes → General → Copias de seguridad del show**:

| Ajuste | Significado |
|---|---|
| **Copiar el show en segundo plano** | Activa o desactiva toda la función (por defecto: activada). |
| **Cada (minutos)** | El intervalo, de 1 a 240 (por defecto 15). |
| **Conservar por show** | Cuántas copias de un show se conservan, de 1 a 50 (por defecto 10). |
| **Restaurar copia...** / **Abrir carpeta** | Abre el diálogo de restauración (sección 2) o la carpeta en el Explorador. |

Los ajustes valen para todo el programa y se pueden cambiar desde cualquier dispositivo, también desde un dispositivo remoto.

---

## 2. Restaurar una copia

**Archivo → Restaurar copia...** (o el botón en los ajustes) lista todas las copias, las más recientes primero: nombre del show, hora, motivo (automática, al salir, manual, antes de una restauración, guardado fallido) y tamaño.

- **Restaurar** carga la copia como un **show sin guardar**. El archivo de show en el disco queda exactamente como está, incluso si está bloqueado. Después **Guardar** (o **Guardar archivo de show como...**) cuando estés conforme.
- El estado que tenías antes se copia primero – una restauración tampoco puede hacer perder nada.
- **Copiar ahora** hace una copia de inmediato; **Borrar** elimina una. Todo esto funciona también desde un dispositivo remoto (*Abrir carpeta* muestra allí el Explorador de OpenCue).
- Shows, disposiciones, escenarios y ajustes se escriben **de forma segura**: primero en un archivo vecino, luego se intercambian – un fallo o un corte de corriente a mitad del guardado no puede destruir el archivo existente.

### Tras un fallo

Si OpenCue no se cerró correctamente (fallo, corte de corriente, tarea finalizada), en el siguiente inicio **ofrece la última copia de esa sesión**: *«OpenCue no se cerró correctamente … ¿Restaurarla?»* – **Restaurar**, **Mostrar todas las copias** o **Ahora no** (las copias siguen disponibles en *Archivo → Restaurar copia...*).

---

## 3. Bloquear un show

Un show terminado se puede **bloquear** para que nadie lo cambie por accidente. En el **gestor de archivos** (*Archivo → Gestor de archivos...*, tipo *Shows*) haz clic en el **símbolo del candado** en la fila del show; haz clic de nuevo para desbloquear.

Un show bloqueado:

- aparece marcado **Bloqueado** en la lista y muestra un pequeño **candado** junto al nombre del show en la barra superior mientras está cargado,
- **no se puede sobrescribir, renombrar ni borrar** – al guardar se muestra *«No guardado: … está bloqueado»*,
- sí se puede **cargar**, **duplicar** (la copia no queda bloqueada) y guardar con **otro nombre** con *Guardar archivo de show como...*.

El bloqueo protege contra despistes, no contra copiar: el archivo en sí aún puede cambiarse con cualquier otro programa.

---

## 4. Salir con seguridad

**Archivo → Salir** (o el botón de cierre) pregunta: **Guardar y salir**, **Salir sin guardar** o **Cancelar**.

Si el show **no se puede guardar** pero tiene cambios – está bloqueado, el archivo está protegido contra escritura, la carpeta no es escribible o el último guardado falló – el diálogo cambia:

- Un **cuadro naranja** arriba dice *«Este show no se puede guardar»* y nombra los motivos. También dice si se conserva una copia de seguridad de tus cambios.
- **Guardar una copia y salir...** sustituye a *Guardar y salir*: eliges un nombre nuevo, el show se guarda allí y luego OpenCue se cierra.
- **Salir sin guardar** requiere **dos clics**: el primero pone el botón en rojo (*«Haz clic otra vez: salir y perder los cambios»*), solo el segundo sale.

Incluso entonces se escribe al salir una copia de tus cambios (si las copias están activadas), de modo que *Archivo → Restaurar copia...* aún puede recuperarlos.

---

## 5. Informar de un problema

- **Ayuda → Abrir carpeta de registros** abre la carpeta con `opencue.log`.
- **Ayuda → Informar de un problema...** copia el **diagnóstico** (versión, sistema, las últimas líneas del registro – sin tokens de acceso ni contraseñas) al portapapeles y abre la página de informes del proyecto en tu navegador. Describe lo que hiciste, pega el diagnóstico.
- Los errores de la interfaz de usuario se escriben en el registro como **OC-3601**; una copia que no se pudo escribir como **OC-3701** (ver la guía *Códigos de error*).
