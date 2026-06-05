"""Phase 5: Kennisbasis inventory endpoint + descriptive-flow source citations."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import chatbot
from app.services.nodes.cite_sources import compute_sources

_app = FastAPI()
_app.include_router(chatbot.router)
_client = TestClient(_app)


def test_kennisbasis_inventory_has_sources_and_freshness():
    r = _client.get("/api/kennisbasis")
    assert r.status_code == 200
    themes = r.json()["themes"]
    assert themes, "no themes in kennisbasis"
    for t in themes:
        assert t["publisher"] and t["url"].startswith(("http", "https"))
        assert "tables" in t
    # at least one table carries a column count
    assert any(tbl.get("columns", 0) > 0 for t in themes for tbl in t["tables"])


def test_descriptive_citations_node_maps_sql_to_sources():
    state = {"sql_query": "SELECT * FROM verzilting v JOIN drinkwaterbedrijven d USING (h3_id)",
             "dictionary": None}
    sources = compute_sources(state)
    themes = {s["theme"] for s in sources}
    assert "gebiedsviewer" in themes and "drinkwaterzekerheid" in themes
    assert all(s["url"].startswith("http") for s in sources)


def test_descriptive_citations_empty_for_no_sql():
    assert compute_sources({"sql_query": "", "dictionary": None}) == []
