"""Stage 6 - Pandas ETL: Extract -> Clean / quality-check -> Transform -> Load.

Quality checks (Section 4.5): null & empty-text detection, duplicate
detection (by id and by text), date-parsing validation, whitespace
normalisation, and - after loading - referential checks of every fact row
against the dimension tables (see ``warehouse.referential_checks``).
"""
from __future__ import annotations

import re

import pandas as pd

from . import config, nlp


def extract(path=config.CORPUS_CSV) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def clean(df: pd.DataFrame):
    """Return (clean_df, quality_report)."""
    report = {"rows_in": int(len(df))}
    df = df.copy()
    for c in ("article_id", "title", "source", "text"):
        df[c] = df[c].fillna("").astype(str).str.strip()
    df["text"] = df["text"].map(lambda t: re.sub(r"[ \t]+", " ", t))

    empty = df["text"].str.len() < 40
    report["rejected_empty_text"] = int(empty.sum())
    df = df[~empty]

    dup_id = df.duplicated("article_id", keep="first")
    dup_text = df.duplicated("text", keep="first") & ~dup_id
    report["rejected_duplicate_id"] = int(dup_id.sum())
    report["rejected_duplicate_text"] = int(dup_text.sum())
    df = df[~(dup_id | dup_text)]

    parsed = pd.to_datetime(df["date"], errors="coerce")
    bad_date = parsed.isna()
    report["rejected_bad_date"] = int(bad_date.sum())
    df = df[~bad_date].assign(date=parsed[~bad_date].dt.date.astype(str))

    df["source"] = df["source"].replace("", "unknown")
    df["clean_text"] = df["text"].map(nlp.preprocess)        # tokenise, stop-words, lemmatise
    report["rows_out"] = int(len(df))
    return df.reset_index(drop=True), report
