"""Workstream 1 — CBS demand signal (population-growth axis, brief scenario 3).
Proves the canonicalized CBS join works and that the growth/homes levers move pressure."""
from pathlib import Path

from app.services.scenario.real_scoring import score_h3_area

DATA = str(Path(__file__).resolve().parents[1] / "data")


def test_cbs_demand_joins_and_contributes():
    r = score_h3_area(DATA)
    assert r["demand_avg"] > 0                       # CBS actually joined (h3 canonicalization)
    assert "cbs_vierkantstatistieken" in r["themes_used"]


def test_population_growth_increases_pressure():
    base = score_h3_area(DATA, {"population_growth_pct": 0.0})
    grow = score_h3_area(DATA, {"population_growth_pct": 0.5})
    assert grow["demand_avg"] > base["demand_avg"]
    assert grow["n_stop"] >= base["n_stop"]


def test_added_homes_is_monotonic():
    base = score_h3_area(DATA, {"added_homes": 0})
    homes = score_h3_area(DATA, {"added_homes": 80000})
    assert homes["demand_avg"] >= base["demand_avg"]
    assert homes["n_stop"] >= base["n_stop"]
