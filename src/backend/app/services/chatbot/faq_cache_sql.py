"""Postgres-backed FAQ cache store (Phase 3).

Implements the same async interface as InMemoryFaqCache, against the shared
sessions Postgres via SQLModel. Enable at app startup, e.g.:

    from app.database import engine
    from app.services.chatbot.faq_cache import set_store
    from app.services.chatbot.faq_cache_sql import SqlFaqCache
    set_store(SqlFaqCache(engine))

Then run the Alembic migration (`alembic upgrade head`) to create the table.
NB: the sandbox cannot run Postgres, so this adapter is import/compile-verified
here; validate it against your database in your environment. The cache LOGIC is
covered by the in-memory store tests.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.faq_cache import FaqCache
from app.services.chatbot.faq_cache import (
    STATUS_PUBLISHED,
    STATUS_REJECTED,
    STATUS_SUGGESTED,
    FaqCacheEntry,
    is_grounded,
    make_cache_key,
    normalize_question,
)
from app.services.chatbot.pii import anonymize_pii


def _to_entry(row: FaqCache) -> FaqCacheEntry:
    return FaqCacheEntry(
        id=str(row.id),
        cache_key=row.cache_key,
        question_norm=row.question_norm,
        question_display=row.question_display,
        answer_nl=row.answer_nl,
        sources=json.loads(row.sources_json or "[]"),
        intent=row.intent,
        hits=row.hits,
        status=row.status,
        version_stamp=row.version_stamp,
        created_at=row.created_at.isoformat() if row.created_at else "",
        last_used_at=row.last_used_at.isoformat() if row.last_used_at else "",
    )


def _parse_id(entry_id: str) -> Optional[uuid.UUID]:
    try:
        return uuid.UUID(str(entry_id))
    except (ValueError, AttributeError, TypeError):
        return None


class SqlFaqCache:
    def __init__(self, engine) -> None:
        self._engine = engine

    async def record_suggestion(self, question: str, answer_nl: str, sources: list[dict],
                                intent: str, version_stamp: str) -> FaqCacheEntry:
        key = make_cache_key(question)
        now = datetime.now(timezone.utc)
        async with AsyncSession(self._engine) as s:
            row = (await s.exec(select(FaqCache).where(FaqCache.cache_key == key))).first()
            if row:
                row.hits += 1
                row.last_used_at = now
                row.version_stamp = version_stamp
                if row.status != STATUS_REJECTED:
                    row.answer_nl = answer_nl or row.answer_nl
                    if sources:
                        row.sources_json = json.dumps(sources)
            else:
                row = FaqCache(
                    cache_key=key,
                    question_norm=normalize_question(question),
                    question_display=anonymize_pii(question or "").strip(),
                    answer_nl=answer_nl,
                    sources_json=json.dumps(sources or []),
                    intent=intent,
                    hits=1,
                    status=STATUS_SUGGESTED,
                    version_stamp=version_stamp,
                    created_at=now,
                    last_used_at=now,
                )
                s.add(row)
            await s.commit()
            await s.refresh(row)
            return _to_entry(row)

    async def get(self, entry_id: str) -> Optional[FaqCacheEntry]:
        uid = _parse_id(entry_id)
        if uid is None:
            return None
        async with AsyncSession(self._engine) as s:
            row = await s.get(FaqCache, uid)
            return _to_entry(row) if row else None

    async def list_suggestions(self, limit: int = 50) -> list[FaqCacheEntry]:
        async with AsyncSession(self._engine) as s:
            rows = (await s.exec(
                select(FaqCache).where(FaqCache.status == STATUS_SUGGESTED)
                .order_by(FaqCache.hits.desc()).limit(limit)
            )).all()
            return [_to_entry(r) for r in rows]

    async def list_published(self, limit: int = 10,
                             current_stamp: Optional[str] = None) -> list[FaqCacheEntry]:
        async with AsyncSession(self._engine) as s:
            q = select(FaqCache).where(FaqCache.status == STATUS_PUBLISHED)
            if current_stamp is not None:
                q = q.where(FaqCache.version_stamp == current_stamp)  # drop stale
            rows = (await s.exec(q.order_by(FaqCache.hits.desc()).limit(limit))).all()
            return [_to_entry(r) for r in rows]

    async def promote(self, entry_id: str) -> tuple[bool, str]:
        uid = _parse_id(entry_id)
        if uid is None:
            return False, "not_found"
        async with AsyncSession(self._engine) as s:
            row = await s.get(FaqCache, uid)
            if not row:
                return False, "not_found"
            if row.status == STATUS_REJECTED:
                return False, "rejected"
            if not is_grounded(_to_entry(row)):
                return False, "not_grounded"
            row.status = STATUS_PUBLISHED
            await s.commit()
            return True, "ok"

    async def reject(self, entry_id: str) -> tuple[bool, str]:
        uid = _parse_id(entry_id)
        if uid is None:
            return False, "not_found"
        async with AsyncSession(self._engine) as s:
            row = await s.get(FaqCache, uid)
            if not row:
                return False, "not_found"
            row.status = STATUS_REJECTED
            await s.commit()
            return True, "ok"

    async def all(self) -> list[FaqCacheEntry]:
        async with AsyncSession(self._engine) as s:
            return [_to_entry(r) for r in (await s.exec(select(FaqCache))).all()]
