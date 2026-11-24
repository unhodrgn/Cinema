"""Task 6: health-check endpoints (app/health.py)."""

import logging

import psycopg2
import pytest

from app import create_app

HEALTHY = {"status": "ok", "database": "ok"}
UNAVAILABLE = {"status": "unavailable", "database": "unavailable"}
SECRETS = ["db.example.org", "5999", "cinema_test_fake", "fake_user", "pw-secret-123"]


def assert_no_secrets(text):
    for secret in SECRETS:
        assert secret not in text


# --- /health: no database involved ----------------------------------------------------


def test_health_reports_ok_without_touching_the_database(fake_app, fake_driver):
    fake_driver.fail_with = psycopg2.OperationalError("down")

    response = fake_app.test_client().get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    assert fake_driver.connect_kwargs == []


def test_health_endpoints_need_no_login_and_set_no_cookie(fake_app):
    for path in ("/health", "/health/db"):
        response = fake_app.test_client().get(path)

        assert "Set-Cookie" not in response.headers


def test_health_responses_are_json_and_not_cacheable(fake_app):
    for path in ("/health", "/health/db"):
        response = fake_app.test_client().get(path)

        assert response.mimetype == "application/json"
        assert response.headers["Cache-Control"] == "no-store"


def test_only_get_is_allowed(fake_app):
    client = fake_app.test_client()

    assert client.post("/health").status_code == 405
    assert client.post("/health/db").status_code == 405
    assert client.head("/health").status_code == 200


# --- /health/db with the fake driver --------------------------------------------------


def test_database_available_gives_200(fake_app, fake_driver):
    response = fake_app.test_client().get("/health/db")

    assert response.status_code == 200
    assert response.get_json() == HEALTHY
    assert_no_secrets(response.get_data(as_text=True))


def test_health_check_runs_one_query_in_one_committed_transaction_and_closes(
    fake_app, fake_driver
):
    fake_app.test_client().get("/health/db")

    connection = fake_driver.last
    assert [sql for sql, _ in connection.statements] == ["SELECT 1 AS ok"]
    assert connection.events == ["commit", "rollback", "close"]


def test_connection_failure_gives_503_with_no_details(fake_app, fake_driver, caplog):
    fake_driver.fail_with = psycopg2.OperationalError(
        'connection to server at "db.example.org", port 5999 failed: FATAL: password '
        'authentication failed for user "fake_user" (pw-secret-123)'
    )

    with caplog.at_level(logging.INFO):
        response = fake_app.test_client().get("/health/db")

    assert response.status_code == 503
    assert response.get_json() == UNAVAILABLE
    assert_no_secrets(response.get_data(as_text=True))
    assert_no_secrets(caplog.text)


def test_application_keeps_serving_after_a_database_failure(fake_app, fake_driver):
    client = fake_app.test_client()
    fake_driver.fail_with = psycopg2.OperationalError("down")

    assert client.get("/health/db").status_code == 503
    assert client.get("/health").status_code == 200  # not crashed
    assert client.get("/health/db").status_code == 503  # and still accurate

    fake_driver.fail_with = None  # database comes back: reported accurately again
    response = client.get("/health/db")

    assert (response.status_code, response.get_json()) == (200, HEALTHY)


def test_failure_while_running_the_query_gives_503_and_rolls_back(
    fake_app, fake_driver, monkeypatch, caplog
):
    original_connect = fake_driver.connect

    def connect_then_fail_on_execute(**kwargs):
        connection = original_connect(**kwargs)
        connection.fail_execute = psycopg2.OperationalError("server closed the connection")
        return connection

    monkeypatch.setattr(psycopg2, "connect", connect_then_fail_on_execute)

    with caplog.at_level(logging.WARNING, logger="app.core.health"):
        response = fake_app.test_client().get("/health/db")

    assert response.status_code == 503
    assert response.get_json() == UNAVAILABLE
    assert fake_driver.last.events[0] == "rollback"
    assert fake_driver.last.closed
    assert "server closed the connection" not in caplog.text
    assert "health check failed (OperationalError)" in caplog.text


@pytest.mark.parametrize("rows", [[{"ok": 0}], [{"ok": None}], []])
def test_an_unexpected_query_result_is_not_reported_as_healthy(fake_app, fake_driver, rows):
    fake_driver.responses["SELECT 1 AS ok"] = rows

    response = fake_app.test_client().get("/health/db")

    assert (response.status_code, response.get_json()) == (503, UNAVAILABLE)


def test_missing_database_configuration_gives_503_without_connecting(fake_driver):
    app = create_app("testing")  # TestingConfig has no DB_NAME until a fixture supplies one

    response = app.test_client().get("/health/db")

    assert (response.status_code, response.get_json()) == (503, UNAVAILABLE)
    assert fake_driver.connect_kwargs == []


# --- /health/db against the disposable PostgreSQL -------------------------------------


def test_real_database_gives_200(db_app):
    response = db_app.test_client().get("/health/db")

    assert response.status_code == 200
    assert response.get_json() == HEALTHY


def test_real_health_check_leaves_no_session_behind(db_app, app_sessions):
    db_app.test_client().get("/health/db")

    assert app_sessions(db_app.config["DB_APPLICATION_NAME"], expect_none=True) == []


def test_unreachable_server_gives_503_and_the_app_survives(cinema_test_db):
    overrides = dict(cinema_test_db.app_config(), DB_PORT=1, DB_CONNECT_TIMEOUT=1)
    app = create_app("testing", overrides)
    client = app.test_client()

    response = client.get("/health/db")

    assert (response.status_code, response.get_json()) == (503, UNAVAILABLE)
    text = response.get_data(as_text=True)
    for detail in ("127.0.0.1", cinema_test_db.name, str(cinema_test_db.settings.user)):
        assert detail not in text
    assert client.get("/health").status_code == 200


def test_unknown_database_gives_503(cinema_test_db):
    overrides = dict(cinema_test_db.app_config(), DB_NAME="cinema_test_no_such_database")
    app = create_app("testing", overrides)

    response = app.test_client().get("/health/db")

    assert (response.status_code, response.get_json()) == (503, UNAVAILABLE)
    assert "no_such_database" not in response.get_data(as_text=True)


def test_database_availability_is_reported_per_request(cinema_test_db):
    # Same server, two apps: one pointing at a closed port, one at the real test database.
    broken = create_app("testing", dict(cinema_test_db.app_config(), DB_PORT=1, DB_CONNECT_TIMEOUT=1))
    working = create_app("testing", cinema_test_db.app_config())

    assert broken.test_client().get("/health/db").status_code == 503
    assert working.test_client().get("/health/db").status_code == 200
