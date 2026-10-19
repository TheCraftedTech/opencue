#NAME Rainbow Dot Chase
#DESCRIPTION Ein Farbpunkt wandert über die Scheinwerfer, dabei wechselt seine Farbe. speed = Runden pro Sekunde.
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR width Slider 1 0.5 8 0.5

loop() {
  float pos = fract(speed * t) * count;
  float d = abs(index - pos);
  if (d > count / 2) d = count - d;
  if (d < width) {
    hsv(speed * t * 0.5, 1, size / 100);
  }
}
