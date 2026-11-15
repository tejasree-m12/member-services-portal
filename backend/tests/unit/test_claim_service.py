"""Unit tests for the claim state machine (business rules only, no HTTP)."""
from decimal import Decimal

import pytest

from app.claims.service import (
    ALLOWED_TRANSITIONS,
    CLAIM_STATUSES,
    TransitionError,
    allowed_next_statuses,
    transition_claim,
)
from app.extensions import db

pytestmark = pytest.mark.unit


def test_every_status_has_a_transition_entry():
    assert set(ALLOWED_TRANSITIONS) == set(CLAIM_STATUSES)


def test_paid_is_a_final_status():
    assert ALLOWED_TRANSITIONS["paid"] == set()


def test_full_happy_path(claim, agent_user, admin_user):
    transition_claim(claim, "in_review", agent_user)
    transition_claim(claim, "approved", agent_user, approved_amount=Decimal("180.00"))
    transition_claim(claim, "paid", admin_user)
    db.session.commit()

    assert claim.status == "paid"
    assert claim.approved_amount == Decimal("180.00")
    # One history row from the fixture plus one per transition.
    assert [h.to_status for h in claim.history] == ["submitted", "in_review", "approved", "paid"]
    assert claim.history[-1].from_status == "approved"
    assert claim.history[-1].changed_by == admin_user


@pytest.mark.parametrize("target", ["approved", "denied", "paid", "submitted"])
def test_cannot_skip_review(claim, admin_user, target):
    with pytest.raises(TransitionError) as excinfo:
        transition_claim(claim, target, admin_user, approved_amount=Decimal("1.00"), denial_reason="x")
    assert excinfo.value.status_code == 409
    assert claim.status == "submitted"


def test_unknown_status_is_rejected(claim, admin_user):
    with pytest.raises(TransitionError) as excinfo:
        transition_claim(claim, "archived", admin_user)
    assert excinfo.value.status_code == 422


def test_approve_requires_amount(claim, agent_user):
    transition_claim(claim, "in_review", agent_user)
    with pytest.raises(TransitionError) as excinfo:
        transition_claim(claim, "approved", agent_user)
    assert excinfo.value.status_code == 422
    assert claim.status == "in_review"


def test_approved_amount_cannot_exceed_billed(claim, agent_user):
    transition_claim(claim, "in_review", agent_user)
    with pytest.raises(TransitionError):
        transition_claim(claim, "approved", agent_user, approved_amount=Decimal("200.01"))


def test_approved_amount_may_equal_billed(claim, agent_user):
    transition_claim(claim, "in_review", agent_user)
    transition_claim(claim, "approved", agent_user, approved_amount=Decimal("200.00"))
    assert claim.status == "approved"


def test_deny_requires_reason(claim, agent_user):
    transition_claim(claim, "in_review", agent_user)
    with pytest.raises(TransitionError):
        transition_claim(claim, "denied", agent_user)


def test_appeal_clears_denial_reason(claim, agent_user):
    transition_claim(claim, "in_review", agent_user)
    transition_claim(claim, "denied", agent_user, denial_reason="Missing documentation.")
    assert claim.denial_reason == "Missing documentation."

    transition_claim(claim, "in_review", agent_user, note="Member appealed.")
    assert claim.status == "in_review"
    assert claim.denial_reason is None


def test_only_admin_can_mark_paid(claim, agent_user):
    transition_claim(claim, "in_review", agent_user)
    transition_claim(claim, "approved", agent_user, approved_amount=Decimal("100.00"))
    with pytest.raises(TransitionError) as excinfo:
        transition_claim(claim, "paid", agent_user)
    assert excinfo.value.status_code == 403
    assert claim.status == "approved"


def test_viewer_cannot_transition(claim, viewer_user):
    with pytest.raises(TransitionError) as excinfo:
        transition_claim(claim, "in_review", viewer_user)
    assert excinfo.value.status_code == 403


def test_allowed_next_statuses_depend_on_role(claim, agent_user):
    assert allowed_next_statuses(claim, "agent") == ["in_review"]
    assert allowed_next_statuses(claim, "viewer") == []
    transition_claim(claim, "in_review", agent_user)
    assert allowed_next_statuses(claim, "agent") == ["approved", "denied"]
    transition_claim(claim, "approved", agent_user, approved_amount=Decimal("50.00"))
    assert allowed_next_statuses(claim, "agent") == []
    assert allowed_next_statuses(claim, "admin") == ["paid"]
