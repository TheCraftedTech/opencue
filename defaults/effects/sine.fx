#NAME Sine Wave
#DESCRIPTION en A smooth sine wave of brightness.
#DESCRIPTION de Eine weiche Sinuswelle der Helligkeit.
#TAGS basic, wave
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  dimmer = lerp(low, size, 0.5 + 0.5 * sin(2 * PI * (speed * t + index * spread)));
}
