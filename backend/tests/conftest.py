import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./sentinel_test.db"
os.environ["SECRET_KEY"] = "test-secret-key-32-chars-long!!!!"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    # Fresh DB file
    if os.path.exists("sentinel_test.db"):
        os.remove("sentinel_test.db")
    from app.database.session import init_db
    init_db()
    yield
    if os.path.exists("sentinel_test.db"):
        os.remove("sentinel_test.db")

@pytest.fixture(scope="session")
def client(setup_db):
    from app.main import app
    return TestClient(app)

@pytest.fixture(scope="session")
def token(client):
    r = client.post("/api/v1/auth/register", json={"email": "tester@example.com", "password": "password123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]

@pytest.fixture(scope="session")
def auth(token):
    return {"Authorization": f"Bearer {token}"}
