PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS movies (
    movie_id         INTEGER PRIMARY KEY,
    title            TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    release_year     INTEGER,
    genres           TEXT,
    overview         TEXT,
    runtime          REAL,
    popularity       REAL,
    vote_average     REAL,
    vote_count       INTEGER
);

CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title);
CREATE INDEX IF NOT EXISTS idx_movies_normalized ON movies(normalized_title);
CREATE INDEX IF NOT EXISTS idx_movies_year ON movies(release_year);

CREATE TABLE IF NOT EXISTS movie_genres (
    movie_id INTEGER NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    genre    TEXT NOT NULL,
    PRIMARY KEY (movie_id, genre)
);

CREATE INDEX IF NOT EXISTS idx_movie_genres_genre ON movie_genres(genre);

CREATE TABLE IF NOT EXISTS watched_movies (
    watched_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    movie_id   INTEGER NOT NULL REFERENCES movies(movie_id),
    user_rating REAL CHECK (user_rating IS NULL OR (user_rating >= 0 AND user_rating <= 5)),
    source     TEXT NOT NULL CHECK (source IN ('csv', 'pdf', 'manual')),
    added_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, movie_id)
);

CREATE TABLE IF NOT EXISTS import_runs (
    import_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    file_name  TEXT NOT NULL,
    file_type  TEXT NOT NULL CHECK (file_type IN ('csv', 'pdf')),
    status     TEXT NOT NULL DEFAULT 'uploaded',
    total_rows INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS import_records (
    record_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    import_id        INTEGER NOT NULL REFERENCES import_runs(import_id) ON DELETE CASCADE,
    raw_movie_title  TEXT,
    raw_rating       REAL,
    normalized_title TEXT,
    matched_movie_id INTEGER REFERENCES movies(movie_id),
    match_status     TEXT NOT NULL DEFAULT 'pending'
        CHECK (match_status IN ('pending', 'matched', 'ambiguous', 'unmatched', 'skipped')),
    match_candidates TEXT,
    is_duplicate     INTEGER NOT NULL DEFAULT 0,
    is_valid         INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_import_records_import ON import_records(import_id);

CREATE TABLE IF NOT EXISTS data_quality_reports (
    report_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    import_id         INTEGER NOT NULL REFERENCES import_runs(import_id) ON DELETE CASCADE,
    original_rows     INTEGER NOT NULL,
    duplicate_rows    INTEGER NOT NULL,
    missing_movie_rows INTEGER NOT NULL,
    invalid_rows      INTEGER NOT NULL,
    matched_rows      INTEGER NOT NULL,
    ambiguous_rows    INTEGER NOT NULL,
    unmatched_rows    INTEGER NOT NULL,
    final_rows        INTEGER NOT NULL,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS mining_runs (
    run_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    algorithm      TEXT NOT NULL CHECK (algorithm IN ('kmeans', 'apriori', 'naive_bayes')),
    parameters_json TEXT,
    metrics_json   TEXT,
    status         TEXT NOT NULL DEFAULT 'completed',
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS kmeans_results (
    result_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     INTEGER NOT NULL REFERENCES mining_runs(run_id) ON DELETE CASCADE,
    movie_id   INTEGER NOT NULL REFERENCES movies(movie_id),
    cluster_id INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_kmeans_run ON kmeans_results(run_id);

CREATE TABLE IF NOT EXISTS cluster_profiles (
    profile_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id                 INTEGER NOT NULL REFERENCES mining_runs(run_id) ON DELETE CASCADE,
    cluster_id             INTEGER NOT NULL,
    cluster_size           INTEGER NOT NULL,
    average_rating         REAL,
    average_movies_watched REAL,
    dominant_genre         TEXT,
    silhouette_score       REAL
);

CREATE TABLE IF NOT EXISTS apriori_rules (
    rule_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER NOT NULL REFERENCES mining_runs(run_id) ON DELETE CASCADE,
    antecedent  TEXT NOT NULL,
    consequent  TEXT NOT NULL,
    support     REAL NOT NULL,
    confidence  REAL NOT NULL,
    lift        REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_apriori_run ON apriori_rules(run_id);

CREATE TABLE IF NOT EXISTS naive_bayes_results (
    result_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER NOT NULL REFERENCES mining_runs(run_id) ON DELETE CASCADE,
    genre       TEXT NOT NULL,
    probability REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_nb_run ON naive_bayes_results(run_id);

CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    movie_id          INTEGER NOT NULL REFERENCES movies(movie_id),
    score             REAL NOT NULL,
    reason            TEXT NOT NULL,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, movie_id)
);
