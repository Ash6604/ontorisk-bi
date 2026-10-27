"""Builds docs/OntoRisk_BI_Project_Explanation.pdf from the latest pipeline outputs.

    python docs/build_explanation_pdf.py        (after python run_pipeline.py)
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (CondPageBreak, Image, KeepTogether, PageBreak, Paragraph, Preformatted,  # noqa: E402
                                SimpleDocTemplate, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents  # noqa: E402

from ontorisk import config, nlp, ontology  # noqa: E402

OUT = ROOT / "docs" / "OntoRisk_BI_Project_Explanation.pdf"
FIG = config.FIG_DIR
M = json.loads((config.OUTPUT_DIR / "metrics.json").read_text())

# ------------------------------------------------------------------ fonts & styles
FD = "/usr/share/fonts/truetype/dejavu/"
for name, f in [("Sans", "DejaVuSans.ttf"), ("Sans-Bold", "DejaVuSans-Bold.ttf"),
                ("Sans-Oblique", "DejaVuSans-Oblique.ttf"), ("Sans-BoldOblique", "DejaVuSans-BoldOblique.ttf"),
                ("Serif", "DejaVuSerif.ttf"), ("Serif-Bold", "DejaVuSerif-Bold.ttf"), ("Mono", "DejaVuSansMono.ttf")]:
    try:
        pdfmetrics.registerFont(TTFont(name, FD + f))
    except Exception:
        pass
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-Bold", italic="Sans-Oblique",
                              boldItalic="Sans-BoldOblique")

ACCENT = colors.HexColor("#1c5aa6")
INK = colors.HexColor("#1b1b1b")
MUTED = colors.HexColor("#5a5955")
RULE = colors.HexColor("#d9d8d3")
TINT = colors.HexColor("#eef3fa")
CODEBG = colors.HexColor("#f5f4f0")

S = {
    "body": ParagraphStyle("body", fontName="Sans", fontSize=9.4, leading=13.6, textColor=INK, spaceAfter=5),
    "h1": ParagraphStyle("h1", fontName="Sans-Bold", fontSize=17, leading=21, textColor=ACCENT, spaceBefore=4,
                         spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName="Sans-Bold", fontSize=12.2, leading=16, textColor=INK, spaceBefore=10,
                         spaceAfter=5),
    "h3": ParagraphStyle("h3", fontName="Sans-Bold", fontSize=10.2, leading=14, textColor=ACCENT, spaceBefore=7,
                         spaceAfter=3),
    "small": ParagraphStyle("small", fontName="Sans", fontSize=8, leading=10.6, textColor=MUTED),
    "cell": ParagraphStyle("cell", fontName="Sans", fontSize=8.1, leading=10.6, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Sans-Bold", fontSize=8.1, leading=10.6, textColor=INK),
    "bullet": ParagraphStyle("bullet", fontName="Sans", fontSize=9.4, leading=13.4, leftIndent=13,
                             bulletIndent=3, spaceAfter=2.5, textColor=INK),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=7.6, leading=9.8, textColor=INK,
                           backColor=CODEBG, borderPadding=6, leftIndent=4, rightIndent=4, spaceBefore=4,
                           spaceAfter=8),
    "caption": ParagraphStyle("caption", fontName="Sans-Oblique", fontSize=8, leading=10.5, textColor=MUTED,
                              alignment=TA_CENTER, spaceBefore=3, spaceAfter=9),
    "callout": ParagraphStyle("callout", fontName="Sans", fontSize=9.2, leading=13.2, textColor=INK,
                              backColor=TINT, borderPadding=8, spaceBefore=6, spaceAfter=10,
                              borderColor=ACCENT, borderWidth=0, leftIndent=6, rightIndent=6),
    "q": ParagraphStyle("q", fontName="Sans-Bold", fontSize=9.4, leading=13, textColor=ACCENT, spaceBefore=6,
                        spaceAfter=1.5),
}

story = []


def P(text, style="body"):
    story.append(Paragraph(text, S[style]))


def H1(text):
    story.append(CondPageBreak(90 * mm))
    p = Paragraph(text, S["h1"])
    p._toc = (0, text)
    story.append(p)


def H2(text):
    story.append(CondPageBreak(35 * mm))
    p = Paragraph(text, S["h2"])
    p._toc = (1, text)
    story.append(p)


def H3(text):
    story.append(Paragraph(text, S["h3"]))


def B(items):
    for it in items:
        story.append(Paragraph(it, S["bullet"], bulletText="•"))


def CODE(text):
    story.append(Preformatted(text.strip("\n"), S["code"]))


def CALL(text):
    story.append(Paragraph(text, S["callout"]))


def SP(h=6):
    story.append(Spacer(1, h))


def TABLE(rows, widths, header=True, zebra=True, font=None):
    data = [[Paragraph(str(c), S["cellb"] if (header and i == 0) else S["cell"]) for c in r]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT),
          ("LINEBELOW", (0, 1), (-1, -1), 0.3, RULE), ("TOPPADDING", (0, 0), (-1, -1), 3.2),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2), ("LEFTPADDING", (0, 0), (-1, -1), 4),
          ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), TINT))
    t.setStyle(TableStyle(st))
    story.append(t)
    SP(8)


def FIGURE(path, caption, width_mm=165):
    if not Path(path).exists():
        return
    img = Image(str(path))
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth = width_mm * mm
    img.drawHeight = width_mm * mm * ratio
    story.append(KeepTogether([img, Paragraph(caption, S["caption"])]))


def pct(x):
    return f"{100 * float(x):.1f}%"


# ------------------------------------------------------------------ diagrams
def pipeline_diagram():
    stages = [("News corpus", "CSV, 240 articles", "#dbe7f5"), ("Clean +\npreprocess", "pandas, spaCy", "#dbe7f5"),
              ("NER + risk\ntagging", "spaCy, vocab", "#dbe7f5"), ("Co-occurrence\nrule", "ORG+LOC+term", "#dcefe3"),
              ("RDF triples +\nontology", "RDFLib, OWL", "#dcefe3"), ("Star schema", "DuckDB", "#fbe7d3"),
              ("Mining", "FP-Growth\nk-Means", "#e8e1f5"), ("Dashboard", "Streamlit", "#e8e1f5")]
    W, H = 175 * mm, 40 * mm
    d = Drawing(W, H)
    n = len(stages)
    bw, gap = 18.5 * mm, (W - n * 18.5 * mm) / (n - 1)
    for i, (title, sub, col) in enumerate(stages):
        x = i * (bw + gap)
        d.add(Rect(x, 9 * mm, bw, 22 * mm, fillColor=colors.HexColor(col), strokeColor=MUTED, strokeWidth=0.5,
                   rx=2, ry=2))
        for j, line in enumerate(title.split("\n")):
            d.add(String(x + bw / 2, 25.5 * mm - j * 3.4 * mm, line, fontName="Sans-Bold", fontSize=5.9,
                         textAnchor="middle", fillColor=INK))
        for j, line in enumerate(sub.split("\n")):
            d.add(String(x + bw / 2, 15 * mm - j * 3 * mm, line, fontName="Sans", fontSize=5.8,
                         textAnchor="middle", fillColor=MUTED))
        if i < n - 1:
            x1, x2, y = x + bw + 0.6 * mm, x + bw + gap - 0.6 * mm, 20 * mm
            d.add(Line(x1, y, x2 - 1.2 * mm, y, strokeColor=MUTED, strokeWidth=0.8))
            d.add(Polygon([x2, y, x2 - 1.6 * mm, y + 0.9 * mm, x2 - 1.6 * mm, y - 0.9 * mm], fillColor=MUTED,
                          strokeColor=MUTED))
    labels = [(0, 3, "Text analytics layer", "#3d6fb0"), (3, 5, "Semantic layer", "#2f8a57"),
              (5, 6, "Warehouse", "#b5651d"), (6, 8, "Mining + BI", "#6a4fb0")]
    for a, b, lab, col in labels:
        x0 = a * (bw + gap)
        x1 = (b - 1) * (bw + gap) + bw
        d.add(Line(x0, 5.5 * mm, x1, 5.5 * mm, strokeColor=colors.HexColor(col), strokeWidth=1.4))
        d.add(String((x0 + x1) / 2, 1.5 * mm, lab, fontName="Sans", fontSize=6.4, textAnchor="middle",
                     fillColor=colors.HexColor(col)))
    story.append(d)
    story.append(Paragraph("Figure 1 — The implemented OntoRisk BI pipeline (each stage's output is the next "
                           "stage's input).", S["caption"]))


def star_diagram():
    W, H = 170 * mm, 62 * mm
    d = Drawing(W, H)

    def box(x, y, w, h, title, fields, col):
        d.add(Rect(x, y, w, h, fillColor=colors.HexColor(col), strokeColor=MUTED, strokeWidth=0.6, rx=2, ry=2))
        d.add(String(x + w / 2, y + h - 4.2 * mm, title, fontName="Sans-Bold", fontSize=7, textAnchor="middle"))
        for j, f in enumerate(fields):
            d.add(String(x + 2.2 * mm, y + h - 8.4 * mm - j * 3.1 * mm, f, fontName="Mono", fontSize=5.6,
                         fillColor=INK))

    fx, fy, fw, fh = 62 * mm, 9 * mm, 46 * mm, 41 * mm
    box(fx, fy, fw, fh, "FACT_RISKEVENT",
        ["event_id (PK)", "time_key (FK)", "location_key (FK)", "risktype_key (FK)", "entity_name  [degenerate]",
         "sector", "source_id  [degenerate]", "impact_score   (measure)", "severity", "mention_count  (measure)"],
        "#fbe7d3")
    box(4 * mm, 30 * mm, 42 * mm, 28 * mm, "DIM_TIME",
        ["time_key (PK)", "date", "week, month, month_name", "quarter", "year"], "#dbe7f5")
    box(4 * mm, 2 * mm, 42 * mm, 24 * mm, "DIM_LOCATION",
        ["location_key (PK)", "place", "region, state", "country"], "#dbe7f5")
    box(124 * mm, 32 * mm, 42 * mm, 22 * mm, "DIM_RISKTYPE",
        ["risktype_key (PK)", "category", "sub_type"], "#dbe7f5")
    box(124 * mm, 4 * mm, 42 * mm, 24 * mm, "BRIDGE_SEMANTIC_LINK",
        ["event_id (FK)", "subject", "predicate", "object"], "#dcefe3")
    for (x1, y1, x2, y2) in [(46, 44, 62, 40), (46, 14, 62, 20), (108, 40, 124, 43), (108, 18, 124, 16)]:
        d.add(Line(x1 * mm, y1 * mm, x2 * mm, y2 * mm, strokeColor=MUTED, strokeWidth=0.8))
    story.append(d)
    story.append(Paragraph("Figure 2 — Implemented star schema (orange = fact, blue = dimensions) and the "
                           "semantic bridge table (green) that links each fact row to its RDF triples.",
                           S["caption"]))


# ------------------------------------------------------------------ page decorations
def on_page(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont("Sans", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 10 * mm, "OntoRisk BI — Project Explanation & Technical Guide")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.setStrokeColor(RULE)
        canvas.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
    canvas.restoreState()


class Doc(SimpleDocTemplate):
    def afterFlowable(self, f):
        if hasattr(f, "_toc"):
            level, text = f._toc
            key = f"toc{id(f)}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=level > 0)
            self.notify("TOCEntry", (level, text, self.page, key))


# ================================================================== CONTENT
q = M.get("triple_precision", {})
ar = M["association_rules"]
cl = M["clustering"]
wh = M["warehouse"]
etlq = M["etl_quality"]
rules = pd.read_csv(config.OUTPUT_DIR / "association_rules.csv")
profiles = pd.read_csv(config.OUTPUT_DIR / "cluster_profiles.csv")
events = pd.read_csv(config.EVENTS_CSV)
articles = pd.read_csv(config.CLEAN_ARTICLES)
sparql = json.loads((config.OUTPUT_DIR / "sparql_validation.json").read_text())
vocab = nlp.vocabulary()

# ---------------------------------------------------------------- cover
story.append(Spacer(1, 30 * mm))
story.append(Paragraph("MANIPAL INSTITUTE OF TECHNOLOGY, BENGALURU", ParagraphStyle(
    "c0", fontName="Sans-Bold", fontSize=10, textColor=MUTED, alignment=TA_CENTER)))
story.append(Paragraph("Department of Computer Science and Engineering", ParagraphStyle(
    "c00", fontName="Sans", fontSize=9, textColor=MUTED, alignment=TA_CENTER, spaceAfter=24)))
story.append(Paragraph("OntoRisk BI", ParagraphStyle("c1", fontName="Sans-Bold", fontSize=34, leading=40,
                                                     textColor=ACCENT, alignment=TA_CENTER)))
story.append(Paragraph("Ontology-Driven Semantic Data Warehouse for<br/>Proactive Business Risk Intelligence",
                       ParagraphStyle("c2", fontName="Sans", fontSize=14, leading=19, textColor=INK,
                                      alignment=TA_CENTER, spaceBefore=6, spaceAfter=26)))
story.append(Paragraph("PROJECT EXPLANATION &amp; TECHNICAL GUIDE", ParagraphStyle(
    "c3", fontName="Sans-Bold", fontSize=11, textColor=INK, alignment=TA_CENTER, spaceAfter=4)))
story.append(Paragraph("What was built, how every technology is used and why, the results, how to run it, "
                       "and answers to the questions examiners usually ask", ParagraphStyle(
                           "c4", fontName="Sans-Oblique", fontSize=9, textColor=MUTED, alignment=TA_CENTER,
                           spaceAfter=40)))
team = [["Team member", "Register No."], ["Aishwarya Patil", "235890068"],
        ["Thiriveedhi Venkata Subba Sai Teja", "235890021"], ["Dhruv Naveen", "235890154"],
        ["Shaswat Das", "235890222"]]
t = Table([[Paragraph(a, S["cellb"] if i == 0 else S["cell"]), Paragraph(b, S["cellb"] if i == 0 else S["cell"])]
           for i, (a, b) in enumerate(team)], colWidths=[75 * mm, 35 * mm])
t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT), ("LINEBELOW", (0, 1), (-1, -1), 0.3, RULE),
                       ("BACKGROUND", (0, 0), (-1, 0), TINT)]))
story.append(t)
story.append(Spacer(1, 10))
story.append(Paragraph("Section B · B.Tech Computer Science and Engineering<br/>Guide: <b>Dr. Sathiyaraj "
                       "Rajendran</b>, Associate Professor, CSE Dept., M.I.T Bengaluru",
                       ParagraphStyle("c5", fontName="Sans", fontSize=9, leading=13, alignment=TA_CENTER)))
story.append(PageBreak())

# ---------------------------------------------------------------- TOC
story.append(Paragraph("Contents", S["h1"]))
toc = TableOfContents()
toc.levelStyles = [ParagraphStyle("t0", fontName="Sans-Bold", fontSize=9.6, leading=14, leftIndent=0),
                   ParagraphStyle("t1", fontName="Sans", fontSize=8.6, leading=11.5, leftIndent=12,
                                  textColor=MUTED)]
story.append(toc)
story.append(PageBreak())

# ---------------------------------------------------------------- 1 at a glance
H1("1. The project in one page")
CALL("<b>Elevator pitch.</b> Businesses learn about risks — a flood at a warehouse, congestion at a port, a "
     "new export ban, a supplier going bust, a product recall — from the news, but that news is unstructured "
     "text that BI tools cannot query. OntoRisk BI reads news articles, finds <i>which organisation</i> is "
     "affected by <i>what kind of risk</i> <i>where</i>, stores that knowledge twice — as RDF triples in a "
     "small ontology (for meaning and SPARQL) and as rows in a DuckDB star schema (for fast OLAP) — then mines "
     "it for co-occurring risk factors (FP-Growth) and groups of similar disruptions (k-Means), and shows "
     "everything on one Streamlit dashboard.")
P("<b>The problem.</b> SMEs in supply chain, retail, finance and manufacturing have no affordable way to turn "
  "risk-relevant text into structured, queryable intelligence. Text-mining outputs usually live apart from "
  "the warehouse, and semantic-web tools are rarely combined with star-schema/OLAP practice.")
P("<b>The contribution.</b> As the report states, the contribution is <b>integration, not novelty in any one "
  "layer</b>: semantic layer + dimensional warehouse + data-mining layer in a single, open, reproducible "
  "pipeline, each layer in the simplest form that still produces a genuine artefact for the next one, with an "
  "explicit Indian context (monsoon disruption, port congestion, domestic policy change).")
H2("What was delivered")
TABLE([
    ["Deliverable", "Where", "Result of the latest run"],
    ["Curated news corpus (150–300 articles)", "data/raw/news_corpus.csv", f"{etlq['rows_in']} raw records → "
     f"{etlq['rows_out']} clean articles"],
    ["Compact risk ontology (6 classes, 2 object properties)", "ontology/ontorisk.owl (Protégé)",
     f"{len(ontology.CLASSES)} classes, {len(ontology.OBJECT_PROPERTIES)} object properties, "
     f"{len(ontology.DATA_PROPERTIES)} data properties"],
    ["spaCy NER + risk vocabulary tagging", "src/ontorisk/nlp.py",
     f"{sum(M['ner']['mentions_by_label'].values())} entity / term mentions"],
    ["Co-occurrence RDF triples linked to ontology", "ontology/ontorisk_kg.ttl",
     f"{M['rdf']['total_triples']:,} triples ({M['rdf']['abox_triples']:,} generated)"],
    ["SPARQL validation queries", "outputs/sparql_validation.json",
     f"{sum(M['sparql_validation'].values())}/{len(M['sparql_validation'])} passing"],
    ["DuckDB star schema + semantic bridge", "warehouse/ontorisk.duckdb",
     f"{wh['rows']['FACT_RISKEVENT']} fact rows, 0 orphan keys"],
    ["FP-Growth association rules (Apriori cross-check)", "outputs/association_rules.csv",
     f"{ar['frequent_itemsets']} frequent itemsets, {ar['rules']} rules"],
    ["k-Means clustering (elbow + silhouette)", "outputs/clusters.csv",
     f"k = {cl['k_chosen']}, silhouette = {cl['silhouette_chosen']:.3f}"],
    ["Triple precision evaluation", "outputs/triple_review_sample.csv",
     f"precision {pct(q.get('precision', 0))}, recall {pct(q.get('recall', 0))}" if q else "manual sample"],
    ["Single-page Streamlit dashboard", "dashboard/app.py", "4 KPIs, OLAP filters, rules table, cluster scatter"],
    ["Automated tests", "tests/", "17 pytest tests (16 + 1 that needs Streamlit)"],
], [62, 50, 62])

# ---------------------------------------------------------------- 2 traceability
H1("2. Requirement traceability — every item in the report, and where it is")
P("The table walks through the report (abstract, objectives, Chapter 4 and the scope decisions) and points to "
  "the code that satisfies each point. Use it when someone asks <i>“where did you implement X?”</i>.")
TABLE([
    ["Report requirement", "Implementation", "Status"],
    ["Obj. 1 — small domain ontology in Protégé: RiskEvent, Entity, Location, RiskType + supporting classes; "
     "properties “affects”, “located-in”", "ontology.py generates ontorisk.owl (RDF/XML, opens in Protégé) and "
     ".ttl. Supporting classes: SourceArticle, RiskTerm. Impact & provenance are data properties, as in §4.4",
     "Done"],
    ["Obj. 2 — spaCy NER on news, risk terms, RDF triples linked to ontology", "nlp.py (en_core_web_sm; ORG, "
     "GPE/LOC, DATE; PhraseMatcher over the vocabulary), extraction.py (RDFLib)", "Done"],
    ["Obj. 3 — star schema + ETL into DuckDB", "warehouse.py, etl.py, run_pipeline.py", "Done"],
    ["Obj. 4 — association rules + clustering", "mining.py (mlxtend FP-Growth/Apriori; scikit-learn k-Means)",
     "Done"],
    ["Obj. 5 — Streamlit dashboard with KPIs, filters, rules, clusters + basic evaluation",
     "dashboard/app.py, logic.py; evaluate.py", "Done"],
    ["§4.1 seven-stage pipeline, independently testable stages", "one module per stage; tests per stage",
     "Done"],
    ["§4.2 150–300 public news articles, Indian context, multiple sectors", "corpus.py: 240 synthetic "
     "articles (default) or any public CSV via --input; four sectors; monsoon, port, policy themes",
     "Done (see note §4.1)"],
    ["§4.3 tokenisation, stop-words, lemmatisation", "nlp.preprocess → clean_text column", "Done"],
    ["§4.3 risk vocabulary grouped by type (weather, policy, supplier, logistics, reputational)",
     "data/risk_vocabulary.json (5 types, weighted terms)", "Done"],
    ["§4.3 co-occurrence rule within paragraph (else article)", "extraction.extract_events; split_paragraphs "
     "falls back to whole article when no blank-line paragraphs exist", "Done"],
    ["§4.3 manual review of a random triple sample", "outputs/triple_review_sample.csv (50 rows, paragraph "
     "shown, column for manual Y/N) + automatic precision vs ground truth", "Done"],
    ["§4.4 SPARQL as validation mechanism", "semantic.VALIDATION_QUERIES (6 checks)", "Done"],
    ["§4.5 Table 4.1 fact + 3 dimensions; entity & source degenerate", "warehouse.DDL", "Done"],
    ["§4.5 quality checks: nulls, duplicates, date parsing, referential checks", "etl.clean, "
     "warehouse.referential_checks", "Done"],
    ["§4.5 semantic enrichment via shared event identifier", "BRIDGE_SEMANTIC_LINK + ork:eventId", "Done"],
    ["§4.6 transactions of risk type, region, sector, severity; support/confidence/lift",
     "mining.build_transactions / mine_rules", "Done"],
    ["§4.6 k-Means on impact, mentions, encoded risk type, temporal features; elbow + silhouette",
     "mining.feature_matrix / cluster_events", "Done"],
    ["§4.7 single page: KPI row, OLAP filter (region, time, risk type), rules table, cluster scatter, "
     "caching", "dashboard/app.py with st.cache_data / st.cache_resource", "Done"],
    ["Table 4.3 KPIs: Risk Exposure Index, Avg Impact, Events in View, Top Rule Confidence",
     "dashboard/logic.kpis", "Done"],
    ["§4.8 tools: pandas, spaCy, RDFLib, Protégé, SPARQL, mlxtend, scikit-learn, DuckDB, Streamlit, Plotly, "
     "pytest, GitHub", "requirements.txt; branch-per-stage workflow described in §10", "Done"],
    ["Out of scope: decision tree, DBSCAN, rule-based alerts, SVM, BIRCH, OPTICS", "deliberately not built "
     "(documented as future scope, §12)", "Excluded by design"],
], [62, 82, 30])

# ---------------------------------------------------------------- 3 architecture
H1("3. Architecture")
pipeline_diagram()
P("The system is a linear, layered pipeline. Each stage reads a file or table written by the previous one, so "
  "each can be tested and replaced on its own, and the four team members could build adjacent stages in "
  "parallel against agreed interfaces (a cleaned-article DataFrame after Week 1, a populated warehouse after "
  "Week 2). <font name='Mono'>run_pipeline.py</font> executes all of them in order and prints one log line "
  "per stage.")
TABLE([
    ["#", "Stage", "Module", "Input → Output"],
    ["1", "Corpus collection", "corpus.py", "generator / external CSV → data/raw/news_corpus.csv"],
    ["2", "Ontology (T-Box)", "ontology.py", "vocabulary → ontology/ontorisk.ttl, .owl"],
    ["3", "Cleaning & preprocessing", "etl.py, nlp.preprocess", "raw CSV → articles_clean.csv + quality report"],
    ["4", "NER + co-occurrence rule", "nlp.py, extraction.py", "clean articles → risk_events.csv, entities.csv"],
    ["5", "RDF + SPARQL validation", "extraction.py, semantic.py", "events → ontorisk_kg.ttl, validation JSON"],
    ["6", "Semantic ETL to warehouse", "warehouse.py", "events → DuckDB star schema + bridge"],
    ["7", "Mining", "mining.py", "V_RISK_EVENTS → rules, itemsets, clusters, profiles"],
    ["8", "Evaluation + figures", "evaluate.py, figures.py", "events + gold → metrics.json, PNG figures"],
    ["—", "Dashboard", "dashboard/app.py", "warehouse + mining outputs + KG → web page"],
], [8, 42, 44, 80])
H2("Folder structure")
CODE("""ontorisk-bi/
├── run_pipeline.py            # one command runs every stage
├── requirements.txt  README.md  pytest.ini
├── data/
│   ├── risk_vocabulary.json   # curated risk vocabulary (project artefact)
│   ├── location_gazetteer.json
│   ├── raw/        news_corpus.csv, gold_events.csv
│   └── processed/  articles_clean.csv, entities.csv, risk_events.csv
├── ontology/       ontorisk.owl (Protégé), ontorisk.ttl, ontorisk_kg.ttl
├── warehouse/      ontorisk.duckdb, olap_queries.sql
├── src/ontorisk/   config, corpus, nlp, extraction, ontology, semantic,
│                   etl, warehouse, mining, evaluate, figures
├── dashboard/      app.py (Streamlit), logic.py (tested data layer)
├── tests/          test_pipeline.py, test_dashboard_smoke.py
├── outputs/        metrics.json, association_rules.csv, clusters.csv, figures/ ...
└── docs/           this explanation PDF and its generator""")

# ---------------------------------------------------------------- 4 stage by stage
H1("4. How each stage works")
H2("4.1 Data collection — the corpus")
P(f"The report plans 150–300 public news articles (Kaggle and other public sources) with Indian regional "
  f"context and coverage of four sectors. The repository ships a <b>curated synthetic corpus of "
  f"{etlq['rows_out']} articles</b> generated by <font name='Mono'>corpus.py</font>, and the same pipeline "
  f"runs unchanged on any real news CSV (<font name='Mono'>python run_pipeline.py --input news.csv</font>; "
  f"column names such as headline/content/published_at are mapped automatically).")
P("<b>Why a synthetic corpus?</b> (1) It is reproducible (fixed random seed), so every team member and the "
  "examiner get identical results. (2) Because the generator knows which company, place and risk each story is "
  "really about, it writes a ground-truth file (<font name='Mono'>gold_events.csv</font>), which turns the "
  "planned manual precision check into an exact, automatic measurement over all triples. (3) It avoids "
  "copyright and scraping issues. Companies are fictional (e.g. Konkan Freight Ltd, Kalinga Steel Works); "
  "places and seasonality are real Indian context.")
B(["<b>Five risk types</b> with realistic biases: weather (Mumbai, Chennai, Kochi, Guwahati, Odisha; 75% in "
   "June–September), logistics (Nhava Sheva, Mundra, Chennai, Kolkata, Visakhapatnam, Colombo, Singapore), "
   "policy (mostly New Delhi), supplier (Hosur, Pune, Bengaluru, Coimbatore, Jamshedpur), reputational "
   "(Bengaluru, Gurugram, Hyderabad, Noida).",
   "<b>Co-occurring risks</b>: 55% of weather stories also report port/freight disruption; some policy "
   "stories lead to supplier shortages — patterns the miner should rediscover.",
   "<b>Realistic noise</b>: 65% of articles contain an analyst/industry paragraph that names another "
   "organisation and city, sometimes with a risk word — exactly the incidental co-mention that produces "
   "spurious triples.",
   f"<b>Dirty records</b> for the ETL to catch: one duplicate, one unparseable date, one empty article "
   f"(rejected: {etlq['rejected_duplicate_id']} duplicate id, {etlq['rejected_duplicate_text']} duplicate "
   f"text, {etlq['rejected_bad_date']} bad date, {etlq['rejected_empty_text']} empty)."])
ex = articles.iloc[0]
H3("Example article")
CODE(f"{ex.article_id} | {ex.date} | {ex.source}\nTITLE: {ex.title}\n\n" +
     "\n\n".join(_wrap for _wrap in [__import__('textwrap').fill(p, 105) for p in str(ex.text).split('\n\n')]))

H2("4.2 Preprocessing and named entity recognition")
P(f"<b>Backend used in this run:</b> {M['nlp_backend']}.")
P("Each article is split into paragraphs (blank-line separated). Two things happen with spaCy:")
B(["<b>Preprocessing</b> (<font name='Mono'>nlp.preprocess</font>): the spaCy pipeline tokenises the text; "
   "stop words, punctuation, spaces and numbers are dropped and every remaining token is replaced by its "
   "lower-case <i>lemma</i> (“disrupted” → “disrupt”, “floods” → “flood”). The result is stored in "
   "<font name='Mono'>clean_text</font> for analysis.",
   "<b>NER</b> runs on the <i>original</i> paragraph (NER needs capital letters and function words). "
   "The pre-trained <font name='Mono'>en_core_web_sm</font> model labels ORG (organisations), GPE/LOC "
   "(places) and DATE spans.",
   "<b>Normalisation</b>: organisation names lose possessives and leading words (“Shares of …”); places are "
   "looked up in <font name='Mono'>location_gazetteer.json</font> to get region/state/country. A gazetteer "
   "pass also recovers multi-word Indian place names the small model may miss (e.g. “Nhava Sheva”) — "
   "standard NER + knowledge-base linking practice. Unmappable places are ignored.",
   "<b>Risk tagging</b>: spaCy's <font name='Mono'>PhraseMatcher</font> (on lower-cased text) finds every "
   "vocabulary term; <font name='Mono'>filter_spans</font> keeps the longest match so “port congestion” "
   "is counted once, not also as “congestion”."])
TABLE([["Entity label", "Mentions found"]] + [[k, v] for k, v in M["ner"]["mentions_by_label"].items()] +
      [["Distinct organisations", M["ner"]["distinct_orgs"]], ["Distinct places", M["ner"]["distinct_places"]]],
      [70, 40])
H3("Risk vocabulary (data/risk_vocabulary.json)")
TABLE([["Risk type", "Sub-type", "Example terms (weight 1–3)"]] +
      [[k, v["sub_type"], ", ".join(f"{t} ({w})" for t, w in list(v["terms"].items())[:8]) + " …"]
       for k, v in vocab["risk_types"].items()], [24, 46, 104])
P("The vocabulary also holds <b>sector terms</b> (freight, cargo → Supply Chain &amp; Logistics; stores, "
  "e-commerce → Retail; bank, loan → Finance; plant, factory → Manufacturing) used to assign a sector to every "
  "event from the organisation name and its paragraph, and <b>intensity terms</b> (severe, halted, crore, "
  "stranded … vs. minor, resumed, limited impact) used in the impact score.")

H2("4.3 The co-occurrence relation rule")
CALL("<b>Rule.</b> In every paragraph that contains at least one ORGANISATION, one LOCATION and one RISK "
     "TERM, create a RiskEvent for each (organisation, location, risk type) combination and emit<br/>"
     "&nbsp;&nbsp;<font name='Mono'>&lt;entity&gt; ork:affects &lt;event&gt;</font> and "
     "<font name='Mono'>&lt;event&gt; ork:locatedIn &lt;location&gt;</font><br/>plus data-property triples "
     "(category, impact score, severity, date, provenance). Nothing is learned — the rule is fast, explainable "
     "and auditable; its known cost is precision.")
P("Two clean-ups follow: if an event is found both at a city and at that city's own state (“Mumbai, "
  "Maharashtra”) only the more specific city is kept, and duplicate (article, organisation, place, risk type) "
  "combinations are merged. Each event receives a deterministic id "
  "(<font name='Mono'>EV_</font> + MD5 of article|org|place|type), shared by its RDF node and its fact row.")
H3("Impact score and severity (transparent heuristic)")
CODE("""impact = 0.5 + 1.5 x (highest vocabulary weight of matched terms, 1..3)
       + 0.8 x min(mention_count - 1, 2)        # repeated coverage of the same risk type
       + 1.6 x article_intensity                 # +severe/halted/crore..., -minor/resumed...
       + 1.0 if the event is in the lead paragraph
