#NAME Flicker
#DESCRIPTION en Random, soft flickering (candle, faulty lamp). speed = unrest.
#DESCRIPTION de Zufälliges, weiches Flackern (Kerze, defekte Lampe). speed = Unruhe.
#TAGS advanced, random
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1

float level = 0;
float target = 0;

loop() {
  if (tick % max(1, round(rate / (speed * 8))) == 0) {
    target = random(lerp(low, size, 0.3), size);
  }
  level += (target - level) * 0.35;
  dimmer = max(level, low);
}
