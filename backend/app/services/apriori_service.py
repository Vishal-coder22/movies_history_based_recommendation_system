"""Apriori genre association mining over the master catalogue.

Transactions = catalogue movies -> genre baskets (the agreed MVP approach;
one user's history alone would be a single transaction, see spec section 14).
"""

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

from app.errors import UserError

DEFAULT_MIN_SUPPORT = 0.1
DEFAULT_MIN_CONFIDENCE = 0.3
MAX_RULES = 50


def _genre_transactions(conn) -> pd.DataFrame:
    rows = conn.execute(
        "SELECT movie_id, genres FROM movies WHERE genres IS NOT NULL AND genres != ''"
    ).fetchall()
    vocabulary: set[str] = set()
    baskets: list[set[str]] = []
    for row in rows:
        basket = {genre.strip() for genre in str(row["genres"]).split("|") if genre.strip()}
        if basket:
            vocabulary.update(basket)
            baskets.append(basket)
    genres = sorted(vocabulary)
    return pd.DataFrame(
        [{genre: genre in basket for genre in genres} for basket in baskets],
        columns=genres,
    )


def run_apriori(
    conn,
    min_support: float = DEFAULT_MIN_SUPPORT,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    min_lift: float | None = None,
) -> dict:
    if not (0 < min_support <= 1):
        raise UserError("Minimum support must be greater than 0 and at most 1 (for example 0.1).")
    if not (0 < min_confidence <= 1):
        raise UserError("Minimum confidence must be greater than 0 and at most 1 (for example 0.3).")
    if min_lift is not None and min_lift < 0:
        raise UserError("Minimum lift must be 0 or greater.")

    transactions = _genre_transactions(conn)
    if len(transactions) == 0:
        raise UserError("The catalogue has no genre data to mine.")

    frequent = apriori(transactions, min_support=min_support, use_colnames=True)
    if frequent.empty:
        return {
            "min_support": min_support,
            "min_confidence": min_confidence,
            "min_lift": min_lift,
            "transaction_count": int(len(transactions)),
            "frequent_itemset_count": 0,
            "rules": [],
            "message": (
                f"No genre patterns occur in at least {min_support:.0%} of the catalogue. "
                "Try a lower minimum support."
            ),
        }

    rules = association_rules(
        frequent, metric="confidence", min_threshold=min_confidence, num_itemsets=len(transactions)
    )
    if min_lift is not None:
        rules = rules[rules["lift"] >= min_lift]

    formatted = []
    for _, row in rules.iterrows():
        formatted.append(
            {
                "antecedent": ", ".join(sorted(row["antecedents"])),
                "consequent": ", ".join(sorted(row["consequents"])),
                "support": round(float(row["support"]), 4),
                "confidence": round(float(row["confidence"]), 4),
                "lift": round(float(row["lift"]), 4),
            }
        )
    formatted.sort(key=lambda rule: (-rule["lift"], -rule["confidence"], rule["antecedent"]))
    formatted = formatted[:MAX_RULES]

    return {
        "min_support": min_support,
        "min_confidence": min_confidence,
        "min_lift": min_lift,
        "transaction_count": int(len(transactions)),
        "frequent_itemset_count": int(len(frequent)),
        "rules": formatted,
        "message": None,
    }
