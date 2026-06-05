# Calibration & validation status (Phase 7, Gap E)

## What this is — and isn't (read this first)
The DrinkwaterDruk verdict is an **assumption-driven composite** on real H3 data. It is
**sourced and reproducible**, but a government tool must answer one more question:
*"has this verdict ever matched a real assessment?"*

This repo ships a **calibration harness**, not external validation. No external Dunea/Evides
capacity study is bundled, so the calibration set is the design's **own verified reference
figures** (ontwerpdocument Part H). That makes this a **reproducibility / consistency
calibration**: it proves the engine still produces the documented verdicts. It is **NOT**
evidence that those verdicts match an independent hydrological forecast.

Every scenario card and citation therefore carries this honest status:

> *Directioneel gevalideerd tegen de eigen geverifieerde ontwerp-referentiecijfers
> (ontwerpdocument Part H); nog NIET vergeleken met een externe capaciteitsstudie
> (bijv. Dunea/Evides). Beleidsmatige verkenning, geen gevalideerde voorspelling.*

## The reference cases (`CALIBRATION_CASES`)
| Case | Expected | Basis | Result |
|---|---|---|---|
| Inname Hollandse IJssel — KNMI Hd, 2040 | STOP (band 70–95) | Ontwerp Part H ~82,4 | ✅ STOP 82,4 |
| Inname Hollandse IJssel — KNMI B, 2040 | CAUTION (band 38–66) | Ontwerp Part H ~50,5 | ✅ CAUTION 50,5 |

`GET /api/scenario/calibration` runs the harness and returns agreement (currently **2/2, 100%**).

## How to add REAL external validation
Add entries to `CALIBRATION_CASES` in `app/services/scenario/calibration.py` with
`kind="external-study"` and a real `source` (a published capacity study, a Dunea/Evides
forecast, a KRW assessment). Set the `expected_verdict` + `score_band` from that study.
Once external cases exist, update `assumptions.VALIDATION_STATUS_NL` to reflect the new
validation level. The harness, endpoint and card status then report the stronger evidence
automatically.

## Why this is the honest maximum today
Claiming external validation without an external dataset would be the exact "confidently
wrong" failure the policymaker critique warned about. The harness + explicit status + the
pluggable slot give the calibration *story* and *mechanism* now, and make real validation a
drop-in data task — without overstating what the tool currently knows.
