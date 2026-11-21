#NAME Pan Sweep
#DESCRIPTION en The heads sweep in pan (sine).
#DESCRIPTION de Die Köpfe schwenken im Pan (Sinus).
#TAGS basic, sweep
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 40 0 50 1
#VAR spread Slider 0 0 1 0.05
#VAR center_pan Slider 50 0 100 1

loop() {
  pan = center_pan + size * sin(2 * PI * (speed * t + index * spread));
}
