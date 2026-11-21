#NAME Beat Gobo Change
#DESCRIPTION en The gobo changes on every beat (or every n-th one). mode: 0 steps through the gobos, 1 random. Without a detected tempo it shows the first gobo.
#DESCRIPTION de Das Gobo wechselt bei jedem Beat (oder jedem n-ten). mode: 0 schaltet der Reihe nach, 1 zufällig. Ohne erkanntes Tempo zeigt es das erste Gobo.
#TAGS advanced, steps, toggle
#CATEGORY gobo
#RATE 40
#VAR every Slider 1 1 16 1
#VAR first Slider 0 0 20 1
#VAR mode Slider 0 0 1 1
#INFO mode en Order | 0 = one after the other, 1 = random.
#INFO mode de Reihenfolge | 0 = der Reihe nach, 1 = zufällig.

loop() {
  float n = max(1, slots - first);
  float s = floor(a_beat_count / max(every, 1));
  float i = mode == 1 ? floor(fract(sin(s * 12.9898) * 43758.5453) * n) : mod(s, n);
  gobo = slot(first + (a_bpm > 0 ? mod(i + index, n) : 0));
}
