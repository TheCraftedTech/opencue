#NAME Random Steps
#DESCRIPTION en A new random brightness between low and max at every step.
#DESCRIPTION de Bei jedem Schritt eine neue zufällige Helligkeit zwischen low und max.
#TAGS advanced, random, steps
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1

float level = 0;

loop() {
  if (tick % max(1, round(rate / speed)) == 0) {
    level = random(low, size);
  }
  dimmer = level;
}
