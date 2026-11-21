#NAME Even / Odd Alternate
#DESCRIPTION en Even and odd fixtures take turns. speed = changes per second, strobe adds flashing inside the lit phase.
#DESCRIPTION de Gerade und ungerade Scheinwerfer wechseln sich ab. speed = Wechsel pro Sekunde, strobe blitzt in der Leuchtphase.
#TAGS advanced, toggle, alternate, strobe
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1
#VAR strobe Slider 0 0 25 1

loop() {
  float step = floor(speed * t * 2);
  float gate = strobe > 0 ? square(strobe * t) : 1;
  dimmer = mod(step + index, 2) == 0 ? lerp(low, size, gate) : low;
}
