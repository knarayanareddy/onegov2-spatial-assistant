# OneGov #2 — Drinkwaterzekerheid Scenario Engine
## Design Document **v3 — repo-aligned** (adapts v2 to `govtechnl/onegov2-spatial-assistant`)

**What this is.** v2 (`onegov2_design_document_complete.md`) was written *before* the real starter
repo was in hand. It assumed Leaflet, a relational m³/day operational schema, invented SSE events,
and `requirements.txt`. This v3 re-grounds the same product vision on the **actual** repo and the
**actual** shipped data, folds in the fix-pack corrections, and re-bases the calculation model on
**assumption-driven H3 scoring** over the real thematic layers.

**The one decision (made):** *re-ground the quantitative model on sourced assumptions applied to the
real H3 thematic data.* Rationale: it runs on the data that actually ships, and it matches what the
brief rewards (combine ≥2 themes; surface assumptions/uncertainty; a navolgbaar redeneerproces). The
hard m³/day supply-gap engine in v2 is **not** implementable on the shipped data (no capacity/demand
tables; `drinkwater_productieketen` and `toestandsbeoordeling_oppervlaktewaterlichamen` are empty).

**The trust/traceability spine is kept verbatim:** sourced assumptions with a CI gate, ranges over
constants, scenario hash + reproducibility, reasoning trail, official-position anchor, citation.

---

# Part A — DELTA LOG (v2 section → status)

Status: **KEEP** (unchanged intent) · **ADAPT** (same intent, re-grounded) · **REPLACE** (new mechanism) · **DROP**.

