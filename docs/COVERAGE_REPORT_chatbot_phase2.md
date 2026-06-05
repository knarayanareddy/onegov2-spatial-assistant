# Chatbot Phase 2 — coverage report (scenario-from-chat)

Maps the Kickoff Brief's Phase 2 to what shipped, with test evidence.

## Verification snapshot
- `tests_chatbot`: **40 passed** (29 Phase 1 + 11 Phase 2).
- `tests_scenario`: **27 passed** (engine `params=` hook is backward-compatible — no regression).
- assumption-source gate: **PASSED**.
- Real run via chat (offline, shipped data): IJssel intake + KNMI Hd → **STOP, score 82.4, 110 cells** (matches design doc Part H verified numbers).

## Brief §5 Phase 2 + §2 job B
| Requirement | Status | Evidence |
|---|---|---|
| Route a chat message through `extract_scenario_params` into the engine | **Implemented** | `scenario_run.prepare_scenario_request` → `execute_plan` → `run_scenario`/`run_comparison`. `test_execute_plan_returns_real_card` |
| Validate against supported levers/datasets (whitelist) | **Implemented** | `validate_params` + `ALLOWED_*` sets. `test_unknown_lever_is_rejected`, `test_unknown_intake_clarifies`, `test_weight_out_of_range_is_rejected` |
| Return ScenarioCard + map | **Implemented** | endpoint streams `scenario_card` + `map_data`. `test_endpoint_runs_scenario_and_streams_card` |
| Optional comparison | **Implemented** | `_detect_comparison` → `run_comparison`; streams `scenario_delta`. `test_comparison_is_detected`, `test_execute_comparison_returns_delta` |
| No code execution | **Implemented (by construction)** | The LLM only emits validated params; the engine runs deterministic scoring. No exec/SQL path exists. |
| Clarify when a request doesn't fit the levers (no dead ends) | **Implemented** | low confidence / bad type / unknown intake / missing location / unknown lever → `followup_question`. `test_low_confidence_clarifies`, `test_missing_location_clarifies`, `test_endpoint_clarifies_underspecified_run` |

## The whitelist (the safety gate)
- scenario_type ∈ {drop_pin, intake_failure, multi_hazard, intervention}
- knmi_preset ∈ {B, Hd, Hn, Ld, Ln}; growth_preset ∈ {laag, middel, hoog}
- assumption-override lever keys ∈ {knmi_dryness_multiplier, population_growth_pct,
  added_homes, weight_salinity, weight_demand, weight_flood, weight_protection,
  demand_ref_m3_per_cell} (weights clamped 0–1)
- intake ∈ {IJssel, Lek, Maas, Hollandse IJssel, Nieuwe Maas}; horizon 2025–2100
- min extraction confidence 0.5
Anything else → clarifying question; never executed.

## Design notes / honest limitations
- The recipe that runs is shown first via `scenario_params_confirmed` (transparency):
  the rule extractor defaults some fields (e.g. an unrecognised place in an intake
  question falls back to IJssel), so the confirmed recipe is the user's correction point.
- Map rendering is reused from the Scenario-engine (Deck.gl `H3HexagonLayer`) via an
  Open-in-engine handoff rather than duplicating the map in the chat panel.
- GreenPT extraction quality for free-text scenarios is validated in your env (key);
  the gate + run path are tested offline with the rule extractor and an injected fake LLM.

## Out of scope (later)
Phase 3 FAQ caching; Phase 4 declarative recipe-builder.
