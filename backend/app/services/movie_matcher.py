"""Match a raw uploaded title against the master catalogue.

Matching order (per spec):
1. Exact movie id, if provided.
2. Normalized exact title.
3. Case-insensitive / near-exact similarity.
4. Basic string similarity - never silently pick an ambiguous match.
"""

import difflib
import json

from app.services.table_reader import normalize_title

SIMILARITY_HIGH = 0.92
SIMILARITY_SINGLE = 0.75
SIMILARITY_LOW = 0.60
MAX_CANDIDATES = 10


def _similarity(query: str, title: str) -> float:
    score = difflib.SequenceMatcher(None, query, title).ratio()
    if query in title or title in query:
        score = max(score, 0.85)
    return score


def _candidate(movie: dict, score: float) -> dict:
    return {
        "movie_id": movie["movie_id"],
        "title": movie["title"],
        "release_year": movie["release_year"],
        "score": round(score, 3),
    }


def match_title(conn, raw_title: str | None, raw_movie_id: str | None = None) -> dict:
    """Return {'status', 'movie_id', 'candidates'} for one raw title."""
    # 1. Exact id, when the upload provides one.
    if raw_movie_id:
        try:
            movie_id = int(str(raw_movie_id).strip())
        except ValueError:
            movie_id = None
        if movie_id is not None:
            from app.database.repositories import MovieRepository

            movie = MovieRepository.get_by_id(conn, movie_id)
            if movie is not None:
                return {"status": "matched", "movie_id": movie_id, "candidates": []}

    from app.database.repositories import MovieRepository

    # 2. Normalized exact title.
    normalized = normalize_title(raw_title)
    if not normalized:
        return {"status": "unmatched", "movie_id": None, "candidates": []}

    exact = MovieRepository.find_by_normalized(conn, normalized)
    if len(exact) == 1:
        return {"status": "matched", "movie_id": exact[0]["movie_id"], "candidates": []}
    if len(exact) > 1:
        # Same title exists more than once (e.g. a remake): ask the user.
        candidates = [_candidate(movie, 1.0) for movie in exact[:MAX_CANDIDATES]]
        return {"status": "ambiguous", "movie_id": None, "candidates": candidates}

    # 3./4. Similarity scoring.
    candidates = MovieRepository.search_containing(conn, normalized)
    if not candidates:
        tokens = [token for token in normalized.split() if len(token) >= 3]
        if tokens:
            candidates = MovieRepository.search_by_tokens(conn, tokens)

    scored = sorted(
        ((_similarity(normalized, movie["normalized_title"]), movie) for movie in candidates),
        key=lambda pair: pair[0],
        reverse=True,
    )
    scored = [pair for pair in scored if pair[0] >= SIMILARITY_LOW]

    if not scored:
        return {"status": "unmatched", "movie_id": None, "candidates": []}

    best_score, best_movie = scored[0]
    if best_score >= SIMILARITY_HIGH:
        return {"status": "matched", "movie_id": best_movie["movie_id"], "candidates": []}
    if len(scored) == 1 and best_score >= SIMILARITY_SINGLE:
        return {"status": "matched", "movie_id": best_movie["movie_id"], "candidates": []}

    candidates_out = [_candidate(movie, score) for score, movie in scored[:MAX_CANDIDATES]]
    return {"status": "ambiguous", "movie_id": None, "candidates": candidates_out}


def candidates_json(candidates: list[dict]) -> str | None:
    return json.dumps(candidates) if candidates else None


def parse_candidates(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return []
