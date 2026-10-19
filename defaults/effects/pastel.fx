#NAME Pastel Colors
#DESCRIPTION Wandert in Pastellfarben durch den Farbkreis.
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 100 0 100 1
#VAR spread Slider 0 0 1 0.05

loop() {
  hsv(speed * t + index * spread, 0.4, size / 100);
}
