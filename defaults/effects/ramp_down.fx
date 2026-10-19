#NAME Ramp Down
#DESCRIPTION Springt auf Volllicht und blendet langsam ab (Sägezahn abwärts).
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  dimmer = size * (1 - fract(speed * t + index * spread));
}
