"""Postgres-backed audit store (Phase 6) — same async interface as InMemoryAuditStore.

Enable at startup (AUDIT_BACKEND=postgres): set_store(SqlAuditStore(engine)) and run
the Alembic migration. SQLite-verified in-sandbox; validate on your Postgres.
"""
from __future__ import annotations

import json
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.audit import AuditLog
from app.services.audit import AuditEntry


def _to_entry(row: AuditLog) -> AuditEntry:
    return AuditEntry(
        id=str(row.id), ts=row.ts.isoformat() if row.ts else "",
        user_oid=row.user_oid, user_name=row.user_name, auth_mode=row.auth_mode,
        action=row.action, target=row.target,
        detail=json.loads(row.detail_json or "{}"), params_hash=row.params_hash,
    )


class SqlAuditStore:
    def __init__(self, engine) -> None:
        self._engine = engine

    async def record(self, entry: AuditEntry) -> AuditEntry:
        async with AsyncSession(self._engine) as s:
            row = AuditLog(
                user_oid=entry.user_oid, user_name=entry.user_name, auth_mode=entry.auth_mode,
                action=entry.action, target=entry.target,
                detail_json=json.dumps(entry.detail or {}), params_hash=entry.params_hash,
            )
            s.add(row)
            await s.commit()
            await s.refresh(row)
            return _to_entry(row)

    async def list_recent(self, limit: int = 100,
                          action: Optional[str] = None,
                          user_oid: Optional[str] = None) -> list[AuditEntry]:
        async with AsyncSession(self._engine) as s:
            q = select(AuditLog)
            if action:
                q = q.where(AuditLog.action == action)
            if user_oid:
                q = q.where(AuditLog.user_oid == user_oid)
            rows = (await s.exec(q.order_by(AuditLog.ts.desc()).limit(limit))).all()
            return [_to_entry(r) for r in rows]
