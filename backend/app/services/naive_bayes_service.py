"""Naive Bayes genre preference prediction.

One binary GaussianNB per genre, trained on the master catalogue's real
labels (movie -> genre) with a stratified holdout for honest metrics. The
user's feature vector is the mean profile of their watched movies; the
predicted probability is how likely a movie of that profile belongs to the
genre. No probabilities are ever invented - genres with too little data to
hold out are simply not modelled.
"""

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB

from app.errors import UserError

RANDOM_STATE = 42
TEST_SIZE = 0.25
MIN_POSITIVES = 4
MIN_TRAINING_ROWS = 20
FEATURE_COLUMNS = ["release_year", "runtime", "popularity", "vote_average", "vote_count"]


def _catalogue(conn) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (features frame, one-hot genre labels frame) aligned by row."""
    movies = pd.read_sql_query(
        f"SELECT movie_id, {', '.join(FEATURE_COLUMNS)} FROM movies", conn
    )
    labels = pd.read_sql_query(
        "SELECT movie_id, genre FROM movie_genres", conn
    )
    genres = sorted(labels["genre"].unique()) if len(labels) else []
    matrix = pd.DataFrame(
        {
            genre: movies["movie_id"].isin(
                labels.loc[labels["genre"] == genre, "movie_id"]
            ).astype(int)
            for genre in genres
        }
    )
    features = movies[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    return features, matrix


def _user_vector(conn, user_id: int, imputer: SimpleImputer) -> np.ndarray | None:
    rows = conn.execute(
        f"SELECT {', '.join(FEATURE_COLUMNS)} FROM watched_movies w "
        "JOIN movies m ON m.movie_id = w.movie_id WHERE w.user_id = ?",
        (user_id,),
    ).fetchall()
    if not rows:
        return None
    frame = pd.DataFrame([dict(row) for row in rows], columns=FEATURE_COLUMNS)
    frame = frame.apply(pd.to_numeric, errors="coerce")
    return imputer.transform(frame.mean().to_frame().T)[0]


def run_naive_bayes(conn, user_id: int) -> dict:
    features, labels = _catalogue(conn)
    if len(features) < MIN_TRAINING_ROWS:
        raise UserError(
            f"Naive Bayes needs at least {MIN_TRAINING_ROWS} catalogue movies to train - "
            f"the catalogue has {len(features)}."
        )

    imputer = SimpleImputer(strategy="median")
    X = imputer.fit_transform(features)

    user_vector = _user_vector(conn, user_id, imputer)
    if user_vector is None:
        raise UserError(
            "Watch at least one movie before running Naive Bayes - your watched list "
            "is the feature vector we predict with."
        )

    probabilities = []
    metrics = []
    modelled_genres = 0

    for genre in labels.columns:
        y = labels[genre].to_numpy()
        positives = int(y.sum())
        negatives = int(len(y) - positives)
        if positives < MIN_POSITIVES or negatives < MIN_POSITIVES:
            continue

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
        )
        holdout = GaussianNB()
        holdout.fit(X_train, y_train)
        predicted = holdout.predict(X_test)
        metrics.append(
            {
                "genre": genre,
                "accuracy": round(float(accuracy_score(y_test, predicted)), 4),
                "precision": round(float(precision_score(y_test, predicted, zero_division=0)), 4),
                "recall": round(float(recall_score(y_test, predicted, zero_division=0)), 4),
                "f1": round(float(f1_score(y_test, predicted, zero_division=0)), 4),
                "positive_movies": positives,
                "holdout_size": int(len(y_test)),
            }
        )

        model = GaussianNB()
        model.fit(X, y)
        probability = float(model.predict_proba(user_vector.reshape(1, -1))[0][1])
        probabilities.append({"genre": genre, "probability": round(probability, 4)})
        modelled_genres += 1

    if modelled_genres == 0:
        raise UserError(
            "No genre has enough labelled movies in the catalogue to model. "
            "Import a larger catalogue first."
        )

    probabilities.sort(key=lambda item: (-item["probability"], item["genre"]))
    metrics.sort(key=lambda item: item["genre"])

    return {
        "features": FEATURE_COLUMNS,
        "trained_movies": int(len(features)),
        "user_movies": int(
            conn.execute(
                "SELECT COUNT(*) FROM watched_movies WHERE user_id = ?", (user_id,)
            ).fetchone()[0]
        ),
        "modelled_genres": modelled_genres,
        "probabilities": probabilities,
        "metrics": metrics,
    }
