"""Analytics over the user's watched list: summary, genre stats, rating stats."""

from app.database.repositories import ImportRepository, MovieRepository, WatchedMovieRepository


def _watched_movies(conn, user_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT w.movie_id, w.user_rating, m.title, m.release_year, m.genres,
               m.vote_average, m.vote_count, m.popularity
        FROM watched_movies w
        JOIN movies m ON m.movie_id = w.movie_id
        WHERE w.user_id = ?
        ORDER BY w.movie_id
        """,
        (user_id,),
    ).fetchall()
    movies = [dict(row) for row in rows]
    MovieRepository.attach_genres(conn, movies)
    return movies


def _genre_counts(movies: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for movie in movies:
        for genre in movie.get("genre_list") or []:
            counts[genre] = counts.get(genre, 0) + 1
    return counts


def _most_common(counts: dict[str, int]) -> str | None:
    if not counts:
        return None
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _data_quality(conn, user_id: int) -> dict:
    return ImportRepository.quality_totals(conn, user_id)


def summary(conn, user_id: int) -> dict:
    movies = _watched_movies(conn, user_id)
    ratings = [movie["user_rating"] for movie in movies if movie["user_rating"] is not None]
    counts = _genre_counts(movies)
    total_assignments = sum(counts.values())
    percentages = {
        genre: round(count / total_assignments * 100, 2)
        for genre, count in sorted(counts.items())
    } if total_assignments else {}

    return {
        "movies_watched": len(movies),
        "unique_watched": len({movie["movie_id"] for movie in movies}),
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "rated_count": len(ratings),
        "unrated_count": len(movies) - len(ratings),
        "genre_counts": dict(sorted(counts.items())),
        "genre_percentages": percentages,
        "total_genre_assignments": total_assignments,
        "most_common_genre": _most_common(counts),
        "data_quality": _data_quality(conn, user_id),
    }


def genre_stats(conn, user_id: int) -> dict:
    movies = _watched_movies(conn, user_id)
    counts = _genre_counts(movies)
    total_assignments = sum(counts.values())

    rating_sums: dict[str, list[float]] = {}
    for movie in movies:
        if movie["user_rating"] is None:
            continue
        for genre in movie.get("genre_list") or []:
            rating_sums.setdefault(genre, []).append(movie["user_rating"])

    genres = []
    for genre, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        ratings = rating_sums.get(genre) or []
        genres.append(
            {
                "genre": genre,
                "count": count,
                "percentage": round(count / total_assignments * 100, 2) if total_assignments else 0.0,
                "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
            }
        )
    return {"genres": genres, "total_genre_assignments": total_assignments}


def rating_stats(conn, user_id: int) -> dict:
    movies = _watched_movies(conn, user_id)
    ratings = [movie["user_rating"] for movie in movies if movie["user_rating"] is not None]

    counts: dict[float, int] = {}
    for rating in ratings:
        counts[rating] = counts.get(rating, 0) + 1

    distribution = [
        {"rating": rating, "count": counts[rating]} for rating in sorted(counts)
    ]
    return {
        "distribution": distribution,
        "rated_count": len(ratings),
        "unrated_count": len(movies) - len(ratings),
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
    }
