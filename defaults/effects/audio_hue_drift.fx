#NAME Hue Drift
#DESCRIPTION en The colours drift through the colour range, one full cycle takes `beats` beats. pulse dips the brightness between the beats (0 = steady). Dark without a detected tempo.
#DESCRIPTION de Die Farben wandern durch den Farbbereich, ein voller Durchlauf dauert beats Beats. pulse senkt die Helligkeit zwischen den Beats (0 = gleichmäßig). Dunkel ohne erkanntes Tempo.
#TAGS advanced, rainbow, fade
#CATEGORY color
#RATE 40
#VAR beats Slider 16 1 64 1
#VAR spread Slider 0 0 1 0.05
#VAR hue_from Slider 0 0 360 1
#VAR hue_range Slider 360 10 360 1
#VAR saturation Slider 100 0 100 1
#VAR size Slider 100 0 100 1
#VAR pulse Slider 0 0 100 1
#INFO beats en Beats per cycle | How many beats one full colour cycle takes.
#INFO beats de Beats pro Durchlauf | Wie viele Beats ein voller Farbdurchlauf dauert.
#INFO pulse en Beat dip | How far the brightness dips between the beats (%, 0 = steady).
#INFO pulse de Beat-Einbruch | Wie weit die Helligkeit zwischen den Beats einbricht (%, 0 = gleichmäßig).

loop() {
  float h = fract((a_beat_count + a_beat_phase) / max(beats, 1) + index * spread);
  float k = hue_range >= 359.5 ? h : tri(h);
  float dip = 1 - pulse / 100;
  float v = a_bpm > 0 ? lerp(dip, 1, pow(1 - a_beat_phase, 2)) : 0;
  hsv(hue_from / 360 + hue_range / 360 * k, saturation / 100, v * size / 100);
}
