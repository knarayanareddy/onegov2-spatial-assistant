"""FAQ cache + ranking (Phase 3).

Turns confident, grounded chat answers into a growing FAQ:
  - capture: cache a confident, cited knowledge/data_limits answer as a
    *suggestion* (PII anonymised, version-stamped); repeats bump `hits`.
  - moderation: a suggestion is promoted to *published* only after a
    grounded-with-sources re-check (auth-gated endpoint). Nothing publishes silently.
  - ranking: published entries are served ranked by `hits`, after the curated
    Phase 1 FAQs.
  - invalidation: every entry carries a `version_stamp` = hash(git_commit +
    corpus signature). Stale-stamp entries are filtered from serving — the same
    drift idea as the scenario cache (scenario_store.detect_version_drift).

The store is behind a small async interface. The default is an in-memory store
(zero-infra, fully tested offline, and a graceful fallback when Postgres is not
configured). A SQLModel/Postgres adapter (faq_cache_sql.SqlFaqCache) implements
the same interface for the shared sessions DB — see CHANGES_chatbot.md.
"""
from __future__ import annotations

import hashlib
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.services.chatbot.pii import anonymize_pii
from app.services.chatbot.text import content_tokens

CACHE_MIN_CONFIDENCE = 0.6
CACHEABLE_INTENTS = frozenset({"knowledge", "data_limits"})
STATUS_SUGGESTED = "suggested"
STATUS_PUBLISHED = "published"
STATUS_REJECTED = "rejected"


# --------------------------------------------------------------------- entry
@dataclass
class FaqCacheEntry:
    id: str
    cache_key: str
    question_norm: str
    question_display: str       # anonymised original (shown in the queue / FAQ)
    answer_nl: str
    sources: list[dict] = field(default_factory=list)
    intent: str = "knowledge"
    hits: int = 1
    status: str = STATUS_SUGGESTED
    version_stamp: str = ""
    created_at: str = ""
    last_used_at: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------- helpers
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_question(question: str) -> str:
    """Lowercased, PII-stripped, whitespace-collapsed form (for display/debug)."""
    return " ".join(anonymize_pii(question or "").lower().split())


def make_cache_key(question: str) -> str:
    """Order-insensitive keyword signature so paraphrases collapse to one entry.
    PII is stripped first so it never enters the key."""
    toks = sorted(set(content_tokens(anonymize_pii(question or ""))))
    return "|".join(toks) if toks else normalize_question(question)


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def corpus_signature() -> str:
    """Short digest of the corpus contents — changes when docs/metadata change."""
    try:
        from app.services.chatbot.corpus import get_default_corpus
        corpus = get_default_corpus()
        ids = "".join(sorted(p.id for p in corpus))
        return hashlib.sha1(f"{len(corpus)}:{ids}".encode()).hexdigest()[:12]
    except Exception:
        return "nocorpus"


def current_version_stamp() -> str:
    """hash(git_commit + corpus signature) — the cache invalidation key."""
    return hashlib.sha1(f"{_git_commit()}:{corpus_signature()}".encode()).hexdigest()[:16]


def should_cache(intent: str, confidence: float, citations,
                 followup_nl: Optional[str] = None) -> bool:
    """Grounded-and-confident gate. Only confident, cited knowledge/data_limits
    answers are cacheable — never scenario runs or clarification turns."""
    return (
        intent in CACHEABLE_INTENTS
        and followup_nl is None
        and confidence >= CACHE_MIN_CONFIDENCE
        and bool(citations)
    )


def is_grounded(entry: FaqCacheEntry) -> bool:
    """Re-check used before promotion: an entry must have an answer and sources."""
    return bool((entry.answer_nl or "").strip()) and bool(entry.sources)


