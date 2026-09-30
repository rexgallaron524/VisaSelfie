from datetime import timedelta

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.core.database import get_db
from app.core.security import utcnow
from app.limiter import limiter
from app.main import create_app
from app.processes.models import RegistrationLink
from app.processes.services import aware
from tests.test_auth import sign_in


def settings_for(url="http://localhost:3000", **overrides):
    values = {
        "database_url": "postgresql+psycopg://unused",
        "app_env": "development",
        "frontend_public_url": url,
        "allowed_origins": [url.rstrip("/")],
        "cookie_secure": None,
        "forwarded_allow_ips": "",
    }
    return Settings(_env_file=None, **(values | overrides))


@pytest.mark.parametrize("url", ["http://localhost:3000/", "https://demo.example.com///"])
def test_trailing_slashes_are_normalized(url):
    assert settings_for(url).frontend_public_url == url.rstrip("/")


@pytest.mark.parametrize(
    "url",
    [
        "",
        "example.com",
        "//example.com",
        "http:example.com",
        "ftp://example.com",
        "https://",
        "https://demo.example.com:bad",
        "https://demo.example.com:99999",
        "https://user:password@demo.example.com",
        "https://demo.example.com/path",
        "https://demo.example.com/path/..",
        "https://demo.example.com?query=1",
        "https://demo.example.com#fragment",
        "https://demo example.com",
        "https://demo.example.com\\evil",
        "https://*.example.com",
    ],
)
def test_invalid_public_urls_are_rejected(url):
    with pytest.raises(ValueError):
        settings_for(url, allowed_origins=["https://demo.example.com"])


def test_cookie_defaults_follow_public_scheme():
    assert settings_for().cookie_secure is False
    assert settings_for("https://demo.example.com", app_env="production").cookie_secure is True
    with pytest.raises(ValueError):
        settings_for(app_env="production")
    with pytest.raises(ValueError, match="secure cookies"):
        settings_for("https://demo.example.com", app_env="production", cookie_secure=False)


@pytest.mark.parametrize(
    "origins",
    [
        "https://demo.example.com",
        '["https://demo.example.com"]',
        "https://demo.example.com,https://admin.example.com",
    ],
)
def test_production_origin_environment(monkeypatch, origins):
    monkeypatch.setenv("ALLOWED_ORIGINS", origins)
    monkeypatch.setenv("FRONTEND_PUBLIC_URL", "https://demo.example.com/")
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unused",
        app_env="production",
        cookie_secure=None,
    )
    assert settings.frontend_public_url == "https://demo.example.com"
    assert "https://demo.example.com" in settings.allowed_origins


@pytest.mark.parametrize(
    "origins",
    [
        ["*"],
        ["https://*.example.com"],
        ["https://other.example.com"],
        ["https://demo.example.com", "http://insecure.example.com"],
        [],
    ],
)
def test_unsafe_or_missing_production_origins_are_rejected(origins):
    with pytest.raises(ValueError):
        settings_for("https://demo.example.com", app_env="production", allowed_origins=origins)


@pytest.mark.parametrize(
    "url,environment",
    [
        ("http://localhost:3000", "development"),
        ("https://demo.example.com", "production"),
    ],
)
def test_canonical_links_cookies_origins_and_expiry(db, url, environment):
    app = create_app(settings_for(url + "/", app_env=environment))
    app.dependency_overrides[get_db] = lambda: db
    limiter.reset()
    with TestClient(app, base_url=url, headers={"Origin": url}) as client:
        login = sign_in(client)
        assert login.status_code == 200
        cookie = login.headers["set-cookie"]
        assert ("Secure" in cookie) == (environment == "production")
        assert "HttpOnly" in cookie and "SameSite=lax" in cookie
        assert "Domain=" not in cookie
        assert client.get("/api/auth/me").status_code == 200
        response = client.post(
            "/api/admin/processes",
            headers={
                "Host": "internal-api:8000",
                "X-Forwarded-Host": "evil.example",
                "X-Forwarded-Proto": "http",
            },
            json={"full_name": "Test Applicant", "phone_number": "+44 7700 900123"},
        )
        assert response.status_code == 201, response.text
        issued = response.json()
        assert issued["registration_url"] == f"{url}/register/{issued['token']}"
        bearer = {"Authorization": f"Bearer {issued['token']}"}
        assert client.post("/api/public/open", headers=bearer).status_code == 200
        link = db.scalar(select(RegistrationLink))
        assert 47.99 < (aware(link.expires_at) - utcnow()).total_seconds() / 3600 <= 48
        link.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
        assert client.post("/api/public/open", headers=bearer).status_code == 410
        replacement = client.post(f"/api/admin/processes/{issued['process_id']}/link").json()
        assert replacement["registration_url"] == f"{url}/register/{replacement['token']}"
        assert replacement["token"] != issued["token"]
        assert client.post("/api/public/open", headers=bearer).status_code == 404
        preflight = client.options(
            "/api/auth/login",
            headers={
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert preflight.headers["access-control-allow-origin"] == url
        assert preflight.headers["access-control-allow-credentials"] == "true"
        assert (
            client.post("/api/auth/logout", headers={"Origin": "https://evil.example"}).status_code
            == 403
        )
        rejected = client.options(
            "/api/auth/login",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert rejected.status_code == 400
        assert "access-control-allow-origin" not in rejected.headers
        logout = client.post("/api/auth/logout")
        assert logout.status_code == 204
        assert ("Secure" in logout.headers["set-cookie"]) == (environment == "production")
    limiter.reset()


@pytest.mark.parametrize(
    "trusted,scheme,ip",
    [
        ("", "http", "127.0.0.1"),
        ("127.0.0.1", "https", "203.0.113.10"),
    ],
)
def test_only_configured_proxies_can_forward_headers(trusted, scheme, ip):
    app = create_app(settings_for(forwarded_allow_ips=trusted))

    @app.get("/proxy-test")
    def inspect_request(request: Request):
        return {"scheme": request.url.scheme, "ip": request.client.host}

    with TestClient(app, client=("127.0.0.1", 12345)) as client:
        result = client.get(
            "/proxy-test",
            headers={
                "X-Forwarded-Proto": "https",
                "X-Forwarded-For": "203.0.113.10",
            },
        )
        assert result.json() == {"scheme": scheme, "ip": ip}


def test_wildcard_proxy_trust_is_rejected():
    with pytest.raises(ValueError):
        settings_for(forwarded_allow_ips="*")
