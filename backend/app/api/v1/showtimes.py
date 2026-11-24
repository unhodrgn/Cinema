"""Screening schedule (public): B03 C-03. Login is not required (D4).

``has_started`` is computed by the database clock. It is a display state only: the rule that
a started screening cannot be booked (BR-12) is enforced by the database when booking.
"""

from flask import Blueprint, current_app, jsonify

from app.core.database import expire_overdue_bookings, transaction
from app.core.errors import HTTP_ERRORS, AppError, ValidationError
from app.core.params import check_path_id, query_date, query_id
from app.core.security import Policy, policy

from app.models.showtime import SCREENING_COLUMNS, SCREENING_FROM
from app.services.showtime_service import fetch_screening

bp = Blueprint("screenings", __name__, url_prefix="/screenings")

@bp.get("")
@policy(Policy.PUBLIC)
def list_screenings():
    problems = {}
    movie_id = query_id("movie_id", problems)
    day = query_date("date", problems)
    if problems:
        raise ValidationError(problems)

    timezone = current_app.config["APP_TIMEZONE"]
    with transaction() as cur:
        if movie_id is not None:
            cur.execute("SELECT 1 FROM movies WHERE movie_id = %s", (movie_id,))
            if cur.fetchone() is None:
                raise AppError(HTTP_ERRORS[404])  # B03 C-03: an unknown movie is an error
        if day is None:  # today in the cinema's time zone, decided by the database
            cur.execute("SELECT (now() AT TIME ZONE %s)::date AS today", (timezone,))
            day = cur.fetchone()["today"].isoformat()
        # The whole local calendar day as a half-open range: [00:00 of the day, 00:00 next day)
        cur.execute(
            f"""
            SELECT {SCREENING_COLUMNS} {SCREENING_FROM}
            WHERE s.starts_at >= (%(day)s::date)::timestamp AT TIME ZONE %(tz)s
              AND s.starts_at <  ((%(day)s::date + 1)::timestamp AT TIME ZONE %(tz)s)
              AND (%(movie)s::bigint IS NULL OR s.movie_id = %(movie)s::bigint)
            ORDER BY s.starts_at, s.room_id
            """,
            {"day": day, "tz": timezone, "movie": movie_id},
        )
        screenings = [dict(row) for row in cur.fetchall()]
    return jsonify(date=day, screenings=screenings)


@bp.get("/<int:showtime_id>")
@policy(Policy.PUBLIC)
def get_screening(showtime_id):
    check_path_id(showtime_id)
    with transaction() as cur:
        screening = fetch_screening(cur, showtime_id)
    if screening is None:
        raise AppError(HTTP_ERRORS[404])
    return jsonify(screening=screening)


@bp.get("/<int:showtime_id>/seats")
@policy(Policy.PUBLIC)
def get_screening_seats(showtime_id):
    check_path_id(showtime_id)
    with transaction() as cur:
        expire_overdue_bookings(cur)
        screening = fetch_screening(cur, showtime_id)
        if screening is None:
            raise AppError(HTTP_ERRORS[404])
        cur.execute(
            """
            SELECT se.seat_id, se.seat_row, se.seat_number,
                   NOT EXISTS (
                     SELECT 1 FROM booking_seats bs JOIN bookings b ON b.booking_id = bs.booking_id
                     WHERE b.showtime_id = %(showtime)s AND bs.seat_id = se.seat_id AND b.status = 'BOOKED'
                       AND (b.payment_status = 'PAID' OR b.expires_at > clock_timestamp())
                   ) AS is_available
            FROM showtimes s JOIN seats se ON se.room_id = s.room_id
            WHERE s.showtime_id = %(showtime)s
            ORDER BY se.seat_row, se.seat_number
            """,
            {"showtime": showtime_id},
        )
        seats = [dict(row) for row in cur.fetchall()]
    return jsonify(screening=screening, seats=seats)
