REGISTER = {"name": "Vishal", "email": "vishal@example.com", "password": "secret123"}


def _register(client, **overrides):
    payload = {**REGISTER, **overrides}
    return client.post("/api/auth/register", json=payload)


def test_register_returns_token_and_safe_user(client):
    response = _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "vishal@example.com"
    assert body["user"]["name"] == "Vishal"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]


def test_register_normalizes_email_and_allows_login(client):
    _register(client, email="  Vishal@Example.COM ")
    response = client.post(
        "/api/auth/login", json={"email": "vishal@example.com", "password": "secret123"}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_register_rejects_duplicate_email(client):
    _register(client)
    response = _register(client, name="Someone Else")
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_register_rejects_invalid_email(client):
    response = _register(client, email="not-an-email")
    assert response.status_code == 400
    assert "valid email" in response.json()["detail"]


def test_register_rejects_short_password(client):
    response = _register(client, password="abc")
    assert response.status_code == 400
    assert "6 characters" in response.json()["detail"]


def test_register_rejects_blank_name(client):
    response = _register(client, name="   ")
    assert response.status_code == 400


def test_login_with_wrong_password_is_401(client):
    _register(client)
    response = client.post(
        "/api/auth/login", json={"email": "vishal@example.com", "password": "wrongpass"}
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_with_unknown_email_is_401(client):
    response = client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "secret123"}
    )
    assert response.status_code == 401


def test_me_requires_valid_token(client):
    assert client.get("/api/auth/me").status_code == 401

    bad = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage.token.here"})
    assert bad.status_code == 401

    empty = client.get("/api/auth/me", headers={"Authorization": "Bearer"})
    assert empty.status_code == 401


def test_me_returns_current_user(client):
    token = _register(client).json()["access_token"]
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "vishal@example.com"


def test_password_is_stored_hashed(client):
    _register(client)
    from app.database.connection import connect

    conn = connect()
    try:
        row = conn.execute("SELECT password_hash FROM users WHERE email = ?", (
            "vishal@example.com",
        )).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] != "secret123"
    assert row[0].startswith("$2b$") or row[0].startswith("$2y$")


def test_seed_demo_user_idempotent(db):
    from app.database.seed import seed_demo_user
    from app.database.repositories import UserRepository
    from app.database.connection import connect

    # First call creates the user
    uid1 = seed_demo_user()
    assert uid1 is not None

    conn = connect()
    try:
        user = UserRepository.get_by_email(conn, "demo@cinemine.dev")
        assert user is not None
        assert user["email"] == "demo@cinemine.dev"
        assert user["name"] == "Demo User"
    finally:
        conn.close()

    # Second call returns None (idempotent)
    uid2 = seed_demo_user()
    assert uid2 is None
