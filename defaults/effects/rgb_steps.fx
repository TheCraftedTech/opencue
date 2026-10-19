#NAME RGB Steps
#DESCRIPTION Rot, Grün, Blau nacheinander. speed = Wechsel pro Sekunde.
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  float step = mod(floor(speed * t + index * spread * 3), 3);
  r = step == 0 ? 255 * size / 100 : 0;
  g = step == 1 ? 255 * size / 100 : 0;
  b = step == 2 ? 255 * size / 100 : 0;
}
