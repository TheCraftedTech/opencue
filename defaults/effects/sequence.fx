#NAME Dimmer Sequence
#DESCRIPTION en A timed sequence from the start of the effect: 2 s up, 3 s hold, 2 s down, then rest. length = total length in seconds.
#DESCRIPTION de Eine Sequenz ab dem Start des Effekts: 2 s hoch, 3 s halten, 2 s herunter, dann Pause. length = Gesamtlänge in Sekunden.
#TAGS advanced, sequence
#CATEGORY dimmer
#RATE 40
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1
#VAR length Slider 8 2 30 1

loop() {
  float s = mod(elapsed, length);
  if (s < 2) {
    dimmer = map(s, 0, 2, low, size);
  } else if (s < 5) {
    dimmer = size;
  } else if (s < 7) {
    dimmer = map(s, 5, 7, size, low);
  } else {
    dimmer = low;
  }
}
