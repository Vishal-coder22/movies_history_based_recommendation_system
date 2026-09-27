"""Shared helpers for turning tabular input (CSV / PDF) into raw records."""

import re


def normalize_column(name) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(name or "").strip().lower())


def normalize_title(title) -> str:
    return " ".join(str(title or "").lower().split())


_MOVIE_EXACT = {"movie", "title", "film", "name", "movietitle", "filmtitle", "moviename"}
_RATING_EXACT = {"rating", "rate", "score", "stars", "star", "myrating", "userrating", "personalrating"}
_ID_EXACT = {"movieid", "id", "tmdbid", "tmdb"}


def detect_columns(columns) -> dict:
    """Map detected columns: {'movie': col|None, 'rating': col|None, 'movie_id': col|None}.

    Exact header matches always win over keyword matches, so a 'Movie ID'
    column can never shadow a real 'Title' column.
    """
    normalized = {col: normalize_column(col) for col in columns}
    taken: set = set()

    def pick(exact: set[str], keywords: tuple[str, ...] | None):
        for col, value in normalized.items():
            if col not in taken and value in exact:
                taken.add(col)
                return col
        if keywords is None:
            return None
        for col, value in normalized.items():
            if col not in taken and any(keyword in value for keyword in keywords):
                taken.add(col)
                return col
        return None

    movie_id = pick(_ID_EXACT, None)
    movie = pick(_MOVIE_EXACT, ("movie", "title", "film"))
    rating = pick(_RATING_EXACT, ("rating",))

    if movie is not None and rating == movie:
        rating = None

    return {"movie": movie, "rating": rating, "movie_id": movie_id}


def rating_values_are_usable(values: list) -> bool:
    """True when at least one non-empty value parses as a number."""
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        try:
            float(text)
            return True
        except ValueError:
            continue
    return False


def build_records(rows: list[list], movie_idx: int, rating_idx: int | None, id_idx: int | None) -> list[dict]:
    records = []
    for row in rows:
        def cell(index):
            if index is None or index >= len(row):
                return None
            value = row[index]
            if value is None:
                return None
            text = str(value).strip()
            return text or None

        records.append(
            {
                "raw_movie_title": cell(movie_idx),
                "raw_rating": cell(rating_idx),
                "raw_movie_id": cell(id_idx),
            }
        )
    return records
