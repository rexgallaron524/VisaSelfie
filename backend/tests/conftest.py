import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.models import AdminUser
from app.core.config import Settings
from app.core.database import Base, get_db
from app.core.security import password_hasher
from app.limiter import limiter
from app.main import create_app

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "test-password-long-enough"


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            AdminUser(email=ADMIN_EMAIL, password_hash=password_hasher.hash(ADMIN_PASSWORD))
        )
        session.commit()
        yield session
    engine.dispose()


@pytest.fixture
def client(db):
    settings = Settings(
        _env_file=None,
        database_url="sqlite://",
        app_env="test",
        frontend_public_url="http://testserver",
        cookie_secure=False,
        allowed_origins=["http://testserver"],
    )
    app = create_app(settings)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    limiter.reset()
    with TestClient(app, headers={"Origin": "http://testserver"}) as test_client:
        yield test_client
    limiter.reset()
