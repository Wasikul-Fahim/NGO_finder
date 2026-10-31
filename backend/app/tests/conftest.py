import os

os.environ["DB_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-test-secret-key-1234"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import NGO, Base, Role, User, VerificationStatus, Volunteer
from app.services.rate_limit import login_limiter

PASSWORD = "Passw0rdTest"


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with Session() as session:
        yield session
    engine.dispose()


@pytest.fixture()
def client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    login_limiter.reset()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(db, email, role=Role.VOLUNTEER, name="Test User", active=True) -> User:
    user = User(
        name=name, email=email, password_hash=hash_password(PASSWORD), role=role, is_active=active
    )
    db.add(user)
    db.flush()
    if role == Role.VOLUNTEER:
        db.add(Volunteer(user_id=user.id, skills=[], interests=[], availability=[]))
    db.commit()
    return user


def make_ngo_admin(db, email, verified=True, ngo_name="Helping Hands") -> User:
    user = make_user(db, email, Role.NGO_ADMIN, name="NGO Admin")
    db.add(
        NGO(
            user_id=user.id,
            ngo_name=ngo_name,
            verification_status=VerificationStatus.VERIFIED if verified else VerificationStatus.PENDING,
        )
    )
    db.commit()
    return user


def login(client, email, password=PASSWORD):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def ngo_headers(db, client):
    make_ngo_admin(db, "ngo@example.com")
    return login(client, "ngo@example.com")


@pytest.fixture()
def other_ngo_headers(db, client):
    make_ngo_admin(db, "ngo2@example.com", ngo_name="Other NGO")
    return login(client, "ngo2@example.com")


@pytest.fixture()
def volunteer_headers(db, client):
    make_user(db, "vol@example.com")
    return login(client, "vol@example.com")


@pytest.fixture()
def platform_headers(db, client):
    make_user(db, "root@example.com", Role.PLATFORM_ADMIN, name="Root")
    return login(client, "root@example.com")


@pytest.fixture()
def volunteer2_headers(db, client):
    make_user(db, "vol2@example.com", name="Second Volunteer")
    return login(client, "vol2@example.com")
