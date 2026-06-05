"""CiteSourcesNode (Phase 5) — brings hyperlinked Bronnen to the descriptive flow.

The descriptive SQL assistant historically answered in prose with no provenance.
This append-only node maps the tables the generated SQL touched to their
publisher + source URL (via app.services.data_sources) and dispatches a
`sources_block` event, so the descriptive answer — like the knowledge chatbot —
now carries clickable sources. It never blocks the answer: any failure degrades
to no sources.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from app.models.state import ConversationState
from app.services import data_sources
from app.services.nodes.base import BaseNode


def _known_tables(dictionary) -> tuple[list[str], dict[str, str]]:
    """Table names + a table->theme index, from the loaded data dictionary when
    available, else the static source registry."""
    known: list[str] = []
    dynamic: dict[str, str] = {}
    themes = getattr(dictionary, "themes", None)
    if themes:
        for theme in themes:
            tname = getattr(theme, "name", "")
            for tbl in getattr(theme, "tables", []) or []:
                name = getattr(tbl, "name", None)
                if name:
                    known.append(name)
                    dynamic[name.lower()] = tname
    if not known:
        dynamic = data_sources.build_table_theme_index()
        known = list(dynamic.keys())
    return known, dynamic


def compute_sources(state: ConversationState) -> list[dict]:
    sql = state.get("sql_query") or ""
    known, dynamic = _known_tables(state.get("dictionary"))
    return data_sources.sources_for_sql(sql, known, dynamic)


class CiteSourcesNode(BaseNode):
    def __init__(self) -> None:
        super().__init__("cite_sources", auto_activate=False)

    async def run(self, state: ConversationState, config: RunnableConfig) -> dict:
        sources = compute_sources(state)
        if sources:
            try:
                await self.dispatch("sources_block", {"sources": sources}, config)
            except Exception:
                pass   # never block the answer on a telemetry/dispatch hiccup
        return {"sources": sources}

    def fallback(self) -> dict:
        return {"sources": []}
