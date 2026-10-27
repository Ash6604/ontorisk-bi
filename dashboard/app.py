"""OntoRisk BI - Streamlit risk dashboard (Section 4.7).

    streamlit run dashboard/app.py      # from the project root, so .streamlit/config.toml is applied

Structure (Figure 4.4):
    Sidebar        - page navigation, OLAP filters (Region | Time period | Risk type), rule-mining thresholds
    Top bar        - breadcrumb, page title, warehouse status, search across entities / places / sectors
    Overview       - KPI cards (Risk Exposure Index, Avg Impact Score, Events in View, Top Rule Confidence),
                     exposure trend, strongest rule, roll-up / drill-down cube, risk mix, cluster snapshot
    Rules          - FP-Growth association rules re-mined for the current selection
    Clusters       - k-Means scatter (PCA projection) and cluster profiles
    Knowledge graph- semantic (SPARQL) query console over the RDF knowledge graph
    Event log      - the events in view
Every page responds to the sidebar filters and the search box.
Presentation (theme, components, chart style) lives in ui.py; data logic in logic.py.
"""
from __future__ import annotations

import sys
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

import logic  # noqa: E402
import ui  # noqa: E402
from ontorisk import config, semantic  # noqa: E402

RISK_ORDER = ["weather", "logistics", "policy", "supplier", "reputational"]
RISK_COLOR = dict(zip(RISK_ORDER, ui.SERIES))
MEASURES = {"events": "Events", "avg_impact": "Avg impact", "exposure": "Exposure"}

st.set_page_config(page_title="OntoRisk BI", page_icon=str(HERE / "assets" / "mark.svg"), layout="wide",
                   initial_sidebar_state="expanded")
st.logo(str(HERE / "assets" / "logo.svg"), icon_image=str(HERE / "assets" / "mark.svg"), size="large")
ui.inject()

if not config.WAREHOUSE_DB.exists() and not config.WAREHOUSE_DB.with_suffix(".sqlite").exists():
    ui.empty_state("database", "Warehouse not found",
                   "Run `python run_pipeline.py` from the project root to build it, then reload this page.")
    st.stop()


@st.cache_data(show_spinner=False)
def get_events():
    return logic.load_events()


@st.cache_data(show_spinner=False)
def get_clusters():
    return logic.load_clusters()


@st.cache_data(show_spinner="Mining association rules …")
def get_rules(event_ids: tuple, min_support: float, min_conf: float, min_lift: float):
    ev = get_events()
    return logic.rules_for_view(ev[ev["event_id"].isin(event_ids)], min_support, min_conf, min_lift)


@st.cache_resource(show_spinner="Loading knowledge graph …")
def get_graph():
    return semantic.load_graph()


def fmt_day(d) -> str:
    return pd.Timestamp(d).strftime("%#d %b %Y" if sys.platform == "win32" else "%-d %b %Y")


def chart(fig):
    st.plotly_chart(fig, theme=None, config=ui.PLOT_CONFIG)


