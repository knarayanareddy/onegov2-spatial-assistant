"""Audit trail (Phase 6) — who did what, for Woo/accountability.

Every accountable action (running a scenario, a cumulative stack, a verify, a
recipe, or moderating a cached FAQ) writes an AuditEntry: timestamp, the user,
the action, the target, and a params hash. Behind a small async store interface
with an in-memory default (tested) and a Postgres adapter (audit_sql.SqlAuditStore).

Recording is best-effort: an audit hiccup must never break the user's request.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class AuditEntry:
    id: str
    ts: str
    user_oid: str
    user_name: str
    auth_mode: str
    action: str                 # e.g. "scenario.run", "faq.promote"
    target: str = ""            # scenario id / faq id / intake / ...
    detail: dict = field(default_factory=dict)
    params_hash: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InMemoryAuditStore:
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    async def record(self, entry: AuditEntry) -> AuditEntry:
        self._entries.append(entry)
        return entry

    async def list_recent(self, limit: int = 100,
                          action: Optional[str] = None,
                          user_oid: Optional[str] = None) -> list[AuditEntry]:
        items = list(reversed(self._entries))
        if action:
            items = [e for e in items if e.action == action]
        if user_oid:
            items = [e for e in items if e.user_oid == user_oid]
        return items[:limit]


_default_store: object = InMemoryAuditStore()


def get_store():
    return _default_store


def set_store(store) -> None:
    global _default_store
    _default_store = store


async def record_audit(user, action: str, target: str = "",
                       detail: Optional[dict] = None, params_hash: str = "") -> Optional[AuditEntry]:
    """Best-effort audit write. `user` is a CurrentUser (or None). Never raises."""
    try:
        entry = AuditEntry(
            id=str(uuid.uuid4()), ts=_now(),
            user_oid=getattr(user, "oid", "unknown"),
            user_name=getattr(user, "name", "unknown"),
            auth_mode=getattr(user, "auth_mode", "dev"),
            action=action, target=target, detail=detail or {}, params_hash=params_hash,
        )
        return await get_store().record(entry)
    except Exception:
        return None
