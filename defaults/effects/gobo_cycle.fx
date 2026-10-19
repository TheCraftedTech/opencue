#NAME Gobo Cycle
#DESCRIPTION Schaltet der Reihe nach durch die Gobos des Geräts. speed = Wechsel pro Sekunde, first = erstes Gobo (0 = meist offen).
#CATEGORY gobo
#RATE 40
#VAR speed Slider 0.5 0.05 8 0.05
#VAR first Slider 0 0 20 1
#VAR spread Slider 0 0 1 0.05

loop() {
  float n = max(1, slots - first);
  gobo = slot(first + mod(floor(speed * t + index * spread * n), n));
}
