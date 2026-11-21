# Comandos de voz

Con los **comandos de voz** controla OpenCue con la voz: dice la **palabra de activación** (por defecto «OpenCue») y justo después un **comando de la línea de comandos**; OpenCue lo transcribe, lo convierte a la notación de la línea de comandos y lo **ejecuta al instante**, exactamente igual que un comando escrito (también aparece en el historial de comandos y todas las ventanas lo siguen). Todo funciona **sin conexión** en el ordenador de la consola (tras la descarga única de los modelos); no se necesita ninguna IA.

Se habla en **inglés**: los comandos de la línea de comandos (`Fixture`, `At`, `Color`, `Blackout`, `Go` …) están en inglés y el reconocimiento de voz está configurado para escribir palabras inglesas.

---

## 1. Activarlo

1. El **símbolo del micrófono** arriba a la derecha de la barra de herramientas es un **interruptor de encendido/apagado**:
   - **verde** = el control por voz escucha la palabra de activación,
   - **rojo y tachado** = apagado,
   - **amarillo** = error (micrófono inaccesible, falta el modelo …; la indicación está en la información sobre herramientas).
2. Una vez se descargan dos modelos (cada uno una sola vez; después todo funciona sin internet): el pequeño **modelo de la palabra de activación** (41 MB: *Ajustes → Palabra de activación → Descargar el modelo de voz*, o ya en el instalador) y el **modelo de habla** para los comandos (*Ajustes → Dictado → Cargar ahora*; es el mismo que para el dictado). El modelo de habla *Preciso* (small) entiende mucho mejor que *Rápido* (base).
3. El micrófono, la palabra de activación y la sensibilidad se ajustan en *Ajustes → Palabra de activación*.

El símbolo existe en el ordenador de la consola y también en los dispositivos remotos (iPad): el interruptor activa o desactiva el control por voz del servidor; el micrófono en sí siempre está conectado al ordenador principal.

---

## 2. Cómo hablar

```
"OpenCue … Blackout on."
"OpenCue … Fixture five at seventy nine, color green."
"OpenCue … Fixtures one through five at full."
```

- Primero la **palabra de activación** y después – de un tirón o tras una breve pausa (hasta unos 2 segundos) – el **comando**.
- Cuando el comando haya terminado, **espere aproximadamente un segundo**: una breve pausa finaliza la grabación (10 segundos como máximo).
- En la parte inferior central de la pantalla una burbuja muestra el progreso: **Escuchando …** → **Entendiendo …** → **el comando** con su resultado (verde = hecho, rojo = error o no se entendió nada). Si OpenCue ha corregido una palabra, se muestra detrás («corregido: add → At»).
- Hable con comandos cortos y claros. Las palabras de relleno («uh», «please», «now», «set») y los tartamudeos se eliminan.

---

## 3. Qué se puede decir

Los comandos se dicen tal como se escriben en la línea de comandos (véase la guía *Línea de comandos*). Los números se pueden decir con palabras («seventy nine») o con cifras. Varios comandos de un tirón se separan con **«then»**.

### Seleccionar proyectores y brillo

| Usted dice | Qué se ejecuta |
|---|---|
| Fixture five | `Fixture 5` |
| Fixtures one through ten | `Fixture 1 Thru 10` |
| Fixture three and seven | `Fixture 3 + 7` |
| Fixture five at seventy nine | `Fixture 5 At 79` |
| Fixture five brightness fifty percent | `Fixture 5 At 50%` (también *dimmer, intensity, level*) |
| Fixtures one through five at full / at half | `Fixture 1 Thru 5 At Full` / `… At Half` |
| Fixture five on / full | `Fixture 5 At Full` |
| Fixture five off / out | `Fixture 5 At 0` |
| Fixture five at seventy nine point five | `Fixture 5 At 79.5` |
| At at / Everything on / All lights on | `At At` – **todo encendido** (100 % + blanco): sin selección todos los proyectores, con una selección solo esa selección. Diga antes «Clear» para asegurarse de que sea todo. |
| Fixtures one through ten minus five (también *except / without*) | `Fixture 1 Thru 10 - 5` (sin el n.º 5) |
| Next fixture / Previous fixture | `Next` / `Previous` (selecciona el proyector siguiente / anterior) |
| Group front at full | `Group front At Full` |
| Group front truss at forty | `Group "front truss" At 40` (varias palabras de un nombre van juntas entre comillas) |
| Light / lamp / spot five | `Fixture 5` |

