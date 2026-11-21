#NAME Color Strobe
#DESCRIPTION en A coloured strobe. mode: 0 always colour A, 1 every flash switches between A and B, 2 every flash a new rainbow colour.
#DESCRIPTION de Ein farbiges Stroboskop. mode: 0 immer Farbe A, 1 jeder Blitz wechselt zwischen A und B, 2 jeder Blitz eine neue Regenbogenfarbe.
#TAGS advanced, strobe, flash, toggle
#CATEGORY color
#RATE 40
#VAR rate_hz Slider 8 1 25 0.5
#VAR duty Slider 25 5 90 5
#VAR mode Slider 1 0 2 1
#VAR size Slider 100 0 100 1
#VAR color_a ColorPicker #ff0030
#VAR color_b ColorPicker #0030ff
#INFO mode en Colours | 0 = always colour A, 1 = A and B alternating, 2 = a new rainbow colour per flash.
#INFO mode de Farben | 0 = immer Farbe A, 1 = A und B im Wechsel, 2 = pro Blitz eine neue Regenbogenfarbe.

loop() {
  float c = floor(rate_hz * t);
  float on = fract(rate_hz * t) < duty / 100 ? size / 100 : 0;
  if (mode == 2) {
    hsv(c * 0.17 + index * 0.05, 1, on);
  } else {
    float pick = mode == 1 ? mod(c, 2) : 0;
    r = lerp(color_a_r, color_b_r, pick) * on;
    g = lerp(color_a_g, color_b_g, pick) * on;
    b = lerp(color_a_b, color_b_b, pick) * on;
  }
}
