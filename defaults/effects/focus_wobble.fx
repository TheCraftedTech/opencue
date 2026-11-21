#NAME Focus Wobble
#DESCRIPTION en The focus wobbles slightly around a centre value.
#DESCRIPTION de Der Fokus wackelt leicht um einen Mittelwert.
#TAGS advanced, wave
#CATEGORY focus
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR center Slider 50 0 100 1
#VAR amount Slider 10 0 50 1
#VAR spread Slider 0 0 1 0.05

loop() {
  focus = center + amount * sin(2 * PI * (speed * t + index * spread));
}
