#NAME Breathe
#DESCRIPTION Weiches Atmen: langsam auf und ab, an den Enden besonders sanft.
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  float s = 0.5 - 0.5 * cos(2 * PI * (speed * t + index * spread));
  dimmer = size * s * s;
}
