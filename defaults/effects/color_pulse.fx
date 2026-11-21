#NAME Color Pulse
#DESCRIPTION en The chosen colour pulses in brightness between low and size.
#DESCRIPTION de Die gewählte Farbe pulsiert in der Helligkeit zwischen low und size.
#TAGS basic, pulse, wave
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR spread Slider 0 0 1 0.05
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1
#VAR tint ColorPicker #ff3000

loop() {
  float k = lerp(low / 100, 1, 0.5 + 0.5 * sin(2 * PI * (speed * t + index * spread)));
  float q = k * size / 100;
  r = tint_r * q;
  g = tint_g * q;
  b = tint_b * q;
}
