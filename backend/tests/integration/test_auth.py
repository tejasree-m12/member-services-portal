"""Integration tests: authentication and the health check."""
import pytest

from app.extensions import db
from tests.conftest import PASSWORD, login, make_user

pytestmark = pytest.mark.integration


def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_login_returns_token_and_user(client, admin_user):
    response = client.post("/api/v1/auth/login", json={"email": admin_user.email, "password": PASSWORD})
    body = response.get_json()
    assert response.status_code == 200
    assert body["access_token"]
    assert body["user"]["role"] == "admin"
    assert "password_hash" not in body["user"]


def test_login_email_is_case_insensitive(client, admin_user):
    response = client.post("/api/v1/auth/login", json={"email": admin_user.email.upper(), "password": PASSWORD})
    assert response.status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "admin@test.local", "password": "wrong-password"},
        {"email": "nobody@test.local", "password": PASSWORD},
        {"email": "", "password": ""},
        {},
    ],
)
def test_login_failures_all_look_the_same(client, admin_user, payload):
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "invalid_credentials"


def test_login_rejects_non_json_body(client):
    response = client.post("/api/v1/auth/login", data="not json", content_type="text/plain")
    assert response.status_code == 400


def test_inactive_user_cannot_login(client, app):
    make_user("agent", email="gone@test.local", active=False)
    response = client.post("/api/v1/auth/login", json={"email": "gone@test.local", "password": PASSWORD})
    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_me_rejects_garbage_token(client):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "invalid_token"


def test_me_returns_current_user(client, agent_headers, agent_user):
    response = client.get("/api/v1/auth/me", headers=agent_headers)
    assert response.status_code == 200
    assert response.get_json()["user"]["email"] == agent_user.email


def test_token_stops_working_when_user_is_deactivated(client, agent_user):
    headers = login(client, agent_user.email)
    agent_user.is_active = False
    db.session.commit()
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401


def test_unknown_route_returns_json_404(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"