# ================================================================== pages
def page_overview():
    k = logic.kpis(view, events, rules)
    ui.kpi_cards([
        dict(label="Risk exposure index", key="rei", value=k["risk_exposure_index"], decimals=0, icon="bolt",
             accent=ui.VIOLET, spark=list(monthly["exposure"]),
             trend=ui.trend_badge(logic.recent_change(monthly["exposure"])),
             note=f"last 3 mo vs prior · {k['exposure_share']:.0%} of total",
             help="Σ impact score × severity weight (Low 1, Medium 2, High 3) for events in view. "
                  "Trend compares the last 3 months in view with the 3 before."),
        dict(label="Avg impact score", key="avg", value=k["avg_impact"] if len(view) else None, decimals=2,
             unit="/ 10", icon="speed", accent=ui.CYAN, spark=list(monthly["avg_impact"]),
             trend=ui.trend_badge(logic.recent_change(monthly["avg_impact"])), note="last 3 mo vs prior"),
        dict(label="Events in view", key="events", value=k["events_in_view"], decimals=0, icon="stacks",
             accent=ui.BLUE, unit=f"of {len(events):,}", spark=list(monthly["events"]),
             trend=ui.trend_badge(logic.recent_change(monthly["events"])), note="last 3 mo vs prior"),
        dict(label="Top rule confidence", key="conf",
             value=None if k["top_rule_confidence"] is None else round(k["top_rule_confidence"] * 100),
             unit="%" if k["top_rule_confidence"] is not None else "", decimals=0, icon="hub", accent=ui.MAGENTA,
             progress=k["top_rule_confidence"] or 0,
             note=f"lift {rules.iloc[0]['lift']:.2f}× · {len(rules)} rules" if len(rules) else "no rules for this view",
             help="Confidence of the highest-lift rule mined for the current selection."),
    ])
    st.space("small")

    if not len(view):
        ui.empty_state("filter_alt_off", "No events match this scope",
                       "Widen the region, period or risk-type filters in the sidebar, or clear the search.")
        return

    left, right = st.columns([1.85, 1], gap="medium")
    with left.container(border=True, key="card_trend", height="stretch"):
        ui.card_head("Exposure over time", "Monthly risk exposure index for events in view", "monitoring",
                     badge=f"{len(monthly)} months")
        x = pd.to_datetime(monthly.index + "-01")
        fig = go.Figure(go.Scatter(
            x=x, y=monthly["exposure"], mode="lines", line=dict(color=ui.VIOLET, width=2.25),
            fill="tozeroy", fillgradient=dict(type="vertical", colorscale=[[0, "rgba(139,92,246,0)"],
                                                                           [1, "rgba(139,92,246,0.38)"]]),
            customdata=monthly[["events"]].to_numpy(),
            hovertemplate="%{x|%b %Y}<br>Exposure <b>%{y:,.0f}</b><br>%{customdata[0]} events<extra></extra>"))
        fig = ui.style(fig, 290, legend=False)
        fig.update_layout(hovermode="x unified", hoverlabel=dict(namelength=0))
        fig.update_xaxes(tickformat="%b %y", showspikes=True, spikecolor="#3F3F46", spikethickness=1,
                         spikedash="dot", spikemode="across")
        chart(fig)

    with right.container(border=True, key="cardfeature_rule", height="stretch"):
        if len(rules):
            top = rules.iloc[0]
            ui.rule_feature(logic.describe_items(top["antecedents"]).split(" · "),
                            logic.describe_items(top["consequents"]).split(" · "),
                            top["confidence"], top["lift"], top["support"], "Strongest signal in view")
            st.page_link(p_rules, label=f"Explore all {len(rules)} rules", icon=":material/arrow_forward:")
        else:
            ui.empty_state("rule", "No rules for this view", rules_note)

    left, right = st.columns([1.85, 1], gap="medium")
    with left.container(border=True, key="card_cube", height="stretch"):
        ui.card_head("Roll-up / drill-down", "Aggregate by geography and time · up to 8 largest members", "view_in_ar")
        with st.container(horizontal=True, wrap=True, gap="medium"):
            geo_level = st.segmented_control("Geography", list(logic.REGION_LEVELS), default="Region",
                                             width="content") or "Region"
            time_level = st.segmented_control("Time", list(logic.TIME_LEVELS), default="Quarter",
                                              width="content") or "Quarter"
            measure = st.segmented_control("Measure", list(MEASURES), format_func=MEASURES.get, default="events",
                                           width="content") or "events"
        cube = logic.olap_cube(view, geo_level, time_level, measure)
        top8 = cube.groupby(geo_level)[measure].sum().nlargest(8).index
        cube = cube[cube[geo_level].isin(top8)]
        members = sorted(view[logic.REGION_LEVELS[geo_level]].unique())
        cmap = {m: ui.SERIES[i % len(ui.SERIES)] for i, m in enumerate(members)}   # colour follows the member
        fig = px.bar(cube, x=time_level, y=measure, color=geo_level, color_discrete_map=cmap,
                     category_orders={geo_level: [m for m in members if m in set(top8)],
                                      time_level: sorted(cube[time_level].unique())},
                     barmode="stack" if measure != "avg_impact" else "group",
                     labels={measure: MEASURES[measure], time_level: ""})
        fig.update_traces(marker_line_color=ui.S2, marker_line_width=1.5,
                          hovertemplate="<b>%{fullData.name}</b> · %{x}<br>" + MEASURES[measure]
                                        + " <b>%{y:,.2f}</b><extra></extra>")
        chart(ui.style(fig, 340))

    with right.container(border=True, key="card_mix", height="stretch"):
        ui.card_head("Risk mix", "Share of exposure by risk type", "donut_large")
        mix = view.groupby("risk_type").apply(logic.exposure).sort_values(ascending=False)
        n_by_type = view["risk_type"].value_counts()
        ui.rows([dict(name=t.capitalize(), desc=f"{n_by_type[t]} events", value=f"{v / mix.sum():.0%}",
                      value_label=f"{v:,.0f}", color=RISK_COLOR.get(t, ui.MUTED), share=v / mix.max())
                 for t, v in mix.items()])
        st.space("small")
        ui.card_head("Clusters in view", "", "scatter_plot")
        cv = clusters[clusters["event_id"].isin(view["event_id"])]
        cl = cv.groupby(["cluster", "label"]).agg(n=("event_id", "count"), imp=("impact_score", "mean")).reset_index()
        ui.rows([dict(name=f"C{r.cluster} · {r.label}", desc=f"avg impact {r.imp:.2f}", value=f"{r.n}",
                      value_label="events", color=ui.SERIES[int(r.cluster) % len(ui.SERIES)])
                 for r in cl.itertuples()])
        st.page_link(p_clusters, label="Open cluster map", icon=":material/arrow_forward:")


