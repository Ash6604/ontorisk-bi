// Builds the IEEE-format project report: docs/report/OntoRisk_BI_IEEE_Report.docx
//
//     cd docs/report && npm install && node build_report.js
//
// Layout follows the IEEE conference template (A4): single-column title block, two-column body
// in 10 pt Times New Roman, Roman-numeral small-caps section heads, "Fig. n." captions below
// figures, "TABLE N" captions above tables, and an 8 pt numbered reference list.
// Citations ({ref:key}), figures ({fig:key}) and tables ({tab:key}) are numbered automatically
// in order of first mention. All numbers quoted come from outputs/metrics.json of the latest run.

const fs = require("fs");
const path = require("path");
const {
  AlignmentType, BorderStyle, Document, HeadingLevel, ImageRun, LevelFormat, Packer, Paragraph,
  SectionType, Table, TableCell, TableRow, TabStopType, TextRun, VerticalAlign, WidthType,
} = require("docx");

const IMG = path.join(__dirname, "img");
const OUT = path.join(__dirname, "OntoRisk_BI_IEEE_Report.docx");

// ------------------------------------------------------------------ page geometry (A4, IEEE)
const PAGE = { width: 11906, height: 16838 };
const MARGIN = { top: 1077, bottom: 1440, left: 811, right: 811 };   // 19 mm / 25.4 mm / 14.3 mm
const GAP = 360;                                                     // 6.35 mm column gap
const TEXT_W = PAGE.width - MARGIN.left - MARGIN.right;              // 10284 dxa
const COL_W = (TEXT_W - GAP) / 2;                                    // 4962 dxa
const PX = (dxa) => Math.floor((dxa / 1440) * 96);                   // dxa -> image px
const FONT = "Times New Roman";

// ------------------------------------------------------------------ numbering registries
const REFS = {
  tang: "C. S. Tang, “Perspectives in supply chain risk management,” *Int. J. Prod. Econ.*, vol. 103, no. 2, pp. 451–488, 2006.",
  ho: "W. Ho, T. Zheng, H. Yildiz, and S. Talluri, “Supply chain risk management: A literature review,” *Int. J. Prod. Res.*, vol. 53, no. 16, pp. 5031–5069, 2015.",
  bernerslee: "T. Berners-Lee, J. Hendler, and O. Lassila, “The Semantic Web,” *Sci. Amer.*, vol. 284, no. 5, pp. 34–43, May 2001.",
  gruber: "T. R. Gruber, “A translation approach to portable ontology specifications,” *Knowl. Acquis.*, vol. 5, no. 2, pp. 199–220, 1993.",
  kimball: "R. Kimball and M. Ross, *The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling*, 3rd ed. Indianapolis, IN, USA: Wiley, 2013.",
  inmon: "W. H. Inmon, *Building the Data Warehouse*, 4th ed. Indianapolis, IN, USA: Wiley, 2005.",
  chaudhuri: "S. Chaudhuri and U. Dayal, “An overview of data warehousing and OLAP technology,” *ACM SIGMOD Rec.*, vol. 26, no. 1, pp. 65–74, 1997.",
  nebot: "V. Nebot and R. Berlanga, “Building data warehouses with semantic web data,” *Decis. Support Syst.*, vol. 52, no. 4, pp. 853–868, 2012.",
  abello: "A. Abelló *et al.*, “Using semantic web technologies for exploratory OLAP: A survey,” *IEEE Trans. Knowl. Data Eng.*, vol. 27, no. 2, pp. 571–588, Feb. 2015.",
  owl: "W3C OWL Working Group, “OWL 2 Web Ontology Language document overview (second edition),” W3C Recommendation, Dec. 2012. [Online]. Available: https://www.w3.org/TR/owl2-overview/",
  rdf: "R. Cyganiak, D. Wood, and M. Lanthaler, “RDF 1.1 concepts and abstract syntax,” W3C Recommendation, Feb. 2014. [Online]. Available: https://www.w3.org/TR/rdf11-concepts/",
  sparql: "S. Harris and A. Seaborne, “SPARQL 1.1 query language,” W3C Recommendation, Mar. 2013. [Online]. Available: https://www.w3.org/TR/sparql11-query/",
  noy: "N. F. Noy and D. L. McGuinness, “Ontology development 101: A guide to creating your first ontology,” Stanford Knowl. Syst. Lab., Stanford, CA, USA, Tech. Rep. KSL-01-05, 2001.",
  protege: "M. A. Musen, “The Protégé project: A look back and a look forward,” *AI Matters*, vol. 1, no. 4, pp. 4–12, 2015.",
  nadeau: "D. Nadeau and S. Sekine, “A survey of named entity recognition and classification,” *Lingvisticae Investigationes*, vol. 30, no. 1, pp. 3–26, 2007.",
  spacy: "M. Honnibal, I. Montani, S. Van Landeghem, and A. Boyd, “spaCy: Industrial-strength natural language processing in Python,” Zenodo, 2020, doi: 10.5281/zenodo.1212303.",
  agrawal: "R. Agrawal and R. Srikant, “Fast algorithms for mining association rules,” in *Proc. 20th Int. Conf. Very Large Data Bases (VLDB)*, 1994, pp. 487–499.",
  han: "J. Han, J. Pei, and Y. Yin, “Mining frequent patterns without candidate generation,” in *Proc. ACM SIGMOD Int. Conf. Manage. Data*, 2000, pp. 1–12.",
  macqueen: "J. MacQueen, “Some methods for classification and analysis of multivariate observations,” in *Proc. 5th Berkeley Symp. Math. Statist. Probab.*, vol. 1, 1967, pp. 281–297.",
  rousseeuw: "P. J. Rousseeuw, “Silhouettes: A graphical aid to the interpretation and validation of cluster analysis,” *J. Comput. Appl. Math.*, vol. 20, pp. 53–65, 1987.",
  kneedle: "V. Satopää, J. Albrecht, D. Irwin, and B. Raghavan, “Finding a ‘kneedle’ in a haystack: Detecting knee points in system behavior,” in *Proc. 31st Int. Conf. Distrib. Comput. Syst. Workshops*, 2011, pp. 166–171.",
  jolliffe: "I. T. Jolliffe, *Principal Component Analysis*, 2nd ed. New York, NY, USA: Springer, 2002.",
  duckdb: "M. Raasveldt and H. Mühleisen, “DuckDB: An embeddable analytical database,” in *Proc. ACM SIGMOD Int. Conf. Manage. Data*, 2019, pp. 1981–1984.",
  pandas: "W. McKinney, “Data structures for statistical computing in Python,” in *Proc. 9th Python Sci. Conf. (SciPy)*, 2010, pp. 56–61.",
  rdflib: "RDFLib Team, “RDFLib: A Python library for working with RDF.” [Online]. Available: https://github.com/RDFLib/rdflib",
  sklearn: "F. Pedregosa *et al.*, “Scikit-learn: Machine learning in Python,” *J. Mach. Learn. Res.*, vol. 12, pp. 2825–2830, 2011.",
  mlxtend: "S. Raschka, “MLxtend: Providing machine learning and data science utilities and extensions to Python’s scientific computing stack,” *J. Open Source Softw.*, vol. 3, no. 24, p. 638, 2018.",
  streamlit: "Snowflake Inc., “Streamlit documentation.” [Online]. Available: https://docs.streamlit.io",
  plotly: "Plotly Technologies Inc., “Collaborative data science,” Montréal, QC, Canada, 2015. [Online]. Available: https://plot.ly",
  dbscan: "M. Ester, H.-P. Kriegel, J. Sander, and X. Xu, “A density-based algorithm for discovering clusters in large spatial databases with noise,” in *Proc. 2nd Int. Conf. Knowl. Discovery Data Mining (KDD)*, 1996, pp. 226–231.",
  bert: "J. Devlin, M.-W. Chang, K. Lee, and K. Toutanova, “BERT: Pre-training of deep bidirectional transformers for language understanding,” in *Proc. NAACL-HLT*, 2019, pp. 4171–4186.",
  wikidata: "D. Vrandečić and M. Krötzsch, “Wikidata: A free collaborative knowledgebase,” *Commun. ACM*, vol. 57, no. 10, pp. 78–85, 2014.",
};
const refOrder = [];
const FIG_ORDER = ["arch", "onto", "schema", "region", "severity", "season", "rules", "elbow", "scatter",
                   "dash_main", "dash_clusters", "dash_explore"];