| v2 §| Topic | Status | Why / what changes |
|---|---|---|---|
| 0 | Purpose, scope, changelog | ADAPT | re-scoped to "extend the starter repo"; out-of-scope list kept |
| 1 | Product vision / institutional contract | **KEEP** | the defensible, citeable, explainable thesis is the differentiator |
| 2 | Users, personas, UI principles | KEEP | + adopt PZH house-style libs (below) instead of bespoke GGC clone |
| 2.3–2.4 | Kadaster GGC / Leaflet baseline | REPLACE | repo uses **Deck.gl + MapLibre** (native H3); reuse repo's map shell |
| 3 | Golden-path scenarios | ADAPT | re-anchored to the challenge owners' authoritative list (`docs/example-scenarios.md`) |
| 4.1 | Stack overview | ADAPT | Deck.gl/MapLibre, uv, ports 5173/8001, Postgres sessions, GreenPT `gemma4` |
| 4.2 | File-level map | REPLACE | use the real tree: `app/services/{workflow.py,nodes/,helpers/,prompts/}` |
| 4.3 | Env vars | ADAPT | `GREENPT_KEY` (set), `MLFLOW_ENABLED`, `DATABASE_URL`; not v2's invented vars |
| 4.4 | docker-compose | DROP | repo already ships `docker-compose.yml` + `.prod.yml` + MLflow on :5001 |
| 4.5 | `requirements.txt` deps | REPLACE | **uv + `pyproject.toml`**; add `h3` usage (DuckDB `h3` ext already loaded) |
| 5 | Data inventory & schema | REPLACE | re-grounded in real tables/columns + `_llm_metadata_*.json` (Part C) |
| 5.2 | H3 join strategy | ADAPT | repo `helpers/tables.py` globs Parquet, `LEFT JOIN`s themes on `h3_id` (res **9**) |
| 5.3 | Day-1 blocking checks | ADAPT | check the **real** tables exist + non-empty; flag the two empty tables |
| 6 | Unified `/scenario/run` endpoint | ADAPT | implement as a **scenario branch** + a thin `/api/scenario/run`; reuse repo SSE |
| 6.3 | Invented SSE event types | REPLACE | reuse repo events (`map_config/map_data/text/step_thinking_summary/done`) |
| 7 | Data model (dataclasses) | KEEP | trimmed `ScenarioParams/Results/Card`; **Assumption is central** |
| 7.2 | Assumption + source CI gate | **KEEP** | this is the spine; CI gate already wired (`check_assumption_sources.py`) |
| 7.3 | Default assumption library | REPLACE | new library for the H3 model (Part D) |
| 8 | AgentState | ADAPT | extend the repo's `ConversationState` TypedDict, don't invent a parallel one |
| 9 | LangGraph workflow | ADAPT | mirror repo's `BaseNode` async contract + `astream_events` streaming |
| 10 | GreenPT prompts | ADAPT | repo prompt convention: `.md` per node under `services/prompts/`; temp 0 |
| 11.1 | Demand calc | ADAPT | becomes a per-cell **demand-pressure** signal from CBS × sourced assumptions |
| 11.2 | Chloride mg/L + Waterinfo + per-intake threshold | REPLACE | use real **`verzilting.ZOUT_CONC`** class per H3 cell; live Waterinfo optional (team-added) |
| 11.3 | Capacity check from DuckDB | DROP | no capacity table exists; replaced by protection-sensitivity signal |
| 11.4 | KRW risk check | ADAPT | `toestandsbeoordeling` is empty → use `gebiedsviewer` quality/nutrient layers |
| 11.5 | Onset-year calculator | ADAPT | year stepping applies KNMI/growth assumption multipliers to the score |
| 11.6 | Stakeholder rule engine | KEEP | rule table maps (scenario, verdict) → stakeholders + policy URLs |
| 11.7 | Intervention catalogue + ranking | ADAPT | interventions become **score/assumption deltas**, not m³/day (Part D) |
| 11.8 | Human-scale converter | KEEP | fix-pack metric-aware version (C4) |
| 11.9 | Overlay `layer_id` contract | KEEP | overlays are H3-cell collections carrying `layer_id` |
| 12 | SQL per scenario type | REPLACE | H3 layer-combination SQL over real views (Part D) |
| 13/20 | Type 2 multi-hazard | ADAPT | natural fit: weighted multi-layer composite = multi-hazard |
| 14/21 | Type 4 intervention effectiveness | ADAPT | re-expressed as score deltas; stacking kept |
| 15 | Frontend state mgmt (Pinia/Leaflet) | REPLACE | repo uses Vue composables (`useChat/useMap/useInzicht`) + Deck.gl |
| 16 | Vue components | ADAPT | build on PZH component libraries + existing `components/{chat,map,inzicht}` |
| 17 | Map layer config (Leaflet z-order) | REPLACE | Deck.gl `H3HexagonLayer` configs + color scales |
| 18/19 | Trust primitives & traceability (10 GAPs) | KEEP/ADAPT | see Part E — most survive; GAP7/9 re-grounded on real data |
| 19.1 | 3-layer traceability (Insight/MLflow/Card) | **KEEP** | repo already has Insight panel + MLflow; reuse both |
| 22 | Error catalogue | KEEP | map onto repo's `error` SSE event |
| 23 | README | ADAPT | repo README stands; add a scenario section |
| 24 | `.env.example` | ADAPT | repo ships one; add scenario knobs |
| 25 | Build plan | ADAPT | re-sequenced for "extend the graph" (Part F) |
| 26 | Acceptance criteria | ADAPT | re-map to `CHALLENGE.md` Must/Should + `example-scenarios.md` |

---

# Part B — Architecture (re-targeted to the real repo)

```
Vue 3 + Deck.gl + MapLibre (H3 hexagons) + PZH component libs
   │  POST /api/chat (SSE)  — events: meta · text · map_config · map_data · status · step_thinking_summary · error · done
   ▼
FastAPI + LangGraph (StateGraph(ConversationState), astream_events v2)
   nodes: check_intent → [scenario? ] → … → describe_results            (existing descriptive branch kept intact)
   NEW scenario branch: extract_scenario → select_h3_area → score_h3 → rank_interventions → format_scenario
   ▼
DuckDB (delta + h3 extensions)  ── reads Parquet via helpers/tables.py glob, LEFT JOIN all themes on h3_id (res 9)
GreenPT (gemma4, OpenAI-compatible, temperature 0)   ·   PDOK geocoder   ·   MLflow tracing (:5001)   ·   Postgres sessions
```

