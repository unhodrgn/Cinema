"""PostgreSQL access: the only module that opens connections.

One connection is opened lazily per application context (per request), the first time
``get_db()`` is called, and is always rolled back and closed when the context ends.
Nothing is ever committed implicitly.

The supported way to run SQL is ``with transaction() as cur:``: one user action is one
transaction, committed when the block ends normally and rolled back on any exception
(integration contract, section 4). Use it for reads as well, so no transaction is ever
left open.
"""

import logging
from contextlib import contextmanager

import psycopg2
from flask import current_app, g
from psycopg2.extensions import TRANSACTION_STATUS_IDLE
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

DEFAULT_APPLICATION_NAME = "cinema_flask"


class DatabaseUnavailableError(Exception):
    """The database cannot be reached or is not configured.

    The message is deliberately generic and safe to show: it never contains the host,
    user, password or the driver's error text. Details go to the log (without secrets).
    """


class TransactionError(RuntimeError):
    """``transaction()`` was misused (for example nested). This is a programming error."""


def connect(config):
    """Open a new connection from an application config mapping.

    Uses ``DB_HOST``, ``DB_PORT``, ``DB_NAME``, ``DB_USER``, ``DB_PASSWORD``,
    ``DB_CONNECT_TIMEOUT``, ``APP_TIMEZONE`` and (optionally) ``DB_APPLICATION_NAME``.
    The session time zone is ``APP_TIMEZONE``; rows are returned as dicts.

    Raises ``DatabaseUnavailableError`` if ``DB_NAME`` is not configured (the driver
    would otherwise silently connect to a database named after the user) or if the
    connection fails.
    """
    dbname = config.get("DB_NAME")
    if not dbname:
        logger.error("DB_NAME is not configured; refusing to connect")
        raise DatabaseUnavailableError("the database is not configured")

    params = {
        "host": config.get("DB_HOST"),
        "port": config.get("DB_PORT"),
        "dbname": dbname,
        "connect_timeout": config.get("DB_CONNECT_TIMEOUT"),
        "application_name": config.get("DB_APPLICATION_NAME") or DEFAULT_APPLICATION_NAME,
        "cursor_factory": RealDictCursor,
    }
    if config.get("DB_USER"):
        params["user"] = config["DB_USER"]
    if config.get("DB_PASSWORD"):
        params["password"] = config["DB_PASSWORD"]
    if config.get("APP_TIMEZONE"):
        # APP_TIMEZONE was format-checked by the config (no spaces or quotes).
        params["options"] = f"-c TimeZone={config['APP_TIMEZONE']}"

    try:
        return psycopg2.connect(**params)
    except psycopg2.Error as error:
        # Never log the driver's message (it can name the host and user) or the config.
        logger.error(
            "could not connect to PostgreSQL (%s); check the DB_* settings", type(error).__name__
        )
        raise DatabaseUnavailableError("the database is unavailable") from None


def get_db():
    """The current context's connection, opened on first use.

    A connection that has been closed (for example after the server dropped it) is
    replaced by a new one. If connecting fails, ``DatabaseUnavailableError`` is raised
    and nothing is stored, so a later call tries again.
    """
    connection = g.get("db")
    if connection is not None and connection.closed:
        g.pop("db", None)
        connection = None
    if connection is None:
        connection = connect(current_app.config)
        g.db = connection
    return connection


def close_db(exception=None):
    """Teardown: roll back anything uncommitted and close the connection.

    Never commits and never raises, so a broken connection cannot mask the original
    error of the request.
    """
    connection = g.pop("db", None)
    if connection is None:
        return
    try:
        if not connection.closed:
            connection.rollback()
    except psycopg2.Error as error:
        logger.warning("rollback during cleanup failed (%s)", type(error).__name__)
    finally:
        try:
            connection.close()
        except psycopg2.Error as error:
            logger.warning("closing the connection failed (%s)", type(error).__name__)


def init_app(app):
    """Register connection cleanup. Does not open any connection."""
    app.teardown_appcontext(close_db)


def _rollback(connection):
    try:
        if not connection.closed:
            connection.rollback()
    except psycopg2.Error as error:
        # The original exception is what matters; a broken connection is replaced by
        # get_db() or discarded by close_db().
        logger.warning("rollback failed (%s)", type(error).__name__)


@contextmanager
def transaction():
    """Run a block as one database transaction and yield a cursor (dict rows).

    * Normal exit: ``COMMIT``. A commit can fail (the deferred consistency checks of
      the schema run at COMMIT, contract section 4): the transaction is rolled back and
      the error is raised.
    * Any exception, including ``KeyboardInterrupt``: ``ROLLBACK``, then the exception
      propagates unchanged.
    * The cursor is always closed. The connection stays open until the context ends
      (``close_db``), so several transactions can follow each other in one request.

    ``pay_booking`` and ``cancel_booking`` can return ``'EXPIRED'``: that is a committed
    outcome, not an error. Do not raise before leaving the block.

    Not re-entrant: calling it while a transaction is open (nested, or after SQL was run
    outside it) raises ``TransactionError`` instead of silently joining it.
    """
    connection = get_db()
    # PostgreSQL starts a transaction lazily, at the first statement, so the connection
    # status alone cannot detect an outer block that has not run SQL yet: keep a flag too.
    if g.get("db_transaction_active") or (
        connection.info.transaction_status != TRANSACTION_STATUS_IDLE
    ):
        raise TransactionError(
            "a transaction is already open on this connection; transaction() cannot be nested"
        )
    g.db_transaction_active = True
    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except BaseException:
        _rollback(connection)
        raise
    finally:
        g.db_transaction_active = False
        try:
            cursor.close()
        except psycopg2.Error:
            pass


def first_value(row):
    """The first column of a fetched row, whether it is a dict row or a tuple."""
    if row is None:
        return None
    if isinstance(row, dict):
        return next(iter(row.values()))
    return row[0]


def expire_overdue_bookings(cur):
    """Expire every overdue unpaid booking (D3) and return how many were expired.

    Calls the database function ``expire_overdue_bookings()`` on the supplied cursor,
    so it joins the caller's transaction: the expiry is committed together with the
    rest of the request, and an availability or history query that follows in the same
    transaction sees the result. It opens no connection of its own.

    The function's optional ``p_as_of`` argument exists only for database tests; it is
    never passed. Nothing runs by itself (no scheduler): callers invoke this before
    seat availability, booking history and admin booking lists (contract section 3.3).
    """
    cur.execute("SELECT expire_overdue_bookings() AS expired")
    return int(first_value(cur.fetchone()))
