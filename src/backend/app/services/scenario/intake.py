"""Intake identity resolution — Fix S1.

An intake is identified by `winlocaties.locatie_id`, and
`productieketen.intake_id` is a foreign key to it. Resolve a human name OR an
id to that canonical id ONCE, then pass the id to every downstream query
(capacity, chloride, Type-1 affected zones). No more repeated `naam LIKE`.

`conn` is a duckdb connection; not imported at module level to keep this
dependency-light.
"""
from __future__ import annotations

from typing import Any


def resolve_intake_id(conn: Any, query: str) -> str | None:
    """Map an id or a human name to the canonical winlocaties.locatie_id.
    One LIKE, once. Prefers an exact id match, then the shortest name match."""
    row = conn.execute(
        """SELECT locatie_id
           FROM winlocaties
           WHERE locatie_id = ? OR lower(naam) LIKE '%' || lower(?) || '%'
           ORDER BY (locatie_id = ?) DESC, length(naam) ASC
           LIMIT 1""",
        [query, query, query],
    ).fetchone()
    return row[0] if row else None


def get_intake_capacity(conn: Any, intake_id: str, outage_weeks: int = 0) -> dict:
    """Production capacity for a resolved intake id, plus alternative-source
    coverage if the primary is down. Joins on the locked key (S1)."""
    primary = conn.execute(
        """SELECT p.locatie_id, p.productie_cap_m3_dag, p.cl_threshold_mg_l,
                  p.behandel_tech, p.status, w.naam, w.capaciteit_m3_dag
           FROM productieketen p
           JOIN winlocaties w ON w.locatie_id = p.intake_id
           WHERE p.intake_id = ?
           LIMIT 1""",
        [intake_id],
    ).fetchone()
    alternatives = conn.execute(
        """SELECT ab.max_capaciteit_m3_dag
           FROM alternatieve_bronnen ab
           WHERE ab.intake_id = ?""",
        [intake_id],
    ).fetchall()
    alt_capacity = sum(a[0] for a in alternatives) if alternatives else 0.0
    return {
        "locatie_id": primary[0] if primary else None,
        "production_cap_m3": primary[1] if primary else 0.0,
        "cl_threshold_mg_l": primary[2] if primary else None,
        "cl_threshold_from_db": (primary[2] is not None) if primary else False,
        "treatment_tech": primary[3] if primary else None,
        "intake_naam": primary[5] if primary else intake_id,
        "alternative_cap_m3": alt_capacity,
        "net_capacity_if_down": alt_capacity if outage_weeks > 0 else (primary[1] if primary else 0.0),
    }
