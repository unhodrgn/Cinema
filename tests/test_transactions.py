"""Task 5: transaction() and expire_overdue_bookings(cur)."""

import logging

import psycopg2
import pytest
from psycopg2.extensions import TRANSACTION_STATUS_IDLE, TRANSACTION_STATUS_INTRANS

from app import database
from app.database import TransactionError, expire_overdue_bookings, transaction
from fake_driver import FakeCursor

# --- unit tests with the fake driver --------------------------------------------------


def test_normal_exit_commits_and_keeps_the_connection_open(fake_app, fake_driver):
    with fake_app.app_context():
        with transaction() as cur:
            cur.execute("SELECT 1 AS ok")
        connection = fake_driver.last

        assert connection.events == ["commit"]
        assert connection.status == TRANSACTION_STATUS_IDLE
        assert not connection.closed
    assert connection.events == ["commit", "rollback", "close"]  # cleanup runs at context end


def test_the_cursor_belongs_to_the_connection_and_is_closed_afterwards(fake_app, fake_driver):
    with fake_app.app_context():
        with transaction() as cur:
            assert isinstance(cur, FakeCursor)
            assert cur.connection is fake_driver.last
        assert cur.closed


def test_exception_rolls_back_never_commits_and_propagates_unchanged(fake_app, fake_driver):
    class Boom(Exception):
        pass

    with fake_app.app_context():
        with pytest.raises(Boom):
            with transaction() as cur:
                cur.execute("INSERT INTO anything VALUES (1)")
                raise Boom()
        connection = fake_driver.last

        assert connection.events == ["rollback"]
        assert connection.status == TRANSACTION_STATUS_IDLE
        assert cur.closed


@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit, GeneratorExit])
def test_base_exceptions_also_roll_back(fake_app, fake_driver, exception):
    with fake_app.app_context():
        with pytest.raises(exception):
            with transaction():
                raise exception()

        assert fake_driver.last.events == ["rollback"]


def test_a_database_error_inside_the_block_rolls_back(fake_app, fake_driver):
    with fake_app.app_context():
        with pytest.raises(psycopg2.DatabaseError):
            with transaction() as cur:
                fake_driver.last.fail_execute = psycopg2.DatabaseError("constraint violated")
                cur.execute("INSERT INTO anything VALUES (1)")

        assert fake_driver.last.events == ["rollback"]


def test_failed_commit_rolls_back_and_raises_the_commit_error(fake_app, fake_driver):
    # The schema's deferred consistency triggers (UC009/UC010) fire at COMMIT.
    with fake_app.app_context():
        database.get_db().fail_commit = psycopg2.DatabaseError("booking has no seats")
        with pytest.raises(psycopg2.DatabaseError, match="booking has no seats"):
            with transaction() as cur:
                cur.execute("INSERT INTO anything VALUES (1)")

        assert fake_driver.last.events == ["commit", "rollback"]


def test_failed_rollback_does_not_mask_the_original_error(fake_app, fake_driver, caplog):
    with fake_app.app_context():
        database.get_db().fail_rollback = psycopg2.OperationalError("connection lost")
        with caplog.at_level(logging.WARNING, logger="app.database"):
            with pytest.raises(ValueError, match="the real problem"):
                with transaction():
                    raise ValueError("the real problem")

    assert "rollback failed" in caplog.text
    assert "connection lost" not in caplog.text


def test_rollback_is_skipped_on_a_closed_connection(fake_app, fake_driver):
    with fake_app.app_context():
        connection = database.get_db()
        with pytest.raises(RuntimeError):
            with transaction():
                connection.closed = 2
                raise RuntimeError("connection dropped")

        assert connection.events == []


def test_transactions_can_follow_each_other_on_one_connection(fake_app, fake_driver):
    with fake_app.app_context():
        with transaction() as first:
            first.execute("SELECT 1 AS ok")
        with pytest.raises(ValueError):
            with transaction() as second:
                second.execute("SELECT 1 AS ok")
                raise ValueError()
        with transaction() as third:
            third.execute("SELECT 1 AS ok")

        assert len(fake_driver.connections) == 1
        assert fake_driver.last.events == ["commit", "rollback", "commit"]


def test_nested_transactions_are_rejected_without_touching_the_outer_one(fake_app, fake_driver):
    with fake_app.app_context():
        with transaction() as outer:
            outer.execute("SELECT 1 AS ok")
            with pytest.raises(TransactionError, match="cannot be nested"):
                with transaction():
                    pytest.fail("the nested block must not run")
            assert fake_driver.last.status == TRANSACTION_STATUS_INTRANS
        assert fake_driver.last.events == ["commit"]


def test_nesting_is_rejected_even_before_the_outer_block_ran_any_sql(fake_app, fake_driver):
    # A real connection stays "idle" until its first statement: the flag must catch this.
    with fake_app.app_context():
        with transaction():
            assert fake_driver.last.status == TRANSACTION_STATUS_IDLE
            with pytest.raises(TransactionError, match="cannot be nested"):
                with transaction():
                    pytest.fail("must not run")
        assert fake_driver.last.events == ["commit"]


