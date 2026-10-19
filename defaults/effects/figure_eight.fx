#NAME Figure Eight
#DESCRIPTION Pan und Tilt fahren eine liegende Acht.
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 40 0 50 1
#VAR spread Slider 0 0 1 0.05

loop() {
  float a = 2 * PI * (speed * t + index * spread);
  pan = 50 + size * sin(a);
  tilt = 50 + size * sin(2 * a) / 2;
}
