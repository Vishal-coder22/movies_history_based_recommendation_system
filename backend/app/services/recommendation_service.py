"""Scored movie recommendations with signal-based explanations.

Pipeline (backend spec section 16):
candidates -> drop watched -> genre affinity -> association strength ->
quality signal -> score -> top N -> explanation.

Every explanation phrase maps to a real component of the score; nothing is
fabricated.
"""

import math

from app.database.repositories import MovieRepository, WatchedMovieRepository
from app.services.apriori_service import DEFAULT_MIN_CONFIDENCE, DEFAULT_MIN_SUPPORT, genre_transactions

DEFAULT_LIMIT = 10
MAX_LIMIT = 50

GENRE_WEIGHT = 2.0
ASSOCIATION_WEIGHT = 1.5
QUALITY_WEIGHT = 1.0

HIGH_RATING = 8.0

SCORE_WEIGHTS = {
    "genre_affinity": GENRE_WEIGHT,
    "association": ASSOCIATION_WEIGHT,
    "quality": QUALITY_WEIGHT,
}


def _genre_profile(conn, user_id: int) -> tuple[dict[str, float], dict[str, int]]:
    """Return (share per genre, raw count per genre) across watched movies."""
    movies = []
    watched_ids = WatchedMovieRepository.get_movie_ids(conn, user_id)
    if watched_ids:
        rows = conn.execute(
            "SELECT movie_id FROM watched_movies WHERE user_id = ?", (user_id,)
        ).fetchall()
        movies = [{"movie_id": row["movie_id"]} for row in rows]
        MovieRepository.attach_genres(conn, movies)

    counts: dict[str, int] = {}
    for movie in movies:
        for genre in movie.get("genre_list") or []:
            counts[genre] = counts.get(genre, 0) + 1
    total = sum(counts.values())
    shares = {genre: count / total for genre, count in counts.items()} if total else {}
    return shares, counts


def _catalogue_rules(conn) -> list[dict]:
    """Fresh catalogue association rules (same defaults as the Apriori endpoint)."""
    from mlxtend.frequent_patterns import apriori, association_rules

    transactions = genre_transactions(conn)
    if len(transactions) == 0:
        return []
    frequent = apriori(transactions, min_support=DEFAULT_MIN_SUPPORT, use_colnames=True)
    if frequent.empty:
        return []
    rules = association_rules(
        frequent, metric="confidence", min_threshold=DEFAULT_MIN_CONFIDENCE,
        num_itemsets=len(transactions),
    )
    return [
        {
            "antecedents": frozenset(row["antecedents"]),
            "consequents": frozenset(row["consequents"]),
            "confidence": float(row["confidence"]),
            "lift": float(row["lift"]),
        }
        for _, row in rules.iterrows()
    ]


def _quality(movie: dict) -> float:
    vote_average = float(movie.get("vote_average") or 0.0)
    vote_count = float(movie.get("vote_count") or 0.0)
    popularity = min(1.0, math.log10(1.0 + vote_count) / 4.5)
    return 0.7 * (vote_average / 10.0) + 0.3 * popularity


def _score_movie(
    movie: dict,
    shares: dict[str, float],
    counts: dict[str, int],
    rules: list[dict],
) -> tuple[float, list[str]]:
    genres = movie.get("genre_list") or []
    user_genres = set(shares)

    matched = [genre for genre in genres if genre in shares]
    affinity = sum(shares[genre] for genre in matched) / len(genres) if genres else 0.0

    best_rule = None
    best_contribution = 0.0
    if matched:
        matched_set = set(matched)
        for rule in rules:
            consequent = next(iter(rule["consequents"]), None)
            if len(rule["consequents"]) != 1 or consequent not in matched_set:
                continue
            if not rule["antecedents"] or not rule["antecedents"] <= user_genres:
                continue
            antecedent_shares = [shares[g] for g in rule["antecedents"]]
            contribution = (
                rule["lift"] * rule["confidence"] * (sum(antecedent_shares) / len(antecedent_shares))
            )
            if contribution > best_contribution:
                best_contribution = contribution
                best_rule = rule
    association = best_contribution
    quality = _quality(movie)

    score = GENRE_WEIGHT * affinity + ASSOCIATION_WEIGHT * association + QUALITY_WEIGHT * quality

    reasons = []
    if matched:
        top = sorted(matched, key=lambda genre: (-shares[genre], genre))[:2]
        reasons.append("Matches your taste in " + " and ".join(top))
    if best_rule is not None:
        antecedent = ", ".join(sorted(best_rule["antecedents"]))
        consequent = ", ".join(sorted(best_rule["consequents"]))
        reasons.append(
            f"Connected to the {antecedent} → {consequent} pattern "
            f"(lift {best_rule['lift']:.1f})"
        )
    vote_average = float(movie.get("vote_average") or 0.0)
    if vote_average >= HIGH_RATING:
        reasons.append(f"Highly rated by audiences ({vote_average:g}/10)")
    elif not reasons:
        reasons.append(f"Audience rating {vote_average:g}/10")
    return score, reasons


def recommend(conn, user_id: int, limit: int = DEFAULT_LIMIT) -> dict:
    shares, counts = _genre_profile(conn, user_id)
    watched = WatchedMovieRepository.get_movie_ids(conn, user_id)

    if not watched:
        return {
            "items": [],
            "total": 0,
            "limit": limit,
            "message": "Watch a few movies first - recommendations are built from your watched list.",
            "weights": SCORE_WEIGHTS,
        }

    rules = _catalogue_rules(conn)
    candidates = MovieRepository.get_all(conn)
    MovieRepository.attach_genres(conn, candidates)

    scored = []
    for movie in candidates:
        if movie["movie_id"] in watched:
            continue
        score, reasons = _score_movie(movie, shares, counts, rules)
        scored.append((score, movie, reasons))

    scored.sort(key=lambda entry: (-entry[0], entry[1]["movie_id"]))
    top = scored[:limit]

    items = [
        {
            "movie_id": movie["movie_id"],
            "title": movie["title"],
            "release_year": movie["release_year"],
            "genre_list": movie.get("genre_list") or [],
            "vote_average": movie.get("vote_average"),
            "score": round(score, 4),
            "reason": ". ".join(reasons) + ".",
            "reasons": reasons,
        }
        for score, movie, reasons in top
    ]

    from app.database.repositories import RecommendationRepository

    RecommendationRepository.replace(conn, user_id, items)

    return {
        "items": items,
        "total": len(scored),
        "limit": limit,
        "message": None,
        "weights": SCORE_WEIGHTS,
    }


def explain(conn, user_id: int, movie_id: int) -> dict:
    movie = MovieRepository.get_by_id(conn, movie_id)
    if movie is None:
        from app.errors import UserError

        raise UserError("We couldn't find that movie.", status_code=404)

    shares, counts = _genre_profile(conn, user_id)
    rules = _catalogue_rules(conn) if shares else []
    MovieRepository.attach_genres(conn, [movie])

    score, reasons = _score_movie(movie, shares, counts, rules)
    return {
        "movie_id": movie["movie_id"],
        "title": movie["title"],
        "genre_list": movie.get("genre_list") or [],
        "vote_average": movie.get("vote_average"),
        "score": round(score, 4),
        "reason": ". ".join(reasons) + ".",
        "reasons": reasons,
        "is_watched": movie_id in WatchedMovieRepository.get_movie_ids(conn, user_id),
    }
