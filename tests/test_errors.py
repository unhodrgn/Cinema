"""Task 6: error mapping (app/errors.py) against the integration contract, section 6."""

import logging
import re
from pathlib import Path

import psycopg2
import pytest

from app import create_app
from app.database import DatabaseUnavailableError, transaction
from app.errors import (
    DATABASE_UNAVAILABLE,
    INTERNAL_ERROR,
    SQLSTATE_ERRORS,
    AppError,
    ErrorInfo,
    describe_database_error,
    translate_database_error,
)
from fake_driver import database_error

CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "database"
    / "postgresql_flask_integration_contract.md"
)

# What the application must answer for each SQLSTATE: (HTTP status, internal?).
EXPECTED = {
    "UC001": (409, False),
    "UC002": (409, False),
    "UC003": (400, False),
    "UC004": (409, False),
    "UC005": (409, False),
    "UC006": (409, False),
    "UC007": (500, True),  # contract: internal error, the application must not do this
    "UC008": (403, False),
    "UC009": (500, True),  # contract: internal error, use create_booking
    "UC010": (400, False),
    "UC011": (404, False),
    "23505": (409, False),
    "23503": (400, False),
    "23514": (400, False),
    "23P01": (409, False),
    "23001": (500, True),  # contract: not an application feature
}

SECRET_DRIVER_TEXT = (
    "SELECT password_hash FROM users WHERE username = 'hunter2' "
    'violates constraint "users_username_key" DETAIL: Key (username)=(hunter2)'
)
LEAK_MARKERS = [
    "hunter2",
    "password_hash",
    "SELECT",
    "constraint",
    "users_username_key",
    "DETAIL",
    "Key (",
    "psycopg2",
    "postgres",
    "Traceback",
]


def contract_sqlstates():
    """The SQLSTATE codes in the contract's section 6 table, read from the document."""
    text = CONTRACT.read_text(encoding="utf-8")
    section = text.split("## 6.", 1)[1].split("## 7.", 1)[0]
    return set(re.findall(r"^\| `([0-9A-Z]{5})` \|", section, flags=re.MULTILINE))


def app_with_routes():
    app = create_app("testing")

    @app.get("/raise-db/<code>")
    def raise_db(code):
        raise database_error(code, SECRET_DRIVER_TEXT)

    @app.get("/raise-db-no-code")
    def raise_db_no_code():
        raise database_error(None, SECRET_DRIVER_TEXT)

    @app.get("/raise-operational")
    def raise_operational():
        raise psycopg2.OperationalError(SECRET_DRIVER_TEXT)

    @app.get("/raise-unavailable")
    def raise_unavailable():
        raise DatabaseUnavailableError("the database is unavailable")

    @app.get("/raise-app-error")
    def raise_app_error():
        raise AppError(ErrorInfo(418, "teapot", "I am a teapot."))

    @app.get("/raise-unexpected")
    def raise_unexpected():
        raise RuntimeError(SECRET_DRIVER_TEXT)

    return app


@pytest.fixture
def client():
    return app_with_routes().test_client()


def assert_safe(response, info):
    body = response.get_json()
    assert response.status_code == info.status
    assert body == {"error": {"code": info.code, "message": info.message}}
    assert response.headers["Cache-Control"] == "no-store"
    assert response.mimetype == "application/json"
    text = response.get_data(as_text=True)
    for marker in LEAK_MARKERS:
        assert marker not in text


# --- the mapping versus the contract --------------------------------------------------


def test_the_contract_lists_the_expected_sqlstates():
    # Guards the parser below: if the contract table changes, this test says so.
    assert contract_sqlstates() == set(EXPECTED)


def test_every_contract_sqlstate_is_mapped_and_nothing_else_is():
    assert set(SQLSTATE_ERRORS) == contract_sqlstates()


@pytest.mark.parametrize("code, expected", sorted(EXPECTED.items()))
def test_status_and_kind_of_each_mapping(code, expected):
    status, internal = expected
    info = SQLSTATE_ERRORS[code]

    assert (info.status, info.internal) == (status, internal)


def test_contract_internal_errors_use_the_generic_500():
    for code in ("UC007", "UC009", "23001"):
        assert SQLSTATE_ERRORS[code] is INTERNAL_ERROR


