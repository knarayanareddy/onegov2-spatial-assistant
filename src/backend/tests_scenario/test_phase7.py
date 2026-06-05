"""Phase 7 — assumption-library versioning (Gap F) + calibration/validation (Gap E)."""
import asyncio
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import scenario
from app.services.scenario.assumptions import ASSUMPTIONS_VERSION, assumption_library
from app.services.scenario.calibration import run_calibration, validation_status
from app.services.scenario.pdf import build_citation
from app.services.helpers.tables import DATA_DIR

DATA = str(DATA_DIR)
_app = FastAPI(); _app.include_router(scenario.router); _c = TestClient(_app)
_Q = "Verzilting op de Hollandse IJssel onder KNMI Hd in 2040"


def _parse_sse(text):
    events, ev = [], None
    for line in text.splitlines():
        if line.startswith("event:"):
            ev = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and ev is not None:
            events.append((ev, line.split(":", 1)[1].strip()))
    return events


# ---------------------------------------------------------------- Gap F: versioning
def test_assumption_library_has_version_and_changelog():
    lib = assumption_library()
    assert lib["version"] == ASSUMPTIONS_VERSION and lib["changelog"]
    assert "weights_and_thresholds" in lib and lib["weights_and_thresholds"]["weight_salinity"] == 0.4


def test_assumptions_endpoint():
    r = _c.get("/api/assumptions")
    assert r.status_code == 200 and r.json()["version"] == ASSUMPTIONS_VERSION


def test_card_is_stamped_with_version_and_status():
    r = _c.post("/api/scenario/run", json={"question": _Q})
    card = json.loads(dict(_parse_sse(r.text))["scenario_card"])
    assert card["assumptions_version"] == ASSUMPTIONS_VERSION
    assert card["validation_status"] and "extern" in card["validation_status"].lower()


def test_citation_includes_version_and_validation():
    r = _c.post("/api/scenario/run", json={"question": _Q})
    sid = json.loads(dict(_parse_sse(r.text))["scenario_card"])["scenario_id"]
    cit = _c.get(f"/api/scenario/{sid}/citation").json()
    assert cit["assumptions_version"] == ASSUMPTIONS_VERSION and cit["validation_status"]
    assert "Aannameversie" in cit["metadata_block"] and "Validatiestatus" in cit["metadata_block"]


def test_verify_reports_assumption_version():
    r = _c.post("/api/scenario/run", json={"question": _Q})
    sid = json.loads(dict(_parse_sse(r.text))["scenario_card"])["scenario_id"]
    v = _c.get(f"/api/scenario/{sid}/verify").json()
    assert v["assumption_drift"] is False                       # same library -> no drift
    assert v["current"]["assumptions_version"] == ASSUMPTIONS_VERSION
    assert v["cached"]["assumptions_version"] == ASSUMPTIONS_VERSION


def test_build_citation_unit_includes_version():
    card = {"created_at": "2026-06-04T10:00:00", "scenario_id": "abcd1234", "scenario_hash": "h",
            "stable_url": "/x", "scenario_type": "intake_failure", "params": {"time_horizon": 2040},
            "assumptions_version": "v3.0.0", "validation_status": "Directioneel gevalideerd ..."}
    cit = build_citation(card)
    assert cit["assumptions_version"] == "v3.0.0" and "Aannameversie: v3.0.0" in cit["metadata_block"]


# ---------------------------------------------------------------- Gap E: calibration
def test_calibration_agrees_with_design_reference():
    rep = asyncio.run(run_calibration(DATA))
    assert rep["n_total"] == 2 and rep["n_pass"] == 2 and rep["agreement_pct"] == 100.0
    assert all(c["verdict_match"] for c in rep["cases"])
    assert "extern" in rep["validation_status_nl"].lower()       # honest: external pending
    assert rep["kinds"] == ["design-reference"]


def test_calibration_endpoint():
    r = _c.get("/api/scenario/calibration")
    assert r.status_code == 200 and r.json()["n_total"] == 2


def test_validation_status_is_honest():
    s = validation_status().lower()
    assert "niet" in s and "extern" in s                          # does not claim external validation
