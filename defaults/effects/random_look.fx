#NAME Random Look
#DESCRIPTION en The heads look to new random positions around the base position and glide there.
#DESCRIPTION de Die Köpfe schauen zu neuen zufälligen Positionen um die Grundposition und gleiten dorthin.
#TAGS advanced, random
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 40 0 50 1
#VAR center_pan Slider 50 0 100 1
#VAR center_tilt Slider 50 0 100 1

float px = -1;
float py = -1;
float tx = 50;
float ty = 50;

loop() {
  if (px < 0) {
    px = center_pan;
    py = center_tilt;
    tx = px;
    ty = py;
  }
  if (tick % max(1, round(rate / speed)) == 0) {
    tx = center_pan + random(-size, size);
    ty = center_tilt + random(-size, size);
  }
  px += (tx - px) * 0.12;
  py += (ty - py) * 0.12;
  pan = px;
  tilt = py;
}
