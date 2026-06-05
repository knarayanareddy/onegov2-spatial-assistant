import os
import sys

import pytest

# Ensure `app...` imports resolve when pytest is invoked from anywhere.
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


@pytest.fixture(autouse=True)
def _reset_faq_cache_store():
    """Phase 3: give every test a fresh in-memory FAQ cache (the store is a
    module-level singleton)."""
    from app.services.chatbot import faq_cache as _fc
    _fc.set_store(_fc.InMemoryFaqCache())
    yield

# A small, realistic ScenarioCard (asdict shape) for explain-mode tests.
SAMPLE_CARD = {
    "scenario_id": "abcd1234ef",
    "scenario_hash": "hash1234" * 4,
    "created_at": "2026-06-04T00:00:00Z",
    "git_commit": "deadbeef",
    "stable_url": "/api/scenario/abcd1234ef",
    "question_nl": "Verzilting op de Hollandse IJssel onder KNMI Hd in 2040",
    "scenario_type": "intake_failure",
    "results": {
        "feasibility_class": "STOP",
        "score_avg": 82.4,
        "stop_share": 0.6,
        "n_cells": 110,
        "n_stop": 70,
        "n_caution": 30,
        "n_go": 10,
        "themes_used": ["verzilting", "zes_uur_zones_drinkwater", "cbs"],
    },
    "reasoning_steps": [
        {"step_nr": 1, "label_nl": "Gebiedsselectie",
         "description_nl": "110 zes-uurscellen rond de inname geselecteerd",
         "datasets_used": ["zes_uur_zones_drinkwater"]},
        {"step_nr": 2, "label_nl": "Verziltingsscore",
         "description_nl": "ZOUT_CONC-klasse vermenigvuldigd met de KNMI-droogtefactor",
         "calculated_value": "0.82", "datasets_used": ["verzilting"]},
    ],
    "official_position": {
        "primary": {"summary_nl": "De provincie werkt aan een robuuste voorziening tot 2040."},
        "positions": [],
        "disclaimer_nl": "Dit is geen officieel standpunt.",
    },
    "source_registry": [{"label": "KNMI'23", "url": "https://www.knmi.nl/klimaatscenarios"}],
    "overlays": [],
}
