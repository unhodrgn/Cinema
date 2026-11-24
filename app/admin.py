"""Admin operations (T7, T8): B03 A-01 (Movies), A-02 (Screenings), A-03 (Bookings).

All routes require Policy.ADMIN. Anonymous and CUSTOMER access is rejected with 401/403.
Follows decisions D2 (screening edit protection) and D5 (movie attributes).
"""

import datetime as dt
import re
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, request

from .body import json_body
from .database import expire_overdue_bookings, transaction
from .errors import HTTP_ERRORS, SCREENING_STARTED, AppError, ValidationError
from .params import check_path_id, query_id, strict_iso_date
from .security import Policy, policy

bp = Blueprint("admin", __name__, url_prefix="/admin")

MOVIE_COLUMNS = "movie_id, title, genre, duration_minutes, rating, synopsis, release_date, poster_url"

SCREENING_COLUMNS = """
    s.showtime_id, s.movie_id, m.title, m.poster_url, s.room_id, r.room_name,
    s.starts_at, s.ends_at, s.ticket_price,
    (s.starts_at <= clock_timestamp()) AS has_started,
    EXISTS (SELECT 1 FROM bookings b WHERE b.showtime_id = s.showtime_id) AS has_bookings
"""
SCREENING_FROM = """
    FROM showtimes s
    JOIN movies m ON m.movie_id = s.movie_id
    JOIN theater_rooms r ON r.room_id = s.room_id
"""


# Technical limits (not business rules): they keep every value inside what the database
# (numeric(10,2), timestamptz) and the JSON serialization can represent.
MAX_TICKET_PRICE = Decimal("99999999.99")
MIN_TIMESTAMP_YEAR = 1900
MAX_TIMESTAMP_YEAR = 2200


# Words for the person filling in the form: messages never show an internal field name.
_TIMESTAMP_LABELS = {"starts_at": "Start time", "ends_at": "End time"}


def _parse_timestamp(value, field_name, problems):
    """Parse an ISO timestamp string. If naive, localize to APP_TIMEZONE."""
    label = _TIMESTAMP_LABELS.get(field_name, "Date and time")
    if not isinstance(value, str) or not value.strip():
        problems[field_name] = f"{label} is required."
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            tz = ZoneInfo(current_app.config["APP_TIMEZONE"])
            parsed = parsed.replace(tzinfo=tz)
    except Exception:
        problems[field_name] = f"{label} must be a valid date and time."
        return None
    if not (MIN_TIMESTAMP_YEAR <= parsed.year <= MAX_TIMESTAMP_YEAR):
        problems[field_name] = (
            f"{label} must be between the years {MIN_TIMESTAMP_YEAR} and {MAX_TIMESTAMP_YEAR}."
        )
        return None
    return parsed


def _parse_price(raw, problems):
    """A ticket price: a finite number from 0 to MAX_TICKET_PRICE with at most two decimals."""
    if raw is None or isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
        problems["ticket_price"] = "Ticket price is required."
        return None
    try:
        price = Decimal(str(raw).strip())
        if not price.is_finite():
            raise InvalidOperation
        if price < 0:
            problems["ticket_price"] = "Ticket price cannot be negative."
            return None
        if price > MAX_TICKET_PRICE:
            problems["ticket_price"] = f"Ticket price must be at most {MAX_TICKET_PRICE}."
            return None
        if price != price.quantize(Decimal("0.01")):
            problems["ticket_price"] = "Ticket price can have at most two decimal places."
            return None
    except (InvalidOperation, ValueError):
        problems["ticket_price"] = "Ticket price must be a valid number."
        return None
    return price


# Same rule as the CHECK on movies.poster_url: a file directly under /images/posters/.
POSTER_PATH = re.compile(r"/images/posters/[A-Za-z0-9][A-Za-z0-9._-]*\.(jpg|png)")
POSTER_PROBLEM = "Poster path must look like /images/posters/name.jpg (at most 255 characters)."


