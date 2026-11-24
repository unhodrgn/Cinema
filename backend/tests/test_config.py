import os

import pytest

from app.core import config
from app.core.config import ConfigError

VALID_ENV = {
    "SECRET_KEY": "a-secret-key-with-enough-length",
    "DB_NAME": "cinema_dev",
    "DB_USER": "cinema_app",
}


def env(**overrides):
    values = dict(VALID_ENV)
    values.update(overrides)
    return values


# --- defaults and loading -------------------------------------------------------------


def test_development_defaults():
    cfg = config.DevelopmentConfig(VALID_ENV)

    assert cfg.DB_HOST == "localhost"
    assert cfg.DB_PORT == 5432
    assert cfg.DB_CONNECT_TIMEOUT == 5
    assert cfg.DB_PASSWORD is None
    assert cfg.DEBUG is False
    assert cfg.TESTING is False


def test_default_timezone_is_asia_seoul():
    assert config.DEFAULT_TIMEZONE == "Asia/Seoul"
    assert config.DevelopmentConfig(VALID_ENV).APP_TIMEZONE == "Asia/Seoul"
    assert config.TestingConfig({}).APP_TIMEZONE == "Asia/Seoul"


def test_all_variables_are_loaded_from_the_environment():
    cfg = config.DevelopmentConfig(
        env(
            DB_HOST="db.example.org",
            DB_PORT="6543",
            DB_PASSWORD="s3cret",
            DB_CONNECT_TIMEOUT="12",
            APP_TIMEZONE="UTC",
            FLASK_DEBUG="1",
        )
    )

    assert cfg.SECRET_KEY == VALID_ENV["SECRET_KEY"]
    assert cfg.DB_HOST == "db.example.org"
    assert cfg.DB_PORT == 6543
    assert cfg.DB_NAME == "cinema_dev"
    assert cfg.DB_USER == "cinema_app"
    assert cfg.DB_PASSWORD == "s3cret"
    assert cfg.DB_CONNECT_TIMEOUT == 12
    assert cfg.APP_TIMEZONE == "UTC"
    assert cfg.DEBUG is True


def test_config_reads_the_real_environment_when_no_mapping_is_given(monkeypatch):
    for name, value in env(DB_PORT="6000").items():
        monkeypatch.setenv(name, value)

    cfg = config.DevelopmentConfig()

    assert cfg.DB_NAME == "cinema_dev"
    assert cfg.DB_PORT == 6000


def test_blank_values_are_treated_as_unset():
    cfg = config.DevelopmentConfig(
        env(DB_HOST="  ", DB_PORT="", DB_PASSWORD="", APP_TIMEZONE="", FLASK_DEBUG="")
    )

    assert cfg.DB_HOST == "localhost"
    assert cfg.DB_PORT == 5432
    assert cfg.DB_PASSWORD is None
    assert cfg.APP_TIMEZONE == "Asia/Seoul"
    assert cfg.DEBUG is False


def test_session_cookie_flags():
    cfg = config.DevelopmentConfig(VALID_ENV)

    assert cfg.SESSION_COOKIE_HTTPONLY is True
    assert cfg.SESSION_COOKIE_SAMESITE == "Lax"


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_flask_debug_truthy_values(value):
    assert config.DevelopmentConfig(env(FLASK_DEBUG=value)).DEBUG is True


@pytest.mark.parametrize("value", ["0", "false", "No", "off"])
def test_flask_debug_falsy_values(value):
    assert config.DevelopmentConfig(env(FLASK_DEBUG=value)).DEBUG is False


def test_base_config_never_enables_debug():
    assert config.Config(env(FLASK_DEBUG="1")).DEBUG is False


# --- missing and invalid values -------------------------------------------------------


def test_missing_required_values_are_all_reported():
    with pytest.raises(ConfigError) as excinfo:
        config.DevelopmentConfig({})

    message = str(excinfo.value)
    assert "SECRET_KEY is required" in message
    assert "DB_NAME is required" in message
    assert "DB_USER is required" in message
    assert ".env.example" in message


@pytest.mark.parametrize("missing", ["SECRET_KEY", "DB_NAME", "DB_USER"])
def test_each_required_value_is_enforced(missing):
    values = env()
    del values[missing]

    with pytest.raises(ConfigError, match=f"{missing} is required"):
        config.DevelopmentConfig(values)


def test_short_secret_key_is_rejected_without_echoing_it():
    with pytest.raises(ConfigError) as excinfo:
        config.DevelopmentConfig(env(SECRET_KEY="change-me"))

    assert "SECRET_KEY must be at least" in str(excinfo.value)
    assert "change-me" not in str(excinfo.value)


@pytest.mark.parametrize("value", ["abc", "0", "-1", "65536", "5432.5"])
def test_invalid_db_port(value):
    with pytest.raises(ConfigError, match="DB_PORT"):
        config.DevelopmentConfig(env(DB_PORT=value))


