# Data inventory

This is a verified per-theme inventory of the datasets that ship with this repository. It records what is loaded by default at `src/backend/data/`, what is available as opt-in extras at `src/backend/extra_data/`, and what the challenge brief still expects the challenge owners to confirm or supply.

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

Around 60 provincial layers. Covers the categories called out in the brief: verzilting, bodemdaling, *overstromingskwetsbaarheid*, *groenblauwe ruimte*, *natuurnetwerk*, nutrient-polluted areas, soil stability, and other soil and land-use data. Examples: `verzilting`, `bodemdaling_bodemdaling_wegen`, `overstromingen_kwetsbaarheid_panden_na_dijkdoorbraak`, `groenblauwe_ruimte_huidig_new`, `natuurnetwerk_nederland`, `nutri_nten_verontreinigde_gebieden`, `stabiliteit`, `stabiele_bodem`, `veenoxidatie`, `daling_bij_ontwateringsdiepte_0_5_m_new`, `daling_bij_ontwateringsdiepte_1_0_m_new`. The full list is in [src/backend/data/gebiedsviewer/](../src/backend/data/gebiedsviewer/).

LLM metadata: `_llm_metadata_gebiedsviewer.json`.

### `lgn` — loaded by default

Land-use rasters (*Landgebruik Nederland*).

| Table | In repo |
| --- | --- |
| `lgn2018_pzh_vectorized_consumption` | yes |
| `lgn2019_pzh_vectorized_consumption` | yes |
| `lgn2020_pzh_vectorized_consumption` | yes |
| `lgn2021_pzh_vectorized_consumption` | yes |
| `lgn2022_pzh_vectorized_consumption` | yes |

LLM metadata: `_llm_metadata_lgn.json`.

> _TODO (challenge owners): confirm whether `lgn` is intended to be loaded by default. It is currently in `src/backend/data/`, so it is loaded; the brief lists it as a primary theme alongside drinkwaterzekerheid and gebiedsviewer, so this looks correct, but a one-line confirmation would close the loop._

## Optional themes (`src/backend/extra_data/`)

These ship with the repo but are not loaded by default. Teams that need them must register them; expect a small drop in model accuracy because the extra column names are added to the prompts.

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

### `gebiedsviewer` (extra)

A second `gebiedsviewer` layer set sits under `src/backend/extra_data/gebiedsviewer/` with its own `_llm_metadata_gebiedsviewer.json`. Treat it as an opt-in extension of the primary `gebiedsviewer` theme, not as a replacement.

> _TODO (challenge owners): confirm what the relationship is between `src/backend/data/gebiedsviewer/` and `src/backend/extra_data/gebiedsviewer/`. If the extra copy is a superset or a snapshot from a different export, document that in this file so teams know which one to register._

## Open data inventory questions

- **LGN as a separate primary theme.** The brief lists three primary themes (drinkwaterzekerheid, gebiedsviewer, LGN). LGN is present under `src/backend/data/lgn/`, so it is loaded; please confirm.
- **Extra drinkwater-specific datasets.** The brief implies more drinkwater-specific datasets and example scenarios may be supplied by the challenge owners. Land them here and in [example-scenarios.md](example-scenarios.md) so teams know what to plan for.
- **Dataset licences.** Each dataset retains its source licence (PZH, CBS, RIVM, RIONED, PDOK, etc.). A short licence column per table is not yet recorded; if you need it for the open-source Must criterion, add a `licence` field to the `_llm_metadata_*.json` files.