def test_the_flag_is_cleared_after_success_and_after_failure(fake_app, fake_driver):
    with fake_app.app_context():
        with transaction():
            pass
        with pytest.raises(ValueError):
            with transaction():
                raise ValueError()
        with transaction() as cur:  # would raise TransactionError if the flag were stuck
            cur.execute("SELECT 1 AS ok")


def test_sql_run_outside_transaction_blocks_the_next_transaction(fake_app, fake_driver):
    with fake_app.app_context():
        with database.get_db().cursor() as cur:
            cur.execute("SELECT 1 AS ok")  # leaves a transaction open

        with pytest.raises(TransactionError):
            with transaction():
                pytest.fail("must not run")


def test_connection_failure_propagates_before_the_block_runs(fake_app, fake_driver):
    fake_driver.fail_with = psycopg2.OperationalError("down")

    with fake_app.app_context():
        with pytest.raises(database.DatabaseUnavailableError):
            with transaction():
                pytest.fail("must not run")


# --- expire_overdue_bookings(cur): unit tests -----------------------------------------


@pytest.fixture
def no_new_connections(monkeypatch):
    """Fail if the helper opens or fetches a connection of its own."""

    def refuse(*args, **kwargs):
        raise AssertionError("the helper must use the supplied cursor only")

    monkeypatch.setattr(psycopg2, "connect", refuse)
    monkeypatch.setattr(database, "get_db", refuse)
    monkeypatch.setattr(database, "connect", refuse)


class RecordingCursor:
    def __init__(self, row):
        self.statements = []
        self._row = row

    def execute(self, sql, params=None):
        self.statements.append((sql, params))

    def fetchone(self):
        return self._row


def test_helper_uses_only_the_supplied_cursor(no_new_connections):
    cur = RecordingCursor({"expired": 3})

    assert expire_overdue_bookings(cur) == 3
    assert len(cur.statements) == 1


def test_helper_calls_the_database_function_without_arguments(no_new_connections):
    cur = RecordingCursor({"expired": 0})

    expire_overdue_bookings(cur)

    sql, params = cur.statements[0]
    assert sql == "SELECT expire_overdue_bookings() AS expired"
    assert params is None
    assert "p_as_of" not in sql  # reserved for database tests (contract section 3)


@pytest.mark.parametrize("row", [{"expired": 4}, (4,), {"anything": 4}, [4]])
def test_helper_returns_an_integer_for_dict_and_tuple_rows(row):
    assert expire_overdue_bookings(RecordingCursor(row)) == 4


def test_helper_does_not_commit_or_manage_the_transaction(fake_app, fake_driver):
    with fake_app.app_context():
        with transaction() as cur:
            assert expire_overdue_bookings(cur) == 0
            assert fake_driver.last.events == []  # nothing committed yet
            assert fake_driver.last.statements[-1][0] == (
                "SELECT expire_overdue_bookings() AS expired"
            )
        assert fake_driver.last.events == ["commit"]


def test_helper_propagates_database_errors(fake_app, fake_driver):
    with fake_app.app_context():
        with pytest.raises(psycopg2.DatabaseError):
            with transaction() as cur:
                fake_driver.last.fail_execute = psycopg2.DatabaseError("function missing")
                expire_overdue_bookings(cur)
        assert fake_driver.last.events == ["rollback"]


def test_helper_followed_by_a_read_shares_one_transaction(fake_app, fake_driver):
    with fake_app.app_context():
        with transaction() as cur:
            expire_overdue_bookings(cur)
            cur.execute("SELECT 1 AS ok")
        assert fake_driver.last.events == ["commit"]  # one commit for both statements
        assert len(fake_driver.last.statements) == 2


# --- integration tests against the disposable database --------------------------------


@pytest.fixture
def probe_table(cinema_test_db):
    """A scratch table that exists only in the disposable database (dropped with it).

    Rows are deleted before and after each test. The table is never dropped here: a
    DROP would wait for locks held by other connections of the same test.
    """

    def clear():
        connection = cinema_test_db.connect()
        try:
            with connection.cursor() as cur:
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS phase3_probe "
                    "(id serial PRIMARY KEY, note text NOT NULL)"
                )
                cur.execute("DELETE FROM phase3_probe")
            connection.commit()
        finally:
            connection.close()

    clear()
    yield "phase3_probe"
    clear()


def probe_notes(connection):
    with connection.cursor() as cur:
        cur.execute("SELECT note FROM phase3_probe ORDER BY id")
        return [row[0] for row in cur.fetchall()]


def test_commit_makes_the_work_visible_to_other_connections(
    db_app, db_connection, probe_table
):
    with db_app.app_context():
        with transaction() as cur:
            cur.execute("INSERT INTO phase3_probe(note) VALUES ('committed')")
            # not yet visible to anyone else while the transaction is open
            assert probe_notes(db_connection) == []
            db_connection.rollback()
        assert database.get_db().info.transaction_status == TRANSACTION_STATUS_IDLE

    db_connection.rollback()
    assert probe_notes(db_connection) == ["committed"]


