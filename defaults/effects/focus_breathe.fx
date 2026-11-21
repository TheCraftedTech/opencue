#NAME Focus Breathe
#DESCRIPTION en The focus breathes softly between low and high.
#DESCRIPTION de Der Fokus atmet weich zwischen low und high.
#TAGS advanced, wave
#CATEGORY focus
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  float k = 0.5 + 0.5 * sin(2 * PI * (speed * t + index * spread));
  focus = lerp(low, high, k);
}
