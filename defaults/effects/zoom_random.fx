#NAME Zoom Random
#DESCRIPTION Springt zu zufälligen Zoom-Werten und fährt weich dorthin.
#CATEGORY zoom
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1

float value = 50;
float target = 50;

loop() {
  if (tick % max(1, round(rate / speed)) == 0) {
    target = random(low, high);
  }
  value += (target - value) * 0.15;
  zoom = value;
}
