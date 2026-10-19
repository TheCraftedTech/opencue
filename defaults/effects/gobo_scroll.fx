#NAME Gobo Scroll
#DESCRIPTION Fährt den ganzen Wertebereich des Gobo-Kanals durch (für Geräte, die dort ein durchlaufendes Rad haben).
#CATEGORY gobo
#RATE 40
#VAR speed Slider 0.2 0.02 4 0.02
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1

loop() {
  gobo = lerp(low, high, fract(speed * t));
}
