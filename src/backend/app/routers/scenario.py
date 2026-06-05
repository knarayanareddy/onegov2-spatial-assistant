"""Unified scenario endpoint (design doc §6, v3).

POST /api/scenario/run    -> SSE stream (single scenario, or with/without-shock comparison)
GET  /api/scenario/{id}   -> cached ScenarioCard (stable URL)

Runs the assumption-driven H3 model on the real shipped data (real_scoring); no
synthetic fixture, no LLM key required. Reuses the repo's SSE convention.
"""
from __future__ import annotations

import glob
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.auth import CurrentUser, get_current_user
from app.services.audit import get_store as _audit_store
from app.services.audit import record_audit
from app.services.scenario.assumptions import ASSUMPTIONS_VERSION, assumption_library
from app.services.scenario.calibration import run_calibration
from app.services.scenario.citizen import detect_citizen_mode, format_citizen_response
from app.services.scenario.compare import compare_scenarios
from app.services.scenario.cumulative import execute_cumulative, validate_cumulative
from app.services.scenario.models import ScenarioParams
from app.services.scenario.pdf import build_citation, render_scenario_pdf
from app.services.scenario.scenario_store import ScenarioStore, detect_version_drift
from app.services.scenario.uncertainty import run_uncertainty
from app.services.scenario.waterinfo import get_chloride, is_intake_relevant
from app.services.scenario.workflow import STABLE_URL_BASE, run_comparison, run_scenario

router = APIRouter(tags=["scenario"])

# Absolute data dir so the engine works regardless of the process cwd.
DATA_DIR = str(Path(__file__).resolve().parents[2] / "data")

_con = duckdb.connect()
_store = ScenarioStore(_con)


class ScenarioRunRequest(BaseModel):
    question: str
    compare: bool = False                  # with/without-shock comparison
    assumptions: Optional[dict] = None     # assumption overrides for a single run (sliders)
    baseline: Optional[dict] = None        # assumption overrides for the baseline run
    shock: Optional[dict] = None           # assumption overrides for the shock run
    user_persona: str = "professional"
    language: str = "nl"


def _sse(event: str, data) -> dict:
    return {"event": event, "data": json.dumps(data, ensure_ascii=False, default=str)}


def _dataset_versions() -> dict:
    """Current dataset versions = newest parquet mtime per table (for drift/verify)."""
    try:
        from app.services.helpers.tables import discover_tables
        out: dict[str, str] = {}
        for e in discover_tables(Path(DATA_DIR)):
            files = glob.glob(e.parquet_glob)
            if files:
                mtime = max(os.path.getmtime(f) for f in files)
                out[e.table_name] = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
        return out
    except Exception:
        return {}


def _persist(card, run_by: Optional[dict] = None) -> dict:
    d = asdict(card)
    if run_by:
        d["run_by"] = run_by   # who ran it (stamped into the citation)
    _store.set(card.scenario_id, card.scenario_hash, asdict(card.params), d,
               _dataset_versions(), card.git_commit, STABLE_URL_BASE)
    return d


def _run_by(user: CurrentUser) -> dict:
    return {"oid": user.oid, "name": user.name, "auth_mode": user.auth_mode}


def _emit_card(card_dict: dict):
    yield _sse("scenario_params_confirmed", card_dict["params"])
    for step in card_dict["reasoning_steps"]:
        yield _sse("reasoning_step", step)
    yield _sse("feasibility_class", {
        "feasibility_class": card_dict["results"]["feasibility_class"],
        "score_avg": card_dict["results"]["score_avg"],
        "stop_share": card_dict["results"]["stop_share"],
    })
    yield _sse("official_position", card_dict["official_position"])
    yield _sse("scenario_card", card_dict)
    yield _sse("map_data", {"overlays": card_dict["overlays"]})


