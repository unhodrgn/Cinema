"""Safety logic of the disposable-database helper, tested against a fake server.

No PostgreSQL server is needed here: ``psycopg2.connect`` is replaced by a fake that
records every connection and every statement, so the tests can prove what was (and,
more importantly, what was not) sent to the server.
"""

import os
import re
import subprocess
import sys

import psycopg2
import pytest

import disposable_db
from app import config
from disposable_db import (
    DatabaseSetupError,
    DisposableDatabase,
    ServerSettings,
    UnsafeDatabaseError,
)

SETTINGS = ServerSettings(host="db.example.org", port=5999, user="tester", password="pw-secret-123")


class FakeCursor:
    def __init__(self, connection):
        self._connection = connection
        self._row = None

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, sql, params=None):
        self._row = self._connection.server.handle(sql, params)

    def fetchone(self):
        return self._row


class FakeConnection:
    def __init__(self, server, dbname):
        self.server = server
        self.dbname = dbname
        self.autocommit = False
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True


class FakeServer:
    """Just enough of PostgreSQL for the statements disposable_db sends."""

    def __init__(self, databases=None, fail_marker=False, fail_script_containing=None):
        self.databases = dict(databases or {})  # name -> database comment
        self.fail_marker = fail_marker
        self.fail_script_containing = fail_script_containing
        self.connect_kwargs = []
        self.statements = []  # (sql, params)

    def connect(self, **kwargs):
        self.connect_kwargs.append(kwargs)
        return FakeConnection(self, kwargs["dbname"])

    def handle(self, sql, params):
        self.statements.append((sql, params))
        if sql.startswith("SELECT 1 FROM pg_database"):
            return (1,) if params[0] in self.databases else None
        if sql.startswith("SELECT shobj_description"):
            return (self.databases[params[0]],) if params[0] in self.databases else None
        if sql.startswith("CREATE DATABASE"):
            self.databases[sql.split('"')[1]] = None
            return None
        if sql.startswith("COMMENT ON DATABASE"):
            if self.fail_marker:
                raise psycopg2.Error("permission denied")
            self.databases[sql.split('"')[1]] = params[0]
            return None
        if sql.startswith("DROP DATABASE"):
            del self.databases[sql.split('"')[1]]
            return None
        if self.fail_script_containing and self.fail_script_containing in sql:
            raise psycopg2.Error("syntax error at or near ...")
        return None

    @property
    def dropped(self):
        return [sql for sql, _ in self.statements if sql.startswith("DROP DATABASE")]

    @property
    def created(self):
        return [sql for sql, _ in self.statements if sql.startswith("CREATE DATABASE")]

    @property
    def databases_connected_to(self):
        return {kwargs["dbname"] for kwargs in self.connect_kwargs}


@pytest.fixture
def server(monkeypatch):
    fake = FakeServer()
    monkeypatch.setattr(disposable_db.psycopg2, "connect", fake.connect)
    monkeypatch.setattr(disposable_db, "_created_this_session", set())
    return fake


@pytest.fixture
def sql_files(tmp_path):
    schema = tmp_path / "schema.sql"
    seed = tmp_path / "seed.sql"
    schema.write_text("-- schema script 100% fine\nCREATE TABLE t();", encoding="utf-8")
    seed.write_text("-- seed script\nINSERT INTO t DEFAULT VALUES;", encoding="utf-8")
    return schema, seed


# --- name rules -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["cinema_test_a", "cinema_test_20261120120000_1a2b3c4d", "cinema_test_" + "x" * 40],
)
def test_valid_names_are_accepted(name):
    assert disposable_db.assert_disposable_name(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "postgres",
        "template1",
        "cinema",
        "cinema_dev",
        "cinema_test",  # no suffix
        "cinema_test_",  # empty suffix
        "xcinema_test_a",
        "Cinema_Test_a",
        "cinema_test_A",
        "cinema_test_a-b",
        "cinema_test_a b",
        'cinema_test_a"; DROP DATABASE postgres; --',
        "cinema_test_" + "x" * 41,
        "",
        None,
        123,
    ],
)
def test_names_without_the_prefix_or_with_unsafe_characters_are_refused(name):
    with pytest.raises(UnsafeDatabaseError):
        disposable_db.assert_disposable_name(name)


