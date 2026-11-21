# Atajos de teclado y gestos

Todos los atajos de teclado y gestos táctiles de OpenCue en un solo lugar. Dentro del programa la misma lista está disponible en **Ayuda → Atajos de teclado** y **Controles → Atajos de teclado ...**; y allí también puede **cambiar** los atajos propios del programa (sección 11b).

En un teclado de Mac (o en un navegador en un Mac) `Cmd` funciona como `Ctrl`.

---

## 1. Resumen

La mayoría de los atajos son **globales**: funcionan estén donde estén el foco, con una regla: **mientras escribe en un campo de texto, solo unos pocos atajos siguen activos**: `Ctrl+S`, `Ctrl+Shift+S`, `Ctrl+F`, `F1`, `F5`, `Ctrl+F5`, `F11` y `Ctrl+L`. Todo lo demás (`Ctrl+N`, `Ctrl+O`, `Ctrl+Q`, `Ctrl+E`, teclas de flecha, `Ctrl+1–9`, escala, portapapeles y deshacer) permanece callado para que escribir nunca se vea perturbado.

---

## 2. Archivo de show

| Atajo | Acción |
|---|---|
| `Ctrl+N` | Nuevo archivo de show (pregunta antes si hay cambios sin guardar) |
| `Ctrl+O` | Abrir un archivo de show (abre el gestor de archivos en *Shows*) |
| `Ctrl+M` | Gestor de archivos (todos los archivos: shows, disposiciones, escenarios, modelos, medios, efectos ...) |
| `Ctrl+L` | **Bloquear pantalla** (menú *Controles → Bloquear pantalla*; requiere *Ajustes → Seguridad → Usar el modo de bloqueo*; en un dispositivo remoto: cerrar sesión; en modo operador: pide la contraseña para salir de él) |
| `Ctrl+S` | Guardar el archivo de show **y** la disposición de esta consola (un show sin nombre abre *Guardar como*) |
| `Ctrl+Shift+S` | Guardar el archivo de show con un nombre nuevo |
| `Ctrl+Q` | Salir de OpenCue (pregunta antes si guardar) |

`Ctrl+S` también funciona mientras escribe en un campo de nombre, por ejemplo en el cuadro *Guardar como*.

---

## 3. Vista e interfaz

| Atajo | Acción |
|---|---|
| `?` | **Mostrar / ocultar este resumen de todos los atajos de teclado** (no mientras escribe en un campo ni con otro cuadro de diálogo abierto) |
| `F1` | Abrir las **Guías** (todos los manuales dentro del programa, también sin conexión). Dentro de ellas `Ctrl+F` busca, `Intro` / `Mayús+Intro` saltan a la coincidencia siguiente / anterior, `Esc` borra la búsqueda |
| `F5` | **Recargar la disposición**: la disposición actual se carga de nuevo como en un cambio de disposición y **todos los paneles se reconstruyen** (ayuda si algo – por ejemplo la simulación 3D – no apareció correctamente tras el inicio). Con cambios de disposición sin guardar no se lee nada del archivo: los paneles solo se reconstruyen y sus cambios permanecen. También en *Ver → Recargar el diseño* |
| `Ctrl+F5` | **Recargar toda la interfaz** (como recargar una página web; el dispositivo recupera después su disposición). También en *Ver → Recargar la interfaz* |
| `F11` | Pantalla completa (ventana de la consola, o el navegador de este dispositivo) |
| `Ctrl +` / `Ctrl =` | Ampliar la interfaz (escala de la interfaz, pasos del 5 %) |
| `Ctrl -` | Reducir la interfaz |
| `Ctrl+0` | Restablecer la escala al 100 % |
| `Ctrl+Shift+L` | Cambiar de idioma (uno tras otro: inglés, alemán, francés, neerlandés, italiano, español) |
| `Ctrl+F` | Abrir / cerrar la **consola de comandos**: línea de comandos con teclado numérico y teclas de comando en una ventana; también sin estos paneles en la disposición; el cursor está de inmediato en el campo de entrada |
| `Esc` | Cerrar / cancelar el cuadro de diálogo, la ventana de panel o el menú superior; una pulsación cierra **un** cuadro (los Ajustes preguntan antes si hay cambios) |

