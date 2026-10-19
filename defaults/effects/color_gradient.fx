#NAME Color Gradient
#DESCRIPTION Farbverlauf von Farbe A zu Farbe B über die Scheinwerfer (in Auswahl-Reihenfolge). Der Verlauf wandert langsam (speed); mit speed = 0 steht er still. direction: 1 = vorwärts, 0 = rückwärts.
#CATEGORY color
#RATE 40
#VAR speed Slider 0.1 0 2 0.05
#VAR direction Slider 1 0 1 1
#VAR color_a ColorPicker #ff0000
#VAR color_b ColorPicker #0000ff

loop() {
  float dir = direction > 0.5 ? 1 : -1;
  float base = count > 1 ? index / (count - 1) : 0;
  float k = tri(base * 0.5 + dir * speed * t * 0.5);
  r = lerp(color_a_r, color_b_r, k);
  g = lerp(color_a_g, color_b_g, k);
  b = lerp(color_a_b, color_b_b, k);
}
