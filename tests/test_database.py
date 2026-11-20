"""Task 4: connection lifecycle (app/database.py)."""

import logging

import psycopg2
import pytest
from flask import g
from psycopg2.extras import RealDictCursor

from app import create_app, database
from app.database import DatabaseUnavailableError
from fake_driver import FAKE_DB_CONFIG

# --- unit tests with the fake driver --------------------------------------------------


def test_creating_the_app_does_not_open_a_connection(fake_app, fake_driver):
    assert fake_driver.connect_kwargs == []


def test_a_request_that_never_uses_the_database_never_connects(fake_app, fake_driver):
    fake_app.test_client().get("/does-not-exist")

    assert fake_driver.connect_kwargs == []


def test_init_app_registers_the_cleanup_hook(fake_app):
    assert database.close_db in fake_app.teardown_appcontext_funcs


def test_connect_passes_the_configuration_to_the_driver(fake_app, fake_driver):
    with fake_app.app_context():
        database.get_db()

    kwargs = fake_driver.connect_kwargs[0]
    assert kwargs["host"] == "db.example.org"
    assert kwargs["port"] == 5999
    assert kwargs["dbname"] == "cinema_test_fake"
    assert kwargs["user"] == "fake_user"
    assert kwargs["password"] == "pw-secret-123"
    assert kwargs["connect_timeout"] == 5
    assert kwargs["application_name"] == database.DEFAULT_APPLICATION_NAME
    assert kwargs["cursor_factory"] is RealDictCursor
    assert kwargs["options"] == "-c TimeZone=Asia/Seoul"


def test_timezone_follows_app_timezone(fake_driver):
    app = create_app("testing", dict(FAKE_DB_CONFIG, APP_TIMEZONE="UTC"))

    with app.app_context():
        database.get_db()

    assert fake_driver.last.kwargs["options"] == "-c TimeZone=UTC"


def test_password_and_user_are_omitted_when_not_configured(fake_driver):
    config = dict(FAKE_DB_CONFIG, DB_PASSWORD=None, DB_USER=None)
    app = create_app("testing", config)

    with app.app_context():
        database.get_db()

    assert "password" not in fake_driver.last.kwargs
    assert "user" not in fake_driver.last.kwargs


def test_application_name_is_configurable(fake_driver):
    app = create_app("testing", dict(FAKE_DB_CONFIG, DB_APPLICATION_NAME="custom_name"))

    with app.app_context():
        database.get_db()

    assert fake_driver.last.kwargs["application_name"] == "custom_name"


@pytest.mark.parametrize("name", [None, ""])
def test_missing_db_name_is_refused_without_connecting(fake_driver, name):
    # Without a name the driver would connect to a database named after the user.
    app = create_app("testing", dict(FAKE_DB_CONFIG, DB_NAME=name))

    with app.app_context():
        with pytest.raises(DatabaseUnavailableError, match="not configured"):
            database.get_db()

    assert fake_driver.connect_kwargs == []


def test_default_testing_app_has_no_database_and_cannot_connect(fake_driver):
    app = create_app("testing")

    with app.app_context():
        with pytest.raises(DatabaseUnavailableError):
            database.get_db()

    assert fake_driver.connect_kwargs == []


def test_connection_is_opened_lazily_and_reused_within_a_context(fake_app, fake_driver):
    with fake_app.app_context():
        assert fake_driver.connect_kwargs == []
        first = database.get_db()
        second = database.get_db()

        assert first is second
        assert len(fake_driver.connections) == 1


def test_each_context_gets_its_own_connection(fake_app, fake_driver):
    with fake_app.app_context():
        first = database.get_db()
    with fake_app.app_context():
        second = database.get_db()

    assert first is not second
    assert len(fake_driver.connections) == 2


def test_connection_is_rolled_back_then_closed_when_the_context_ends(fake_app, fake_driver):
    with fake_app.app_context():
        connection = database.get_db()
        assert connection.events == []

    assert connection.events == ["rollback", "close"]
    assert connection.closed


def test_cleanup_never_commits(fake_app, fake_driver):
    with fake_app.app_context():
        with database.get_db().cursor() as cur:
            cur.execute("INSERT INTO anything VALUES (1)")
        connection = fake_driver.last

    assert "commit" not in connection.events
    assert connection.events == ["rollback", "close"]


