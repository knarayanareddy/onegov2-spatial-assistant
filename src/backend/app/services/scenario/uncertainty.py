"""Uncertainty band on the verdict (Phase 6) — the false-precision fix.

A single verdict ("STOP at 66.1") hides how close the call was. This sweeps the
scenario across the five KNMI'23 presets (B/Ln/Hn/Ld/Hd, mild -> harsh) and reports
the robustness a policymaker actually needs: the score band, the verdict
distribution ("STOP in 3 van 5"), and whether the call is robust or knife-edge.

Deterministic: reuses run_scenario with a per-preset dryness override.
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

from app.services.scenario.models import ScenarioParams
from app.services.scenario.workflow import KNMI_DRYNESS, run_scenario

KNMI_PRESETS = ["B", "Ln", "Hn", "Ld", "Hd"]   # mild -> harsh
_RANK = {"GO": 0, "CAUTION": 1, "STOP": 2}


async def run_uncertainty(question: str, data_dir: str = "data",
                          params: Optional[ScenarioParams] = None) -> dict:
    presets: dict[str, dict] = {}
    for p in KNMI_PRESETS:
        st = await run_scenario(question, data_dir,
                                extra_assumptions={"knmi_dryness_multiplier": KNMI_DRYNESS[p]},
                                params=params)
        r = st["card"].results
        presets[p] = {"verdict": r.feasibility_class, "score": round(r.score_avg, 1),
                      "stop_share": r.stop_share}

    scores = [v["score"] for v in presets.values()]
    verdicts = [v["verdict"] for v in presets.values()]
    dist = dict(Counter(verdicts))
    n = len(KNMI_PRESETS)
    n_stop, n_caution, n_go = dist.get("STOP", 0), dist.get("CAUTION", 0), dist.get("GO", 0)
    robust = len(set(verdicts)) == 1
    worst = max(verdicts, key=lambda v: _RANK[v])
    best = min(verdicts, key=lambda v: _RANK[v])

    if robust:
        robustness = "robuust"
    elif n_go and n_stop:
        robustness = "wankel (knife-edge)"   # spans GO..STOP
    else:
        robustness = "matig robuust"

    narrative = (
        f"Het oordeel varieert over de vijf KNMI'23-scenario's: STOP in {n_stop} van {n}, "
        f"CAUTION in {n_caution}, GO in {n_go}. Score-bandbreedte {min(scores):.0f}–{max(scores):.0f} "
        f"(op 100). Robuustheid: {robustness}; zwaarste scenario {worst}, lichtste {best}."
    )
    return {
        "axis": "knmi", "presets": presets,
        "score_min": round(min(scores), 1), "score_max": round(max(scores), 1),
        "score_mean": round(sum(scores) / n, 1),
        "verdict_distribution": dist, "n_total": n,
        "n_stop": n_stop, "n_caution": n_caution, "n_go": n_go,
        "worst_case": worst, "best_case": best, "robust": robust,
        "robustness_nl": robustness, "narrative_nl": narrative,
        "headline_nl": f"{worst} — {robustness} ({n_stop}/{n} STOP)",
    }