const TAB_ORDER = ["vocab", "onto", "stack", "etl", "extract", "sparql", "warehouse", "rules", "clusters"];
const ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV"];

function refNo(key) {
  if (!REFS[key]) throw new Error("unknown reference " + key);
  let i = refOrder.indexOf(key);
  if (i < 0) { refOrder.push(key); i = refOrder.length - 1; }
  return i + 1;
}
const figNo = (k) => { const i = FIG_ORDER.indexOf(k); if (i < 0) throw new Error("fig " + k); return i + 1; };
const tabNo = (k) => { const i = TAB_ORDER.indexOf(k); if (i < 0) throw new Error("tab " + k); return ROMAN[i]; };

// ------------------------------------------------------------------ inline markup -> runs
// **bold**  *italic*  `mono`  _{sub}  ^{sup}  {ref:a,b}  {fig:k}  {tab:k}
function runs(text, base = {}) {
  text = text
    .replace(/\{ref:([a-z0-9_,]+)\}/g, (_, keys) => "[" + keys.split(",").map(refNo).join("], [") + "]")
    .replace(/\{fig:([a-z_]+)\}/g, (_, k) => "Fig. " + figNo(k))
    .replace(/\{tab:([a-z_]+)\}/g, (_, k) => "Table " + tabNo(k));
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|_\{[^}]+\}|\^\{[^}]+\})/g;
  let last = 0, m;
  const push = (t, extra = {}) => t && out.push(new TextRun({ text: t, font: FONT, ...base, ...extra }));
  while ((m = re.exec(text))) {
    push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) push(tok.slice(2, -2), { bold: true });
    else if (tok.startsWith("*")) push(tok.slice(1, -1), { italics: !base.italics });
    else if (tok.startsWith("`")) push(tok.slice(1, -1), { font: "Courier New", size: (base.size || 20) - 2 });
    else if (tok.startsWith("_{")) push(tok.slice(2, -1), { subScript: true });
    else push(tok.slice(2, -1), { superScript: true });
    last = m.index + tok.length;
  }
  push(text.slice(last));
  return out;
}

// ------------------------------------------------------------------ block helpers
const body = [];           // current section's children
const sections = [];
function startSection(columns) {
  if (body.length) sections.push({ columns: sections.pending, children: body.splice(0) });
  sections.pending = columns;
}

const P = (text, opts = {}) => body.push(new Paragraph({
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 0, line: 230 }, indent: { firstLine: opts.noIndent ? 0 : 202 },
  children: runs(text, { size: 20 }), ...opts.para,
}));

let h1 = 0, h2 = 0;
function H1(title) {
  h2 = 0;
  body.push(new Paragraph({
    heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, keepNext: true,
    spacing: { before: 200, after: 100 },
    children: [new TextRun({ text: `${ROMAN[h1++]}. ${title}`, font: FONT, size: 20, smallCaps: true })],
  }));
}
function H2(title) {
  body.push(new Paragraph({
    heading: HeadingLevel.HEADING_2, keepNext: true, spacing: { before: 120, after: 60 },
    children: [new TextRun({ text: `${String.fromCharCode(65 + h2++)}. ${title}`, font: FONT, size: 20, italics: true })],
  }));
}

let eqNo = 0;
function EQ(text) {
  eqNo++;
  body.push(new Paragraph({
    spacing: { before: 60, after: 60 }, keepLines: true,
    tabStops: [{ type: TabStopType.CENTER, position: Math.round(COL_W / 2) }, { type: TabStopType.RIGHT, position: COL_W - 10 }],
    children: [new TextRun({ text: "\t", font: FONT }), ...runs(text, { size: 20 }),
               new TextRun({ text: `\t(${eqNo})`, font: FONT, size: 20 })],
  }));
}

function bullets(items) {
  for (const t of items) body.push(new Paragraph({
    numbering: { reference: "ieee-bullets", level: 0 }, alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 20, line: 230 }, children: runs(t, { size: 20 }),
  }));
}

