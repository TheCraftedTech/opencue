#NAME Random Look
#DESCRIPTION Fährt weich zu zufälligen Punkten. speed = Ziele pro Sekunde.
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 40 0 50 1

float px = 50;
float py = 50;
float tx = 50;
float ty = 50;

loop() {
  if (tick % max(1, round(rate / speed)) == 0) {
    tx = 50 + random(-size, size);
    ty = 50 + random(-size, size);
  }
  px += (tx - px) * 0.12;
  py += (ty - py) * 0.12;
  pan = px;
  tilt = py;
}
