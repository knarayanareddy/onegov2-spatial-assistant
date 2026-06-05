"""With/without-shock comparison (design doc Golden C / brief Should criterion),
on real data."""
import asyncio
from pathlib import Path

from app.services.scenario.workflow import run_comparison

DATA = str(Path(__file__).resolve().parents[1] / "data")


def test_with_without_shock_comparison():
    comp = asyncio.run(run_comparison("Verzilting op de Hollandse IJssel", DATA))
    a, b, d = comp["card_a"].results, comp["card_b"].results, comp["delta"]
    # the dry/verzilting shock must worsen the picture
    assert b.score_avg > a.score_avg
    assert b.stop_share >= a.stop_share
    assert d.score_avg_delta > 0
    assert d.n_stop_delta >= 0
    assert ("→" in d.feasibility_change) or ("STOP" in d.feasibility_change)
    assert d.narrative_nl
    # the two runs are distinct, citeable artefacts
    assert comp["card_a"].scenario_hash != comp["card_b"].scenario_hash
    assert comp["card_b"].delta is not None
