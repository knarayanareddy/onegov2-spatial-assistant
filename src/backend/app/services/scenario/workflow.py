"""LangGraph scenario workflow (design doc v3, §9 adapted).

Runs the assumption-driven H3 model on the REAL shipped data via real_scoring —
the synthetic fixture is no longer on the path. Supports single scenarios and
with/without-shock comparison (the brief's Should criterion).
"""
from __future__ import annotations

import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.services.scenario import real_scoring
from app.services.scenario.area import select_h3_area
from app.services.scenario.extraction import extract_scenario_params
from app.services.scenario.models import (
    ReasoningStep, ScenarioCard, ScenarioDelta, ScenarioParams, ScenarioResults,
)
from app.services.scenario.assumptions import ASSUMPTIONS_VERSION, VALIDATION_STATUS_NL
from app.services.scenario.official_positions import get_official_position
from app.services.scenario.scenario_hash import compute_scenario_hash
from app.services.scenario.tracing import annotate, scenario_span

STABLE_URL_BASE = "http://localhost:8001"

# KNMI'23 preset -> dryness multiplier (amplifies salinity pressure). From demand.KNMI_PRESETS.
KNMI_DRYNESS = {"B": 1.0, "Ln": 1.2, "Hn": 1.3, "Ld": 1.5, "Hd": 1.8}

# "Make it feasible" interventions, expressed as assumption deltas (v3: no m3/day).
INTERVENTIONS = [
    {"id": "interconnectie_alternatieve_bron", "label_nl": "Interconnectie / alternatieve inname",
     "delta": {"weight_salinity": 0.25, "weight_flood": 0.4, "weight_protection": 0.35},
     "source_url": "https://www.pzh.nl/regiovisie-waterprogramma-2022-2027",
     "source_label": "Regionaal Waterprogramma ZH 2022–2027"},
    {"id": "klimaatadaptatie_droogte", "label_nl": "Klimaatadaptatie (droogtebuffer)",
     "delta": {"knmi_dryness_multiplier": 1.0},
     "source_url": "https://www.knmi.nl/klimaatscenarios",
     "source_label": "KNMI'23 Klimaatscenario's"},
    {"id": "natuurlijke_spons_intrekgebied", "label_nl": "Natuurlijke spons in intrekgebieden",
     "delta": {"weight_salinity": 0.35, "weight_flood": 0.25, "weight_protection": 0.2},
     "source_url": "https://www.pzh.nl/regiovisie-waterprogramma-2022-2027",
     "source_label": "Regionaal Waterprogramma ZH 2022–2027"},
]


class ScenarioState(TypedDict, total=False):
    question: str
    data_dir: str
    extra_assumptions: dict
    base: str                     # optional universe override: "salinity" | "populated"
    params: ScenarioParams
    confidence: float
    score: dict
    assumptions_used: dict
    interventions_ranked: list
    official_position: dict
    overlays: list
    human_scale: dict
    reasoning_steps: list
    card: ScenarioCard
    followup_nl: str


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


GROWTH_PCT = {"laag": 0.04, "middel": 0.065, "hoog": 0.09}  # Ruimtelijk Arrangement Rijk-ZH


def params_to_assumptions(params: ScenarioParams, extra: dict | None = None) -> dict:
    a: dict[str, Any] = {
        "knmi_dryness_multiplier": KNMI_DRYNESS.get(params.knmi_preset, 1.0),
        "population_growth_pct": GROWTH_PCT.get(params.growth_preset, 0.065),
    }
    # housing development -> added homes (demand lever, brief scenario 3)
    if params.development_units:
        a["added_homes"] = float(params.development_units)
    # housing scenarios are demand-led on the built-up area: weight demand heavily
    if params.development_type and "housing" in params.development_type:
        a.update({"weight_demand": 0.6, "weight_salinity": 0.15, "weight_flood": 0.2,
                  "weight_protection": 0.05, "demand_ref_m3_per_cell": 2.0})
    if extra:
        a.update(extra)
    if params.assumption_overrides:
        a.update(params.assumption_overrides)
    return a


def _step(state, label, desc, datasets=None, value=None, urls=None) -> list:
    steps = list(state.get("reasoning_steps", []))
    steps.append(ReasoningStep(len(steps) + 1, label, desc, datasets or [], value, urls or []))
    return steps


# ---------------------------------------------------------------- nodes
async def extract_node(state: ScenarioState) -> dict:
    # If a caller supplied pre-validated params (e.g. the chatbot's whitelist
    # gate), use them as-is instead of re-extracting — the recipe that runs is
    # exactly the one that was validated. Backward-compatible: absent -> extract.
    provided = state.get("params")
    if provided is not None:
        params = provided
        conf = float(state.get("confidence", 1.0) or 1.0)
    else:
        params, conf = extract_scenario_params(state["question"])
    steps = _step(state, "Vraag begrepen",
                  f"Scenario-type {params.scenario_type}, KNMI {params.knmi_preset}, jaar {params.time_horizon}.",
                  value=f"confidence={conf:.2f}")
    return {"params": params, "confidence": conf, "reasoning_steps": steps}