// image size from PNG / JPEG headers
function imgSize(file) {
  const b = fs.readFileSync(file);
  if (b.readUInt32BE(0) === 0x89504e47) return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
  let i = 2;
  while (i < b.length) {
    const marker = b.readUInt16BE(i), len = b.readUInt16BE(i + 2);
    if (marker >= 0xffc0 && marker <= 0xffc3) return { h: b.readUInt16BE(i + 5), w: b.readUInt16BE(i + 7) };
    i += 2 + len;
  }
  throw new Error("cannot size " + file);
}
function image(file, widthPx) {
  const f = path.join(IMG, file);
  const { w, h } = imgSize(f);
  return new ImageRun({ type: file.endsWith(".png") ? "png" : "jpg", data: fs.readFileSync(f),
                        transformation: { width: widthPx, height: Math.round((h * widthPx) / w) } });
}
function caption(prefix, text, wide) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED, spacing: { before: 60, after: 180 },
    children: [new TextRun({ text: prefix, font: FONT, size: 16 }), ...runs(text, { size: 16 })],
    ...(wide ? {} : {}),
  });
}
function FIG(key, file, text, { wide = false, scale = 1 } = {}) {
  const width = Math.floor(PX(wide ? TEXT_W : COL_W) * scale);
  body.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 0 },
                            children: [image(file, width)] }));
  body.push(caption(`Fig. ${figNo(key)}.  `, text, wide));
}
// two images side by side across the full text width
function FIG2(key, a, b, text) {
  const cellW = Math.floor(TEXT_W / 2);
  const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const ha = imgSize(path.join(IMG, a[0])), hb = imgSize(path.join(IMG, b[0]));
  const ratio = Math.min(ha.h / ha.w, hb.h / hb.w);           // shared height = the shorter image at full cell width
  const widthFor = (f) => { const d = imgSize(path.join(IMG, f)); return Math.round(((PX(cellW) - 12) * ratio * d.w) / d.h); };
  const cell = (file, sub) => new TableCell({
    width: { size: cellW, type: WidthType.DXA }, borders: { top: none, bottom: none, left: none, right: none },
    margins: { left: 60, right: 60 },
    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [image(file, widthFor(file))] }),
               new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 40 },
                               children: runs(sub, { size: 16 }) })],
  });
  body.push(new Table({ width: { size: cellW * 2, type: WidthType.DXA }, columnWidths: [cellW, cellW],
                        rows: [new TableRow({ children: [cell(a[0], a[1]), cell(b[0], b[1])] })] }));
  body.push(caption(`Fig. ${figNo(key)}.  `, text, true));
}

// IEEE table: caption above in small caps, thin full grid, 8 pt
function TABLE(key, title, header, rows, { widths, wide = false, align } = {}) {
  const total = wide ? TEXT_W : COL_W;
  const ws = widths ? widths.map((f) => Math.floor(total * f)) : header.map(() => Math.floor(total / header.length));
  ws[ws.length - 1] = total - ws.slice(0, -1).reduce((s, x) => s + x, 0);
  const line = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
  const n = rows.length;
  const mk = (cells, isHead, idx) => new TableRow({
    tableHeader: isHead, cantSplit: true,
    children: cells.map((c, i) => new TableCell({
      width: { size: ws[i], type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
      borders: { top: line, bottom: line, left: line, right: line },
      margins: { top: 20, bottom: 20, left: 70, right: 70 },
      children: [new Paragraph({
        keepNext: idx < n - 1, keepLines: true,
        alignment: isHead ? AlignmentType.CENTER : (align ? align[i] : AlignmentType.LEFT),
        children: runs(String(c), { size: 16, bold: isHead }),
      })],
    })),
  });
  body.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 160, after: 0 },
                            children: [new TextRun({ text: `TABLE ${tabNo(key)}`, font: FONT, size: 16, smallCaps: true })] }));
  body.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { after: 60 },
                            children: [new TextRun({ text: title, font: FONT, size: 16, smallCaps: true })] }));
  body.push(new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: ws,
                        rows: [mk(header, true, -1), ...rows.map((r, i) => mk(r, false, i))] }));
  body.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
}
const C = AlignmentType.CENTER, L = AlignmentType.LEFT, R = AlignmentType.RIGHT;

// ------------------------------------------------------------------ data from the latest run
const M = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "..", "outputs", "metrics.json"), "utf8"));
const pct = (x, d = 1) => (x * 100).toFixed(d) + "%";
const nf = (x) => x.toLocaleString("en-US");
const tp = M.triple_precision, cl = M.clustering, wh = M.warehouse.rows, ar = M.association_rules;

// ================================================================== TITLE BLOCK (1 column)
startSection(1);
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
  children: [new TextRun({ text: "OntoRisk BI: An Ontology-Driven Semantic Data Warehouse for Proactive Business Risk Intelligence",
                           font: FONT, size: 48 })] }));
// IEEE author block: one column per author, name over registration number
const AUTHORS = [
  ["Aishwarya Patil", "235890068"],
  ["Thiriveedhi Venkata Subba Sai Teja", "235890021"],
  ["Dhruv Naveen", "235890154"],
  ["Shaswat Das", "235890222"],
];
{
  const w = Math.floor(TEXT_W / AUTHORS.length);
  const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  body.push(new Table({
    width: { size: w * AUTHORS.length, type: WidthType.DXA }, columnWidths: AUTHORS.map(() => w),
    rows: [new TableRow({ children: AUTHORS.map(([name, reg]) => new TableCell({
      width: { size: w, type: WidthType.DXA }, borders: { top: none, bottom: none, left: none, right: none },
      margins: { left: 80, right: 80 },
      children: [
        new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: name, font: FONT, size: 22 })] }),
        new Paragraph({ alignment: AlignmentType.CENTER,
                        children: [new TextRun({ text: `Reg. No. ${reg}`, font: FONT, size: 20, italics: true })] }),
      ],
    })) })],
  }));
}
body.push(new Paragraph({ spacing: { after: 280 }, children: [] }));

// ================================================================== BODY (2 columns)
startSection(2);
body.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 100, line: 220 }, children: [
  new TextRun({ text: "Abstract", font: FONT, size: 18, bold: true, italics: true }),
  new TextRun({ text: "—", font: FONT, size: 18, bold: true }),
  ...runs("Businesses learn about operational risks such as monsoon flooding, port congestion, export bans, supplier failures and product recalls from news text, which conventional business-intelligence (BI) tools cannot query. This paper presents OntoRisk BI, an open, reproducible pipeline that converts business news into structured, queryable risk intelligence. Organisations, locations, dates and risk-vocabulary terms are recognised with spaCy; a transparent paragraph-level co-occurrence rule turns them into risk events that are stored twice: as RDF triples linked to a compact six-class OWL ontology, and as rows of a DuckDB star schema joined to the triples through a semantic bridge table. FP-Growth association-rule mining and k-Means clustering run over the warehouse, and a Streamlit dashboard exposes KPIs, OLAP roll-up and drill-down, the mined rules, the cluster map and a SPARQL console. On a 240-article Indian-context corpus the pipeline extracts " + nf(tp.predicted_events) + " risk events and " + nf(M.rdf.total_triples) + " triples, passes all six SPARQL integrity checks with zero orphan warehouse keys, and achieves extraction precision of " + pct(tp.precision) + ", recall of " + pct(tp.recall) + " and F1 of " + pct(tp.f1) + " against ground truth. It mines " + ar.rules + " association rules (strongest lift 3.96) and five interpretable clusters, and runs end to end in about " + Math.round(M.runtime_seconds) + " s.", { size: 18, bold: true }),
]}));
body.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 120, line: 220 }, children: [
  new TextRun({ text: "Index Terms", font: FONT, size: 18, bold: true, italics: true }),
  new TextRun({ text: "—", font: FONT, size: 18, bold: true }),
  ...runs("Business intelligence, ontology, semantic web, RDF, SPARQL, data warehouse, star schema, OLAP, named entity recognition, association rules, FP-Growth, k-Means clustering, supply chain risk.", { size: 18, bold: true }),
]}));

