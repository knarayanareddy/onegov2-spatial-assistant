"""Demand projection.

Fix B5: the cosmetic `np.random.seed(42)` is removed — the calculation is
pure arithmetic with no random draws, so the seed was misleading. Determinism
comes from the parameter hash (C2) and pinned GreenPT temperature (S7).

The KNMI / growth / development constants are included here so this module is
self-contained.
"""
from __future__ import annotations

# KNMI'23 presets: per-scenario drought frequency, chloride delta, peak multiplier.
KNMI_PRESETS: dict[str, dict] = {
    "B":  {"drought_freq": 1.0, "cl_delta": 0,  "peak_multiplier": 1.00, "low_flow_weeks": 0},
    "Hn": {"drought_freq": 1.3, "cl_delta": 30, "peak_multiplier": 1.08, "low_flow_weeks": 2},
    "Hd": {"drought_freq": 1.8, "cl_delta": 80, "peak_multiplier": 1.15, "low_flow_weeks": 6},
    "Ln": {"drought_freq": 1.2, "cl_delta": 20, "peak_multiplier": 1.05, "low_flow_weeks": 1},
    "Ld": {"drought_freq": 1.5, "cl_delta": 50, "peak_multiplier": 1.10, "low_flow_weeks": 4},
}

GROWTH_PRESETS: dict[str, dict] = {
    "laag":   {"demand_delta_pct": 0.040},
    "middel": {"demand_delta_pct": 0.065},
    "hoog":   {"demand_delta_pct": 0.090},
}

DEVELOPMENT_DEMAND: dict[str, dict] = {
    "datacenter_50mw": {"formula": "mw * multiplier", "default_mw": 50.0,
                        "multiplier_default": 12.0, "multiplier_min": 5.0, "multiplier_max": 20.0,
                        "assumption_key": "datacenter_m3_per_mw_day"},
    "housing_5000":    {"formula": "units * demand_per_unit", "default_units": 5000,
                        "demand_per_unit_default": 0.35, "demand_per_unit_min": 0.28,
                        "demand_per_unit_max": 0.42, "assumption_key": "demand_per_dwelling_m3_day"},
}

# Peak-demand buffer factor (VEWIN); KNMI preset can override upward.
PEAK_BUFFER_DEFAULT, PEAK_BUFFER_MIN, PEAK_BUFFER_MAX = 1.15, 1.05, 1.30


def calculate_daily_demand(
    baseline_m3_per_day: float,
    growth_preset: str,
    knmi_preset: str,
    development_type: str | None,
    development_params: dict,
    assumption_overrides: dict[str, float] | None = None,
) -> tuple[float, float, float]:
    """Return (point_estimate, range_min, range_max) in m3/day. Deterministic."""
    growth = GROWTH_PRESETS[growth_preset]
    knmi = KNMI_PRESETS[knmi_preset]
    overrides = assumption_overrides or {}

    growth_fraction = growth["demand_delta_pct"]
    peak = max(overrides.get("peak_demand_buffer_factor", PEAK_BUFFER_DEFAULT), knmi["peak_multiplier"])

    dev_delta = dev_min = dev_max = 0.0
    if development_type and development_type in DEVELOPMENT_DEMAND:
        dev = DEVELOPMENT_DEMAND[development_type]
        if dev["formula"] == "mw * multiplier":
            mw = development_params.get("mw", dev["default_mw"])
            mult = overrides.get(dev["assumption_key"], dev["multiplier_default"])
            dev_delta, dev_min, dev_max = mw * mult, mw * dev["multiplier_min"], mw * dev["multiplier_max"]
        elif dev["formula"] == "units * demand_per_unit":
            units = development_params.get("units", dev["default_units"])
            rate = overrides.get(dev["assumption_key"], dev["demand_per_unit_default"])
            dev_delta = units * rate
            dev_min, dev_max = units * dev["demand_per_unit_min"], units * dev["demand_per_unit_max"]

    point = baseline_m3_per_day * (1 + growth_fraction) * peak + dev_delta
    range_min = baseline_m3_per_day * (1 + growth_fraction * 0.8) * PEAK_BUFFER_MIN + dev_min
    range_max = baseline_m3_per_day * (1 + growth_fraction * 1.2) * PEAK_BUFFER_MAX + dev_max
    return point, range_min, range_max
