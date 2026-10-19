#NAME Pulse
#DESCRIPTION Harter Puls: ein Viertel jeder Periode an, der Rest aus. speed = Pulse pro Sekunde.
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  frac = speed * t + index * spread;
  frac = frac - floor(frac);
  if (frac < 0.25) {
    dimmer = size;
  } else {
    dimmer = 0;
  }
}
