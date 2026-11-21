# Entrada DMX (recibir Art-Net y sACN)

OpenCue no solo puede enviar DMX sino también **recibirlo por la red** – desde una mesa de iluminación, un programa (por ejemplo un visualizador o un controlador de show) o un dispositivo. Los valores recibidos se pueden **reenviar y mezclar** en la salida o usar como **disparadores**.

Ábrela con **Controles → Entrada DMX…** (también se puede cambiar desde una tableta).

---

## 1. Activarla

- Activa **Recibir DMX** (desactivado por defecto – el DMX no tiene contraseña, cualquiera en la red puede enviar).
- **Protocolos:** Art-Net (UDP 6454) y/o sACN / E1.31 (UDP 5568, multicast). Universo Art-Net = *dirección de puerto* (exactamente como lo envía OpenCue: universo 1 = dirección de puerto 1).
- **Emisores permitidos:** vacío = cualquiera; si no, direcciones IP o sus comienzos (p. ej. `192.168.1.`).
- **Adaptador de red:** solo hace falta si el ordenador tiene varios y la entrada debe escuchar en uno concreto.
- **Fuente desaparecida tras:** tanto tiempo sin paquetes, luego OpenCue libera los valores de la fuente (sACN: de inmediato con «flujo terminado»).

**Fuentes vistas** muestra en directo todo lo que se envía: protocolo, universo, emisor, paquetes por segundo y cuántos canales no están a cero. **Ver** muestra los 512 canales como una cuadrícula; **Reenviar** crea al instante una asignación.

---

## 2. Reenviar / mezclar (fuente → salida)

Una **asignación** mezcla un *universo de entrada* en un *universo de salida* de OpenCue:

| Modo | Significado |
|---|---|
| **Gana el más alto** (HTP) | Por canal cuenta el mayor valor entre OpenCue y la entrada. El modo por defecto, seguro para mezclar. |
| **Reemplazar** | Cuenta la entrada mientras la fuente está presente (ceros incluidos). Opcionalmente solo para un rango de canales. |

- Varias fuentes para el mismo universo: **gana el más alto**. Con sACN solo cuentan las fuentes de mayor **prioridad**.
- Si el universo de salida **no tiene proyectores**, se emite igualmente – eso da un **reenvío puro** (p. ej. Art-Net → sACN o → un adaptador USB).
- La entrada va **por encima de todo** (programmer, cues, efectos). Los valores dentro de OpenCue permanecen sin cambios; la mezcla ocurre solo en la **salida**.
- Los paquetes propios se reconocen y se ignoran – un reenvío no crea un bucle de realimentación.
- Funciona en el **proceso de salida DMX**: el reenvío continúa sin cambios aunque el programa principal se cuelgue. Si ese proceso falla y la salida funciona dentro del programa principal como alternativa, los disparadores y la visualización siguen funcionando pero la mezcla no (el diálogo lo indica).

---

## 3. Disparadores (canal → comando)

Un **disparador** ejecuta un comando de la línea de comandos cuando cambia un canal:

- **Botón:** cuando el valor sube por encima del **umbral** se ejecuta el primer comando (p. ej. `Go`); cuando vuelve a bajar, el segundo (opcional, p. ej. `Blackout Off`).
- **Fader:** cada valor nuevo se ejecuta como comando; `{value}` representa el valor escalado al **rango** (por defecto 0–100), p. ej. `Master {value}`.
- **Aprender:** haz clic en **Aprender** y mueve un canal en la mesa – se rellenan protocolo, universo y canal.
- El primer valor visto solo se recuerda, no se dispara nada (sin salto al conectar). Los comandos de fader se ejecutan como máximo 20 veces por segundo; el último valor siempre llega.

Ejemplos: canal 1 = `Go` (botón), canal 2 = `Blackout` (botón), canal 3 = `Master {value}` (fader), canal 10 = `Goto Cue 5`.

**Últimos disparadores** muestra lo que se ha disparado.

---

## 4. Bueno saber

- La entrada pertenece a la **configuración de la aplicación** (no al show) y vale para este ordenador.
- Para que una mesa llegue a OpenCue debe enviar a la dirección IP del ordenador o por difusión (broadcast); el cortafuegos de Windows debe permitir UDP 6454 / 5568 para OpenCue – el diálogo muestra si la regla existe y la crea con un clic (Windows pide permiso en el ordenador principal).
- **Anunciarse como dispositivo Art-Net:** OpenCue responde a la búsqueda (ArtPoll) de otros dispositivos y aparece en su lista de dispositivos Art-Net – una mesa puede elegirlo como destino sin escribir la dirección IP.
- Una vista general de todas las entradas y salidas está en **Ajustes → Resumen**.
