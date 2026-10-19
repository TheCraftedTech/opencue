#NAME Gobo Random
#DESCRIPTION Wechselt zu zufälligen Gobos. speed = Wechsel pro Sekunde.
#CATEGORY gobo
#RATE 40
#VAR speed Slider 0.5 0.05 8 0.05
#VAR first Slider 0 0 20 1

float pick = 0;

loop() {
  if (tick % max(1, round(rate / speed)) == 0) {
    pick = first + floor(random(0, max(1, slots - first)));
  }
  gobo = slot(pick);
}
