# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Globales Rueckgaengig / Wiederholen fuer den Inhalt der Show (Strg+Z / Strg+Y ausserhalb des Bearbeitungsmodus der Panels).

Was rueckgaengig gemacht werden kann - alles, was auch in die Showfile gespeichert wird, plus die Bedienung davor:
  - Cue-Listen und ihre Cues (speichern, aktualisieren, Zeiten / Ausloeser / Namen aendern - auch mehrere auf einmal -, kopieren, loeschen, Listen anlegen / umbenennen / loeschen / ordnen),
  - Variablen (Presets) und ihre Gruppen, Scheinwerfer-Gruppen,
  - das Patch (Scheinwerfer anlegen / loeschen / umadressieren / umbenennen / anordnen),
  - Effekte (Definitionen und ihre Gruppen), Zeitplan, Timeline-Befehlsspuren,
  - die Auswahl der Scheinwerfer,
  - Programmer-Werte (Fader, Befehle wie `At 80`, Variablen anwenden) samt dem DMX-Stand der betroffenen Scheinwerfer,
  - auf Wunsch (Schalter in der Toolbar, aus als Vorgabe) auch Go / Back / Springen: Rueckgaengig springt zum vorigen Cue.
Nicht dabei: Einstellungen, das Panel-Layout (hat sein eigenes Rueckgaengig im Bearbeitungsmodus), Zuweisungen laufender Effekte, Fader der Executor, Show-Wechsel (Neu / Laden leeren die Liste).