async def followup_node(state: ScenarioState) -> dict:
    return {"followup_nl": "Ik heb de vraag niet helemaal begrepen. Gaat het om een ruimtelijke "
                           "locatievraag of om een inname/verzilting-scenario?"}


async def score_node(state: ScenarioState) -> dict:
    p: ScenarioParams = state["params"]
    data_dir = state.get("data_dir", "data")
    a = params_to_assumptions(p, state.get("extra_assumptions"))
    # An explicit base override (e.g. the Phase-4 recipe-builder) wins; otherwise
    # housing scenarios default to the populated universe. Backward-compatible.
    override_base = state.get("base")
    is_housing = bool(p.development_type and "housing" in p.development_type)
    use_populated = override_base == "populated" or (override_base is None and is_housing)
    if use_populated:
        # demand scenario: score the built-up universe (where people live), whole region
        base, area_cells = "populated", None
        area_desc = "bebouwd gebied (CBS-bevolkte cellen, hele regio)"
        area_meta = {"mode": "populated", "n": "alle"}
    else:
        base = "salinity"
        area_cells, area_desc, area_meta = select_h3_area(p, data_dir)
    res = real_scoring.score_h3_area(data_dir, a, return_cells=200, area_cells=area_cells, base=base)
    steps = _step(state, "Interessegebied gekozen",
                  f"Gebied: {area_desc}. Scoring beperkt tot deze H3-cellen.",
                  value=f"mode={area_meta['mode']}; cells={area_meta.get('n', 'alle')}")
    steps = _step(
        {"reasoning_steps": steps}, "Gebieds-score (H3)",
        f"DrinkwaterDruk {res['score_avg']:.0f}/100 over {res['n_cells']:,} H3-cellen; "
        f"oordeel {res['area_verdict']} ({res['stop_share'] * 100:.0f}% STOP-cellen). "
        f"Thema's gecombineerd: {', '.join(res['themes_used'])}.",
        datasets=res["themes_used"],
        value=(f"score={res['score_avg']}; verdict={res['area_verdict']}; "
               f"dryness={a['knmi_dryness_multiplier']}; demand_avg={res['demand_avg']}; "
               f"added_homes={a.get('added_homes', 0)}"),
    )
    return {"score": res, "assumptions_used": a, "reasoning_steps": steps}


async def enrich_node(state: ScenarioState) -> dict:
    p: ScenarioParams = state["params"]
    res = state["score"]
    a = state["assumptions_used"]
    data_dir = state.get("data_dir", "data")

    # "Make it feasible": re-score each intervention's assumption delta, rank by STOP-share reduction.
    ranked: list[dict] = []
    if res["area_verdict"] != "GO":
        for iv in INTERVENTIONS:
            r2 = real_scoring.score_h3_area(data_dir, {**a, **iv["delta"]})
            ranked.append({
                "id": iv["id"], "label_nl": iv["label_nl"],
                "new_area_verdict": r2["area_verdict"],
                "stop_share_after": r2["stop_share"],
                "stop_share_reduction_pct": round((res["stop_share"] - r2["stop_share"]) * 100, 1),
                "source_url": iv["source_url"], "source_label": iv["source_label"],
            })
        ranked.sort(key=lambda x: -x["stop_share_reduction_pct"])
        ranked = ranked[:3]

    op = get_official_position(p.scenario_type, p.knmi_preset,
                               involves_housing=(p.development_type == "housing_5000"),
                               involves_krw=True)
    op_serial = {"primary": op["primary"].topic, "disclaimer_nl": op["disclaimer_nl"],
                 "documents": op["primary"].documents}

    area_km2 = round(res["n_stop"] * 0.1, 1)  # res-9 cell ≈ 0.1 km²
    human_scale = {
        "analogy_nl": f"≈ {area_km2:,.0f} km² met hoge drinkwaterdruk (~{res['n_stop']:,} H3-cellen)",
        "analogy_source_url": "/methodology#h3-score",
        "analogy_source_label": "Methodologie (DrinkwaterDruk H3-score)",
    }
    overlays = [{
        "layer_id": "drinkwaterdruk_h3", "label_nl": "DrinkwaterDruk (H3)",
        "type": "H3HexagonLayer", "cells": res.get("cells", []),
        "colorScale": {"GO": "#28a745", "CAUTION": "#ffc107", "STOP": "#dc3545"},
    }]
    return {"interventions_ranked": ranked, "official_position": op_serial,
            "overlays": overlays, "human_scale": human_scale}


