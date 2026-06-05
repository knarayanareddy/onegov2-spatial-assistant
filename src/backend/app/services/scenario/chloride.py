"""Chloride concentration + per-intake threshold.

Fixes:
  - S3: replace the hard `min(outage_weeks, 6)` cap (which coincided with the
        6-week golden-path value) with a configurable `outage_cap_weeks`
        (default 12) so longer outages still change the result, while still
        saturating.
  - S2: the threshold query uses the canonical column name `behandel_tech`
        and the added provenance columns `threshold_source` /
        `threshold_last_updated`.
  - S1: intake is identified by a resolved id (see intake.resolve_intake_id),
        not a repeated name LIKE.

KNMI chloride deltas mirror demand.KNMI_PRESETS (kept in sync).
"""
from __future__ import annotations

from typing import Any

KNMI_CL_DELTAS: dict[str, float] = {"B": 0, "Hn": 30, "Hd": 80, "Ln": 20, "Ld": 50}

# S3: configurable, sourced cap (add to DEFAULT_ASSUMPTIONS with a Waterinfo trend source_url)
DEFAULT_OUTAGE_CAP_WEEKS = 12
DEFAULT_DEGRADATION_PER_WEEK = 0.20

# S2 fallback (Drinkwaterbesluit): NL norm 150 mg/L is stricter than EU norm 250 mg/L
CHLORIDE_FALLBACK = {
    "value": 150.0, "value_min": 150.0, "value_max": 250.0,
    "source_url": "https://wetten.overheid.nl/BWBR0026304",
    "source_label": "Drinkwaterbesluit (NL norm 150 mg/L; EU norm 250 mg/L)",
}


def chloride_outage_multiplier(
    outage_weeks: int,
    degradation_per_week: float = DEFAULT_DEGRADATION_PER_WEEK,
    outage_cap_weeks: int = DEFAULT_OUTAGE_CAP_WEEKS,
) -> float:
    """S3 fix: 6w < 10w (no longer frozen equal); saturates at outage_cap_weeks."""
    if outage_weeks <= 0:
        return 1.0
    return 1 + degradation_per_week * min(outage_weeks, outage_cap_weeks)


def effective_chloride(
    baseline_cl_mg_l: float,
    knmi_preset: str,
    outage_weeks: int = 0,
    degradation_per_week: float = DEFAULT_DEGRADATION_PER_WEEK,
    outage_cap_weeks: int = DEFAULT_OUTAGE_CAP_WEEKS,
) -> float:
    """Baseline (live from Waterinfo) + KNMI delta, scaled by outage degradation."""
    base = baseline_cl_mg_l + KNMI_CL_DELTAS.get(knmi_preset, 0)
    return base * chloride_outage_multiplier(outage_weeks, degradation_per_week, outage_cap_weeks)


def get_intake_chloride_threshold(conn: Any, intake_id: str) -> dict:
    """Per-intake threshold from productieketen (GAP 7). S2: selects behandel_tech,
    threshold_source, threshold_last_updated. Falls back to the labelled assumption."""
    row = conn.execute(
        """SELECT cl_threshold_mg_l, behandel_tech, threshold_source, threshold_last_updated
           FROM productieketen
           WHERE intake_id = ? AND cl_threshold_mg_l IS NOT NULL
           LIMIT 1""",
        [intake_id],
    ).fetchone()
    if row and row[0] is not None:
        return {
            "threshold_mg_l": float(row[0]), "treatment_tech": row[1],
            "source": row[2] or "productieketen dataset", "last_updated": row[3],
            "from_db": True, "is_assumption": False, "assumption_label_nl": None,
        }
    return {
        "threshold_mg_l": CHLORIDE_FALLBACK["value"], "treatment_tech": "onbekend",
        "source": CHLORIDE_FALLBACK["source_url"], "last_updated": None,
        "from_db": False, "is_assumption": True,
        "assumption_label_nl": (
            f"Drempelwaarde niet gevonden voor inname '{intake_id}' in productieketen. "
            f"Terugvalwaarde {CHLORIDE_FALLBACK['value']} mg/L gebruikt (Drinkwaterbesluit). "
            f"Pas aan via aanname-slider (bandbreedte 150–250 mg/L)."
        ),
    }
