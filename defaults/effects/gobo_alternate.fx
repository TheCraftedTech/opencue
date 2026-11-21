#NAME Gobo Alternate
#DESCRIPTION en Alternates between two gobos.
#DESCRIPTION de Wechselt zwischen zwei Gobos.
#TAGS advanced, toggle
#CATEGORY gobo
#RATE 40
#VAR speed Slider 0.5 0.05 8 0.05
#VAR slot_a Slider 0 0 20 1
#VAR slot_b Slider 1 0 20 1

loop() {
  gobo = fract(speed * t) < 0.5 ? slot(slot_a) : slot(slot_b);
}
