"""Phase 2 — scenario-from-chat: whitelist gate, comparison detection, real run.

The validation gate is exercised with the deterministic rule extractor and with
an injected fake LLM (for the cases the rule extractor can't produce), mirroring
tests_scenario/test_extraction_greenpt.py.
"""
import asyncio
from types import SimpleNamespace

from conftest import SAMPLE_CARD
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import chatbot
from app.services.chatbot.scenario_run import (
    ALLOWED_LEVER_KEYS,
    execute_plan,
    prepare_scenario_request,
)
from app.services.helpers.tables import DATA_DIR

DATA = str(DATA_DIR)


def _fake_llm(**fields):
    base = dict(scenario_type="intake_failure", knmi_preset="Hd", time_horizon=2040,
                growth_preset="middel", location_name=None, development_type=None,
                development_mw=None, development_units=None, intake_id="IJssel",
                outage_weeks=6, confidence=0.9)
    base.update(fields)

    class FakeStructured:
        def invoke(self, msgs):
            return SimpleNamespace(**base)

    class FakeLLM:
        def with_structured_output(self, schema):
            return FakeStructured()

    return lambda model: FakeLLM()


# ----------------------------------------------------------------- validation gate
def test_valid_intake_is_runnable():
    p = prepare_scenario_request(
        "Wat als de Hollandse IJssel-inname 6 weken uitvalt onder KNMI Hd in 2040?")
    assert p.runnable and p.params.scenario_type == "intake_failure"
    assert p.params.intake_id == "IJssel" and p.params.knmi_preset == "Hd"


def test_unknown_lever_is_rejected():
    p = prepare_scenario_request("inname IJssel KNMI Hd", overrides={"weight_unicorns": 0.9})
    assert not p.runnable and p.reason == "unknown_lever"
    assert "weight_unicorns" not in ALLOWED_LEVER_KEYS  # guard: never an allowed key


def test_weight_out_of_range_is_rejected():
    p = prepare_scenario_request("inname IJssel KNMI Hd", overrides={"weight_salinity": 2.0})
    assert not p.runnable and p.reason == "weight_out_of_range"


def test_low_confidence_clarifies():
    p = prepare_scenario_request("iets vaags", use_llm=True, llm_factory=_fake_llm(confidence=0.3))
    assert not p.runnable and p.reason == "low_confidence"


def test_unknown_intake_clarifies():
    p = prepare_scenario_request("inname scenario", use_llm=True,
                                 llm_factory=_fake_llm(intake_id="Spree", confidence=0.9))
    assert not p.runnable and p.reason == "unknown_intake"


def test_missing_location_clarifies():
    p = prepare_scenario_request("een drop-pin scenario", use_llm=True,
                                 llm_factory=_fake_llm(scenario_type="drop_pin",
                                                       location_name=None, intake_id=None))
    assert not p.runnable and p.reason == "missing_location"


def test_comparison_is_detected():
    p = prepare_scenario_request("Vergelijk verzilting met en zonder droogteschok op de IJssel")
    assert p.runnable and p.compare is True


# ----------------------------------------------------------------- real engine run
def test_execute_plan_returns_real_card():
    p = prepare_scenario_request(
        "Wat als de Hollandse IJssel-inname uitvalt onder KNMI Hd in 2040?")
    res = asyncio.run(execute_plan(p, "q", DATA))
    assert res["mode"] == "single"
    assert res["card"].results.feasibility_class in {"GO", "CAUTION", "STOP"}
    assert res["card"].results.n_cells > 0


def test_execute_comparison_returns_delta():
    p = prepare_scenario_request("Vergelijk met en zonder schok op de Hollandse IJssel")
    res = asyncio.run(execute_plan(p, "q", DATA))
    assert res["mode"] == "comparison"
    assert res["card_a"] is not None and res["card_b"] is not None
    assert res["delta"].feasibility_change


# ----------------------------------------------------------------- SSE endpoint
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


def test_endpoint_runs_scenario_and_streams_card():
    import json
    r = _client.post("/api/chatbot/ask",
                     json={"question": "Wat als de Hollandse IJssel-inname uitvalt onder KNMI Hd in 2040?"})
    assert r.status_code == 200
    events = _parse_sse(r.text)
    names = [n for n, _ in events]
    assert "scenario_params_confirmed" in names
    assert "scenario_card" in names and "map_data" in names
    assert names[-1] == "done"
    card = json.loads(dict(events)["scenario_card"])
    assert card["results"]["feasibility_class"] in {"GO", "CAUTION", "STOP"}


def test_endpoint_clarifies_underspecified_run():
    r = _client.post("/api/chatbot/ask", json={"question": "Bereken een scenario"})
    names = [n for n, _ in _parse_sse(r.text)]
    assert "followup_question" in names and "scenario_card" not in names
