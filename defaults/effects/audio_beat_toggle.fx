#NAME Beat Toggle
#DESCRIPTION en Switches between two groups on every beat (or every n-th one), hard or cross-faded (soft). Without a detected tempo it stays at low.
#DESCRIPTION de Schaltet bei jedem Beat (oder jedem n-ten) zwischen zwei Gruppen um, hart oder überblendet (soft). Ohne erkanntes Tempo bleibt es auf low.
#TAGS advanced, toggle, alternate
#CATEGORY dimmer
#RATE 40
#VAR mode Slider 0 0 2 1
#VAR every Slider 1 1 8 1
#VAR soft Slider 0 0 1 0.05
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1
#INFO mode en Groups | 0 = even/odd fixtures, 1 = first/second half, 2 = all together on/off.
#INFO mode de Gruppen | 0 = gerade/ungerade Scheinwerfer, 1 = erste/zweite Hälfte, 2 = alle gemeinsam an/aus.

loop() {
  float e = max(every, 1);
  float step = floor(a_beat_count / e);
  float grp = 0;
  if (mode == 0) { grp = mod(index, 2); }
  if (mode == 1) { grp = index >= count / 2 ? 1 : 0; }
  float cur = mod(step + grp, 2) == 0 ? 1 : 0;
  float prev = mod(step - 1 + grp + 2, 2) == 0 ? 1 : 0;
  float within = (mod(a_beat_count, e) + a_beat_phase) / e;
  float f = soft > 0 ? smoothstep(0, soft, within) : 1;
  dimmer = a_bpm > 0 ? lerp(low, high, lerp(prev, cur, f)) : low;
}
