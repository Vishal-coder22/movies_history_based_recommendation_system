"""Full user journey: register -> upload -> clean -> resolve -> confirm ->
analytics -> mining -> recommendations.

One test per journey stage group so a failure pinpoints the broken link.
"""

from tests.helpers import register, upload_csv

# The messy history used across the journey (fixture ids: Inception=5,
# The Dark Knight=3, The Dark Knight Rises=4, Titanic=7, Interstellar=6,
# The Matrix=9, Joker=20).
JOURNEY_CSV = """Movie,Rating
Inception,5
The Matrix,4.5
The Dark Knight,5
Joker,4
dark knight,
Interstellar,4.5
Zzz Missing Film,3
,4
Inception,5
"""


def _import_and_clean(client, headers):
    upload = upload_csv(client, headers, JOURNEY_CSV)
    assert upload.status_code == 200, upload.text
    import_id = upload.json()["import_id"]

    clean = client.post(f"/api/imports/{import_id}/clean", headers=headers)
    assert clean.status_code == 200, clean.text
    return import_id, clean.json()


def _import_and_confirm(client, headers):
    """Clean, resolve every pending decision, then confirm. Returns inserted count."""
    import_id, clean = _import_and_clean(client, headers)
    decisions = [{"record_id": clean["ambiguous"][0]["record_id"], "movie_id": 4},
                 {"record_id": clean["unmatched"][0]["record_id"], "movie_id": None}]
    resolved = client.post(
        f"/api/imports/{import_id}/confirm-matches",
        json={"decisions": decisions},
        headers=headers,
    )
    assert resolved.status_code == 200, resolved.text
    confirmed = client.post(f"/api/imports/{import_id}/confirm", headers=headers)
    assert confirmed.status_code == 200, confirmed.text
    return import_id, confirmed.json()


