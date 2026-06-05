"""B1-Dutch answer composer.

Two paths, one entry point (mirrors extraction.py's discipline):
  - GreenPT path: app.services.llm.make_llm at temperature 0, grounded strictly
    on the retrieved passages, citing sources by [n]. Lazy import so the module
    stays importable offline.
  - Deterministic extractive fallback: keyless, reproducible — pulls the most
    relevant sentence from each top passage and appends a 'Bronnen:' list.

compose_answer() auto-selects (GreenPT when a key/factory is available) and
ALWAYS falls back to the extractive composer on any error, so the bot works
without a key and tests stay offline.
"""
from __future__ import annotations

import os
from typing import Callable, Optional

from app.services.chatbot.models import RetrievedPassage
from app.services.chatbot.text import content_tokens, split_sentences_nl

_INTRO = {
    "knowledge": "Op basis van de beschikbare documentatie:",
    "data_limits": "Let op de volgende databeperkingen:",
    "explain_scenario": "Uitleg van dit scenario-resultaat:",
}

# B1-Dutch, grounding-strict system prompts. Temperature is pinned to 0.
_SYSTEM_BASE = (
    "Je bent een behulpzame assistent voor het OneGov #2-systeem over "
    "drinkwaterzekerheid in Zuid-Holland. Beantwoord de vraag UITSLUITEND op basis "
    "van de meegegeven genummerde context. Schrijf in eenvoudig Nederlands op "
    "B1-niveau: korte zinnen, weinig jargon, leg vaktermen kort uit. Verwijs bij "
    "elke bewering naar de bron met [nummer]. Verzin niets en noem geen getallen "
    "die niet in de context staan. Als de context onvoldoende is, zeg dat eerlijk "
    "en stel één verduidelijkende vraag. Sluit af met een korte 'Bronnen:'-lijst."
)
_SYSTEM = {
    "knowledge": _SYSTEM_BASE,
    "data_limits": _SYSTEM_BASE + (
        " De vraag gaat over betrouwbaarheid of beperkingen: benoem de relevante "
        "kanttekeningen expliciet en overschat de data niet."
    ),
    "explain_scenario": _SYSTEM_BASE + (
        " De context bevat de redeneerstappen en het resultaat van een al berekend "
        "scenario. Leg het eindoordeel en de stappen uit; herbereken niets."
    ),
}


def _default_llm_factory(model: str, streaming: bool = False):
    from app.services.llm import make_llm  # lazy: avoids langchain import at module load
    llm = make_llm(model, streaming=streaming)
    try:
        llm.temperature = 0  # brief §3: pin temperature 0 for the chatbot
    except Exception:
        pass
    return llm


def _format_context(retrieved: list[RetrievedPassage], max_chars: int = 600) -> str:
    bits = []
    for i, rp in enumerate(retrieved, 1):
        text = rp.passage.text_nl.strip()
        if len(text) > max_chars:
            text = text[:max_chars].rsplit(" ", 1)[0] + "…"
        bits.append(f"[{i}] {text} (Bron: {rp.passage.citation.title_nl})")
    return "\n".join(bits)


def _best_sentence(question: str, text: str, max_chars: int = 320) -> str:
    q = set(content_tokens(question))
    sentences = split_sentences_nl(text)
    if not sentences:
        return text[:max_chars]
    best, best_score = sentences[0], -1
    for s in sentences:
        score = len(q & set(content_tokens(s)))
        if score > best_score:
            best, best_score = s, score
    if len(best) > max_chars:
        best = best[:max_chars].rsplit(" ", 1)[0] + "…"
    return best


def _compose_llm(question: str, intent: str, retrieved: list[RetrievedPassage],
                 model: str, llm_factory: Optional[Callable]) -> str:
    factory = llm_factory or _default_llm_factory
    llm = factory(model)
    context = _format_context(retrieved)
    system = _SYSTEM.get(intent, _SYSTEM_BASE)
    user = (
        f"Vraag: {question}\n\n"
        f"Context (genummerde bronnen):\n{context}\n\n"
        f"Geef een kort, feitelijk antwoord in B1-Nederlands met bronverwijzingen [nummer]."
    )
    msg = llm.invoke([("system", system), ("user", user)])
    content = getattr(msg, "content", None)
    content = (content if isinstance(content, str) else str(msg)).strip()
    if not content:
        raise ValueError("empty LLM response")
    return content


def _compose_extractive(question: str, intent: str, retrieved: list[RetrievedPassage]) -> str:
    if not retrieved:
        return (
            "Ik heb hier niet genoeg informatie voor in de beschikbare documentatie. "
            "Kun je je vraag iets specifieker maken?"
        )
    top = retrieved[:4]
    intro = _INTRO.get(intent, _INTRO["knowledge"])
    lines = [f"- {_best_sentence(question, rp.passage.text_nl)} [{i}]" for i, rp in enumerate(top, 1)]
    sources = "\n".join(
        f"[{i}] {rp.passage.citation.title_nl} — {rp.passage.citation.url}"
        for i, rp in enumerate(top, 1)
    )
    return f"{intro}\n" + "\n".join(lines) + f"\n\nBronnen:\n{sources}"


def compose_answer(question: str, intent: str, retrieved: list[RetrievedPassage], *,
                   model: str = "gemma4", llm_factory: Optional[Callable] = None,
                   use_llm: Optional[bool] = None) -> tuple[str, bool]:
    """Return (answer_nl, used_llm). Auto-selects GreenPT vs extractive, always
    falling back to extractive on any error."""
    want_llm = use_llm if use_llm is not None else (llm_factory is not None or bool(os.getenv("GREENPT_KEY")))
    if want_llm:
        try:
            return _compose_llm(question, intent, retrieved, model, llm_factory), True
        except Exception:
            pass  # GreenPT unavailable / errored -> deterministic fallback
    return _compose_extractive(question, intent, retrieved), False
