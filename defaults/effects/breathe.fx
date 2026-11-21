#NAME Breathe
#DESCRIPTION en Slow, soft breathing between low and max brightness.
#DESCRIPTION de Langsames, weiches Atmen zwischen minimaler und maximaler Helligkeit.
#TAGS basic, wave, fade
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  float s = 0.5 - 0.5 * cos(2 * PI * (speed * t + index * spread));
  dimmer = lerp(low, size, s * s);
}
