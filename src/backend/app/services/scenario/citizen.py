"""Citizen mode (design doc GAP 10): a verdict-first, plain-Dutch response for the
public — no m³/jargon, postcode-aware, with the responsible water company and the
official policy link. Deterministic (no LLM needed)."""
from __future__ import annotations

import re
from typing import Any

from app.services.scenario.official_positions import OFFICIAL_POSITIONS

CITIZEN_PHRASES = (
    "mijn water", "ons water", "is het veilig", "drinkwater veilig", "kan ik nog",
    "voor mijn buurt", "bij mij thuis", "in mijn straat", "mijn postcode", "mijn wijk",
    "wat betekent dit voor mij",
)
POSTCODE_RE = re.compile(r"\b([1-9][0-9]{3})\s?([A-Za-z]{2})\b")

WATER_COMPANIES = {
    "dunea": {"name": "Dunea", "url": "https://www.dunea.nl", "phone": "0800-5000 400",
              "keywords": ("den haag", "westland", "zoetermeer", "leiden")},
    "evides": {"name": "Evides Waterbedrijf", "url": "https://www.evides.nl", "phone": "0900-0929",
               "keywords": ("rotterdam", "dordrecht", "voorne", "goeree")},
    "oasen": {"name": "Oasen", "url": "https://www.oasen.nl", "phone": "088-0880 100",
              "keywords": ("gouda", "alphen", "ijssel", "krimpen")},
}
DEFAULT_COMPANY = {"name": "Uw drinkwaterbedrijf", "url": "https://www.vewin.nl/drinkwaterbedrijven",
                   "phone": "Zie uw waterbedrijf"}

VERDICT_CITIZEN = {
    "GO": "Op dit moment lijkt je drinkwater veilig.",
    "CAUTION": "Je drinkwater vraagt aandacht: bij droogte en verzilting kan de voorziening krap worden.",
    "STOP": "In dit scenario is er een risico voor je drinkwater; de voorziening kan onder druk komen.",
}


def detect_citizen_mode(question: str, persona: str | None = None) -> bool:
    if persona and persona.lower() in ("citizen", "burger"):
        return True
    q = question.lower()
    return any(p in q for p in CITIZEN_PHRASES) or bool(POSTCODE_RE.search(question))


def _postcode(question: str) -> str | None:
    m = POSTCODE_RE.search(question)
    return f"{m.group(1)}{m.group(2).upper()}" if m else None


def _water_company(question: str) -> dict:
    q = question.lower()
    for c in WATER_COMPANIES.values():
        if any(k in q for k in c["keywords"]):
            return {k: v for k, v in c.items() if k != "keywords"}
    return dict(DEFAULT_COMPANY)


def format_citizen_response(card: Any, question: str) -> dict:
    """Verdict-first, <100-word, jargon-free citizen card. `card` may be a dict or ScenarioCard."""
    results = card["results"] if isinstance(card, dict) else card.results
    params = card["params"] if isinstance(card, dict) else card.params
    fc = results["feasibility_class"] if isinstance(results, dict) else results.feasibility_class
    horizon = params["time_horizon"] if isinstance(params, dict) else params.time_horizon

    wc = _water_company(question)
    docs = OFFICIAL_POSITIONS["drinkwater_zh"].documents[:2]
    return {
        "postcode": _postcode(question),
        "verdict_nl": VERDICT_CITIZEN.get(fc, "We konden dit niet goed bepalen."),
        "explanation_nl": (f"Dit is een verkenning voor het jaar {horizon}. Het gaat over de regio, "
                           f"niet over jouw kraan thuis."),
        "action_nl": f"Wil je het zeker weten? Neem contact op met {wc['name']}.",
        "water_company": wc,
        "official_links": [{"title": d["title"], "url": d["url"]} for d in docs],
        "disclaimer_nl": "Dit is een exploratief scenario, geen officiële meting.",
    }
