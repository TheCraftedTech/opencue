#NAME Color Pulse
#DESCRIPTION Eine gewählte Farbe pulsiert in der Helligkeit.
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR spread Slider 0 0 1 0.05
#VAR tint ColorPicker #ff3000

loop() {
  float k = 0.5 + 0.5 * sin(2 * PI * (speed * t + index * spread));
  r = tint_r * k;
  g = tint_g * k;
  b = tint_b * k;
}
