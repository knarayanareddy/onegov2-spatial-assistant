"""SqlFaqCache against a real SQL engine (SQLite via aiosqlite).

The Postgres adapter shares this exact code path; the sandbox can't run Postgres,
so we exercise it on SQLite (the models avoid Postgres-only types). Skipped if
aiosqlite isn't installed.
"""
import asyncio

import pytest

pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.models.faq_cache import FaqCache  # noqa: E402
from app.services.chatbot import faq_cache as fc  # noqa: E402
from app.services.chatbot.faq_cache_sql import SqlFaqCache  # noqa: E402


def _engine(tmp_path):
    return create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'faq.db'}")


async def _setup(engine):
    async with engine.begin() as conn:
        await conn.run_sync(FaqCache.__table__.create)


def test_sql_adapter_full_lifecycle(tmp_path):
    src = [{"title_nl": "Doc", "url": "https://example.org"}]
    stamp = fc.current_version_stamp()

    async def main():
        engine = _engine(tmp_path)
        await _setup(engine)
        store = SqlFaqCache(engine)

        a = await store.record_suggestion("Welke databronnen?", "Antwoord [1].", src, "knowledge", stamp)
        b = await store.record_suggestion("databronnen welke", "Antwoord [1].", src, "knowledge", stamp)
        assert a.id == b.id and b.hits == 2                      # dedup + hits

        assert len(await store.list_suggestions()) == 1
        ok, why = await store.promote(a.id)
        assert ok and why == "ok"
        assert len(await store.list_published(10, stamp)) == 1   # matching stamp
        assert len(await store.list_published(10, "STALE")) == 0  # stale filtered

        assert (await store.reject(a.id))[0] is True
        assert (await store.promote(a.id)) == (False, "rejected")  # can't resurrect
        assert await store.get("not-a-uuid") is None               # bad id guard
        await engine.dispose()

    asyncio.run(main())
