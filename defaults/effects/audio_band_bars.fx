#NAME Band Bars
#DESCRIPTION en Every fixture shows one frequency band: the first the lows, the last the highs (repeats with more than 8 fixtures).
#DESCRIPTION de Jeder Scheinwerfer zeigt ein Frequenzband: der erste die Tiefen, der letzte die Höhen (wiederholt sich bei mehr als 8 Scheinwerfern).
#TAGS advanced, spectrum
#CATEGORY dimmer
#RATE 40
#VAR gain Slider 1 0.2 3 0.05
#VAR low Slider 0 0 100 1
#VAR flip Slider 0 0 1 1

loop() {
  float i = flip > 0.5 ? count - 1 - index : index;
  float band = count > 1 ? floor(i * 8 / count) : 0;
  float v = a_b1;
  if (band == 1) { v = a_b2; }
  if (band == 2) { v = a_b3; }
  if (band == 3) { v = a_b4; }
  if (band == 4) { v = a_b5; }
  if (band == 5) { v = a_b6; }
  if (band == 6) { v = a_b7; }
  if (band == 7) { v = a_b8; }
  dimmer = lerp(low, 100, constrain(v * gain, 0, 1));
}
