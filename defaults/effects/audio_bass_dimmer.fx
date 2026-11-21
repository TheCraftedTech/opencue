#NAME Bass Dimmer
#DESCRIPTION en The brightness follows the bass of the music. Without audio it stays at low.
#DESCRIPTION de Die Helligkeit folgt dem Bass der Musik. Ohne Audio bleibt es auf low.
#TAGS advanced, strobe
#CATEGORY dimmer
#RATE 40
#VAR gain Slider 1 0.2 3 0.05
#VAR low Slider 5 0 100 1
#VAR high Slider 100 0 100 1
#VAR drop Slider 100 50 100 1
#VAR strobe Slider 12 2 25 1
#INFO drop en Strobe threshold | Above this level (%) the lights strobe instead of following smoothly (100 = never, e.g. 85 for drops).
#INFO drop de Stroboskop-Schwelle | Ab diesem Pegel (%) blitzen die Lichter als Stroboskop, statt weich zu folgen (100 = nie, z. B. 85 für Drops).
#INFO strobe en Strobe speed | Flashes per second above the threshold.
#INFO strobe de Blitzfrequenz | Blitze pro Sekunde oberhalb der Schwelle.

loop() {
  float k = constrain(a_bass * gain, 0, 1);
  float v = lerp(low, high, k);
  if (k * 100 >= drop) { v = lerp(low, high, square(strobe * t)); }
  dimmer = v;
}
