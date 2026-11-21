#NAME Gobo Scroll
#DESCRIPTION en Scrolls continuously through the gobo wheel (low to high).
#DESCRIPTION de Läuft stufenlos durch das Gobo-Rad (von low bis high).
#TAGS advanced, sweep
#CATEGORY gobo
#RATE 40
#VAR speed Slider 0.2 0.02 4 0.02
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1

loop() {
  gobo = lerp(low, high, fract(speed * t));
}
