"""Scenario-engine data model (design doc §7), trimmed to what the wired
vertical slice uses. Faithful field names so it stays compatible with the
fix-pack calculators and the design doc's ScenarioCard contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ScenarioParams:
    scenario_type: Literal["drop_pin", "intake_failure", "multi_hazard", "intervention"]
    knmi_preset: Literal["B", "Hd", "Hn", "Ld", "Ln"] = "Hd"
    time_horizon: int = 2040
    growth_preset: Literal["laag", "middel", "hoog"] = "middel"
    location_name: str | None = None
    development_type: str | None = None
    development_mw: float | None = None
    development_units: int | None = None
    intake_id: str | None = None
    outage_weeks: int | None = None
    interventions: list[str] = field(default_factory=list)
    assumption_overrides: dict[str, float] = field(default_factory=dict)


@dataclass
class ReasoningStep:
    step_nr: int
    label_nl: str
    description_nl: str
    datasets_used: list[str] = field(default_factory=list)
    calculated_value: str | None = None
    source_urls: list[str] = field(default_factory=list)


@dataclass
class ScenarioResults:
    # Verdict — v3: derived from the H3 composite DrinkwaterDruk score
    feasibility_class: str = "CAUTION"            # area verdict GO/CAUTION/STOP
    score_avg: float = 0.0                        # DrinkwaterDruk 0-100 (area mean)
    n_cells: int = 0
    n_stop: int = 0
    n_caution: int = 0
    n_go: int = 0
    stop_share: float = 0.0
    themes_used: list[str] = field(default_factory=list)
    human_scale: dict | None = None
    interventions_ranked: list[dict] = field(default_factory=list)
    is_policy_approx: bool = True
    # Legacy m3/day fields — kept for compatibility, unused in the H3 path
    daily_demand_m3: float = 0.0
    supply_capacity_m3: float = 0.0
    supply_gap_m3: float = 0.0


@dataclass
class ScenarioDelta:
    score_avg_delta: float
    stop_share_delta: float
    n_stop_delta: int
    feasibility_change: str        # e.g. "CAUTION → STOP"
    narrative_nl: str


@dataclass
class ScenarioCard:
    scenario_id: str
    scenario_hash: str
    created_at: str
    git_commit: str
    stable_url: str
    question_nl: str
    scenario_type: str
    params: ScenarioParams
    results: ScenarioResults
    reasoning_steps: list[ReasoningStep] = field(default_factory=list)
    official_position: dict | None = None
    source_registry: list[dict] = field(default_factory=list)
    overlays: list[dict] = field(default_factory=list)
    delta: dict | None = None        # populated in comparison mode
    cache_used: bool = False
    assumptions_version: str = ""    # Phase 7 (Gap F): which assumption library produced this
    validation_status: str = ""      # Phase 7 (Gap E): what the verdict is/ isn't validated against