def page_rules():
    if not len(rules):
        ui.empty_state("rule", "No rules meet the thresholds",
                       f"{rules_note}. Widen the filters or lower the rule-mining thresholds in the sidebar.")
        return
    top = rules.iloc[0]
    left, right = st.columns([1, 1.6], gap="medium")
    with left.container(border=True, key="cardfeature_top", height="stretch"):
        ui.rule_feature(logic.describe_items(top["antecedents"]).split(" · "),
                        logic.describe_items(top["consequents"]).split(" · "),
                        top["confidence"], top["lift"], top["support"], "Highest-lift rule")
        st.caption(rules_note)
    with right.container(border=True, key="card_rulemap", height="stretch"):
        ui.card_head("Rule landscape", "Support vs confidence · bubble size = lift", "bubble_chart",
                     badge=f"{len(rules)} rules")
        r = rules.copy()
        r["if"] = r["antecedents"].map(logic.describe_items)
        r["then"] = r["consequents"].map(logic.describe_items)
        fig = go.Figure(go.Scatter(
            x=r["support"], y=r["confidence"], mode="markers",
            marker=dict(size=r["lift"], sizemode="area", sizeref=r["lift"].max() / 26 ** 2, sizemin=5,
                        color=r["lift"], colorscale=[[0, "#3B2A6B"], [0.5, ui.VIOLET], [1, ui.CYAN]],
                        line=dict(width=1.5, color=ui.S2), opacity=0.95,
                        colorbar=dict(title=dict(text="Lift", font=dict(color=ui.MUTED, size=11)), thickness=8,
                                      outlinewidth=0, tickfont=dict(color=ui.MUTED, size=11), len=0.8)),
            customdata=r[["if", "then", "lift"]].to_numpy(),
            hovertemplate="<b>If</b> %{customdata[0]}<br><b>Then</b> %{customdata[1]}<br>"
                          "support %{x:.2f} · confidence %{y:.0%} · lift %{customdata[2]:.2f}×<extra></extra>"))
        fig = ui.style(fig, 300, legend=False)
        fig.update_xaxes(title_text="Support", tickformat=".0%", showgrid=True, gridcolor="#16181F")
        fig.update_yaxes(title_text="Confidence", tickformat=".0%")
        chart(fig)

    with st.container(border=True, key="card_ruletable"):
        ui.card_head("All rules", "Ranked by lift · antecedent → consequent", "table_rows")
        show = rules.head(50)[["antecedents", "consequents", "support", "confidence", "lift"]].copy()
        show["antecedents"] = show["antecedents"].map(logic.describe_items)
        show["consequents"] = show["consequents"].map(logic.describe_items)
        st.dataframe(show, hide_index=True, use_container_width=True, height=min(38 + 35 * len(show), 600),
                     column_config={
                         "antecedents": st.column_config.TextColumn("If", width="large"),
                         "consequents": st.column_config.TextColumn("Then", width="medium"),
                         "support": st.column_config.ProgressColumn("Support", format="%.2f", min_value=0,
                                                                    max_value=1, width="small"),
                         "confidence": st.column_config.ProgressColumn("Confidence", format="percent",
                                                                       min_value=0, max_value=1, width="small"),
                         "lift": st.column_config.NumberColumn("Lift", format="%.2f×", width="small")})


