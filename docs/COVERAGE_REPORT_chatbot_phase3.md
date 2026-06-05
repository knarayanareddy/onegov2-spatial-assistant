# Chatbot Phase 3 — coverage report (FAQ caching + ranking)

Maps the Kickoff Brief's Phase 3 to what shipped, with test evidence.

## Verification snapshot
- `tests_chatbot`: **58 passed** (29 Phase 1 + 11 Phase 2 + 18 Phase 3).
- `tests_scenario`: **27 passed** (no regression).
- assumption-source gate: **PASSED**.
- Store: in-memory (tested in-sandbox) + SQLModel/Postgres adapter & Alembic migration
  (import/compile-verified; validate against your DB — the sandbox can't run Postgres).

## Brief §5 Phase 3 + §4 cache reuse
| Requirement | Status | Evidence |
|---|---|---|
| faq_cache (question_norm, key, answer_nl, sources, hits, dataset_versions) | **Implemented** | `FaqCacheEntry` + `FaqCache` SQLModel table; `version_stamp` = git+corpus. `test_faq_cache.py` |
| Embedding-or-keyword key | **Implemented (keyword)** | `make_cache_key` — order-insensitive token signature (retrieval is BM25, not embeddings). `test_cache_key_collapses_paraphrase_and_strips_pii` |
| Surface top-N as veelgestelde vragen | **Implemented** | `GET /api/chatbot/faqs` = curated + published ranked by hits. `test_endpoint_capture_moderate_and_serve`, `test_published_ranked_by_hits` |
| Cache user questions | **Implemented** | `capture_answer` after a confident, cited answer (best-effort). `test_capture_dedups_and_counts_hits` |
| Invalidation on data/doc change | **Implemented** | `version_stamp` stale-filtering, mirroring scenario `detect_version_drift`. `test_stale_stamp_is_filtered` |
| Anonymise postcodes/PII before caching | **Implemented** | `pii.anonymize_pii` (postcode/e-mail/phone) applied in key + display. `test_pii.py`, `test_pii_in_question_is_anonymised_before_storage` |
| Cache invalidation tied to dataset_versions/git_commit | **Implemented** | `version_stamp = hash(git_commit + corpus_signature)`. |

## Brief §6 open Q2 — moderation policy
| Item | Status | Evidence |
|---|---|---|
| Auto-cache user Q&A as 'suggested' only | **Implemented** | new entries are `status="suggested"`. `test_promote_then_published_and_ranked` |
| Grounded-with-sources check before promotion | **Implemented** | `is_grounded` re-check in `promote`. `test_rejected_entry_is_not_promotable` (and not_grounded path) |
| Light human review before public | **Implemented** | auth-gated `promote`/`reject` endpoints. `test_endpoint_*` |
| Who reviews | **Decision** | repo auth is a single-user stub (`get_current_user`); the logged-in user reviews. Restrict to an admin role in your env (documented hook). |

## Storage / safety notes
- Default = in-memory store (zero-infra, tested, graceful no-Postgres fallback). Production
  = `SqlFaqCache` over the shared sessions Postgres (`alembic upgrade head` + `set_store(...)`).
- PII is stripped before the question enters the cache key OR the stored display text — so the
  cache cannot leak postcodes/e-mail/phone.
- A rejected suggestion can never be promoted; capture won't resurrect a rejected entry's content.

## Out of scope (later)
Phase 4 — declarative recipe-builder (whitelisted H3 layer combinations + weights, validated, not code).
