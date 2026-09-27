from tests.helpers import register


def test_list_movies(client):
    headers = register(client)
    response = client.get("/api/movies?limit=5", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 25
    assert len(body["items"]) == 5
    first = body["items"][0]
    assert "genre_list" in first
    assert first["is_watched"] is False


def test_list_movies_requires_auth(client):
    assert client.get("/api/movies").status_code == 401


def test_genre_filter(client):
    headers = register(client)
    response = client.get("/api/movies?genre=Horror", headers=headers)
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Get Out"


def test_min_rating_filter(client):
    headers = register(client)
    response = client.get("/api/movies?min_rating=8.5", headers=headers)
    assert response.json()["total"] == 10


def test_search_by_query(client):
    headers = register(client)
    response = client.get("/api/movies/search?q=dark", headers=headers)
    body = response.json()
    assert body["total"] == 2
    assert {m["title"] for m in body["items"]} == {"The Dark Knight", "The Dark Knight Rises"}


def test_search_single_match(client):
    headers = register(client)
    body = client.get("/api/movies/search?q=inception", headers=headers).json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Inception"


def test_genre_names_endpoint(client):
    headers = register(client)
    genres = client.get("/api/movies/genres", headers=headers).json()["genres"]
    assert "Horror" in genres
    assert "Science Fiction" in genres
    assert genres == sorted(genres)


def test_movie_detail(client):
    headers = register(client)
    response = client.get("/api/movies/3", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "The Dark Knight"
    assert body["genre_list"] == ["Action", "Crime", "Drama"]
    assert body["is_watched"] is False

    missing = client.get("/api/movies/999999", headers=headers)
    assert missing.status_code == 404


def test_manual_add_and_rating_validation(client):
    headers = register(client)

    added = client.post("/api/movies/3/watched", json={"rating": 4.5}, headers=headers)
    assert added.status_code == 200, added.text
    assert added.json()["added"] is True

    detail = client.get("/api/movies/3", headers=headers).json()
    assert detail["is_watched"] is True
    assert detail["user_rating"] == 4.5

    readd = client.post("/api/movies/3/watched", json={"rating": 5}, headers=headers)
    assert readd.json()["added"] is False
    assert readd.json()["updated"] is True
    assert client.get("/api/movies/3", headers=headers).json()["user_rating"] == 5

    too_high = client.post("/api/movies/3/watched", json={"rating": 7}, headers=headers)
    assert too_high.status_code == 400
    assert "between" in too_high.json()["detail"]

    negative = client.post("/api/movies/3/watched", json={"rating": -1}, headers=headers)
    assert negative.status_code == 400

    no_rating = client.post("/api/movies/999999/watched", json={"rating": 4}, headers=headers)
    assert no_rating.status_code == 404
