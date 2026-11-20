import os

import psycopg2
import pytest
from flask import Flask

from app import config, create_app
from app.config import ConfigError

DEV_ENV = {
    "SECRET_KEY": "a-secret-key-with-enough-length",
    "DB_NAME": "cinema_dev",
    "DB_USER": "cinema_app",
}


@pytest.fixture
def dev_env(monkeypatch):
    for name, value in DEV_ENV.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def no_database(monkeypatch):
    """Fail the test if anything tries to open a PostgreSQL connection."""

    def refuse(*args, **kwargs):
        raise AssertionError("a PostgreSQL connection was attempted")

    monkeypatch.setattr(psycopg2, "connect", refuse)


def test_create_app_with_testing_config_needs_no_environment():
    app = create_app("testing")

    assert isinstance(app, Flask)
    assert app.testing is True
    assert app.config["SECRET_KEY"] == config.TESTING_SECRET_KEY
    assert app.config["DB_NAME"] is None


def test_default_timezone_is_available_in_app_config():
    assert create_app("testing").config["APP_TIMEZONE"] == "Asia/Seoul"


def test_timezone_is_configurable(monkeypatch):
    monkeypatch.setenv("APP_TIMEZONE", "UTC")

    assert create_app("testing").config["APP_TIMEZONE"] == "UTC"


def test_create_app_defaults_to_development_config(dev_env):
    app = create_app()

    assert app.testing is False
    assert app.debug is False
    assert app.config["DB_NAME"] == "cinema_dev"
    assert app.config["DB_USER"] == "cinema_app"
    assert app.config["DB_HOST"] == "localhost"
    assert app.config["DB_PORT"] == 5432
    assert app.config["SECRET_KEY"] == DEV_ENV["SECRET_KEY"]


def test_development_debug_is_opt_in(dev_env, monkeypatch):
    monkeypatch.setenv("FLASK_DEBUG", "1")

    assert create_app("development").debug is True


def test_development_config_without_environment_fails_clearly():
    with pytest.raises(ConfigError, match="SECRET_KEY is required"):
        create_app("development")


def test_invalid_environment_value_fails_clearly(dev_env, monkeypatch):
    monkeypatch.setenv("DB_PORT", "not-a-number")

    with pytest.raises(ConfigError, match="DB_PORT"):
        create_app()


def test_unknown_config_name_fails_clearly():
    with pytest.raises(ConfigError, match="Unknown configuration"):
        create_app("production")


def test_config_overrides_are_applied_after_loading():
    app = create_app("testing", {"DB_NAME": "cinema_test_example", "CUSTOM": 1})

    assert app.config["DB_NAME"] == "cinema_test_example"
    assert app.config["CUSTOM"] == 1
    assert app.config["TESTING"] is True


def test_each_call_returns_an_independent_app():
    first = create_app("testing", {"CUSTOM": "first"})
    second = create_app("testing")

    assert first is not second
    assert "CUSTOM" not in second.config


def test_session_cookie_flags_are_set():
    app = create_app("testing")

    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_app_serves_requests_with_the_test_client():
    # No routes exist yet: an unknown path must give a normal 404, not an error.
    assert create_app("testing").test_client().get("/").status_code == 404


def test_development_config_loads_the_dotenv_file(tmp_path, monkeypatch):
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text(
        "SECRET_KEY=a-secret-key-from-the-dotenv-file\nDB_NAME=from_file\nDB_USER=file_user\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "DOTENV_PATH", dotenv_file)
    for name in ("SECRET_KEY", "DB_NAME", "DB_USER"):  # undone after the test
        monkeypatch.setenv(name, "placeholder")
        monkeypatch.delenv(name)

    app = create_app("development")

    assert app.config["DB_NAME"] == "from_file"
    assert app.config["SECRET_KEY"] == "a-secret-key-from-the-dotenv-file"


def test_testing_config_does_not_load_the_dotenv_file(tmp_path, monkeypatch):
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("DB_NAME=dev_database\n", encoding="utf-8")
    monkeypatch.setattr(config, "DOTENV_PATH", dotenv_file)

    app = create_app("testing")

    assert app.config["DB_NAME"] is None
    assert "DB_NAME" not in os.environ


def test_creating_the_app_never_connects_to_postgresql(dev_env, no_database, monkeypatch):
    # Point at an address nothing listens on: creation must not even try.
    monkeypatch.setenv("DB_HOST", "192.0.2.1")
    monkeypatch.setenv("DB_PORT", "1")

    create_app("development")
    create_app("testing")
