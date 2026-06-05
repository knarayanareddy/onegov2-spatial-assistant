# OneGov #2 — Design Doc ↔ Build Coverage Report

**Date:** 2026-06-04 · **Base repo:** `govtechnl/onegov2-spatial-assistant` (hackathon starter) ·
**Compared against:** `onegov2_design_document_complete.md` v2.0 · **Reviewer:** independent wiring pass.

Legend: ✅ Implemented & tested · 🟡 Partial / simplified / stubbed · ⬜ Deferred (not this pass) ·
⛔ Blocked by data (real datasets can't support it) · 🔑 Needs a live key/API to run.

---

## 1. Executive summary

The scenario engine described in the design doc has been **wired into the real starter repo as a
working, tested vertical slice**: a unified `POST /api/scenario/run` SSE endpoint and a LangGraph
workflow that drives the corrected calculators end-to-end. **Both golden paths run and pass
automated tests** (datacenter drop-pin → STOP; IJssel 6-week intake failure → STOP with chloride
513.7 mg/L over the per-intake threshold of 200). A CI gate enforces the design doc's
"every source is a URL" rule.

But the headline finding is a **data-reality gap that the design doc does not acknowledge**, and it
caps how "end-to-end" anything can be:

> **The bundled datasets do not contain the operational data the engine is specified against.**
> There is no `leveringszones` table with `capaciteit_m3_dag` / `vraag_2023_m3_dag`, no
> `winlocaties` capacities, no per-intake `cl_threshold_mg_l`, no chloride time series, and no
> alternative-source table. Two tables the golden paths depend on —
> `drinkwater_productieketen` and `toestandsbeoordeling_oppervlaktewaterlichamen` (KRW) — are
> **present but empty (0 rows)**. The real data is **H3-cell thematic map layers** (every table
> keyed by `h3_id`, mostly categorical `VARCHAR` columns), not capacity/demand/threshold
> utility data.

So the engine's **logic is implemented and proven correct**, but it currently runs on a **synthetic
fixture shaped the way the design doc assumes**, not on the provided data. Making it run on real
data requires either sourcing the missing operational figures or redefining the scenario model
around the layers that actually exist (see §6).

**Bottom line:** the orchestration and math are real, wired, and tested; the design doc's data model
is the principal blocker to a true real-data end-to-end run; and a large part of the spec (frontend,
citizen mode, comparison, several trust gaps) is intentionally **deferred** in this pass.

---

## 2. What this pass wired (new/changed files)

```
src/backend/app/services/scenario/      NEW package
  feasibility.py  scenario_hash.py  interventions.py  human_scale.py
  official_positions.py  chloride.py  demand.py  intake.py  scenario_store.py   (corrected fix-pack modules)
  models.py        scenario dataclasses (ScenarioParams/Results/Card/ReasoningStep)
  extraction.py    deterministic param extractor (mock GreenPT — keyless, testable)
  fixture.py       synthetic DuckDB shaped per the design doc
  workflow.py      LangGraph StateGraph: extract→fetch→calculate→enrich→format (+followup)
src/backend/app/routers/scenario.py      NEW  POST /api/scenario/run (SSE) + GET /api/scenario/{id}
src/backend/app/main.py                  EDIT (2 lines): import + include scenario.router
src/backend/scripts/check_assumption_sources.py   NEW  CI source_url gate
src/backend/tests_scenario/              NEW  golden-path A & B + SSE endpoint tests (all green)
.github/workflows/ci.yml                 NEW  runs the gate + scenario tests on push
```

Run locally:
```bash
cd src/backend
pip install langgraph duckdb fastapi sse-starlette httpx pytest fpdf2 pydantic
PYTHONPATH=. python scripts/check_assumption_sources.py     # gate
PYTHONPATH=. python -m pytest tests_scenario -q             # 5 passed
```

---

## 3. The data-reality gap (detail)

| Design doc assumes | Real bundled table | Reality |
|---|---|---|
| `leveringszones(capaciteit_m3_dag, vraag_2023_m3_dag, zone_id)` | — | **Does not exist.** No supply/demand table at all. |
| `winlocaties(capaciteit_m3_dag, naam)` | `drinkwater_infrastructuur` | Different: `h3_id, IMRO_kleur, Onderverdeling, *_fraction` (1408 rows). No capacities. |
| `productieketen(cl_threshold_mg_l, intake_id, productie_cap_m3_dag)` | `drinkwater_productieketen` | `h3_id, Bedrijf, Functie, Locatie` — **0 rows**, no threshold column. |
| `krw_waterlichamen(status_2023, krw_doeljaar)` | `toestandsbeoordeling_oppervlaktewaterlichamen` | KRW quality cols present but **0 rows**. |
| `innamepunten_chloride(cl_mg_l, datum)` | — | Does not exist. |
| `alternatieve_bronnen(max_capaciteit_m3_dag)` | — | Does not exist. |
| `zes_uur_zones(intake_id, radius_km)` | `zes_uur_zones_drinkwater` | Exists (900 rows) but schema differs: `OBJECTNAAM, OWMNAAM, STATUS, STROOMGEB…`. |

All real views are registered by folder name via `register_tables(con)` and share an `h3_id` key —
the H3 strategy itself is sound; the **operational attributes are simply absent**.

---

## 4. End-to-end proof (on the synthetic fixture)

| Golden path | Result | Notes |
|---|---|---|
| A — "50 MW datacenter bij Pijnacker-Nootdorp, 2040" | **STOP**, demand 169,616 m³/d, gap −19,616 | ≈ the doc's own 169,000 example; verdict across all 5 KNMI presets; make-it-feasible ranks interconnection→GO, buffer→STOP (B2 fix). |
| B — "Hollandse IJssel 6 weken uit, KNMI Hd, 2040" | **STOP**, gap −317,223, chloride 513.7 mg/L | exceeds the **per-intake** threshold 200 mg/L read from `productieketen` (`from_db=True`); chloride reasoning step recorded. |

`tests_scenario`: 5 passed (golden A x2, golden B x2, SSE+stable-URL endpoint x1).

---

## 5. Coverage matrix (by design-doc area)

### Architecture & API (§4, §6, §8, §9)
| Requirement | Status | Evidence / gap |
|---|---|---|
| Unified `POST /scenario/run` | ✅ | `routers/scenario.py` |
| SSE event stream (params_confirmed, reasoning_step, feasibility_class, official_position, scenario_card, map_data, done) | ✅ | run-to-completion then stream; token-level `astream_events` deferred |
| `GET /scenario/{id}` stable URL | ✅ | in-memory `ScenarioStore`; DuckDB-file persistence deferred |
| `/kennisbasis/query` + `/status` | ⬜ | not wired (GAP 1) |
| LangGraph scenario workflow | 🟡 | 6 nodes wired vs ~19 specified; existing descriptive workflow left intact |
| ScenarioState / AgentState | ✅ | `workflow.ScenarioState` (trimmed) |
| detect_mode / confirm_with_user | 🟡 | low-confidence `followup` wired; explicit confirm + mode routing simplified |

### Data model (§7)
| Requirement | Status | Evidence / gap |
|---|---|---|
| ScenarioParams / Results / Card / ReasoningStep | ✅ | `scenario/models.py` |
| Assumption + mandatory-source validation | 🟡 | sources enforced by CI gate; full slider-grade Assumption objects not all wired |
| SourceEntry registry | 🟡 | official docs + intervention sources carry URLs; full per-number registry light |

### Calculation engine (§11)
| Requirement | Status | Evidence / gap |
|---|---|---|
| Demand + conservative range | ✅ | `demand.py` |
| Feasibility GO/CAUTION/STOP across 5 KNMI presets | ✅ | `feasibility.py` (C1 single-definition fix) |
| Capacity check | ✅ | on synthetic data |
| Per-intake chloride threshold + fallback | ✅ / ⛔ | works on synthetic; real `productieketen` empty |
| KRW risk check | 🟡 / ⛔ | logic + table present; real KRW table empty |
| Onset-year calculator | 🟡 | simplified inline stepping |
| Stakeholder rule engine | ⬜ | rule table exists in fix-pack; not wired into this slice |
| "Make it feasible" intervention ranking | ✅ | `interventions.py` (C3 + B2 buffer fix) |
| Human-scale analogy | ✅ | `human_scale.py` |
| Overlay `layer_id` contract | 🟡 | overlay emitted with `layer_id`; geojson empty (no real geometry) |

### Trust primitives — the 10 GAPs (§18/§19)
| GAP | Status | Evidence / gap |
|---|---|---|
| 1 Kennisbasis panel | ⬜ | deferred |
| 2 hash + stable URL + version drift | 🟡 | hash ✅ (reproducible, tested), stable URL ✅; drift + "verify" ⬜ |
| 3 citation block + PDF export | 🟡 | `render_scenario_pdf` exists (fix-pack, Unicode-safe); route not mounted; APA strings ⬜ |
| 4 human scale on metrics | ✅ | wired into results |
| 5 make-it-feasible ranking | ✅ | wired; shown on STOP/CAUTION |
| 6 cumulative load warning | ⬜ | deferred |
| 7 per-intake chloride threshold | ✅ / ⛔ | wired; blocked on real (empty) data |
| 8 official position panel | ✅ | `official_positions.py` (C5; housing figure corrected to 235.460) |
| 9 Waterinfo mandatory guard | ⬜ 🔑 | no live API; chloride uses a baseline value |
| 10 citizen mode | ⬜ | deferred |

### Scenario types (§3, §13, §14)
| Type | Status | Evidence / gap |
|---|---|---|
| Type 3 drop-pin (Golden A) | ✅ | tested |
| Type 1 intake failure (Golden B) | ✅ | tested |
| Comparison / scenario_b + ScenarioDelta (Golden C) | ⬜ | deferred |
| Type 2 multi-hazard | ⬜ | deferred (stretch in doc) |
| Type 4 intervention stacking | 🟡 | `stack_interventions` logic present; endpoint not exposed |

### Frontend (§15, §16)
| Requirement | Status | Evidence / gap |
|---|---|---|
| Corrected `useScenarioSSE.ts` | 🟡 | delivered in fix-pack; not integrated into the repo's Vue app |
| 17 Vue components (ScenarioCard, FeasibilityBadge, …) | ⬜ | deferred — this pass is backend + endpoint |
| GGC layer tree / legend / feature info | ⬜ | deferred |

### Reproducibility & determinism (§26)
| Requirement | Status | Evidence / gap |
|---|---|---|
| same params → same hash | ✅ | tested in `test_golden_path_a` |
| `git_commit` in every card | ✅ | `format_node` |
| cosmetic `np.random.seed` removed | ✅ | B5 |
| GreenPT temperature pinned | 🟡 | extractor is deterministic; LLM path (`fix-pack greenpt.py`, temp 0) not yet merged into repo `llm.py` |
| dataset version drift / verify endpoint | ⬜ | deferred |
| MLflow per-node scenario logging | ⬜ | deferred (repo has MLflow for the descriptive flow) |

### Acceptance tests & CI (§4.2, §26)
| Requirement | Status | Evidence / gap |
|---|---|---|
| `test_calculation_golden_path_a` | ✅ | `tests_scenario/test_golden_path_a.py` (doc named it; now written) |
| `test_calculation_golden_path_b` | ✅ | `tests_scenario/test_golden_path_b.py` |
| SSE endpoint test | ✅ | `tests_scenario/test_scenario_endpoint.py` |
| CI gate blocks empty `source_url` | ✅ | `scripts/check_assumption_sources.py` + `.github/workflows/ci.yml` |

---

## 6. Running it on real data (what it would take)

1. **Source the operational data the model needs** — per-zone supply capacity and demand, intake
   production capacities, per-intake chloride thresholds, a chloride time series, and alternative
   sources. None are in the bundled datasets.
2. **OR redefine the scenario model** around the layers that DO exist (H3 thematic coverage,
   `zes_uur_zones_drinkwater`, `drinkwaterbedrijven`, `waterschappen`) — e.g. a qualitative
   pressure/exposure score per H3 cell rather than an m³/day supply gap. This is the more realistic
   path for the actual hackathon data and should be a design decision, not a silent substitution.
3. **Swap the fixture for real views:** replace `fixture.build_synthetic_db()` in
   `workflow.fetch_node` with the repo's `connect_delta()` + `register_tables(con)` and point the
   queries at the chosen real tables/columns.
4. **Add a live LLM + Waterinfo:** set `GREENPT_KEY`, route extraction through `make_llm(...)`
   at `temperature=0` (merge the fix-pack `greenpt.py` defaults into `app/services/llm.py`), and
   implement the Waterinfo client behind GAP 9's guard.

---

## 7. Prioritized "what's left"

**P0 (to claim a real end-to-end):** resolve the data model decision (§6.1/§6.2); wire `fetch_node`
to real views; add comparison mode (Golden C) since the demo hinges on it.
**P1:** citizen mode (GAP 10), cumulative load (GAP 6), Waterinfo guard (GAP 9), PDF/citation route
(GAP 3), version-drift + verify (GAP 2), stakeholder-rule node.
**P2:** the Vue frontend (17 components + integrate the corrected `useScenarioSSE.ts`), kennisbasis
(GAP 1), MLflow scenario logging, Type 2/4 endpoints.

---

*Statuses reflect the wired build in this pass. The scenario logic is verified by automated tests on
a synthetic fixture; the binding constraint on a real end-to-end run is the absence of operational
data in the provided datasets, not the engine code.*
