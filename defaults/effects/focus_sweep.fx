#NAME Focus Sweep
#DESCRIPTION en The focus sweeps back and forth between low and high.
#DESCRIPTION de Der Fokus fährt zwischen low und high hin und her.
#TAGS basic, sweep
#CATEGORY focus
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  focus = lerp(low, high, tri(speed * t + index * spread));
}
