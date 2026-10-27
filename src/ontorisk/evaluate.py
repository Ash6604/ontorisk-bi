"""Evaluation of the extraction layer (Sections 4.3 / 4.6).

* Triple precision - the report plans a manual review of a random sample of
  generated triples.  ``review_sample`` writes that sample to
  ``outputs/triple_review_sample.csv`` with the source paragraph, ready for a
  team member to mark ``is_correct`` by hand.
* When the synthetic corpus is used the generator's ground truth
  (``gold_events.csv``) is available, so precision / recall / F1 of the
  co-occurrence rule are also computed automatically over *all* events and
  the sample is pre-labelled.  A predicted event is correct when the gold
  standard has the same (article, organisation, risk type) at the same place
  or in the same state.
"""
from __future__ import annotations

import pandas as pd

from . import config, nlp


def _gold_index(gold: pd.DataFrame):
    by_city = set(zip(gold.article_id, gold.entity, gold.risk_type, gold.location.str.lower()))
    by_state = set(zip(gold.article_id, gold.entity, gold.risk_type, gold.state.str.lower()))
    return by_city, by_state


def label_events(events: pd.DataFrame, gold: pd.DataFrame) -> pd.Series:
    by_city, by_state = _gold_index(gold)
    return pd.Series([
        (r.article_id, r.entity_name, r.risk_type, r.location.lower()) in by_city
        or (r.article_id, r.entity_name, r.risk_type, r.state.lower()) in by_state
        for r in events.itertuples()], index=events.index)


def precision_recall(events: pd.DataFrame, gold: pd.DataFrame) -> dict:
    correct = label_events(events, gold)
    gold_keys = set(zip(gold.article_id, gold.entity, gold.risk_type, gold.state.str.lower()))
    found = set(zip(events.article_id, events.entity_name, events.risk_type, events.state.str.lower()))
    tp_gold = len(gold_keys & found)
    p = float(correct.mean()) if len(events) else 0.0
    r = tp_gold / len(gold_keys) if gold_keys else 0.0
    by_type = (events.assign(correct=correct).groupby("risk_type")["correct"].mean().round(3).to_dict())
    return {"predicted_events": int(len(events)), "correct_events": int(correct.sum()),
            "gold_events": len(gold_keys), "gold_events_found": tp_gold,
            "precision": round(p, 4), "recall": round(r, 4),
            "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0,
            "precision_by_risk_type": by_type}


def review_sample(events: pd.DataFrame, articles: pd.DataFrame, gold: pd.DataFrame | None,
                  n: int = config.TRIPLE_REVIEW_SAMPLE) -> pd.DataFrame:
    s = events.sample(min(n, len(events)), random_state=config.RANDOM_STATE).copy()
    text = dict(zip(articles.article_id, articles.text))
    s["paragraph"] = [nlp.split_paragraphs(text[a])[p] for a, p in zip(s.article_id, s.para_no)]
    s["triple_affects"] = "<" + s.entity_name + "> ork:affects <" + s.event_id + ">"
    s["triple_locatedIn"] = "<" + s.event_id + "> ork:locatedIn <" + s.location + ">"
    s["auto_label"] = label_events(s, gold).map({True: "correct", False: "spurious"}) if gold is not None else ""
    s["is_correct (manual Y/N)"] = ""
    cols = ["event_id", "article_id", "entity_name", "location", "risk_type", "matched_term",
            "triple_affects", "triple_locatedIn", "paragraph", "auto_label", "is_correct (manual Y/N)"]
    return s[cols].reset_index(drop=True)


def ner_stats(entities: pd.DataFrame) -> dict:
    return {"mentions_by_label": entities["label"].value_counts().to_dict(),
            "distinct_orgs": int(entities.loc[entities.label == "ORG", "text"].nunique()),
            "distinct_places": int(entities.loc[entities.label == "LOC", "text"].nunique())}
