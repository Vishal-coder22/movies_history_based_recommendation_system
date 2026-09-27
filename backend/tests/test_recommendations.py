from tests.helpers import register, watch_movies

# Watched: a heavy Action/Science Fiction/Drama profile.
WATCHED = [(5, 5), (9, 4.5), (3, 5), (16, 4), (6, 4.5)]
WATCHED_IDS = {movie_id for movie_id, _ in WATCHED}


def _watched_client(client, movies=WATCHED):
    headers = register(client)
    watch_movies(client, headers, movies)
    return headers


def test_recommendations_empty_history_has_message(client):
    headers = register(client)
    body = client.get("/api/recommendations", headers=headers).json()
    assert body["items"] == []
    assert body["total"] == 0
    assert "Watch a few movies first" in body["message"]


def test_recommendations_exclude_watched_and_rank_by_score(client):
    headers = _watched_client(client)
    body = client.get("/api/recommendations?limit=5", headers=headers).json()

    assert body["total"] == 20  # 25 fixture movies - 5 watched
    assert len(body["items"]) == 5
    ids = [item["movie_id"] for item in body["items"]]
    assert not WATCHED_IDS & set(ids), "watched movies must never be recommended"

    scores = [item["score"] for item in body["items"]]
    assert scores == sorted(scores, reverse=True)


def test_recommendations_reasons_use_real_signals(client):
    headers = _watched_client(client)
    items = client.get("/api/recommendations?limit=5", headers=headers).json()["items"]

    for item in items:
        assert item["reasons"], "every recommendation needs at least one reason"
        assert item["reason"] == ". ".join(item["reasons"]) + "."
        # The top items for this Action/Sci-Fi profile must match the profile.
        assert {"Action", "Science Fiction", "Drama"} & set(item["genre_list"])
        # Reason phrases must be backed by content, not placeholders.
        assert any(
            phrase in item["reason"]
            for phrase in ("Matches your taste", "pattern", "rated", "Audience rating")
        )


def test_recommendations_are_deterministic(client):
    headers = _watched_client(client)
    first = client.get("/api/recommendations?limit=5", headers=headers).json()["items"]
    second = client.get("/api/recommendations?limit=5", headers=headers).json()["items"]
    assert first == second


def test_recommendations_limit_is_clamped(client):
    headers = _watched_client(client)
    assert client.get("/api/recommendations?limit=500", headers=headers).json()["limit"] == 50
    assert client.get("/api/recommendations?limit=0", headers=headers).json()["limit"] == 1
    body = client.get("/api/recommendations?limit=3", headers=headers).json()
    assert len(body["items"]) == 3


def test_recommendations_persist_for_owner_only(client):
    headers = _watched_client(client)
    client.get("/api/recommendations?limit=5", headers=headers)

    from app.database.connection import connect
    from app.database.repositories import RecommendationRepository

    conn = connect()
    try:
        stored = RecommendationRepository.get_recent(conn, 1)
        other = RecommendationRepository.get_recent(conn, 2)
    finally:
        conn.close()
    assert len(stored) == 5
    assert all(item["reason"] for item in stored)
    assert other == []


def test_single_movie_explanation(client):
    headers = _watched_client(client)

    unwatched = client.get("/api/recommendations/8", headers=headers)  # Avatar
    assert unwatched.status_code == 200
    body = unwatched.json()
    assert body["title"] == "Avatar"
    assert body["is_watched"] is False
    assert body["score"] > 0
    assert body["reasons"]

    watched = client.get("/api/recommendations/5", headers=headers)
    assert watched.status_code == 200
    assert watched.json()["is_watched"] is True


def test_single_movie_missing_is_404(client):
    headers = _watched_client(client)
    response = client.get("/api/recommendations/999999", headers=headers)
    assert response.status_code == 404
    assert "find that movie" in response.json()["detail"]


def test_recommendations_require_authentication(client):
    assert client.get("/api/recommendations").status_code == 401
    assert client.get("/api/recommendations/5").status_code == 401
