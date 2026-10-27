"""Stage 7 - Data mining over the warehouse (Section 4.6).

1. Association rules - FP-Growth (mlxtend), Apriori as fallback/cross-check.
   Each risk event becomes a *transaction* of items:
       risktype=<t>, region=<r>, sector=<s>, severity=<band>
   plus  co_risk=<t2>  for every *other* risk type reported in the same
   article (this is what lets rules such as {risktype=weather} =>
   {co_risk=logistics} surface).  Rules are kept if support >= MIN_SUPPORT,
   confidence >= MIN_CONFIDENCE and lift >= MIN_LIFT.

2. k-Means clustering - scikit-learn.  Feature vector per event:
   impact_score, mention_count, one-hot risk type, temporal features
   (month as sin/cos so December is next to January, monsoon-season flag),
   all standardised.  k is chosen with the elbow method (kneedle-style
   maximum distance from the chord of the inertia curve) and validated with
   the silhouette score.  PCA projects the vectors to 2-D for the scatter plot.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from . import config

try:
    from mlxtend.frequent_patterns import apriori, association_rules, fpgrowth
    from mlxtend.preprocessing import TransactionEncoder
    MLXTEND = True
except Exception:  # pragma: no cover
    MLXTEND = False


# ============================================================ association rules
def build_transactions(ev: pd.DataFrame) -> list[list[str]]:
    types_per_article = ev.groupby("source_id")["risk_type"].agg(set).to_dict()
    tx = []
    for r in ev.itertuples(index=False):
        items = [f"risktype={r.risk_type}", f"region={r.region}", f"sector={r.sector}",
                 f"severity={r.severity}"]
        items += [f"co_risk={t}" for t in sorted(types_per_article[r.source_id] - {r.risk_type})]
        tx.append(items)
    return tx


def one_hot(transactions: list[list[str]]) -> pd.DataFrame:
    if MLXTEND:
        te = TransactionEncoder()
        return pd.DataFrame(te.fit(transactions).transform(transactions), columns=te.columns_)
    items = sorted({i for t in transactions for i in t})
    return pd.DataFrame([[i in set(t) for i in items] for t in transactions], columns=items)


def _fmt(itemset) -> str:
    return ", ".join(sorted(itemset))


def mine_rules(ev: pd.DataFrame, min_support=config.MIN_SUPPORT, min_conf=config.MIN_CONFIDENCE,
               min_lift=config.MIN_LIFT, algorithm="fpgrowth"):
    """Return (rules_df, frequent_itemsets_df)."""
    onehot = one_hot(build_transactions(ev))
    algo = fpgrowth if algorithm == "fpgrowth" else apriori
    freq = algo(onehot, min_support=min_support, use_colnames=True)
    if freq.empty:
        return pd.DataFrame(columns=["antecedents", "consequents", "support", "confidence", "lift"]), freq
    rules = association_rules(freq, metric="confidence", min_threshold=min_conf)
    rules = rules[rules["lift"] >= min_lift].copy()
    rules["n_items"] = rules["antecedents"].map(len) + rules["consequents"].map(len)
    rules = rules[rules["consequents"].map(len) == 1]                # readable single-item consequents
    rules["antecedents"] = rules["antecedents"].map(_fmt)
    rules["consequents"] = rules["consequents"].map(_fmt)
    rules = rules.sort_values(["lift", "confidence", "support"], ascending=False)
    cols = ["antecedents", "consequents", "support", "confidence", "lift", "leverage", "conviction", "n_items"]
    freq = freq.assign(itemsets=freq["itemsets"].map(_fmt)).sort_values("support", ascending=False)
    return rules[cols].round(4).reset_index(drop=True), freq.reset_index(drop=True)


# ============================================================ clustering
RISK_TYPES = ["weather", "logistics", "policy", "supplier", "reputational"]


def feature_matrix(ev: pd.DataFrame) -> pd.DataFrame:
    month = pd.to_datetime(ev["date"]).dt.month
    X = pd.DataFrame({
        "impact_score": ev["impact_score"].astype(float),
        "mention_count": ev["mention_count"].astype(float),
        "month_sin": np.sin(2 * np.pi * month / 12),
        "month_cos": np.cos(2 * np.pi * month / 12),
        "monsoon_season": month.between(6, 9).astype(float),
    })
    for t in RISK_TYPES:
        X[f"rt_{t}"] = (ev["risk_type"] == t).astype(float)
    return X.reset_index(drop=True)


def elbow_k(ks, inertias) -> int:
    """Kneedle-style knee: point with max distance from the line joining the curve's ends."""
    x = np.array(list(ks), float)
    y = np.array(inertias, float)
    xn = (x - x.min()) / (x.max() - x.min())
    yn = (y - y.min()) / (y.max() - y.min() + 1e-12)
    dist = np.abs((yn[-1] - yn[0]) * xn - (xn[-1] - xn[0]) * yn + xn[-1] * yn[0] - yn[-1] * xn[0])
    return int(x[int(np.argmax(dist))])


