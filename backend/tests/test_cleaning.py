from tests.helpers import register, upload_csv

# Fixture catalogue ids: Inception=5, The Dark Knight=3, The Dark Knight Rises=4,
# Titanic=7, Interstellar=6.
MESSY_CSV = """Movie,Rating
Inception,5
The Dark Knight,4.5
,3
Inception,5
dark knight,4
Zzz Nonexistent Film,3
Interstellar,99
Titanic,
"""


def _clean_flow(client):
    """Upload + clean the messy CSV; returns (headers, import_id, clean_body)."""
    headers = register(client)
    upload = upload_csv(client, headers, MESSY_CSV)
    assert upload.status_code == 200, upload.text
    import_id = upload.json()["import_id"]
    clean = client.post(f"/api/imports/{import_id}/clean", headers=headers)
    assert clean.status_code == 200, clean.text
    return headers, import_id, clean.json()


def test_clean_reports_exact_counts(client):
    _, _, body = _clean_flow(client)
    assert body["report"] == {
        "original_rows": 8,
        "duplicate_rows": 1,
        "missing_movie_rows": 1,
        "invalid_rows": 1,
        "matched_rows": 3,
        "ambiguous_rows": 1,
        "unmatched_rows": 1,
        "final_rows": 3,
    }
    assert body["status"] == "awaiting_match"


def test_clean_flags_each_record(client):
    headers, import_id, body = _clean_flow(client)
    from app.database.connection import connect
    from app.database.repositories import ImportRepository

    conn = connect()
    try:
        records = ImportRepository.get_records(conn, import_id)
    finally:
        conn.close()

    by_title = {r["raw_movie_title"]: r for r in records}
    assert len(records) == 8

    dup = [r for r in records if r["raw_movie_title"] == "Inception" and r["is_duplicate"]]
    assert len(dup) == 1
    assert dup[0]["match_status"] == "skipped"

    missing = [r for r in records if r["raw_movie_title"] is None]
    assert len(missing) == 1
    assert missing[0]["is_valid"] == 0
    assert missing[0]["match_status"] == "skipped"

    invalid = by_title["Interstellar"]
    assert invalid["is_valid"] == 0
    assert invalid["match_status"] == "skipped"
    assert invalid["normalized_title"] == "interstellar"

    matched_inception = [r for r in records if r["raw_movie_title"] == "Inception" and not r["is_duplicate"]]
    assert matched_inception[0]["match_status"] == "matched"
    assert matched_inception[0]["matched_movie_id"] == 5

    assert by_title["The Dark Knight"]["match_status"] == "matched"
    assert by_title["The Dark Knight"]["matched_movie_id"] == 3
    assert by_title["Titanic"]["match_status"] == "matched"


def test_ambiguous_title_returns_candidates(client):
    headers, import_id, body = _clean_flow(client)
    assert len(body["ambiguous"]) == 1
    item = body["ambiguous"][0]
    assert item["raw_movie_title"] == "dark knight"
    candidate_ids = {c["movie_id"] for c in item["candidates"]}
    assert 3 in candidate_ids
    assert 4 in candidate_ids
    for candidate in item["candidates"]:
        assert candidate["title"]
        assert candidate["score"] >= 0.6


def test_unmatched_title_is_listed(client):
    _, _, body = _clean_flow(client)
    assert len(body["unmatched"]) == 1
    assert body["unmatched"][0]["raw_movie_title"] == "Zzz Nonexistent Film"


def test_clean_is_idempotent_and_report_is_replaced(client):
    headers, import_id, first = _clean_flow(client)
    second = client.post(f"/api/imports/{import_id}/clean", headers=headers)
    assert second.status_code == 200
    assert second.json()["report"] == first["report"]

    from app.database.connection import connect

    conn = connect()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM data_quality_reports WHERE import_id = ?", (import_id,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 1


def test_confirm_blocked_while_ambiguous_remain(client):
    headers, import_id, _ = _clean_flow(client)
    response = client.post(f"/api/imports/{import_id}/confirm", headers=headers)
    assert response.status_code == 409
    assert "ambiguous" in response.json()["detail"].lower()


def test_resolve_matches_then_confirm(client):
    headers, import_id, body = _clean_flow(client)
    ambiguous_id = body["ambiguous"][0]["record_id"]
    unmatched_id = body["unmatched"][0]["record_id"]

    resolved = client.post(
        f"/api/imports/{import_id}/confirm-matches",
        json={"decisions": [
            {"record_id": ambiguous_id, "movie_id": 3},
            {"record_id": unmatched_id, "movie_id": None},
        ]},
        headers=headers,
    )
    assert resolved.status_code == 200, resolved.text
    report = resolved.json()["report"]
    assert report["ambiguous_rows"] == 0
    assert report["unmatched_rows"] == 0
    assert report["matched_rows"] == 4
    assert report["final_rows"] == 4
    assert resolved.json()["status"] == "cleaned"

    confirmed = client.post(f"/api/imports/{import_id}/confirm", headers=headers)
    assert confirmed.status_code == 200, confirmed.text
    result = confirmed.json()
    assert result["inserted"] == 3
    assert result["already_watched"] == 1  # "dark knight" resolved to the already-matched film
    assert result["status"] == "completed"

    from app.database.connection import connect
    from app.database.repositories import WatchedMovieRepository

    conn = connect()
    try:
        watched = WatchedMovieRepository.get_movie_ids(conn, 1)
        ratings = {
            row["movie_id"]: row["user_rating"]
            for row in conn.execute(
                "SELECT movie_id, user_rating FROM watched_movies WHERE user_id = 1"
            ).fetchall()
        }
    finally:
        conn.close()
    assert watched == {3, 5, 7}
    assert ratings[5] == 5.0
    assert ratings[3] == 4.5
    assert ratings[7] is None  # empty rating stays empty


def test_unmatched_left_alone_is_excluded_from_confirm(client):
    headers, import_id, body = _clean_flow(client)
    ambiguous_id = body["ambiguous"][0]["record_id"]

    client.post(
        f"/api/imports/{import_id}/confirm-matches",
        json={"decisions": [{"record_id": ambiguous_id, "movie_id": 4}]},
        headers=headers,
    )
    confirmed = client.post(f"/api/imports/{import_id}/confirm", headers=headers)
    assert confirmed.status_code == 200, confirmed.text
    result = confirmed.json()
    assert result["inserted"] == 4  # Inception, Dark Knight, Rises (resolved), Titanic
    assert result["unmatched_skipped"] == 1


def test_resolving_unknown_record_is_friendly(client):
    headers, import_id, _ = _clean_flow(client)
    response = client.post(
        f"/api/imports/{import_id}/confirm-matches",
        json={"decisions": [{"record_id": 999999, "movie_id": 3}]},
        headers=headers,
    )
    assert response.status_code == 400
    assert "re-run cleaning" in response.json()["detail"].lower()


def test_resolving_unknown_movie_is_friendly(client):
    headers, import_id, body = _clean_flow(client)
    ambiguous_id = body["ambiguous"][0]["record_id"]
    response = client.post(
        f"/api/imports/{import_id}/confirm-matches",
        json={"decisions": [{"record_id": ambiguous_id, "movie_id": 999999}]},
        headers=headers,
    )
    assert response.status_code == 400