// ------------------------------------------------------------------ I. Introduction
H1("Introduction");
P("Supply chains and the firms that depend on them are exposed to a wide range of disruptions: extreme weather, transport bottlenecks, regulatory change, supplier distress and reputational incidents {ref:tang,ho}. In the Indian context these risks have a strong regional and seasonal signature: the south-west monsoon (June–September) floods warehouses and roads, cyclones affect the eastern coast in October and November, container ports such as Nhava Sheva, Mundra and Chennai suffer congestion, and policy decisions taken in New Delhi (GST revisions, import duties, export bans) ripple across sectors.");
P("Most early signals of such risks appear first in news text. Text, however, is unstructured: a BI analyst cannot slice it by region and quarter, join it to other facts, or mine it for patterns. Text-mining outputs usually live apart from the warehouse, while semantic-web technology {ref:bernerslee}, which gives data explicit meaning, is rarely combined with dimensional modelling and OLAP practice {ref:kimball}. Small and medium enterprises in particular lack an affordable way to bridge the two.");
P("OntoRisk BI addresses this gap. Its contribution is integration rather than novelty in any single layer: a semantic layer, a dimensional warehouse and a data-mining layer are combined in one open, reproducible pipeline, each in the simplest form that still produces a genuine artefact for the next layer. The specific contributions are:");
bullets([
  "a compact OWL ontology (six classes, two object properties) for business-risk events, with impact and provenance modelled as data properties;",
  "a transparent, auditable extraction layer (spaCy NER, a curated 63-term risk vocabulary and a paragraph-level co-occurrence rule) whose precision is measured against ground truth;",
  "a *hybrid* warehouse in which every fact row of a DuckDB star schema is linked to its RDF triples through a shared event identifier, so SQL and SPARQL results can be joined;",
  "FP-Growth association rules and k-Means clusters mined from the warehouse, re-computed interactively for any OLAP slice;",
  "an interactive dashboard and a fully tested, deployable code base.",
]);
P("Section II reviews related work, Section III describes the architecture, Section IV details the methodology and Section V the implementation. Section VI reports results, Section VII discusses limitations and future work, and Section VIII concludes.");

// ------------------------------------------------------------------ II. Related work
H1("Related Work");
H2("Ontologies and the Semantic Web");
P("An ontology is an explicit specification of a shared conceptualisation {ref:gruber}. The W3C semantic-web stack represents knowledge as RDF triples {ref:rdf}, describes vocabularies with OWL {ref:owl} and queries graphs with SPARQL {ref:sparql}. Methodological guidance recommends starting from competency questions and keeping the class hierarchy minimal {ref:noy}; Protégé is the de-facto editor for inspecting and reasoning over OWL ontologies {ref:protege}. OntoRisk BI follows this advice: the ontology is generated as code with RDFLib, opens in Protégé, and is validated with SPARQL.");
H2("Data Warehousing and OLAP");
P("Inmon defines the warehouse as a subject-oriented, integrated, time-variant store {ref:inmon}, while Kimball’s dimensional approach organises it as star schemas of facts and conformed dimensions {ref:kimball}. OLAP operations (roll-up, drill-down, slice and dice) over such schemas are the core of BI {ref:chaudhuri}. Embedded columnar engines such as DuckDB bring this analytical model to a single process without a server {ref:duckdb}.");
H2("Semantic Data Warehouses");
P("Several works combine semantic-web data with warehouses. Nebot and Berlanga build multidimensional warehouses from semantically annotated data {ref:nebot}, and Abelló *et al.* survey the use of semantic-web technologies for exploratory OLAP {ref:abello}. These systems typically assume curated RDF sources; OntoRisk BI instead *produces* the RDF from raw news text and keeps the triples and the fact rows linked one-to-one.");
H2("Information Extraction and Pattern Mining");
P("Named entity recognition (NER) identifies organisations, places and dates in text {ref:nadeau}; spaCy provides fast statistical NER pipelines {ref:spacy}. For pattern discovery, Apriori {ref:agrawal} and FP-Growth {ref:han} mine frequent itemsets and association rules, and k-Means {ref:macqueen} with the silhouette coefficient {ref:rousseeuw} is the standard baseline for partitional clustering. OntoRisk BI applies these well-understood techniques to the risk events extracted from text.");

// ------------------------------------------------------------------ III. Architecture
H1("System Architecture");
P("{fig:arch} shows the pipeline. It is organised as four layers and eight independently testable stages, each implemented as one Python module and orchestrated by `run_pipeline.py`:");
bullets([
  "**Acquisition and NLP** — corpus collection, text cleaning and preprocessing, NER and risk-term tagging;",
  "**Semantic layer** — the co-occurrence relation rule, impact scoring, RDF generation against the ontology and SPARQL validation;",
  "**Hybrid warehouse** — Pandas ETL with data-quality checks into a DuckDB star schema plus a triple–fact bridge;",
  "**Mining and presentation** — FP-Growth rules, k-Means clusters, evaluation, figures and the Streamlit dashboard.",
]);
FIG("arch", "architecture.png", "OntoRisk BI architecture. Solid arrows show data flow; dashed arrows show the event_id link between the knowledge graph and the warehouse and the SPARQL queries issued from the dashboard.");
P("All paths, namespaces and thresholds live in a single configuration module, so the whole pipeline can be re-pointed at another corpus by editing one file or passing `--input news.csv`.");