### Colores

| Usted dice | Qué se ejecuta |
|---|---|
| Fixture five color green | `Fixture 5 Color Green` |
| Fixture five green | `Fixture 5 Color Green` (se añade la palabra «color») |
| Fixture five warm white / cool white / light blue | `Fixture 5 Color Warm` / `Cool` / `Lightblue` |
| RGB two fifty five zero zero | `RGB 255 0 0` |
| Color two fifty five one twenty eight zero | `Color 255 128 0` («one twenty eight» = 128 tras *color / rgb / bpm*) |

Colores como en la línea de comandos: red, green, blue, white, black, yellow, cyan, magenta, orange, pink, purple, amber, lime, teal, violet, light blue, warm, cool.

### Posición y haz

| Usted dice | Qué se ejecuta |
|---|---|
| Pan ninety / Pan fifty percent | `Pan 90` / `Pan 50%` |
| Tilt minus forty five / Pan plus fifteen | `Tilt -45` / `Pan +15` (un signo = relativo) |
| Fixture five home / center | `Fixture 5 Pan 50% Tilt 50%` |
| Zoom half / full / minimum / fifty | `Zoom Half` / `Zoom Full` / `Zoom Min` / `Zoom 50` |
| Focus twenty five | `Focus 25` |
| Gobo forty / gobo spin thirty | `Gobo 40` / `GoboSpin 30` |
| Prism one hundred | `Prism 100` |
| Strobe zero / shutter ten | `Strobe 0` / `Strobe 10` |
| Channel six one hundred twenty eight | `Channel 6 128` (canal 6 del proyector a DMX 128) |

### Master y blackout

| Usted dice | Qué se ejecuta |
|---|---|
| Blackout | `Blackout` (alternar) |
| Blackout on / Blackout off | `Blackout On` / `Blackout Off` |
| Master eighty / Master full / Master minus ten | `Master 80` / `Master Full` / `Master -10` |

### Listas de cues

| Usted dice | Qué se ejecuta |
|---|---|
| Go / Next cue | `Go` |
| Back / Go back / Previous cue | `Back` |
| Pause / Resume / Stop | `Pause` / `Resume` / `Stop` |
| Go to cue five | `Go Cue 5` (también *goto cue five*) |
| Cue list main go | `Cuelist main Go` |
| Cue list front of house back | `Cuelist "front of house" Back` |
| Cuelist two go | `Cuelist 2 Go` |
| Cuelist main fader eighty / Fader fifty | `Cuelist main Fader 80` / `Fader 50` |
| Cue five fade three / Cue five delay one point five | `Cue 5 Fade 3` / `Cue 5 Delay 1.5` |
| Store cue five (merge) | `Store Cue 5` (`Merge`) |
| Update / Clear | `Update` / `Clear` |

### Timecode y audio

| Usted dice | Qué se ejecuta |
|---|---|
| Timecode play / pause / stop / reset / reverse | `Timecode Play` / `Pause` / `Stop` / `Reset` / `Reverse` |
| Timecode rate two | `Timecode Rate 2` |
| Tap | `Tap` (marcar el tempo) |
| BPM one twenty eight / BPM auto / BPM half | `BPM 128` / `BPM Auto` / `BPM Half` (también *beats per minute*) |
| Audio start / stop / demo | `Audio Start` / `Stop` / `Demo` |

### Efectos, variables, programador

| Usted dice | Qué se ejecuta |
|---|---|
| Effect rainbow / Effect off | `Effect rainbow` / `Effect Off` |
| Variable warm white | `Variable "warm white"` |
| Manual / Manual color | `Manual` / `Manual Color` |

### Varios comandos

«Fixture one at full **then** fixture two at zero» → `Fixture 1 At Full; Fixture 2 At 0`.

---

## 4. Qué se corrige automáticamente

Whisper a veces escribe palabras que suenan igual pero no tienen sentido en el comando («add» en lugar de «at», «true» en lugar de «thru»). OpenCue comprueba **en qué lugar del comando** está la palabra y pone la palabra de comando adecuada, solo donde encaja:

