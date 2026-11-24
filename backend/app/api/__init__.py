"""The REST API under ``/api`` (docs/api/api_contract.md).

``bp`` is the ``/api`` blueprint. Feature modules define their own blueprints and are
registered on it at the bottom of this file, before ``create_app`` registers ``bp`` on the
application (a blueprint cannot gain children after it has been registered once).
"""

from flask import Blueprint, jsonify

from app.core.body import json_body  # noqa: F401  (re-exported: ``from app.api import json_body``)
from app.core.security import Policy, policy

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("")
@policy(Policy.PUBLIC)
def service_info():
    """Tells a client (or a person with a browser) that this is the API and that it is up."""
    return jsonify({"service": "cinema-reservation-api", "status": "ok"})


from .v1 import admin, auth, bookings, movies, payments, showtimes  # noqa: E402  (after ``bp`` exists; none imports this module)

bp.register_blueprint(admin.bp)
bp.register_blueprint(auth.bp)
bp.register_blueprint(bookings.bp)
bp.register_blueprint(payments.bp)
bp.register_blueprint(movies.bp)
bp.register_blueprint(showtimes.bp)
