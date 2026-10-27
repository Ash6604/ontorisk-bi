"""Stage 6 - Hybrid warehouse: DuckDB star schema + linked semantic triples.

Star schema (Table 4.1):
    FACT_RISKEVENT(event_id, time_key, location_key, risktype_key, entity_name,
                   sector, source_id, impact_score, severity, mention_count)
    DIM_TIME(time_key, date, week, month, quarter, year)
    DIM_LOCATION(location_key, place, region, state, country)
    DIM_RISKTYPE(risktype_key, category, sub_type)
Entity and source are *degenerate attributes* on the fact row (Kimball).

Semantic side of the hybrid warehouse:
    BRIDGE_SEMANTIC_LINK(event_id, subject, predicate, object) - every RDF
    triple produced for an event, keyed by the shared event_id, so a SQL query
    can jump from a fact row to its triples and a SPARQL result (ork:eventId)
    can jump back to the fact row.
Staging: STG_ARTICLES holds the cleaned corpus.

DuckDB is used when installed (embedded, serverless, columnar, reads Pandas
DataFrames directly).  If it is missing, SQLite (Python standard library) is
used with the identical schema so the project still runs - ``ENGINE`` says
which one is active.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from . import config

try:
    import duckdb
    ENGINE = f"DuckDB {duckdb.__version__}"
except Exception:  # pragma: no cover
    duckdb = None
    ENGINE = "SQLite (fallback - DuckDB not installed)"

DDL = [
    """CREATE TABLE DIM_TIME (
        time_key INTEGER PRIMARY KEY, date DATE NOT NULL, week INTEGER, month INTEGER,
        month_name VARCHAR, quarter INTEGER, year INTEGER)""",
    """CREATE TABLE DIM_LOCATION (
        location_key INTEGER PRIMARY KEY, place VARCHAR NOT NULL, region VARCHAR,
        state VARCHAR, country VARCHAR)""",
    """CREATE TABLE DIM_RISKTYPE (
        risktype_key INTEGER PRIMARY KEY, category VARCHAR NOT NULL, sub_type VARCHAR)""",
    """CREATE TABLE FACT_RISKEVENT (
        event_id VARCHAR PRIMARY KEY,
        time_key INTEGER REFERENCES DIM_TIME(time_key),
        location_key INTEGER REFERENCES DIM_LOCATION(location_key),
        risktype_key INTEGER REFERENCES DIM_RISKTYPE(risktype_key),
        entity_name VARCHAR, sector VARCHAR, source_id VARCHAR,
        impact_score DOUBLE, severity VARCHAR, mention_count INTEGER)""",
    """CREATE TABLE BRIDGE_SEMANTIC_LINK (
        event_id VARCHAR REFERENCES FACT_RISKEVENT(event_id),
        subject VARCHAR, predicate VARCHAR, object VARCHAR)""",
    """CREATE TABLE STG_ARTICLES (
        article_id VARCHAR PRIMARY KEY, title VARCHAR, date DATE, source VARCHAR, text VARCHAR)""",
]
LOAD_ORDER = ["DIM_TIME", "DIM_LOCATION", "DIM_RISKTYPE", "FACT_RISKEVENT", "BRIDGE_SEMANTIC_LINK", "STG_ARTICLES"]

# Denormalised view used by the dashboard and the miners
VIEW_SQL = """
CREATE VIEW V_RISK_EVENTS AS
SELECT f.event_id, f.entity_name, f.sector, f.source_id, f.impact_score, f.severity, f.mention_count,
       t.date, t.week, t.month, t.month_name, t.quarter, t.year,
       l.place, l.region, l.state, l.country,
       r.category AS risk_type, r.sub_type
