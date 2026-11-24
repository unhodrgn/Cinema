"""T1 / Spike A: per-test database clones and the owner-only time-simulation helpers.

Needs a disposable PostgreSQL server (explicit TEST_DB_PORT); skipped otherwise. Every
destructive operation here targets only ``cinema_test_*`` databases created by this
process.
"""

import psycopg2
import pytest

import disposable_db
from disposable_db import DatabaseSetupError, DisposableDatabase, UnsafeDatabaseError
from helpers import future_showtime_id
from time_travel import (
    TimeTravelError,
    age_booking,
    assert_triggers_enabled,
    create_spare_room_screening,
    start_screening_in_past,
)


def scalar(connection, sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params)
        value = cur.fetchone()[0]
    connection.rollback()
    return value


def database_comment(settings, name):
    admin = disposable_db._open(settings, disposable_db.MAINTENANCE_DATABASE, autocommit=True)
    try:
        return scalar(
            admin,
            "SELECT shobj_description(oid, 'pg_database') FROM pg_database WHERE datname = %s",
            (name,),
        )
    finally:
        admin.close()


def database_exists(settings, name):
    admin = disposable_db._open(settings, disposable_db.MAINTENANCE_DATABASE, autocommit=True)
    try:
        return scalar(admin, "SELECT count(*) FROM pg_database WHERE datname = %s", (name,)) == 1
    finally:
        admin.close()


def customer_id(connection):
    return scalar(connection, "SELECT user_id FROM users WHERE username = 'customer1'")


def book(connection, user_id, showtime_id, seat_ids):
    with connection.cursor() as cur:
        cur.execute("SELECT create_booking(%s, %s, %s)", (user_id, showtime_id, seat_ids))
        booking_id = cur.fetchone()[0]
    connection.commit()
    return booking_id


# --- clones -----------------------------------------------------------------------------


def test_a_clone_is_a_seeded_disposable_database(fresh_db, fresh_connection):
    assert fresh_db.name.startswith(disposable_db.TEST_DB_PREFIX)
    assert scalar(fresh_connection, "SELECT current_database()") == fresh_db.name
    assert scalar(fresh_connection, "SELECT count(*) FROM showtimes") == 280
    assert scalar(fresh_connection, "SELECT count(*) FROM seats") == 250
    assert scalar(fresh_connection, "SELECT count(*) FROM bookings") == 0


def test_the_marker_is_written_again_for_every_clone(cinema_template_db, fresh_db, postgres_settings):
    # CREATE DATABASE ... TEMPLATE does not copy the database comment (Spike A), so a
    # clone carries this session's marker only because create() writes it.
    assert database_comment(postgres_settings, fresh_db.name) == disposable_db.MARKER
    assert fresh_db.name != cinema_template_db.name
    assert fresh_db.name in disposable_db._created_this_session


def test_clones_are_independent_of_each_other_and_of_the_template(
    cinema_template_db, fresh_db, fresh_connection
):
    showtime = future_showtime_id(fresh_connection)
    with fresh_connection.cursor() as cur:
        cur.execute("SELECT seat_id FROM seats s JOIN showtimes t USING (room_id) "
                    "WHERE t.showtime_id = %s ORDER BY seat_id LIMIT 1", (showtime,))
        seat = cur.fetchone()[0]
    book(fresh_connection, customer_id(fresh_connection), showtime, [seat])
    assert scalar(fresh_connection, "SELECT count(*) FROM bookings") == 1

    forbidden = frozenset()
    with disposable_db.clone_database(cinema_template_db, forbidden) as other:
        connection = other.connect()
        try:
            assert scalar(connection, "SELECT count(*) FROM bookings") == 0
        finally:
            connection.close()


def test_a_clone_is_dropped_after_use(cinema_template_db, postgres_settings):
    with disposable_db.clone_database(cinema_template_db) as clone:
        name = clone.name
        assert database_exists(postgres_settings, name)
    assert not database_exists(postgres_settings, name)
    assert name not in disposable_db._created_this_session


def test_a_clone_is_dropped_even_when_the_body_fails(cinema_template_db, postgres_settings):
    with pytest.raises(RuntimeError, match="boom"):
        with disposable_db.clone_database(cinema_template_db) as clone:
            name = clone.name
            raise RuntimeError("boom")
    assert not database_exists(postgres_settings, name)


