"""Module 1 (part 2): provider directory."""
from flask import Blueprint, jsonify, request
from sqlalchemy import or_, select

from ..auth.decorators import login_required, roles_required
from ..errors import ApiError
from ..extensions import db
from ..models import Provider
from ..utils import collect, get_json_body, get_or_404, paginate, record_audit
from ..validation import ValidationError, clean_npi, clean_phone, clean_string

bp = Blueprint("providers", __name__, url_prefix="/api/v1/providers")


def _clean_state(value):
    value = clean_string(value, "state", 2)
    if len(value) != 2 or not value.isalpha():
        raise ValidationError("state", "Use the two-letter state code, e.g. IL.")
    return value.upper()


def _clean_bool(value):
    if not isinstance(value, bool):
        raise ValidationError("accepting_patients", "Must be true or false.")
    return value


FIELD_CLEANERS = {
    "npi": lambda v: clean_npi(v),
    "name": lambda v: clean_string(v, "name", 150),
    "specialty": lambda v: clean_string(v, "specialty", 100),
    "city": lambda v: clean_string(v, "city", 100),
    "state": _clean_state,
    "phone": lambda v: clean_phone(v),
    "accepting_patients": _clean_bool,
}


def _ensure_npi_unique(npi, exclude_id=None):
    stmt = select(Provider).where(Provider.npi == npi)
    if exclude_id is not None:
        stmt = stmt.where(Provider.id != exclude_id)
    if db.session.scalar(stmt) is not None:
        raise ApiError(409, "A provider with this NPI already exists.")


@bp.get("")
@login_required
def list_providers():
    """List providers. Query parameters: q, specialty, state, accepting, page, per_page."""
    stmt = select(Provider)
    q = request.args.get("q", "").strip()
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Provider.name.ilike(like), Provider.npi.ilike(like), Provider.city.ilike(like)))
    if request.args.get("specialty"):
        stmt = stmt.where(Provider.specialty == request.args["specialty"])
    if request.args.get("state"):
        stmt = stmt.where(Provider.state == request.args["state"].upper())
    if request.args.get("accepting") in ("true", "false"):
        stmt = stmt.where(Provider.accepting_patients == (request.args["accepting"] == "true"))
    stmt = stmt.order_by(Provider.name, Provider.id)
    return jsonify(paginate(stmt, Provider.to_dict))


@bp.post("")
@roles_required("admin")
def create_provider():
    data = get_json_body()
    data.setdefault("accepting_patients", True)
    cleaned = collect(data, FIELD_CLEANERS)
    _ensure_npi_unique(cleaned["npi"])
    provider = Provider(**cleaned)
    db.session.add(provider)
    db.session.flush()
    record_audit("provider.create", "provider", provider.id, {"npi": provider.npi})
    db.session.commit()
    return jsonify(provider.to_dict()), 201


@bp.get("/<int:provider_id>")
@login_required
def get_provider(provider_id):
    return jsonify(get_or_404(Provider, provider_id).to_dict())


@bp.put("/<int:provider_id>")
@roles_required("admin")
def update_provider(provider_id):
    provider = get_or_404(Provider, provider_id)
    data = get_json_body()
    cleaners = {field: fn for field, fn in FIELD_CLEANERS.items() if field in data}
    if not cleaners:
        raise ApiError(400, "No editable fields were provided.")
    cleaned = collect(data, cleaners)
    if "npi" in cleaned:
        _ensure_npi_unique(cleaned["npi"], exclude_id=provider.id)

    changes = {}
    for field, new_value in cleaned.items():
        old_value = getattr(provider, field)
        if old_value != new_value:
            changes[field] = {"from": old_value, "to": new_value}
            setattr(provider, field, new_value)
    if changes:
        record_audit("provider.update", "provider", provider.id, changes)
        db.session.commit()
    return jsonify(provider.to_dict())
