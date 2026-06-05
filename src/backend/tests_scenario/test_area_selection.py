"""Workstream 2 — area-of-interest selection. Drop-pin uses an H3 grid_disk around
the geocoded location; intake uses the zes-uur protection cells; they score
different cell sets. Offline-safe (PDOK geocode falls back to labeled coords)."""
import asyncio
from pathlib import Path

from app.services.scenario.area import select_h3_area
from app.services.scenario.models import ScenarioParams
from app.services.scenario.workflow import run_scenario

DATA = str(Path(__file__).resolve().parents[1] / "data")


def test_intake_uses_zes_uur_cells():
    cells, desc, meta = select_h3_area(ScenarioParams(scenario_type="intake_failure", intake_id="IJssel"), DATA)
    assert meta["mode"] == "zes_uur" and meta["n"] > 0
    assert "zes-uur" in desc


def test_drop_pin_uses_grid_disk():
    cells, desc, meta = select_h3_area(
        ScenarioParams(scenario_type="drop_pin", location_name="Pijnacker-Nootdorp"), DATA)
    assert meta["mode"] == "grid_disk" and meta["n"] > 0
    assert "grid_disk" in desc and meta["k"] >= 1


def test_drop_pin_and_intake_score_different_cell_sets():
    a = asyncio.run(run_scenario(
        "Kan er een 50 MW datacenter komen bij Pijnacker-Nootdorp in 2040?", DATA))["card"].results
    b = asyncio.run(run_scenario(
        "Wat als de Hollandse IJssel-inname verzilt onder KNMI Hd in 2040?", DATA))["card"].results
    assert a.n_cells > 0 and b.n_cells > 0
    assert a.n_cells != b.n_cells                        # different areas -> different cell sets
    assert a.feasibility_class in {"GO", "CAUTION", "STOP"}
    assert b.feasibility_class in {"GO", "CAUTION", "STOP"}
