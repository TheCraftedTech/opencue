#NAME Ramp Up
#DESCRIPTION en Rising ramp: dark, fading up to bright, then jumping back.
#DESCRIPTION de Steigende Rampe: dunkel, dann hochblenden, dann zurückspringen.
#TAGS advanced, ramp
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  dimmer = lerp(low, size, fract(speed * t + index * spread));
}
