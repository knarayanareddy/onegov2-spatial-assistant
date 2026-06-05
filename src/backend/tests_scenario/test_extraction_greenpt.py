"""Extraction: GreenPT path + deterministic fallback (Piece 2).
Uses an injected fake LLM factory so the wiring is tested without langchain/a key."""
from types import SimpleNamespace

from app.services.scenario.extraction import extract_scenario_params


def test_rule_fallback_when_no_key():
    # no GREENPT_KEY -> deterministic rule extractor
    p, conf = extract_scenario_params(
        "Wat als de Hollandse IJssel-inname 6 weken onbruikbaar is, KNMI Hd 2040?")
    assert p.scenario_type == "intake_failure" and p.intake_id == "IJssel" and p.outage_weeks == 6


def test_llm_used_when_forced_and_fields_mapped():
    class FakeStructured:
        def invoke(self, msgs):
            return SimpleNamespace(
                scenario_type="intake_failure", knmi_preset="Hd", time_horizon=2040,
                growth_preset="middel", location_name=None, development_type=None,
                development_mw=None, development_units=None, intake_id="Lek",
                outage_weeks=4, confidence=0.93)

    class FakeLLM:
        def with_structured_output(self, schema):
            return FakeStructured()

    p, conf = extract_scenario_params("vraag", use_llm=True, llm_factory=lambda m: FakeLLM())
    assert p.scenario_type == "intake_failure" and p.intake_id == "Lek"
    assert p.outage_weeks == 4 and conf == 0.93


def test_falls_back_to_rule_when_llm_raises():
    def boom(model):
        raise RuntimeError("GreenPT unavailable")

    p, conf = extract_scenario_params(
        "Kan er een 50 MW datacenter komen bij Pijnacker-Nootdorp in 2040?",
        use_llm=True, llm_factory=boom)
    assert p.scenario_type == "drop_pin" and p.development_type == "datacenter_50mw"
