#NAME Hi-Hat Color Sparkle
#DESCRIPTION en On every hi-hat hit randomly chosen fixtures flash in a random colour (within the colour range).
#DESCRIPTION de Bei jedem Hi-Hat-Schlag blitzen zufällig ausgewählte Scheinwerfer in einer zufälligen Farbe (im Farbbereich).
#TAGS advanced, flash, random
#CATEGORY color
#RATE 40
#VAR density Slider 40 5 100 5
#VAR size Slider 100 0 100 1
#VAR hue_from Slider 0 0 360 1
#VAR hue_range Slider 360 10 360 1
#VAR saturation Slider 100 0 100 1

float lit = 0;
float last = 0;
float hue = 0;

loop() {
  if (a_hat > last + 0.3) {
    lit = random(0, 100) < density ? 1 : 0;
    hue = random();
  }
  last = a_hat;
  hsv(hue_from / 360 + hue_range / 360 * hue, saturation / 100, lit * a_hat * size / 100);
}
