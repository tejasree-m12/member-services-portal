"""One consistent JSON error format for the whole API.

Every error response looks like::

    {"error": {"code": "validation_error", "message": "...", "details": {...}}}

so the frontend needs only one piece of error-handling code.
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException

from .extensions import db, jwt


class ApiError(Exception):
    """Raise this anywhere in a request to return a clean JSON error."""

    def __init__(self, status_code, message, code=None, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.code = code or _default_code(status_code)
        self.details = details


def _default_code(status_code):
    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        413: "payload_too_large",
        422: "validation_error",
    }.get(status_code, "error")


def error_response(status_code, message, code=None, details=None):
    body = {"error": {"code": code or _default_code(status_code), "message": message}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status_code


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(err):
        db.session.rollback()
        return error_response(err.status_code, err.message, err.code, err.details)

    @app.errorhandler(HTTPException)
    def handle_http_exception(err):
        # 404 for unknown URLs, 405 wrong method, 413 upload too large, etc.
        return error_response(err.code, err.description)

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        # Never leak a stack trace to the client. Log it and return a generic 500.
        db.session.rollback()
        app.logger.exception("Unhandled exception: %s", err)
        return error_response(500, "An unexpected error occurred.", "internal_error")

    # --- JWT errors: make them use the same JSON format ---------------------
    @jwt.unauthorized_loader
    def missing_token(reason):
        return error_response(401, "Authentication required.", "unauthorized")

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return error_response(401, "Invalid authentication token.", "invalid_token")

    @jwt.expired_token_loader
    def expired_token(header, payload):
        return error_response(401, "Your session has expired. Please sign in again.", "token_expired")
