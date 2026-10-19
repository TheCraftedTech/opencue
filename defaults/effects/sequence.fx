#NAME Dimmer Sequence
#DESCRIPTION Ein Ablauf auf der Zeitleiste: einblenden, halten, ausblenden, Pause. length = Länge in Sekunden.
#CATEGORY dimmer
#RATE 40
#VAR size Slider 100 0 100 1
#VAR length Slider 8 2 30 1

loop() {
  float s = mod(elapsed, length);
  if (s < 2) {
    dimmer = map(s, 0, 2, 0, size);
  } else if (s < 5) {
    dimmer = size;
  } else if (s < 7) {
    dimmer = map(s, 5, 7, size, 0);
  } else {
    dimmer = 0;
  }
}
