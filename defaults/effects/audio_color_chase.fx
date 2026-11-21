#NAME Beat Color Chase
#DESCRIPTION en A coloured light (A) runs across a background colour (B), one step per beat (or every n-th). direction: 0 forward, 1 backward, 2 back and forth, 3 random.
#DESCRIPTION de Ein farbiges Licht (A) läuft über eine Hintergrundfarbe (B), ein Schritt pro Beat (oder jedem n-ten). direction: 0 vorwärts, 1 rückwärts, 2 hin und her, 3 zufällig.
#TAGS advanced, chase, strobe
#CATEGORY color
#RATE 40
#VAR every Slider 1 1 8 1
#VAR trail Slider 2 1 8 1
#VAR direction Slider 0 0 3 1
#VAR strobe Slider 0 0 25 1
#VAR size Slider 100 0 100 1
#VAR color_a ColorPicker #ff0040
#VAR color_b ColorPicker #100020
#INFO direction en Direction | 0 = forward, 1 = backward, 2 = back and forth, 3 = random.
#INFO direction de Richtung | 0 = vorwärts, 1 = rückwärts, 2 = hin und her, 3 = zufällig.

loop() {
  float n = max(count, 1);
  float tr = max(trail, 1);
  float s = floor(a_beat_count / max(every, 1));
  float pos = mod(s, n);
  if (direction == 1) { pos = n - 1 - pos; }
  if (direction == 2) {
    float m = max(2 * n - 2, 1);
    float u = mod(s, m);
    pos = u < n ? u : m - u;
  }
  if (direction == 3) { pos = mod(floor(fract(sin(s * 12.9898) * 43758.5453) * n), n); }
  float k = 0;
  if (a_bpm > 0) {
    if (direction == 0) { k = pow(max(0, 1 - mod(pos - index + n, n) / tr), 2); }
    else if (direction == 1) { k = pow(max(0, 1 - mod(index - pos + n, n) / tr), 2); }
    else { k = pow(max(0, 1 - abs(index - pos) / tr), 2); }
  }
  float gate = strobe > 0 ? square(strobe * t) : 1;
  float m = k * gate;
  float q = size / 100;
  r = lerp(color_b_r, color_a_r, m) * q;
  g = lerp(color_b_g, color_a_g, m) * q;
  b = lerp(color_b_b, color_a_b, m) * q;
}
