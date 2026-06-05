"""Explain-mode: ground over an existing ScenarioCard (read-only), cite the hash."""
from conftest import SAMPLE_CARD

from app.services.chatbot.scenario_context import passages_from_card
from app.services.chatbot.service import answer_question


def test_card_becomes_passages():
    ps = passages_from_card(SAMPLE_CARD)
    assert any("Eindoordeel" in p.text_nl for p in ps)            # results
    assert any("Redeneerstap 2" in p.text_nl for p in ps)         # reasoning steps
    assert all(p.citation.kind == "scenario" for p in ps)
    # cited by the scenario hash + stable URL
    assert any(p.citation.url == "/api/scenario/abcd1234ef" for p in ps)


def test_explain_grounds_over_card():
    a = answer_question("Leg uit waarom dit resultaat STOP is", scenario_card=SAMPLE_CARD)
    assert a.intent == "explain_scenario"
    assert a.scenario_id == "abcd1234ef"
    assert any(c.kind == "scenario" for c in a.citations)
    low = a.answer_nl.lower()
    assert "stop" in low or "verzilting" in low or "redeneer" in low


def test_malformed_card_does_not_crash():
    assert passages_from_card({}) == []
    assert passages_from_card(None) == []
