"""SQLModel table for the FAQ cache (Phase 3).

Lives in the shared sessions Postgres (the brief's target). JSON payloads are
stored as TEXT for portability (same rationale as scenario_store). The active
store is selected at runtime (see faq_cache.set_store / faq_cache_sql.SqlFaqCache);
the in-memory store is the default and the offline-tested one.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Text
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FaqCache(SQLModel, table=True):
    __tablename__ = "faq_cache"  # pyright: ignore[reportAssignmentType]

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    cache_key: str = Field(index=True, max_length=512)
    question_norm: str = Field(default="", max_length=2000)
    question_display: str = Field(default="", max_length=2000)
    answer_nl: str = Field(default="", sa_column=Column(Text))
    sources_json: str = Field(default="[]", sa_column=Column(Text))  # JSON text
    intent: str = Field(default="knowledge", max_length=32)
    hits: int = Field(default=1)
    status: str = Field(default="suggested", index=True, max_length=16)
    version_stamp: str = Field(default="", max_length=64)
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_type=DateTime(timezone=True),  # pyright: ignore[reportArgumentType]
    )
    last_used_at: datetime = Field(
        default_factory=_utcnow,
        sa_type=DateTime(timezone=True),  # pyright: ignore[reportArgumentType]
    )