La escala de la interfaz (50–200 %) se guarda **por dispositivo**: una tableta puede ser grande mientras la consola se mantiene pequeña.

---

## 4. Disposiciones

| Atajo | Acción |
|---|---|
| `Ctrl+1` … `Ctrl+9` | Cargar la disposición 1 a 9 (primero las favoritas, luego A–Z) |
| `←` / `→` | Disposición anterior / siguiente (no en campos de texto, cuadros de diálogo, menús ni modo de edición) |
| Deslizamiento horizontal | Disposición anterior / siguiente en dispositivos táctiles (*Ajustes → General → Cambiar de diseño deslizando*, por dispositivo) |

Cargar una disposición descarta los cambios sin guardar de la actual. El orden es el mismo que en **Ver → Diseños**.

---

## 5. Modo de edición de paneles

El modo de edición (**Editar → Editar paneles**) permite mover, redimensionar y configurar paneles.

| Atajo | Acción |
|---|---|
| `Ctrl+E` | Activar / desactivar el modo de edición |
| Clic en un panel | Lo marca (marco de acento fino) |
| `Mayús`/`Ctrl` + clic | Añadir un panel a la marca / quitarlo de ella |
| Clic en el espacio de trabajo vacío | Borra la marca |
| `Ctrl+C` / `Ctrl+X` / `Ctrl+V` | Copiar / cortar / pegar los paneles marcados (el portapapeles sobrevive a un cambio de disposición) |
| `Ctrl+Z` | Deshacer el último cambio de panel |
| `Ctrl+Y` o `Ctrl+Shift+Z` | Rehacer |
| Clic derecho → *Duplicar* | Copia los paneles marcados (o pulsados) con un pequeño desplazamiento |

En el **modo de edición**, `Ctrl+Z` / `Ctrl+Y` se aplican a la disposición de los paneles. **Fuera** de él deshacen cambios en el **contenido del show** (véase *Deshacer y rehacer* más abajo).

Salir del modo de edición con cambios sin guardar pregunta: **Guardar**, **Descartar cambios** (recarga la disposición guardada) o **Seguir editando**.

---

## 6. Lista de proyectores y programador

| Acción | Cómo |
|---|---|
| Seleccionar un proyector | Clic / toque en su recuadro |
| Seleccionar varios | **Lazo**: arrastrar un marco sobre los recuadros (ratón y táctil); el lazo permanece dentro de su panel |
| Eliminar los proyectores seleccionados | `Supr` o `Retroceso` (pide confirmación) |
| Cambiar con precisión un valor de Pan/Tilt | **Deslizar** arriba/abajo sobre el campo numérico (grueso: 2 px por paso, fino: 4 px por paso fino); toque para escribir |
| Abrir el menú contextual | Clic derecho (ratón) o pulsación larga (táctil) sobre un proyector o sobre un espacio vacío |

---

## 7. Línea de comandos

| Tecla | Efecto |
|---|---|
| `Intro` | Ejecutar el comando |
| `↑` / `↓` | Comando más antiguo / más reciente del historial (abajo vuelve a su borrador) |
| `Tab` | Tomar la primera sugerencia; cada `Tab` siguiente pasa a la siguiente |
| `Shift+Tab` | Recorrer las sugerencias hacia atrás |
| `Esc` | Cerrar la lista de sugerencias (en la consola de comandos: cerrar la consola) |

Detalles sobre los comandos: *Referencia de comandos*.

---

## 8. Estudio de efectos

| Atajo | Acción |
|---|---|
| `Ctrl+S` | Guardar el efecto (**no** el show) cuando el cursor está en el script |
| `Tab` | Inserta dos espacios |
| `Intro` | Nueva línea con la sangría de la anterior (dos espacios más tras `{`) |

---

## 9. Simulación 3D – modo de construcción

Estos atajos solo actúan en la simulación 3D mientras construye (modos *Construcción* / *Proyectores*), no en el modo *Vista*.

