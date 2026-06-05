"""Dataset -> publisher/source registry (Phase 5).

Single source of truth for "where does this data come from", used by:
  - the descriptive SQL assistant's new citation step (sources_for_sql), so its
    prose answers also carry hyperlinked Bronnen, and
  - the Kennisbasis endpoint (theme freshness + source links).

The brief's disclaimer lists the publishers: PZH (gebiedsviewer, drinkwater-
zekerheid, woondeals), plus open data from CBS, RIVM, RIONED and PDOK. Every
entry carries a non-empty http(s) source_url (same discipline as the scenario
assumption registry).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

# theme -> publisher + canonical source URL + licence note.
THEME_SOURCES: dict[str, dict] = {
    "drinkwaterzekerheid": {
        "publisher": "Provincie Zuid-Holland — Drinkwaterzekerheid",
        "url": "https://www.pzh.nl/regiovisie-waterprogramma-2022-2027",
        "licence": "PZH open data",
    },
    "gebiedsviewer": {
        "publisher": "Provincie Zuid-Holland — Gebiedsviewer",
        "url": "https://www.zuid-holland.nl/loket/kaarten/",
        "licence": "PZH open data",
    },
    "cbs": {
        "publisher": "CBS — Vierkantstatistieken",
        "url": "https://www.cbs.nl/nl-nl/dossier/nederland-regionaal/geografische-data/kaart-van-100-meter-bij-100-meter-met-statistieken",
        "licence": "CBS open data",
    },
    "lgn": {
        "publisher": "Landgebruik Nederland (LGN) — Wageningen Environmental Research",
        "url": "https://www.wur.nl/nl/onderzoek-resultaten/onderzoeksinstituten/environmental-research/faciliteiten-tools/kaarten-en-gis-bestanden/landgebruik.htm",
        "licence": "WUR / open data",
    },
    "woondeals": {
        "publisher": "Woondeals Zuid-Holland (incl. PMIEK, stikstof, luchtkwaliteit)",
        "url": "https://www.rijksoverheid.nl/onderwerpen/volkshuisvesting/woningbouw/woondeals",
        "licence": "Rijksoverheid / PZH open data",
    },
    "pdok": {
        "publisher": "PDOK — Publieke Dienstverlening Op de Kaart",
        "url": "https://www.pdok.nl",
        "licence": "open data",
    },
}

# Static table->theme hints so source lookup works offline (no data dir needed).
# Extended at runtime by the real data dictionary when available.
_TABLE_THEME_HINTS: dict[str, str] = {
    "verzilting": "gebiedsviewer",
    "overstromingen_kwetsbaarheid_panden_na_dijkdoorbraak": "gebiedsviewer",
    "bodemdaling_bodemdaling_wegen": "gebiedsviewer",
    "natuurlijke_spons_kansrijk": "gebiedsviewer",
    "zes_uur_zones_drinkwater": "drinkwaterzekerheid",
    "drinkwater_infrastructuur": "drinkwaterzekerheid",
    "drinkwaterbedrijven": "drinkwaterzekerheid",
    "drinkwater_productieketen": "drinkwaterzekerheid",
    "toestandsbeoordeling_oppervlaktewaterlichamen": "drinkwaterzekerheid",
    "capaciteitskaart_afname_regionaal": "woondeals",
}


def _theme_for_table(table: str, dynamic: dict[str, str] | None = None) -> Optional[str]:
    t = table.lower()
    if t.startswith("cbs_"):
        return "cbs"
    if t.startswith("lgn"):
        return "lgn"
    if dynamic and t in dynamic:
        return dynamic[t]
    if t in _TABLE_THEME_HINTS:
        return _TABLE_THEME_HINTS[t]
    # group-prefix fallback (e.g. "verzilting_x" -> "verzilting")
    for known, theme in _TABLE_THEME_HINTS.items():
        if t.startswith(known.split("_", 1)[0]):
            return theme
    return None


def build_table_theme_index(data_dir: Optional[str] = None) -> dict[str, str]:
    """Merge the static hints with the real data dictionary (if reachable)."""
    index = dict(_TABLE_THEME_HINTS)
    try:
        from app.services.helpers.tables import load_theme_metadata
        meta = load_theme_metadata(Path(data_dir)) if data_dir else load_theme_metadata()
        for theme_name, theme in meta.items():
            for tbl in theme.get("data", []) or []:
                name = tbl.get("naam")
                if name:
                    index[name.lower()] = theme_name
    except Exception:
        pass
    return index


def source_for_theme(theme: str) -> dict:
    src = THEME_SOURCES.get(theme, {
        "publisher": "Provincie Zuid-Holland", "url": "https://www.zuid-holland.nl", "licence": "open data",
    })
    return {"theme": theme, **src}


def sources_for_tables(tables: list[str], dynamic: dict[str, str] | None = None) -> list[dict]:
    """De-duplicated source entries for the given tables (by theme)."""
    seen: set[str] = set()
    out: list[dict] = []
    for t in tables:
        theme = _theme_for_table(t, dynamic)
        if not theme or theme in seen:
            continue
        seen.add(theme)
        out.append(source_for_theme(theme))
    return out


def extract_tables_from_sql(sql: str, known_tables: list[str]) -> list[str]:
    """Return the known table/view names that appear in the SQL (word-boundary match)."""
    if not sql:
        return []
    found = []
    for t in known_tables:
        if re.search(r"\b" + re.escape(t) + r"\b", sql, re.IGNORECASE):
            found.append(t)
    return sorted(set(found))


_EMPTY_TABLES = {"drinkwater_productieketen", "toestandsbeoordeling_oppervlaktewaterlichamen"}


def build_kennisbasis(data_dir: Optional[str] = None) -> dict:
    """The "Wat weet dit systeem?" inventory: every loaded theme + its tables,
    publisher/source link, column count, and a freshness date (newest parquet
    mtime). Used by the always-visible Kennisbasis panel."""
    import glob
    import os
    from datetime import datetime, timezone

    try:
        from app.services.helpers.tables import discover_tables, load_theme_metadata
    except Exception:
        return {"themes": [], "generated_at": "", "note_nl": "Datawoordenboek niet beschikbaar."}

    root = Path(data_dir) if data_dir else None
    meta = load_theme_metadata(root) if root else load_theme_metadata()

    freshness: dict[str, str] = {}
    try:
        entries = discover_tables(root) if root else discover_tables()
        for e in entries:
            files = glob.glob(e.parquet_glob)
            if files:
                mtime = max(os.path.getmtime(f) for f in files)
                freshness[e.table_name] = datetime.fromtimestamp(mtime, tz=timezone.utc).date().isoformat()
    except Exception:
        pass

    themes_out = []
    for theme_name, theme in meta.items():
        src = source_for_theme(theme_name)
        tables = []
        for tbl in theme.get("data", []) or []:
            name = tbl.get("naam")
            tables.append({
                "name": name,
                "columns": len(tbl.get("kolommen", {}) or {}),
                "last_updated": freshness.get(name),
                "empty": name in _EMPTY_TABLES,
            })
        themes_out.append({
            "theme": theme_name,
            "label": theme.get("label", theme_name),
            "publisher": src["publisher"],
            "url": src["url"],
            "voorbeeldvragen": (theme.get("voorbeeldvragen", []) or [])[:3],
            "tables": tables,
        })
    return {
        "themes": themes_out,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note_nl": "Dit is wat het systeem weet. Vraag de Kennis-chat voor uitleg mét bron.",
    }


def sources_for_sql(sql: str, known_tables: list[str],
                    dynamic: dict[str, str] | None = None) -> list[dict]:
    """The hyperlinked Bronnen for a descriptive SQL answer: which datasets it
    touched and where they come from."""
    tables = extract_tables_from_sql(sql, known_tables)
    srcs = sources_for_tables(tables, dynamic)
    # annotate each source with the matching tables (nice for the UI)
    by_theme: dict[str, list[str]] = {}
    for t in tables:
        theme = _theme_for_table(t, dynamic)
        if theme:
            by_theme.setdefault(theme, []).append(t)
    for s in srcs:
        s["tables"] = sorted(by_theme.get(s["theme"], []))
    return srcs
