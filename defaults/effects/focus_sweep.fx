#NAME Focus Sweep
#DESCRIPTION Der Fokus fährt gleichmäßig zwischen low und high hin und her.
#CATEGORY focus
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  focus = lerp(low, high, tri(speed * t + index * spread));
}
