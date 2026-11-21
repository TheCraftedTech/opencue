#NAME Tilt Sweep
#DESCRIPTION en The heads sweep in tilt (sine).
#DESCRIPTION de Die Köpfe schwenken im Tilt (Sinus).
#TAGS basic, sweep
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 40 0 50 1
#VAR spread Slider 0 0 1 0.05
#VAR center_tilt Slider 50 0 100 1

loop() {
  tilt = center_tilt + size * sin(2 * PI * (speed * t + index * spread));
}
