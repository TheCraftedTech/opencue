#NAME Pan/Tilt Sway
#DESCRIPTION en The heads move in time with the music. mode: 0 soft swing (one swing = beats beats), 1 snap left/right on every beat, 2 like 1 but neighbours opposite. bounce = nodding (tilt).
#DESCRIPTION de Die Köpfe bewegen sich im Takt der Musik. mode: 0 weiches Schwingen (ein Schwung = beats Beats), 1 bei jedem Beat links/rechts springen, 2 wie 1, aber Nachbarn gegenläufig. bounce = Nicken (Tilt).
#TAGS advanced, toggle
#CATEGORY position
#RATE 40
#VAR mode Slider 0 0 2 1
#VAR beats Slider 4 1 16 1
#VAR size Slider 60 0 100 1
#VAR spread Slider 0 0 1 0.05
#VAR bounce Slider 20 0 100 1
#VAR center_pan Slider 50 0 100 1
#VAR center_tilt Slider 50 0 100 1
#INFO mode en Movement | 0 = soft swing, 1 = snap left/right on every beat, 2 = snap, neighbours opposite.
#INFO mode de Bewegung | 0 = weiches Schwingen, 1 = bei jedem Beat links/rechts springen, 2 = springen, Nachbarn gegenläufig.
#INFO bounce en Nodding | How far the heads nod in tilt (%).
#INFO bounce de Nicken | Wie weit die Köpfe im Tilt nicken (%).

loop() {
  float cycle = (a_beat_count + a_beat_phase) / max(beats, 1);
  float on = a_bpm > 0 ? 1 : 0;
  float side = mod(a_beat_count + (mode == 2 ? index : 0), 2) == 0 ? -1 : 1;
  if (mode == 0) {
    pan = center_pan + on * 50 * (size / 100) * sin(2 * PI * (cycle + index * spread));
  } else {
    pan = center_pan + on * 50 * (size / 100) * side;
  }
  tilt = center_tilt + on * 50 * (bounce / 100) * sin(4 * PI * (cycle + index * spread));
}