def test_exception_rolls_back_and_leaves_nothing_behind(db_app, db_connection, probe_table):
    with db_app.app_context():
        with pytest.raises(ZeroDivisionError):
            with transaction() as cur:
                cur.execute("INSERT INTO phase3_probe(note) VALUES ('lost')")
                1 / 0
        assert database.get_db().info.transaction_status == TRANSACTION_STATUS_IDLE

    assert probe_notes(db_connection) == []


def test_database_error_rolls_back_the_whole_transaction(db_app, db_connection, probe_table):
    with db_app.app_context():
        with pytest.raises(psycopg2.errors.NotNullViolation):
            with transaction() as cur:
                cur.execute("INSERT INTO phase3_probe(note) VALUES ('first row')")
                cur.execute("INSERT INTO phase3_probe(note) VALUES (NULL)")

    assert probe_notes(db_connection) == []


def test_the_connection_is_usable_after_a_rollback(db_app, db_connection, probe_table):
    with db_app.app_context():
        with pytest.raises(psycopg2.errors.NotNullViolation):
            with transaction() as cur:
                cur.execute("INSERT INTO phase3_probe(note) VALUES (NULL)")
        connection = database.get_db()
        with transaction() as cur:
            cur.execute("INSERT INTO phase3_probe(note) VALUES ('after rollback')")
        assert database.get_db() is connection  # same connection, no reconnect

    assert probe_notes(db_connection) == ["after rollback"]


def test_a_read_only_transaction_leaves_no_open_transaction(db_app):
    with db_app.app_context():
        with transaction() as cur:
            cur.execute("SELECT count(*) AS n FROM movies")
            assert cur.fetchone()["n"] == 5
        assert database.get_db().info.transaction_status == TRANSACTION_STATUS_IDLE


def test_nested_transaction_is_rejected_on_a_real_connection(db_app):
    with db_app.app_context():
        with transaction():
            with pytest.raises(TransactionError):
                with transaction():
                    pass


def test_commit_time_failure_rolls_back_everything(db_app, db_connection):
    # A BOOKED booking without seats is rejected by the deferred consistency trigger at
    # COMMIT (UC010), not at INSERT: the commit fails and the row must not survive.
    with db_connection.cursor() as cur:
        cur.execute("SELECT showtime_id FROM showtimes ORDER BY starts_at DESC LIMIT 1")
        showtime_id = cur.fetchone()[0]
        cur.execute("SELECT user_id FROM users WHERE role = 'CUSTOMER' ORDER BY user_id LIMIT 1")
        user_id = cur.fetchone()[0]

    with db_app.app_context():
        with pytest.raises(psycopg2.Error) as excinfo:
            with transaction() as cur:
                cur.execute(
                    "INSERT INTO bookings(user_id, showtime_id, status, payment_status, "
                    "booked_at, expires_at, total_amount) VALUES "
                    "(%s, %s, 'BOOKED', 'UNPAID', now(), now() + interval '10 minutes', 0)",
                    (user_id, showtime_id),
                )
        assert excinfo.value.pgcode in {"UC009", "UC010"}
        assert database.get_db().info.transaction_status == TRANSACTION_STATUS_IDLE

    with db_connection.cursor() as cur:
        cur.execute("SELECT count(*) FROM bookings")
        assert cur.fetchone()[0] == 0


def test_session_is_closed_after_transactions_and_failures(db_app, app_sessions):
    name = db_app.config["DB_APPLICATION_NAME"]
    with db_app.app_context():
        with transaction() as cur:
            cur.execute("SELECT 1")
        with pytest.raises(ZeroDivisionError):
            with transaction() as cur:
                cur.execute("SELECT 1")
                1 / 0
        assert app_sessions(name) == ["idle"]  # between transactions: nothing left open

    assert app_sessions(name, expect_none=True) == []


def test_expiry_helper_runs_the_real_function_on_the_supplied_cursor(db_app):
    with db_app.app_context():
        with transaction() as cur:
            first = expire_overdue_bookings(cur)
            second = expire_overdue_bookings(cur)  # idempotent

    assert (first, second) == (0, 0)
    assert isinstance(first, int)


def test_expiry_helper_and_a_read_share_one_transaction(db_app):
    with db_app.app_context():
        with transaction() as cur:
            expire_overdue_bookings(cur)
            cur.execute("SELECT txid_current() AS tx")
            first_tx = cur.fetchone()["tx"]
            expire_overdue_bookings(cur)
            cur.execute("SELECT txid_current() AS tx")
            assert cur.fetchone()["tx"] == first_tx


def test_expiry_helper_never_opens_another_session(db_app, app_sessions):
    name = db_app.config["DB_APPLICATION_NAME"]
    with db_app.app_context():
        with transaction() as cur:
            expire_overdue_bookings(cur)
            assert len(app_sessions(name)) == 1  # still only the request's own connection


def test_expiry_helper_with_a_plain_tuple_cursor_on_a_real_connection(cinema_test_db):
    connection = cinema_test_db.connect()
    try:
        with connection.cursor() as cur:  # default tuple cursor, not the app's dict cursor
            assert expire_overdue_bookings(cur) == 0
        connection.commit()
    finally:
        connection.close()
