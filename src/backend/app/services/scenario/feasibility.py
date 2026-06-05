"""Feasibility classification — SINGLE SOURCE OF TRUTH.

Fix C1. Replaces three divergent definitions in the design doc:
  - -5% of demand   (§11.7 ranker, §14.2 stacking)
  - -5% of capacity (§12.3 overlay SQL)
  - fixed -10,000 m3 (§19.5 _compute_single_feasibility_class)

The verdict is demand-relative so it scales correctly between a small
village zone and a large urban one. Every caller must use this function;
the overlay SQL must use the matching CASE in sql/feasibility_overlay.sql.
"""
from __future__ import annotations

# The one tunable: shortfall up to this fraction of daily demand is CAUTION.
CAUTION_BAND = 0.05


def compute_feasibility_class(gap_m3: float, daily_demand_m3: float) -> str:
    """GO / CAUTION / STOP from a supply gap (negative = shortfall)."""
    if daily_demand_m3 <= 0:
        return "GO" if gap_m3 >= 0 else "STOP"
    caution_floor = -CAUTION_BAND * daily_demand_m3
    if gap_m3 >= 0:
        return "GO"
    if gap_m3 >= caution_floor:
        return "CAUTION"
    return "STOP"


def feasibility_by_knmi(
    gaps: dict[str, float],
    demand: dict[str, float],
) -> dict[str, str]:
    """Verdict per KNMI preset. Capacity is constant; the demand peak varies
    by preset, so demand is supplied per-preset."""
    return {
        preset: compute_feasibility_class(gaps[preset], demand.get(preset, 0.0))
        for preset in gaps
    }