def test_user_visible_messages_are_fixed_text_without_internals():
    for info in [*SQLSTATE_ERRORS.values(), INTERNAL_ERROR, DATABASE_UNAVAILABLE]:
        assert info.message and info.message[0].isupper() and info.message.endswith(".")
        assert not re.search(r"(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE)", info.message)
        for marker in ("constraint", "sqlstate", "psycopg", "postgres"):
            assert marker not in info.message.lower()
        assert not re.search(r"\b(UC\d{3}|23\d{3}|23P01)\b", info.message)


def test_error_codes_are_unique_per_meaning():
    named = {info.code for info in SQLSTATE_ERRORS.values() if not info.internal}
    assert len(named) == len([i for i in SQLSTATE_ERRORS.values() if not i.internal])


# --- describe_database_error ----------------------------------------------------------


@pytest.mark.parametrize("code", sorted(EXPECTED))
def test_describe_uses_the_sqlstate_only(code):
    assert describe_database_error(database_error(code, "anything at all")) is SQLSTATE_ERRORS[code]


def test_message_text_is_never_used_for_matching():
    # A message that merely mentions another code must not change the result.
    error = database_error("XX000", "UC011 not found; 23505 duplicate")

    assert describe_database_error(error) is INTERNAL_ERROR


@pytest.mark.parametrize("code", ["XX000", "42P01", "40001", "", None])
def test_unknown_or_missing_sqlstate_is_a_generic_500(code):
    assert describe_database_error(database_error(code)) is INTERNAL_ERROR


@pytest.mark.parametrize("error_class", [psycopg2.OperationalError, psycopg2.InterfaceError])
def test_lost_connections_are_503(error_class):
    assert describe_database_error(error_class("server closed the connection")) is DATABASE_UNAVAILABLE


def test_a_mapped_sqlstate_wins_over_the_exception_class():
    error_class = type("E", (psycopg2.OperationalError,), {"pgcode": "UC011"})

    assert describe_database_error(error_class("x")) is SQLSTATE_ERRORS["UC011"]


def test_translate_returns_an_app_error_carrying_the_info():
    translated = translate_database_error(database_error("UC002"))

    assert isinstance(translated, AppError)
    assert translated.info is SQLSTATE_ERRORS["UC002"]


# --- the registered handlers ----------------------------------------------------------


@pytest.mark.parametrize("code", sorted(EXPECTED))
def test_every_mapped_sqlstate_gives_a_safe_response(client, code):
    assert_safe(client.get(f"/raise-db/{code}"), SQLSTATE_ERRORS[code])


def test_unknown_sqlstate_gives_a_safe_generic_500(client):
    assert_safe(client.get("/raise-db/XX000"), INTERNAL_ERROR)
    assert_safe(client.get("/raise-db-no-code"), INTERNAL_ERROR)


def test_operational_error_gives_a_safe_503(client):
    assert_safe(client.get("/raise-operational"), DATABASE_UNAVAILABLE)


def test_database_unavailable_error_gives_a_safe_503(client):
    assert_safe(client.get("/raise-unavailable"), DATABASE_UNAVAILABLE)


def test_app_error_gives_its_own_response(client):
    response = client.get("/raise-app-error")

    assert response.status_code == 418
    assert response.get_json() == {"error": {"code": "teapot", "message": "I am a teapot."}}


def test_unexpected_exception_gives_a_safe_500_and_is_logged(client, caplog):
    with caplog.at_level(logging.ERROR, logger="app.errors"):
        response = client.get("/raise-unexpected")

    assert_safe(response, INTERNAL_ERROR)
    assert "unhandled RuntimeError" in caplog.text
    assert "Traceback" in caplog.text  # the full details stay in the server log


