"""Runnable v3 engine on the REAL shipped data (no synthetic fixture, no LLM key).

Composes real themes joined on a canonical h3_id into a per-cell DrinkwaterDruk
score (0-100) and an area verdict. Every quantitative knob is a sourced
Assumption (see docs/onegov2_design_v3_repo_aligned.md Part D).

Themes (all LEFT-joined onto the chosen universe of cells):
  - `verzilting`               -> salinity pressure (ZOUT_CONC mask)
  - `overstromingen_...`       -> flood co-pressure (Risico class)
  - `zes_uur_zones_drinkwater` -> drinking-water protection sensitivity
  - CBS vierkantstatistieken   -> demand pressure (population), with growth + a
                                  relative added-homes lever (brief scenario 3)

Universe selection (`base`):
  - "salinity"  -> score the verzilting (salinity-relevant) cells. Default; right
                   for verzilting/intake scenarios.
  - "populated" -> score the built-up cells (CBS population > pop_min). Right for
                   housing/demand scenarios — demand dominates where people live.

Honesty notes:
  - `verzilting.ZOUT_CONC` ships as one class ('> 200mg/l') -> salinity is a MASK;
    a dry KNMI scenario amplifies its contribution (capped).
  - CBS `_consumption` totals ~46k, not real headcounts -> it is a RELATIVE
    population-density signal. Housing growth is therefore modelled as a relative
    households increase (added_homes / regional_households), never absolute m³.
  - CBS h3_index is a leading-zero 16-char id the repo's tables.py only LOWER()s
    (0 overlap); we strip the pad zero so it joins (0 -> 2145 cells; both res 9).
"""
from __future__ import annotations

import glob
import os
from typing import Any

import duckdb

DEFAULT_ASSUMPTIONS: dict[str, float] = {
    # composite weights (Methodologie)
    "weight_salinity": 0.4,
    "weight_demand": 0.3,
    "weight_flood": 0.2,
    "weight_protection": 0.1,
    # climate
    "knmi_dryness_multiplier": 1.0,        # KNMI'23 (1.0 baseline ... 1.8 Hd)
    # demand
    "demand_per_person_m3_day": 0.119,     # VEWIN Waterstatistiek
    "population_growth_pct": 0.0,          # Ruimtelijk Arrangement Rijk-ZH (scenario sets it)
    "demand_ref_m3_per_cell": 1.5,         # Methodologie (per-cell demand reference)
    "added_homes": 0.0,                    # scenario 3 lever (e.g. 80000)
    "regional_households": 1_700_000.0,    # ZH households (CBS) — homes add relative to this
    "pop_min_built_up": 0.0,               # min CBS pop for a cell to count as built-up
    # verdict thresholds (Methodologie)
    "verdict_caution": 33.0,
    "verdict_stop": 66.0,
    "area_stop_share": 0.20,
}

FLOOD_SEVERITY: dict[str, float] = {
    "Niet kwetsbaar": 0.0, "0 - 0,2 m": 0.2, "0,2 - 0,5 m": 0.4,
    "0,5 - 2,0 m": 0.7, "Meer dan 2 m": 1.0, "Onbekend": 0.3,
}


def verdict_from_score(score: float, a: dict[str, float] | None = None) -> str:
    """Single verdict definition (fix-pack C1 discipline, 0-100 form)."""
    a = {**DEFAULT_ASSUMPTIONS, **(a or {})}
    if score >= a["verdict_stop"]:
        return "STOP"
    if score >= a["verdict_caution"]:
        return "CAUTION"
    return "GO"


def _one(data_dir: str, theme: str, table: str) -> str | None:
    fs = glob.glob(os.path.join(data_dir, theme, table, "*.parquet"))
    return fs[0] if fs else None


def _cbs(data_dir: str) -> str | None:
    base = os.path.join(data_dir, "..", "extra_data", "CBS")
    hit = None
    for cand in sorted(glob.glob(os.path.join(base, "cbs_vierkantstatistieken_*_consumption"))):
        f = glob.glob(os.path.join(cand, "*.parquet"))
        if f:
            hit = f[0]
    return hit


