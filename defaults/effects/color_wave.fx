#NAME Color Wave
#DESCRIPTION en A soft colour wave mixes two colours across the fixtures.
#DESCRIPTION de Eine weiche Farbwelle mischt zwei Farben über die Scheinwerfer.
#TAGS advanced, wave, fade
#CATEGORY color
#RATE 40
#VAR speed Slider 0.5 0.05 4 0.05
#VAR waves Slider 1 0.25 4 0.25
#VAR direction Slider 1 0 1 1
#VAR size Slider 100 0 100 1
#VAR color_a ColorPicker #ffcc00
#VAR color_b ColorPicker #ff0000

loop() {
  float dir = direction > 0.5 ? 1 : -1;
  float k = 0.5 + 0.5 * sin(2 * PI * (dir * speed * t - waves * index / max(count, 1)));
  float q = size / 100;
  r = lerp(color_a_r, color_b_r, k) * q;
  g = lerp(color_a_g, color_b_g, k) * q;
  b = lerp(color_a_b, color_b_b, k) * q;
}
