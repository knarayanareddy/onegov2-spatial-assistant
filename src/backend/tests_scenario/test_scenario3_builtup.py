"""Scenario 3 sharpened: demand scored on the BUILT-UP universe (where people live),
so the population/growth axis actually drives the verdict."""
import asyncio
from pathlib import Path

from app.services.scenario.real_scoring import score_h3_area
from app.services.scenario.workflow import run_scenario

DATA = str(Path(__file__).resolve().parents[1] / "data")
W = {"weight_demand": 0.6, "weight_salinity": 0.15, "weight_flood": 0.2,
     "weight_protection": 0.05, "demand_ref_m3_per_cell": 2.0, "population_growth_pct": 0.065}


def test_demand_dominates_on_built_up_area():
    built = score_h3_area(DATA, dict(W), base="populated")
    sal = score_h3_area(DATA, dict(W), base="salinity")
    assert built["base"] == "populated" and built["n_cells"] > 1000
    # demand pressure is far higher where people live than over the salinity region
    assert built["demand_avg"] > 5 * sal["demand_avg"]


def test_housing_growth_axis_is_monotonic():
    base = score_h3_area(DATA, {**W, "added_homes": 0}, base="populated")
    h80 = score_h3_area(DATA, {**W, "added_homes": 80000}, base="populated")
    comp = score_h3_area(DATA, {**W, "added_homes": 80000, "knmi_dryness_multiplier": 1.8}, base="populated")
    assert h80["n_stop"] > base["n_stop"]          # +80k homes raises pressure
    assert comp["n_stop"] > h80["n_stop"]          # + dry/verzilting shock raises it further
    assert comp["score_avg"] > base["score_avg"]


def test_housing_question_routes_to_built_up_universe():
    c = asyncio.run(run_scenario(
        "Wat betekent 80.000 extra woningen in de Zuidelijke Randstad voor drinkwater in 2040?",
        DATA))["card"]
    assert c.params.development_type == "housing_5000"
    assert c.params.development_units == 80000
    assert c.results.n_cells > 1000               # built-up universe, not a grid_disk
