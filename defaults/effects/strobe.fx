#NAME Strobe
#DESCRIPTION en Strobe: fast, short flashes. mode: 0 = all together, 1 = even/odd alternating, 2 = chase (the flash runs across the fixtures), 3 = random (each fixture flashes with 50 % chance per period).
#DESCRIPTION de Stroboskop: schnelle, kurze Blitze. mode: 0 = alle gemeinsam, 1 = gerade/ungerade im Wechsel, 2 = Lauflicht (der Blitz wandert über die Scheinwerfer), 3 = zufällig (jeder Scheinwerfer blitzt je Periode mit 50 % Wahrscheinlichkeit).
#TAGS basic, strobe, flash
#CATEGORY dimmer
#RATE 40
#VAR rate_hz Slider 10 1 25 0.5
#VAR duty Slider 20 5 90 5
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1
#VAR mode Slider 0 0 3 1
#INFO mode en Pattern | 0 = all together, 1 = even/odd alternating, 2 = chase, 3 = random.
#INFO mode de Muster | 0 = alle gemeinsam, 1 = gerade/ungerade im Wechsel, 2 = Lauflicht, 3 = zufällig.

float cycle = -1;
float coin = 1;

loop() {
  float shift = 0;
  if (mode == 1) { shift = mod(index, 2) * 0.5; }
  if (mode == 2) { shift = index / max(count, 1); }
  float on = fract(rate_hz * t + shift) < duty / 100 ? 1 : 0;
  if (mode == 3) {
    float c = floor(rate_hz * t);
    if (c != cycle) { cycle = c; coin = random(0, 100) < 50 ? 1 : 0; }
    on = on * coin;
  }
  dimmer = lerp(low, size, on);
}
