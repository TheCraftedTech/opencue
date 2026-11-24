# Proyectores y patch

Un **proyector** es una luz que usted controla: un dimmer, un par LED, una cabeza móvil. Para controlarlo, OpenCue necesita saber **qué tipo de dispositivo es** (sus canales) y **dónde escucha** (su dirección DMX). Comunicarle ambas cosas a OpenCue se llama **patch**. Esta guía le acompaña por la biblioteca de proyectores, el patch, los grupos y el programador.

---

## 1. La idea en un minuto

- Un **tipo de proyector** describe un modelo de dispositivo: cuántos canales DMX usa en qué modo y qué hace cada canal (dimmer, pan, tilt, color, gobo …). OpenCue usa para ello el formato estándar **GDTF**: un pequeño archivo por dispositivo que publica el fabricante.
- Un **proyector** en su show es un dispositivo real de ese tipo, con un **número** (FID), un **nombre**, un **universo** y un **canal inicial** (la dirección DMX que ajusta en el dispositivo).
- El show guarda los proyectores (tipo, modo, dirección, nombre, grupo). Los archivos GDTF en sí están en la **biblioteca de proyectores** de su ordenador.
- Tres tipos de proyector **integrados** están siempre disponibles, incluso sin ningún archivo GDTF: **Generic Dimmer** (1 canal), **Generic RGBW LED Par** (4 canales) y **Generic Moving Head Spot 16ch** (16 canales, con pan/tilt fino). Perfectos para probar.

---

## 2. Conseguir tipos de proyector: la biblioteca

Abra **Biblioteca → Biblioteca de proyectores…**. El cuadro grande tiene estas pestañas:

| Pestaña | Qué muestra |
|---|---|
| **Instalados** | Cada archivo GDTF de este ordenador como tarjeta: imagen de vista previa, nombre, fabricante, tipo, modos, número de canales, revisión y *En uso (N)* cuando el show lo usa. |
| **En este show** | Los tipos que usa el show cargado, con el número («4× en el show») y la revisión. Si el archivo de un tipo no está en la biblioteca, la pestaña muestra *Sustituto integrado* o *Falta el archivo*. Solo para ver. |
| **En línea (GDTF Share)** | Busque en la base de datos oficial de GDTF (véase más abajo). |

En la pestaña *Instalados* puede **buscar** por nombre o fabricante y filtrar por **tipo** (cabeza móvil, barra LED, PAR / wash, dimmer, estroboscopio / blinder, efecto / humo, otro – deducido de los canales reales) y por **fabricante**. Cada pestaña mantiene sus propios filtros.

### Importar un archivo GDTF que ya tiene

Haga clic en **Importar archivo GDTF…** o simplemente **suelte el archivo** en el cuadro. El archivo debe ser un archivo GDTF válido (30 MB como máximo). Los archivos se copian a la carpeta `fixtures` dentro de la carpeta de datos de OpenCue (Ajustes → Almacenamiento muestra dónde está).

### Descargar desde GDTF Share

GDTF Share (gdtf-share.com) es la colección oficial y gratuita de archivos GDTF de fabricantes y usuarios.

1. Abra la pestaña **En línea (GDTF Share)**.
2. **Inicie sesión** con su cuenta de GDTF Share. Para descargar se necesita una cuenta gratuita; en el cuadro hay un enlace *Crear una cuenta gratuita*. Su contraseña se conserva en memoria solo durante esta sesión, salvo que marque *Mantener la sesión iniciada*, lo que la guarda **cifrada en este ordenador**.
3. Busque, ordene (nombre, más recientes, mejor valorados), filtre por **archivos de fabricantes** / valoración. Cada tarjeta muestra si el archivo lo subió **el fabricante** o **un usuario**, cuántos modos tiene (con el número de canales) y su tamaño.
4. Haga clic en **Detalles** para **ver un proyector antes de instalarlo**: el archivo solo se carga temporalmente (no se instala) y se abre en la misma vista de detalle que los tipos instalados, con todos los canales, ruedas y el modelo 3D. **Instalar** y **Volver a la búsqueda** están arriba. O haga clic directamente en **Instalar**.
5. La tarjeta muestra entonces *Instalado*. Si más adelante aparece una revisión más reciente, se ofrece un botón **Actualizar**.

Este es el único lugar donde OpenCue usa internet para proyectores; todo lo demás funciona sin conexión. OpenCue no incluye archivos GDTF de GDTF Share, porque sus condiciones no permiten la redistribución: usted los descarga.

### Detalles de un proyector