impact clipped to [0, 10];   severity: Low < 4 <= Medium < 7 <= High""")
sev = events["severity"].value_counts()
P(f"In this run: {sev.get('High', 0)} High, {sev.get('Medium', 0)} Medium and {sev.get('Low', 0)} Low events; "
  f"mean impact {events['impact_score'].mean():.2f}.")
# worked example
counts = events.groupby("article_id").size()
aid = counts.sort_values(ascending=False).index[0]
art = articles.set_index("article_id").loc[aid]
evs = events[events.article_id == aid]
H3(f"Worked example — article {aid}")
CODE("\n\n".join(f"[para {i}] " + __import__('textwrap').fill(p, 100) for i, p in
                 enumerate(str(art.text).split("\n\n"))))
TABLE([["Event", "Para.", "Entity —affects→", "—locatedIn→ place", "Type", "Impact", "Severity"]] +
      [[r.event_id, r.para_no, r.entity_name, r.location, r.risk_type, r.impact_score, r.severity]
       for r in evs.itertuples()], [27, 12, 42, 30, 22, 14, 18])
P("Events from the lead paragraph are the true story; events created from a later paragraph may be genuine "
  "(a second disruption) or spurious (an analyst quoted in another city) — the rule cannot tell, which is "
  "exactly why precision is measured in §4.8.")

H2("4.4 The ontology")
P("Built as code with RDFLib (so it is version-controlled and regenerated on every run) and saved as "
  "<font name='Mono'>ontology/ontorisk.owl</font> (RDF/XML) which opens directly in <b>Protégé</b>, and as "
  "Turtle. The design follows §4.4 exactly: six classes, only two object properties, impact and provenance as "
  "data properties, no causal relations (the co-occurrence rule cannot distinguish cause from association).")
TABLE([["Class", "Meaning"]] + [[k, v] for k, v in ontology.CLASSES.items()], [32, 142])
TABLE([["Object property", "Domain → Range", "Meaning"]] +
      [[k, f"{d} → {r}", c] for k, (d, r, c) in ontology.OBJECT_PROPERTIES.items()], [32, 45, 97])
TABLE([["Data properties (selection)", "Domain", "Type"]] +
      [[k, d, str(r).split("#")[-1]] for k, (d, r, _) in list(ontology.DATA_PROPERTIES.items())[:12]],
      [55, 45, 30])
P("Extra axioms: the six classes are pairwise <font name='Mono'>owl:disjointWith</font>; "
  "<font name='Mono'>locatedIn</font>, <font name='Mono'>eventId</font>, <font name='Mono'>impactScore</font>, "
  "<font name='Mono'>severityBand</font> and <font name='Mono'>riskCategory</font> are functional. "
  "The five RiskType individuals and every vocabulary term (as a RiskTerm individual with its weight) are "
  "part of the ontology, so the vocabulary itself is machine-readable.")
H3("What the generated triples look like (Turtle)")
ev0 = events.iloc[0]
CODE(f"""@prefix ork: <{config.BASE_IRI}> .
@prefix ord: <{config.DATA_IRI}> .

