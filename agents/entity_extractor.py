"""
entity_extractor.py
-------------------
Extracts industrial entities from document chunks using Claude + regex fallback.

Entities we care about:
  - Equipment tags  (P-101, V-202, HE-301, C-401, …)
  - Regulations     (Factory Act, OISD-GDN-192, PESO, …)
  - Persons / roles (shift supervisor, safety officer, …)
  - Processes       (confined space entry, LOTO, hot work, …)
  - Parameters      (85 °C, 7.1 mm/s, 450 m3/h, …)

Relationships we infer:
  equipment → HAS_PROCEDURE → procedure
  procedure → GOVERNED_BY  → regulation
  equipment → LOCATED_IN   → location
  equipment → MAINTAINED_BY → person/role
"""

from __future__ import annotations
import json
import re
import anthropic
from config import ANTHROPIC_API_KEY, LLM_MODEL

# Regex patterns are our guaranteed fallback (no API key needed)
_EQUIPMENT_RE = re.compile(
    r"\b([A-Z]{1,3}-\d{2,4}[A-Z]?)\b"       # P-101, HE-302A
)
_REGULATION_RE = re.compile(
    r"\b(OISD[- ]\w+|Factory Act|PESO|DGMS|MSIHC|IS[: ]\d+)\b", re.I
)
_PARAMETER_RE = re.compile(
    r"\b(\d+(?:\.\d+)?\s*(?:°C|bar[ag]?|mm/s|ppm|m3/h|kW|rpm|%\s*LEL|%\s*O2))\b"
)
_PROCESS_RE = re.compile(
    r"\b(LOTO|lock[- ]?out|tag[- ]?out|hot[- ]?work|confined[- ]?space|"
    r"permit[- ]?to[- ]?work|PTW|shutdown|overhaul|purging|blinding)\b", re.I
)

_EXTRACT_PROMPT = """Extract ALL industrial entities from the following text.
Return a JSON object with these keys:
  equipment   : list of equipment tag strings  (e.g. ["P-101", "D-204"])
  regulations : list of regulation names        (e.g. ["OISD-GDN-192", "Factory Act"])
  processes   : list of operational process names
  parameters  : list of process parameter strings (e.g. ["85 °C", "7.1 mm/s"])
  locations   : list of plant location names
  relationships: list of {from, relation, to} dicts

TEXT:
{text}

Return ONLY valid JSON, no markdown."""


def extract_entities(text: str) -> dict:
    """
    Extract entities from `text`.
    Uses Claude when available; regex-only when no API key.
    """
    if ANTHROPIC_API_KEY:
        return _extract_with_claude(text)
    return _extract_with_regex(text)


def _extract_with_claude(text: str) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        msg = client.messages.create(
            model=LLM_MODEL,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": _EXTRACT_PROMPT.format(text=text[:4000]),
            }],
        )
        raw = msg.content[0].text.strip()
        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        return _merge_with_regex(text, data)
    except Exception:
        return _extract_with_regex(text)


def _extract_with_regex(text: str) -> dict:
    return {
        "equipment": list(dict.fromkeys(_EQUIPMENT_RE.findall(text))),
        "regulations": list(dict.fromkeys(m.group() for m in _REGULATION_RE.finditer(text))),
        "processes": list(dict.fromkeys(m.group() for m in _PROCESS_RE.finditer(text))),
        "parameters": list(dict.fromkeys(m.group() for m in _PARAMETER_RE.finditer(text))),
        "locations": [],
        "relationships": _infer_relationships(text),
    }


def _merge_with_regex(text: str, claude_data: dict) -> dict:
    """Add any regex hits that Claude missed."""
    regex_data = _extract_with_regex(text)
    for key in ("equipment", "regulations", "processes", "parameters"):
        existing = set(claude_data.get(key, []))
        for item in regex_data.get(key, []):
            if item not in existing:
                claude_data.setdefault(key, []).append(item)
    if not claude_data.get("relationships"):
        claude_data["relationships"] = regex_data["relationships"]
    return claude_data


def _infer_relationships(text: str) -> list[dict]:
    """Heuristic relationship extraction from co-occurrence within sentences."""
    rels: list[dict] = []
    sentences = re.split(r"[.!\?]\s+", text)
    for sent in sentences:
        equip = _EQUIPMENT_RE.findall(sent)
        regs  = [m.group() for m in _REGULATION_RE.finditer(sent)]
        procs = [m.group() for m in _PROCESS_RE.finditer(sent)]

        for e in equip:
            for r in regs:
                rels.append({"from": e, "relation": "GOVERNED_BY", "to": r})
            for p in procs:
                rels.append({"from": e, "relation": "HAS_PROCEDURE", "to": p})

    return rels