def _validate_movie_input(body):
    problems = {}

    title = body.get("title")
    if not isinstance(title, str) or not title.strip():
        problems["title"] = "Title is required."
    elif len(title.strip()) > 200:
        problems["title"] = "Title must be at most 200 characters."
    else:
        title = title.strip()

    duration = body.get("duration_minutes")
    if duration is None:
        problems["duration_minutes"] = "Running time is required."
    elif isinstance(duration, bool) or not isinstance(duration, int):
        problems["duration_minutes"] = "Running time must be a whole number of minutes."
    elif not (1 <= duration <= 300):
        problems["duration_minutes"] = "Running time must be between 1 and 300 minutes."

    genre = body.get("genre")
    if genre is not None:
        if not isinstance(genre, str):
            problems["genre"] = "Genre must be text."
        else:
            genre = genre.strip() or None
            if genre and len(genre) > 100:
                problems["genre"] = "Genre must be at most 100 characters."

    rating = body.get("rating")
    if rating is not None:
        if not isinstance(rating, str):
            problems["rating"] = "Rating must be text."
        else:
            rating = rating.strip() or None
            if rating and len(rating) > 50:
                problems["rating"] = "Rating must be at most 50 characters."

    synopsis = body.get("synopsis")
    if synopsis is not None:
        if not isinstance(synopsis, str):
            problems["synopsis"] = "Synopsis must be text."
        else:
            synopsis = synopsis.strip() or None

    release_date = body.get("release_date")
    if release_date is not None:
        if not isinstance(release_date, str):
            problems["release_date"] = "Release date must be in YYYY-MM-DD format."
        else:
            release_date = release_date.strip() or None
            if release_date and strict_iso_date(release_date) is None:
                problems["release_date"] = "Release date must be in YYYY-MM-DD format."

    poster_url = body.get("poster_url")
    if poster_url is not None:
        if not isinstance(poster_url, str):
            problems["poster_url"] = POSTER_PROBLEM
        else:
            poster_url = poster_url.strip() or None
            if poster_url and (len(poster_url) > 255 or not POSTER_PATH.fullmatch(poster_url)):
                problems["poster_url"] = POSTER_PROBLEM

    if problems:
        raise ValidationError(problems)

    return {
        "title": title,
        "genre": genre,
        "duration_minutes": duration,
        "rating": rating,
        "synopsis": synopsis,
        "release_date": release_date,
        "poster_url": poster_url,
    }


# ======================================================================================
# T7: Movie Management (A-01)
# ======================================================================================


@bp.get("/movies")
@policy(Policy.ADMIN)
def admin_list_movies():
    with transaction() as cur:
        cur.execute(f"SELECT {MOVIE_COLUMNS} FROM movies ORDER BY movie_id ASC")
        movies = [dict(r) for r in cur.fetchall()]
    return jsonify(movies=movies)


@bp.get("/movies/<int:movie_id>")
@policy(Policy.ADMIN)
def admin_get_movie(movie_id):
    check_path_id(movie_id)
    with transaction() as cur:
        cur.execute(f"SELECT {MOVIE_COLUMNS} FROM movies WHERE movie_id = %s", (movie_id,))
        row = cur.fetchone()
    if row is None:
        raise AppError(HTTP_ERRORS[404])
    return jsonify(movie=dict(row))


@bp.post("/movies")
@policy(Policy.ADMIN)
def admin_create_movie():
    body = json_body()
    data = _validate_movie_input(body)

    with transaction() as cur:
        cur.execute(
            f"""
            INSERT INTO movies(title, genre, duration_minutes, rating, synopsis, release_date, poster_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING {MOVIE_COLUMNS}
            """,
            (
                data["title"],
                data["genre"],
                data["duration_minutes"],
                data["rating"],
                data["synopsis"],
                data["release_date"],
                data["poster_url"],
            ),
        )
        movie = dict(cur.fetchone())

    return jsonify(movie=movie), 201


@bp.put("/movies/<int:movie_id>")
@policy(Policy.ADMIN)
def admin_update_movie(movie_id):
    check_path_id(movie_id)
    body = json_body()
    data = _validate_movie_input(body)

    with transaction() as cur:
        cur.execute(
            f"""
            UPDATE movies
            SET title = %s, genre = %s, duration_minutes = %s, rating = %s, synopsis = %s, release_date = %s,
                poster_url = %s
            WHERE movie_id = %s
            RETURNING {MOVIE_COLUMNS}
            """,
            (
                data["title"],
                data["genre"],
                data["duration_minutes"],
                data["rating"],
                data["synopsis"],
                data["release_date"],
                data["poster_url"],
                movie_id,
            ),
        )
        row = cur.fetchone()

    if row is None:
        raise AppError(HTTP_ERRORS[404])

    return jsonify(movie=dict(row)), 200


