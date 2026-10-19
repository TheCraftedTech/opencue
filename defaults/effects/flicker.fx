#NAME Flicker
#DESCRIPTION Zufälliges, weiches Flackern (Kerze, defekte Lampe). speed = Unruhe.
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1

float level = 0;
float target = 0;

loop() {
  if (tick % max(1, round(rate / (speed * 8))) == 0) {
    target = random(size * 0.3, size);
  }
  level += (target - level) * 0.35;
  dimmer = level;
}
