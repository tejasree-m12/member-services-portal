"""Small helpers shared by the route modules."""
import json

from flask import g, request

from .errors import ApiError
from .extensions import db
from .models import AuditLog
from .validation import ValidationError

MAX_PER_PAGE = 100


def get_json_body():
    """Return the request body as a dict, or raise a 400 error."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object.")
    return data


def collect(data, cleaners):
    """Run several field cleaners and report every problem at once.

    ``cleaners`` maps a field name to a function that takes the raw value and
    returns the cleaned value. Returning all errors together means the user
    fixes a form in one round trip instead of one field at a time.
    """
    cleaned, errors = {}, {}
    for field, cleaner in cleaners.items():
        try:
            cleaned[field] = cleaner(data.get(field))
        except ValidationError as err:
            errors[err.field] = err.message
    if errors:
        raise ApiError(422, "Some fields are invalid.", details=errors)
    return cleaned


def paginate(stmt, serializer):
    """Run a SELECT with page/per_page query parameters and build the response."""
    try:
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(max(int(request.args.get("per_page", 20)), 1), MAX_PER_PAGE)
    except ValueError:
        raise ApiError(400, "page and per_page must be whole numbers.")
    result = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    return {
        "items": [serializer(item) for item in result.items],
        "page": result.page,
        "per_page": result.per_page,
        "total": result.total,
        "pages": result.pages,
    }


def get_or_404(model, object_id, name=None):
    obj = db.session.get(model, object_id)
    if obj is None:
        raise ApiError(404, f"{name or model.__name__} not found.")
    return obj


def record_audit(action, entity_type, entity_id=None, details=None, user=None):
    """Add an audit-log row to the current transaction.

    The caller commits. Because the audit row is in the same transaction as
    the change it describes, either both are saved or neither is.
    """
    user = user or getattr(g, "current_user", None)
    entry = AuditLog(
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=json.dumps(details, default=str) if details else None,
        ip_address=request.remote_addr if request else None,
    )
    db.session.add(entry)
    return entry