def _norm(col: str) -> str:
    """Canonical h3 string: lowercase, and strip a single pad zero on 16-char ids."""
    lc = f"lower({col})"
    return f"CASE WHEN length({lc}) = 16 AND {lc} LIKE '0%' THEN substr({lc}, 2) ELSE {lc} END"


def _scored_cte(data_dir: str, a: dict[str, float], area_cells: list[str] | None, base: str) -> str:
    vz = _one(data_dir, "gebiedsviewer", "verzilting")
    ov = _one(data_dir, "gebiedsviewer", "overstromingen_kwetsbaarheid_panden_na_dijkdoorbraak")
    zes = _one(data_dir, "drinkwaterzekerheid", "zes_uur_zones_drinkwater")
    cbs = _cbs(data_dir)
    if not vz:
        raise FileNotFoundError("verzilting parquet not found under " + data_dir)

    flood_case = " ".join(f"WHEN Risico = '{k}' THEN {v}" for k, v in FLOOD_SEVERITY.items())
    ws, wf, wp, wd = (a["weight_salinity"], a["weight_flood"], a["weight_protection"], a["weight_demand"])
    dry = a["knmi_dryness_multiplier"]
    dppd, growth, ref = a["demand_per_person_m3_day"], a["population_growth_pct"], a["demand_ref_m3_per_cell"]
    # housing: relative households increase (homes ~ households), not absolute headcount
    added_factor = 1.0 + (a["added_homes"] / max(a["regional_households"], 1.0))

    def area_clause(idcol: str) -> str:
        if area_cells is None:
            return ""
        vals = ", ".join("'" + c.replace("'", "") + "'" for c in area_cells) or "''"
        return f"AND ({_norm(idcol)}) IN ({vals})"

    if base == "populated" and cbs:
        universe = (f"SELECT {_norm('h3_index')} AS h FROM read_parquet('{cbs}') "
                    f"WHERE aantal_inwoners_sum > {a['pop_min_built_up']} {area_clause('h3_index')} GROUP BY 1")
    else:  # salinity (default)
        universe = (f"SELECT DISTINCT {_norm('h3_id')} AS h FROM read_parquet('{vz}') "
                    f"WHERE RELEVANT = 'ja' AND ZOUT_CONC LIKE '%200%' {area_clause('h3_id')}")

    cbs_cte = (f"SELECT {_norm('h3_index')} AS h, SUM(aantal_inwoners_sum) AS pop "
               f"FROM read_parquet('{cbs}') GROUP BY 1") if cbs else "SELECT '' AS h, 0.0 AS pop WHERE FALSE"

    return f"""
    WITH universe AS ( {universe} ),
    sal AS (
        SELECT DISTINCT {_norm('h3_id')} AS h, 1.0 AS sal
        FROM read_parquet('{vz}') WHERE RELEVANT = 'ja' AND ZOUT_CONC LIKE '%200%'
    ),
    ovl AS (
        SELECT {_norm('h3_id')} AS h, CASE {flood_case} ELSE 0 END AS flood
        FROM read_parquet('{ov}')
    ),
    prot AS (
        SELECT DISTINCT {_norm('h3_id')} AS h, 1.0 AS prot FROM read_parquet('{zes}')
    ),
    cbs AS ( {cbs_cte} ),
    scored AS (
        SELECT u.h,
               LEAST(1.0, COALESCE(c.pop, 0) * {dppd} * (1.0 + {growth}) * {added_factor} / {ref}) AS demand_norm,
               -- per-factor contributions (0-100 scale, PRE-clamp); they sum to the
               -- unclamped score, so score = LEAST(100, term_salinity + ... ). Exposed
               -- for the A/B comparison's per-factor attribution (compare.py).
               100.0 * ({ws} * COALESCE(s.sal, 0) * {dry}) AS term_salinity,
               100.0 * ({wf} * COALESCE(o.flood, 0)) AS term_flood,
               100.0 * ({wp} * COALESCE(p.prot, 0)) AS term_protection,
               100.0 * ({wd} * LEAST(1.0, COALESCE(c.pop, 0) * {dppd} * (1.0 + {growth}) * {added_factor} / {ref})) AS term_demand,
               100.0 * LEAST(1.0,
                   {ws} * COALESCE(s.sal, 0) * {dry}
                 + {wf} * COALESCE(o.flood, 0)
                 + {wp} * COALESCE(p.prot, 0)
                 + {wd} * LEAST(1.0, COALESCE(c.pop, 0) * {dppd} * (1.0 + {growth}) * {added_factor} / {ref})
               ) AS score
        FROM universe u
        LEFT JOIN sal s USING (h)
        LEFT JOIN ovl o USING (h)
        LEFT JOIN prot p USING (h)
        LEFT JOIN cbs c USING (h)
    )"""


