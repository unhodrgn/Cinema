"""T2: scripts/set_demo_passwords.py, the setup-only way to give seeded accounts known passwords.

Run as a real subprocess against a private PostgreSQL clone. Needs a disposable PostgreSQL
(explicit TEST_DB_PORT); the argument/configuration tests need none.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from app import passwords
from helpers import ApiClient

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "set_demo_passwords.py"
NEW_PASSWORD = "Demo-Pass-#1 (setup test)"

RUNTIME_AND_LIBPQ = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD", "PGHOST", "PGPORT",
                     "PGUSER", "PGDATABASE", "SETUP_DB_HOST", "SETUP_DB_PORT", "SETUP_DB_NAME",
                     "SETUP_DB_USER", "SETUP_DB_PASSWORD", "SETUP_NEW_PASSWORD")


def clean_env(**extra):
    env = {key: value for key, value in os.environ.items() if key.upper() not in RUNTIME_AND_LIBPQ}
    env.update(extra)
    return env


def setup_env(db, **extra):
    config = db.app_config()
    env = clean_env(SETUP_DB_HOST=str(config["DB_HOST"]), SETUP_DB_PORT=str(config["DB_PORT"]),
                    SETUP_DB_NAME=config["DB_NAME"], SETUP_DB_USER=config["DB_USER"])
    if config.get("DB_PASSWORD"):
        env["SETUP_DB_PASSWORD"] = config["DB_PASSWORD"]
    env.update(extra)
    return env


def run_script(args, env, stdin=subprocess.DEVNULL, input_text=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=120,
                          stdin=None if input_text is not None else stdin, input=input_text)


def hashes(connection):
    with connection.cursor() as cur:
        cur.execute("SELECT username, password_hash, role FROM users ORDER BY username")
        rows = {row[0]: (row[1], row[2]) for row in cur.fetchall()}
    connection.rollback()
    return rows


# --- configuration and input (no database needed) -----------------------------------------


def test_the_script_never_reads_the_runtime_or_libpq_connection_settings():
    source = SCRIPT.read_text(encoding="utf-8")
    code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
    # drop the module docstring (it explains what is NOT used)
    code = code.split('"""', 2)[2]

    assert not re.search(r"(?<!SETUP_)\bDB_(HOST|PORT|NAME|USER|PASSWORD)\b", code)
    assert not re.search(r"\bPG(HOST|PORT|USER|DATABASE|PASSWORD)\b", code)
    assert "app.database" not in code and "app.config" not in code and "create_app" not in code
    assert not re.search(r"\.env\b|dotenv", code)  # never reads a .env file (os.environ is fine)
    assert "5432" not in code and "localhost" not in code.lower()  # no default target


@pytest.mark.parametrize(
    "missing",
    ["SETUP_DB_HOST", "SETUP_DB_PORT", "SETUP_DB_NAME", "SETUP_DB_USER"],
)
def test_every_connection_setting_is_required_with_no_default(missing):
    env = clean_env(SETUP_DB_HOST="127.0.0.1", SETUP_DB_PORT="1", SETUP_DB_NAME="x", SETUP_DB_USER="y",
                    SETUP_NEW_PASSWORD="whatever")
    del env[missing]

    result = run_script(["--username", "admin_demo", "--yes"], env)

    assert result.returncode == 2
    assert missing in result.stderr
    assert "Traceback" not in result.stderr


def test_the_runtime_credentials_are_never_used_as_a_fallback():
    # A complete set of runtime (DB_*) and libpq (PG*) settings, but no SETUP_DB_*: refuse.
    env = clean_env(DB_HOST="127.0.0.1", DB_PORT="1", DB_NAME="cinema_runtime", DB_USER="runtime",
                    DB_PASSWORD="runtime-secret", PGHOST="127.0.0.1", PGPORT="1", PGUSER="runtime",
                    PGDATABASE="cinema_runtime", SETUP_NEW_PASSWORD="whatever")

    result = run_script(["--username", "admin_demo", "--yes"], env)

    assert result.returncode == 2
    assert "SETUP_DB_HOST" in result.stderr and "never falls back" in result.stderr
    assert "runtime-secret" not in result.stdout + result.stderr