def test_the_template_is_never_connected_to_by_a_clone_request(cinema_template_db, postgres_settings):
    admin = disposable_db._open(postgres_settings, disposable_db.MAINTENANCE_DATABASE, True)
    try:
        sessions = scalar(
            admin, "SELECT count(*) FROM pg_stat_activity WHERE datname = %s", (cinema_template_db.name,)
        )
    finally:
        admin.close()
    assert sessions == 0


def test_cloning_a_template_that_is_in_use_fails_loudly_and_cleans_up(
    cinema_template_db, postgres_settings
):
    clone = DisposableDatabase(postgres_settings)
    holder = disposable_db._open(postgres_settings, cinema_template_db.name, autocommit=False)
    try:
        with pytest.raises(DatabaseSetupError, match="connection to the template is open"):
            clone.create(template=cinema_template_db, busy_retry_seconds=0.2)
    finally:
        holder.close()
    assert clone.created is False
    assert not database_exists(postgres_settings, clone.name)


def test_a_database_this_session_did_not_create_is_never_a_template(postgres_settings):
    stranger = DisposableDatabase(postgres_settings)  # never created
    with pytest.raises(UnsafeDatabaseError):
        DisposableDatabase(postgres_settings).create(template=stranger)

    forged = DisposableDatabase(postgres_settings)
    forged.created = True  # claims to exist, but is not in the registry
    with pytest.raises(UnsafeDatabaseError, match="registry"):
        DisposableDatabase(postgres_settings).create(template=forged)


def test_a_template_without_this_sessions_marker_is_refused(cinema_template_db, postgres_settings):
    admin = disposable_db._open(postgres_settings, disposable_db.MAINTENANCE_DATABASE, True)
    try:
        with admin.cursor() as cur:
            cur.execute(
                f'COMMENT ON DATABASE "{cinema_template_db.name}" IS %s', ("someone-else",)
            )
        try:
            with pytest.raises(UnsafeDatabaseError, match="marker"):
                DisposableDatabase(postgres_settings).create(template=cinema_template_db)
        finally:
            with admin.cursor() as cur:
                cur.execute(
                    f'COMMENT ON DATABASE "{cinema_template_db.name}" IS %s', (disposable_db.MARKER,)
                )
    finally:
        admin.close()


def test_fresh_app_talks_to_its_own_clone(fresh_app, fresh_db):
    response = fresh_app.test_client().get("/health/db")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


# --- time-simulation helpers ------------------------------------------------------------


def test_helpers_refuse_a_connection_that_is_not_a_disposable_database():
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, *args):
            pass

        def fetchone(self):
            return ("cinema_development",)

    class FakeConnection:
        closed = 0

        def cursor(self):
            return FakeCursor()

        def rollback(self):
            pass

    with pytest.raises(UnsafeDatabaseError):
        age_booking(FakeConnection(), 1)


def test_aged_booking_is_expired_by_the_database_on_payment(fresh_connection):
    user = customer_id(fresh_connection)
    showtime = future_showtime_id(fresh_connection)
    seat = scalar(
        fresh_connection,
        "SELECT seat_id FROM seats s JOIN showtimes t USING (room_id) "
        "WHERE t.showtime_id = %s ORDER BY seat_id LIMIT 1",
        (showtime,),
    )
    booking = book(fresh_connection, user, showtime, [seat])

    age_booking(fresh_connection, booking)  # 11 minutes

    assert_triggers_enabled(fresh_connection)
    # the helper only moved time: the booking is still BOOKED with its seat row
    assert scalar(fresh_connection, "SELECT status FROM bookings WHERE booking_id = %s", (booking,)) == "BOOKED"
    with fresh_connection.cursor() as cur:
        cur.execute("SELECT pay_booking(%s, %s)", (booking, user))
        assert cur.fetchone()[0] == "EXPIRED"
    fresh_connection.commit()
    assert scalar(
        fresh_connection,
        "SELECT status || '/' || payment_status FROM bookings WHERE booking_id = %s",
        (booking,),
    ) == "EXPIRED/UNPAID"
    assert scalar(fresh_connection, "SELECT count(*) FROM booking_seats WHERE booking_id = %s", (booking,)) == 0


def test_a_paid_booking_that_is_aged_never_expires(fresh_connection):
    user = customer_id(fresh_connection)
    showtime = future_showtime_id(fresh_connection)
    seat = scalar(
        fresh_connection,
        "SELECT seat_id FROM seats s JOIN showtimes t USING (room_id) "
        "WHERE t.showtime_id = %s ORDER BY seat_id LIMIT 1",
        (showtime,),
    )
    booking = book(fresh_connection, user, showtime, [seat])
    with fresh_connection.cursor() as cur:
        cur.execute("SELECT pay_booking(%s, %s)", (booking, user))
    fresh_connection.commit()

    age_booking(fresh_connection, booking, minutes=60)

    with fresh_connection.cursor() as cur:
        cur.execute("SELECT expire_overdue_bookings()")
        assert cur.fetchone()[0] == 0
    fresh_connection.commit()
    assert scalar(fresh_connection, "SELECT status FROM bookings WHERE booking_id = %s", (booking,)) == "BOOKED"


