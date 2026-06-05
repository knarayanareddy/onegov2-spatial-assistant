"""SSE endpoint tests (design doc §6, v3): single run + comparison + stable URL.
Mounts only the scenario router (no Postgres/MLflow needed)."""
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import scenario

app = FastAPI()
app.include_router(scenario.router)
client = TestClient(app)

Q = "Verzilting op de Hollandse IJssel onder KNMI Hd in 2040"


def _parse_sse(text: str):
    events, ev = [], None
    for line in text.splitlines():
        if line.startswith("event:"):
            ev = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and ev is not None:
            events.append((ev, line.split(":", 1)[1].strip()))
    return events


def test_single_run_streams_card_and_stable_url():
    r = client.post("/api/scenario/run", json={"question": Q})
    assert r.status_code == 200
    events = _parse_sse(r.text)
    names = [n for n, _ in events]
    assert "scenario_card" in names
    assert "feasibility_class" in names
    assert "map_data" in names
    assert names[-1] == "done"

    card = json.loads(dict(events)["scenario_card"])
    assert card["results"]["feasibility_class"] in {"GO", "CAUTION", "STOP"}
    sid = card["scenario_id"]

    g = client.get(f"/api/scenario/{sid}")
    assert g.status_code == 200 and g.json()["scenario_id"] == sid and g.json()["cache_used"] is True
    assert client.get("/api/scenario/does-not-exist").status_code == 404


def test_comparison_streams_two_cards_and_delta():
    r = client.post("/api/scenario/run", json={"question": Q, "compare": True})
    assert r.status_code == 200
    names = [n for n, _ in _parse_sse(r.text)]
    assert names.count("scenario_card") == 2       # baseline + shock
    assert "scenario_delta" in names
    assert names[-1] == "done"
