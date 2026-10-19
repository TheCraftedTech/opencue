#NAME Color Wave
#DESCRIPTION Eine weiche Farbwelle läuft in Auswahl-Reihenfolge über alle Scheinwerfer und mischt dabei zwei Farben. speed = Wellen pro Sekunde, waves = Wellenlängen über die Auswahl, direction: 1 = vorwärts, 0 = rückwärts.
#CATEGORY color
#RATE 40
#VAR speed Slider 0.5 0.05 4 0.05
#VAR waves Slider 1 0.25 4 0.25
#VAR direction Slider 1 0 1 1
#VAR color_a ColorPicker #ffcc00
#VAR color_b ColorPicker #ff0000

loop() {
  float dir = direction > 0.5 ? 1 : -1;
  float k = 0.5 + 0.5 * sin(2 * PI * (dir * speed * t - waves * index / max(count, 1)));
  r = lerp(color_a_r, color_b_r, k);
  g = lerp(color_a_g, color_b_g, k);
  b = lerp(color_a_b, color_b_b, k);
}
