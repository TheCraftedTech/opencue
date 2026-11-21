#NAME Beat Color Fade
#DESCRIPTION en Fades between two colours in time with the music. mode 1: A to B on one beat, B to A on the next; mode 0: A to B every beat, then jump back. Dark without a detected tempo.
#DESCRIPTION de Blendet im Takt der Musik zwischen zwei Farben. mode 1: A nach B in einem Beat, B nach A im nächsten; mode 0: jeden Beat A nach B, dann zurückspringen. Dunkel ohne erkanntes Tempo.
#TAGS advanced, fade, toggle
#CATEGORY color
#RATE 40
#VAR mode Slider 1 0 1 1
#VAR every Slider 1 1 8 1
#VAR size Slider 100 0 100 1
#VAR color_a ColorPicker #ff0040
#VAR color_b ColorPicker #0040ff
#INFO mode en Fade mode | 0 = A to B every beat then jump back, 1 = A to B, then B to A (smooth).
#INFO mode de Überblendung | 0 = jeden Beat A nach B, dann zurückspringen, 1 = A nach B, dann B nach A (weich).

loop() {
  float cyc = (a_beat_count + a_beat_phase) / max(every, 1);
  float k = mode == 1 ? tri(cyc * 0.5) : fract(cyc);
  float q = a_bpm > 0 ? size / 100 : 0;
  r = lerp(color_a_r, color_b_r, k) * q;
  g = lerp(color_a_g, color_b_g, k) * q;
  b = lerp(color_a_b, color_b_b, k) * q;
}