| Atajo | Acción |
|---|---|
| `Ctrl+C` / `Ctrl+X` / `Ctrl+V` | Copiar / cortar / pegar objetos |
| `Ctrl+D` | Duplicar el objeto seleccionado (pulsar de nuevo para repetir el desplazamiento) |
| `Supr` / `Retroceso` | Eliminar el objeto seleccionado (pide confirmación); en modo proyector: quitar el proyector del escenario |
| `Esc` | Borrar la selección |
| `Mayús` + clic | Añadir / quitar un objeto a la selección |
| Teclas de flecha | Mover la selección (con `Mayús` cinco veces más lejos); mientras algo está seleccionado las flechas no cambian de disposición |
| `Ctrl+Z` | Deshacer |
| `Ctrl+Y` o `Ctrl+Shift+Z` | Rehacer |

Los proyectores existen una sola vez en un escenario, por lo que en el modo proyector copiar, cortar y duplicar están desactivados.

Mientras apunta (*Establecer punto en la simulación 3D* en el control de proyectores), `Esc` termina el apuntado.

---

## 10. Gestos táctiles

| Gesto | Equivale a |
|---|---|
| Pulsación larga | Clic derecho (menú contextual) |
| Pulsación larga sobre un elemento con información sobre herramientas | Muestra la información |
| Doble toque | Doble clic |
| Deslizamiento horizontal (si está activado) | Disposición anterior / siguiente |
| Deslizamiento sobre un campo numérico Pan/Tilt | Cambiar el valor (grueso / fino) |

Los tiradores de los paneles y los botones de la barra de herramientas tienen una zona táctil de al menos 44 × 44 px. El deslizamiento de disposición se reconoce por la dirección del primer movimiento (como máximo 25° respecto a la horizontal, al menos el 40 % del ancho) y nunca empieza sobre elementos con su propia función de arrastre (faders, recuadros de lazo, campos numéricos deslizables, campos de entrada, la rueda de color, tiradores de columnas y paneles). El desplazamiento vertical sigue siendo desplazamiento.

---

## 11. Atajos de teclado personalizados

Una tecla o combinación de teclas propia puede activar un **comando de la línea de comandos**: por ejemplo `Ctrl+H` para `Blackout` o la barra espaciadora para `Cuelist Main Go`. Abra la lista con **Controles → Atajos de teclado personalizados ...** o con el botón al pie del cuadro *Atajos de teclado*.

**Una tecla para el siguiente cue:** bajo *Inicio rápido*, arriba en el cuadro, haga clic en **Siguiente cue (Go)** (o *Cue anterior*, *Pausa*, *Blackout*): aparece una fila nueva con el comando `Go`; haga clic en su campo de tecla y pulse la tecla, por ejemplo la barra espaciadora o una tecla de un segundo teclado / teclado numérico (elija *Solo este teclado* en el cuadro *Definir tecla*). `Go` inicia el siguiente cue de la lista de cues activa; `Cuelist Main Go` siempre esa lista.

Cada fila tiene, de izquierda a derecha:

| Campo | Significado |
|---|---|
| **Activo** | Activa o desactiva la fila sin eliminarla. |
| **Tecla** | Muestra la tecla o combinación. Al hacer clic en ella o en el **botón de teclado** de al lado se abre el cuadro **Definir tecla**: tiene **10 segundos** para pulsar la tecla o combinación (por ejemplo `Ctrl` y `H` juntas); se graba todo desde la primera pulsación hasta que se sueltan todas las teclas. `Esc` cancela, el botón junto al campo vuelve a grabar. Debajo elige a qué se aplica: **Todos los teclados** o **Solo este teclado**. Una fila solo recibe su tecla mediante este cuadro. |
| **Comando** | El comando tal como lo escribiría en la línea de comandos. |
| **Ejecutar** | Activado: el comando se ejecuta al instante. Desactivado: solo se **escribe** en la línea de comandos (usted lo confirma). |
| **En el historial** | Activado: el comando aparece en el historial de la línea de comandos. |
| Papelera | Elimina la fila (tras una confirmación). |

