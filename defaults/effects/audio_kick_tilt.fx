#NAME Kick Tilt Punch
#DESCRIPTION en On every bass drum hit the heads punch in tilt and settle back to the base position. mode: 0 down, 1 up.
#DESCRIPTION de Bei jedem Bassdrum-Schlag schlagen die Köpfe im Tilt aus und setzen sich auf die Grundposition zurück. mode: 0 nach unten, 1 nach oben.
#TAGS advanced, flash
#CATEGORY position
#RATE 40
#VAR size Slider 30 0 50 1
#VAR mode Slider 0 0 1 1
#VAR center_tilt Slider 50 0 100 1
#INFO mode en Direction | 0 = tilt down on a hit, 1 = tilt up.
#INFO mode de Richtung | 0 = bei einem Schlag nach unten, 1 = nach oben.

loop() {
  float amt = size * a_kick;
  tilt = center_tilt + (mode == 1 ? amt : -amt);
}
