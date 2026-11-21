# Estudio de efectos – Guía

Un **efecto** es un pequeño programa que cambia la luz con el tiempo: un dimmer que pulsa, un color que recorre el arcoíris, una cabeza móvil que describe un círculo. Los efectos se escriben en el **Estudio de efectos** (panel *Estudio de efectos*) en un lenguaje que se parece a C++ o Arduino: con variables, `if`, `for`, `while` y sus propias funciones. No hace falta ser programador: las plantillas de **Nuevo...** funcionan de inmediato y están pensadas para leerlas y modificarlas.

Esta guía también está disponible dentro del estudio con el botón **Ayuda**.

---

## 1. La idea en un minuto

- Un **script** es un archivo de texto (`.fx`). Describe lo que ocurre en **una sola pasada**. Esa pasada se llama `loop()` y se ejecuta **`#RATE` veces por segundo** (1 a 40, por defecto 40).
- En cada pasada el script calcula nuevos **valores de salida**: `dimmer`, o `r`/`g`/`b`, o `pan`/`tilt`. Cuáles, lo decide la **categoría** (`#CATEGORY`).
- Entre dos pasadas la **salida se queda donde está**. A 10 pasadas por segundo el valor cambia por tanto diez veces por segundo – a propósito, así se construyen efectos por pasos.
- El script se ejecuta **para cada proyector por separado**. Cada uno conoce su número (`index`) y el total (`count`); úselos para repartir ondas y chases entre varios proyectores.
- Las variables que cree fuera de `loop()` **conservan su valor entre pasadas**: contadores, estados, temporizadores.

```
#NAME Sine
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05

loop() {
  dimmer = 50 + 50 * sin(2 * PI * speed * elapsed);
}
```

Ese es un efecto completo: el dimmer oscila entre 0 y 100 % con `speed` ondas por segundo.

---

## 2. Resumen de comandos (chuleta)

Todos los comandos de un vistazo. Los capítulos siguientes los explican con ejemplos.

| Área | Comandos |
|---|---|
| Líneas de cabecera | `#NAME`, `#DESCRIPTION`, `#CATEGORY dimmer` / `color` / `position`, `#RATE 1` a `40`, `#VAR name Slider` / `NumberInput` / `ColorPicker` / `Internal ...` |
| Estructura | `setup() { }` (una vez al inicio), `loop() { }` (`#RATE` veces por segundo) |
| Tipos | `float` (`double`), `int` (`long`, `short`, `byte`), `bool` (`boolean`), `void`, `const` |
| Asignación | `x = 1;`, `x += 1;` (también `-=` `*=` `/=` `%=`), `x++;`, `x--;` |
| Ramificación | `if (...) { } else if (...) { } else { }`, `condition ? a : b` |
| Bucles | `for (int i = 0; i < n; i++) { }`, `while (...) { }`, `do { } while (...);`, `break;`, `continue;` |
| Funciones | `float name(float x) { return x * 2; }`, `void name() { }`, `return value;` |
| Cálculo | `+ - * / %`, `== != < <= > >=`, `&& \|\| !` |
| Comentarios | `// hasta el final de la línea`, `/* en varias líneas */` |
| Salidas | Dimmer: `dimmer` · Color: `r`, `g`, `b` o `hsv(h, s, v);` · Posición: `pan`, `tilt` · Zoom: `zoom` · Foco: `focus` · Gobo: `gobo`, `gobo_spin`, `gobo2`, `gobo2_spin` |
| Tiempo | `t` (tiempo de sistema compartido), `elapsed` (desde el inicio del efecto), `dt`, `tick` (`loop_count`), `rate` |
| Proyectores | `index`, `count`, `phase` (= `index / count`), `slots`, `slots2` (número de gobos en la rueda 1 y en la rueda 2) |
| Constantes | `PI`, `TWO_PI`, `HALF_PI`, `E`, `true`, `false` |
| Matemáticas | `sin` `cos` `tan` `asin` `acos` `atan` `atan2` `sqrt` `pow` `exp` `log` `abs` `sign` `min` `max` `floor` `ceil` `round` `fract` `mod` |
| Utilidades | `constrain(x, lo, hi)` `map(x, inMin, inMax, outMin, outMax)` `lerp(a, b, k)` `smoothstep(e0, e1, x)` `radians(d)` `degrees(r)` |
| Formas de onda | `saw(x)` `tri(x)` `square(x)` `square(x, duty)` – cada una de 0 a 1 por periodo |
| Aleatorio, color, gobo | `random()` `random(max)` `random(min, max)` · `hsv(h, s, v)` · `slot(n)` `slot(n, wheel)` |