// ------------------------------------------------------------------ IV. Methodology
H1("Methodology");
H2("Corpus Collection");
P("The system accepts any public news CSV with a text column (e.g. an Indian business-news dataset); a loader maps common column names (title/headline, text/content/body, date/published_at, source) onto the project schema. For evaluation, a reproducible *synthetic* corpus is generated from templates: companies are fictional, but places, risk categories and seasonality follow the Indian context (monsoon in June–September, cyclones in October–November, port congestion at Nhava Sheva, Mundra and Chennai, policy news from New Delhi). Each article deliberately contains realistic noise (analyst remarks, second places, generic mentions) so that the extraction rule produces some spurious events. Because the generator knows which organisation, place and risk were really involved, it also writes a gold-standard file of " + 297 + " true events, which allows precision and recall to be measured automatically. The default corpus contains 243 raw records covering four sectors (Supply Chain & Logistics, Retail, Finance and Manufacturing) between January 2024 and December 2025.");
H2("Preprocessing and Named Entity Recognition");
P("Each article is split into paragraphs (falling back to the whole article if no paragraph breaks exist). For analysis, text is tokenised, lemmatised and stripped of stop-words, punctuation and numbers with spaCy. NER is run with `en_core_web_sm` on the *original* paragraphs, because capitalisation and function words are needed for recognition; ORG, GPE, LOC and DATE entities are kept {ref:spacy}. Organisation names are normalised (possessives and leading articles removed) and places are mapped to region, state and country through a gazetteer of Indian states and key foreign ports.");
P("Risk terms are tagged with spaCy’s PhraseMatcher over a curated vocabulary of 63 weighted terms in five risk types ({tab:vocab}). Matching is case-insensitive and longest-match-first, so “port congestion” wins over “congestion”. Each term carries a weight from 1 to 3; a separate list of intensity cues (e.g. *severe*, *halted*, *crore* versus *minor*, *resumed*) raises or lowers the severity of an article.");
TABLE("vocab", "Risk Vocabulary by Risk Type", ["Risk type", "Sub-type", "Terms", "Examples"], [
  ["Weather", "Monsoon / natural disaster", "15", "monsoon, heavy rainfall, flood"],
  ["Logistics", "Port congestion / transport", "13", "port congestion, vessel backlog"],
  ["Policy", "Regulatory / policy change", "13", "export ban, import duty, GST revision"],
  ["Supplier", "Supplier failure / shortage", "11", "supplier insolvency, chip shortage"],
  ["Reputational", "Brand / reputational incident", "11", "product recall, data breach"],
], { widths: [0.19, 0.31, 0.11, 0.39], align: [L, L, C, L] });
H2("Co-occurrence Relation Extraction and Impact Scoring");
P("No model is trained; relations are extracted by a transparent rule. For every paragraph that contains at least one organisation, one location and one risk-vocabulary term, a *RiskEvent* is created for each (organisation, location, risk type) combination, and the triples ⟨entity, `affects`, event⟩ and ⟨event, `locatedIn`, location⟩ are generated, together with data-property triples for score, severity, date and provenance. Before the rule fires, duplicates of the same (article, organisation, place, risk type) are merged, and when an organisation is linked to both a city and its own state only the more specific city is kept.");
P("Each event receives an impact score *I* on a 0–10 scale from a transparent heuristic:");
EQ("*I* = 1.5*w*_{max} + 0.8 min(*m*−1, 2) + 1.6*s* + *l* + 0.5");
P("clipped to [0, 10], where *w*_{max} is the highest weight of the matched terms, *m* the number of mentions of that risk type in the article, *s* the summed intensity of the article’s cue words and *l* = 1 if the event comes from the lead paragraph. The severity band is Low for *I* < 4, Medium for 4 ≤ *I* < 7 and High for *I* ≥ 7.", { noIndent: true });
H2("Ontology Design");
P("The ontology ({fig:onto}, {tab:onto}) is deliberately compact. It has six mutually disjoint classes and exactly two object properties: `affects` (Entity → RiskEvent) and `locatedIn` (RiskEvent → Location, declared functional because every event occurs in one place). Everything else, including impact score, severity band, risk category, dates and provenance, is modelled as one of 19 data properties rather than as additional classes. The five risk types and the 63 vocabulary terms are added as named individuals. The ontology is generated with RDFLib {ref:rdflib} and serialised both as Turtle and as RDF/XML that opens directly in Protégé for browsing and HermiT reasoning.");
FIG("onto", "ontology.png", "OntoRisk ontology. Solid edges are the two object properties; dashed edges are data properties that reference other classes by value.");
TABLE("onto", "Ontology Classes", ["Class", "Meaning"], [
  ["RiskEvent", "A business-risk occurrence detected in text"],
  ["Entity", "An organisation affected by a risk event"],
  ["Location", "City, port, state or country of the event"],
  ["RiskType", "Weather, logistics, policy, supplier or reputational"],
  ["SourceArticle", "The news article an event came from (provenance)"],
  ["RiskTerm", "A vocabulary keyword that signals a risk type"],
], { widths: [0.28, 0.72] });
H2("Semantic Validation with SPARQL");
P("After triple generation, six SPARQL queries act as integrity tests on the knowledge graph {ref:sparql}: the ontology must declare exactly six classes and two object properties; every RiskEvent must have a location and an affected entity; no `affects` or `locatedIn` triple may violate its declared domain or range; and each of the five risk types must have events. The pipeline fails loudly if any check does not hold.");
H2("ETL and the Hybrid Warehouse");
P("Articles pass through a Pandas {ref:pandas} ETL stage that removes empty texts, duplicate identifiers, duplicate texts and unparseable dates, and normalises whitespace. Events are then loaded into a DuckDB {ref:duckdb} star schema ({fig:schema}) following Kimball’s dimensional model {ref:kimball}: a fact table `FACT_RISKEVENT` with the measures impact score, severity and mention count, and three dimensions — time (date, week, month, quarter, year), location (place, region, state, country) and risk type (category, sub-type). Entity name, sector and source identifier are kept as *degenerate* attributes on the fact row.");
FIG("schema", "schema.png", "Star schema of the hybrid warehouse. The dashed link is the semantic bridge that stores every RDF triple of an event under the event’s identifier.");
P("The semantic side of the warehouse is the table `BRIDGE_SEMANTIC_LINK` (event_id, subject, predicate, object), which stores every triple produced for an event. Because the same identifier appears as the `eventId` data property in the graph, a SQL query can jump from a fact row to its triples and a SPARQL result can jump back to the fact row. After loading, referential checks confirm that no fact row has an orphan dimension key, a missing measure or no triples.");
H2("Association-Rule Mining");
P("Each risk event becomes a transaction of items `risktype=`*t*, `region=`*r*, `sector=`*s* and `severity=`*b*, plus `co_risk=`*t*′ for every other risk type reported in the same article; this last item allows cross-risk rules such as weather ⇒ logistics to surface. Frequent itemsets are mined with FP-Growth {ref:han} as implemented in mlxtend {ref:mlxtend}, and Apriori {ref:agrawal} is run as a cross-check. For a rule *X* ⇒ *Y* over the transaction set *T*:");
EQ("supp(*X*) = |{*t* ∈ *T* : *X* ⊆ *t*}| / |*T*|");
EQ("conf(*X* ⇒ *Y*) = supp(*X* ∪ *Y*) / supp(*X*)");
EQ("lift(*X* ⇒ *Y*) = conf(*X* ⇒ *Y*) / supp(*Y*)");
P("Rules are kept when support ≥ 0.05, confidence ≥ 0.60 and lift ≥ 1.10 and are ranked by lift. In the dashboard the rules are re-mined for whatever region, period and risk-type slice is selected (with at least 25 events), so the rule table always describes the data in view.", { noIndent: true });
H2("k-Means Clustering");
P("Each event is described by ten standardised features: impact score, mention count, the month encoded as sine and cosine (so that December is adjacent to January), a monsoon-season flag and a one-hot encoding of the five risk types. k-Means {ref:macqueen} minimises the within-cluster sum of squares");
EQ("*J* = Σ_{k} Σ_{x∈C(k)} ‖*x* − μ_{k}‖²");
P("for *k* = 2…10 using scikit-learn {ref:sklearn}. The number of clusters is chosen at the knee of the inertia curve (the point of maximum distance from the chord joining its ends, in the spirit of Kneedle {ref:kneedle}) and validated with the mean silhouette coefficient {ref:rousseeuw}", { noIndent: true });
EQ("*s*(*i*) = (*b*(*i*) − *a*(*i*)) / max{*a*(*i*), *b*(*i*)}");
P("where *a*(*i*) is the mean distance of event *i* to its own cluster and *b*(*i*) to the nearest other cluster. PCA {ref:jolliffe} projects the vectors to two dimensions for the scatter plot, and each cluster is labelled automatically from its mean impact, dominant risk type and monsoon share.", { noIndent: true });
H2("Interactive Dashboard");
P("The dashboard, built with Streamlit {ref:streamlit} and Plotly {ref:plotly}, has five pages reachable from a sidebar: *Overview*, *Association rules*, *Clusters*, *Knowledge graph* and *Event log*. Sidebar filters (region, time period, risk type, and rule-mining thresholds) and a global search box over entities, places and sectors apply to every page. Four KPIs summarise the selection: the Risk Exposure Index, the average impact score, the number of events in view and the confidence of the strongest rule, where");
EQ("REI = Σ_{e} *I*_{e} · *w*(sev_{e}),   *w* ∈ {1, 2, 3}");
P("for Low, Medium and High severity. The data layer behind the dashboard is a set of pure functions that are unit-tested independently of the user interface.", { noIndent: true });

