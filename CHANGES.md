# Scenario-engine wiring — change set

Apply on top of `govtechnl/onegov2-spatial-assistant`. All paths are repo-relative.

## New files
- `src/backend/app/services/scenario/` — scenario package (corrected fix-pack calculators +
  `models.py`, `extraction.py` (deterministic mock GreenPT), `fixture.py` (synthetic DuckDB),
  `workflow.py` (LangGraph), `scenario_store.py`).
- `src/backend/app/routers/scenario.py` — `POST /api/scenario/run` (SSE) + `GET /api/scenario/{id}`.
- `src/backend/scripts/check_assumption_sources.py` — CI gate (blocks empty `source_url`).
- `src/backend/tests_scenario/` — golden-path A & B + SSE endpoint tests (5, all passing).
- `.github/workflows/ci.yml` — runs the gate + scenario tests on push.
- `docs/COVERAGE_REPORT.md` — design-doc ↔ build coverage report.

## Modified file
- `src/backend/app/main.py` — **2 lines only**:
  1. add `scenario,` to the `from app.routers import (...)` tuple;
  2. add `app.include_router(scenario.router)` after `app.include_router(query.router)`.

  If you prefer not to overwrite your `main.py`, just make those two edits by hand.

## Run
```bash
cd src/backend
pip install langgraph duckdb fastapi sse-starlette httpx pytest fpdf2 pydantic
PYTHONPATH=. python scripts/check_assumption_sources.py
PYTHONPATH=. python -m pytest tests_scenario -q       # 5 passed
```

## v3 update — runs on REAL data now
The scenario branch was re-based on the **assumption-driven H3 model over the shipped Parquet**
(`scenario/real_scoring.py`); the synthetic fixture is no longer on the path (kept only as a dormant
module). New capabilities:
- `workflow.run_scenario()` scores real H3 layers (`verzilting × overstroming × zes_uur`).
- `workflow.run_comparison()` + `POST /api/scenario/run {"compare": true}` → with/without-shock
  comparison with a `ScenarioDelta` (the brief's Should criterion).
- "Make it feasible" interventions are ranked by re-scoring on real data.
- Verified: KNMI B → CAUTION (52.2); KNMI Hd shock → STOP (91.1). 10 tests pass + source gate.

See `docs/onegov2_design_v3_repo_aligned.md` (Part D model, Part H runnable reference). The original
`docs/COVERAGE_REPORT.md` documents the v2→build gap that motivated v3.

## v3.1 — CBS demand + area-of-interest selection
- **CBS demand signal**: `real_scoring.py` now composes a 4th theme — CBS population — into the score
  (demand = population × demand_per_person × (1+growth), with an `added_homes` lever for brief scenario
  3). CBS `h3_index` is a leading-zero 16-char id the repo's `tables.py` only lowercases (0 overlap, a
  latent starter gap); the engine canonicalizes it → 2,145 cells recovered. `params_to_assumptions`
  maps `growth_preset`→growth and housing `development_units`→`added_homes`.
- **Area-of-interest** (`area.py` `select_h3_area`): drop-pin → PDOK geocode + python-`h3` `grid_disk`
  (offline fallback coords); intake → `zes_uur_zones_drinkwater` cells. Wired into `score_node`, so
  drop-pin (Pijnacker, 67 cells) and intake (IJssel, 110 cells) score different areas.
- New dep: `h3>=4.0.0` (added to `.github/workflows/ci.yml`). Tests: 13→**16** passing.

## v3.2 — scenario 3 sharpened + GreenPT extraction + Deck.gl frontend
- **Scenario 3 on the built-up area**: `real_scoring.score_h3_area(base="populated")` scores the
  CBS-populated universe (where demand lives), not the salinity region. Demand now dominates there
  (demand_avg 0.44 vs 0.06 over salinity); the growth/added-homes axis is monotonic
  (baseline→+80k→compound = 754→825→1131 STOP cells). Housing questions auto-route to this universe.
- **GreenPT extraction** (`extraction.py`): `extract_scenario_params()` uses the repo's
  `make_llm` (GreenPT, lazy-imported) when `GREENPT_KEY` is set, and **always falls back** to the
  deterministic rule extractor otherwise / on any error. Tested with an injected fake LLM.
- **Frontend** (not built in CI): `composables/useScenarioSSE.ts` (parses the scenario SSE) and
  `components/scenario/ScenarioPanel.vue` (Deck.gl `H3HexagonLayer` + MapLibre + assumption sliders
  + comparison). Single-run endpoint now accepts an `assumptions` override for the sliders.
- A standalone, viewable Deck.gl demo (KNMI B→CAUTION vs Hd→STOP over the verzilting area) was
  generated from real engine output. Tests: 16→**22** passing.

## v3.3 — frontend wired + citizen mode + PDF/citation
- **Frontend wired into the app**: `App.vue` gets a "🔮 Scenario-engine" full-view toggle rendering
  `components/scenario/ScenarioPanel.vue` (deck.gl v9 `MapboxOverlay` + `H3HexagonLayer` over MapLibre,
  verdict, assumption sliders, comparison, Insight, official position). All deck.gl/h3/maplibre deps
  already in `package.json`. NB: `npm install`/`vite build` must run in your environment — the sandbox
  OOM-kills the install (deck.gl + duckdb-wasm), and `@pzh-temporary/*` may need registry access.
- **GAP 10 citizen mode** (`citizen.py`): `detect_citizen_mode` + `format_citizen_response`
  (verdict-first, B1 Dutch, postcode + water company, no m³ jargon, disclaimer). The single-run
  endpoint emits a `citizen_response` SSE event for citizen questions/persona.
- **GAP 3 citation + PDF** (`pdf.py`): `build_citation` (APA + metadata) and Unicode-safe
  `render_scenario_pdf`; routes `GET /api/scenario/{id}/pdf` and `/citation`.
- Tests: 22→**27** passing; source gate green.
