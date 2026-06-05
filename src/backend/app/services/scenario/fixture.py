"""Synthetic DuckDB fixture matching the DESIGN DOC's assumed schema.

Why this exists: the bundled hackathon datasets do NOT contain the operational
tables the scenario engine needs (no leveringszones with capaciteit/vraag, no
per-intake cl_threshold_mg_l, and drinkwater_productieketen /
toestandsbeoordeling are empty). See the coverage report. To prove the engine's
LOGIC end-to-end we build a tiny in-memory database shaped the way the design
doc specifies. Swap this for register_tables(con) once real operational data is
available (see COVERAGE_REPORT → "Running on real data").
"""
from __future__ import annotations

import duckdb


def build_synthetic_db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()  # in-memory
    con.execute("""
        CREATE TABLE winlocaties (
            locatie_id VARCHAR, naam VARCHAR, capaciteit_m3_dag DOUBLE
        );
        INSERT INTO winlocaties VALUES
            ('WIN_IJSSEL', 'Inname Hollandse IJssel (Gouda)', 240000),
            ('WIN_LEK',    'Inname Lek (Bergambacht)',        180000);

        CREATE TABLE productieketen (
            locatie_id VARCHAR, intake_id VARCHAR, productie_cap_m3_dag DOUBLE,
            behandel_tech VARCHAR, cl_threshold_mg_l DOUBLE,
            threshold_source VARCHAR, threshold_last_updated DATE, status VARCHAR
        );
        INSERT INTO productieketen VALUES
            ('PK_IJSSEL','WIN_IJSSEL',240000,'coagulatie+actiefkool',200,
             'Dunea operationele norm', DATE '2025-01-01','actief'),
            ('PK_LEK','WIN_LEK',180000,'oeverinfiltratie',150,
             'Drinkwaterbesluit', DATE '2024-01-01','actief');

        CREATE TABLE alternatieve_bronnen (
            bron_id VARCHAR, intake_id VARCHAR, max_capaciteit_m3_dag DOUBLE,
            activatie_tijd_uur INT, type VARCHAR
        );
        INSERT INTO alternatieve_bronnen VALUES
            ('ALT_LEK','WIN_IJSSEL',60000,48,'interconnectie');

        CREATE TABLE leveringszones (
            zone_id VARCHAR, naam VARCHAR, capaciteit_m3_dag DOUBLE,
            vraag_2023_m3_dag DOUBLE, h3_id VARCHAR, intake_id VARCHAR
        );
        INSERT INTO leveringszones VALUES
            ('ZONE_PIJNACKER','Pijnacker-Nootdorp e.o.',150000,138000,'88a1','WIN_IJSSEL'),
            ('ZONE_GOUDA',    'Gouda e.o.',             210000,170000,'88a2','WIN_IJSSEL');

        CREATE TABLE innamepunten_chloride (intake_id VARCHAR, datum DATE, cl_mg_l DOUBLE);
        INSERT INTO innamepunten_chloride VALUES
            ('WIN_IJSSEL', CURRENT_DATE - INTERVAL 5 DAY, 145),
            ('WIN_IJSSEL', CURRENT_DATE - INTERVAL 2 DAY, 162);

        CREATE TABLE krw_waterlichamen (
            lichaam_id VARCHAR, naam VARCHAR, status_2023 VARCHAR,
            krw_doeljaar INT, zone_id VARCHAR
        );
        INSERT INTO krw_waterlichamen VALUES
            ('KRW_HIJ','Hollandse IJssel','matig',2027,'ZONE_GOUDA'),
            ('KRW_PLAS','Recreatieplas','goed',2027,'ZONE_PIJNACKER');
    """)
    return con


def find_zone_by_name(con, location_name: str | None) -> dict | None:
    if not location_name:
        row = con.execute(
            "SELECT zone_id, naam, capaciteit_m3_dag, vraag_2023_m3_dag, h3_id, intake_id "
            "FROM leveringszones LIMIT 1").fetchone()
    else:
        row = con.execute(
            "SELECT zone_id, naam, capaciteit_m3_dag, vraag_2023_m3_dag, h3_id, intake_id "
            "FROM leveringszones WHERE lower(naam) LIKE '%' || lower(?) || '%' "
            "ORDER BY length(naam) ASC LIMIT 1", [location_name]).fetchone()
        if not row:  # nearest-zone fallback (design doc E007)
            row = con.execute(
                "SELECT zone_id, naam, capaciteit_m3_dag, vraag_2023_m3_dag, h3_id, intake_id "
                "FROM leveringszones LIMIT 1").fetchone()
    if not row:
        return None
    keys = ["zone_id", "naam", "capaciteit_m3_dag", "vraag_2023_m3_dag", "h3_id", "intake_id"]
    return dict(zip(keys, row))
