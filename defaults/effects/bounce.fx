#NAME Tilt Bounce
#DESCRIPTION en The heads bounce in tilt like a ball.
#DESCRIPTION de Die Köpfe springen im Tilt wie ein Ball.
#TAGS advanced, bounce
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 30 0 50 1
#VAR spread Slider 0 0 1 0.05
#VAR center_tilt Slider 50 0 100 1

loop() {
  float p = fract(speed * t + index * spread);
  tilt = center_tilt - size + 2 * size * (1 - pow(1 - p, 2));
}
