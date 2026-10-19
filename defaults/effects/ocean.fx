#NAME Ocean Blues
#DESCRIPTION Wogen in Blau und Türkis. spread verschiebt die Wellen zwischen den Scheinwerfern.
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
