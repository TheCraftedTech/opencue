#NAME Beat Pulse
#DESCRIPTION en The brightness pulses in time with the music: bright on the beat, then fading softly. Without a detected tempo it stays at low.
#DESCRIPTION de Die Helligkeit pulsiert im Takt der Musik: hell auf dem Beat, dann weich abklingend. Ohne erkanntes Tempo bleibt es auf low.
#TAGS basic, pulse, strobe, toggle
#CATEGORY dimmer
#RATE 40
#VAR softness Slider 3 0.5 8 0.1
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1
#VAR strobe Slider 0 0 25 1
#VAR mode Slider 0 0 1 1
#INFO mode en Pattern | 0 = all together, 1 = even/odd alternating on every beat.
#INFO mode de Muster | 0 = alle gemeinsam, 1 = gerade/ungerade im Wechsel bei jedem Beat.

loop() {
  float k = a_bpm > 0 ? pow(1 - a_beat_phase, softness) : 0;
  float on = mode == 1 ? (mod(index + a_beat_count, 2) == 0 ? 1 : 0) : 1;
  float gate = strobe > 0 ? square(strobe * t) : 1;
  dimmer = lerp(low, high, k * on * gate);
}
