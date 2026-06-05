"""Deterministic Dutch intent router for the Phase-1 chatbot.

Four intents (see models.Intent). The router is keyword/heuristic-based and
deterministic — no LLM call — so routing is reproducible and testable offline.
The v3 design doc's `route_by_mode` sketch motivates this; here it only has to
separate read-only knowledge work from a *request to run a new scenario* (which
Phase 1 routes to the engine rather than executing).
"""
from __future__ import annotations

import re

from app.services.chatbot.text import raw_tokens

# Reliability / limitations / "what does the system NOT know".
_DATA_LIMIT_TERMS = (
    "beperking", "beperkingen", "betrouwbaar", "betrouwbaarheid", "onzeker",
    "onzekerheid", "nauwkeurig", "nauwkeurigheid", "marge", "foutmarge",
    "leeg", "lege", "ontbreek", "ontbreekt", "ontbreken", "mist", "missen",
    "aanname", "aannames", "proxy", "benadering", "schatting", "geschat",
    "kwaliteit van de data", "datakwaliteit", "klopt", "vals", "nadeel",
    "zwakte", "kanttekening", "kanttekeningen", "voorbehoud", "caveat",
    "hoe zeker", "hoe betrouwbaar", "wat weet", "niet weet", "weet niet",
    "verzadigd", "verzadigde", "headcount", "headcounts", "absolute",
    "relatief", "relatieve", "limitation", "limitations",
)

# Explanation of an existing result.
_EXPLAIN_TERMS = (
    "leg uit", "uitleg", "verklaar", "verklaring", "waarom", "hoe komt",
    "wat betekent", "betekenis", "dit resultaat", "deze uitkomst", "dit scenario",
    "deze score", "dit verdict", "dit oordeel", "toelichting", "onderbouw",
    "hoezo", "waardoor",
)

# Request to compute / run a NEW scenario (Phase 1 routes, never executes).
_RUN_TERMS = (
    "bereken", "reken", "doorreken", "doorrekenen", "run", "draai", "simuleer",
    "simulatie", "modelleer", "voer uit", "voer een", "stel dat", "wat als",
    "wat gebeurt er als", "scenario voor", "nieuw scenario", "maak een scenario",
    "kan er een", "kan een", "wat zou er gebeuren",
)

# Scenario "levers" — their presence strengthens a run-request reading.
_LEVER_RE = re.compile(
    r"\b(knmi|datacenter|\d+\s*mw|woningen|woning|inname|verzilting|"
    r"hollandse ijssel|ijssel|lek|maas|overstroming|2030|2040|2050)\b",
    re.IGNORECASE,
)


def _contains_any(haystack: str, needles) -> bool:
    return any(n in haystack for n in needles)


def classify_intent(question: str, has_scenario_card: bool = False) -> str:
    """Return one of: explain_scenario | data_limits | scenario_run_request | knowledge.

    Precedence is deliberate:
      1. If a ScenarioCard is in context and the question is explanatory -> explain_scenario.
      2. Reliability / limitation questions -> data_limits (so caveats are foregrounded).
      3. A clear request to RUN a new scenario -> scenario_run_request (route, don't run).
      4. Everything else -> knowledge.
    """
    q = (question or "").lower().strip()

    explanatory = _contains_any(q, _EXPLAIN_TERMS)
    if has_scenario_card and explanatory:
        return "explain_scenario"

    if _contains_any(q, _DATA_LIMIT_TERMS):
        return "data_limits"

    wants_run = _contains_any(q, _RUN_TERMS)
    if wants_run and not explanatory:
        # "wat als ..." / "bereken ..." with scenario levers is a run request.
        if _LEVER_RE.search(q) or _contains_any(q, ("scenario", "bereken", "simuleer", "doorreken")):
            return "scenario_run_request"

    # An explanatory question without a card in context is still knowledge
    # (we explain the methodology rather than a specific result).
    return "knowledge"
