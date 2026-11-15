"""Authentication endpoints: sign in and "who am I"."""
from flask import Blueprint, g, jsonify
from flask_jwt_extended import create_access_token
from sqlalchemy import select

from ..errors import ApiError
from ..extensions import db
from ..models import User
from ..utils import get_json_body, record_audit
from .decorators import login_required

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@bp.post("/login")
def login():
    data = get_json_body()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

    user = db.session.scalar(select(User).where(User.email == email))
    # Same message whether the email or the password is wrong, so an attacker
    # cannot use this endpoint to discover which emails have accounts.
    if user is None or not user.is_active or not user.check_password(password):
        raise ApiError(401, "Invalid email or password.", "invalid_credentials")

    # The token identity ("sub") is the user id. flask-jwt-extended needs a string.
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    record_audit("login", "user", user.id, user=user)
    db.session.commit()
    return jsonify({"access_token": token, "user": user.to_dict()})


@bp.get("/me")
@login_required
def me():
    return jsonify({"user": g.current_user.to_dict()})
