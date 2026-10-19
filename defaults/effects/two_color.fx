#NAME Two-Color Fade
#DESCRIPTION Weiche Ueberblendung zwischen zwei Farben. speed = Hin-und-Her pro Sekunde.
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05
#VAR color_a ColorPicker #ff0000
#VAR color_b ColorPicker #0000ff

loop() {
  mix = 0.5 + 0.5 * (size / 100) * sin(2 * PI * (speed * t + index * spread));
  r = color_a_r * (1 - mix) + color_b_r * mix;
  g = color_a_g * (1 - mix) + color_b_g * mix;
  b = color_a_b * (1 - mix) + color_b_b * mix;
}
