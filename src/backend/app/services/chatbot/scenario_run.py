"""Phase 2 — scenario-from-chat: the validation/whitelist gate.

The hard safety boundary (brief §2): the LLM only maps a free-text request to
ScenarioParams + sourced assumption overrides + a whitelisted area/layer recipe;
the deterministic engine validates and runs it. The LLM NEVER writes or executes
code or SQL. This module is that gate:

  prepare_scenario_request(question) ->
      ScenarioPlan(runnable=True, params=..., compare=..., recipe_summary=...)   # safe to run
    | ScenarioPlan(runnable=False, followup_nl="...")                            # clarify, never run

  execute_plan(plan, question, data_dir) -> runs the EXISTING engine
      (run_scenario / run_comparison) with the pre-validated params.

Anything outside the whitelist — unknown scenario type, unknown KNMI/growth
preset, an unrecognised intake, an out-of-range horizon, an unknown assumption
lever, or low extraction confidence — yields a clarifying question (no dead ends)
and is never executed.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Callable, Optional

from app.services.scenario.extraction import extract_scenario_params
from app.services.scenario.models import ScenarioParams
from app.services.scenario.workflow import KNMI_DRYNESS, run_comparison, run_scenario

# --------------------------------------------------------------------- whitelist
ALLOWED_SCENARIO_TYPES = frozenset({"drop_pin", "intake_failure", "multi_hazard", "intervention"})
ALLOWED_KNMI = frozenset({"B", "Hd", "Hn", "Ld", "Ln"})
ALLOWED_GROWTH = frozenset({"laag", "middel", "hoog"})
# The ONLY assumption-override keys a chat request may set. Mirrors the levers
# params_to_assumptions / real_scoring actually understand.
ALLOWED_LEVER_KEYS = frozenset({
    "knmi_dryness_multiplier", "population_growth_pct", "added_homes",
    "weight_salinity", "weight_demand", "weight_flood", "weight_protection",
    "demand_ref_m3_per_cell",
})
_WEIGHT_KEYS = frozenset({"weight_salinity", "weight_demand", "weight_flood", "weight_protection"})
KNOWN_INTAKES = ("ijssel", "lek", "maas", "hollandse ijssel", "nieuwe maas")
MIN_CONFIDENCE = 0.5
HORIZON_MIN, HORIZON_MAX = 2025, 2100

_COMPARE_TERMS = (
    "vergelijk", "vergelijking", "met en zonder", "met of zonder", "met vs zonder",
    "met versus zonder", "verschil tussen", "zonder schok", "met schok",
    "baseline", "voor en na", "scenario-delta", "delta",
)
_KNMI_IN_TEXT = re.compile(r"\bknmi\s*([A-Za-z]{1,2})\b", re.I)


@dataclass
class ScenarioPlan:
    runnable: bool
    params: Optional[ScenarioParams] = None
    compare: bool = False
    baseline_extra: Optional[dict] = None
    shock_extra: Optional[dict] = None
    confidence: float = 0.0
    followup_nl: Optional[str] = None
    reason: Optional[str] = None                       # machine-readable note
    recipe_summary: dict = field(default_factory=dict)  # scenario_params_confirmed payload


def _clarify(followup: str, reason: str, confidence: float) -> ScenarioPlan:
    return ScenarioPlan(runnable=False, followup_nl=followup, reason=reason, confidence=confidence)


# --------------------------------------------------------------------- validation
def validate_params(params: ScenarioParams, confidence: float) -> Optional[ScenarioPlan]:
    """Return a clarify-ScenarioPlan if the recipe is out of bounds, else None."""
    if confidence < MIN_CONFIDENCE:
        return _clarify(
            "Ik begreep dit scenario niet goed genoeg om het veilig door te rekenen. "
            "Kun je het concreter maken — bijvoorbeeld gebied of innamepunt, KNMI-scenario "
            "(B/Hd/Hn/Ld/Ln) en jaartal?",
            "low_confidence", confidence)

    if params.scenario_type not in ALLOWED_SCENARIO_TYPES:
        return _clarify(
            "Dit scenariotype kan ik niet doorrekenen. Ik ondersteun: een locatie (drop-pin), "
            "een innamestoring, een multi-hazard of een interventie. Welke bedoel je?",
            "bad_scenario_type", confidence)

    if params.knmi_preset not in ALLOWED_KNMI:
        return _clarify(
            "Welk KNMI'23-scenario wil je gebruiken? Kies uit B, Hd, Hn, Ld of Ln.",
            "bad_knmi", confidence)

    if params.growth_preset not in ALLOWED_GROWTH:
        return _clarify(
            "Welke bevolkingsgroei wil je aanhouden — laag, middel of hoog?",
            "bad_growth", confidence)

    if not (HORIZON_MIN <= int(params.time_horizon) <= HORIZON_MAX):
        return _clarify(
            f"Voor welk zichtjaar (tussen {HORIZON_MIN} en {HORIZON_MAX}) wil je het scenario?",
            "bad_horizon", confidence)

    if params.scenario_type == "intake_failure":
        iid = (params.intake_id or "").lower()
        if not iid or not any(k in iid for k in KNOWN_INTAKES):
            return _clarify(
                "Welke inname bedoel je? Ik ken: IJssel, Lek, Maas, Hollandse IJssel of Nieuwe Maas.",
                "unknown_intake", confidence)

    if params.scenario_type == "drop_pin" and not params.location_name:
        return _clarify(
            "Voor welke locatie of gemeente wil je de drop-pin doorrekenen?",
            "missing_location", confidence)

    overrides = params.assumption_overrides or {}
    bad_keys = [k for k in overrides if k not in ALLOWED_LEVER_KEYS]
    if bad_keys:
        return _clarify(
            "Ik kan alleen deze knoppen aanpassen: " + ", ".join(sorted(ALLOWED_LEVER_KEYS)) + ". "
            f"Niet ondersteund: {', '.join(bad_keys)}.",
            "unknown_lever", confidence)
    for k, v in overrides.items():
        if k in _WEIGHT_KEYS and not (0.0 <= float(v) <= 1.0):
            return _clarify(
                f"De weging '{k}' moet tussen 0 en 1 liggen.", "weight_out_of_range", confidence)

    return None


def _detect_comparison(question: str) -> tuple[bool, Optional[dict], Optional[dict]]:
    """(compare, baseline_extra, shock_extra). Defaults to engine's B-vs-Hd when
    comparison is requested without two explicit presets."""
    q = question.lower()
    presets = []
    for m in _KNMI_IN_TEXT.finditer(question):
        p = m.group(1).capitalize()
        if p in ALLOWED_KNMI and p not in presets:
            presets.append(p)
    wants = any(t in q for t in _COMPARE_TERMS) or len(presets) >= 2
    if not wants:
        return False, None, None
    if len(presets) >= 2:
        ranked = sorted(presets, key=lambda p: KNMI_DRYNESS.get(p, 1.0))
        mild, harsh = ranked[0], ranked[-1]
        return True, {"knmi_dryness_multiplier": KNMI_DRYNESS[mild]}, {"knmi_dryness_multiplier": KNMI_DRYNESS[harsh]}
    return True, None, None  # engine default: B vs Hd


def prepare_scenario_request(question: str, *, overrides: Optional[dict] = None,
                             llm_factory: Optional[Callable] = None,
                             use_llm: Optional[bool] = None) -> ScenarioPlan:
    """Extract -> merge any caller overrides -> validate -> detect comparison.
    Returns a runnable plan or a clarify plan. Never runs anything."""
    params, conf = extract_scenario_params(question, use_llm=use_llm, llm_factory=llm_factory)
    if overrides:
        params.assumption_overrides = {**(params.assumption_overrides or {}), **overrides}

    bad = validate_params(params, conf)
    if bad is not None:
        return bad

    compare, baseline_extra, shock_extra = _detect_comparison(question)
    summary = {k: v for k, v in asdict(params).items() if v not in (None, [], {}, 0)}
    summary["compare"] = compare
    return ScenarioPlan(
        runnable=True, params=params, compare=compare,
        baseline_extra=baseline_extra, shock_extra=shock_extra,
        confidence=conf, recipe_summary=summary,
    )


async def execute_plan(plan: ScenarioPlan, question: str, data_dir: str = "data") -> dict:
    """Run the EXISTING engine with the pre-validated params. No code/SQL synthesis."""
    if not plan.runnable or plan.params is None:
        raise ValueError("execute_plan called with a non-runnable plan")
    if plan.compare:
        comp = await run_comparison(question, data_dir, plan.baseline_extra,
                                    plan.shock_extra, params=plan.params)
        return {"mode": "comparison", **comp}
    state = await run_scenario(question, data_dir, params=plan.params)
    return {"mode": "single", "card": state.get("card"), "followup_nl": state.get("followup_nl")}
