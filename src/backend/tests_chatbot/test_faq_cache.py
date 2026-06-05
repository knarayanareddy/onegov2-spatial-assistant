"""FAQ cache + ranking + moderation (Phase 3).

Logic is exercised against the in-memory store (the autouse fixture in conftest
gives each test a fresh store); the Postgres adapter shares this interface and is
validated in your environment.
"""
import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import chatbot
from app.services.chatbot import faq_cache as fc


class _Cite:
    def as_dict(self):
        return {"title_nl": "Ontwerpdoc", "url": "https://example.org/doc"}


class _Ans:
    """Minimal ChatAnswer stand-in."""
    def __init__(self, intent="knowledge", confidence=0.9, citations=None,
                 followup=None, answer="Antwoord met bron [1]."):
        self.intent = intent
        self.confidence = confidence
        self.citations = citations if citations is not None else [_Cite()]
        self.followup_nl = followup
        self.answer_nl = answer


# --------------------------------------------------------------- keys / gate
def test_cache_key_collapses_paraphrase_and_strips_pii():
    assert fc.make_cache_key("Welke databronnen?") == fc.make_cache_key("databronnen welke")
    key = fc.make_cache_key("mijn postcode is 2611 AB")
    assert "2611" not in key and "ab" not in key.split("|")  # PII never enters the key


def test_should_cache_gate():
    assert fc.should_cache("knowledge", 0.9, [1]) is True
    assert fc.should_cache("data_limits", 0.9, [1]) is True
    assert fc.should_cache("knowledge", 0.3, [1]) is False        # low confidence
    assert fc.should_cache("knowledge", 0.9, []) is False         # no citations
    assert fc.should_cache("explain_scenario", 0.9, [1]) is False  # wrong intent
    assert fc.should_cache("knowledge", 0.9, [1], followup_nl="?") is False


# --------------------------------------------------------------- capture / dedup
def test_capture_dedups_and_counts_hits():
    a = asyncio.run(fc.capture_answer("Welke databronnen?", _Ans()))
    b = asyncio.run(fc.capture_answer("databronnen welke", _Ans()))
    assert a.id == b.id and b.hits == 2 and a.status == "suggested"


def test_uncacheable_answer_not_stored():
    assert asyncio.run(fc.capture_answer("x", _Ans(confidence=0.2))) is None
    assert asyncio.run(fc.capture_answer("x", _Ans(citations=[]))) is None


def test_pii_in_question_is_anonymised_before_storage():
    e = asyncio.run(fc.capture_answer("Mag mijn buurman op 2611 AB hier wonen?", _Ans()))
    assert "2611" not in e.question_display and "[postcode]" in e.question_display


# --------------------------------------------------------------- moderation
def test_promote_then_published_and_ranked():
    e = asyncio.run(fc.capture_answer("Welke databronnen?", _Ans()))
    ok, why = asyncio.run(fc.get_store().promote(e.id))
    assert ok and why == "ok"
    pub = asyncio.run(fc.published_as_faqs(10))
    assert len(pub) == 1 and pub[0]["origin"] == "cached" and pub[0]["hits"] == 1


def test_rejected_entry_is_not_promotable():
    e = asyncio.run(fc.capture_answer("Welke databronnen?", _Ans()))
    asyncio.run(fc.get_store().reject(e.id))
    ok, why = asyncio.run(fc.get_store().promote(e.id))
    assert not ok and why == "rejected"
    assert asyncio.run(fc.published_as_faqs(10)) == []


def test_published_ranked_by_hits():
    e1 = asyncio.run(fc.capture_answer("Welke databronnen?", _Ans()))
    e2 = asyncio.run(fc.capture_answer("Wat is de DrinkwaterDruk-score?", _Ans()))
    asyncio.run(fc.capture_answer("Wat is de DrinkwaterDruk-score?", _Ans()))  # e2 hits=2
    asyncio.run(fc.get_store().promote(e1.id))
    asyncio.run(fc.get_store().promote(e2.id))
    pub = asyncio.run(fc.published_as_faqs(10))
    assert [p["hits"] for p in pub] == sorted([p["hits"] for p in pub], reverse=True)
    assert pub[0]["id"] == e2.id  # most-asked first


# --------------------------------------------------------------- invalidation
def test_stale_stamp_is_filtered():
    e = asyncio.run(fc.capture_answer("Welke databronnen?", _Ans()))
    asyncio.run(fc.get_store().promote(e.id))
    real = fc.current_version_stamp()
    assert len(asyncio.run(fc.get_store().list_published(10, real))) == 1
    assert len(asyncio.run(fc.get_store().list_published(10, "STALE-STAMP"))) == 0


# --------------------------------------------------------------- endpoints
_app = FastAPI()
_app.include_router(chatbot.router)
_client = TestClient(_app)


def test_endpoint_capture_moderate_and_serve():
    # A confident, cited knowledge answer is captured as a suggestion.
    r = _client.post("/api/chatbot/ask", json={"question": "Welke databronnen gebruikt het systeem?"})
    assert r.status_code == 200
    sug = _client.get("/api/chatbot/faqs/suggested").json()["suggestions"]
    assert len(sug) >= 1
    eid = sug[0]["id"]
    # Promote it -> appears in the merged FAQ list as origin "cached".
    assert _client.post(f"/api/chatbot/faqs/suggested/{eid}/promote").status_code == 200
    faqs = _client.get("/api/chatbot/faqs").json()["faqs"]
    assert any(f.get("origin") == "curated" for f in faqs)
    assert any(f.get("origin") == "cached" for f in faqs)


def test_endpoint_promote_missing_is_404():
    assert _client.post("/api/chatbot/faqs/suggested/not-a-real-id/promote").status_code == 404


def test_endpoint_reject_then_promote_is_422():
    _client.post("/api/chatbot/ask", json={"question": "Wat zijn de beperkingen van de CBS-data?"})
    sug = _client.get("/api/chatbot/faqs/suggested").json()["suggestions"]
    eid = sug[0]["id"]
    assert _client.post(f"/api/chatbot/faqs/suggested/{eid}/reject").status_code == 200
    assert _client.get("/api/chatbot/faqs/suggested").json()["suggestions"] == []
    assert _client.post(f"/api/chatbot/faqs/suggested/{eid}/promote").status_code == 422


def test_curated_faq_by_id_still_works():
    assert _client.get("/api/chatbot/faqs/data-beperkingen").status_code == 200
    assert _client.get("/api/chatbot/faqs/nope").status_code == 404
