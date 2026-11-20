"""Translation of database errors into application errors and safe HTTP responses.

``SQLSTATE_ERRORS`` follows section 6 of the PostgreSQL-Flask integration contract: the
database reports problems with stable SQLSTATE codes (``UC001`` ... ``UC011`` and the
standard ``23xxx`` codes) and the application matches on ``error.pgcode``, never on
message text.

Nothing the driver says (SQL text, constraint or column names, hosts, users, passwords,
connection strings, tracebacks) ever reaches a response: responses carry only the fixed
``code`` and ``message`` below. Details go to the log.

Every response is JSON: ``{"error": {"code": ..., "message": ...}}``, plus a ``fields``
object only for validation errors. This includes Flask's own HTTP errors (404, 405, 413,
...), which are converted from the default HTML pages to the same envelope. The
independent frontend renders messages from these values; the backend never renders pages.
"""

import logging
from dataclasses import dataclass

import psycopg2
from flask import current_app, jsonify
from werkzeug.exceptions import HTTPException

from .database import DatabaseUnavailableError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ErrorInfo:
    status: int  # HTTP status
    code: str  # stable machine-readable name
    message: str  # fixed, user-safe text
    internal: bool = False  # True: an application bug or infrastructure fault, not user error


class AppError(Exception):
    """An error that carries an ``ErrorInfo`` and becomes an HTTP response.

    ``fields`` (field name -> fixed message) is added to the body for validation errors;
    ``headers`` are extra response headers such as ``WWW-Authenticate``.
    """

    def __init__(self, info, fields=None, headers=None):
        super().__init__(info.code)
        self.info = info
        self.fields = dict(fields) if fields else None
        self.headers = dict(headers) if headers else None


INTERNAL_ERROR = ErrorInfo(
    500, "internal_error", "Something went wrong on our side. Please try again later.", True
)
DATABASE_UNAVAILABLE = ErrorInfo(
    503,
    "database_unavailable",
    "The service is temporarily unavailable. Please try again later.",
    True,
)

# API-level errors (docs/api/api_contract.md). Messages are fixed text: they never echo
# request data, parser output or exception messages.
UNAUTHORIZED = ErrorInfo(401, "unauthorized", "Authentication is required.")
# One message for an unknown account and for a wrong password (B03 CM-01): the response
# must never reveal which of the two it was.
INVALID_CREDENTIALS = ErrorInfo(
    401, "invalid_credentials", "The account ID or password is incorrect."
)
FORBIDDEN = ErrorInfo(403, "forbidden", "You do not have permission to do this.")
VALIDATION_ERROR = ErrorInfo(400, "validation_error", "One or more fields are not valid.")
INVALID_JSON = ErrorInfo(400, "invalid_json", "The request body must be a valid JSON object.")
UNSUPPORTED_MEDIA_TYPE = ErrorInfo(
    415, "unsupported_media_type", "Requests with a body must use Content-Type: application/json."
)

# Flask / Werkzeug HTTP errors, by status. ``exception.description`` is never used.
HTTP_ERRORS = {
    400: ErrorInfo(400, "bad_request", "The request could not be understood."),
    401: UNAUTHORIZED,
    403: FORBIDDEN,
    404: ErrorInfo(404, "not_found", "The requested resource was not found."),
    405: ErrorInfo(
        405, "method_not_allowed", "This method is not allowed for the requested resource."
    ),
    413: ErrorInfo(413, "payload_too_large", "The request body is too large."),
    415: UNSUPPORTED_MEDIA_TYPE,
}
# Headers worth keeping from a Werkzeug HTTP exception (its Content-Type is HTML).
_KEPT_HTTP_HEADERS = ("Allow", "WWW-Authenticate", "Retry-After")

