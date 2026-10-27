"""Stages 4-5 - Co-occurrence relation rule, impact scoring and RDF generation.

THE CO-OCCURRENCE RULE (Section 4.3)
    For every paragraph, if it contains at least one ORGANISATION, one
    LOCATION and one RISK-VOCABULARY term, then for each (org, location,
    risk type) combination a RiskEvent is created and the triples

        <entity>    ork:affects    <event>
        <event>     ork:locatedIn  <location>

    are generated (plus data-property triples for score, severity, date,
    provenance ...).  No model is trained - it is a transparent, auditable
    rule.  Its weakness (spurious triples from incidental co-mentions) is
    measured in ``evaluate.py``.

Normalisations applied before the rule fires:
    * the same (article, org, risk type) seen with a city *and* its own state
      keeps only the more specific city;
    * duplicate (article, org, place, risk type) combinations are merged.

IMPACT SCORE (0-10) of an event - transparent heuristic:
    1.5 x (highest vocabulary weight of the matched terms, 1..3)
  + 0.8 x min(mention_count - 1, 2)           (repeated coverage)
  + 1.6 x article intensity                   (severe/halted/crore... minus minor/resumed)
  + 1.0 if the event comes from the lead paragraph
  + 0.5 base                                  -> clipped to [0, 10]
Severity band: Low < 4 <= Medium < 7 <= High.
"""
from __future__ import annotations

import hashlib
import warnings
from collections import defaultdict

import pandas as pd

warnings.filterwarnings("ignore", message=".*deprecated.*")
from rdflib import Graph, Literal  # noqa: E402
from rdflib.namespace import RDF, RDFS, XSD  # noqa: E402

from . import config, nlp  # noqa: E402
from .ontology import ORD, ORK, build_tbox  # noqa: E402


def severity_band(score: float) -> str:
    for lo, hi, band in config.SEVERITY_BANDS:
        if lo <= score < hi:
            return band
    return "High"


def impact_score(max_weight: int, mention_count: int, article_intensity: float, lead: bool) -> float:
    s = 0.5 + 1.5 * max_weight + 0.8 * min(mention_count - 1, 2) + 1.6 * article_intensity + (1.0 if lead else 0.0)
    return round(max(0.0, min(10.0, s)), 2)


def _slug(text: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in text).strip("_")


def extract_events(articles: pd.DataFrame):
    """Run NER + co-occurrence rule over cleaned articles.

    Returns (events_df, entities_df).  ``entities_df`` is one row per entity
    mention (for NER statistics); ``events_df`` one row per risk event.
    """
    ent_rows, cand = [], []
    for art in articles.itertuples(index=False):
        paras = nlp.analyse_article(art.article_id, art.text)
        art_intensity = nlp.intensity(art.text)
        # mentions per risk type across the whole article
        mentions = defaultdict(int)
        for p in paras:
            for _, rtype, _ in p.risk_terms:
                mentions[rtype] += 1
        for p in paras:
            for o in p.orgs:
                ent_rows.append((art.article_id, p.para_no, "ORG", o))
            for pl in p.places:
                ent_rows.append((art.article_id, p.para_no, "LOC", pl[0]))
            for d in p.dates:
                ent_rows.append((art.article_id, p.para_no, "DATE", d))
            for t, rtype, _ in p.risk_terms:
                ent_rows.append((art.article_id, p.para_no, "RISK_TERM", f"{t} [{rtype}]"))
            if not (p.orgs and p.places and p.risk_terms):
                continue                                   # rule does not fire
            by_type = defaultdict(list)
            for t, rtype, w in p.risk_terms:
                by_type[rtype].append((t, w))
            for org in p.orgs:
                for place, region, state, country in p.places:
                    for rtype, terms in by_type.items():
                        cand.append(dict(
                            article_id=art.article_id, para_no=p.para_no, entity_name=org,
                            location=place, region=region, state=state, country=country,
                            risk_type=rtype, matched_term=max(terms, key=lambda x: x[1])[0],
                            max_weight=max(w for _, w in terms), mention_count=mentions[rtype],
                            article_intensity=art_intensity, date=art.date, title=art.title,
                            source=art.source,
                            sector=nlp.classify_sector(org + " " + org + " " + p.text)))
    ev = pd.DataFrame(cand)
    ents = pd.DataFrame(ent_rows, columns=["article_id", "para_no", "label", "text"])
    if ev.empty:
        return ev, ents

    # keep the most specific place: drop (state-level) rows when a city of that state exists
    is_state_level = ev["location"].str.lower() == ev["state"].str.lower()
    city_keys = set(map(tuple, ev.loc[~is_state_level, ["article_id", "entity_name", "risk_type", "state"]]
                        .itertuples(index=False)))
    has_city = [(a, e, t, s) in city_keys for a, e, t, s in
                ev[["article_id", "entity_name", "risk_type", "state"]].itertuples(index=False)]
    ev = ev[~(is_state_level & pd.Series(has_city, index=ev.index))]
    ev = ev.sort_values("para_no").drop_duplicates(["article_id", "entity_name", "location", "risk_type"])

    ev["impact_score"] = [impact_score(r.max_weight, r.mention_count, r.article_intensity, r.para_no == 0)
                          for r in ev.itertuples()]
    ev["severity"] = ev["impact_score"].map(severity_band)
    ev["event_id"] = [
        "EV_" + hashlib.md5(f"{r.article_id}|{r.entity_name}|{r.location}|{r.risk_type}".encode()).hexdigest()[:10]
        for r in ev.itertuples()]
    ev = ev.reset_index(drop=True)
    cols = ["event_id", "article_id", "para_no", "date", "entity_name", "sector", "location", "region",
            "state", "country", "risk_type", "matched_term", "mention_count", "impact_score", "severity",
            "title", "source"]
    return ev[cols], ents


