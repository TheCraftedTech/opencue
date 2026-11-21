#NAME Spectrum Color
#DESCRIPTION en The colour mixes from the music: bass = red, mids = green, highs = blue.
#DESCRIPTION de Die Farbe mischt sich aus der Musik: Bass = Rot, Mitten = Grün, Höhen = Blau.
#TAGS advanced, spectrum
#CATEGORY color
#RATE 40
#VAR gain Slider 1 0.2 3 0.05
#VAR size Slider 100 0 100 1

loop() {
  float q = size / 100;
  r = 255 * constrain(a_bass * gain, 0, 1) * q;
  g = 255 * constrain(a_mid * gain, 0, 1) * q;
  b = 255 * constrain(a_high * gain, 0, 1) * q;
}