def page_clusters():
    cv = clusters[clusters["event_id"].isin(view["event_id"])].copy()
    if not len(cv):
        ui.empty_state("scatter_plot", "No events in this selection", "Widen the filters to see the cluster map.")
        return
    cv["cluster_label"] = "C" + cv["cluster"].astype(str) + " · " + cv["label"]
    labels = sorted(("C" + clusters["cluster"].astype(str) + " · " + clusters["label"]).unique())
    cmap = {lab: ui.SERIES[i % len(ui.SERIES)] for i, lab in enumerate(labels)}
    left, right = st.columns([1.85, 1], gap="medium")
    with left.container(border=True, key="card_scatter", height="stretch"):
        ui.card_head("k-Means cluster map", "Events projected onto the first two principal components", "scatter_plot",
                     badge=f"{len(cv)} events")
        fig = px.scatter(cv, x="pc1", y="pc2", color="cluster_label", category_orders={"cluster_label": labels},
                         color_discrete_map=cmap,
                         custom_data=["entity_name", "risk_type", "region", "severity", "impact_score"],
                         labels={"pc1": "Principal component 1", "pc2": "Principal component 2"})
        fig.update_traces(marker=dict(size=9, opacity=0.92, line=dict(width=1.5, color=ui.S2)),
                          hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}"
                                        "<br>Severity %{customdata[3]} · impact %{customdata[4]:.2f}<extra></extra>")
        fig = ui.style(fig, 500, legend=False)
        fig.update_xaxes(showgrid=True, gridcolor="#16181F")
        chart(fig)
    with right.container(border=True, key="card_profiles", height="stretch"):
        ui.card_head("Cluster profiles", "Size, average impact and dominant risk type", "category")
        prof = cv.groupby("cluster_label").agg(events=("event_id", "count"), avg_impact=("impact_score", "mean"),
                                               top_risk=("risk_type", lambda s: s.value_counts().index[0]))
        ui.rows([dict(name=lab, desc=f"Mostly {r.top_risk} · avg impact {r.avg_impact:.2f}", value=f"{r.events}",
                      value_label="events", color=cmap[lab], share=r.avg_impact / 10)
                 for lab, r in prof.iterrows()])
        st.caption("Bar length shows average impact on the 0–10 scale.")


def page_graph():
    left, right = st.columns([1, 2.1], gap="medium")
    with left.container(border=True, key="card_queries", height="stretch"):
        ui.card_head("Query library", "SPARQL over the RDF knowledge graph", "account_tree")
        name = st.selectbox("Example query", list(semantic.EXAMPLE_QUERIES))
        st.caption("Selecting an example loads it into the editor. The `ork:` prefix is pre-declared.")
    with right.container(border=True, key="card_editor", height="stretch"):
        ui.card_head("Editor", "", "code")
        q = st.text_area("SPARQL", semantic.EXAMPLE_QUERIES[name], height=190, label_visibility="collapsed")
        run = st.button("Run query", type="primary", icon=":material/play_arrow:")
    if run:
        try:
            cols, rows = semantic.run_query(get_graph(), q)
        except Exception as exc:  # show parse errors to the user
            st.error(f"Query failed: {exc}", icon=":material/error:")
            return
        with st.container(border=True, key="card_results"):
            ui.card_head("Results", "", "table_rows", badge=f"{len(rows):,} row{'s' if len(rows) != 1 else ''}")
            if rows:
                st.dataframe(pd.DataFrame(rows, columns=cols), hide_index=True, use_container_width=True)
            else:
                ui.empty_state("search_off", "No matches", "The query ran but returned no rows.")
    else:
        ui.empty_state("play_circle", "Run a query to see results",
                       "Pick an example from the library or write your own, then press Run query.")


def page_log():
    with st.container(border=True, key="card_log"):
        ui.card_head("Events in view", "Newest first · use the search box to narrow by entity, place or sector",
                     "receipt_long", badge=f"{len(view):,} events")
        if not len(view):
            ui.empty_state("search_off", "No events match", "Clear the search or widen the filters.")
            return
        log = view[["event_id", "date", "entity_name", "sector", "risk_type", "place", "state", "region",
                    "impact_score", "severity", "source_id"]].sort_values("date", ascending=False)
        st.dataframe(log, hide_index=True, use_container_width=True, height=620,
                     column_config={
                         "event_id": st.column_config.TextColumn("Event"),
                         "date": st.column_config.DateColumn("Date", format="D MMM YYYY"),
                         "entity_name": st.column_config.TextColumn("Entity", width="medium"),
                         "sector": "Sector", "risk_type": "Risk type", "place": "Place", "state": "State",
                         "region": "Region",
                         "impact_score": st.column_config.ProgressColumn("Impact", format="%.2f", min_value=0,
                                                                         max_value=10),
                         "severity": "Severity", "source_id": st.column_config.TextColumn("Source")})