@router.post("/api/scenario/run")
async def scenario_run(req: ScenarioRunRequest, user: CurrentUser = Depends(get_current_user)):
    run_by = _run_by(user)
    if req.compare:
        comp = await run_comparison(req.question, DATA_DIR, req.baseline, req.shock)
        a, b = _persist(comp["card_a"], run_by), _persist(comp["card_b"], run_by)
        await record_audit(user, "scenario.run", comp["card_b"].scenario_id,
                           {"compare": True, "question": req.question[:120]}, comp["card_b"].scenario_hash)

        async def gen_cmp():
            for ev in _emit_card(a):
                yield ev
            for ev in _emit_card(b):
                yield ev
            yield _sse("scenario_delta", asdict(comp["delta"]))
            yield _sse("done", None)
        return EventSourceResponse(gen_cmp())

    state = await run_scenario(req.question, DATA_DIR, req.assumptions)
    _card = state.get("card")
    if _card is not None:
        await record_audit(user, "scenario.run", _card.scenario_id,
                           {"question": req.question[:120], "verdict": _card.results.feasibility_class},
                           _card.scenario_hash)

    async def gen_single():
        if state.get("followup_nl"):
            yield _sse("followup_question", {"question_nl": state["followup_nl"]})
            yield _sse("done", None)
            return
        card_dict = _persist(state["card"], run_by)
        for ev in _emit_card(card_dict):
            yield ev
        # Phase 5: mandatory chloride provenance for IJssel/Lek/Maas intake scenarios
        # (live when WATERINFO_LIVE, else the dated last-known value — never silent).
        p = card_dict.get("params", {})
        if p.get("scenario_type") == "intake_failure" and is_intake_relevant(p.get("intake_id")):
            yield _sse("waterinfo", get_chloride(p.get("intake_id")))
        if detect_citizen_mode(req.question, req.user_persona):
            yield _sse("citizen_response", format_citizen_response(card_dict, req.question))
        yield _sse("done", None)
    return EventSourceResponse(gen_single())


class CumulativeRequest(BaseModel):
    """Phase 5: stack several project demands + an operator-entered al-vergund layer."""
    projects: list[dict] = []                # each: {name, added_homes|development_units|datacenter_mw|m3_day}
    committed: list[dict] = []               # each: {label, m3_day, source_url}
    knmi_preset: str = "Hd"
    growth_preset: str = "middel"


@router.get("/api/scenario")
async def scenario_list(limit: int = 50):
    """Saved-scenario library — most recent first, with stable URLs (Phase 5)."""
    return {"scenarios": _store.list_recent(limit)}


@router.post("/api/scenario/cumulative")
async def scenario_cumulative(req: CumulativeRequest, user: CurrentUser = Depends(get_current_user)):
    """Cumulative / multi-project overlay + al-vergund netting (Phase 5). JSON result."""
    plan = validate_cumulative(req.model_dump())
    if not plan.runnable:
        raise HTTPException(status_code=422, detail=plan.followup_nl or plan.reason or "Ongeldig verzoek.")
    result = await execute_cumulative(plan, DATA_DIR)
    await record_audit(user, "scenario.cumulative", "",
                       {"projects": len(plan.projects), "verdict": result["combined"]["feasibility_class"]})
    return result


class UncertaintyRequest(BaseModel):
    question: str


@router.post("/api/scenario/uncertainty")
async def scenario_uncertainty(req: UncertaintyRequest, user: CurrentUser = Depends(get_current_user)):
    """Uncertainty band across the five KNMI'23 presets (Phase 6). JSON result."""
    if not (req.question or "").strip():
        raise HTTPException(status_code=422, detail="Vraag mag niet leeg zijn.")
    band = await run_uncertainty(req.question, DATA_DIR)
    await record_audit(user, "scenario.uncertainty", "",
                       {"question": req.question[:120], "robust": band["robust"], "headline": band["headline_nl"]})
    return band


class CompareSide(BaseModel):
    """One side of an A/B comparison: a saved scenario, or an inline custom set."""
    scenario_id: Optional[str] = None
    question: Optional[str] = None
    assumptions: Optional[dict] = None
    label: Optional[str] = None


class CompareRequest(BaseModel):
    a: CompareSide
    b: CompareSide
    base: Optional[str] = None              # shared-universe override: "salinity" | "populated"
    area_cells: Optional[list[str]] = None  # shared-universe H3 cells override
    top_n: int = 25                         # how many top changed cells to return per direction


@router.post("/api/scenario/compare")
async def scenario_compare(req: CompareRequest, user: CurrentUser = Depends(get_current_user)):
    """Detailed A/B comparison: any two scenarios (by id or inline assumptions)
    over a shared H3 universe, with per-factor attribution and a per-cell diff."""
    a, b = req.a.model_dump(), req.b.model_dump()
    for side, payload in (("A", a), ("B", b)):
        if not (payload.get("scenario_id") or payload.get("assumptions")):
            raise HTTPException(status_code=422,
                                detail=f"Zijde {side} vereist een scenario_id of assumptions.")
    try:
        result = compare_scenarios(a, b, DATA_DIR, _store,
                                   base=req.base, area_cells=req.area_cells, top_n=req.top_n)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await record_audit(user, "scenario.compare", "",
                       {"verdict_change": result["delta"]["feasibility_change"],
                        "n_cells": result["universe"]["n_cells"]})
    return result


