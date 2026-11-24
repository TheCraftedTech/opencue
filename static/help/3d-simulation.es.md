# Simulación 3D

El panel **Simulación 3D** muestra tu escenario en 3D; cada proyector se ilumina en vivo según sus valores DMX. Añádelo con **Añadir panel**. Esta guía explica los botones, los ajustes de **Sala y luz** y qué comprobar cuando la imagen no es la esperada (no todos los proyectores iluminan el escenario, faltan conos o sombras, va lento).

---

## 1. El panel

- Tres modos arriba a la izquierda: **Ver**, **Construir** (objetos y modelos 3D) y **Proyectores** (colocar proyectores, apuntar las cabezas móviles).
- Botones arriba a la derecha: gafas VR (solo si el navegador ofrece unas), compartir la cámara entre dispositivos, **Sala y luz** (engranaje), **Detener / Iniciar la simulación 3D**, **Blackout** (bombilla), **Restablecer vista**, **Pantalla completa**.
- Abajo a la izquierda: el botón de calidad muestra la tasa de imagen y la resolución; un clic cambia Automática → Baja → Media → Alta.

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

La línea bajo los ajustes muestra lo que se aplica ahora (luces, sombras, proyectores colocados) y lo que permite la tarjeta gráfica. **Restablecer límites** restaura los valores por defecto.

## 4. Cuando la imagen no es la esperada

- **No todos los proyectores iluminan el escenario, algunos no tienen sombra, solo algunos muestran un gobo.** Se debe a los límites de este dispositivo. Solo los *Luces máx.* proyectores más brillantes (por defecto 32) iluminan las superficies, solo *Sombras máx.* de ellos proyectan sombras (la tarjeta gráfica fija un límite superior, indicado en la línea de información) y un patrón de gobo o prisma aparece en las primeras **3** luces de este tipo; las demás muestran luz abierta. Aumenta *Luces máx.* y *Sombras máx.* (0 = tantas como sea posible) si quieres ver todo – con muchos proyectores la imagen se vuelve más lenta o con algo de retraso.
- **Un proyector está encendido pero falta su cono.** Comprueba la **Bruma** (0 % = sin conos), *Máx. conos de luz simples*, el Blackout, el Grand Master, el dimmer del proyector y que la simulación 3D no esté detenida.
- **La imagen está oscura.** La luz de trabajo solo existe en el modo Construir; comprueba el control *Exposición*, el Blackout y el Grand Master.
- **La simulación 3D va lenta.** Prueba por este orden: Bruma 0 % (si no la necesitas), menos *Luces máx.* / *Sombras máx.*, *Máx. conos de luz simples* (por ejemplo 200), desactivar *Los proyectores proyectan sombras*, calidad Baja o Automática, una *Tasa máx. de imagen* de 30, o detener la simulación 3D mientras no la necesites. Los escenarios con 100 o más proyectores encendidos a la vez son exigentes; hasta unos 16 proyectores encendidos a la vez bastan los valores por defecto.
- **Un proyector no se mueve en 3D.** Su tipo necesita un modelo 3D con horquilla / cabeza móvil y canales Pan / Tilt; los tipos sin ellos (paneles LED, barras, blinders) permanecen quietos. El proyector también debe estar colocado en el escenario (modo Proyectores → *Colocar todos*).
- **Un cono de luz apunta en la dirección equivocada.** OpenCue invierte la dirección automáticamente cuando un archivo GDTF hace que el haz apunte hacia la carcasa. Si un tipo sigue mal, anota su nombre y comunícaselo al desarrollador.