Haga clic en una tarjeta para abrir sus **detalles**:

- **Resumen** – datos básicos, óptica por haz (tipo de haz, lámpara, potencia, flujo luminoso, temperatura de color, ángulo de haz y de campo), conectores, emisores.
- **Vista previa 3D** – el proyector como modelo 3D. Arrastre para girar, rueda o dos dedos para hacer zoom, arrastre con el botón derecho para mover, doble clic para restablecer. Botones *Oblicua / Frente / Lado / Arriba*, interruptores para el *haz de luz* y una *cuadrícula*, y **deslizadores Pan / Tilt** para mover una cabeza móvil. Sin archivo 3D en el GDTF, OpenCue dibuja las formas básicas (cilindro, horquilla, cabeza …) con las dimensiones dadas.
- **Canales DMX** – el selector de modo y una tabla de todos los canales con funciones y rangos de valores.
- **Gobos y colores** – cada rueda con sus posiciones: motivos de gobos como imágenes, posiciones de color como muestras.

### Eliminar y actualizar

- **Desinstalar** (pregunta una segunda vez) quita un tipo de la biblioteca, pero se **rechaza mientras el show aún lo use**.
- **Actualizar** instala una revisión más reciente. Si el show usa la antigua, la revisión antigua se queda instalada.

---

## 3. Añadir proyectores al show (patch)

Los proyectores se crean en el panel **Lista de proyectores**.

1. En el panel **Lista de proyectores** haga clic en **Añadir proyectores**.
2. **Tipo de proyector** – elija uno con *Seleccionar tipo...* (fabricante → dispositivo → modo, más una búsqueda) o uno de los genéricos integrados.
3. **Modo** – el modo DMX del dispositivo (decide el número de canales).
4. **Nombre** (opcional) – por ejemplo «Cabeza»; vacío significa el nombre del tipo. Con varios proyectores OpenCue numera los nombres.
5. **Cantidad** – cuántos proyectores idénticos añadir. Se colocan **uno tras otro** en direcciones consecutivas.
6. **Universo** y **Canal inicial** – la dirección del primero. Debe coincidir con la dirección ajustada en el dispositivo (pantalla o interruptores DIP).
7. Haga clic en **Añadir proyectores**.

El cuadro le avisa si el último proyector acabaría más allá del canal **512** de un universo («la dirección final supera 512 … Reduzca la cantidad o la dirección inicial»). Un universo contiene 512 canales; use el universo siguiente para tener más.

Cada proyector recibe un **FID** estable (número de proyector) que usa la línea de comandos (`Fixture 1 Thru 5`).

### Muchos proyectores a la vez: una lista desde CSV o Excel

El cuadro *Añadir proyectores* tiene **Importación avanzada ...** al pie (también en el menú **Biblioteca → Importar lista de proyectores**). Con ella crea todo un montaje a partir de una tabla:

1. **Elegir archivo ...** – un archivo `.csv` o de Excel (`.xlsx`). La **primera fila** contiene los títulos de las columnas. Solo hace falta el **tipo**; *nombre*, *modo*, *universo*, *dirección*, *número* (FID) y *cantidad* son opcionales. **Descargar el patch actual como CSV** le da una plantilla.
2. OpenCue **adivina las columnas** (títulos como *Name*, *Type*, *Device*, *Universe*, *Address*, *Count* ...); puede cambiar cada asignación. Una dirección también puede ser `2.045` o `2/45` (universo 2, dirección 45). Si falta la dirección, continúa tras el dispositivo anterior del mismo universo.
3. La **vista previa** muestra cada fila: en rojo con el motivo cuando algo falla (tipo desconocido o ambiguo, modo desconocido, no cabe en el universo, número ya usado). **Tipo cuando la celda está vacía** y **Universo cuando falta** rellenan huecos.
4. **Importar** crea los proyectores. Si hay problemas, marque antes **Omitir filas con problemas**. Antes no se crea nada.

### La lista de proyectores y la pestaña Proyectores

Dos lugares muestran sus proyectores:

- El panel **Lista de proyectores** es la tabla de patch: una fila por proyector con FID, nombre, tipo, universo, dirección y número de canales, más el botón **Añadir proyectores**.
- La pestaña **Proyectores** del panel **Control de proyectores** muestra los mismos proyectores como una cuadrícula de recuadros (como en una consola de iluminación) para seleccionar rápido.