def test_generated_names_are_valid_prefixed_and_unique():
    names = {disposable_db.generate_database_name() for _ in range(50)}

    assert len(names) == 50
    for name in names:
        assert name.startswith(disposable_db.TEST_DB_PREFIX)
        disposable_db.assert_disposable_name(name)


def test_the_configured_development_database_is_refused_even_with_the_prefix():
    with pytest.raises(UnsafeDatabaseError, match="development database"):
        disposable_db.assert_disposable_name("cinema_test_mine", {"cinema_test_mine"})
    with pytest.raises(UnsafeDatabaseError):
        disposable_db.assert_disposable_name("cinema_test_mine", {"CINEMA_TEST_MINE"})


def test_constructor_refuses_bad_names_without_touching_the_server(server):
    for bad in ("postgres", "cinema_dev", "cinema_test_x; DROP"):
        with pytest.raises(UnsafeDatabaseError):
            DisposableDatabase(SETTINGS, name=bad)

    assert server.connect_kwargs == []


def test_connections_to_other_databases_are_refused(server):
    with pytest.raises(UnsafeDatabaseError):
        disposable_db._open(SETTINGS, "cinema_dev", autocommit=True)

    assert server.connect_kwargs == []


# --- server settings: the test port must be explicit ---------------------------------


def test_missing_test_port_raises_and_never_connects(monkeypatch):
    attempts = []
    monkeypatch.setattr(disposable_db.psycopg2, "connect", lambda **kw: attempts.append(kw))

    with pytest.raises(disposable_db.PortNotConfiguredError, match="TEST_DB_PORT is not set"):
        disposable_db.read_server_settings({})

    assert attempts == []


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_blank_test_port_counts_as_missing(blank):
    with pytest.raises(disposable_db.PortNotConfiguredError):
        disposable_db.read_server_settings({"TEST_DB_PORT": blank})


@pytest.mark.parametrize(
    "environ",
    [
        {"DB_PORT": "5432"},
        {"PGPORT": "5432"},
        {"DB_PORT": "5432", "PGPORT": "5432", "DB_HOST": "localhost", "DB_USER": "u"},
        {"DB_PORT": "54329"},
    ],
)
def test_other_port_variables_never_become_the_test_port(environ):
    with pytest.raises(disposable_db.PortNotConfiguredError):
        disposable_db.read_server_settings(environ)
    with pytest.raises(disposable_db.PortNotConfiguredError):
        disposable_db.read_server_settings({}, environ)  # same names coming from .env


def test_db_port_5432_does_not_override_an_explicit_test_port():
    settings = disposable_db.read_server_settings(
        {"DB_PORT": "5432", "PGPORT": "5432", "TEST_DB_PORT": "54329"}
    )

    assert settings.port == 54329


def test_explicit_test_port_is_used_by_the_connection(monkeypatch):
    fake = FakeServer()
    monkeypatch.setattr(disposable_db.psycopg2, "connect", fake.connect)
    monkeypatch.setattr(disposable_db, "_created_this_session", set())
    settings = disposable_db.read_server_settings({"TEST_DB_PORT": "54329", "DB_PORT": "5432"})

    disposable_db.check_server(settings)
    db = DisposableDatabase(settings)
    db.create()
    db.drop()

    assert {kwargs["port"] for kwargs in fake.connect_kwargs} == {54329}


def test_explicit_port_5432_is_accepted_when_chosen_deliberately():
    assert disposable_db.read_server_settings({"TEST_DB_PORT": "5432"}).port == 5432