ord:entity/{''.join(ch if ch.isalnum() else '_' for ch in ev0.entity_name)}  a ork:Entity ;
    ork:entityName "{ev0.entity_name}" ; ork:sector "{ev0.sector}" ;
    ork:affects ord:{ev0.event_id} .

ord:{ev0.event_id}  a ork:RiskEvent ;
    ork:locatedIn ord:location/{''.join(ch if ch.isalnum() else '_' for ch in ev0.location)} ;
    ork:riskCategory "{ev0.risk_type}" ; ork:impactScore {ev0.impact_score} ;
    ork:severityBand "{ev0.severity}" ; ork:eventDate "{ev0.date}"^^xsd:date ;
    ork:sourceId "{ev0.article_id}" ; ork:matchedTerm "{ev0.matched_term}" .""")
H3("Opening it in Protégé")
B(["Install Protégé 5.6+ (protege.stanford.edu) → File → Open → <font name='Mono'>ontology/ontorisk.owl</font>.",
   "Entities tab: browse the 6 classes, 2 object properties, data properties and the RiskType / RiskTerm "
   "individuals. OntoGraf tab: visual graph.",
   "Reasoner → HermiT → Start reasoner: checks the ontology is consistent.",
   "To inspect the populated graph, open <font name='Mono'>ontology/ontorisk_kg.ttl</font> instead (larger)."])

H2("4.5 SPARQL validation")
P("After triples are generated the knowledge graph is checked with SPARQL (RDFLib's built-in engine). "
  "All checks must pass; they also run in the test suite.")
TABLE([["Validation query", "Passed", "Result"]] +
      [[k.replace("_", " "), "yes" if v["passed"] else "NO",
        "; ".join(" ".join(r) for r in v["result"][:5])] for k, v in sparql.items()], [62, 16, 96])
CODE("""# Example: every High-severity event in Maharashtra, with the affected entity
SELECT ?entity ?type ?place ?date WHERE {
  ?e ork:severityBand "High" ; ork:riskCategory ?type ; ork:eventDate ?date ;
     ork:locatedIn ?loc .
  ?loc ork:state "Maharashtra" ; ork:placeName ?place .
  ?x ork:affects ?e ; ork:entityName ?entity } ORDER BY ?date""")

H2("4.6 The warehouse (DuckDB star schema)")
star_diagram()
P(f"<b>Engine used in this run:</b> {M['warehouse_engine']}. The schema follows Table 4.1. Entity and "
  "source are <b>degenerate attributes</b> on the fact row (Kimball &amp; Ross): they are never browsed "
  "hierarchically, so separate dimension tables would only add joins. DIM_LOCATION also stores the "
  "<font name='Mono'>place</font> (city/port) so the dashboard can drill down Region → State → Place, and "
  "DIM_TIME stores <font name='Mono'>month_name</font> for display.")
TABLE([["Table", "Rows"]] + [[k, v] for k, v in wh["rows"].items()], [70, 30])
P("The ETL (pandas) loads dimensions first, then facts, then the bridge. Afterwards the "
  "<b>referential checks</b> run: " + ", ".join(f"{k.replace('_', ' ')} = {v}" for k, v in
                                                wh["referential_checks"].items()) + ".")
P("<b>Hybrid (semantic) link.</b> Table <font name='Mono'>BRIDGE_SEMANTIC_LINK</font> stores, for every "
  "event_id, the RDF triples generated for it, and every RDF event carries <font name='Mono'>ork:eventId</font>. "
  "So SQL can jump from a fact row to its triples, and a SPARQL result can jump back to the fact row. A view, "
  "<font name='Mono'>V_RISK_EVENTS</font>, joins the fact with all dimensions and feeds the miners and the "
  "dashboard. <font name='Mono'>warehouse/olap_queries.sql</font> shows ROLLUP, drill-down, CUBE, slice/dice "
  "and the hybrid join.")
CODE("""-- Roll-up with subtotals (DuckDB)
SELECT region, risk_type, COUNT(*) AS events, ROUND(AVG(impact_score),2) AS avg_impact
FROM V_RISK_EVENTS GROUP BY ROLLUP (region, risk_type)
ORDER BY region NULLS LAST, events DESC;""")
FIGURE(FIG / "events_by_region_type.png", "Figure 3 — Risk events by region and type (from V_RISK_EVENTS).")
FIGURE(FIG / "monthly_trend.png", "Figure 4 — Seasonality: weather events peak in the June–September monsoon.")

H2("4.7 Data mining")
H3("Association rules (FP-Growth, Apriori as cross-check)")
P("Each risk event becomes a <b>transaction</b> — a basket of items describing it:")
tx_ex = ["risktype=weather", "region=West", "sector=Supply Chain & Logistics", "severity=High",
         "co_risk=logistics"]
CODE("{ " + ", ".join(tx_ex) + " }")
P("The four items from §4.6 (risk type, region, sector, severity band) are extended with "
  "<font name='Mono'>co_risk=&lt;type&gt;</font> for every <i>other</i> risk type reported in the same "
  "article — this is what lets the miner find co-occurring risk factors such as weather together with "
  "logistics. FP-Growth (mlxtend) finds itemsets with support ≥ "
  f"{ar['min_support']:.0%}; rules are kept when confidence ≥ {ar['min_confidence']:.0%} and lift ≥ "
  f"{ar['min_lift']}, with a single-item consequent for readability. Apriori run on the same data returns the "
  f"identical rule set: <b>{'yes' if ar['apriori_rules_identical'] else 'no'}</b>.")
TABLE([["If (antecedent)", "Then (consequent)", "Support", "Confidence", "Lift"]] +
      [[r.antecedents, r.consequents, f"{r.support:.3f}", f"{r.confidence:.2f}", f"{r.lift:.2f}"]
       for r in rules.head(12).itertuples()], [70, 46, 18, 20, 16])
FIGURE(FIG / "top_rules.png", "Figure 5 — Strongest rules by lift.")
if len(rules):
    r0 = rules.iloc[0]
    P(f"<b>How to read the top rule.</b> “{r0.antecedents} ⇒ {r0.consequents}”: {r0.support:.1%} of all "
      f"events contain both sides (support); when the left side holds, the right side holds "
      f"{r0.confidence:.0%} of the time (confidence); and that is {r0.lift:.2f}× more often than if the two "
      f"were independent (lift). The rules rediscover the monsoon story: weather disruption co-occurs with "
      f"port/freight disruption, hits logistics and manufacturing hardest and tends to be High severity.")
H3("k-Means clustering")
P("Feature vector per event: impact score, mention count, one-hot risk type (5 columns), and temporal features "
  "— month as sin/cos (so December sits next to January) and a monsoon-season flag. All features are "
  "standardised. Because the five one-hot columns describe one attribute (and the three time columns another), "
  "each block is divided by √(block size) so it weighs as much as a single numeric feature — otherwise the "
  "risk-type columns alone dictate the clusters.")
P(f"k is scanned over {cl['k_values'][0]}–{cl['k_values'][-1]}; the <b>elbow</b> is detected automatically "
  f"(the point of the inertia curve furthest from the straight line joining its ends) and validated with the "
  f"<b>silhouette score</b>. Elbow k = {cl['k_elbow']}, best-silhouette k = {cl['k_best_silhouette']}, chosen "
  f"k = {cl['k_chosen']} (silhouette {cl['silhouette_chosen']:.3f}). PCA projects the vectors to 2-D for the "
  f"scatter plot (PC1+PC2 explain {sum(cl['pca_explained_variance']):.0%} of variance).")
FIGURE(FIG / "kmeans_elbow_silhouette.png", "Figure 6 — Elbow and silhouette diagnostics.", 150)
FIGURE(FIG / "kmeans_clusters.png", "Figure 7 — Risk events coloured by cluster (PCA projection).")
TABLE([["Cluster", "Label", "Size", "Avg impact", "Top type (share)", "Monsoon share", "High share"]] +
      [[f"C{r.cluster}", r.label, r.size, f"{r.avg_impact:.2f}", f"{r.top_risk_type} ({r.top_risk_share:.0%})",
        f"{r.monsoon_share:.0%}", f"{r.high_share:.0%}"] for r in profiles.itertuples()],
      [14, 52, 13, 18, 33, 22, 18])
P("A silhouette around 0.2–0.3 means the groups are real but overlap — normal for mixed categorical/numeric "
  "event data; the clusters are still clearly interpretable (e.g. a high-impact monsoon-weather group versus "
  "low-impact off-monsoon events).")

H2("4.8 Evaluation of the extraction layer")
if q:
    P(f"Against the generator's ground truth, the co-occurrence rule produced {q['predicted_events']} events, "
      f"of which {q['correct_events']} are correct: <b>precision {pct(q['precision'])}</b>. It found "
      f"{q['gold_events_found']} of the {q['gold_events']} true events: <b>recall {pct(q['recall'])}</b> "
      f"(F1 {q['f1']:.3f}). On the 50-triple review sample the precision is {pct(q['sample_precision'])}.")
    TABLE([["Risk type", "Precision"]] + [[k, pct(v)] for k, v in q["precision_by_risk_type"].items()], [50, 30])
P("<b>Error analysis.</b> Almost all errors are the incidental co-mentions the report predicted: an analyst "
  "firm quoted in another city next to a risk word, or a second paragraph where a weather word and a port "
  "appear together (“the floods also triggered congestion at Mundra”) so the rule also creates a "
  "<i>weather</i>@Mundra event. Weather has the lowest precision for that reason. Recall is high because the "
  "rule is deliberately permissive; the events it misses come from the NER step — organisations the small "
  "spaCy model did not tag as ORG (e.g. some retail names) or span-boundary errors (“Northstar Securities in "
  "Hyderabad”, partly repaired by the name normaliser). Real news will give lower recall (more varied phrasing) — the manual "
  "review sheet <font name='Mono'>outputs/triple_review_sample.csv</font> is provided for exactly that case.")
P("<b>Why the paragraph window matters.</b> As an ablation, the first 160 articles were re-run with their "
  "paragraph breaks removed (so the rule falls back to the whole article, as it would for a CSV that stores "
  "each article as one block). The same text then produced 793 events instead of 256 — about three times as "
  "many, almost all of the extra ones spurious. Keeping paragraph boundaries when collecting real news is "
  "therefore the single most useful thing for precision.")
FIGURE(FIG / "severity_by_type.png", "Figure 8 — Severity mix by risk type.", 150)

H2("4.9 The dashboard")
P("A single Streamlit page (layout of Figure 4.4 in the report), connected directly to the DuckDB warehouse "
  "and the mining outputs. Top to bottom:")
B(["<b>KPI cards</b> (Table 4.3): Risk Exposure Index = Σ impact × severity weight (Low 1, Medium 2, High 3) "
   "with its share of total exposure; Average Impact Score; Events in View (of total); Top Rule Confidence "
   "(confidence of the highest-lift rule shown).",
   "<b>OLAP filters</b>: Region (multi-select), Time period (date range), Risk type (multi-select). "
   "A roll-up / drill-down panel re-aggregates the selection at Region → State → Place and Year → Quarter → "
   "Month for a chosen measure (events, average impact, exposure). Rule thresholds can be tuned with sliders.",
   "<b>Association rules table</b>: FP-Growth is <i>re-run on the filtered events</i>, so the rules respond "
   "to the selection (minimum 25 events).",
   "<b>k-Means scatter</b>: events in view, coloured and shaped by cluster, with hover details, plus a "
   "cluster profile table.",
   "Extras: a SPARQL console over the knowledge graph (example queries included) and the event table.",
   "Performance: data loading and rule mining are cached with <font name='Mono'>st.cache_data</font>; the "
   "RDF graph with <font name='Mono'>st.cache_resource</font>."])
FIGURE(FIG / "dashboard_preview.png", "Figure 9 — Static rendering of the dashboard's content with no filter "
       "applied (the live Streamlit page is interactive: hover, filters, drill-down, SPARQL console).", 150)

# ---------------------------------------------------------------- 5 technologies
H1("5. Technologies — what, how it is used here, why it matters")


def TECH(name, what, how, why, extra):
    H2(name)
    P(f"<b>What it is.</b> {what}")
    P(f"<b>How OntoRisk BI uses it.</b> {how}")
    P(f"<b>Significance in the project.</b> {why}")
    P(f"<b>Good to know.</b> {extra}")


TECH("Python 3",
     "A general-purpose, interpreted language with the richest ecosystem for data science, NLP and the semantic "
     "web.",
     "Every stage, from corpus generation to the dashboard, is Python; the package lives in "
     "<font name='Mono'>src/ontorisk</font> and one script runs the whole pipeline.",
     "One language for NLP, RDF, SQL, mining and UI means no glue code between tools and an easy hand-off "
     "between team members.",
     "Type hints, dataclasses (<font name='Mono'>Paragraph</font>, <font name='Mono'>GoldEvent</font>) and "
     "a central <font name='Mono'>config.py</font> keep the code readable. Python 3.10–3.13 is supported.")
TECH("pandas",
     "The standard Python library for tabular data: the DataFrame (labelled, typed columns) with fast "
     "filtering, grouping, joining and I/O.",
     "Reads the corpus CSV, performs all cleaning and quality checks (duplicates, empty text, date parsing), "
     "builds the dimension and fact tables, and is the exchange format between stages and with DuckDB.",
     "It is the ‘T’ of the ETL. DuckDB can query a pandas DataFrame directly, which removes a separate "
     "loading tool.",
     "<font name='Mono'>pd.to_datetime(errors='coerce')</font> turns bad dates into NaT so they can be "
     "counted and rejected; <font name='Mono'>duplicated()</font> detects duplicates; "
     "<font name='Mono'>crosstab</font>/<font name='Mono'>groupby</font> produce the OLAP-style summaries.")
TECH("spaCy (en_core_web_sm)",
     "An industrial-strength NLP library by Explosion AI (Honnibal &amp; Montani). Its pre-trained pipelines "
     "perform tokenisation, part-of-speech tagging, dependency parsing, lemmatisation and named entity "
     "recognition. <font name='Mono'>en_core_web_sm</font> is the small English pipeline (CNN-based, trained "
     "on OntoNotes 5; 18 entity types).",
     "Tokenisation, stop-word removal and lemmatisation in preprocessing; NER for ORG, GPE, LOC and DATE; "
     "the <font name='Mono'>PhraseMatcher</font> (with <font name='Mono'>attr='LOWER'</font>) for "
     "case-insensitive vocabulary matching; <font name='Mono'>filter_spans</font> for longest-match.",
     "NER is how unstructured text becomes candidate subjects and objects for RDF triples. Using a pre-trained "
     "model needs no annotated training data, which is what makes the project feasible in three weeks "
     "(Chapter 2 of the report).",
     "Larger models (<font name='Mono'>en_core_web_md/lg/trf</font>) are more accurate but slower; fine-tuning "
     "on Indian business news, or an EntityRuler with company lists, would raise recall. If spaCy is "
     "unavailable the code falls back to a regex/gazetteer recogniser so it still runs.")
TECH("RDF and RDFLib",
     "RDF (Resource Description Framework, W3C) represents knowledge as <i>triples</i> — subject, predicate, "
     "object — each identified by an IRI, forming a graph. RDFLib is the main Python library to create, parse, "
     "serialise (Turtle, RDF/XML, N-Triples, JSON-LD) and query RDF graphs.",
     "The ontology (T-Box) and the generated facts (A-Box) are built as an RDFLib <font name='Mono'>Graph</font> "
     "under the namespaces <font name='Mono'>ork:</font> (ontology) and <font name='Mono'>ord:</font> (data), "
     "and saved as Turtle / RDF/XML. RDFLib's SPARQL engine runs the validation and dashboard queries.",
     "RDF is the semantic layer: it gives each extracted fact explicit meaning (types and properties defined in "
     "the ontology) and lets heterogeneous facts be linked and queried by relationship rather than by table "
     "layout.",
     "Turtle is the human-readable syntax (<font name='Mono'>ord:x ork:affects ord:y .</font>). Typed literals "
     "(xsd:decimal, xsd:date) keep values comparable. Large graphs would move to a triple store such as "
     "Apache Jena Fuseki or GraphDB.")
TECH("OWL ontology and Protégé",
     "OWL (Web Ontology Language) adds vocabulary on top of RDF to define classes, properties, domains, "
     "ranges, disjointness and cardinality, so a reasoner can check consistency and infer facts. Protégé "
     "(Stanford, Musen) is the most widely used open-source ontology editor.",
     "Six owl:Class, two owl:ObjectProperty with domain/range, typed owl:DatatypeProperty, disjoint classes "
     "and functional properties, plus RiskType and RiskTerm individuals. The file "
     "<font name='Mono'>ontorisk.owl</font> is designed to be opened, inspected, visualised (OntoGraf) and "
     "reasoned over (HermiT) in Protégé.",
     "The ontology is the shared schema of the semantic layer — it states what a RiskEvent is and how it "
     "relates to an Entity and a Location — and the SPARQL checks verify the extracted data actually conforms "
     "to it.",
     "Keeping the ontology small is a design decision from the literature: a limited class/property set is "
     "easier to populate consistently from automatic extraction. Causal properties (causes, mitigates) were "
     "deliberately not defined because co-occurrence cannot populate them faithfully.")
TECH("SPARQL",
     "The W3C query language for RDF (SPARQL 1.1). Queries match graph patterns of triples with variables and "
     "support FILTER, OPTIONAL, aggregation (GROUP BY, COUNT, AVG), sub-queries and NOT EXISTS.",
     "Six validation queries (class count, property count, every event has a location and an affected "
     "entity, domain/range respected, events per type) and four example semantic queries exposed in the "
     "dashboard.",
     "It is the planned validation mechanism (§4.4) and gives associative, relationship-first queries — e.g. "
     "“entities exposed to more than one risk type” — that are awkward in SQL.",
     "<font name='Mono'>FILTER NOT EXISTS</font> is used to find violations (an event without a location). "
     "SPARQLWrapper would be used instead of RDFLib to query a remote endpoint.")
TECH("DuckDB",
     "An embedded, in-process analytical (OLAP) database — “SQLite for analytics”: column-oriented, "
     "vectorised execution, no server, a single file, full SQL including ROLLUP/CUBE/GROUPING SETS and window "
     "functions, and zero-copy access to pandas DataFrames.",
     "Stores the star schema (FACT_RISKEVENT, DIM_TIME, DIM_LOCATION, DIM_RISKTYPE), the semantic bridge, the "
     "staging table and the denormalised view V_RISK_EVENTS. Data are loaded straight from DataFrames "
     "(<font name='Mono'>register</font> + <font name='Mono'>INSERT … SELECT</font>); the dashboard opens it "
     "read-only.",
     "It provides warehouse behaviour (keys, joins, fast aggregation) on a laptop without installing a "
     "database server — exactly the reason given in §4.5.",
     "If DuckDB is not installed the same schema is created in SQLite so the pipeline still runs; "
     "<font name='Mono'>metrics.json</font> records the engine. The DuckDB CLI can run "
     "<font name='Mono'>olap_queries.sql</font> directly.")
TECH("Star schema, Kimball and Inmon",
     "Dimensional modelling (Kimball &amp; Ross) organises a warehouse into a central fact table of numeric "
     "measures at a declared grain, surrounded by descriptive dimension tables. Inmon's view stresses an "
     "integrated, subject-oriented warehouse fed from many sources.",
     "Grain = one detected risk event. Measures: impact_score, mention_count (severity as a band). "
     "Dimensions: time, location (with a Region → State → Place hierarchy), risk type. Degenerate attributes: "
     "entity name and source id. Surrogate integer keys; time_key = YYYYMMDD.",
     "The star schema makes OLAP questions (by region, quarter, risk type) simple, fast joins, and it is the "
     "relational half of the hybrid warehouse; the RDF graph is the semantic half (Inmon's integration of two "
     "representations of the same events).",
     "Larger versions would normalise entity and source into dimensions with slowly changing dimension (SCD "
     "Type 2) handling.")
TECH("OLAP operations",
     "Online Analytical Processing: interactive analysis of multidimensional data. Core operations: roll-up "
     "(aggregate to a coarser level), drill-down (finer level), slice (fix one dimension), dice (sub-cube on "
     "several), pivot.",
     "The dashboard's filters slice and dice by region, period and risk type; the roll-up/drill-down panel "
     "moves along Region → State → Place and Year → Quarter → Month; olap_queries.sql shows SQL "
     "ROLLUP and CUBE.",
     "OLAP is the main interaction model planned for the dashboard (§2.4).",
     "GROUP BY ROLLUP(a, b) returns totals for (a, b), (a) and the grand total in one query.")
TECH("mlxtend — FP-Growth and Apriori",
     "mlxtend (Raschka) provides frequent-pattern mining. Apriori (Agrawal &amp; Srikant, 1994) generates "
     "candidate itemsets level by level and prunes with the ‘every subset of a frequent itemset is frequent’ "
     "property. FP-Growth (Han, Pei &amp; Yin, 2000) compresses the transactions into an FP-tree and mines it "
     "recursively without candidate generation — faster on larger data.",
     "<font name='Mono'>TransactionEncoder</font> one-hot encodes the event baskets, "
     "<font name='Mono'>fpgrowth</font> finds frequent itemsets, <font name='Mono'>association_rules</font> "
     "derives rules with support, confidence, lift, leverage and conviction; Apriori is run as a cross-check.",
     "It discovers co-occurring risk factors — the first analytical output of the dashboard — with no labelled "
     "data, and the results are directly interpretable.",
     "Support(A⇒B) = P(A∧B); Confidence = P(B|A); Lift = Confidence / P(B) (&gt; 1 means positive "
     "association, 1 independence); Leverage = P(A∧B) − P(A)P(B); Conviction = (1 − P(B)) / (1 − Confidence).")
TECH("scikit-learn — k-Means, silhouette, PCA",
     "scikit-learn is the standard Python machine-learning library. k-Means (MacQueen, 1967) partitions points "
     "into k clusters by alternately assigning each point to its nearest centroid and moving each centroid to "
     "its cluster mean, minimising within-cluster sum of squares (inertia). The silhouette score (−1…1) "
     "compares each point's cohesion with its separation from the next cluster. PCA projects data onto the "
     "directions of largest variance.",
     "<font name='Mono'>StandardScaler</font> for scaling, <font name='Mono'>KMeans(n_init=10, random_state=42)"
     "</font> for k = 2…10, <font name='Mono'>silhouette_score</font> for validation, "
     "<font name='Mono'>PCA(2)</font> for the scatter plot.",
     "Clustering groups similar disruption events (the second analytical output) and needs only k, which the "
     "elbow + silhouette procedure selects.",
     "k-Means assumes roughly spherical clusters and is sensitive to scale — hence standardisation and block "
     "weighting. DBSCAN (density-based, finds outliers) was deliberately deferred because its eps/min_samples "
     "need careful tuning.")
TECH("Streamlit and Plotly",
     "Streamlit turns a Python script into an interactive web app: every widget interaction re-runs the "
     "script top to bottom; caching decorators avoid repeating expensive work. Plotly draws interactive "
     "(hover, zoom) charts in the browser.",
     "Single page: st.metric KPI cards, multiselect / date_input / radio / slider filters, st.dataframe with "
     "progress-bar columns for the rules, Plotly Express bar (OLAP) and scatter (clusters) charts, an expander "
     "with a SPARQL console.",
     "It delivers the decision-support layer with a few hundred lines of Python and no front-end code.",
     "Run with <font name='Mono'>streamlit run dashboard/app.py</font>; it serves on "
     "http://localhost:8501. Business logic sits in <font name='Mono'>logic.py</font> so it can be unit tested.")
TECH("pytest, matplotlib, Git/GitHub",
     "pytest is Python's de-facto test framework; matplotlib is the base plotting library; Git with GitHub "
     "hosts the code and supports branch-based collaboration.",
     "17 tests cover the ontology, NER, longest-match tagging, the co-occurrence rule, RDF validity, severity "
     "bands, ETL quality checks, warehouse integrity, FP-Growth = Apriori, k-Means diagnostics, precision, "
     "dashboard KPIs and a full dashboard run. matplotlib renders the figures in outputs/figures. One Git "
     "branch per pipeline stage, merged into main after review (§4.8).",
     "Tests make each stage independently verifiable — the property the layered architecture was designed "
     "for.",
     "<font name='Mono'>python -m pytest</font> runs everything; the dashboard test uses Streamlit's official "
     "AppTest when Streamlit is installed.")

# ---------------------------------------------------------------- 6 methodologies
H1("6. Methodologies in more depth")
H2("6.1 The semantic-web stack")
P("Layers, bottom-up: IRIs to name things → RDF to state facts as triples → RDFS/OWL to define the vocabulary "
  "(classes, properties, constraints) → SPARQL to query → reasoners to infer and check consistency. "
  "OntoRisk BI uses each layer minimally: IRIs under ontorisk.example.org, RDF triples from the co-occurrence "
  "rule, a six-class OWL ontology, SPARQL validation, and Protégé/HermiT for consistency checking.")
H2("6.2 ETL and data quality")
P("Extract (read CSV) → Transform (clean, validate, enrich with NLP, compute measures, map to surrogate keys) "
  "→ Load (dimensions before facts, then the bridge). Quality checks follow the report: empty/null text, "
  "duplicate ids and duplicate texts, unparseable dates, and post-load referential integrity (no fact row may "
  "point to a missing dimension row; every fact has triples; no null measures). Rejections are counted in "
  "<font name='Mono'>metrics.json</font>.")
H2("6.3 Rule-based relation extraction vs. learned extraction")
P("Learned relation extraction (e.g. a fine-tuned transformer classifying entity pairs) needs annotated "
  "relation data. Co-occurrence within a bounded window is the established low-cost alternative: high recall, "
  "lower precision, fully transparent. Precision is then <i>measured</i>, not assumed — and that number "
  "conditions how much trust to put in everything downstream.")
H2("6.4 Association-rule mining, step by step")
B(["Encode each event as a set of items; one-hot encode all baskets.",
   "FP-Growth: count item frequencies, drop infrequent items, sort items in each basket by frequency, insert "
   "baskets into a prefix tree (FP-tree); mine each item's conditional pattern base recursively to list all "
   "frequent itemsets.",
   "For each frequent itemset, split into antecedent ⇒ consequent and compute confidence and lift; keep rules "
   "above the thresholds; rank by lift.",
   "Interpretation: lift &gt; 1 with good support and confidence indicates a recurring risk pattern worth "
   "monitoring; rules describe association, not causation."])
H2("6.5 Clustering, step by step")
B(["Build the feature matrix; standardise each feature to mean 0, variance 1; weight one-hot and temporal "
   "blocks.",
   "For each k: run k-Means 10 times from different starts (k-means++), keep the lowest inertia; record "
   "inertia and silhouette.",
   "Pick k at the elbow; confirm with silhouette; refit; describe each cluster by size, average impact, "
   "dominant risk type, monsoon share and share of High-severity events; generate a readable label.",
   "Project to 2-D with PCA only for display — the clustering itself uses all features."])
H2("6.6 Evaluation metrics")
B(["Precision = correct extracted events / all extracted events; Recall = true events found / all true events; "
   "F1 = harmonic mean.",
   "Association rules: support, confidence, lift thresholds (and leverage/conviction reported).",
   "Clustering: inertia (elbow) and silhouette coefficient, plus visual inspection of the scatter plot."])

# ---------------------------------------------------------------- 7 results summary
H1("7. Results summary")
TABLE([
    ["Measure", "Value"],
    ["Articles (raw → clean)", f"{etlq['rows_in']} → {etlq['rows_out']}"],
    ["Risk events extracted", f"{len(events)}"],
    ["By risk type", ", ".join(f"{k} {v}" for k, v in events.risk_type.value_counts().items())],
    ["By sector", ", ".join(f"{k} {v}" for k, v in events.sector.value_counts().items())],
    ["RDF triples (total / generated)", f"{M['rdf']['total_triples']:,} / {M['rdf']['abox_triples']:,}"],
    ["SPARQL checks passed", f"{sum(M['sparql_validation'].values())} / {len(M['sparql_validation'])}"],
    ["Warehouse orphans / facts without triples", f"{wh['referential_checks']['orphan_time'] + wh['referential_checks']['orphan_location'] + wh['referential_checks']['orphan_risktype']} / {wh['referential_checks']['facts_without_triples']}"],
    ["Frequent itemsets / rules", f"{ar['frequent_itemsets']} / {ar['rules']}"],
    ["k-Means k / silhouette", f"{cl['k_chosen']} / {cl['silhouette_chosen']:.3f}"],
    ["Triple precision / recall / F1", f"{pct(q['precision'])} / {pct(q['recall'])} / {q['f1']:.3f}" if q else "—"],
    ["NLP backend", M["nlp_backend"]],
    ["Warehouse engine", M["warehouse_engine"]],
    ["Pipeline runtime", f"{M['runtime_seconds']} s"],
], [62, 112])
if "SQLite" in M["warehouse_engine"]:
    CALL("<b>Note on the warehouse engine for these numbers.</b> The run that produced this report was made "
         "on a machine where the DuckDB Python package could not be installed, so the pipeline used its "
         "built-in SQLite fallback with the <i>identical</i> schema and SQL. The same star schema, view and "
         "every query in <font name='Mono'>warehouse/olap_queries.sql</font> (ROLLUP, CUBE, the hybrid join) "
         "were separately loaded and run in the DuckDB 1.4.1 CLI without errors. After "
         "<font name='Mono'>pip install -r requirements.txt</font> on your laptop, "
         "<font name='Mono'>run_pipeline.py</font> uses DuckDB automatically and writes "
         "<font name='Mono'>warehouse/ontorisk.duckdb</font>; all counts and mining results are the same, "
         "because the warehouse engine does not affect them.")
P("<b>Key findings on this corpus.</b> (1) Weather disruption is concentrated in the monsoon months and "
  "co-occurs with logistics disruption with lift above 2.5; (2) weather events are disproportionately High "
  "severity, especially for logistics and manufacturing firms; (3) policy events are typically Medium "
  "severity and come with supplier knock-on effects; (4) clustering separates high-impact monsoon weather "
  "events from low-impact off-season events. Because the corpus is synthetic these findings show the "
  "pipeline <i>can recover</i> planted patterns — on real news the same code reports whatever patterns exist.")

# ---------------------------------------------------------------- 8 run guide
H1("8. How to run the project")
H2("8.1 One-time setup")
CODE("""# 1. unzip ontorisk-bi.zip and open a terminal in the ontorisk-bi folder
# 2. create and activate a virtual environment (Python 3.10 - 3.13)
python -m venv .venv
.venv\\Scripts\\activate            # Windows (PowerShell / cmd)
source .venv/bin/activate          # macOS / Linux