**Conventions to follow (from the repo, not v2):**
- Package manager **uv** (`pyproject.toml`); `uv run pytest tests/...`.
- LLM via `app/services/llm.py::make_llm(model)` → GreenPT; pin `temperature=0` for scenario calls (fix-pack S7).
- New nodes subclass `app/services/nodes/base.py::BaseNode` (`async run()`, `fallback()`, `dispatch()`).
- Reasoning trail = **`step_thinking_summary`** SSE events into the existing **Insight panel** + MLflow — do *not* invent a parallel mechanism (v2 §6.3 dropped).
- Map overlays = Deck.gl `H3HexagonLayer` payloads (list of `{h3_id, value, klasse}`) sent via `map_data`.
- House style = `@pzh-temporary/vue-component-library` + `…/html-component-library`.

---

# Part C — Data, re-grounded in the actual repo (replaces v2 §5)

Registration: `helpers/tables.py` discovers every `data/<theme>/<table>/*.parquet`, exposes each as a
view **named after the folder**, normalises `h3_id` (CBS `h3_index` → `h3_id`), and `LEFT JOIN`s themes
on `h3_id`. Dictionary is built from `_llm_metadata_<theme>.json`. **H3 resolution 9 (~0.1 km²/cell).**

### Real tables this engine uses (verified columns)
| View (real) | Rows | Columns used | Role in the model |
|---|---|---|---|
| `verzilting` | 14 279 | `KWEL_INFIL`, `RELEVANT`, **`ZOUT_CONC`** (e.g. `> 200mg/l`) | **salinity pressure** (the verzilting axis) |
| `zes_uur_zones_drinkwater` | 900 | `OWMNAAM`, `STATUS`, `STROOMGEB`, `WATER` | drinking-water **protection sensitivity** |
| `drinkwater_infrastructuur` | 1 408 | `IMRO_kleur`, `Onderverdeling`, `*_fraction` | infrastructure presence |
| `drinkwaterbedrijven` | 33 942 | `naam` | supplier service area |
| `overstromingen_kwetsbaarheid_panden_na_dijkdoorbraak` | 4 546 | `Risico`, `Wateroverlast_score_fraction` | flood co-pressure |
| `bodemdaling_bodemdaling_wegen` | 2 073 | `Begaanbaar_score_fraction`, … | subsidence co-pressure |
| `natuurlijke_spons_kansrijk` | 6 876 | `KlimaatbufferType`, `Legenda`, `Scenario` | **opportunity** (scenario 6) |
| `cbs_vierkantstatistieken_2022_consumption` *(extra_data)* | 6 248 | `aantal_inwoners_sum`, `aantal_part_huishoudens_sum` | **demand** proxy & growth |
| `capaciteitskaart_afname_regionaal` *(extra_data/woondeals)* | 25 777 | `afname`, `voedingsgebied_naam` | datacenter grid co-location (scenario 5) |

### Caveats the doc must state honestly (and the engine surfaces in the Insight panel)
- `drinkwater_productieketen` (h3_id, Bedrijf, Functie, Locatie) and `toestandsbeoordeling_oppervlaktewaterlichamen` (KRW quality cols) **ship empty (0 rows)** — do not depend on them; degrade gracefully.
- There is **no** `capaciteit_m3_dag` / `vraag_2023_m3_dag` / per-intake `cl_threshold_mg_l` anywhere. All m³/day figures are **assumptions**, not lookups.
- `extra_data/` is opt-in (`CBS`, `lgn`, `woondeals`); registering it adds prompt columns (minor accuracy cost).
- **CBS h3 reconciliation:** CBS ships `h3_index` as a leading-zero 16-char string; the repo's `tables.py` only `LOWER()`s it, so CBS does **not** actually join the 15-char layers (0 overlap — a latent gap in the starter). The engine strips the pad zero to a canonical key → **2,145 overlapping cells** recovered; both layers are resolution 9. NB: the CBS `_consumption` values are normalised/aggregated, not raw headcounts — treat demand as a **relative** population-density signal, not absolute m³.
- **KNMI'23 scenarios, KRW/chloride live (Waterinfo RWS), DINOloket groundwater are NOT shipped** — teams add them under `extra_data/` with a matching `_llm_metadata_*.json` (per `docs/data-inventory.md`). The model treats their absence as the default-assumption path.