@pytest.mark.parametrize("value", ["abc", "0", "-1", "65536", "5432.5", "54 29"])
def test_invalid_test_port_is_rejected(value):
    with pytest.raises(ValueError, match="TEST_DB_PORT"):
        disposable_db.read_server_settings({"TEST_DB_PORT": value, "DB_PASSWORD": "pw-secret-123"})


def test_server_settings_have_no_default_port():
    with pytest.raises(TypeError):
        ServerSettings()


@pytest.mark.parametrize("port", [None, 0, -5, 70000, "5432", True, 54.0])
def test_server_settings_refuse_a_missing_or_invalid_port(port):
    with pytest.raises(UnsafeDatabaseError, match="port must be explicit"):
        ServerSettings(port=port)


def test_host_comes_from_test_db_host_and_defaults_to_loopback():
    assert disposable_db.read_server_settings({"TEST_DB_PORT": "1"}).host == "127.0.0.1"
    assert disposable_db.DEFAULT_TEST_HOST == "127.0.0.1"

    explicit = disposable_db.read_server_settings({"TEST_DB_PORT": "1", "TEST_DB_HOST": "10.0.0.5"})
    assert explicit.host == "10.0.0.5"


def test_db_host_is_not_a_fallback_for_the_test_host():
    settings = disposable_db.read_server_settings(
        {"TEST_DB_PORT": "1", "DB_HOST": "production-db.example.org"},
        {"DB_HOST": "also-not-used.example.org"},
    )

    assert settings.host == "127.0.0.1"


def test_settings_prefer_the_test_admin_role_and_fall_back_to_the_app_role():
    environ = {
        "TEST_DB_PORT": "6000",
        "DB_USER": "app_user",
        "DB_PASSWORD": "app_pw",
        "TEST_DB_ADMIN_USER": "admin_user",
        "TEST_DB_ADMIN_PASSWORD": "admin_pw",
    }
    with_admin = disposable_db.read_server_settings(environ)
    assert with_admin.port == 6000
    assert (with_admin.user, with_admin.password) == ("admin_user", "admin_pw")

    without_admin = disposable_db.read_server_settings(
        {key: value for key, value in environ.items() if not key.startswith("TEST_DB_ADMIN")}
    )
    assert (without_admin.user, without_admin.password) == ("app_user", "app_pw")


def test_role_defaults_when_nothing_is_configured():
    settings = disposable_db.read_server_settings({"TEST_DB_PORT": "6000"})

    assert (settings.user, settings.password) == (None, None)


def test_blank_test_admin_values_fall_back():
    settings = disposable_db.read_server_settings(
        {
            "TEST_DB_PORT": "1",
            "DB_USER": "u",
            "DB_PASSWORD": "p",
            "TEST_DB_ADMIN_USER": " ",
            "TEST_DB_ADMIN_PASSWORD": "",
        }
    )

    assert (settings.user, settings.password) == ("u", "p")


def test_environment_wins_over_dotenv_values():
    settings = disposable_db.read_server_settings(
        {"TEST_DB_HOST": "from-env"},
        {"TEST_DB_HOST": "from-dotenv", "TEST_DB_PORT": "6100", "DB_USER": None},
    )

    assert settings.host == "from-env"
    assert settings.port == 6100
    assert settings.user is None


def test_db_name_is_never_part_of_the_server_settings():
    settings = disposable_db.read_server_settings(
        {"TEST_DB_PORT": "1", "DB_NAME": "cinema_dev", "PGDATABASE": "other"}
    )

    assert "cinema_dev" not in repr(settings)
    assert not hasattr(settings, "dbname") and not hasattr(settings, "database")


def test_forbidden_names_come_from_db_name_and_pgdatabase():
    names = disposable_db.read_forbidden_names(
        {"DB_NAME": "from_env"}, {"DB_NAME": "ignored_dotenv", "PGDATABASE": "pg_db"}
    )

    assert names == {"from_env", "pg_db"}


