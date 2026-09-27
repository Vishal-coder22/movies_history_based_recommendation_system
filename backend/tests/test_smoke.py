import csv

import pytest


def test_health_reports_seeded_catalogue(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["master_movies"] == 25


def test_catalogue_seeded_with_fixture_movies(db):
    from app.database.repositories import MovieRepository

    assert MovieRepository.count(db) == 25
    movie = MovieRepository.get_by_id(db, 3)
    assert movie["title"] == "The Dark Knight"
    assert set(MovieRepository.get_genres(db, 3)) == {"Action", "Crime", "Drama"}


def test_seed_is_idempotent(db):
    from app.database.seed import seed_movies

    assert seed_movies() == 0

    from app.database.repositories import MovieRepository

    assert MovieRepository.count(db) == 25


def test_master_dataset_above_cap_is_rejected(tmp_path):
    big_csv = tmp_path / "too_big.csv"
    header = [
        "movie_id", "title", "release_year", "genres",
        "overview", "runtime", "popularity", "vote_average", "vote_count",
    ]
    with open(big_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for i in range(1, 5002):
            writer.writerow([i, f"Movie {i}", 2000, "Drama", "", 100, 1.0, 5.0, 10])

    from app.database.seed import read_catalogue

    with pytest.raises(ValueError, match="maximum allowed"):
        read_catalogue(str(big_csv))
