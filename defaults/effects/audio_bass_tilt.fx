#NAME Bass Tilt
#DESCRIPTION en The tilt follows the bass: quiet = down, strong bass = up (around the base position). Without audio the heads stay at the base position.
#DESCRIPTION de Der Tilt folgt dem Bass: leise = nach unten, kräftiger Bass = nach oben (um die Grundposition). Ohne Audio bleiben die Köpfe auf der Grundposition.
#TAGS advanced, spectrum
#CATEGORY position
#RATE 40
#VAR gain Slider 1 0.2 3 0.05
#VAR size Slider 30 0 50 1
#VAR center_tilt Slider 50 0 100 1

loop() {
  float k = a_active > 0.5 ? 2 * constrain(a_bass * gain, 0, 1) - 1 : 0;
  tilt = center_tilt + size * k;
}
