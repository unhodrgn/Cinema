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

from app.core.body import json_body
from app.core.database import expire_overdue_bookings, transaction
from app.core.errors import HTTP_ERRORS, AppError
from app.core.params import check_path_id
from app.core.security import Policy, policy

from app.models.booking import BOOKING_COLUMNS, BOOKING_FROM, fetch_booking
from app.schemas.booking import booking_request
from app.services.booking_service import reserve

bp = Blueprint("bookings", __name__, url_prefix="/bookings")

@bp.post("")
@policy(Policy.CUSTOMER)
def create_booking():
    body = json_body()
    screening_id, seat_ids = booking_request(body)
    user_id = g.current_user["user_id"]
    booking = reserve(user_id, screening_id, seat_ids)
    return jsonify(booking=booking), 201


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
