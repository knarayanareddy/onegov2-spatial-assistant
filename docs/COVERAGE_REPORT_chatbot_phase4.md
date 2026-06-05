# Chatbot Phase 4 — coverage report (recipe-builder + Postgres activation)

## Verification snapshot
- `tests_chatbot`: **72 passed** (P1 29 + P2 11 + P3 18 + P4 14).
- `tests_scenario`: **27 passed** (engine `base=` hook is backward-compatible — no regression).
- assumption-source gate: **PASSED**.
- Full suite: **99 passed**.
- Postgres path verified on a real SQL engine (SQLite + aiosqlite): Alembic upgrade/downgrade + full `SqlFaqCache` lifecycle.

## Brief §5 Phase 4 (optional) — declarative recipe-builder
| Requirement | Status | Evidence |
|---|---|---|
| Whitelisted H3 layer combinations + weights | **Implemented** | `recipe.SIGNALS` (salinity/demand/flood/protection) → `weight_*` overrides. `test_valid_recipe_maps_to_overrides` |
| Validated, not code | **Implemented** | `validate_recipe` (weights sum to 1, ranges, whitelisted presets/intakes); maps to ScenarioParams + assumption_overrides; engine stays deterministic. `test_weights_must_sum_to_one`, `test_unknown_signal_rejected`, `test_weight_out_of_range_rejected` |
| Run + surface results | **Implemented** | `POST /api/chatbot/recipe/run` (SSE → ScenarioCard) + `GET /recipe/schema`; frontend recipe-builder. `test_recipe_run_endpoint_streams_card`, `test_schema_endpoint` |
| Choose scoring universe | **Implemented** | optional `base` ("salinity"/"populated") via a backward-compatible engine hook. `test_populated_base_changes_universe` |
| FAQ promotion-with-human-review | **Implemented (Phase 3)** | auth-gated promote/reject + grounded re-check (see Phase 3 report). |

## Postgres activation (Phase 3 store, now wired)
| Item | Status | Evidence |
|---|---|---|
| Opt-in backend switch | **Implemented** | `FAQ_CACHE_BACKEND` setting + lifespan `set_store(SqlFaqCache(engine))`. |
| Alembic migration runs | **Verified on SQLite** | `alembic stamp 7e2e6216e30f && alembic upgrade head` created `faq_cache` (12 cols); `downgrade -1` dropped it. |
| Adapter works against a real DB | **Verified on SQLite** | `test_faq_cache_sql.py` — dedup/hits, promote, published-vs-stale, reject, promote-after-reject, bad-id guard. |
| Postgres run | **Your environment** | `export FAQ_CACHE_BACKEND=postgres; alembic upgrade head` — the wire protocol is firewalled in the sandbox, so the live PG run is yours; de-risked by the SQLite run (portable TEXT/JSON columns). |

## Safety notes
- The recipe-builder cannot inject arbitrary levers: only the four signal weights + the
  whitelisted presets/area reach the engine, and weights must sum to 1.
- No code/SQL synthesis anywhere; the recipe is data, the engine is deterministic and sourced.

## The brief's phased plan is now complete
Phase 1 (knowledge chatbot + FAQs) · Phase 2 (scenario-from-chat gate) ·
Phase 3 (FAQ caching + ranking + moderation) · Phase 4 (recipe-builder + Postgres).
