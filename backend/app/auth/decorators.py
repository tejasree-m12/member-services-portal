"""Decorators that protect routes.

Usage::

    @bp.get("/members")
    @login_required                    # any signed-in user
    def list_members(): ...

    @bp.post("/providers")
    @roles_required("admin")           # only admins
    def create_provider(): ...
"""
from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from ..errors import ApiError
from ..extensions import db
from ..models import User


def roles_required(*roles):
    """Require a valid token and, if roles are given, one of those roles."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            # Load the user on every request instead of trusting the role in
            # the token. If an admin deactivates an account or changes its
            # role, that takes effect immediately, not when the token expires.
            user = db.session.get(User, int(get_jwt_identity()))
            if user is None or not user.is_active:
                raise ApiError(401, "This account is no longer active.")
            if roles and user.role not in roles:
                raise ApiError(403, "You do not have permission to do this.")
            g.current_user = user
            return fn(*args, **kwargs)

        return wrapper

    return decorator


login_required = roles_required()
