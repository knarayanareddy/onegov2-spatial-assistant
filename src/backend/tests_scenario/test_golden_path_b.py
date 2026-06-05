"""Golden Path B — verzilting on the Hollandse IJssel (brief scenarios 1/4),
v3 H3 model on real data."""
import asyncio
from pathlib import Path

from app.services.scenario.workflow import run_scenario

DATA = str(Path(__file__).resolve().parents[1] / "data")
Q = ("Wat als de Hollandse IJssel-inname 6 weken onbruikbaar is door verzilting "
     "onder KNMI Hd in 2040?")


def test_golden_path_b_verzilting_intake():
    c = asyncio.run(run_scenario(Q, DATA))["card"]
    r = c.results
    assert c.scenario_type == "intake_failure"
    assert c.params.knmi_preset == "Hd"
    assert r.feasibility_class in {"CAUTION", "STOP"}    # Hd dryness -> high pressure
    assert "verzilting" in r.themes_used
    # the H3 scoring step is recorded for the Insight panel
    assert any("H3" in s.label_nl or "DrinkwaterDruk" in s.description_nl for s in c.reasoning_steps)


def test_golden_path_b_make_it_feasible_present():
    r = asyncio.run(run_scenario(Q, DATA))["card"].results
    assert r.interventions_ranked                        # GAP 5 on STOP/CAUTION
    assert any(i["stop_share_reduction_pct"] > 0 for i in r.interventions_ranked)
