"""Health-check endpoints.

``GET /health``     the application is running (touches no database).
``GET /health/db``  the application can reach PostgreSQL and run a query: 200 only if
                    ``SELECT 1`` really returned 1, otherwise 503.

Responses are deliberately minimal: no host, port, database name, user, version or error
text. The cause of a failure is in the log (without secrets).
"""

import logging

import psycopg2
from flask import Blueprint, jsonify

from .database import DatabaseUnavailableError, first_value, transaction

logger = logging.getLogger(__name__)

bp = Blueprint("health", __name__)


def _json(body, status=200):
    response = jsonify(body)
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/health")
def health():
    return _json({"status": "ok"})


@bp.get("/health/db")
def health_db():
    try:
        with transaction() as cur:
            cur.execute("SELECT 1 AS ok")
            value = first_value(cur.fetchone())
    except DatabaseUnavailableError:
        # connect() already logged the reason.
        return _json({"status": "unavailable", "database": "unavailable"}, 503)
    except psycopg2.Error as error:
        logger.warning("database health check failed (%s)", type(error).__name__)
        return _json({"status": "unavailable", "database": "unavailable"}, 503)

    if value != 1:
        logger.warning("database health check got an unexpected result")
        return _json({"status": "unavailable", "database": "unavailable"}, 503)
    return _json({"status": "ok", "database": "ok"})
