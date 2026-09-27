from tests.helpers import register, watch_movies

# A 12-movie watched list spanning several genres (fixture ids).
WATCHED = [
    (1, 5), (2, 4.5), (3, 5), (4, 3.5), (5, 4), (6, 4.5),
    (7, 4), (9, 5), (11, 3.5), (13, 4), (17, 4.5), (21, 3),
]


def _watched_client(client, movies=WATCHED):
    headers = register(client)
    watch_movies(client, headers, movies)
    return headers


def test_kmeans_returns_profiles_and_silhouette(client):
    headers = _watched_client(client)
    response = client.post("/api/mining/kmeans", json={"k": 3}, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["run_id"] > 0
    assert body["k"] == 3
    assert body["movie_count"] == 12
    assert -1.0 <= body["silhouette_score"] <= 1.0

    assert len(body["profiles"]) == 3
    assert sum(p["cluster_size"] for p in body["profiles"]) == 12
    for profile in body["profiles"]:
        assert profile["dominant_genre"]
        assert profile["cluster_size"] >= 1

    assert len(body["assignments"]) == 12
    assert {a["movie_id"] for a in body["assignments"]} == {m for m, _ in WATCHED}


def test_kmeans_is_deterministic(client):
    headers = _watched_client(client)
    first = client.post("/api/mining/kmeans", json={"k": 3}, headers=headers).json()
    second = client.post("/api/mining/kmeans", json={"k": 3}, headers=headers).json()
    assert first["silhouette_score"] == second["silhouette_score"]
    assert first["assignments"] == second["assignments"]


def test_kmeans_rejects_k_out_of_range(client):
    headers = _watched_client(client)
    for k in (1, 7, 0):
        response = client.post("/api/mining/kmeans", json={"k": k}, headers=headers)
        assert response.status_code == 400, response.text
        assert "between 2 and 6" in response.json()["detail"]


def test_kmeans_requires_enough_movies(client):
    headers = _watched_client(client, movies=[(1, 5), (3, 4)])
    response = client.post("/api/mining/kmeans", json={"k": 3}, headers=headers)
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "at least 4 watched movies" in detail
    assert "you have 2" in detail


def test_apriori_returns_rules_with_real_metrics(client):
    headers = register(client)
    response = client.post(
        "/api/mining/apriori",
        json={"min_support": 0.1, "min_confidence": 0.3},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["transaction_count"] == 25  # fixture catalogue size
    assert body["frequent_itemset_count"] > 0
    assert len(body["rules"]) > 0

    for rule in body["rules"][:5]:
        assert rule["antecedent"]
        assert rule["consequent"]
        assert rule["antecedent"] != rule["consequent"]
        assert 0 < rule["support"] <= 1
        assert 0 < rule["confidence"] <= 1
        assert rule["lift"] > 0

    lifts = [rule["lift"] for rule in body["rules"]]
    assert lifts == sorted(lifts, reverse=True)


def test_apriori_min_lift_filters_rules(client):
    headers = register(client)
    response = client.post(
        "/api/mining/apriori",
        json={"min_support": 0.1, "min_confidence": 0.3, "min_lift": 1.5},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    for rule in response.json()["rules"]:
        assert rule["lift"] >= 1.5


def test_apriori_rejects_bad_parameters(client):
    headers = register(client)
    for body in (
        {"min_support": 0},
        {"min_support": 1.5},
        {"min_confidence": 0},
        {"min_confidence": 2},
        {"min_lift": -1},
    ):
        response = client.post("/api/mining/apriori", json=body, headers=headers)
        assert response.status_code == 400, f"{body} -> {response.text}"
        assert response.json()["detail"]


def test_apriori_high_support_gives_honest_message(client):
    headers = register(client)
    response = client.post(
        "/api/mining/apriori", json={"min_support": 0.99}, headers=headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["rules"] == []
    assert "lower minimum support" in body["message"]


def test_naive_bayes_returns_probabilities_and_holdout_metrics(client):
    headers = _watched_client(client)
    response = client.post("/api/mining/naive-bayes", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["run_id"] > 0
    assert body["trained_movies"] == 25
    assert body["user_movies"] == 12
    assert body["modelled_genres"] >= 1

    probabilities = body["probabilities"]
    assert len(probabilities) == body["modelled_genres"]
    values = [p["probability"] for p in probabilities]
    assert values == sorted(values, reverse=True)
    for item in probabilities:
        assert 0.0 <= item["probability"] <= 1.0

    assert len(body["metrics"]) == body["modelled_genres"]
    for metric in body["metrics"]:
        assert 0.0 <= metric["accuracy"] <= 1.0
        assert 0.0 <= metric["precision"] <= 1.0
        assert 0.0 <= metric["recall"] <= 1.0
        assert metric["positive_movies"] >= 4
        assert metric["holdout_size"] > 0


def test_naive_bayes_requires_watched_movies(client):
    headers = register(client)
    response = client.post("/api/mining/naive-bayes", headers=headers)
    assert response.status_code == 400
    assert "Watch at least one movie" in response.json()["detail"]


def test_mining_requires_authentication(client):
    assert client.post("/api/mining/kmeans", json={"k": 3}).status_code == 401
    assert client.post("/api/mining/apriori", json={}).status_code == 401
    assert client.post("/api/mining/naive-bayes").status_code == 401
    assert client.get("/api/mining/runs").status_code == 401


def test_mining_runs_are_listed_per_user(client):
    headers = _watched_client(client)
    client.post("/api/mining/kmeans", json={"k": 2}, headers=headers)
    client.post("/api/mining/apriori", json={"min_support": 0.2}, headers=headers)
    client.post("/api/mining/naive-bayes", headers=headers)

    runs = client.get("/api/mining/runs", headers=headers).json()["runs"]
    assert len(runs) == 3
    assert {run["algorithm"] for run in runs} == {"kmeans", "apriori", "naive_bayes"}
    by_algorithm = {run["algorithm"]: run for run in runs}
    assert by_algorithm["kmeans"]["parameters"]["k"] == 2
    assert "silhouette_score" in by_algorithm["kmeans"]["metrics"]
    assert by_algorithm["naive_bayes"]["metrics"]["trained_movies"] == 25

    # A second user sees only their own (empty) run history.
    other = register(client, name="Other", email="other@example.com")
    assert client.get("/api/mining/runs", headers=other).json()["runs"] == []
