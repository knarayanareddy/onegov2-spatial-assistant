"""Human-scale analogies — SINGLE SOURCE OF TRUTH.

Fix C4. Keeps the §19.4 metric-aware converter and removes the §7.5/§11.8
household-only variant (the Vue component reads `analogy_source_url`, which
only this variant provides).
"""
from __future__ import annotations

from dataclasses import dataclass

VEWIN_PERSON_DAY_M3 = 0.119      # m3/person/day  (VEWIN Waterstatistiek)
VEWIN_HOUSEHOLD_DAY_M3 = 0.35    # m3/household/day
VEWIN_URL = "https://www.vewin.nl/publicaties/waterstatistiek"
VEWIN_LABEL = "VEWIN Waterstatistiek"

METRIC_CONVERSIONS: dict[str, dict] = {
    "daily_demand_m3": {
        "divisor": VEWIN_PERSON_DAY_M3, "unit_nl": "mensen",
        "template": "dagelijks verbruik van ~{n} {unit}",
    },
    "supply_gap_m3": {
        "divisor": VEWIN_HOUSEHOLD_DAY_M3, "unit_nl": "huishoudens",
        "template": "equivalent aan ~{n} {unit} zonder water",
    },
    "supply_capacity_m3": {
        "divisor": VEWIN_PERSON_DAY_M3, "unit_nl": "mensen",
        "template": "leveringscapaciteit voor ~{n} {unit}",
    },
    "capacity_remaining_m3": {
        "divisor": VEWIN_HOUSEHOLD_DAY_M3, "unit_nl": "extra huishoudens",
        "template": "ruimte voor ~{n} {unit}",
    },
    "development_delta_m3": {
        "divisor": VEWIN_HOUSEHOLD_DAY_M3, "unit_nl": "woningen",
        "template": "extra vraag gelijk aan ~{n} {unit}",
    },
}


@dataclass
class HumanScaleRef:
    metric_key: str
    metric_value: float
    metric_unit: str
    analogy_nl: str
    analogy_source_url: str        # the field name the Vue component reads
    analogy_source_label: str
    is_policy_approx: bool = True


def to_human_scale(
    metric_key: str,
    value: float,
    unit: str,
    divisor_override: float | None = None,
) -> HumanScaleRef:
    """Convert a raw metric to a cited real-world analogy.
    Raises ValueError on an unknown metric (prevents silent empty sources)."""
    if metric_key not in METRIC_CONVERSIONS:
        raise ValueError(
            f"No human-scale conversion defined for metric '{metric_key}'. "
            f"Add an entry to METRIC_CONVERSIONS or handle explicitly."
        )
    conv = METRIC_CONVERSIONS[metric_key]
    divisor = divisor_override or conv["divisor"]
    n = f"{int(abs(value) / divisor):,}".replace(",", ".")  # Dutch thousands separator
    return HumanScaleRef(
        metric_key=metric_key,
        metric_value=value,
        metric_unit=unit,
        analogy_nl=conv["template"].format(n=n, unit=conv["unit_nl"]),
        analogy_source_url=VEWIN_URL,
        analogy_source_label=VEWIN_LABEL,
        is_policy_approx=True,
    )


def attach_human_scale_refs(
    results: dict,
    demand_per_dwelling_override: float | None = None,
) -> dict:
    """Attach a HumanScaleRef to every headline metric present in `results`.
    Called by the format_scenario_output node (GAP 4)."""
    refs: dict[str, dict] = {}
    demand_relative = {"supply_gap_m3", "capacity_remaining_m3", "development_delta_m3"}
    for key in (
        "daily_demand_m3", "supply_gap_m3", "supply_capacity_m3",
        "capacity_remaining_m3", "development_delta_m3",
    ):
        if results.get(key) is None:
            continue
        override = demand_per_dwelling_override if key in demand_relative else None
        try:
            refs[key] = to_human_scale(key, results[key], "m³/dag", override).__dict__
        except ValueError as e:
            refs[key] = {
                "analogy_nl": "Geen omrekening beschikbaar",
                "analogy_source_url": "/methodology",
                "analogy_source_label": "Zie methodologiedocument",
                "is_policy_approx": True,
                "error": str(e),
            }
    results["human_scale_refs"] = refs
    return results
