"""Input validation helpers.

These are plain functions with no Flask or database dependency, which makes
them easy to unit test. Each one either returns a cleaned value or raises
``ValidationError`` with a message for one field.
"""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# CPT codes are 5 digits; HCPCS Level II codes are a letter followed by 4 digits.
PROCEDURE_CODE_RE = re.compile(r"^(\d{5}|[A-Z]\d{4})$")
# ICD-10-CM: letter (not U), digit, alphanumeric, optional "." + 1-4 alphanumerics.
DIAGNOSIS_CODE_RE = re.compile(r"^[A-TV-Z]\d[0-9A-Z](\.[0-9A-Z]{1,4})?$")
PHONE_RE = re.compile(r"^[0-9+\-() .]{7,20}$")

PLAN_TYPES = ("HMO", "PPO", "EPO", "Medicare Advantage")
MEMBER_STATUSES = ("active", "inactive")
USER_ROLES = ("admin", "agent", "viewer")


class ValidationError(Exception):
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field
        self.message = message


def clean_string(value, field, max_length, required=True):
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValidationError(field, "This field is required.")
        return None
    if not isinstance(value, str):
        raise ValidationError(field, "Must be text.")
    value = value.strip()
    if len(value) > max_length:
        raise ValidationError(field, f"Must be at most {max_length} characters.")
    return value


def clean_email(value, field="email", required=True):
    value = clean_string(value, field, 255, required)
    if value is None:
        return None
    value = value.lower()
    if not EMAIL_RE.match(value):
        raise ValidationError(field, "Enter a valid email address.")
    return value


def clean_phone(value, field="phone", required=False):
    value = clean_string(value, field, 20, required)
    if value is not None and not PHONE_RE.match(value):
        raise ValidationError(field, "Enter a valid phone number.")
    return value


def clean_choice(value, field, choices, required=True):
    if value is None or value == "":
        if required:
            raise ValidationError(field, "This field is required.")
        return None
    if value not in choices:
        raise ValidationError(field, "Must be one of: " + ", ".join(choices) + ".")
    return value


def clean_date(value, field, required=True, allow_future=True):
    """Parse an ISO date string (YYYY-MM-DD)."""
    if value is None or value == "":
        if required:
            raise ValidationError(field, "This field is required.")
        return None
    try:
        parsed = datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(field, "Use the date format YYYY-MM-DD.")
    if not allow_future and parsed > date.today():
        raise ValidationError(field, "Date cannot be in the future.")
    return parsed


def clean_money(value, field, required=True, allow_zero=False):
    """Parse a money amount into a Decimal with two decimal places.

    Money is never handled as a float: 0.1 + 0.2 != 0.3 in binary floating
    point, and rounding errors are not acceptable in claims data.
    """
    if value is None or value == "":
        if required:
            raise ValidationError(field, "This field is required.")
        return None
    if isinstance(value, bool):
        raise ValidationError(field, "Enter a valid amount.")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError(field, "Enter a valid amount.")
    if not amount.is_finite():
        raise ValidationError(field, "Enter a valid amount.")
    if amount != amount.quantize(Decimal("0.01")):
        raise ValidationError(field, "Use at most two decimal places.")
    if amount < 0 or (amount == 0 and not allow_zero):
        raise ValidationError(field, "Amount must be greater than zero.")
    if amount > Decimal("99999999.99"):
        raise ValidationError(field, "Amount is too large.")
    return amount.quantize(Decimal("0.01"))


def clean_procedure_code(value, field="procedure_code"):
    value = clean_string(value, field, 5)
    value = value.upper()
    if not PROCEDURE_CODE_RE.match(value):
        raise ValidationError(field, "Enter a 5-character CPT or HCPCS code, e.g. 99213.")
    return value


def clean_diagnosis_code(value, field="diagnosis_code"):
    value = clean_string(value, field, 8)
    value = value.upper()
    if not DIAGNOSIS_CODE_RE.match(value):
        raise ValidationError(field, "Enter a valid ICD-10 code, e.g. E11.9.")
    return value


def is_valid_npi(npi):
    """Check a National Provider Identifier.

    An NPI is 10 digits. The last digit is a check digit calculated with the
    Luhn algorithm over the first nine digits prefixed with 80840 (the prefix
    for US health identifiers). This catches typing mistakes such as a wrong
    digit or two digits swapped.
    """
    if not isinstance(npi, str) or not re.fullmatch(r"\d{10}", npi):
        return False
    digits = [int(ch) for ch in "80840" + npi]
    total = 0
    # Walk right to left, doubling every second digit (starting with the one
    # next to the check digit).
    for position, digit in enumerate(reversed(digits)):
        if position % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def npi_check_digit(first_nine):
    """Return the check digit that makes ``first_nine`` a valid NPI."""
    for candidate in "0123456789":
        if is_valid_npi(first_nine + candidate):
            return candidate
    raise ValueError("first_nine must be nine digits")


def clean_npi(value, field="npi"):
    value = clean_string(value, field, 10)
    if not is_valid_npi(value):
        raise ValidationError(field, "Enter a valid 10-digit NPI.")
    return value


def clean_password(value, field="password"):
    if not isinstance(value, str) or len(value) < 8:
        raise ValidationError(field, "Password must be at least 8 characters.")
    if len(value) > 128:
        raise ValidationError(field, "Password must be at most 128 characters.")
    return value
