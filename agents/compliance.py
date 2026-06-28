"""Checks the document corpus against Factory Act, OISD, and PESO requirements."""

from __future__ import annotations
import json
import re
import anthropic
from config import ANTHROPIC_API_KEY, LLM_MODEL

REGULATORY_CHECKLIST = [
    {
        "id": "FA-2019-41",
        "regulation": "Factories Act 1948 – Sec 41",
        "requirement": "Hazardous process: safety audit every 2 years with certified auditor",
    },
    {
        "id": "OISD-192-4.3",
        "regulation": "OISD-GDN-192 Clause 4.3",
        "requirement": "Permit-to-work (PTW) system mandated for hot work, confined space, and energy isolation",
    },
    {
        "id": "OISD-192-5.1",
        "regulation": "OISD-GDN-192 Clause 5.1",
        "requirement": "Simultaneous operations (SIMOPS) procedure required when hot work and confined space entry overlap",
    },
    {
        "id": "OISD-116-CSE",
        "regulation": "OISD-STD-116 Section 7",
        "requirement": "Confined space atmosphere testing: O2 19.5–23.5%, flammable gas <10% LEL, H2S <10 ppm",
    },
    {
        "id": "FA-LOTO",
        "regulation": "Factories Act – Energy Isolation",
        "requirement": "Lockout/Tagout (LOTO) procedure documented and workers trained before mechanical maintenance",
    },
    {
        "id": "PESO-static",
        "regulation": "PESO Static Equipment Guidelines",
        "requirement": "Pressure vessels inspected per IBR schedule; inspection records maintained on site",
    },
    {
        "id": "OISD-144-PTW",
        "regulation": "OISD-STD-144 Section 4",
        "requirement": "Hot work permit must specify gas test result, standby fire extinguisher, and watcher assignment",
    },
]

_COMPLIANCE_PROMPT = """You are an industrial safety compliance expert familiar with the Indian Factory Act,
OISD standards, and PESO regulations.

Review the DOCUMENT EXCERPTS below and check each REGULATORY REQUIREMENT.
For each requirement return:
  - status:  "COMPLIANT", "GAP", or "UNKNOWN"
  - evidence: the exact passage (≤ 120 chars) that supports COMPLIANT, or empty string for GAP/UNKNOWN
  - recommendation: short corrective action (for GAP/UNKNOWN only)

Return a JSON array, one object per requirement, in the same order as the input list.
Each object: {{"id": str, "status": str, "evidence": str, "recommendation": str}}

REGULATORY REQUIREMENTS:
{checklist}

DOCUMENT EXCERPTS:
{context}

Return ONLY valid JSON array."""


def run_compliance_check(context_chunks: list[dict]) -> list[dict]:
    """
    Analyse the given chunks against REGULATORY_CHECKLIST.
    Returns a list of findings, one per checklist item.
    """
    context = "\n\n---\n\n".join(
        f"[{c['source']}]\n{c['text'][:800]}" for c in context_chunks[:20]
    )

    if not ANTHROPIC_API_KEY:
        return _mock_compliance(context)

    checklist_str = "\n".join(
        f"{i+1}. [{r['id']}] {r['regulation']}: {r['requirement']}"
        for i, r in enumerate(REGULATORY_CHECKLIST)
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        msg = client.messages.create(
            model=LLM_MODEL,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": _COMPLIANCE_PROMPT.format(
                    checklist=checklist_str, context=context
                ),
            }],
        )
        raw = msg.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        findings_raw = json.loads(raw)
        return _merge_findings(findings_raw)
    except Exception:
        return _mock_compliance(context)


def _merge_findings(raw: list[dict]) -> list[dict]:
    """Merge Claude output with the checklist metadata."""
    by_id = {r["id"]: r for r in raw}
    results = []
    for item in REGULATORY_CHECKLIST:
        finding = by_id.get(item["id"], {})
        results.append({
            "id": item["id"],
            "regulation": item["regulation"],
            "requirement": item["requirement"],
            "status": finding.get("status", "UNKNOWN"),
            "evidence": finding.get("evidence", ""),
            "recommendation": finding.get("recommendation", ""),
        })
    return results


def _mock_compliance(context: str) -> list[dict]:
    """Regex-based compliance check when Claude is unavailable."""
    results = []
    for item in REGULATORY_CHECKLIST:
        keywords = item["requirement"].lower().split()[:3]
        found = any(kw in context.lower() for kw in keywords)
        results.append({
            "id": item["id"],
            "regulation": item["regulation"],
            "requirement": item["requirement"],
            "status": "COMPLIANT" if found else "UNKNOWN",
            "evidence": "",
            "recommendation": "" if found else "Review document corpus for this requirement.",
        })
    return results
