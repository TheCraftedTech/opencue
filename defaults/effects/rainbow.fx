#NAME Rainbow Fade
#DESCRIPTION Farbverlauf durch den Regenbogen. speed = Durchlaeufe pro Sekunde.
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  h = speed * t + index * spread;
  h = h - floor(h);
  r = min(max(abs(h * 6 - 3) - 1, 0), 1) * 255 * size / 100;
  g = min(max(2 - abs(h * 6 - 2), 0), 1) * 255 * size / 100;
  b = min(max(2 - abs(h * 6 - 4), 0), 1) * 255 * size / 100;
}
