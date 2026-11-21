#NAME Random Color
#DESCRIPTION en A new random colour at every step, within the colour range.
#DESCRIPTION de Bei jedem Schritt eine neue zufällige Farbe innerhalb des Farbbereichs.
#TAGS basic, random, steps
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR hue_from Slider 0 0 360 1
#VAR hue_range Slider 360 10 360 1
#VAR saturation Slider 100 0 100 1

float hue = 0;

loop() {
  if (tick % max(1, round(rate / speed)) == 0) {
    hue = random();
  }
  hsv(hue_from / 360 + hue_range / 360 * hue, saturation / 100, size / 100);
}
