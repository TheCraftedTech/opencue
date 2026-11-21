#NAME Radar
#DESCRIPTION en The heads sweep back and forth in pan like a radar (linear, constant speed).
#DESCRIPTION de Die Köpfe schwenken im Pan hin und her wie ein Radar (linear, gleichmäßige Geschwindigkeit).
#TAGS advanced, sweep
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 40 0 50 1
#VAR spread Slider 0 0 1 0.05
#VAR center_pan Slider 50 0 100 1

loop() {
  pan = center_pan + size * (2 * tri(speed * t * 0.5 + index * spread) - 1);
}
