#NAME Heartbeat
#DESCRIPTION Zwei Schläge, dann Pause - wie ein Herzschlag. speed = Schläge pro Sekunde.
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  float p = fract(speed * t + index * spread);
  float first = smoothstep(0, 0.08, p) * (1 - smoothstep(0.08, 0.22, p));
  float second = 0.7 * smoothstep(0.28, 0.36, p) * (1 - smoothstep(0.36, 0.55, p));
  dimmer = size * max(first, second);
}
