#NAME Color Runner
#DESCRIPTION en A colour (B) runs across a background colour (A). soft = softness of the edge, bounce = back and forth.
#DESCRIPTION de Eine Farbe (B) läuft über eine Hintergrundfarbe (A). soft = Weichheit der Kante, bounce = hin und her.
#TAGS advanced, chase
#CATEGORY color
#RATE 40
#VAR speed Slider 0.5 0.05 4 0.05
#VAR width Slider 1.5 0.5 8 0.5
#VAR soft Slider 0.5 0 1 0.05
#VAR direction Slider 1 0 1 1
#VAR bounce Slider 0 0 1 1
#VAR size Slider 100 0 100 1
#VAR color_a ColorPicker #ffcc00
#VAR color_b ColorPicker #ff0000

loop() {
  float run = bounce > 0.5 ? tri(speed * t * 0.5) : fract(speed * t);
  if (direction < 0.5) run = 1 - run;
  float span = bounce > 0.5 ? max(count - 1, 0) : count;
  float pos = run * span;
  float d = abs(index - pos);
  if (bounce < 0.5 && d > count / 2) d = count - d;
  float k = 1 - smoothstep(width * (1 - soft), width + 0.001, d);
  float q = size / 100;
  r = lerp(color_a_r, color_b_r, k) * q;
  g = lerp(color_a_g, color_b_g, k) * q;
  b = lerp(color_a_b, color_b_b, k) * q;
}