---

## 3. Usar el estudio

| Área | Qué hace |
|---|---|
| **Abrir...** | Cuadro con todos los efectos, **favoritos primero** (búsqueda, categoría, bucles por segundo, origen; los efectos incluidos llevan la insignia **Predeterminado**). La lista se desplaza. Haga clic en una fila para abrirla, la **estrella** convierte un efecto en favorito (vale para todos los dispositivos), la papelera lo elimina de la carpeta de usuario. Abajo: **Restaurar efectos predeterminados**. |
| **Nuevo...** | Cuadro: primero la **categoría** (dimmer, color, posición, zoom, foco, gobo) o **Archivo vacío**, después una **plantilla** (*Vacío* viene preseleccionado), después los **bucles por segundo**. *Archivo vacío* crea un editor completamente vacío sin líneas de cabecera. **Crear** carga el resultado en el editor; no se guarda nada hasta que usted lo diga. |
| **Guardar** | Guarda en el archivo del efecto. Un efecto nuevo pide un nombre de archivo. Un punto junto al nombre indica cambios sin guardar. Teclado: **Ctrl+S** en el texto (guarda el efecto, no el show). |
| **Guardar como...** | Un nombre de archivo nuevo. Si ya existe, el estudio pregunta si sobrescribirlo. |
| **Eliminar** | Elimina el efecto cargado (solo en la carpeta de usuario; se pregunta antes). Después el editor queda vacío. Si el botón está gris, una indicación dice por qué (aún no guardado, o no está en la carpeta de usuario). |
| **Ayuda** | Abre esta guía. La chuleta (capítulo 2) lista todos los comandos. |
| **Vista previa** | Muestra u oculta la vista previa de la derecha. |
| **Barra de estado** | Verde = bien. Rojo = error con número de línea. A la derecha: línea y columna del cursor. |

El editor **colorea** palabras clave, tipos, números, comentarios, funciones, variables de sistema, salidas y sus deslizadores (`#VAR`). **Intro** conserva la sangría de la línea (dos espacios más tras `{`), **Tab** inserta dos espacios.

### La vista previa

La vista previa ejecuta su script **sin ningún proyector** mientras escribe – exactamente con los bucles por segundo que eligió con `#RATE` – y dibuja el resultado:

- **Dimmer:** una curva por proyector, de 0 a 100 %.
- **Color:** R/G/B como curvas y debajo una **tira de color** por proyector.
- **Posición:** pan y tilt como curvas y la **trayectoria** en el campo pan/tilt.

Por defecto: **1 proyector, 2 segundos**. Arriba ajusta el número de proyectores (1 a 16) y la duración (1 a 20 s); varios proyectores muestran cómo `index`, `count` y `phase` desplazan las ondas. Debajo hay **deslizadores para sus parámetros `#VAR`**: arrastre uno y la curva lo sigue de inmediato. A una velocidad baja (hasta 20 bucles por segundo) la vista previa dibuja pasos; hasta 10, además, los puntos individuales.

Si el script tiene un error, la vista previa se queda en el **último estado correcto, atenuado**, la línea del error se marca en rojo y la barra de estado nombra la línea y el mensaje.

---

## 4. Su primer efecto

1. **Nuevo...** → categoría **Dimmer** → plantilla **Sine** → **Crear**.
2. La vista previa muestra dos ondas en dos segundos (`speed` es 1).
3. Ponga `speed` en 2: el doble de rápido. Ajuste 3 proyectores en la vista previa y ponga `spread` en 0,33: las ondas quedan desplazadas entre sí.
4. Cambie `0.5 + 0.5 * sin(...)` en el texto y observe la curva.
5. **Guardar** (Ctrl+S), introduzca un nombre de archivo. El efecto aparece ahora en la lista de efectos del programador.

---

## 5. Estructura de un script

Un script tiene tres partes:

```
#NAME My effect                            // 1. Header lines (start with #)
#CATEGORY dimmer
#RATE 25
#VAR speed Slider 1 0.1 8 0.1

float level = 0;                           // 2. Variables and functions (optional)

setup() {                                  //    setup(): once when the effect starts (optional)
  level = 50;
}

loop() {                                   // 3. loop(): required, runs #RATE times per second
  dimmer = level;
}
```

### Líneas de cabecera