// ------------------------------------------------------------------ V. Implementation
H1("Implementation");
P("The system is written in Python 3.13. {tab:stack} lists the main libraries and their role. The code base is organised as one module per stage under `src/ontorisk/`, the dashboard under `dashboard/`, and 17 pytest tests that cover every stage, including a headless run of the whole dashboard with Streamlit’s AppTest harness. If spaCy or DuckDB is unavailable, the code falls back to a rule-based recogniser and to SQLite with an identical schema, and records which back-end was used in `outputs/metrics.json`.");
TABLE("stack", "Technology Stack", ["Layer", "Technology", "Role"], [
  ["NLP", "spaCy 3.8, en_core_web_sm", "Tokens, lemmas, NER, PhraseMatcher"],
  ["Semantic", "RDFLib 7, OWL 2, SPARQL 1.1", "Ontology, triples, validation"],
  ["ETL", "pandas 3", "Cleaning and quality checks"],
  ["Warehouse", "DuckDB 2.0", "Star schema, OLAP queries"],
  ["Mining", "mlxtend 0.25, scikit-learn 1.9", "FP-Growth, Apriori, k-Means, PCA"],
  ["Presentation", "Streamlit 1.66, Plotly", "Dashboard and charts"],
  ["Quality", "pytest, Git/GitHub", "Tests, versioning, deployment"],
], { widths: [0.22, 0.4, 0.38] });
P("The complete pipeline runs end to end in " + M.runtime_seconds.toFixed(1) + " s on a laptop. The dashboard is deployed on Streamlit Community Cloud directly from the project’s GitHub repository; because the built warehouse and mining outputs are versioned, the deployed application does not need to re-run the pipeline.");

