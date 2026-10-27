"""Semantic-layer validation and querying with SPARQL (RDFLib's built-in engine).

``VALIDATION_QUERIES`` are run after triple generation (Week 2 deliverable:
"SPARQL validation queries passing").  Each query has a check that must hold.
``run_query`` is reused by the dashboard's semantic-query panel.
"""
from __future__ import annotations

import warnings

warnings.filterwarnings("ignore", message=".*deprecated.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)
from rdflib import Graph  # noqa: E402

from . import config  # noqa: E402

PREFIXES = """PREFIX ork: <%s>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
""" % config.BASE_IRI

VALIDATION_QUERIES = {
    "ontology_has_six_classes": (
        "SELECT (COUNT(DISTINCT ?c) AS ?n) WHERE { ?c a owl:Class . FILTER(STRSTARTS(STR(?c), STR(ork:))) }",
        lambda rows: int(rows[0][0]) == 6),
    "exactly_two_object_properties": (
        "SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE { ?p a owl:ObjectProperty }",
        lambda rows: int(rows[0][0]) == 2),
    "every_event_has_a_location": (
        "SELECT (COUNT(?e) AS ?n) WHERE { ?e a ork:RiskEvent . FILTER NOT EXISTS { ?e ork:locatedIn ?l } }",
        lambda rows: int(rows[0][0]) == 0),
    "every_event_affects_an_entity": (
        "SELECT (COUNT(?e) AS ?n) WHERE { ?e a ork:RiskEvent . FILTER NOT EXISTS { ?x ork:affects ?e } }",
        lambda rows: int(rows[0][0]) == 0),
    "domain_range_respected": (
        """SELECT (COUNT(*) AS ?n) WHERE {
             { ?x ork:affects ?e . FILTER NOT EXISTS { ?x a ork:Entity } }
             UNION { ?e ork:locatedIn ?l . FILTER NOT EXISTS { ?l a ork:Location } } }""",
        lambda rows: int(rows[0][0]) == 0),
    "events_per_risk_type": (
        "SELECT ?t (COUNT(?e) AS ?n) WHERE { ?e a ork:RiskEvent ; ork:riskCategory ?t } GROUP BY ?t ORDER BY DESC(?n)",
        lambda rows: len(rows) >= 1),
}

EXAMPLE_QUERIES = {
    "Events affecting an entity": """SELECT ?event ?type ?place ?score WHERE {
  ?ent ork:entityName "Konkan Freight Ltd" ; ork:affects ?event .
  ?event ork:riskCategory ?type ; ork:impactScore ?score ; ork:locatedIn ?loc .
  ?loc ork:placeName ?place } ORDER BY DESC(?score)""",
    "High-severity events in a state": """SELECT ?entity ?type ?place ?date WHERE {
  ?e ork:severityBand "High" ; ork:riskCategory ?type ; ork:eventDate ?date ; ork:locatedIn ?loc .
  ?loc ork:state "Maharashtra" ; ork:placeName ?place .
  ?x ork:affects ?e ; ork:entityName ?entity } ORDER BY ?date""",
    "Entities exposed to several risk types": """SELECT ?entity (COUNT(DISTINCT ?type) AS ?types) (COUNT(?e) AS ?events) WHERE {
  ?x ork:affects ?e ; ork:entityName ?entity . ?e ork:riskCategory ?type }
GROUP BY ?entity HAVING (COUNT(DISTINCT ?type) > 1) ORDER BY DESC(?types) DESC(?events)""",
    "Risk events per region": """SELECT ?region (COUNT(?e) AS ?n) (AVG(?s) AS ?avg_impact) WHERE {
  ?e ork:locatedIn ?l ; ork:impactScore ?s . ?l ork:region ?region } GROUP BY ?region ORDER BY DESC(?n)""",
}


def load_graph(path=config.KG_TTL) -> Graph:
    g = Graph()
    g.parse(path, format="turtle")
    return g


def run_query(g: Graph, sparql: str):
    res = g.query(PREFIXES + sparql)
    cols = [str(v) for v in res.vars]
    return cols, [[None if x is None else x.toPython() for x in row] for row in res]


def validate(g: Graph) -> dict:
    out = {}
    for name, (q, check) in VALIDATION_QUERIES.items():
        _, rows = run_query(g, q)
        out[name] = {"passed": bool(check(rows)), "result": [[str(c) for c in r] for r in rows][:10]}
    return out
