"""A fake psycopg2 driver for unit tests: records everything, needs no server.

``FakeDriver.connect`` replaces ``psycopg2.connect``. Connections remember their
connect parameters and an ordered list of events ("commit", "rollback", "close") and
executed statements, and emulate psycopg2's transaction status (idle / in transaction).
"""

import psycopg2
from psycopg2.extensions import TRANSACTION_STATUS_IDLE, TRANSACTION_STATUS_INTRANS

# Application settings for tests that use the fake driver. DB_NAME is a made-up name:
# nothing ever connects to it.
FAKE_DB_CONFIG = {
    "DB_HOST": "db.example.org",
    "DB_PORT": 5999,
    "DB_NAME": "cinema_test_fake",
    "DB_USER": "fake_user",
    "DB_PASSWORD": "pw-secret-123",
}

DEFAULT_RESPONSES = {
    "SELECT 1 AS ok": [{"ok": 1}],
    "SELECT expire_overdue_bookings() AS expired": [{"expired": 0}],
}


class FakeInfo:
    def __init__(self, connection):
        self._connection = connection

    @property
    def transaction_status(self):
        return self._connection.status


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.closed = False
        self.executed = []
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
        return False

    def execute(self, sql, params=None):
        connection = self.connection
        if connection.closed:
            raise psycopg2.InterfaceError("connection already closed")
        self.executed.append((sql, params))
        connection.statements.append((sql, params))
        connection.status = TRANSACTION_STATUS_INTRANS
        if connection.fail_execute is not None:
            raise connection.fail_execute
        self._rows = list(connection.responses.get(sql, []))

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, driver, kwargs):
        self.kwargs = kwargs
        self.closed = 0
        self.status = TRANSACTION_STATUS_IDLE
        self.events = []
        self.statements = []
        self.cursors = []
        self.responses = dict(driver.responses)
        self.info = FakeInfo(self)
        self.fail_execute = None
        self.fail_commit = None
        self.fail_rollback = None
        self.fail_close = None

    def cursor(self):
        cursor = FakeCursor(self)
        self.cursors.append(cursor)
        return cursor

    def commit(self):
        self.events.append("commit")
        self.status = TRANSACTION_STATUS_IDLE
        if self.fail_commit is not None:
            raise self.fail_commit

    def rollback(self):
        self.events.append("rollback")
        if self.fail_rollback is not None:
            raise self.fail_rollback
        self.status = TRANSACTION_STATUS_IDLE

    def close(self):
        self.events.append("close")
        self.closed = 1
        if self.fail_close is not None:
            raise self.fail_close


class FakeDriver:
    def __init__(self):
        self.connections = []
        self.connect_kwargs = []
        self.fail_with = None
        self.responses = dict(DEFAULT_RESPONSES)

    def connect(self, **kwargs):
        self.connect_kwargs.append(kwargs)
        if self.fail_with is not None:
            raise self.fail_with
        connection = FakeConnection(self, kwargs)
        self.connections.append(connection)
        return connection

    @property
    def last(self):
        return self.connections[-1]


def database_error(pgcode, message="SELECT secret FROM users WHERE password = 'hunter2'"):
    """A psycopg2 error that reports ``pgcode`` (the real attribute is read-only)."""
    error_class = type("FakeDatabaseError", (psycopg2.DatabaseError,), {"pgcode": pgcode})
    return error_class(message)
