#NAME Square Path
#DESCRIPTION Springt reihum zu den vier Ecken eines Quadrats. speed = Ecken pro Sekunde.
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 30 0 50 1
#VAR spread Slider 0 0 1 0.05

loop() {
  float corner = mod(floor(speed * t + index * spread * 4), 4);
  pan = 50 + ((corner == 0 || corner == 3) ? -size : size);
  tilt = 50 + (corner < 2 ? -size : size);
}