| Línea | Significado |
|---|---|
| `#NAME text` | Nombre mostrado en el programa. Sin ella se usa el nombre del archivo. |
| `#CATEGORY dimmer` / `color` / `position` | **Obligatoria.** Qué controla el efecto. |
| `#RATE n` | Cuántas veces por segundo se ejecuta `loop()`: un número entero de **1 a 40**. Por defecto 40 – la frecuencia de la salida DMX. |
| `#DESCRIPTION text` | Una descripción breve (también `#DESCRIPTION en ...` y `#DESCRIPTION de ...` para un texto por idioma; el programa muestra el del idioma de la interfaz). |
| `#INFO name en Label \| Hint` | Da al deslizador `name` una **etiqueta** y una **ayuda al pasar el ratón** en un idioma (`en` o `de`), por ejemplo `#INFO speed de Tempo \| Wie schnell der Effekt läuft`. Sin `#INFO` el programa usa su glosario integrado de los nombres habituales (`speed`, `size`, `low`, `high`, `strobe` ...) y por último el propio nombre de la variable. |
| `#TAGS a, b, c` | Palabras clave para buscar y filtrar en el cuadro del tipo de efecto (por ejemplo `strobe, flash, toggle`; hasta 8, en minúsculas). Un script que lee variables de audio recibe automáticamente la etiqueta `audio`; no la escribe usted. Los efectos incluidos llevan `basic` (para principiantes, 19 de ellos) o `advanced` (todos los demás) como primera etiqueta; el cuadro las muestra como «Básico» / «Avanzado»: úselas también para sus propios efectos. |
| `#VAR ...` | Un **deslizador** (véase la sección 9) o una variable interna. |

---

## 6. Tiempo y frecuencia

**La regla más importante:** `loop()` se ejecuta exactamente `#RATE` veces por segundo, sin importar lo rápido que sea el ordenador. Así puede **pensar en segundos exactos**.

| Nombre | Significado |
|---|---|
| `elapsed` | **Segundos desde que el efecto empezó** en este proyector. Empieza en 0. Exactamente `tick / rate`. Así programa «en el segundo 3 debe ocurrir esto». |
| `t` | Tiempo de sistema compartido en segundos. El mismo para **todos** los efectos: los efectos que calculan con `t` permanecen **sincronizados** entre sí aunque se hayan iniciado en momentos distintos. |
| `tick` | Número de la pasada, empieza en 0. |
| `rate` | Pasadas por segundo (el valor de `#RATE`). |
| `dt` | Tiempo entre dos pasadas en segundos (`1 / rate`). |

¿Qué frecuencia elijo?

- **40** (por defecto): las curvas más suaves – para ondas, círculos, fundidos cruzados.
- **10 a 25**: suficiente para cambios de color y efectos que de todos modos van por pasos.
- **1 a 5**: efectos por pasos (un paso por segundo, chases «clic-clic»), baratos de calcular.

**La convención «speed»:** los efectos incluidos y todas las plantillas tienen un deslizador `speed` con valor por defecto **1**: es **un periodo por segundo**. `sin(2 * PI * speed * elapsed)` es una onda por segundo con `speed = 1`.

### En el segundo X ...

```
#NAME Sequence
#CATEGORY dimmer
#RATE 20
#VAR length Slider 8 2 30 1       // length of the sequence in seconds

loop() {
  float s = elapsed % length;     // time within the sequence; jumps back to 0 after "length" seconds
  if (s < 2) {
    dimmer = map(s, 0, 2, 0, 100);                 // seconds 0 to 2: fade in
  } else if (s < 5) {
    dimmer = 100;                                  // seconds 2 to 5: full
  } else {
    dimmer = 100 * (1 - (s - 5) / (length - 5));   // then fade out
  }
}
```

---

## 7. El lenguaje

Todo es un **número**. Los tipos son `float` (decimal, también `double`), `int` (número entero, también `long`, `short`, `byte`) y `bool` (0 o 1, también `boolean`). `true` y `false` son 1 y 0.

### Variables

```
float x = 1.5;          // decimal number (dot, not comma)
int n = 3;              // whole number: assigning truncates (7.9 becomes 7)
bool on = true;         // 0 or 1: any value other than 0 becomes 1
const float K = 0.25;   // constant, cannot be changed
float a = 1, b2 = 2;    // several in one line
```

