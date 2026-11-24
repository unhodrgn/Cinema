"""Safe provisioning of disposable PostgreSQL databases for tests.

A disposable database is created, filled with the canonical ``backend/migrations/0001_baseline.sql``
and ``backend/seeds/demo.sql``, used by tests, and dropped again. Because this code issues
``CREATE DATABASE`` and ``DROP DATABASE``, it is deliberately paranoid:

* Every name must match ``cinema_test_[a-z0-9_]+``; anything else is refused before
  any SQL is sent. The same pattern makes the name safe to quote by hand.
* The database named by DB_NAME / PGDATABASE (the developer's normal database) is
  refused even if it happens to match the pattern.
* The only databases this module ever connects to are the maintenance database
  (``postgres``) and the disposable database it created itself.
* A database is dropped only if (1) this process created it, (2) its name is in the
  per-process registry, and (3) its database comment carries this session's random
  marker. If any check fails, nothing is dropped and ``UnsafeDatabaseError`` is raised.
* Credentials never appear in messages or reprs.
"""

import re
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = BACKEND_DIR / "migrations" / "0001_baseline.sql"
SEED_PATH = BACKEND_DIR / "seeds" / "demo.sql"

TEST_DB_PREFIX = "cinema_test_"
MAINTENANCE_DATABASE = "postgres"
APPLICATION_NAME = "cinema_test_fixture"

_NAME_PATTERN = re.compile(r"^cinema_test_[a-z0-9_]{1,40}$")

# Random per process. Written into the database comment of every database created here
# and checked again before dropping, so only a database created by *this* session can
# ever be dropped, whatever its name.
SESSION_TOKEN = uuid.uuid4().hex
MARKER = f"cinema-test-disposable:{SESSION_TOKEN}"

_created_this_session = set()


class UnsafeDatabaseError(RuntimeError):
    """A safety check failed; the operation was refused or aborted."""


class DatabaseSetupError(RuntimeError):
    """Creating or populating the disposable database failed."""


# --- names ----------------------------------------------------------------------------


def generate_database_name():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{TEST_DB_PREFIX}{stamp}_{uuid.uuid4().hex[:8]}"


def assert_disposable_name(name, forbidden_names=()):
    """Return ``name`` if it is safe to create, connect to or drop; else raise."""
    if not isinstance(name, str) or not _NAME_PATTERN.match(name):
        raise UnsafeDatabaseError(
            f"refusing database name {name!r}: it must match {_NAME_PATTERN.pattern}"
        )
    if name.lower() in {forbidden.lower() for forbidden in forbidden_names if forbidden}:
        raise UnsafeDatabaseError(
            f"refusing database name {name!r}: it is the configured development database"
        )
    return name


def _quote(name):
    # Only called with names that passed assert_disposable_name (letters, digits, _).
    return f'"{name}"'


def _first_line(error):
    lines = str(error).strip().splitlines()
    return lines[0] if lines else type(error).__name__


# --- server settings ------------------------------------------------------------------


DEFAULT_TEST_HOST = "127.0.0.1"


class PortNotConfiguredError(Exception):
    """TEST_DB_PORT is not set, so no connection may be attempted."""


@dataclass(frozen=True)
class ServerSettings:
    """Where the PostgreSQL test server is and which role may create test databases.

    The port has no default on purpose: it must always be chosen explicitly.
    """

    port: int
    host: str = DEFAULT_TEST_HOST
    user: str = None
    password: str = field(default=None, repr=False)
    connect_timeout: int = 5

    def __post_init__(self):
        if isinstance(self.port, bool) or not isinstance(self.port, int) or not 1 <= self.port <= 65535:
            raise UnsafeDatabaseError("refusing to connect: the test server port must be explicit")


def _lookup(name, environ, dotenv):
    for source in (environ, dotenv or {}):
        value = (source.get(name) or "").strip()
        if value:
            return value
    return None


