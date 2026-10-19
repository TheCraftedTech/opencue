#NAME Zoom Ramp
#DESCRIPTION Fährt langsam von low nach high und springt zurück.
#CATEGORY zoom
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  zoom = lerp(low, high, fract(speed * t + index * spread));
}
