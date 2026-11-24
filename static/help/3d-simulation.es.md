# Simulación 3D

El panel **Simulación 3D** muestra tu escenario en 3D; cada proyector se ilumina en vivo según sus valores DMX. Añádelo con **Añadir panel**. Esta guía explica los botones, los ajustes de **Sala y luz** y qué comprobar cuando la imagen no es la esperada (no todos los proyectores iluminan el escenario, faltan conos o sombras, va lento).

---

## 1. El panel

- Tres modos arriba a la izquierda: **Ver**, **Construir** (objetos y modelos 3D) y **Proyectores** (colocar proyectores, apuntar las cabezas móviles).
- Botones arriba a la derecha: gafas VR (solo si el navegador ofrece unas), compartir la cámara entre dispositivos, **Sala y luz** (engranaje), **Detener / Iniciar la simulación 3D**, **Blackout** (bombilla), **Restablecer vista**, **Pantalla completa**.
- Abajo a la izquierda: el botón de calidad muestra la tasa de imagen y la resolución; un clic cambia Automática → Baja → Media → Alta.
- **Luz de planificación en el editor:** En los modos **Construir** y **Proyectores** los proyectores no emiten luz y no hay neblina – la luz de trabajo ilumina la sala de forma uniforme y la visualización sigue fluida. En el modo *Proyectores* se marcan en rojo para ver dónde están. En **Vista** todo sigue como siempre. Para desactivarlo: *Sala y luz → Proyectores apagados en el editor* (solo este dispositivo).
- **Nitidez en reposo:** Cuando la imagen está en reposo (cámara quieta, nada cambia, ninguna luz en directo se mueve), OpenCue la vuelve a dibujar una vez con mayor resolución; cualquier movimiento o cambio vuelve de inmediato a lo normal. Hasta dónde llega depende de la tarjeta gráfica (las débiles reciben menos, el ajuste *Baja* lo desactiva). Mientras se mueve una luz en directo, la resolución se mantiene normal.
- **3D en ventana propia:** El botón *3D en ventana propia* (arriba a la derecha del panel 3D, solo en el ordenador de la consola) abre la simulación 3D en una **ventana propia con su propio proceso**. La consola funciona entonces sin la carga 3D (faders y listas siguen fluidos aunque la vista 3D esté ocupada) y el proceso 3D se ejecuta con **menor prioridad**: la consola va primero. La ventana se puede arrastrar a una segunda pantalla; se recuerdan posición y tamaño. En la ventana principal el panel muestra un marcador con *Traer la ventana al frente* y *Mostrar aquí (cerrar la ventana)*. Al cerrar la ventana (o el programa), vuelve la vista 3D. Todo lo que haces en la consola se ve en directo en la ventana 3D. Ambas ventanas siguen compartiendo la tarjeta gráfica.
- **Pausa cuando no se ve nada:** Si la ventana está minimizada, en otro escritorio o totalmente tapada por otras ventanas, la vista 3D no dibuja nada (sin cálculo, sin carga de la tarjeta gráfica); en cuanto vuelves a ver la ventana, continúa al instante. También puedes pausar y reanudar la vista 3D con el botón de pausa – incluida la **ventana 3D desde la ventana principal** (botón *Pausar 3D* / *Iniciar 3D* en el marcador).

## 2. Detener e iniciar la simulación 3D

El botón de pausa detiene la simulación por completo: la escena, el contexto gráfico y los modelos se eliminan, no se calcula ni se dibuja nada y el resto de OpenCue no se ralentiza. El panel permanece en tu layout y muestra un botón de reproducir; **Iniciar** lo reconstruye todo. La elección se recuerda **por dispositivo** y vale para todos los paneles 3D de ese dispositivo. Si un panel 3D está vacío y indica que está detenido, pulsa el botón de reproducir.

Tras iniciar, tras cargar un show grande o tras cambiar los límites de luz, el panel muestra un momento *Preparando la iluminación …*: la tarjeta gráfica prepara sus programas en segundo plano y el resto de OpenCue sigue siendo utilizable.

## 3. Sala y luz

Abre el diálogo con el engranaje. Tiene dos partes.

**Para todos los dispositivos** – vale para cada dispositivo conectado al show (consola, iPad, acceso remoto): *Iluminación* (luz de trabajo en el modo Construir, luz de sala), *Luz reflejada* (luz de sala, reflexión de paredes, radiación de color), *Imagen* (reflexión de objetos, exposición, **Bruma**) y *Cuadrícula y ejes en la vista*. **Bruma al 0 %** desactiva la bruma por completo: sin conos de luz y sin cálculo de bruma – es lo que más rendimiento ahorra.

