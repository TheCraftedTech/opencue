#NAME Beat Fan
#DESCRIPTION en The fixtures fan out and close in time with the music. mode 0: smooth, one open/close takes `beats` beats; mode 1: snap open on every beat and close slowly.
#DESCRIPTION de Die Scheinwerfer fächern im Takt der Musik auf und zu. mode 0: weich, ein Auf/Zu dauert beats Beats; mode 1: auf jedem Beat aufspringen und langsam zufahren.
#TAGS advanced, sweep, toggle
#CATEGORY position
#RATE 40
#VAR beats Slider 2 1 16 1
#VAR mode Slider 0 0 1 1
#VAR size Slider 40 0 50 1
#VAR center_pan Slider 50 0 100 1
#INFO mode en Movement | 0 = smooth open/close, 1 = snap open on every beat.
#INFO mode de Bewegung | 0 = weich auf/zu, 1 = auf jedem Beat aufspringen.

loop() {
  float side = count > 1 ? index / (count - 1) - 0.5 : 0;
  float open = mode == 1 ? pow(1 - a_beat_phase, 2) : 0.5 + 0.5 * sin(2 * PI * (a_beat_count + a_beat_phase) / max(beats, 1));
  float on = a_bpm > 0 ? 1 : 0;
  pan = center_pan + on * side * 2 * size * open;
}
