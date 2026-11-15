"""Business rules for the claim workflow.

A claim moves through a fixed set of statuses (a "state machine")::

    submitted --> in_review --> approved --> paid
                      |  ^
                      v  |  (appeal)
                     denied

The rules live here, not in the route functions, so they can be unit tested
without HTTP and reused by any future caller (a batch job, for example).
"""
from ..models import ClaimStatusHistory

CLAIM_STATUSES = ("submitted", "in_review", "approved", "denied", "paid")

ALLOWED_TRANSITIONS = {
    "submitted": {"in_review"},
    "in_review": {"approved", "denied"},
    "approved": {"paid"},
    "denied": {"in_review"},  # an appeal sends a denied claim back to review
    "paid": set(),  # final status
}

# Which roles may move a claim INTO each status.
ROLES_FOR_TARGET_STATUS = {
    "in_review": {"admin", "agent"},
    "approved": {"admin", "agent"},
    "denied": {"admin", "agent"},
    "paid": {"admin"},  # releasing payment is restricted to admins
}


class TransitionError(Exception):
    """A status change that breaks a business rule."""

    def __init__(self, message, status_code=409):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def allowed_next_statuses(claim, role):
    """Statuses this role may move the claim to (drives the buttons in the UI)."""
    return sorted(
        status
        for status in ALLOWED_TRANSITIONS.get(claim.status, set())
        if role in ROLES_FOR_TARGET_STATUS.get(status, set())
    )


def transition_claim(claim, to_status, user, note=None, approved_amount=None, denial_reason=None):
    """Change a claim's status, enforcing every rule, and record the history.

    Raises TransitionError if the change is not allowed. Does not commit;
    the caller owns the database transaction.
    """
    if to_status not in CLAIM_STATUSES:
        raise TransitionError(f"Unknown status '{to_status}'.", 422)

    if to_status not in ALLOWED_TRANSITIONS[claim.status]:
        raise TransitionError(f"A claim cannot move from '{claim.status}' to '{to_status}'.")

    if user.role not in ROLES_FOR_TARGET_STATUS[to_status]:
        raise TransitionError(f"Your role cannot move a claim to '{to_status}'.", 403)

    if to_status == "approved":
        if approved_amount is None:
            raise TransitionError("An approved amount is required to approve a claim.", 422)
        if approved_amount > claim.billed_amount:
            raise TransitionError("The approved amount cannot be more than the billed amount.", 422)
        claim.approved_amount = approved_amount
        claim.denial_reason = None

    if to_status == "denied":
        if not denial_reason:
            raise TransitionError("A denial reason is required to deny a claim.", 422)
        claim.denial_reason = denial_reason
        claim.approved_amount = None

    if to_status == "in_review" and claim.status == "denied":
        # Appeal: clear the old decision so the claim is reviewed afresh.
        claim.denial_reason = None

    entry = ClaimStatusHistory(
        from_status=claim.status,
        to_status=to_status,
        note=note,
        changed_by=user,
    )
    claim.history.append(entry)
    claim.status = to_status
    return entry