- Las variables creadas **fuera** de las funciones son **globales** y **conservan su valor** de una pasada a otra. Su valor inicial se aplica cuando el efecto empieza (para restablecerlas más tarde, escriba `setup()`).
- Las variables creadas **dentro** de `{ }` son **locales**: duran hasta la llave de cierre y empiezan de nuevo en cada pasada.
- Asignar a una variable **no declarada** (`counter = counter + 1;`) crea automáticamente un `float` global; así funcionaban los scripts antiguos. Mejor: decláresela.
- Los nombres `t`, `elapsed`, `dt`, `tick`, `rate`, `index`, `count`, `phase`, `dimmer`, `r`, `g`, `b`, `pan`, `tilt`, `PI` y todas las palabras clave y nombres de función están ocupados.

### Calcular y comparar

| Símbolo | Significado |
|---|---|
| `+ - * /` | Aritmética básica. La división por 0 da 0. |
| `%` | Resto (también para decimales): `5.5 % 2` es 1,5. |
| `== != < <= > >=` | Comparaciones; resultado 1 (verdadero) o 0 (falso). |
| `&& \|\| !` | Y, o, no. Las condiciones son verdaderas cuando no son 0. |
| `condition ? a : b` | Elección: `a` si la condición es verdadera, si no `b`. |
| `= += -= *= /= %=` | Asignación; `x += 2;` es `x = x + 2;`. |
| `x++;` `x--;` | Aumentar / disminuir en 1. |

### Ramificar y repetir

```
if (x > 10) {                 // if ...
  dimmer = 100;
} else if (x > 5) {           // else if ...
  dimmer = 50;
} else {                      // else
  dimmer = 0;
}

for (int i = 0; i < 5; i++) { // count i from 0 to 4
  total += i;
}

while (n > 0) { n--; }        // as long as n is greater than 0

do { n++; } while (n < 3);    // run at least once

break;                        // leave the loop at once
continue;                     // jump to the next loop pass
```

Las llaves `{ }` son opcionales para una sola instrucción (`if (a) b = 1;`), pero más claras con ellas. No hay `switch`: use `if` / `else if`.

### Sus propias funciones

```
float wave(float x) {                     // return type, name, parameters
  return 0.5 + 0.5 * sin(2 * PI * x);     // return hands the value back
}

void setBright(float v) {                 // void: returns nothing
  dimmer = v;
}

loop() {
  setBright(100 * wave(speed * elapsed));
}
```

Las funciones pueden estar antes o después del lugar donde se llaman y pueden llamarse a sí mismas (recursividad, limitada). Los parámetros son locales; las variables globales y las salidas (`dimmer` ...) son accesibles en todas partes.

### Comentarios

```
// rest of the line is a comment
/* several
   lines */
```

### Límites

- Una pasada puede hacer como máximo **60 000 iteraciones de bucle y llamadas a funciones**; un bucle infinito se detiene con el mensaje «endless loop?».
- Un efecto que **lanza un error o necesita más de 50 ms por pasada** se desactiva («descansa») para que no retrase a los demás. Guarde de nuevo el script y vuelve a funcionar.
- Solo hay números: sin texto, listas (arrays) ni punteros.

---

## 8. Salidas por categoría

El script escribe su resultado en variables que encajan con la categoría:

| `#CATEGORY` | Salidas | Rango |
|---|---|---|
| `dimmer` | `dimmer` | 0 a 100 (%) |
| `color` | `r`, `g`, `b` | 0 a 255 |
| `position` | `pan`, `tilt` | 0 a 100 (%), 50 es el centro. Si el proyector tiene canales finos (16 bits), se usan decimales: `pan = 33.3333;` es más preciso que `pan = 33;` |
| `zoom` | `zoom` | 0 a 100 (%) – los extremos del canal de zoom (ancho/estrecho, según el proyector) |
| `focus` | `focus` | 0 a 100 (%) – los extremos del canal de foco (cerca/lejos) |
| `gobo` | `gobo` | 0 a 100 (%) – la posición del canal de gobo de la rueda 1; elija los gobos mejor con `slot(n)` (véase abajo) |
| `gobo` | `gobo_spin` | 0 a 100 (%) – rotación o temblor de la rueda 1 (el rango fija dirección y velocidad, según el proyector) |
| `gobo` | `gobo2` | 0 a 100 (%) – rueda de gobos 2 (solo proyectores con una segunda rueda), elija los gobos con `slot(n, 2)` |
| `gobo` | `gobo2_spin` | 0 a 100 (%) – rotación de la rueda 2 |

