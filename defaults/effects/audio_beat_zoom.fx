#NAME Beat Zoom Pulse
#DESCRIPTION en The zoom pulses on every beat: high on the beat, then falling back to low.
#DESCRIPTION de Der Zoom pulsiert bei jedem Beat: high auf dem Beat, dann zurück auf low.
#TAGS advanced, pulse
#CATEGORY zoom
#RATE 40
#VAR softness Slider 3 0.5 8 0.1
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1

loop() {
  float k = a_bpm > 0 ? pow(1 - a_beat_phase, softness) : 0;
  zoom = lerp(low, high, k);
}
