"""Cumulative / multi-project overlay + "al vergund" layer (Phase 5).

Closes the deepest silo gap: individual plans each "pass" while their COMBINED
load on a supply universe fails. A cumulative request bundles several project
demands plus an operator-entered "al vergund / in behandeling" (already-permitted /
under-review) committed-demand list, and scores the stacked load on the populated
universe via the existing deterministic engine.

Honest scope: no permit dataset ships in this repo (productieketen is empty), so
the committed-demand layer is OPERATOR/MANUAL entry — clearly labelled, ready for
an OLO/permits koppeling later. Each committed entry carries its own source label.

Every project's demand is converted to an "added households" equivalent (the
engine's demand lever), so housing units, datacentre MW and raw m3/day all stack
on one axis. Sources: VEWIN (household use) and IEA (datacentre intensity).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.services.scenario.human_scale import VEWIN_HOUSEHOLD_DAY_M3, VEWIN_URL
from app.services.scenario.models import ScenarioParams
from app.services.scenario.workflow import run_scenario
from app.services.chatbot.scenario_run import ALLOWED_GROWTH, ALLOWED_KNMI

# Datacentre water intensity — design doc Part D default assumption.
DATACENTER_M3_PER_MW_DAY = 12.0
DATACENTER_SOURCE = "https://www.iea.org/energy-system/buildings/data-centres-and-data-transmission-networks"
MAX_PROJECTS = 8


@dataclass
class CumulativePlan:
    runnable: bool
    knmi_preset: str = "Hd"
    growth_preset: str = "middel"
    projects: list[dict] = field(default_factory=list)     # each: {name, homes_equiv, raw}
    committed: list[dict] = field(default_factory=list)     # each: {label, m3_day, homes_equiv, source_url}
    followup_nl: Optional[str] = None
    reason: Optional[str] = None


def _homes_equiv(project: dict) -> float:
    """Convert a project's demand to an added-households equivalent."""
    if project.get("added_homes") is not None:
        return float(project["added_homes"])
    if project.get("development_units") is not None:
        return float(project["development_units"])
    if project.get("datacenter_mw") is not None:
        m3 = float(project["datacenter_mw"]) * DATACENTER_M3_PER_MW_DAY
        return m3 / VEWIN_HOUSEHOLD_DAY_M3
    if project.get("m3_day") is not None:
        return float(project["m3_day"]) / VEWIN_HOUSEHOLD_DAY_M3
    return 0.0


def validate_cumulative(spec: dict) -> CumulativePlan:
    knmi = str(spec.get("knmi_preset", "Hd"))
    if knmi not in ALLOWED_KNMI:
        return CumulativePlan(False, followup_nl="Kies een KNMI-scenario: B, Hd, Hn, Ld of Ln.", reason="bad_knmi")
    growth = str(spec.get("growth_preset", "middel"))
    if growth not in ALLOWED_GROWTH:
        return CumulativePlan(False, followup_nl="Kies bevolkingsgroei: laag, middel of hoog.", reason="bad_growth")

    raw_projects = spec.get("projects") or []
    if not raw_projects:
        return CumulativePlan(False, followup_nl="Voeg minstens één project toe om te stapelen.", reason="no_projects")
    if len(raw_projects) > MAX_PROJECTS:
        return CumulativePlan(False, followup_nl=f"Maximaal {MAX_PROJECTS} projecten per stapeling.", reason="too_many")

    projects: list[dict] = []
    for i, p in enumerate(raw_projects):
        he = _homes_equiv(p)
        if he < 0:
            return CumulativePlan(False, followup_nl="Projectvraag kan niet negatief zijn.", reason="negative_demand")
        projects.append({"name": p.get("name") or f"Project {i + 1}", "homes_equiv": round(he, 1), "raw": p})

    committed: list[dict] = []
    for c in (spec.get("committed") or []):
        m3 = float(c.get("m3_day", 0) or 0)
        if m3 < 0:
            return CumulativePlan(False, followup_nl="Al-vergund-vraag kan niet negatief zijn.", reason="negative_committed")
        committed.append({
            "label": c.get("label") or "Al vergund (eigen invoer)",
            "m3_day": m3, "homes_equiv": round(m3 / VEWIN_HOUSEHOLD_DAY_M3, 1),
            "source_url": c.get("source_url") or "eigen invoer / OLO-koppeling",
        })

    return CumulativePlan(True, knmi_preset=knmi, growth_preset=growth, projects=projects, committed=committed)


def _params(knmi: str, growth: str, added_homes: float) -> ScenarioParams:
    return ScenarioParams(
        scenario_type="multi_hazard", knmi_preset=knmi, growth_preset=growth,
        assumption_overrides={"added_homes": float(added_homes)},
    )


async def execute_cumulative(plan: CumulativePlan, data_dir: str = "data") -> dict:
    """Score baseline, each project alone, and the combined stack (+ al vergund)
    on the populated universe. Shows the stapelingseffect deterministically."""
    if not plan.runnable:
        raise ValueError("execute_cumulative called with a non-runnable plan")

    async def verdict(added: float) -> dict:
        st = await run_scenario("Stapeling", data_dir, params=_params(plan.knmi_preset, plan.growth_preset, added),
                                base="populated")
        r = st["card"].results
        return {"feasibility_class": r.feasibility_class, "score_avg": r.score_avg,
                "n_cells": r.n_cells, "n_stop": r.n_stop, "stop_share": r.stop_share}

    committed_homes = sum(c["homes_equiv"] for c in plan.committed)
    projects_homes = sum(p["homes_equiv"] for p in plan.projects)
    total_homes = projects_homes + committed_homes

    baseline = await verdict(committed_homes)   # the world as already committed (al vergund)
    for p in plan.projects:                     # each project's marginal-alone verdict (on top of committed)
        v = await verdict(committed_homes + p["homes_equiv"])
        p["alone_verdict"] = v["feasibility_class"]
        p["alone_score"] = v["score_avg"]
    combined = await verdict(total_homes)

    individually_ok = all(p["alone_verdict"] != "STOP" for p in plan.projects)
    stacking_flips = individually_ok and combined["feasibility_class"] == "STOP"
    narrative = (
        f"Gestapeld ({len(plan.projects)} projecten + {committed_homes:,.0f} al-vergunde "
        f"woning-equivalenten) verschuift het oordeel naar {combined['feasibility_class']} "
        f"(score {combined['score_avg']:.0f}, {combined['stop_share'] * 100:.0f}% STOP-cellen)."
    )
    if stacking_flips:
        narrative += (" Let op: afzonderlijk halen de projecten het wél, samen niet — "
                      "dit is een stapelingseffect dat alleen zichtbaar is bij gezamenlijke beoordeling.")

    return {
        "knmi_preset": plan.knmi_preset, "growth_preset": plan.growth_preset,
        "projects": plan.projects, "committed": plan.committed,
        "committed_homes_equiv": round(committed_homes, 1),
        "projects_homes_equiv": round(projects_homes, 1),
        "total_homes_equiv": round(total_homes, 1),
        "baseline_al_vergund": baseline, "combined": combined,
        "stacking_flips": stacking_flips, "narrative_nl": narrative,
        "human_scale_source": VEWIN_URL,
        "disclaimer_nl": ("De 'al vergund'-laag is eigen invoer (geen vergunningendataset in deze repo); "
                          "het stapelingseffect is een beleidsmatige verkenning."),
    }
