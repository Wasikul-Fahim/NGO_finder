from app.core.config import get_settings
from app.models import AuditLog, RefreshToken, Role, User, Volunteer
from app.tests.conftest import PASSWORD, login, make_ngo_admin, make_user

REG = {
    "name": "Ayesha Rahman",
    "email": "  Ayesha@Example.com ",
    "password": PASSWORD,
    "confirm_password": PASSWORD,
    "role": "VOLUNTEER",
    "location": "Dhaka",
}


def register(client, **overrides):
    return client.post("/api/v1/auth/register", json={**REG, **overrides})


def test_register_each_public_role(client, db):
    for role in ("VOLUNTEER", "DONOR", "BENEFICIARY"):
        r = register(client, role=role, email=f"{role.lower()}@example.com")
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["role"] == role
        assert "password" not in body and "password_hash" not in body
    user = db.query(User).filter_by(email="volunteer@example.com").one()
    assert db.query(Volunteer).filter_by(user_id=user.id).one().skills == []
    assert user.password_hash != PASSWORD


def test_email_normalised(client):
    r = register(client)
    assert r.json()["email"] == "ayesha@example.com"
    assert register(client, email="AYESHA@example.com").status_code == 409


def test_duplicate_email(client):
    register(client)
    r = register(client)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CONFLICT"
    assert "email" in r.json()["error"]["fields"]


def test_invalid_fields_give_field_errors(client):
    r = register(client, email="nope", password="short", confirm_password="other", name="")
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert {"email", "password", "name"} <= set(err["fields"])


def test_password_mismatch(client):
    r = register(client, confirm_password="Different1")
    assert r.status_code == 422
    assert "Passwords do not match" in str(r.json()["error"]["fields"])


def test_public_cannot_register_admin_roles(client, db):
    for role in ("NGO_ADMIN", "PLATFORM_ADMIN"):
        r = register(client, role=role)
        assert r.status_code == 422
        assert "role" in r.json()["error"]["fields"]
    assert db.query(User).count() == 0


def test_login_and_me(client, db):
    make_user(db, "a@example.com")
    r = client.post("/api/v1/auth/login", json={"email": "A@example.com", "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in"] > 0
    cookie = r.headers["set-cookie"]
    assert "refresh_token=" in cookie and "HttpOnly" in cookie
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200 and me.json()["email"] == "a@example.com"


def test_login_failures_are_generic(client, db):
    make_user(db, "a@example.com")
    wrong = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "Wrong1234"})
    unknown = client.post("/api/v1/auth/login", json={"email": "zz@example.com", "password": "Wrong1234"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_inactive_user_cannot_login(client, db):
    make_user(db, "off@example.com", active=False)
    r = client.post("/api/v1/auth/login", json={"email": "off@example.com", "password": PASSWORD})
    assert r.status_code == 401


def test_deactivated_user_token_rejected(client, db):
    user = make_user(db, "a@example.com")
    headers = login(client, "a@example.com")
    user.is_active = False
    db.commit()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_login_rate_limit(client, db):
    make_user(db, "a@example.com")
    for _ in range(get_settings().login_max_attempts):
        r = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "Wrong1234"})
        assert r.status_code == 401
    r = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    assert r.status_code == 429
    assert "Retry-After" in r.headers


def test_me_requires_valid_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


def test_refresh_rotates_and_rejects_reuse(client, db):
    make_user(db, "a@example.com")
    client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    old = client.cookies.get("refresh_token")
    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 200 and r.json()["access_token"]
    new = client.cookies.get("refresh_token")
    assert new and new != old
    assert db.query(RefreshToken).count() == 2

    # Replaying the rotated token fails and burns the whole family.
    client.cookies.set("refresh_token", old, path="/api")
    assert client.post("/api/v1/auth/refresh").status_code == 401
    client.cookies.set("refresh_token", new, path="/api")
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_refresh_without_cookie(client):
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_refresh_token_stored_hashed(client, db):
    make_user(db, "a@example.com")
    client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    raw = client.cookies.get("refresh_token")
    assert raw and all(t.token_hash != raw for t in db.query(RefreshToken))


