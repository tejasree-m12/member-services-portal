"""Integration tests: admin tools and dashboard (module 3)."""
import csv
import io

import pytest

from app.extensions import db
from app.models import AuditLog, User
from tests.conftest import PASSWORD, login

pytestmark = pytest.mark.integration

NEW_USER = {"email": "New.Agent@Test.Local", "full_name": "New Agent", "role": "agent", "password": "Welcome#123"}


# --- Access control -----------------------------------------------------------


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/api/v1/admin/users"),
        ("post", "/api/v1/admin/users"),
        ("get", "/api/v1/admin/audit-logs"),
        ("get", "/api/v1/admin/reports/claims.csv"),
    ],
)
def test_admin_endpoints_are_admin_only(client, agent_headers, viewer_headers, method, path):
    assert getattr(client, method)(path).status_code == 401
    assert getattr(client, method)(path, headers=agent_headers, json={}).status_code == 403
    assert getattr(client, method)(path, headers=viewer_headers, json={}).status_code == 403


# --- Users --------------------------------------------------------------------


def test_create_user_and_new_user_can_login(client, admin_headers):
    response = client.post("/api/v1/admin/users", json=NEW_USER, headers=admin_headers)
    assert response.status_code == 201
    assert response.get_json()["email"] == "new.agent@test.local"
    assert login(client, "new.agent@test.local", "Welcome#123")


def test_create_user_validation_and_duplicate(client, admin_headers, admin_user):
    weak = client.post("/api/v1/admin/users", json=dict(NEW_USER, password="short"), headers=admin_headers)
    assert weak.status_code == 422
    bad_role = client.post("/api/v1/admin/users", json=dict(NEW_USER, role="superuser"), headers=admin_headers)
    assert bad_role.status_code == 422
    duplicate = client.post(
        "/api/v1/admin/users", json=dict(NEW_USER, email=admin_user.email), headers=admin_headers
    )
    assert duplicate.status_code == 409


def test_change_role_takes_effect_immediately(client, admin_headers, agent_user):
    agent_headers = login(client, agent_user.email)
    response = client.patch(f"/api/v1/admin/users/{agent_user.id}", json={"role": "viewer"}, headers=admin_headers)
    assert response.get_json()["role"] == "viewer"
    # The agent's existing token now carries viewer permissions only.
    blocked = client.post("/api/v1/members", json={}, headers=agent_headers)
    assert blocked.status_code == 403


def test_deactivate_user_blocks_login(client, admin_headers, agent_user):
    client.patch(f"/api/v1/admin/users/{agent_user.id}", json={"is_active": False}, headers=admin_headers)
    response = client.post("/api/v1/auth/login", json={"email": agent_user.email, "password": PASSWORD})
    assert response.status_code == 401


def test_admin_cannot_lock_themselves_out(client, admin_headers, admin_user):
    deactivate = client.patch(
        f"/api/v1/admin/users/{admin_user.id}", json={"is_active": False}, headers=admin_headers
    )
    demote = client.patch(f"/api/v1/admin/users/{admin_user.id}", json={"role": "viewer"}, headers=admin_headers)
    assert deactivate.status_code == 409
    assert demote.status_code == 409
    assert db.session.get(User, admin_user.id).role == "admin"


def test_password_reset_is_audited_without_the_password(client, admin_headers, agent_user):
    client.patch(f"/api/v1/admin/users/{agent_user.id}", json={"password": "BrandNew#123"}, headers=admin_headers)
    assert login(client, agent_user.email, "BrandNew#123")
    audit = db.session.query(AuditLog).filter_by(action="user.update").one()
    assert "BrandNew#123" not in audit.details


# --- Audit log ----------------------------------------------------------------


def test_audit_log_lists_and_filters(client, admin_headers):
    client.post("/api/v1/admin/users", json=NEW_USER, headers=admin_headers)
    everything = client.get("/api/v1/admin/audit-logs", headers=admin_headers).get_json()
    actions = [entry["action"] for entry in everything["items"]]
    assert actions[0] == "user.create"  # newest first
    assert "login" in actions

    only_logins = client.get("/api/v1/admin/audit-logs?action=login", headers=admin_headers).get_json()
    assert {entry["action"] for entry in only_logins["items"]} == {"login"}


