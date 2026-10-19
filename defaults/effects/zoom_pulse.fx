#NAME Zoom Pulse
#DESCRIPTION Der Zoom schwingt weich zwischen low und high (0 = weit, 100 = eng, je nach Gerät).
#CATEGORY zoom
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  float k = 0.5 + 0.5 * sin(2 * PI * (speed * t + index * spread));
  zoom = lerp(low, high, k);
}
