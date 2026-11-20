"""Customer booking operations (T5, T6): B03 C-06, C-07, C-08, C-09.

Every route requires a logged-in account with role CUSTOMER (Policy.CUSTOMER).
Administrators cannot make, pay or cancel customer bookings (BR-13, B03 CM-01).

PostgreSQL enforces all core booking rules (schema.sql):
* Atomic booking creation with create_booking()
* Atomic simulated payment with pay_booking()
* Atomic cancellation with cancel_booking()
* Request-time expiry with expire_overdue_bookings()
* Preserved history and seat release on cancellation/expiry (D1, D3)
"""

from flask import Blueprint, g, jsonify

from .body import json_body
from .database import expire_overdue_bookings, transaction
from .errors import HTTP_ERRORS, AppError, ValidationError
from .params import check_path_id
from .security import Policy, policy

bp = Blueprint("bookings", __name__, url_prefix="/bookings")

BOOKING_COLUMNS = """
    b.booking_id, b.user_id, b.showtime_id, m.title, s.starts_at, s.ends_at, r.room_name,
    s.ticket_price, b.booked_at, b.expires_at, b.total_amount, b.status, b.payment_status,
    b.paid_at, b.cancelled_at
"""
BOOKING_FROM = """
    FROM bookings b
    JOIN showtimes s ON s.showtime_id = b.showtime_id
    JOIN movies m ON m.movie_id = s.movie_id
    JOIN theater_rooms r ON r.room_id = s.room_id
"""


def fetch_booking(cur, booking_id, user_id=None):
    """Fetch booking dict with its seats (or empty list if cancelled/expired)."""
    if user_id is not None:
        cur.execute(
            f"SELECT {BOOKING_COLUMNS} {BOOKING_FROM} WHERE b.booking_id = %s AND b.user_id = %s",
            (booking_id, user_id),
        )
    else:
        cur.execute(
            f"SELECT {BOOKING_COLUMNS} {BOOKING_FROM} WHERE b.booking_id = %s",
            (booking_id,),
        )
    row = cur.fetchone()
    if row is None:
        return None
    booking = dict(row)

    if booking["status"] == "BOOKED":
        cur.execute(
            """
            SELECT se.seat_id, se.seat_row, se.seat_number, bs.price_at_booking
            FROM booking_seats bs
            JOIN seats se ON se.seat_id = bs.seat_id
            WHERE bs.booking_id = %s
            ORDER BY se.seat_row, se.seat_number
            """,
            (booking_id,),
        )
        booking["seats"] = [dict(r) for r in cur.fetchall()]
    else:
        booking["seats"] = []

    return booking


@bp.post("")
@policy(Policy.CUSTOMER)
def create_booking():
    body = json_body()
    problems = {}

    screening_id = body.get("screening_id")
    if screening_id is None or isinstance(screening_id, bool) or not isinstance(screening_id, int):
        problems["screening_id"] = "A valid positive screening ID is required."
    elif screening_id <= 0 or screening_id >= 2**63:
        problems["screening_id"] = "A valid positive screening ID is required."

    raw_seats = body.get("seat_ids")
    if not isinstance(raw_seats, list) or len(raw_seats) == 0:
        problems["seat_ids"] = "At least one seat must be selected."
    else:
        seat_ids = []
        has_invalid = False
        for s in raw_seats:
            if isinstance(s, bool) or not isinstance(s, int) or s <= 0 or s >= 2**63:
                has_invalid = True
                break
            seat_ids.append(s)
        if has_invalid:
            problems["seat_ids"] = "All seat IDs must be positive integers."
        elif len(seat_ids) != len(set(seat_ids)):
            problems["seat_ids"] = "Seat list contains duplicates."

    if problems:
        raise ValidationError(problems)

    user_id = g.current_user["user_id"]
    with transaction() as cur:
        cur.execute(
            "SELECT create_booking(%s, %s, %s) AS booking_id",
            (user_id, screening_id, seat_ids),
        )
        booking_id = cur.fetchone()["booking_id"]
        booking = fetch_booking(cur, booking_id, user_id)

    return jsonify(booking=booking), 201


@bp.post("/<int:booking_id>/pay")
@policy(Policy.CUSTOMER)
def pay_booking(booking_id):
    check_path_id(booking_id)
    user_id = g.current_user["user_id"]

    with transaction() as cur:
        cur.execute(
            "SELECT pay_booking(%s, %s) AS outcome",
            (booking_id, user_id),
        )
        outcome = cur.fetchone()["outcome"]  # 'PAID' or 'EXPIRED'
        booking = fetch_booking(cur, booking_id, user_id)

    return jsonify(outcome=outcome, booking=booking)


@bp.get("")
@policy(Policy.CUSTOMER)
def list_bookings():
    user_id = g.current_user["user_id"]

    with transaction() as cur:
        expire_overdue_bookings(cur)
        cur.execute(
            f"""
            SELECT {BOOKING_COLUMNS} {BOOKING_FROM}
            WHERE b.user_id = %s
            ORDER BY b.booked_at DESC, b.booking_id DESC
            """,
            (user_id,),
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
                b["seats"] = []
            bookings.append(b)

    return jsonify(bookings=bookings)


@bp.get("/<int:booking_id>")
@policy(Policy.CUSTOMER)
def get_booking(booking_id):
    check_path_id(booking_id)
    user_id = g.current_user["user_id"]

    with transaction() as cur:
        expire_overdue_bookings(cur)
        booking = fetch_booking(cur, booking_id, user_id)

    if booking is None:
        raise AppError(HTTP_ERRORS[404])

    return jsonify(booking=booking)


@bp.post("/<int:booking_id>/cancel")
@policy(Policy.CUSTOMER)
def cancel_booking(booking_id):
    check_path_id(booking_id)
    user_id = g.current_user["user_id"]

    with transaction() as cur:
        cur.execute(
            "SELECT cancel_booking(%s, %s) AS outcome",
            (booking_id, user_id),
        )
        outcome = cur.fetchone()["outcome"]  # 'CANCELLED' or 'EXPIRED'
        booking = fetch_booking(cur, booking_id, user_id)

    return jsonify(outcome=outcome, booking=booking)