def events_to_graph(events: pd.DataFrame, with_tbox: bool = True) -> Graph:
    """Convert events to RDF triples linked to the ontology classes/properties."""
    g = build_tbox() if with_tbox else Graph()
    g.bind("ork", ORK)
    g.bind("ord", ORD)
    for r in events.itertuples(index=False):
        ev = ORD[r.event_id]
        ent = ORD["entity/" + _slug(r.entity_name)]
        loc = ORD["location/" + _slug(r.location)]
        art = ORD["article/" + r.article_id]
        # classes
        g.add((ev, RDF.type, ORK.RiskEvent))
        g.add((ent, RDF.type, ORK.Entity))
        g.add((loc, RDF.type, ORK.Location))
        g.add((art, RDF.type, ORK.SourceArticle))
        # the two object properties produced by the co-occurrence rule
        g.add((ent, ORK.affects, ev))
        g.add((ev, ORK.locatedIn, loc))
        # data properties
        g.add((ev, RDFS.label, Literal(f"{r.risk_type} risk: {r.entity_name} @ {r.location}")))
        g.add((ev, ORK.eventId, Literal(r.event_id)))
        g.add((ev, ORK.riskCategory, Literal(r.risk_type)))
        g.add((ev, ORK.impactScore, Literal(r.impact_score, datatype=XSD.decimal)))
        g.add((ev, ORK.severityBand, Literal(r.severity)))
        g.add((ev, ORK.mentionCount, Literal(int(r.mention_count), datatype=XSD.integer)))
        g.add((ev, ORK.eventDate, Literal(str(r.date)[:10], datatype=XSD.date)))
        g.add((ev, ORK.sourceId, Literal(r.article_id)))
        g.add((ev, ORK.matchedTerm, Literal(r.matched_term)))
        g.add((ent, ORK.entityName, Literal(r.entity_name)))
        g.add((ent, ORK.sector, Literal(r.sector)))
        g.add((loc, ORK.placeName, Literal(r.location)))
        g.add((loc, ORK.region, Literal(r.region)))
        g.add((loc, ORK.state, Literal(r.state)))
        g.add((loc, ORK.country, Literal(r.country)))
        g.add((art, ORK.headline, Literal(r.title)))
        g.add((art, ORK.publisher, Literal(r.source)))
    return g


def link_table(events: pd.DataFrame) -> pd.DataFrame:
    """The triple <-> fact-row bridge stored in the warehouse (semantic enrichment)."""
    rows = []
    for r in events.itertuples(index=False):
        ev = f"ord:{r.event_id}"
        ent = f"ord:entity/{_slug(r.entity_name)}"
        loc = f"ord:location/{_slug(r.location)}"
        rows += [(r.event_id, ent, "ork:affects", ev),
                 (r.event_id, ev, "ork:locatedIn", loc),
                 (r.event_id, ev, "rdf:type", "ork:RiskEvent"),
                 (r.event_id, ev, "ork:riskCategory", r.risk_type),
                 (r.event_id, ev, "ork:severityBand", r.severity)]
    return pd.DataFrame(rows, columns=["event_id", "subject", "predicate", "object"])