| Oído / escrito | Se convierte en | Cuándo |
|---|---|---|
| add, ad, it, app | At | después de un número, antes de un número («fixture 5 **add** 70») |
| true, threw, till, through, until, to, too, drew, grew, crew, throw … | Thru | entre dos números («fixtures 1 **true** 5») |
| **2** (Whisper oye «thru» como el número *two*) | Thru | en una selección justo entre dos números («fixtures one **two** five» = `Fixture 1 Thru 5`; también «fixture 1-5» y «1, 2, 5») |
| eight (8) | At | en una selección entre dos números («fixture 5 **eight** 70») |
| halve, calf | Half | siempre; «fixture 3 half» = `Fixture 3 At Half` |
| chanel, clair, stroke, pawn, tell, fate, delight … | Channel, Clear, Strobe, Pan, Tilt, Fade, Delay | según la posición (antes de un número, o siempre) |
| oh | 0 | donde debe haber un número («at oh», «master oh») |
| picture, pitcher, fix sure, fixer | Fixture | siempre («**picture** one to four») |
| for, to, too, won, ate, tree | 4, 2, 2, 1, 8, 3 | solo donde debe haber un número («fixture **for** at fifty» → Fixture 4 At 50) |
| collar, caller | Color | siempre |
| pen, ban, pun | Pan | antes de un número |
| till, tilted | Tilt | antes de un número («**till** minus ten») |
| queue, q, cute, cube, key | Cue | antes de un número («go **key** five») |
| fool | Full | siempre |
| of, own | Off, On | después de Blackout |
| prison, prisms | Prism | siempre |
| strove | Strobe | siempre |
| paws, pours | Pause | siempre |
| affect, effects | Effect | siempre |
| tab | Tap | siempre |
| read, grin, grain, blew, wait … | Red, Green, Blue, White | después de «color» o como nombre de color |
| black out, black art, blackouts | Blackout | siempre |
| time code, cue list, grand master, go bo, b p m | Timecode, Cuelist, Master, Gobo, BPM | expresiones de varias palabras |

Además:

- **Números con palabras** → cifras («twenty one», «one hundred and five», «two point five», «minus ten percent»).
- **Comparación fonética:** una palabra desconocida que está donde debe ir una determinada palabra de comando y suena igual se convierte en esa palabra.
- **Pequeñas faltas de ortografía** de las palabras clave → la palabra de comando más cercana («blakout» → Blackout).
- **Variantes de la palabra de activación** («open queue», «open Q», «OpenCue») se eliminan al principio, y también todo lo dicho antes de la palabra de activación.
- **Los nombres** (después de *group, cuelist, effect, variable*) se quedan como se pronunciaron.
- **El porcentaje** después de Master, Fader, BPM y números de cue se omite («master eighty percent» → `Master 80`), porque la línea de comandos no conoce el porcentaje ahí.
- La charla introductoria antes del comando («set», «please», todo lo que no se entiende) se omite; el comando debe empezar con una palabra de comando.

---

## 5. Qué no funciona por voz

En el **modo operador** de la consola (*Ver → Modo operador ...*) el control por voz está **desactivado**, de modo que en este PC solo es posible lo que ofrece la superficie de control; al salir vuelve a funcionar si estaba activado.

Por seguridad el control por voz **nunca ejecuta nada que borre o sobrescriba**: `Delete …`, `Clear Clear`, `Overwrite`. La burbuja dice entonces «No por voz». Escriba estos comandos o use la interfaz.

---

## 6. Cuando no funciona

| Indicación | Qué hacer |
|---|---|
| Micrófono amarillo | Lea la información sobre herramientas; *Ajustes → Palabra de activación* (¿el micrófono correcto?) |
| «Falta el modelo de habla» | *Ajustes → Dictado → Cargar ahora* (y para la palabra de activación: *Ajustes → Palabra de activación → Descargar el modelo de voz*) |
| «No se entendió nada» | Acérquese al micrófono, hable con más claridad, diga el comando justo después de la palabra de activación |
| «No se reconoció ningún comando» | El texto no empieza con una palabra de comando; la burbuja muestra lo que se entendió; hable exactamente como en la línea de comandos |
| Comando rojo (✗) | La línea de comandos dice qué no encaja (por ejemplo el proyector no existe, «esta lista de cues no tiene cues») |
| No se reconoce la palabra de activación | Suba *Ajustes → Palabra de activación → Sensibilidad* |
| Una palabra se escribe siempre mal | Anote lo que escribe Whisper (el texto está en el registro); la tabla de correcciones es fácil de ampliar |

La palabra de activación la reconoce un pequeño modelo sin conexión; el comando que sigue lo transcribe Whisper (de 1 a 3 segundos en un ordenador normal). La música alta o el ruido en la sala empeoran el reconocimiento: un micrófono cerca de la boca ayuda más que nada.
