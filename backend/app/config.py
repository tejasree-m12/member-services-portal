"""Application configuration.

Every setting that differs between environments (laptop, CI, EC2) is read from
an environment variable. The code never contains real secrets; see
``.env.example`` for the full list of variables.
"""
import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _split_csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


class Config:
    """Default configuration, used for local development and production."""

    TESTING = False

    # Used by Flask to sign data. Must be overridden in production.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-key-change-me-in-production")

    # --- Database -----------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://portal:portal_password@127.0.0.1:3306/member_portal?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # pool_pre_ping checks a pooled connection is still alive before using it.
    # MySQL closes idle connections (wait_timeout); without this the first
    # request after a quiet period fails with "MySQL server has gone away".
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 1800}

    # --- Authentication -----------------------------------------------------
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-only-jwt-secret-key-change-me-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_TOKEN_MINUTES", "60"))
    )

    # --- CORS ---------------------------------------------------------------
    # Browser origins allowed to call the API (the React dev server by default).
    CORS_ORIGINS = _split_csv(os.environ.get("CORS_ORIGINS", "http://localhost:5173"))

    # --- File storage -------------------------------------------------------
    # If S3_BUCKET is set, claim documents go to Amazon S3. Otherwise they are
    # written to UPLOAD_DIR on local disk (development and tests).
    S3_BUCKET = os.environ.get("S3_BUCKET", "")
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # reject request bodies over 5 MB
    ALLOWED_UPLOAD_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "txt"}


class TestConfig(Config):
    """Configuration used by the automated tests.

    Tests run on an in-memory SQLite database by default so they need no
    setup. CI sets TEST_DATABASE_URL to run the same tests against MySQL.
    """

    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_ENGINE_OPTIONS = {}
    S3_BUCKET = ""
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
