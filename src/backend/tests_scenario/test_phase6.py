"""Phase 6 — auth + audit trail (accountability) and the uncertainty band.

JWT is verified with a MINTED token (PyJWT); no live IdP needed. Auth settings are
saved/restored per test so the dev default is never leaked between tests."""
import asyncio

import jwt as pyjwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import auth
from app.config import settings
from app.routers import chatbot, scenario
from app.services import audit
from app.services.helpers.tables import DATA_DIR
from app.services.scenario.pdf import build_citation
from app.services.scenario.uncertainty import run_uncertainty

DATA = str(DATA_DIR)
_KEYS = ["AUTH_MODE", "AUTH_REQUIRED", "AUTH_JWT_SECRET", "AUTH_JWT_ALGORITHM", "AUTH_JWT_AUDIENCE"]


@pytest.fixture(autouse=True)
def _reset():
    audit.set_store(audit.InMemoryAuditStore())
    saved = {k: getattr(settings, k) for k in _KEYS}
    yield
    for k, v in saved.items():
        setattr(settings, k, v)


def _mint(secret: str, **claims) -> str:
    return pyjwt.encode(claims, secret, algorithm="HS256")


_app_s = FastAPI(); _app_s.include_router(scenario.router); _cs = TestClient(_app_s)
_app_c = FastAPI(); _app_c.include_router(chatbot.router); _cc = TestClient(_app_c)


# --------------------------------------------------------------- auth
def test_jwt_maps_claims_to_user_and_roles():
    settings.AUTH_MODE = "jwt"; settings.AUTH_JWT_SECRET = "testsecret"
    u = auth._from_jwt(_mint("testsecret", sub="u123", name="Anna Beheer",
                             roles=["admin", "planner"], email="a@pzh.nl"))
    assert u.oid == "u123" and u.name == "Anna Beheer" and "admin" in u.roles and u.auth_mode == "jwt"


def test_dev_mode_audit_open():
    settings.AUTH_MODE = "dev"
    assert _cs.get("/api/audit").status_code == 200


def test_auth_required_rejects_missing_and_invalid_token():
    settings.AUTH_MODE = "jwt"; settings.AUTH_JWT_SECRET = "s"; settings.AUTH_REQUIRED = True
    assert _cs.get("/api/audit").status_code == 401                                  # missing
    assert _cs.get("/api/audit", headers={"Authorization": "Bearer not.a.jwt"}).status_code == 401  # invalid
    tok = _mint("s", sub="u1", name="U", roles=[])
    assert _cs.get("/api/audit", headers={"Authorization": f"Bearer {tok}"}).status_code == 200


def test_moderation_requires_admin_role():
    settings.AUTH_MODE = "jwt"; settings.AUTH_JWT_SECRET = "s"; settings.AUTH_REQUIRED = True
    nonadmin = _mint("s", sub="p", name="Planner", roles=["planner"])
    assert _cc.post("/api/chatbot/faqs/suggested/x/promote",
                    headers={"Authorization": f"Bearer {nonadmin}"}).status_code == 403
    admin = _mint("s", sub="boss", name="Boss", roles=["admin"])
    # admin clears the role gate; the (nonexistent) entry then yields 404
    assert _cc.post("/api/chatbot/faqs/suggested/x/promote",
                    headers={"Authorization": f"Bearer {admin}"}).status_code == 404


# --------------------------------------------------------------- audit trail
def test_scenario_run_is_audited_with_the_user():
    settings.AUTH_MODE = "jwt"; settings.AUTH_JWT_SECRET = "s"
    tok = _mint("s", sub="planner7", name="Planner Zeven", roles=["planner"])
    hdr = {"Authorization": f"Bearer {tok}"}
    r = _cs.post("/api/scenario/run", json={"question": "Verzilting op de Hollandse IJssel onder KNMI Hd in 2040"}, headers=hdr)
    assert r.status_code == 200
    entries = _cs.get("/api/audit", headers=hdr).json()["entries"]
    assert any(e["action"] == "scenario.run" and e["user_oid"] == "planner7" for e in entries)


def test_audit_inmemory_record_and_list():
    store = audit.InMemoryAuditStore(); audit.set_store(store)
    user = auth.CurrentUser(oid="x", name="X", roles=[], auth_mode="dev")
    asyncio.run(audit.record_audit(user, "test.action", "tgt", {"k": 1}, "hash1"))
    entries = asyncio.run(store.list_recent())
    assert entries and entries[0].action == "test.action" and entries[0].user_oid == "x"


# --------------------------------------------------------------- citation identity
def test_citation_includes_uitgevoerd_door():
    card = {"created_at": "2026-06-04T10:00:00", "scenario_id": "abcd1234ef", "scenario_hash": "h",
            "stable_url": "/x", "scenario_type": "intake_failure", "params": {"time_horizon": 2040},
            "run_by": {"oid": "planner7", "name": "Planner Zeven"}}
    cit = build_citation(card)
    assert cit["uitgevoerd_door"] == "Planner Zeven" and "Uitgevoerd door" in cit["metadata_block"]


# --------------------------------------------------------------- uncertainty band
def test_uncertainty_sweep_on_real_data():
    band = asyncio.run(run_uncertainty("Verzilting op de Hollandse IJssel in 2040", DATA))
    assert band["n_total"] == 5
    assert band["n_stop"] + band["n_caution"] + band["n_go"] == 5
    assert band["score_min"] <= band["score_max"]
    assert band["worst_case"] in {"GO", "CAUTION", "STOP"}
    assert isinstance(band["robust"], bool) and band["headline_nl"]


def test_uncertainty_endpoint():
    r = _cs.post("/api/scenario/uncertainty", json={"question": "Verzilting op de Hollandse IJssel in 2040"})
    assert r.status_code == 200 and r.json()["n_total"] == 5
    assert _cs.post("/api/scenario/uncertainty", json={"question": "  "}).status_code == 422