def read_server_settings(environ, dotenv=None):
    """Server settings from the environment (``dotenv`` values rank below it).

    * Port: TEST_DB_PORT only. It is required; if it is missing or blank,
      ``PortNotConfiguredError`` is raised. DB_PORT, PGPORT and 5432 are never used.
    * Host: TEST_DB_HOST, default 127.0.0.1. DB_HOST is not used.
    * Role: TEST_DB_ADMIN_USER, falling back to DB_USER; password:
      TEST_DB_ADMIN_PASSWORD, falling back to DB_PASSWORD.
    * DB_NAME is never read here.
    """
    port_text = _lookup("TEST_DB_PORT", environ, dotenv)
    if port_text is None:
        raise PortNotConfiguredError(
            "TEST_DB_PORT is not set, so the PostgreSQL integration tests are skipped. "
            "Set TEST_DB_PORT (and optionally TEST_DB_HOST, TEST_DB_ADMIN_USER and "
            "TEST_DB_ADMIN_PASSWORD) to a disposable PostgreSQL server. DB_PORT, PGPORT "
            "and port 5432 are never used as a fallback."
        )
    try:
        port = int(port_text)
    except ValueError:
        raise ValueError("TEST_DB_PORT must be an integer between 1 and 65535") from None
    if not 1 <= port <= 65535:
        raise ValueError("TEST_DB_PORT must be an integer between 1 and 65535")
    return ServerSettings(
        port=port,
        host=_lookup("TEST_DB_HOST", environ, dotenv) or DEFAULT_TEST_HOST,
        user=_lookup("TEST_DB_ADMIN_USER", environ, dotenv) or _lookup("DB_USER", environ, dotenv),
        password=_lookup("TEST_DB_ADMIN_PASSWORD", environ, dotenv)
        or _lookup("DB_PASSWORD", environ, dotenv),
    )


def read_forbidden_names(environ, dotenv=None):
    """Database names that must never be used as a test database."""
    names = {_lookup("DB_NAME", environ, dotenv), _lookup("PGDATABASE", environ, dotenv)}
    return frozenset(name for name in names if name)


# --- connections ----------------------------------------------------------------------


def _open(settings, dbname, autocommit):
    if dbname != MAINTENANCE_DATABASE:
        assert_disposable_name(dbname)
    params = {
        "host": settings.host,
        "port": settings.port,
        "dbname": dbname,
        "connect_timeout": settings.connect_timeout,
        "application_name": APPLICATION_NAME,
    }
    if settings.user:
        params["user"] = settings.user
    if settings.password:
        params["password"] = settings.password
    connection = psycopg2.connect(**params)
    connection.autocommit = autocommit
    return connection


def check_server(settings):
    """Connect to the maintenance database once. Raises ``psycopg2.OperationalError``."""
    _open(settings, MAINTENANCE_DATABASE, autocommit=True).close()


# --- the disposable database ----------------------------------------------------------


