"""Unit tests for the validation helpers. No database, no HTTP."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.validation import (
    ValidationError,
    clean_date,
    clean_diagnosis_code,
    clean_email,
    clean_money,
    clean_password,
    clean_procedure_code,
    clean_string,
    is_valid_npi,
    npi_check_digit,
)

pytestmark = pytest.mark.unit


class TestCleanString:
    def test_strips_whitespace(self):
        assert clean_string("  hello  ", "name", 20) == "hello"

    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_required_rejects_blank(self, value):
        with pytest.raises(ValidationError) as excinfo:
            clean_string(value, "name", 20)
        assert excinfo.value.field == "name"

    def test_optional_returns_none_for_blank(self):
        assert clean_string("", "name", 20, required=False) is None

    def test_rejects_too_long(self):
        with pytest.raises(ValidationError):
            clean_string("x" * 21, "name", 20)

    def test_rejects_non_string(self):
        with pytest.raises(ValidationError):
            clean_string(123, "name", 20)


class TestCleanEmail:
    def test_lowercases(self):
        assert clean_email("Someone@Example.COM") == "someone@example.com"

    @pytest.mark.parametrize("value", ["not-an-email", "a@b", "@example.com", "a b@example.com"])
    def test_rejects_invalid(self, value):
        with pytest.raises(ValidationError):
            clean_email(value)


class TestCleanDate:
    def test_parses_iso_date(self):
        assert clean_date("2026-02-28", "d") == date(2026, 2, 28)

    @pytest.mark.parametrize("value", ["28/02/2026", "2026-13-01", "2026-02-30", "yesterday"])
    def test_rejects_bad_format(self, value):
        with pytest.raises(ValidationError):
            clean_date(value, "d")

    def test_rejects_future_when_not_allowed(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        with pytest.raises(ValidationError):
            clean_date(tomorrow, "d", allow_future=False)

    def test_today_is_allowed(self):
        assert clean_date(date.today().isoformat(), "d", allow_future=False) == date.today()


class TestCleanMoney:
    @pytest.mark.parametrize(
        "value, expected",
        [("125.50", "125.50"), (125.5, "125.50"), (100, "100.00"), ("0.01", "0.01")],
    )
    def test_accepts_valid_amounts(self, value, expected):
        assert clean_money(value, "amount") == Decimal(expected)

    @pytest.mark.parametrize("value", ["abc", "-5", "0", "10.999", "NaN", "Infinity", True, "100000000"])
    def test_rejects_invalid_amounts(self, value):
        with pytest.raises(ValidationError):
            clean_money(value, "amount")

    def test_zero_allowed_when_requested(self):
        assert clean_money("0", "amount", allow_zero=True) == Decimal("0.00")

    def test_float_input_does_not_lose_precision(self):
        # 0.1 + 0.2 as floats is 0.30000000000000004; Decimals stay exact.
        assert clean_money(0.1, "a") + clean_money(0.2, "a") == Decimal("0.30")


class TestMedicalCodes:
    @pytest.mark.parametrize("code", ["99213", "g0439", "A0428"])
    def test_valid_procedure_codes(self, code):
        assert clean_procedure_code(code) == code.upper()

    @pytest.mark.parametrize("code", ["9921", "992133", "ABCDE", "9921A"])
    def test_invalid_procedure_codes(self, code):
        with pytest.raises(ValidationError):
            clean_procedure_code(code)

    @pytest.mark.parametrize("code", ["E11.9", "I10", "Z00.00", "m25.511", "S72.001A"])
    def test_valid_diagnosis_codes(self, code):
        assert clean_diagnosis_code(code) == code.upper()

    @pytest.mark.parametrize("code", ["11.9", "E1", "U07.1", "E11.", "E11.12345"])
    def test_invalid_diagnosis_codes(self, code):
        with pytest.raises(ValidationError):
            clean_diagnosis_code(code)


class TestNpi:
    @pytest.mark.parametrize("npi", ["1234567893", "1245319599"])
    def test_valid_npi(self, npi):
        assert is_valid_npi(npi)

    @pytest.mark.parametrize(
        "npi",
        [
            "1234567890",  # wrong check digit
            "1234567839",  # two digits swapped
            "123456789",  # too short
            "12345678931",  # too long
            "12345A7893",  # not all digits
            "",
            None,
            1234567893,  # a number, not a string
        ],
    )
    def test_invalid_npi(self, npi):
        assert not is_valid_npi(npi)

    def test_check_digit_makes_a_valid_npi(self):
        assert npi_check_digit("123456789") == "3"
        assert is_valid_npi("987654321" + npi_check_digit("987654321"))


class TestCleanPassword:
    def test_accepts_long_enough(self):
        assert clean_password("longenough") == "longenough"

    @pytest.mark.parametrize("value", ["short", "", None, 12345678])
    def test_rejects_weak_or_invalid(self, value):
        with pytest.raises(ValidationError):
            clean_password(value)
