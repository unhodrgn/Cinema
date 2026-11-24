"""Read-only preflight for an existing PostgreSQL database before adopting baseline 0001."""
from pathlib import Path
import re

from app.core.config import DevelopmentConfig, load_environment
from app.core.database import connect

BASELINE = Path(__file__).resolve().parents[1] / "migrations/0001_baseline.sql"


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
    for kind, pattern, query in checks:
        cursor.execute(query)
        found = {next(iter(row.values())) for row in cursor.fetchall()}
        expected = set(re.findall(pattern, schema, re.MULTILINE))
        missing.extend(f"{kind} {name}" for name in sorted(expected - found))
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
            print("Missing or incompatible baseline objects:", ", ".join(missing))
            return 1
        print("Baseline inventory present. Compare schema definitions on a restored copy before adoption.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
