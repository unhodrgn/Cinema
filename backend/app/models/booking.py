BOOKING_COLUMNS = """
    b.booking_id, b.user_id, b.showtime_id, m.title, m.poster_url, s.starts_at, s.ends_at, r.room_name,
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