@pytest.mark.parametrize("port", ["abc", "0", "70000", "-1", "5432.5"])
def test_an_invalid_port_is_refused(port):
    env = clean_env(SETUP_DB_HOST="127.0.0.1", SETUP_DB_PORT=port, SETUP_DB_NAME="x", SETUP_DB_USER="y",
                    SETUP_NEW_PASSWORD="whatever")

    result = run_script(["--username", "admin_demo", "--yes"], env)

    assert result.returncode == 2 and "SETUP_DB_PORT" in result.stderr


def test_at_least_one_username_is_required():
    result = run_script([], clean_env(SETUP_NEW_PASSWORD="x"))

    assert result.returncode == 2  # argparse usage error


def test_without_a_password_source_the_script_stops_instead_of_hanging():
    env = clean_env(SETUP_DB_HOST="127.0.0.1", SETUP_DB_PORT="1", SETUP_DB_NAME="x", SETUP_DB_USER="y")

    result = run_script(["--username", "admin_demo", "--yes"], env)

    assert result.returncode == 2
    assert "no password given" in result.stderr


@pytest.mark.parametrize("password, message", [("p" * 257, "at most 256"), ("", "no password given")])
def test_unusable_passwords_are_refused_before_any_connection(password, message):
    env = clean_env(SETUP_DB_HOST="127.0.0.1", SETUP_DB_PORT="1", SETUP_DB_NAME="x", SETUP_DB_USER="y",
                    SETUP_NEW_PASSWORD=password)

    result = run_script(["--username", "admin_demo", "--yes"], env)

    assert result.returncode == 2
    assert message in result.stderr
    assert "p" * 257 not in result.stderr


# --- against a private database -----------------------------------------------------------


def test_it_sets_known_passwords_that_then_work_through_the_api(fresh_db, fresh_app, fresh_connection):
    before = hashes(fresh_connection)

    result = run_script(["--username", "admin_demo", "--username", "customer_demo", "--yes"],
                        setup_env(fresh_db, SETUP_NEW_PASSWORD=NEW_PASSWORD))

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("Password updated for: admin_demo, customer_demo")
    after = hashes(fresh_connection)
    for name in ("admin_demo", "customer_demo"):
        assert after[name][0] != before[name][0]
        assert after[name][0].startswith("pbkdf2:sha256:600000$")
        assert passwords.verify_password(after[name][0], NEW_PASSWORD)
        assert after[name][1] == before[name][1]  # the role is untouched
    assert after["customer_demo2"] == before["customer_demo2"]  # not named: unchanged

    api = ApiClient(fresh_app.test_client())
    admin = api.post("/api/auth/login", json={"username": "admin_demo", "password": NEW_PASSWORD})
    customer = api.post("/api/auth/login", json={"username": "customer_demo", "password": NEW_PASSWORD})
    untouched = api.post("/api/auth/login", json={"username": "customer_demo2", "password": NEW_PASSWORD})
    assert admin.status_code == 200 and admin.get_json()["user"]["role"] == "ADMIN"
    assert customer.status_code == 200 and customer.get_json()["user"]["role"] == "CUSTOMER"
    assert untouched.status_code == 401


def test_neither_the_password_nor_a_hash_is_ever_printed(fresh_db, fresh_connection):
    result = run_script(["--username", "admin_demo", "--yes"], setup_env(fresh_db, SETUP_NEW_PASSWORD=NEW_PASSWORD))

    assert result.returncode == 0
    new_hash = hashes(fresh_connection)["admin_demo"][0]
    for stream in (result.stdout, result.stderr):
        assert NEW_PASSWORD not in stream and new_hash not in stream and "pbkdf2" not in stream


