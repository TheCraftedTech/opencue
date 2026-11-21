#NAME Kick Color Flash
#DESCRIPTION en The base colour flashes into the flash colour on every bass drum hit. mode 1: every hit switches between the colours and holds it.
#DESCRIPTION de Die Grundfarbe blitzt bei jedem Bassdrum-Schlag in die Blitzfarbe. mode 1: jeder Schlag wechselt zwischen den Farben und hält sie.
#TAGS advanced, flash, strobe, toggle
#CATEGORY color
#RATE 40
#VAR base ColorPicker #1a0030
#VAR flash ColorPicker #ffffff
#VAR mode Slider 0 0 1 1
#VAR strobe Slider 0 0 25 1
#VAR size Slider 100 0 100 1
#INFO mode en Hold mode | 0 = flash that fades out, 1 = every hit switches between the colours.
#INFO mode de Halten | 0 = Blitz, der abklingt, 1 = jeder Schlag wechselt zwischen den Farben.

float state = 0;
float last = 0;

loop() {
  if (a_kick > last + 0.3) { state = 1 - state; }
  last = a_kick;
  float gate = strobe > 0 ? square(strobe * t) : 1;
  float k = (mode == 1 ? state : a_kick) * gate;
  float q = size / 100;
  r = lerp(base_r, flash_r, k) * q;
  g = lerp(base_g, flash_g, k) * q;
  b = lerp(base_b, flash_b, k) * q;
}
