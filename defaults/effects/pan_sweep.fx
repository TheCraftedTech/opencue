#NAME Pan Sweep
#DESCRIPTION Pan schwingt hin und her. Nur Pan wird gesteuert – Tilt kannst du weiter von Hand einstellen. size = Weite in %.
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 40 0 50 1
#VAR spread Slider 0 0 1 0.05

loop() {
  pan = 50 + size * sin(2 * PI * (speed * t + index * spread));
}