**Solo este dispositivo** – rendimiento y calidad. Solo valen en este dispositivo, cada dispositivo puede elegir los suyos:

| Ajuste | Significado |
|---|---|
| **Calidad** | Automática (se adapta a la tasa de imagen), Baja, Media, Alta: resolución y detalle de sombras. |
| **Luces máx.** | Cuántos proyectores reciben a la vez su propia luz sobre las superficies (por defecto 32). Ganan los más brillantes. |
| **Sombras máx.** | Cuántas de estas luces proyectan sombras. 0 = tantas como permita la tarjeta gráfica. |
| **Reflejos de espejo máx.** | Reflejos en metal y espejos. |
| **Máx. conos de luz simples** | Cuántos conos de luz simples se dibujan. 0 = todos. Con un límite, cada proyector conserva primero su primer cono, luego los más brillantes. |
| **Tasa máx. de imagen** | Limita cuántas veces por segundo se redibuja la imagen (por ejemplo 30). 0 = ilimitada. |
| **Los proyectores proyectan sombras** | Las carcasas de los proyectores proyectan sombras en los conos de luz (activado por defecto). |
| **Proyectores apagados en el editor** | En el modo construcción y proyectores, los proyectores no emiten luz (por defecto: sí); en el modo proyectores se marcan en rojo. |
| **Marcado en el modo proyectores** | Cómo se marcan los proyectores en el modo *Proyectores*: *Ninguno*, *Proyectores rojos* (por defecto), *Punto rojo* o *Rojo y punto*. |
| **Botón VR** | Cuándo aparece el botón VR (gafas): *Automático* (solo en dispositivos VR como Quest, Pico, Vision Pro – no en PC o portátil), *Siempre que sea posible* (p. ej. VR en PC) o *Nunca*. |

La línea bajo los ajustes muestra lo que se aplica ahora (luces, sombras, proyectores colocados) y lo que permite la tarjeta gráfica. **Restablecer límites** restaura los valores por defecto.

## 4. Cuando la imagen no es la esperada

- **No todos los proyectores iluminan el escenario, algunos no tienen sombra, solo algunos muestran un gobo.** Se debe a los límites de este dispositivo. Solo los *Luces máx.* proyectores más brillantes (por defecto 32) iluminan las superficies, solo *Sombras máx.* de ellos proyectan sombras (la tarjeta gráfica fija un límite superior, indicado en la línea de información) y un patrón de gobo o prisma aparece en las primeras **3** luces de este tipo; las demás muestran luz abierta. Aumenta *Luces máx.* y *Sombras máx.* (0 = tantas como sea posible) si quieres ver todo – con muchos proyectores la imagen se vuelve más lenta o con algo de retraso.
- **Un proyector está encendido pero falta su cono.** Comprueba la **Bruma** (0 % = sin conos), *Máx. conos de luz simples*, el Blackout, el Grand Master, el dimmer del proyector y que la simulación 3D no esté detenida.
- **La imagen está oscura.** La luz de trabajo solo existe en el modo Construir; comprueba el control *Exposición*, el Blackout y el Grand Master.
- **La simulación 3D va lenta.** Prueba por este orden: Bruma 0 % (si no la necesitas), menos *Luces máx.* / *Sombras máx.*, *Máx. conos de luz simples* (por ejemplo 200), desactivar *Los proyectores proyectan sombras*, calidad Baja o Automática, una *Tasa máx. de imagen* de 30, o detener la simulación 3D mientras no la necesites. Los escenarios con 100 o más proyectores encendidos a la vez son exigentes; hasta unos 16 proyectores encendidos a la vez bastan los valores por defecto.
- **Un proyector no se mueve en 3D.** Su tipo necesita un modelo 3D con horquilla / cabeza móvil y canales Pan / Tilt; los tipos sin ellos (paneles LED, barras, blinders) permanecen quietos. El proyector también debe estar colocado en el escenario (modo Proyectores → *Colocar todos*).
- **Un cono de luz apunta en la dirección equivocada.** OpenCue invierte la dirección automáticamente cuando un archivo GDTF hace que el haz apunte hacia la carcasa. Si un tipo sigue mal, anota su nombre y comunícaselo al desarrollador.