---

# Part D — The calculation model: assumption-driven H3 scoring (replaces v2 §11–§12)

**Idea.** A scenario selects a set of H3 cells (area of interest), computes a per-cell
**DrinkwaterDruk score 0–100** as a weighted sum of normalised sub-signals derived from *real* layers,
each **modulated by sourced assumptions**, then aggregates to a GO/CAUTION/STOP verdict by the share of
area above thresholds. Every number that isn't directly in the data is an `Assumption` (sourced,
slider-adjustable, shown in the Insight panel).

### Sub-signals (each normalised 0–1 from real columns)
| Signal | Source (real) | Mapping (an Assumption) |
|---|---|---|
| `salinity` | `verzilting.ZOUT_CONC` | class → severity, e.g. `{">200mg/l":1.0, "150-200mg/l":0.6, "<150mg/l":0.2}`; × KNMI dryness multiplier |
| `demand` | CBS `aantal_inwoners_sum` | × `demand_per_person_m3` (VEWIN) × `(1+population_growth_pct)`; min-max normalised over the area |
| `flood` | `overstroming….Risico` | risk class → severity |
| `subsidence` | `bodemdaling….Begaanbaar_score_fraction` | already 0–1 |
| `protection` | in `zes_uur_zones_drinkwater` (STATUS) | binary/weighted — raises the stakes in protection zones |
| `opportunity` | `natuurlijke_spons_kansrijk` present | **subtracts** (restoration potential) — scenario 6 |

`score = 100 · Σ wᵢ·signalᵢ` (weights `wᵢ` are Assumptions summing to 1). Development add-ons (datacenter,
housing) inject extra `demand` via their own sourced assumptions (datacenter L/day per MW; m³/dwelling).

### Verdict — ONE definition (fix-pack C1 discipline, re-expressed for a 0–100 score)
```python
# app/services/scenario/scoring.py — single source of truth
VERDICT_CAUTION, VERDICT_STOP = 33.0, 66.0   # sourced thresholds (Assumptions)
def verdict_from_score(score: float) -> str:
    if score >= VERDICT_STOP: return "STOP"
    if score >= VERDICT_CAUTION: return "CAUTION"
    return "GO"
# area verdict: STOP if >X% of cells are STOP (X is an Assumption, default 20%)
```

### Default assumption library (replaces v2 §7.3) — every entry has a mandatory `source_url`
| key | value (range) | unit | source |
|---|---|---|---|
| `demand_per_person_m3_day` | 0.119 (0.10–0.14) | m³/p/d | VEWIN Waterstatistiek |
| `datacenter_m3_per_mw_day` | 12 (5–20) | m³/d/MW | IEA Data Centres |
| `population_growth_pct_2040` | 0.08 (0.04–0.12) | frac | Ruimtelijk Arrangement Rijk–ZH 2025 |
| `knmi_dryness_multiplier` | 1.8 Hd (1.0–1.8) | factor | KNMI'23 |
| `weight_salinity / demand / flood / …` | 0.35 / 0.30 / … | frac | Methodologie |
| `verdict_caution / verdict_stop` | 33 / 66 | score | Methodologie |
| `area_stop_share` | 0.20 | frac | Methodologie |

