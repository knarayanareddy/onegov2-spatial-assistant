"""SqlAuditStore against a real SQL engine (SQLite via aiosqlite). The Postgres
adapter shares this code path; validated on SQLite since the sandbox can't run PG."""
import asyncio

import pytest

pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.models.audit import AuditLog  # noqa: E402
from app.services.audit import AuditEntry  # noqa: E402
from app.services.audit_sql import SqlAuditStore  # noqa: E402


def test_sql_audit_record_and_filter(tmp_path):
    async def main():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'audit.db'}")
        async with engine.begin() as conn:
            await conn.run_sync(AuditLog.__table__.create)
        store = SqlAuditStore(engine)
        await store.record(AuditEntry(id="1", ts="2026-06-04T00:00:00", user_oid="planner7",
                                      user_name="Planner Zeven", auth_mode="jwt",
                                      action="scenario.run", target="abc", detail={"verdict": "STOP"}))
        await store.record(AuditEntry(id="2", ts="2026-06-04T00:01:00", user_oid="boss",
                                      user_name="Boss", auth_mode="jwt", action="faq.promote", target="f1"))
        all_e = await store.list_recent()
        assert len(all_e) == 2
        runs = await store.list_recent(action="scenario.run")
        assert len(runs) == 1 and runs[0].user_oid == "planner7" and runs[0].detail["verdict"] == "STOP"
        await engine.dispose()

    asyncio.run(main())