# Contract section 6. "Suggested response" column in comments.
SQLSTATE_ERRORS = {
    # admin edits a screening that has any booking record (D2)
    "UC001": ErrorInfo(
        409, "screening_has_bookings", "This screening has bookings and cannot be modified."
    ),
    # seat already reserved for this screening, including a lost race: re-select seats
    "UC002": ErrorInfo(
        409,
        "seat_unavailable",
        "One or more of the selected seats are no longer available. Please choose again.",
    ),
    # seat belongs to another room: internal / tampering error
    "UC003": ErrorInfo(400, "invalid_seat", "The selected seats are not valid for this screening."),
    # booking for a screening that already started: block
    "UC004": ErrorInfo(409, "screening_started", "This screening has already started."),
    # cancellation after the screening started: block
    "UC005": ErrorInfo(
        409,
        "cancellation_closed",
        "This booking can no longer be cancelled because the screening has started.",
    ),
    # payment / cancel not allowed in the booking's state: explain the state
    "UC006": ErrorInfo(
        409,
        "invalid_booking_state",
        "This action is not possible for the booking in its current state.",
    ),
    # illegal change (immutable column, illegal transition, ...): the application bug
    "UC007": INTERNAL_ERROR,
    # booking owner is not a CUSTOMER (for example an ADMIN): block
    "UC008": ErrorInfo(403, "customer_only", "Only customer accounts can make bookings."),
    # price snapshot / total mismatch: the application bug (use create_booking)
    "UC009": INTERNAL_ERROR,
    # empty or duplicate seat list, BOOKED booking without seats: select at least one seat
    "UC010": ErrorInfo(400, "no_seat_selected", "Please select at least one seat."),
    # booking / screening not found for this user: 404
    "UC011": ErrorInfo(404, "not_found", "The requested booking or screening was not found."),
    # duplicate username (registration) or duplicate seat position
    "23505": ErrorInfo(409, "duplicate_value", "That value is already in use."),
    # unknown user / seat / screening / movie / room id
    "23503": ErrorInfo(400, "unknown_reference", "A referenced record does not exist."),
    # CHECK violation (role, duration, row/number, price, end before start)
    "23514": ErrorInfo(400, "invalid_value", "One of the submitted values is not valid."),
    # screening overlaps another one in the same room (BR-04): ask for another time
    "23P01": ErrorInfo(
        409,
        "screening_overlap",
        "This screening overlaps another screening in the same room. Please choose another time.",
    ),
    # deleting a referenced row: not an application feature
    "23001": INTERNAL_ERROR,
}


def describe_database_error(error):
    """The ``ErrorInfo`` for a psycopg2 error, chosen by its SQLSTATE only.

    Unknown or missing SQLSTATEs map to a generic 500, except lost or refused
    connections (``OperationalError`` / ``InterfaceError``), which map to 503.
    """
    info = SQLSTATE_ERRORS.get(getattr(error, "pgcode", None))
    if info is not None:
        return info
    if isinstance(error, (psycopg2.OperationalError, psycopg2.InterfaceError)):
        return DATABASE_UNAVAILABLE
    return INTERNAL_ERROR


def translate_database_error(error):
    """Turn a psycopg2 error into an ``AppError`` (use as ``raise translate_...(e) from e``)."""
    return AppError(describe_database_error(error))


class ValidationError(AppError):
    """Invalid request data: HTTP 400 ``validation_error`` with a ``fields`` object."""

    def __init__(self, fields):
        super().__init__(VALIDATION_ERROR, fields=fields)


def describe_http_error(error):
    """The ``ErrorInfo`` for a Werkzeug ``HTTPException``, chosen by its status only."""
    info = HTTP_ERRORS.get(error.code)
    if info is not None:
        return info
    status = error.code or 500
    if status >= 500:
        return ErrorInfo(status, "server_error", INTERNAL_ERROR.message, True)
    return ErrorInfo(status, "http_error", "The request could not be processed.")


def error_response(info, fields=None, headers=None):
    body = {"error": {"code": info.code, "message": info.message}}
    if fields:
        body["error"]["fields"] = fields
    response = jsonify(body)
    response.status_code = info.status
    response.headers["Cache-Control"] = "no-store"
    for name, value in (headers or {}).items():
        response.headers[name] = value
    return response


def _handle_app_error(error):
    return error_response(error.info, fields=error.fields, headers=error.headers)


def _handle_database_unavailable(error):
    # connect() already logged the cause without secrets.
    return error_response(DATABASE_UNAVAILABLE)


def _handle_database_error(error):
    info = describe_database_error(error)
    # Only the SQLSTATE and the exception class are logged, never the driver message
    # (it can contain SQL text and data values).
    logger.log(
        logging.ERROR if info.internal else logging.INFO,
        "database error %s (SQLSTATE %s) -> HTTP %s",
        type(error).__name__,
        getattr(error, "pgcode", None),
        info.status,
    )
    return error_response(info)


def _handle_unexpected_error(error):
    if isinstance(error, HTTPException):
        if error.response is not None:
            return error.response  # abort(response): the caller built it deliberately
        # 404, 405, 413, ...: same status and headers as before, but the JSON envelope
        # instead of Werkzeug's HTML page.
        headers = {
            name: value for name, value in error.get_headers() if name in _KEPT_HTTP_HEADERS
        }
        info = describe_http_error(error)
        if info.internal:
            logger.error("HTTP error %s", error.code)
        return error_response(info, headers=headers)
    if current_app.debug:
        raise error  # let the interactive debugger show the real problem
    logger.exception("unhandled %s", type(error).__name__)
    return error_response(INTERNAL_ERROR)


def register_error_handlers(app):
    """Register the handlers. Flask picks the most specific one for each exception."""
    app.register_error_handler(AppError, _handle_app_error)
    app.register_error_handler(DatabaseUnavailableError, _handle_database_unavailable)
    app.register_error_handler(psycopg2.Error, _handle_database_error)
    app.register_error_handler(Exception, _handle_unexpected_error)
