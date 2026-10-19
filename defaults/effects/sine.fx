#NAME Sine Wave
#DESCRIPTION Dimmer folgt einer Sinuswelle. speed = Wellen pro Sekunde, size = Staerke, spread = Versatz.
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  dimmer = size * (0.5 + 0.5 * sin(2 * PI * (speed * t + index * spread)));
}
