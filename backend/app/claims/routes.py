"""Module 2: claims workflow (create, review, approve/deny, pay, documents)."""
import io
import uuid

from flask import Blueprint, current_app, g, jsonify, request, send_file
from sqlalchemy import or_, select
from werkzeug.utils import secure_filename

from ..auth.decorators import login_required, roles_required
from ..errors import ApiError
from ..extensions import db
from ..models import Claim, ClaimDocument, ClaimStatusHistory, Member, Provider
from ..storage import get_storage
from ..utils import collect, get_json_body, get_or_404, paginate, record_audit
from ..validation import (
    ValidationError,
    clean_date,
    clean_diagnosis_code,
    clean_money,
    clean_procedure_code,
    clean_string,
)
from .service import CLAIM_STATUSES, TransitionError, allowed_next_statuses, transition_claim

bp = Blueprint("claims", __name__, url_prefix="/api/v1/claims")


def _clean_id(field):
    def cleaner(value):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError(field, "This field is required.")
        return value

    return cleaner


def _claim_response(claim):
    data = claim.to_dict(include_details=True)
    data["allowed_transitions"] = allowed_next_statuses(claim, g.current_user.role)
    return data


@bp.get("")
@login_required
def list_claims():
    """List claims. Query parameters: q, status, member_id, provider_id, page, per_page."""
    stmt = select(Claim)
    status = request.args.get("status")
    if status:
        if status not in CLAIM_STATUSES:
            raise ApiError(400, "Unknown status filter.")
        stmt = stmt.where(Claim.status == status)
    if request.args.get("member_id", type=int):
        stmt = stmt.where(Claim.member_id == request.args.get("member_id", type=int))
    if request.args.get("provider_id", type=int):
        stmt = stmt.where(Claim.provider_id == request.args.get("provider_id", type=int))
    q = request.args.get("q", "").strip()
    if q:
        like = f"%{q}%"
        stmt = stmt.join(Claim.member).where(
            or_(Claim.claim_number.ilike(like), Member.last_name.ilike(like), Member.member_number.ilike(like))
        )
    stmt = stmt.order_by(Claim.created_at.desc(), Claim.id.desc())
    return jsonify(paginate(stmt, Claim.to_dict))


@bp.post("")
@roles_required("admin", "agent")
def create_claim():
    data = get_json_body()
    cleaned = collect(
        data,
        {
            "member_id": _clean_id("member_id"),
            "provider_id": _clean_id("provider_id"),
            "service_date": lambda v: clean_date(v, "service_date", allow_future=False),
            "procedure_code": lambda v: clean_procedure_code(v),
            "diagnosis_code": lambda v: clean_diagnosis_code(v),
            "billed_amount": lambda v: clean_money(v, "billed_amount"),
        },
    )

    member = db.session.get(Member, cleaned["member_id"])
    if member is None:
        raise ApiError(422, "Some fields are invalid.", details={"member_id": "Member not found."})
    if member.status != "active":
        raise ApiError(422, "Some fields are invalid.", details={"member_id": "Member is not active."})
    if db.session.get(Provider, cleaned["provider_id"]) is None:
        raise ApiError(422, "Some fields are invalid.", details={"provider_id": "Provider not found."})

    claim = Claim(**cleaned, status="submitted", created_by=g.current_user)
    claim.history.append(
        ClaimStatusHistory(from_status=None, to_status="submitted", note="Claim created.", changed_by=g.current_user)
    )
    db.session.add(claim)
    db.session.flush()
    record_audit("claim.create", "claim", claim.id, {"claim_number": claim.claim_number})
    db.session.commit()
    return jsonify(_claim_response(claim)), 201


@bp.get("/<int:claim_id>")
@login_required
def get_claim(claim_id):
    return jsonify(_claim_response(get_or_404(Claim, claim_id)))


@bp.post("/<int:claim_id>/transition")
@roles_required("admin", "agent")
def transition(claim_id):
    """Move a claim to a new status.

    Body: {"to_status": "...", "note": "...", "approved_amount": "...", "denial_reason": "..."}
    """
    data = get_json_body()
    cleaned = collect(
        data,
        {
            "to_status": lambda v: clean_string(v, "to_status", 20),
            "note": lambda v: clean_string(v, "note", 500, required=False),
            "approved_amount": lambda v: clean_money(v, "approved_amount", required=False, allow_zero=True),
            "denial_reason": lambda v: clean_string(v, "denial_reason", 255, required=False),
        },
    )

    # SELECT ... FOR UPDATE locks the claim row until this transaction ends.
    # If two agents act on the same claim at the same moment, the second
    # request waits, then sees the new status and is rejected by the state
    # machine instead of silently overwriting the first decision.
    claim = db.session.scalar(select(Claim).where(Claim.id == claim_id).with_for_update())
    if claim is None:
        raise ApiError(404, "Claim not found.")

    from_status = claim.status
    try:
        transition_claim(claim, user=g.current_user, **cleaned)
    except TransitionError as err:
        raise ApiError(err.status_code, err.message)

    record_audit("claim.transition", "claim", claim.id, {"from": from_status, "to": claim.status})
    db.session.commit()
    return jsonify(_claim_response(claim))


@bp.post("/<int:claim_id>/documents")
@roles_required("admin", "agent")
def upload_document(claim_id):
    """Attach a file to a claim (multipart/form-data, field name "file")."""
    claim = get_or_404(Claim, claim_id)
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        raise ApiError(400, "Attach a file in the 'file' field.")

    # Never trust a filename from the browser: secure_filename strips path
    # separators and unusual characters.
    filename = secure_filename(upload.filename)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed = current_app.config["ALLOWED_UPLOAD_EXTENSIONS"]
    if extension not in allowed:
        raise ApiError(422, "File type not allowed. Allowed types: " + ", ".join(sorted(allowed)) + ".")

    data = upload.read()
    if not data:
        raise ApiError(422, "The file is empty.")

    # A random prefix means two uploads with the same name never collide.
    storage_key = f"claims/{claim.id}/{uuid.uuid4().hex}_{filename}"
    content_type = upload.mimetype or "application/octet-stream"
    storage = get_storage()
    storage.save(storage_key, data, content_type)

    document = ClaimDocument(
        claim=claim,
        filename=filename,
        storage_key=storage_key,
        content_type=content_type,
        size_bytes=len(data),
        uploaded_by=g.current_user,
    )
    try:
        db.session.add(document)
        db.session.flush()
        record_audit("claim.document_upload", "claim", claim.id, {"filename": filename})
        db.session.commit()
    except Exception:
        # The file was stored but the database row was not: remove the file
        # so storage and database stay in step.
        db.session.rollback()
        storage.delete(storage_key)
        raise
    return jsonify(document.to_dict()), 201


@bp.get("/<int:claim_id>/documents/<int:document_id>")
@login_required
def download_document(claim_id, document_id):
    document = db.session.get(ClaimDocument, document_id)
    if document is None or document.claim_id != claim_id:
        raise ApiError(404, "Document not found.")
    data = get_storage().read(document.storage_key)
    return send_file(
        io.BytesIO(data),
        mimetype=document.content_type,
        as_attachment=True,
        download_name=document.filename,
    )
