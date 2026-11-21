#NAME Blink
#DESCRIPTION en Even on and off. speed = blinks per second, low = brightness while off.
#DESCRIPTION de Gleichmäßig an und aus. speed = Blinks pro Sekunde, low = Helligkeit im Aus-Zustand.
#TAGS basic, blink
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  float p = fract(speed * t + index * spread);
  dimmer = p < 0.5 ? size : low;
}
