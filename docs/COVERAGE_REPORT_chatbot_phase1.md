# Chatbot Phase 1 — coverage report

Maps the Kickoff Brief's Phase 1 scope to what shipped, with test evidence.
Status: **Implemented** · **Partial** · **Deferred** (by design, later phase).

## Verification snapshot
- `tests_chatbot`: **29 passed**.
- `tests_scenario`: **27 passed** (unchanged — no regression).
- assumption-source gate: **PASSED**.
- Corpus: **124 passages** (28 design-doc chunks, 75 dictionary, 6 assumptions,
  5 official positions, 10 FAQ folded in, 6 first-class caveats).

## Brief §2 — Chatbot scope
| Job | Status | Evidence |
|---|---|---|
| A. Answer about build/datasets/methodology in B1 Dutch, with citations | **Implemented** | `service.answer_question` → `compose_answer`; every answer carries `citations`. `test_answer.py`, `test_endpoint.py` |
| A. Explain a produced ScenarioCard | **Implemented** | `scenario_context.passages_from_card` + explain intent; cited by scenario hash + stable URL. `test_explain_scenario.py` |
| B. Run a scenario from free text | **Deferred (Phase 2)** | A run request is **routed** to the engine, never executed — `service._route_to_engine`. `test_intents.py::test_scenario_run_request` |
| C. Curated FAQs | **Implemented** | `faq.py` (10 entries) + `GET /api/chatbot/faqs`. `test_faq.py` |
| C. Caching of user questions | **Deferred (Phase 3)** | `faq_cache` (Postgres) is out of Phase 1 scope. |
| Hard boundary: no LLM code/SQL execution | **Implemented** | Read-only; LLM only maps to params/prose. No exec path exists. |
| No dead ends (clarify instead) | **Implemented** | Low idf-weighted coverage → `followup_nl`. `test_answer.py::test_offtopic_question_asks_clarifying_question` |

## Brief §5 — Phase 1 build plan
| Item | Status | Evidence |
|---|---|---|
| Assemble corpus (v3 doc + dictionary + assumption sources) | **Implemented** | `corpus.build_corpus`. `test_corpus.py::test_corpus_has_core_sources` |
| Index honest data caveats + surface on data/limits questions | **Implemented** | `_caveat_passages` (tagged `data_limits`) + `data_limits` intent boost. `test_corpus.py::test_caveats_are_first_class_and_tagged`, `test_answer.py::test_data_limits_answer_surfaces_caveat` |
| Retrieve step | **Implemented** | `retrieval.BM25Retriever` (Dutch stopwords + compounds). `test_retrieval.py` |
| Answer in B1 Dutch with citations via chat SSE | **Implemented** | `routers/chatbot.py` SSE; `answer.py` B1 prompt + extractive fallback. `test_endpoint.py` |
| Static Dutch FAQ registry | **Implemented** | `faq.FAQ_REGISTRY`. `test_faq.py` |

## Brief §6 — Open questions, resolved
1. **GreenPT embeddings?** Endpoint exists (`/v1/embeddings` → 401). Decision:
   **keyword BM25** primary for keyless/offline determinism; embeddings are a
   drop-in upgrade.
2. **FAQ moderation.** N/A in Phase 1 (static curated registry only); the
   suggested→reviewed→promoted flow is Phase 3.
3. **Chat UI location.** A new **Kennis-chat** tab beside the Scenario-engine
   toggle in `App.vue` (additive, mutually exclusive).
4. **Custom-scenario scope.** Confined to routing in Phase 1; engine execution is
   Phase 2 (levers/whitelist).
5. **Frontend build.** Ships as drop-in; `npm install` + `vite build` run in your
   environment (sandbox cannot build Vue/Deck.gl).

## Honest limitations of this phase
- GreenPT answer *quality* is not validated in-sandbox (no key); the wiring and
  the keyless fallback are tested, real generation is to be validated in your env.
- Retrieval is lexical (BM25); paraphrases with no shared/derivable terms fall to
  the clarifying-question path rather than guessing.
- The FAQ registry is hand-curated and static (no caching/promotion yet).
