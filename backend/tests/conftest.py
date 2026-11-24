import os
import time
import uuid

import psycopg2
import pytest
from dotenv import dotenv_values

import disposable_db
from app import create_app
from app.core import config
from fake_driver import FAKE_DB_CONFIG, FakeDriver

# Every variable the application configuration reads.
CONFIG_VARIABLES = (
    "SECRET_KEY",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "DB_CONNECT_TIMEOUT",
    "APP_TIMEZONE",
    "FLASK_DEBUG",
    "CORS_ALLOWED_ORIGINS",
    "AUTH_TOKEN_MAX_AGE_SECONDS",
)

# Snapshots taken before any fixture runs, so the per-test environment isolation below
# cannot hide how the PostgreSQL test server is configured. The .env file is only read,
# never loaded into os.environ.
_ORIGINAL_ENVIRON = dict(os.environ)
_DOTENV_VALUES = dotenv_values(os.environ.get("CINEMA_TEST_ENV_FILE", config.PROJECT_ROOT / ".env"))


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    """Run every test without the developer's real settings.

    Removes the configuration variables from the process environment and points the
    .env lookup at a file that does not exist, so tests never read a real .env.
    """
    for name in CONFIG_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config, "DOTENV_PATH", tmp_path / "no-such.env")


# --- disposable PostgreSQL database ---------------------------------------------------
#
# The test server is chosen explicitly: TEST_DB_PORT is required (there is no fallback to
# DB_PORT, PGPORT or 5432) and TEST_DB_HOST defaults to 127.0.0.1. The role comes from
# TEST_DB_ADMIN_USER / DB_USER and TEST_DB_ADMIN_PASSWORD / DB_PASSWORD (environment
# first, then .env). DB_NAME is never used for connecting; it is only read to make sure
# it is refused as a test database. See tests/disposable_db.py for the safety rules.


@pytest.fixture(scope="session")
def postgres_settings():
    """Test server settings; skips the requesting tests when TEST_DB_PORT is not set.

    Nothing connects before this fixture succeeds, so a missing port never causes a
    connection attempt.
    """
    try:
        return disposable_db.read_server_settings(_ORIGINAL_ENVIRON, _DOTENV_VALUES)
    except disposable_db.PortNotConfiguredError as error:
        pytest.skip(str(error))


@pytest.fixture(scope="session")
def cinema_test_db(postgres_settings):
    """A disposable ``cinema_test_*`` database with schema.sql and seed.sql applied.

    Created once per test session and dropped at the end. Skips the requesting tests
    if no PostgreSQL server can be reached; every other problem fails loudly.
    """
    try:
        disposable_db.check_server(postgres_settings)
    except psycopg2.OperationalError:
        if os.environ.get("CINEMA_REQUIRE_LIVE_DB") == "1":
            raise
        pytest.skip(
            f"PostgreSQL test server not reachable at "
            f"{postgres_settings.host}:{postgres_settings.port} "
            "(check TEST_DB_HOST, TEST_DB_PORT, TEST_DB_ADMIN_USER and TEST_DB_ADMIN_PASSWORD)"
        )
    forbidden = disposable_db.read_forbidden_names(_ORIGINAL_ENVIRON, _DOTENV_VALUES)
    with disposable_db.provision_database(
        postgres_settings, disposable_db.SCHEMA_PATH, disposable_db.SEED_PATH, forbidden
    ) as database:
        yield database


