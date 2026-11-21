#NAME Square Path
#DESCRIPTION en The heads jump to the four corners of a square around the base position.
#DESCRIPTION de Die Köpfe springen zu den vier Ecken eines Quadrats um die Grundposition.
#TAGS advanced, steps
#CATEGORY position
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR size Slider 30 0 50 1
#VAR spread Slider 0 0 1 0.05
#VAR center_pan Slider 50 0 100 1
#VAR center_tilt Slider 50 0 100 1

loop() {
  float corner = mod(floor(speed * t + index * spread * 4), 4);
  pan = center_pan + ((corner == 0 || corner == 3) ? -size : size);
  tilt = center_tilt + (corner < 2 ? -size : size);
}
