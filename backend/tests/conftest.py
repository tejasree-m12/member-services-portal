"""Shared pytest fixtures.

A fixture is setup code that pytest runs for any test that names it as an
argument. Every test here gets a brand-new empty database, so tests cannot
affect each other and can run in any order.
"""
from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import Claim, ClaimStatusHistory, Member, Provider, User

PASSWORD = "Password#123"
VALID_NPI = "1234567893"  # passes the NPI check-digit test
OTHER_VALID_NPI = "1245319599"


@pytest.fixture
def app(tmp_path):
    class Config(TestConfig):
        UPLOAD_DIR = str(tmp_path / "uploads")

    app = create_app(Config)
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def make_user(role, email=None, active=True):
    user = User(email=email or f"{role}@test.local", full_name=f"Test {role.title()}", role=role, is_active=active)
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, email, password=PASSWORD):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.get_json()
    return {"Authorization": "Bearer " + response.get_json()["access_token"]}


@pytest.fixture
def admin_user(app):
    return make_user("admin")


@pytest.fixture
def agent_user(app):
    return make_user("agent")


@pytest.fixture
def viewer_user(app):
    return make_user("viewer")


@pytest.fixture
def admin_headers(client, admin_user):
    return login(client, admin_user.email)


@pytest.fixture
def agent_headers(client, agent_user):
    return login(client, agent_user.email)


@pytest.fixture
def viewer_headers(client, viewer_user):
    return login(client, viewer_user.email)


@pytest.fixture
def provider(app):
    provider = Provider(
        npi=VALID_NPI, name="Dr. Test Provider", specialty="Family Medicine", city="Chicago", state="IL"
    )
    db.session.add(provider)
    db.session.commit()
    return provider


@pytest.fixture
def member(app, provider):
    member = Member(
        first_name="Sample",
        last_name="Member",
        date_of_birth=date(1985, 6, 15),
        email="sample.member@example.com",
        plan_type="PPO",
        status="active",
        primary_provider=provider,
    )
    db.session.add(member)
    db.session.commit()
    return member


@pytest.fixture
def claim(app, member, provider, agent_user):
    claim = Claim(
        member=member,
        provider=provider,
        service_date=date(2026, 1, 10),
        procedure_code="99213",
        diagnosis_code="E11.9",
        billed_amount=Decimal("200.00"),
        status="submitted",
        created_by=agent_user,
    )
    claim.history.append(ClaimStatusHistory(from_status=None, to_status="submitted", changed_by=agent_user))
    db.session.add(claim)
    db.session.commit()
    return claim