| Acción | Cómo |
|---|---|
| Seleccionar | Clic / toque en una fila o un recuadro |
| Seleccionar varios | En la cuadrícula de recuadros, arrastre un **lazo** sobre los recuadros (ratón y táctil) |
| Editar un proyector | Clic derecho / pulsación larga → **Editar proyector…** |
| Eliminar | Seleccionar, pulsar `Supr` o usar el menú contextual (pide confirmación) |

### Editar proyector

Un solo cuadro cambia todo: **Nombre**, **Universo**, **Canal inicial**, **Grupo** y un **Índice de orden** libre.

- El índice de orden decide dónde aparece el recuadro. Vacío significa el FID; un número (se admiten decimales, por ejemplo 2,5) lo coloca en consecuencia.
- Un proyector pertenece como máximo a **un grupo**.
- Con **varios proyectores seleccionados** el menú ofrece también *Mover N proyectores al grupo…*.

Cambiar la dirección cambia adónde envía los datos OpenCue; hágalo, por tanto, cuando mueva un dispositivo a otra dirección.

---

## 4. Grupos

Los grupos son puramente organizativos: ordenar y seleccionar varios proyectores con un clic o un comando. Se guardan con el show.

- **Crear:** en la pestaña **Proyectores** del panel Control de proyectores, clic derecho / pulsación larga en el área vacía → *Añadir nuevo grupo…* e introduzca un nombre (los nombres son únicos, sin distinguir mayúsculas).
- **Rellenar:** la lista desplegable *Grupo* en *Editar proyector…*, o *Mover N proyectores al grupo…* para una selección.
- **Seleccionar:** haga clic en el grupo o use la línea de comandos: `Group Front`, `Group 1 Thru 4`.
- **Desde una selección:** `Store Group "Front"` guarda la selección actual como grupo (véase *Referencia de comandos*).

---

## 5. Controlar proyectores: el panel Control de proyectores

Seleccione proyectores y use después el panel **Control de proyectores** (en las consolas se suele llamar «Programador»). Un panel puede mostrarlo todo (una barra lateral con todas las categorías) o una sola categoría (*Propiedades del panel → Vista*).

| Categoría | Controles |
|---|---|
| **Proyectores** | La cuadrícula de recuadros para seleccionar; cambie **Lista / Diseño** (véase más abajo) |
| **Dimmer** | Fader y botones rápidos |
| **Posición** | Cambie **Grueso / Fino**. *Grueso*: faders pan/tilt, **Centro / Inicio / Invertir**, campos numéricos en grados. *Fino*: los canales finos (16 bits) como campos numéricos; deslice un campo numérico hacia arriba o abajo para cambiarlo con precisión. Los proyectores sin canales finos actúan como 8 bits. |
| **Color** | **Fader** (HSV, CMY o RGB) o **Selector de color** (rueda de color) |
| **Haz** | Subpáginas **Shutter/Strobe** (abierto, cerrado, lento, rápido, strobe, pulso …), **Gobo** (con miniaturas de la rueda), **Prisma** |
| **Foco** | Enfoque y zoom |
| **DMX directo** | Cada canal del modo como fader propio (por número de canal, 0–255) |

Cada canal que describe el archivo GDTF recibe un control, de modo que puede alcanzar incluso funciones poco habituales (frost, iris, ruedas de color, velocidades).

**Apuntar a un punto (3D):** si los proyectores están colocados en la **Simulación 3D**, el panel de posición ofrece *Establecer punto en la simulación 3D*: toque un objetivo en la vista 3D y las cabezas móviles seleccionadas apuntan a él. En el panel de foco, *Enfoque automático (3D)* y *Zoom automático (3D) …* ajustan enfoque y zoom según la distancia a ese punto.

### Qué le dice el color de los controles

Los controles muestran siempre lo que se está emitiendo en ese momento (los mismos valores que el monitor DMX), también mientras un cue o un efecto está en marcha. Una fina línea de color junto a un proyector o a una pestaña de categoría muestra lo que **ha cambiado respecto al cue activo**: manejado a mano o por un *Clear* que lo dejó todo oscuro. *Store Cue* guarda siempre el cambio respecto al cue que sonaría antes (también al insertar con `2.5`). Tras guardar, el nuevo cue es el activo y las líneas desaparecen. Con varias listas de cues cuenta el cue activo de la lista usada más recientemente.

---

### Proyectores: lista o diseño

Arriba en la pestaña **Proyectores** cambia entre dos vistas (como *Color* entre Fader / Selector / Rueda):

