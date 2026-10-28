"""Static result figures written to outputs/figures (used in the explanation report)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from . import config  # noqa: E402

# Validated categorical palette (fixed order, never cycled) + recessive ink
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]
RISK_ORDER = ["weather", "logistics", "policy", "supplier", "reputational"]
RISK_COLOR = dict(zip(RISK_ORDER, SERIES))
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 9,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
})


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(config.FIG_DIR / name, dpi=170)
    plt.close(fig)


def events_by_type_region(ev: pd.DataFrame):
    tab = pd.crosstab(ev["region"], ev["risk_type"]).reindex(columns=RISK_ORDER, fill_value=0)
    tab = tab.loc[tab.sum(axis=1).sort_values().index]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    left = pd.Series(0, index=tab.index)
    for t in RISK_ORDER:
        ax.barh(tab.index, tab[t], left=left, color=RISK_COLOR[t], label=t, height=0.62,
                edgecolor=SURFACE, linewidth=1.5)
        left += tab[t]
    for y, v in enumerate(left):
        ax.text(v + 0.8, y, str(int(v)), va="center", color=INK2, fontsize=8)
    ax.set_title("Risk events by region and risk type", pad=24)
    ax.set_xlabel("Number of risk events")
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, ncol=5, loc="lower left", fontsize=8, bbox_to_anchor=(0, 1.0))
    _save(fig, "events_by_region_type.png")


def monthly_trend(ev: pd.DataFrame):
    m = pd.to_datetime(ev["date"]).dt.month
    tab = pd.crosstab(m, ev["risk_type"]).reindex(index=range(1, 13), columns=RISK_ORDER, fill_value=0)
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    for i, t in enumerate(RISK_ORDER):
        ax.plot(tab.index, tab[t], color=RISK_COLOR[t], lw=2, marker=MARKERS[i], ms=4.5, label=t)
    ax.axvspan(5.5, 9.5, color="#2a78d6", alpha=0.06, lw=0)
    ax.text(7.5, ax.get_ylim()[1] * 0.95, "SW monsoon (Jun-Sep)", ha="center", va="top", color=INK2, fontsize=8)
    ax.set_xticks(range(1, 13), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.set_title("Seasonality: risk events per calendar month (2024-2025)")
    ax.set_ylabel("Events")
    ax.legend(frameon=False, ncol=5, fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.12))
    _save(fig, "monthly_trend.png")


def elbow(diag: dict):
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    axes[0].plot(diag["k_values"], diag["inertia"], color=SERIES[0], lw=2, marker="o", ms=5)
    axes[0].axvline(diag["k_chosen"], color=INK2, lw=1, ls="--")
    axes[0].set_title("Elbow method (inertia)")
    axes[0].set_xlabel("k")
    axes[1].plot(diag["k_values"], diag["silhouette"], color=SERIES[1], lw=2, marker="s", ms=5)
    axes[1].axvline(diag["k_chosen"], color=INK2, lw=1, ls="--")
    axes[1].set_title("Silhouette score")
    axes[1].set_xlabel("k")
    axes[0].annotate(f"chosen k = {diag['k_chosen']}", (diag["k_chosen"], max(diag["inertia"]) * 0.9),
                     xytext=(6, 0), textcoords="offset points", color=INK2, fontsize=8)
    _save(fig, "kmeans_elbow_silhouette.png")


def cluster_scatter(cl: pd.DataFrame, diag: dict):
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    labels = cl.drop_duplicates("cluster").set_index("cluster")["label"].sort_index()
    for i, (c, lab) in enumerate(labels.items()):
        d = cl[cl.cluster == c]
        ax.scatter(d.pc1, d.pc2, s=26, color=SERIES[i % len(SERIES)], marker=MARKERS[i % len(MARKERS)],
                   edgecolor=SURFACE, linewidth=0.8, label=f"C{c}: {lab} (n={len(d)})", alpha=0.9)
    ev = diag["pca_explained_variance"]
    ax.set_xlabel(f"PC1 ({ev[0]:.0%} variance)")
    ax.set_ylabel(f"PC2 ({ev[1]:.0%} variance)")
    ax.set_title(f"k-Means clusters of risk events (k={diag['k_chosen']}, silhouette={diag['silhouette_chosen']:.2f})")
    ax.legend(frameon=False, fontsize=7.5, loc="upper left", bbox_to_anchor=(0, -0.13), ncol=2)
    _save(fig, "kmeans_clusters.png")


def top_rules(rules: pd.DataFrame, n=12):
    r = rules.head(n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8.4, 0.36 * len(r) + 1.2))
    labels = [f"{a}  =>  {c}" for a, c in zip(r.antecedents, r.consequents)]
    ax.barh(range(len(r)), r["lift"], color=SERIES[0], height=0.6)
    for y, (lift, conf, sup) in enumerate(zip(r.lift, r.confidence, r.support)):
        ax.text(lift + 0.05, y, f"lift {lift:.2f} | conf {conf:.0%} | sup {sup:.0%}", va="center",
                fontsize=7, color=INK2)
    ax.set_yticks(range(len(r)), labels, fontsize=6.6)
    ax.set_xlim(0, r["lift"].max() * 1.95 if len(r) else 1)
    ax.set_xlabel("Lift")
    fig.suptitle("Top association rules (FP-Growth) ranked by lift", x=0.02, ha="left", fontsize=11,
                 fontweight="bold")
    ax.grid(axis="y", visible=False)
    _save(fig, "top_rules.png")


def severity_by_type(ev: pd.DataFrame):
    order = ["Low", "Medium", "High"]
    tab = pd.crosstab(ev["risk_type"], ev["severity"], normalize="index").reindex(index=RISK_ORDER, columns=order, fill_value=0)
    seq = ["#b7d3f2", "#5b9be3", "#1c5aa6"]                         # one hue, light -> dark
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    left = pd.Series(0.0, index=tab.index)
    for s, col in zip(order, seq):
        ax.barh(tab.index, tab[s], left=left, color=col, label=s, height=0.6, edgecolor=SURFACE, linewidth=1.5)
        for y, (l, v) in enumerate(zip(left, tab[s])):
            if v > 0.08:
                ax.text(l + v / 2, y, f"{v:.0%}", ha="center", va="center", fontsize=7.5,
                        color="white" if s != "Low" else INK)
        left += tab[s]
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_title("Severity mix by risk type", pad=24)
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, ncol=3, fontsize=8, loc="lower left", bbox_to_anchor=(0, 1.0))
    _save(fig, "severity_by_type.png")


def make_all(ev, rules, clusters, diag, metrics):
    config.FIG_DIR.mkdir(parents=True, exist_ok=True)
    events_by_type_region(ev)
    monthly_trend(ev)
    severity_by_type(ev)
    elbow(diag)
    cluster_scatter(clusters, diag)
    if len(rules):
        top_rules(rules)
        dashboard_preview(ev, rules, clusters)


def dashboard_preview(ev: pd.DataFrame, rules: pd.DataFrame, cl: pd.DataFrame):
    """Static rendering of the dashboard's content (all events, no filter) for documentation."""
    sev_w = ev["severity"].map(config.SEVERITY_WEIGHT)
    rei = float((ev["impact_score"] * sev_w).sum())
    fig = plt.figure(figsize=(8.6, 8.0))
    gs = fig.add_gridspec(4, 4, height_ratios=[0.5, 0.22, 1.25, 1.9], hspace=0.42, wspace=0.25)
    fig.suptitle("OntoRisk BI — Risk Intelligence Dashboard (static preview)", x=0.05, ha="left",
                 fontsize=12, fontweight="bold", y=0.985)
    kp = [("Risk Exposure Index", f"{rei:,.0f}", "100% of total exposure"),
          ("Avg Impact Score", f"{ev['impact_score'].mean():.2f} / 10", ""),
          ("Events in View", f"{len(ev):,}", f"of {len(ev):,}"),
          ("Top Rule Confidence", f"{rules['confidence'].iloc[0]:.0%}" if len(rules) else "—", "highest-lift rule")]
    for i, (lab, val, sub) in enumerate(kp):
        ax = fig.add_subplot(gs[0, i]); ax.axis("off")
        ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor="white", edgecolor=GRID))
        ax.text(0.07, 0.75, lab, fontsize=7.5, color=INK2, transform=ax.transAxes)
        ax.text(0.07, 0.36, val, fontsize=14, color=INK, transform=ax.transAxes, fontweight="bold")
        ax.text(0.07, 0.1, sub, fontsize=6.5, color=INK2, transform=ax.transAxes)
    ax = fig.add_subplot(gs[1, :]); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor="#eef6f0", edgecolor=GRID))
    ax.text(0.02, 0.45, "OLAP filters:   Region [All regions ▾]    Time period [2024-01-01 → 2025-12-31]    "
            "Risk type [All risk types ▾]    ·   Drill: Region/State/Place × Year/Quarter/Month",
            fontsize=7.2, color=INK, transform=ax.transAxes, va="center")
    ax = fig.add_subplot(gs[2, :]); ax.axis("off")
    ax.set_title("Association rules — co-occurring risk factors", fontsize=9.5)
    top = rules.head(7)
    cells = [[a if len(a) < 62 else a[:59] + "…", c, f"{s:.2f}", f"{cf:.2f}", f"{l:.2f}"]
             for a, c, s, cf, l in zip(top.antecedents, top.consequents, top.support, top.confidence, top.lift)]
    t = ax.table(cellText=cells, colLabels=["If (antecedent)", "Then (consequent)", "Support", "Confidence", "Lift"],
                 colWidths=[0.52, 0.24, 0.08, 0.09, 0.07], loc="upper center", cellLoc="left")
    t.auto_set_font_size(False); t.set_fontsize(6.6); t.scale(1, 1.25)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor(GRID)
        if r == 0:
            cell.set_facecolor("#eef3fa"); cell.set_text_props(fontweight="bold")
    ax = fig.add_subplot(gs[3, :])
    labels = cl.drop_duplicates("cluster").set_index("cluster")["label"].sort_index()
    for i, (c, lab) in enumerate(labels.items()):
        d = cl[cl.cluster == c]
        ax.scatter(d.pc1, d.pc2, s=18, color=SERIES[i % 8], marker=MARKERS[i % 8], edgecolor=SURFACE,
                   linewidth=0.6, label=f"C{c}: {lab}")
    ax.set_title("k-Means clusters of risk events", fontsize=9.5)
    ax.set_xlabel("Principal component 1"); ax.set_ylabel("Principal component 2")
    ax.legend(frameon=False, fontsize=6.8, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    fig.savefig(config.FIG_DIR / "dashboard_preview.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
