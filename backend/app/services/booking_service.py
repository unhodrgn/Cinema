import psycopg2

from app.core.database import run_retryable_transaction
from app.core.errors import ValidationError
from app.models.booking import fetch_booking


def reserve(user_id, screening_id, seat_ids):
    def _reserve_once(cur):
        cur.execute(
            """
            SELECT (SELECT count(*) FROM seats se WHERE se.room_id = s.room_id) AS capacity
            FROM showtimes s
            WHERE s.showtime_id = %s
            """,
            (screening_id,),
        )
        row = cur.fetchone()
        if row is not None and len(seat_ids) > row["capacity"]:
            raise ValidationError(
                {"seat_ids": f"Cannot book more than {row['capacity']} seats for this screening room."}
            )

        try:
            cur.execute(
                "SELECT create_booking(%s, %s, %s) AS booking_id",
                (user_id, screening_id, seat_ids),
            )
        except psycopg2.DataError as error:
            if getattr(error, "pgcode", None) == "22003":
                raise ValidationError(
                    {"seat_ids": "Selected seat count or total amount exceeds the allowed limit."}
                ) from error
            raise
        booking_id = cur.fetchone()["booking_id"]
        return fetch_booking(cur, booking_id, user_id)

    return run_retryable_transaction(_reserve_once)
