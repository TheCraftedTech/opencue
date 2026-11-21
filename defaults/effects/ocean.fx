#NAME Ocean Blues
#DESCRIPTION en Slow waves in blue and turquoise.
#DESCRIPTION de Langsame Wellen in Blau und Türkis.
#TAGS advanced, wave
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0.15 0 1 0.05

loop() {
  float w = 0.5 + 0.5 * sin(2 * PI * (speed * t * 0.5 + index * spread));
  g = (60 + 150 * w) * size / 100;
  b = (190 + 65 * w) * size / 100;
}
