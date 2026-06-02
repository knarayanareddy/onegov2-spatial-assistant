# Challenge Brief | Drinkwaterzekerheid

> **OneGov #2** · Provincie Zuid-Holland · 4 and 5 June 2026 · The Hague Tech
>
> *From descriptive analysis to exploratory what-if scenarios for the drinking-water supply of Zuid-Holland in 2040.*
>
> **Challenge owners:** Sebastiaan Schmidt, Tim Padmos, Thijs Raterink (Provincie Zuid-Holland)
> **Contact:** [hack@govtechnl.nl](mailto:hack@govtechnl.nl)

This is an English working translation of the original Dutch challenge brief. The authoritative source is the PDF at the root of this repository: [OneGov_2_Challenge_Brief_Drinkwaterzekerheid.pdf](OneGov_2_Challenge_Brief_Drinkwaterzekerheid.pdf).

---

## Background

Provincie Zuid-Holland (PZH) is responsible for the policy framework around the drinking-water supply: protecting *intrekgebieden* (capture zones around abstraction points), monitoring water quality, and steering policy in the face of climate change, salinisation (*verzilting*), changing legislation, and population growth. PZH already runs a working **Ruimtelijke Assistent**: a Dutch-language chat tool that answers questions about spatial datasets, organised in H3 hexagons, by translating natural language into DuckDB SQL and rendering the result as text plus an interactive map. That assistant is forked into this repository as the starting point.

What the assistant does well today is **descriptive**: "how many X are in area Y?". What the drinking-water question requires is **exploratory**: combining multiple data themes to answer what-if questions about 2040.

## The challenge

> *Hoe zeker is de drinkwatervoorziening van Zuid-Holland in 2040, en welke combinatie van klimaatdruk, regelgeving en bevolkingsgroei vormt het grootste risico of biedt juist kansen voor een robuustere watervoorziening?*

Translated: *How secure is the drinking-water supply of Zuid-Holland in 2040, and which combination of climate pressure, regulation, and population growth poses the biggest risk, or offers the biggest opportunity, for a more robust water supply?*

Teams take the working spatial assistant and extend it from descriptive questions to exploratory, multi-theme, what-if scenarios. Three guiding example scenarios are listed in [docs/example-scenarios.md](docs/example-scenarios.md); challenge owners will add more on or before the hackathon.

## Data themes

Two primary data themes are loaded by default from `src/backend/data/`:

1. **drinkwaterzekerheid.** Drinking-water infrastructure, drinking-water production chain, drinking-water companies, *toestandsbeoordeling oppervlaktewaterlichamen*, water boards, and the six-hour zones around abstraction points.
2. **gebiedsviewer.** Around 50 provincial layers, including verzilting, bodemdaling, *overstromingskwetsbaarheid*, *groenblauwe ruimte*, *natuurnetwerk*, nutrient-polluted areas, soil stability, and other soil data.

Optional extra themes are available in `src/backend/extra_data/`:

- **lgn.** Land-use rasters (*Landgebruik Nederland*), 2018 through 2022. Not directly tied to the drinkwater question, but useful for scenarios that hinge on land-use change.
- **CBS** vierkantstatistieken 2018 through 2023.
- **Woondeals** umbrella, which in this repository also bundles **PMIEK** projects, **stikstof** depositions and KDW exceedance, **air quality** (CIMLK 2025 baselines and 2030 projections), **traffic intensity** measurements, and OV stop locations.

A precise per-table inventory, with an indication of what is loaded by default and what still needs to be confirmed by the challenge owners, is in [docs/data-inventory.md](docs/data-inventory.md).

## Working method

Use the working assistant as a starting point. Do not rebuild the architecture. Extend it where it matters for drinkwaterzekerheid, for example by:

- Combining themes in a single question (drinkwaterzekerheid plus verzilting plus CBS population growth).
- Adding what-if filters or scenario parameters to the LangGraph workflow.
- Adding new datasets in `src/backend/extra_data/` and registering them, while accepting that extra column names in the prompts may slightly reduce model accuracy.
- Tightening prompts or adding follow-up questions for ambiguous scenario inputs.