Los valores fuera de rango se limitan. **Un efecto solo controla las salidas que su script asigna en algún sitio** (`hsv()` cuenta como `r`, `g`, `b`; para el color siempre las tres). Si un script solo escribe `pan`, `tilt` se deja en paz: el canal no sigue al efecto, y en el programador solo está bloqueado el fader Pan; puede seguir ajustando Tilt a mano. Si una salida no se alcanza en una pasada (p. ej. la asignación está en un `if`), queda en 0 durante esa pasada (`pan`/`tilt`: centro, 50). Si el proyector no tiene el canal, la salida se ignora en silencio. Las salidas de otra categoría se ignoran. Con `hsv(h, s, v);` ajusta `r`, `g`, `b` a partir de tono, saturación y valor (cada uno de 0 a 1) en un solo paso.

Nota: las salidas solo se aplican a **la pasada actual**; para recordar un valor, cree su propia variable (`float level = 0;` ... `dimmer = level;`).

---

## 9. Deslizadores: `#VAR`

```
#VAR <name> <type> <default> [min max step]
```

| Tipo | Valor por defecto | Control |
|---|---|---|
| `Slider` | número, más `min max step` | deslizador |
| `NumberInput` | número, más `min max step` | campo numérico |
| `ColorPicker` | color hexadecimal, p. ej. `#ff8800` | selector de color; en el script como `name_r`, `name_g`, `name_b` (0 a 255) |
| `Internal` | número | sin control: una variable global con un valor inicial (como `float name = 0;`) |

```
#VAR speed Slider 1 0.05 8 0.05          // periods per second
#VAR size Slider 100 0 100 1             // strength in %
#VAR color ColorPicker #00aaff           // color_r, color_g, color_b
```

Los deslizadores aparecen en el cuadro **Crear / Editar efecto** y en la vista previa del estudio. En el script son de **solo lectura**.

---

## 10. Variables de sistema

| Nombre | Significado |
|---|---|
| `t` | Tiempo de sistema compartido en segundos (mantiene los efectos sincronizados). |
| `elapsed` | Segundos desde que este efecto empezó en este proyector. |
| `dt` | Segundos entre dos pasadas (`1 / rate`). |
| `tick` | Número de la pasada (0, 1, 2 ...). También `loop_count`. |
| `rate` | Pasadas por segundo. |
| `index` | Número de este proyector en el orden de selección del programador (0, 1, 2 ...). |
| `count` | Número de proyectores en los que se ejecuta el efecto. |
| `phase` | `index / count`: desplazamiento uniforme a lo largo de la selección (0 a casi 1). |
| `slots` | Número de gobos fijos en la rueda 1 (solo en la categoría `gobo`, si no 0). La vista previa usa 8 gobos. |
| `slots2` | Lo mismo para la rueda 2 (0 si el proyector solo tiene una rueda). |

El orden de selección es el orden en que eligió los proyectores.

### Variables de audio (`a_...`)

Los efectos pueden reaccionar a la música. El panel **Audio** analiza el sonido (véase la guía *Audio*); estas variables contienen el resultado. Todas empiezan por `a_`, así que nunca chocan con sus propios nombres. Sin una fuente de audio en marcha todas valen `0`. Un script que lee una de ellas es un **efecto de audio** (marcado en la lista y en el estudio; la vista previa ejecuta entonces un ritmo de ejemplo a 120 BPM).

| Nombre | Significado |
|---|---|
| `a_active` | `1` mientras llega sonido, si no `0`. |
| `a_level` | Volumen general de 0 a 1 (relativo a las partes más fuertes de los últimos segundos). |
| `a_bass`, `a_mid`, `a_high` | Graves (hasta 150 Hz), medios (150 Hz a 2,5 kHz) y agudos (por encima de 2,5 kHz), de 0 a 1. |
| `a_b1` ... `a_b8` | Las ocho bandas una por una (20-60, 60-150, 150-400, 400-1k, 1k-2,5k, 2,5k-5k, 5k-10k, 10k-20k Hz), de 0 a 1. |
| `a_kick`, `a_snare`, `a_hat` | Golpes de bombo, caja (o palmada) y hi-hat: salta a 0,45 - 1 en cada golpe y se desvanece en unos 0,15 s (hi-hat 0,07 s). |
| `a_beat` | El mismo tipo de pulso en cada pulso del tempo detectado. |
| `a_beat_phase` | Posición dentro del pulso, de 0 a 1, creciendo uniformemente de un pulso al siguiente: ideal para ondas sincronizadas con el tempo. |
| `a_beat_count` | Número del pulso; aumenta en 1 en cada pulso. |
| `a_bpm` | Tempo detectado (o fijado) en pulsos por minuto; `0` mientras es desconocido. |
| `a_conf` | Cuán segura es la detección del tempo, de 0 a 1. |

