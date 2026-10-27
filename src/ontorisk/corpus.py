"""Stage 1 - Corpus collection.

Two ways to obtain the 150-300 article corpus described in Section 4.2:

1. ``load_external_csv(path)`` - use a real public news dataset (e.g. a Kaggle
   Indian business-news CSV).  Any CSV with a text column works; the loader
   maps common column names (title/headline, text/content/description/body,
   date/published_at, source/publisher) onto the project schema.

2. ``build_synthetic_corpus(n)`` - a reproducible, curated *synthetic* corpus
   of Indian business-risk news written from templates.  Companies are
   fictional; places, risk categories and seasonality (monsoon June-September,
   cyclones October-November, port congestion at Nhava Sheva / Mundra /
   Chennai, policy news from New Delhi...) follow the Indian regional context
   of the report.  Because the generator knows which company/place/risk was
   really involved, it also writes ``gold_events.csv`` - the ground truth used
   to measure the precision of the co-occurrence rule automatically.  Every
   article also contains realistic "noise" (analyst comments, second places,
   generic mentions) so the rule produces some spurious triples, as the report
   anticipates.

Output schema (data/raw/news_corpus.csv):
    article_id, title, date, source, text   (paragraphs separated by a blank line)
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from . import config

# --------------------------------------------------------------------- actors
COMPANIES = {
    "Supply Chain & Logistics": [
        "Konkan Freight Ltd", "Coromandel Shipping Lines", "Saurashtra Logistics Ltd",
        "Brahmaputra Cargo Movers", "Deccan Warehousing Corporation", "Eastern Gateway Logistics",
        "Malabar Container Services", "Vizag Port Logistics Ltd",
    ],
    "Retail": [
        "Annapurna Retail Ltd", "BazaarKart Technologies", "Kaveri Fresh Mart",
        "Sangam Fashion Stores", "UrbanCart Retail", "Himalaya Grocers Ltd",
    ],
    "Finance": [
        "Sindhu Finance Ltd", "Narmada Cooperative Bank", "Trident Capital Ltd",
        "PaySetu Fintech", "Garuda Insurance Company", "Vijaynagar Credit Ltd",
    ],
    "Manufacturing": [
        "Sahyadri Textiles Ltd", "Hosur Auto Components Ltd", "Kalinga Steel Works",
        "Nilgiri Pharma Ltd", "Vindhya Cement Ltd", "Tapti Electronics Ltd", "Godavari Chemicals Ltd",
    ],
}
ANALYSTS = ["Meridian Research", "Ashoka Analytics", "Northstar Securities", "Lotus Ratings Agency"]

SECTOR_WORDS = {
    "Supply Chain & Logistics": ["freight", "cargo", "warehouse", "logistics"],
    "Retail": ["stores", "retail", "outlets", "e-commerce"],
    "Finance": ["bank", "loan", "credit", "lender"],
    "Manufacturing": ["plant", "factory", "production", "manufacturing"],
}

STATE_OF = {
    "Mumbai": "Maharashtra", "Nhava Sheva": "Maharashtra", "Pune": "Maharashtra", "Nashik": "Maharashtra",
    "Mundra": "Gujarat", "Kandla": "Gujarat", "Ahmedabad": "Gujarat", "Surat": "Gujarat",
    "Chennai": "Tamil Nadu", "Hosur": "Tamil Nadu", "Coimbatore": "Tamil Nadu", "Tuticorin": "Tamil Nadu",
    "Bengaluru": "Karnataka", "Mangaluru": "Karnataka", "Kochi": "Kerala", "Kozhikode": "Kerala",
    "Hyderabad": "Telangana", "Visakhapatnam": "Andhra Pradesh", "Kolkata": "West Bengal",
    "Haldia": "West Bengal", "Bhubaneswar": "Odisha", "Paradip": "Odisha", "Jamshedpur": "Jharkhand",
    "Guwahati": "Assam", "New Delhi": "Delhi", "Gurugram": "Haryana", "Noida": "Uttar Pradesh",
    "Ludhiana": "Punjab", "Jaipur": "Rajasthan", "Indore": "Madhya Pradesh",
    "Singapore": "Singapore", "Colombo": "Western Province",
}

# Per-risk-type generative profile: where it happens, when, to which sectors,
# and how severe it tends to be.  These biases are what the mining layer is
# expected to rediscover.
PROFILE = {
    "weather": dict(
        places=["Mumbai", "Chennai", "Kochi", "Guwahati", "Bhubaneswar", "Paradip", "Kolkata", "Kozhikode", "Mangaluru"],
        months=[6, 7, 8, 9] * 4 + [10, 11, 5],
        sectors=["Supply Chain & Logistics"] * 3 + ["Manufacturing"] * 2 + ["Retail"],
        severity=[("high", .55), ("medium", .35), ("low", .10)],
    ),
    "logistics": dict(
        places=["Nhava Sheva", "Mundra", "Chennai", "Kolkata", "Visakhapatnam", "Tuticorin", "Kandla", "Haldia", "Colombo", "Singapore"],
        months=list(range(1, 13)),
        sectors=["Supply Chain & Logistics"] * 3 + ["Retail"] * 2 + ["Manufacturing"],
        severity=[("high", .25), ("medium", .55), ("low", .20)],
    ),
    "policy": dict(
        places=["New Delhi"] * 4 + ["Mumbai"] * 2 + ["Ahmedabad"],
        months=list(range(1, 13)) + [2, 2, 7],
        sectors=["Finance"] * 3 + ["Manufacturing"] * 2 + ["Retail"],
        severity=[("high", .20), ("medium", .60), ("low", .20)],
    ),
    "supplier": dict(
        places=["Hosur", "Pune", "Bengaluru", "Coimbatore", "Jamshedpur", "Ludhiana", "Surat", "Nashik"],
        months=list(range(1, 13)),
        sectors=["Manufacturing"] * 4 + ["Retail"],
        severity=[("high", .40), ("medium", .45), ("low", .15)],
    ),
    "reputational": dict(
        places=["Bengaluru", "Gurugram", "Hyderabad", "Mumbai", "Noida"],
        months=list(range(1, 13)),
        sectors=["Retail"] * 3 + ["Finance"] * 3,
        severity=[("high", .10), ("medium", .35), ("low", .55)],
    ),
}
TYPE_WEIGHTS = {"weather": .27, "logistics": .25, "policy": .16, "supplier": .17, "reputational": .15}
# Secondary risk that tends to accompany a primary one in the same story.
SECONDARY = {"weather": ("logistics", .55), "policy": ("supplier", .30), "supplier": ("reputational", .15),
             "logistics": ("supplier", .15), "reputational": ("policy", .15)}

# --------------------------------------------------------------------- templates
EVENT_TPL = {
    "weather": [
        "{org} said operations at its {city} {sw} were disrupted after {term} lashed {state} on {weekday}.",
        "Heavy rain and {term} in {city} forced {org} to suspend dispatches from its {sw} facility, the company said.",
        "{org} reported that its {city} {sw} was inundated as {term} swept across coastal {state}.",
        "A {term} warning issued for {city} prompted {org} to move inventory out of its {sw} hub.",
    ],
    "logistics": [
        "{org} said {term} at {city} has delayed inbound containers bound for its {sw} network.",
        "Shipments handled by {org} at {city} are facing {term}, with trucks queuing outside the terminal.",
        "{org} flagged {term} at the {city} terminal as a key risk to its {sw} schedules this quarter.",
        "Exporters including {org} said {term} at {city} has pushed up costs for {sw} operations.",
    ],
    "policy": [
        "{org} said the {term} announced in {city} would affect its {sw} business from next month.",
        "Following the {term} notified by authorities in {city}, {org} said it was reviewing its {sw} portfolio.",
        "{org} warned investors that the {term} unveiled in {city} could squeeze {sw} margins.",
        "Officials in {city} confirmed a {term} that {org} said would raise compliance costs across its {sw} operations.",
    ],
    "supplier": [
        "{org} said a {term} at a key vendor near {city} has hit output at its {sw}.",
        "{org} reported a {term} affecting its {city} {sw}, citing problems at a tier-two supplier.",
        "Production at the {city} {sw} of {org} was affected by a {term}, the company told exchanges.",
        "{org} said it was sourcing alternatives after a {term} disrupted supplies to its {city} {sw}.",
    ],
    "reputational": [
        "{org} is facing a {term} after customers in {city} raised concerns about its {sw} services.",
        "A {term} hit {org} this week, with complaints from {city} spreading quickly online about its {sw}.",
        "{org} said it had initiated a review following a {term} linked to its {city} {sw} operations.",
        "Shares of {org} fell after reports of a {term} involving its {sw} business in {city}.",
    ],
}
TERMS = {
    "weather": ["floods", "heavy rainfall", "a cyclone", "landslides", "flooding", "monsoon rains", "a cloudburst", "waterlogging"],
    "logistics": ["port congestion", "berthing delays", "a vessel backlog", "a container shortage", "freight delays", "cargo pile-up", "a truckers' strike"],
    "policy": ["export ban", "import duty", "tariff hike", "GST revision", "regulatory crackdown", "RBI circular", "anti-dumping duty", "price cap", "new compliance norms"],
    "supplier": ["raw material shortage", "plant shutdown", "chip shortage", "supplier default", "labour strike", "production halt", "component shortage", "supplier insolvency"],
    "reputational": ["product recall", "consumer boycott", "data breach", "social media backlash", "quality complaints", "fraud allegations"],
}
IMPACT_TPL = {
    "high": [
        "Operations were halted for nearly {n} days and the company estimated losses of about Rs {m} crore.",
        "The disruption was described as the worst in a decade, with severe delays and stranded consignments.",
        "Management said activity had been shut across affected sites and losses could exceed Rs {m} crore.",
    ],
    "medium": [
        "The company expects delays of {n} to {n2} days and said it was working to restore normal schedules.",
        "Executives said deliveries were partially suspended and margins could come under some pressure.",
        "The firm said it had rerouted part of its volumes and would assess the financial effect next quarter.",
    ],
    "low": [
        "The company said the impact was minor and normal activity had resumed within a day.",
        "Officials described it as a limited impact event, with most operations unaffected.",
        "A spokesperson said there was only a minor effect on schedules and no change to guidance.",
    ],
}
SECONDARY_TPL = {
    "logistics": "The {term} also triggered {term2} at {city2}, where {org} moves much of its cargo.",
    "supplier": "{org} added that the {term} could lead to a {term2} for units in {city2}.",
    "reputational": "The episode has since sparked {term2} in {city2}, {org} acknowledged.",
    "policy": "Regulators in {city2} have also signalled a {term2} that {org} is monitoring.",
    "weather": "{org} said {term2} near {city2} added to the strain.",
}
NOISE_TPL = [
    "Analysts at {analyst} in {city3} said they were tracking the {term3} situation closely.",
    "Separately, {analyst} economists in {city3} kept their growth outlook for the sector unchanged.",
    "Market watchers at {analyst} said investors in {city3} were largely unmoved by the news.",
    "{analyst}, based in {city3}, noted that broader {sector_word} demand remained steady despite talk of {term3}.",
    "Industry body representatives in {city3} called for better infrastructure to cut such losses.",
]
CLOSING_TPL = [
    "The company said it would update stakeholders as the situation evolves.",
    "Shares of the company were little changed in afternoon trade.",
    "Industry executives expect clarity over the coming weeks.",
    "No further details were provided by the company.",
]
TITLE_TPL = {
    "weather": ["{term_t} disrupt {org} operations in {city}", "{org} hit as {term} batter {state}"],
    "logistics": ["{term_t} at {city} delays {org} shipments", "{org} flags {term} at {city}"],
    "policy": ["{org} reviews business after {term}", "{term_t}: {org} warns of margin pressure"],
    "supplier": ["{term_t} hits {org} output in {city}", "{org} grapples with {term}"],
    "reputational": ["{org} faces {term} in {city}", "{term_t} puts {org} under scrutiny"],
}
SOURCES = ["OntoRisk Synthetic Wire", "Synthetic Business Desk", "Synthetic Regional Bulletin"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


@dataclass
class GoldEvent:
    article_id: str
    entity: str
    location: str
    state: str
    risk_type: str
    severity_hint: str


def _pick_weighted(rng: random.Random, pairs):
    r, acc = rng.random(), 0.0
    for v, w in pairs:
        acc += w
        if r <= acc:
            return v
    return pairs[-1][0]


def _date_in_month(rng: random.Random, month: int) -> date:
    year = rng.choice([2024, 2025])
    start = date(year, month, 1)
    return start + timedelta(days=rng.randint(0, 27))


def _strip_article(term: str) -> str:
    return term.split(" ", 1)[1] if term.startswith(("a ", "an ")) else term


def build_synthetic_corpus(n: int = 240, seed: int = config.RANDOM_STATE):
    """Generate ``n`` news-style articles and their gold events."""
    rng = random.Random(seed)
    articles, gold = [], []
    types, weights = zip(*TYPE_WEIGHTS.items())
    for i in range(1, n + 1):
        aid = f"A{i:04d}"
        rtype = rng.choices(types, weights)[0]
        prof = PROFILE[rtype]
        sector = rng.choice(prof["sectors"])
        org = rng.choice(COMPANIES[sector])
        city = rng.choice(prof["places"])
        state = STATE_OF[city]
        term = rng.choice(TERMS[rtype])
        level = _pick_weighted(rng, prof["severity"])
        d = _date_in_month(rng, rng.choice(prof["months"]))
        sw = rng.choice(SECTOR_WORDS[sector])

        p1 = rng.choice(EVENT_TPL[rtype]).format(org=org, city=city, state=state, term=term, sw=sw,
                                                 weekday=rng.choice(WEEKDAYS))
        p1 = p1[0].upper() + p1[1:]
        imp = rng.choice(IMPACT_TPL[level]).format(n=rng.randint(2, 9), n2=rng.randint(10, 15),
                                                     m=rng.randint(5, 400))
        paragraphs = [p1 + " " + imp]
        gold.append(GoldEvent(aid, org, city, state, rtype, level))

        # optional secondary (co-occurring) risk in its own paragraph
        sec = SECONDARY.get(rtype)
        if sec and rng.random() < sec[1]:
            rtype2 = sec[0]
            city2 = rng.choice(PROFILE[rtype2]["places"])
            term2 = _strip_article(rng.choice(TERMS[rtype2]))
            paragraphs.append(SECONDARY_TPL[rtype2].format(term=_strip_article(term), term2=term2,
                                                           city2=city2, org=org))
            gold.append(GoldEvent(aid, org, city2, STATE_OF[city2], rtype2, level))

        # noise paragraph (incidental co-mentions -> spurious triples)
        if rng.random() < 0.65:
            city3 = rng.choice([c for c in STATE_OF if c not in (city,)])
            other_type = rng.choice(list(TERMS))
            paragraphs.append(rng.choice(NOISE_TPL).format(
                analyst=rng.choice(ANALYSTS), city3=city3,
                term3=_strip_article(rng.choice(TERMS[other_type])),
                sector_word=rng.choice(SECTOR_WORDS[sector])))
        paragraphs.append(rng.choice(CLOSING_TPL))

        t = rng.choice(TITLE_TPL[rtype])
        term_t = _strip_article(term)
        title = t.format(org=org, city=city, state=state, term=term_t, term_t=term_t[0].upper() + term_t[1:])
        articles.append(dict(article_id=aid, title=title, date=d.isoformat(),
                             source=rng.choice(SOURCES), text="\n\n".join(paragraphs)))

    # inject a few dirty records so the ETL quality checks have work to do
    if n >= 20:
        articles.append(dict(articles[3]))                                    # exact duplicate
        articles.append(dict(article_id=f"A{n + 1:04d}", title="Untitled", date="not-a-date",
                             source=SOURCES[0], text=articles[5]["text"] + " (Updated)"))  # bad date
        articles.append(dict(article_id=f"A{n + 2:04d}", title="Empty", date="2025-01-10",
                             source=SOURCES[0], text=""))                     # empty text

    return pd.DataFrame(articles), pd.DataFrame([g.__dict__ for g in gold])


COLUMN_ALIASES = {
    "title": ["title", "headline", "heading"],
    "text": ["text", "content", "body", "description", "article", "news", "summary"],
    "date": ["date", "published_at", "publish_date", "published", "datetime", "time"],
    "source": ["source", "publisher", "site", "outlet", "author"],
}


def load_external_csv(path: str | Path, limit: int = 300) -> pd.DataFrame:
    """Normalise an arbitrary public news CSV (e.g. from Kaggle) to the corpus schema."""
    df = pd.read_csv(path)
    lower = {c.lower(): c for c in df.columns}
    out = pd.DataFrame()
    for target, aliases in COLUMN_ALIASES.items():
        col = next((lower[a] for a in aliases if a in lower), None)
        out[target] = df[col] if col is not None else ("" if target != "date" else pd.NaT)
    out = out.head(limit).reset_index(drop=True)
    out.insert(0, "article_id", [f"X{i + 1:04d}" for i in range(len(out))])
    return out[["article_id", "title", "date", "source", "text"]]


def write_corpus(n: int = 240, external: str | None = None) -> pd.DataFrame:
    config.ensure_dirs()
    if external:
        df = load_external_csv(external)
        if config.GOLD_CSV.exists():
            config.GOLD_CSV.unlink()
    else:
        df, gold = build_synthetic_corpus(n)
        gold.to_csv(config.GOLD_CSV, index=False)
    df.to_csv(config.CORPUS_CSV, index=False)
    return df


if __name__ == "__main__":
    out = write_corpus()
    print(f"wrote {len(out)} articles -> {config.CORPUS_CSV}")
