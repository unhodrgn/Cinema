"""Reading ids and simple query parameters safely (shared by the API modules).

* A path id above the bigint maximum is harmless in a plain comparison (it matches no row),
  but PostgreSQL raises an error when it is passed to a bigint FUNCTION parameter such as
  ``pay_booking(id, user)`` (HTTP 500). ``check_path_id`` turns every such id into the
  ordinary 404 up front, so no endpoint has to remember which of its queries is the risky one.
* Query parameters are strings from the client: they are validated here and reported as
  ``400 validation_error`` with a ``fields`` object, never passed on unchecked.
"""

import datetime as dt
import re

from flask import request

from .errors import HTTP_ERRORS, AppError

MAX_ID = 2**63 - 1  # the largest value of a bigint identity column

_ID_PATTERN = re.compile(r"^[0-9]{1,19}$")
_DATE_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")

ID_MESSAGE = "Must be a positive whole number."
DATE_MESSAGE = "Use the format YYYY-MM-DD, for example 2026-11-25."


def check_path_id(value):
    """``value`` if it is a usable id, else raise the standard 404."""
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= MAX_ID:
        raise AppError(HTTP_ERRORS[404])
    return value


def query_id(name, problems):
    """An optional positive integer query parameter, or None. Adds to ``problems`` if invalid."""
    text = (request.args.get(name) or "").strip()
    if text == "":
        return None
    if _ID_PATTERN.fullmatch(text) and 1 <= int(text) <= MAX_ID:
        return int(text)
    problems[name] = ID_MESSAGE
    return None


def query_date(name, problems):
    """An optional ``YYYY-MM-DD`` query parameter as an ISO string, or None.

    Strictly that shape: ``20261125`` or ``2026-W47-3`` (which ``date.fromisoformat`` would
    accept) are refused, as is any impossible date.
    """
    text = (request.args.get(name) or "").strip()
    if text == "":
        return None
    if _DATE_PATTERN.fullmatch(text):
        try:
            return dt.date.fromisoformat(text).isoformat()
        except ValueError:
            pass
    problems[name] = DATE_MESSAGE
    return None
