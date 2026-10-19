#NAME Gobo Spin Sweep
#DESCRIPTION Wählt ein Gobo und lässt seine Drehung langsam zwischen zwei Werten pendeln. first = Gobo-Nummer, low/high = Drehung in %, speed = Pendel pro Sekunde.
#CATEGORY gobo
#RATE 40
#VAR speed Slider 0.2 0.05 2 0.05
#VAR first Slider 1 0 20 1
#VAR low Slider 55 0 100 1
#VAR high Slider 80 0 100 1

loop() {
  gobo = slot(first);
  gobo_spin = lerp(low, high, tri(speed * t + index * 0.1));
}