# --------------------------------------------------------------------- in-memory store
class InMemoryFaqCache:
    """Default store. Async methods so the interface matches the Postgres adapter."""

    def __init__(self) -> None:
        self._by_id: dict[str, FaqCacheEntry] = {}
        self._key_to_id: dict[str, str] = {}

    async def record_suggestion(self, question: str, answer_nl: str, sources: list[dict],
                                intent: str, version_stamp: str) -> FaqCacheEntry:
        key = make_cache_key(question)
        eid = self._key_to_id.get(key)
        if eid and eid in self._by_id:
            e = self._by_id[eid]
            e.hits += 1
            e.last_used_at = _now()
            e.version_stamp = version_stamp
            if e.status != STATUS_REJECTED:   # don't resurrect a rejected entry
                e.answer_nl = answer_nl or e.answer_nl
                e.sources = sources or e.sources
            return e
        entry = FaqCacheEntry(
            id=str(uuid.uuid4()), cache_key=key,
            question_norm=normalize_question(question),
            question_display=anonymize_pii(question or "").strip(),
            answer_nl=answer_nl, sources=list(sources or []), intent=intent,
            hits=1, status=STATUS_SUGGESTED, version_stamp=version_stamp,
            created_at=_now(), last_used_at=_now(),
        )
        self._by_id[entry.id] = entry
        self._key_to_id[key] = entry.id
        return entry

    async def get(self, entry_id: str) -> Optional[FaqCacheEntry]:
        return self._by_id.get(entry_id)

    async def list_suggestions(self, limit: int = 50) -> list[FaqCacheEntry]:
        items = [e for e in self._by_id.values() if e.status == STATUS_SUGGESTED]
        items.sort(key=lambda e: (-e.hits, e.created_at))
        return items[:limit]

    async def list_published(self, limit: int = 10,
                             current_stamp: Optional[str] = None) -> list[FaqCacheEntry]:
        items = [e for e in self._by_id.values() if e.status == STATUS_PUBLISHED]
        if current_stamp is not None:
            items = [e for e in items if e.version_stamp == current_stamp]  # drop stale
        items.sort(key=lambda e: (-e.hits, e.created_at))
        return items[:limit]

    async def promote(self, entry_id: str) -> tuple[bool, str]:
        e = self._by_id.get(entry_id)
        if not e:
            return False, "not_found"
        if e.status == STATUS_REJECTED:
            return False, "rejected"        # a rejected entry stays rejected
        if not is_grounded(e):
            return False, "not_grounded"   # grounded-with-sources re-check
        e.status = STATUS_PUBLISHED
        return True, "ok"

    async def reject(self, entry_id: str) -> tuple[bool, str]:
        e = self._by_id.get(entry_id)
        if not e:
            return False, "not_found"
        e.status = STATUS_REJECTED
        return True, "ok"

    async def all(self) -> list[FaqCacheEntry]:
        return list(self._by_id.values())


# --------------------------------------------------------------------- module store
_default_store: object = InMemoryFaqCache()


def get_store():
    return _default_store


def set_store(store) -> None:
    """Swap the active store (e.g. SqlFaqCache(engine) at app startup)."""
    global _default_store
    _default_store = store


# --------------------------------------------------------------------- service helpers
async def capture_answer(question: str, answer) -> Optional[FaqCacheEntry]:
    """Best-effort: cache a confident, grounded answer as a suggestion.
    `answer` is a ChatAnswer. Returns the entry, or None if not cacheable."""
    if not should_cache(answer.intent, answer.confidence, answer.citations, answer.followup_nl):
        return None
    sources = [c.as_dict() for c in answer.citations]
    return await get_store().record_suggestion(
        question, answer.answer_nl, sources, answer.intent, current_version_stamp())


async def published_as_faqs(limit: int = 10) -> list[dict]:
    """Published cache entries shaped like FAQ items, ranked by hits, non-stale."""
    entries = await get_store().list_published(limit, current_version_stamp())
    return [{
        "id": e.id,
        "question_nl": e.question_display,
        "answer_nl": e.answer_nl,
        "citations": e.sources,
        "tags": ["cached"],
        "hits": e.hits,
        "origin": "cached",
    } for e in entries]
