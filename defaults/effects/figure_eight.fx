#NAME Figure Eight
#DESCRIPTION en Pan and tilt draw a figure eight around the base position.
#DESCRIPTION de Pan und Tilt zeichnen eine Acht um die Grundposition.
#TAGS advanced, circle
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 40 0 50 1
#VAR spread Slider 0 0 1 0.05
#VAR center_pan Slider 50 0 100 1
#VAR center_tilt Slider 50 0 100 1

loop() {
  float a = 2 * PI * (speed * t + index * spread);
  pan = center_pan + size * sin(a);
  tilt = center_tilt + size * sin(2 * a) / 2;
}
