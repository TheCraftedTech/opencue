#NAME Tilt Bounce
#DESCRIPTION Tilt springt wie ein Ball: schnell hoch, langsam zurück. Nur Tilt wird gesteuert, Pan bleibt frei.
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 30 0 50 1
#VAR spread Slider 0 0 1 0.05

loop() {
  float p = fract(speed * t + index * spread);
  tilt = 50 - size + 2 * size * (1 - pow(1 - p, 2));
}
