#NAME Bass Focus
#DESCRIPTION en The focus follows the bass of the music.
#DESCRIPTION de Der Fokus folgt dem Bass der Musik.
#TAGS advanced, spectrum
#CATEGORY focus
#RATE 40
#VAR gain Slider 1 0.2 3 0.05
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1

loop() {
  focus = lerp(low, high, constrain(a_bass * gain, 0, 1));
}