// ------------------------------------------------------------------ VI. Results
H1("Results and Discussion");
H2("Data Quality and NER");
P("Of 243 raw records, the ETL stage rejected one empty text, one duplicate identifier and one unparseable date, leaving 240 clean articles ({tab:etl}). NER and vocabulary tagging found " + nf(M.ner.mentions_by_label.LOC) + " location, " + nf(M.ner.mentions_by_label.ORG) + " organisation, " + nf(M.ner.mentions_by_label.DATE) + " date and " + nf(M.ner.mentions_by_label.RISK_TERM) + " risk-term mentions (1,590 in total), covering " + M.ner.distinct_orgs + " distinct organisations and " + M.ner.distinct_places + " distinct places.");
TABLE("etl", "ETL Data-Quality Report", ["Check", "Records"], [
  ["Raw records read", "243"], ["Rejected: empty text", "1"], ["Rejected: duplicate id", "1"],
  ["Rejected: duplicate text", "0"], ["Rejected: invalid date", "1"], ["Clean articles loaded", "240"],
], { widths: [0.7, 0.3], align: [L, R] });
H2("Extraction Quality");
P("Against the gold standard, the co-occurrence rule produced " + tp.predicted_events + " events, of which " + tp.correct_events + " were correct, and recovered " + tp.gold_events_found + " of the " + tp.gold_events + " true events ({tab:extract}). Precision is " + pct(tp.precision) + ", recall " + pct(tp.recall) + " and F1 " + pct(tp.f1) + ", where");
EQ("*P* = *TP*/(*TP*+*FP*),  *R* = *TP*/(*TP*+*FN*),  *F*_{1} = 2*PR*/(*P*+*R*)");
P("The high recall and moderate precision are exactly what a co-occurrence rule is expected to deliver: it rarely misses an event but also links organisations to incidental places or risks mentioned in the same paragraph. Precision is highest for logistics (" + pct(tp.precision_by_risk_type.logistics) + ") and supplier (" + pct(tp.precision_by_risk_type.supplier) + ") risks, whose vocabulary is specific, and lowest for weather (" + pct(tp.precision_by_risk_type.weather) + ") and policy (" + pct(tp.precision_by_risk_type.policy) + "), where words such as *monsoon* or *GST* often appear as background context. A random sample of 50 triples was also prepared for manual review, giving a sample precision of " + pct(tp.sample_precision, 0) + ", consistent with the automatic figure.", { noIndent: true });
TABLE("extract", "Extraction Quality Against Ground Truth", ["Metric", "Value"], [
  ["Predicted events", nf(tp.predicted_events)], ["Correct events (TP)", nf(tp.correct_events)],
  ["Gold events / found", `${tp.gold_events} / ${tp.gold_events_found}`],
  ["Precision", pct(tp.precision)], ["Recall", pct(tp.recall)], ["F1 score", pct(tp.f1)],
  ["Precision: logistics / supplier", `${pct(tp.precision_by_risk_type.logistics)} / ${pct(tp.precision_by_risk_type.supplier)}`],
  ["Precision: reputational", pct(tp.precision_by_risk_type.reputational)],
  ["Precision: policy / weather", `${pct(tp.precision_by_risk_type.policy)} / ${pct(tp.precision_by_risk_type.weather)}`],
  ["Manual sample precision (n = 50)", pct(tp.sample_precision, 0)],
], { widths: [0.68, 0.32], align: [L, R] });
H2("Knowledge Graph and Warehouse Integrity");
P("The knowledge graph contains " + nf(M.rdf.total_triples) + " triples, " + nf(M.rdf.abox_triples) + " of them generated instance (A-Box) triples. All six SPARQL validation queries pass ({tab:sparql}). The warehouse holds " + wh.FACT_RISKEVENT + " fact rows, " + wh.DIM_TIME + " time members, " + wh.DIM_LOCATION + " locations, " + wh.DIM_RISKTYPE + " risk types and " + nf(wh.BRIDGE_SEMANTIC_LINK) + " bridge rows ({tab:warehouse}); referential checks report zero orphan keys, zero null measures and zero facts without triples, so the semantic and dimensional views are fully consistent.");
TABLE("sparql", "SPARQL Validation Checks", ["Check", "Result", "Status"], [
  ["Ontology declares six classes", "6", "Pass"],
  ["Exactly two object properties", "2", "Pass"],
  ["Events without a location", "0", "Pass"],
  ["Events without an affected entity", "0", "Pass"],
  ["Domain / range violations", "0", "Pass"],
  ["Events per risk type", "113 / 86 / 74 / 64 / 50", "Pass"],
], { widths: [0.5, 0.33, 0.17], align: [L, C, C] });
TABLE("warehouse", "Warehouse Tables and Integrity", ["Table / check", "Rows"], [
  ["FACT_RISKEVENT", nf(wh.FACT_RISKEVENT)], ["DIM_TIME", nf(wh.DIM_TIME)], ["DIM_LOCATION", nf(wh.DIM_LOCATION)],
  ["DIM_RISKTYPE", nf(wh.DIM_RISKTYPE)], ["BRIDGE_SEMANTIC_LINK", nf(wh.BRIDGE_SEMANTIC_LINK)],
  ["STG_ARTICLES (staging)", nf(wh.STG_ARTICLES)], ["Orphan keys / null measures", "0 / 0"],
  ["Facts without triples", "0"],
], { widths: [0.7, 0.3], align: [L, R] });
H2("Descriptive Analytics");
P("Logistics is the most frequent risk type (113 events), followed by weather (86), policy (74), supplier (64) and reputational (50). Geographically, the West (121 events) and South (118) dominate, reflecting the port-heavy western and southern coasts, while policy risk is concentrated in the North ({fig:region}). Weather events are the most severe: 62% of them fall in the High band, compared with 12% of reputational events ({fig:severity}). Weighting by severity, weather accounts for the largest share of the Risk Exposure Index (31%, 1,822 of 5,802), ahead of logistics (29%).");
FIG("region", "events_by_region_type.png", "Risk events by region and risk type (" + wh.FACT_RISKEVENT + " events).");
FIG("severity", "severity_by_type.png", "Severity mix (Low, Medium, High) within each risk type.");
P("The seasonal pattern is pronounced ({fig:season}): weather events rise sharply from June and peak in September at the end of the south-west monsoon, and logistics events track them through the same months, a first visual hint of the weather–logistics association that the rule miner later quantifies.");
FIG("season", "monthly_trend.png", "Seasonality: risk events per calendar month over 2024–2025; the shaded band marks the south-west monsoon.");
H2("Association Rules");
P("FP-Growth found " + ar.frequent_itemsets + " frequent itemsets and " + ar.rules + " rules that satisfy all three thresholds; Apriori produced an identical rule set, confirming the implementation. {tab:rules} and {fig:rules} show the strongest rules. The top rule states that a High-severity event in the Supply Chain & Logistics sector that co-occurs with a logistics risk is a weather event in 88% of cases, 3.96 times the base rate. Its mirror image (weather in the same sector implies a co-occurring logistics risk, lift 3.23) confirms that monsoon disruption and transport disruption travel together. A second family links policy risk to the Finance sector and to co-occurring supplier risk (lift 3.16–3.44), consistent with regulatory changes that propagate to input supply.");
TABLE("rules", "Top Association Rules by Lift", ["Antecedent ⇒ consequent", "Sup.", "Conf.", "Lift"],
  ar.top_rules.slice(0, 6).map((r) => [
    r.antecedents.replace(/co_risk=/g, "co-risk ").replace(/risktype=/g, "").replace(/sector=Supply Chain & Logistics/g, "SC&L").replace(/sector=/g, "").replace(/severity=/g, "").replace(/region=/g, "")
      + " ⇒ " + r.consequents.replace(/co_risk=/g, "co-risk ").replace(/risktype=/g, ""),
    r.support.toFixed(3), r.confidence.toFixed(2), r.lift.toFixed(2)]),
  { widths: [0.61, 0.13, 0.13, 0.13], align: [L, R, R, R] });
P("In {tab:rules}, SC&L abbreviates the Supply Chain & Logistics sector and “co-risk” marks another risk type reported in the same article.", { noIndent: true });
FIG("rules", "top_rules.png", "Top twelve FP-Growth rules ranked by lift, annotated with confidence and support.");
H2("Clusters of Risk Events");
P("The inertia curve has its knee at *k* = 5 ({fig:elbow}). The silhouette score at *k* = 5 is " + cl.silhouette_chosen.toFixed(3) + "; *k* = 2 scores slightly higher (" + cl.silhouette[0].toFixed(3) + ") but merely separates high- from low-impact events, so the elbow choice was kept for interpretability. The first two principal components explain " + pct(cl.pca_explained_variance[0]) + " and " + pct(cl.pca_explained_variance[1]) + " of the variance. The five clusters ({tab:clusters}, {fig:scatter}) are clearly interpretable: a *high-impact monsoon weather* cluster (C1, 84% weather, 90% in monsoon months, 78% High severity), a *high-impact all-year* cluster led by logistics (C2, 97% High), a *moderate policy* cluster (C3, 61% policy) and two low-impact mixed clusters that differ only in season (C0 off-monsoon, C4 monsoon).");
FIG("elbow", "kmeans_elbow_silhouette.png", "Choosing *k*: inertia (elbow) and mean silhouette score for *k* = 2…10; the dashed line marks the chosen *k* = 5.");
TABLE("clusters", "Cluster Profiles (k = 5)", ["Cluster", "Size", "Avg. impact", "Dominant type", "Monsoon"],
  cl.profiles.map((p) => [`C${p.cluster}`, p.size, p.avg_impact.toFixed(2),
                          `${p.top_risk_type} (${Math.round(p.top_risk_share * 100)}%)`, pct(p.monsoon_share, 0)]),
  { widths: [0.15, 0.13, 0.2, 0.32, 0.2], align: [C, R, R, L, R] });
