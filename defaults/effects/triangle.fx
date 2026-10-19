#NAME Triangle Wave
#DESCRIPTION Gleichmäßig auf und ab (Dreieck).
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  dimmer = size * tri(speed * t + index * spread);
}
