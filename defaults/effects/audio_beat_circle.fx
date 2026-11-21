#NAME Beat Circle
#DESCRIPTION en The heads travel a circle in time with the music: one turn takes `beats` beats. Without a detected tempo they stay at the base position.
#DESCRIPTION de Die Köpfe fahren im Takt der Musik einen Kreis: eine Umdrehung dauert beats Beats. Ohne erkanntes Tempo bleiben sie auf der Grundposition.
#TAGS advanced, circle
#CATEGORY position
#RATE 40
#VAR beats Slider 4 1 32 1
#VAR size Slider 60 0 100 1
#VAR spread Slider 0 0 1 0.05
#VAR direction Slider 1 0 1 1
#VAR center_pan Slider 50 0 100 1
#VAR center_tilt Slider 50 0 100 1

loop() {
  float dir = direction > 0.5 ? 1 : -1;
  float a = 2 * PI * (dir * (a_beat_count + a_beat_phase) / max(beats, 1) + index * spread);
  float on = a_bpm > 0 ? 1 : 0;
  pan = center_pan + on * 50 * (size / 100) * cos(a);
  tilt = center_tilt + on * 50 * (size / 100) * sin(a);
}
