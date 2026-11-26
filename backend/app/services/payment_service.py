from app.core.database import run_retryable_transaction
from app.models.booking import fetch_booking


def pay(booking_id, user_id):
    def _pay_once(cur):
        cur.execute(
            "SELECT pay_booking(%s, %s) AS outcome",
            (booking_id, user_id),
        )
        outcome = cur.fetchone()["outcome"]  # 'PAID' or 'EXPIRED'
        booking = fetch_booking(cur, booking_id, user_id)
        return outcome, booking

    return run_retryable_transaction(_pay_once)
