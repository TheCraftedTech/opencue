#NAME Beat Color
#DESCRIPTION en The colour changes on every beat (or every n-th one) and is brightest on the beat. mode: 0 rainbow steps (within the colour range), 1 back and forth between colour A and B, 2 even/odd fixtures opposite.
#DESCRIPTION de Die Farbe wechselt bei jedem Beat (oder jedem n-ten) und leuchtet auf dem Beat am hellsten. mode: 0 Regenbogen-Schritte (im Farbbereich), 1 zwischen Farbe A und B hin und her, 2 gerade/ungerade Scheinwerfer gegenläufig.
#TAGS basic, toggle, strobe
#CATEGORY color
#RATE 40
#VAR mode Slider 0 0 2 1
#VAR every Slider 1 1 8 1
#VAR spread Slider 0.15 0 1 0.05
#VAR hold Slider 0.4 0 1 0.05
#VAR strobe Slider 0 0 25 1
#VAR size Slider 100 0 100 1
#VAR color_a ColorPicker #ff0040
#VAR color_b ColorPicker #0040ff
#VAR hue_from Slider 0 0 360 1
#VAR hue_range Slider 360 10 360 1
#VAR saturation Slider 100 0 100 1
#INFO mode en Colour mode | 0 = rainbow steps, 1 = A/B back and forth, 2 = even/odd opposite.
#INFO mode de Farbmodus | 0 = Regenbogen-Schritte, 1 = A/B hin und her, 2 = gerade/ungerade gegenläufig.
#INFO hold en Brightness between beats | Brightness between the beats (0 to 1).
#INFO hold de Helligkeit zwischen den Beats | Helligkeit zwischen den Beats (0 bis 1).

loop() {
  float step = floor(a_beat_count / max(every, 1));
  float gate = strobe > 0 ? square(strobe * t) : 1;
  float v = (a_bpm > 0 ? lerp(hold, 1, a_beat) : 0) * gate * size / 100;
  if (mode == 0) {
    float h = fract(step * 0.137 + index * spread);
    float k = hue_range >= 359.5 ? h : tri(h);
    hsv(hue_from / 360 + hue_range / 360 * k, saturation / 100, v);
  } else {
    float flip = mode == 2 ? mod(step + index, 2) : mod(step, 2);
    r = lerp(color_a_r, color_b_r, flip) * v;
    g = lerp(color_a_g, color_b_g, flip) * v;
    b = lerp(color_a_b, color_b_b, flip) * v;
  }
}
