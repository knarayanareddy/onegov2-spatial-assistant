# Chatbot Phase 6 — coverage report (accountability + uncertainty)

## Verification snapshot
- Full suite: **123 passed** (Phase 6 adds 10 scenario tests + 1 SQLite audit-adapter test).
- assumption-source gate: **PASSED**.
- JWT verified with a minted HS256 token; audit adapter verified on SQLite; uncertainty swept on the real shipped data.

## Gap A — real auth + audit trail
| Requirement | Status | Evidence |
|---|---|---|
| Real (configurable) authentication, not a stub | **Implemented** | `auth.py` AUTH_MODE dev/jwt/header; `_from_jwt` HS256+RS256/JWKS. `test_jwt_maps_claims_to_user_and_roles` |
| Reject unauthenticated when required | **Implemented** | `AUTH_REQUIRED` → 401 on missing/invalid token. `test_auth_required_rejects_missing_and_invalid_token` |
| Roles / admin-only moderation | **Implemented** | `require_role`; FAQ promote/reject admin-gated. `test_moderation_requires_admin_role` |
| Audit trail (who did what) | **Implemented** | `audit.py` + `record_audit`; scenario run/cumulative/verify/uncertainty + recipe + FAQ moderation logged; `GET /api/audit`. `test_scenario_run_is_audited_with_the_user` |
| Human identity in the citation | **Implemented** | `run_by` stamped into the card + `build_citation` "Uitgevoerd door". `test_citation_includes_uitgevoerd_door` |
| Persistent audit store | **Implemented / SQLite-verified** | SQLModel `AuditLog` + `SqlAuditStore` + Alembic `c3d4e5f6a7b8`. `test_sql_audit_record_and_filter` |
| Live SSO | **Your env** | point `AUTH_JWT_*`/`AUTH_HEADER_*` at Keycloak/Azure AD (verified here with a minted token). |

## Gap B — uncertainty band
| Requirement | Status | Evidence |
|---|---|---|
| Output confidence, not just a point estimate | **Implemented** | `uncertainty.run_uncertainty` sweeps 5 KNMI presets → score band + verdict distribution + robust/knife-edge. `test_uncertainty_sweep_on_real_data` |
| Surfaced to the user | **Implemented** | `POST /api/scenario/uncertainty` + a robustness line on the ScenarioPanel verdict. `test_uncertainty_endpoint` |

## Honest scope
- No live IdP / MLflow / Postgres in the sandbox: auth verified via minted token, audit via SQLite, MLflow no-op; all activate via env config. Default behaviour unchanged unless `AUTH_MODE`/`AUTH_REQUIRED`/`AUDIT_BACKEND` are set.
- Uncertainty axis = the five KNMI presets (the jury-relevant axis); an assumption-range low/mid/high sweep can be layered on later.

## Remaining speculative gaps (not in this pack)
C data-refresh governance · D chat-session PII/retention · E calibration vs an official study · F assumption-library versioning.