# ================================================================== shared chrome
p_overview = st.Page(page_overview, title="Overview", icon=":material/space_dashboard:", url_path="overview",
                     default=True)
p_rules = st.Page(page_rules, title="Association rules", icon=":material/hub:", url_path="rules")
p_clusters = st.Page(page_clusters, title="Clusters", icon=":material/scatter_plot:", url_path="clusters")
p_graph = st.Page(page_graph, title="Knowledge graph", icon=":material/account_tree:", url_path="knowledge-graph")
p_log = st.Page(page_log, title="Event log", icon=":material/receipt_long:", url_path="events")
page = st.navigation({"Analyse": [p_overview, p_rules, p_clusters], "Explore": [p_graph, p_log]})

SUBTITLES = {
    "Overview": "Risk exposure, the strongest co-occurrence signal and where it concentrates across regions and time.",
    "Association rules": "FP-Growth rules re-mined on the events in view — which risk factors travel together.",
    "Clusters": "k-Means groups of risk events by impact, type and season, projected to two dimensions.",
    "Knowledge graph": "Query the ontology-backed RDF graph directly with SPARQL.",
    "Event log": "Every risk event in the current scope, traced back to its source article.",
}

events = get_events()
clusters = get_clusters()
dmin, dmax = events["date"].min().date(), events["date"].max().date()

with st.sidebar:
    st.html(f'<p class="or-side-label">{ui.icon("tune")}Scope</p>')
    regions = st.multiselect("Region", sorted(events["region"].unique()), placeholder="All regions")
    period = st.date_input("Time period", (dmin, dmax), min_value=dmin, max_value=dmax, format="DD/MM/YYYY")
    risk_types = st.multiselect("Risk type", [t for t in RISK_ORDER if t in set(events["risk_type"])],
                                format_func=str.capitalize, placeholder="All risk types")
    st.html(f'<p class="or-side-label">{ui.icon("hub")}Rule mining</p>')
    min_support = st.slider("Min support", 0.02, 0.30, config.MIN_SUPPORT, 0.01)
    min_conf = st.slider("Min confidence", 0.30, 0.95, config.MIN_CONFIDENCE, 0.05)
    min_lift = st.slider("Min lift", 1.0, 3.0, config.MIN_LIFT, 0.05)
    st.html('<div class="or-side-foot"><b>Pipeline</b><br>News text → RDF triples → DuckDB star schema → '
            'FP-Growth rules &amp; k-Means clusters. Rules are re-mined for every selection.</div>')

head, side = st.columns([2.2, 1], vertical_alignment="bottom", gap="large")
db = config.WAREHOUSE_DB if config.WAREHOUSE_DB.exists() else config.WAREHOUSE_DB.with_suffix(".sqlite")
with side:
    ui.status_pill(len(events), f"{datetime.fromtimestamp(db.stat().st_mtime):%d %b}")
    query = st.text_input("Search", key="q", placeholder="Search entities, places, sectors…",
                          icon=":material/search:", label_visibility="collapsed")
start, end = (period if isinstance(period, (list, tuple)) and len(period) == 2 else (dmin, dmax))
view = logic.apply_filters(events, regions, risk_types, start, end, query)
rules, rules_note = get_rules(tuple(sorted(view["event_id"])), min_support, min_conf, min_lift)
monthly = logic.monthly_series(view)

with head:
    ui.topbar(page.title, page.title, SUBTITLES.get(page.title, ""))

ui.divider()
ui.scope_tags([
    ("public", ", ".join(regions) if regions else "All regions", bool(regions)),
    ("category", ", ".join(t.capitalize() for t in risk_types) if risk_types else "All risk types", bool(risk_types)),
    ("calendar_month", f"{fmt_day(start)} – {fmt_day(end)}", (start, end) != (dmin, dmax)),
    *([("search", f"“{query.strip()}”", True)] if query and query.strip() else []),
    ("stacks", f"{len(view):,} of {len(events):,} events", len(view) != len(events)),
])
st.space("small")

page.run()
