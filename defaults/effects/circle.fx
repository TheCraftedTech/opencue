#NAME Pan/Tilt Circle
#DESCRIPTION en Pan and tilt travel a circle around the base position. speed = turns per second, spread = offset between the fixtures.
#DESCRIPTION de Pan und Tilt fahren einen Kreis um die Grundposition. speed = Umdrehungen pro Sekunde, spread = Versatz zwischen den Scheinwerfern.
#TAGS basic, circle
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05
#VAR center_pan Slider 50 0 100 1
#VAR center_tilt Slider 50 0 100 1

loop() {
  float c = 2 * PI * (speed * t + index * spread);
  pan = center_pan + 50 * (size / 100) * cos(c);
  tilt = center_tilt + 50 * (size / 100) * sin(c);
}