FROM FACT_RISKEVENT f
JOIN DIM_TIME t      ON f.time_key = t.time_key
JOIN DIM_LOCATION l  ON f.location_key = l.location_key
JOIN DIM_RISKTYPE r  ON f.risktype_key = r.risktype_key
"""


class Warehouse:
    """Thin wrapper so the same code runs on DuckDB or SQLite."""

    def __init__(self, path: Path | str = config.WAREHOUSE_DB, read_only: bool = False):
        self.path = Path(path)
        if duckdb is not None:
            self.con = duckdb.connect(str(self.path), read_only=read_only)
            self.kind = "duckdb"
        else:
            self.path = self.path.with_suffix(".sqlite")
            self.con = sqlite3.connect(str(self.path), check_same_thread=False)
            self.kind = "sqlite"

    def execute(self, sql: str):
        return self.con.execute(sql)

    def query(self, sql: str) -> pd.DataFrame:
        if self.kind == "duckdb":
            return self.con.execute(sql).df()
        return pd.read_sql_query(sql, self.con)

    def load(self, table: str, df: pd.DataFrame) -> None:
        if self.kind == "duckdb":
            self.con.register("_tmp_df", df)
            self.con.execute(f"INSERT INTO {table} SELECT * FROM _tmp_df")
            self.con.unregister("_tmp_df")
        else:
            out = df.copy()
            for c in out.columns:
                if pd.api.types.is_datetime64_any_dtype(out[c]):
                    out[c] = out[c].dt.strftime("%Y-%m-%d")
            out.to_sql(table, self.con, if_exists="append", index=False)
            self.con.commit()

    def close(self):
        self.con.close()


def reset(path: Path | str = config.WAREHOUSE_DB) -> Warehouse:
    p = Path(path)
    for f in (p, p.with_suffix(".sqlite"), Path(str(p) + ".wal")):
        if f.exists():
            f.unlink()
    wh = Warehouse(p)
    for stmt in DDL:
        wh.execute(stmt)
    wh.execute(VIEW_SQL)
    return wh


def build_dimensions(events: pd.DataFrame):
    vocab = json.loads(config.VOCAB_JSON.read_text())["risk_types"]
    dates = pd.to_datetime(events["date"]).dt.normalize().drop_duplicates().sort_values()
    dim_time = pd.DataFrame({
        "time_key": dates.dt.strftime("%Y%m%d").astype(int).values,
        "date": dates.dt.date.values,
        "week": dates.dt.isocalendar().week.astype(int).values,
        "month": dates.dt.month.values,
        "month_name": dates.dt.strftime("%b").values,
        "quarter": dates.dt.quarter.values,
        "year": dates.dt.year.values,
    })
    locs = events[["location", "region", "state", "country"]].drop_duplicates("location") \
        .sort_values(["region", "state", "location"]).reset_index(drop=True)
    dim_loc = pd.DataFrame({"location_key": range(1, len(locs) + 1), "place": locs["location"],
                            "region": locs["region"], "state": locs["state"], "country": locs["country"]})
    cats = list(vocab)
    dim_rt = pd.DataFrame({"risktype_key": range(1, len(cats) + 1), "category": cats,
                           "sub_type": [vocab[c]["sub_type"] for c in cats]})
    return dim_time, dim_loc, dim_rt


def build_fact(events: pd.DataFrame, dim_loc: pd.DataFrame, dim_rt: pd.DataFrame) -> pd.DataFrame:
    loc_key = dict(zip(dim_loc["place"], dim_loc["location_key"]))
    rt_key = dict(zip(dim_rt["category"], dim_rt["risktype_key"]))
    return pd.DataFrame({
        "event_id": events["event_id"].values,
        "time_key": pd.to_datetime(events["date"]).dt.strftime("%Y%m%d").astype(int).values,
        "location_key": events["location"].map(loc_key).astype(int).values,
        "risktype_key": events["risk_type"].map(rt_key).astype(int).values,
        "entity_name": events["entity_name"].values,
        "sector": events["sector"].values,
        "source_id": events["article_id"].values,
        "impact_score": events["impact_score"].astype(float).values,
        "severity": events["severity"].values,
        "mention_count": events["mention_count"].astype(int).values,
    })


def referential_checks(wh: Warehouse) -> dict:
    checks = {
        "fact_rows": "SELECT COUNT(*) AS n FROM FACT_RISKEVENT",
        "orphan_time": "SELECT COUNT(*) AS n FROM FACT_RISKEVENT f LEFT JOIN DIM_TIME t ON f.time_key=t.time_key WHERE t.time_key IS NULL",
        "orphan_location": "SELECT COUNT(*) AS n FROM FACT_RISKEVENT f LEFT JOIN DIM_LOCATION l ON f.location_key=l.location_key WHERE l.location_key IS NULL",
        "orphan_risktype": "SELECT COUNT(*) AS n FROM FACT_RISKEVENT f LEFT JOIN DIM_RISKTYPE r ON f.risktype_key=r.risktype_key WHERE r.risktype_key IS NULL",
        "facts_without_triples": "SELECT COUNT(*) AS n FROM FACT_RISKEVENT f WHERE NOT EXISTS (SELECT 1 FROM BRIDGE_SEMANTIC_LINK b WHERE b.event_id=f.event_id)",
        "null_measures": "SELECT COUNT(*) AS n FROM FACT_RISKEVENT WHERE impact_score IS NULL OR severity IS NULL",
    }
    return {k: int(wh.query(q)["n"].iloc[0]) for k, q in checks.items()}
