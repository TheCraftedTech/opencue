#NAME Warm / Cool Fade
#DESCRIPTION en Slowly fades between a warm and a cool white.
#DESCRIPTION de Blendet langsam zwischen einem warmen und einem kalten Weiß.
#TAGS advanced, fade, wave
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR spread Slider 0 0 1 0.05
#VAR size Slider 100 0 100 1
#VAR warm ColorPicker #ffb464
#VAR cool ColorPicker #b4c8ff

loop() {
  float k = 0.5 + 0.5 * sin(2 * PI * (speed * t * 0.5 + index * spread));
  float q = size / 100;
  r = lerp(warm_r, cool_r, k) * q;
  g = lerp(warm_g, cool_g, k) * q;
  b = lerp(warm_b, cool_b, k) * q;
}
