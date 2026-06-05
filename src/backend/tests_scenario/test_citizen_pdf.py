"""GAP 10 citizen mode + GAP 3 PDF/citation."""
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import scenario
from app.services.scenario.citizen import detect_citizen_mode, format_citizen_response
from app.services.scenario.pdf import build_citation, render_scenario_pdf

app = FastAPI()
app.include_router(scenario.router)
client = TestClient(app)

_CARD = {
    "scenario_id": "abc12345", "scenario_hash": "h", "created_at": "2026-06-04T10:00:00+00:00",
    "git_commit": "deadbee", "stable_url": "http://localhost:8001/scenario/abc12345",
    "question_nl": "x", "scenario_type": "intake_failure", "params": {"time_horizon": 2040},
    "results": {"feasibility_class": "STOP", "score_avg": 82.4, "n_cells": 110, "stop_share": 1.0,
                "themes_used": ["verzilting", "cbs"], "human_scale": {"analogy_nl": "≈ 11 km² — test"},
                "interventions_ranked": [{"label_nl": "Interconnectie", "new_area_verdict": "CAUTION",
                                          "stop_share_reduction_pct": 90, "source_label": "RWP 2022–2027"}]},
    "reasoning_steps": [{"step_nr": 1, "label_nl": "Gebied", "description_nl": "zes-uur — test"}],
    "official_position": {"disclaimer_nl": "verkenning"},
}


def test_detect_citizen_mode():
    assert detect_citizen_mode("Is mijn water veilig in 2040?")
    assert detect_citizen_mode("iets", persona="burger")
    assert detect_citizen_mode("Wat gebeurt er bij 2611 AB?")          # postcode
    assert not detect_citizen_mode("Wat als de IJssel verzilt onder KNMI Hd?")


def test_citizen_card_is_verdict_first_and_jargon_free():
    r = format_citizen_response({"results": {"feasibility_class": "STOP"}, "params": {"time_horizon": 2040}},
                                "Is mijn water veilig in Rotterdam? 3011 AB")
    assert r["verdict_nl"] and r["disclaimer_nl"]
    assert r["water_company"]["name"] == "Evides Waterbedrijf"   # Rotterdam -> Evides
    assert r["postcode"] == "3011AB"
    blob = " ".join([r["verdict_nl"], r["explanation_nl"], r["action_nl"]])
    assert "m³" not in blob and "m3" not in blob                  # no jargon


def test_pdf_bytes_and_citation_unicode_safe():
    data = render_scenario_pdf(_CARD)                            # contains –, ³, ≈, →
    assert data[:4] == b"%PDF" and len(data) > 800
    cit = build_citation(_CARD)
    assert "abc12345" in cit["apa_nl"] and cit["stable_url"].endswith("abc12345")


def test_citizen_endpoint_emits_citizen_response():
    r = client.post("/api/scenario/run",
                    json={"question": "Is mijn water veilig in 2040? 2611 AB", "user_persona": "citizen"})
    names = [l.split(":", 1)[1].strip() for l in r.text.splitlines() if l.startswith("event:")]
    assert "citizen_response" in names


def test_pdf_and_citation_endpoints():
    rr = client.post("/api/scenario/run", json={"question": "Verzilting op de Hollandse IJssel onder KNMI Hd"})
    sid, ev = None, None
    for l in rr.text.splitlines():
        if l.startswith("event:"):
            ev = l.split(":", 1)[1].strip()
        elif l.startswith("data:") and ev == "scenario_card":
            sid = json.loads(l.split(":", 1)[1].strip())["scenario_id"]
            break
    assert sid
    p = client.get(f"/api/scenario/{sid}/pdf")
    assert p.status_code == 200 and p.content[:4] == b"%PDF"
    c = client.get(f"/api/scenario/{sid}/citation")
    assert c.status_code == 200 and c.json()["scenario_id"] == sid
