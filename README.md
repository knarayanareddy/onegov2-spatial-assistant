# OneGov #2 — Drinkwaterzekerheid · Ruimtelijke Assistent + Scenario-engine + GreenPT Kennis-chat

A Dutch-language decision-support tool for **drinking-water security in Zuid-Holland (2040)**.
Built on the GovTech NL OneGov #2 starter and extended from a *descriptive* spatial assistant into a
full **exploratory what-if scenario engine** and a **grounded GreenPT knowledge chatbot** — with
accountability, uncertainty, and an honest validation story.

> *"Hoe zeker is de drinkwatervoorziening van Zuid-Holland in 2040, en welke combinatie van
> klimaatdruk, regelgeving en bevolkingsgroei vormt het grootste risico of biedt juist kansen voor
> een robuustere watervoorziening?"*

**Stack:** Vue 3 · MapLibre + Deck.gl (H3) · FastAPI + SSE · LangGraph · DuckDB-on-Parquet (H3 res 9)
· GreenPT (OpenAI-compatible) · PostgreSQL (SQLModel + Alembic) · MLflow · Python ≥ 3.12
· **132 backend tests passing** · Apache-2.0.

📐 **Full rebuild-from-scratch spec:** [`docs/onegov2_design_v4_current_build.md`](docs/onegov2_design_v4_current_build.md)

---

## What it does — three query surfaces

| Surface | What you do | What you get |
|---|---|---|
| **🗺️ Ruimtelijke Assistent** (descriptive) | Ask in plain Dutch ("hoeveel X in Y?") | NL→SQL over real H3 data → interactive map + explanation, an **Insight** reasoning trail, and **sourced Bronnen** |
| **🔮 Scenario-engine** | A what-if ("verzilting op de Hollandse IJssel onder KNMI Hd in 2040") or a weighted **recipe** | An H3 **DrinkwaterDruk** verdict (🟢 GO / 🟡 CAUTION / 🔴 STOP), map, reasoning, "make it feasible" options, official policy, a citeable **PDF advies**, a stable shareable URL |
| **💧 Kennis-chat** (GreenPT) | Ask about the data/method, or "explain this scenario" | Grounded **B1-Dutch** answers **with citations**, curated FAQs, and a data-limits–aware honest stance |

All three are **read-only or whitelist-validated** — the LLM never writes or runs code/SQL.

---

## Highlights

- **Verdict-first, plain Dutch** GO/CAUTION/STOP with a permanent map title and human-scale analogies (VEWIN-sourced).
- **Sourced & reproducible**: every assumption has an http(s) source (CI-gated); a `scenario_hash` + dataset-version stamp make the same inputs give the same verdict; a **stable URL** + **PDF citation** (incl. *Uitgevoerd door* + *Aannameversie*).
- **"Make this feasible"**: interventions re-scored on real data and ranked by risk reduction, each with a source.
- **Cumulative / "al vergund" overlay**: stack multiple projects + committed demand and see the *stapelingseffect* single-project checks miss.
- **Uncertainty band**: sweep the five KNMI'23 scenarios → "STOP in N/5", robust vs knife-edge.
- **Knowledge chatbot** that surfaces the **honest data caveats** (saturated `ZOUT_CONC`, CBS density proxy, empty operational tables) instead of overstating them.
- **Accountability**: real auth (JWT/OIDC-header) + an **audit trail** (who ran/changed what) + **assumption-library versioning** + a **calibration** harness with an explicit validation status.
- **Live integrations, env-gated**: RWS Waterinfo chloride (with a dated fallback, never silent), MLflow tracing, Postgres-backed FAQ cache + audit.

---

## Quick start

### Option A — Docker (the base app, fastest)
```bash
cp src/backend/.env.example src/backend/.env     # set GREENPT_KEY (offered to OneGov #2 teams; docs.greenpt.ai)
cp src/frontend/.env.example src/frontend/.env
docker compose up --build
```
Frontend → http://localhost:5173 · Backend → http://localhost:8001 · MLflow → http://localhost:5001.

### Option B — Local backend + the full test suite (Python ≥ 3.12)
```bash
cd src/backend
python3.12 -m venv .venv && source .venv/bin/activate      # or: uv venv
pip install -e . --group dev                                # or: uv sync
PYTHONPATH=. python -m pytest tests_scenario tests_chatbot -q   # -> 132 passed
PYTHONPATH=. python scripts/check_assumption_sources.py        # -> source gate PASSED
PYTHONPATH=. uvicorn app.main:app --reload --port 8001
```
Frontend:
```bash
cd src/frontend && npm install && npm run dev      # may need the @pzh-temporary package registry
```