```
#CATEGORY dimmer
#RATE 40
loop() {
  dimmer = lerp(5, 100, a_kick);                              // flash on every bass drum
}
```

Consejo: una pasada solo ve el estado en su propio instante. Leer un pulso (`a_kick`) es siempre seguro porque se desvanece; para reaccionar al *momento* de un golpe, recuerde el último valor en una variable global y compare (véase el efecto *Audio: Hi-Hat Sparkle*). Use `#RATE 40` para efectos de audio para que sigan siendo ágiles.

---

## 11. Funciones

| Función | Significado |
|---|---|
| `sin(x)`, `cos(x)`, `tan(x)` | Ángulo en radianes (círculo completo = `2 * PI`). |
| `asin(x)`, `acos(x)`, `atan(x)`, `atan2(y, x)` | Funciones inversas. |
| `sqrt(x)`, `pow(x, y)`, `exp(x)`, `log(x)` | Raíz, potencia, función exponencial, logaritmo natural. Una entrada no válida da 0. |
| `abs(x)`, `sign(x)` | Valor absoluto; signo (-1, 0, 1). |
| `min(a, b)`, `max(a, b)` | Valor menor / mayor. |
| `floor(x)`, `ceil(x)`, `round(x)` | Redondear hacia abajo, hacia arriba, redondear. |
| `fract(x)` | Parte fraccionaria: `fract(2.25)` es 0,25. Útil para «posición dentro del periodo». |
| `mod(a, b)` | Resto que nunca es negativo (a diferencia de `%` con números negativos). |
| `constrain(x, low, high)` | Limita `x` al rango. |
| `map(x, inMin, inMax, outMin, outMax)` | Convierte `x` de un rango a otro (como en Arduino). |
| `lerp(a, b, k)` | Lineal de `a` a `b`: `a + (b - a) * k`. |
| `smoothstep(e0, e1, x)` | Transición suave de 0 a 1 entre `e0` y `e1`. |
| `saw(x)`, `tri(x)`, `square(x)`, `square(x, duty)` | Formas de onda de 0 a 1 por periodo de `x`: diente de sierra, triángulo, cuadrada (`duty` = proporción «encendido», por defecto 0,5). |
| `radians(d)`, `degrees(r)` | Grados ↔ radianes. |
| `random()`, `random(max)`, `random(min, max)` | Número aleatorio (0 a 1, 0 a `max`, `min` a `max`). Cada proyector tiene su propia secuencia **reproducible**. |
| `hsv(h, s, v)` | Ajusta `r`, `g`, `b` a partir del tono `h` (0 a 1, cíclico), la saturación `s` y el valor `v` (0 a 1). |
| `slot(n)` | El valor (en %) del n-ésimo gobo de la rueda 1; `slot(0)` es el primero (normalmente abierto). Solo en la categoría `gobo`; la lista procede del archivo del proyector, sin datos `slot()` devuelve 0. |
| `slot(n, wheel)` | Como `slot(n)`, pero para la rueda `wheel` (1 o 2): `gobo2 = slot(3, 2);` |

Constantes: `PI`, `TWO_PI`, `HALF_PI`, `E`, `true`, `false`.

---

## 12. Ejemplos

### Pulse (dimmer)

Encendido y apagado secos; `duty` es la proporción del periodo en la que la luz está encendida.

```
#NAME Pulse
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR duty Slider 0.25 0.05 1 0.05
#VAR spread Slider 0 0 1 0.05

loop() {
  float p = fract(speed * elapsed + index * spread);
  dimmer = p < duty ? 100 : 0;
}
```

### Chase (dimmer)

Una luz recorre todos los proyectores seleccionados.

```
#NAME Chase
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.1 8 0.1
#VAR width Slider 1 0.5 8 0.5

loop() {
  float pos = fract(speed * elapsed) * count;   // current step (decimal)
  float d = abs(index - pos);
  if (d > count / 2) d = count - d;             // distance on the circle
  dimmer = d < width ? 100 : 0;
}
```

### Color aleatorio (color)

Cambia `speed` veces por segundo a un tono aleatorio. La variable global `hue` lo recuerda.

```
#NAME Random color
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.1 8 0.1

float hue = 0;

loop() {
  if (tick % max(1, round(rate / speed)) == 0) {
    hue = random();
  }
  hsv(hue, 1, 1);
}
```