def test_settings_repr_hides_the_password():
    assert "pw-secret-123" not in repr(SETTINGS)


# --- create, connect and drop ---------------------------------------------------------


def test_create_marks_the_database_and_drop_removes_it(server):
    db = DisposableDatabase(SETTINGS)
    db.create()

    assert db.created and db.name in server.databases
    assert server.databases[db.name] == disposable_db.MARKER
    assert db.name in disposable_db._created_this_session

    db.drop()

    assert not db.created and db.name not in server.databases
    assert server.dropped == [f'DROP DATABASE "{db.name}" WITH (FORCE)']
    assert db.name not in disposable_db._created_this_session


def test_only_the_maintenance_and_the_new_database_are_ever_contacted(server, sql_files):
    schema, seed = sql_files
    with disposable_db.provision_database(SETTINGS, schema, seed) as db:
        name = db.name

    assert server.databases_connected_to == {disposable_db.MAINTENANCE_DATABASE, name}


def test_connection_parameters_are_passed_to_the_driver(server):
    db = DisposableDatabase(SETTINGS)
    db.create()

    kwargs = server.connect_kwargs[0]
    assert (kwargs["host"], kwargs["port"], kwargs["user"], kwargs["password"]) == (
        "db.example.org",
        5999,
        "tester",
        "pw-secret-123",
    )
    assert kwargs["dbname"] == disposable_db.MAINTENANCE_DATABASE
    assert kwargs["application_name"] == disposable_db.APPLICATION_NAME


def test_create_refuses_an_existing_database(server):
    db = DisposableDatabase(SETTINGS, name="cinema_test_existing")
    server.databases["cinema_test_existing"] = "someone else's database"

    with pytest.raises(UnsafeDatabaseError, match="already exists"):
        db.create()

    assert server.created == []
    assert not db.created
    assert server.databases == {"cinema_test_existing": "someone else's database"}


def test_create_twice_is_refused(server):
    db = DisposableDatabase(SETTINGS)
    db.create()

    with pytest.raises(UnsafeDatabaseError, match="already created"):
        db.create()


def test_connect_and_app_config_require_a_created_database(server):
    db = DisposableDatabase(SETTINGS)

    with pytest.raises(UnsafeDatabaseError):
        db.connect()
    with pytest.raises(UnsafeDatabaseError):
        db.app_config()
    assert server.connect_kwargs == []


def test_connect_returns_a_non_autocommit_connection(server):
    db = DisposableDatabase(SETTINGS)
    db.create()

    connection = db.connect()

    assert connection.autocommit is False
    assert connection.dbname == db.name


def test_app_config_targets_the_disposable_database(server):
    db = DisposableDatabase(SETTINGS)
    db.create()

    assert db.app_config() == {
        "DB_HOST": "db.example.org",
        "DB_PORT": 5999,
        "DB_NAME": db.name,
        "DB_USER": "tester",
        "DB_PASSWORD": "pw-secret-123",
        "DB_CONNECT_TIMEOUT": 5,
    }


# --- drop protection ------------------------------------------------------------------


def test_drop_refuses_a_database_this_fixture_did_not_create(server):
    server.databases["cinema_test_bystander"] = None
    db = DisposableDatabase(SETTINGS, name="cinema_test_bystander")

    with pytest.raises(UnsafeDatabaseError, match="not created by this fixture"):
        db.drop()

    assert server.connect_kwargs == [] and server.dropped == []
    assert "cinema_test_bystander" in server.databases


def test_drop_refuses_when_the_name_is_not_in_the_session_registry(server):
    server.databases["cinema_test_forged"] = None
    db = DisposableDatabase(SETTINGS, name="cinema_test_forged")
    db.created = True  # forged flag, but the registry never saw this database

    with pytest.raises(UnsafeDatabaseError, match="not created by this fixture"):
        db.drop()

    assert server.dropped == []