@router.get("/api/audit")
async def audit_list(limit: int = 100, action: Optional[str] = None,
                     user: CurrentUser = Depends(get_current_user)):
    """Recent audit trail — who did what (Phase 6). Auth-gated."""
    entries = await _audit_store().list_recent(limit, action=action)
    return {"entries": [e.as_dict() for e in entries]}


@router.get("/api/assumptions")
async def assumptions_endpoint():
    """The versioned, sourced assumption library + changelog (Phase 7, Gap F)."""
    return assumption_library()


# NB: declared BEFORE /api/scenario/{scenario_id} so "calibration" isn't an id.
@router.get("/api/scenario/calibration")
async def scenario_calibration(user: CurrentUser = Depends(get_current_user)):
    """Run the calibration harness vs the design reference figures (Phase 7, Gap E)."""
    report = await run_calibration(DATA_DIR)
    await record_audit(user, "scenario.calibration", "",
                       {"n_pass": report["n_pass"], "n_total": report["n_total"]})
    return report


def _load_card(scenario_id: str) -> dict:
    cached = _store.get_by_id(scenario_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Scenario niet gevonden.")
    result = cached["result_json"]
    card = json.loads(result) if isinstance(result, str) else result
    card["cached_at"] = cached["cached_at"]
    return card


@router.get("/api/scenario/{scenario_id}")
async def scenario_get(scenario_id: str):
    card = _load_card(scenario_id)
    card["cache_used"] = True
    return card


@router.get("/api/scenario/{scenario_id}/citation")
async def scenario_citation(scenario_id: str):
    return build_citation(_load_card(scenario_id))


@router.get("/api/scenario/{scenario_id}/pdf")
async def scenario_pdf(scenario_id: str):
    pdf_bytes = render_scenario_pdf(_load_card(scenario_id))
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename=scenario_{scenario_id[:8]}.pdf'})


@router.get("/api/scenario/waterinfo/{intake_id}")
async def scenario_waterinfo(intake_id: str):
    """Live RWS chloride for an intake (or the dated last-known fallback). Phase 5."""
    if not is_intake_relevant(intake_id):
        raise HTTPException(status_code=404, detail="Onbekend innamepunt (IJssel, Lek of Maas).")
    return get_chloride(intake_id)


@router.get("/api/scenario/{scenario_id}/verify")
async def scenario_verify(scenario_id: str, user: CurrentUser = Depends(get_current_user)):
    """Re-run a saved scenario on the CURRENT data and compare to the cached result,
    plus report dataset-version drift (Phase 5). 'Verifieer berekening'."""
    cached = _store.get_by_id(scenario_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Scenario niet gevonden.")
    card = cached["result_json"]
    card = json.loads(card) if isinstance(card, str) else card
    try:
        params = ScenarioParams(**card.get("params", {}))
    except Exception:
        raise HTTPException(status_code=422, detail="Kan de parameters van dit scenario niet herleiden.")

    state = await run_scenario(card.get("question_nl", ""), DATA_DIR, params=params)
    new = state["card"]
    cached_res = card.get("results", {})
    matches = (
        new.scenario_hash == card.get("scenario_hash")
        and new.results.feasibility_class == cached_res.get("feasibility_class")
        and abs(new.results.score_avg - float(cached_res.get("score_avg", 0))) < 0.05
    )
    drift = detect_version_drift(cached.get("dataset_versions_at_cache") or {}, _dataset_versions())
    cached_av = card.get("assumptions_version", "")
    assumption_drift = bool(cached_av) and cached_av != ASSUMPTIONS_VERSION
    await record_audit(user, "scenario.verify", scenario_id,
                       {"matches": matches, "drift": len(drift), "assumption_drift": assumption_drift})
    clean = matches and not drift and not assumption_drift
    return {
        "scenario_id": scenario_id,
        "matches": matches,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "cached": {"feasibility_class": cached_res.get("feasibility_class"),
                   "score_avg": cached_res.get("score_avg"), "scenario_hash": card.get("scenario_hash"),
                   "assumptions_version": cached_av},
        "current": {"feasibility_class": new.results.feasibility_class,
                    "score_avg": new.results.score_avg, "scenario_hash": new.scenario_hash,
                    "assumptions_version": ASSUMPTIONS_VERSION},
        "dataset_drift": drift,
        "assumption_drift": assumption_drift,
        "note_nl": ("Identiek herberekend op de huidige data en aanname-bibliotheek." if clean
                    else "Let op: resultaat, dataset of aanname-versie is gewijzigd sinds de opslag — zie details."),
    }
