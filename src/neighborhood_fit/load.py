"""Load Zillow ZORI (ZIP level) and seed data into DuckDB."""
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
ZORI_CSV = ROOT / "data/raw/Zip_zori_uc_sfrcondomfr_sm_month.csv"
SEED = ROOT / "data/seed"
DB_PATH = ROOT / "build/fit.duckdb"


def build(db_path: Path = DB_PATH, zori_csv: Path = ZORI_CSV) -> duckdb.DuckDBPyConnection:
    db_path.parent.mkdir(exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute(f"""
        CREATE OR REPLACE TABLE neighborhoods AS
        SELECT * REPLACE (CAST(zip AS VARCHAR) AS zip)
        FROM read_csv('{SEED / "neighborhoods.csv"}', types={{'zip': 'VARCHAR'}})
    """)
    con.execute(f"CREATE OR REPLACE TABLE hubs AS SELECT * FROM read_csv('{SEED / 'hubs.csv'}')")
    # Long format, only the ZIPs we care about; drop months with no value.
    con.execute(f"""
        CREATE OR REPLACE TABLE zori AS
        WITH raw AS (
            SELECT * FROM read_csv('{zori_csv}', types={{'RegionName': 'VARCHAR'}})
            WHERE RegionName IN (SELECT zip FROM neighborhoods)
        )
        SELECT RegionName AS zip, CAST(month AS DATE) AS month, rent
        FROM (UNPIVOT raw ON COLUMNS('^\\d{{4}}-\\d{{2}}-\\d{{2}}$') INTO NAME month VALUE rent)
        WHERE rent IS NOT NULL
    """)
    # Latest rent plus rent ~12 months earlier per ZIP.
    con.execute("""
        CREATE OR REPLACE TABLE rent_latest AS
        WITH latest AS (
            SELECT zip, max(month) AS month FROM zori GROUP BY zip
        )
        SELECT l.zip, l.month AS as_of, z.rent AS rent,
               p.rent AS rent_year_ago,
               round(100 * (z.rent / p.rent - 1), 1) AS yoy_pct
        FROM latest l
        JOIN zori z ON z.zip = l.zip AND z.month = l.month
        LEFT JOIN zori p ON p.zip = l.zip AND p.month = l.month - INTERVAL 12 MONTH
    """)
    return con


def missing_zips(con) -> list[str]:
    rows = con.execute("""
        SELECT DISTINCT n.zip FROM neighborhoods n
        LEFT JOIN rent_latest r USING (zip) WHERE r.rent IS NULL ORDER BY 1
    """).fetchall()
    return [r[0] for r in rows]


if __name__ == "__main__":
    con = build()
    print(con.sql("""
        SELECT n.name, n.zip, r.as_of, round(r.rent) AS rent, r.yoy_pct
        FROM neighborhoods n LEFT JOIN rent_latest r USING (zip) ORDER BY rent
    """))
    miss = missing_zips(con)
    if miss:
        print("MISSING ZORI for ZIPs:", ", ".join(miss), file=sys.stderr)
        sys.exit(1)
