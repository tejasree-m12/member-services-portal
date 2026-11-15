"""Unit tests for model helpers."""
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.models import User, iso, money, new_claim_number, new_member_number

pytestmark = pytest.mark.unit


def test_password_is_hashed_not_stored():
    user = User(email="a@b.co", full_name="A", role="viewer")
    user.set_password("Secret#123")
    assert user.password_hash != "Secret#123"
    assert user.check_password("Secret#123")
    assert not user.check_password("secret#123")


def test_same_password_gives_different_hashes():
    # Each hash includes a random salt, so equal passwords do not look equal
    # in the database.
    first, second = User(), User()
    first.set_password("Secret#123")
    second.set_password("Secret#123")
    assert first.password_hash != second.password_hash


def test_money_keeps_two_decimals_as_string():
    assert money(Decimal("12.5")) == "12.50"
    assert money(None) is None


def test_iso_formats():
    assert iso(date(2026, 3, 1)) == "2026-03-01"
    assert iso(datetime(2026, 3, 1, 14, 5, 9)) == "2026-03-01T14:05:09Z"
    assert iso(None) is None


def test_generated_numbers_have_prefix_and_are_unique():
    assert new_member_number().startswith("MBR-")
    assert new_claim_number().startswith("CLM-")
    assert len({new_claim_number() for _ in range(200)}) == 200