def score_h3_area(data_dir: str = "data", assumptions: dict[str, float] | None = None,
                  return_cells: int = 0, area_cells: list[str] | None = None,
                  base: str = "salinity") -> dict[str, Any]:
    """Per-cell score over the chosen universe -> aggregate verdict (+ optional top cells)."""
    a = {**DEFAULT_ASSUMPTIONS, **(assumptions or {})}
    con = duckdb.connect()
    cte = _scored_cte(data_dir, a, area_cells, base)

    n_cells, score_avg, demand_avg, n_stop, n_caution, n_go = con.execute(cte + f"""
        SELECT count(*), round(avg(score), 1), round(avg(demand_norm), 3),
               sum(CASE WHEN score >= {a['verdict_stop']} THEN 1 ELSE 0 END),
               sum(CASE WHEN score >= {a['verdict_caution']} AND score < {a['verdict_stop']} THEN 1 ELSE 0 END),
               sum(CASE WHEN score < {a['verdict_caution']} THEN 1 ELSE 0 END)
        FROM scored
    """).fetchone()
    n_cells = int(n_cells or 0)
    score_avg = float(score_avg) if score_avg is not None else 0.0
    stop_share = (n_stop or 0) / n_cells if n_cells else 0.0
    area_verdict = ("STOP" if stop_share >= a["area_stop_share"]
                    else "CAUTION" if (n_stop or 0) + (n_caution or 0) > 0 else "GO")

    cells: list[dict] = []
    if return_cells:
        for h, sc in con.execute(cte + f" SELECT h, score FROM scored ORDER BY score DESC LIMIT {int(return_cells)}").fetchall():
            sc = float(sc)
            cells.append({"h3_id": h, "score": round(sc, 1), "klasse": verdict_from_score(sc, a)})

    themes = ["verzilting", "overstromingen_kwetsbaarheid", "zes_uur_zones_drinkwater", "cbs_vierkantstatistieken"]
    return {
        "n_cells": n_cells, "score_avg": score_avg,
        "demand_avg": float(demand_avg) if demand_avg is not None else 0.0,
        "n_stop": int(n_stop or 0), "n_caution": int(n_caution or 0), "n_go": int(n_go or 0),
        "stop_share": round(stop_share, 3), "area_verdict": area_verdict, "base": base,
        "themes_used": themes, "assumptions_used": a, "cells": cells,
    }


# Per-factor labels used by the comparison attribution (compare.py). Order matters
# (it is the canonical display/iteration order).
FACTORS: tuple[str, ...] = ("salinity", "flood", "protection", "demand")


def score_cells_components(data_dir: str = "data", assumptions: dict[str, float] | None = None,
                          area_cells: list[str] | None = None,
                          base: str = "salinity") -> list[dict[str, Any]]:
    """Every scored cell with its DrinkwaterDruk score AND the four per-factor
    contributions (0-100 scale, pre-clamp). Used by the A/B comparison to build
    per-factor attribution and a per-cell diff. The factor terms sum to the
    unclamped score, i.e. ``score == min(100, salinity + flood + protection + demand)``.
    """
    a = {**DEFAULT_ASSUMPTIONS, **(assumptions or {})}
    con = duckdb.connect()
    cte = _scored_cte(data_dir, a, area_cells, base)
    rows = con.execute(
        cte + " SELECT h, score, term_salinity, term_flood, term_protection, term_demand FROM scored"
    ).fetchall()
    out: list[dict[str, Any]] = []
    for h, sc, ts, tf, tp, td in rows:
        out.append({
            "h3_id": h,
            "score": round(float(sc), 1),
            "salinity": round(float(ts), 2),
            "flood": round(float(tf), 2),
            "protection": round(float(tp), 2),
            "demand": round(float(td), 2),
        })
    return out
