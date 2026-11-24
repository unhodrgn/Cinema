from app.core.database import transaction
from app.models.booking import fetch_booking


def reserve(user_id, screening_id, seat_ids):
    with transaction() as cur:
        cur.execute(
            "SELECT create_booking(%s, %s, %s) AS booking_id",
            (user_id, screening_id, seat_ids),
        )
        booking_id = cur.fetchone()["booking_id"]
        booking = fetch_booking(cur, booking_id, user_id)

    return booking
