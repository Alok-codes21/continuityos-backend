import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app import db as dbm
from app.main import app
from app.routers import auth as auth_router


@pytest.fixture()
def client():
    dbm.Base.metadata.drop_all(dbm.engine)
    dbm.init_db()
    auth_router.reset_rate_limits()
    with TestClient(app) as c:
        yield c


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def register(client, email, name, org="Acme", pw="correct-horse-1"):
    r = client.post("/api/auth/register", json={"email": email, "name": name, "password": pw, "org_name": org})
    assert r.status_code == 201, r.text
    return r.json()


def add_member(client, admin, org_id, email, name, role, pw="member-pass-123"):
    r = client.post(f"/api/orgs/{org_id}/members", json={"email": email, "name": name, "role": role}, headers=H(admin["token"]))
    assert r.status_code == 201, r.text
    temp = r.json()["temporary_password"]
    tok = client.post("/api/auth/login", json={"email": email, "password": temp}).json()["token"]
    return {"token": tok, "user_id": r.json()["user_id"]}
