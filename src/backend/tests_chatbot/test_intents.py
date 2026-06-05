"""Intent router: data_limits / scenario_run_request / explain_scenario / knowledge."""
from app.services.chatbot.intents import classify_intent


def test_data_limits():
    assert classify_intent("Hoe betrouwbaar zijn de data?") == "data_limits"
    assert classify_intent("Wat zijn de beperkingen van de CBS-data?") == "data_limits"


def test_scenario_run_request():
    assert classify_intent(
        "Bereken een scenario met KNMI Hd en een datacenter bij Pijnacker in 2040"
    ) == "scenario_run_request"
    assert classify_intent("Wat als de Hollandse IJssel-inname uitvalt?") == "scenario_run_request"


def test_explain_requires_card():
    assert classify_intent("Leg uit waarom dit STOP is", has_scenario_card=True) == "explain_scenario"
    # without a card, an explanation request is knowledge (explain the methodology)
    assert classify_intent("Leg uit waarom verzilting meetelt") == "knowledge"


def test_knowledge_default():
    assert classify_intent("Wat is verzilting?") == "knowledge"
    assert classify_intent("Welke databronnen zijn er?") == "knowledge"
