"""GreenPT knowledge chatbot (Phase 1).

A grounded, Dutch (B1) knowledge chatbot + curated FAQ registry on top of the
OneGov #2 drinkwaterzekerheid scenario engine. Read-only: it answers questions
about the build, the datasets, and the methodology, and explains a produced
ScenarioCard. It NEVER writes or executes code/SQL and does NOT run scenarios
(that is Phase 2). Every answer carries citations back to the corpus.

Public entry point: ``app.services.chatbot.service.answer_question``.
"""
from app.services.chatbot.models import (
    ChatAnswer,
    Citation,
    FAQEntry,
    Passage,
    RetrievedPassage,
)
from app.services.chatbot.service import answer_question

__all__ = [
    "answer_question",
    "ChatAnswer",
    "Citation",
    "FAQEntry",
    "Passage",
    "RetrievedPassage",
]