def test_drop_refuses_a_database_without_this_sessions_marker(server):
    db = DisposableDatabase(SETTINGS)
    db.create()
    server.databases[db.name] = "cinema-test-disposable:some-other-session"

    with pytest.raises(UnsafeDatabaseError, match="marker"):
        db.drop()

    assert server.dropped == [] and db.name in server.databases


def test_drop_refuses_a_database_with_no_comment_at_all(server):
    db = DisposableDatabase(SETTINGS)
    db.create()
    server.databases[db.name] = None

    with pytest.raises(UnsafeDatabaseError, match="marker"):
        db.drop()

    assert server.dropped == []


def test_drop_of_a_database_that_is_already_gone_is_harmless(server):
    db = DisposableDatabase(SETTINGS)
    db.create()
    del server.databases[db.name]

    db.drop()

    assert server.dropped == [] and not db.created


def test_drop_refuses_the_development_database_name(server):
    db = DisposableDatabase(SETTINGS, name="cinema_test_mine")
    db.create()
    db.forbidden_names = frozenset({"cinema_test_mine"})

    with pytest.raises(UnsafeDatabaseError, match="development database"):
        db.drop()

    assert server.dropped == []


def test_if_the_marker_cannot_be_written_nothing_is_dropped(server):
    server.fail_marker = True
    db = DisposableDatabase(SETTINGS)

    with pytest.raises(UnsafeDatabaseError, match="left in place"):
        db.create()

    assert db.name in server.databases
    with pytest.raises(UnsafeDatabaseError, match="marker"):
        db.drop()
    assert server.dropped == []


# --- provisioning and partial failure -------------------------------------------------


def test_provision_applies_schema_then_seed_and_cleans_up(server, sql_files):
    schema, seed = sql_files
    with disposable_db.provision_database(SETTINGS, schema, seed) as db:
        name = db.name
        assert name in server.databases
        scripts = [sql for sql, _ in server.statements if sql.startswith("-- ")]
        assert "schema script" in scripts[0] and "seed script" in scripts[1]

    assert name not in server.databases
    assert len(server.dropped) == 1


def test_scripts_are_sent_without_parameters_so_percent_signs_survive(server, sql_files):
    schema, seed = sql_files
    with disposable_db.provision_database(SETTINGS, schema, seed):
        pass

    sent = [(sql, params) for sql, params in server.statements if sql.startswith("-- ")]
    assert all(params is None for _, params in sent)
    assert "100% fine" in sent[0][0]


def test_scripts_run_in_autocommit_mode(server, sql_files, monkeypatch):
    modes = []

    def recording_connect(**kwargs):
        connection = server.connect(**kwargs)
        modes.append(connection)
        return connection

    monkeypatch.setattr(disposable_db.psycopg2, "connect", recording_connect)
    schema, _ = sql_files
    db = DisposableDatabase(SETTINGS)
    db.create()
    db.apply_sql_file(schema)

    script_connection = modes[-1]
    assert script_connection.dbname == db.name
    assert script_connection.autocommit is True and script_connection.closed


@pytest.mark.parametrize("failing", ["schema script", "seed script"])
def test_failure_during_setup_drops_the_partial_database(server, sql_files, failing):
    schema, seed = sql_files
    server.fail_script_containing = failing

    with pytest.raises(DatabaseSetupError) as excinfo:
        with disposable_db.provision_database(SETTINGS, schema, seed):
            pytest.fail("the body must not run when setup fails")

    assert server.databases == {}
    assert len(server.dropped) == 1
    assert "pw-secret-123" not in str(excinfo.value)


def test_failure_to_create_drops_nothing(server, sql_files, monkeypatch):
    schema, seed = sql_files
    server.databases["cinema_test_taken"] = "someone else's database"
    monkeypatch.setattr(disposable_db, "generate_database_name", lambda: "cinema_test_taken")

    with pytest.raises(UnsafeDatabaseError, match="already exists"):
        with disposable_db.provision_database(SETTINGS, schema, seed):
            pytest.fail("the body must not run")

    assert server.dropped == []
    assert server.databases == {"cinema_test_taken": "someone else's database"}