def test_an_unknown_account_changes_nothing_not_even_the_valid_ones(fresh_db, fresh_connection):
    before = hashes(fresh_connection)

    result = run_script(["--username", "admin_demo", "--username", "nobody_here", "--yes"],
                        setup_env(fresh_db, SETUP_NEW_PASSWORD=NEW_PASSWORD))

    assert result.returncode == 1
    assert "nobody_here" in result.stderr and "nothing was changed" in result.stderr
    assert hashes(fresh_connection) == before  # all-or-nothing


def test_it_only_updates_existing_accounts_it_never_creates_or_promotes(fresh_db, fresh_connection):
    before = hashes(fresh_connection)

    run_script(["--username", "customer_demo", "--yes"], setup_env(fresh_db, SETUP_NEW_PASSWORD=NEW_PASSWORD))
    after = hashes(fresh_connection)

    assert set(after) == set(before)
    assert {name: role for name, (_, role) in after.items()} == {name: role for name, (_, role) in before.items()}


def test_confirmation_by_typing_the_database_name(fresh_db, fresh_connection):
    before = hashes(fresh_connection)
    env = setup_env(fresh_db, SETUP_NEW_PASSWORD=NEW_PASSWORD)

    refused = run_script(["--username", "admin_demo"], env, input_text="some other database\n")
    assert refused.returncode == 1 and "not confirmed" in refused.stderr
    assert hashes(fresh_connection) == before
    no_answer = run_script(["--username", "admin_demo"], env)  # stdin closed: no answer
    assert no_answer.returncode == 1
    assert hashes(fresh_connection) == before

    accepted = run_script(["--username", "admin_demo"], env, input_text=fresh_db.name + "\n")
    assert accepted.returncode == 0
    assert hashes(fresh_connection)["admin_demo"][0] != before["admin_demo"][0]
    assert fresh_db.name in accepted.stdout  # the target is always shown before anything happens


def test_a_database_failure_prints_only_the_sqlstate(fresh_db):
    env = setup_env(fresh_db, SETUP_NEW_PASSWORD=NEW_PASSWORD, SETUP_DB_PORT="1")  # nothing listens there

    result = run_script(["--username", "admin_demo", "--yes"], env)

    assert result.returncode == 1
    assert "database error" in result.stderr and "nothing was changed" in result.stderr
    assert "Traceback" not in result.stderr
    assert NEW_PASSWORD not in result.stdout + result.stderr


def test_a_role_without_update_permission_cannot_change_anything(fresh_db, fresh_connection, postgres_settings):
    # The point of keeping this separate: a runtime-style role (no UPDATE on users) is refused
    # by PostgreSQL itself, and the script reports it without changing a thing.
    role = "t2_runtime_probe"
    with fresh_connection.cursor() as cur:
        cur.execute(f"CREATE ROLE {role} LOGIN")
        cur.execute(f"GRANT CONNECT ON DATABASE \"{fresh_db.name}\" TO {role}")
        cur.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
        cur.execute(f"GRANT SELECT ON users TO {role}")
    fresh_connection.commit()
    before = hashes(fresh_connection)
    try:
        result = run_script(["--username", "admin_demo", "--yes"],
                            setup_env(fresh_db, SETUP_NEW_PASSWORD=NEW_PASSWORD, SETUP_DB_USER=role))
        assert result.returncode == 1
        assert "42501" in result.stderr  # insufficient_privilege
        assert hashes(fresh_connection) == before
    finally:
        with fresh_connection.cursor() as cur:
            cur.execute(f"REVOKE ALL ON users FROM {role}")
            cur.execute(f"REVOKE ALL ON SCHEMA public FROM {role}")
            cur.execute(f"REVOKE ALL ON DATABASE \"{fresh_db.name}\" FROM {role}")
            cur.execute(f"DROP ROLE {role}")
        fresh_connection.commit()
