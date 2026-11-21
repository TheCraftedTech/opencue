#NAME Color Blend
#DESCRIPTION en Blends from colour A (quiet) to colour B (loud). source picks what drives it: level, bass, mids or highs. Without audio it shows colour A.
#DESCRIPTION de Blendet von Farbe A (leise) zu Farbe B (laut). source wählt, was es steuert: Pegel, Bass, Mitten oder Höhen. Ohne Audio zeigt es Farbe A.
#TAGS advanced, fade
#CATEGORY color
#RATE 40
#VAR gain Slider 1 0.2 3 0.05
#VAR source Slider 0 0 3 1
#VAR size Slider 100 0 100 1
#VAR color_a ColorPicker #0030ff
#VAR color_b ColorPicker #ff0030
#INFO source en Source | 0 = overall level, 1 = bass, 2 = mids, 3 = highs.
#INFO source de Quelle | 0 = Gesamtlautstärke, 1 = Bass, 2 = Mitten, 3 = Höhen.

loop() {
  float v = a_level;
  if (source == 1) { v = a_bass; }
  if (source == 2) { v = a_mid; }
  if (source == 3) { v = a_high; }
  float k = constrain(v * gain, 0, 1);
  float q = size / 100;
  r = lerp(color_a_r, color_b_r, k) * q;
  g = lerp(color_a_g, color_b_g, k) * q;
  b = lerp(color_a_b, color_b_b, k) * q;
}
