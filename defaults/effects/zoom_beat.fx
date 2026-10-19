#NAME Zoom Beat
#DESCRIPTION Schlagartig auf, dann langsam zurück - wie ein Beat. speed = Schläge pro Sekunde.
#CATEGORY zoom
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  float p = fract(speed * t + index * spread);
  zoom = lerp(low, high, pow(1 - p, 3));
}
