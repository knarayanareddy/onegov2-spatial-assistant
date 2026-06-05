# Chatbot Phase 7 — coverage report (assumption versioning + calibration)

## Verification snapshot
- Full suite: **132 passed** (Phase 7 adds 9 scenario tests).
- assumption-source gate: **PASSED**.
- Calibration agreement on the real shipped data: **2/2 (100%)** — IJssel KNMI Hd→STOP 82,4, KNMI B→CAUTION 50,5 (matches design Part H).

## Gap F — assumption-library versioning
| Requirement | Status | Evidence |
|---|---|---|
| Versioned assumption library + changelog | **Implemented** | `assumptions.ASSUMPTIONS_VERSION` + `ASSUMPTIONS_CHANGELOG` + `assumption_library()`; `GET /api/assumptions`. `test_assumption_library_has_version_and_changelog` |
| Version stamped on card + citation | **Implemented** | `format_node` sets `assumptions_version`; `build_citation` "Aannameversie". `test_card_is_stamped_*`, `test_citation_includes_version_and_validation` |
| Reproduce-as-advised (drift on re-verify) | **Implemented** | `/verify` reports `assumption_drift` (cached vs current version). `test_verify_reports_assumption_version` |

## Gap E — calibration & validation status (honest)
| Requirement | Status | Evidence |
|---|---|---|
| Calibration harness vs reference cases | **Implemented** | `calibration.run_calibration` + `GET /api/scenario/calibration`; 2/2 agreement. `test_calibration_agrees_with_design_reference` |
| Validation status on card + citation | **Implemented** | `validation_status()` stamped on card + citation; ScenarioPanel "Herkomst & validatie" line. |
| Honest about external validation | **Implemented (by design)** | status states it is NOT validated against an external study; `kind` pluggable slot for real cases. `test_validation_status_is_honest`. See `docs/CALIBRATION.md`. |

## Honest scope
- Calibration = the design's own verified figures (consistency/reproducibility), **not** external validation — explicitly stated everywhere it appears. Real external validation is a drop-in data task (`kind="external-study"` cases).

## The six speculative gaps from the Phase-5 critique
A (auth/audit) ✅ · B (uncertainty band) ✅ · E (calibration/validation status) ✅ · F (assumption versioning) ✅ · C (data-refresh governance) and D (chat-session PII) remain — lighter, not yet built.