# 3. install the libraries and the spaCy English model
pip install -r requirements.txt
python -m spacy download en_core_web_sm""")
H2("8.2 Build everything")
CODE("""python run_pipeline.py
# [hh:mm:ss] 1/8 corpus: 243 raw records (synthetic)
# [hh:mm:ss] 2/8 ontology: ... T-Box triples -> ontology/ontorisk.owl
# ...
# [hh:mm:ss] 8/8 evaluation: precision=... recall=...; figures -> outputs/figures
# Done. Launch the dashboard with:  streamlit run dashboard/app.py""")
H2("8.3 Test, then open the dashboard")
CODE("""python -m pytest                     # all tests should pass
streamlit run dashboard/app.py       # browser opens at http://localhost:8501""")
H2("8.4 Optional steps")
B(["<b>Real news data</b>: <font name='Mono'>python run_pipeline.py --input path/to/news.csv</font> "
   "(no gold file → the manual review sheet is the precision check).",
   "<b>Bigger synthetic corpus</b>: <font name='Mono'>python run_pipeline.py --n 300</font>.",
   "<b>Protégé</b>: open <font name='Mono'>ontology/ontorisk.owl</font>.",
   "<b>DuckDB CLI</b>: <font name='Mono'>duckdb warehouse/ontorisk.duckdb &lt; warehouse/olap_queries.sql</font>.",
   "<b>Change thresholds</b> (support, confidence, lift, k range, severity bands) in "
   "<font name='Mono'>src/ontorisk/config.py</font>; edit the vocabulary in "
   "<font name='Mono'>data/risk_vocabulary.json</font>.",
   "<b>Regenerate this PDF</b>: <font name='Mono'>python docs/build_explanation_pdf.py</font>."])
