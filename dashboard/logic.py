"""Dashboard data layer - pure functions (no Streamlit), so they are unit-tested.

KPI definitions (Table 4.3)
    Risk Exposure Index  = sum over events in view of impact_score x severity weight
                           (Low=1, Medium=2, High=3); shown with its share of the
                           exposure of the whole warehouse.
    Average Impact Score = mean impact_score of events in view.
    Events in View       = count of events matching the filters.
    Top Rule Confidence  = confidence of the highest-ranked (by lift) rule shown.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ontorisk import config, mining  # noqa: E402
from ontorisk.warehouse import Warehouse  # noqa: E402

REGION_LEVELS = {"Region": "region", "State": "state", "Place": "place"}
TIME_LEVELS = {"Year": "year", "Quarter": "quarter_label", "Month": "month_label"}


def load_events(db_path=config.WAREHOUSE_DB) -> pd.DataFrame:
    wh = Warehouse(db_path, read_only=True)
    try:
        ev = wh.query("SELECT * FROM V_RISK_EVENTS")
    finally:
        wh.close()
    ev["date"] = pd.to_datetime(ev["date"])
    ev["quarter_label"] = ev["year"].astype(str) + "-Q" + ev["quarter"].astype(str)
    ev["month_label"] = ev["date"].dt.strftime("%Y-%m")
    return ev


def load_clusters() -> pd.DataFrame:
    return pd.read_csv(config.OUTPUT_DIR / "clusters.csv")


SEARCH_COLUMNS = ["entity_name", "sector", "place", "state", "region", "risk_type", "event_id"]


def apply_filters(ev: pd.DataFrame, regions=None, risk_types=None, start=None, end=None, query=None) -> pd.DataFrame:
    m = pd.Series(True, index=ev.index)
    if query and query.strip():
        q = query.strip().lower()
        m &= ev[SEARCH_COLUMNS].astype(str).apply(lambda col: col.str.lower().str.contains(q, regex=False)).any(axis=1)
    if regions:
        m &= ev["region"].isin(regions)
    if risk_types:
        m &= ev["risk_type"].isin(risk_types)
    if start is not None:
        m &= ev["date"] >= pd.Timestamp(start)
    if end is not None:
        m &= ev["date"] <= pd.Timestamp(end)
    return ev[m]


def exposure(df: pd.DataFrame) -> float:
    return float((df["impact_score"] * df["severity"].map(config.SEVERITY_WEIGHT)).sum())


def kpis(view: pd.DataFrame, all_events: pd.DataFrame, rules: pd.DataFrame) -> dict:
    total = exposure(all_events)
    rei = exposure(view)
    return {
        "risk_exposure_index": round(rei, 1),
        "exposure_share": round(rei / total, 4) if total else 0.0,
        "avg_impact": round(float(view["impact_score"].mean()), 2) if len(view) else 0.0,
        "events_in_view": int(len(view)),
        "top_rule_confidence": round(float(rules["confidence"].iloc[0]), 4) if len(rules) else None,
    }


def monthly_series(view: pd.DataFrame) -> pd.DataFrame:
    """Per-month events, mean impact and exposure for the view (feeds KPI sparklines and the trend chart)."""
    by_month = view.groupby("month_label")
    out = by_month.agg(events=("event_id", "count"), avg_impact=("impact_score", "mean"))
    out["exposure"] = [exposure(g) for _, g in by_month]
    return out


def recent_change(values, window: int = 3) -> float | None:
    """Relative change of the last `window` periods vs the `window` before them (None if too short)."""
    vals = list(values)
    if len(vals) < 2 * window:
        return None
    prev, last = sum(vals[-2 * window:-window]) / window, sum(vals[-window:]) / window
    return (last - prev) / prev if prev else None


def rules_for_view(view: pd.DataFrame, min_support=config.MIN_SUPPORT, min_conf=config.MIN_CONFIDENCE,
                   min_lift=config.MIN_LIFT, min_events: int = 25) -> tuple[pd.DataFrame, str]:
    """Re-mine FP-Growth rules on the filtered events (the table responds to the filters).

    For very small selections there is not enough data for rules to be meaningful,
    so an empty table is returned together with an explanatory note.
    """
    if len(view) < min_events:
        return pd.DataFrame(), f"Only {len(view)} events in view - at least {min_events} are needed to mine rules."
    rules, _ = mining.mine_rules(view, min_support=min_support, min_conf=min_conf, min_lift=min_lift)
    return rules, f"FP-Growth on {len(view)} events in view (support >= {min_support:.0%}, confidence >= {min_conf:.0%}, lift >= {min_lift})"


ITEM_LABELS = {"co_risk": "Co-risk", "risktype": "Risk type", "sector": "Sector", "severity": "Severity",
               "region": "Region"}


def describe_items(itemset: str, sep: str = " · ") -> str:
    """'co_risk=logistics, severity=High' -> 'Co-risk: logistics · Severity: High'."""
    parts = []
    for item in str(itemset).split(", "):
        key, _, value = item.partition("=")
        parts.append(f"{ITEM_LABELS.get(key, key.replace('_', ' ').capitalize())}: {value}" if value else item)
    return sep.join(parts)


def olap_cube(view: pd.DataFrame, region_level="Region", time_level="Quarter", measure="events") -> pd.DataFrame:
    """Roll-up / drill-down: aggregate the view at the chosen hierarchy levels."""
    r, t = REGION_LEVELS[region_level], TIME_LEVELS[time_level]
    agg = view.groupby([t, r]).agg(events=("event_id", "count"), avg_impact=("impact_score", "mean"),
                                    exposure=("impact_score", lambda s: exposure(view.loc[s.index])))
    return agg[[measure]].reset_index().rename(columns={t: time_level, r: region_level})