### Reproducibility & interventions (fix-pack folded in)
- **Scenario hash** = `compute_scenario_hash(params, assumption_overrides)` → 32 hex, overrides in identity (fix-pack **C2**).
- **Determinism**: SQL + arithmetic are deterministic; GreenPT only extracts params and writes prose at `temperature=0`; the **cache** is the reproducibility boundary (fix-pack S7/F14). No cosmetic seeds (B5).
- **"Make it feasible"** (GAP 5): interventions are **score/assumption deltas**, not m³/day. Reuse the fix-pack single catalogue + `effective_delta()` + `rank_interventions()` (fix-pack **C3**), with the **buffer fixed to volume/window** (≈1 000 m³/d, not 30 000 — **B2**). Example deltas: *nature restoration in intrekgebieden* → +opportunity in targeted cells; *demand restriction 10%* → ×0.9 on `demand`; *interconnection* → −salinity weight where an alternative supply applies.
- **Human-scale** (GAP 4): fix-pack metric-aware converter (**C4**), e.g. demand → "≈ N huishoudens".

---

# Part E — Trust primitives / 10 GAPs, re-grounded (v2 §18–§19)

| GAP | Status | Re-grounded form |
|---|---|---|
| 1 Kennisbasis | KEEP | reuse `GET /api/dictionary` (already built from `_llm_metadata`) — "what does the system know?" |
| 2 hash + stable URL + drift | KEEP | fix-pack `ScenarioStore` (DuckDB); dataset version = Parquet folder mtime/hash |
| 3 citation + PDF | **DONE** | `pdf.py` Unicode-safe `render_scenario_pdf` + APA `build_citation`; routes `/api/scenario/{id}/pdf` + `/citation` mounted |
| 4 human scale | KEEP | every headline number gets a cited analogy (**C4**) |
| 5 make it feasible | ADAPT | interventions as score deltas (Part D) |
| 6 cumulative load | ADAPT | "other active scenarios in the same `voedingsgebied`/zone" via the scenario store |
| 7 per-intake chloride threshold | REPLACE | real **`verzilting.ZOUT_CONC`** class per cell; threshold is a sourced Assumption (no per-intake DB value exists) |
| 8 official position | KEEP | fix-pack registry (**C5**); housing figure corrected to 235 460 (ZH 2022–2030) |
| 9 Waterinfo guard | ADAPT | optional team-added live data; absence → labelled fallback to `verzilting` class (never silent) |
| 10 citizen mode | **DONE** | `citizen.py`: verdict-first B1-Dutch card, postcode + water-company, no jargon; `citizen_response` SSE event |

Traceability stays the v2 three-layer model **using the repo's existing channels**: Insight panel
(`step_thinking_summary`) for humans, **MLflow** for machines, ScenarioCard for citeable artefacts.

---

# Part F — Build plan & acceptance (re-mapped to CHALLENGE.md)

