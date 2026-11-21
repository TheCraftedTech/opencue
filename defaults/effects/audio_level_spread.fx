#NAME Level Spread
#DESCRIPTION en The louder the music, the wider the fixtures fan out (symmetrically around the base position).
#DESCRIPTION de Je lauter die Musik, desto weiter fächern die Scheinwerfer auf (symmetrisch um die Grundposition).
#TAGS advanced, spectrum
#CATEGORY position
#RATE 40
#VAR gain Slider 1 0.2 3 0.05
#VAR size Slider 40 0 50 1
#VAR center_pan Slider 50 0 100 1

loop() {
  float side = count > 1 ? index / (count - 1) - 0.5 : 0;
  pan = center_pan + side * 2 * size * constrain(a_level * gain, 0, 1);
}
