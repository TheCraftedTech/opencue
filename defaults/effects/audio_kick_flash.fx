#NAME Kick Flash
#DESCRIPTION en Every bass drum hit flashes the lights and fades out. strobe flashes inside the flash, mode picks the pattern.
#DESCRIPTION de Bei jedem Bassdrum-Schlag blitzen die Scheinwerfer auf und klingen ab. strobe blitzt im Blitz, mode wählt das Muster.
#TAGS advanced, flash, strobe, toggle
#CATEGORY dimmer
#RATE 40
#VAR base Slider 5 0 100 1
#VAR peak Slider 100 0 100 1
#VAR strobe Slider 0 0 25 1
#VAR mode Slider 0 0 2 1
#VAR density Slider 50 5 100 5
#INFO mode en Pattern | 0 = all together, 1 = even/odd alternating on every beat, 2 = random fixtures (density).
#INFO mode de Muster | 0 = alle gemeinsam, 1 = gerade/ungerade im Wechsel bei jedem Beat, 2 = zufällige Scheinwerfer (density).
#INFO base en Base brightness | Brightness between the hits (%).
#INFO base de Grundhelligkeit | Helligkeit zwischen den Schlägen (%).
#INFO peak en Hit brightness | Brightness at the moment of a hit (%).
#INFO peak de Helligkeit beim Schlag | Helligkeit im Moment eines Schlags (%).

float lit = 1;
float last = 0;

loop() {
  if (a_kick > last + 0.3) {
    if (mode == 1) { lit = mod(index + a_beat_count, 2) == 0 ? 1 : 0; }
    else if (mode == 2) { lit = random(0, 100) < density ? 1 : 0; }
    else { lit = 1; }
  }
  last = a_kick;
  float gate = strobe > 0 ? square(strobe * t) : 1;
  dimmer = lerp(base, peak, a_kick * lit * gate);
}
