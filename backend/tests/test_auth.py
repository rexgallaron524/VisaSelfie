from datetime import timedelta

import pytest
from sqlalchemy import select

from app.audit.models import AuditLog
from app.auth.models import AdminSession, AdminUser
from app.core.config import Settings
from app.core.security import SESSION_COOKIE, hash_token, utcnow
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


def sign_in(client, password=ADMIN_PASSWORD, email=ADMIN_EMAIL):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_login_logout_and_replay_protection(client, db):
    response = sign_in(client)
    assert response.status_code == 200
    assert response.json()["email"] == ADMIN_EMAIL
    assert "password_hash" not in response.text
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    token = client.cookies[SESSION_COOKIE]
    stored = db.scalar(select(AdminSession))
    assert stored.token_hash == hash_token(token)
    assert token not in stored.token_hash
    assert client.get("/api/auth/me").status_code == 200
    assert client.get("/api/admin/activity").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.set(SESSION_COOKIE, token)
    assert client.get("/api/auth/me").status_code == 401
    actions = list(db.scalars(select(AuditLog.action)))
    assert actions == ["admin.login", "admin.logout"]


@pytest.mark.parametrize("path", ["/api/auth/me", "/api/admin/activity"])
def test_admin_routes_require_session(client, path):
    assert client.get(path).status_code == 401


def test_failed_login_is_generic_and_audited_without_credentials(client, db):
    wrong_password = sign_in(client, password="wrong-password")
    unknown_user = sign_in(client, email="missing@example.com")
    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()
    assert SESSION_COOKIE not in client.cookies
    events = db.scalars(select(AuditLog)).all()
    assert len(events) == 2
    assert all(event.action == "admin.login_failed" and event.details == {} for event in events)


def test_login_is_rate_limited(client):
    for _ in range(5):
        assert sign_in(client, password="incorrect").status_code == 401
    assert sign_in(client).status_code == 429


@pytest.mark.parametrize(
    "origin", ["https://evil.example", "null", "http://testserver.evil.example"]
)
def test_cross_origin_login_is_rejected(client, origin):
    response = client.post(
        "/api/auth/login",
        headers={"Origin": origin},
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 403
    assert SESSION_COOKIE not in client.cookies


def test_missing_origin_and_cross_origin_logout_are_rejected(client):
    assert sign_in(client).status_code == 200
    assert (
        client.post("/api/auth/logout", headers={"Origin": "https://evil.example"}).status_code
        == 403
    )
    del client.headers["Origin"]
    assert client.post("/api/auth/logout").status_code == 403
    assert client.get("/api/auth/me").status_code == 200


def test_expired_and_disabled_sessions_are_rejected(client, db):
    assert sign_in(client).status_code == 200
    session = db.scalar(select(AdminSession))
    session.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert client.get("/api/auth/me").status_code == 401
    assert sign_in(client).status_code == 200
    admin = db.scalar(select(AdminUser))
    admin.is_active = False
    db.commit()
    assert client.get("/api/auth/me").status_code == 401
    assert sign_in(client).status_code == 401


def test_login_rotates_existing_session(client):
    assert sign_in(client).status_code == 200
    old_token = client.cookies[SESSION_COOKIE]
    assert sign_in(client).status_code == 200
    assert client.cookies[SESSION_COOKIE] != old_token
    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE, old_token)
    assert client.get("/api/auth/me").status_code == 401


def test_validation_does_not_echo_password(client):
    secret = "sensitive-value-" * 20
    response = sign_in(client, password=secret)
    assert response.status_code == 422
    assert secret not in response.text
    assert "input" not in response.json()["detail"][0]


def test_security_headers(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_production_configuration_requires_https_and_secure_cookies():
    with pytest.raises(ValueError, match="secure cookies"):
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://unused",
            app_env="production",
            frontend_public_url="https://demo.example.com",
            allowed_origins=["https://demo.example.com"],
            cookie_secure=False,
        )
    with pytest.raises(ValueError, match="HTTPS"):
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://unused",
            app_env="production",
            cookie_secure=True,
        )


def test_production_sets_secure_cookie(client):
    client.app.state.settings.cookie_secure = True
    response = sign_in(client)
    assert "Secure" in response.headers["set-cookie"]
