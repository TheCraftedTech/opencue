#NAME Brightness Wave
#DESCRIPTION Eine weiche Helligkeitswelle läuft über alle Scheinwerfer (in Auswahl-Reihenfolge). speed = Wellen pro Sekunde, waves = Wellenlängen über die Auswahl, low/high = dunkelster und hellster Wert, direction: 1 = vorwärts, 0 = rückwärts.
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 0.5 0.05 4 0.05
#VAR waves Slider 1 0.25 4 0.25
#VAR low Slider 0 0 100 1
#VAR high Slider 100 0 100 1
#VAR direction Slider 1 0 1 1

loop() {
  float dir = direction > 0.5 ? 1 : -1;
  float k = 0.5 + 0.5 * sin(2 * PI * (dir * speed * t - waves * index / max(count, 1)));
  dimmer = lerp(low, high, k);
}
