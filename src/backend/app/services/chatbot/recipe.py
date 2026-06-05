"""Phase 4 — declarative recipe-builder.

A "recipe" is DATA, not code: a whitelisted combination of the H3 composite
signal weights (salinity / demand / flood / protection) plus presets, validated
and mapped onto the existing deterministic engine. It is the structured sibling
of the Phase-2 free-text path — same safety boundary (no code/SQL synthesis; only
known levers in known ranges), surfaced as explicit knobs a UI can render.

  recipe_schema()       -> the available signals/weights/presets/ranges (for a form)
  validate_recipe(spec) -> RecipePlan(runnable=True, params=..., base=...)  | clarify
  execute_recipe(plan)  -> runs the engine with the validated recipe

Weights must sum to 1 (within a small tolerance) — an off-balance recipe is
rejected with a clarifying message rather than silently normalised.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.services.scenario.models import ScenarioParams
from app.services.scenario.real_scoring import DEFAULT_ASSUMPTIONS
from app.services.scenario.workflow import run_scenario
from app.services.chatbot.scenario_run import (
    ALLOWED_GROWTH,
    ALLOWED_KNMI,
    HORIZON_MAX,
    HORIZON_MIN,
    KNOWN_INTAKES,
)

# signal key -> the assumption weight it controls + a Dutch label + the real layer.
SIGNALS = {
    "salinity":   {"weight_key": "weight_salinity",   "label_nl": "Verzilting",        "layer": "verzilting.ZOUT_CONC"},
    "demand":     {"weight_key": "weight_demand",      "label_nl": "Vraag (CBS)",       "layer": "cbs_vierkantstatistieken"},
    "flood":      {"weight_key": "weight_flood",       "label_nl": "Overstroming",      "layer": "overstromingen_kwetsbaarheid"},
    "protection": {"weight_key": "weight_protection",  "label_nl": "Beschermingszone",  "layer": "zes_uur_zones_drinkwater"},
}
ALLOWED_SIGNALS = frozenset(SIGNALS)
ALLOWED_BASE = frozenset({"salinity", "populated"})
WEIGHT_SUM_TOL = 0.01


@dataclass
class RecipePlan:
    runnable: bool
    params: Optional[ScenarioParams] = None
    base: str = "salinity"
    followup_nl: Optional[str] = None
    reason: Optional[str] = None
    recipe_summary: dict = field(default_factory=dict)


def recipe_schema() -> dict:
    """Describe the recipe surface so a UI can build a form. Defaults come from
    the engine's sourced DEFAULT_ASSUMPTIONS."""
    return {
        "signals": [
            {"key": k, "weight_key": v["weight_key"], "label_nl": v["label_nl"],
             "layer": v["layer"], "default": DEFAULT_ASSUMPTIONS[v["weight_key"]]}
            for k, v in SIGNALS.items()
        ],
        "knmi_presets": sorted(ALLOWED_KNMI),
        "growth_presets": sorted(ALLOWED_GROWTH),
        "base_options": sorted(ALLOWED_BASE),
        "known_intakes": ["IJssel", "Lek", "Maas", "Hollandse IJssel", "Nieuwe Maas"],
        "constraints": {
            "weights_sum": 1.0, "weights_sum_tolerance": WEIGHT_SUM_TOL,
            "weight_range": [0.0, 1.0], "time_horizon": [HORIZON_MIN, HORIZON_MAX],
            "added_homes_min": 0,
        },
        "notes_nl": (
            "Een recept combineert de H3-lagen met wegingen die optellen tot 1. "
            "Het wordt gevalideerd en door de deterministische engine doorgerekend — geen code."
        ),
    }


def _clarify(followup: str, reason: str) -> RecipePlan:
    return RecipePlan(runnable=False, followup_nl=followup, reason=reason)


