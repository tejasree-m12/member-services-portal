"""Integration tests: claims workflow and documents (module 2)."""
import io
from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import AuditLog, Claim, ClaimDocument

pytestmark = pytest.mark.integration


def claim_payload(member, provider, **overrides):
    payload = {
        "member_id": member.id,
        "provider_id": provider.id,
        "service_date": "2026-01-15",
        "procedure_code": "99213",
        "diagnosis_code": "E11.9",
        "billed_amount": "150.00",
    }
    payload.update(overrides)
    return payload


def move(client, headers, claim_id, **body):
    return client.post(f"/api/v1/claims/{claim_id}/transition", json=body, headers=headers)


# --- Create and read ----------------------------------------------------------


def test_create_claim(client, agent_headers, member, provider):
    response = client.post("/api/v1/claims", json=claim_payload(member, provider), headers=agent_headers)
    body = response.get_json()
    assert response.status_code == 201
    assert body["status"] == "submitted"
    assert body["billed_amount"] == "150.00"  # money is a string, not a float
    assert body["claim_number"].startswith("CLM-")
    assert [h["to_status"] for h in body["history"]] == ["submitted"]
    assert body["allowed_transitions"] == ["in_review"]


@pytest.mark.parametrize(
    "overrides, bad_field",
    [
        ({"billed_amount": "-10"}, "billed_amount"),
        ({"billed_amount": "12.345"}, "billed_amount"),
        ({"procedure_code": "ABC"}, "procedure_code"),
        ({"diagnosis_code": "123"}, "diagnosis_code"),
        ({"service_date": (date.today() + timedelta(days=3)).isoformat()}, "service_date"),
        ({"member_id": 9999}, "member_id"),
        ({"provider_id": 9999}, "provider_id"),
        ({"member_id": "1"}, "member_id"),
    ],
)
def test_create_claim_validation(client, agent_headers, member, provider, overrides, bad_field):
    response = client.post(
        "/api/v1/claims", json=claim_payload(member, provider, **overrides), headers=agent_headers
    )
    assert response.status_code == 422
    assert bad_field in response.get_json()["error"]["details"]
    assert db.session.query(Claim).count() == 0


def test_cannot_create_claim_for_inactive_member(client, agent_headers, member, provider):
    member.status = "inactive"
    db.session.commit()
    response = client.post("/api/v1/claims", json=claim_payload(member, provider), headers=agent_headers)
    assert response.status_code == 422


def test_viewer_cannot_create_claim(client, viewer_headers, member, provider):
    response = client.post("/api/v1/claims", json=claim_payload(member, provider), headers=viewer_headers)
    assert response.status_code == 403


def test_list_claims_filters(client, viewer_headers, agent_headers, claim, member, provider):
    client.post("/api/v1/claims", json=claim_payload(member, provider), headers=agent_headers)
    move(client, agent_headers, claim.id, to_status="in_review")

    assert client.get("/api/v1/claims", headers=viewer_headers).get_json()["total"] == 2
    in_review = client.get("/api/v1/claims?status=in_review", headers=viewer_headers).get_json()
    assert [c["id"] for c in in_review["items"]] == [claim.id]
    by_number = client.get(f"/api/v1/claims?q={claim.claim_number}", headers=viewer_headers).get_json()
    assert by_number["total"] == 1
    by_member = client.get(f"/api/v1/claims?member_id={member.id}", headers=viewer_headers).get_json()
    assert by_member["total"] == 2
    assert client.get("/api/v1/claims?status=bogus", headers=viewer_headers).status_code == 400


def test_get_claim_404(client, viewer_headers):
    assert client.get("/api/v1/claims/9999", headers=viewer_headers).status_code == 404


# --- Workflow -----------------------------------------------------------------


def test_full_workflow_through_api(client, agent_headers, admin_headers, claim):
    assert move(client, agent_headers, claim.id, to_status="in_review").status_code == 200

    approved = move(client, agent_headers, claim.id, to_status="approved", approved_amount="180.00", note="OK")
    assert approved.status_code == 200
    assert approved.get_json()["approved_amount"] == "180.00"
    assert approved.get_json()["allowed_transitions"] == []  # agents cannot pay

    assert move(client, agent_headers, claim.id, to_status="paid").status_code == 403

    paid = move(client, admin_headers, claim.id, to_status="paid")
    body = paid.get_json()
    assert paid.status_code == 200
    assert body["status"] == "paid"
    assert [h["to_status"] for h in body["history"]] == ["submitted", "in_review", "approved", "paid"]
    assert db.session.query(AuditLog).filter_by(action="claim.transition").count() == 3


