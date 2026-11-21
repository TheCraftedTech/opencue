#NAME Gobo Spin Sweep
#DESCRIPTION en One gobo whose rotation sweeps between low and high.
#DESCRIPTION de Ein Gobo, dessen Rotation zwischen low und high pendelt.
#TAGS advanced, sweep
#CATEGORY gobo
#RATE 40
#VAR speed Slider 0.2 0.05 2 0.05
#VAR first Slider 1 0 20 1
#VAR low Slider 55 0 100 1
#VAR high Slider 80 0 100 1

loop() {
  gobo = slot(first);
  gobo_spin = lerp(low, high, tri(speed * t + index * 0.1));
}
