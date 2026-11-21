#NAME Pulse
#DESCRIPTION en Hard pulse: a quarter of each period on, the rest off. speed = pulses per second, strobe flashes inside the pulse.
#DESCRIPTION de Harter Puls: ein Viertel jeder Periode an, der Rest aus. speed = Pulse pro Sekunde, strobe blitzt im Puls.
#TAGS advanced, pulse, strobe
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1
#VAR spread Slider 0 0 1 0.05
#VAR strobe Slider 0 0 25 1

loop() {
  float frac = speed * t + index * spread;
  frac = frac - floor(frac);
  float gate = strobe > 0 ? square(strobe * t) : 1;
  dimmer = frac < 0.25 ? lerp(low, size, gate) : low;
}