Arbeitsweise: nach jeder Nachricht eines Clients, die den Zustand veraendert hat, wird ein Schnappschuss der Show-Bereiche mit dem vorherigen verglichen; Unterschiede
werden ein Eintrag (Vorher / Nachher). Schnelle gleichartige Aenderungen (Wischgeste auf Zeiten, Fader ziehen) werden zu EINEM Schritt zusammengefasst. Der absolute Zustand
eines Cues (`Cue.absolute`) wird nie an Ort und Stelle veraendert, nur ersetzt - deshalb teilen sich die Schnappschuesse ihn (kein Kopieren der grossen Tabellen).
Programmer-Schritte merken sich nur die betroffenen Scheinwerfer (Programmer-Werte, Variablen-Verknuepfungen, Cue-Schichten, rohe DMX-Kanaele)."""
from __future__ import annotations

import copy
import time
from dataclasses import fields as dc_fields
from typing import Any, Dict, List, Optional, Set

from app.state_manager import Cue, CueList, Fixture, StateManager

LIMIT = 100                   # so viele Schritte merkt sich die Liste
COALESCE_SECONDS = 1.5        # gleichartige Aenderungen innerhalb dieser Zeit sind ein Schritt

# Nachrichten -> Art der Aenderung (fuer die Meldung "Rueckgaengig: ..." und das Zusammenfassen)
SHOW_LABELS: Dict[str, str] = {
    "save_cue": "cue_store", "update_active_cue": "cue_update",
    "update_cue": "cue_edit", "update_cues": "cue_edit", "copy_cues": "cue_copy",
    "delete_cue": "cue_delete", "delete_cues": "cue_delete",
    "add_cuelist": "cuelist", "duplicate_cuelist": "cuelist", "reorder_cuelists": "cuelist", "delete_cuelist": "cuelist", "rename_cuelist": "cuelist",
    "add_preset": "preset", "update_preset": "preset", "delete_preset": "preset", "add_preset_group": "preset", "delete_preset_group": "preset",
    "add_fixture_group": "group", "rename_fixture_group": "group", "delete_fixture_group": "group", "assign_fixture_group": "group",
    "add_fixtures": "patch", "delete_fixtures": "patch", "update_fixture": "patch", "rename_fixture": "patch", "set_fixture_layout": "patch",
    "reset_fixture_layout": "patch", "set_fixture_layout_options": "patch", "set_fixture_layout_views": "patch", "set_fixture_sort_index": "patch",
    "add_fx": "effect", "update_fx": "effect", "delete_fx": "effect", "add_fx_group": "effect", "delete_fx_group": "effect", "simple_look": "effect",
    "set_schedule": "schedule", "set_timeline_tracks": "timeline",
    "run_command": "command",
}
LIVE_LABELS: Dict[str, str] = {            # Programmer-Bedienung
    "set_fixture_values": "programmer", "set_fixture_raw_channel": "programmer", "preset_apply": "programmer", "preset_release": "programmer",
    "fx_assign": "effect", "simple_look": "effect", "run_command": "command",
}
MASTER_MESSAGES = {"set_cuelist_master": "master"}                       # Executor-Fader
PLAYBACK_MESSAGES = {"cue_go": "playback", "cue_back": "playback", "jump_to_cue": "playback"}
SELECTION_MESSAGES = {"set_selection": "selection"}
# Nachrichten, nach denen der Show-Inhalt immer verglichen wird (auch wenn der Zaehler sich nicht bewegt hat); alle anderen nur, wenn die Show als geaendert markiert wurde
SHOW_CHECK = set(SHOW_LABELS)
# Nachrichten, die die ganze Show austauschen: die Liste beginnt von vorn
RESET_MESSAGES = {"new_show", "load_show"}


def _clone_cue(cue: Cue) -> Cue:
    clone = copy.copy(cue)
    clone.fixture_values = copy.deepcopy(cue.fixture_values)
    clone.fx = copy.deepcopy(cue.fx)
    clone.fx_order = copy.deepcopy(cue.fx_order)
    clone.clock_days = list(cue.clock_days)
    # clone.absolute bleibt dieselbe Tabelle (wird nur ersetzt, nie veraendert)
    return clone


def _clone_cuelists(cuelists: Dict[str, CueList]) -> Dict[str, CueList]:
    return {cid: CueList(id=cl.id, name=cl.name, cues=[_clone_cue(c) for c in cl.cues]) for cid, cl in cuelists.items()}


_FIXTURE_FIELDS = [f.name for f in dc_fields(Fixture) if f.name != "values"]


def snapshot(state: StateManager) -> Dict[str, Any]:
    """Der Inhalt der Show, soweit er rueckgaengig gemacht werden kann (unabhaengige Kopie). Die Live-Kanalwerte der Scheinwerfer gehoeren nicht zum Patch."""
    state._ensure_layout_positions()          # Plaetze in der Layout-Ansicht werden beim Senden vergeben: vorher festlegen, damit das keinen Unterschied vortaeuscht
    return {
        "cuelists": _clone_cuelists(state.cuelists),
        "presets": copy.deepcopy(state.presets),
        "preset_groups": list(state.preset_groups),
        "groups": copy.deepcopy(state.groups),
        "fixtures": {fid: {name: getattr(fx, name) for name in _FIXTURE_FIELDS} for fid, fx in state.fixtures.items()},
        "fixture_layout": copy.deepcopy(state.fixture_layout),
        "fx_effects": copy.deepcopy(state.fx_effects),
        "fx_groups": list(state.fx_groups),
        "schedule": copy.deepcopy(state.schedule),
        "timeline_tracks": copy.deepcopy(state.timeline_tracks),
    }


def changed_domains(a: Dict[str, Any], b: Dict[str, Any]) -> List[str]:
    return [key for key in a if a[key] != b[key]]


# ---------------------------------------------------------------------------------------------------- Programmer (Live-Zustand einzelner Scheinwerfer)
def _live_ids(state: StateManager, message_type: str, payload: Dict[str, Any]) -> Optional[List[str]]:
    """Welche Scheinwerfer eine Programmer-Nachricht betrifft (None = alle: Befehle koennen jeden ansprechen)."""
    if message_type in ("set_fixture_values", "set_fixture_raw_channel"):
        return [str(i) for i in payload.get("ids", [])]
    if message_type in ("preset_apply", "preset_release", "fx_assign"):
        return [str(i) for i in payload.get("fixture_ids", [])]
    return None


def live_snapshot(state: StateManager, ids: Optional[List[str]]) -> Dict[str, Dict[str, Any]]:
    """Programmer-Werte, Variablen-Verknuepfungen, Cue-Schichten und rohe DMX-Kanaele der Scheinwerfer (None = alle)."""
    from app.dmx_engine import dmx_engine
    wanted = [f for f in (ids if ids is not None else list(state.fixtures)) if f in state.fixtures]
    universes: Dict[int, List[int]] = {}
    out: Dict[str, Dict[str, Any]] = {}
    for fid in wanted:
        fx = state.fixtures[fid]
        if fx.universe not in universes:
            universes[fx.universe] = dmx_engine.get_universe_snapshot(fx.universe)
        buf = universes[fx.universe]
        out[fid] = {
            "pv": copy.deepcopy(state.programmer_values.get(fid)),
            "pr": copy.deepcopy(state.programmer_refs.get(fid)),
            "fxa": copy.deepcopy(state.fx_assignments.get(fid)),            # laufende Effekte dieses Scheinwerfers: {Kategorie: {fx_id, index, count}}
            "layers": {name: {cl_id: copy.deepcopy(table[cl_id][fid]) for cl_id in table if fid in table[cl_id]}
                       for name, table in (("cue_layer", state.cue_layer), ("cue_base", state.cue_base))},
            "raw": [buf[fx.start_channel - 1 + k] if 0 <= fx.start_channel - 1 + k < len(buf) else 0 for k in range(fx.channel_count)],      # DMX-Kanal 1 = Puffer-Platz 0
            "values": dict(fx.values),
        }
    return out


def _live_same(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return a["pv"] == b["pv"] and a["pr"] == b["pr"] and a["layers"] == b["layers"] and a["fxa"] == b["fxa"]


class ShowUndo:
    def __init__(self) -> None:
        self._undo: List[Dict[str, Any]] = []
        self._redo: List[Dict[str, Any]] = []
        self._baseline: Optional[Dict[str, Any]] = None
        self._counter = -1
        self._epoch = -1
        self._sel: List[str] = []
        self._ctx: Optional[Dict[str, Any]] = None
        self._live_before: Optional[Dict[str, Dict[str, Any]]] = None
        self._live_ids: Optional[List[str]] = None
        self._play_before: Dict[str, str] = {}
        self._master_before: Dict[str, float] = {}
        self.last_restore: Dict[str, Any] = {}

    # ------------------------------------------------------------------ Verlauf
    def reset(self) -> None:
        self._undo.clear()
        self._redo.clear()
        self._baseline = None
        self._counter = -1

    def info(self) -> Dict[str, Any]:
        return {
            "can_undo": bool(self._undo), "can_redo": bool(self._redo),
            "undo_label": self._undo[-1]["label"] if self._undo else "", "redo_label": self._redo[-1]["label"] if self._redo else "",
        }

    # ------------------------------------------------------------------ Aufzeichnen: vor und nach einer Client-Nachricht
    def _programmer_key(self, message_type: str, ids: Optional[List[str]]) -> Any:
        return ("programmer", message_type, tuple(sorted(ids)) if ids is not None else None)

    def _coalescing_live(self, message_type: str, ids: Optional[List[str]]) -> bool:
        """Zieht der Nutzer gerade einen Fader (gleiche Nachricht, gleiche Scheinwerfer, kurz nach dem letzten Schritt)? Dann bleibt das Vorher des ersten Schritts."""
        last = self._undo[-1] if self._undo else None
        return (ids is not None and last is not None and last["key"] == self._programmer_key(message_type, ids)
                and time.monotonic() - last["t"] <= COALESCE_SECONDS and "programmer" in last["parts"])

    def begin(self, state: StateManager, message_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Vor der Verarbeitung: Ausgangslage merken (der Schnappschuss wird nur neu gemacht, wenn sich die Show seit dem letzten Mal veraendert hat)."""
        payload = payload or {}
        if state.show_epoch != self._epoch:
            self.reset()
            self._epoch = state.show_epoch
        if self._baseline is None or state.change_counter != self._counter:
            self._baseline = snapshot(state)               # z.B. von der REST-Schnittstelle veraendert: gilt als Ausgangslage, nicht als Schritt
            self._counter = state.change_counter
        self._sel = list(state.selected_fixture_ids)
        self._ctx = {"type": message_type}
        self._live_before = None
        self._live_ids = None
        if message_type in LIVE_LABELS:
            ids = _live_ids(state, message_type, payload)
            self._live_ids = ids
            if not self._coalescing_live(message_type, ids):
                self._live_before = live_snapshot(state, ids)
        if (message_type in PLAYBACK_MESSAGES or message_type == "run_command") and getattr(state, "undo_playback", False):
            self._play_before = dict(state.active_cue_ids)
        if message_type in MASTER_MESSAGES:
            cl_id = str(payload.get("cuelist_id", ""))
            self._master_before = {cl_id: state.cuelist_master(cl_id)} if cl_id in state.cuelists else {}

    def end(self, state: StateManager, message_type: str, payload: Dict[str, Any]) -> bool:
        """Nach der Verarbeitung: hat sich etwas veraendert, wird es ein Schritt. True = die Liste hat sich geaendert (Anzeige auffrischen)."""
        if self._ctx is None or self._ctx.get("type") != message_type:
            return False
        self._ctx = None
        if message_type in RESET_MESSAGES:
            self.reset()
            self._epoch = state.show_epoch
            return True
        parts: Dict[str, Any] = {}
        if state.selected_fixture_ids != self._sel:
            parts["selection"] = (list(self._sel), list(state.selected_fixture_ids))
        if self._baseline is not None and (message_type in SHOW_CHECK or state.change_counter != self._counter):
            after = snapshot(state)
            if changed_domains(self._baseline, after):
                parts["show"] = (self._baseline, after)
                self._baseline = after
            self._counter = state.change_counter
        coalesced_live = False
        if message_type in LIVE_LABELS:
            if self._live_before is not None:
                after_live = live_snapshot(state, self._live_ids)
                moved = {fid: (self._live_before[fid], after_live[fid]) for fid in after_live
                         if fid in self._live_before and not _live_same(self._live_before[fid], after_live[fid])}
                if moved:
                    parts["programmer"] = moved
            else:                                           # Fader laeuft weiter: nur der Endzustand des letzten Schritts wird nachgefuehrt
                last = self._undo[-1]
                after_live = live_snapshot(state, self._live_ids)
                for fid, (before, _old) in list(last["parts"]["programmer"].items()):
                    if fid in after_live:
                        last["parts"]["programmer"][fid] = (before, after_live[fid])
                last["t"] = time.monotonic()
                coalesced_live = True
        if message_type in MASTER_MESSAGES and self._master_before:
            cl_id = next(iter(self._master_before))
            before_level, after_level = self._master_before[cl_id], state.cuelist_master(cl_id)
            last = self._undo[-1] if self._undo else None
            if last is not None and "master" in last["parts"] and last["key"] == ("master", cl_id) and time.monotonic() - last["t"] <= COALESCE_SECONDS:
                old_before = last["parts"]["master"][cl_id][0]       # Fader wird weiter gezogen: ein Schritt, das Vorher des ersten Zugs bleibt
                last["parts"]["master"][cl_id] = (old_before, after_level)
                last["t"] = time.monotonic()
                return False
            if abs(before_level - after_level) > 1e-9:
                parts["master"] = {cl_id: (before_level, after_level)}
        if (message_type in PLAYBACK_MESSAGES or message_type == "run_command") and getattr(state, "undo_playback", False):
            moved_lists = {cl_id: (self._play_before.get(cl_id), state.active_cue_ids.get(cl_id))
                           for cl_id in set(self._play_before) | set(state.active_cue_ids)
                           if self._play_before.get(cl_id) != state.active_cue_ids.get(cl_id)}
            if moved_lists:
                parts["playback"] = moved_lists
        if coalesced_live and not parts:
            return False
        if not parts:
            return False
        label = (MASTER_MESSAGES.get(message_type) or LIVE_LABELS.get(message_type) or SHOW_LABELS.get(message_type) or PLAYBACK_MESSAGES.get(message_type) or SELECTION_MESSAGES.get(message_type) or "change")
        if message_type == "run_command":
            label = "command"
        elif "show" in parts and label in ("selection", "programmer", "playback", "master"):
            label = "change"
        elif set(parts) == {"selection"}:
            label = "selection"
        elif not ({"show", "programmer", "playback", "master"} & set(parts)):
            label = "selection"
        ids = payload.get("cue_ids") or [u.get("cue_id", "") for u in (payload.get("updates") or []) if isinstance(u, dict)] or [payload.get("cue_id", "")]
        key: Any = (label, str(payload.get("cuelist_id", "")), tuple(sorted(str(c) for c in ids)))
        if "programmer" in parts and message_type in LIVE_LABELS:
            key = self._programmer_key(message_type, self._live_ids)
        if "master" in parts:
            key = ("master", next(iter(parts["master"])))
        now = time.monotonic()
        last = self._undo[-1] if self._undo else None
        if (last is not None and label == "cue_edit" and last["key"] == key and now - last["t"] <= COALESCE_SECONDS
                and set(last["parts"]) == set(parts) and "show" in parts):
            last["parts"]["show"] = (last["parts"]["show"][0], parts["show"][1])      # derselbe Schritt, neuer Endzustand
            last["t"] = now
        else:
            self._undo.append({"label": label, "parts": parts, "t": now, "key": key})
            del self._undo[:-LIMIT]
        self._redo.clear()
        return True

    # ------------------------------------------------------------------ Rueckgaengig / Wiederholen
    def pop(self, direction: str) -> Optional[Dict[str, Any]]:
        stack, other = (self._undo, self._redo) if direction == "undo" else (self._redo, self._undo)
        if not stack:
            return None
        entry = stack.pop()
        other.append(entry)
        return entry

    def restore(self, state: StateManager, entry: Dict[str, Any], direction: str) -> List[str]:
        """Setzt den Zustand des Eintrags (vorher beim Rueckgaengig, nachher beim Wiederholen). Liefert die geaenderten Bereiche: cuelists, presets, preset_groups, groups,
        fixtures, fx_effects, fx_groups, schedule, timeline_tracks, selection, programmer, playback. Weitere Angaben fuer die Anzeige stehen in `last_restore`."""
        index = 0 if direction == "undo" else 1
        changed: List[str] = []
        self.last_restore = {"released_fx": [], "fids": [], "universes": set(), "playback": {}, "masters": {}, "fx_changed": False}
        show = entry["parts"].get("show")
        if show is not None:
            changed += self._restore_show(state, show[index])
        sel = entry["parts"].get("selection")
        if sel is not None:
            state.set_selection(list(sel[index]))
            changed.append("selection")
        live = entry["parts"].get("programmer")
        if live:
            self._restore_live(state, live, index)
            changed.append("programmer")
        masters = entry["parts"].get("master")
        if masters:
            self.last_restore["masters"] = {cl_id: pair[index] for cl_id, pair in masters.items()}
            changed.append("master")
        play = entry["parts"].get("playback")
        if play:
            self.last_restore["playback"] = {cl_id: pair[index] for cl_id, pair in play.items()}
            changed.append("playback")
        return changed

    def _restore_show(self, state: StateManager, target: Dict[str, Any]) -> List[str]:
        current = snapshot(state)
        changed = changed_domains(current, target)
        state.cuelists = _clone_cuelists(target["cuelists"])
        state.presets = copy.deepcopy(target["presets"])
        state.preset_groups = list(target["preset_groups"])
        state.groups = copy.deepcopy(target["groups"])
        # Patch: vorhandene Scheinwerfer-Objekte bleiben (Live-Kanalwerte, Verweise), nur die Felder werden zurueckgesetzt
        if "fixtures" in changed:
            rebuilt: Dict[str, Fixture] = {}
            for fid, data in target["fixtures"].items():
                fx = state.fixtures.get(fid)
                if fx is None:
                    fx = Fixture(**copy.deepcopy(data), values={})
                else:
                    for name, value in data.items():
                        setattr(fx, name, copy.deepcopy(value))
                rebuilt[fid] = fx
            gone = [fid for fid in state.fixtures if fid not in rebuilt]
            state.fixtures = rebuilt
            for fid in gone:
                state._forget_fixture(fid)
            state.selected_fixture_ids = [f for f in state.selected_fixture_ids if f in state.fixtures]
        state.fixture_layout = copy.deepcopy(target["fixture_layout"])
        # Effekte: entfernte Definitionen geben ihre Zuweisungen frei (wie beim Loeschen), danach gilt der Stand des Eintrags
        from app.fx_engine import fx_engine
        removed = [fx_id for fx_id in state.fx_effects if fx_id not in target["fx_effects"]]
        for fx_id in removed:
            self.last_restore["released_fx"] += fx_engine.delete_definition(fx_id)
        state.fx_effects = copy.deepcopy(target["fx_effects"])
        state.fx_groups = list(target["fx_groups"])
        state.schedule = copy.deepcopy(target["schedule"])
        state.timeline_tracks = copy.deepcopy(target["timeline_tracks"])
        for cid in list(state.active_cue_ids):                     # ein wiederhergestellter Stand kennt den aktiven Cue vielleicht nicht mehr
            cl = state.cuelists.get(cid)
            if cl is None or not any(c.id == state.active_cue_ids[cid] for c in cl.cues):
                state.active_cue_ids.pop(cid, None)
        if state.active_cuelist_id not in state.cuelists:
            state.active_cuelist_id = next(iter(state.cuelists), None)
        state.mark_dirty()
        self._baseline = snapshot(state)
        self._counter = state.change_counter
        return changed

    def _restore_live(self, state: StateManager, pairs: Dict[str, Any], index: int) -> None:
        """Programmer-Zustand einzelner Scheinwerfer zurueck: Werte, Verknuepfungen, Cue-Schichten, laufende Effekte, rohe DMX-Kanaele (Ausgabe sofort)."""
        from app.dmx_engine import dmx_engine
        from app.fx_engine import fx_engine
        batches: Dict[int, Dict[int, int]] = {}
        for fid, pair in pairs.items():
            snap, other = pair[index], pair[1 - index]
            fx = state.fixtures.get(fid)
            if fx is None:
                continue
            for store, key in ((state.programmer_values, "pv"), (state.programmer_refs, "pr")):
                if snap[key] is None:
                    store.pop(fid, None)
                else:
                    store[fid] = copy.deepcopy(snap[key])
            for name, table in (("cue_layer", state.cue_layer), ("cue_base", state.cue_base)):
                saved = snap["layers"][name]
                for cl_id in list(table):
                    if cl_id not in saved:
                        table[cl_id].pop(fid, None)
                for cl_id, entry in saved.items():
                    table.setdefault(cl_id, {})[fid] = copy.deepcopy(entry)
            fx_changed = snap["fxa"] != other["fxa"]
            if fx_changed:                                           # laufende Effekte: wie Zuweisen / Abwaehlen - entfernte geben den Scheinwerfer frei (gespeicherter Stand erscheint)
                with fx_engine.lock:
                    now_cats = state.fx_assignments.get(fid) or {}
                    wanted = snap["fxa"] or {}
                    lost = False
                    for cat in list(now_cats):
                        if cat not in wanted or now_cats[cat] != wanted[cat]:
                            fx_engine._forget(fid, cat)
                            lost = lost or cat not in wanted
                    if wanted:
                        state.fx_assignments[fid] = copy.deepcopy(wanted)
                    else:
                        state.fx_assignments.pop(fid, None)
                if lost:
                    self.last_restore["released_fx"].append(fid)
                self.last_restore["fx_changed"] = True
            fx.values = dict(snap["values"])
            if not (fx_changed and snap["pv"] == other["pv"]):       # nur ein Effekt hat sich geaendert: die Ausgabe regelt der Effekt bzw. die Freigabe, keine Rohwerte zurueckschreiben
                batch = batches.setdefault(fx.universe, {})
                for k, value in enumerate(snap["raw"]):
                    batch[fx.start_channel + k] = int(value)
            self.last_restore["fids"].append(fid)
            self.last_restore["universes"].add(fx.universe)
        for universe, batch in batches.items():
            dmx_engine.commit_batch(universe, batch)

show_undo = ShowUndo()
