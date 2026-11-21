#NAME Color Hit
#DESCRIPTION en The base colour flashes into the flash colour on every hit of the chosen drum. toggle = 1: every hit switches between the two colours and holds it.
#DESCRIPTION de Die Grundfarbe blitzt bei jedem Schlag der gewählten Trommel in die Blitzfarbe. toggle = 1: jeder Schlag wechselt zwischen den beiden Farben und hält sie.
#TAGS advanced, flash, strobe, toggle
#CATEGORY color
#RATE 40
#VAR source Slider 0 0 2 1
#VAR base ColorPicker #1a0030
#VAR flash ColorPicker #ffffff
#VAR strobe Slider 0 0 25 1
#VAR toggle Slider 0 0 1 1
#VAR size Slider 100 0 100 1
#INFO source en Source | 0 = bass drum, 1 = snare, 2 = hi-hat.
#INFO source de Quelle | 0 = Bassdrum, 1 = Snare, 2 = Hi-Hat.
#INFO toggle en Hold mode | 0 = flash that fades out, 1 = every hit switches between the colours.
#INFO toggle de Halten | 0 = Blitz, der abklingt, 1 = jeder Schlag wechselt zwischen den Farben.

float state = 0;
float last = 0;

loop() {
  float v = a_kick;
  if (source == 1) { v = a_snare; }
  if (source == 2) { v = a_hat; }
  if (v > last + 0.3) { state = 1 - state; }
  last = v;
  float gate = strobe > 0 ? square(strobe * t) : 1;
  float k = (toggle > 0.5 ? state : v) * gate;
  float q = size / 100;
  r = lerp(base_r, flash_r, k) * q;
  g = lerp(base_g, flash_g, k) * q;
  b = lerp(base_b, flash_b, k) * q;
}
