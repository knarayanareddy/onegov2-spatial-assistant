"""Answer composer: keyless fallback, caveat surfacing, GreenPT path + fallback.

GreenPT is exercised via an injected fake LLM factory (no key / langchain needed),
mirroring tests_scenario/test_extraction_greenpt.py.
"""
from app.services.chatbot.service import answer_question


def test_keyless_fallback_is_cited_and_deterministic():
    a = answer_question("Welke databronnen gebruikt het systeem?")
    assert a.used_llm is False
    assert a.citations and a.followup_nl is None
    assert "Bronnen" in a.answer_nl  # extractive composer appends a source list
    b = answer_question("Welke databronnen gebruikt het systeem?")
    assert a.answer_nl == b.answer_nl  # deterministic


def test_data_limits_answer_surfaces_caveat():
    a = answer_question("Wat zijn de beperkingen van de CBS-data?")
    assert a.intent == "data_limits"
    low = a.answer_nl.lower()
    assert ("proxy" in low or "dichtheid" in low or "headcount" in low or "~46" in low)


def test_greenpt_path_used_when_factory_injected():
    class FakeMsg:
        content = "De DrinkwaterDruk-score is een maat van 0 tot 100 [1]."

    class FakeLLM:
        def invoke(self, msgs):
            # grounding contract: a system + user message pair is passed in
            assert len(msgs) == 2 and msgs[0][0] == "system"
            return FakeMsg()

    a = answer_question("Wat is de DrinkwaterDruk-score?", llm_factory=lambda m: FakeLLM())
    assert a.used_llm is True and "DrinkwaterDruk-score is een maat" in a.answer_nl


def test_falls_back_to_extractive_when_llm_raises():
    def boom(model):
        raise RuntimeError("GreenPT unavailable")

    a = answer_question("Wat is de DrinkwaterDruk-score?", llm_factory=boom)
    assert a.used_llm is False and a.citations


def test_offtopic_question_asks_clarifying_question():
    a = answer_question("Wat is de hoofdstad van Frankrijk?")
    assert a.followup_nl is not None and a.confidence < 0.34
