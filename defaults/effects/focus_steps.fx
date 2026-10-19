#NAME Focus Steps
#DESCRIPTION Springt in Stufen durch den Fokusbereich. steps = Anzahl der Stufen.
#CATEGORY focus
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1
#VAR steps Slider 4 2 12 1

loop() {
  float n = floor(fract(speed * t) * steps);
  focus = lerp(low, high, n / (steps - 1));
}