> **Data (~70 MB).** The real H3 parquet lives in `src/backend/data/` + `src/backend/extra_data/`
> (it ships with this repo / the base fork). Everything runs offline against it — no key required for
> the deterministic paths.

---

## Architecture (in brief)

Vue 3 SPA → FastAPI (SSE) → LangGraph services → DuckDB-on-Parquet (read) + an in-process
`ScenarioStore` (DuckDB) for scenario cache/stable-URLs + Postgres (sessions, FAQ cache, audit) +
MLflow tracing. GreenPT is reached through `app/services/llm.make_llm` (temperature 0 for the bot).
Full diagrams, the score formula, and per-module detail are in
[`docs/onegov2_design_v4_current_build.md`](docs/onegov2_design_v4_current_build.md) (§2, §6, §7).

The **DrinkwaterDruk** score (per H3 cell, 0–100):
```
score = 100 · min(1, 0.40·salinity·dryness + 0.20·flood + 0.10·protection + 0.30·demand)
verdict: GO <33 · CAUTION 33–66 · STOP ≥66   |   area STOP if ≥20% cells STOP
```
(weights/thresholds are sourced, versioned assumptions; KNMI dryness 1.0→1.8 for B→Hd.)

---

## Repository layout (highlights)
```
CHALLENGE.md  ·  README.md  ·  SETUP.md  ·  docker-compose.yml  ·  LICENSE
docs/         onegov2_design_v4_current_build.md   <- full spec
              onegov2_design_v3_repo_aligned.md, CALIBRATION.md, example-scenarios.md, data-inventory.md
              COVERAGE_REPORT_chatbot_phase{1..4,6,7}.md
initdoc/      stakeholdercritique.md (v1), stakeholdercritique_v2.{md,html}, remediation_phase5.{md,html}
CHANGES_chatbot.md                                  <- phase-by-phase change log
src/backend/app/
  routers/    chat, query, dictionary, sessions, feedback, health, scenario, chatbot
  services/
    workflow.py + nodes/   descriptive LangGraph (intent→…→describe→cite_sources)
    data_sources.py        dataset→publisher/URL registry (citations + kennisbasis)
    audit.py / audit_sql.py
    scenario/   real_scoring, workflow, extraction, area, chloride, interventions, human_scale,
                official_positions, citizen, pdf, scenario_store, cumulative, waterinfo, tracing,
                uncertainty, assumptions, calibration, models, scenario_hash
    chatbot/    corpus, retrieval, intents, answer, faq, faq_cache(+_sql), recipe, scenario_run,
                scenario_context, text, models
  auth.py · config.py · database.py · models/(session,feedback,faq_cache,audit) · alembic/
  tests_scenario/  tests_chatbot/   (132 tests)
src/frontend/src/components/  chat/ · map/ · scenario/ · chatbot/ · kennisbasis/ · info/ · layout/
```

---

## API quick reference
**Descriptive/base:** `POST /api/chat` · `POST /api/query` · `GET /api/dictionary` · `GET /api/health`
**Scenario:** `POST /api/scenario/run` · `GET /api/scenario` · `GET /api/scenario/{id}` ·
`/{id}/citation` · `/{id}/pdf` · `/{id}/verify` · `POST /api/scenario/cumulative` ·
`POST /api/scenario/uncertainty` · `GET /api/scenario/calibration` · `GET /api/scenario/waterinfo/{intake}` ·
`GET /api/assumptions` · `GET /api/audit` (auth)
**Chatbot:** `POST /api/chatbot/ask` · `GET /api/chatbot/faqs[/{id}]` · `GET /api/chatbot/faqs/suggested` ·
`POST /api/chatbot/faqs/suggested/{id}/promote|reject` (admin) · `GET|POST /api/chatbot/recipe/schema|run` ·
`GET /api/kennisbasis`

Full request/response + SSE-event catalogue: design doc §11–§12.

---

