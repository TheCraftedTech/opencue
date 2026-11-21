#NAME Rainbow Dot Chase
#DESCRIPTION en A coloured dot runs across the fixtures and changes its colour. hue_from / hue_range limit the colours (a narrow range swings back and forth).
#DESCRIPTION de Ein farbiger Punkt wandert über die Scheinwerfer und wechselt seine Farbe. hue_from / hue_range begrenzen die Farben (ein schmaler Bereich pendelt hin und her).
#TAGS advanced, chase, rainbow
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR width Slider 1 0.5 8 0.5
#VAR hue_from Slider 0 0 360 1
#VAR hue_range Slider 360 10 360 1
#VAR saturation Slider 100 0 100 1

loop() {
  float pos = fract(speed * t) * count;
  float d = abs(index - pos);
  if (d > count / 2) d = count - d;
  if (d < width) {
    float h = fract(speed * t * 0.5);
    float k = hue_range >= 359.5 ? h : tri(h);
    float hue = hue_from / 360 + hue_range / 360 * k;
    hsv(hue, saturation / 100, size / 100);
  }
}
