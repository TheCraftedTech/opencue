#NAME Fire
#DESCRIPTION Flackerndes Feuer in Orange und Rot. speed = Unruhe.
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1

float level = 0.7;

loop() {
  if (tick % max(1, round(rate / (speed * 10))) == 0) {
    level += (random(0.35, 1) - level) * 0.6;
  }
  r = 255 * level * size / 100;
  g = 90 * level * level * size / 100;
}
