from flask import Blueprint, g, jsonify

from app.core.params import check_path_id
from app.core.security import Policy, policy
from app.services.payment_service import pay

bp = Blueprint("payments", __name__, url_prefix="/bookings")


@bp.post("/<int:booking_id>/pay")
@policy(Policy.CUSTOMER)
def pay_booking(booking_id):
    check_path_id(booking_id)
    user_id = g.current_user["user_id"]

    outcome, booking = pay(booking_id, user_id)
    return jsonify(outcome=outcome, booking=booking)
