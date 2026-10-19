#NAME Pan/Tilt Circle
#DESCRIPTION Pan/Tilt fahren einen Kreis. speed = Umdrehungen pro Sekunde, size = Groesse, spread = Versatz zwischen den Scheinwerfern.
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  c = 2 * PI * (speed * t + index * spread);
  pan = 50 + 50 * (size / 100) * cos(c);
  tilt = 50 + 50 * (size / 100) * sin(c);
}
