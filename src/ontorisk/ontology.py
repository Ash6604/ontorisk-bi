"""Stage 4a - The compact OntoRisk domain ontology (Section 4.4).

Six classes  : RiskEvent, Entity, Location, RiskType, SourceArticle, RiskTerm
Two object properties (the only ones, by design):
    affects    : Entity    -> RiskEvent
    locatedIn  : RiskEvent -> Location
Everything else - impact score, severity band, risk category, provenance,
dates - is a *data* property, exactly as the report specifies (impact and
provenance are modelled as properties rather than classes).

The ontology is generated with RDFLib so that it is version-controlled as
code, and serialised both as Turtle and as RDF/XML (.owl) - the RDF/XML file
opens directly in Protégé (File > Open) for inspection, visual browsing with
OntoGraf, and running the HermiT reasoner.
"""
from __future__ import annotations

import json
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*deprecated.*")

from rdflib import Graph, Literal, Namespace, URIRef  # noqa: E402
from rdflib.namespace import OWL, RDF, RDFS, XSD, DCTERMS  # noqa: E402

from . import config  # noqa: E402

ORK = Namespace(config.BASE_IRI)
ORD = Namespace(config.DATA_IRI)

CLASSES = {
    "RiskEvent": "A business-risk occurrence detected in text, e.g. a flood disrupting a warehouse.",
    "Entity": "An organisation (company, bank, retailer...) that a risk event affects.",
    "Location": "A geographic place (city, port, state, country) where a risk event occurs.",
    "RiskType": "The category of a risk: weather, logistics, policy, supplier or reputational.",
    "SourceArticle": "The news article a risk event was extracted from (provenance).",
    "RiskTerm": "A controlled-vocabulary keyword that signals a risk type (e.g. 'port congestion').",
}
OBJECT_PROPERTIES = {
    "affects": ("Entity", "RiskEvent", "The entity is affected by (exposed to) the risk event."),
    "locatedIn": ("RiskEvent", "Location", "The risk event takes place in the location."),
}
# name: (domain, xsd range, comment)
DATA_PROPERTIES = {
    "eventId": ("RiskEvent", XSD.string, "Shared identifier linking the event to its warehouse fact row."),
    "impactScore": ("RiskEvent", XSD.decimal, "Impact score on a 0-10 scale."),
    "severityBand": ("RiskEvent", XSD.string, "Low / Medium / High band derived from the impact score."),
    "riskCategory": ("RiskEvent", XSD.string, "Name of the RiskType individual for the event."),
    "mentionCount": ("RiskEvent", XSD.integer, "Number of risk-vocabulary mentions of this type in the article."),
    "eventDate": ("RiskEvent", XSD.date, "Publication date of the source article."),
    "sourceId": ("RiskEvent", XSD.string, "Identifier of the source article (provenance as a property)."),
    "matchedTerm": ("RiskEvent", XSD.string, "Vocabulary term that triggered the event."),
    "sector": ("Entity", XSD.string, "Business sector assigned to the entity in the article."),
    "entityName": ("Entity", XSD.string, "Normalised organisation name."),
    "placeName": ("Location", XSD.string, "Normalised place name."),
    "region": ("Location", XSD.string, "Indian region (West, South, ...) or International."),
    "state": ("Location", XSD.string, "State / province."),
    "country": ("Location", XSD.string, "Country."),
    "termLabel": ("RiskTerm", XSD.string, "Surface form of the vocabulary term."),
    "signalsCategory": ("RiskTerm", XSD.string, "Risk type the term signals."),
    "termWeight": ("RiskTerm", XSD.integer, "Weight (1-3) of the term in impact scoring."),
    "headline": ("SourceArticle", XSD.string, "Article headline."),
    "publisher": ("SourceArticle", XSD.string, "Article source / publisher."),
}


def build_tbox() -> Graph:
    g = Graph()
    g.bind("ork", ORK)
    g.bind("ord", ORD)
    g.bind("owl", OWL)
    g.bind("dcterms", DCTERMS)
    onto = URIRef(config.BASE_IRI.rstrip("#"))
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, RDFS.label, Literal("OntoRisk BI domain risk ontology", lang="en")))
    g.add((onto, DCTERMS.description, Literal(
        "Compact ontology for business-risk intelligence: six classes, two object properties.")))
    g.add((onto, OWL.versionInfo, Literal("1.0")))

    for name, comment in CLASSES.items():
        g.add((ORK[name], RDF.type, OWL.Class))
        g.add((ORK[name], RDFS.label, Literal(name, lang="en")))
        g.add((ORK[name], RDFS.comment, Literal(comment, lang="en")))
    # classes are mutually disjoint
    names = list(CLASSES)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            g.add((ORK[a], OWL.disjointWith, ORK[b]))

    for name, (dom, rng, comment) in OBJECT_PROPERTIES.items():
        g.add((ORK[name], RDF.type, OWL.ObjectProperty))
        g.add((ORK[name], RDFS.domain, ORK[dom]))
        g.add((ORK[name], RDFS.range, ORK[rng]))
        g.add((ORK[name], RDFS.label, Literal(name, lang="en")))
        g.add((ORK[name], RDFS.comment, Literal(comment, lang="en")))
    # every event happens in exactly one place
    g.add((ORK.locatedIn, RDF.type, OWL.FunctionalProperty))

    for name, (dom, rng, comment) in DATA_PROPERTIES.items():
        g.add((ORK[name], RDF.type, OWL.DatatypeProperty))
        g.add((ORK[name], RDF.type, OWL.FunctionalProperty)) if name in (
            "eventId", "impactScore", "severityBand", "riskCategory") else None
        g.add((ORK[name], RDFS.domain, ORK[dom]))
        g.add((ORK[name], RDFS.range, rng))
        g.add((ORK[name], RDFS.comment, Literal(comment, lang="en")))

    # RiskType individuals and RiskTerm individuals from the vocabulary
    vocab = json.loads(config.VOCAB_JSON.read_text())
    for rtype, spec in vocab["risk_types"].items():
        rt = ORK[f"RiskType_{rtype}"]
        g.add((rt, RDF.type, OWL.NamedIndividual))
        g.add((rt, RDF.type, ORK.RiskType))
        g.add((rt, RDFS.label, Literal(rtype, lang="en")))
        g.add((rt, RDFS.comment, Literal(spec["sub_type"], lang="en")))
        for term, w in spec["terms"].items():
            tid = ORK["Term_" + "".join(ch if ch.isalnum() else "_" for ch in term)]
            g.add((tid, RDF.type, OWL.NamedIndividual))
            g.add((tid, RDF.type, ORK.RiskTerm))
            g.add((tid, ORK.termLabel, Literal(term)))
            g.add((tid, ORK.signalsCategory, Literal(rtype)))
            g.add((tid, ORK.termWeight, Literal(int(w), datatype=XSD.integer)))
    return g


def write_ontology() -> Graph:
    config.ensure_dirs()
    g = build_tbox()
    g.serialize(config.ONTOLOGY_TTL, format="turtle")
    g.serialize(config.ONTOLOGY_OWL, format="xml")
    return g


if __name__ == "__main__":
    graph = write_ontology()
    print(f"ontology: {len(graph)} triples -> {config.ONTOLOGY_TTL.name}, {config.ONTOLOGY_OWL.name}")
