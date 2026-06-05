# 🎭 Stakeholder Critique v2 — Drinkwaterzekerheid build (post-remediation re-assessment)

**Five voices. One tool. What got fixed, what still itches.**

> *Companion to [`initdoc/stakeholdercritique.md`](stakeholdercritique.md). That first critique read the **design document** and found 10 gaps. This v2 reads the **shipped build** — the scenario engine, the original descriptive Ruimtelijke Assistent, the data dictionary, the frontend, and the new GreenPT knowledge chatbot (Phases 1–4) — and re-scores every gap against what the code actually does. Grounded in the official [Challenge Brief](../CHALLENGE.md).*

**How to read this:** I step back into the shoes of each stakeholder named in the brief and re-run their critique against the current build. After each voice I mark the residual gaps. At the end: a gap-by-gap status table, a scorecard against the three pointers, and a mapping to the jury's Moet/Zou-moeten criteria.

**Status legend:** ✅ Fixed · 🟡 Partial · ⛔ Open

**The three overheard pointers (unchanged):**
- 🏚️ **Silo** — people work in isolation, no shared truth.
- 🪞 **Consistency** — the same query should give everyone the same answer.
- 👁️ **Intuition + transparency** — instantly understandable, every output self-explanatory, with sources.

---

## STAKEHOLDER 1 — PROVINCIAL POLICYMAKER
*"Ik ben beleidsmedewerker Ruimtelijke Ordening, Provincie Zuid-Holland."*
My job: I write adviezen for permit decisions and brief Provinciale Staten. I am not a hydrologist. I use Excel.

**What now works**
- ✅ **I can finally ask the tool what it knows — and get sourced answers.** The new Dutch knowledge chatbot (Kennisbasis-chat) answers "welke databronnen gebruikt het systeem?" or "wat zijn de beperkingen van de CBS-data?" in plain B1-Dutch, *with a Bronnen list and clickable links*, and foregrounds the honest data caveats instead of overstating them. This was my #1 ask in v1 (the "Wat weet dit systeem?" gap).
- ✅ **Citation I can defend in an advies.** Every scenario produces an APA-style Dutch citation plus a metadata block — Scenario-ID, scenario-hash, generation date, software git-commit, dataset versions, stable URL — and a one-click PDF adviesnota (`/api/scenario/{id}/citation`, `/api/scenario/{id}/pdf`). If my advice is challenged, I can show exactly which calculation, on which data version, produced the number.
- ✅ **Plain-language verdict first.** Every scenario opens with a GO / CAUTION / STOP banner ("HAALBAAR / RISICO / NIET HAALBAAR") before any number.
- ✅ **Official policy is attached.** Each scenario links the relevant Waterprogramma / KNMI'23 / KRW documents with a "dit is een beleidsmatige verkenning, geen besluit" disclaimer.

**What still itches**
- 🟡 **A permanent "Kennisbasis" panel with freshness dates.** The knowledge is now *queryable* and *sourced*, but there is no always-visible catalogue panel listing each dataset with a publication date and a freshness indicator. I have to ask; I can't glance.
- 🟡 **A scenario *library* I can browse.** Stable shareable URLs exist (the silo-breaker), but there's no "Opgeslagen Scenario's" list where my water colleague and I can see we opened the *same* saved calculation.

---

## STAKEHOLDER 2 — SPATIAL PLANNER (Gemeente / Omgevingsdienst)
*"Ik toets ruimtelijke plannen op haalbaarheid."*
My job: 200+ permit reviews open at once. I need fast, defensible answers.

**What now works**
- ✅ **One-second GO/CAUTION/STOP** on every project scenario, with the share of "niet-haalbaar" cells.
- ✅ **"Make this plan feasible" is built in.** For any non-green result the engine re-scores a catalogue of interventions on the real data and ranks them by how much they cut the STOP-share, each with a source link — surfaced on screen and in the PDF as "Wat maakt dit haalbaarder?".
- ✅ **What-if sliders + a recipe-builder.** I can nudge the assumptions (KNMI dryness, the signal weights) and the scenario re-runs; the Phase-4 recipe-builder lets me compose a weighted multi-layer recipe (validated, never free-form code).

**What still itches**
- ⛔ **Cumulative effect — still the biggest practical gap.** The tool assesses one plan at a time. There is a with/without-shock *comparison* and an "added homes" demand lever, but I still cannot drop several concurrent projects on the map and see their *combined* load on a zone. I am the fifth reviewer for this zone this year and the tool doesn't know about the four plans before mine.
- ⛔ **No "al vergund / in behandeling" demand layer.** Residual capacity still doesn't net out already-approved permits. (Honest reason: the `productieketen` operational dataset ships empty, so there is no committed-demand data to net against — the build flags this rather than inventing it.)

---

## STAKEHOLDER 3 — WATER AUTHORITY (Dunea / Evides / Oasen)
*"Ik ben capaciteitsplanner."* Engineering + hydrology background.

