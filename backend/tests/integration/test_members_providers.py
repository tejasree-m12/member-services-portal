"""Integration tests: member and provider directory (module 1)."""
from datetime import date

import pytest

from app.extensions import db
from app.models import AuditLog, Member
from tests.conftest import OTHER_VALID_NPI, VALID_NPI

pytestmark = pytest.mark.integration

NEW_MEMBER = {
    "first_name": "Ada",
    "last_name": "Lovelace",
    "date_of_birth": "1990-12-10",
    "email": "ada@example.com",
    "plan_type": "HMO",
}


# --- Members ------------------------------------------------------------------


def test_list_members_requires_login(client):
    assert client.get("/api/v1/members").status_code == 401


def test_create_member(client, agent_headers, provider):
    payload = dict(NEW_MEMBER, primary_provider_id=provider.id)
    response = client.post("/api/v1/members", json=payload, headers=agent_headers)
    body = response.get_json()
    assert response.status_code == 201
    assert body["member_number"].startswith("MBR-")
    assert body["status"] == "active"
    assert body["primary_provider"]["id"] == provider.id
    # The change was written to the audit log in the same transaction.
    audit = db.session.query(AuditLog).filter_by(action="member.create").one()
    assert audit.entity_id == body["id"]


def test_create_member_reports_all_invalid_fields(client, agent_headers):
    response = client.post(
        "/api/v1/members",
        json={"first_name": "", "last_name": "X", "date_of_birth": "10-12-1990", "plan_type": "Gold"},
        headers=agent_headers,
    )
    body = response.get_json()
    assert response.status_code == 422
    assert set(body["error"]["details"]) == {"first_name", "date_of_birth", "plan_type"}


def test_create_member_rejects_unknown_provider(client, agent_headers):
    response = client.post("/api/v1/members", json=dict(NEW_MEMBER, primary_provider_id=999), headers=agent_headers)
    assert response.status_code == 422
    assert "primary_provider_id" in response.get_json()["error"]["details"]


def test_viewer_cannot_create_member(client, viewer_headers):
    response = client.post("/api/v1/members", json=NEW_MEMBER, headers=viewer_headers)
    assert response.status_code == 403
    assert db.session.query(Member).count() == 0


def test_get_member_and_404(client, viewer_headers, member):
    assert client.get(f"/api/v1/members/{member.id}", headers=viewer_headers).get_json()["last_name"] == "Member"
    assert client.get("/api/v1/members/9999", headers=viewer_headers).status_code == 404


def test_search_filter_and_pagination(client, viewer_headers, app):
    for index in range(25):
        db.session.add(
            Member(
                first_name=f"First{index}",
                last_name="Zeta" if index < 5 else "Alpha",
                date_of_birth=date(1980, 1, 1),
                plan_type="HMO" if index % 2 == 0 else "PPO",
                status="active",
            )
        )
    db.session.commit()

    page1 = client.get("/api/v1/members?per_page=10", headers=viewer_headers).get_json()
    assert (page1["total"], page1["pages"], len(page1["items"])) == (25, 3, 10)
    page3 = client.get("/api/v1/members?per_page=10&page=3", headers=viewer_headers).get_json()
    assert len(page3["items"]) == 5

    search = client.get("/api/v1/members?q=zet", headers=viewer_headers).get_json()
    assert search["total"] == 5
    assert all(item["last_name"] == "Zeta" for item in search["items"])

    hmo = client.get("/api/v1/members?plan_type=HMO", headers=viewer_headers).get_json()
    assert hmo["total"] == 13

    assert client.get("/api/v1/members?page=abc", headers=viewer_headers).status_code == 400


def test_per_page_is_capped(client, viewer_headers, member):
    body = client.get("/api/v1/members?per_page=100000", headers=viewer_headers).get_json()
    assert body["per_page"] == 100


def test_search_text_is_not_executed_as_sql(client, viewer_headers, member):
    # A classic SQL-injection attempt is treated as plain text and matches nothing.
    response = client.get("/api/v1/members?q=' OR '1'='1", headers=viewer_headers)
    assert response.status_code == 200
    assert response.get_json()["total"] == 0
    assert db.session.query(Member).count() == 1


def test_update_member_changes_only_given_fields(client, agent_headers, member):
    response = client.put(f"/api/v1/members/{member.id}", json={"plan_type": "HMO"}, headers=agent_headers)
    body = response.get_json()
    assert response.status_code == 200
    assert body["plan_type"] == "HMO"
    assert body["first_name"] == "Sample"
    audit = db.session.query(AuditLog).filter_by(action="member.update").one()
    assert '"from": "PPO"' in audit.details


def test_update_member_validates(client, agent_headers, member):
    response = client.put(f"/api/v1/members/{member.id}", json={"email": "nope"}, headers=agent_headers)
    assert response.status_code == 422
    assert client.put(f"/api/v1/members/{member.id}", json={}, headers=agent_headers).status_code == 400


def test_only_admin_can_deactivate_and_row_is_kept(client, agent_headers, admin_headers, member):
    assert client.delete(f"/api/v1/members/{member.id}", headers=agent_headers).status_code == 403
    response = client.delete(f"/api/v1/members/{member.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["status"] == "inactive"
    assert db.session.get(Member, member.id) is not None  # soft delete: still in the table


def test_member_claims_list(client, viewer_headers, claim, member):
    body = client.get(f"/api/v1/members/{member.id}/claims", headers=viewer_headers).get_json()
    assert body["total"] == 1
    assert body["items"][0]["claim_number"] == claim.claim_number


# --- Providers ----------------------------------------------------------------

NEW_PROVIDER = {
    "npi": OTHER_VALID_NPI,
    "name": "Dr. Grace Hopper",
    "specialty": "Cardiology",
    "city": "Louisville",
    "state": "ky",
}


def test_admin_creates_provider(client, admin_headers):
    response = client.post("/api/v1/providers", json=NEW_PROVIDER, headers=admin_headers)
    body = response.get_json()
    assert response.status_code == 201
    assert body["state"] == "KY"
    assert body["accepting_patients"] is True


def test_agent_cannot_create_provider(client, agent_headers):
    assert client.post("/api/v1/providers", json=NEW_PROVIDER, headers=agent_headers).status_code == 403


def test_provider_npi_must_pass_check_digit(client, admin_headers):
    response = client.post("/api/v1/providers", json=dict(NEW_PROVIDER, npi="1234567890"), headers=admin_headers)
    assert response.status_code == 422
    assert "npi" in response.get_json()["error"]["details"]


def test_duplicate_npi_is_a_conflict(client, admin_headers, provider):
    response = client.post("/api/v1/providers", json=dict(NEW_PROVIDER, npi=VALID_NPI), headers=admin_headers)
    assert response.status_code == 409


def test_list_and_filter_providers(client, viewer_headers, admin_headers, provider):
    client.post("/api/v1/providers", json=NEW_PROVIDER, headers=admin_headers)
    assert client.get("/api/v1/providers", headers=viewer_headers).get_json()["total"] == 2
    cardio = client.get("/api/v1/providers?specialty=Cardiology", headers=viewer_headers).get_json()
    assert [p["name"] for p in cardio["items"]] == ["Dr. Grace Hopper"]
    by_state = client.get("/api/v1/providers?state=il", headers=viewer_headers).get_json()
    assert by_state["total"] == 1


def test_update_provider(client, admin_headers, provider):
    response = client.put(
        f"/api/v1/providers/{provider.id}", json={"accepting_patients": False}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.get_json()["accepting_patients"] is False
