#NAME Pan Fan
#DESCRIPTION en The fixtures fan out and close again, spread symmetrically around the base position.
#DESCRIPTION de Die Scheinwerfer fächern auf und wieder zu, symmetrisch um die Grundposition.
#TAGS basic, sweep
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 40 0 50 1
#VAR center_pan Slider 50 0 100 1

loop() {
  float side = count > 1 ? index / (count - 1) - 0.5 : 0;
  float open = 0.5 + 0.5 * sin(2 * PI * speed * t);
  pan = center_pan + side * 2 * size * open;
}