def test_a_missing_sql_file_is_a_setup_error_and_cleans_up(server, tmp_path):
    with pytest.raises(DatabaseSetupError, match="could not read missing.sql"):
        with disposable_db.provision_database(SETTINGS, tmp_path / "missing.sql", tmp_path / "x"):
            pytest.fail("the body must not run")

    assert server.databases == {}


def test_an_exception_in_the_test_body_still_cleans_up(server, sql_files):
    schema, seed = sql_files

    with pytest.raises(RuntimeError, match="test failure"):
        with disposable_db.provision_database(SETTINGS, schema, seed):
            raise RuntimeError("test failure")

    assert server.databases == {}


def test_forbidden_name_aborts_before_anything_is_created(server, sql_files, monkeypatch):
    schema, seed = sql_files
    monkeypatch.setattr(disposable_db, "generate_database_name", lambda: "cinema_test_mine")

    with pytest.raises(UnsafeDatabaseError, match="development database"):
        with disposable_db.provision_database(
            SETTINGS, schema, seed, forbidden_names={"cinema_test_mine"}
        ):
            pytest.fail("the body must not run")

    assert server.connect_kwargs == [] and server.databases == {}


def test_setup_errors_never_contain_the_password(server, sql_files):
    schema, seed = sql_files
    server.fail_script_containing = "schema script"

    with pytest.raises(DatabaseSetupError) as excinfo:
        with disposable_db.provision_database(SETTINGS, schema, seed):
            pass

    assert "pw-secret-123" not in str(excinfo.value)
    assert "pw-secret-123" not in repr(excinfo.value)


# --- no connection without an explicit port -------------------------------------------

_RECORD_CONNECTS = r"""
import psycopg2

def _record(*args, **kwargs):
    with open({log!r}, "a") as handle:
        handle.write("connection attempted\n")
    raise RuntimeError("connection attempt blocked by the test")

psycopg2.connect = _record
"""


@pytest.mark.parametrize("test_port", [None, "", "  "])
def test_database_tests_skip_and_never_connect_without_test_db_port(tmp_path, test_port):
    """Run the real fixture tests in a child pytest that has no usable TEST_DB_PORT.

    The child sees the tempting values (DB_PORT=5432, PGPORT=5432, a development DB_NAME)
    and a driver whose connect() records any attempt and fails. It must skip every
    PostgreSQL test, pass, and never call connect().
    """
    log = tmp_path / "connect_attempts.txt"
    (tmp_path / "record_connects.py").write_text(
        _RECORD_CONNECTS.format(log=str(log)), encoding="utf-8"
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("TEST_DB_", "DB_", "PG"))
    }
    env.update(
        DB_HOST="localhost",
        DB_PORT="5432",
        PGPORT="5432",
        DB_NAME="cinema_dev",
        DB_USER="someone",
        PYTHONPATH=str(tmp_path),
    )
    if test_port is not None:
        env["TEST_DB_PORT"] = test_port

    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "tests/test_database_fixture.py",
            "-q", "-rs", "-p", "record_connects", "-p", "no:cacheprovider",
        ],
        cwd=config.PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert re.search(r"\d+ skipped", output), output
    assert "passed" not in output and "failed" not in output and "error" not in output.lower()
    assert "TEST_DB_PORT is not set" in output
    assert not log.exists(), "psycopg2.connect() was called although TEST_DB_PORT was missing"


def test_unreachable_server_raises_operational_error_without_leaking_credentials():
    settings = ServerSettings(
        port=1, host="127.0.0.1", user="nobody", password="pw-secret-123", connect_timeout=1
    )

    with pytest.raises(psycopg2.OperationalError) as excinfo:
        disposable_db.check_server(settings)

    assert "pw-secret-123" not in str(excinfo.value)
