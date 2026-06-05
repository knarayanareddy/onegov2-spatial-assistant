"""Intervention catalogue, ranking and stacking — SINGLE SOURCE OF TRUTH.

Fix C3 (+ B2 buffer model). Replaces:
  - §11.7 dict catalogue (keys buffer_30000; supply_delta_m3_day/implementation_years)
  - §19.5 list catalogue (ids buffer_30k; supply_delta_m3/lead_time_years)

One list, stable ids, unified field names, applicable_types. The buffer
(B2 fix) is modelled as a stored VOLUME drawn over a planning WINDOW, so its
daily contribution is ~1,000 m3/day, not 30,000. effective_supply_delta() is
the only place that math lives; the ranker and stacker both call it.
"""
from __future__ import annotations

from app.services.scenario.feasibility import compute_feasibility_class

INTERVENTION_CATALOGUE: list[dict] = [
    {
        "id": "buffer_30k",
        "label_nl": "Bufferopslag 30.000 m³",
        # B2 FIX: 30,000 m3 buffer drawn over a 30-day window ≈ 1,000 m3/day sustained,
        # NOT 30,000 m3/day. planning_window_days is a sourced, slider-adjustable assumption.
        "buffer_volume_m3": 30_000,
        "planning_window_days": 30,
        "supply_delta_m3_day": None,
        "demand_delta_fraction": 0.0,
        "supply_delta_range": (800, 1_200),
        "cost_eur_low": 15_000_000,
        "cost_eur_high": 25_000_000,
        "lead_time_years": 3,
        "source_url": "https://www.pzh.nl/regiovisie-waterprogramma-2022-2027",
        "source_label": "Regionaal Waterprogramma ZH 2022–2027",
        "applicable_types": ["drop_pin", "intake_failure", "multi_hazard"],
    },
    {
        "id": "alt_intake_lek",
        "label_nl": "Alternatieve inname via de Lek",
        "supply_delta_m3_day": 65_000,
        "demand_delta_fraction": 0.0,
        "supply_delta_range": (50_000, 80_000),
        "cost_eur_low": 40_000_000,
        "cost_eur_high": 100_000_000,
        "lead_time_years": 7,
        "source_url": "https://www.pzh.nl/regiovisie-waterprogramma-2022-2027",
        "source_label": "Regionaal Waterprogramma ZH 2022–2027",
        "applicable_types": ["intake_failure", "multi_hazard"],
    },
    {
        "id": "demand_restriction_10pct",
        "label_nl": "Vraagbeperking 10% (regelgeving)",
        "supply_delta_m3_day": 0.0,
        "demand_delta_fraction": -0.10,  # reduces demand by 10%
        "cost_eur_low": 0,
        "cost_eur_high": 500_000,
        "lead_time_years": 1,
        "source_url": "https://wetten.overheid.nl/BWBR0026306",
        "source_label": "Drinkwaterwet, art. 10",
        "applicable_types": ["drop_pin", "intake_failure", "multi_hazard"],
    },
    {
        "id": "interconnect_neighbor",
        "label_nl": "Interconnectie met buurregio",
        "supply_delta_m3_day": 30_000,
        "demand_delta_fraction": 0.0,
        "supply_delta_range": (20_000, 40_000),
        "cost_eur_low": 20_000_000,
        "cost_eur_high": 60_000_000,
        "lead_time_years": 5,
        "source_url": "https://www.vewin.nl/publicaties/infrastructuurrapport-2023",
        "source_label": "VEWIN Infrastructuurrapport 2023",
        "applicable_types": ["drop_pin", "intake_failure", "multi_hazard"],
    },
]

CATALOGUE_BY_ID: dict[str, dict] = {i["id"]: i for i in INTERVENTION_CATALOGUE}


def effective_supply_delta(intv: dict, daily_demand_m3: float) -> float:
    """Daily m3 a single intervention adds to supply (or removes from demand).
    The only place this math lives."""
    if intv.get("buffer_volume_m3"):  # volume / window  (B2 fix)
        return intv["buffer_volume_m3"] / intv["planning_window_days"]
    if intv.get("supply_delta_m3_day"):  # fixed supply-side delta
        return intv["supply_delta_m3_day"]
    if intv.get("demand_delta_fraction"):  # demand-side (negative fraction)
        return abs(intv["demand_delta_fraction"]) * daily_demand_m3
    return 0.0


def rank_interventions(
    gap_m3: float,
    daily_demand_m3: float,
    scenario_type: str,
) -> list[dict]:
    """Top-3 applicable interventions by gap-closure %, then shortest lead time.
    Empty if the scenario is already GO."""
    if gap_m3 >= 0:
        return []
    ranked: list[dict] = []
    for intv in INTERVENTION_CATALOGUE:
        if scenario_type not in intv["applicable_types"]:
            continue
        delta = effective_supply_delta(intv, daily_demand_m3)
        new_gap = gap_m3 + delta
        ranked.append(
            {
                "id": intv["id"],
                "label_nl": intv["label_nl"],
                "gap_closure_pct": min(100.0, delta / abs(gap_m3) * 100),
                "new_supply_gap_m3": new_gap,
                "new_feasibility_class": compute_feasibility_class(new_gap, daily_demand_m3),
                "cost_range_eur": (intv["cost_eur_low"], intv["cost_eur_high"]),
                "lead_time_years": intv["lead_time_years"],
                "source_url": intv["source_url"],
                "source_label": intv["source_label"],
            }
        )
    ranked.sort(key=lambda x: (-x["gap_closure_pct"], x["lead_time_years"]))
    return ranked[:3]


def stack_interventions(
    baseline_gap_m3: float,
    daily_demand_m3: float,
    intervention_ids: list[str],
) -> dict:
    """Apply interventions cumulatively (Type 4). Same catalogue, same
    feasibility function as everything else."""
    running_gap = baseline_gap_m3
    steps: list[dict] = []
    for iid in intervention_ids:
        intv = CATALOGUE_BY_ID.get(iid)
        if not intv:
            continue
        running_gap += effective_supply_delta(intv, daily_demand_m3)
        steps.append(
            {
                "id": iid,
                "label_nl": intv["label_nl"],
                "cumulative_gap_m3": running_gap,
                "feasibility_class": compute_feasibility_class(running_gap, daily_demand_m3),
            }
        )
    return {
        "baseline_gap_m3": baseline_gap_m3,
        "final_gap_m3": running_gap,
        "final_feasibility_class": compute_feasibility_class(running_gap, daily_demand_m3),
        "achieves_go": running_gap >= 0,
        "steps": steps,
    }
