#NAME Kick Zoom Punch
#DESCRIPTION en The zoom punches from low to high on every bass drum hit and falls back.
#DESCRIPTION de Der Zoom schlägt bei jedem Bassdrum-Schlag von low nach high aus und fällt zurück.
#TAGS advanced, flash
#CATEGORY zoom
#RATE 40
#VAR gain Slider 1 0.2 3 0.05
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1

loop() {
  zoom = lerp(low, high, constrain(a_kick * gain, 0, 1));
}
