#NAME Hi-Hat Sparkle
#DESCRIPTION en On every hi-hat hit randomly chosen fixtures sparkle. density = share of fixtures taking part (%).
#DESCRIPTION de Bei jedem Hi-Hat-Schlag funkeln zufällig ausgewählte Scheinwerfer auf. density = Anteil der Scheinwerfer, die mitmachen (%).
#TAGS advanced, flash, strobe, random
#CATEGORY dimmer
#RATE 40
#VAR density Slider 40 5 100 5
#VAR base Slider 0 0 100 1
#VAR strobe Slider 0 0 25 1

float lit = 0;
float last = 0;

loop() {
  if (a_hat > last + 0.3) {
    lit = random(0, 100) < density ? 1 : 0;
  }
  last = a_hat;
  float gate = strobe > 0 ? square(strobe * t) : 1;
  dimmer = lerp(base, 100, lit * a_hat * gate);
}
