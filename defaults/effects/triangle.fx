#NAME Triangle Wave
#DESCRIPTION en A linear triangle wave of brightness.
#DESCRIPTION de Eine lineare Dreieckswelle der Helligkeit.
#TAGS advanced, wave
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  dimmer = lerp(low, size, tri(speed * t + index * spread));
}
