"""Run the database suites on a database provisioned by this process."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

from dotenv import dotenv_values

from disposable_db import (
    DisposableDatabase, CURRENT_SCHEMA_PATHS, SEED_PATH, read_forbidden_names, read_server_settings,
)

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-db", action="store_true")
    args = parser.parse_args()
    dotenv = dotenv_values(os.environ.get("CINEMA_TEST_ENV_FILE", HERE.parents[1] / ".env"))
    settings = read_server_settings(os.environ, dotenv)
    database = DisposableDatabase(settings, forbidden_names=read_forbidden_names(os.environ, dotenv))
    try:
        database.create()
        for migration in CURRENT_SCHEMA_PATHS:
            database.apply_sql_file(migration)
        database.apply_sql_file(SEED_PATH)
        env = dict(os.environ, PGHOST=settings.host, PGPORT=str(settings.port),
                   PGDATABASE=database.name, PGCLIENTENCODING="UTF8")
        if settings.user:
            env["PGUSER"] = settings.user
        if settings.password:
            env["PGPASSWORD"] = settings.password
        checks = {
            "money_domain.sql": [r"MONEY DOMAIN CHECKS PASSED"],
            "integrity_tests.sql": [r"ALL [1-9]\d* CHECKS PASSED"],
            "reconciliation_probes.sql": [r"SUMMARY: [1-9]\d* MATCH, 0 MISMATCH", r"\[P16\] MATCH\s+failed commit left 0 booking rows"],
        }
        for filename, expected in checks.items():
            result = subprocess.run(
                ["psql", "-X", "-v", "ON_ERROR_STOP=1", "-f", str(HERE / "sql" / filename)],
                env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf8",
            )
            if result.returncode or not all(re.search(pattern, result.stdout) for pattern in expected):
                sys.stderr.write(result.stdout)
                return 1
            print(filename, "passed", flush=True)
        return subprocess.run([sys.executable, str(HERE / "test_booking_concurrency.py")], env=env).returncode
    finally:
        if database.created:
            if args.keep_db:
                print("Kept test database:", database.name)
            else:
                database.drop()


if __name__ == "__main__":
    raise SystemExit(main())