H2("8.5 Troubleshooting")
TABLE([
    ["Symptom", "Fix"],
    ["OSError: [E050] Can't find model 'en_core_web_sm'", "python -m spacy download en_core_web_sm (inside the "
     "activated venv)"],
    ["metrics.json says “rule-based fallback” or “SQLite”", "spaCy / DuckDB not installed in the active "
     "environment — pip install -r requirements.txt, then re-run the pipeline"],
    ["Dashboard: “Warehouse not found”", "run python run_pipeline.py first"],
    ["duckdb IOException: could not set lock", "close other programs (DuckDB CLI, another Streamlit) using "
     "warehouse/ontorisk.duckdb, then re-run"],
    ["'streamlit' is not recognized", "activate the venv, or use python -m streamlit run dashboard/app.py"],
    ["No rules shown in dashboard", "selection has fewer than 25 events or thresholds too strict — widen filters "
     "or lower thresholds"],
], [70, 104])

# ---------------------------------------------------------------- 9 team
H1("9. Team allocation and timeline (Table 4.4, mapped to code)")
TABLE([
    ["Week", "Member tasks", "Code produced", "Deliverable check"],
    ["1", "A — ontology in Protégé; B — dataset collection & cleaning; C — spaCy NER pipeline; D — DuckDB "
     "schema & ETL skeleton", "ontology.py, corpus.py, etl.py, nlp.py, warehouse.py (DDL)",
     "six-class ontology; corpus cleaned; NER on sample text; empty star schema"],
    ["2", "A + C — co-occurrence triples & ontology linking; B + D — ETL load & quality checks",
     "extraction.py, semantic.py, warehouse.py (load, checks)", "triples linked; SPARQL checks pass; warehouse "
     "populated and linked to triples"],
    ["3", "A + B — FP-Growth & k-Means; C + D — Streamlit dashboard; all — integration & testing",
     "mining.py, evaluate.py, figures.py, dashboard/, tests/", "rules & clusters evaluated; dashboard live; "
     "end-to-end tests pass; documentation & demo"],
], [12, 66, 50, 46])
P("Git workflow: one branch per stage (e.g. <font name='Mono'>feat/ontology</font>, "
  "<font name='Mono'>feat/ner</font>, <font name='Mono'>feat/warehouse</font>, "
  "<font name='Mono'>feat/mining</font>, <font name='Mono'>feat/dashboard</font>), merged to "
  "<font name='Mono'>main</font> by pull request after the tests pass.")

