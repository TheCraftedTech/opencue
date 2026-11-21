#NAME Two-Color Fade
#DESCRIPTION en Fades back and forth between two colours. size = how far it swings (100 % = fully from A to B), bright = brightness.
#DESCRIPTION de Blendet zwischen zwei Farben hin und her. size = wie weit es ausschlägt (100 % = ganz von A nach B), bright = Helligkeit.
#TAGS basic, fade, wave
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05
#VAR bright Slider 100 0 100 1
#VAR color_a ColorPicker #ff0000
#VAR color_b ColorPicker #0000ff
#INFO size en Fade depth | How far the fade swings between the two colours (100 % = fully).
#INFO size de Überblendtiefe | Wie weit die Überblendung zwischen den Farben ausschlägt (100 % = ganz).
#INFO bright en Brightness | Brightness of the colours (100 % = full).
#INFO bright de Helligkeit | Helligkeit der Farben (100 % = voll).

loop() {
  float mix = 0.5 + 0.5 * (size / 100) * sin(2 * PI * (speed * t + index * spread));
  float q = bright / 100;
  r = (color_a_r * (1 - mix) + color_b_r * mix) * q;
  g = (color_a_g * (1 - mix) + color_b_g * mix) * q;
  b = (color_a_b * (1 - mix) + color_b_b * mix) * q;
}