The Insight panel in the running app and the **MLflow** trace at [http://localhost:5001](http://localhost:5001) expose every step of the reasoning chain. That same chain is the most direct way to satisfy the Should criterion below that the prototype's reasoning is *navolgbaar vastgelegd*.

## Judging criteria

### Moet (Must): minimum requirements for a valid submission

- The prototype demonstrably works on the supplied data (or a self-composed variant in the same shape).
- The prototype answers at least one **exploratory, what-if** question that combines two or more data themes (for example drinkwaterzekerheid plus verzilting, or drinkwaterzekerheid plus CBS bevolking).
- The solution is open source and ships with a readable README that explains how the prototype works and how it can be extended.

### Zou moeten (Should): distinguishing qualities

- The prototype answers at least two scenarios or comparisons end-to-end, both visible in a demo.
- The reasoning chain is *navolgbaar vastgelegd*: visible in the in-app Insight panel and traced in MLflow.
- The prototype reasons about uncertainty: it shows assumptions, data gaps, and the time horizon (for example 2025 vs 2040) explicitly to the user.
- The prototype handles ambiguous user input with a clarifying follow-up question instead of a guessed answer.

### Zou niet (Should not): pitfalls to avoid

- Replacing or rewriting the LangGraph workflow, the DuckDB query path, or the frontend architecture. Reason from existing building blocks; extend, do not rebuild.
- Loading every extra dataset at once. Extra columns in the prompt reduce model accuracy; pick the datasets that your scenarios actually need.
- Hiding the reasoning chain behind a single text answer. The whole point of the Insight panel and MLflow tracing is that civil servants can audit the steps.

### Kan (Could): bonus for outstanding submissions

- Extending the LangGraph workflow with a dedicated *scenario* node that can compose multiple shocks (for example *Hollandse IJssel six weeks unusable* plus *Zuid-Holland population +10%*).
- Adding a small UI for scenario parameters (sliders, presets) on top of the existing chat box.
- Aligning with the **Federatief Datastelsel (FDS)** standards and principles, with **NORA**, and with PZH service-design guidance.
- Reusing or contributing back to the other OneGov #2 repositories (synthetic data, digital assistants, citizen-centric services).

## Deliverables

At the end of the hackathon every team submits:

- A **working prototype or PoC**, even if not finished, that shows the core.
- A **demo of at least two scenarios or comparisons**.
- A **short description of data, assumptions, and limitations**.
- A **pitch deck** (max. 10 slides).
- A **repository link** (your own fork of this repo, or a derivative repo).

## Submission

Teams submit through **Alkemio**, the central submission and review point for the OneGov #2 jury.

- **Alkemio submission link:** [alkem.io/onegov-hackathon/challenges/ruimtelijkeassistentdrink](https://alkem.io/onegov-hackathon/challenges/ruimtelijkeassistentdrink).
- The Alkemio submission is what the jury scores during the hackathon. Pull requests against this repository remain welcome for high-quality reusable artefacts (datasets, prompts, nodes, documentation), and are leading for the post-hackathon review and merge of those contributions.

## Resources and inspiration

- [OneGov_2_Challenge_Brief_Drinkwaterzekerheid.pdf](OneGov_2_Challenge_Brief_Drinkwaterzekerheid.pdf): original Dutch brief.
- [docs/example-scenarios.md](docs/example-scenarios.md): the three guiding what-if questions plus space for additions from the challenge owners.
- [docs/data-inventory.md](docs/data-inventory.md): per-theme dataset inventory.
- [docs/architecture_diagram.mmd](docs/architecture_diagram.mmd) and [docs/workflow.mmd](docs/workflow.mmd): architecture and LangGraph workflow.
- [docs.greenpt.ai](https://docs.greenpt.ai): GreenPT credentials offered to teams as the LLM provider, with the public OpenAI API as a fallback.
- [federatiefdatastelsel.pleio.nl](https://federatiefdatastelsel.pleio.nl): FDS standards and principles.
- [noraonline.nl](https://www.noraonline.nl): NORA reference architecture.

## Disclaimer

The data in this repository is the data Provincie Zuid-Holland already publishes via its *gebiedsviewer*, *drinkwaterzekerheid*, and *woondeals* themes, plus open data from CBS, RIVM, RIONED, and PDOK. Datasets retain the licences of their original sources; see [docs/data-inventory.md](docs/data-inventory.md). Prototypes that emerge from the hackathon are not policy commitments and require further review before they can go into production.

---

**Challenge owners:**
Sebastiaan Schmidt, Tim Padmos, Thijs Raterink (Provincie Zuid-Holland)

**Hackathon questions:** [hack@govtechnl.nl](mailto:hack@govtechnl.nl)
