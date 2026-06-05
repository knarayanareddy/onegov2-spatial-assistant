# 🔧 Phase 5 — Remediation + a fresh policymaker critique

**Part A closes the six prioritised residual gaps from [`stakeholdercritique_v2.md`](stakeholdercritique_v2.md). Part B puts the policymaker hat back on and speculates on the glaring gaps that *remain* — the ones nobody has listed yet.**

Verification legend: ✅ **built & tested in-sandbox** · 🧩 **drop-in frontend** (build in your env) · 🌐 **activated in your env** (live service the sandbox can't reach).

---

## PART A — the six residuals, closed

### 1. Cumulative / multi-project overlay + "al vergund" layer ✅ 🧩
- **Backend:** `app/services/scenario/cumulative.py` + `POST /api/scenario/cumulative`. Stacks several project demands (woningen / datacentre-MW / raw m³/day, all converted to an *added-households* equivalent) plus an operator-entered **"al vergund / in behandeling"** committed-demand list, scores the combined load on the populated universe, and returns each project's marginal-alone verdict, the combined verdict, and a **stapelingseffect** narrative that flags when individually-passing plans fail together.
- **Honest scope:** no permit dataset ships (productieketen is empty), so the committed layer is **operator/manual entry**, clearly labelled and ready for an OLO koppeling. Not invented data.
- **Frontend:** `CumulativePanel.vue` (add projects + committed rows → combined verdict + breakdown).
- **Tests:** validation, homes-equivalent conversion, a real stacked run, the endpoint.

### 2. Citations on the descriptive SQL assistant ✅ 🧩
- **Backend:** `app/services/data_sources.py` (a dataset→publisher/URL registry) + `app/services/nodes/cite_sources.py`, an **append-only** LangGraph node (`describe_results → cite_sources → END`) that maps the tables the generated SQL touched to sourced hyperlinks and emits a `sources_block` event (mapped to a `sources` SSE event in the chat router). The descriptive flow now answers with **Bronnen**, like the knowledge chatbot — without rewriting the workflow (honors "Zou niet").
- **Tests:** SQL→sources mapping, http-link discipline, empty-SQL safety.

### 3. Live RWS Waterinfo chloride for IJssel/Lek/Maas ✅ 🌐
- **Backend:** `app/services/scenario/waterinfo.py` — a mandatory chloride lookup for intake scenarios. Live RWS feed when `WATERINFO_LIVE=true`; otherwise (and on any failure/staleness) the **last-known value with an explicit "laatste bekende waarde van [datum]" warning** and a source link — *never silent*. Emitted as a `waterinfo` SSE event on intake runs; also `GET /api/scenario/waterinfo/{intake}`.
- **Honest scope:** the sandbox can't reach the RWS service, so the live path is exercised with an injected fake; the labelled fallback is the default and is fully tested. Set `WATERINFO_LIVE=true` in your env for live values.

### 4. Always-visible Kennisbasis + freshness + permanent map title ✅ 🧩
- **Backend:** `GET /api/kennisbasis` — every loaded theme, its tables (column count, **freshness date** from the parquet mtime, an "empty" flag), publisher and source link.
- **Frontend:** `KennisbasisPanel.vue` (the always-accessible "Wat weet dit systeem?" inventory) + a **permanent plain-language map-title caption** in `ScenarioPanel.vue` ("Kaart toont: DrinkwaterDruk per H3-cel — oordeel: …").
- **Tests:** the inventory endpoint (sources + freshness + columns).

### 5. MLflow scenario tracing ✅ 🌐
- **Backend:** `app/services/scenario/tracing.py` — guarded MLflow spans around `run_scenario` / `run_comparison`, tagged with params/hash/verdict. **No-op when `MLFLOW_ENABLED` is false** (the default), so tests and keyless runs are untouched; traces appear in your MLflow UI when enabled. Closes the Should "navolgbaar" MLflow axis.
- **Tests:** the span is a verified no-op when disabled.

### 6. Shared scenario-library UI + `/verify` re-run ✅ 🧩
- **Backend:** `GET /api/scenario` (the saved-scenario library, most recent first, with stable URLs) + `GET /api/scenario/{id}/verify` (re-runs the scenario on **current** data, compares verdict/score/hash, and reports dataset-version drift). Persistence now records real **dataset versions** (parquet mtimes) so drift/verify are meaningful.
- **Frontend:** `ScenarioLibrary.vue` (browse + a "Verifieer berekening" button).
- **Tests:** list + verify (match + no-drift on unchanged data).

**Result:** the three Partial gaps and the one Open gap are addressed; backend is tested (**113 tests pass**, source gate green), frontend ships drop-in, and the two live services activate via one env flag each.

---

## PART B — a fresh policymaker critique: the gaps nobody has listed yet

*"Ik ben beleidsmedewerker. The tool is now genuinely good — legible, sourced, reproducible. So let me be the awkward voice in the room and ask the questions that will come up the first time this is used for a real advies."*

### 🔴 GAP A — Nobody can prove *who* ran this (the Woo / accountability gap)
There is no real authentication: the user is a stub ("local-user"), and nothing records **who** ran a scenario or **who** changed an assumption. The moment an output lands in an official advies, the Wet open overheid and basic accountability require a human-attributable trail: which civil servant, which version, which inputs. **The tool has perfect *calculation* provenance and zero *human* provenance.** This is the single biggest production blocker — more than any data gap.
*Fix direction:* real SSO (the province's identity provider), a per-user action log (ran / shared / promoted / overrode), and the user identity stamped into the citation block.

### 🟠 GAP B — A single number where there should be a confidence band (false precision)
The verdict is a point estimate: "STOP at 66.1" and "CAUTION at 65.9" look identical to the model but flip the advice. Yet the assumptions *carry ranges* (chloride 150–250, demand 0.10–0.14, growth 0.04–0.12). A policymaker who defends a STOP must answer "how robust is that?" — and today the tool can't say. **Uncertainty is shown for inputs but not for the output.**
*Fix direction:* sweep the assumption ranges and the four KNMI scenarios and report robustness — "STOP in 3 of 4 klimaatscenario's; CAUTION onder Ln/Hn" — and a verdict that only commits when the band is one-sided.

### 🟠 GAP C — Who keeps the data fresh? (no staleness governance)
The build now *detects* drift and shows freshness dates — good. But there is no **process**: no refresh SLA, no owner, no "data is X months oud" banner that escalates. A 2022 dataset silently underpinning a 2026 advies is a credibility risk even when the date is technically visible.
*Fix direction:* a per-dataset refresh owner + SLA, a staleness banner ("verzilting is 18 maanden oud — actualiseer vóór formeel gebruik"), and a scheduled refresh job.

### 🟡 GAP D — Privacy asymmetry: the chat remembers everything
Phase 3 carefully anonymises PII before caching FAQs — but the **descriptive chat sessions store raw user questions in Postgres** (a citizen typing a postcode or address), with no anonymisation or retention policy. The careful door is locked while the window is open. AVG/GDPR exposure.
*Fix direction:* anonymise-on-write for session storage too, a retention window, and a "geen persoonsgegevens invoeren" notice on the citizen path.

### 🟡 GAP E — The model has never been checked against reality
Every number is an *assumption-driven composite*. It is sourced and reproducible — but it has **never been validated against an actual Dunea/Evides capacity forecast or a published drinkwater study**. The disclaimer says "verkenning, geen besluit" (good), yet a jury or a director will ask: "has this verdict ever matched a real assessment?" Without a calibration story, the tool risks being *confidently wrong*.
*Fix direction:* a calibration appendix — run the engine against one or two historical/known cases and report agreement; state the validation status on the scenario card.

### 🟡 GAP F — Assumptions change; old adviezen shouldn't silently change with them
Assumptions are sourced *today*. But when the weights or thresholds are revised next quarter, re-opening a 2-year-old scenario URL may now compute a **different** verdict — and the old advies cited the old model. The `scenario_hash` pins parameters, not the assumption *library version*.
*Fix direction:* version the assumption library (a methodology changelog + an `assumptions_version` stamped in the citation), so "reproduce exactly as advised on [date]" is possible.

### Honourable mentions
- **WCAG/accessibility** isn't asserted for the citizen path (verdicts use colour *and* text — good — but no conformance statement or screen-reader audit).
- **LLM cost / rate-limit / abuse controls** aren't visible — an operational concern for a public-facing tool.

### The one-line summary for the steering group
> The tool has crossed the line from "interesting prototype" to "defensible instrument" — but **three things still stand between it and a real advies: a human accountability trail (who), an uncertainty band (how sure), and a calibration story (is it right).** Those, not more features, are the next milestone.