def test_a_failing_helper_leaves_the_trigger_enabled(fresh_connection):
    user = customer_id(fresh_connection)
    showtime = future_showtime_id(fresh_connection)
    seat = scalar(
        fresh_connection,
        "SELECT seat_id FROM seats s JOIN showtimes t USING (room_id) "
        "WHERE t.showtime_id = %s ORDER BY seat_id LIMIT 1",
        (showtime,),
    )
    booking = book(fresh_connection, user, showtime, [seat])

    # 2**40 makes the UPDATE fail AFTER the trigger was disabled (Spike A, failure path)
    with pytest.raises(psycopg2.Error):
        age_booking(fresh_connection, booking, minutes=2**40)

    assert_triggers_enabled(fresh_connection)
    # and the guard really is active again: a direct illegal change is rejected
    with pytest.raises(psycopg2.Error) as caught:
        with fresh_connection.cursor() as cur:
            cur.execute("UPDATE bookings SET booked_at = booked_at - interval '1 hour' WHERE booking_id = %s", (booking,))
    fresh_connection.rollback()
    assert caught.value.pgcode == "UC007"


def test_unknown_booking_is_refused_without_changes(fresh_connection):
    with pytest.raises(TimeTravelError, match="does not exist"):
        age_booking(fresh_connection, 987654)
    assert_triggers_enabled(fresh_connection)


def test_spare_room_screening_is_isolated_and_can_be_started_in_the_past(fresh_connection):
    user = customer_id(fresh_connection)
    spare = create_spare_room_screening(fresh_connection)
    assert len(spare["seat_ids"]) == 50
    booking = book(fresh_connection, user, spare["showtime_id"], spare["seat_ids"][:2])

    start_screening_in_past(fresh_connection, spare["showtime_id"])

    assert_triggers_enabled(fresh_connection)
    assert scalar(
        fresh_connection, "SELECT starts_at < now() FROM showtimes WHERE showtime_id = %s", (spare["showtime_id"],)
    )
    # D2 trigger really is back: the screening (which has a booking) can no longer change
    with pytest.raises(psycopg2.Error) as protected:
        with fresh_connection.cursor() as cur:
            cur.execute("UPDATE showtimes SET ticket_price = 1 WHERE showtime_id = %s", (spare["showtime_id"],))
    fresh_connection.rollback()
    assert protected.value.pgcode == "UC001"

    # the database now treats it as started: cancel and new bookings are refused
    with pytest.raises(psycopg2.Error) as cancel:
        with fresh_connection.cursor() as cur:
            cur.execute("SELECT cancel_booking(%s, %s)", (booking, user))
    fresh_connection.rollback()
    assert cancel.value.pgcode == "UC005"
    with pytest.raises(psycopg2.Error) as late:
        with fresh_connection.cursor() as cur:
            cur.execute("SELECT create_booking(%s, %s, %s)", (user, spare["showtime_id"], spare["seat_ids"][5:6]))
    fresh_connection.rollback()
    assert late.value.pgcode == "UC004"


def test_starting_a_screening_in_the_past_refuses_an_overlapping_window(fresh_connection):
    spare = create_spare_room_screening(fresh_connection)
    with fresh_connection.cursor() as cur:
        cur.execute(
            "INSERT INTO showtimes(movie_id, room_id, starts_at, ends_at, ticket_price) "
            "SELECT movie_id, room_id, now() - interval '30 minutes', now() + interval '30 minutes', 1 "
            "FROM showtimes WHERE showtime_id = %s",
            (spare["showtime_id"],),
        )
    fresh_connection.commit()
    before = scalar(fresh_connection, "SELECT starts_at FROM showtimes WHERE showtime_id = %s", (spare["showtime_id"],))

    with pytest.raises(TimeTravelError, match="overlaps"):
        start_screening_in_past(fresh_connection, spare["showtime_id"], started_minutes_ago=60)

    assert_triggers_enabled(fresh_connection)
    assert scalar(fresh_connection, "SELECT starts_at FROM showtimes WHERE showtime_id = %s", (spare["showtime_id"],)) == before
