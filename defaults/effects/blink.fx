#NAME Blink
#DESCRIPTION Gleichmäßig an und aus. speed = Blinks pro Sekunde, spread = Versatz zwischen den Scheinwerfern.
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  float p = fract(speed * t + index * spread);
  dimmer = p < 0.5 ? size : 0;
}
