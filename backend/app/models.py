"""Database models (tables) defined with SQLAlchemy.

Relationships at a glance::

    Provider 1 --- * Member        (a member's primary care provider)
    Member   1 --- * Claim
    Provider 1 --- * Claim         (the provider who performed the service)
    Claim    1 --- * ClaimStatusHistory
    Claim    1 --- * ClaimDocument
    User     1 --- * AuditLog
"""
import json
import uuid
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    """Current UTC time without tzinfo (MySQL DATETIME stores no timezone).

    Always store UTC in the database and convert to local time in the UI.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(value):
    """Serialize a date/datetime for JSON. Datetimes are marked as UTC."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds") + "Z"
    return value.isoformat()


def money(value):
    """Serialize a Decimal as a string so no precision is lost in JSON."""
    return None if value is None else f"{value:.2f}"


def new_member_number():
    return "MBR-" + uuid.uuid4().hex[:8].upper()


def new_claim_number():
    return "CLM-" + uuid.uuid4().hex[:10].upper()


class User(db.Model):
    """A staff account that can sign in to the portal."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="viewer")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def set_password(self, password):
        # Stores a salted hash, never the password itself.
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": iso(self.created_at),
        }


class Provider(db.Model):
    """A doctor or facility that treats members."""

    __tablename__ = "providers"

    id = db.Column(db.Integer, primary_key=True)
    npi = db.Column(db.String(10), nullable=False, unique=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    specialty = db.Column(db.String(100), nullable=False, index=True)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(2), nullable=False)
    phone = db.Column(db.String(20))
    accepting_patients = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "npi": self.npi,
            "name": self.name,
            "specialty": self.specialty,
            "city": self.city,
            "state": self.state,
            "phone": self.phone,
            "accepting_patients": self.accepting_patients,
        }


class Member(db.Model):
    """A person covered by a health plan."""

    __tablename__ = "members"

    id = db.Column(db.Integer, primary_key=True)
    member_number = db.Column(db.String(20), nullable=False, unique=True, default=new_member_number)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False, index=True)
    date_of_birth = db.Column(db.Date, nullable=False)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    plan_type = db.Column(db.String(30), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    primary_provider_id = db.Column(db.Integer, db.ForeignKey("providers.id"))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    primary_provider = db.relationship("Provider")
    claims = db.relationship("Claim", back_populates="member", lazy="dynamic")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def to_dict(self):
        return {
            "id": self.id,
            "member_number": self.member_number,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "date_of_birth": iso(self.date_of_birth),
            "email": self.email,
            "phone": self.phone,
            "plan_type": self.plan_type,
            "status": self.status,
            "primary_provider": (
                {"id": self.primary_provider.id, "name": self.primary_provider.name}
                if self.primary_provider
                else None
            ),
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
        }


class Claim(db.Model):
    """A request for payment for a service a provider gave a member."""

    __tablename__ = "claims"
    __table_args__ = (
        # Most list screens filter by status and sort by newest first.
        db.Index("ix_claims_status_created", "status", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    claim_number = db.Column(db.String(20), nullable=False, unique=True, default=new_claim_number)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False, index=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("providers.id"), nullable=False, index=True)
    service_date = db.Column(db.Date, nullable=False)
    procedure_code = db.Column(db.String(5), nullable=False)
    diagnosis_code = db.Column(db.String(8), nullable=False)
    billed_amount = db.Column(db.Numeric(10, 2), nullable=False)
    approved_amount = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(20), nullable=False, default="submitted")
    denial_reason = db.Column(db.String(255))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    member = db.relationship("Member", back_populates="claims")
    provider = db.relationship("Provider")
    created_by = db.relationship("User")
    history = db.relationship(
        "ClaimStatusHistory",
        back_populates="claim",
        order_by="ClaimStatusHistory.id",
        cascade="all, delete-orphan",
    )
    documents = db.relationship(
        "ClaimDocument",
        back_populates="claim",
        order_by="ClaimDocument.id",
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_details=False):
        data = {
            "id": self.id,
            "claim_number": self.claim_number,
            "member": {
                "id": self.member.id,
                "member_number": self.member.member_number,
                "full_name": self.member.full_name,
            },
            "provider": {"id": self.provider.id, "name": self.provider.name},
            "service_date": iso(self.service_date),
            "procedure_code": self.procedure_code,
            "diagnosis_code": self.diagnosis_code,
            "billed_amount": money(self.billed_amount),
            "approved_amount": money(self.approved_amount),
            "status": self.status,
            "denial_reason": self.denial_reason,
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
        }
        if include_details:
            data["history"] = [entry.to_dict() for entry in self.history]
            data["documents"] = [doc.to_dict() for doc in self.documents]
        return data


class ClaimStatusHistory(db.Model):
    """One row per status change, so a claim's full history can be shown."""

    __tablename__ = "claim_status_history"

    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.id"), nullable=False, index=True)
    from_status = db.Column(db.String(20))
    to_status = db.Column(db.String(20), nullable=False)
    note = db.Column(db.String(500))
    changed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    changed_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    claim = db.relationship("Claim", back_populates="history")
    changed_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "note": self.note,
            "changed_by": self.changed_by.full_name if self.changed_by else None,
            "changed_at": iso(self.changed_at),
        }


class ClaimDocument(db.Model):
    """Metadata for a file attached to a claim.

    The file itself lives in Amazon S3 (or local disk in development); the
    database only stores where to find it.
    """

    __tablename__ = "claim_documents"

    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    storage_key = db.Column(db.String(500), nullable=False)
    content_type = db.Column(db.String(100), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    claim = db.relationship("Claim", back_populates="documents")
    uploaded_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "uploaded_by": self.uploaded_by.full_name if self.uploaded_by else None,
            "uploaded_at": iso(self.uploaded_at),
        }


class AuditLog(db.Model):
    """Who did what, and when. Rows are only ever inserted, never changed."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    action = db.Column(db.String(50), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user.full_name if self.user else None,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "details": json.loads(self.details) if self.details else None,
            "created_at": iso(self.created_at),
        }