def test_illegal_transition_returns_409_and_changes_nothing(client, agent_headers, claim):
    response = move(client, agent_headers, claim.id, to_status="approved", approved_amount="10.00")
    assert response.status_code == 409
    assert db.session.get(Claim, claim.id).status == "submitted"


def test_approve_over_billed_amount_is_rejected(client, agent_headers, claim):
    move(client, agent_headers, claim.id, to_status="in_review")
    response = move(client, agent_headers, claim.id, to_status="approved", approved_amount="200.01")
    assert response.status_code == 422
    assert db.session.get(Claim, claim.id).status == "in_review"


def test_deny_then_appeal(client, agent_headers, claim):
    move(client, agent_headers, claim.id, to_status="in_review")
    assert move(client, agent_headers, claim.id, to_status="denied").status_code == 422  # reason required

    denied = move(client, agent_headers, claim.id, to_status="denied", denial_reason="Duplicate claim.")
    assert denied.get_json()["denial_reason"] == "Duplicate claim."

    appealed = move(client, agent_headers, claim.id, to_status="in_review", note="Appeal received.")
    assert appealed.get_json()["status"] == "in_review"
    assert appealed.get_json()["denial_reason"] is None


def test_viewer_cannot_transition(client, viewer_headers, claim):
    assert move(client, viewer_headers, claim.id, to_status="in_review").status_code == 403


def test_transition_on_missing_claim(client, agent_headers):
    assert move(client, agent_headers, 9999, to_status="in_review").status_code == 404


# --- Documents ----------------------------------------------------------------


def upload(client, headers, claim_id, filename="receipt.pdf", content=b"%PDF-1.4 test"):
    return client.post(
        f"/api/v1/claims/{claim_id}/documents",
        data={"file": (io.BytesIO(content), filename)},
        content_type="multipart/form-data",
        headers=headers,
    )


def test_upload_and_download_document(client, agent_headers, viewer_headers, claim):
    response = upload(client, agent_headers, claim.id)
    body = response.get_json()
    assert response.status_code == 201
    assert body["filename"] == "receipt.pdf"
    assert body["size_bytes"] == len(b"%PDF-1.4 test")

    detail = client.get(f"/api/v1/claims/{claim.id}", headers=viewer_headers).get_json()
    assert len(detail["documents"]) == 1

    download = client.get(f"/api/v1/claims/{claim.id}/documents/{body['id']}", headers=viewer_headers)
    assert download.status_code == 200
    assert download.data == b"%PDF-1.4 test"
    assert "attachment" in download.headers["Content-Disposition"]


def test_upload_rejects_disallowed_type(client, agent_headers, claim):
    response = upload(client, agent_headers, claim.id, filename="script.exe")
    assert response.status_code == 422
    assert db.session.query(ClaimDocument).count() == 0


def test_upload_sanitizes_filename(client, agent_headers, claim):
    response = upload(client, agent_headers, claim.id, filename="../../etc/passwd.txt")
    assert response.status_code == 201
    assert "/" not in response.get_json()["filename"]
    assert ".." not in db.session.query(ClaimDocument).one().storage_key


def test_upload_requires_file_and_permission(client, agent_headers, viewer_headers, claim):
    missing = client.post(f"/api/v1/claims/{claim.id}/documents", data={}, headers=agent_headers)
    assert missing.status_code == 400
    assert upload(client, agent_headers, claim.id, content=b"").status_code == 422
    assert upload(client, viewer_headers, claim.id).status_code == 403


def test_upload_too_large_is_rejected(client, agent_headers, claim):
    response = upload(client, agent_headers, claim.id, content=b"x" * (5 * 1024 * 1024 + 1))
    assert response.status_code == 413


def test_document_of_another_claim_is_not_served(client, agent_headers, claim):
    document_id = upload(client, agent_headers, claim.id).get_json()["id"]
    response = client.get(f"/api/v1/claims/{claim.id + 1}/documents/{document_id}", headers=agent_headers)
    assert response.status_code == 404
