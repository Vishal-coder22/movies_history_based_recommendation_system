from tests.helpers import register, upload_csv, watch_movies

# Watched set used by most analytics tests (fixture catalogue ids/genres):
#   1  The Shawshank Redemption  Drama                  rated 5
#   3  The Dark Knight           Action|Crime|Drama    rated 4.5
#   5  Inception                 Action|Science Fiction rated 4
#   7  Titanic                   Drama|Romance         unrated
#   11 Toy Story                 Animation|Family      rated 3.5
WATCHED = [(1, 5), (3, 4.5), (5, 4), (7, None), (11, 3.5)]


def _watch(client):
    headers = register(client)
    watch_movies(client, headers, WATCHED)
    return headers


def test_summary_counts_genres_and_ratings(client):
    headers = _watch(client)
    body = client.get("/api/analytics/summary", headers=headers).json()

    assert body["movies_watched"] == 5
    assert body["unique_watched"] == 5
    assert body["rated_count"] == 4
    assert body["unrated_count"] == 1
    assert body["average_rating"] == 4.25  # (5 + 4.5 + 4 + 3.5) / 4
    assert body["most_common_genre"] == "Drama"
    assert body["genre_counts"] == {
        "Action": 2,
        "Animation": 1,
        "Crime": 1,
        "Drama": 3,
        "Family": 1,
        "Romance": 1,
        "Science Fiction": 1,
    }
    # 10 genre assignments across 5 movies; Drama = 3/10
    assert body["total_genre_assignments"] == 10
    assert body["genre_percentages"]["Drama"] == 30.0
    assert body["genre_percentages"]["Action"] == 20.0
    assert round(sum(body["genre_percentages"].values()), 1) == 100.0


def test_summary_empty_history_is_neutral(client):
    headers = register(client)
    body = client.get("/api/analytics/summary", headers=headers).json()

    assert body["movies_watched"] == 0
    assert body["average_rating"] is None
    assert body["most_common_genre"] is None
    assert body["genre_counts"] == {}
    assert body["data_quality"]["imports"] == 0
    assert body["data_quality"]["duplicates_removed"] == 0


def test_summary_includes_data_quality(client):
    headers = register(client)
    upload = upload_csv(
        client,
        headers,
        "Movie,Rating\nInception,5\nInception,5\n,3\nInterstellar,99\nTitanic,\n",
    )
    import_id = upload.json()["import_id"]
    clean = client.post(f"/api/imports/{import_id}/clean", headers=headers)
    assert clean.status_code == 200, clean.text

    quality = client.get("/api/analytics/summary", headers=headers).json()["data_quality"]
    assert quality["imports"] == 1
    assert quality["duplicates_removed"] == 1
    assert quality["missing_values"] == 1  # blank title
    assert quality["invalid_rows"] == 1  # rating 99 out of range


def test_genres_endpoint_ranks_and_averages(client):
    headers = _watch(client)
    body = client.get("/api/analytics/genres", headers=headers).json()

    genres = body["genres"]
    assert genres[0]["genre"] == "Drama"
    assert genres[0]["count"] == 3
    assert genres[0]["percentage"] == 30.0
    # Drama ratings: 5 (Shawshank), 4.5 (Dark Knight); Titanic is unrated
    assert genres[0]["average_rating"] == 4.75
    assert body["total_genre_assignments"] == 10
    counts = [genre["count"] for genre in genres]
    assert counts == sorted(counts, reverse=True)


def test_ratings_endpoint_distribution(client):
    headers = _watch(client)
    body = client.get("/api/analytics/ratings", headers=headers).json()

    assert body["rated_count"] == 4
    assert body["unrated_count"] == 1
    assert body["average_rating"] == 4.25
    assert body["distribution"] == [
        {"rating": 3.5, "count": 1},
        {"rating": 4.0, "count": 1},
        {"rating": 4.5, "count": 1},
        {"rating": 5.0, "count": 1},
    ]


def test_analytics_require_authentication(client):
    assert client.get("/api/analytics/summary").status_code == 401
    assert client.get("/api/analytics/genres").status_code == 401
    assert client.get("/api/analytics/ratings").status_code == 401
