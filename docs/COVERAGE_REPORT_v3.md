# OneGov #2 — v3 Build Coverage Re-grade

**Date:** 2026-06-04 · **Graded against:** `docs/onegov2_design_v3_repo_aligned.md` (repo-aligned v3) ·
**Build:** the wired scenario engine in `src/backend/app/services/scenario/` + `routers/scenario.py` +
the frontend drop-ins. Companion sortable matrix: the "v3 Build Coverage Re-grade" table.
(The earlier `COVERAGE_REPORT.md` graded v2-against-the-starter; this supersedes it for v3.)

Statuses verified against the actual build before scoring: **27 tests pass**, source_url gate green,
4 endpoints live (`/run`, `/{id}`, `/{id}/citation`, `/{id}/pdf`), 10 SSE event types, 18 modules.

## Headline

| Tally | Count |
|---|---|
| **Implemented (tested)** | **34 / 46** |
| Partial (caveat / not fully wired) | 5 |
| Deferred (not this build) | 6 |
| Blocked-by-data | 1 |

- **CHALLENGE.md Must:** ✅ **all met** (NL→scenario, ≥2 themes, explicit data/assumptions, open-source, existing flow intact).
- **CHALLENGE.md Should:** 2 of 3 Implemented; "navolgbaar redeneerproces" **Partial** (Insight reasoning steps done; MLflow scenario tracing deferred).
- **10 trust gaps:** **6 Implemented · 2 Partial · 2 Deferred.**
  - Implemented: GAP 3 (citation+PDF), 4 (human scale), 5 (make-it-feasible), 7 (per-intake/verzilting salinity), 8 (official position), 10 (citizen mode).
  - Partial: GAP 2 (hash+stable URL done; drift/verify deferred), GAP 9 (no live Waterinfo; uses verzilting class, labelled, never silent).
  - Deferred: GAP 1 (kennisbasis — reuse `/api/dictionary`), GAP 6 (cumulative load).

## What changed since the v2-era grade
Big movers — all now **Implemented (tested)** that were previously Deferred/Blocked:
- **GAP 7** chloride threshold: was **Blocked-by-data** (no per-intake `cl_threshold`) → re-grounded on real `verzilting.ZOUT_CONC`.
- **GAP 3** citation + PDF, **GAP 10** citizen mode, **comparison** (with/without shock + `ScenarioDelta`), **area-of-interest selection** (drop-pin grid_disk vs intake zes-uur), **CBS demand** (built-up universe), and **GreenPT extraction with fallback** — all newly Implemented.
- The whole engine now runs **on the real shipped data** (was synthetic-fixture only at the first wiring).

## Honest caveats (so nothing is overstated)
- **verzilting.ZOUT_CONC** ships as a single class (`>200mg/l`) → salinity is a *mask*, and the KNMI dryness knob is modelled as amplifying its contribution (GAP 7 / GAP 9 carry this caveat).
- **CBS `_consumption`** is a downsampled relative density proxy (~46k total), not headcounts → housing is a *relative* households increase; scenario-3 shift over the built-up area is monotonic but modest at realistic numbers.
- **Frontend** (`ScenarioPanel.vue` + `App.vue` toggle) is **Partial**: written and wired, but `vite build` must run in your environment (the sandbox OOM-kills `npm install`); the published Deck.gl demo is the working visual proof.
- `productieketen` / KRW `toestandsbeoordeling` ship **empty** → Blocked-by-data; not depended on.

## Prioritized remaining (to push the last Partial/Deferred items)
1. **MLflow scenario tracing** — closes the Should "navolgbaar" gap fully (repo already runs MLflow).
2. **GAP 1 kennisbasis** — thin: surface `/api/dictionary` in the scenario UI.
3. **GAP 2 drift/verify** — dataset-version drift + a `/verify` re-run endpoint.
4. **GAP 6 cumulative load** — same-`voedingsgebied` active-scenario warning.
5. **Frontend build** in your environment (npm + `@pzh-temporary` registry) and a smoke test against the backend.
6. **Type 2 / Type 4** dedicated endpoints (compound already expressible via assumptions).

## Verdict
Against v3, the build is **substantially complete for a hackathon submission**: every Must criterion met, the Should criteria met except full MLflow tracing, 6/10 trust gaps fully implemented and 2 more partial, and the two golden paths + the with/without-shock comparison demonstrably run on the real data with 27 passing tests. The remaining work is additive (tracing, two trust gaps, the frontend build), not corrective.
