"""Chatbot data model — plain dataclasses, no heavy imports.

Mirrors the scenario package's style (faithful field names, dataclasses) so the
chatbot stays importable offline (tests stay fast, no langchain/key needed).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Intent labels. Phase 1 is read-only:
#   knowledge            — general question about build/data/methodology
#   data_limits          — reliability / limitations / "what the system does NOT know"
#   explain_scenario     — explain an already-produced ScenarioCard (grounded, read-only)
#   scenario_run_request — user wants a NEW scenario computed -> route to the engine, do NOT execute
Intent = str


@dataclass(frozen=True)
class Citation:
    """A pointer back to a source. ``url`` is an http(s) link for assumptions /
    official positions / external sources, or a repo-relative doc path for the
    design doc and data dictionary, or a scenario stable URL for explain-mode."""

    source_id: str           # stable id, e.g. "design:part-c-caveats"
    title_nl: str            # human-readable Dutch title
    url: str                 # http(s) URL, repo doc path, or scenario stable URL
    locator: str = ""        # section / table.column / reasoning-step locator
    kind: str = "doc"        # doc | dictionary | assumption | official_position | dataset | scenario

    def as_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "title_nl": self.title_nl,
            "url": self.url,
            "locator": self.locator,
            "kind": self.kind,
        }


@dataclass
class Passage:
    """A retrievable unit of the knowledge corpus."""

    id: str
    text_nl: str
    citation: Citation
    tags: list[str] = field(default_factory=list)   # e.g. ["data_limits", "verzilting"]


@dataclass
class RetrievedPassage:
    passage: Passage
    score: float


@dataclass
class ChatAnswer:
    answer_nl: str
    intent: str
    confidence: float
    citations: list[Citation] = field(default_factory=list)          # sources actually cited
    sources_considered: list[Citation] = field(default_factory=list)  # everything retrieved
    followup_nl: Optional[str] = None       # clarifying question (no dead ends)
    used_llm: bool = False                  # True if GreenPT generated the prose
    scenario_id: Optional[str] = None       # set in explain-mode

    def as_dict(self) -> dict:
        return {
            "answer_nl": self.answer_nl,
            "intent": self.intent,
            "confidence": round(self.confidence, 3),
            "citations": [c.as_dict() for c in self.citations],
            "sources_considered": [c.as_dict() for c in self.sources_considered],
            "followup_nl": self.followup_nl,
            "used_llm": self.used_llm,
            "scenario_id": self.scenario_id,
        }


@dataclass
class FAQEntry:
    id: str
    question_nl: str
    answer_nl: str
    citations: list[Citation] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "question_nl": self.question_nl,
            "answer_nl": self.answer_nl,
            "citations": [c.as_dict() for c in self.citations],
            "tags": self.tags,
        }


def dedupe_citations(citations: list[Citation]) -> list[Citation]:
    """Stable de-duplication by (source_id, locator)."""
    seen: set[tuple[str, str]] = set()
    out: list[Citation] = []
    for c in citations:
        key = (c.source_id, c.locator)
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out
