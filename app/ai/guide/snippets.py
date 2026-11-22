# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Die Textschnipsel des Wegweisers: kleine Abschnitte aus den Anleitungen als JSON (static/help/guide/snippets/<sprache>/<seite>.json). Python sucht die passenden heraus -
einfache Stichwortsuche (kein Modell, keine Embeddings): Woerter der Frage gegen Ueberschriften, Stichwoerter und Text, seltene Woerter zaehlen mehr als haeufige (IDF); das Ergebnis
geht als "Anleitung" an die KI. Die KI soll NUR damit antworten (nichts erfinden): kommt nichts Passendes, sagt das Ergebnis es ausdruecklich."""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app import paths

MIN_SCORE = 3.0                  # darunter gilt ein Schnipsel nicht als Treffer
TEXT_LIMIT = 1400
USER_PAGES = {"getting-started": 1.5, "fixtures": 1.2, "fixture-editor": 1.2, "remote": 1.0, "keyboard-shortcuts": 1.0, "audio": 0.8, "voice-commands": 1.0, "midi": 1.0, "dmx-input": 1.0, "timeline": 1.0, "show-safety": 1.0, "startup-options": 1.0, "automation": 1.0, "whatsnew": 0.8, "error-codes": 1.0, "chat": 1.0}      # Anleitungen fuer Anwender: bei gleichem Treffer vorn
STOP = {
    "de": set("der die das den dem des ein eine einen einem einer und oder aber auch ich du wir ihr sie es ist sind war wird werden kann kannst koennen können man mir mich dir dich was wie wo wann wer welche welcher welches "
              "mit von zu im in am an auf aus bei für fuer nach vor über ueber um zum zur dass nicht nur noch schon sehr mal bitte wenn dann als so viel viele hier dort gibt gibts soll sollte will möchte moechte "
              "habe haben hat hast machen mache zeige zeig sag sage erkläre erklaere erklär funktioniert funktionieren geht gehen benutze benutzen benutzt nutzen nutze verwenden verwende finde finden mein meine meinen "
              "kommt komme muss musst brauche brauchst bedeutet heißt heisst".split()),
    "fr": set("le la les un une des du de et ou mais aussi je tu il elle nous vous ils elles est sont etait etre peut peux comment quoi quel quelle quels quelles ou quand qui que avec dans sur pour par au aux ce cet cette ces mon ma mes ton ta tes son sa ses pas plus tres bien si en y a ai as avons avez ont fait faire veux voudrais utiliser utilise besoin".split()),
    "nl": set("de het een en of maar ook ik jij je wij we jullie zij ze het is zijn was waren kan kun hoe wat waar wanneer wie welke met van naar in op aan voor door om bij uit dat dit die deze niet nog al zeer wel als dan zo heb hebben heeft doen maak maken wil wilt gebruik gebruiken nodig".split()),
    "it": set("il lo la i gli le un una uno e o ma anche io tu lui lei noi voi loro e sono era essere puo posso come cosa dove quando chi quale con di da in su per tra fra al alla ai alle del della dei delle questo questa questi queste non piu molto bene se ho hai ha abbiamo hanno fare faccio voglio vorrei usare uso serve bisogno".split()),
    "es": set("el la los las un una unos unas y o pero tambien yo tu el ella nosotros vosotros ellos es son era ser puede puedo como que donde cuando quien cual con de del en sobre para por al a este esta estos estas no mas muy bien si he has ha hemos han hacer hago quiero quisiera usar uso necesito".split()),
    "en": set("the a an and or but also i you we they it is are was were be been can could how what where when who which with of to in on at for from by about that this these those do does did me my your please show tell "
              "explain there here have has had make want would should work works use using find need needs mean means".split()),
}
_cache: Dict[str, Dict[str, Any]] = {}
_synonyms: Dict[str, Any] = {}


def folder() -> Path:
    return paths.project_root() / "static" / "help" / "guide"


def stem(word: str) -> str:
    """Grobes Abschneiden der Endung (Einstellung / Einstellungen / einstellen -> 'einst'): reicht fuer die Stichwortsuche."""
    if re.fullmatch(r"oc-\d{4}", word):                          # Fehlercodes (static/help/error-codes.*.md) bleiben ganz: OC-1001 und OC-1002 sind verschieden
        return word
    return word if len(word) <= 5 else word[:5]


def tokens(text: str, lang: str) -> List[str]:
    words = re.findall(r"[a-zäöüß0-9][a-zäöüß0-9+\-]*", str(text).lower())
    stop = STOP.get(lang, STOP["en"])
    return [stem(w) for w in words if len(w) >= 2 and w not in stop]


def _synonym_table() -> Dict[str, List[str]]:
    if not _synonyms:
        try:
            _synonyms.update(json.loads((folder() / "synonyms.json").read_text(encoding="utf-8")))
        except (OSError, ValueError):
            _synonyms["words"] = {}
    return _synonyms.get("words", {})


def expand(question: str, lang: str) -> List[str]:
    """Die Woerter der Frage plus Verwandtes aus synonyms.json ('dateimanager' -> 'file manager', 'shows' ...)."""
    base = tokens(question, lang)
    extra: List[str] = []
    low = question.lower()
    for word, more in _synonym_table().items():
        if word in low:
            for item in more:
                extra.extend(tokens(item, lang))
    return base + extra


def load(lang: str) -> List[Dict[str, Any]]:
    """Alle Schnipsel einer Sprache (mit vorberechneten Woertern). Eine kaputte Datei wird uebersprungen."""
    return _index(lang)["items"]


def _index(lang: str) -> Dict[str, Any]:
    lang = lang if lang in ("de", "en", "fr", "nl", "it", "es") else "en"
    key = str(folder() / "snippets" / lang)
    if key in _cache:
        return _cache[key]
    items: List[Dict[str, Any]] = []
    directory = folder() / "snippets" / lang
    english = folder() / "snippets" / "en"
    files = {p.name: p for p in (sorted(directory.glob("*.json")) if directory.is_dir() else [])}
    if lang != "en" and english.is_dir():                         # Seiten, die es in dieser Sprache noch nicht gibt, kommen auf Englisch (die KI antwortet trotzdem in der Sprache des Nutzers)
        for p in sorted(english.glob("*.json")):
            files.setdefault(p.name, p)
    for path in [files[name] for name in sorted(files)]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for chunk in data if isinstance(data, list) else []:
            if not isinstance(chunk, dict) or not chunk.get("text"):
                continue
            title_words = tokens(" ".join(list(chunk.get("path") or []) + [str(chunk.get("title", ""))] + list(chunk.get("keywords") or [])), lang)
            chunk["_title"] = set(title_words)
            chunk["_body"] = Counter(tokens(chunk["text"], lang))
            items.append(chunk)
    frequency: Counter = Counter()
    for chunk in items:
        frequency.update(chunk["_title"] | set(chunk["_body"]))
    idf = {word: math.log((len(items) + 1) / (1 + count)) for word, count in frequency.items()}
    _cache[key] = {"items": items, "idf": idf, "n": len(items)}
    return _cache[key]


def score(question_tokens: List[str], chunk: Dict[str, Any], idf: Dict[str, float], unknown: float) -> float:
    total = 0.0
    seen = set()
    for word in question_tokens:
        if word in seen:
            continue
        seen.add(word)
        weight = idf.get(word, unknown)
        if word in chunk["_title"]:
            total += 3 * weight
        hits = chunk["_body"].get(word, 0)
        if hits:
            total += min(hits, 2) * weight
    return total


def source_of(chunk: Dict[str, Any]) -> str:
    return " › ".join(str(p) for p in (chunk.get("path") or [chunk.get("title", "")]))


def search(question: str, lang: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Die besten Schnipsel zur Frage (hoechstens `limit`): [{"source": "Seite › Abschnitt", "text": ...}]. Leer, wenn nichts passt."""
    wanted = expand(question, lang)
    if not wanted:
        return []
    index = _index(lang)
    ranked: List[Tuple[float, Dict[str, Any]]] = []
    for chunk in index["items"]:
        s = score(wanted, chunk, index["idf"], 0.0)
        if s >= MIN_SCORE:
            ranked.append((s + USER_PAGES.get(str(chunk.get("page", "")), 0.0), chunk))
    ranked.sort(key=lambda item: -item[0])
    return [{"source": source_of(c), "text": str(c["text"])[:TEXT_LIMIT]} for _, c in ranked[:limit]]


def topics(lang: str) -> List[Dict[str, Any]]:
    """Welche Seiten und Abschnitte es gibt (fuer 'was kannst du erklaeren?'): [{"page": Titel, "sections": [...]}]."""
    pages: Dict[str, List[str]] = {}
    for chunk in load(lang):
        path = chunk.get("path") or []
        if not path:
            continue
        sections = pages.setdefault(path[0], [])
        if len(path) > 1 and path[1] not in sections:
            sections.append(path[1])
    return [{"page": page, "sections": sections[:14]} for page, sections in pages.items()]
