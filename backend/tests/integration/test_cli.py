"""Integration tests: the `flask` command-line tasks."""
import pytest
from sqlalchemy import func, select

from app.claims.service import ALLOWED_TRANSITIONS
from app.extensions import db
from app.models import Claim, Member, Provider, User
from app.validation import is_valid_npi

pytestmark = pytest.mark.integration


def test_seed_loads_consistent_demo_data(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed"])
    assert result.exit_code == 0
    assert "admin@example.com" in result.output

    assert db.session.scalar(select(func.count(User.id))) == 3
    assert db.session.scalar(select(func.count(Provider.id))) == 12
    assert db.session.scalar(select(func.count(Member.id))) == 40
    assert db.session.scalar(select(func.count(Claim.id))) == 120
    assert all(is_valid_npi(p.npi) for p in db.session.scalars(select(Provider)))

    # Every seeded claim obeys the same rules the API enforces.
    for claim in db.session.scalars(select(Claim)):
        assert claim.status in ALLOWED_TRANSITIONS
        assert claim.history[-1].to_status == claim.status
        if claim.status in ("approved", "paid"):
            assert claim.approved_amount is not None
            assert claim.approved_amount <= claim.billed_amount
        else:
            assert claim.approved_amount is None
        assert (claim.denial_reason is not None) == (claim.status == "denied")


def test_seed_does_nothing_on_a_database_with_data(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["seed"])
    second = runner.invoke(args=["seed"])
    assert "nothing was changed" in second.output
    assert db.session.scalar(select(func.count(User.id))) == 3


def test_seeded_user_can_sign_in(app, client):
    app.test_cli_runner().invoke(args=["seed"])
    response = client.post("/api/v1/auth/login", json={"email": "agent@example.com", "password": "Agent#12345"})
    assert response.status_code == 200


def test_create_admin(app):
    runner = app.test_cli_runner()
    args = ["create-admin", "--email", "Boss@Example.com", "--name", "The Boss", "--password", "Strong#Pass1"]
    assert runner.invoke(args=args).exit_code == 0
    user = db.session.scalar(select(User).where(User.email == "boss@example.com"))
    assert user.role == "admin"
    assert user.check_password("Strong#Pass1")

    duplicate = runner.invoke(args=args)
    assert duplicate.exit_code != 0
    assert "already exists" in duplicate.output


def test_create_admin_rejects_short_password(app):
    result = app.test_cli_runner().invoke(
        args=["create-admin", "--email", "a@example.com", "--name", "A", "--password", "short"]
    )
    assert result.exit_code != 0
    assert db.session.scalar(select(func.count(User.id))) == 0


def test_init_db_and_print_schema(app):
    runner = app.test_cli_runner()
    assert "created" in runner.invoke(args=["init-db"]).output
    schema = runner.invoke(args=["print-schema"]).output
    for table in ("users", "providers", "members", "claims", "claim_status_history", "claim_documents", "audit_logs"):
        assert f"CREATE TABLE {table}" in schema
