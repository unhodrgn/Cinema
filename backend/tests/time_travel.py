"""Owner-only helpers that simulate elapsed time on a DISPOSABLE test database.

The application never moves a deadline or a screening time; these helpers exist only so
tests can reach states that would otherwise need real waiting (an unpaid booking past its
10-minute window, a screening that has already started). They follow the technique the
database tests already use (``docs/database/database_test_documentation.md``, section 1):
temporarily disable one USER trigger, change the data, enable the trigger again.

Safety rules:

* They refuse to run unless the connection is to a ``cinema_test_*`` database
  (``disposable_db.assert_disposable_name``), whatever the caller passes in.
* Each helper is ONE transaction. ``ALTER TABLE ... DISABLE TRIGGER`` is transactional in
  PostgreSQL, so a failure at any point rolls the trigger back to enabled; the helpers
  roll back on every exception and then verify the trigger state again.
* They need the table owner (the role that created the disposable database), exactly like
  the fixtures that call them. They are never part of an application path.
"""

import uuid

import disposable_db

GUARDED_TRIGGERS = {
    "bookings": "trg_bookings_validate",
    "showtimes": "trg_showtimes_protect_booked",
}


class TimeTravelError(RuntimeError):
    """A precondition of a helper failed; nothing was changed."""


def _scalar(cur, sql, params=None):
    cur.execute(sql, params)
    row = cur.fetchone()
    return None if row is None else row[0]


def _require_disposable_connection(connection):
    if connection.closed:
        raise TimeTravelError("the connection is closed")
    with connection.cursor() as cur:
        name = _scalar(cur, "SELECT current_database()")
    connection.rollback()  # end the read-only transaction the check just opened
    disposable_db.assert_disposable_name(name)


def assert_triggers_enabled(connection):
    """Raise unless both guarded USER triggers are enabled (state ``O``)."""
    with connection.cursor() as cur:
        cur.execute(
            "SELECT tgname, tgenabled FROM pg_trigger "
            "WHERE tgname = ANY(%s) AND NOT tgisinternal",
            (list(GUARDED_TRIGGERS.values()),),
        )
        states = {row[0]: row[1] for row in cur.fetchall()}
    connection.rollback()
    expected = {name: "O" for name in GUARDED_TRIGGERS.values()}
    if states != expected:
        raise TimeTravelError(f"guarded triggers are not all enabled: {states}")


def _run(connection, work):
    """Run ``work(cursor)`` as one transaction on a disposable database; restore on failure."""
    _require_disposable_connection(connection)
    try:
        with connection.cursor() as cur:
            result = work(cur)
        connection.commit()
    except BaseException:
        connection.rollback()  # DDL is transactional: a disabled trigger is enabled again
        raise
    finally:
        assert_triggers_enabled(connection)
    return result


def age_booking(connection, booking_id, minutes=11):
    """Move a booking's ``booked_at`` and ``expires_at`` ``minutes`` into the past.

    With the default 11 minutes an unpaid booking is past its 10-minute window. Both
    timestamps move together, so the ``expires_at = booked_at + 10 minutes`` CHECK still
    holds. Seat rows, status and payment status are not touched: expiry itself must still
    happen through the application's request-time path.
    """
    if minutes <= 0:
        raise ValueError("minutes must be positive")

    def work(cur):
        if _scalar(cur, "SELECT 1 FROM bookings WHERE booking_id = %s", (booking_id,)) is None:
            raise TimeTravelError(f"booking {booking_id} does not exist")
        cur.execute("ALTER TABLE bookings DISABLE TRIGGER trg_bookings_validate")
        cur.execute(
            "UPDATE bookings SET booked_at = booked_at - make_interval(mins => %s), "
            "expires_at = expires_at - make_interval(mins => %s) WHERE booking_id = %s",
            (minutes, minutes, booking_id),
        )
        cur.execute("ALTER TABLE bookings ENABLE TRIGGER trg_bookings_validate")

    _run(connection, work)


def create_spare_room_screening(connection, starts_in_hours=3, ticket_price=12000):
    """Create a new room with 50 seats and one future screening in it.

    Returns ``{"showtime_id", "room_id", "seat_ids"}``. Because the room is new, no other
    screening can overlap it, which is what makes ``start_screening_in_past`` safe (the
    exclusion constraint cannot be disabled). Needs no trigger changes.
    """

    def work(cur):
        room_name = "Spare " + uuid.uuid4().hex[:12]
        cur.execute("INSERT INTO theater_rooms(room_name) VALUES (%s) RETURNING room_id", (room_name,))
        room_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO seats(room_id, seat_row, seat_number) "
            "SELECT %s, chr(65 + r)::char(1), n FROM generate_series(0, 4) r, generate_series(1, 10) n",
            (room_id,),
        )
        cur.execute("SELECT seat_id FROM seats WHERE room_id = %s ORDER BY seat_id", (room_id,))
        seat_ids = [row[0] for row in cur.fetchall()]
        movie_id = _scalar(cur, "SELECT movie_id FROM movies ORDER BY movie_id LIMIT 1")
        cur.execute(
            "INSERT INTO showtimes(movie_id, room_id, starts_at, ends_at, ticket_price) "
            "VALUES (%s, %s, now() + make_interval(hours => %s), "
            "now() + make_interval(hours => %s) + interval '2 hours', %s) RETURNING showtime_id",
            (movie_id, room_id, starts_in_hours, starts_in_hours, ticket_price),
        )
        return {"showtime_id": cur.fetchone()[0], "room_id": room_id, "seat_ids": seat_ids}

    return _run(connection, work)


def start_screening_in_past(connection, showtime_id, started_minutes_ago=60):
    """Move a screening so that it started ``started_minutes_ago`` minutes ago.

    The screening keeps its duration. If another screening in the same room would overlap
    the new window the helper refuses (``TimeTravelError``) instead of tripping the
    exclusion constraint: use a screening from ``create_spare_room_screening``.
    """
    if started_minutes_ago <= 0:
        raise ValueError("started_minutes_ago must be positive")

    def work(cur):
        cur.execute(
            "SELECT room_id, ends_at - starts_at FROM showtimes WHERE showtime_id = %s",
            (showtime_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise TimeTravelError(f"screening {showtime_id} does not exist")
        room_id, duration = row
        cur.execute(
            "SELECT 1 FROM showtimes WHERE room_id = %s AND showtime_id <> %s AND "
            "tstzrange(starts_at, ends_at, '[)') && "
            "tstzrange(now() - make_interval(mins => %s), "
            "now() - make_interval(mins => %s) + %s, '[)')",
            (room_id, showtime_id, started_minutes_ago, started_minutes_ago, duration),
        )
        if cur.fetchone() is not None:
            raise TimeTravelError(
                "another screening in this room overlaps the target window; "
                "use create_spare_room_screening()"
            )
        cur.execute("ALTER TABLE showtimes DISABLE TRIGGER trg_showtimes_protect_booked")
        cur.execute(
            "UPDATE showtimes SET starts_at = now() - make_interval(mins => %s), "
            "ends_at = now() - make_interval(mins => %s) + %s WHERE showtime_id = %s",
            (started_minutes_ago, started_minutes_ago, duration, showtime_id),
        )
        cur.execute("ALTER TABLE showtimes ENABLE TRIGGER trg_showtimes_protect_booked")

    _run(connection, work)
