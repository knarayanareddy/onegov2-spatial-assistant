"""SQLModel table for the audit trail (Phase 6).

Lives in the shared sessions Postgres. Detail is stored as TEXT (JSON) for
portability, same rationale as faq_cache. Activated via AUDIT_BACKEND=postgres
(see audit_sql.SqlAuditStore); the in-memory store is the tested default.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Text
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"  # pyright: ignore[reportAssignmentType]

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ts: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))  # pyright: ignore[reportArgumentType]
    user_oid: str = Field(index=True, max_length=255)
    user_name: str = Field(default="", max_length=255)
    auth_mode: str = Field(default="dev", max_length=16)
    action: str = Field(index=True, max_length=64)
    target: str = Field(default="", max_length=255)
    detail_json: str = Field(default="{}", sa_column=Column(Text))
    params_hash: str = Field(default="", max_length=64)
