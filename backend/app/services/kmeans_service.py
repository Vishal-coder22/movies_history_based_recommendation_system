"""Movie-level K-Means clustering of a user's watched list.

The MVP clusters the user's watched *movies* (not users) because a single
account does not provide enough independent user rows for user-to-user
clustering - see backend spec section 13.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from app.errors import UserError

K_MIN, K_MAX, K_DEFAULT = 2, 6, 3
RANDOM_STATE = 42


def _watched_frame(conn, user_id: int) -> pd.DataFrame:
    rows = conn.execute(
        """
        SELECT w.movie_id, w.user_rating, m.title, m.genres, m.release_year,
               m.runtime, m.popularity, m.vote_average, m.vote_count
        FROM watched_movies w
        JOIN movies m ON m.movie_id = w.movie_id
        WHERE w.user_id = ?
        """,
        (user_id,),
    ).fetchall()
    return pd.DataFrame([dict(row) for row in rows])


def _genre_vocabulary(genres_series: pd.Series) -> list[str]:
    seen: set[str] = set()
    for cell in genres_series.fillna(""):
        for genre in str(cell).split("|"):
            genre = genre.strip()
            if genre:
                seen.add(genre)
    return sorted(seen)


def _build_features(frame: pd.DataFrame, vocabulary: list[str]) -> tuple[pd.DataFrame, list[str]]:
    numeric = frame[["release_year", "runtime", "popularity", "vote_average", "vote_count"]].apply(
        pd.to_numeric, errors="coerce"
    )
    genre_columns = {}
    for genre in vocabulary:
        genre_columns[f"genre_{genre}"] = (
            frame["genres"].fillna("").apply(lambda cell, g=genre: g in str(cell).split("|")).astype(float)
        )
    features = pd.concat([numeric, pd.DataFrame(genre_columns, index=frame.index)], axis=1)
    return features, list(features.columns)


def run_kmeans(conn, user_id: int, k: int = K_DEFAULT) -> dict:
    if not isinstance(k, int) or k < K_MIN or k > K_MAX:
        raise UserError(f"Choose a cluster count (K) between {K_MIN} and {K_MAX}.")

    frame = _watched_frame(conn, user_id)
    if len(frame) < k + 1:
        raise UserError(
            f"K-Means with K={k} needs at least {k + 1} watched movies for a reliable "
            f"silhouette score - you have {len(frame)}. Watch a few more movies first.",
            status_code=400,
        )

    vocabulary = _genre_vocabulary(frame["genres"])
    features, feature_names = _build_features(frame, vocabulary)

    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    matrix = scaler.fit_transform(imputer.fit_transform(features))

    model = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
    labels = model.fit_predict(matrix)
    score = float(silhouette_score(matrix, labels))

    frame = frame.copy()
    frame["cluster_id"] = labels

    assignments = [
        {"movie_id": int(row.movie_id), "title": row.title, "cluster_id": int(row.cluster_id)}
        for row in frame.itertuples()
    ]

    profiles = []
    for cluster_id in sorted(int(c) for c in frame["cluster_id"].unique()):
        members = frame[frame["cluster_id"] == cluster_id]
        genre_counts: dict[str, int] = {}
        for cell in members["genres"].fillna(""):
            for genre in str(cell).split("|"):
                genre = genre.strip()
                if genre:
                    genre_counts[genre] = genre_counts.get(genre, 0) + 1
        dominant = sorted(genre_counts.items(), key=lambda item: (-item[1], item[0]))
        ratings = members["user_rating"].dropna()
        profiles.append(
            {
                "cluster_id": cluster_id,
                "cluster_size": int(len(members)),
                "average_rating": round(float(ratings.mean()), 2) if len(ratings) else None,
                "average_movies_watched": None,
                "dominant_genre": dominant[0][0] if dominant else None,
                "silhouette_score": round(score, 4),
            }
        )

    return {
        "k": k,
        "feature_names": feature_names,
        "movie_count": int(len(frame)),
        "silhouette_score": round(score, 4),
        "assignments": assignments,
        "profiles": profiles,
    }
