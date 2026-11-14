import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DB = Path("/tmp/opencode/polis_test.db")
TEST_DB.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["SECRET_KEY"] = "polis-test-secret-key-not-for-production"
os.environ["ENVIRONMENT"] = "test"
os.environ["DEMO_SEED"] = "true"
os.environ["COOKIE_SECURE"] = "false"

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def seeded_client():
    """Start the app once, run lifespan seeding, and log in as the demo user."""
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/demo")
        assert response.status_code == 200, response.text
        yield client


@pytest.fixture(scope="session")
def demo_client(seeded_client):
    return seeded_client


@pytest.fixture(scope="session")
def app_client(seeded_client):
    # Separate cookie jar for anonymous/other-account requests, after schema init.
    return TestClient(app)


@pytest.fixture
def make_account(app_client):
    created: list[TestClient] = []

    def _make(label: str = "user", *, ai_processing: bool = False) -> tuple[TestClient, str]:
        client = TestClient(app)
        email = f"{label}-{uuid.uuid4().hex[:10]}@example.com"
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "StrongPass123",
                "name": f"Test {label.title()}",
                "accept_terms": True,
                "ai_processing": ai_processing,
                "research_participation": False,
            },
        )
        assert response.status_code == 201, response.text
        created.append(client)
        return client, response.json()["user"]["id"]

    yield _make
    for client in created:
        client.close()


@pytest.fixture
def demo_consent_reset(demo_client):
    original = demo_client.get("/api/v1/privacy/consent").json()["consent"]
    yield
    demo_client.patch(
        "/api/v1/privacy/consent",
        json={
            "ai_processing": original["ai_processing"],
            "research_participation": original["research_participation"],
            "federated_learning": original["federated_learning"],
            "analytics": original["analytics"],
        },
    )