### Cuatro posiciones (posición, máquina de estados)

La cabeza salta a la siguiente de cuatro esquinas cada `interval` segundos. El estado vive en `step`.

```
#NAME Four positions
#CATEGORY position
#RATE 10
#VAR interval Slider 1 0.2 10 0.1

int step = 0;
float start = 0;

loop() {
  if (elapsed - start >= interval) {
    step = (step + 1) % 4;
    start = elapsed;
  }
  pan = (step == 0 || step == 3) ? 20 : 80;
  tilt = (step < 2) ? 20 : 80;
}
```

### Armónicos (dimmer, bucle)

Suma varias ondas con un bucle `for` (cuanto más alto, más silencioso).

```
#NAME Harmonics
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.1 4 0.1
#VAR harmonics Slider 3 1 8 1

loop() {
  float sum = 0;
  float norm = 0;
  for (int k = 1; k <= harmonics; k++) {
    sum += sin(2 * PI * k * speed * elapsed) / k;
    norm += 1.0 / k;
  }
  dimmer = 50 + 50 * sum / norm;
}
```

### Zoom que respira (zoom)

El zoom oscila entre `low` y `high` (0 y 100 son los extremos del canal de zoom).

```
#NAME Zoom breathing
#CATEGORY zoom
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR low Slider 20 0 100 1
#VAR high Slider 80 0 100 1

loop() {
  float k = 0.5 + 0.5 * sin(2 * PI * speed * elapsed);
  zoom = lerp(low, high, k);
}
```

### Cambio de gobo (gobo)

Recorre por turnos los gobos del proyector. `slots` es su número, `slot(n)` el valor del n-ésimo (0 = el primero, normalmente abierto). Cada proyector tiene gobos distintos, así que el efecto se lo pregunta al proyector en lugar de adivinar porcentajes.

```
#NAME Gobo change
#CATEGORY gobo
#RATE 20
#VAR speed Slider 0.5 0.05 8 0.05
#VAR first Slider 0 0 20 1

loop() {
  float n = max(1, slots - first);
  gobo = slot(first + mod(floor(speed * elapsed), n));
}
```

### Gobo con rotación y segunda rueda (gobo)

Las salidas `gobo`, `gobo_spin`, `gobo2` y `gobo2_spin` se pueden usar por separado. Este ejemplo recorre la rueda 1, hace que la rueda 2 la siga con un desfase y hace girar el gobo elegido:

```
#NAME Two wheels
#CATEGORY gobo
#RATE 20
#VAR speed Slider 0.5 0.05 8 0.05

loop() {
  float n  = max(1, slots);
  float n2 = max(1, slots2);
  gobo  = slot(mod(floor(speed * elapsed), n));
  gobo2 = slot(mod(floor(speed * elapsed) + 1, n2), 2);
  gobo_spin = 70;                    // rotation of wheel 1 (set only if wanted)
}
```

### Corredor bicolor (color)

Todos los proyectores muestran el color A, uno o dos recorren la fila en el color B (orden de selección). `direction` fija la dirección; este es el *Color Runner* incluido en versión corta:

```
#NAME Color runner
#CATEGORY color
#RATE 40
#VAR speed Slider 0.5 0.05 4 0.05
#VAR width Slider 1.5 0.5 8 0.5
#VAR direction Slider 1 0 1 1
#VAR color_a ColorPicker #ffcc00
#VAR color_b ColorPicker #ff0000

loop() {
  float run = fract(speed * t);
  if (direction < 0.5) run = 1 - run;
  float d = abs(index - run * count);
  if (d > count / 2) d = count - d;
  float k = d < width ? 1 : 0;
  r = lerp(color_a_r, color_b_r, k);
  g = lerp(color_a_g, color_b_g, k);
  b = lerp(color_a_b, color_b_b, k);
}
```

### Su propia función (dimmer)

```
#NAME Triangle with function
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.1 8 0.1

float triangle(float x) {
  return 1 - abs(2 * fract(x) - 1);
}

loop() {
  dimmer = 100 * triangle(speed * elapsed + phase);
}
```

---

## 13. Errores y comprobación

El estudio comprueba mientras escribe. Mensajes típicos (siempre con número de línea):

