"""OntoRisk BI - end-to-end pipeline runner.

    python run_pipeline.py                      # synthetic Indian-context corpus (240 articles)
    python run_pipeline.py --n 300              # bigger synthetic corpus
    python run_pipeline.py --input my_news.csv  # a real news CSV (e.g. from Kaggle)

Stages: corpus -> clean/preprocess -> NER + risk tagging -> co-occurrence RDF
triples linked to the ontology -> SPARQL validation -> DuckDB star schema +
semantic bridge -> FP-Growth / Apriori rules + k-Means -> evaluation + figures.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import pandas as pd  # noqa: E402

from ontorisk import config, corpus, etl, evaluate, extraction, mining, nlp, ontology, semantic, warehouse  # noqa: E402
from ontorisk import figures  # noqa: E402


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=240, help="number of synthetic articles (150-300)")
    ap.add_argument("--input", help="path to a real news CSV instead of the synthetic corpus")
    ap.add_argument("--skip-corpus", action="store_true", help="reuse data/raw/news_corpus.csv")
    args = ap.parse_args(argv)
    config.ensure_dirs()
    t0 = time.time()
    metrics = {"nlp_backend": nlp.BACKEND, "warehouse_engine": warehouse.ENGINE}

    # 1. corpus --------------------------------------------------------------
    if not args.skip_corpus:
        corpus.write_corpus(args.n, args.input)
    raw = etl.extract()
    log(f"1/8 corpus: {len(raw)} raw records ({'external CSV' if args.input else 'synthetic'})")

    # 2. ontology ------------------------------------------------------------
    tbox = ontology.write_ontology()
    log(f"2/8 ontology: {len(tbox)} T-Box triples -> {config.ONTOLOGY_OWL.relative_to(config.ROOT)}")

    # 3. clean + preprocess ----------------------------------------------------
    articles, quality = etl.clean(raw)
    articles.to_csv(config.CLEAN_ARTICLES, index=False)
    metrics["etl_quality"] = quality
    log(f"3/8 cleaned: {quality['rows_out']} articles kept, {quality['rows_in'] - quality['rows_out']} rejected")

    # 4. NER + co-occurrence rule ---------------------------------------------
    events, ents = extraction.extract_events(articles)
    events.to_csv(config.EVENTS_CSV, index=False)
    ents.to_csv(config.ENTITIES_CSV, index=False)
    metrics["ner"] = evaluate.ner_stats(ents)
    log(f"4/8 NER [{nlp.BACKEND}]: {len(ents)} mentions -> {len(events)} risk events")

    # 5. RDF + SPARQL validation ------------------------------------------------
    kg = extraction.events_to_graph(events)
    kg.serialize(config.KG_TTL, format="turtle")
    metrics["rdf"] = {"total_triples": len(kg), "abox_triples": len(kg) - len(tbox)}
    val = semantic.validate(kg)
    metrics["sparql_validation"] = {k: v["passed"] for k, v in val.items()}
    (config.OUTPUT_DIR / "sparql_validation.json").write_text(json.dumps(val, indent=2))
    log(f"5/8 RDF: {len(kg)} triples; SPARQL checks passed "
        f"{sum(v['passed'] for v in val.values())}/{len(val)}")

    # 6. warehouse -------------------------------------------------------------
    wh = warehouse.reset()
    dim_time, dim_loc, dim_rt = warehouse.build_dimensions(events)
    fact = warehouse.build_fact(events, dim_loc, dim_rt)
    for name, df in [("DIM_TIME", dim_time), ("DIM_LOCATION", dim_loc), ("DIM_RISKTYPE", dim_rt),
                     ("FACT_RISKEVENT", fact), ("BRIDGE_SEMANTIC_LINK", extraction.link_table(events)),
                     ("STG_ARTICLES", articles[["article_id", "title", "date", "source", "text"]])]:
        wh.load(name, df)
    ref = warehouse.referential_checks(wh)
    metrics["warehouse"] = {"engine": warehouse.ENGINE, "path": str(wh.path.relative_to(config.ROOT)),
                            "rows": {t: int(wh.query(f"SELECT COUNT(*) AS n FROM {t}")["n"].iloc[0])
                                     for t in warehouse.LOAD_ORDER},
                            "referential_checks": ref}
    log(f"6/8 warehouse [{warehouse.ENGINE}]: {ref['fact_rows']} facts, "
        f"orphans={ref['orphan_time'] + ref['orphan_location'] + ref['orphan_risktype']}")

    # 7. mining ----------------------------------------------------------------
    ev = wh.query("SELECT * FROM V_RISK_EVENTS ORDER BY event_id")
    wh.close()
    rules, freq = mining.mine_rules(ev, algorithm="fpgrowth")
    rules_ap, _ = mining.mine_rules(ev, algorithm="apriori")
    rules.to_csv(config.OUTPUT_DIR / "association_rules.csv", index=False)
    freq.to_csv(config.OUTPUT_DIR / "frequent_itemsets.csv", index=False)
    clusters, profiles, diag = mining.cluster_events(ev)
    clusters.to_csv(config.OUTPUT_DIR / "clusters.csv", index=False)
    profiles.to_csv(config.OUTPUT_DIR / "cluster_profiles.csv", index=False)
    metrics["association_rules"] = {
        "algorithm": "FP-Growth (mlxtend)", "min_support": config.MIN_SUPPORT,
        "min_confidence": config.MIN_CONFIDENCE, "min_lift": config.MIN_LIFT,
        "frequent_itemsets": int(len(freq)), "rules": int(len(rules)),
        "apriori_rules_identical": bool(len(rules_ap) == len(rules) and
                                        set(zip(rules_ap.antecedents, rules_ap.consequents)) ==
                                        set(zip(rules.antecedents, rules.consequents))),
        "top_rules": rules.head(10).to_dict("records")}
    metrics["clustering"] = {**diag, "profiles": profiles.to_dict("records")}
    log(f"7/8 mining: {len(freq)} frequent itemsets, {len(rules)} rules; "
        f"k-Means k={diag['k_chosen']} silhouette={diag['silhouette_chosen']:.3f}")

    # 8. evaluation + figures ---------------------------------------------------
    gold = pd.read_csv(config.GOLD_CSV) if config.GOLD_CSV.exists() else None
    if gold is not None:
        metrics["triple_precision"] = evaluate.precision_recall(events, gold)
    sample = evaluate.review_sample(events, articles, gold)
    sample.to_csv(config.OUTPUT_DIR / "triple_review_sample.csv", index=False)
    if gold is not None:
        metrics["triple_precision"]["sample_precision"] = round(
            float((sample["auto_label"] == "correct").mean()), 4)
    figures.make_all(ev, rules, clusters, diag, metrics)
    metrics["runtime_seconds"] = round(time.time() - t0, 1)
    (config.OUTPUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str))
    tp = metrics.get("triple_precision", {})
    log(f"8/8 evaluation: precision={tp.get('precision', 'n/a')} recall={tp.get('recall', 'n/a')}; "
        f"figures -> outputs/figures; total {metrics['runtime_seconds']}s")
    print("\nDone. Launch the dashboard with:  streamlit run dashboard/app.py")
    return metrics


if __name__ == "__main__":
    main()