**Nueva combinación de teclas** al pie añade tantas filas vacías como quiera (sin grabación). Los cambios se aplican de inmediato y en cada dispositivo con teclado conectado (también un iPad).

**Copia de seguridad y compartir:** Al pie del cuadro, **Exportar ...** guarda la asignación como archivo (`opencue-keyboard-mapping.json`), **Importar ...** lee un archivo así. Las filas se **añaden**; las teclas que el programa u otra fila ya usan se omiten (el mensaje indica el número).

**Conviene saber**

- Las combinaciones que el programa o el navegador ya usan (`Ctrl+S`, `Ctrl+1...9`, `Izquierda`/`Derecha`, `F5` ...) se rechazan durante la grabación; cada combinación solo se puede usar una vez.
- Mientras **escribe en un campo de entrada** solo se aplican combinaciones con `Ctrl`. Con un cuadro de diálogo abierto las teclas simples no hacen nada, y con el cuadro *Atajos de teclado personalizados* abierto no se activa nada.
- El comando se ejecuta cuando la tecla se **pulsa** (no al soltarla). Una tecla mantenida lo activa **solo una vez**.
- Una combinación puede tener **varias teclas principales**, p. ej. `Ctrl+H+J`: se aplica en cuanto están todas pulsadas (el orden no importa). Si también existe `Ctrl+H`, esa combinación más corta espera un momento para ver si se añade `J`.
- Si una combinación ya la usa el programa o el navegador (también como parte de una más larga, p. ej. `Ctrl+S+J`), OpenCue no la acepta y muestra un mensaje arriba en el cuadro.
- Las teclas se guardan con independencia de la distribución del teclado (la tecla `Z` sigue siendo la tecla en esa posición). El teclado numérico se llama `Num1` ... `Num9`.

**Tecla de un teclado concreto (p. ej. macro pad, solo Windows)**

En el cuadro **Definir tecla** (botón de teclado de una fila) pulsa la tecla en el teclado que desee. En la consola con Windows OpenCue detecta **de cuál** teclado procede (el nombre aparece bajo el campo) y usted elige **Todos los teclados** o **Solo este teclado**. En una tableta o sin Windows graba el navegador y siempre se aplica a «Todos los teclados». Una tecla se aplica o a todos los teclados o a concretos, no a ambos a la vez. Una fila ajustada a «solo este teclado» solo se activa cuando la tecla se pulsa exactamente en ese teclado, incluso cuando OpenCue no está en primer plano. La fila muestra el teclado bajo la tecla.

- Esto funciona **en la propia consola** solo con Windows, no desde una tableta.
- OpenCue **solo escucha mientras** haya al menos una fila activada para un teclado concreto (o mientras graba). Solo evalúa los teclados de la lista; todo lo demás se descarta de inmediato y nunca se guarda.
- Windows solo informa de la tecla, **no la bloquea**: la tecla llega también al programa activo (por ejemplo como carácter en un campo de texto). Para un macro pad elija teclas que por lo demás no hagan nada, como `F13` a `F24` o el teclado numérico.
- Algunos teclados se presentan como varios dispositivos (por ejemplo teclas y teclas multimedia por separado). OpenCue lo detecta por sí solo durante la grabación.
- Dos teclados distintos pueden asignar la misma tecla de forma diferente. Un aviso duplicado de la misma pulsación (en menos de 80 ms) se activa una sola vez.

## 11b. Cambiar los atajos propios del programa

Los atajos que el programa ya tiene (`Ctrl+S`, `F11`, `Ctrl+E` ...) se pueden mover a otras teclas o desactivar. Abra **Controles → Atajos de teclado ...** y haga clic al pie en **Editar accesos directos**:

1. Cada fila modificable muestra un marco discontinuo alrededor de su tecla. **Haga clic en la tecla**, pulse la nueva combinación y **suéltela**: se fija de inmediato (la tecla muestra *Pulsa teclas ...* mientras la mantiene). `Esc` cancela.
2. La **cruz** junto a una fila **desactiva** ese atajo, la **flecha** restablece su tecla estándar. **Restaurar todas las teclas estándar** lo restablece todo. **Hecho** sale del modo de edición.
3. Las teclas cambiadas se muestran aquí en el color de acento, en los menús (por ejemplo *Archivo → Guardar show*) y en el cuadro *Atajos de teclado personalizados*, que rechaza las teclas ocupadas.