def test_database_errors_are_logged_by_sqlstate_without_the_driver_message(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.errors"):
        client.get("/raise-db/UC002")
        client.get("/raise-db/UC009")

    assert "SQLSTATE UC002" in caplog.text and "SQLSTATE UC009" in caplog.text
    assert "hunter2" not in caplog.text and "SELECT" not in caplog.text


def test_user_errors_log_at_info_and_internal_ones_at_error(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.errors"):
        client.get("/raise-db/UC002")
        client.get("/raise-db/UC009")

    by_code = {
        ("UC002" if "UC002" in record.getMessage() else "UC009"): record.levelname
        for record in caplog.records
    }
    assert by_code == {"UC002": "INFO", "UC009": "ERROR"}


def test_http_errors_keep_their_normal_behaviour(client):
    not_found = client.get("/no/such/page")
    not_allowed = client.post("/health")

    assert not_found.status_code == 404
    assert not_allowed.status_code == 405
    assert "internal_error" not in not_found.get_data(as_text=True)


def test_in_debug_mode_unexpected_exceptions_propagate_to_the_debugger():
    app = app_with_routes()
    app.debug = True

    with pytest.raises(RuntimeError):
        app.test_client().get("/raise-unexpected")


def test_in_debug_mode_database_errors_are_still_sanitised():
    app = app_with_routes()
    app.debug = True

    assert_safe(app.test_client().get("/raise-db/UC011"), SQLSTATE_ERRORS["UC011"])


# --- with a transaction: the request rolls back and the response stays safe -----------


def test_error_inside_a_transaction_rolls_back_and_closes_the_connection(fake_app, fake_driver):
    @fake_app.get("/fail")
    def fail():
        with transaction() as cur:
            fake_driver.last.fail_execute = database_error("UC002", SECRET_DRIVER_TEXT)
            cur.execute("SELECT create_booking(1, 1, '{}')")

    response = fake_app.test_client().get("/fail")

    assert_safe(response, SQLSTATE_ERRORS["UC002"])
    assert fake_driver.last.events == ["rollback", "rollback", "close"]
    assert fake_driver.last.closed


def test_unavailable_database_inside_a_view_gives_a_safe_503(fake_app, fake_driver):
    fake_driver.fail_with = psycopg2.OperationalError(SECRET_DRIVER_TEXT + " pw-secret-123")

    @fake_app.get("/needs-db")
    def needs_db():
        with transaction() as cur:
            cur.execute("SELECT 1")

    response = fake_app.test_client().get("/needs-db")

    assert_safe(response, DATABASE_UNAVAILABLE)
    assert "pw-secret-123" not in response.get_data(as_text=True)


# --- real database errors through a real transaction ----------------------------------

REAL_ERRORS = {
    "UC011": "SELECT pay_booking(-1, -1)",
    "UC010": (
        "SELECT create_booking((SELECT min(user_id) FROM users WHERE role = 'CUSTOMER'), "
        "(SELECT min(showtime_id) FROM showtimes), '{}'::bigint[])"
    ),
    "23505": "INSERT INTO users(username, password_hash) VALUES ('admin_demo', 'x')",
    "23503": (
        "INSERT INTO showtimes(movie_id, room_id, starts_at, ends_at, ticket_price) "
        "VALUES (999999, 1, now() + interval '30 days', now() + interval '31 days', 1)"
    ),
    "23514": "INSERT INTO movies(title, duration_minutes) VALUES ('Too short', 0)",
    "23P01": (
        "INSERT INTO showtimes(movie_id, room_id, starts_at, ends_at, ticket_price) "
        "SELECT movie_id, room_id, starts_at, ends_at, ticket_price FROM showtimes "
        "ORDER BY showtime_id LIMIT 1"
    ),
}


@pytest.mark.parametrize("code", sorted(REAL_ERRORS))
def test_real_database_errors_map_to_the_contract_response(
    db_app, db_connection, app_sessions, code
):
    sql = REAL_ERRORS[code]

    @db_app.get("/real-error")
    def real_error():
        with transaction() as cur:
            cur.execute(sql)

    response = db_app.test_client().get("/real-error")

    assert_safe(response, SQLSTATE_ERRORS[code])
    with db_connection.cursor() as cur:  # nothing was changed
        cur.execute(
            "SELECT (SELECT count(*) FROM users), (SELECT count(*) FROM movies), "
            "(SELECT count(*) FROM showtimes), (SELECT count(*) FROM bookings)"
        )
        assert cur.fetchone() == (3, 5, 140, 0)
    assert app_sessions(db_app.config["DB_APPLICATION_NAME"], expect_none=True) == []


def test_the_real_errors_carry_the_sqlstates_the_mapping_expects(db_app):
    # Guards REAL_ERRORS itself: each statement must really raise the code it is filed under.
    from app import database

    with db_app.app_context():
        for code, sql in REAL_ERRORS.items():
            with pytest.raises(psycopg2.Error) as excinfo:
                with transaction() as cur:
                    cur.execute(sql)
            assert excinfo.value.pgcode == code, (code, sql)
        assert database.get_db().info.transaction_status == 0  # idle: every one rolled back
