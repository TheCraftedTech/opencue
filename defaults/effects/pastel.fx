#NAME Pastel Colors
#DESCRIPTION en Soft pastel colours that slowly change. saturation = how pale, hue_from / hue_range = which colours.
#DESCRIPTION de Weiche Pastellfarben, die sich langsam ändern. saturation = wie blass, hue_from / hue_range = welche Farben.
#TAGS advanced, rainbow, fade
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05
#VAR hue_from Slider 0 0 360 1
#VAR hue_range Slider 360 10 360 1
#VAR saturation Slider 40 0 100 1

loop() {
  float h = fract(speed * t + index * spread);
  float k = hue_range >= 359.5 ? h : tri(h);
  float hue = hue_from / 360 + hue_range / 360 * k;
  hsv(hue, saturation / 100, size / 100);
}