**What now works**
- ✅ **Per-intake chloride threshold — mechanism fixed.** The threshold is no longer a hard global constant: the engine looks it up per intake from the production chain and, when absent, falls back to the Drinkwaterbesluit value (150 mg/L, band 150–250) *explicitly labelled as a sourced assumption*, never silently.
- ✅ **Determinism I can rely on for a dispute.** A scenario's parameters + assumption overrides hash to a stable ID; the result is cached; the dataset versions used are recorded; the arithmetic is deterministic and the LLM runs at temperature 0. If a developer and I run the same parameters, we get the same answer — and I can point to the hash.
- ✅ **Honest about the salinity signal.** The build states plainly that `verzilting.ZOUT_CONC` ships as a single saturated class, so salinity acts as a *mask* amplified by the KNMI dryness knob — not a precise mg/L field.

**What still itches**
- 🟡 **Live Waterinfo chloride is still not mandatory.** For IJssel/Lek/Maas intake scenarios the engine uses the verzilting class with a labelled fallback, not the live RWS Waterinfo feed. Graceful and honest — but for an authority the live signal is the core input.
- 🟡 **Per-intake thresholds are mechanism-only until the data lands.** Because `productieketen` is empty, every intake currently resolves to the same labelled fallback. Correct by design; not yet differentiated in practice.
- ⛔ **No production-chain *flow* view.** Intake → productie → distributie is still not drawn as a directed flow graph.

---

## STAKEHOLDER 4 — PROJECT DEVELOPER (Data Centre / Housing)
*"Ik wil weten of mijn project water krijgt."* Business Dutch, no water expertise.

**What now works**
- ✅ **Numbers I can feel.** Headline metrics carry a plain-Dutch human-scale analogy (VEWIN-sourced) — e.g. STOP-area expressed as "≈ N km² met hoge drinkwaterdruk" — so I'm not staring at a bare "m³/dag".
- ✅ **The feasibility traffic light + the "make it feasible" options** are exactly the decision support I need before buying land.
- ✅ **A stable, shareable scenario URL** I can paste into a financing memo.

**What still itches**
- ⛔ **I still can't see if another developer already claimed the headroom.** Same root cause as the planner's cumulative gap — two developers asking about the same zone both get "green" because no shared cumulative layer nets their plans together. For a financial decision this is the one I'd most want closed.

---

## STAKEHOLDER 5 — GENERAL PUBLIC / CITIZEN
*"Ik woon in Zoetermeer en wil weten of mijn drinkwater veilig is in 2040."*

**What now works**
- ✅ **A real citizen answer format.** Ask in citizen language (or give a postcode) and the tool replies verdict-first, jargon-free, under ~100 words: "Op dit moment lijkt je drinkwater veilig… dit gaat over de regio, niet over jouw kraan thuis," names your water company (Dunea / Evides / Oasen) with phone + link, and points to the official policy — with a "dit is een verkenning, geen meting" disclaimer.
- ✅ **It matches the official line.** Because every output is anchored to the published Waterprogramma / KNMI position, the tool won't quietly contradict what I read in a provincial press release.