## Configuration (all default-safe; secrets in `src/backend/.env`)
| Key | Default | Purpose |
|---|---|---|
| `GREENPT_KEY` / `OPENAI_MODEL` | "" / gemma4 | live GreenPT (else deterministic fallbacks) |
| `AUTH_MODE` (+ `AUTH_JWT_*` / `AUTH_HEADER_*` / `AUTH_REQUIRED`) | dev | `jwt`/`header` for real SSO + roles |
| `FAQ_CACHE_BACKEND` / `AUDIT_BACKEND` (+ `DATABASE_URL`) | memory | `postgres` to persist (run `alembic upgrade head`) |
| `WATERINFO_LIVE` | false | live RWS chloride (else dated fallback) |
| `MLFLOW_ENABLED` (+ `MLFLOW_*`) | false | scenario + descriptive tracing |

Full table: design doc §12.

---

## Trust & safety (the spine)
1. **Sourced** — every assumption carries an http(s) URL; `scripts/check_assumption_sources.py` gates the build.
2. **Deterministic** — engine: hash + cache + dataset-version; chatbot: temp-0 + deterministic retrieval + keyless fallback.
3. **No code/SQL synthesis** — the LLM only maps language to *validated* parameters; the engine runs it.
4. **PII anonymised** before any question enters the FAQ cache.
5. **Accountable** — auth identifies the user; the audit trail and citation record who did what.
6. **Honest** — caveats surfaced everywhere; calibration is reproducibility-consistency, explicitly *not* external validation.

---

## Phase summary
| Phase | Delivered |
|---|---|
| Base | Descriptive Ruimtelijke Assistent (NL→SQL→map) + data + MLflow |
| Scenario engine | Assumption-driven H3 DrinkwaterDruk verdict, comparison, citizen mode, PDF/citation |
| **1** | Grounded Dutch knowledge chatbot + curated FAQs |
| **2** | Scenario-from-chat (validation/whitelist gate) |
| **3** | FAQ caching + ranking + moderation (PII-safe) |
| **4** | Declarative recipe-builder + Postgres FAQ store |
| **5** | Cumulative/"al vergund", descriptive-flow citations, live Waterinfo, Kennisbasis, MLflow tracing, scenario library + verify |
| **6** | Real auth + audit trail + uncertainty band |
| **7** | Assumption-library versioning + calibration & validation status |

Phase-by-phase detail: [`CHANGES_chatbot.md`](CHANGES_chatbot.md) and the `docs/COVERAGE_REPORT_chatbot_phase*.md`.

---

## Documentation index
- **[CHALLENGE.md](CHALLENGE.md)** — the OneGov #2 brief.
- **[docs/onegov2_design_v4_current_build.md](docs/onegov2_design_v4_current_build.md)** — the complete current-build spec.
- **[SETUP.md](SETUP.md)** — install / run / env activation.
- **[docs/CALIBRATION.md](docs/CALIBRATION.md)** — calibration method + honest validation status.
- **[CHANGES_chatbot.md](CHANGES_chatbot.md)** — change log (Phases 1–7).
- **[initdoc/stakeholdercritique_v2.md](initdoc/stakeholdercritique_v2.md)** + **[remediation_phase5.md](initdoc/remediation_phase5.md)** — stakeholder review + remediation.
- **[docs/example-scenarios.md](docs/example-scenarios.md)** · **[docs/data-inventory.md](docs/data-inventory.md)**.

---

## Honest limitations & future work
- Salinity is a saturated single class (a *mask*); CBS is a relative density proxy; `productieketen`/`toestandsbeoordeling` ship empty.
- Calibration is reproducibility-consistency, **not** external validation (pluggable `external-study` slot).
- **Not yet built:** (C) data-refresh governance/SLA, (D) chat-session PII/retention, external validation cases, a WCAG conformance statement.
- Live SSO, Postgres cache/audit, MLflow, and Waterinfo are env-activated; the frontend builds in your environment.

---

## House style · Submission · License
- PZH house style via `@pzh-temporary/vue-component-library` + `@pzh-temporary/html-component-library`.
- **Submission:** Alkemio — [alkem.io/onegov-hackathon/challenges/ruimtelijkeassistentdrink](https://alkem.io/onegov-hackathon/challenges/ruimtelijkeassistentdrink) (repo link + working prototype + a ≥2-scenario/comparison demo + data/assumptions/limitations + a ≤10-slide pitch deck).
- **License:** code under [Apache-2.0](LICENSE); datasets retain their source licences (PZH, CBS, RIVM, RIONED, PDOK — see [docs/data-inventory.md](docs/data-inventory.md)).

> Prototypes here are exploratory *verkenningen*, not policy commitments or validated forecasts.
