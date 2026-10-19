#NAME Gobo Dual Wheels
#DESCRIPTION Wechselt Rad 1 und Rad 2 gegeneinander (Rad 2 läuft versetzt). Eine Ausgabe, die das Gerät nicht hat, wird einfach ignoriert.
#CATEGORY gobo
#RATE 40
#VAR speed Slider 0.5 0.05 8 0.05
#VAR first Slider 0 0 20 1

loop() {
  float n = max(1, slots - first);
  float n2 = max(1, slots2 - first);
  gobo = slot(first + mod(floor(speed * t), n));
  gobo2 = slot(first + mod(floor(speed * t) + 1, n2), 2);
}
