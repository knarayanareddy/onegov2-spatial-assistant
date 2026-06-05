"""Phase 4 — declarative recipe-builder: validation, mapping, real run, endpoints."""
import asyncio
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import chatbot
from app.services.chatbot import recipe as rc
from app.services.helpers.tables import DATA_DIR

DATA = str(DATA_DIR)
_BAL = {"salinity": 0.4, "demand": 0.3, "flood": 0.2, "protection": 0.1}


# ----------------------------------------------------------------- schema
def test_schema_signals_default_to_one():
    sch = rc.recipe_schema()
    keys = {s["key"] for s in sch["signals"]}
    assert keys == {"salinity", "demand", "flood", "protection"}
    assert abs(sum(s["default"] for s in sch["signals"]) - 1.0) < 1e-9
    assert "B" in sch["knmi_presets"] and "populated" in sch["base_options"]


# ----------------------------------------------------------------- validation
def test_valid_recipe_maps_to_overrides():
    p = rc.validate_recipe({"weights": _BAL, "knmi_preset": "Hd"})
    assert p.runnable and p.params.scenario_type == "multi_hazard"
    assert p.params.assumption_overrides["weight_salinity"] == 0.4
    assert p.params.assumption_overrides["weight_demand"] == 0.3


def test_weights_must_sum_to_one():
    p = rc.validate_recipe({"weights": {"salinity": 0.5, "demand": 0.3, "flood": 0.2, "protection": 0.1}})
    assert not p.runnable and p.reason == "weights_sum"


def test_unknown_signal_rejected():
    p = rc.validate_recipe({"weights": {"unicorns": 1.0}})
    assert not p.runnable and p.reason == "unknown_signal"


def test_weight_out_of_range_rejected():
    p = rc.validate_recipe({"weights": {"salinity": 1.5, "demand": -0.5}})
    assert not p.runnable and p.reason == "weight_out_of_range"


def test_bad_presets_rejected():
    assert rc.validate_recipe({"weights": _BAL, "knmi_preset": "Z"}).reason == "bad_knmi"
    assert rc.validate_recipe({"weights": _BAL, "growth_preset": "enorm"}).reason == "bad_growth"
    assert rc.validate_recipe({"weights": _BAL, "base": "mars"}).reason == "bad_base"


def test_unknown_intake_rejected():
    p = rc.validate_recipe({"weights": _BAL, "intake_id": "Spree"})
    assert not p.runnable and p.reason == "unknown_intake"


def test_intake_and_location_set_scenario_type():
    assert rc.validate_recipe({"weights": _BAL, "intake_id": "IJssel"}).params.scenario_type == "intake_failure"
    assert rc.validate_recipe({"weights": _BAL, "location_name": "Pijnacker"}).params.scenario_type == "drop_pin"


# ----------------------------------------------------------------- real run
def test_execute_recipe_returns_card():
    p = rc.validate_recipe({"weights": _BAL})
    res = asyncio.run(rc.execute_recipe(p, DATA))
    assert res["mode"] == "single"
    assert res["card"].results.feasibility_class in {"GO", "CAUTION", "STOP"}
    assert res["card"].results.n_cells > 0


def test_populated_base_changes_universe():
    sal = asyncio.run(rc.execute_recipe(rc.validate_recipe({"weights": _BAL, "base": "salinity"}), DATA))
    pop = asyncio.run(rc.execute_recipe(rc.validate_recipe({"weights": _BAL, "base": "populated"}), DATA))
    assert sal["card"].results.n_cells != pop["card"].results.n_cells


# ----------------------------------------------------------------- endpoints
_app = FastAPI()
_app.include_router(chatbot.router)
_client = TestClient(_app)


def _parse_sse(text: str):
    events, ev = [], None
    for line in text.splitlines():
        if line.startswith("event:"):
            ev = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and ev is not None:
            events.append((ev, line.split(":", 1)[1].strip()))
    return events


def test_schema_endpoint():
    r = _client.get("/api/chatbot/recipe/schema")
    assert r.status_code == 200 and len(r.json()["signals"]) == 4


def test_recipe_run_endpoint_streams_card():
    r = _client.post("/api/chatbot/recipe/run", json={"weights": _BAL, "knmi_preset": "Hd"})
    assert r.status_code == 200
    names = [n for n, _ in _parse_sse(r.text)]
    assert "scenario_params_confirmed" in names and "scenario_card" in names
    assert names[-1] == "done"


def test_recipe_run_endpoint_clarifies_bad_weights():
    r = _client.post("/api/chatbot/recipe/run", json={"weights": {"salinity": 0.9, "demand": 0.3}})
    names = [n for n, _ in _parse_sse(r.text)]
    assert "followup_question" in names and "scenario_card" not in names
