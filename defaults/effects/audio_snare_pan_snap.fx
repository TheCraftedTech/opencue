#NAME Snare Pan Snap
#DESCRIPTION en On every snare hit each head snaps to the next of four pan positions. glide = how smoothly it travels there (0 = jump).
#DESCRIPTION de Bei jedem Snare-Schlag springt jeder Kopf zur nächsten von vier Pan-Positionen. glide = wie weich er dorthin fährt (0 = Sprung).
#TAGS advanced, toggle, steps
#CATEGORY position
#RATE 40
#VAR size Slider 40 0 50 1
#VAR glide Slider 0.6 0 0.95 0.05
#VAR center_pan Slider 50 0 100 1

float idx = 0;
float last = 0;
float value = 50;

loop() {
  if (a_snare > last + 0.3) { idx += 1; }
  last = a_snare;
  float place = mod(idx + index, 4);
  float target = a_active > 0.5 ? center_pan + size * (place - 1.5) / 1.5 : center_pan;
  value += (target - value) * (1 - glide);
  pan = value;
}
