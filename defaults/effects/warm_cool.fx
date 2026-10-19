#NAME Warm / Cool Fade
#DESCRIPTION Weiche Überblendung zwischen warmem und kaltem Weiß.
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR spread Slider 0 0 1 0.05
#VAR warm ColorPicker #ffb464
#VAR cool ColorPicker #b4c8ff

loop() {
  float k = 0.5 + 0.5 * sin(2 * PI * (speed * t * 0.5 + index * spread));
  r = lerp(warm_r, cool_r, k);
  g = lerp(warm_g, cool_g, k);
  b = lerp(warm_b, cool_b, k);
}
