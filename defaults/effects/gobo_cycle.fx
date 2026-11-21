#NAME Gobo Cycle
#DESCRIPTION en Cycles through the gobos of wheel 1.
#DESCRIPTION de Schaltet durch die Gobos von Rad 1.
#TAGS basic, steps
#CATEGORY gobo
#RATE 40
#VAR speed Slider 0.5 0.05 8 0.05
#VAR first Slider 0 0 20 1
#VAR spread Slider 0 0 1 0.05

loop() {
  float n = max(1, slots - first);
  gobo = slot(first + mod(floor(speed * t + index * spread * n), n));
}