**Scenarios (anchored to `docs/example-scenarios.md`, the owners' authoritative list):**
- **Spine (Golden A):** *Scenario 5 — datacenter water consumption* (drop-pin; datacenter L/day is the headline assumption, surfaced in Insight). Touches `drinkwaterzekerheid` + `capaciteitskaart_afname` + `verzilting`.
- **Second / comparison (Golden B + Should-criterion):** *Scenario 1 / 4 — dry KNMI + verzilting on the Hollandse IJssel (± population peak)*; demo **with vs without** the verzilting/dry shock (a comparison). Touches `verzilting` + `zes_uur_zones_drinkwater` + CBS.
- **Stretch:** *Scenario 2 (KRW land-use)* and *Scenario 6 (nature restoration opportunity)* — pure spatial, strong fit for the H3 model.

**Acceptance (maps to CHALLENGE.md Must/Should):** NL question → computed scenario ✓; ≥2 data themes combined ✓ (e.g. `verzilting` × CBS × `zes_uur_zones`); data/assumptions/limitations explicit ✓ (Insight + assumption sliders); reasoning chain navolgbaar ✓ (Insight + MLflow); open-source ✓; existing descriptive flow still works ✓ (separate branch); ≥2 scenarios / a comparison demo ✓.

**Sequencing:** (1) register `extra_data/CBS` + `woondeals`; (2) `scoring.py` + assumption library + verdict (fix-pack discipline); (3) `select_h3_area` (PDOK drop-pin `grid_disk`; intake → `zes_uur_zones` cells); (4) scenario nodes on `BaseNode` + scenario branch in `workflow.py`; (5) Insight/`step_thinking_summary` + MLflow; (6) Deck.gl `H3HexagonLayer` overlay + assumption sliders (PZH components); (7) comparison mode; (8) citation/PDF + stable URL; (9) CI gate (already wired).

---

# Part G — Fix-pack corrections folded in (so v3 can't reintroduce v2's bugs)
C1 single feasibility/verdict definition · C2 one scenario hash (overrides in identity, [:32]) ·
C3 one intervention catalogue · **B2 buffer = volume/window** · C4 metric-aware human-scale ·
C5 one official-positions registry (housing 235 460) · C6 one `ScenarioStore` · B1 Unicode-safe PDF ·
S3 adjustable outage cap · S7 GreenPT `temperature=0` + cache-is-the-determinism-boundary ·
B5 cosmetic seed removed. (Full rationale + drop-in code: `onegov2_fixpack.md`.)

# Part H — Runnable reference (wired on real data)

The scenario branch at `src/backend/app/services/scenario/` now runs the v3 H3 model **on the real
shipped Parquet — the synthetic fixture is off the path**:

- `real_scoring.py` composes **`verzilting` × `overstromingen_kwetsbaarheid` × `zes_uur_zones_drinkwater`
  × CBS** on a canonical `h3_id` into a per-cell DrinkwaterDruk score (0–100) + area verdict. The
  **demand** sub-signal comes from CBS population × `demand_per_person` × `(1+growth)`, with an
  **added-homes** lever (brief scenario 3). All four weights + demand reference are sourced assumptions.
- `area.py` **`select_h3_area`**: drop-pin → PDOK geocode + H3 `grid_disk` (python `h3`, ~0.35 km/ring);
  intake → the `zes_uur_zones_drinkwater` cells. So scoring runs on the scenario's actual cells.
- `workflow.py` LangGraph: `extract → score(area + real_scoring) → enrich → format`; `run_scenario()`
  for a single scenario and **`run_comparison()`** for the with/without-shock comparison (Should criterion).
- `routers/scenario.py`: `POST /api/scenario/run` (add `"compare": true`) streams the SSE events;
  `GET /api/scenario/{id}` is the stable URL.
- Interventions ("make it feasible", GAP 5) are ranked by **re-scoring** each assumption-delta on the real data.

**Verified numbers (real data):**
- *Comparison (intake area = 110 zes-uur cells):* without shock (KNMI B) → **CAUTION** (score 50.5);
  with the dry/verzilting shock (KNMI Hd) → **STOP** (score 82.4); Δ +31.9, verdict CAUTION→STOP.
- *Area selection:* datacenter drop-pin (Pijnacker, PDOK grid_disk) scores **67 cells** vs the IJssel
  intake's **110 zes-uur cells** — genuinely different areas.
- *Scenario 3 (population):* over the whole salinity region, +80 000 homes nudges STOP-cells 750→779
  (demand is sparse where salinity bites — an honest geographic-separation finding; the demand axis
  bites harder when scored on the built-up area via `select_h3_area`).

The dry knob amplifies the salinity contribution (honest, since `ZOUT_CONC` is a saturated single class);
CBS `_consumption` is a relative density signal, not absolute headcounts. Proven by **16 passing tests**
(`tests_scenario/`: golden A & B, comparison, SSE endpoint, real-scoring, CBS demand, area selection) +
the source_url CI gate.
