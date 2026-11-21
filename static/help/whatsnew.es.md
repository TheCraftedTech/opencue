# Novedades

Los cambios más importantes de esta versión de un vistazo. La lista completa está en `CHANGELOG.md`; cada tema tiene su propia guía (Ayuda → Guías).

---

## Un nuevo núcleo DMX

- **La salida DMX funciona en su propio proceso** – junto con los efectos y los fundidos de cues. Una ventana ocupada o una tableta lenta ya no pueden perturbar un fundido: unos 40 fotogramas por segundo constantes, incluso con mucha carga.
- **Entrada DMX:** recibir Art-Net y sACN de otra mesa, reenviarlos y mezclarlos, usar canales como disparadores (*Controles → Entrada DMX…*). OpenCue también se anuncia como dispositivo Art-Net.

## Un acceso remoto que lo puede todo

- Una tableta tiene **los mismos derechos que la consola, todos los ajustes incluidos**, y su propio **Explorador de OpenCue** para archivos. **Modo servidor** sin ventana (`--no-ui`) con icono de bandeja e inicio con Windows.

## Control desde fuera

- **MIDI** de entrada y salida, **OSC**, una **API REST** con flujo WebSocket, **atajos de teclado personalizados**, una **programación** y **control por voz** sin conexión.

## Línea de tiempo y timecode

- Un **editor de línea de tiempo** con formas de onda y pistas de comandos, **LTC** de entrada y salida, **timecode MIDI**.

## Proyectores

- Un **editor de proyectores** propio, una **vista previa de los proyectores de GDTF Share** antes de instalar y la **importación de una lista de patch desde CSV o Excel**.

## Shows seguros

- **Deshacer / Rehacer**, **copias de seguridad** en segundo plano con restauración tras un fallo, un **bloqueo** para shows terminados, **guardado seguro** y una pregunta antes de que algo pueda perderse.

## Aspecto y ayuda

- **Seis idiomas**, diálogos en cinco tamaños homogéneos, **ajustes** con una búsqueda en todas las categorías y explicaciones tras una pequeña **(i)**, temas de color donde cada color se puede cambiar, y **guías** con `F1`.

Todo permanece desactivado por defecto; tú decides qué se activa.
