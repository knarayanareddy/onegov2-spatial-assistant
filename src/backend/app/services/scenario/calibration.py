"""Calibration harness (Phase 7, Gap E) — an honest validation story.

A government tool's verdict should come with "has this ever matched a real
assessment?". No external Dunea/Evides capacity study ships in this repo, so the
calibration set here is the design's OWN verified reference figures (ontwerp
Part H): a REPRODUCIBILITY / CONSISTENCY calibration, not external validation.
`validation_status()` says exactly that, and CALIBRATION_CASES is the pluggable
slot to add real external cases later (kind="external-study").
"""
from __future__ import annotations

from app.services.scenario.assumptions import VALIDATION_STATUS_NL
from app.services.scenario.workflow import run_scenario


def validation_status() -> str:
    return VALIDATION_STATUS_NL


# Each case: a question, the EXPECTED verdict + a score band, and the documented
# basis. kind="design-reference" = the engine's own verified figures (consistency);
# add kind="external-study" cases (with a real source) for true external validation.
CALIBRATION_CASES: list[dict] = [
    {
        "name": "Inname Hollandse IJssel — KNMI Hd, 2040 (droogte/verzilting-schok)",
        "question": "Verzilting op de Hollandse IJssel onder KNMI Hd in 2040",
        "expected_verdict": "STOP", "score_band": [70.0, 95.0],
        "basis": "Ontwerpdocument Part H — geverifieerd ~82,4 (STOP)",
        "kind": "design-reference",
        "source": "docs/onegov2_design_v3_repo_aligned.md",
    },
    {
        "name": "Inname Hollandse IJssel — KNMI B, 2040 (geen schok)",
        "question": "Verzilting op de Hollandse IJssel onder KNMI B in 2040",
        "expected_verdict": "CAUTION", "score_band": [38.0, 66.0],
        "basis": "Ontwerpdocument Part H — geverifieerd ~50,5 (CAUTION)",
        "kind": "design-reference",
        "source": "docs/onegov2_design_v3_repo_aligned.md",
    },
]


async def run_calibration(data_dir: str = "data") -> dict:
    """Run each reference case through the engine and report agreement."""
    cases: list[dict] = []
    for c in CALIBRATION_CASES:
        state = await run_scenario(c["question"], data_dir)
        card = state.get("card")
        if card is None:
            cases.append({**_case_meta(c), "actual_verdict": None, "actual_score": None,
                          "verdict_match": False, "score_in_band": False, "note": "geen kaart (followup)"})
            continue
        r = card.results
        lo, hi = c["score_band"]
        cases.append({
            **_case_meta(c),
            "actual_verdict": r.feasibility_class, "actual_score": r.score_avg,
            "verdict_match": r.feasibility_class == c["expected_verdict"],
            "score_in_band": lo <= r.score_avg <= hi,
        })

    n = len(cases)
    n_pass = sum(1 for x in cases if x["verdict_match"])
    return {
        "cases": cases, "n_total": n, "n_pass": n_pass,
        "agreement_pct": round(100.0 * n_pass / n, 1) if n else 0.0,
        "validation_status_nl": validation_status(),
        "kinds": sorted({c["kind"] for c in CALIBRATION_CASES}),
        "note_nl": (
            "Dit is calibratie tegen de eigen geverifieerde ontwerp-referentie "
            "(consistentie/reproduceerbaarheid). Voeg externe cases toe (kind='external-study') "
            "met bron voor echte externe validatie tegen een capaciteitsstudie."),
    }


def _case_meta(c: dict) -> dict:
    return {k: c[k] for k in ("name", "expected_verdict", "score_band", "basis", "kind", "source")}
