# Data inventory

This is a per-theme inventory of the datasets that ship with this repository. It records what is loaded by default from `src/backend/data/`, what is available as opt-in extras at `src/backend/extra_data/`, and what the challenge brief still expects the challenge owners to confirm or supply.

> **How to read this file.** A theme is **loaded by default** when its directory sits under `src/backend/data/`. A theme is **optional** when it sits under `src/backend/extra_data/`; teams can register it but every extra dataset adds column names to the prompts and may reduce model accuracy.

## Primary themes (`src/backend/data/`)

### `drinkwaterzekerheid` — loaded by default

Matches the brief one for one.

| Table | In repo |
| --- | --- |
| `drinkwater_infrastructuur` | yes |
| `drinkwater_productieketen` | yes |
| `drinkwaterbedrijven` | yes |
| `toestandsbeoordeling_oppervlaktewaterlichamen` | yes |
| `waterschappen` | yes |
| `zes_uur_zones_drinkwater` | yes |

LLM metadata: `_llm_metadata_drinkwaterzekerheid.json`.

### `gebiedsviewer` — loaded by default

Around 50 provincial layers. Covers the categories called out in the brief: verzilting, bodemdaling, *overstromingskwetsbaarheid*, *groenblauwe ruimte*, *natuurnetwerk*, nutrient-polluted areas, soil stability, and other soil and land-use data. Examples: `verzilting`, `bodemdaling_bodemdaling_wegen`, `overstromingen_kwetsbaarheid_panden_na_dijkdoorbraak`, `groenblauwe_ruimte_huidig_new`, `natuurnetwerk_nederland`, `nutri_nten_verontreinigde_gebieden`, `stabiliteit`, `stabiele_bodem`, `veenoxidatie`, `daling_bij_ontwateringsdiepte_0_5_m_new`, `daling_bij_ontwateringsdiepte_1_0_m_new`. The full list is in [src/backend/data/gebiedsviewer/](../src/backend/data/gebiedsviewer/).

LLM metadata: `_llm_metadata_gebiedsviewer.json`.

## Optional themes (`src/backend/extra_data/`)

These ship with the repo but are not loaded by default. Teams that need them must register them; expect a small drop in model accuracy because the extra column names are added to the prompts.

### `lgn` — Landgebruik Nederland

| Table | In repo |
| --- | --- |
| `lgn2018_pzh_vectorized_consumption` | yes |
| `lgn2019_pzh_vectorized_consumption` | yes |
| `lgn2020_pzh_vectorized_consumption` | yes |
| `lgn2021_pzh_vectorized_consumption` | yes |
| `lgn2022_pzh_vectorized_consumption` | yes |

LLM metadata: `_llm_metadata_lgn.json`. Per the challenge owners, LGN is not directly tied to the drinkwater question but can be useful for scenarios that hinge on land-use change (for example: opportunities in *intrekgebieden*).

### `CBS` — vierkantstatistieken

| Table | In repo |
| --- | --- |
| `cbs_vierkantstatistieken_2018_consumption` | yes |
| `cbs_vierkantstatistieken_2019_consumption` | yes |
| `cbs_vierkantstatistieken_2020_consumption` | yes |
| `cbs_vierkantstatistieken_2021_consumption` | yes |
| `cbs_vierkantstatistieken_2022_consumption` | yes |
| `cbs_vierkantstatistieken_2023_consumption` | yes |

LLM metadata: `_llm_metadata_CBS.json`. Useful for the population-growth side of scenario 2 in [example-scenarios.md](example-scenarios.md).

### `woondeals` umbrella

In this repository, the `woondeals` directory bundles the brief's "woondeals data, PMIEK projects, stikstof and traffic data". Concretely:

| Subgroup | Tables |
| --- | --- |
| Capacity / grid | `capaciteitskaart_afname_regionaal` |
| Air quality | `lucht_cimlk_2025j2025`, `lucht_cimlk_2025j2030` |
| OV | `ov_haltes_nl_actueel` |
| PMIEK projects | `pmiek_projecten_lijnen_2023`, `pmiek_projecten_punten_2023`, `pmiek_projecten_vlakken_2023` |
| Stikstof | `stikstof_natura2000_stats`, `stikstof_overschrijding_kdw` |
| Traffic | `verkeersintensiteit_meetvakken_pzh_weekdag` |

LLM metadata: `_llm_metadata_woondeals.json`.

## Open data inventory questions

- **Optional external sources teams may add themselves.** The brief points teams at three open sources that are not shipped with the repo and can be registered into `src/backend/extra_data/` with a matching `_llm_metadata_*.json`:
  - **KNMI klimaatscenario's 2050** ([klimaatscenarios.knmi.nl](https://www.klimaatscenarios.knmi.nl)) for the dry-climate axis in scenarios 4 and 7.
  - **KRW monitoringsdata** via Waterinfo RWS ([waterinfo.rws.nl](https://waterinfo.rws.nl)) for scenario 5.
  - **DINOloket** grondwaterdata ([dinoloket.nl](https://www.dinoloket.nl)) for groundwater-driven scenarios.
- **Dataset licences.** Each dataset retains its source licence (PZH, CBS, RIVM, RIONED, PDOK, etc.). A short licence column per table is not yet recorded; a `licence` field per table in the `_llm_metadata_*.json` files would make the open-source Must criterion easier to satisfy. Recorded as a known limitation; not in scope for this repo's hackathon prep.
