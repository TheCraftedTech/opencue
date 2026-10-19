#NAME Focus Pulse
#DESCRIPTION Schlagartig scharf, dann langsam unscharf. speed = Schläge pro Sekunde.
#CATEGORY focus
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  float p = fract(speed * t + index * spread);
  focus = lerp(low, high, pow(1 - p, 3));
}
