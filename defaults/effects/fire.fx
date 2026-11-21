#NAME Fire
#DESCRIPTION en Flickering fire colours. low = how low the flames sink (%).
#DESCRIPTION de Flackernde Feuerfarben. low = wie tief die Flammen sinken (%).
#TAGS advanced, random
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR low Slider 35 0 100 1

float level = 0.7;

loop() {
  if (tick % max(1, round(rate / (speed * 10))) == 0) {
    level += (random(low / 100, 1) - level) * 0.6;
  }
  r = 255 * level * size / 100;
  g = 90 * level * level * size / 100;
}