def test_full_journey_happy_path(client):
    headers = register(client)

    # --- Stage 1: upload + clean -------------------------------
    import_id, clean = _import_and_clean(client, headers)
    assert clean["report"] == {
        "original_rows": 9,
        "duplicate_rows": 1,
        "missing_movie_rows": 1,
        "invalid_rows": 0,
        "matched_rows": 5,
        "ambiguous_rows": 1,
        "unmatched_rows": 1,
        "final_rows": 5,
    }
    assert clean["status"] == "awaiting_match"
    assert clean["ambiguous"][0]["raw_movie_title"] == "dark knight"

    # --- Stage 2: resolve ambiguity, confirm --------------------
    ambiguous_id = clean["ambiguous"][0]["record_id"]
    unmatched_id = clean["unmatched"][0]["record_id"]
    resolved = client.post(
        f"/api/imports/{import_id}/confirm-matches",
        json={"decisions": [
            {"record_id": ambiguous_id, "movie_id": 4},
            {"record_id": unmatched_id, "movie_id": None},
        ]},
        headers=headers,
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "cleaned"

    confirmed = client.post(f"/api/imports/{import_id}/confirm", headers=headers)
    assert confirmed.status_code == 200, confirmed.text
    result = confirmed.json()
    # Inception, Matrix, Dark Knight, Joker, Interstellar, Rises (resolved)
    assert result["inserted"] == 6
    assert result["status"] == "completed"

    # --- Stage 3: analytics reflect the import ------------------
    summary = client.get("/api/analytics/summary", headers=headers).json()
    assert summary["movies_watched"] == 6
    # "dark knight" matched after cleaning with no rating, so 5 of 6 are rated.
    assert summary["rated_count"] == 5
    assert summary["unrated_count"] == 1
    assert summary["average_rating"] == 4.6  # (5+4.5+5+4+4.5)/5
    assert summary["most_common_genre"] == "Action"
    assert summary["data_quality"]["imports"] == 1
    assert summary["data_quality"]["duplicates_removed"] == 1
    assert summary["data_quality"]["missing_values"] == 1

    ratings = client.get("/api/analytics/ratings", headers=headers).json()
    assert ratings["rated_count"] == 5

    genres = client.get("/api/analytics/genres", headers=headers).json()
    assert genres["genres"][0]["genre"] == "Action"

    # --- Stage 4: mining runs over the real history -------------
    kmeans = client.post("/api/mining/kmeans", json={"k": 2}, headers=headers)
    assert kmeans.status_code == 200, kmeans.text
    km = kmeans.json()
    assert km["movie_count"] == 6
    assert sum(p["cluster_size"] for p in km["profiles"]) == 6

    apriori = client.post(
        "/api/mining/apriori", json={"min_support": 0.1, "min_confidence": 0.3},
        headers=headers,
    )
    assert apriori.status_code == 200, apriori.text
    assert apriori.json()["transaction_count"] == 25

    nb = client.post("/api/mining/naive-bayes", headers=headers)
    assert nb.status_code == 200, nb.text
    assert nb.json()["modelled_genres"] >= 1

    runs = client.get("/api/mining/runs", headers=headers).json()["runs"]
    assert {run["algorithm"] for run in runs} == {"kmeans", "apriori", "naive_bayes"}

    # --- Stage 5: recommendations exclude the imported list -----
    recs = client.get("/api/recommendations?limit=5", headers=headers).json()
    assert len(recs["items"]) == 5
    assert recs["total"] == 25 - 6
    watched_now = {5, 9, 3, 20, 6, 4}
    assert not watched_now & {item["movie_id"] for item in recs["items"]}
    for item in recs["items"]:
        assert item["reasons"]


def test_journey_second_user_is_fully_isolated(client):
    first = register(client, name="First", email="first@example.com")
    second = register(client, name="Second", email="second@example.com")

    import_id, _ = _import_and_confirm(client, first)
    client.post("/api/mining/kmeans", json={"k": 2}, headers=first)
    client.get("/api/recommendations", headers=first)

    # The second user sees none of it.
    assert client.get("/api/analytics/summary", headers=second).json()["movies_watched"] == 0
    assert client.get("/api/mining/runs", headers=second).json()["runs"] == []
    preview = client.get(f"/api/imports/{import_id}/preview", headers=second)
    assert preview.status_code == 404

    # ...and the first user still has everything.
    assert client.get("/api/analytics/summary", headers=first).json()["movies_watched"] == 6


def test_journey_manual_history_reaches_recommendations(client):
    """A user who only used 'mark as watched' (no upload) still gets full analytics."""
    headers = register(client)
    for movie_id, rating in [(1, 5), (2, 4.5), (18, 4)]:
        response = client.post(
            f"/api/movies/{movie_id}/watched", json={"rating": rating}, headers=headers
        )
        assert response.status_code == 200, response.text

    summary = client.get("/api/analytics/summary", headers=headers).json()
    assert summary["movies_watched"] == 3
    assert summary["data_quality"]["imports"] == 0

    nb = client.post("/api/mining/naive-bayes", headers=headers)
    assert nb.status_code == 200, nb.text

    recs = client.get("/api/recommendations", headers=headers).json()
    assert recs["total"] == 22
    assert not {1, 2, 18} & {item["movie_id"] for item in recs["items"]}


def test_journey_reupload_is_reported_not_duplicated(client):
    """Re-confirming an import never duplicates the watched list."""
    headers = register(client)
    import_id, _ = _import_and_clean(client, headers)

    ambiguous_id = None
    clean_again = client.post(f"/api/imports/{import_id}/clean", headers=headers).json()
    if clean_again["ambiguous"]:
        ambiguous_id = clean_again["ambiguous"][0]["record_id"]
    if ambiguous_id is not None:
        client.post(
            f"/api/imports/{import_id}/confirm-matches",
            json={"decisions": [{"record_id": ambiguous_id, "movie_id": 4}]},
            headers=headers,
        )

    first = client.post(f"/api/imports/{import_id}/confirm", headers=headers).json()
    second = client.post(f"/api/imports/{import_id}/confirm", headers=headers).json()

    assert first["inserted"] == 6
    assert second["inserted"] == 0
    assert second["already_watched"] == 6

    summary = client.get("/api/analytics/summary", headers=headers).json()
    assert summary["movies_watched"] == 6
