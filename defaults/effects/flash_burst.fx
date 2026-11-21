#NAME Flash Burst
#DESCRIPTION en A burst of fast flashes, then a pause - again and again. spread offsets the bursts between the fixtures (0 = all at once).
#DESCRIPTION de Eine Salve aus schnellen Blitzen, dann eine Pause - immer wieder. spread versetzt die Salven zwischen den Scheinwerfern (0 = alle gleichzeitig).
#TAGS advanced, strobe, flash
#CATEGORY dimmer
#RATE 40
#VAR flashes Slider 3 1 10 1
#VAR speed Slider 12 2 25 1
#VAR pause Slider 1 0 5 0.1
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1
#VAR spread Slider 0 0 1 0.05
#INFO speed en Flash speed | Flashes per second inside a burst.
#INFO speed de Blitzfrequenz | Blitze pro Sekunde innerhalb einer Salve.

loop() {
  float burst = flashes / speed;
  float cyc = burst + pause;
  float p = mod(t + index * spread * cyc, cyc);
  dimmer = (p < burst && fract(p * speed) < 0.5) ? size : low;
}
