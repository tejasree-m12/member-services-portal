"""Command-line tasks, run with ``flask <command>``.

    flask init-db        create the tables
    flask seed           load synthetic demo data
    flask create-admin   create an admin account
    flask print-schema   print the MySQL CREATE TABLE statements
"""
import random
from datetime import date, timedelta
from decimal import Decimal

import click
from sqlalchemy import select
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateIndex, CreateTable

from .claims.service import transition_claim
from .extensions import db
from .models import Claim, ClaimStatusHistory, Member, Provider, User
from .validation import PLAN_TYPES, npi_check_digit

# Demo accounts created by `flask seed`. For local use only.
DEMO_USERS = [
    ("admin@example.com", "Avery Admin", "admin", "Admin#12345"),
    ("agent@example.com", "Jordan Agent", "agent", "Agent#12345"),
    ("viewer@example.com", "Riley Viewer", "viewer", "Viewer#12345"),
]

FIRST_NAMES = [
    "James", "Maria", "Robert", "Linda", "Michael", "Patricia", "David", "Jennifer", "Daniel", "Elizabeth",
    "Priya", "Wei", "Carlos", "Aisha", "Hannah", "Omar", "Grace", "Ethan", "Sofia", "Noah",
]
LAST_NAMES = [
    "Anderson", "Brooks", "Carter", "Diaz", "Edwards", "Foster", "Garcia", "Hughes", "Iyer", "Johnson",
    "Kim", "Lopez", "Miller", "Nguyen", "Owens", "Patel", "Quinn", "Rivera", "Smith", "Turner",
]
SPECIALTIES = ["Family Medicine", "Cardiology", "Dermatology", "Orthopedics", "Pediatrics", "Internal Medicine"]
CITIES = [("Chicago", "IL"), ("Springfield", "IL"), ("Louisville", "KY"), ("Indianapolis", "IN"), ("St. Louis", "MO")]
# (procedure code, diagnosis code, typical billed amount)
SERVICES = [
    ("99213", "E11.9", 150), ("99214", "I10", 220), ("93000", "R00.2", 95),
    ("80053", "Z00.00", 60), ("73030", "M25.511", 180), ("99395", "Z00.00", 250),
    ("11102", "D22.9", 320), ("G0439", "Z00.00", 175),
]
DENIAL_REASONS = [
    "Service not covered under the member's plan.",
    "Duplicate claim.",
    "Missing supporting documentation.",
]


def seed_database():
    """Fill an empty database with synthetic data. Nothing here is real."""
    rng = random.Random(42)  # fixed seed: everyone gets the same demo data

    users = {}
    for email, name, role, password in DEMO_USERS:
        user = User(email=email, full_name=name, role=role)
        user.set_password(password)
        db.session.add(user)
        users[role] = user

    providers = []
    for index in range(12):
        first_nine = f"1{rng.randrange(10**8):08d}"
        city, state = rng.choice(CITIES)
        provider = Provider(
            npi=first_nine + npi_check_digit(first_nine),
            name=f"Dr. {rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
            specialty=SPECIALTIES[index % len(SPECIALTIES)],
            city=city,
            state=state,
            phone=f"555-01{index:02d}",
            accepting_patients=index % 5 != 0,
        )
        providers.append(provider)
    db.session.add_all(providers)

    members = []
    for index in range(40):
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        members.append(
            Member(
                member_number=f"MBR-{10000 + index}",
                first_name=first,
                last_name=last,
                date_of_birth=date(1950, 1, 1) + timedelta(days=rng.randrange(20000)),
                email=f"{first}.{last}{index}@example.com".lower(),
                phone=f"555-02{index:02d}",
                plan_type=rng.choice(PLAN_TYPES),
                status="inactive" if index % 10 == 9 else "active",
                primary_provider=rng.choice(providers),
            )
        )
    db.session.add_all(members)
    db.session.flush()

    active_members = [m for m in members if m.status == "active"]
    for index in range(120):
        procedure, diagnosis, base_amount = rng.choice(SERVICES)
        billed = Decimal(base_amount + rng.randrange(0, 80)).quantize(Decimal("0.01"))
        claim = Claim(
            claim_number=f"CLM-{100000 + index}",
            member=rng.choice(active_members),
            provider=rng.choice(providers),
            service_date=date.today() - timedelta(days=rng.randrange(1, 180)),
            procedure_code=procedure,
            diagnosis_code=diagnosis,
            billed_amount=billed,
            status="submitted",
            created_by=users["agent"],
        )
        claim.history.append(
            ClaimStatusHistory(from_status=None, to_status="submitted", note="Claim created.", changed_by=users["agent"])
        )
        db.session.add(claim)

        # Walk each claim part of the way through the workflow, using the same
        # rules as the API, so the demo data is always in a valid state.
        outcome = rng.random()
        if outcome < 0.15:
            continue  # stays "submitted"
        transition_claim(claim, "in_review", users["agent"])
        if outcome < 0.30:
            continue  # stays "in_review"
        if outcome < 0.45:
            transition_claim(claim, "denied", users["agent"], denial_reason=rng.choice(DENIAL_REASONS))
            continue
        approved = (billed * Decimal(rng.choice(["0.80", "0.90", "1.00"]))).quantize(Decimal("0.01"))
        transition_claim(claim, "approved", users["agent"], approved_amount=approved)
        if outcome > 0.65:
            transition_claim(claim, "paid", users["admin"])

    db.session.commit()


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create all database tables."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("seed")
    def seed():
        """Load synthetic demo data (only into an empty database)."""
        if db.session.scalar(select(User).limit(1)) is not None:
            click.echo("Database already contains data; nothing was changed.")
            return
        seed_database()
        click.echo("Demo data loaded. Demo accounts:")
        for email, _, role, password in DEMO_USERS:
            click.echo(f"  {role:<7} {email}  /  {password}")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt="Full name")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(email, name, password):
        """Create an admin account (use this instead of `seed` on a real server)."""
        email = email.strip().lower()
        if len(password) < 8:
            raise click.ClickException("Password must be at least 8 characters.")
        if db.session.scalar(select(User).where(User.email == email)) is not None:
            raise click.ClickException("A user with this email already exists.")
        user = User(email=email, full_name=name.strip(), role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Admin account created for {email}.")

    @app.cli.command("print-schema")
    def print_schema():
        """Print the MySQL DDL for every table (used to produce database/schema.sql)."""
        dialect = mysql.dialect()
        for table in db.metadata.sorted_tables:
            click.echo(str(CreateTable(table).compile(dialect=dialect)).strip() + ";\n")
            for index in sorted(table.indexes, key=lambda i: i.name):
                click.echo(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";\n")
