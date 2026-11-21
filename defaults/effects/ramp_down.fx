#NAME Ramp Down
#DESCRIPTION en Falling ramp: bright, fading to dark, then jumping back.
#DESCRIPTION de Fallende Rampe: hell, dann ausblenden, dann zurückspringen.
#TAGS advanced, ramp
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  dimmer = lerp(low, size, 1 - fract(speed * t + index * spread));
}
