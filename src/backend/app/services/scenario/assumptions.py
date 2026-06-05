"""Assumption-library versioning (Phase 7, Gap F).

Assumptions are sourced — but if the weights/thresholds are revised, re-opening an
old scenario could compute a different verdict while the old advies cited the old
model. This pins a VERSION to the sourced library and a CHANGELOG, so a scenario
records "computed under assumption library vX" and "reproduce exactly as advised
on [date]" is answerable. Also the home of the model's VALIDATION status string
(shared by the calibration harness and the citation).
"""
from __future__ import annotations

ASSUMPTIONS_VERSION = "v3.0.0"

ASSUMPTIONS_CHANGELOG: list[dict] = [
    {
        "version": "v3.0.0",
        "date": "2026-06-04",
        "summary": (
            "Initiële gepubliceerde aanname-bibliotheek voor het assumptie-gedreven H3 "
            "DrinkwaterDruk-model: gewichten verzilting/vraag/overstroming/bescherming "
            "0,40/0,30/0,20/0,10; verdict-drempels 33/66; area_stop_share 0,20; "
            "VEWIN-verbruik 0,119 m³/p/d; KNMI-droogtefactor 1,0–1,8; bevolkingsgroei 0,04–0,12."
        ),
        "source": "docs/onegov2_design_v3_repo_aligned.md (Part D)",
    },
]

# What the verdict IS and ISN'T validated against (honest — no external study ships).
VALIDATION_STATUS_NL = (
    "Directioneel gevalideerd tegen de eigen geverifieerde ontwerp-referentiecijfers "
    "(ontwerpdocument Part H); nog NIET vergeleken met een externe capaciteitsstudie "
    "(bijv. Dunea/Evides). Beleidsmatige verkenning, geen gevalideerde voorspelling."
)


def assumption_library() -> dict:
    """The current sourced library + its version + changelog (transparency)."""
    from app.services.scenario.real_scoring import DEFAULT_ASSUMPTIONS
    try:
        from app.services.scenario.workflow import GROWTH_PCT, KNMI_DRYNESS
    except Exception:
        GROWTH_PCT, KNMI_DRYNESS = {}, {}
    return {
        "version": ASSUMPTIONS_VERSION,
        "weights_and_thresholds": dict(DEFAULT_ASSUMPTIONS),
        "knmi_dryness": dict(KNMI_DRYNESS),
        "growth_pct": dict(GROWTH_PCT),
        "changelog": ASSUMPTIONS_CHANGELOG,
        "source": "docs/onegov2_design_v3_repo_aligned.md (Part D)",
        "note_nl": "Elk scenario stempelt deze versie; vergelijk via /verify of de versie sinds opslag is gewijzigd.",
    }