# ---------------------------------------------------------------- 10 limitations
H1("10. Limitations and future scope")
H2("Limitations (from the report, confirmed by the build)")
B(["Corpus of 150–300 articles is modest; the bundled corpus is synthetic, so the mined patterns demonstrate "
   "the method rather than real-world findings.",
   f"Co-occurrence produces spurious triples (measured precision {pct(q['precision']) if q else 'n/a'}).",
   "Compact ontology, two object properties, no causal taxonomy: the semantic layer records association, not "
   "causation.",
   "Entity and source are degenerate attributes — fine at this scale, not for hierarchical browsing.",
   "Batch processing of historical text, no live feeds; no supervised severity classification (no labels); "
   "no alerting layer.",
   "Impact score is a transparent heuristic, not a calibrated financial measure."])
H2("Future scope")
B(["Pruned decision-tree classifier for severity once a labelled subset exists; DBSCAN with tuned parameters "
   "for outliers; rule-based alerting over mining outputs.",
   "Learned relation extraction (fine-tuned transformer) replacing the co-occurrence rule; then a causal "
   "relation taxonomy (causes, mitigates) in the ontology.",
   "Entity and source as full dimensions with SCD Type 2; real-time news / social-media ingestion; more "
   "sectors and geographies; SVM, ensembles, BIRCH, OPTICS on a larger labelled dataset.",
   "Entity linking to Wikidata / company registries; a triple store (Fuseki/GraphDB) with OWL reasoning."])

