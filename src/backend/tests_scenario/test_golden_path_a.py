"""Golden Path A — datacenter drop-pin (brief scenario 5), v3 H3 model on real data."""
import asyncio
from pathlib import Path

from app.services.scenario.workflow import run_scenario

DATA = str(Path(__file__).resolve().parents[1] / "data")
Q = "Kan er een 50 MW datacenter komen bij Pijnacker-Nootdorp in 2040?"


def test_golden_path_a_runs_on_real_data():
    c = asyncio.run(run_scenario(Q, DATA))["card"]
    r = c.results
    assert c.scenario_type == "drop_pin"
    assert r.feasibility_class in {"GO", "CAUTION", "STOP"}
    assert len(r.themes_used) >= 2                 # Must: combine >=2 themes
    assert 0 <= r.score_avg <= 100
    assert len(c.scenario_hash) == 32
    assert c.overlays and c.overlays[0]["layer_id"] == "drinkwaterdruk_h3"


def test_golden_path_a_reproducible():
    h1 = asyncio.run(run_scenario(Q, DATA))["card"].scenario_hash
    h2 = asyncio.run(run_scenario(Q, DATA))["card"].scenario_hash
    assert h1 == h2
