"""Module 3: internal admin tools (user management, audit log, reports)."""
import csv
import io

from flask import Blueprint, Response, g, jsonify, request
from sqlalchemy import select

from ..auth.decorators import roles_required
from ..claims.service import CLAIM_STATUSES
from ..errors import ApiError
from ..extensions import db
from ..models import AuditLog, Claim, User, money
from ..utils import collect, get_json_body, get_or_404, paginate, record_audit
from ..validation import (
    USER_ROLES,
    ValidationError,
    clean_choice,
    clean_date,
    clean_email,
    clean_password,
    clean_string,
)

bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


# --- Users -------------------------------------------------------------------


@bp.get("/users")
@roles_required("admin")
def list_users():
    return jsonify(paginate(select(User).order_by(User.full_name, User.id), User.to_dict))


@bp.post("/users")
@roles_required("admin")
def create_user():
    cleaned = collect(
        get_json_body(),
        {
            "email": lambda v: clean_email(v),
            "full_name": lambda v: clean_string(v, "full_name", 120),
            "role": lambda v: clean_choice(v, "role", USER_ROLES),
            "password": lambda v: clean_password(v),
        },
    )
    if db.session.scalar(select(User).where(User.email == cleaned["email"])) is not None:
        raise ApiError(409, "A user with this email already exists.")

    user = User(email=cleaned["email"], full_name=cleaned["full_name"], role=cleaned["role"])
    user.set_password(cleaned["password"])
    db.session.add(user)
    db.session.flush()
    record_audit("user.create", "user", user.id, {"email": user.email, "role": user.role})
    db.session.commit()
    return jsonify(user.to_dict()), 201


def _clean_bool(field):
    def cleaner(value):
        if not isinstance(value, bool):
            raise ValidationError(field, "Must be true or false.")
        return value

    return cleaner


@bp.patch("/users/<int:user_id>")
@roles_required("admin")
def update_user(user_id):
    """Change a user's name, role, active flag or password."""
    user = get_or_404(User, user_id)
    data = get_json_body()
    cleaners = {
        "full_name": lambda v: clean_string(v, "full_name", 120),
        "role": lambda v: clean_choice(v, "role", USER_ROLES),
        "is_active": _clean_bool("is_active"),
        "password": lambda v: clean_password(v),
    }
    cleaners = {field: fn for field, fn in cleaners.items() if field in data}
    if not cleaners:
        raise ApiError(400, "No editable fields were provided.")
    cleaned = collect(data, cleaners)

    # Stop an admin from locking themselves out by mistake.
    if user.id == g.current_user.id:
        if cleaned.get("is_active") is False:
            raise ApiError(409, "You cannot deactivate your own account.")
        if "role" in cleaned and cleaned["role"] != "admin":
            raise ApiError(409, "You cannot remove your own admin role.")

    changes = {}
    for field in ("full_name", "role", "is_active"):
        if field in cleaned and getattr(user, field) != cleaned[field]:
            changes[field] = {"from": getattr(user, field), "to": cleaned[field]}
            setattr(user, field, cleaned[field])
    if "password" in cleaned:
        user.set_password(cleaned["password"])
        changes["password"] = "changed"  # never log the password itself
    if changes:
        record_audit("user.update", "user", user.id, changes)
        db.session.commit()
    return jsonify(user.to_dict())


# --- Audit log ---------------------------------------------------------------


@bp.get("/audit-logs")
@roles_required("admin")
def list_audit_logs():
    """Query parameters: action, entity_type, user_id, page, per_page."""
    stmt = select(AuditLog)
    if request.args.get("action"):
        stmt = stmt.where(AuditLog.action == request.args["action"])
    if request.args.get("entity_type"):
        stmt = stmt.where(AuditLog.entity_type == request.args["entity_type"])
    if request.args.get("user_id", type=int):
        stmt = stmt.where(AuditLog.user_id == request.args.get("user_id", type=int))
    stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    return jsonify(paginate(stmt, AuditLog.to_dict))


# --- Reports -----------------------------------------------------------------


def _csv_safe(value):
    """Protect against CSV injection.

    If a cell starts with =, +, - or @, Excel treats it as a formula. A value
    typed into the app (a denial reason, say) could then run when someone
    opens the export. Prefixing a single quote makes Excel show it as text.
    """
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@"):
        return "'" + text
    return text


@bp.get("/reports/claims.csv")
@roles_required("admin")
def claims_report():
    """Download claims as CSV. Query parameters: status, date_from, date_to (service date)."""
    stmt = select(Claim)
    status = request.args.get("status")
    if status:
        if status not in CLAIM_STATUSES:
            raise ApiError(400, "Unknown status filter.")
        stmt = stmt.where(Claim.status == status)
    try:
        date_from = clean_date(request.args.get("date_from"), "date_from", required=False)
        date_to = clean_date(request.args.get("date_to"), "date_to", required=False)
    except ValidationError as err:
        raise ApiError(400, f"{err.field}: {err.message}")
    if date_from:
        stmt = stmt.where(Claim.service_date >= date_from)
    if date_to:
        stmt = stmt.where(Claim.service_date <= date_to)
    stmt = stmt.order_by(Claim.service_date, Claim.id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "claim_number", "member_number", "member_name", "provider_npi", "provider_name",
            "service_date", "procedure_code", "diagnosis_code", "billed_amount",
            "approved_amount", "status", "denial_reason",
        ]
    )
    count = 0
    for claim in db.session.scalars(stmt):
        writer.writerow(
            [
                claim.claim_number,
                claim.member.member_number,
                _csv_safe(claim.member.full_name),
                claim.provider.npi,
                _csv_safe(claim.provider.name),
                claim.service_date.isoformat(),
                claim.procedure_code,
                claim.diagnosis_code,
                money(claim.billed_amount),
                money(claim.approved_amount) or "",
                claim.status,
                _csv_safe(claim.denial_reason),
            ]
        )
        count += 1

    record_audit("report.claims_export", "report", details={"rows": count, "status": status})
    db.session.commit()
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=claims_report.csv"},
    )
