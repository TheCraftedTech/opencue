#NAME Pan/Tilt Wave
#DESCRIPTION Pan und Tilt schwingen als Sinuswellen (Acht-Bewegung). speed = Perioden pro Sekunde.
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  c = 2 * PI * (speed * t + index * spread);
  pan = 50 + 50 * (size / 100) * sin(c);
  tilt = 50 + 50 * (size / 100) * sin(c + PI / 2);
}
