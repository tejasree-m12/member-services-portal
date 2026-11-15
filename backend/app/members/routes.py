"""Module 1 (part 1): member directory."""
from flask import Blueprint, jsonify, request
from sqlalchemy import or_, select

from ..auth.decorators import login_required, roles_required
from ..errors import ApiError
from ..extensions import db
from ..models import Claim, Member, Provider
from ..utils import collect, get_json_body, get_or_404, paginate, record_audit
from ..validation import (
    MEMBER_STATUSES,
    PLAN_TYPES,
    clean_choice,
    clean_date,
    clean_email,
    clean_phone,
    clean_string,
)

bp = Blueprint("members", __name__, url_prefix="/api/v1/members")


def _clean_provider_id(value):
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ApiError(422, "Some fields are invalid.", details={"primary_provider_id": "Must be a provider id."})
    if db.session.get(Provider, value) is None:
        raise ApiError(422, "Some fields are invalid.", details={"primary_provider_id": "Provider not found."})
    return value


# One cleaner per editable field. Used by both create and update.
FIELD_CLEANERS = {
    "first_name": lambda v: clean_string(v, "first_name", 80),
    "last_name": lambda v: clean_string(v, "last_name", 80),
    "date_of_birth": lambda v: clean_date(v, "date_of_birth", allow_future=False),
    "email": lambda v: clean_email(v, required=False),
    "phone": lambda v: clean_phone(v),
    "plan_type": lambda v: clean_choice(v, "plan_type", PLAN_TYPES),
    "status": lambda v: clean_choice(v, "status", MEMBER_STATUSES),
    "primary_provider_id": _clean_provider_id,
}


@bp.get("")
@login_required
def list_members():
    """List members with optional search and filters.

    Query parameters: q, status, plan_type, page, per_page.
    """
    stmt = select(Member)
    q = request.args.get("q", "").strip()
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Member.first_name.ilike(like),
                Member.last_name.ilike(like),
                Member.member_number.ilike(like),
            )
        )
    if request.args.get("status"):
        stmt = stmt.where(Member.status == request.args["status"])
    if request.args.get("plan_type"):
        stmt = stmt.where(Member.plan_type == request.args["plan_type"])
    stmt = stmt.order_by(Member.last_name, Member.first_name, Member.id)
    return jsonify(paginate(stmt, Member.to_dict))


@bp.post("")
@roles_required("admin", "agent")
def create_member():
    data = get_json_body()
    data.setdefault("status", "active")
    cleaned = collect(data, FIELD_CLEANERS)
    member = Member(**cleaned)
    db.session.add(member)
    db.session.flush()  # sends the INSERT so member.id is available for the audit row
    record_audit("member.create", "member", member.id, {"member_number": member.member_number})
    db.session.commit()
    return jsonify(member.to_dict()), 201


@bp.get("/<int:member_id>")
@login_required
def get_member(member_id):
    return jsonify(get_or_404(Member, member_id).to_dict())


@bp.put("/<int:member_id>")
@roles_required("admin", "agent")
def update_member(member_id):
    """Update a member. Only the fields present in the body are changed."""
    member = get_or_404(Member, member_id)
    data = get_json_body()
    cleaners = {field: fn for field, fn in FIELD_CLEANERS.items() if field in data}
    if not cleaners:
        raise ApiError(400, "No editable fields were provided.")
    cleaned = collect(data, cleaners)

    changes = {}
    for field, new_value in cleaned.items():
        old_value = getattr(member, field)
        if old_value != new_value:
            changes[field] = {"from": old_value, "to": new_value}
            setattr(member, field, new_value)
    if changes:
        record_audit("member.update", "member", member.id, changes)
        db.session.commit()
    return jsonify(member.to_dict())


@bp.delete("/<int:member_id>")
@roles_required("admin")
def deactivate_member(member_id):
    """Deactivate a member.

    This is a "soft delete": the row is kept and marked inactive. Member and
    claim records must be retained, and claims reference the member row, so
    it is never physically deleted.
    """
    member = get_or_404(Member, member_id)
    if member.status != "inactive":
        member.status = "inactive"
        record_audit("member.deactivate", "member", member.id)
        db.session.commit()
    return jsonify(member.to_dict())


@bp.get("/<int:member_id>/claims")
@login_required
def list_member_claims(member_id):
    get_or_404(Member, member_id)
    stmt = select(Claim).where(Claim.member_id == member_id).order_by(Claim.created_at.desc(), Claim.id.desc())
    return jsonify(paginate(stmt, Claim.to_dict))