# ---------------------------------------------------------------- 11 viva
H1("11. Likely questions and model answers")
QA = [
    ("What is the main contribution of OntoRisk BI?",
     "Integration: a single open pipeline that connects text analytics, a semantic layer (ontology + RDF + "
     "SPARQL), a star-schema warehouse and data mining, ending in a dashboard. No single layer is novel; the "
     "end-to-end combination for SME risk intelligence is."),
    ("Why do you need both RDF and a star schema? Isn't that duplication?",
     "They serve different questions. The RDF graph captures meaning and relationships and supports flexible, "
     "relationship-first SPARQL queries and validation against the ontology; the star schema gives fast, "
     "familiar OLAP aggregation for BI. The shared event_id and the bridge table keep the two consistent — "
     "this is the ‘hybrid warehouse’."),
    ("How are relations extracted?",
     "By a documented co-occurrence rule, not a trained model: an organisation, a location and a risk term in "
     "the same paragraph generate ‘entity affects event’ and ‘event locatedIn location’. It is fast and "
     "auditable; its precision is measured."),
    ("What is the precision of your extraction and how did you measure it?",
     (f"{pct(q['precision'])} precision and {pct(q['recall'])} recall against ground-truth labels for every "
      "event in the corpus; a 50-triple random sample is also exported for manual review, as planned in the "
      "report." if q else "Using the 50-triple manual review sheet.")),
    ("Why spaCy and not a transformer like BERT?",
     "Pre-trained spaCy pipelines give a good accuracy/cost balance, run on a laptop CPU and need no "
     "annotated data. A transformer would need fine-tuning data and GPU time we did not have in three weeks."),
    ("Why only six classes and two object properties?",
     "A compact ontology is easier to populate consistently from automatic extraction. Defining properties "
     "such as ‘causes’ that the rule cannot populate faithfully would weaken the semantic layer."),
    ("Why is impact a data property and not a class?",
     "Impact is a value describing one event (a score and a band), not a thing with its own identity and "
     "relationships, so modelling it as a data property is simpler and correct."),
    ("What does ‘degenerate dimension’ mean?",
     "An attribute kept on the fact row without its own dimension table — here entity name and source id. "
     "They are never browsed hierarchically, so a dimension table would only add joins."),
    ("Why DuckDB instead of MySQL/PostgreSQL?",
     "DuckDB is an embedded columnar OLAP engine: no server, one file, very fast aggregation, and it reads "
     "pandas DataFrames directly — ideal for a short laptop project."),
    ("Explain support, confidence and lift with one of your rules.",
     (f"For “{rules.iloc[0].antecedents} ⇒ {rules.iloc[0].consequents}”: support {rules.iloc[0].support:.3f} "
      f"is the share of events containing both sides; confidence {rules.iloc[0].confidence:.2f} is how often "
      f"the consequent holds given the antecedent; lift {rules.iloc[0].lift:.2f} says that is "
      f"{rules.iloc[0].lift:.1f}× more than chance." if len(rules) else "Support = P(A∧B), confidence = P(B|A), "
      "lift = confidence / P(B).")),
    ("Why FP-Growth over Apriori?",
     "FP-Growth avoids repeated candidate generation and database scans by mining a compressed FP-tree, so "
     "it scales better; on our data it returns exactly the same rules as Apriori, which we check."),
    ("How did you choose k for k-Means?",
     f"Elbow method on inertia for k = 2–10, detected automatically, validated with the silhouette score; "
     f"chosen k = {cl['k_chosen']} with silhouette {cl['silhouette_chosen']:.3f}."),
    ("Why scale features and down-weight the one-hot block?",
     "k-Means uses Euclidean distance, so unscaled features with large ranges dominate. Five one-hot columns "
     "for one attribute would also count five times; dividing the block by √5 gives it the weight of one "
     "feature."),
    ("Why not DBSCAN or decision trees?",
     "DBSCAN needs careful eps/min_samples tuning on more data; decision trees need reliable severity labels "
     "that the corpus does not provide. Both are documented as future work."),
    ("Is the data real?",
     "The bundled corpus is synthetic with fictional companies and real Indian places/seasonality, chosen so "
     "results are reproducible and precision can be measured exactly. The pipeline also runs unchanged on a "
     "real news CSV via --input."),
    ("How is the Risk Exposure Index computed?",
     "Σ over events in view of impact score × severity weight (Low 1, Medium 2, High 3), shown with its "
     "share of total exposure."),
    ("What does the SPARQL validation check?",
     "Six classes and two object properties exist; every event has a location and an affected entity; "
     "affects/locatedIn respect their domain and range; events per risk type are returned."),
    ("How does the dashboard stay responsive?",
     "Data loading and rule mining are cached with st.cache_data, the RDF graph with st.cache_resource; "
     "rules are re-mined only when the filtered event set changes."),
    ("What happens with an article mentioning many companies?",
     "The rule creates an event for each company–place–risk combination in the paragraph, which raises recall "
     "but lowers precision — the main limitation, quantified by the evaluation."),
    ("How would you scale this to thousands of articles a day?",
     "Stream ingestion (e.g. RSS/APIs) into a queue, spaCy nlp.pipe batching, a triple store for the graph, "
     "incremental DuckDB loads or a cloud warehouse, scheduled re-mining, and alerting on new high-lift rules."),
]
for qq, aa in QA:
    story.append(KeepTogether([Paragraph(qq, S["q"]), Paragraph(aa, S["body"])]))

