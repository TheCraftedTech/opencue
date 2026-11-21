#NAME Police Red/Blue
#DESCRIPTION en Two colours (default red and blue) alternate, even and odd fixtures in opposite phase.
#DESCRIPTION de Zwei Farben (Standard Rot und Blau) wechseln sich ab, gerade und ungerade Scheinwerfer gegenläufig.
#TAGS advanced, toggle, blink
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR color_a ColorPicker #ff0000
#VAR color_b ColorPicker #0000ff

loop() {
  bool flip = fract(speed * t) < 0.5;
  bool first = (mod(index, 2) == 0) == flip;
  float q = size / 100;
  r = (first ? color_a_r : color_b_r) * q;
  g = (first ? color_a_g : color_b_g) * q;
  b = (first ? color_a_b : color_b_b) * q;
}
