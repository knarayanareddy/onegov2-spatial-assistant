"""SSE endpoint + FAQ routes. Mounts only the chatbot router (no Postgres/MLflow)."""
import json

from conftest import SAMPLE_CARD
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import chatbot

app = FastAPI()
app.include_router(chatbot.router)
client = TestClient(app)


def _parse_sse(text: str):
    events, ev = [], None
    for line in text.splitlines():
        if line.startswith("event:"):
            ev = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and ev is not None:
            events.append((ev, line.split(":", 1)[1].strip()))
    return events


def test_ask_streams_grounded_answer():
    r = client.post("/api/chatbot/ask", json={"question": "Welke databronnen gebruikt het systeem?"})
    assert r.status_code == 200
    events = _parse_sse(r.text)
    names = [n for n, _ in events]
    assert "intent" in names and "text" in names and "citations" in names
    assert names[-1] == "done"
    # citations are present and structured
    cites = json.loads(dict(events)["citations"])
    assert isinstance(cites, list) and cites


def test_ask_data_limits_surfaces_caveat_in_stream():
    r = client.post("/api/chatbot/ask", json={"question": "Wat zijn de beperkingen van de data?"})
    text = " ".join(
        json.loads(d)["content"] for n, d in _parse_sse(r.text) if n == "text"
    ).lower()
    assert "beperking" in text or "proxy" in text or "leeg" in text or "verzadig" in text


def test_ask_offtopic_emits_followup():
    r = client.post("/api/chatbot/ask", json={"question": "Wat is de hoofdstad van Frankrijk?"})
    names = [n for n, _ in _parse_sse(r.text)]
    assert "followup_question" in names


def test_ask_explain_with_inline_card():
    r = client.post(
        "/api/chatbot/ask",
        json={"question": "Leg uit waarom dit STOP is", "scenario_card": SAMPLE_CARD},
    )
    intent = json.loads(dict(_parse_sse(r.text))["intent"])
    assert intent["intent"] == "explain_scenario" and intent["scenario_id"] == "abcd1234ef"


def test_empty_question_rejected():
    assert client.post("/api/chatbot/ask", json={"question": "   "}).status_code == 422


def test_faqs_endpoints():
    r = client.get("/api/chatbot/faqs")
    assert r.status_code == 200 and len(r.json()["faqs"]) >= 8
    assert client.get("/api/chatbot/faqs/data-beperkingen").status_code == 200
    assert client.get("/api/chatbot/faqs/nope").status_code == 404
