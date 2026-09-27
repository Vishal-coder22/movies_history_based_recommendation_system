import os

from tests.helpers import register, upload_csv, upload_pdf

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

GOOD_CSV = """Movie,Rating
Inception,5
Interstellar,4.5
The Dark Knight,5
"""


def test_upload_csv_returns_preview(client):
    headers = register(client)
    response = upload_csv(client, headers, GOOD_CSV)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["import_id"] > 0
    assert body["file_type"] == "csv"
    assert body["file_name"] == "watched.csv"
    assert body["total_rows"] == 3
    assert body["columns"]["movie"] == "Movie"
    assert body["columns"]["rating"] == "Rating"
    assert len(body["sample_rows"]) == 3
    assert body["sample_rows"][0]["raw_movie_title"] == "Inception"
    assert body["status"] == "validated"


def test_upload_requires_authentication(client):
    response = upload_csv(client, {}, GOOD_CSV)
    assert response.status_code == 401


def test_upload_rejects_missing_movie_column(client):
    headers = register(client)
    response = upload_csv(client, headers, "Director,Year\nNolan,1970\n")
    assert response.status_code == 400
    assert "movie column" in response.json()["detail"].lower()


def test_upload_rejects_wrong_extension(client):
    headers = register(client)
    response = upload_csv(client, headers, GOOD_CSV, filename="watched.txt")
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_rejects_empty_file(client):
    headers = register(client)
    response = upload_csv(client, headers, "")
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_rejects_oversized_file(client):
    headers = register(client)
    huge = "x" * (11 * 1024 * 1024 + 1)
    response = upload_csv(client, headers, huge, filename="huge.csv")
    assert response.status_code == 400
    assert "larger than" in response.json()["detail"]


def test_upload_rejects_fully_non_numeric_ratings(client):
    headers = register(client)
    response = upload_csv(client, headers, "Movie,Rating\nInception,amazing\nTitanic,good\n")
    assert response.status_code == 400
    assert "numbers" in response.json()["detail"]


def test_upload_without_rating_column_warns_but_succeeds(client):
    headers = register(client)
    response = upload_csv(client, headers, "Movie\nInception\nTitanic\n")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["columns"]["rating"] is None
    assert any("Rating" in warning for warning in body["warnings"])


def test_upload_handles_corrupt_csv_gracefully(client):
    headers = register(client)
    bad = b"\xff\xfe\x00\x00,not,a\x00valid\x00csv"
    response = client.post(
        "/api/upload/csv",
        files={"file": ("bad.csv", bad, "text/csv")},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"]


def test_upload_pdf_extracts_table(client):
    headers = register(client)
    with open(os.path.join(FIXTURES, "watched_table.pdf"), "rb") as handle:
        pdf_bytes = handle.read()
    response = upload_pdf(client, headers, pdf_bytes)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["file_type"] == "pdf"
    assert body["total_rows"] == 5
    assert body["columns"]["movie"] == "Movie"
    assert body["columns"]["rating"] == "Rating"


def test_upload_pdf_without_table_gives_friendly_error(client):
    headers = register(client)
    with open(os.path.join(FIXTURES, "no_table.pdf"), "rb") as handle:
        pdf_bytes = handle.read()
    response = upload_pdf(client, headers, pdf_bytes)
    assert response.status_code == 400
    assert "table" in response.json()["detail"].lower()


def test_upload_pdf_rejects_non_pdf_file(client):
    headers = register(client)
    response = upload_pdf(client, headers, b"just text", filename="fake.pdf")
    assert response.status_code == 400


def test_preview_and_ownership(client):
    headers = register(client)
    import_id = upload_csv(client, headers, GOOD_CSV).json()["import_id"]

    preview = client.get(f"/api/imports/{import_id}/preview", headers=headers)
    assert preview.status_code == 200
    assert preview.json()["total_rows"] == 3

    other = register(client, name="Other", email="other@example.com")
    forbidden = client.get(f"/api/imports/{import_id}/preview", headers=other)
    assert forbidden.status_code == 404

    missing = client.get("/api/imports/999999/preview", headers=headers)
    assert missing.status_code == 404
