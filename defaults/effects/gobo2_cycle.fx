#NAME Gobo Wheel 2 Cycle
#DESCRIPTION en Cycles through the gobos of wheel 2.
#DESCRIPTION de Schaltet durch die Gobos von Rad 2.
#TAGS advanced, steps
#CATEGORY gobo
#RATE 40
#VAR speed Slider 0.5 0.05 8 0.05
#VAR first Slider 0 0 20 1

loop() {
  float n = max(1, slots2 - first);
  gobo2 = slot(first + mod(floor(speed * t), n), 2);
}
