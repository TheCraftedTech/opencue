#NAME Random Steps
#DESCRIPTION Springt zu zufälligen Helligkeiten. speed = Sprünge pro Sekunde.
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1

float level = 0;

loop() {
  if (tick % max(1, round(rate / speed)) == 0) {
    level = random(0, size);
  }
  dimmer = level;
}
