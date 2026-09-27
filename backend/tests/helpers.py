"""Shared helpers for API tests (not a test module itself)."""


def register(client, name="Vishal", email="test@example.com", password="secret123"):
    response = client.post(
        "/api/auth/register", json={"name": name, "email": email, "password": password}
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def upload_csv(client, headers, content, filename="watched.csv"):
    response = client.post(
        "/api/upload/csv",
        files={"file": (filename, content.encode("utf-8"), "text/csv")},
        headers=headers,
    )
    return response


def upload_pdf(client, headers, pdf_bytes, filename="watched.pdf"):
    response = client.post(
        "/api/upload/pdf",
        files={"file": (filename, pdf_bytes, "application/pdf")},
        headers=headers,
    )
    return response