**What still itches**
- 🟡 **The citizen path lives in the engine, not yet as a front-door.** The verdict-first citizen response is generated (and there's a postcode detector), but a citizen still meets a professional-looking app first; a dedicated "burger" landing view would close the loop.

---

## THE 10 GAPS — STATUS TABLE

| # | Gap (from v1) | Status | Evidence in the build |
|---|---|---|---|
| 1 | "What does this system know?" / Kennisbasis | 🟡 mostly | Knowledge chatbot answers data/methodology questions **with sourced citations** + a data-limits intent; `/api/dictionary` exists. Residual: no always-visible freshness *panel*. |
| 2 | Shared scenario library + stable URL + same-answer + dataset version | ✅ spine / 🟡 UI | `GET /api/scenario/{id}` stable URL, `scenario_hash`, `dataset_versions`, drift detection, temp-0 engine, ScenarioStore. Residual: browse-list UI + a `/verify` endpoint. |
| 3 | Formal citation / export metadata | ✅ Fixed | `build_citation` (APA + ID + hash + git commit + versions + URL) and a PDF adviesnota. |
| 4 | Human-scale contextualisation | ✅ Fixed | `human_scale` analogies in the card, the PDF and citizen mode. |
| 5 | "Make this feasible" recommendation flow | ✅ Fixed | Interventions re-scored on real data, ranked by STOP-share reduction, each sourced. |
| 6 | Cumulative / stacking effect + "al vergund" layer | ⛔ Open | Comparison + added-homes lever exist; **no multi-project overlay, no committed-demand layer**. |
| 7 | Per-location chloride threshold | ✅ mechanism | Per-intake lookup + sourced 150 mg/L fallback flagged as an assumption (data ships empty). |
| 8 | "What does the government say?" panel | ✅ Fixed | Official-positions registry with links + disclaimer on every scenario; in the chatbot corpus. |
| 9 | Waterinfo chloride live/mandatory | 🟡 Partial | Verzilting-class fallback, labelled, never silent; live RWS feed not wired. |
| 10 | Citizen response format | ✅ Fixed | `citizen.py`: verdict-first, postcode, water company, official links, disclaimer. |

**Tally: 6 Fixed · 3 Partial · 1 Open** (plus the headline cross-cutting capability below).

---

## THE THREE POINTERS — SCORECARD

| Pointer | Verdict | Why |
|---|---|---|
| 🏚️ **Silo** | **Largely closed** | Stable scenario URLs + reproducible hash + a shared knowledge chatbot that gives *everyone the same sourced answer*. Residual: cumulative multi-project overlay, "al vergund" layer, and an org scenario-library UI. |
| 🪞 **Consistency** | **Strong, with one honest tier** | **Hard-deterministic** for scenarios (hash + cache + dataset version + temperature-0 arithmetic); **strong** for the knowledge chatbot (temp-0 + deterministic keyword retrieval + a keyless deterministic fallback + a versioned answer cache). **Weaker** only for the *legacy* descriptive SQL prose, which is generative and not temp-0-pinned. |
| 👁️ **Intuition + transparency** | **Strong** | GO/CAUTION/STOP first, an Insight reasoning trail, human-scale analogies, official-policy links, citizen mode, **chatbot answers with clickable sources**, and a PDF adviesnota. Residual: a permanent plain-language *map title* line (the colour legend is always visible, but not a "this map shows…" caption), a browseable Kennisbasis/freshness panel, and **bringing source-citations to the descriptive SQL answers** (today they're prose-only). |

**Headline requirement — "query any aspect and get relevant information with sourced hyperlinks":** ✅ **Delivered** by the Phase-1 knowledge chatbot (a corpus over the design doc, the data dictionary, the sourced assumptions and the honest caveats; B1-Dutch answers that always carry citations; a clarifying question when confidence is low). **One caveat:** the build now has *two* query surfaces — the new chatbot (sourced) and the original descriptive SQL assistant (prose, **not** yet citing sources). Unifying citations across both is the cleanest next step.

---

## MAPPING TO THE JURY'S CRITERIA (CHALLENGE.md)

- **Moet (Must):** ✅ All met — works on the supplied data; answers exploratory what-if questions combining ≥2 themes (verzilting × CBS × zes-uurszones); open-source with READMEs; the original descriptive flow still works untouched.
- **Zou moeten (Should):** ✅ Two+ scenarios and a with/without-shock comparison run end-to-end; ✅ uncertainty/assumptions/time-horizon shown explicitly; ✅ ambiguous input gets a clarifying question (both in the scenario engine and the chatbot). 🟡 *Navolgbaar*: the in-app Insight trail + chatbot citations are done; **MLflow scenario tracing is still deferred**.
- **Zou niet (Should not):** ✅ Respected — the LangGraph/DuckDB/frontend architecture was *extended, not rebuilt*; the reasoning chain is never hidden behind a single answer.
- **Kan (Could):** ✅ A dedicated scenario node composing shocks; ✅ a sliders/presets UI (the recipe-builder). 🟡 Explicit FDS/NORA alignment not yet documented.

*(The project's own v3 re-grade scored 34/46 implemented before the chatbot existed; the chatbot advances Gap 1 and the headline "query-anything-with-sources" capability beyond that grade.)*

---

## CONSOLIDATED RESIDUAL GAPS (prioritised)

1. ⛔ **Cumulative / multi-project overlay + "al vergund" layer** — the deepest remaining silo gap; affects planner, developer and water authority. (Needs a committed-demand data source.)
2. 🟡 **Bring source-citations to the descriptive SQL assistant** — so *every* query surface, not just the new chatbot, answers with hyperlinks. Highest-leverage transparency fix.
3. 🟡 **Live Waterinfo (RWS) chloride** for IJssel/Lek/Maas intake scenarios — mandatory with an explicit "laatste bekende waarde van [datum]" warning on failure.
4. 🟡 **Always-visible Kennisbasis + freshness panel** and a **permanent plain-language map title** — finish the "glanceable" half of the intuition pointer.
5. 🟡 **MLflow scenario tracing** — closes the last "navolgbaar" axis for the jury.
6. 🟡 **Shared scenario-library UI + `/verify` re-run** — turn the existing stable URLs into a browseable, re-verifiable institutional library.

## VERDICT
The remediation landed. Of the 10 v1 gaps, **6 are fully fixed, 3 partial, 1 open**, and the headline "ask anything, get sourced answers" requirement is now real through the knowledge chatbot. The three pointers are largely satisfied — silos broken by shared, reproducible, sourced outputs; consistency hard-guaranteed for scenarios; transparency strong end-to-end. What remains is **additive, not corrective**: the cumulative-effect overlay (data-dependent), citations on the legacy SQL path, live Waterinfo, MLflow tracing, and a few glanceable UI panels. For a non-technical policy audience the tool is now legible, defensible and citeable; the open items are about *breadth of coverage*, not trust in what it already shows.