class DisposableDatabase:
    """One test database: ``create()``, ``apply_sql_file()``, ``connect()``, ``drop()``."""

    def __init__(self, settings, name=None, forbidden_names=()):
        self.settings = settings
        self.forbidden_names = frozenset(forbidden_names)
        self.name = assert_disposable_name(name or generate_database_name(), self.forbidden_names)
        self.created = False

    def __repr__(self):
        return f"<DisposableDatabase {self.name} created={self.created}>"

    def create(self, template=None, busy_retry_seconds=2.0):
        """Create this database, empty or cloned from ``template``.

        ``template`` is another ``DisposableDatabase`` and must itself have been created
        by this process (registry) and carry this session's marker: a database this
        session did not create is never used as a template. ``CREATE DATABASE ...
        TEMPLATE`` does not copy the database comment, so the marker is always written
        again below. PostgreSQL refuses the clone while anything is connected to the
        template, so nothing may keep a connection to it open. A session that was only
        just closed can linger for a moment, hence the short retry before giving up.
        """
        assert_disposable_name(self.name, self.forbidden_names)
        if self.created:
            raise UnsafeDatabaseError(f"{self.name} was already created by this fixture")
        template_clause = ""
        if template is not None:
            template._require_owned()
            template_clause = f" TEMPLATE {_quote(template.name)}"
        admin = _open(self.settings, MAINTENANCE_DATABASE, autocommit=True)
        try:
            with admin.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.name,))
                if cur.fetchone():
                    raise UnsafeDatabaseError(
                        f"refusing to create {self.name}: a database with that name already exists"
                    )
                deadline = time.monotonic() + busy_retry_seconds
                while True:
                    try:
                        cur.execute(f"CREATE DATABASE {_quote(self.name)}{template_clause}")
                        break
                    except psycopg2.errors.ObjectInUse:
                        if time.monotonic() >= deadline:
                            raise DatabaseSetupError(
                                f"cannot clone {template.name}: a connection to the template "
                                "is open (nothing may connect to a template database)"
                            ) from None
                        time.sleep(0.05)
                self.created = True
                _created_this_session.add(self.name)
                try:
                    cur.execute(f"COMMENT ON DATABASE {_quote(self.name)} IS %s", (MARKER,))
                except psycopg2.Error as error:
                    raise UnsafeDatabaseError(
                        f"created {self.name} but could not mark it as disposable "
                        f"({_first_line(error)}); it is left in place and must be removed manually"
                    ) from None
        finally:
            admin.close()

    def connect(self):
        """A new non-autocommit connection to the disposable database (caller closes it)."""
        self._require_created()
        return _open(self.settings, self.name, autocommit=False)

    def apply_sql_file(self, path):
        """Run a whole SQL script (it may contain its own BEGIN/COMMIT)."""
        self._require_created()
        path = Path(path)
        try:
            script = path.read_text(encoding="utf-8")
        except OSError as error:
            raise DatabaseSetupError(f"could not read {path.name}: {_first_line(error)}") from None
        connection = _open(self.settings, self.name, autocommit=True)
        try:
            with connection.cursor() as cur:
                cur.execute(script)  # no parameters, so '%' in the script is left alone
        except psycopg2.Error as error:
            raise DatabaseSetupError(
                f"could not apply {path.name} to {self.name}: [{error.pgcode}] {_first_line(error)}"
            ) from None
        finally:
            connection.close()

    def app_config(self):
        """Overrides for ``create_app("testing", overrides)`` pointing at this database."""
        self._require_created()
        return {
            "DB_HOST": self.settings.host,
            "DB_PORT": self.settings.port,
            "DB_NAME": self.name,
            "DB_USER": self.settings.user,
            "DB_PASSWORD": self.settings.password,
            "DB_CONNECT_TIMEOUT": self.settings.connect_timeout,
        }

    def drop(self):
        """Drop this database, but only after every ownership check has passed."""
        assert_disposable_name(self.name, self.forbidden_names)
        if not self.created or self.name not in _created_this_session:
            raise UnsafeDatabaseError(f"refusing to drop {self.name}: not created by this fixture")
        admin = _open(self.settings, MAINTENANCE_DATABASE, autocommit=True)
        try:
            with admin.cursor() as cur:
                cur.execute(
                    "SELECT shobj_description(oid, 'pg_database') FROM pg_database "
                    "WHERE datname = %s",
                    (self.name,),
                )
                row = cur.fetchone()
                if row is None:
                    self.created = False  # already gone
                    _created_this_session.discard(self.name)
                    return
                if row[0] != MARKER:
                    raise UnsafeDatabaseError(
                        f"refusing to drop {self.name}: it does not carry this session's marker"
                    )
                cur.execute(f"DROP DATABASE {_quote(self.name)} WITH (FORCE)")
                self.created = False
                _created_this_session.discard(self.name)
        finally:
            admin.close()

    def _require_created(self):
        assert_disposable_name(self.name, self.forbidden_names)
        if not self.created:
            raise UnsafeDatabaseError(f"{self.name} has not been created by this fixture")

    def _require_owned(self):
        """Raise unless this database was created by this process and still carries its marker."""
        self._require_created()
        if self.name not in _created_this_session:
            raise UnsafeDatabaseError(f"{self.name} is not in this session's registry")
        admin = _open(self.settings, MAINTENANCE_DATABASE, autocommit=True)
        try:
            with admin.cursor() as cur:
                cur.execute(
                    "SELECT shobj_description(oid, 'pg_database') FROM pg_database "
                    "WHERE datname = %s",
                    (self.name,),
                )
                row = cur.fetchone()
        finally:
            admin.close()
        if row is None or row[0] != MARKER:
            raise UnsafeDatabaseError(f"{self.name} does not carry this session's marker")


@contextmanager
def provision_database(settings, schema_path, seed_path, forbidden_names=()):
    """Create a disposable database with schema and seed applied; always clean it up.

    If setup fails half way, the database created so far is dropped before the error
    propagates. A database that was never created is never dropped.
    """
    database = DisposableDatabase(settings, forbidden_names=forbidden_names)
    try:
        database.create()
        database.apply_sql_file(schema_path)
        database.apply_sql_file(seed_path)
        yield database
    finally:
        if database.created:
            database.drop()


@contextmanager
def clone_database(template, forbidden_names=()):
    """A private, fully seeded copy of ``template`` for one test; always dropped afterwards.

    ``template`` must be a database created by this process (see ``DisposableDatabase.create``).
    The clone is created and dropped through the same checks as any disposable database:
    name pattern, registry, session marker (written again, it is not copied) and the
    development-database refusal.
    """
    clone = DisposableDatabase(template.settings, forbidden_names=forbidden_names)
    try:
        clone.create(template=template)
        yield clone
    finally:
        if clone.created:
            clone.drop()
