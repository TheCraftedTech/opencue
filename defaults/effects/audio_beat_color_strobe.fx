#NAME Beat Color Strobe
#DESCRIPTION en A coloured strobe in time with the music: mult flashes per beat, alternating between colour A and B. mode 1: only as a burst after each bass drum.
#DESCRIPTION de Ein farbiges Stroboskop im Takt der Musik: mult Blitze pro Beat, abwechselnd in Farbe A und B. mode 1: nur als Salve nach jeder Bassdrum.
#TAGS advanced, strobe, flash, toggle
#CATEGORY color
#RATE 40
#VAR mult Slider 4 1 16 1
#VAR duty Slider 30 5 90 5
#VAR mode Slider 0 0 1 1
#VAR size Slider 100 0 100 1
#VAR color_a ColorPicker #ff0030
#VAR color_b ColorPicker #0030ff
#INFO mode en Pattern | 0 = always, 1 = only as a burst after each bass drum.
#INFO mode de Muster | 0 = immer, 1 = nur als Salve nach jeder Bassdrum.

loop() {
  float p = (a_beat_count + a_beat_phase) * mult;
  float on = fract(p) < duty / 100 ? 1 : 0;
  if (mode == 1) { on = on * (a_kick > 0.15 ? 1 : 0); }
  float pick = mod(floor(p), 2);
  float q = a_bpm > 0 ? on * size / 100 : 0;
  r = lerp(color_a_r, color_b_r, pick) * q;
  g = lerp(color_a_g, color_b_g, pick) * q;
  b = lerp(color_a_b, color_b_b, pick) * q;
}