- **Lista:** los recuadros ordenados por grupos y números.
- **Diseño:** cada proyector es un **recuadro cuadrado** en una cuadrícula. Disponga los proyectores como cuelgan en el escenario y llegue a ellos más rápido. Los recuadros muestran lo mismo que la lista (número, brillo, vista previa de color y haz).

En el diseño:

- **Seleccionar** como en la lista: clic o un **deslizamiento** (lazo) por el área vacía.
- **Área ilimitada:** continúa en **todas las direcciones** (también a la izquierda y arriba; las posiciones pueden ser negativas). Mueva la vista con la rueda del ratón / barras de desplazamiento / deslizando, **arrastre con el botón central**, o vaya al borde mientras arrastra un recuadro. **Ctrl + rueda** hace zoom.
- **Mostrar todo:** el botón arriba a la derecha hace zoom y centra de modo que **todos los proyectores** queden en el centro.
- **Vistas (áreas):** *Guardar vista…* (clic derecho) guarda el centro y el zoom actuales con un nombre, por ejemplo «Escenario izquierda». Aparece un botón arriba; un clic salta allí, clic derecho en el botón: sobrescribir, renombrar, eliminar. Con muchos proyectores no tiene que mantenerlo todo a la vista a la vez.
- **Clic derecho** (táctil: pulsación larga) en el área libre o en un recuadro abre el menú: *Modo de construcción*, *Mostrar todo*, *Guardar vista…*, *Cuadrícula* (recuadro entero, medio o cuarto), *Los recuadros pueden superponerse*, *Restablecer zoom*, *Reorganizar todos los proyectores…*.
- **Modo de construcción:** arrastrar mueve un recuadro; con varios seleccionados se mueven juntos. Los recuadros se ajustan a la cuadrícula; sin *Superposición* nunca se tapan, con *Superposición* puede encajarlos unos en otros (el último movido queda encima) y escalonarlos de cerca con la cuadrícula fina (1/4). El área vacía sigue seleccionando por deslizamiento. **Hecho** o **Esc** termina el modo de construcción.
- **Guardado en el show:** las posiciones, la resolución de la cuadrícula, la *Superposición* y las vistas guardadas. **En su dispositivo** (no en el show): el zoom, el último centro mostrado y la última subvista usada.

**Vistas recordadas:** dondequiera que un panel cambie entre vistas, su dispositivo recuerda la última y la restaura la próxima vez: en Control de proyectores (Lista / Diseño, Fader / Selector / Rueda, Strobe / Gobo / Prisma, Grueso / Fino), en *Variables / Efectos* (variables o efectos, filtro de tipo, orden), en el *Estudio de efectos* (vista previa activada / desactivada), en la *Simulación 3D* (Vista / Construcción / Proyectores) y en el selector de efectos (categoría y etiquetas como *Básico*).

## 6. Variables y efectos (presets)

El panel **Variables / Efectos** contiene valores reutilizables: un color «Blanco cálido», una posición «Frente», un haz «Ancho». Una variable es una **referencia viva**: aplíquela a proyectores y la siguen; cambie la variable más tarde y todos los proyectores que la usan cambian con ella, incluidos los cues que la usan. Los efectos son pequeños programas que cambian valores con el tiempo; véase la guía *Estudio de efectos*.

---

## 7. Proyectores y el archivo de show