def test_connection_is_closed_even_if_the_request_fails(fake_app, fake_driver):
    class Boom(Exception):
        pass

    with pytest.raises(Boom):
        with fake_app.app_context():
            database.get_db()
            raise Boom()

    assert fake_driver.last.closed


def test_cleanup_without_a_connection_is_a_no_op(fake_app, fake_driver):
    with fake_app.app_context():
        pass

    assert fake_driver.connections == []


def test_failed_rollback_during_cleanup_still_closes_and_does_not_raise(
    fake_app, fake_driver, caplog
):
    with caplog.at_level(logging.WARNING, logger="app.database"):
        with fake_app.app_context():
            connection = database.get_db()
            connection.fail_rollback = psycopg2.OperationalError("server closed the connection")

    assert connection.events == ["rollback", "close"]
    assert connection.closed
    assert "rollback during cleanup failed" in caplog.text
    assert "server closed the connection" not in caplog.text


def test_failed_close_during_cleanup_does_not_raise(fake_app, fake_driver):
    with fake_app.app_context():
        database.get_db().fail_close = psycopg2.OperationalError("boom")

    assert fake_driver.last.events == ["rollback", "close"]


def test_cleanup_skips_rollback_on_an_already_closed_connection(fake_app, fake_driver):
    with fake_app.app_context():
        connection = database.get_db()
        connection.closed = 2  # the driver reports a lost connection this way

    assert connection.events == ["close"]


def test_a_lost_connection_is_replaced_on_the_next_call(fake_app, fake_driver):
    with fake_app.app_context():
        first = database.get_db()
        first.closed = 2
        second = database.get_db()

        assert second is not first
        assert g.db is second
    assert second.closed


def test_connection_failure_raises_a_safe_error_and_stores_nothing(fake_app, fake_driver):
    fake_driver.fail_with = psycopg2.OperationalError(
        'connection to server at "db.example.org" failed: password authentication failed '
        'for user "fake_user" pw-secret-123'
    )

    with fake_app.app_context():
        with pytest.raises(DatabaseUnavailableError) as excinfo:
            database.get_db()
        assert "db" not in g

    message = str(excinfo.value)
    for secret in ("db.example.org", "fake_user", "pw-secret-123", "cinema_test_fake"):
        assert secret not in message
    assert excinfo.value.__cause__ is None and excinfo.value.__suppress_context__


def test_connection_failure_is_logged_without_secrets(fake_app, fake_driver, caplog):
    fake_driver.fail_with = psycopg2.OperationalError("pw-secret-123 db.example.org fake_user")

    with caplog.at_level(logging.ERROR, logger="app.database"):
        with fake_app.app_context():
            with pytest.raises(DatabaseUnavailableError):
                database.get_db()

    assert "could not connect to PostgreSQL" in caplog.text
    assert "OperationalError" in caplog.text
    for secret in ("pw-secret-123", "db.example.org", "fake_user"):
        assert secret not in caplog.text


def test_next_call_retries_after_a_failed_connection(fake_app, fake_driver):
    fake_driver.fail_with = psycopg2.OperationalError("down")
    with fake_app.app_context():
        with pytest.raises(DatabaseUnavailableError):
            database.get_db()

        fake_driver.fail_with = None
        assert database.get_db() is fake_driver.last

    assert len(fake_driver.connect_kwargs) == 2


def test_any_driver_error_on_connect_is_reported_as_unavailable(fake_app, fake_driver):
    fake_driver.fail_with = psycopg2.ProgrammingError("bad option")

    with fake_app.app_context():
        with pytest.raises(DatabaseUnavailableError):
            database.get_db()


# --- integration tests against the disposable database --------------------------------


def scalar(cursor, sql, params=None):
    cursor.execute(sql, params)
    return next(iter(cursor.fetchone().values()))


def test_get_db_runs_real_queries(db_app):
    with db_app.app_context():
        with database.get_db().cursor() as cur:
            assert scalar(cur, "SELECT 1") == 1
            assert scalar(cur, "SELECT count(*) FROM movies") == 5
            assert scalar(cur, "SELECT count(*) FROM seats") == 250


