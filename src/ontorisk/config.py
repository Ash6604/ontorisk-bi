"""Central configuration: paths, namespaces and tunable thresholds.

Every stage of the pipeline imports its paths and parameters from here so that
the whole project can be re-pointed (e.g. at a real Kaggle news CSV) by editing
one file.
"""
from pathlib import Path

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
ONTOLOGY_DIR = ROOT / "ontology"
WAREHOUSE_DIR = ROOT / "warehouse"
OUTPUT_DIR = ROOT / "outputs"
FIG_DIR = OUTPUT_DIR / "figures"

CORPUS_CSV = RAW_DIR / "news_corpus.csv"            # input articles
GOLD_CSV = RAW_DIR / "gold_events.csv"               # ground truth (synthetic corpus only)
VOCAB_JSON = DATA_DIR / "risk_vocabulary.json"       # curated risk vocabulary
GAZETTEER_JSON = DATA_DIR / "location_gazetteer.json"

CLEAN_ARTICLES = PROCESSED_DIR / "articles_clean.csv"
ENTITIES_CSV = PROCESSED_DIR / "entities.csv"
EVENTS_CSV = PROCESSED_DIR / "risk_events.csv"

ONTOLOGY_TTL = ONTOLOGY_DIR / "ontorisk.ttl"          # T-Box, Turtle
ONTOLOGY_OWL = ONTOLOGY_DIR / "ontorisk.owl"          # T-Box, RDF/XML (open in Protégé)
KG_TTL = ONTOLOGY_DIR / "ontorisk_kg.ttl"             # T-Box + A-Box (generated triples)

WAREHOUSE_DB = WAREHOUSE_DIR / "ontorisk.duckdb"

# ---------------------------------------------------------------- semantic web
BASE_IRI = "http://ontorisk.example.org/ontology#"
DATA_IRI = "http://ontorisk.example.org/data/"

# ---------------------------------------------------------------- scoring
SEVERITY_BANDS = [(0.0, 4.0, "Low"), (4.0, 7.0, "Medium"), (7.0, 10.01, "High")]
SEVERITY_WEIGHT = {"Low": 1, "Medium": 2, "High": 3}

# ---------------------------------------------------------------- mining
MIN_SUPPORT = 0.05
MIN_CONFIDENCE = 0.60
MIN_LIFT = 1.10
K_RANGE = range(2, 11)
RANDOM_STATE = 42

# ---------------------------------------------------------------- evaluation
TRIPLE_REVIEW_SAMPLE = 50


def ensure_dirs() -> None:
    for d in (RAW_DIR, PROCESSED_DIR, ONTOLOGY_DIR, WAREHOUSE_DIR, OUTPUT_DIR, FIG_DIR):
        d.mkdir(parents=True, exist_ok=True)
