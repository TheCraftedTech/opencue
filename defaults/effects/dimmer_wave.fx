#NAME Brightness Wave
#DESCRIPTION en A soft brightness wave runs across the fixtures. waves = wavelengths across the selection.
#DESCRIPTION de Eine weiche Helligkeitswelle läuft über alle Scheinwerfer. waves = Wellenlängen über die Auswahl.
#TAGS advanced, wave
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 0.5 0.05 4 0.05
#VAR waves Slider 1 0.25 4 0.25
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1
#VAR direction Slider 1 0 1 1

loop() {
  float dir = direction > 0.5 ? 1 : -1;
  float k = 0.5 + 0.5 * sin(2 * PI * (dir * speed * t - waves * index / max(count, 1)));
  dimmer = lerp(low, high, k);
}
