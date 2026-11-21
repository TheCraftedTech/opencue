#NAME Color Gradient
#DESCRIPTION en A colour gradient from A to B across the fixtures that slowly moves.
#DESCRIPTION de Ein Farbverlauf von A nach B über die Scheinwerfer, der sich langsam bewegt.
#TAGS advanced, fade
#CATEGORY color
#RATE 40
#VAR speed Slider 0.1 0 2 0.05
#VAR direction Slider 1 0 1 1
#VAR size Slider 100 0 100 1
#VAR color_a ColorPicker #ff0000
#VAR color_b ColorPicker #0000ff

loop() {
  float dir = direction > 0.5 ? 1 : -1;
  float base = count > 1 ? index / (count - 1) : 0;
  float k = tri(base * 0.5 + dir * speed * t * 0.5);
  float q = size / 100;
  r = lerp(color_a_r, color_b_r, k) * q;
  g = lerp(color_a_g, color_b_g, k) * q;
  b = lerp(color_a_b, color_b_b, k) * q;
}
