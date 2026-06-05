"""Phase 5 remediation pack: data-source citations, cumulative overlay, live
Waterinfo (mandatory + labelled fallback), MLflow tracing no-op, and the new
library / verify / cumulative / waterinfo endpoints. Runs on the real shipped data."""
import asyncio
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import scenario
from app.services import data_sources as ds
from app.services.helpers.tables import DATA_DIR
from app.services.scenario import waterinfo
from app.services.scenario.cumulative import execute_cumulative, validate_cumulative
from app.services.scenario.tracing import scenario_span

DATA = str(DATA_DIR)
_KNOWN = ["verzilting", "zes_uur_zones_drinkwater", "cbs_vierkantstatistieken_2022_consumption", "drinkwaterbedrijven"]


# ----------------------------------------------------------- data-source citations
def test_sql_sources_have_http_links():
    sql = "SELECT * FROM verzilting v LEFT JOIN cbs_vierkantstatistieken_2022_consumption c USING (h3_id)"
    srcs = ds.sources_for_sql(sql, _KNOWN)
    themes = {s["theme"] for s in srcs}
    assert "gebiedsviewer" in themes and "cbs" in themes
    assert all(s["url"].startswith("http") for s in srcs)
    assert any("verzilting" in s["tables"] for s in srcs)


def test_extract_tables_ignores_unrelated():
    assert ds.extract_tables_from_sql("SELECT 1", _KNOWN) == []


# ----------------------------------------------------------- cumulative
def test_cumulative_validation():
    assert validate_cumulative({"projects": [{"added_homes": 1}], "knmi_preset": "Z"}).reason == "bad_knmi"
    assert validate_cumulative({"projects": []}).reason == "no_projects"
    ok = validate_cumulative({"projects": [{"name": "DC", "datacenter_mw": 50}], "committed": [{"m3_day": 3500}]})
    assert ok.runnable and ok.projects[0]["homes_equiv"] > 0 and ok.committed[0]["homes_equiv"] > 0


def test_cumulative_run_on_real_data():
    plan = validate_cumulative({
        "knmi_preset": "Hd", "growth_preset": "hoog",
        "projects": [{"name": "Woningen", "development_units": 40000}, {"name": "DC", "datacenter_mw": 50}],
        "committed": [{"label": "Reeds vergund", "m3_day": 5000}],
    })
    res = asyncio.run(execute_cumulative(plan, DATA))
    assert res["combined"]["feasibility_class"] in {"GO", "CAUTION", "STOP"}
    assert all("alone_verdict" in p for p in res["projects"])
    assert res["total_homes_equiv"] >= res["projects_homes_equiv"]
    assert "stapeling" in res["narrative_nl"].lower() or "gestapeld" in res["narrative_nl"].lower()


# ----------------------------------------------------------- waterinfo
def test_waterinfo_fallback_is_dated_and_never_silent():
    out = waterinfo.get_chloride("IJssel")          # live off by default -> labelled fallback
    assert out["live"] is False and out["value_mg_l"] > 0
    assert "laatste bekende waarde" in out["warning_nl"]
    assert out["source_url"].startswith("http")


def test_waterinfo_live_path_with_injected_requester():
    out = waterinfo.get_chloride("Lek", requester=lambda st: {"value_mg_l": 175.0, "measured_at": "2026-06-01"})
    assert out["live"] is True and out["value_mg_l"] == 175.0 and out["exceeds_norm"] is True


def test_waterinfo_unknown_intake():
    assert waterinfo.is_intake_relevant("Spree") is False
    out = waterinfo.get_chloride("Spree")
    assert out["live"] is False and out["intake"] is None


# ----------------------------------------------------------- mlflow tracing
def test_tracing_is_noop_when_disabled():
    with scenario_span("scenario_run", verdict="STOP") as span:
        assert span is None     # MLFLOW_ENABLED defaults to False


# ----------------------------------------------------------- endpoints
_app = FastAPI()
_app.include_router(scenario.router)
_client = TestClient(_app)


def _parse_sse(text):
    events, ev = [], None
    for line in text.splitlines():
        if line.startswith("event:"):
            ev = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and ev is not None:
            events.append((ev, line.split(":", 1)[1].strip()))
    return events


def test_cumulative_endpoint():
    r = _client.post("/api/scenario/cumulative", json={
        "knmi_preset": "Hd", "projects": [{"name": "A", "development_units": 20000}]})
    assert r.status_code == 200 and r.json()["combined"]["feasibility_class"] in {"GO", "CAUTION", "STOP"}
    assert _client.post("/api/scenario/cumulative", json={"projects": []}).status_code == 422


def test_waterinfo_endpoint():
    assert _client.get("/api/scenario/waterinfo/ijssel").status_code == 200
    assert _client.get("/api/scenario/waterinfo/berlijn").status_code == 404


def test_run_then_library_and_verify():
    q = "Verzilting op de Hollandse IJssel onder KNMI Hd in 2040"
    r = _client.post("/api/scenario/run", json={"question": q})
    events = dict(_parse_sse(r.text))
    names = [n for n, _ in _parse_sse(r.text)]
    assert "waterinfo" in names                       # intake scenario emits chloride provenance
    sid = json.loads(events["scenario_card"])["scenario_id"]

    lib = _client.get("/api/scenario").json()["scenarios"]
    assert any(s["scenario_id"] == sid for s in lib)

    v = _client.get(f"/api/scenario/{sid}/verify").json()
    assert v["matches"] is True and v["dataset_drift"] == []
