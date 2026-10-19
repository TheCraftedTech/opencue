#NAME Pan Fan
#DESCRIPTION Die Scheinwerfer fächern sich in Pan auf und wieder zusammen. Nur Pan wird gesteuert, Tilt bleibt frei. size = größte Auffächerung.
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 40 0 50 1

loop() {
  float side = count > 1 ? index / (count - 1) - 0.5 : 0;
  float open = 0.5 + 0.5 * sin(2 * PI * speed * t);
  pan = 50 + side * 2 * size * open;
}