# ======================================================================================
# T7: Screening Management (A-02)
# ======================================================================================


def _validate_screening_input(body):
    problems = {}

    movie_id = body.get("movie_id")
    if movie_id is None or isinstance(movie_id, bool) or not isinstance(movie_id, int) or movie_id <= 0:
        problems["movie_id"] = "Please choose a movie."

    room_id = body.get("room_id")
    if room_id is None or isinstance(room_id, bool) or not isinstance(room_id, int) or room_id <= 0:
        problems["room_id"] = "Please choose a theater room."

    starts_at = _parse_timestamp(body.get("starts_at"), "starts_at", problems)

    ends_at = None
    if body.get("ends_at"):
        ends_at = _parse_timestamp(body.get("ends_at"), "ends_at", problems)
        if starts_at and ends_at and ends_at <= starts_at:
            problems["ends_at"] = "End time must be strictly after start time."

    ticket_price = _parse_price(body.get("ticket_price"), problems)

    if problems:
        raise ValidationError(problems)

    return {
        "movie_id": movie_id,
        "room_id": room_id,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "ticket_price": ticket_price,
    }


def _fetch_screening_detail(cur, showtime_id):
    cur.execute(f"SELECT {SCREENING_COLUMNS} {SCREENING_FROM} WHERE s.showtime_id = %s", (showtime_id,))
    row = cur.fetchone()
    return dict(row) if row is not None else None


@bp.get("/screenings")
@policy(Policy.ADMIN)
def admin_list_screenings():
    problems = {}
    movie_id = query_id("movie_id", problems)
    if problems:
        raise ValidationError(problems)

    with transaction() as cur:
        cur.execute(
            f"""
            SELECT {SCREENING_COLUMNS} {SCREENING_FROM}
            WHERE (%(movie)s::bigint IS NULL OR s.movie_id = %(movie)s::bigint)
            ORDER BY s.starts_at DESC, s.room_id ASC
            """,
            {"movie": movie_id},
        )
        screenings = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT room_id, room_name FROM theater_rooms ORDER BY room_id ASC")
        rooms = [dict(r) for r in cur.fetchall()]

    return jsonify(screenings=screenings, rooms=rooms)


@bp.get("/screenings/<int:showtime_id>")
@policy(Policy.ADMIN)
def admin_get_screening(showtime_id):
    check_path_id(showtime_id)
    with transaction() as cur:
        screening = _fetch_screening_detail(cur, showtime_id)
    if screening is None:
        raise AppError(HTTP_ERRORS[404])
    return jsonify(screening=screening)


@bp.post("/screenings")
@policy(Policy.ADMIN)
def admin_create_screening():
    body = json_body()
    data = _validate_screening_input(body)

    with transaction() as cur:
        # Check movie and room existence
        cur.execute("SELECT 1 FROM movies WHERE movie_id = %s", (data["movie_id"],))
        if cur.fetchone() is None:
            raise ValidationError({"movie_id": "Referenced movie does not exist."})

        cur.execute("SELECT 1 FROM theater_rooms WHERE room_id = %s", (data["room_id"],))
        if cur.fetchone() is None:
            raise ValidationError({"room_id": "Referenced room does not exist."})

        # Insert showtime. If ends_at is NULL, trigger trg_showtimes_default_end_time sets it.
        # If overlapping, EXCLUDE constraint raises 23P01 (mapped to 409 screening_overlap).
        cur.execute(
            """
            INSERT INTO showtimes(movie_id, room_id, starts_at, ends_at, ticket_price)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING showtime_id
            """,
            (
                data["movie_id"],
                data["room_id"],
                data["starts_at"],
                data["ends_at"],
                data["ticket_price"],
            ),
        )
        showtime_id = cur.fetchone()["showtime_id"]
        screening = _fetch_screening_detail(cur, showtime_id)

    return jsonify(screening=screening), 201