def cluster_events(ev: pd.DataFrame, k_range=config.K_RANGE, k: int | None = None):
    """Return (assignments_df, diagnostics)."""
    X = feature_matrix(ev)
    Xs = StandardScaler().fit_transform(X)
    # The five one-hot risk-type columns describe ONE attribute; without re-weighting they
    # would carry 5x the weight of impact score and dominate the distance.  Scaling the block
    # by 1/sqrt(5) gives the categorical attribute the weight of a single feature.
    # The same block weighting is applied to the three time-of-year columns.
    for prefix in (("rt_",), ("month_", "monsoon")):
        cols = [i for i, c in enumerate(X.columns) if c.startswith(prefix)]
        Xs[:, cols] /= np.sqrt(len(cols))
    ks = [kk for kk in k_range if kk < len(ev)]
    inertias, sils = [], []
    for kk in ks:
        km = KMeans(n_clusters=kk, n_init=10, random_state=config.RANDOM_STATE).fit(Xs)
        inertias.append(float(km.inertia_))
        sils.append(float(silhouette_score(Xs, km.labels_)))
    k_elbow = elbow_k(ks, inertias)
    k_best_sil = ks[int(np.argmax(sils))]
    chosen = k or k_elbow
    km = KMeans(n_clusters=chosen, n_init=10, random_state=config.RANDOM_STATE).fit(Xs)
    labels = km.labels_
    pca = PCA(n_components=2, random_state=config.RANDOM_STATE)
    xy = pca.fit_transform(Xs)

    out = ev[["event_id", "entity_name", "risk_type", "region", "sector", "severity",
              "impact_score", "mention_count", "date"]].reset_index(drop=True).copy()
    out["cluster"] = labels
    out["pc1"], out["pc2"] = xy[:, 0], xy[:, 1]

    # human-readable profile for each cluster
    prof = out.assign(month=pd.to_datetime(out["date"]).dt.month).groupby("cluster").agg(
        size=("event_id", "count"), avg_impact=("impact_score", "mean"),
        avg_mentions=("mention_count", "mean"),
        top_risk_type=("risk_type", lambda s: s.value_counts().index[0]),
        top_risk_share=("risk_type", lambda s: s.value_counts(normalize=True).iloc[0]),
        top_region=("region", lambda s: s.value_counts().index[0]),
        monsoon_share=("month", lambda m: m.between(6, 9).mean()),
        high_share=("severity", lambda s: (s == "High").mean()),
    ).round(3).reset_index()
    def _label(r):
        level = "High" if r.avg_impact >= 6.5 else "Moderate" if r.avg_impact >= 4.5 else "Low"
        kind = r.top_risk_type if r.top_risk_share >= .5 else "mixed-type"
        season = "monsoon" if r.monsoon_share > .6 else "off-monsoon" if r.monsoon_share < .25 else "all-year"
        return f"{level}-impact {kind}, {season}"
    prof["label"] = [_label(r) for r in prof.itertuples()]
    out = out.merge(prof[["cluster", "label"]], on="cluster", how="left")

    diag = dict(k_values=ks, inertia=inertias, silhouette=sils, k_elbow=k_elbow,
                k_best_silhouette=k_best_sil, k_chosen=chosen,
                silhouette_chosen=float(silhouette_score(Xs, labels)),
                pca_explained_variance=[float(v) for v in pca.explained_variance_ratio_],
                features=list(X.columns))
    return out, prof, diag
