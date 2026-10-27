"""Stages 2-3 - Text preprocessing, named entity recognition and risk tagging.

* Preprocessing (spaCy): tokenisation, stop-word removal and lemmatisation.
  The lemmatised, stop-word-free text is stored for analysis/inspection.
* NER (spaCy ``en_core_web_sm``): ORG, GPE, LOC and DATE entities, run on the
  *original* paragraphs (NER needs capitalisation and function words).
* Risk tagging: longest-match lookup of the curated risk vocabulary
  (``data/risk_vocabulary.json``) using spaCy's PhraseMatcher on lower-cased
  text, so "port congestion" wins over the shorter "congestion".
* Normalisation: organisation names are cleaned (possessives, "the"), places
  are mapped to (region, state, country) via the gazetteer.

If spaCy or its model is not installed the module falls back to a small
rule-based recogniser (capitalised spans ending in Ltd/Bank/... for ORG and
gazetteer lookup for places) so the rest of the pipeline can still be run;
``BACKEND`` records which one was used and is reported in the metrics.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache

from . import config

try:  # ------------------------------------------------------------ spaCy
    import spacy
    from spacy.matcher import PhraseMatcher
    from spacy.util import filter_spans

    _NLP = spacy.load("en_core_web_sm")
    BACKEND = f"spaCy {spacy.__version__} / en_core_web_sm {_NLP.meta.get('version', '?')}"
except Exception:  # pragma: no cover - exercised only without spaCy
    spacy = None
    _NLP = None
    BACKEND = "rule-based fallback (spaCy not installed)"


@lru_cache(maxsize=1)
def vocabulary() -> dict:
    return json.loads(config.VOCAB_JSON.read_text())


@lru_cache(maxsize=1)
def gazetteer() -> dict:
    return json.loads(config.GAZETTEER_JSON.read_text())["places"]


@lru_cache(maxsize=1)
def term_index() -> dict:
    """term (lower-case) -> (risk_type, weight)."""
    idx = {}
    for rtype, spec in vocabulary()["risk_types"].items():
        for term, w in spec["terms"].items():
            idx[term.lower()] = (rtype, w)
    return idx


@lru_cache(maxsize=1)
def _phrase_matcher():
    pm = PhraseMatcher(_NLP.vocab, attr="LOWER")
    for term in term_index():
        pm.add(term, [_NLP.make_doc(term)])
    return pm


# --------------------------------------------------------------------- data types
@dataclass
class Paragraph:
    article_id: str
    para_no: int
    text: str
    orgs: list = field(default_factory=list)
    places: list = field(default_factory=list)
    dates: list = field(default_factory=list)
    risk_terms: list = field(default_factory=list)   # (term, risk_type, weight)


# --------------------------------------------------------------------- preprocessing
def preprocess(text: str) -> str:
    """Lower-cased lemmas with stop words, punctuation and numbers removed."""
    if _NLP is not None:
        doc = _NLP(text)
        return " ".join(t.lemma_.lower() for t in doc
                        if not (t.is_stop or t.is_punct or t.is_space or t.like_num))
    toks = re.findall(r"[a-zA-Z][a-zA-Z'-]+", text.lower())
    stop = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "at", "for", "its", "it", "is",
            "was", "were", "be", "by", "with", "as", "from", "that", "this", "said", "has", "had"}
    return " ".join(t for t in toks if t not in stop)


def split_paragraphs(text: str) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", str(text)) if p.strip()]
    return paras or ([str(text).strip()] if str(text).strip() else [])


# --------------------------------------------------------------------- normalisation
_ORG_PREFIX = re.compile(r"^(the|shares of|exporters including|officials at)\s+", re.I)


_ORG_SUFFIX = re.compile(r"\s+(on|at|in|near|from|for)(\s+.*)?$", re.I)   # "X Ltd in Hyderabad" -> "X Ltd"
_ORG_LEAD = re.compile(r"^.*\s(prompted|forced|said|hit)\s+", re.I)          # "Kochi prompted X Ltd" -> "X Ltd"


def normalise_org(name: str) -> str:
    """Clean NER span-boundary errors (small model sometimes swallows neighbouring words)."""
    name = re.sub(r"[’']s$", "", name.strip())
    name = _ORG_SUFFIX.sub("", name)
    name = _ORG_LEAD.sub("", name)
    name = _ORG_PREFIX.sub("", name)
    return re.sub(r"\s+", " ", name).strip(" .,")


def lookup_place(name: str):
    """Return (canonical name, region, state, country) or None."""
    key = re.sub(r"^the\s+", "", name.strip().lower()).strip(" .,")
    key = re.sub(r"\s+(port|terminal|city)$", "", key)
    g = gazetteer()
    if key in g:
        region, state, country = g[key]
        return key.title() if key != "nhava sheva" else "Nhava Sheva", region, state, country
    return None


def classify_sector(text: str) -> str:
    low = text.lower()
    scores = {s: sum(len(re.findall(rf"\b{re.escape(w)}\b", low)) for w in words)
              for s, words in vocabulary()["sector_terms"].items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "General"


def intensity(text: str) -> float:
    low = text.lower()
    return sum(v * len(re.findall(rf"\b{re.escape(k)}\b", low))
               for k, v in vocabulary()["intensity_terms"].items())


# --------------------------------------------------------------------- extraction
def _risk_terms_spacy(doc):
    spans = filter_spans([doc[s:e] for _, s, e in _phrase_matcher()(doc)])  # longest match wins
    idx = term_index()
    return [(sp.text.lower(), *idx[sp.text.lower()]) for sp in spans]


def _risk_terms_regex(text: str):
    low, found, taken = text.lower(), [], []
    for term in sorted(term_index(), key=len, reverse=True):
        for m in re.finditer(rf"\b{re.escape(term)}\b", low):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            taken.append((m.start(), m.end()))
            found.append((term, *term_index()[term]))
    return found


_ORG_RE = re.compile(r"((?:[A-Z][A-Za-z]+\s){1,4}(?:Ltd|Limited|Bank|Company|Corporation|Lines|Movers|"
                     r"Logistics|Services|Technologies|Mart|Stores|Retail|Fintech|Works|Research|"
                     r"Analytics|Securities|Agency))\b")


def analyse_paragraph(article_id: str, para_no: int, text: str) -> Paragraph:
    p = Paragraph(article_id, para_no, text)
    if _NLP is not None:
        doc = _NLP(text)
        for ent in doc.ents:
            if ent.label_ == "ORG":
                org = normalise_org(ent.text)
                if lookup_place(org):          # e.g. "Chennai Port" tagged ORG -> it is a place
                    p.places.append(lookup_place(org))
                elif len(org) > 2 and not term_index().get(org.lower()) and org.upper() != "RBI":
                    p.orgs.append(org)
            elif ent.label_ in ("GPE", "LOC", "FAC"):
                place = lookup_place(ent.text)
                if place:
                    p.places.append(place)
            elif ent.label_ == "DATE":
                p.dates.append(ent.text)
        # pretrained NER sometimes misses multi-word Indian place names (e.g. "Nhava Sheva");
        # a gazetteer pass on the paragraph recovers them - standard practice for NER + KB linking.
        low = text.lower()
        for key in gazetteer():
            if re.search(rf"\b{re.escape(key)}\b", low) and not any(pl[0].lower() == key for pl in p.places):
                if any(key in pl[0].lower() for pl in p.places):   # "mumbai" inside "navi mumbai"
                    continue
                p.places.append(lookup_place(key))
        p.risk_terms = _risk_terms_spacy(doc)
    else:
        p.orgs = [normalise_org(m) for m in _ORG_RE.findall(text)]
        low = text.lower()
        for key in sorted(gazetteer(), key=len, reverse=True):
            if re.search(rf"\b{re.escape(key)}\b", low) and not any(key in pl[0].lower() for pl in p.places):
                p.places.append(lookup_place(key))
        p.risk_terms = _risk_terms_regex(text)
    # de-duplicate while keeping order
    p.orgs = list(dict.fromkeys(p.orgs))
    p.places = list(dict.fromkeys(p.places))
    return p


def analyse_article(article_id: str, text: str) -> list[Paragraph]:
    return [analyse_paragraph(article_id, i, t) for i, t in enumerate(split_paragraphs(text))]