| Mensaje | Causa |
|---|---|
| `Unbekannte Variable 'x'` | Nombre nunca declarado ni asignado (¿errata?). |
| `Unbekannte Funktion 'foo()'` | La función no existe. |
| `sin() erwartet 1 Argument(e)` | Número de argumentos incorrecto. |
| `';' erwartet, gefunden '}'` | Falta un punto y coma (el mensaje suele señalar la línea siguiente). |
| `Ausdruck erwartet, gefunden ';'` | Falta un valor, p. ej. `dimmer = 1 +;`. |
| `'speed' ist ein Regler (#VAR) ...` | Los deslizadores son de solo lectura; cree su propia variable. |
| `'b' ist eine Ausgabe des Effekts ...` | `dimmer`, `r`, `g`, `b`, `pan`, `tilt` y los nombres de sistema están ocupados. |
| `'break' ist nur in einer Schleife erlaubt` | `break` / `continue` fuera de `for` / `while`. |
| `#RATE erwartet eine ganze Zahl von 1 bis 40` | Frecuencia no válida. |
| `#CATEGORY fehlt` | La cabecera no tiene categoría. |
| `loop() erwartet` | El script no tiene la función `loop()`. |
| `Zu viele Schritte in einem Durchlauf ... Endlosschleife?` | Un bucle no termina nunca (error de ejecución, se muestra en la vista previa). |

(Los mensajes se muestran en alemán sea cual sea el idioma de la interfaz.)

**Guardar** también guarda scripts con errores para que pueda seguir trabajando. Un script defectuoso no se ejecuta; los efectos en marcha conservan la **última versión correcta**.

Si se guarda un script mientras hay efectos en marcha, estos toman el código nuevo en la siguiente pasada. Su **memoria** (variables globales, contadores, estado) se conserva; las variables recién añadidas empiezan con su valor inicial.

---

## 14. Cómo funcionan los efectos en el programa

- **Script y efecto:** el script (`.fx`) es el archivo. Un **efecto** (en la lista de efectos del programador) es una **definición**: un nombre, un script y valores para sus deslizadores. Varios efectos pueden usar el mismo script con valores de deslizador distintos. Al crear uno, el cuadro muestra la descripción del script y sus bucles por segundo.
- **Aplicar:** en el programador asigna un efecto por **categoría** (dimmer, color, posición, zoom, foco, gobo) a los proyectores seleccionados: la fila **Variable:/Efecto** en la vista del programador correspondiente (foco y zoom en la vista de foco, gobo en la pestaña de gobo del área de haz; mientras un efecto está en marcha, el fader correspondiente queda bloqueado). El orden de selección determina `index` y con él el reparto entre los proyectores. Un efecto solo controla los canales de su categoría.
- **En cues:** un cue guarda las asignaciones de efectos (con el orden de selección) y las inicia al reproducirse; los tiempos de **entrada** y **salida del efecto** del cue mezclan la amplitud desde / hacia el valor anterior. Si un cue fija un valor para una categoría, el efecto en marcha termina ahí y el cue hace un fundido desde la última salida del efecto.
- **Sincronización:** los efectos que usan `t` (o `phase`/`index` junto con `t`) van al compás entre sí. Con `elapsed`, cada efecto empieza desde el principio cuando arranca; correcto para secuencias «a partir de ahora».
- **Estado:** cada efecto tiene su **propia memoria** por proyector y categoría. Empieza de nuevo cuando el efecto se vuelve a asignar.
- **Archivos:** los scripts están en la carpeta `effects/` de la carpeta de datos. El estudio, el **gestor de archivos** (tipo *Efectos*: renombrar, duplicar, descargar, subir) y la **exportación** del show (los scripts usados van al paquete) trabajan con los mismos archivos. Los efectos incluidos se copian en el primer inicio; **Restaurar efectos predeterminados** (en el cuadro Abrir o en el gestor de archivos) recrea los que faltan y **nunca** sobrescribe nada.
- **El show guarda las definiciones** (nombre, nombre del script, valores de los deslizadores), no el texto del script. Si falta el script, las definiciones pierden su efecto y vuelven a funcionar cuando regresa; un cue con un efecto ausente deja el canal sin cambios.

### Límites actuales

- Hay seis categorías (dimmer, color, posición, zoom, foco, gobo). Más (prisma, estroboscopio, valores DMX en bruto) están preparadas pero aún no integradas.
- El zoom y el foco usan el canal propio del proyector y este debe existir; los gobos dependen del archivo del proyector. La vista previa solo muestra los valores de los gobos, no la imagen.
- Un efecto controla una categoría por proyector; dos categorías a la vez necesitan dos efectos.
- La frecuencia es como máximo de 40 por segundo porque la salida DMX no envía más rápido.
