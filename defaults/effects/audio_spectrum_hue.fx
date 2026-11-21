#NAME Spectrum Hue
#DESCRIPTION en The colour follows the sound: bass-heavy music shows the start of the colour range, bright sounds its end. Brightness follows the loudness.
#DESCRIPTION de Die Farbe folgt dem Klang: bassige Musik zeigt den Anfang des Farbbereichs, helle Klänge sein Ende. Die Helligkeit folgt der Lautstärke.
#TAGS advanced, spectrum, rainbow
#CATEGORY color
#RATE 40
#VAR gain Slider 1 0.2 3 0.05
#VAR size Slider 100 0 100 1
#VAR low Slider 0 0 100 1
#VAR hue_from Slider 0 0 360 1
#VAR hue_range Slider 240 10 360 1
#VAR saturation Slider 100 0 100 1

loop() {
  float total = a_bass + a_mid + a_high + 0.001;
  float bal = (a_mid * 0.5 + a_high) / total;
  float v = lerp(low / 100, 1, constrain(a_level * gain, 0, 1));
  hsv(hue_from / 360 + hue_range / 360 * bal, saturation / 100, v * size / 100);
}
