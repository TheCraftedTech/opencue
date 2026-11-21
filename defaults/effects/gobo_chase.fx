#NAME Gobo Chase
#DESCRIPTION en Every fixture shows a different gobo and they shift along.
#DESCRIPTION de Jeder Scheinwerfer zeigt ein anderes Gobo, und sie rücken weiter.
#TAGS advanced, chase
#CATEGORY gobo
#RATE 40
#VAR speed Slider 0.5 0.05 8 0.05
#VAR first Slider 0 0 20 1

loop() {
  float n = max(1, slots - first);
  gobo = slot(first + mod(index + floor(speed * t), n));
}
