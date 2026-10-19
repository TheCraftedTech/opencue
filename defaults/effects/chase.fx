#NAME Dimmer Chase
#DESCRIPTION Ein Licht wandert über die Scheinwerfer (in der Reihenfolge der Auswahl). speed = Runden pro Sekunde, width = Breite in Scheinwerfern.
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR width Slider 1 0.5 8 0.5

loop() {
  float pos = fract(speed * t) * count;
  float d = abs(index - pos);
  if (d > count / 2) d = count - d;
  dimmer = d < width ? size : 0;
}