# ---------------------------------------------------------------- 12 glossary + refs
H1("12. Glossary")
TABLE([["Term", "Meaning"]] + [list(x) for x in [
    ("Ontology", "Formal definition of the concepts (classes) and relations (properties) of a domain."),
    ("Triple", "Subject–predicate–object statement, the unit of RDF."),
    ("T-Box / A-Box", "Terminology (the ontology schema) / Assertions (the instance facts)."),
    ("IRI", "Internationalised Resource Identifier — the global name of an RDF resource."),
    ("NER", "Named Entity Recognition — finding names of organisations, places, dates in text."),
    ("Lemma", "Dictionary form of a word (‘disrupted’ → ‘disrupt’)."),
    ("Gazetteer", "Lookup list of place names with their attributes."),
    ("Fact table / grain", "Table of measurable events / what one row represents."),
    ("Dimension", "Descriptive context for facts (time, location, risk type)."),
    ("Surrogate key", "System-generated integer key for a dimension row."),
    ("OLAP", "Online Analytical Processing — roll-up, drill-down, slice, dice, pivot."),
    ("Itemset / transaction", "Set of items / one basket (one event) in rule mining."),
    ("Support, confidence, lift", "Frequency, conditional probability, and strength-versus-chance of a rule."),
    ("Inertia", "Sum of squared distances of points to their cluster centroid."),
    ("Silhouette", "Cluster quality from −1 (wrong) to 1 (well separated)."),
    ("Precision / recall", "Share of extracted items that are correct / share of true items extracted."),
]], [45, 129])
H1("13. References")
for ref in [
    "R. Agrawal and R. Srikant, “Fast Algorithms for Mining Association Rules in Large Databases,” VLDB, 1994.",
    "J. Han, J. Pei and Y. Yin, “Mining Frequent Patterns without Candidate Generation,” ACM SIGMOD, 2000.",
    "J. MacQueen, “Some Methods for Classification and Analysis of Multivariate Observations,” 5th Berkeley "
    "Symposium, 1967.",
    "M. Ester, H.-P. Kriegel, J. Sander and X. Xu, “A Density-Based Algorithm for Discovering Clusters…,” KDD, 1996.",
    "J. R. Quinlan, C4.5: Programs for Machine Learning, Morgan Kaufmann, 1993.",
    "T. Berners-Lee, J. Hendler and O. Lassila, “The Semantic Web,” Scientific American, 2001.",
    "R. Kimball and M. Ross, The Data Warehouse Toolkit, 3rd ed., Wiley, 2013.",
    "W. H. Inmon, Building the Data Warehouse, 4th ed., Wiley, 2005.",
    "M. A. Musen, “The Protégé Project: A Look Back and a Look Forward,” AI Matters, 2015.",
    "P. J. Rousseeuw, “Silhouettes: a graphical aid to the interpretation and validation of cluster analysis,” "
    "J. Comput. Appl. Math., 1987.",
    "Documentation: spaCy (spacy.io), RDFLib (rdflib.readthedocs.io), W3C RDF/OWL/SPARQL 1.1, DuckDB "
    "(duckdb.org/docs), mlxtend (rasbt.github.io/mlxtend), scikit-learn (scikit-learn.org), Streamlit "
    "(docs.streamlit.io), Plotly (plotly.com/python).",
]:
    story.append(Paragraph(ref, S["bullet"], bulletText="•"))

# ------------------------------------------------------------------ build
doc = Doc(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=17 * mm,
          bottomMargin=18 * mm, title="OntoRisk BI — Project Explanation & Technical Guide",
          author="Aishwarya Patil, T. V. S. Sai Teja, Dhruv Naveen, Shaswat Das")
doc.multiBuild(story, onFirstPage=on_page, onLaterPages=on_page)
print(f"wrote {OUT}")
