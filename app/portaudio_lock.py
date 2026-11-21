# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Ein gemeinsames Schloss fuer PortAudio: Initialisieren (PyAudio()), Oeffnen eines Eingangs und Beenden (terminate()) duerfen nicht gleichzeitig aus mehreren Faeden laufen.
Die Audio-Analyse und die Sprachsteuerung starten beim Programmstart in eigenen Faeden - ohne dieses Schloss kam es vor, dass das Mikrofon nicht aufging
("Unanticipated host error", -9999) und erst nach einem Wechsel der Auswahl funktionierte.
"""
import threading

LOCK = threading.RLock()