@pytest.mark.parametrize("value", ["abc", "0", "61"])
def test_invalid_db_connect_timeout(value):
    with pytest.raises(ConfigError, match="DB_CONNECT_TIMEOUT"):
        config.DevelopmentConfig(env(DB_CONNECT_TIMEOUT=value))


@pytest.mark.parametrize("value", ["maybe", "2", "enabled"])
def test_invalid_flask_debug(value):
    with pytest.raises(ConfigError, match="FLASK_DEBUG"):
        config.DevelopmentConfig(env(FLASK_DEBUG=value))


@pytest.mark.parametrize("value", ["Seoul", "Asia/", "Asia/Seoul; DROP", "Asia Seoul", "/Seoul"])
def test_invalid_timezone_format(value):
    with pytest.raises(ConfigError, match="APP_TIMEZONE"):
        config.DevelopmentConfig(env(APP_TIMEZONE=value))


@pytest.mark.parametrize(
    "value", ["Asia/Seoul", "UTC", "GMT", "America/Argentina/Buenos_Aires", "Etc/GMT+9"]
)
def test_valid_timezone_format(value):
    assert config.DevelopmentConfig(env(APP_TIMEZONE=value)).APP_TIMEZONE == value


def test_several_problems_are_reported_together():
    with pytest.raises(ConfigError) as excinfo:
        config.DevelopmentConfig(env(DB_PORT="x", DB_CONNECT_TIMEOUT="0"))

    message = str(excinfo.value)
    assert "DB_PORT" in message and "DB_CONNECT_TIMEOUT" in message


def test_error_messages_never_contain_the_db_password():
    with pytest.raises(ConfigError) as excinfo:
        config.DevelopmentConfig(env(DB_PASSWORD="hunter2-password", DB_PORT="x"))

    assert "hunter2-password" not in str(excinfo.value)


# --- testing configuration ------------------------------------------------------------


def test_testing_config_needs_no_environment():
    cfg = config.TestingConfig({})

    assert cfg.TESTING is True
    assert cfg.DEBUG is False
    assert cfg.DB_HOST == "localhost"
    assert cfg.DB_PORT == 5432


def test_testing_config_ignores_the_environment_secret_key():
    cfg = config.TestingConfig(env(SECRET_KEY="a-real-looking-secret-key-123"))

    assert cfg.SECRET_KEY == config.TESTING_SECRET_KEY


def test_testing_config_never_reads_db_name_from_the_environment():
    cfg = config.TestingConfig(env(DB_NAME="cinema_dev"))

    assert cfg.DB_NAME is None


def test_testing_config_reads_connection_settings_from_the_environment():
    cfg = config.TestingConfig(env(DB_HOST="db.local", DB_PORT="6000", DB_PASSWORD="pw"))

    assert (cfg.DB_HOST, cfg.DB_PORT, cfg.DB_USER, cfg.DB_PASSWORD) == (
        "db.local",
        6000,
        "cinema_app",
        "pw",
    )


def test_testing_config_still_validates_what_it_reads():
    with pytest.raises(ConfigError, match="DB_PORT"):
        config.TestingConfig({"DB_PORT": "nope"})


# --- repr, lookup and .env loading ----------------------------------------------------


def test_repr_does_not_expose_secrets():
    cfg = config.DevelopmentConfig(env(DB_PASSWORD="hunter2-password"))

    text = repr(cfg)
    assert "hunter2-password" not in text
    assert VALID_ENV["SECRET_KEY"] not in text
    assert "cinema_dev" in text


def test_get_config_class():
    assert config.get_config_class("development") is config.DevelopmentConfig
    assert config.get_config_class("testing") is config.TestingConfig


def test_unknown_config_name_is_rejected():
    with pytest.raises(ConfigError, match="Unknown configuration 'production'"):
        config.get_config_class("production")


def _forget_after_test(monkeypatch, *names):
    """Make sure variables a test sets through load_dotenv are removed afterwards."""
    for name in names:
        monkeypatch.setenv(name, "placeholder")
        monkeypatch.delenv(name)


def test_load_environment_reads_a_dotenv_file(tmp_path, monkeypatch):
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("DB_NAME=from_file\nDB_USER=file_user\n", encoding="utf-8")
    _forget_after_test(monkeypatch, "DB_NAME", "DB_USER")

    assert config.load_environment(dotenv_file) is True

    assert os.environ["DB_NAME"] == "from_file"
    assert os.environ["DB_USER"] == "file_user"


def test_real_environment_wins_over_dotenv_file(tmp_path, monkeypatch):
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("DB_NAME=from_file\n", encoding="utf-8")
    monkeypatch.setenv("DB_NAME", "from_environment")

    config.load_environment(dotenv_file)

    assert os.environ["DB_NAME"] == "from_environment"


def test_load_environment_without_a_file_is_harmless(tmp_path):
    assert config.load_environment(tmp_path / "missing.env") is False