@pytest.fixture(scope="session")
def cinema_template_db(postgres_settings):
    """A seeded ``cinema_test_*`` database used ONLY as a template for per-test clones.

    Nothing may ever connect to it (PostgreSQL refuses to clone a database that is in
    use), so no fixture hands out a connection to it. Created once per session by the
    same safe provisioning as ``cinema_test_db`` and dropped at the end.
    """
    try:
        disposable_db.check_server(postgres_settings)
    except psycopg2.OperationalError:
        if os.environ.get("CINEMA_REQUIRE_LIVE_DB") == "1":
            raise
        pytest.skip(
            f"PostgreSQL test server not reachable at "
            f"{postgres_settings.host}:{postgres_settings.port}"
        )
    forbidden = disposable_db.read_forbidden_names(_ORIGINAL_ENVIRON, _DOTENV_VALUES)
    with disposable_db.provision_database(
        postgres_settings, disposable_db.SCHEMA_PATH, disposable_db.SEED_PATH, forbidden
    ) as template:
        yield template


@pytest.fixture
def fresh_db(cinema_template_db):
    """A private, freshly seeded database for ONE test (opt-in: about 0.4 s to create and drop).

    Use it for tests that commit bookings: a booking can never be deleted and a booked
    screening can never be edited (D2), so such tests must not share a database. The clone
    is dropped after the test, whether it passed or failed.
    """
    forbidden = disposable_db.read_forbidden_names(_ORIGINAL_ENVIRON, _DOTENV_VALUES)
    with disposable_db.clone_database(cinema_template_db, forbidden) as clone:
        yield clone


@pytest.fixture
def fresh_connection(fresh_db):
    """An owner connection to the per-test clone (also usable by the time-travel helpers)."""
    connection = fresh_db.connect()
    try:
        yield connection
    finally:
        if not connection.closed:
            connection.rollback()
            connection.close()


@pytest.fixture
def fresh_app(fresh_db):
    """A testing app connected to the per-test clone, with a unique application_name."""
    overrides = dict(fresh_db.app_config())
    overrides["DB_APPLICATION_NAME"] = "cinema_flask_test_" + uuid.uuid4().hex[:8]
    return create_app("testing", overrides)


@pytest.fixture
def db_connection(cinema_test_db):
    """A connection to the disposable database; uncommitted work is rolled back.

    A test that commits is responsible for undoing it: the database is shared by the
    whole session.
    """
    connection = cinema_test_db.connect()
    try:
        yield connection
    finally:
        if not connection.closed:
            connection.rollback()
            connection.close()


@pytest.fixture
def db_app_config(cinema_test_db):
    """Overrides for ``create_app("testing", overrides)`` that target the test database."""
    return cinema_test_db.app_config()


# --- application fixtures -------------------------------------------------------------


@pytest.fixture
def fake_driver(monkeypatch):
    """Replace ``psycopg2.connect`` with a recording fake; no server is involved."""
    driver = FakeDriver()
    monkeypatch.setattr(psycopg2, "connect", driver.connect)
    return driver


@pytest.fixture
def fake_app(fake_driver):
    """A testing app configured for the fake driver (see FAKE_DB_CONFIG)."""
    return create_app("testing", FAKE_DB_CONFIG)


@pytest.fixture
def db_app(cinema_test_db):
    """A testing app connected to the disposable database.

    Its connections carry a unique application_name so tests can look for them (and for
    leaked sessions) in pg_stat_activity.
    """
    overrides = dict(cinema_test_db.app_config())
    overrides["DB_APPLICATION_NAME"] = "cinema_flask_test_" + uuid.uuid4().hex[:8]
    return create_app("testing", overrides)


@pytest.fixture
def app_sessions(cinema_test_db):
    """``app_sessions(application_name)`` -> states of that application's open sessions.

    Waits briefly for the server to finish closing sessions that were just closed.
    """

    def states(application_name, expect_none=False):
        deadline = time.monotonic() + 3.0
        while True:
            connection = cinema_test_db.connect()
            try:
                with connection.cursor() as cur:
                    cur.execute(
                        "SELECT state FROM pg_stat_activity WHERE application_name = %s",
                        (application_name,),
                    )
                    found = [row[0] for row in cur.fetchall()]
            finally:
                connection.close()
            if not (expect_none and found) or time.monotonic() > deadline:
                return found
            time.sleep(0.05)

    return states