async def format_node(state: ScenarioState) -> dict:
    p: ScenarioParams = state["params"]
    res = state["score"]
    sid = str(uuid.uuid4())
    results = ScenarioResults(
        feasibility_class=res["area_verdict"], score_avg=res["score_avg"],
        n_cells=res["n_cells"], n_stop=res["n_stop"], n_caution=res["n_caution"], n_go=res["n_go"],
        stop_share=res["stop_share"], themes_used=res["themes_used"],
        human_scale=state.get("human_scale"), interventions_ranked=state.get("interventions_ranked", []),
    )
    card = ScenarioCard(
        scenario_id=sid,
        scenario_hash=compute_scenario_hash(p, state.get("assumptions_used", {})),
        created_at=datetime.now(timezone.utc).isoformat(),
        git_commit=_git_commit(),
        stable_url=f"{STABLE_URL_BASE}/scenario/{sid}",
        question_nl=state["question"],
        scenario_type=p.scenario_type,
        params=p,
        results=results,
        reasoning_steps=state.get("reasoning_steps", []),
        official_position=state.get("official_position"),
        overlays=state.get("overlays", []),
        assumptions_version=ASSUMPTIONS_VERSION,
        validation_status=VALIDATION_STATUS_NL,
    )
    return {"card": card}


def _route_after_extract(state: ScenarioState) -> str:
    return "score" if state.get("confidence", 0) >= 0.5 else "followup"


def build_scenario_workflow():
    g = StateGraph(ScenarioState)
    g.add_node("extract", extract_node)
    g.add_node("followup", followup_node)
    g.add_node("score", score_node)
    g.add_node("enrich", enrich_node)
    g.add_node("format", format_node)
    g.set_entry_point("extract")
    g.add_conditional_edges("extract", _route_after_extract, {"score": "score", "followup": "followup"})
    g.add_edge("score", "enrich")
    g.add_edge("enrich", "format")
    g.add_edge("format", END)
    g.add_edge("followup", END)
    return g.compile()


scenario_workflow = build_scenario_workflow()


async def run_scenario(question: str, data_dir: str = "data",
                       extra_assumptions: dict | None = None,
                       params: ScenarioParams | None = None,
                       base: str | None = None) -> ScenarioState:
    """Single scenario, end-to-end on real data.

    `params`: optional pre-validated ScenarioParams. When provided the extract
    node uses them verbatim (skips re-extraction) — used by the chatbot's
    validated scenario-from-chat path.
    `base`: optional universe override ("salinity" | "populated"), used by the
    Phase-4 recipe-builder. Absent -> the housing-aware default.
    """
    init: dict = {"question": question, "data_dir": data_dir,
                  "extra_assumptions": extra_assumptions or {}}
    if params is not None:
        init["params"] = params
        init["confidence"] = 1.0
    if base is not None:
        init["base"] = base
    # MLflow tracing (no-op unless MLFLOW_ENABLED) — Should "navolgbaar" axis.
    with scenario_span("scenario_run", question=(question or "")[:80], base=base) as span:
        state = await scenario_workflow.ainvoke(init)
        card = state.get("card")
        if card is not None:
            annotate(span, scenario_type=card.scenario_type, verdict=card.results.feasibility_class,
                     score_avg=card.results.score_avg, scenario_hash=card.scenario_hash)
        return state


def _verdict_rank(v: str) -> int:
    return {"GO": 0, "CAUTION": 1, "STOP": 2}.get(v, 1)


async def run_comparison(question: str, data_dir: str = "data",
                         baseline_extra: dict | None = None,
                         shock_extra: dict | None = None,
                         params: ScenarioParams | None = None) -> dict:
    """With/without-shock comparison (design doc Golden C / brief Should criterion).
    Default: baseline = KNMI B (no shock) vs shock = KNMI Hd (dry + verzilting).
    `params`: optional pre-validated ScenarioParams (shared by both runs)."""
    baseline_extra = baseline_extra if baseline_extra is not None else {"knmi_dryness_multiplier": KNMI_DRYNESS["B"]}
    shock_extra = shock_extra if shock_extra is not None else {"knmi_dryness_multiplier": KNMI_DRYNESS["Hd"]}

    cmp_span = scenario_span("scenario_comparison", question=(question or "")[:80])
    with cmp_span as _span:
        state_a = await run_scenario(question, data_dir, baseline_extra, params=params)
        state_b = await run_scenario(question, data_dir, shock_extra, params=params)
    ra, rb = state_a["card"].results, state_b["card"].results

    change = (f"{ra.feasibility_class} → {rb.feasibility_class}"
              if ra.feasibility_class != rb.feasibility_class else f"blijft {ra.feasibility_class}")
    delta = ScenarioDelta(
        score_avg_delta=round(rb.score_avg - ra.score_avg, 1),
        stop_share_delta=round(rb.stop_share - ra.stop_share, 3),
        n_stop_delta=rb.n_stop - ra.n_stop,
        feasibility_change=change,
        narrative_nl=(
            f"Onder de droogte/verzilting-schok verschuift het oordeel: {change}. "
            f"Het aandeel STOP-cellen gaat van {ra.stop_share * 100:.0f}% naar {rb.stop_share * 100:.0f}%, "
            f"en de gemiddelde DrinkwaterDruk van {ra.score_avg:.0f} naar {rb.score_avg:.0f} (op 100)."
        ),
    )
    state_b["card"].delta = delta.__dict__
    return {"card_a": state_a["card"], "card_b": state_b["card"], "delta": delta}
