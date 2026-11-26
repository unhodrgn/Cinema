"""Read-only preflight for an existing PostgreSQL database against migrations 0001, 0003, 0004 and 0005."""
from pathlib import Path
import re

from app.core.config import DevelopmentConfig, load_environment
from app.core.database import connect

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
BASELINE = MIGRATIONS_DIR / "0001_baseline.sql"

MIGRATION_0003_CONSTRAINTS = (
    "bookings_id_showtime_key",
    "booking_seats_booking_showtime_fkey",
    "booking_seats_showtime_seat_key",
)
MIGRATION_0003_TRIGGERS = ("trg_bookings_z_version_showtime",)
MIGRATION_0005_INDEXES = ("users_username_lower_key",)
MIGRATION_0004_FINITE_CHECKS = (
    "showtimes_ticket_price_finite",
    "bookings_total_amount_finite",
    "booking_seats_price_at_booking_finite",
)


def missing_objects(cursor):
    schema = BASELINE.read_text(encoding="utf8")
    checks = (
        ("table", r"^CREATE TABLE (\w+)", "SELECT tablename FROM pg_tables WHERE schemaname='public'"),
        ("function", r"^CREATE FUNCTION (\w+)", "SELECT proname FROM pg_proc WHERE pronamespace='public'::regnamespace"),
        ("trigger", r"^CREATE (?:CONSTRAINT )?TRIGGER (\w+)",
         "SELECT tgname FROM pg_trigger JOIN pg_class ON tgrelid=pg_class.oid "
         "WHERE relnamespace='public'::regnamespace AND tgenabled IN ('O','A')"),
        ("index", r"^CREATE INDEX (\w+)", "SELECT indexname FROM pg_indexes WHERE schemaname='public'"),
        ("constraint", r"^\s*CONSTRAINT (\w+)", "SELECT conname FROM pg_constraint WHERE connamespace='public'::regnamespace"),
    )
    missing = []
    found_by_kind = {}
    for kind, pattern, query in checks:
        cursor.execute(query)
        found = {next(iter(row.values())) for row in cursor.fetchall()}
        found_by_kind[kind] = found
        expected = set(re.findall(pattern, schema, re.MULTILINE))
        missing.extend(f"{kind} {name}" for name in sorted(expected - found))

    for name in MIGRATION_0003_TRIGGERS:
        if name not in found_by_kind["trigger"]:
            missing.append(f"trigger {name}")

    for name in MIGRATION_0003_CONSTRAINTS:
        if name not in found_by_kind["constraint"]:
            missing.append(f"constraint {name}")

    cursor.execute(
        "SELECT conname FROM pg_constraint "
        "WHERE connamespace='public'::regnamespace AND contype='c' AND convalidated"
    )
    validated_checks = {next(iter(row.values())) for row in cursor.fetchall()}
    for name in MIGRATION_0004_FINITE_CHECKS:
        if name not in validated_checks:
            missing.append(f"validated check {name}")

    cursor.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_schema='public' "
        "AND table_name='bookings' AND column_name='total_amount' "
        "AND numeric_precision=12 AND numeric_scale=2"
    )
    if not cursor.fetchone():
        missing.append("column bookings.total_amount numeric(12,2)")

    cursor.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_schema='public' "
        "AND table_name='booking_seats' AND column_name='showtime_id' AND is_nullable='NO'"
    )
    if not cursor.fetchone():
        missing.append("column booking_seats.showtime_id NOT NULL")

    for name in MIGRATION_0005_INDEXES:
        if name not in found_by_kind["index"]:
            missing.append(f"index {name}")

    cursor.execute("SELECT 1 FROM pg_extension WHERE extname='btree_gist'")
    if not cursor.fetchone():
        missing.append("extension btree_gist")
    cursor.execute("SELECT 1 FROM information_schema.columns WHERE table_schema='public' "
                   "AND table_name='movies' AND column_name='poster_url' AND character_maximum_length=255")
    if not cursor.fetchone():
        missing.append("column movies.poster_url varchar(255)")
    return missing


def main():
    load_environment()
    config = DevelopmentConfig()
    connection = connect({name: getattr(config, name) for name in
                          ("DB_NAME", "DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_CONNECT_TIMEOUT", "APP_TIMEZONE")})
    try:
        connection.set_session(readonly=True)
        with connection.cursor() as cur:
            missing = missing_objects(cur)
        if missing:
            print("Missing or incompatible schema objects:", ", ".join(missing))
            return 1
        print("Schema inventory (0001-0005) present. Compare schema definitions and grants on a restored copy before adoption.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
