# OneGov #2 — full build setup

This fork of `govtechnl/onegov2-spatial-assistant` carries the original base app
**and the shipped datasets**, plus the **scenario engine** and the **GreenPT chatbot
(Phases 1–7)** added on the `full-build` branch.

> The ~70 MB of H3 parquet data lives in `src/backend/data/` and `src/backend/extra_data/`
> — it came with the fork (it could not be pushed through the GitHub API, which is exactly
> why we forked the data-carrying base repo).

## What was added on top of the base
- **Scenario engine** — `src/backend/app/services/scenario/` + `app/routers/scenario.py` (assumption-driven H3 DrinkwaterDruk model, comparison, citizen mode, PDF/citation).
- **Chatbot Phase 1** — grounded Dutch knowledge chatbot + curated FAQs (`app/services/chatbot/`, `app/routers/chatbot.py`).
- **Phase 2** — scenario-from-chat with a validation/whitelist gate.
- **Phase 3** — FAQ caching + ranking + moderation (PII-anonymised).
- **Phase 4** — declarative recipe-builder + Postgres FAQ store.
- **Phase 5** — cumulative/"al vergund" overlay, descriptive-flow citations, live RWS Waterinfo, Kennisbasis, MLflow tracing, scenario library + verify.
- **Phase 6** — real auth (JWT/header) + audit trail + uncertainty band.
- **Phase 7** — assumption-library versioning + calibration & validation status.
- Docs: `CHANGES_chatbot.md`, `docs/COVERAGE_REPORT_chatbot_phase*.md`, `docs/CALIBRATION.md`, `initdoc/stakeholdercritique_v2.*`, `initdoc/remediation_phase5.*`.

## Backend — install & verify (Python ≥ 3.12)
```bash
git clone https://github.com/knarayanareddy/onegov2-spatial-assistant.git
cd onegov2-spatial-assistant
git checkout full-build            # until the PR is merged to main
cd src/backend
python3.12 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e . --group dev       # or:  uv sync
PYTHONPATH=. python -m pytest tests_scenario tests_chatbot -q   # -> 132 passed
PYTHONPATH=. python scripts/check_assumption_sources.py         # -> gate PASSED
PYTHONPATH=. uvicorn app.main:app --reload --port 8001
```

## Frontend
```bash
cd src/frontend
npm install        # may need your @pzh package-registry config
npm run dev        # or: npm run build
```

## Optional production config (all OFF by default — the build runs without it)
Put secrets in `src/backend/.env` (never commit them):
```bash
GREENPT_KEY=...                     # live GreenPT answers/extraction
AUTH_MODE=jwt                       # or "header" behind an OIDC proxy
AUTH_JWT_JWKS_URL=...               # your SSO (Keycloak/Azure AD); + AUTH_REQUIRED=true
FAQ_CACHE_BACKEND=postgres
AUDIT_BACKEND=postgres
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
WATERINFO_LIVE=true
MLFLOW_ENABLED=true
```
Then create the new tables:
```bash
cd src/backend && alembic upgrade head      # creates faq_cache + audit_log
```

## New endpoints
`/api/chatbot/ask` · `/api/chatbot/faqs` · `/api/kennisbasis` · `/api/scenario/run` ·
`/api/scenario/cumulative` · `/api/scenario/uncertainty` · `/api/scenario/calibration` ·
`/api/scenario/{id}/verify` · `/api/assumptions` · `/api/audit`
