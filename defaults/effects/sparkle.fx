#NAME Random Sparkle
#DESCRIPTION en Single fixtures flash up at random and fade out. speed = flashes per second and fixture.
#DESCRIPTION de Einzelne Scheinwerfer blitzen zufällig auf und klingen ab. speed = Blitze pro Sekunde und Scheinwerfer.
#TAGS advanced, random, flash
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1
#VAR fade Slider 0.4 0.05 3 0.05

float level = 0;

loop() {
  if (random() < speed * dt) {
    level = size;
  }
  level = max(low, level - dt * (size - low) / fade);
  dimmer = level;
}