- Un archivo de show guarda los proyectores **con** su tipo, modo, dirección y grupo, además de los cues, efectos, variables y presets.
- Los archivos GDTF **no** están dentro del show, pero cuando **exporta un show** (gestor de archivos → exportar), los archivos GDTF y los scripts de efectos que usa el show se empaquetan en el ZIP, de modo que puede abrir el show en otro ordenador sin instalar nada. Al importar, un archivo local del mismo nombre nunca se reemplaza.
- **Imprimir / PDF** (menú Archivo): documentación del show para técnicos – **lista de patch**, **mapa de canales DMX** (qué proyector ocupa qué canales de cada universo, solapamientos en rojo), **grupos**, **plano (vista superior)** de los proyectores (del escenario 3D, si no de la vista de diseño) y **listas de cues**. El cuadro muestra una **vista previa** del PDF junto a las opciones (sigue cada cambio de las opciones y del tamaño de papel; en pantallas pequeñas se omite la vista previa). Los nombres largos se **ajustan en varias líneas** en las tablas y en el plano (un nombre larguísimo sin espacios se divide). En el plano cada proyector lleva su número, y una lista bajo el plano indica qué número es qué proyector; los nombres de los objetos del escenario van dentro de su forma. *Guardar como PDF* descarga el archivo, *Abrir para imprimir* lo muestra en el visor de PDF (imprima allí con Ctrl+P).
- **Archivo de show `.ocshow`:** *Archivo → Exportar show* escribe un archivo `.ocshow` (un ZIP con el show y sus archivos). Un **doble clic** lo abre en OpenCue (el instalador lo configura; para la versión sin instalar use *Ajustes → General → Abrir archivos .ocshow con OpenCue*). Si OpenCue ya está en marcha, toma el archivo y pregunta antes por los cambios sin guardar. **Archivo → Abrir reciente** lista los últimos shows.
- **Escenario 3D como JSON:** en el panel 3D (modo *Construcción* o *Proyectores*) cambie la barra lateral de **Herramientas** a **JSON** (interruptor bajo el botón Guardar; permanece arriba en la barra lateral al desplazarse). Las herramientas (añadir cuerpos, lista, propiedades) se sustituyen por el texto del escenario (sala, objetos, posiciones de proyectores; metros, grados, Z hacia arriba; proyectores por su número); el nombre del escenario, deshacer y **Guardar** siguen igual, **Herramientas** devuelve la vista normal. **El ancho de la barra lateral se puede cambiar:** arrastre su borde izquierdo (doble clic = ancho estándar); el ancho se recuerda como proporción del panel (como máximo tres cuartos), de modo que se mantiene proporcional a pantalla completa. Los cambios se comprueban y se **aplican en directo** (un error de sintaxis nombra la línea y no cambia nada); lo que mueva en la vista 3D aparece en el texto. *Guardar* guarda el escenario, *Cerrar JSON* devuelve la barra lateral. El mismo texto está disponible como cuadro en *Biblioteca → Editar escenario 3D como JSON* (con *Comprobar* y *Aplicar*).
- **Importación MVR (escenario y proyectores):** *Biblioteca → Importar escena MVR…* lee un archivo **.mvr** de un programa de diseño de escenario o iluminación (Vectorworks, Capture, Depence …). Elige el archivo (o arrástralo a la ventana): OpenCue muestra lo que contiene - piezas de escenario, proyectores y sus tipos - y tú decides: **escenario 3D** *reemplazar* (por defecto; un archivo de escenario guardado antes queda intacto en el disco), *añadir* o *no tocar*, y si se **parchean los proyectores**. Los proyectores reciben tipo, modo, dirección DMX y número del archivo y se colocan en el escenario 3D con su posición y giro (un número ya usado o una dirección que falta se sustituye por uno libre - los avisos te lo dicen). Los archivos GDTF van a la biblioteca de proyectores (no se sobrescribe nada). Las piezas de escenario (suelo, truss, decorado, pantallas …) se convierten en **modelos 3D** (STL binario, en *Biblioteca → Modelos 3D…*) y en objetos de escenario que puedes mover, girar y escalar como los demás; una pieza que aparece muchas veces (un símbolo del archivo) comparte un solo modelo. Una escena con más de 200 piezas se agrupa por capa para que quepa en un escenario. El nuevo escenario no se guarda hasta que guardes el show. Los colores de los materiales se conservan (por superficie) y las piezas reflejadas siguen reflejadas. Una barra de progreso muestra la importación - los archivos de proyectores LED grandes tardan unos segundos cada uno, una vez por tipo, y luego se recuerdan. La ventana también se abre desde el pequeño botón *Importar escena MVR…* del panel 3D (modos *Construcción* y *Proyectores*). No se importan: puntos de enfoque y texturas de imagen.
- Si un show usa un tipo de proyector cuyo archivo falta, OpenCue usa un sustituto integrado para que el show funcione igualmente; la pestaña *En este show* lo muestra como *Sustituto integrado* o *Falta el archivo*.

---

## 8. Consejos rápidos

- **Empiece con un genérico:** añada unos cuantos proyectores *Generic Dimmer* para aprender el programador, los cues y la línea de comandos antes de buscar archivos GDTF reales.
- **Haga coincidir las direcciones:** el canal inicial en OpenCue debe ser igual a la dirección del dispositivo. Las cabezas móviles suelen necesitar un bloque de canales (por ejemplo 16 canales), de modo que el siguiente proyector empieza 16 canales después; OpenCue lo calcula por usted cuando añade una cantidad.
- **Varios modos:** muchos dispositivos ofrecen varios modos (por ejemplo 8 bits y 16 bits). Elija el modo en el que el dispositivo está realmente ajustado.
- **¿Falta un dispositivo?** Busque en GDTF Share por fabricante; si el modelo no está, parta del más cercano o use *Generic* y cree sus propios cues.
