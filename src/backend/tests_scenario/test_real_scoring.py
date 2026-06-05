"""v3 runnable reference — proves the assumption-driven H3 model runs on the
REAL shipped Parquet (no fixture, no LLM). See docs/onegov2_design_v3_repo_aligned.md Part D/H.
"""
from pathlib import Path

from app.services.scenario.real_scoring import score_h3_area, verdict_from_score, DEFAULT_ASSUMPTIONS

DATA = str(Path(__file__).resolve().parents[1] / "data")


def test_runs_on_real_data_and_combines_two_themes():
    r = score_h3_area(DATA)
    assert r["n_cells"] == 14279                 # the real verzilting cell count
    assert len(r["themes_used"]) >= 2            # Must criterion: combine >=2 themes
    assert r["area_verdict"] in {"GO", "CAUTION", "STOP"}
    assert 0 <= r["score_avg"] <= 100
    assert r["n_stop"] + r["n_caution"] + r["n_go"] == r["n_cells"]


def test_assumptions_are_live_and_deterministic():
    a = score_h3_area(DATA)
    b = score_h3_area(DATA)
    assert a["score_avg"] == b["score_avg"]      # deterministic
    # moving the weights changes the score (assumptions actually drive the model)
    c = score_h3_area(DATA, {"weight_salinity": 0.4, "weight_flood": 0.45, "weight_protection": 0.15})
    assert c["score_avg"] != a["score_avg"]


def test_verdict_thresholds_single_definition():
    a = DEFAULT_ASSUMPTIONS
    assert verdict_from_score(10, a) == "GO"
    assert verdict_from_score(50, a) == "CAUTION"
    assert verdict_from_score(80, a) == "STOP"
