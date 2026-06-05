"""Area-of-interest selection (design doc v3, §11 spatial).

Picks the H3 cells a scenario should be scored over, instead of the whole
verzilting region:
  - intake_failure -> the zes_uur_zones_drinkwater protection cells (optionally
    the zone whose OWMNAAM matches the intake).
  - drop_pin       -> an H3 grid_disk around the geocoded location.

Geocoding uses the PDOK locatieserver over HTTPS; the H3 ring math uses the
python `h3` library (the DuckDB `h3` extension cannot be installed offline in
this sandbox). A labeled hardcoded-coordinate fallback keeps it runnable without
network. `K` follows the repo convention: ~0.35 km per ring at resolution 9.
"""
from __future__ import annotations

import glob
import math
import os
import re
from typing import Any

import duckdb
import h3

PDOK_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
RING_KM = 0.35  # repo convention: 1 H3 ring ≈ 0.35 km at resolution 9
H3_RES = 9

# Labeled offline fallback coordinates (lat, lon) for common ZH locations.
FALLBACK_COORDS: dict[str, tuple[float, float]] = {
    "pijnacker": (52.019, 4.432), "nootdorp": (52.040, 4.392),
    "den haag": (52.080, 4.310), "rotterdam": (51.922, 4.479),
    "gouda": (52.011, 4.711), "delft": (52.011, 4.357),
}
DEFAULT_ZH = (52.02, 4.50)


def geocode_pdok(name: str, timeout: float = 2.5) -> tuple[float, float] | None:
    """Resolve a place name to (lat, lon) via PDOK. Returns None on any failure."""
    if not name:
        return None
    try:
        import httpx
        r = httpx.get(PDOK_URL, params={"q": name, "rows": 1, "fl": "centroide_ll"},
                      timeout=timeout, trust_env=True)
        r.raise_for_status()
        docs = r.json().get("response", {}).get("docs", [])
        if not docs:
            return None
        m = re.search(r"POINT\(([-\d.]+)\s+([-\d.]+)\)", docs[0].get("centroide_ll", ""))
        if not m:
            return None
        return float(m.group(2)), float(m.group(1))   # (lat, lon)
    except Exception:
        return None


def _fallback_coords(name: str | None) -> tuple[tuple[float, float], str]:
    n = (name or "").lower()
    for key, coords in FALLBACK_COORDS.items():
        if key in n:
            return coords, f"fallback:{key}"
    return DEFAULT_ZH, "fallback:Zuid-Holland"


def _zes_cells(data_dir: str, intake_id: str | None) -> list[str]:
    f = glob.glob(os.path.join(data_dir, "drinkwaterzekerheid", "zes_uur_zones_drinkwater", "*.parquet"))
    if not f:
        return []
    con = duckdb.connect()
    if intake_id:
        rows = con.execute(
            f"SELECT DISTINCT lower(h3_id) FROM read_parquet('{f[0]}') "
            f"WHERE lower(OWMNAAM) LIKE '%{intake_id.lower()}%'").fetchall()
        if rows:
            return [r[0] for r in rows]
    return [r[0] for r in con.execute(
        f"SELECT DISTINCT lower(h3_id) FROM read_parquet('{f[0]}')").fetchall()]


def select_h3_area(params: Any, data_dir: str = "data",
                   radius_km: float = 3.5) -> tuple[list[str] | None, str, dict]:
    """Return (area_cells | None, descriptor_nl, meta). None = whole verzilting region."""
    st = getattr(params, "scenario_type", None)

    if st == "intake_failure":
        cells = _zes_cells(data_dir, getattr(params, "intake_id", None))
        return cells, f"zes-uur beschermingszones ({len(cells)} cellen)", {"mode": "zes_uur", "n": len(cells)}

    if st == "drop_pin":
        name = getattr(params, "location_name", None)
        latlon = geocode_pdok(name)
        source = "PDOK"
        if latlon is None:
            latlon, source = _fallback_coords(name)
        lat, lon = latlon
        center = h3.latlng_to_cell(lat, lon, H3_RES)
        k = max(1, math.ceil(radius_km / RING_KM))
        cells = list(h3.grid_disk(center, k))
        return (cells,
                f"H3 grid_disk ~{radius_km:g} km rond {name or 'locatie'} via {source} ({len(cells)} cellen)",
                {"mode": "grid_disk", "lat": lat, "lon": lon, "k": k, "source": source, "n": len(cells)})

    return None, "volledige verziltingsregio", {"mode": "all"}