# --- Reports ------------------------------------------------------------------


def test_claims_csv_report(client, admin_headers, claim):
    response = client.get("/api/v1/admin/reports/claims.csv", headers=admin_headers)
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    rows = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))
    assert len(rows) == 1
    assert rows[0]["claim_number"] == claim.claim_number
    assert rows[0]["billed_amount"] == "200.00"
    assert rows[0]["status"] == "submitted"


def test_claims_csv_filters(client, admin_headers, claim):
    def row_count(query):
        response = client.get(f"/api/v1/admin/reports/claims.csv?{query}", headers=admin_headers)
        assert response.status_code == 200
        return len(response.get_data(as_text=True).strip().splitlines()) - 1

    assert row_count("status=paid") == 0
    assert row_count("status=submitted") == 1
    assert row_count("date_from=2026-01-01&date_to=2026-01-31") == 1
    assert row_count("date_from=2026-02-01") == 0
    assert client.get("/api/v1/admin/reports/claims.csv?date_from=bad", headers=admin_headers).status_code == 400


def test_csv_export_neutralises_formulas(client, admin_headers, agent_headers, claim):
    client.post(f"/api/v1/claims/{claim.id}/transition", json={"to_status": "in_review"}, headers=agent_headers)
    client.post(
        f"/api/v1/claims/{claim.id}/transition",
        json={"to_status": "denied", "denial_reason": "=HYPERLINK(\"http://bad.example\")"},
        headers=agent_headers,
    )
    response = client.get("/api/v1/admin/reports/claims.csv", headers=admin_headers)
    row = next(csv.DictReader(io.StringIO(response.get_data(as_text=True))))
    assert row["denial_reason"].startswith("'=")


# --- Dashboard ----------------------------------------------------------------


def test_dashboard_requires_login(client):
    assert client.get("/api/v1/dashboard/summary").status_code == 401


def test_dashboard_on_empty_database(client, viewer_headers):
    body = client.get("/api/v1/dashboard/summary", headers=viewer_headers).get_json()
    assert body["claims"]["total"] == 0
    assert body["claims"]["approval_rate"] is None
    assert body["claims"]["total_billed"] == "0.00"
    assert body["recent_claims"] == []


def test_dashboard_numbers(client, viewer_headers, agent_headers, claim, member, provider):
    # Second claim: approve it for 90.00 of 100.00.
    created = client.post(
        "/api/v1/claims",
        json={
            "member_id": member.id, "provider_id": provider.id, "service_date": "2026-01-20",
            "procedure_code": "99214", "diagnosis_code": "I10", "billed_amount": "100.00",
        },
        headers=agent_headers,
    ).get_json()
    client.post(f"/api/v1/claims/{created['id']}/transition", json={"to_status": "in_review"}, headers=agent_headers)
    client.post(
        f"/api/v1/claims/{created['id']}/transition",
        json={"to_status": "approved", "approved_amount": "90.00"},
        headers=agent_headers,
    )

    body = client.get("/api/v1/dashboard/summary", headers=viewer_headers).get_json()
    assert body["members"] == {"active": 1, "total": 1, "by_plan_type": [{"plan_type": "PPO", "count": 1}]}
    assert body["providers"]["total"] == 1
    assert body["claims"]["total"] == 2
    assert body["claims"]["by_status"]["submitted"] == {"count": 1, "billed_amount": "200.00"}
    assert body["claims"]["by_status"]["approved"]["count"] == 1
    assert body["claims"]["total_billed"] == "300.00"
    assert body["claims"]["total_approved"] == "90.00"
    assert body["claims"]["approval_rate"] == 100.0
    assert body["claims"]["awaiting_action"] == 1
    assert len(body["recent_claims"]) == 2
