"""pytest suite - run with:  python -m pytest -q

Unit tests for each stage plus one end-to-end test that builds a small
corpus into a temporary warehouse.
"""
import sys
import warnings
from pathlib import Path

import pandas as pd
import pytest

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "dashboard"))

from ontorisk import corpus, etl, evaluate, extraction, mining, nlp, ontology, semantic, warehouse  # noqa: E402

PARA = ("Konkan Freight Ltd said operations at its Mumbai warehouse were disrupted after floods "
        "lashed Maharashtra on Monday. Operations were halted for nearly 4 days.")


# ---------------------------------------------------------------- ontology
def test_ontology_has_six_classes_and_two_object_properties():
    g = ontology.build_tbox()
    res = semantic.validate(g)
    assert res["ontology_has_six_classes"]["passed"]
    assert res["exactly_two_object_properties"]["passed"]


# ---------------------------------------------------------------- NLP
def test_ner_and_risk_tagging():
    p = nlp.analyse_paragraph("T1", 0, PARA)
    assert any("Konkan Freight" in o for o in p.orgs)
    assert "Mumbai" in [pl[0] for pl in p.places]
    assert ("floods", "weather", 3) in p.risk_terms


def test_longest_match_wins():
    p = nlp.analyse_paragraph("T1", 0, "Saurashtra Logistics Ltd reported port congestion at Mundra.")
    terms = [t for t, _, _ in p.risk_terms]
    assert "port congestion" in terms and "congestion" not in terms


def test_preprocess_removes_stopwords_and_lemmatises():
    out = nlp.preprocess("The trucks were stranded at the ports")
    assert "the" not in out.split()
    assert "truck" in out or "trucks" in out


def test_gazetteer_lookup():
    assert nlp.lookup_place("Nhava Sheva")[1:] == ("West", "Maharashtra", "India")
    assert nlp.lookup_place("Atlantis") is None


# ---------------------------------------------------------------- co-occurrence rule
def test_cooccurrence_rule_fires_only_with_org_loc_and_term():
    arts = pd.DataFrame([
        dict(article_id="T1", title="t", date="2025-07-01", source="s", text=PARA),
        dict(article_id="T2", title="t", date="2025-07-01", source="s",
             text="Konkan Freight Ltd opened a new office in Mumbai on Monday."),   # no risk term
    ])
    ev, _ = extraction.extract_events(arts)
    assert set(ev["article_id"]) == {"T1"}
    row = ev.iloc[0]
    assert row.risk_type == "weather" and row.location == "Mumbai"   # state-level duplicate dropped
    assert 0 <= row.impact_score <= 10 and row.severity in {"Low", "Medium", "High"}


def test_rdf_triples_link_to_ontology():
    arts = pd.DataFrame([dict(article_id="T1", title="t", date="2025-07-01", source="s", text=PARA)])
    ev, _ = extraction.extract_events(arts)
    g = extraction.events_to_graph(ev)
    res = semantic.validate(g)
    assert all(v["passed"] for v in res.values()), res


def test_severity_bands():
    assert extraction.severity_band(2) == "Low"
    assert extraction.severity_band(5) == "Medium"
    assert extraction.severity_band(9.5) == "High"


# ---------------------------------------------------------------- ETL quality checks
def test_etl_rejects_dirty_rows():
    df, _ = corpus.build_synthetic_corpus(30)
    clean, rep = etl.clean(df.astype(str))
    assert rep["rejected_duplicate_id"] == 1
    assert rep["rejected_bad_date"] == 1
    assert rep["rejected_empty_text"] == 1
    assert rep["rows_out"] == 30
    assert clean["article_id"].is_unique


# ---------------------------------------------------------------- mining
@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """Small end-to-end build into a temporary warehouse."""
    df, gold = corpus.build_synthetic_corpus(150, seed=7)
    arts, _ = etl.clean(df.astype(str))
    ev, _ = extraction.extract_events(arts)
    db = tmp_path_factory.mktemp("wh") / "test.duckdb"
    wh = warehouse.reset(db)
    dt, dl, dr = warehouse.build_dimensions(ev)
    for name, d in [("DIM_TIME", dt), ("DIM_LOCATION", dl), ("DIM_RISKTYPE", dr),
                    ("FACT_RISKEVENT", warehouse.build_fact(ev, dl, dr)),
                    ("BRIDGE_SEMANTIC_LINK", extraction.link_table(ev))]:
        wh.load(name, d)
    view = wh.query("SELECT * FROM V_RISK_EVENTS")
    checks = warehouse.referential_checks(wh)
    wh.close()
    return dict(events=ev, gold=gold, view=view, checks=checks, db=db)


def test_warehouse_referential_integrity(built):
    c = built["checks"]
    assert c["fact_rows"] == len(built["events"])
    assert c["orphan_time"] == c["orphan_location"] == c["orphan_risktype"] == 0
    assert c["facts_without_triples"] == 0 and c["null_measures"] == 0


def test_fpgrowth_matches_apriori(built):
    r1, _ = mining.mine_rules(built["view"], algorithm="fpgrowth")
    r2, _ = mining.mine_rules(built["view"], algorithm="apriori")
    assert len(r1) > 0
    assert set(zip(r1.antecedents, r1.consequents)) == set(zip(r2.antecedents, r2.consequents))
    assert (r1["confidence"] >= 0.6).all() and (r1["lift"] >= 1.1).all()


def test_kmeans_diagnostics(built):
    cl, prof, diag = mining.cluster_events(built["view"])
    assert diag["k_chosen"] in diag["k_values"]
    assert -1 <= diag["silhouette_chosen"] <= 1
    assert cl["cluster"].nunique() == diag["k_chosen"] == len(prof)


def test_precision_against_gold(built):
    pr = evaluate.precision_recall(built["events"], built["gold"])
    assert 0.5 <= pr["precision"] <= 1.0 and pr["recall"] >= 0.8


def test_dashboard_kpis(built):
    import logic
    ev = built["view"].assign(date=pd.to_datetime(built["view"]["date"]))
    view = logic.apply_filters(ev, regions=["West"], risk_types=["weather", "logistics"])
    assert set(view["region"]) == {"West"}
    rules, _ = mining.mine_rules(ev)
    k = logic.kpis(view, ev, rules)
    assert k["events_in_view"] == len(view)
    assert 0 < k["exposure_share"] < 1
    cube = logic.olap_cube(ev.assign(quarter_label="Q", month_label="M"), "State", "Year", "events")
    assert cube["events"].sum() == len(ev)
