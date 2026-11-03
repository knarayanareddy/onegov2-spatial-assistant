# OneGov — remediation plan

All work below is proposed, not performed. Preserve existing thresholds and separate synthetic from real data. Entry to implementation requires owner approval for identity and data access; independent acceptance follows all phases.

## Phases and tasks

### P0: Baseline and identity contract
**Exit:** reproduction report distinguishes local and production modes. **OG-T1** (OG-1, OG-3; prerequisites: authorized test environment and owner identity contract; observed `src/backend/app/auth.py`, `.github/workflows/ci.yml`).
1. Inventory configuration and every route using `get_current_user`, `require_role`, and `require_session_access`; document gaps without assuming helpers are universally applied.
2. Reproduce dev, header and JWT modes with synthetic users, missing credentials, malformed tokens, incorrect issuer/audience and cross-user session IDs.
3. Record approved IdP issuer, audience, algorithms, role mapping, proxy strip rules and separate local-only behavior; secure a maintainer decision on whether anonymous access exists.
Deliverable: reproducible access matrix. Verify with route-level HTTP responses and actor identities, not helper calls alone. DoD: [ ] routes inventoried; [ ] negative cases reproduce; [ ] owner signs identity contract.

### P1: Correct identity and authorization
**Exit:** no protected route can obtain an admin via fallback. **OG-T2** (OG-1/OG-3; after T1; observed `src/backend/app/auth.py`, proposed route integration tests under `src/backend/tests/`).
1. Restrict local admin identity to an explicit local mode and reject unsafe production combinations at startup; do not silently grant admin on authentication failure.
2. Validate configured token issuer, audience, stable subject, expiry and selected algorithm; constrain trusted-header mode to a proxy-protected network with stripped inbound headers.
3. Exercise protected routes for owner/non-owner, non-admin/admin, missing, invalid, expired, wrong-audience and spoofed-header requests; test configured anonymous routes separately.
Deliverable: enforced policy and regression suite. Verify with independently minted test credentials and a live test proxy; intentionally restore fallback or bypass audience validation and require the corresponding tests to fail. DoD: [ ] fail-closed tests pass; [ ] privilege and tenant isolation observed; [ ] mutation detected.

### P2: Persistence and operational recovery
**Exit:** durable audit behavior and degraded states are observable. **OG-T3** (OG-2; after T1; observed `src/backend/app/main.py`, `docker-compose.yml`; proposed production configuration/runbook).
1. Define whether audit failure blocks startup or denies affected operations; distinguish a deliberately ephemeral local environment.
2. Implement and test readiness and error reporting for configured FAQ/audit stores, including failures at first use, not only constructor failures.
3. In a permitted isolated database, test migration, restart, encrypted backup and restoration; compare audit records and document recovery time and missed-write behavior.
Deliverable: operational policy and restore record. Verify by disconnecting the database and checking readiness, responses and restored records. DoD: [ ] degraded behavior matches policy; [ ] restore observed; [ ] credentials are not in logs or backup reports.

### P3: Meaningful gates and user acceptance
**Exit:** required gates and domain review cover actual risks. **OG-T4** (OG-4; preventive injection, dependency and accessibility requirements; after T2 and T3; observed `.github/workflows/ci.yml`, `src/backend/tests/unit/test_auth.py`, `src/frontend/package.json`).
1. Decide whether `src/backend/tests/unit/test_auth.py` remains the intended auth-unit entry point; if yes, update it to match the sampled `get_current_user(request: Request)` signature and add negative auth cases, and if no, replace it with the maintained auth regression path and document the supersession.
2. Add explicit backend authentication and route integration coverage to CI so the chosen auth regression path runs in a required gate alongside the existing assumption-source check, `tests_scenario`, `tests_chatbot`, and frontend build; define any new test scripts rather than claiming they already exist.
3. Trace generated SQL and retrieved text to their trust boundaries; add adversarial input, prompt-injection, and unauthorized-object tests, alongside dependency lock/integrity and secret checks.
4. Test keyboard, screen-reader, map alternative, and uncertainty/source display with representative Dutch users; domain experts compare outputs to approved reference cases.
Deliverable: required gate and acceptance evidence, including an explicit auth regression path bound to the CI scope. Verify by deliberately breaking an access check and the sampled auth regression path, then requiring the corresponding gate to fail; manually record user and expert observations. DoD: [ ] stale or superseded auth-unit path resolved; [ ] required CI auth regression gate added; [ ] regression failure demonstration recorded; [ ] provenance and uncertainty validated; [ ] accessibility issues triaged.

## Dependencies and acceptance
T1 → T2 → T4; T1 → T3 → T4. Independent reviewer must inspect actual deployed configuration, identity proxy, and test evidence, then observe smoke tests and a restore.

| Task | Depends on | Enables |
| --- | --- | --- |
| OG-T1 | Owner identity contract and authorized test environment | OG-T2, OG-T3 |
| OG-T2 | OG-T1 | OG-T4 auth policy and negative controls |
| OG-T3 | OG-T1 | OG-T4 operational gate/restore evidence |
| OG-T4 | OG-T2, OG-T3 | Release-candidate acceptance review |

Production acceptance: [ ] no admin fallback; [ ] issuer/audience and session isolation enforced; [ ] audit persistence and recovery observed; [ ] auth regression path tied to required CI scope and release SHA; [ ] SQL/injection boundaries assessed; [ ] domain and accessibility reviews signed.

Owner approval is required for identity integration, real data, production infrastructure, retention, migration and release. Release only a reviewed immutable artifact; retain prior version and schema-compatible rollback, with a tested restore path for incompatible migrations. Stop rollout on authorization or audit failure; never treat rollback as a substitute for restoring lost records.
