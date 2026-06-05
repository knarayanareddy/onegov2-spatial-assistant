"""Chatbot orchestration — the single entry point ``answer_question``.

Pipeline: classify intent -> retrieve (corpus + optional ScenarioCard context,
with intent-aware boosting) -> compose a grounded B1-Dutch answer with citations.

Safety spine (Phase 1):
  - Read-only. A request to RUN a new scenario is ROUTED to the engine with a
    grounded explanation of the levers — never executed, never code/SQL.
  - No dead ends: low-confidence retrieval returns a clarifying question.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Optional

from app.services.chatbot.answer import compose_answer
from app.services.chatbot.corpus import get_default_corpus
from app.services.chatbot.intents import classify_intent
from app.services.chatbot.models import (
    ChatAnswer,
    Passage,
    RetrievedPassage,
    dedupe_citations,
)
from app.services.chatbot.retrieval import CONFIDENCE_THRESHOLD, BM25Retriever
from app.services.chatbot.scenario_context import passages_from_card

_LOW_CONF_NL = (
    "Ik heb hier in de beschikbare documentatie niet genoeg context voor om dit "
    "met zekerheid te beantwoorden."
)

_CLARIFY = {
    "data_limits": (
        "Over welke databron of beperking wil je meer weten — bijvoorbeeld verzilting "
        "(ZOUT_CONC), de CBS-bevolkingsproxy, of de lege tabellen?"
    ),
    "knowledge": (
        "Kun je je vraag iets specifieker maken? Bedoel je bijvoorbeeld de databronnen, "
        "de methodologie (de DrinkwaterDruk-score), of een specifiek scenario-resultaat?"
    ),
}


def _clarifying_question(intent: str) -> str:
    return _CLARIFY.get(intent, _CLARIFY["knowledge"])


def _card_id(scenario_card: Optional[dict]) -> Optional[str]:
    if isinstance(scenario_card, dict):
        sid = scenario_card.get("scenario_id")
        return str(sid) if sid else None
    return None


@lru_cache(maxsize=1)
def _default_retriever() -> BM25Retriever:
    return BM25Retriever(list(get_default_corpus()))


def _route_to_engine(question: str, retriever: BM25Retriever, intent: str, *,
                     model: str, llm_factory, use_llm, scenario_card) -> ChatAnswer:
    """A scenario *run* request: explain how to do it + the levers; do NOT run it."""
    retrieved = retriever.retrieve(question, top_k=4, boost_tags=("methodology",))
    sources = dedupe_citations([rp.passage.citation for rp in retrieved])
    answer = (
        "Ik kan in deze kennis-chat (fase 1) zelf nog geen nieuw scenario doorrekenen — "
        "dat doet de Scenario-engine, zodat de cijfers deterministisch, reproduceerbaar en "
        "met bron blijven. Gebruik daarvoor de knop 'Scenario-engine'. Ik kan je hier wél "
        "uitleggen welke knoppen (aannames met bron) een scenario heeft, zoals het "
        "KNMI-scenario, bevolkingsgroei, verbruik per persoon en de weging van de deelsignalen."
    )
    confidence = retriever.coverage(question, retrieved)
    return ChatAnswer(
        answer_nl=answer,
        intent=intent,
        confidence=confidence,
        citations=sources[:4],
        sources_considered=sources,
        followup_nl=(
            "Wil je dat ik de aannames van een scenario uitleg, of beschrijf je scenario "
            "(gebied, KNMI-scenario, jaartal) zodat je het in de Scenario-engine kunt doorrekenen?"
        ),
        used_llm=False,
        scenario_id=_card_id(scenario_card),
    )


def answer_question(question: str, *,
                    corpus: Optional[list[Passage]] = None,
                    scenario_card: Optional[dict] = None,
                    model: str = "qwen3-235b-a22b-instruct-2507",
                    llm_factory: Optional[Callable] = None,
                    use_llm: Optional[bool] = None,
                    top_k: int = 6) -> ChatAnswer:
    has_card = bool(scenario_card)
    card_passages = passages_from_card(scenario_card) if has_card else []
    intent = classify_intent(question, has_card)

    # Build the retriever (cache the common no-card / default-corpus case).
    if corpus is None and not has_card:
        retriever = _default_retriever()
    else:
        base = list(corpus) if corpus is not None else list(get_default_corpus())
        retriever = BM25Retriever(base + card_passages)

    # Route a run-request to the engine (no execution).
    if intent == "scenario_run_request":
        return _route_to_engine(question, retriever, intent, model=model,
                                llm_factory=llm_factory, use_llm=use_llm,
                                scenario_card=scenario_card)

    boost_tags = ("data_limits",) if intent == "data_limits" else ()
    boost_kinds = ("scenario",) if intent == "explain_scenario" else ()
    retrieved = retriever.retrieve(question, top_k=top_k,
                                   boost_tags=boost_tags, boost_kinds=boost_kinds)

    # Explain-mode must always ground on the card, even if word overlap is low.
    if intent == "explain_scenario" and not retrieved and card_passages:
        retrieved = [RetrievedPassage(p, 0.0) for p in card_passages[:top_k]]

    confidence = retriever.coverage(question, retrieved)
    sources_considered = dedupe_citations([rp.passage.citation for rp in retrieved])

    # No dead ends: clarify when retrieval is weak (explain-mode is exempt — the
    # attached card is strong, relevant context).
    if (not retrieved) or (confidence < CONFIDENCE_THRESHOLD and intent != "explain_scenario"):
        return ChatAnswer(
            answer_nl=_LOW_CONF_NL,
            intent=intent,
            confidence=confidence,
            citations=[],
            sources_considered=sources_considered,
            followup_nl=_clarifying_question(intent),
            used_llm=False,
            scenario_id=_card_id(scenario_card),
        )

    answer_nl, used_llm = compose_answer(question, intent, retrieved, model=model,
                                         llm_factory=llm_factory, use_llm=use_llm)
    citations = dedupe_citations([rp.passage.citation for rp in retrieved[:4]])
    return ChatAnswer(
        answer_nl=answer_nl,
        intent=intent,
        confidence=confidence,
        citations=citations,
        sources_considered=sources_considered,
        followup_nl=None,
        used_llm=used_llm,
        scenario_id=_card_id(scenario_card),
    )
