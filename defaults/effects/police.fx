#NAME Police Red/Blue
#DESCRIPTION Rot und Blau im Wechsel, gerade und ungerade Scheinwerfer gegenläufig. speed = Wechsel pro Sekunde.
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1

loop() {
  bool flip = fract(speed * t) < 0.5;
  bool red = (mod(index, 2) == 0) == flip;
  r = red ? 255 * size / 100 : 0;
  b = red ? 0 : 255 * size / 100;
}