def test_logout_revokes_refresh(client, db):
    make_user(db, "a@example.com")
    client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    token = client.cookies.get("refresh_token")
    assert client.post("/api/v1/auth/logout").status_code == 204
    client.cookies.set("refresh_token", token, path="/api")
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_change_password(client, db):
    make_user(db, "a@example.com")
    headers = login(client, "a@example.com")
    body = {"current_password": PASSWORD, "new_password": "BrandNew123", "confirm_password": "BrandNew123"}
    assert client.post("/api/v1/auth/change-password", json=body, headers=headers).status_code == 204
    old = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    assert old.status_code == 401
    new = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "BrandNew123"})
    assert new.status_code == 200


def test_change_password_wrong_current(client, db):
    make_user(db, "a@example.com")
    headers = login(client, "a@example.com")
    body = {"current_password": "Nope12345", "new_password": "BrandNew123", "confirm_password": "BrandNew123"}
    r = client.post("/api/v1/auth/change-password", json=body, headers=headers)
    assert r.status_code == 400


def test_change_password_revokes_sessions(client, db):
    make_user(db, "a@example.com")
    headers = login(client, "a@example.com")
    body = {"current_password": PASSWORD, "new_password": "BrandNew123", "confirm_password": "BrandNew123"}
    client.post("/api/v1/auth/change-password", json=body, headers=headers)
    assert all(t.revoked_at for t in db.query(RefreshToken))


def test_update_profile_cannot_change_role(client, db):
    make_user(db, "a@example.com")
    headers = login(client, "a@example.com")
    r = client.patch("/api/v1/auth/me", json={"name": "New Name", "location": "Sylhet"}, headers=headers)
    assert r.status_code == 200 and r.json()["name"] == "New Name"
    r = client.patch("/api/v1/auth/me", json={"role": "PLATFORM_ADMIN"}, headers=headers)
    assert r.status_code == 422
    assert db.query(User).one().role == Role.VOLUNTEER


def test_role_dependency_returns_403(client, volunteer_headers):
    r = client.get("/api/v1/ngos/me", headers=volunteer_headers)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_unverified_ngo_admin_blocked_from_writes(client, db):
    make_ngo_admin(db, "pending@example.com", verified=False)
    headers = login(client, "pending@example.com")
    assert client.get("/api/v1/ngos/me", headers=headers).status_code == 200
    r = client.post(
        "/api/v1/campaigns",
        json={"title": "X", "start_date": "2026-01-01", "end_date": "2026-02-01"},
        headers=headers,
    )
    assert r.status_code == 403
    assert db.query(AuditLog).count() == 0


def test_login_accepts_any_stored_email_domain(client, db):
    make_user(db, "demo@volunteersync.test")
    r = client.post("/api/v1/auth/login", json={"email": "demo@volunteersync.test", "password": PASSWORD})
    assert r.status_code == 200


def _preflight(client, origin):
    return client.options("/api/v1/auth/login", headers={
        "Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})


def test_cors_allows_local_dev_origins_on_any_port(client):
    for origin in ("http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174"):
        r = _preflight(client, origin)
        assert r.status_code == 200 and r.headers["access-control-allow-origin"] == origin
        assert r.headers["access-control-allow-credentials"] == "true"


def test_cors_rejects_other_origins(client):
    for origin in ("https://evil.example.com", "http://localhost.evil.com:5173", "https://localhost:5173"):
        assert _preflight(client, origin).status_code == 400


def test_relative_sqlite_path_is_anchored_to_backend_folder(monkeypatch):
    from app.core.config import BACKEND_DIR, Settings

    monkeypatch.chdir("/")  # whatever folder the server happens to be started from
    s = Settings(db_url="sqlite:///./volunteersync.db", secret_key="x" * 40)
    assert s.db_url == f"sqlite:///{(BACKEND_DIR / 'volunteersync.db').as_posix()}"
    assert Settings(db_url="sqlite://", secret_key="x" * 40).db_url == "sqlite://"  # in-memory untouched
    absolute = Settings(db_url="sqlite:////tmp/x.db", secret_key="x" * 40)
    assert absolute.db_url == "sqlite:////tmp/x.db"
