"""Detailed A/B scenario comparison (design doc §16 extension).

Compares any two scenarios — each given either by a saved ``scenario_id`` or by
an inline custom ``assumptions`` set — over a SHARED H3 universe, so the cells
line up and the consequences can be attributed in detail:

  * per-factor attribution: how much each factor (salinity / flood / protection /
    demand) contributes to the average-score change between A and B;
  * per-cell diff: score_a vs score_b per H3 cell, with verdict transitions
    (e.g. GO -> STOP) and the cells that move the most.

Why a shared universe? Per-cell and per-factor attribution are only meaningful
when both sides score the *same* cells. The universe (base + area) is taken from
side A (or from an explicit request override); side B's assumptions are then
scored over that same universe. This is the "what does changing the assumptions
do to THIS area" comparison — the high-value case the brief asks for.

This module reuses the canonical scorer (real_scoring.score_cells_components),
so the factor terms always sum to the same DrinkwaterDruk score the rest of the
engine reports — attribution can never silently drift from the verdict.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from app.services.scenario import real_scoring
from app.services.scenario.area import select_h3_area
from app.services.scenario.models import ScenarioDelta, ScenarioParams
from app.services.scenario.workflow import params_to_assumptions

# factor -> Dutch label for narratives / UI
FACTOR_NL: dict[str, str] = {
    "salinity": "verzilting",
    "flood": "overstroming",
    "protection": "drinkwaterbescherming",
    "demand": "vraag/bevolking",
}


def resolve_side(spec: dict, data_dir: str, store: Any | None) -> dict:
    """Turn a comparison-side spec into (label, question, params, assumptions).

    spec = {"scenario_id": "..."} OR {"assumptions": {...}, "question"?, "label"?}.
    A saved scenario's effective assumptions are reconstructed from its stored
    params exactly the way the engine produced them (params_to_assumptions),
    mirroring the /verify re-run path.
    """
    sid = spec.get("scenario_id")
    if sid:
        if store is None:
            raise ValueError(f"Scenario {sid}: geen opslag beschikbaar.")
        cached = store.get_by_id(sid)
        if not cached:
            raise ValueError(f"Scenario {sid} niet gevonden.")
        raw = cached["result_json"]
        card = json.loads(raw) if isinstance(raw, str) else raw
        try:
            params = ScenarioParams(**card.get("params", {}))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Scenario {sid}: parameters niet herleidbaar.") from exc
        assumptions = params_to_assumptions(params)
        label = spec.get("label") or (card.get("question_nl") or "")[:60] or sid[:8]
        return {"label": label, "question": card.get("question_nl", ""),
                "params": params, "assumptions": assumptions}

    # inline custom assumptions
    assumptions = dict(spec.get("assumptions") or {})
    return {"label": spec.get("label") or "Aangepast", "question": spec.get("question") or "",
            "params": None, "assumptions": assumptions}


def resolve_universe(params: ScenarioParams | None, data_dir: str,
                     base_override: str | None = None,
                     area_override: list[str] | None = None) -> tuple[str, list[str] | None]:
    """Shared scoring universe (base + area_cells), mirroring workflow.score_node.

    An explicit override wins; otherwise housing scenarios use the populated
    universe and everything else uses the salinity universe with the scenario's
    selected H3 area.
    """
    if area_override is not None:
        return (base_override or "salinity"), area_override
    is_housing = bool(params and params.development_type and "housing" in params.development_type)
    if base_override == "populated" or (base_override is None and is_housing):
        return "populated", None
    base = base_override or "salinity"
    if params is None:
        return base, None
    area_cells, _, _ = select_h3_area(params, data_dir)
    return base, area_cells


def _aggregate(cells: list[dict], a_full: dict) -> dict:
    """Area-level verdict over a cell set (same rule as real_scoring.score_h3_area)."""
    n = len(cells)
    if not n:
        return {"n_cells": 0, "score_avg": 0.0, "n_stop": 0, "n_caution": 0,
                "n_go": 0, "stop_share": 0.0, "feasibility_class": "GO"}
    stop, caution = a_full["verdict_stop"], a_full["verdict_caution"]
    n_stop = sum(1 for c in cells if c["score"] >= stop)
    n_caution = sum(1 for c in cells if caution <= c["score"] < stop)
    n_go = n - n_stop - n_caution
    stop_share = n_stop / n
    verdict = ("STOP" if stop_share >= a_full["area_stop_share"]
               else "CAUTION" if (n_stop + n_caution) > 0 else "GO")
    return {"n_cells": n, "score_avg": round(sum(c["score"] for c in cells) / n, 1),
            "n_stop": n_stop, "n_caution": n_caution, "n_go": n_go,
            "stop_share": round(stop_share, 3), "feasibility_class": verdict}


def _factor_means(cells: list[dict]) -> dict[str, float]:
    n = len(cells) or 1
    return {f: sum(c[f] for c in cells) / n for f in real_scoring.FACTORS}


def compare_scenarios(spec_a: dict, spec_b: dict, data_dir: str, store: Any | None = None,
                      base: str | None = None, area_cells: list[str] | None = None,
                      top_n: int = 25) -> dict:
    """Full detailed comparison of two scenarios over a shared universe."""
    side_a = resolve_side(spec_a, data_dir, store)
    side_b = resolve_side(spec_b, data_dir, store)

    sbase, sarea = resolve_universe(side_a["params"], data_dir, base, area_cells)
    area_source = "request" if (base is not None or area_cells is not None) else (
        "A" if side_a["params"] is not None else "default")

    a_full = {**real_scoring.DEFAULT_ASSUMPTIONS, **side_a["assumptions"]}
    b_full = {**real_scoring.DEFAULT_ASSUMPTIONS, **side_b["assumptions"]}

    cells_a = real_scoring.score_cells_components(data_dir, side_a["assumptions"], sarea, sbase)
    cells_b = real_scoring.score_cells_components(data_dir, side_b["assumptions"], sarea, sbase)
    ib = {c["h3_id"]: c for c in cells_b}

    agg_a = _aggregate(cells_a, a_full)
    agg_b = _aggregate(cells_b, b_full)

    # per-factor attribution of the mean-score change
    fa, fb = _factor_means(cells_a), _factor_means(cells_b)
    deltas = {f: fb[f] - fa[f] for f in real_scoring.FACTORS}
    tot_abs = sum(abs(d) for d in deltas.values()) or 1.0
    attribution = [{
        "factor": f, "factor_nl": FACTOR_NL[f],
        "mean_a": round(fa[f], 2), "mean_b": round(fb[f], 2),
        "delta": round(deltas[f], 2),
        "share_of_change_pct": round(deltas[f] / tot_abs * 100, 1),
    } for f in real_scoring.FACTORS]

    # per-cell diff over the shared (identical) universe
    diffs: list[dict] = []
    for c in cells_a:
        h = c["h3_id"]
        cb = ib.get(h)
        if cb is None:
            continue
        sa, sb = c["score"], cb["score"]
        diffs.append({
            "h3_id": h, "score_a": sa, "score_b": sb, "delta": round(sb - sa, 1),
            "klasse_a": real_scoring.verdict_from_score(sa, a_full),
            "klasse_b": real_scoring.verdict_from_score(sb, b_full),
        })

    transitions: dict[tuple[str, str], int] = {}
    for d in diffs:
        if d["klasse_a"] != d["klasse_b"]:
            key = (d["klasse_a"], d["klasse_b"])
            transitions[key] = transitions.get(key, 0) + 1
    transitions_list = sorted(
        [{"from": k[0], "to": k[1], "n": v} for k, v in transitions.items()],
        key=lambda x: -x["n"],
    )

    n_worsened = sum(1 for d in diffs if d["delta"] > 0)
    n_improved = sum(1 for d in diffs if d["delta"] < 0)
    n_unchanged = len(diffs) - n_worsened - n_improved
    top_increases = sorted(diffs, key=lambda d: -d["delta"])[:top_n]
    top_decreases = sorted(diffs, key=lambda d: d["delta"])[:top_n]

    change = (f"{agg_a['feasibility_class']} → {agg_b['feasibility_class']}"
              if agg_a["feasibility_class"] != agg_b["feasibility_class"]
              else f"blijft {agg_a['feasibility_class']}")
    dom = max(real_scoring.FACTORS, key=lambda f: abs(deltas[f]))
    delta = ScenarioDelta(
        score_avg_delta=round(agg_b["score_avg"] - agg_a["score_avg"], 1),
        stop_share_delta=round(agg_b["stop_share"] - agg_a["stop_share"], 3),
        n_stop_delta=agg_b["n_stop"] - agg_a["n_stop"],
        feasibility_change=change,
        narrative_nl=(
            f"Vergelijking '{side_a['label']}' vs '{side_b['label']}' over "
            f"{agg_a['n_cells']:,} H3-cellen ({sbase}). Oordeel: {change}. "
            f"Gemiddelde DrinkwaterDruk {agg_a['score_avg']:.0f} → {agg_b['score_avg']:.0f}; "
            f"STOP-aandeel {agg_a['stop_share'] * 100:.0f}% → {agg_b['stop_share'] * 100:.0f}%. "
            f"Grootste bijdrage aan de verandering: {FACTOR_NL[dom]} "
            f"({deltas[dom]:+.1f} punt gemiddeld)."
        ),
    )

    # Full per-cell overlay for the map (every cell, coloured by A->B delta).
    overlay = {
        "layer_id": "compare_delta_h3",
        "label_nl": "Verschil DrinkwaterDruk (A → B) per H3-cel",
        "type": "H3HexagonLayer",
        "cells": [{"h3_id": d["h3_id"], "delta": d["delta"],
                   "score_a": d["score_a"], "score_b": d["score_b"]} for d in diffs],
        "legend_nl": {"up": "hoger (slechter) in B", "down": "lager (beter) in B", "zero": "gelijk"},
    }

    return {
        "universe": {"base": sbase, "n_cells": agg_a["n_cells"], "area_source": area_source},
        "a": {"label": side_a["label"], "question": side_a["question"],
              "assumptions": a_full, **agg_a},
        "b": {"label": side_b["label"], "question": side_b["question"],
              "assumptions": b_full, **agg_b},
        "delta": asdict(delta),
        "factor_attribution": attribution,
        "overlay": overlay,
        "cell_diff": {
            "n_common": len(diffs),
            "n_worsened": n_worsened, "n_improved": n_improved, "n_unchanged": n_unchanged,
            "transitions": transitions_list,
            "top_increases": top_increases,
            "top_decreases": top_decreases,
        },
        "note_nl": ("Beide scenario's zijn gescoord over hetzelfde H3-universum "
                    f"(herkomst: {area_source}). Factorbijdragen zijn vóór begrenzing "
                    "(een cel kan op 100 zijn afgetopt), dus de som kan de score "
                    "overschrijden waar afgetopt is."),
    }
