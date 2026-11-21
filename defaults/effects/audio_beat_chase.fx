#NAME Beat Chase
#DESCRIPTION en A chase that steps on every beat (or every n-th one). direction: 0 forward, 1 backward, 2 back and forth, 3 random.
#DESCRIPTION de Ein Lauflicht, das bei jedem Beat (oder jedem n-ten) weiterspringt. direction: 0 vorwärts, 1 rückwärts, 2 hin und her, 3 zufällig.
#TAGS advanced, chase, strobe
#CATEGORY dimmer
#RATE 40
#VAR every Slider 1 1 8 1
#VAR trail Slider 2 1 8 1
#VAR direction Slider 0 0 3 1
#VAR strobe Slider 0 0 25 1
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1
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
  dimmer = lerp(low, high, k * gate);
}
