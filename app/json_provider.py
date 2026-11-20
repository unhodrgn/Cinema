"""JSON serialization rules of the API (docs/api/api_contract.md, section 4).

* ``datetime``  ISO 8601 **with** a UTC offset, e.g. ``2026-11-25T19:00:00+09:00``. A naive
                datetime is refused: it would be ambiguous for the frontend (the database
                always returns timezone-aware values for ``timestamptz``).
* ``date``      ISO 8601 date, e.g. ``2026-11-25``.
* ``Decimal``   a decimal **string**, e.g. ``"12000.00"``, never a float, so money never
                loses precision in JavaScript.

Everything else behaves like Flask's default provider (for instance ``uuid``).
"""

import datetime as dt
from decimal import Decimal

from flask.json.provider import DefaultJSONProvider


def _api_default(value):
    if isinstance(value, dt.datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise TypeError("naive datetime cannot be serialized; use a timezone-aware value")
        return value.isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    return DefaultJSONProvider.default(value)


class ApiJSONProvider(DefaultJSONProvider):
    default = staticmethod(_api_default)