def test_rows_are_dicts(db_app):
    with db_app.app_context():
        with database.get_db().cursor() as cur:
            cur.execute("SELECT 1 AS one, 'x' AS letter")
            assert cur.fetchone() == {"one": 1, "letter": "x"}


def test_connection_targets_the_test_database_with_the_expected_session_settings(
    db_app, cinema_test_db
):
    with db_app.app_context():
        with database.get_db().cursor() as cur:
            assert scalar(cur, "SELECT current_database()") == cinema_test_db.name
            assert scalar(cur, "SHOW TimeZone") == "Asia/Seoul"
            assert scalar(cur, "SHOW application_name") == db_app.config["DB_APPLICATION_NAME"]


def test_connection_is_reused_in_a_context_and_separate_across_contexts(db_app):
    with db_app.app_context():
        first = database.get_db()
        assert database.get_db() is first
        with first.cursor() as cur:
            first_pid = scalar(cur, "SELECT pg_backend_pid()")
    with db_app.app_context():
        with database.get_db().cursor() as cur:
            second_pid = scalar(cur, "SELECT pg_backend_pid()")

    assert first_pid != second_pid


def test_a_request_context_also_cleans_up(db_app, app_sessions):
    name = db_app.config["DB_APPLICATION_NAME"]
    with db_app.test_request_context():
        connection = database.get_db()
        assert app_sessions(name) == ["idle"]

    assert connection.closed
    assert app_sessions(name, expect_none=True) == []


def test_connection_is_closed_and_the_session_gone_after_the_context(db_app, app_sessions):
    name = db_app.config["DB_APPLICATION_NAME"]
    with db_app.app_context():
        connection = database.get_db()
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        assert len(app_sessions(name)) == 1

    assert connection.closed
    assert app_sessions(name, expect_none=True) == []


def test_session_is_closed_even_when_the_request_fails(db_app, app_sessions):
    name = db_app.config["DB_APPLICATION_NAME"]
    with pytest.raises(RuntimeError, match="request failed"):
        with db_app.app_context():
            with database.get_db().cursor() as cur:
                cur.execute("SELECT 1")
            raise RuntimeError("request failed")

    assert app_sessions(name, expect_none=True) == []


def test_uncommitted_work_is_discarded_by_cleanup(db_app, db_connection, app_sessions):
    name = db_app.config["DB_APPLICATION_NAME"]
    with db_app.app_context():
        with database.get_db().cursor() as cur:
            cur.execute("INSERT INTO movies(title, duration_minutes) VALUES ('Cleanup probe', 90)")
            assert scalar(cur, "SELECT count(*) FROM movies") == 6

    with db_connection.cursor() as cur:
        cur.execute("SELECT count(*) FROM movies WHERE title = 'Cleanup probe'")
        assert cur.fetchone()[0] == 0
    assert app_sessions(name, expect_none=True) == []  # nothing left "idle in transaction"


def test_an_unreachable_server_is_reported_as_unavailable(cinema_test_db):
    overrides = dict(cinema_test_db.app_config(), DB_PORT=1, DB_CONNECT_TIMEOUT=1)
    app = create_app("testing", overrides)

    with app.app_context():
        with pytest.raises(DatabaseUnavailableError) as excinfo:
            database.get_db()

    assert "127.0.0.1" not in str(excinfo.value)


def test_an_unknown_database_is_reported_as_unavailable(cinema_test_db, caplog):
    overrides = dict(cinema_test_db.app_config(), DB_NAME="cinema_test_no_such_database")
    app = create_app("testing", overrides)

    with caplog.at_level(logging.ERROR, logger="app.database"):
        with app.app_context():
            with pytest.raises(DatabaseUnavailableError):
                database.get_db()

    assert "could not connect to PostgreSQL" in caplog.text
    assert "cinema_test_no_such_database" not in caplog.text  # the driver message is not logged


def test_an_invalid_timezone_name_is_reported_as_unavailable(cinema_test_db):
    overrides = dict(cinema_test_db.app_config(), APP_TIMEZONE="Mars/Phobos")
    app = create_app("testing", overrides)

    with app.app_context():
        with pytest.raises(DatabaseUnavailableError):
            database.get_db()