OpenCue rechaza una combinación que ya se usa (por otro atajo, por un comando de tecla personalizado, o por el navegador / Windows, por ejemplo `Ctrl+W`). Un atajo del programa tiene **una tecla principal más Ctrl, Alt o Mayús**; una letra o número solo se rechaza porque bloquearía la escritura; las teclas de función (`F1` ... `F24`) funcionan solas. El cambio se aplica a **todos los dispositivos** de la consola.

No se pueden cambiar (dependen de la situación): `Esc`, `Ctrl+C / X / V` para paneles, `Ctrl+1 ... 9` para disposiciones, las teclas de flecha y las teclas de edición 3D.

---

## Deshacer y rehacer (contenido del show)

Fuera del modo de edición de paneles, `Ctrl+Z` y `Ctrl+Y` (o `Ctrl+Shift+Z`) – y *Editar → Deshacer / Rehacer* – deshacen y rehacen todo lo que está **guardado en el archivo del show**, y la operación previa:

- **cues y listas de cues:** guardar, actualizar, cambiar horas / disparadores / nombres (también varios a la vez), copiar, eliminar, crear, renombrar, reordenar y eliminar listas;
- **variables** y sus grupos, **grupos de proyectores**, el **patch** (añadir, eliminar, reasignar direcciones, renombrar, organizar proyectores), **efectos** (definiciones y grupos), la **programación** y las **pistas de comandos de la línea de tiempo**;
- la **selección** de proyectores;
- **valores del programador** (color, posición, brillo, haz …): un arrastre de fader o un comando como `At 80` es **un** paso; también vuelve atrás el estado DMX de los proyectores afectados;
- **efectos en marcha:** aplicar o deseleccionar un efecto en proyectores;
- el **fader del ejecutor** de una lista de cues (un arrastre = un paso).

Un breve mensaje nombra lo que se deshizo. Los cambios rápidos del mismo tipo (por ejemplo un deslizamiento sobre una hora o un arrastre de fader) cuentan como **un** paso; el historial conserva los últimos 100 pasos. Iniciar un show nuevo (*Nuevo*, *Abrir*) lo borra.

**Go y Back (interruptor):** si **Go / Back / Jump** (y un `Go` escrito como comando) también se deshacen; `Ctrl+Z` vuelve entonces al cue anterior. Por defecto: **desactivado**, para que nunca retire un cue por accidente durante una actuación. El interruptor es un icono (flecha de deshacer con un pequeño triángulo de reproducción) en la barra de herramientas **y** en *Ajustes → Más opciones → Interruptores rápidos*; allí funciona incluso cuando el icono está oculto en la barra de herramientas.

**No incluido:** los ajustes, el Go mediante MIDI / OSC / timecode y los cambios hechos mediante la interfaz REST. En un cuadro de diálogo abierto y en campos de texto los atajos no hacen nada. Puede reasignar las teclas en *Atajos de teclado → Editar accesos directos*.

## 12. Chuleta

```
Ctrl+N  Nuevo show         Ctrl+O  Abrir show          Ctrl+S  Guardar       Ctrl+Shift+S  Guardar como
Ctrl+E  Editar paneles     Ctrl+Z / Ctrl+Y  Deshacer / Rehacer (paneles en modo edición, si no contenido del show)
Ctrl+C / X / V  Copiar / cortar / pegar paneles (modo edición)
Ctrl+1…9  Cargar disposición   ← / →  Disposición anterior / siguiente
Ctrl +  Ctrl -  Ctrl+0     Escala de la interfaz mayor / menor / 100 %
Ctrl+Shift+L  Idioma       F11  Pantalla completa  Ctrl+Q  Salir       Esc  Cerrar cuadro
Ctrl+F  Consola de comandos (línea de comandos + teclado numérico + teclas)
```
