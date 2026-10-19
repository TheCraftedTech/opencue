#NAME Even / Odd Alternate
#DESCRIPTION Gerade und ungerade Scheinwerfer wechseln sich ab. speed = Wechsel pro Sekunde.
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1

loop() {
  float step = floor(speed * t * 2);
  dimmer = mod(step + index, 2) == 0 ? size : 0;
}
