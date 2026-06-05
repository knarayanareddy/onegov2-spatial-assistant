"""Scenario persistence + version-drift detection — SINGLE SOURCE OF TRUTH.

Fix C6. Keeps the §19.2 `ScenarioStore` / `scenarios` table (the superset:
it has stable_url and is_citizen_mode) and removes the §18 `ScenarioCache` /
`scenario_cache` class. /scenario/{id}, /verify, cumulative-load and
version-drift all assume this schema.

Cache key = compute_scenario_hash(params, assumption_overrides)  (fix C2).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import duckdb

# created_at is stored as an ISO-8601 string (set in Python) rather than a
# TIMESTAMPTZ: ISO strings sort chronologically, are portable, and avoid the
# DuckDB-Python tz runtime dependency (pytz). JSON payloads are VARCHAR for the
# same portability reason (no json-extension requirement to CREATE the table).
CREATE_SCENARIOS_TABLE = """
CREATE TABLE IF NOT EXISTS scenarios (
    scenario_id      VARCHAR PRIMARY KEY,
    scenario_hash    VARCHAR NOT NULL,
    params_json      VARCHAR NOT NULL,
    result_json      VARCHAR NOT NULL,
    dataset_versions VARCHAR NOT NULL,    -- JSON text: {table_name: last_modified_iso}
    git_commit       VARCHAR NOT NULL,
    created_at       VARCHAR NOT NULL,    -- ISO-8601 (UTC)
    stable_url       VARCHAR NOT NULL,
    is_citizen_mode  BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_scenario_hash ON scenarios(scenario_hash);
"""


class ScenarioStore:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn
        conn.execute(CREATE_SCENARIOS_TABLE)

    def get_by_hash(self, scenario_hash: str) -> dict | None:
        row = self.conn.execute(
            "SELECT result_json, dataset_versions, created_at, scenario_id, stable_url "
            "FROM scenarios WHERE scenario_hash = ? ORDER BY created_at DESC LIMIT 1",
            [scenario_hash],
        ).fetchone()
        if not row:
            return None
        return {
            "result_json": row[0],
            "dataset_versions_at_cache": json.loads(row[1]) if isinstance(row[1], str) else row[1],
            "cached_at": row[2],
            "scenario_id": row[3],
            "stable_url": row[4],
        }

    def get_by_id(self, scenario_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT result_json, dataset_versions, created_at, stable_url "
            "FROM scenarios WHERE scenario_id = ?",
            [scenario_id],
        ).fetchone()
        if not row:
            return None
        return {
            "result_json": row[0],
            "dataset_versions_at_cache": json.loads(row[1]) if isinstance(row[1], str) else row[1],
            "cached_at": row[2],
            "stable_url": row[3],
        }

    def list_recent(self, limit: int = 50) -> list[dict]:
        """Summary rows for the saved-scenario library (most recent first)."""
        rows = self.conn.execute(
            "SELECT scenario_id, scenario_hash, result_json, created_at, stable_url "
            "FROM scenarios ORDER BY created_at DESC LIMIT ?",
            [int(limit)],
        ).fetchall()
        out: list[dict] = []
        for sid, shash, result_json, created_at, stable_url in rows:
            card = json.loads(result_json) if isinstance(result_json, str) else (result_json or {})
            results = card.get("results", {}) if isinstance(card, dict) else {}
            out.append({
                "scenario_id": sid,
                "scenario_hash": shash,
                "created_at": created_at,
                "stable_url": stable_url,
                "question_nl": card.get("question_nl", "") if isinstance(card, dict) else "",
                "scenario_type": card.get("scenario_type", "") if isinstance(card, dict) else "",
                "feasibility_class": results.get("feasibility_class", ""),
                "score_avg": results.get("score_avg", 0),
            })
        return out

    def set(
        self,
        scenario_id: str,
        scenario_hash: str,
        params: dict,
        result: dict,
        dataset_versions: dict,
        git_commit: str,
        stable_url_base: str,
        is_citizen_mode: bool = False,
    ) -> str:
        stable_url = f"{stable_url_base}/scenario/{scenario_id}"
        created_at = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """INSERT INTO scenarios
                 (scenario_id, scenario_hash, params_json, result_json,
                  dataset_versions, git_commit, created_at, stable_url, is_citizen_mode)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (scenario_id) DO NOTHING""",
            [scenario_id, scenario_hash, json.dumps(params), json.dumps(result),
             json.dumps(dataset_versions), git_commit, created_at, stable_url, is_citizen_mode],
        )
        return stable_url


def detect_version_drift(
    dataset_versions_at_cache: dict,
    current_dataset_versions: dict,
) -> list[dict]:
    """Compare dataset versions at cache time vs now; return drifted tables."""
    drifted: list[dict] = []
    for table, cached_version in dataset_versions_at_cache.items():
        current = current_dataset_versions.get(table)
        if current and current != cached_version:
            drifted.append({
                "table": table,
                "cached_version": cached_version,
                "current_version": current,
                "warning_nl": (
                    f"Let op: tabel '{table}' is bijgewerkt sinds dit scenario werd berekend "
                    f"({cached_version} → {current}). Herbereken voor actuele uitkomst."
                ),
            })
    return drifted
