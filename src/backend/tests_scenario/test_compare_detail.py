"""Detailed A/B scenario comparison (compare.py + /api/scenario/compare).

Runs on the REAL shipped data (no LLM key, no network), like the rest of the
scenario suite. Covers: per-factor term decomposition, factor attribution,
per-cell diff + verdict transitions, the endpoint, validation, and comparing
two SAVED scenarios by id.
"""
from dataclasses import asdict

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.routers import scenario
from app.services import audit
from app.services.helpers.tables import DATA_DIR
from app.services.scenario import real_scoring
from app.services.scenario.compare import compare_scenarios
from app.services.scenario.models import ScenarioParams
from app.services.scenario.scenario_store import ScenarioStore
from app.services.scenario.workflow import run_scenario

DATA = str(DATA_DIR)
_AUTH_KEYS = ["AUTH_MODE", "AUTH_REQUIRED"]


@pytest.fixture(autouse=True)
def _reset():
    audit.set_store(audit.InMemoryAuditStore())
    saved = {k: getattr(settings, k) for k in _AUTH_KEYS}
    settings.AUTH_MODE = "dev"
    settings.AUTH_REQUIRED = False
    yield
    for k, v in saved.items():
        setattr(settings, k, v)


_app = FastAPI(); _app.include_router(scenario.router); _client = TestClient(_app)

_DRY_LOW = {"knmi_dryness_multiplier": 1.0}
_DRY_HIGH = {"knmi_dryness_multiplier": 1.8}


# ---------------------------------------------------------------- unit: scorer
def test_components_sum_to_score():
    """Per-factor terms must reconstruct the canonical score: score == min(100, sum)."""
    cells = real_scoring.score_cells_components(DATA, _DRY_HIGH, None, "salinity")
    assert cells, "expected scored cells on the salinity universe"
    for c in cells[:200]:
        s = c["salinity"] + c["flood"] + c["protection"] + c["demand"]
        assert abs(c["score"] - min(100.0, s)) < 0.5


def test_components_have_all_factors():
    c = real_scoring.score_cells_components(DATA, _DRY_LOW, None, "salinity")[0]
    for f in real_scoring.FACTORS:
        assert f in c and isinstance(c[f], float)


# ---------------------------------------------------------------- unit: compare
def test_compare_inline_dryness_worsens_and_attributes_to_salinity():
    res = compare_scenarios(
        {"label": "KNMI B", "assumptions": _DRY_LOW},
        {"label": "KNMI Hd", "assumptions": _DRY_HIGH},
        DATA, store=None,
    )
    # universe shared + aligned
    assert res["universe"]["n_cells"] > 0
    assert res["a"]["n_cells"] == res["b"]["n_cells"] == res["cell_diff"]["n_common"]
    # the dry shock raises the score
    assert res["delta"]["score_avg_delta"] > 0
    # salinity must be the dominant driver (dryness multiplies the salinity term)
    attr = {a["factor"]: a for a in res["factor_attribution"]}
    assert set(attr) == set(real_scoring.FACTORS)
    assert attr["salinity"]["delta"] > 0
    dominant = max(real_scoring.FACTORS, key=lambda f: abs(attr[f]["delta"]))
    assert dominant == "salinity"
    # at least some cells worsen
    assert res["cell_diff"]["n_worsened"] > 0


def test_compare_percell_diff_and_transitions_shape():
    res = compare_scenarios({"assumptions": _DRY_LOW}, {"assumptions": _DRY_HIGH}, DATA, store=None, top_n=5)
    cd = res["cell_diff"]
    assert len(cd["top_increases"]) <= 5 and len(cd["top_decreases"]) <= 5
    # top_increases sorted by descending delta
    deltas = [c["delta"] for c in cd["top_increases"]]
    assert deltas == sorted(deltas, reverse=True)
    for c in cd["top_increases"]:
        assert {"h3_id", "score_a", "score_b", "delta", "klasse_a", "klasse_b"} <= set(c)
    for t in cd["transitions"]:
        assert {"from", "to", "n"} <= set(t) and t["from"] != t["to"]


def test_compare_overlay_covers_universe_with_deltas():
    res = compare_scenarios({"assumptions": _DRY_LOW}, {"assumptions": _DRY_HIGH}, DATA, store=None)
    ov = res["overlay"]
    assert ov["layer_id"] == "compare_delta_h3" and ov["type"] == "H3HexagonLayer"
    # one cell per universe cell, each with an h3 id and a numeric delta
    assert len(ov["cells"]) == res["universe"]["n_cells"]
    for c in ov["cells"][:50]:
        assert c["h3_id"] and isinstance(c["delta"], (int, float))
    # the dry shock pushes at least one cell's delta positive
    assert any(c["delta"] > 0 for c in ov["cells"])


def test_compare_identical_sides_no_change():
    res = compare_scenarios({"assumptions": _DRY_LOW}, {"assumptions": _DRY_LOW}, DATA, store=None)
    assert res["delta"]["score_avg_delta"] == 0
    assert res["cell_diff"]["n_worsened"] == 0 and res["cell_diff"]["n_improved"] == 0
    assert res["delta"]["feasibility_change"].startswith("blijft")


# ---------------------------------------------------------------- endpoint
def test_compare_endpoint_inline_ok():
    r = _client.post("/api/scenario/compare", json={
        "a": {"label": "B", "assumptions": _DRY_LOW},
        "b": {"label": "Hd", "assumptions": _DRY_HIGH},
        "top_n": 10,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["delta"]["score_avg_delta"] > 0
    assert len(body["factor_attribution"]) == 4
    assert body["universe"]["n_cells"] > 0


def test_compare_endpoint_validation_422():
    r = _client.post("/api/scenario/compare", json={"a": {"label": "x"}, "b": {"assumptions": _DRY_HIGH}})
    assert r.status_code == 422


def test_compare_endpoint_unknown_id_404():
    r = _client.post("/api/scenario/compare", json={
        "a": {"scenario_id": "does-not-exist"},
        "b": {"assumptions": _DRY_HIGH},
    })
    assert r.status_code == 404


# ---------------------------------------------------------------- saved-by-id
def test_compare_two_saved_scenarios_by_id():
    """Persist two scenarios that differ only in KNMI preset, then compare by id."""
    con = duckdb.connect()
    store = ScenarioStore(con)
    q = "Wat als de Hollandse IJssel-inname verzilt in 2040?"

    async def _persist(preset: str) -> str:
        params = ScenarioParams(scenario_type="intake_failure", knmi_preset=preset)
        state = await run_scenario(q, DATA, params=params)
        card = state["card"]
        store.set(card.scenario_id, card.scenario_hash, asdict(card.params),
                  asdict(card), {}, card.git_commit, "http://localhost:8001")
        return card.scenario_id

    import asyncio
    id_b = asyncio.run(_persist("B"))
    id_hd = asyncio.run(_persist("Hd"))

    res = compare_scenarios({"scenario_id": id_b}, {"scenario_id": id_hd}, DATA, store=store)
    assert res["universe"]["n_cells"] > 0
    assert res["delta"]["score_avg_delta"] > 0          # Hd (dry) is worse than B
    attr = {a["factor"]: a for a in res["factor_attribution"]}
    assert attr["salinity"]["delta"] > 0
