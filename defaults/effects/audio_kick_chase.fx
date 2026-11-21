#NAME Kick Chase
#DESCRIPTION en A chase that steps on every bass drum hit (instead of the beat). direction: 0 forward, 1 backward.
#DESCRIPTION de Ein Lauflicht, das bei jedem Bassdrum-Schlag (statt im Beat) weiterspringt. direction: 0 vorwärts, 1 rückwärts.
#TAGS advanced, chase, strobe
#CATEGORY dimmer
#RATE 40
#VAR trail Slider 2 1 8 1
#VAR direction Slider 0 0 1 1
#VAR strobe Slider 0 0 25 1
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1
#INFO direction en Direction | 0 = forward, 1 = backward.
#INFO direction de Richtung | 0 = vorwärts, 1 = rückwärts.

float step = 0;
float last = 0;

loop() {
  if (a_kick > last + 0.3) { step += 1; }
  last = a_kick;
  float n = max(count, 1);
  float pos = mod(step, n);
  if (direction == 1) { pos = n - 1 - pos; }
  float k = direction == 1 ? pow(max(0, 1 - mod(index - pos + n, n) / max(trail, 1)), 2) : pow(max(0, 1 - mod(pos - index + n, n) / max(trail, 1)), 2);
  float gate = strobe > 0 ? square(strobe * t) : 1;
  dimmer = lerp(low, high, step > 0 ? k * gate : 0);
}