@bp.put("/screenings/<int:showtime_id>")
@policy(Policy.ADMIN)
def admin_update_screening(showtime_id):
    check_path_id(showtime_id)
    body = json_body()
    data = _validate_screening_input(body)

    with transaction() as cur:
        # Existence, and whether it has started (database clock, like BR-12). The row is locked so
        # a start-time edit cannot race with this check. A started screening is never edited
        # (any change, even an identical save); the D2 rule below (bookings) applies as well.
        cur.execute(
            "SELECT starts_at <= clock_timestamp() AS has_started FROM showtimes WHERE showtime_id = %s FOR UPDATE",
            (showtime_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise AppError(HTTP_ERRORS[404])
        if row["has_started"]:
            raise AppError(SCREENING_STARTED)

        cur.execute("SELECT 1 FROM movies WHERE movie_id = %s", (data["movie_id"],))
        if cur.fetchone() is None:
            raise ValidationError({"movie_id": "Referenced movie does not exist."})

        cur.execute("SELECT 1 FROM theater_rooms WHERE room_id = %s", (data["room_id"],))
        if cur.fetchone() is None:
            raise ValidationError({"room_id": "Referenced room does not exist."})

        # D2: trigger trg_showtimes_protect_booked raises UC001 (mapped to 409 screening_has_bookings)
        # if ANY booking references this screening (regardless of status).
        cur.execute(
            """
            UPDATE showtimes
            SET movie_id = %s,
                room_id = %s,
                starts_at = %s,
                ends_at = COALESCE(%s, %s::timestamptz + (SELECT duration_minutes FROM movies WHERE movie_id = %s) * interval '1 minute'),
                ticket_price = %s
            WHERE showtime_id = %s
            RETURNING showtime_id
            """,
            (
                data["movie_id"],
                data["room_id"],
                data["starts_at"],
                data["ends_at"],
                data["starts_at"],
                data["movie_id"],
                data["ticket_price"],
                showtime_id,
            ),
        )
        screening = _fetch_screening_detail(cur, showtime_id)

    return jsonify(screening=screening), 200


# ======================================================================================
# T8: Admin Booking List (A-03, View-Only)
# ======================================================================================


ADMIN_BOOKING_COLUMNS = """
    b.booking_id, b.user_id, u.username, b.showtime_id, m.title,
    s.starts_at, s.ends_at, r.room_name, s.ticket_price,
    b.booked_at, b.expires_at, b.total_amount, b.status, b.payment_status,
    b.paid_at, b.cancelled_at
"""
ADMIN_BOOKING_FROM = """
    FROM bookings b
    JOIN users u ON u.user_id = b.user_id
    JOIN showtimes s ON s.showtime_id = b.showtime_id
    JOIN movies m ON m.movie_id = s.movie_id
    JOIN theater_rooms r ON r.room_id = s.room_id
"""


@bp.get("/bookings")
@policy(Policy.ADMIN)
def admin_list_bookings():
    problems = {}
    status_filter = request.args.get("status")
    if status_filter:
        status_filter = status_filter.strip().upper()
        if status_filter not in {"BOOKED", "CANCELLED", "EXPIRED"}:
            problems["status"] = "Status must be BOOKED, CANCELLED, or EXPIRED."

    screening_id = query_id("screening_id", problems)
    user_id = query_id("user_id", problems)

    if problems:
        raise ValidationError(problems)

    with transaction() as cur:
        expire_overdue_bookings(cur)
        cur.execute(
            f"""
            SELECT {ADMIN_BOOKING_COLUMNS} {ADMIN_BOOKING_FROM}
            WHERE (%(status)s IS NULL OR b.status = %(status)s)
              AND (%(screening)s::bigint IS NULL OR b.showtime_id = %(screening)s::bigint)
              AND (%(user)s::bigint IS NULL OR b.user_id = %(user)s::bigint)
            ORDER BY b.booked_at DESC, b.booking_id DESC
            """,
            {"status": status_filter or None, "screening": screening_id, "user": user_id},
        )
        rows = cur.fetchall()
        bookings = []
        for r in rows:
            b = dict(r)
            if b["status"] == "BOOKED":
                cur.execute(
                    """
                    SELECT se.seat_id, se.seat_row, se.seat_number, bs.price_at_booking
                    FROM booking_seats bs
                    JOIN seats se ON se.seat_id = bs.seat_id
                    WHERE bs.booking_id = %s
                    ORDER BY se.seat_row, se.seat_number
                    """,
                    (b["booking_id"],),
                )
                b["seats"] = [dict(s) for s in cur.fetchall()]
            else:
                # Cancelled and expired bookings do not expose seat lists (D1, D3)
                b["seats"] = []
            bookings.append(b)

    return jsonify(bookings=bookings)
