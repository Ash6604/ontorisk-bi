# OntoRisk BI — Ontology-Driven Semantic Data Warehouse for Proactive Business Risk Intelligence

Unstructured news text → **spaCy NER** → **co-occurrence RDF triples** linked to a **6-class OWL ontology** →
**DuckDB star schema** (+ semantic bridge) → **FP-Growth rules** and **k-Means clusters** → **Streamlit dashboard**.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

python run_pipeline.py              # builds corpus, ontology, triples, warehouse, rules, clusters, figures (~30 s)
python -m pytest                    # 17 tests (1 needs Streamlit)
streamlit run dashboard/app.py      # opens http://localhost:8501
```

## Deploy (Streamlit Community Cloud)

The built warehouse (`warehouse/ontorisk.duckdb`) and mining outputs are committed, so the dashboard runs without
re-running the pipeline. At [share.streamlit.io](https://share.streamlit.io) choose **Create app → Deploy a public
app from GitHub**, pick this repo and branch `main`, set **Main file path** to `dashboard/app.py`, and under
**Advanced settings** choose Python 3.13. Each push to `main` redeploys the app.

Use a real news dataset instead of the synthetic corpus (any CSV with a text column — e.g. a Kaggle Indian business-news CSV):

```bash
python run_pipeline.py --input path/to/news.csv
```

## Project layout

| Path | What it is |
|---|---|
| `run_pipeline.py` | Runs all 8 stages end to end |
| `src/ontorisk/config.py` | Paths, IRIs, thresholds (support, confidence, lift, k range, severity bands) |
| `src/ontorisk/corpus.py` | Synthetic Indian-context corpus generator + loader for external CSVs |
| `src/ontorisk/ontology.py` | The 6-class / 2-object-property ontology (writes `.ttl` and Protégé-ready `.owl`) |
| `src/ontorisk/nlp.py` | spaCy preprocessing, NER, risk-vocabulary PhraseMatcher, gazetteer normalisation |
| `src/ontorisk/extraction.py` | Co-occurrence rule, impact score, severity band, RDFLib triples, triple↔fact bridge |
| `src/ontorisk/semantic.py` | SPARQL validation queries and example semantic queries |
| `src/ontorisk/etl.py` | Pandas ETL with data-quality checks |
| `src/ontorisk/warehouse.py` | DuckDB star schema (FACT_RISKEVENT + DIM_TIME / DIM_LOCATION / DIM_RISKTYPE), view, referential checks |
| `src/ontorisk/mining.py` | FP-Growth / Apriori (mlxtend), k-Means + elbow + silhouette + PCA (scikit-learn) |
| `src/ontorisk/evaluate.py` | Triple precision/recall vs ground truth, manual-review sample, NER statistics |
| `src/ontorisk/figures.py` | Result charts in `outputs/figures` |
| `dashboard/app.py`, `dashboard/logic.py` | Single-page Streamlit dashboard and its tested data layer |
| `data/risk_vocabulary.json` | Curated risk vocabulary (5 risk types, term weights, sector & intensity terms) |
| `data/location_gazetteer.json` | Place → region / state / country mapping (Indian states + key foreign ports) |
| `ontology/ontorisk.owl` | Open in **Protégé** (File → Open) to browse classes, properties, individuals |
| `ontology/ontorisk_kg.ttl` | Full knowledge graph (ontology + generated triples) |
| `warehouse/ontorisk.duckdb` | The warehouse; `warehouse/olap_queries.sql` has ROLLUP/CUBE examples |
| `outputs/` | `metrics.json`, `association_rules.csv`, `clusters.csv`, `cluster_profiles.csv`, `triple_review_sample.csv`, `sparql_validation.json`, figures |

## Notes

* The bundled corpus is **synthetic** (fictional companies, real Indian places and seasonal patterns) because it ships with
  ground-truth labels, which lets the precision of the co-occurrence rule be measured automatically. For the final
  submission you can also run the pipeline on a real public news CSV with `--input`.
* If spaCy or DuckDB is missing the code falls back to a rule-based recogniser / SQLite so it still runs;
  `outputs/metrics.json` records which backend was used (`nlp_backend`, `warehouse_engine`). Install the
  requirements to get the intended stack.
