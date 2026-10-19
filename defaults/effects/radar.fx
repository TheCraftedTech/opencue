#NAME Radar
#DESCRIPTION Pan fährt gleichmäßig hin und her wie ein Radarstrahl. Nur Pan wird gesteuert, Tilt bleibt frei.
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 40 0 50 1
#VAR spread Slider 0 0 1 0.05

loop() {
  pan = 50 + size * (2 * tri(speed * t * 0.5 + index * spread) - 1);
}
