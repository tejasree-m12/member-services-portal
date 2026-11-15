"""Dashboard summary: the numbers shown on the home screen."""
from decimal import Decimal

from flask import Blueprint, jsonify
from sqlalchemy import func, select

from ..auth.decorators import login_required
from ..claims.service import CLAIM_STATUSES
from ..extensions import db
from ..models import Claim, Member, Provider, money

bp = Blueprint("dashboard", __name__, url_prefix="/api/v1/dashboard")


@bp.get("/summary")
@login_required
def summary():
    # The database does the counting and adding (GROUP BY). Loading every row
    # into Python to count them would get slower as the tables grow.
    status_rows = db.session.execute(
        select(Claim.status, func.count(Claim.id), func.sum(Claim.billed_amount)).group_by(Claim.status)
    ).all()
    by_status = {status: {"count": 0, "billed_amount": "0.00"} for status in CLAIM_STATUSES}
    total_claims, total_billed = 0, Decimal("0")
    for status, count, billed in status_rows:
        billed = Decimal(billed or 0)
        by_status[status] = {"count": count, "billed_amount": money(billed)}
        total_claims += count
        total_billed += billed

    total_approved = db.session.scalar(
        select(func.sum(Claim.approved_amount)).where(Claim.status.in_(("approved", "paid")))
    )

    plan_rows = db.session.execute(
        select(Member.plan_type, func.count(Member.id))
        .where(Member.status == "active")
        .group_by(Member.plan_type)
        .order_by(func.count(Member.id).desc())
    ).all()

    decided = by_status["approved"]["count"] + by_status["paid"]["count"] + by_status["denied"]["count"]
    approved = by_status["approved"]["count"] + by_status["paid"]["count"]

    recent = db.session.scalars(select(Claim).order_by(Claim.created_at.desc(), Claim.id.desc()).limit(5)).all()

    return jsonify(
        {
            "members": {
                "active": db.session.scalar(select(func.count(Member.id)).where(Member.status == "active")),
                "total": db.session.scalar(select(func.count(Member.id))),
                "by_plan_type": [{"plan_type": plan, "count": count} for plan, count in plan_rows],
            },
            "providers": {"total": db.session.scalar(select(func.count(Provider.id)))},
            "claims": {
                "total": total_claims,
                "by_status": by_status,
                "total_billed": money(total_billed),
                "total_approved": money(Decimal(total_approved or 0)),
                "approval_rate": round(approved / decided * 100, 1) if decided else None,
                "awaiting_action": by_status["submitted"]["count"] + by_status["in_review"]["count"],
            },
            "recent_claims": [claim.to_dict() for claim in recent],
        }
    )