def validate_recipe(spec: dict) -> RecipePlan:
    weights = spec.get("weights") or {}

    bad_keys = [k for k in weights if k not in ALLOWED_SIGNALS]
    if bad_keys:
        return _clarify(
            "Onbekende signalen: " + ", ".join(bad_keys) + ". Toegestaan: "
            + ", ".join(sorted(ALLOWED_SIGNALS)) + ".", "unknown_signal")

    for k, v in weights.items():
        try:
            v = float(v)
        except (TypeError, ValueError):
            return _clarify(f"Weging '{k}' moet een getal zijn.", "weight_not_number")
        if not (0.0 <= v <= 1.0):
            return _clarify(f"Weging '{k}' moet tussen 0 en 1 liggen.", "weight_out_of_range")

    total = sum(float(weights.get(k, 0.0)) for k in ALLOWED_SIGNALS)
    if abs(total - 1.0) > WEIGHT_SUM_TOL:
        return _clarify(
            f"De wegingen moeten samen optellen tot 1 (nu {total:.2f}). "
            f"Pas de wegingen voor verzilting, vraag, overstroming en beschermingszone aan.",
            "weights_sum")

    knmi = str(spec.get("knmi_preset", "Hd"))
    if knmi not in ALLOWED_KNMI:
        return _clarify("Kies een KNMI-scenario: B, Hd, Hn, Ld of Ln.", "bad_knmi")

    growth = str(spec.get("growth_preset", "middel"))
    if growth not in ALLOWED_GROWTH:
        return _clarify("Kies bevolkingsgroei: laag, middel of hoog.", "bad_growth")

    base = str(spec.get("base", "salinity"))
    if base not in ALLOWED_BASE:
        return _clarify("Kies een gebiedsuniversum: salinity of populated.", "bad_base")

    try:
        horizon = int(spec.get("time_horizon", 2040))
    except (TypeError, ValueError):
        return _clarify("Geef een geldig zichtjaar.", "bad_horizon")
    if not (HORIZON_MIN <= horizon <= HORIZON_MAX):
        return _clarify(f"Kies een zichtjaar tussen {HORIZON_MIN} en {HORIZON_MAX}.", "bad_horizon")

    try:
        added_homes = float(spec.get("added_homes", 0) or 0)
    except (TypeError, ValueError):
        return _clarify("Aantal extra woningen moet een getal zijn.", "bad_added_homes")
    if added_homes < 0:
        return _clarify("Aantal extra woningen kan niet negatief zijn.", "bad_added_homes")

    intake = spec.get("intake_id")
    location = spec.get("location_name")
    if intake:
        if not any(k in str(intake).lower() for k in KNOWN_INTAKES):
            return _clarify(
                "Onbekende inname. Ik ken: IJssel, Lek, Maas, Hollandse IJssel of Nieuwe Maas.",
                "unknown_intake")
        scenario_type = "intake_failure"
    elif location:
        scenario_type = "drop_pin"
    else:
        scenario_type = "multi_hazard"   # whole region, weighted multi-layer composite

    overrides: dict[str, float] = {
        SIGNALS[k]["weight_key"]: float(weights.get(k, 0.0)) for k in ALLOWED_SIGNALS
    }
    if added_homes:
        overrides["added_homes"] = added_homes

    params = ScenarioParams(
        scenario_type=scenario_type, knmi_preset=knmi, time_horizon=horizon,
        growth_preset=growth, location_name=location, intake_id=intake,
        assumption_overrides=overrides,
    )
    summary = {
        "weights": {k: float(weights.get(k, 0.0)) for k in ALLOWED_SIGNALS},
        "knmi_preset": knmi, "growth_preset": growth, "base": base,
        "time_horizon": horizon, "added_homes": added_homes,
        "scenario_type": scenario_type, "location_name": location, "intake_id": intake,
    }
    return RecipePlan(runnable=True, params=params, base=base, recipe_summary=summary)


def _question_nl(summary: dict) -> str:
    w = summary["weights"]
    parts = ", ".join(f"{SIGNALS[k]['label_nl']} {w[k]:.2f}" for k in SIGNALS)
    return (f"Recept ({summary['scenario_type']}, universum {summary['base']}, "
            f"KNMI {summary['knmi_preset']}, {summary['time_horizon']}): wegingen {parts}.")


async def execute_recipe(plan: RecipePlan, data_dir: str = "data") -> dict:
    """Run the existing engine with the validated recipe. No code/SQL synthesis."""
    if not plan.runnable or plan.params is None:
        raise ValueError("execute_recipe called with a non-runnable plan")
    question = _question_nl(plan.recipe_summary)
    state = await run_scenario(question, data_dir, params=plan.params, base=plan.base)
    return {"mode": "single", "card": state.get("card"), "followup_nl": state.get("followup_nl")}
