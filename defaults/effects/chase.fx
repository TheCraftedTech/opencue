#NAME Dimmer Chase
#DESCRIPTION en A light runs across the fixtures (in selection order). speed = laps per second, width = width in fixtures.
#DESCRIPTION de Ein Licht wandert über die Scheinwerfer (in Auswahl-Reihenfolge). speed = Runden pro Sekunde, width = Breite in Scheinwerfern.
#TAGS basic, chase, strobe
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1
#VAR width Slider 1 0.5 8 0.5
#VAR strobe Slider 0 0 25 1

loop() {
  float pos = fract(speed * t) * count;
  float d = abs(index - pos);
  if (d > count / 2) d = count - d;
  float gate = strobe > 0 ? square(strobe * t) : 1;
  dimmer = d < width ? lerp(low, size, gate) : low;
}
