#NAME Beat Strobe
#DESCRIPTION en Strobe in time with the music: mult flashes per beat, locked to the tempo. Without a detected tempo it stays at low.
#DESCRIPTION de Stroboskop im Takt der Musik: mult Blitze pro Beat, phasenstarr zum Tempo. Ohne erkanntes Tempo bleibt es auf low.
#TAGS advanced, strobe, flash, toggle
#CATEGORY dimmer
#RATE 40
#VAR mult Slider 4 1 16 1
#VAR duty Slider 30 5 90 5
#VAR mode Slider 0 0 2 1
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1
#INFO mode en Pattern | 0 = always, 1 = only as a burst after each bass drum, 2 = even/odd fixtures alternating.
#INFO mode de Muster | 0 = immer, 1 = nur als Salve nach jeder Bassdrum, 2 = gerade/ungerade Scheinwerfer im Wechsel.

loop() {
  float p = (a_beat_count + a_beat_phase) * mult;
  float on = fract(p) < duty / 100 ? 1 : 0;
  if (mode == 1) { on = on * (a_kick > 0.15 ? 1 : 0); }
  if (mode == 2) { on = on * (mod(floor(p) + index, 2) == 0 ? 1 : 0); }
  dimmer = a_bpm > 0 ? lerp(low, size, on) : low;
}
