#NAME Pan/Tilt Wave
#DESCRIPTION en Pan and tilt move in a wave, shifted against each other.
#DESCRIPTION de Pan und Tilt bewegen sich in einer Welle, gegeneinander verschoben.
#TAGS advanced, wave, circle
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05
#VAR center_pan Slider 50 0 100 1
#VAR center_tilt Slider 50 0 100 1

loop() {
  float c = 2 * PI * (speed * t + index * spread);
  pan = center_pan + 50 * (size / 100) * sin(c);
  tilt = center_tilt + 50 * (size / 100) * sin(c + PI / 2);
}