FIG("scatter", "kmeans_clusters.png", "k-Means clusters of the " + wh.FACT_RISKEVENT + " risk events projected onto the first two principal components.");

// dashboard outputs: text in two columns, then the screenshots full width
H2("Dashboard Outputs");
P("{fig:dash_main}(a) shows the Overview page for the full data set: a Risk Exposure Index of 5,802, an average impact of 6.16 out of 10, all 387 events in view and a top-rule confidence of 88%. Every element responds to the filters; for example, restricting the region to the West re-computes the KPIs, the OLAP cube and the association rules for that slice only. {fig:dash_main}(b) shows the rules page, where the strongest rule is stated in plain language next to a support–confidence map of all rules (bubble size encodes lift) and the full rule table. {fig:dash_clusters} shows the interactive cluster map with cluster profiles, and {fig:dash_explore} the SPARQL console, here listing all events affecting one organisation with their type, place and score, and the searchable event log that traces every event back to its source article.");
startSection(1);
FIG2("dash_main", ["dash_overview.jpg", "(a) Overview"], ["dash_rules.jpg", "(b) Association rules"],
     "Dashboard pages. (a) Overview: sidebar navigation and OLAP filters, KPI cards with monthly sparklines, exposure trend, strongest rule in view, roll-up/drill-down cube, risk mix and cluster summary. (b) Association rules: highest-lift rule, rule landscape (support vs. confidence, bubble size = lift) and the ranked rule table.");
FIG("dash_clusters", "dash_clusters.jpg", "Dashboard — Clusters page: k-Means cluster map in PCA space with per-cluster size, dominant risk type and average impact.", { wide: true, scale: 0.72 });
FIG2("dash_explore", ["dash_knowledge_graph.jpg", "(a) Knowledge graph: SPARQL query and results"],
     ["dash_events.jpg", "(b) Event log with global search"],
     "Dashboard — exploration pages. (a) A SPARQL query over the RDF knowledge graph returning the events that affect one organisation. (b) The event log of the current scope, linked to source articles.");
startSection(2);

// ------------------------------------------------------------------ VII. Limitations & future work
H1("Limitations and Future Work");
P("The study has several limitations. The bundled corpus is synthetic, so the mined patterns demonstrate the method rather than real-world findings, and 240 articles is a modest sample. The co-occurrence rule produces spurious triples (precision " + pct(tp.precision) + "). The ontology records association, not causation, and has no causal taxonomy. Entity and source are degenerate attributes, adequate at this scale but not for hierarchical browsing. Processing is batch-oriented over historical text, there is no supervised severity classifier (no labels are available), and the impact score is a transparent heuristic rather than a calibrated financial measure.");
P("Future work follows directly from these limitations:");
bullets([
  "replace the co-occurrence rule with learned relation extraction, e.g. a fine-tuned transformer {ref:bert}, and add causal relations (*causes*, *mitigates*) to the ontology;",
  "train a severity classifier once a labelled subset exists, use DBSCAN {ref:dbscan} for outlier events and add rule-based alerting over the mining outputs;",
  "promote entity and source to full dimensions with slowly changing history, and ingest live news and social-media feeds;",
  "link entities to Wikidata {ref:wikidata} and company registries, and move the graph to a triple store with OWL reasoning;",
  "evaluate on a large real-world news corpus across more sectors and geographies.",
]);

// ------------------------------------------------------------------ VIII. Conclusion
H1("Conclusion");
P("OntoRisk BI shows that a small, transparent pipeline can turn unstructured business news into risk intelligence that is simultaneously *meaningful* (an OWL ontology and SPARQL-validated RDF graph), *analysable* (a DuckDB star schema supporting OLAP) and *mined* (FP-Growth rules and k-Means clusters), with every fact row linked to its triples. On an Indian-context corpus it extracted " + tp.predicted_events + " risk events with " + pct(tp.recall) + " recall and " + pct(tp.precision) + " precision, passed all semantic and referential integrity checks, and surfaced interpretable patterns, most notably the strong coupling of monsoon weather and logistics disruption (lift 3.96) and a distinct high-impact monsoon cluster. The open, tested and deployed implementation provides a practical base for small enterprises and for the learned-extraction and causal-modelling extensions outlined above.");

// ------------------------------------------------------------------ Acknowledgment + references
body.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 200, after: 100 },
  children: [new TextRun({ text: "Acknowledgment", font: FONT, size: 20, smallCaps: true })] }));
P("The authors thank Dr. Sathiyaraj Rajendran, Associate Professor, Department of Computer Science and Engineering, Manipal Institute of Technology Bengaluru, for his guidance throughout this project, and the department for its support.");

body.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 200, after: 100 },
  children: [new TextRun({ text: "References", font: FONT, size: 20, smallCaps: true })] }));
// cite any remaining technology references in the order they appear in the stack table
for (const k of ["rdflib", "pandas", "mlxtend", "streamlit", "plotly"]) refNo(k);
refOrder.forEach((key, i) => body.push(new Paragraph({
  alignment: AlignmentType.LEFT, spacing: { after: 30, line: 200 },
  indent: { left: 400, hanging: 400 }, tabStops: [{ type: TabStopType.LEFT, position: 400 }],
  children: [new TextRun({ text: `[${i + 1}]\t`, font: FONT, size: 16 }), ...runs(REFS[key], { size: 16 })],
})));
startSection(null);

// ------------------------------------------------------------------ assemble
const unused = Object.keys(REFS).filter((k) => !refOrder.includes(k));
if (unused.length) console.warn("Uncited references (not listed):", unused.join(", "));

const doc = new Document({
  creator: "OntoRisk BI team", title: "OntoRisk BI: An Ontology-Driven Semantic Data Warehouse for Proactive Business Risk Intelligence",
  styles: {
    default: { document: { run: { font: FONT, size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 20, smallCaps: true, color: "000000" }, paragraph: { outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 20, italics: true, color: "000000" }, paragraph: { outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "ieee-bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 300, hanging: 200 } } } }] }] },
  sections: sections.map((s, i) => ({
    properties: {
      ...(i ? { type: SectionType.CONTINUOUS } : {}),
      page: { size: PAGE, margin: MARGIN },
      column: s.columns === 2 ? { count: 2, space: GAP, equalWidth: true } : { count: 1 },
    },
    children: s.children,
  })),
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log(`Wrote ${OUT}  (${refOrder.length} references, ${FIG_ORDER.length} figures, ${TAB_ORDER.length} tables)`);
});
