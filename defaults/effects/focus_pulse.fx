#NAME Focus Pulse
#DESCRIPTION en A hard focus pulse: sharp at the beat, then drifting away.
#DESCRIPTION de Ein harter Fokus-Puls: scharf auf dem Beat, dann wegdriftend.
#TAGS advanced, pulse
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
